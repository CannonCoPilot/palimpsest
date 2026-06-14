"""Self-similarity matrix track — pairwise similarity over paragraph embeddings.

Computes all four metrics (cosine, jaccard, word_overlap, edit_distance)
and stores each as a separate binary file so the UI can switch instantly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from palimpsest.formats.signals import SignalManifest
from palimpsest.project import Project
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

logger = logging.getLogger(__name__)

METRICS = ("cosine", "jaccard", "word_overlap", "edit_distance")


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


def _word_overlap_matrix(project: Project) -> np.ndarray:
    """Jaccard on token sets — no embeddings needed."""
    paras = [text for _, _, text in project.paragraphs()]
    token_sets = [set(t.lower().split()) for t in paras]
    n = len(token_sets)
    matrix = np.zeros((n, n), dtype=np.float32)
    for i in range(n):
        if not token_sets[i]:
            continue
        for j in range(i, n):
            if not token_sets[j]:
                continue
            intersection = len(token_sets[i] & token_sets[j])
            union = len(token_sets[i] | token_sets[j])
            val = intersection / union if union > 0 else 0.0
            matrix[i, j] = val
            matrix[j, i] = val
    return matrix


def _edit_distance_matrix(project: Project) -> np.ndarray:
    """Normalized edit distance similarity (1 - norm_edit_dist) on paragraph text."""
    paras = [text for _, _, text in project.paragraphs()]
    n = len(paras)
    matrix = np.zeros((n, n), dtype=np.float32)

    for i in range(n):
        matrix[i, i] = 1.0
        for j in range(i + 1, n):
            a, b = paras[i], paras[j]
            if not a or not b:
                continue
            # Use token-level edit distance for efficiency
            toks_a = a.lower().split()
            toks_b = b.lower().split()
            la, lb = len(toks_a), len(toks_b)
            if la == 0 or lb == 0:
                continue
            # Banded DP — skip pairs where length ratio is extreme
            if la > 3 * lb or lb > 3 * la:
                continue
            prev = list(range(lb + 1))
            for ii in range(1, la + 1):
                curr = [ii] + [0] * lb
                for jj in range(1, lb + 1):
                    cost = 0 if toks_a[ii - 1] == toks_b[jj - 1] else 1
                    curr[jj] = min(curr[jj - 1] + 1, prev[jj] + 1, prev[jj - 1] + cost)
                prev = curr
            dist = prev[lb]
            sim = 1.0 - dist / max(la, lb)
            matrix[i, j] = max(0.0, sim)
            matrix[j, i] = max(0.0, sim)

    return matrix


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

        n = len(all_vectors)
        dim = len(all_vectors[0])
        embeddings = np.array(all_vectors, dtype=np.float32)
        paras = project.paragraphs()
        sha = project.metadata.reference_sha256
        signals_dir = project.path / "signals"
        available_metrics: list[str] = []

        for metric in METRICS:
            logger.info("Computing self-similarity: %s (%d paragraphs)", metric, n)
            if metric == "cosine":
                matrix = _cosine_matrix(embeddings)
            elif metric == "jaccard":
                matrix = _jaccard_matrix(embeddings)
            elif metric == "word_overlap":
                matrix = _word_overlap_matrix(project)
            elif metric == "edit_distance":
                matrix = _edit_distance_matrix(project)
            else:
                continue

            np.fill_diagonal(matrix, 1.0)

            signals_dir.mkdir(parents=True, exist_ok=True)
            matrix.astype(np.float32).tofile(signals_dir / f"self_similarity_{metric}.bin")
            available_metrics.append(metric)

        # Write master manifest pointing to cosine as default, listing all metrics
        master = SignalManifest(
            type="matrix",
            name="self_similarity",
            source="embedding_cosine/0.1",
            reference_sha256=sha,
            dimensions=[n, n],
            data_file="self_similarity_cosine.bin",
            segment_offsets=[[s, e] for s, e, _ in paras],
            metadata={
                "similarity_metric": "cosine",
                "paragraph_count": n,
                "embedding_dim": dim,
                "available_metrics": available_metrics,
            },
        )
        manifest_path = signals_dir / "self_similarity.json"
        import json
        manifest_path.write_text(
            json.dumps(master.to_dict(), indent=2, ensure_ascii=False),
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
