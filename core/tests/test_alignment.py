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
