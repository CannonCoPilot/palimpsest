"""embedding_analytics — deterministic, numpy-only semantic-space compute for the P3 embedding-viz suite.

Every function here reads the persisted embedding vectors (``get_all_vectors()`` order = chunk order,
so row *i* is chunk *i*) and returns data the frontend renders. The contract that makes this safe:

  * **Index alignment is preserved end to end.** Projection, lane, and cluster outputs are returned in
    the same row order as the input — the frontend joins them to chunks by position, so any reordering
    here would silently mislabel the document. Only the ``order="cluster"`` heatmap intentionally
    permutes, and it returns the permutation so the caller can undo it.
  * **Determinism with no new dependencies.** PCA is numpy SVD with sign-canonicalised components;
    k-means is seeded Lloyd's; histograms have a fixed cosine-distance range ``[0, 2]``. No sklearn,
    no UMAP — UMAP is the opt-in escape hatch deferred to Vision OQ#4.
  * **No silent caps (fallbacks-are-failures).** When a result is sampled (pairwise distances) or
    block-reduced (large heatmap), the function returns the realised sample size / reduced dimension so
    the caller can report it instead of presenting a truncated view as if it were exhaustive.

Cosine geometry throughout: vectors are unit-normalised before any similarity/cluster computation, so
"distance" means cosine distance ``1 - cos ∈ [0, 2]`` and clustering is spherical.
"""

from __future__ import annotations

import numpy as np

# Above this chunk count the dense N×N similarity matrix is block-reduced before serving — an O(N^2)
# payload past a few hundred chunks is neither renderable nor honest as a per-chunk heatmap. The
# reduction is reported, never silent.
HEATMAP_MAX_N = 512

# Default pair budget for the pairwise-distance histogram; above it we sample (and report the count).
PAIRWISE_SAMPLE_BUDGET = 200_000

_EPS = 1e-12


def _as_matrix(vectors: object) -> np.ndarray:
    """Coerce to a 2-D float64 array. float64 internally for stable SVD/means; callers downcast on
    serialize. Raises on ragged / non-2-D input rather than guessing a shape."""
    arr = np.asarray(vectors, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"expected a 2-D (n, dim) array of vectors, got shape {arr.shape}")
    return arr


