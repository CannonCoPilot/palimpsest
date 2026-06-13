"""Tests for narrative alphabet alignment."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from palimpsest.alignment.alphabet_align import align_alphabets


class TestAlignAlphabets:
    @patch("palimpsest.alignment.alphabet_align.load_alphabet_sequence")
    def test_identical_sequences(self, mock_load):
        mock_load.side_effect = ["ABCABC", "ABCABC"]
        proj_a = MagicMock()
        proj_a.metadata.id = "test_a"
        proj_b = MagicMock()
        proj_b.metadata.id = "test_b"

        records = align_alphabets(proj_a, proj_b, min_length=2)
        assert len(records) > 0
        assert all(r.method == "alphabet" for r in records)
        assert records[0].score > 0

    @patch("palimpsest.alignment.alphabet_align.load_alphabet_sequence")
    def test_completely_different(self, mock_load):
        mock_load.side_effect = ["AAAA", "BBBB"]
        proj_a = MagicMock()
        proj_a.metadata.id = "a"
        proj_b = MagicMock()
        proj_b.metadata.id = "b"

        records = align_alphabets(proj_a, proj_b, min_length=2)
        # No matches → no alignments above threshold
        assert len(records) == 0

    @patch("palimpsest.alignment.alphabet_align.load_alphabet_sequence")
    def test_partial_match(self, mock_load):
        mock_load.side_effect = ["XXABCXX", "YYABCYY"]
        proj_a = MagicMock()
        proj_a.metadata.id = "a"
        proj_b = MagicMock()
        proj_b.metadata.id = "b"

        records = align_alphabets(proj_a, proj_b, min_length=2)
        assert len(records) > 0
        # The aligned region should be around the ABC portion
        best = records[0]
        assert best.query_start >= 1
        assert best.target_start >= 1
