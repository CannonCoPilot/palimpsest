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
4. Threshold calibrated empirically via random pseudo-chunk alignment
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
DEFAULT_CHUNK_SIZE = 17
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
    Returns list of {index, start, end, text, words}."""
    words = text.split()
    chunks: list[dict[str, Any]] = []
    word_idx = 0
    char_pos = 0

    while word_idx < len(words):
        chunk_words = words[word_idx:word_idx + chunk_size]
        if len(chunk_words) < MIN_CHUNK_SIZE:
            break
        chunk_text = " ".join(chunk_words)
        start = text.find(chunk_words[0], char_pos)
        end_word = chunk_words[-1]
        end = text.find(end_word, start) + len(end_word)
        chunks.append({
            "index": len(chunks),
            "start": start,
            "end": end,
            "text": chunk_text,
            "words": chunk_words,
        })
        char_pos = end
        word_idx += chunk_size

    return chunks


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
    """Content-word Jaccard similarity between chunks."""
    n = len(chunks)
    sets = [_content_set(c["words"]) for c in chunks]
    matrix = np.zeros((n, n), dtype=np.float32)
    for i in range(n):
        if not sets[i]:
            continue
        matrix[i, i] = 1.0
        for j in range(i + 1, n):
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
    """Token-level Levenshtein distance."""
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[lb]


def _edit_distance_matrix(chunks: list[dict[str, Any]]) -> np.ndarray:
    """Normalized content-word edit distance similarity between chunks."""
    n = len(chunks)
    content = [_content_tokens(c["words"]) for c in chunks]
    matrix = np.zeros((n, n), dtype=np.float32)
    for i in range(n):
        la = len(content[i])
        if la == 0:
            continue
        matrix[i, i] = 1.0
        for j in range(i + 1, n):
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


def _calibrate_threshold(chunks: list[dict[str, Any]], n_samples: int = 200) -> float:
    """Empirically calibrate identity threshold from random pseudo-chunk pairs.
    Returns the 95th percentile of random-pair character-level identity."""
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
        # Build two pseudo-chunks from random word samples
        idx_a = rng.choice(len(all_words), size=min(chunk_size, len(all_words)), replace=False)
        idx_b = rng.choice(len(all_words), size=min(chunk_size, len(all_words)), replace=False)
        pseudo_a = " ".join(all_words[i] for i in sorted(idx_a))
        pseudo_b = " ".join(all_words[i] for i in sorted(idx_b))
        # Character-level identity
        identity = _char_identity(pseudo_a, pseudo_b)
        scores.append(identity)

    scores.sort()
    # 95th percentile as threshold
    p95 = scores[int(len(scores) * 0.95)]
    logger.info("LASTZ threshold calibrated: 95th pct = %.3f (from %d random pairs)", p95, n_samples)
    return max(p95, 0.1)


def _char_identity(a: str, b: str) -> float:
    """Character-level identity score via LCS ratio."""
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0
    # Use a banded approach for long strings
    if la > 500 or lb > 500:
        # Approximate with token-level
        ta = a.lower().split()
        tb = b.lower().split()
        shared = len(set(ta) & set(tb))
        return shared / max(len(set(ta) | set(tb)), 1)

    # Standard LCS length via DP
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


def _extend_alignment(
    text: str,
    chunks: list[dict[str, Any]],
    seed_i: int,
    seed_j: int,
    threshold: float,
) -> dict[str, Any] | None:
    """Extend from a seed (chunk_i, chunk_j) along the diagonal,
    performing character-level matching. Extends outward in both directions
    until identity drops below threshold."""
    n = len(chunks)
    best_start_i, best_start_j = seed_i, seed_j
    best_end_i, best_end_j = seed_i, seed_j

    # Extend forward (increasing indices)
    ci, cj = seed_i, seed_j
    while ci < n and cj < n and ci != cj:
        text_a = chunks[ci]["text"]
        text_b = chunks[cj]["text"]
        identity = _char_identity(text_a, text_b)
        if identity < threshold:
            break
        best_end_i = ci
        best_end_j = cj
        ci += 1
        cj += 1

    # Extend backward (decreasing indices)
    ci, cj = seed_i - 1, seed_j - 1
    while ci >= 0 and cj >= 0 and ci != cj:
        text_a = chunks[ci]["text"]
        text_b = chunks[cj]["text"]
        identity = _char_identity(text_a, text_b)
        if identity < threshold:
            break
        best_start_i = ci
        best_start_j = cj
        ci -= 1
        cj -= 1

    length = best_end_i - best_start_i + 1
    if length < 2:
        return None

    # Compute overall identity for the aligned region
    region_a = text[chunks[best_start_i]["start"]:chunks[best_end_i]["end"]]
    region_b = text[chunks[best_start_j]["start"]:chunks[best_end_j]["end"]]
    overall_identity = _char_identity(region_a, region_b)

    return {
        "chunk_start_a": best_start_i,
        "chunk_end_a": best_end_i,
        "chunk_start_b": best_start_j,
        "chunk_end_b": best_end_j,
        "char_start_a": chunks[best_start_i]["start"],
        "char_end_a": chunks[best_end_i]["end"],
        "char_start_b": chunks[best_start_j]["start"],
        "char_end_b": chunks[best_end_j]["end"],
        "length_chunks": length,
        "identity": round(overall_identity, 4),
        "seed_score": float(round(float(_char_identity(
            chunks[seed_i]["text"], chunks[seed_j]["text"]
        )), 4)),
    }


def _lastz_align(
    text: str,
    chunks: list[dict[str, Any]],
    coarse_matrix: np.ndarray,
) -> list[dict[str, Any]]:
    """LASTZ-style seed-and-extend alignment on self-similarity matrix."""
    k = 2 * (os.cpu_count() or 4)
    optima = _find_local_optima(coarse_matrix, k)

    if not optima:
        return []

    threshold = _calibrate_threshold(chunks)
    logger.info("LASTZ: %d optima found, threshold=%.3f", len(optima), threshold)

    alignments: list[dict[str, Any]] = []
    for seed_i, seed_j, _seed_score in optima:
        result = _extend_alignment(text, chunks, seed_i, seed_j, threshold)
        if result is not None:
            alignments.append(result)

    # Sort by identity descending
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
        self._chunk_size = DEFAULT_CHUNK_SIZE

    def set_params(self, params: dict[str, Any]) -> None:
        if "metric" in params and params["metric"] in METRICS:
            self._metric = params["metric"]
        if "chunk_size" in params:
            self._chunk_size = max(MIN_CHUNK_SIZE, min(MAX_CHUNK_SIZE, int(params["chunk_size"])))

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
        ref_text = (project.path / "reference.txt").read_text(encoding="utf-8")
        chunks = _chunk_text(ref_text, self._chunk_size)
        n = len(chunks)
        logger.info("Self-similarity: %d chunks of %d words", n, self._chunk_size)

        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)
        available_metrics: list[str] = []
        metric_info: dict[str, dict[str, Any]] = {}
        alignments: list[dict[str, Any]] = []

        # Embed chunks for cosine/jaccard
        embeddings = _embed_chunks(project, chunks, self._chunk_size)

        for metric in METRICS:
            logger.info("Computing self-similarity: %s (%d chunks)", metric, n)

            if metric in ("cosine", "jaccard") and embeddings is None:
                logger.warning("Skipping %s — no embeddings available", metric)
                continue

            if metric == "cosine":
                matrix = _cosine_matrix(embeddings)
            elif metric == "jaccard":
                matrix = _jaccard_matrix(embeddings)
            elif metric == "word_overlap":
                matrix = _word_overlap_matrix(chunks)
            elif metric == "edit_distance":
                matrix = _edit_distance_matrix(chunks)
                # Run LASTZ alignment on the edit distance matrix
                alignments = _lastz_align(ref_text, chunks, matrix)
                logger.info("LASTZ found %d significant alignments", len(alignments))
            else:
                continue

            np.fill_diagonal(matrix, 1.0)
            matrix.astype(np.float32).tofile(signals_dir / f"self_similarity_{metric}.bin")
            available_metrics.append(metric)
            metric_info[metric] = {
                "unit_type": "chunk",
                "n_units": n,
                "dimensions": [n, n],
                "chunk_size": self._chunk_size,
            }

        # Write alignment records
        if alignments:
            (signals_dir / "self_similarity_alignments.json").write_text(
                json.dumps(alignments, indent=2), encoding="utf-8",
            )

        # Master manifest
        paras = project.paragraphs()
        master = {
            "type": "matrix",
            "name": "self_similarity",
            "source": f"chunk_{self._chunk_size}/0.2",
            "reference_sha256": project.metadata.reference_sha256,
            "dimensions": [n, n],
            "dtype": "float32",
            "byte_order": "little-endian",
            "data_file": "self_similarity_cosine.bin" if "cosine" in available_metrics else f"self_similarity_{available_metrics[0]}.bin",
            "segment_offsets": [[c["start"], c["end"]] for c in chunks],
            "metadata": {
                "similarity_metric": "cosine" if "cosine" in available_metrics else available_metrics[0],
                "paragraph_count": len(paras),
                "chunk_count": n,
                "chunk_size": self._chunk_size,
                "available_metrics": available_metrics,
                "metric_info": metric_info,
                "alignment_count": len(alignments),
                "has_alignments": len(alignments) > 0,
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
        return {
            "self_similarity.metric": "cosine",
            "self_similarity.chunk_size": self._chunk_size,
            "self_similarity.source": "chunk_embeddings",
        }
