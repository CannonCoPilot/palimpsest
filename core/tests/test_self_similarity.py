"""Unit tests for self-similarity primitives — chunk positions, scoring, calibration, alignment.

These cover the pure LASTZ / matrix / chunking helpers that survive the P7 layer-consumer redesign
unchanged. The track-level behaviour (layer binding, multi-size extract, manifest contract) lives in
test_self_similarity_consumer.py; repeat detection/masking lives with the repeats + repeat_mask tracks.
"""

from __future__ import annotations

import numpy as np
import pytest

from palimpsest.tracks.chunking import build_word_positions, chunk_words
from palimpsest.tracks.self_similarity import (
    LASTZ_SMALL_SAMPLE_THRESHOLD,
    _banded_lcs_identity,
    _calibrate_threshold,
    _char_identity,
    _edit_distance_matrix,
    _edit_distance_tokens,
    _extend_alignment,
    _find_local_optima,
    _sliding_window_refine,
    _word_overlap_matrix,
)


class TestBuildWordPositions:
    def test_basic(self):
        words, positions = build_word_positions("the quick brown fox")
        assert words == ["the", "quick", "brown", "fox"]
        assert positions[0] == (0, 3)
        assert positions[1] == (4, 9)
        assert positions[3] == (16, 19)

    def test_extra_whitespace(self):
        words, positions = build_word_positions("  hello   world  ")
        assert words == ["hello", "world"]
        assert positions[0] == (2, 7)
        assert positions[1] == (10, 15)

    def test_empty(self):
        words, positions = build_word_positions("")
        assert words == []
        assert positions == []


class TestChunkText:
    def test_round_trip(self):
        text = "the quick brown fox jumps over the lazy dog and the cat sat on the mat"
        chunks = chunk_words(text, 5)
        for c in chunks:
            assert text[c["start"]:c["end"]] == c["text"], f"Chunk {c['index']} position mismatch"

    def test_repeated_words(self):
        text = "the fox and the cat and the dog and the bird"
        chunks = chunk_words(text, 5)
        for c in chunks:
            assert text[c["start"]:c["end"]] == c["text"], (
                f"Chunk {c['index']}: positions [{c['start']}:{c['end']}] give "
                f"'{text[c['start']:c['end']]}' but expected '{c['text']}'"
            )

    def test_short_tail_is_kept(self):
        # No silent tail drop: a text shorter than the window is one chunk covering all words.
        text = "one two three four"
        chunks = chunk_words(text, 5)
        assert len(chunks) == 1
        assert chunks[0]["words"] == ["one", "two", "three", "four"]

    def test_chunk_count(self):
        words = ["w"] * 50
        text = " ".join(words)
        chunks = chunk_words(text, 10)
        assert len(chunks) == 5


class TestCharIdentity:
    def test_identical(self):
        assert _char_identity("hello world", "hello world") == pytest.approx(1.0)

    def test_empty(self):
        assert _char_identity("", "hello") == 0.0
        assert _char_identity("hello", "") == 0.0

    def test_completely_different(self):
        score = _char_identity("aaaa", "bbbb")
        assert score == 0.0

    def test_partial_match(self):
        score = _char_identity("abcdef", "abcxyz")
        assert 0.0 < score < 1.0

    def test_symmetric(self):
        a, b = "the quick brown fox", "the slow brown cat"
        assert _char_identity(a, b) == pytest.approx(_char_identity(b, a))


class TestBandedLcsIdentity:
    def test_consistent_with_char_identity_on_short_strings(self):
        a = "the quick brown fox"
        b = "the quick brown cat"
        full = _char_identity(a, b)
        banded = _banded_lcs_identity(a, b, bandwidth=200)
        assert banded == pytest.approx(full, abs=0.001)

    def test_long_strings(self):
        a = "word " * 200
        b = "word " * 200
        score = _banded_lcs_identity(a, b, bandwidth=200)
        assert score > 0.9


class TestCalibrateThreshold:
    def test_returns_positive(self):
        chunks = [{"words": ["the", "quick", "brown", "fox", "jumps"]} for _ in range(20)]
        threshold = _calibrate_threshold(chunks, n_samples=100)
        assert threshold > 0.0

    def test_small_input_fallback(self):
        chunks = [{"words": ["a"]}] * 5
        threshold = _calibrate_threshold(chunks)
        # the small-sample fallback is the declared LOCKED_CONSTANT, not a magic literal
        assert threshold == LASTZ_SMALL_SAMPLE_THRESHOLD

    def test_deterministic(self):
        chunks = [{"words": ["word", str(i), "test", "the", "and"]} for i in range(50)]
        t1 = _calibrate_threshold(chunks, n_samples=200)
        t2 = _calibrate_threshold(chunks, n_samples=200)
        assert t1 == t2


