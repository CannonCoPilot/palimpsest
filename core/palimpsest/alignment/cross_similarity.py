"""Cross-similarity matrix between two projects' paragraph embeddings."""

from __future__ import annotations

import logging

import numpy as np

from palimpsest.formats.signals import SignalManifest
from palimpsest.project import Project
from palimpsest.tracks.self_similarity import _content_set
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
        # Fail loud: a silent cosine fallback would mask a caller bug and mislabel the result's metric.
        raise ValueError(f"Unknown cross-similarity metric {metric!r}; expected 'cosine' or 'jaccard'")

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
    """Load a project's embeddings, resolving the labeled vector store the modern pipeline writes.

    The embedding track writes one store per layer at ``cache/embeddings_{label}.db``; a legacy
    unlabeled ``cache/embeddings.db`` may also exist from ``palimpsest analyze``. Resolve the newest
    labeled store first (else a member embedded through the modern pipeline is invisible — the path
    split that made default *semantic* cross-alignment unreachable), then fall back to the legacy path."""
    cache = project.path / "cache"
    labeled = sorted(cache.glob("embeddings_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    emb_db = labeled[0] if labeled else cache / "embeddings.db"
    if not emb_db.exists():
        raise FileNotFoundError(
            f"Embeddings not found for {project.metadata.id} (looked for cache/embeddings_*.db then "
            "cache/embeddings.db). Run the embedding track or `palimpsest analyze` first."
        )
    store = SqliteVecStore.open_existing(emb_db)
    try:
        vectors = store.get_all_vectors()
    finally:
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


def _word_overlap_similarity(project_a: Project, project_b: Project) -> np.ndarray:
    """Word-overlap (Jaccard on content-token sets) between all paragraph pairs.

    Tokens are content words (stopwords + punctuation + single chars stripped, via the same
    ``_content_set`` the self-similarity track uses), NOT a raw ``split()``. Function words are
    shared by every paragraph in a language, so raw-token Jaccard floats unrelated cross-book
    passages above the Smith-Waterman zero-point (``score = sim*2-1``) and manufactures spurious
    homology edges; content-token Jaccard keeps only genuine lexical overlap."""
    paras_a = [text for _, _, text in project_a.paragraphs()]
    paras_b = [text for _, _, text in project_b.paragraphs()]

    sets_a = [_content_set(t.split()) for t in paras_a]
    sets_b = [_content_set(t.split()) for t in paras_b]

    n = len(sets_a)
    m = len(sets_b)
    matrix = np.zeros((n, m), dtype=np.float32)

    for i in range(n):
        if not sets_a[i]:
            continue
        for j in range(m):
            if not sets_b[j]:
                continue
            intersection = len(sets_a[i] & sets_b[j])
            union = len(sets_a[i] | sets_b[j])
            matrix[i, j] = intersection / union if union > 0 else 0.0

    return matrix


def compute_word_overlap(
    project_a: Project,
    project_b: Project,
) -> tuple[np.ndarray, SignalManifest]:
    """Compute word-overlap (Jaccard) similarity matrix between two projects."""
    matrix = _word_overlap_similarity(project_a, project_b)
    n, m = matrix.shape

    paras_a = project_a.paragraphs()
    paras_b = project_b.paragraphs()

    manifest = SignalManifest(
        type="matrix",
        name="cross_similarity",
        source="word_overlap/0.1",
        reference_sha256=f"{project_a.metadata.reference_sha256}:{project_b.metadata.reference_sha256}",
        dimensions=[n, m],
        data_file="cross_similarity.bin",
        segment_offsets=[[s, e] for s, e, _ in paras_a],
        metadata={
            "similarity_metric": "word_overlap",
            "query_id": project_a.metadata.id,
            "target_id": project_b.metadata.id,
            "query_paragraphs": n,
            "target_paragraphs": m,
            "target_segment_offsets": [[s, e] for s, e, _ in paras_b],
        },
    )
    return matrix, manifest


def _jaccard_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Jaccard similarity on binarized embeddings."""
    bin_a = (a > 0).astype(np.float32)
    bin_b = (b > 0).astype(np.float32)

    intersection = bin_a @ bin_b.T
    sums_a = bin_a.sum(axis=1)
    sums_b = bin_b.sum(axis=1)
    union = sums_a[:, None] + sums_b[None, :] - intersection

    return np.where(union > 0, intersection / union, 0.0).astype(np.float32)
