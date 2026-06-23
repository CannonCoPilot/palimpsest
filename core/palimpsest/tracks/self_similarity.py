"""Self-similarity matrix track — chunk-based multi-metric with LASTZ-style alignment.

Text is divided into non-overlapping word chunks (default 17 words).
Four metrics are computed on this chunked representation:
- cosine: chunk-level embeddings, cosine similarity
- jaccard: binarized embedding Jaccard
- word_overlap: content-word-set Jaccard (stopwords removed)
- edit_distance: coarse token-level Levenshtein + LASTZ seed-and-extend

LASTZ alignment:
1. Coarse edit distance on non-overlapping chunks → NxN matrix
2. Find top K off-diagonal local optima (K = 2 × CPU cores)
3. At each optimum, extend with character-level matching along the diagonal
   in two directions: parallel (1,1) and antiparallel (1,-1).
   Parallel finds repeated passages; antiparallel finds chiasmus (ABBA) structures.
4. Refine boundaries with 1-word-stride sliding windows for sub-chunk precision
5. Threshold calibrated empirically via random pseudo-chunk alignment
6. Mirror deduplication (A↔B counted once)

Repeat masking:
- Frequent exact n-gram phrases (>= 3 words, >= 3 occurrences) are detected.
- Chunks where >50% of content words are covered by such phrases are masked.
- Masked chunks are skipped in matrix computation, then unmasked for final scoring.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import numpy as np

from palimpsest.project import Project
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

logger = logging.getLogger(__name__)

METRICS = ("cosine", "jaccard", "word_overlap", "edit_distance")
DEFAULT_CHUNK_SIZE = 7
MIN_CHUNK_SIZE = 5
MAX_CHUNK_SIZE = 25

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "nor", "not", "no", "so", "as",
    "at", "by", "for", "from", "in", "into", "of", "on", "to", "up", "with",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "shall", "would", "should", "may", "might", "can", "could", "must",
    "he", "she", "it", "i", "me", "my", "we", "us", "our", "you", "your",
    "they", "them", "their", "him", "his", "her", "its",
    "this", "that", "these", "those", "which", "who", "whom", "whose",
    "what", "when", "where", "how", "why", "if", "then", "than", "else",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "also", "just", "very", "too",
    "ye", "thee", "thou", "thy", "thine", "unto", "upon", "hath", "doth",
    "thereof", "therein", "hereby", "thereby", "wherefore",
    "saith", "cometh", "goeth",
})


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int) -> list[dict[str, Any]]:
    """Split text into non-overlapping word chunks of `chunk_size` words.
    Returns list of {index, start, end, text, words}.
    Uses pre-built word positions for correct character offsets (avoids
    first-occurrence bug with repeated words like articles)."""
    all_words, positions = _build_word_positions(text)
    chunks: list[dict[str, Any]] = []
    word_idx = 0

    while word_idx < len(all_words):
        end_idx = min(word_idx + chunk_size, len(all_words))
        chunk_words = all_words[word_idx:end_idx]
        if len(chunk_words) < MIN_CHUNK_SIZE:
            break
        start = positions[word_idx][0]
        end = positions[end_idx - 1][1]
        chunks.append({
            "index": len(chunks),
            "start": start,
            "end": end,
            "text": text[start:end],
            "words": chunk_words,
        })
        word_idx += chunk_size

    return chunks


def _discover_chunk_sizes(signals_dir: Path) -> list[int]:
    """Find all computed chunk sizes by scanning for self_similarity_csN/ directories."""
    sizes: list[int] = []
    for entry in signals_dir.iterdir():
        if entry.is_dir() and entry.name.startswith("self_similarity_cs"):
            try:
                cs = int(entry.name.replace("self_similarity_cs", ""))
                if (entry / "cosine.bin").exists() or (entry / "word_overlap.bin").exists():
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


def _zero_layout_masked_chunks(matrix: np.ndarray, chunks: list[dict[str, Any]]) -> None:
    """Zero every row/col (incl. diagonal) of layout-masked chunks, in-place.

    Layout-masked chunks cover non-work text (front matter, contents, endnotes …)
    that must contribute no self-similarity structure. Applied uniformly to every
    metric's matrix, so cosine/jaccard honor layout masks too — the masked-chunk
    skip inside the word_overlap/edit_distance builders only covers those two
    metrics, and embedding-based metrics never see the flag otherwise."""
    masked_idx = [i for i, c in enumerate(chunks) if c.get("layout_masked")]
    if not masked_idx:
        return
    idx = np.array(masked_idx, dtype=np.intp)
    matrix[idx, :] = 0.0
    matrix[:, idx] = 0.0


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


def _calibrate_threshold(chunks: list[dict[str, Any]], n_samples: int = 1000) -> float:
    """Empirically calibrate identity threshold from shuffled pseudo-chunk pairs.
    Shuffles the full word list and takes contiguous slices to build a true
    null distribution (no text-order preservation). Returns the 95th percentile."""
    rng = np.random.default_rng(42)
    n = len(chunks)
    if n < 10:
        return 0.3

    all_words: list[str] = []
    for c in chunks:
        all_words.extend(c["words"])

    if len(all_words) < 20:
        return 0.3

    chunk_size = len(chunks[0]["words"]) if chunks else 17
    scores: list[float] = []

    for _ in range(n_samples):
        shuffled = rng.permutation(all_words)
        pseudo_a = " ".join(shuffled[:chunk_size])
        pseudo_b = " ".join(shuffled[chunk_size:2 * chunk_size])
        identity = _char_identity_consistent(pseudo_a, pseudo_b)
        scores.append(identity)

    scores.sort()
    p95 = scores[int(len(scores) * 0.95)]
    logger.info("LASTZ threshold calibrated: 95th pct = %.3f (from %d shuffled pairs)", p95, n_samples)
    return max(p95, 0.1)


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


def _char_identity_consistent(a: str, b: str) -> float:
    """Same algorithm as _char_identity — consistent scoring for calibration."""
    return _char_identity(a, b)


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


def _build_word_positions(text: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Build word list and (start, end) char positions for each word."""
    words: list[str] = []
    positions: list[tuple[int, int]] = []
    i = 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        start = i
        while i < len(text) and not text[i].isspace():
            i += 1
        words.append(text[start:i])
        positions.append((start, i))
    return words, positions


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

    def _is_masked(ci: int, cj: int) -> bool:
        """True when either chunk is layout-masked — alignments must not span
        non-work text (front matter, endnotes …), so extension halts here."""
        return bool(chunks[ci].get("layout_masked") or chunks[cj].get("layout_masked"))

    # Extend in the forward direction
    ci, cj = seed_i, seed_j
    while _in_bounds(ci, cj) and not _is_self(ci, cj) and not _is_masked(ci, cj):
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
    while _in_bounds(ci, cj) and not _is_self(ci, cj) and not _is_masked(ci, cj):
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
    words, word_positions = _build_word_positions(text)
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

