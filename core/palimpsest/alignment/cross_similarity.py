"""Cross-similarity matrix between two projects' paragraph embeddings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from palimpsest.formats.signals import SignalManifest, write_signal
from palimpsest.project import Project
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

logger = logging.getLogger(__name__)


def compute_cross_similarity(
    project_a: Project,
    project_b: Project,
    metric: str = "cosine",
) -> tuple[np.ndarray, SignalManifest]:
    """Compute NxM cross-similarity matrix between two projects' paragraph embeddings.

    Returns (matrix, manifest) where matrix is float32 [N, M].
    N = paragraphs in project_a (query), M = paragraphs in project_b (target).
    """
    emb_a = _load_embeddings(project_a)
    emb_b = _load_embeddings(project_b)

    n, dim_a = emb_a.shape
    m, dim_b = emb_b.shape

    if dim_a != dim_b:
        raise ValueError(
            f"Embedding dimensions differ: {project_a.metadata.id} has dim={dim_a}, "
            f"{project_b.metadata.id} has dim={dim_b}"
        )

    logger.info("Computing %dx%d cross-similarity (%s)", n, m, metric)

    if metric == "cosine":
        matrix = _cosine_similarity(emb_a, emb_b)
    elif metric == "jaccard":
        matrix = _jaccard_similarity(emb_a, emb_b)
    else:
        matrix = _cosine_similarity(emb_a, emb_b)

    paras_a = project_a.paragraphs()
    paras_b = project_b.paragraphs()

    manifest = SignalManifest(
        type="matrix",
        name="cross_similarity",
        source=f"embedding_{metric}/0.1",
        reference_sha256=f"{project_a.metadata.reference_sha256}:{project_b.metadata.reference_sha256}",
        dimensions=[n, m],
        data_file="cross_similarity.bin",
        segment_offsets=[[s, e] for s, e, _ in paras_a],
        metadata={
            "similarity_metric": metric,
            "query_id": project_a.metadata.id,
            "target_id": project_b.metadata.id,
            "query_paragraphs": n,
            "target_paragraphs": m,
            "embedding_dim": dim_a,
            "target_segment_offsets": [[s, e] for s, e, _ in paras_b],
        },
    )

    return matrix, manifest


def _load_embeddings(project: Project) -> np.ndarray:
    """Load paragraph embeddings from a project's cache."""
    emb_db = project.path / "cache" / "embeddings.db"
    if not emb_db.exists():
        raise FileNotFoundError(
            f"Embeddings not found for {project.metadata.id}. "
            "Run `palimpsest analyze` with Ollama available first."
        )
    store = SqliteVecStore.open_existing(emb_db)
    vectors = store.get_all_vectors()
    store.close()

    if not vectors:
        raise ValueError(f"No embeddings found for {project.metadata.id}")

    return np.array(vectors, dtype=np.float32)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity between all pairs of rows in a and b."""
    norms_a = np.linalg.norm(a, axis=1, keepdims=True)
    norms_a = np.where(norms_a > 1e-8, norms_a, 1.0)
    norms_b = np.linalg.norm(b, axis=1, keepdims=True)
    norms_b = np.where(norms_b > 1e-8, norms_b, 1.0)

    normed_a = a / norms_a
    normed_b = b / norms_b

    matrix = normed_a @ normed_b.T
    np.clip(matrix, -1.0, 1.0, out=matrix)
    return matrix.astype(np.float32)


def _jaccard_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Jaccard similarity on binarized embeddings."""
    bin_a = (a > 0).astype(np.float32)
    bin_b = (b > 0).astype(np.float32)

    intersection = bin_a @ bin_b.T
    sums_a = bin_a.sum(axis=1)
    sums_b = bin_b.sum(axis=1)
    union = sums_a[:, None] + sums_b[None, :] - intersection

    return np.where(union > 0, intersection / union, 0.0).astype(np.float32)
