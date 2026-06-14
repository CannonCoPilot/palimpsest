"""Self-similarity matrix track — multi-metric pairwise similarity.

Computes four metrics at different granularities:
- cosine, jaccard: paragraph-level (embedding-based, semantically meaningful at this scale)
- word_overlap: sentence-level with stopword removal (token-set Jaccard on content words)
- edit_distance: sentence-level (normalized token-level Levenshtein on content words)

Each metric is stored as a separate binary file for instant switching in the UI.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import numpy as np

from palimpsest.project import Project
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

logger = logging.getLogger(__name__)

METRICS = ("cosine", "jaccard", "word_overlap", "edit_distance")

# Common English stopwords — function words that inflate Jaccard without semantic content
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
    # KJV archaisms
    "ye", "thee", "thou", "thy", "thine", "unto", "upon", "hath", "doth",
    "thereof", "therein", "thereof", "hereby", "thereby", "wherefore",
    "saith", "cometh", "goeth", "sayeth",
})


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences. Uses punctuation-based splitting
    since we can't assume spaCy is available at analysis time."""
    raw = re.split(r'(?<=[.!?;:])\s+', text)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s.split()) >= 3:
            sentences.append(s)
    return sentences


def _content_tokens(text: str) -> set[str]:
    """Extract content word set from text, removing stopwords and punctuation."""
    tokens = re.findall(r"[a-z']+", text.lower())
    return {t for t in tokens if t not in STOPWORDS and len(t) > 1}


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


def _word_overlap_matrix_sentences(project: Project) -> tuple[np.ndarray, int]:
    """Sentence-level content-word Jaccard similarity matrix."""
    ref_text = (project.path / "reference.txt").read_text(encoding="utf-8")
    sentences = _split_sentences(ref_text)
    n = len(sentences)
    logger.info("Word overlap: %d sentences", n)

    token_sets = [_content_tokens(s) for s in sentences]
    matrix = np.zeros((n, n), dtype=np.float32)

    for i in range(n):
        if not token_sets[i]:
            continue
        matrix[i, i] = 1.0
        for j in range(i + 1, n):
            if not token_sets[j]:
                continue
            intersection = len(token_sets[i] & token_sets[j])
            if intersection == 0:
                continue
            union = len(token_sets[i] | token_sets[j])
            val = intersection / union if union > 0 else 0.0
            matrix[i, j] = val
            matrix[j, i] = val

    return matrix, n


def _edit_distance_matrix_sentences(project: Project) -> tuple[np.ndarray, int]:
    """Sentence-level normalized content-word edit distance similarity."""
    ref_text = (project.path / "reference.txt").read_text(encoding="utf-8")
    sentences = _split_sentences(ref_text)
    n = len(sentences)
    logger.info("Edit distance: %d sentences", n)

    token_lists = [list(_content_tokens(s)) for s in sentences]
    # Sort for determinism
    for tl in token_lists:
        tl.sort()

    matrix = np.zeros((n, n), dtype=np.float32)

    for i in range(n):
        la = len(token_lists[i])
        if la == 0:
            continue
        matrix[i, i] = 1.0
        for j in range(i + 1, n):
            lb = len(token_lists[j])
            if lb == 0:
                continue
            # Skip extreme length mismatches
            if la > 3 * lb or lb > 3 * la:
                continue
            # Token-level edit distance
            toks_a = token_lists[i]
            toks_b = token_lists[j]
            prev = list(range(lb + 1))
            for ii in range(1, la + 1):
                curr = [ii] + [0] * lb
                for jj in range(1, lb + 1):
                    cost = 0 if toks_a[ii - 1] == toks_b[jj - 1] else 1
                    curr[jj] = min(curr[jj - 1] + 1, prev[jj] + 1, prev[jj - 1] + cost)
                prev = curr
            dist = prev[lb]
            sim = 1.0 - dist / max(la, lb)
            if sim > 0.05:
                matrix[i, j] = sim
                matrix[j, i] = sim

    return matrix, n


class SelfSimilarityTrack:
    def __init__(self) -> None:
        self._metric = "cosine"

    def set_params(self, params: dict[str, Any]) -> None:
        if "metric" in params and params["metric"] in METRICS:
            self._metric = params["metric"]

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
        embeddings_db = project.path / "cache" / "embeddings.db"
        if not embeddings_db.exists():
            raise FileNotFoundError(
                f"Embeddings not found at {embeddings_db}. "
                "Run `palimpsest analyze` with Ollama available first."
            )

        store = SqliteVecStore.open_existing(embeddings_db)
        try:
            all_vectors = store.get_all_vectors()
        finally:
            store.close()

        if not all_vectors:
            raise ValueError("No embeddings found in database")

        n_paras = len(all_vectors)
        dim = len(all_vectors[0])
        embeddings = np.array(all_vectors, dtype=np.float32)
        paras = project.paragraphs()
        sha = project.metadata.reference_sha256
        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)
        available_metrics: list[str] = []
        metric_info: dict[str, dict[str, Any]] = {}

        for metric in METRICS:
            logger.info("Computing self-similarity: %s", metric)

            if metric == "cosine":
                matrix = _cosine_matrix(embeddings)
                np.fill_diagonal(matrix, 1.0)
                n_units = n_paras
                unit_type = "paragraph"
            elif metric == "jaccard":
                matrix = _jaccard_matrix(embeddings)
                np.fill_diagonal(matrix, 1.0)
                n_units = n_paras
                unit_type = "paragraph"
            elif metric == "word_overlap":
                matrix, n_units = _word_overlap_matrix_sentences(project)
                unit_type = "sentence"
            elif metric == "edit_distance":
                matrix, n_units = _edit_distance_matrix_sentences(project)
                unit_type = "sentence"
            else:
                continue

            matrix.astype(np.float32).tofile(signals_dir / f"self_similarity_{metric}.bin")
            available_metrics.append(metric)
            metric_info[metric] = {
                "unit_type": unit_type,
                "n_units": n_units,
                "dimensions": [n_units, n_units],
            }

        # Master manifest — default to cosine
        master = {
            "type": "matrix",
            "name": "self_similarity",
            "source": "embedding_cosine/0.1",
            "reference_sha256": sha,
            "dimensions": [n_paras, n_paras],
            "dtype": "float32",
            "byte_order": "little-endian",
            "data_file": "self_similarity_cosine.bin",
            "segment_offsets": [[s, e] for s, e, _ in paras],
            "metadata": {
                "similarity_metric": "cosine",
                "paragraph_count": n_paras,
                "embedding_dim": dim,
                "available_metrics": available_metrics,
                "metric_info": metric_info,
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
            "self_similarity.source": "paragraph_embeddings",
        }