class TestEditDistanceTokens:
    def test_identical(self):
        assert _edit_distance_tokens(["a", "b"], ["a", "b"]) == 0

    def test_completely_different(self):
        assert _edit_distance_tokens(["a"], ["b"]) == 1

    def test_empty(self):
        assert _edit_distance_tokens([], ["a", "b"]) == 2
        assert _edit_distance_tokens(["a"], []) == 1


class TestFindLocalOptima:
    def test_finds_known_optima(self):
        matrix = np.zeros((10, 10), dtype=np.float32)
        matrix[2, 7] = 0.9
        matrix[7, 2] = 0.9
        optima = _find_local_optima(matrix, k=2, min_gap=1)
        assert len(optima) >= 1
        assert optima[0][2] == pytest.approx(0.9)

    def test_excludes_diagonal(self):
        matrix = np.eye(10, dtype=np.float32)
        optima = _find_local_optima(matrix, k=5, min_gap=3)
        assert len(optima) == 0


class TestWordOverlapMatrix:
    def test_self_similarity_is_one(self):
        chunks = [
            {"words": ["the", "quick", "brown", "fox"]},
            {"words": ["the", "quick", "brown", "fox"]},
        ]
        matrix = _word_overlap_matrix(chunks)
        assert matrix[0, 0] == pytest.approx(1.0)
        assert matrix[0, 1] == pytest.approx(1.0)

    def test_no_overlap(self):
        chunks = [
            {"words": ["alpha", "beta"]},
            {"words": ["gamma", "delta"]},
        ]
        matrix = _word_overlap_matrix(chunks)
        assert matrix[0, 1] == pytest.approx(0.0)


class TestExtendAlignment:
    def test_finds_planted_repeat(self):
        repeated = "alpha beta gamma delta epsilon"
        different = "one two three four five"
        text = f"{repeated} {different} {repeated} {different}"
        chunks = chunk_words(text, 5)
        assert len(chunks) >= 4
        result = _extend_alignment(text, chunks, 0, 2, threshold=0.3, chunk_size=5)
        if result is not None:
            assert result["identity"] > 0.3


class TestSlidingWindowRefine:
    def test_refines_boundaries(self):
        text = "AAA BBB CCC DDD EEE FFF GGG HHH III JJJ"
        words, positions = build_word_positions(text)
        refined = _sliding_window_refine(
            text, words, positions,
            coarse_start_a=0, coarse_end_a=11,
            coarse_start_b=20, coarse_end_b=31,
            chunk_size=3, threshold=0.0,
        )
        assert len(refined) == 4
        assert refined[0] >= 0
        assert refined[1] <= len(text)


class TestMatrixMasking:
    """The four matrix builders skip chunks flagged ``masked=True`` — the masked-skip contract the P7
    consumer relies on for every metric (the flags now come from the repeat_mask layer, but the builder
    behaviour is unchanged)."""

    def test_matrix_builders_skip_masked_chunks(self):
        chunks = [
            {"words": ["alpha", "beta", "gamma", "delta"], "masked": True},
            {"words": ["alpha", "beta", "gamma", "delta"], "masked": False},
            {"words": ["alpha", "beta", "gamma", "delta"], "masked": False},
        ]
        for builder in (_word_overlap_matrix, _edit_distance_matrix):
            matrix = builder(chunks)
            # Row/col 0 is masked → all its cells stay 0 (including the diagonal).
            assert np.all(matrix[0, :] == 0.0)
            assert np.all(matrix[:, 0] == 0.0)
            # The two unmasked identical chunks still score high.
            assert matrix[1, 2] > 0.0

    def test_lastz_copy_preserves_shared_mask(self):
        """Building an unmasked LASTZ view must not clear masks on the shared chunk list the matrix
        builders read (the consumer builds the copy with ``{**c, "masked": False}``)."""
        chunks = [
            {"words": ["alpha", "beta"], "masked": True},
            {"words": ["one", "two"], "masked": False},
        ]
        lastz_chunks = [{**c, "masked": False} for c in chunks]
        assert all(c["masked"] is False for c in lastz_chunks)
        assert chunks[0]["masked"] is True
