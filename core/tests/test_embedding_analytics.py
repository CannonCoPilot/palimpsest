"""Unit tests for palimpsest.vectorstore.analytics — the P3 deterministic embedding compute module.

These exercise the pure numpy functions directly (no server, no embedding service): determinism,
shape/dtype contracts, index alignment, and the no-silent-cap behaviour of sampling/block-reduction.
"""

import numpy as np
import pytest

from palimpsest.vectorstore import analytics as A


@pytest.fixture
def vectors() -> np.ndarray:
    """30 reproducible 8-D vectors."""
    return np.random.default_rng(7).standard_normal((30, 8)).astype(np.float32)


@pytest.fixture
def blobs() -> np.ndarray:
    """Three well-separated clusters of 10 points each (rows 0-9, 10-19, 20-29)."""
    rng = np.random.default_rng(11)
    centers = np.array([[10, 0, 0, 0], [0, 10, 0, 0], [0, 0, 10, 0]], dtype=np.float64)
    pts = [c + 0.05 * rng.standard_normal((10, 4)) for c in centers]
    return np.vstack(pts).astype(np.float32)


class TestPCA:
    def test_shape_and_dtype(self, vectors):
        coords = A.pca_projection(vectors, 2)
        assert coords.shape == (30, 2)
        assert coords.dtype == np.float32

    def test_deterministic(self, vectors):
        assert np.array_equal(A.pca_projection(vectors), A.pca_projection(vectors))

    def test_variance_ordered(self, vectors):
        # PC1 must capture at least as much spread as PC2 (that is what "principal" means).
        coords = A.pca_projection(vectors, 2)
        assert coords[:, 0].var() >= coords[:, 1].var()

    def test_rank_deficient_is_zero_padded(self):
        # Two points span at most one dimension; the 2nd component is zero-padded, not an error.
        coords = A.pca_projection(np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]), 2)
        assert coords.shape == (2, 2)
        assert np.allclose(coords[:, 1], 0.0)

    def test_empty(self):
        assert A.pca_projection(np.zeros((0, 5)), 2).shape == (0, 2)


class TestKMeans:
    def test_deterministic(self, vectors):
        a, sa = A.kmeans(vectors, 4, seed=0)
        b, sb = A.kmeans(vectors, 4, seed=0)
        assert np.array_equal(a, b) and sa == sb

    def test_sizes_sum_to_n(self, vectors):
        labels, sizes = A.kmeans(vectors, 4, seed=0)
        assert sum(sizes) == 30
        assert labels.shape == (30,)

    def test_k_clamped_to_n(self):
        labels, sizes = A.kmeans(np.zeros((3, 4)), 10, seed=0)
        assert len(sizes) == 3  # cannot have more clusters than points

    def test_recovers_separated_blobs(self, blobs):
        # Each true blob (10 contiguous rows) must land in a single cluster.
        labels, sizes = A.kmeans(blobs, 3, seed=0)
        assert sorted(sizes) == [10, 10, 10]
        for start in (0, 10, 20):
            assert len(set(labels[start:start + 10].tolist())) == 1

    def test_seed_is_a_param(self, blobs):
        # Different seeds are allowed to differ; same seed must not. (No hidden RNG.)
        same = np.array_equal(A.kmeans(blobs, 3, seed=1)[0], A.kmeans(blobs, 3, seed=1)[0])
        assert same


class TestSimilarityMatrix:
    def test_diagonal_is_one_and_symmetric(self, vectors):
        m, order = A.similarity_matrix(vectors)
        assert m.shape == (30, 30) and order is None
        assert np.allclose(np.diag(m), 1.0, atol=1e-4)
        assert np.allclose(m, m.T, atol=1e-5)

    def test_cluster_order_returns_permutation(self, blobs):
        labels, _ = A.kmeans(blobs, 3, seed=0)
        perm = np.argsort(labels, kind="stable")
        m, served = A.similarity_matrix(blobs, order=perm)
        assert served is not None and np.array_equal(served, perm)
        assert m.shape == (30, 30)

    def test_block_reduced_above_cap(self):
        big = np.random.default_rng(1).standard_normal((A.HEATMAP_MAX_N + 100, 6)).astype(np.float32)
        m, served = A.similarity_matrix(big)
        assert m.shape == (A.HEATMAP_MAX_N, A.HEATMAP_MAX_N)
        assert served is None  # reduced matrices carry no chunk-order permutation


class TestDistanceHistograms:
    def test_pairwise_counts_all_pairs_when_unsampled(self, vectors):
        edges, counts, sampled = A.pairwise_distance_histogram(vectors, bins=20)
        assert edges.shape == (21,)
        assert sampled == 30 * 29 // 2
        assert int(counts.sum()) == sampled

    def test_pairwise_samples_and_reports(self, vectors):
        edges, counts, sampled = A.pairwise_distance_histogram(vectors, bins=20, sample_budget=50)
        assert sampled <= 50  # realised sample reported, never a silent cap
        assert int(counts.sum()) == sampled

    def test_fixed_range_zero_to_two(self, vectors):
        edges, _, _ = A.pairwise_distance_histogram(vectors, bins=10)
        assert edges[0] == 0.0 and edges[-1] == 2.0

    def test_nn_counts_one_per_chunk(self, vectors):
        edges, counts, count = A.nn_distance_histogram(vectors, bins=20)
        assert count == 30
        assert int(counts.sum()) == 30


class TestLaneEncoding:
    @pytest.mark.parametrize("encoding", ["pc1", "cluster", "nn-density"])
    def test_one_scalar_per_chunk(self, vectors, encoding):
        lane = A.lane_encoding(vectors, encoding)
        assert lane.shape == (30,)
        assert lane.dtype == np.float32

    def test_pc1_matches_projection_first_component(self, vectors):
        # Lane 'pc1' must equal the projection's first column — same axis, so P5/P6 agree.
        assert np.allclose(A.lane_encoding(vectors, "pc1"), A.pca_projection(vectors, 2)[:, 0])

    def test_cluster_lane_matches_clusters(self, blobs):
        lane = A.lane_encoding(blobs, "cluster", k=3, seed=0)
        labels, _ = A.kmeans(blobs, 3, seed=0)
        assert np.array_equal(lane.astype(np.int64), labels)

    def test_unknown_encoding_raises(self, vectors):
        with pytest.raises(ValueError, match="unknown lane encoding"):
            A.lane_encoding(vectors, "tsne")
