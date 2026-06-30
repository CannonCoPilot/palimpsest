"""Unit tests for palimpsest.analysis.chunk_stats — P6 deterministic per-chunk-layer stats (FR-14)."""

import pytest

from palimpsest.analysis import chunk_stats as C

# A 6-chunk fixture with hand-checkable alignment.
#   chunk_starts vs structural [0, 60, 150]: chunks at 0 (idx0), 60 (idx3), 150 (idx5) align exactly.
_CHAR = [10, 20, 30, 40, 50, 60]
_WORDS = [2, 4, 6, 8, 10, 12]
_TYPES = ["verse", "verse", "verse", "chapter", "chapter", "none"]
_STARTS = [0, 10, 30, 60, 100, 150]
_BOUNDS = [0, 60, 150]


def _stats(**over):
    kw = dict(
        char_lengths=_CHAR, word_counts=_WORDS, element_types=_TYPES,
        chunk_starts=_STARTS, structural_boundaries=_BOUNDS,
    )
    kw.update(over)
    return C.compute_chunk_layer_stats(**kw)


class TestEcdf:
    def test_monotone_ends_at_one(self):
        e = C.ecdf([3, 1, 2, 2])
        assert e["x"] == [1.0, 2.0, 3.0]  # sorted distinct
        assert e["y"] == [pytest.approx(0.25), pytest.approx(0.75), pytest.approx(1.0)]
        assert all(b >= a for a, b in zip(e["y"], e["y"][1:]))  # non-decreasing

    def test_empty(self):
        assert C.ecdf([]) == {"x": [], "y": []}


class TestHistograms:
    def test_bins_sum_to_chunk_count(self):
        s = _stats()
        for metric in ("words", "chars"):
            counts = s["length"][metric]["histogram"]["counts"]
            assert sum(counts) == len(_CHAR)  # every chunk lands in exactly one bin

    def test_summary_present(self):
        h = _stats()["length"]["words"]["histogram"]
        assert h["n"] == 6 and h["min"] == 2 and h["max"] == 12


class TestByElementType:
    def test_groups_index_correct_and_complete(self):
        groups = _stats()["by_element_type"]["groups"]
        by = {g["type"]: g for g in groups}
        assert by["verse"]["values"] == [2, 4, 6]      # idx 0,1,2
        assert by["chapter"]["values"] == [8, 10]      # idx 3,4
        assert by["none"]["values"] == [12]            # idx 5
        assert sum(g["summary"]["n"] for g in groups) == len(_WORDS)

    def test_ordered_by_descending_size(self):
        types = [g["type"] for g in _stats()["by_element_type"]["groups"]]
        assert types == ["verse", "chapter", "none"]

    def test_sampling_reported_not_silent(self):
        s = C.compute_chunk_layer_stats(
            char_lengths=[1] * 5, word_counts=[1, 2, 3, 4, 5], element_types=["p"] * 5,
            chunk_starts=[0, 1, 2, 3, 4], structural_boundaries=[0], max_violin=3,
        )
        g = s["by_element_type"]["groups"][0]
        assert g["sampled"] is True and g["sample_size"] == 3 and g["original_n"] == 5
        assert g["summary"]["n"] == 5  # summary still over the full group


class TestBoundaryAlignment:
    def test_exact_alignment_counts(self):
        ba = _stats()["boundary_alignment"]
        assert ba["n_chunk_boundaries"] == 6
        assert ba["n_aligned"] == 3                       # starts 0, 60, 150
        assert ba["fraction_aligned"] == pytest.approx(0.5)
        assert ba["n_structural_boundaries"] == 3
        assert ba["n_structural_hit"] == 3                # every boundary has a chunk start
        assert ba["fraction_structural_hit"] == pytest.approx(1.0)

    def test_fractions_in_unit_interval(self):
        ba = _stats()["boundary_alignment"]
        assert 0.0 <= ba["fraction_aligned"] <= 1.0
        assert 0.0 <= ba["fraction_structural_hit"] <= 1.0
        for bt in ba["by_type"]:
            assert 0.0 <= bt["fraction"] <= 1.0

    def test_by_type_breakdown(self):
        by = {bt["type"]: bt for bt in _stats()["boundary_alignment"]["by_type"]}
        assert by["verse"]["aligned"] == 1 and by["verse"]["n"] == 3   # only start 0
        assert by["chapter"]["aligned"] == 1 and by["chapter"]["n"] == 2  # only start 60
        assert by["none"]["aligned"] == 1 and by["none"]["n"] == 1     # start 150

    def test_tolerance_widens_match(self):
        near = dict(
            char_lengths=[1], word_counts=[1], element_types=["p"],
            chunk_starts=[5], structural_boundaries=[0],
        )
        assert C.compute_chunk_layer_stats(**near, tolerance=0)["boundary_alignment"]["n_aligned"] == 0
        assert C.compute_chunk_layer_stats(**near, tolerance=5)["boundary_alignment"]["n_aligned"] == 1


class TestContract:
    def test_deterministic(self):
        assert _stats() == _stats()

    def test_parallel_length_validation(self):
        with pytest.raises(ValueError):
            C.compute_chunk_layer_stats(
                char_lengths=[1, 2], word_counts=[1], element_types=["p", "p"],
                chunk_starts=[0, 1], structural_boundaries=[0],
            )

    def test_empty_layer_well_defined(self):
        s = C.compute_chunk_layer_stats(
            char_lengths=[], word_counts=[], element_types=[],
            chunk_starts=[], structural_boundaries=[],
        )
        assert s["n_chunks"] == 0
        assert s["boundary_alignment"]["fraction_aligned"] == 0.0
        assert s["length"]["words"]["ecdf"] == {"x": [], "y": []}