def _find_exact_repeats(
    text: str,
    chunks: list[dict[str, Any]],
    min_words: int = 3,
    min_occurrences: int = 3,
) -> set[str]:
    """Build a phrase-occurrence index from all chunks and return the set of
    contiguous word sequences (of length min_words to chunk_size) that appear
    at least min_occurrences times across the full text.

    The index is built once over the concatenated word list (not per-chunk),
    so phrase counts reflect the whole document.
    """
    # Collect all words from the full text in document order
    all_words: list[str] = []
    for chunk in chunks:
        all_words.extend(chunk["words"])

    if len(all_words) < min_words:
        return set()

    chunk_size = len(chunks[0]["words"]) if chunks else DEFAULT_CHUNK_SIZE
    max_ngram = min(chunk_size, len(all_words) // 2)

    # Normalise words for comparison (lowercase, strip punctuation)
    normalised = [re.sub(r"[^a-z']", "", w.lower()) for w in all_words]

    # Count every n-gram of each length
    phrase_counts: dict[str, int] = {}
    for n in range(min_words, max_ngram + 1):
        for start in range(len(normalised) - n + 1):
            gram = normalised[start:start + n]
            # Skip n-grams that are entirely stopwords
            if all(w in STOPWORDS or not w for w in gram):
                continue
            key = " ".join(gram)
            if not key.strip():
                continue
            phrase_counts[key] = phrase_counts.get(key, 0) + 1

    repeats = {phrase for phrase, count in phrase_counts.items()
               if count >= min_occurrences}
    logger.info(
        "Repeat masking: found %d phrases with >= %d occurrences",
        len(repeats), min_occurrences,
    )
    return repeats


def _mask_repeats(
    chunks: list[dict[str, Any]],
    repeats: set[str],
) -> list[dict[str, Any]]:
    """Mark chunks where >50% of content words are covered by a repeated phrase.

    A content word is 'covered' if it belongs to any repeated n-gram that
    appears somewhere within the chunk's content-token sequence.  The function
    adds a ``masked`` key (True/False) to each chunk dict in-place and also
    returns the list for convenience.
    """
    if not repeats:
        for chunk in chunks:
            chunk["masked"] = False
        return chunks

    # Pre-split repeated phrases into token lists for fast membership testing
    repeat_token_lists: list[list[str]] = [p.split() for p in repeats]

    for chunk in chunks:
        tokens = [re.sub(r"[^a-z']", "", w.lower()) for w in chunk["words"]]
        content_tokens = [t for t in tokens if t and t not in STOPWORDS and len(t) > 1]
        if not content_tokens:
            chunk["masked"] = False
            continue

        # Mark which token positions are covered by any repeated phrase
        covered = [False] * len(tokens)
        for phrase_tokens in repeat_token_lists:
            plen = len(phrase_tokens)
            for start in range(len(tokens) - plen + 1):
                if tokens[start:start + plen] == phrase_tokens:
                    for k in range(start, start + plen):
                        covered[k] = True

        # Count covered content tokens
        covered_content = sum(
            1 for t, cov in zip(tokens, covered)
            if cov and t and t not in STOPWORDS and len(t) > 1
        )
        chunk["masked"] = covered_content / len(content_tokens) > 0.5

    masked_count = sum(1 for c in chunks if c.get("masked"))
    if masked_count:
        logger.info("Repeat masking: %d / %d chunks masked", masked_count, len(chunks))
    return chunks


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
# Chunk-level embedding
# ---------------------------------------------------------------------------

def _embed_chunks(
    project: Project,
    chunks: list[dict[str, Any]],
    chunk_size: int,
) -> np.ndarray | None:
    """Embed chunks via MLX or Ollama. Returns embedding matrix or None."""
    cache_dir = project.path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    chunk_db = cache_dir / f"embeddings_chunk{chunk_size}.db"

    # Check if already cached
    if chunk_db.exists():
        store = SqliteVecStore.open_existing(chunk_db)
        try:
            vectors = store.get_all_vectors()
            if len(vectors) == len(chunks):
                return np.array(vectors, dtype=np.float32)
        finally:
            store.close()

    # Probe for embedding dimension
    import httpx

    dim: int | None = None
    try:
        resp = httpx.post("http://localhost:8000/embed", json={"text": "probe"}, timeout=3.0)
        if resp.status_code == 200 and "embedding" in resp.json():
            dim = len(resp.json()["embedding"])
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    if dim is None:
        try:
            from palimpsest.services.manager import OllamaManager
            mgr = OllamaManager()
            client = mgr.embedding_client()
            probe = client.embed_one("probe")
            if probe is not None:
                dim = len(probe)
        except Exception:
            pass

    if dim is None:
        logger.warning("No embedding service available for chunk embedding")
        return None

    # Embed chunks
    # Create a temporary project-like structure for the embedding pipeline
    # We'll embed directly using the low-level batch API
    store = SqliteVecStore(chunk_db, dim=dim)
    slug = project.metadata.id

    try:
        texts = [c["text"] for c in chunks]
        batch_size = 32

        try:
            mlx_client = httpx.Client(base_url="http://localhost:8000")
            resp = mlx_client.post("/embed", json={"text": "probe"}, timeout=3.0)
            if resp.status_code == 200:
                logger.info("Embedding %d chunks via MLX (dim=%d)", len(chunks), dim)
                for batch_start in range(0, len(texts), batch_size):
                    batch_texts = texts[batch_start:batch_start + batch_size]
                    resp = mlx_client.post("/embed_batch", json={"texts": batch_texts}, timeout=30.0)
                    resp.raise_for_status()
                    vectors = resp.json()["embeddings"]
                    ids = [f"{slug}:chunk{chunk_size}:{batch_start + k}" for k in range(len(batch_texts))]
                    meta = [{"chunk_index": batch_start + k} for k in range(len(batch_texts))]
                    store.add(ids, vectors, meta)
            mlx_client.close()
        except Exception:
            # Fall back to Ollama
            logger.info("Embedding %d chunks via Ollama (dim=%d)", len(chunks), dim)
            ollama_client = httpx.Client(base_url="http://localhost:11434")
            for batch_start in range(0, len(texts), batch_size):
                batch_texts = texts[batch_start:batch_start + batch_size]
                resp = ollama_client.post("/api/embed", json={"model": "qwen3-embedding:4b", "input": batch_texts}, timeout=30.0)
                resp.raise_for_status()
                vectors = resp.json()["embeddings"]
                ids = [f"{slug}:chunk{chunk_size}:{batch_start + k}" for k in range(len(batch_texts))]
                meta = [{"chunk_index": batch_start + k} for k in range(len(batch_texts))]
                store.add(ids, vectors, meta)
            ollama_client.close()

        all_vectors = store.get_all_vectors()
        return np.array(all_vectors, dtype=np.float32) if all_vectors else None
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Track class
# ---------------------------------------------------------------------------

class SelfSimilarityTrack:
    def __init__(self) -> None:
        self._metric = "cosine"
        # Metrics to compute this run; defaults to all. The UI's per-metric
        # checkboxes narrow this so large texts can skip expensive metrics
        # (edit_distance is O(n²)).
        self._selected_metrics: list[str] = list(METRICS)
        self._chunk_size = DEFAULT_CHUNK_SIZE
        # Per-metric chunk sizes (None means fall back to shared _chunk_size)
        self._chunk_size_cosine: int | None = None
        self._chunk_size_jaccard: int | None = None
        self._chunk_size_word_overlap: int | None = None
        self._chunk_size_edit_distance: int | None = None

    def _clamp_chunk_size(self, value: int) -> int:
        return max(MIN_CHUNK_SIZE, min(MAX_CHUNK_SIZE, value))

    def set_params(self, params: dict[str, Any]) -> None:
        if "metric" in params and params["metric"] in METRICS:
            self._metric = params["metric"]
        if "metrics" in params:
            selected = [m for m in params["metrics"] if m in METRICS]
            if selected:
                self._selected_metrics = selected
        if "chunk_size" in params:
            self._chunk_size = self._clamp_chunk_size(int(params["chunk_size"]))
        # Per-metric chunk size overrides
        for metric_key in ("cosine", "jaccard", "word_overlap", "edit_distance"):
            param_key = f"chunk_size_{metric_key}"
            if param_key in params:
                setattr(
                    self,
                    f"_chunk_size_{metric_key}",
                    self._clamp_chunk_size(int(params[param_key])),
                )

    def _chunk_size_for(self, metric: str) -> int:
        """Return the effective chunk size for a metric, falling back to the shared size."""
        per_metric: int | None = getattr(self, f"_chunk_size_{metric}", None)
        return per_metric if per_metric is not None else self._chunk_size

    @property
    def name(self) -> str:
        return "self_similarity"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        return ["_embeddings"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.self_similarity"]

    @property
    def evidence_level(self) -> str:
        return "E4"

    def extract(self, project: Project) -> Path:
        from palimpsest.layout import range_is_masked

        ref_text = (project.path / "reference.txt").read_text(encoding="utf-8")

        # Step-4 layout masks (front matter, contents, endnotes …). Empty when no
        # layout is configured, making the whole masking path a no-op.
        layout_masked_intervals = project.masked_intervals()

        MAX_MATRIX_DIM = 4000
        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)

        available_metrics: list[str] = []
        metric_info: dict[str, dict[str, Any]] = {}
        # All alignments combined across metrics; each record carries a "metric" field.
        all_alignments: list[dict[str, Any]] = []

        # Caches keyed by chunk_size to avoid re-chunking when multiple metrics
        # share the same window size.
        _chunks_cache: dict[int, list[dict[str, Any]]] = {}
        _embeddings_cache: dict[int, np.ndarray | None] = {}

        def _get_chunks(cs: int) -> list[dict[str, Any]]:
            if cs not in _chunks_cache:
                raw = _chunk_text(ref_text, cs)
                repeats = _find_exact_repeats(ref_text, raw)
                _mask_repeats(raw, repeats)
                for chunk in raw:
                    chunk["layout_masked"] = bool(layout_masked_intervals) and range_is_masked(
                        layout_masked_intervals, chunk["start"], chunk["end"]
                    )
                _chunks_cache[cs] = raw
            return _chunks_cache[cs]

        def _get_embeddings(cs: int) -> np.ndarray | None:
            if cs not in _embeddings_cache:
                _embeddings_cache[cs] = _embed_chunks(project, _get_chunks(cs), cs)
            return _embeddings_cache[cs]

        # Track which chunk-size is used for cosine so the legacy manifest
        # fields (dimensions, segment_offsets) stay coherent.
        primary_chunk_size = self._chunk_size_for("cosine")
        primary_chunks: list[dict[str, Any]] = []

        # Collect the set of repeated phrases from the primary chunk size for
        # the manifest (used for display / debugging).
        exact_repeats_list: list[str] = []

        # Iterate in canonical METRICS order (keeps cosine first so the primary
        # manifest fields stay coherent) but only over the selected subset.
        selected_metrics = [m for m in METRICS if m in self._selected_metrics]
        for metric in selected_metrics:
            cs = self._chunk_size_for(metric)
            chunks = _get_chunks(cs)
            n = len(chunks)
            logger.info(
                "Computing self-similarity: %s (%d chunks, chunk_size=%d)",
                metric, n, cs,
            )

            if n > MAX_MATRIX_DIM:
                logger.warning(
                    "Skipping %s — matrix too large: %d×%d. "
                    "Increase chunk_size above %d.",
                    metric, n, n, cs,
                )
                continue

            if metric in ("cosine", "jaccard"):
                embeddings = _get_embeddings(cs)
                if embeddings is None:
                    logger.warning("Skipping %s — no embeddings available", metric)
                    continue
                if metric == "cosine":
                    matrix = _cosine_matrix(embeddings)
                else:
                    matrix = _jaccard_matrix(embeddings)
            elif metric == "word_overlap":
                matrix = _word_overlap_matrix(chunks)
            elif metric == "edit_distance":
                matrix = _edit_distance_matrix(chunks)
            else:
                continue

            np.fill_diagonal(matrix, 1.0)

            # Exclude layout-masked (non-work) chunks from every metric's matrix.
            _zero_layout_masked_chunks(matrix, chunks)

            # Per-chunk-size subdirectory
            cs_dir = signals_dir / f"self_similarity_cs{cs}"
            cs_dir.mkdir(parents=True, exist_ok=True)

            # Write binary matrix (per-cs dir and legacy flat location)
            matrix.astype(np.float32).tofile(cs_dir / f"{metric}.bin")
            matrix.astype(np.float32).tofile(signals_dir / f"self_similarity_{metric}.bin")

            # LASTZ scores final identity on the full (unmasked) text. Build an
            # unmasked *copy* rather than clearing masks on the shared cache —
            # `chunks` is the per-chunk-size cached list that later metrics reuse
            # for their masked matrix computation, so mutating it here silently
            # disables repeat masking for every metric after this one.
            lastz_chunks = [{**chunk, "masked": False} for chunk in chunks]

            # Run LASTZ for this metric and tag records with the metric name
            metric_alns = _lastz_align(ref_text, lastz_chunks, matrix, cs)
            logger.info("LASTZ[%s] found %d significant alignments", metric, len(metric_alns))
            tagged_alns = [{**rec, "metric": metric} for rec in metric_alns]

            if tagged_alns:
                (cs_dir / f"alignments_{metric}.json").write_text(
                    json.dumps(tagged_alns, indent=2), encoding="utf-8"
                )

            all_alignments.extend(tagged_alns)

            available_metrics.append(metric)
            metric_info[metric] = {
                "unit_type": "chunk",
                "n_units": n,
                "dimensions": [n, n],
                "chunk_size": cs,
                "alignment_count": len(metric_alns),
            }

            # Populate primary-metric data for manifest segment_offsets
            if metric == "cosine" or not primary_chunks:
                primary_chunk_size = cs
                primary_chunks = chunks
                # Grab exact-repeat phrases from this chunk size for the manifest
                cs_repeats = _find_exact_repeats(ref_text, chunks)
                exact_repeats_list = sorted(cs_repeats)

        # Write the combined alignments.json into each affected cs_dir
        # and the legacy flat file.
        if all_alignments:
            combined_json = json.dumps(all_alignments, indent=2)
            (signals_dir / "self_similarity_alignments.json").write_text(
                combined_json, encoding="utf-8"
            )
            written_cs: set[int] = {self._chunk_size_for(m) for m in available_metrics}
            for cs in written_cs:
                cs_dir = signals_dir / f"self_similarity_cs{cs}"
                cs_dir.mkdir(parents=True, exist_ok=True)
                cs_alns = [r for r in all_alignments
                           if self._chunk_size_for(r["metric"]) == cs]
                (cs_dir / "alignments.json").write_text(
                    json.dumps(cs_alns, indent=2), encoding="utf-8"
                )

        # Discover all computed chunk sizes (including previously computed ones)
        available_chunk_sizes = _discover_chunk_sizes(signals_dir)
        for m in available_metrics:
            cs = self._chunk_size_for(m)
            if cs not in available_chunk_sizes:
                available_chunk_sizes.append(cs)
        available_chunk_sizes.sort()

        paras = project.paragraphs()
        n_primary = len(primary_chunks)
        # Primary metric drives both data_file and similarity_metric; derive once
        # so the two can't drift. data_file stays a flat-path filename because the
        # frontend loader (SignalAdapter + DotplotView) resolves it relative to
        # the signals dir and overrides it per-metric with the same flat scheme.
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
            "metadata": {
                "similarity_metric": primary_metric,
                "paragraph_count": len(paras),
                "chunk_count": n_primary,
                "chunk_size": primary_chunk_size,
                "available_metrics": available_metrics,
                "metric_info": metric_info,
                "layout_masked_chunks": sum(
                    1 for c in primary_chunks if c.get("layout_masked")
                ),
                "alignment_count": len(all_alignments),
                "has_alignments": len(all_alignments) > 0,
                "available_chunk_sizes": available_chunk_sizes,
                "exact_repeats": exact_repeats_list,
                "formulaic_patterns": _derive_formulaic_patterns(
                    primary_chunks, set(exact_repeats_list)
                ) if exact_repeats_list else [],
            },
        }
        manifest_path = signals_dir / "self_similarity.json"
        manifest_path.write_text(
            json.dumps(master, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

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

    def parameters(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "self_similarity.metric": "cosine",
            "self_similarity.chunk_size": self._chunk_size,
            "self_similarity.source": "chunk_embeddings",
        }
        for metric_key in ("cosine", "jaccard", "word_overlap", "edit_distance"):
            per_metric: int | None = getattr(self, f"_chunk_size_{metric_key}", None)
            if per_metric is not None:
                params[f"self_similarity.chunk_size_{metric_key}"] = per_metric
        return params
