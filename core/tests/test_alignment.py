"""Tests for pairwise text alignment engine."""

import numpy as np
import pytest

from palimpsest.alignment.records import AlignmentRecord, write_alignment_records, read_alignment_records
from palimpsest.alignment.smith_waterman import smith_waterman
from palimpsest.alignment.gumbel import calibrate_gumbel, p_value


class TestAlignmentRecords:
    def test_roundtrip(self, tmp_path):
        records = [
            AlignmentRecord(
                query_id="text-a",
                query_start=10,
                query_end=20,
                target_id="text-b",
                target_start=15,
                target_end=25,
                score=5.0,
                p_value=0.001,
                method="semantic",
                strand="+",
                identity=0.85,
            ),
        ]
        path = tmp_path / "alignment.jsonl"
        write_alignment_records(path, records)
        loaded = read_alignment_records(path)
        assert len(loaded) == 1
        assert loaded[0].query_id == "text-a"
        assert loaded[0].score == 5.0
        assert loaded[0].identity == 0.85


class TestSmithWaterman:
    def test_identity_matrix(self):
        """A self-comparison should find a strong diagonal alignment."""
        n = 20
        matrix = np.eye(n, dtype=np.float32)
        records = smith_waterman(matrix, "a", "a", min_length=3)
        assert len(records) >= 1
        assert records[0].score > 0

    def test_no_similarity(self):
        """A zero matrix should produce no alignments."""
        matrix = np.zeros((10, 10), dtype=np.float32)
        records = smith_waterman(matrix, "a", "b")
        assert len(records) == 0

    def test_block_similarity(self):
        """A block of high similarity should be found."""
        matrix = np.zeros((20, 20), dtype=np.float32)
        # Insert a 5x5 block of high similarity at (5,8)
        matrix[5:10, 8:13] = 0.9
        records = smith_waterman(matrix, "a", "b", min_length=2)
        assert len(records) >= 1
        best = records[0]
        assert best.query_start >= 5
        assert best.target_start >= 8

    def test_asymmetric_matrix(self):
        """NxM matrices (non-square) should work."""
        matrix = np.random.default_rng(42).random((15, 30)).astype(np.float32) * 0.3
        # Add a strong signal
        matrix[3:8, 10:15] = 0.95
        records = smith_waterman(matrix, "short", "long", min_length=2)
        assert len(records) >= 1


class TestSmithWatermanNonOverlap:
    """C6a: extraction is non-overlapping (Waterman-Eggert style) and has no silent cap."""

    def test_shifted_diagonal_duplicate_is_rejected(self):
        """A 2-wide high-similarity diagonal offers a main path and a shifted path overlapping it on
        both axes; only one alignment should survive (the flood the old min(100,...) cap hid)."""
        n = 6
        matrix = np.zeros((n, n + 1), dtype=np.float32)
        for i in range(n):
            matrix[i, i] = 0.9
            matrix[i, i + 1] = 0.85
        records = smith_waterman(matrix, "a", "b", min_length=2)
        assert len(records) == 1
        # and no two records ever overlap >50% on both axes (the invariant, trivially here).
        for x in range(len(records)):
            for y in range(x + 1, len(records)):
                rx, ry = records[x], records[y]
                q_ov = max(0, min(rx.query_end, ry.query_end) - max(rx.query_start, ry.query_start))
                t_ov = max(0, min(rx.target_end, ry.target_end) - max(rx.target_start, ry.target_start))
                assert not (q_ov > 0 and t_ov > 0)

    def test_repeat_survives_overlap_on_a_single_axis(self):
        """One query range aligning to two disjoint target ranges (a repeat) overlaps only on the
        query axis, so both alignments must be kept."""
        matrix = np.zeros((4, 16), dtype=np.float32)
        matrix[0:4, 0:4] = np.eye(4) * 0.9
        matrix[0:4, 8:12] = np.eye(4) * 0.9
        records = smith_waterman(matrix, "a", "b", min_length=2)
        assert len(records) == 2
        targets = sorted(r.target_start for r in records)
        assert targets[0] < 4 and targets[1] >= 8  # two distinct target locations

    @staticmethod
    def _six_disjoint_blocks() -> np.ndarray:
        """Six 3x3 identity blocks on the ANTI-diagonal — disjoint in both rows and cols, so no single
        monotonic path can chain them (a main-diagonal layout would merge into one local alignment)."""
        matrix = np.zeros((30, 30), dtype=np.float32)
        for k in range(6):
            r = k * 5
            c = (5 - k) * 5
            matrix[r:r + 3, c:c + 3] = np.eye(3) * 0.9
        return matrix

    def test_exhaustive_by_default_no_silent_cap(self):
        """Six disjoint blocks are all returned by default (no arbitrary result cap)."""
        records = smith_waterman(self._six_disjoint_blocks(), "a", "b", min_length=2)
        assert len(records) == 6

    def test_max_alignments_caps_and_warns(self, caplog):
        """An explicit ceiling truncates, but the truncation is logged (never silent)."""
        import logging

        with caplog.at_level(logging.WARNING, logger="palimpsest.alignment.smith_waterman"):
            records = smith_waterman(
                self._six_disjoint_blocks(), "a", "b", min_length=2, max_alignments=2
            )
        assert len(records) == 2
        assert any("max_alignments" in r.message for r in caplog.records)


class TestGumbel:
    def test_calibration(self):
        """Gumbel calibration should return reasonable parameters."""
        rng = np.random.default_rng(42)
        matrix = rng.random((30, 30)).astype(np.float32) * 0.3
        mu, beta = calibrate_gumbel(matrix, n_shuffles=50)
        assert beta > 0
        assert mu > -100

    def test_p_value_monotonic(self):
        """Higher scores should have lower p-values."""
        mu, beta = 2.0, 1.0
        p_low = p_value(5.0, mu, beta)
        p_high = p_value(1.0, mu, beta)
        assert p_low < p_high

    def test_p_value_range(self):
        """p-values should be in [0, 1]."""
        for score in [0.0, 1.0, 5.0, 10.0, 100.0]:
            p = p_value(score, 2.0, 1.0)
            assert 0.0 <= p <= 1.0
