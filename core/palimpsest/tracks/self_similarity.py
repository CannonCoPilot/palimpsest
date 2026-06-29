"""Self-similarity matrix track — a fail-loud, embedding-agnostic layer consumer (Wave-0 P7).

This track does not chunk, embed, or detect repeats itself. The user names the layers to analyse
(one ``{chunk, repeat_mask, embedding?}`` bundle per chunk size); the track binds them by explicit
label, fails loud if a required layer is absent, and runs the similarity math on the bound layers.
It supports a family of metrics — ``cosine`` / ``jaccard`` (embedding-based) and ``word_overlap`` /
``edit_distance`` (text-only) — selected per run; an embedding layer is required only for the
embedding-based metrics.

LASTZ alignment (the seed-and-extend pass that surfaces aligned passages on top of the matrix):
1. Coarse edit distance on the bound chunks → NxN matrix
2. Find top K off-diagonal local optima (K = 2 × CPU cores)
3. At each optimum, extend with character-level matching along the diagonal
   in two directions: parallel (1,1) and antiparallel (1,-1).
   Parallel finds repeated passages; antiparallel finds chiasmus (ABBA) structures.
4. Refine boundaries with 1-word-stride sliding windows for sub-chunk precision
5. Threshold calibrated empirically via random pseudo-chunk alignment
6. Mirror deduplication (A↔B counted once)

Repeat handling is flag-only and consumed from the bound ``repeat_mask`` layer: masked chunks are
skipped in matrix computation, then unmasked for final scoring. The track never re-derives the mask.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from palimpsest.project import Project
from palimpsest.tracks.bundles import ComparisonSpec, LayerBundle, resolve_explicit_bundle
from palimpsest.tracks.chunking import build_word_positions
from palimpsest.tracks.params import Param, ParameterizedTrack
from palimpsest.tracks.repeats import STOPWORDS
from palimpsest.tracks.requirements import LayerResolutionError
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

logger = logging.getLogger(__name__)

METRICS = ("cosine", "jaccard", "word_overlap", "edit_distance")
DEFAULT_CHUNK_SIZE = 7
# Matrices larger than this many chunks per side are unusually heavy (an N×N float32 matrix);
# warn-only — the run proceeds as the user requested rather than silently skipping.
WARN_MATRIX_DIM = 16000

# Locked analytical constants (G2 / design §6): these change the result for a fixed input — they set
# the LASTZ alignment cutoff and decide which text is masked out of analysis — so they must be
# DECLARED and REPORTED, not buried as function-default magic numbers (audit A3). They are not yet
# user-tunable ("locked"), but parameters() and the signal manifest now report them, so a run is
# reconstructible and the cutoffs are auditable. Surfaced as LOCKED_CONSTANTS below.
LASTZ_CALIBRATION_SEED = 42            # RNG seed for the shuffled-pair null distribution
LASTZ_CALIBRATION_SAMPLES = 1000       # number of shuffled pseudo-chunk pairs sampled
LASTZ_CALIBRATION_PERCENTILE = 0.95    # percentile of the null distribution used as the cutoff
LASTZ_THRESHOLD_FLOOR = 0.1            # minimum identity threshold (floor under the calibrated p95)
LASTZ_SMALL_SAMPLE_THRESHOLD = 0.3     # fallback threshold when there is too little text to calibrate
# The declared-and-reported view of the LASTZ calibration constants above. Reported in parameters()
# (→ {track}.run.json provenance) and written into the signal manifest metadata so a stored run is
# reconstructible and the cutoffs are auditable. The masking cutoffs are deliberately NOT here: post-P7
# this track does not detect or apply repeat masking — those values live with (and are reported by) the
# bound repeat / repeat_mask layers, echoed per bundle in the manifest's layer_inputs.
LOCKED_CONSTANTS: dict[str, dict[str, float]] = {
    "calibration": {
        "seed": LASTZ_CALIBRATION_SEED,
        "samples": LASTZ_CALIBRATION_SAMPLES,
        "percentile": LASTZ_CALIBRATION_PERCENTILE,
        "threshold_floor": LASTZ_THRESHOLD_FLOOR,
        "small_sample_threshold": LASTZ_SMALL_SAMPLE_THRESHOLD,
    },
}

# STOPWORDS lives in palimpsest.tracks.repeats (imported above) — one shared definition for the
# content-token filter used here and by the repeat helpers.


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _discover_chunk_sizes(signals_dir: Path) -> list[int]:
    """Find all computed chunk sizes by scanning for self_similarity_csN/ directories."""
    sizes: list[int] = []
    for entry in signals_dir.iterdir():
        if entry.is_dir() and entry.name.startswith("self_similarity_cs"):
            try:
                cs = int(entry.name.replace("self_similarity_cs", ""))
                if any((entry / f"{m}.bin").exists() for m in METRICS):
                    sizes.append(cs)
            except ValueError:
                pass
    return sorted(sizes)


def _content_tokens(words: list[str]) -> list[str]:
    """Extract content tokens from word list, removing stopwords and punctuation."""
    return [re.sub(r'[^a-z\']', '', w.lower()) for w in words
            if re.sub(r'[^a-z\']', '', w.lower()) not in STOPWORDS
            and len(re.sub(r'[^a-z\']', '', w.lower())) > 1]


def _content_set(words: list[str]) -> set[str]:
    return set(_content_tokens(words))


# ---------------------------------------------------------------------------
# Metric computations
# ---------------------------------------------------------------------------

def _cosine_matrix(embeddings: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms > 1e-8, norms, 1.0)
    normed = embeddings / norms
    matrix = normed @ normed.T
    np.clip(matrix, -1.0, 1.0, out=matrix)
    return matrix


def _jaccard_matrix(embeddings: np.ndarray) -> np.ndarray:
    binary = (embeddings > 0).astype(np.float32)
    intersection = binary @ binary.T
    row_sums = binary.sum(axis=1)
    union = row_sums[:, None] + row_sums[None, :] - intersection
    return np.where(union > 0, intersection / union, 0.0).astype(np.float32)


def _word_overlap_matrix(chunks: list[dict[str, Any]]) -> np.ndarray:
    """Content-word Jaccard similarity between chunks.
    Chunks marked masked=True are skipped (their matrix cells remain 0)."""
    n = len(chunks)
    sets = [_content_set(c["words"]) for c in chunks]
    matrix = np.zeros((n, n), dtype=np.float32)
    for i in range(n):
        if chunks[i].get("masked"):
            continue
        if not sets[i]:
            continue
        matrix[i, i] = 1.0
        for j in range(i + 1, n):
            if chunks[j].get("masked"):
                continue
            if not sets[j]:
                continue
            isect = len(sets[i] & sets[j])
            if isect == 0:
                continue
            union = len(sets[i] | sets[j])
            val = isect / union
            matrix[i, j] = val
            matrix[j, i] = val
    return matrix


def _edit_distance_tokens(a: list[str], b: list[str]) -> int:
    """Token-level Levenshtein distance.

    Early-exit optimisation: if the two token sets share no common tokens at
    all (zero intersection), the minimum edit distance equals max(la, lb) and
    there is no point running the O(la*lb) DP.  This is a guaranteed lower
    bound — if the intersection is empty every token in the longer sequence
    must be inserted, costing at least max(la, lb).  We return that bound
    directly so the caller can skip the full DP for clearly dissimilar pairs.
    """
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    # Fast set-intersection check before expensive DP
    if not (set(a) & set(b)):
        return max(la, lb)
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[lb]


def _edit_distance_matrix(chunks: list[dict[str, Any]]) -> np.ndarray:
    """Normalized content-word edit distance similarity between chunks.
    Chunks marked masked=True are skipped (their matrix cells remain 0)."""
    n = len(chunks)
    content = [_content_tokens(c["words"]) for c in chunks]
    matrix = np.zeros((n, n), dtype=np.float32)
    for i in range(n):
        if chunks[i].get("masked"):
            continue
        la = len(content[i])
        if la == 0:
            continue
        matrix[i, i] = 1.0
        for j in range(i + 1, n):
            if chunks[j].get("masked"):
                continue
            lb = len(content[j])
            if lb == 0:
                continue
            if la > 3 * lb or lb > 3 * la:
                continue
            dist = _edit_distance_tokens(content[i], content[j])
            sim = 1.0 - dist / max(la, lb)
            if sim > 0.05:
                matrix[i, j] = sim
                matrix[j, i] = sim
    return matrix


# ---------------------------------------------------------------------------
# Similarity-method family (Wave-0 P7)
# ---------------------------------------------------------------------------
# An extensible registry over the four matrix builders. ``requires_embedding`` is the single switch
# tying a method to whether a bound input needs an embedding layer; text-only methods ignore the
# ``embeddings`` argument. Adding a new similarity method later = one registry entry, no other change.

@dataclass(frozen=True)
class SimilarityMethod:
    """One similarity metric: its name, whether it needs an embedding array, and the builder turning
    ``(chunks, embeddings)`` into an N×N float32 matrix.

    The trailing descriptors are forward metadata for the two-operand generalization (P9/FR-18..20;
    consumed by P10 cross-text). ``representation`` is what the builder compares over (``embedding`` or
    ``tokens``); ``symmetric`` means ``R(a, b) == R(b, a)``; ``supports_cross`` means the method
    generalizes to two distinct operands. Every current method is symmetric and cross-capable — only
    the executed self (``A = B``) path matters today, so the descriptors change no behavior."""

    name: str
    requires_embedding: bool
    build: Callable[..., np.ndarray]
    representation: str = "embedding"
    symmetric: bool = True
    supports_cross: bool = True


_METHODS: dict[str, SimilarityMethod] = {
    "cosine": SimilarityMethod(
        "cosine", True, lambda chunks, *, embeddings: _cosine_matrix(embeddings)
    ),
    "jaccard": SimilarityMethod(
        "jaccard", True, lambda chunks, *, embeddings: _jaccard_matrix(embeddings)
    ),
    "word_overlap": SimilarityMethod(
        "word_overlap", False, lambda chunks, *, embeddings=None: _word_overlap_matrix(chunks),
        representation="tokens",
    ),
    "edit_distance": SimilarityMethod(
        "edit_distance", False, lambda chunks, *, embeddings=None: _edit_distance_matrix(chunks),
        representation="tokens",
    ),
}

# METRICS (module constant, imported by server.py and validated against by the frontend) must stay in
# lock-step with the registry's canonical, cosine-first order. Assert rather than redefine, so the
# import site at the top of the module is unchanged.
assert tuple(_METHODS) == METRICS, "similarity-method registry drifted from METRICS order"


def resolve_methods(selected: list[str]) -> list[SimilarityMethod]:
    """Resolve user-selected metric names to :class:`SimilarityMethod` objects in canonical
    (cosine-first) order. Unknown names fail loud, mirroring the legacy ``_validate_metrics``."""
    unknown = [m for m in selected if m not in _METHODS]
    if unknown:
        raise ValueError(
            f"unknown similarity metric(s): {', '.join(unknown)}; "
            f"valid metrics: {', '.join(_METHODS)}"
        )
    return [_METHODS[m] for m in METRICS if m in selected]


# ---------------------------------------------------------------------------
# LASTZ-style seed-and-extend alignment
# ---------------------------------------------------------------------------

def _find_local_optima(matrix: np.ndarray, k: int, min_gap: int = 3) -> list[tuple[int, int, float]]:
    """Find top K off-diagonal local maxima in the matrix.
    Excludes near-diagonal cells (within min_gap of diagonal)."""
    n = matrix.shape[0]
    flat = matrix.copy()
    # Mask diagonal and near-diagonal
    for d in range(-min_gap, min_gap + 1):
        np.fill_diagonal(flat[max(0, -d):, max(0, d):], 0.0)

    optima: list[tuple[int, int, float]] = []
    # Greedily extract top-K, masking around each found optimum
    for _ in range(k):
        idx = np.argmax(flat)
        i, j = divmod(idx, n)
        val = flat[i, j]
        if val <= 0.0:
            break
        optima.append((int(i), int(j), float(val)))
        # Mask a region around this optimum to avoid nearby duplicates
        r = max(2, min_gap)
        flat[max(0, i - r):i + r + 1, max(0, j - r):j + r + 1] = 0.0
    return optima


def _calibrate_threshold(
    chunks: list[dict[str, Any]], n_samples: int = LASTZ_CALIBRATION_SAMPLES
) -> float:
    """Empirically calibrate identity threshold from shuffled pseudo-chunk pairs.
    Shuffles the full word list and takes contiguous slices to build a true
    null distribution (no text-order preservation). Returns the calibrated percentile.

    All cutoffs/seeds are the declared LOCKED_CONSTANTS (audit A3): the cutoff this returns
    decides which alignments survive, so it is reported, not hidden."""
    rng = np.random.default_rng(LASTZ_CALIBRATION_SEED)
    n = len(chunks)
    if n < 10:
        return LASTZ_SMALL_SAMPLE_THRESHOLD

    all_words: list[str] = []
    for c in chunks:
        all_words.extend(c["words"])

    if len(all_words) < 20:
        return LASTZ_SMALL_SAMPLE_THRESHOLD

    chunk_size = len(chunks[0]["words"]) if chunks else DEFAULT_CHUNK_SIZE
    scores: list[float] = []

    for _ in range(n_samples):
        shuffled = rng.permutation(all_words)
        pseudo_a = " ".join(shuffled[:chunk_size])
        pseudo_b = " ".join(shuffled[chunk_size:2 * chunk_size])
        identity = _char_identity(pseudo_a, pseudo_b)
        scores.append(identity)

    scores.sort()
    p95 = scores[int(len(scores) * LASTZ_CALIBRATION_PERCENTILE)]
    logger.info("LASTZ threshold calibrated: 95th pct = %.3f (from %d shuffled pairs)", p95, n_samples)
    return max(p95, LASTZ_THRESHOLD_FLOOR)


def _char_identity(a: str, b: str) -> float:
    """Character-level identity score via LCS ratio.
    For long strings, uses banded LCS (O(n*bandwidth)) instead of switching metrics."""
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0
    if la > 500 or lb > 500:
        return _banded_lcs_identity(a, b, bandwidth=200)

    prev = [0] * (lb + 1)
    for i in range(1, la + 1):
        curr = [0] * (lb + 1)
        for j in range(1, lb + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    lcs_len = prev[lb]
    return (2 * lcs_len) / (la + lb)


def _banded_lcs_identity(a: str, b: str, bandwidth: int = 200) -> float:
    """Banded LCS for long strings — O(n * bandwidth) instead of O(n * m).
    Only considers diagonals within `bandwidth` of the main diagonal."""
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0
    if la > lb:
        a, b = b, a
        la, lb = lb, la

    prev = [0] * (lb + 1)
    for i in range(1, la + 1):
        curr = [0] * (lb + 1)
        diag_center = int(i * lb / la)
        j_start = max(1, diag_center - bandwidth)
        j_end = min(lb, diag_center + bandwidth)
        for j in range(j_start, j_end + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    lcs_len = prev[lb]
    return (2 * lcs_len) / (la + lb)


def _sliding_window_refine(
    text: str,
    words: list[str],
    word_positions: list[tuple[int, int]],
    coarse_start_a: int,
    coarse_end_a: int,
    coarse_start_b: int,
    coarse_end_b: int,
    chunk_size: int,
    threshold: float,
) -> tuple[int, int, int, int]:
    """Refine coarse chunk boundaries to word-level precision using sliding windows.

    Slides a window of `chunk_size` words at stride 1 around each boundary,
    testing character identity to find the precise word offset where the
    alignment starts/ends. Returns refined (char_start_a, char_end_a,
    char_start_b, char_end_b).
    """
    n_words = len(words)
    # Convert char positions to word indices
    char_to_word: dict[int, int] = {}
    for wi, (ws, _we) in enumerate(word_positions):
        char_to_word[ws] = wi

    def _char_start_to_word(cs: int) -> int:
        best = 0
        for wi, (ws, _) in enumerate(word_positions):
            if ws <= cs:
                best = wi
            else:
                break
        return best

    def _char_end_to_word(ce: int) -> int:
        for wi, (_, we) in enumerate(word_positions):
            if we >= ce:
                return wi
        return n_words - 1

    w_start_a = _char_start_to_word(coarse_start_a)
    w_end_a = _char_end_to_word(coarse_end_a)
    w_start_b = _char_start_to_word(coarse_start_b)
    w_end_b = _char_end_to_word(coarse_end_b)

    def _window_text(start_word: int, end_word: int) -> str:
        s = word_positions[max(0, start_word)][0]
        e = word_positions[min(n_words - 1, end_word)][1]
        return text[s:e]

    # Refine start boundary: slide backward from coarse start, 1 word at a time
    search_range = min(chunk_size, w_start_a, w_start_b)
    refined_start_a, refined_start_b = w_start_a, w_start_b
    for offset in range(1, search_range + 1):
        wa = w_start_a - offset
        wb = w_start_b - offset
        if wa < 0 or wb < 0:
            break
        window_a = _window_text(wa, wa + chunk_size - 1)
        window_b = _window_text(wb, wb + chunk_size - 1)
        if _char_identity(window_a, window_b) >= threshold:
            refined_start_a = wa
            refined_start_b = wb
        else:
            break

    # Refine end boundary: slide forward from coarse end
    search_range = min(chunk_size, n_words - 1 - w_end_a, n_words - 1 - w_end_b)
    refined_end_a, refined_end_b = w_end_a, w_end_b
    for offset in range(1, search_range + 1):
        wa = w_end_a + offset
        wb = w_end_b + offset
        if wa >= n_words or wb >= n_words:
            break
        window_a = _window_text(wa - chunk_size + 1, wa)
        window_b = _window_text(wb - chunk_size + 1, wb)
        if _char_identity(window_a, window_b) >= threshold:
            refined_end_a = wa
            refined_end_b = wb
        else:
            break

    return (
        word_positions[refined_start_a][0],
        word_positions[refined_end_a][1],
        word_positions[refined_start_b][0],
        word_positions[refined_end_b][1],
    )


def _extend_alignment(
    text: str,
    chunks: list[dict[str, Any]],
    seed_i: int,
    seed_j: int,
    threshold: float,
    chunk_size: int,
    direction: tuple[int, int] = (1, 1),
) -> dict[str, Any] | None:
    """Extend from a seed (chunk_i, chunk_j) along a diagonal direction,
    performing character-level matching.  Extends outward in both directions
    until identity drops below threshold, then refines boundaries with
    sliding 1-word-stride windows for sub-chunk precision.

    Parameters
    ----------
    direction:
        (di, dj) step applied at each forward extension step.
        (1, 1)  — parallel: both indices increase (standard repeated passage).
        (1, -1) — antiparallel: row increases while column decreases,
                  detecting chiasmus / ABBA mirror structures.
    """
    n = len(chunks)
    di, dj = direction
    best_start_i, best_start_j = seed_i, seed_j
    best_end_i, best_end_j = seed_i, seed_j

    def _in_bounds(ci: int, cj: int) -> bool:
        return 0 <= ci < n and 0 <= cj < n

    def _is_self(ci: int, cj: int) -> bool:
        """True when both pointers land on the same chunk (self-comparison)."""
        return ci == cj

    # Extend in the forward direction
    ci, cj = seed_i, seed_j
    while _in_bounds(ci, cj) and not _is_self(ci, cj):
        text_a = chunks[ci]["text"]
        text_b = chunks[cj]["text"]
        identity = _char_identity(text_a, text_b)
        if identity < threshold:
            break
        best_end_i = ci
        best_end_j = cj
        ci += di
        cj += dj

    # Extend in the backward direction (negate the step)
    ci, cj = seed_i - di, seed_j - dj
    while _in_bounds(ci, cj) and not _is_self(ci, cj):
        text_a = chunks[ci]["text"]
        text_b = chunks[cj]["text"]
        identity = _char_identity(text_a, text_b)
        if identity < threshold:
            break
        best_start_i = ci
        best_start_j = cj
        ci -= di
        cj -= dj

    # Length is measured along the row dimension (always monotone increasing)
    length = best_end_i - best_start_i + 1
    if length < 2:
        return None

    coarse_start_a = chunks[best_start_i]["start"]
    coarse_end_a = chunks[best_end_i]["end"]

    # For antiparallel, chunk_b spans from the *higher* column index to the lower
    if dj == -1:
        coarse_start_b = chunks[best_end_j]["start"]
        coarse_end_b = chunks[best_start_j]["end"]
    else:
        coarse_start_b = chunks[best_start_j]["start"]
        coarse_end_b = chunks[best_end_j]["end"]

    # Sliding window refinement for sub-chunk boundary precision
    words, word_positions = build_word_positions(text)
    if len(words) > 0:
        refined = _sliding_window_refine(
            text, words, word_positions,
            coarse_start_a, coarse_end_a,
            coarse_start_b, coarse_end_b,
            chunk_size, threshold,
        )
        char_start_a, char_end_a, char_start_b, char_end_b = refined
    else:
        char_start_a, char_end_a = coarse_start_a, coarse_end_a
        char_start_b, char_end_b = coarse_start_b, coarse_end_b

    region_a = text[char_start_a:char_end_a]
    region_b = text[char_start_b:char_end_b]
    overall_identity = _char_identity(region_a, region_b)

    alignment_direction = "parallel" if di == dj else "antiparallel"

    return {
        "chunk_start_a": best_start_i,
        "chunk_end_a": best_end_i,
        "chunk_start_b": best_start_j,
        "chunk_end_b": best_end_j,
        "char_start_a": char_start_a,
        "char_end_a": char_end_a,
        "char_start_b": char_start_b,
        "char_end_b": char_end_b,
        "length_chunks": length,
        "identity": round(overall_identity, 4),
        "seed_score": float(round(float(_char_identity(
            chunks[seed_i]["text"], chunks[seed_j]["text"]
        )), 4)),
        "direction": alignment_direction,
    }


# ---------------------------------------------------------------------------
# Exact-repeat masking (word-match n-gram phrases)
# ---------------------------------------------------------------------------
# _find_exact_repeats / _mask_repeats moved verbatim to palimpsest.tracks.repeats (imported above as
# the underscore aliases) so EmbeddingTrack can reuse them. _derive_formulaic_patterns stays here — it
# is self_similarity-specific (LASTZ formulaic-pattern derivation), not shared substrate.


def _derive_formulaic_patterns(
    chunks: list[dict[str, Any]],
    repeats: set[str],
    min_support: int = 3,
    max_wildcards: int = 2,
    max_pairwise_phrases: int = 300,
) -> list[dict[str, Any]]:
    """Derive formulaic patterns from exact repeats by generalizing with wildcards.

    Takes exact repeated phrases and tries to find abstract patterns like
    "X saith unto Y" where X/Y are variable slots. Works by:
    1. For each pair of similar-length repeats, compute token-level diff
    2. If they differ in <= max_wildcards positions, create a pattern with * wildcards
    3. Scan all chunks for pattern matches and count support

    Returns list of {pattern, support, examples} sorted by support descending.
    """
    if not repeats or len(repeats) < 2:
        return []

    # Group repeats by word count
    by_length: dict[int, list[list[str]]] = {}
    for phrase in repeats:
        tokens = phrase.split()
        by_length.setdefault(len(tokens), []).append(tokens)

    patterns: dict[str, dict[str, Any]] = {}

    for length, phrases in by_length.items():
        if length < 3 or len(phrases) < 2:
            continue

        # The pairwise generalization below is O(phrases²). Highly formulaic
        # texts (e.g. scripture) can yield thousands of same-length repeats, so
        # cap the group deterministically to keep this bounded.
        if len(phrases) > max_pairwise_phrases:
            logger.warning(
                "Formulaic patterns: %d length-%d phrases exceed cap %d; "
                "truncating to bound O(n²) pairwise generalization",
                len(phrases), length, max_pairwise_phrases,
            )
            phrases = sorted(phrases)[:max_pairwise_phrases]

        for i in range(len(phrases)):
            for j in range(i + 1, len(phrases)):
                a, b = phrases[i], phrases[j]
                diffs = [k for k in range(length) if a[k] != b[k]]

                if 1 <= len(diffs) <= max_wildcards:
                    template = list(a)
                    for d in diffs:
                        template[d] = "*"
                    pattern_key = " ".join(template)

                    if pattern_key not in patterns:
                        patterns[pattern_key] = {
                            "pattern": pattern_key,
                            "template": template,
                            "length": length,
                            "wildcard_positions": diffs,
                            "examples": set(),
                            "support": 0,
                        }
                    patterns[pattern_key]["examples"].add(" ".join(a))
                    patterns[pattern_key]["examples"].add(" ".join(b))

    # Count support: scan chunks for pattern matches
    all_tokens: list[list[str]] = []
    for chunk in chunks:
        all_tokens.append([re.sub(r"[^a-z']", "", w.lower()) for w in chunk["words"]])

    for pdata in patterns.values():
        template = pdata["template"]
        plen = len(template)
        count = 0
        for tokens in all_tokens:
            for start in range(len(tokens) - plen + 1):
                match = True
                for k in range(plen):
                    if template[k] != "*" and tokens[start + k] != template[k]:
                        match = False
                        break
                if match:
                    count += 1
                    matched_phrase = " ".join(tokens[start:start + plen])
                    pdata["examples"].add(matched_phrase)
        pdata["support"] = count

    # Filter by minimum support and serialize
    results = []
    for pdata in sorted(patterns.values(), key=lambda p: p["support"], reverse=True):
        if pdata["support"] >= min_support:
            results.append({
                "pattern": pdata["pattern"],
                "length": pdata["length"],
                "support": pdata["support"],
                "wildcard_positions": pdata["wildcard_positions"],
                "examples": sorted(pdata["examples"])[:10],
            })

    logger.info("Formulaic patterns: %d patterns with >= %d support", len(results), min_support)
    return results


def _lastz_align(
    text: str,
    chunks: list[dict[str, Any]],
    coarse_matrix: np.ndarray,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[dict[str, Any]]:
    """LASTZ-style seed-and-extend alignment on self-similarity matrix.

    Uses coarse non-overlapping chunks for seed detection, then refines
    alignment boundaries with sliding 1-word-stride windows.

    Each seed is tried in both directions:
    - (1, 1) parallel: both chunk indices increase — finds repeated passages.
    - (1,-1) antiparallel: row increases, column decreases — finds chiasmus
      (ABBA mirror structures) where themes appear in reverse order.

    Mirror deduplication is applied: an alignment A↔B is the same as B↔A
    regardless of direction, and is counted only once.
    """
    k = 2 * (os.cpu_count() or 4)
    optima = _find_local_optima(coarse_matrix, k)

    if not optima:
        return []

    threshold = _calibrate_threshold(chunks)
    logger.info("LASTZ: %d optima found, threshold=%.3f, chunk_size=%d", len(optima), threshold, chunk_size)

    alignments: list[dict[str, Any]] = []
    # Dedup key: frozenset of the two (start,end) chunk span pairs, plus direction,
    # so a parallel and antiparallel alignment at the same coordinates are kept distinct.
    seen: set[tuple[str, tuple[int, int], tuple[int, int]]] = set()

    directions: list[tuple[int, int]] = [(1, 1), (1, -1)]

    for seed_i, seed_j, _seed_score in optima:
        for direction in directions:
            result = _extend_alignment(
                text, chunks, seed_i, seed_j, threshold, chunk_size, direction=direction,
            )
            if result is None:
                continue
            # Deduplicate mirror alignments (A↔B same as B↔A within same direction)
            span_a = (result["chunk_start_a"], result["chunk_end_a"])
            span_b = (result["chunk_start_b"], result["chunk_end_b"])
            pair = tuple(sorted([span_a, span_b]))
            key = (result["direction"], pair[0], pair[1])
            if key in seen:
                continue
            seen.add(key)
            alignments.append(result)

    alignments.sort(key=lambda a: a["identity"], reverse=True)
    return alignments


# ---------------------------------------------------------------------------
# Layer-sourced chunk + embedding access (Wave-0 P7)
# ---------------------------------------------------------------------------

def reconstruct_chunks(bundle: LayerBundle) -> list[dict[str, Any]]:
    """Rebuild the chunk dicts the metric builders and LASTZ consume, entirely from layer data: texts
    and original-coordinate offsets from the chunk layer, the per-chunk ``masked`` flag from the
    repeat_mask layer (flag-only — never recomputed here). ``words = text.split()`` reproduces the
    original chunker's ``words`` (proven byte-identical to the inline chunker in P8), so the lexical
    metrics see identical input."""
    meta = bundle.chunk.manifest["metadata"]
    texts: list[str] = meta["chunk_texts"]
    offsets = bundle.chunk.manifest["segment_offsets"]
    masked = bundle.repeat_mask.manifest["metadata"]["masked"]
    if not (len(texts) == len(offsets) == len(masked)):
        raise ValueError(
            f"layer length mismatch for chunk layer '{bundle.chunk.label}': "
            f"{len(texts)} texts, {len(offsets)} offsets, {len(masked)} mask flags"
        )
    return [
        {"text": t, "start": int(s), "end": int(e), "words": t.split(), "masked": bool(mk)}
        for t, (s, e), mk in zip(texts, offsets, masked)
    ]


def load_embeddings(project: Project, bundle: LayerBundle) -> np.ndarray:
    """Load the vectors the embedding layer already computed — the consumer never embeds. Vectors come
    back in insertion order (= chunk order); the count must match the chunk layer or the layers are out
    of sync (fail loud)."""
    if bundle.embedding is None:
        raise ValueError("load_embeddings called for a bundle without an embedding layer")
    rel = bundle.embedding.vectorstore_path
    if not rel:
        raise ValueError(f"embedding layer '{bundle.embedding.label}' has no vectorstore path")
    db = Path(project.path) / rel
    if not db.exists():
        raise LayerResolutionError(
            f"embedding vectorstore '{rel}' for layer '{bundle.embedding.label}' is missing — re-run "
            "the embedding track"
        )
    store = SqliteVecStore.open_existing(db)
    try:
        vectors = store.get_all_vectors()
    finally:
        store.close()
    n_chunks = len(bundle.chunk.manifest["metadata"]["chunk_texts"])
    if len(vectors) != n_chunks:
        raise ValueError(
            f"embedding layer '{bundle.embedding.label}' has {len(vectors)} vectors but chunk layer "
            f"'{bundle.chunk.label}' has {n_chunks} chunks"
        )
    return np.array(vectors, dtype=np.float32)


def _embedding_provenance(bundle: LayerBundle) -> dict[str, Any] | None:
    """The bound embedding layer's identity, recorded in the manifest so the run is reconstructible
    (P3). ``None`` when no embedding-based metric was selected."""
    if bundle.embedding is None:
        return None
    cap = bundle.embedding.capability
    return {
        "provider": cap.get("provider"),
        "model": cap.get("model"),
        "dim": cap.get("dim"),
        "model_fingerprint": cap.get("model_fingerprint"),
        "layer_label": bundle.embedding.label,
    }


def _csv_list(value: Any) -> list[str]:
    """Param converter: a comma-separated string (or an already-list) → a list of metric names."""
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(v).strip() for v in value]


def _parse_inputs(value: Any) -> list[dict[str, str]]:
    """Param converter for the explicit layer bundles. Accepts a JSON array string (the HTTP path) or an
    already-decoded list (tests/CLI) of ``{chunk_label, repeat_mask_label, embedding_label?}`` objects.
    Fails loud (→ 400) on malformed structure or a missing required key."""
    if isinstance(value, str):
        value = json.loads(value)  # JSONDecodeError subclasses ValueError → clean 400
    if not isinstance(value, list) or not value:
        raise ValueError("inputs must be a non-empty list of layer-bundle objects")
    out: list[dict[str, str]] = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"inputs[{i}] must be an object")
        chunk = item.get("chunk_label")
        rmask = item.get("repeat_mask_label")
        if not chunk or not rmask:
            raise ValueError(f"inputs[{i}] requires 'chunk_label' and 'repeat_mask_label'")
        entry: dict[str, str] = {"chunk_label": str(chunk), "repeat_mask_label": str(rmask)}
        emb = item.get("embedding_label")
        if emb:
            entry["embedding_label"] = str(emb)
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Track class
# ---------------------------------------------------------------------------

class SelfSimilarityTrack(ParameterizedTrack):
    """Self-similarity as an embedding-agnostic, fail-loud LAYER CONSUMER (Wave-0 P7).

    It no longer chunks, embeds, or masks. The user names explicit layer bundles — one per chunk size,
    each a ``{chunk_label, repeat_mask_label, embedding_label?}`` triple — and this track reads those
    persisted layers, computes the selected similarity methods at every bundle's chunk size, and writes
    the same on-disk dotplot contract as before (``self_similarity.json`` + per-size
    ``self_similarity_cs{N}/{metric}.bin`` + alignments). It does not run if a named layer is absent or
    mis-paired (``LayerResolutionError``), and it never dictates the embedding model — embeddings are
    read from the bound embedding layer's vector cache.

    Repeat masking is consumed FLAG-ONLY from the bound ``repeat_mask`` layer (required); the metric
    builders skip flagged chunks exactly as before. ``exact_repeats`` / ``formulaic_patterns`` are
    sourced from the ``repeats`` layer the mask was derived from.
    """

    # Declarative params (G1/G2). `inputs` is the explicit list of layer bundles; `metrics`/`metric`
    # select the similarity-method family members (resolved in cosine-first canonical order).
    PARAMS = (
        Param("metrics", _csv_list, default=None,
              help="comma-separated similarity methods (cosine, jaccard, word_overlap, edit_distance); "
                   "falls back to `metric` when omitted"),
        Param("metric", str, default="cosine", choices=METRICS,
              help="primary metric: drives data_file / segment_offsets, and the fallback when metrics "
                   "is omitted"),
        Param("inputs", _parse_inputs, required=True,
              help="explicit layer bundles, one per chunk size: a JSON list of "
                   "{chunk_label, repeat_mask_label, embedding_label?} objects"),
    )

    @property
    def name(self) -> str:
        return "self_similarity"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        # Real producer names: orders this after chunking/embedding/repeat_mask AND makes it a
        # signal-CONSUMER, so runner.extract_masked runs it on the full project without remap — the
        # layers it reads already carry original coordinates.
        return ["chunking", "embedding", "repeat_mask"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.self_similarity"]

    @property
    def evidence_level(self) -> str:
        return "E4"

    def validate_params(self) -> dict[str, Any]:
        """Resolve + echo the params, additionally rejecting an unknown metric name synchronously
        (→ HTTP 400) so a typo fails before the job starts rather than as a late async failure."""
        resolved = self.resolved_params()
        resolve_methods(resolved["metrics"] or [resolved["metric"]])
        return resolved

    def _methods(self, resolved: dict[str, Any]) -> list[SimilarityMethod]:
        return resolve_methods(resolved["metrics"] or [resolved["metric"]])

    def extract(self, project: Project) -> Path:
        resolved = self.resolved_params()
        methods = self._methods(resolved)
        needs_embedding = any(m.requires_embedding for m in methods)
        inputs = resolved["inputs"]

        # Bind every named bundle up front, so a missing/mis-paired layer fails BEFORE any matrix work
        # (and never leaves a partial run). Bundle order follows the user's explicit input order;
        # bundles[0] is the PRIMARY, driving the master manifest's headline fields.
        bundles = [
            resolve_explicit_bundle(
                project, inp["chunk_label"], inp["repeat_mask_label"],
                need_embedding=needs_embedding, embedding_label=inp.get("embedding_label"),
            )
            for inp in inputs
        ]

        # Signal-consumer: runs on the full project. The chunk layer's offsets are already original
        # coordinates, so LASTZ char-identity and segment_offsets need no remap.
        ref_text = project.reference_text()

        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)

        available_metrics: list[str] = []
        metric_info: dict[str, dict[str, Any]] = {}
        all_alignments: list[dict[str, Any]] = []
        alns_by_cs: dict[int, list[dict[str, Any]]] = {}

        primary_chunks: list[dict[str, Any]] = []
        primary_chunk_size: int | None = None
        primary_repeats: list[str] = []
        embedding_provenance: dict[str, Any] | None = None

        # Stage-then-commit (C3): write every matrix/alignment/manifest to an invisible ".partial"
        # sibling and promote with an atomic os.replace only after the whole run succeeds, so a mid-run
        # failure leaves no orphan .bin for the filename-scanning readers and no manifest without data.
        staged: list[tuple[Path, Path]] = []
        for leftover in signals_dir.rglob("*.partial"):
            try:
                leftover.unlink()
            except OSError:
                pass

        def _stage_array(final: Path, arr: np.ndarray) -> None:
            final.parent.mkdir(parents=True, exist_ok=True)
            tmp = final.with_name(f".{final.name}.partial")
            arr.astype(np.float32).tofile(tmp)
            staged.append((tmp, final))

        def _stage_text(final: Path, text: str) -> None:
            final.parent.mkdir(parents=True, exist_ok=True)
            tmp = final.with_name(f".{final.name}.partial")
            tmp.write_text(text, encoding="utf-8")
            staged.append((tmp, final))

        # Loop (method, bundle): canonical method order (cosine first → coherent primary fields), and
        # every selected method is computed at every bundle's chunk size, preserving multi-size. The
        # per-size matrices feed the slider; only the PRIMARY bundle drives the headline manifest fields
        # (available_metrics / metric_info / dimensions), which DotplotView self-corrects per size from
        # the matrix byte-length.
        try:
            for method in methods:
                for bundle in bundles:
                    chunks = reconstruct_chunks(bundle)
                    # Each bound input is one operand; today every comparison is the self (A=B) case —
                    # the input schema carries a single within-project operand. A genuine two-operand
                    # cross-text spec is the deferred P10/FR-21 extension; it is gated fail-loud here so
                    # the single-operand assumptions below (the self diagonal, the symmetric LASTZ
                    # alignment) stay explicit rather than silent. This is the one dispatch point P10
                    # generalizes — the four matrix kernels remain self kernels until then.
                    spec = ComparisonSpec.self_(bundle, tuple(m.name for m in methods))
                    if not spec.is_self:
                        raise NotImplementedError(
                            "cross-text comparison (operand_a is not operand_b) is deferred to "
                            "P10/FR-21; self_similarity computes the A=B self case only"
                        )
                    n = len(chunks)
                    cs = bundle.chunk_size
                    if cs is None:
                        raise ValueError(
                            f"chunk layer '{bundle.chunk.label}' has no numeric 'size' capability"
                        )
                    if n > WARN_MATRIX_DIM:
                        logger.warning(
                            "self_similarity %s: %d×%d matrix exceeds %d per side — proceeding as "
                            "requested (this may be slow and memory-heavy).",
                            method.name, n, n, WARN_MATRIX_DIM,
                        )

                    embeddings = load_embeddings(project, bundle) if method.requires_embedding else None
                    matrix = method.build(chunks, embeddings=embeddings)
                    if spec.is_self:
                        # A=B: every chunk is identical to itself, so the leading diagonal is 1.0 by
                        # definition. A genuine cross matrix (P10) has no self-diagonal to set.
                        np.fill_diagonal(matrix, 1.0)

                    cs_dir = signals_dir / f"self_similarity_cs{cs}"
                    cs_dir.mkdir(parents=True, exist_ok=True)
                    _stage_array(cs_dir / f"{method.name}.bin", matrix)
                    # The flat per-metric file is the manifest's headline data_file — the PRIMARY size
                    # only. Stage it once (for bundles[0]); a multi-size run would otherwise stage the
                    # same flat path once per size, leaving the first temp orphaned at commit (the
                    # second os.replace would find its source already renamed away). Other sizes are
                    # served from the cs{N} dirs, and DotplotView self-corrects N from the byte length.
                    if bundle is bundles[0]:
                        _stage_array(signals_dir / f"self_similarity_{method.name}.bin", matrix)

                    # LASTZ scores identity on the full (unmasked) text — build an unmasked copy rather
                    # than clearing the shared chunk list's flags (the matrix above must see the masks).
                    lastz_chunks = [{**c, "masked": False} for c in chunks]
                    metric_alns = _lastz_align(ref_text, lastz_chunks, matrix, cs)
                    mode = bundle.chunk.capability.get("mode")
                    refinement = "approximate" if mode in ("slide", "smart") else "exact"
                    tagged = [{**rec, "metric": method.name, "refinement": refinement}
                              for rec in metric_alns]
                    if tagged:
                        _stage_text(cs_dir / f"alignments_{method.name}.json", json.dumps(tagged, indent=2))
                    all_alignments.extend(tagged)
                    alns_by_cs.setdefault(cs, []).extend(tagged)

                    if bundle is bundles[0]:
                        available_metrics.append(method.name)
                        metric_info[method.name] = {
                            "unit_type": "chunk",
                            "n_units": n,
                            "dimensions": [n, n],
                            "chunk_size": cs,
                            "chunk_mode": mode,
                            "alignment_refinement": refinement,
                            "alignment_count": len(metric_alns),
                        }
                        if not primary_chunks:
                            primary_chunks = chunks
                            primary_chunk_size = cs
                            primary_repeats = sorted(bundle.repeat_phrases)
                            embedding_provenance = _embedding_provenance(bundle)

            # Combined alignments: the flat file across all sizes, plus a per-size combined file grouped
            # by the size each alignment was actually computed at (no per-metric size map to re-derive).
            if all_alignments:
                _stage_text(signals_dir / "self_similarity_alignments.json",
                            json.dumps(all_alignments, indent=2))
                for cs, recs in alns_by_cs.items():
                    _stage_text(signals_dir / f"self_similarity_cs{cs}" / "alignments.json",
                                json.dumps(recs, indent=2))

            # All chunk sizes from this run's bundles, unioned with sizes already on disk from prior runs.
            bundle_sizes = {b.chunk_size for b in bundles if b.chunk_size is not None}
            available_chunk_sizes = sorted(set(_discover_chunk_sizes(signals_dir)) | bundle_sizes)

            paras = project.paragraphs()
            n_primary = len(primary_chunks)
            primary_cap = bundles[0].chunk.capability if bundles else {}
            primary_metric = (
                "cosine" if "cosine" in available_metrics
                else (available_metrics[0] if available_metrics else "cosine")
            )
            master = {
                "type": "matrix",
                "name": "self_similarity",
                "source": f"chunk_{primary_chunk_size}/0.3",
                "reference_sha256": project.metadata.reference_sha256,
                "dimensions": [n_primary, n_primary],
                "dtype": "float32",
                "byte_order": "little-endian",
                "data_file": f"self_similarity_{primary_metric}.bin",
                "segment_offsets": [[c["start"], c["end"]] for c in primary_chunks],
                # Coordinate-frame axes (P9/FR-20). Self-similarity is the A=B case: one operand used as
                # both row and col, so a single axis. ``axes[0]`` mirrors the legacy top-level
                # ``reference_sha256`` / ``segment_offsets`` / ``dimensions`` — those are kept for
                # back-compat so DotplotView and /analysis/status need no change, and ``axes`` is purely
                # additive. A cross-text matrix (P10/FR-21) carries a second axis (the column operand,
                # coordinate-mapped onto this root backbone via an OffsetMap).
                "mode": "auto",
                "symmetric": True,
                "storage": "dense",
                "axes": [
                    {
                        "role": "both",
                        "project_id": project.metadata.id,
                        "ref_sha256": project.metadata.reference_sha256,
                        "segment_offsets": [[c["start"], c["end"]] for c in primary_chunks],
                        "label": bundles[0].chunk.label if bundles else None,
                    }
                ],
                "metadata": {
                    "similarity_metric": primary_metric,
                    "paragraph_count": len(paras),
                    "chunk_count": n_primary,
                    "chunk_size": primary_chunk_size,
                    "chunk_mode": primary_cap.get("mode"),
                    "smart_unit": primary_cap.get("unit") if primary_cap.get("mode") == "smart" else None,
                    "embedding": embedding_provenance,
                    "available_metrics": available_metrics,
                    "metric_info": metric_info,
                    "alignment_count": len(all_alignments),
                    "has_alignments": len(all_alignments) > 0,
                    "available_chunk_sizes": available_chunk_sizes,
                    "exact_repeats": primary_repeats,
                    "formulaic_patterns": _derive_formulaic_patterns(
                        primary_chunks, set(primary_repeats)
                    ) if primary_repeats else [],
                    # The LASTZ calibration cutoffs that produced this matrix (the masking cutoffs now
                    # live with the repeat/repeat_mask layers — see layer_inputs), recorded so the
                    # stored artifact alone reconstructs the run (P3) and the cutoffs are auditable (P1).
                    "locked_constants": LOCKED_CONSTANTS,
                    # P7 provenance: the exact layer bundles consumed, so the artifact reconstructs
                    # which chunking / repeat_mask / embedding layers produced this matrix.
                    "layer_inputs": [
                        {
                            "chunk_label": b.chunk.label,
                            "chunk_size": b.chunk_size,
                            "chunk_mode": b.chunk.capability.get("mode"),
                            "repeat_mask_label": b.repeat_mask.label,
                            "repeat_layer_id": b.repeat_mask.capability.get("repeat_layer_id"),
                            "coverage_threshold": b.repeat_mask.capability.get("coverage_threshold"),
                            "embedding_label": (b.embedding.label if b.embedding else None),
                        }
                        for b in bundles
                    ],
                },
            }
            manifest_path = signals_dir / "self_similarity.json"
            _stage_text(manifest_path, json.dumps(master, indent=2, ensure_ascii=False))

            # Commit: promote every staged file with an atomic rename. Reaching here means the whole run
            # succeeded; the manifest (staged last) is therefore promoted last.
            for tmp, final in staged:
                os.replace(tmp, final)
        except BaseException:
            # Any failure between the first stage and the final rename must leave nothing behind: drop
            # every staged temp so the filename-scanning readers never see an orphan .bin and no
            # manifest ever lands without its data. Re-raise the original failure unchanged.
            for tmp, _ in staged:
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise

        return manifest_path

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "self_similarity",
            "bodyType": "signal",
            "colorScheme": {
                "primary": "#3B82F6",
                "secondary": "#1E40AF",
                "scale": ["#EFF6FF", "#3B82F6", "#1E3A8A"],
            },
            "dedicatedView": "dotplot",
        }