def _unit(vectors: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalise; zero rows stay zero (their cosine similarity to anything is 0)."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    safe = np.where(norms == 0.0, 1.0, norms)
    return vectors / safe


def _canonicalize_signs(coords: np.ndarray) -> np.ndarray:
    """SVD component signs are arbitrary; fix each column so its largest-magnitude entry is positive.
    This makes PCA output reproducible across platforms/BLAS without changing the geometry."""
    out = coords.copy()
    for j in range(out.shape[1]):
        col = out[:, j]
        if col.size and col[int(np.argmax(np.abs(col)))] < 0:
            out[:, j] = -col
    return out


def pca_projection(vectors: object, n_components: int = 2) -> np.ndarray:
    """Project ``vectors`` onto their top ``n_components`` principal axes → ``(n, n_components)`` float32.

    Deterministic: mean-centre, numpy SVD, sign-canonicalised. Rank-deficient input (fewer informative
    dimensions than ``n_components``, or n < n_components) is zero-padded so the shape contract holds."""
    if n_components < 1:
        raise ValueError(f"n_components must be >= 1, got {n_components}")
    X = _as_matrix(vectors)
    n = X.shape[0]
    if n == 0:
        return np.zeros((0, n_components), dtype=np.float32)
    Xc = X - X.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(Xc, full_matrices=False)
    comps = vt[:n_components]
    coords = Xc @ comps.T
    if coords.shape[1] < n_components:
        coords = np.hstack(
            [coords, np.zeros((n, n_components - coords.shape[1]), dtype=coords.dtype)]
        )
    return _canonicalize_signs(coords).astype(np.float32)


def _kmeanspp_init(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """Seeded k-means++ centre initialisation (deterministic given ``rng``)."""
    n = X.shape[0]
    centers = np.empty((k, X.shape[1]), dtype=X.dtype)
    first = int(rng.integers(0, n))
    centers[0] = X[first]
    closest_sq = np.sum((X - centers[0]) ** 2, axis=1)
    for c in range(1, k):
        total = float(closest_sq.sum())
        if total <= _EPS:  # all remaining points coincide with a chosen centre
            centers[c] = X[int(rng.integers(0, n))]
        else:
            probs = closest_sq / total
            centers[c] = X[int(rng.choice(n, p=probs))]
        new_sq = np.sum((X - centers[c]) ** 2, axis=1)
        closest_sq = np.minimum(closest_sq, new_sq)
    return centers


def kmeans(
    vectors: object, k: int, seed: int = 0, max_iter: int = 100
) -> tuple[np.ndarray, list[int]]:
    """Spherical k-means (unit-normalised inputs) via seeded Lloyd's iteration.

    Returns ``(labels (n,) int64, sizes list[int])`` with ``labels`` in input/chunk order. ``k`` is
    clamped to ``n`` (cannot have more clusters than points). Deterministic: k-means++ init uses the
    seeded ``rng``; assignment ties fall to the lowest index (numpy ``argmin``); empty clusters keep
    their previous centre rather than a random reseed, so a run never depends on unseeded chance."""
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    U = _unit(_as_matrix(vectors))
    n = U.shape[0]
    if n == 0:
        return np.zeros(0, dtype=np.int64), []
    k = min(k, n)
    rng = np.random.default_rng(seed)
    centers = _kmeanspp_init(U, k, rng)
    labels = np.full(n, -1, dtype=np.int64)
    for _ in range(max_iter):
        # squared euclidean on unit vectors is monotone in cosine distance → spherical assignment
        d = np.sum(U**2, axis=1)[:, None] - 2.0 * (U @ centers.T) + np.sum(centers**2, axis=1)[None, :]
        new_labels = np.argmin(d, axis=1).astype(np.int64)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for c in range(k):
            mask = labels == c
            if mask.any():
                centers[c] = U[mask].mean(axis=0)
    sizes = [int((labels == c).sum()) for c in range(k)]
    return labels, sizes


def similarity_matrix(
    vectors: object, order: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray | None]:
    """Cosine-similarity matrix → ``(matrix float32, served_order | None)``.

    For ``n <= HEATMAP_MAX_N`` returns the dense ``(n, n)`` matrix. Above it, block-reduces to
    ``(HEATMAP_MAX_N, HEATMAP_MAX_N)`` by averaging contiguous blocks and returns ``served_order=None``
    with the reduced matrix (the caller reports the reduction). When ``order`` (a permutation of chunk
    indices, e.g. cluster order) is given for an un-reduced matrix, rows/cols are permuted by it and the
    permutation is returned so the frontend can map cells back to chunks."""
    U = _unit(_as_matrix(vectors))
    n = U.shape[0]
    if n == 0:
        return np.zeros((0, 0), dtype=np.float32), None
    if n > HEATMAP_MAX_N:
        sims = (U @ U.T).astype(np.float64)
        reduced = _block_reduce(sims, HEATMAP_MAX_N)
        return reduced.astype(np.float32), None
    if order is not None:
        perm = np.asarray(order, dtype=np.int64)
        Uo = U[perm]
        return (Uo @ Uo.T).astype(np.float32), perm
    return (U @ U.T).astype(np.float32), None


def _block_reduce(matrix: np.ndarray, target: int) -> np.ndarray:
    """Average ``matrix`` down to ``(target, target)`` over near-equal contiguous index blocks."""
    n = matrix.shape[0]
    bounds = np.linspace(0, n, target + 1, dtype=int)
    out = np.empty((target, target), dtype=np.float64)
    for i in range(target):
        ri = slice(bounds[i], bounds[i + 1])
        for j in range(target):
            cj = slice(bounds[j], bounds[j + 1])
            block = matrix[ri, cj]
            out[i, j] = float(block.mean()) if block.size else 0.0
    return out


def _nn_distances(U: np.ndarray) -> np.ndarray:
    """Per-row nearest-neighbour cosine distance (self excluded). ``U`` must be unit-normalised."""
    sims = U @ U.T
    np.fill_diagonal(sims, -np.inf)
    nn_sims = sims.max(axis=1)
    return 1.0 - nn_sims


def pairwise_distance_histogram(
    vectors: object, bins: int = 50, sample_budget: int = PAIRWISE_SAMPLE_BUDGET, seed: int = 0
) -> tuple[np.ndarray, np.ndarray, int]:
    """Histogram of pairwise cosine distances → ``(edges (bins+1,), counts (bins,), sampled_pairs)``.

    Fixed range ``[0, 2]`` so histograms from different layers are comparable. When the full pair count
    ``n(n-1)/2`` exceeds ``sample_budget`` the pairs are randomly sampled (seeded) and the realised
    sample size is returned — never a silent cap. ``sampled_pairs`` equals the exact total when no
    sampling occurred."""
    U = _unit(_as_matrix(vectors))
    n = U.shape[0]
    total_pairs = n * (n - 1) // 2
    if total_pairs == 0:
        return np.linspace(0.0, 2.0, bins + 1), np.zeros(bins, dtype=np.int64), 0
    if total_pairs > sample_budget:
        rng = np.random.default_rng(seed)
        i = rng.integers(0, n, size=sample_budget)
        j = rng.integers(0, n, size=sample_budget)
        keep = i != j
        i, j = i[keep], j[keep]
        dists = 1.0 - np.sum(U[i] * U[j], axis=1)
        sampled = int(dists.size)
    else:
        sims = U @ U.T
        iu = np.triu_indices(n, k=1)
        dists = 1.0 - sims[iu]
        sampled = total_pairs
    # Cosine distance is mathematically in [0, 2]; clip float-error excursions (a self-similar pair can
    # land at 1 - (1 + 1e-7)) back into range so every pair is binned. Without this, np.histogram
    # silently drops out-of-range values and counts.sum() < pairs — a silent undercount.
    dists = np.clip(dists, 0.0, 2.0)
    counts, edges = np.histogram(dists, bins=bins, range=(0.0, 2.0))
    return edges, counts.astype(np.int64), sampled


def nn_distance_histogram(
    vectors: object, bins: int = 50
) -> tuple[np.ndarray, np.ndarray, int]:
    """Histogram of each chunk's nearest-neighbour cosine distance → ``(edges, counts, n)``.

    O(N²) in memory like the heatmap but O(N·N) cheap to scan; the scalable companion to the pairwise
    histogram. ``n`` (the chunk count = number of NN distances) is returned for symmetry with the
    pairwise variant's realised-sample report."""
    U = _unit(_as_matrix(vectors))
    n = U.shape[0]
    if n < 2:
        return np.linspace(0.0, 2.0, bins + 1), np.zeros(bins, dtype=np.int64), n
    nn = np.clip(_nn_distances(U), 0.0, 2.0)  # clip float-error excursions so every chunk is binned
    counts, edges = np.histogram(nn, bins=bins, range=(0.0, 2.0))
    return edges, counts.astype(np.int64), n


def lane_encoding(
    vectors: object, encoding: str, k: int = 8, seed: int = 0
) -> np.ndarray:
    """One scalar per chunk (chunk order) for the in-text embedding lane → ``(n,)`` float32.

      * ``pc1``        — first principal component (continuous position along the dominant axis).
      * ``cluster``    — k-means cluster id (categorical, coloured as a palette index).
      * ``nn-density`` — inverse nearest-neighbour distance: high where a chunk sits in a dense
                         semantic neighbourhood, low where it is an outlier.
    """
    if encoding == "pc1":
        return pca_projection(vectors, 1)[:, 0].astype(np.float32)
    if encoding == "cluster":
        labels, _ = kmeans(vectors, k, seed=seed)
        return labels.astype(np.float32)
    if encoding == "nn-density":
        U = _unit(_as_matrix(vectors))
        if U.shape[0] < 2:
            return np.zeros(U.shape[0], dtype=np.float32)
        return (1.0 / (_nn_distances(U) + _EPS)).astype(np.float32)
    raise ValueError(f"unknown lane encoding {encoding!r} (expected pc1 | cluster | nn-density)")
