"""Unit tests for self-similarity pipeline — chunk positions, scoring, calibration, alignment."""

from __future__ import annotations

import numpy as np
import pytest

from palimpsest.tracks.self_similarity import (
    METRICS,
    SelfSimilarityTrack,
    _build_word_positions,
    _chunk_text,
    _char_identity,
    _banded_lcs_identity,
    _calibrate_threshold,
    _content_tokens,
    _edit_distance_tokens,
    _edit_distance_matrix,
    _find_exact_repeats,
    _find_local_optima,
    _extend_alignment,
    _mask_repeats,
    _word_overlap_matrix,
    _lastz_align,
    _sliding_window_refine,
    _zero_layout_masked_chunks,
)


class TestBuildWordPositions:
    def test_basic(self):
        words, positions = _build_word_positions("the quick brown fox")
        assert words == ["the", "quick", "brown", "fox"]
        assert positions[0] == (0, 3)
        assert positions[1] == (4, 9)
        assert positions[3] == (16, 19)

    def test_extra_whitespace(self):
        words, positions = _build_word_positions("  hello   world  ")
        assert words == ["hello", "world"]
        assert positions[0] == (2, 7)
        assert positions[1] == (10, 15)

    def test_empty(self):
        words, positions = _build_word_positions("")
        assert words == []
        assert positions == []


class TestChunkText:
    def test_round_trip(self):
        text = "the quick brown fox jumps over the lazy dog and the cat sat on the mat"
        chunks = _chunk_text(text, 5)
        for c in chunks:
            assert text[c["start"]:c["end"]] == c["text"], f"Chunk {c['index']} position mismatch"

    def test_repeated_words(self):
        text = "the fox and the cat and the dog and the bird"
        chunks = _chunk_text(text, 5)
        for c in chunks:
            assert text[c["start"]:c["end"]] == c["text"], (
                f"Chunk {c['index']}: positions [{c['start']}:{c['end']}] give "
                f"'{text[c['start']:c['end']]}' but expected '{c['text']}'"
            )

    def test_minimum_chunk_size(self):
        text = "one two three four"
        chunks = _chunk_text(text, 5)
        assert len(chunks) == 0

    def test_chunk_count(self):
        words = ["w"] * 50
        text = " ".join(words)
        chunks = _chunk_text(text, 10)
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
        assert threshold == 0.3

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
        chunks = _chunk_text(text, 5)
        assert len(chunks) >= 4
        result = _extend_alignment(text, chunks, 0, 2, threshold=0.3, chunk_size=5)
        if result is not None:
            assert result["identity"] > 0.3


class TestSlidingWindowRefine:
    def test_refines_boundaries(self):
        text = "AAA BBB CCC DDD EEE FFF GGG HHH III JJJ"
        words, positions = _build_word_positions(text)
        refined = _sliding_window_refine(
            text, words, positions,
            coarse_start_a=0, coarse_end_a=11,
            coarse_start_b=20, coarse_end_b=31,
            chunk_size=3, threshold=0.0,
        )
        assert len(refined) == 4
        assert refined[0] >= 0
        assert refined[1] <= len(text)


class TestRepeatMasking:
    """Covers the repeat-masking subsystem (previously untested — audit E-NEW2)."""

    def _repeat_text(self) -> str:
        phrase = "alpha beta gamma delta epsilon"
        fillers = ["one two three four five", "six seven eight nine ten",
                   "red green blue cyan gold", "north south east west center"]
        parts = []
        for f in fillers:
            parts.append(phrase)
            parts.append(f)
        return " ".join(parts)

    def test_find_exact_repeats_detects_phrase(self):
        text = self._repeat_text()
        chunks = _chunk_text(text, 5)
        repeats = _find_exact_repeats(text, chunks, min_words=3, min_occurrences=3)
        assert "alpha beta gamma delta epsilon" in repeats

    def test_find_exact_repeats_ignores_unique_phrases(self):
        text = "alpha beta gamma one two three four five six seven eight nine ten"
        chunks = _chunk_text(text, 5)
        repeats = _find_exact_repeats(text, chunks, min_words=3, min_occurrences=3)
        assert repeats == set()

    def test_mask_repeats_marks_dominated_chunks(self):
        text = self._repeat_text()
        chunks = _chunk_text(text, 5)
        repeats = _find_exact_repeats(text, chunks, min_words=3, min_occurrences=3)
        _mask_repeats(chunks, repeats)
        # The phrase-only chunks (every other chunk) must be masked.
        masked_texts = {c["text"] for c in chunks if c.get("masked")}
        assert any("alpha beta gamma delta epsilon" in t for t in masked_texts)
        # At least one filler chunk must remain unmasked.
        assert any(not c.get("masked") for c in chunks)

    def test_mask_repeats_empty_set_unmasks_all(self):
        chunks = _chunk_text("one two three four five six seven eight nine ten", 5)
        _mask_repeats(chunks, set())
        assert all(c["masked"] is False for c in chunks)

    def test_matrix_builders_skip_masked_chunks(self):
        """E3 contract: masked chunks must produce zero matrix cells. The extract
        loop relies on this holding for every metric, not just the first."""
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
        """E3 regression: building an unmasked LASTZ view must not clear masks on
        the shared per-chunk-size cache that later metrics reuse."""
        cached_chunks = [
            {"words": ["alpha", "beta"], "masked": True},
            {"words": ["one", "two"], "masked": False},
        ]
        lastz_chunks = [{**c, "masked": False} for c in cached_chunks]
        assert all(c["masked"] is False for c in lastz_chunks)
        # The shared cache is untouched — metric #2 will still see the mask.
        assert cached_chunks[0]["masked"] is True


