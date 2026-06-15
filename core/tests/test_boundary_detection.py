"""Unit tests for boundary_detection — directionality, insulation, Viterbi HMM, domains."""

from __future__ import annotations

import numpy as np

from palimpsest.tracks.boundary_detection import (
    _directionality_index,
    _extract_domains,
    _insulation_score,
    _viterbi_boundary,
)


class TestDirectionalityIndex:
    def test_shape_matches_input(self):
        di = _directionality_index(np.ones((12, 12)), window=3)
        assert di.shape == (12,)

    def test_uniform_matrix_deep_interior_is_balanced(self):
        # Uniform similarity → upstream == downstream → DI ~ 0, but only where both
        # windows are full (>= `window` from each edge; nearer the edges the windows
        # truncate asymmetrically and DI is nonzero by construction).
        window = 3
        di = _directionality_index(np.ones((20, 20)), window=window)
        assert np.allclose(di[window:-window], 0.0, atol=1e-6)

    def test_downstream_bias_is_positive(self):
        n = 10
        m = np.zeros((n, n))
        m[5, 6:9] = 1.0  # position 5 only similar to downstream neighbours
        di = _directionality_index(m, window=3)
        assert di[5] > 0.0

    def test_upstream_bias_is_negative(self):
        n = 10
        m = np.zeros((n, n))
        m[5, 2:5] = 1.0  # position 5 only similar to upstream neighbours
        di = _directionality_index(m, window=3)
        assert di[5] < 0.0


class TestInsulationScore:
    def test_shape_matches_input(self):
        ins = _insulation_score(np.ones((15, 15)), window=3)
        assert ins.shape == (15,)

    def test_uniform_matrix_is_constant_high(self):
        ins = _insulation_score(np.ones((15, 15)), window=3)
        assert np.allclose(ins, 1.0)

    def test_lower_at_block_boundary(self):
        n = 20
        m = np.zeros((n, n))
        m[:10, :10] = 1.0
        m[10:, 10:] = 1.0  # two non-interacting blocks
        ins = _insulation_score(m, window=3)
        # The window at the block seam straddles the zero cross-block region.
        assert ins[10] < ins[5]
        assert ins[10] < ins[15]


class TestViterbiBoundary:
    def test_empty_features_returns_zeros(self):
        assert _viterbi_boundary(np.zeros((0, 0))).tolist() == []
        assert np.all(_viterbi_boundary(np.zeros((5, 0))) == 0)

    def test_output_length_and_valid_states(self):
        rng = np.random.RandomState(0)
        features = rng.rand(30, 4)
        states = _viterbi_boundary(features)
        assert states.shape == (30,)
        assert set(np.unique(states)).issubset({0, 1, 2})

    def test_deterministic(self):
        rng = np.random.RandomState(1)
        features = rng.rand(40, 2)
        assert np.array_equal(_viterbi_boundary(features), _viterbi_boundary(features))

    def test_distinguishes_inside_from_boundary_regions(self):
        n = 40
        # cols: [DI, insulation]. First half = inside (low |DI|, high insulation);
        # second half = boundary-like (high |DI|, low insulation).
        di = np.zeros(n)
        ins = np.ones(n)
        di[20:] = 3.0
        ins[20:] = -2.0
        features = np.column_stack([di, ins])
        states = _viterbi_boundary(features)
        # First half should be predominantly inside-domain (state 0)...
        assert (states[:18] == 0).sum() >= 12
        # ...and the second half should carry non-inside (boundary/transition) states.
        assert (states[22:] != 0).sum() >= 8


class TestExtractDomains:
    def test_empty_states(self):
        assert _extract_domains(np.array([], dtype=int)) == []

    def test_single_domain_spans_all(self):
        domains = _extract_domains(np.zeros(10, dtype=int))
        assert len(domains) == 1
        assert domains[0]["start"] == 0
        assert domains[0]["end"] == 10
        assert domains[0]["length"] == 10

    def test_boundary_splits_into_two_domains(self):
        states = np.array([0, 0, 0, 0, 1, 0, 0, 0, 0, 0])
        domains = _extract_domains(states)
        assert len(domains) == 2
        assert domains[0]["end"] == 4
        assert domains[1]["start"] == 5

    def test_small_domains_filtered(self):
        # First run of 0s has length 2 (< 3) and must be dropped.
        states = np.array([0, 0, 1, 0, 0, 0, 0, 0])
        domains = _extract_domains(states)
        assert len(domains) == 1
        assert domains[0]["length"] >= 3