class TestMetricSelection:
    """Covers E1 subset-compute: per-metric checkboxes drive which metrics run."""

    def test_default_selects_all_metrics(self):
        track = SelfSimilarityTrack()
        assert track._selected_metrics == list(METRICS)

    def test_set_params_narrows_selection(self):
        track = SelfSimilarityTrack()
        track.set_params({"metrics": ["cosine", "edit_distance"]})
        assert track._selected_metrics == ["cosine", "edit_distance"]

    def test_invalid_metrics_filtered_out(self):
        track = SelfSimilarityTrack()
        track.set_params({"metrics": ["bogus", "jaccard"]})
        assert track._selected_metrics == ["jaccard"]

    def test_all_invalid_metrics_leaves_selection_unchanged(self):
        track = SelfSimilarityTrack()
        track.set_params({"metrics": ["nonsense"]})
        assert track._selected_metrics == list(METRICS)


class TestPerMetricChunkSize:
    """Covers E-NEW1 consumer side: per-metric chunk sizes resolve correctly."""

    def test_shared_chunk_size_applies_to_all(self):
        track = SelfSimilarityTrack()
        track.set_params({"chunk_size": 12})
        assert track._chunk_size_for("cosine") == 12
        assert track._chunk_size_for("jaccard") == 12

    def test_per_metric_override_takes_precedence(self):
        track = SelfSimilarityTrack()
        track.set_params({"chunk_size": 12, "chunk_size_cosine": 20})
        assert track._chunk_size_for("cosine") == 20
        assert track._chunk_size_for("jaccard") == 12

    def test_chunk_size_clamped_to_bounds(self):
        track = SelfSimilarityTrack()
        track.set_params({"chunk_size_cosine": 999})
        assert 5 <= track._chunk_size_for("cosine") <= 25


class TestLayoutMasking:
    """Step-4 layout masks (front matter, endnotes …) must drop out of the
    self-similarity matrix and alignments — separate from repeat masking, which
    only touches two metrics and is cleared before LASTZ scores final identity."""

    def test_zero_layout_masked_chunks_clears_row_and_col(self):
        matrix = np.ones((3, 3), dtype=np.float32)
        chunks = [
            {"layout_masked": False},
            {"layout_masked": True},
            {"layout_masked": False},
        ]
        _zero_layout_masked_chunks(matrix, chunks)
        # Masked chunk's entire row and column (incl. diagonal) are zeroed.
        assert np.all(matrix[1, :] == 0.0)
        assert np.all(matrix[:, 1] == 0.0)
        # Unmasked pair is untouched.
        assert matrix[0, 2] == pytest.approx(1.0)
        assert matrix[2, 0] == pytest.approx(1.0)
        assert matrix[0, 0] == pytest.approx(1.0)

    def test_zero_layout_masked_chunks_noop_when_none_masked(self):
        matrix = np.ones((2, 2), dtype=np.float32)
        _zero_layout_masked_chunks(matrix, [{}, {}])
        assert np.all(matrix == 1.0)

    def test_extend_alignment_halts_at_layout_masked_chunk(self):
        # Six identical chunks — char identity is 1.0 everywhere, so the only
        # thing that can stop forward extension is the layout mask.
        text = " ".join(["rep"] * 30)
        chunks = _chunk_text(text, 5)
        assert len(chunks) == 6

        # Baseline: extension reaches chunk index 2 along the (1,1) diagonal.
        baseline = _extend_alignment(text, chunks, 0, 3, threshold=0.3, chunk_size=5)
        assert baseline is not None
        assert baseline["chunk_end_a"] == 2

        # Mask chunk 2 → forward extension must stop one chunk earlier.
        chunks[2]["layout_masked"] = True
        masked = _extend_alignment(text, chunks, 0, 3, threshold=0.3, chunk_size=5)
        assert masked is not None
        assert masked["chunk_end_a"] == 1
