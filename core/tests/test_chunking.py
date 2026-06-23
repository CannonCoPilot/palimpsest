"""Tests for the chunking + embedding stage (modes, strict config, fail-loud behaviour)."""

from __future__ import annotations

import pytest

from palimpsest.tracks.chunking import (
    ChunkingConfig,
    build_word_positions,
    chunk_punctuation,
    chunk_slide,
    chunk_smart,
    chunk_text,
    chunk_verse,
    chunk_words,
    smart_unit_sizes,
)
from palimpsest.tracks.embedding import EmbeddingConfig


def _assert_offsets(text, chunks):
    for c in chunks:
        assert text[c["start"]:c["end"]] == c["text"], f"offset mismatch at chunk {c['index']}"
        assert c["words"] == c["text"].split()


class TestChunkingConfig:
    def test_word_requires_size(self):
        with pytest.raises(ValueError, match="requires 'size'"):
            ChunkingConfig(mode="word")

    def test_word_rejects_extraneous(self):
        with pytest.raises(ValueError, match="does not accept"):
            ChunkingConfig(mode="word", size=7, smart_unit="verse")

    def test_slide_must_be_even_and_min(self):
        with pytest.raises(ValueError, match="even"):
            ChunkingConfig(mode="slide", size=11)
        with pytest.raises(ValueError, match=">= 10"):
            ChunkingConfig(mode="slide", size=8)
        ChunkingConfig(mode="slide", size=10)  # ok

    def test_punctuation_requires_delimiters(self):
        with pytest.raises(ValueError, match="requires 'delimiters'"):
            ChunkingConfig(mode="punctuation")

    def test_punctuation_rejects_empty_delimiters(self):
        with pytest.raises(ValueError, match="non-empty"):
            ChunkingConfig(mode="punctuation", delimiters=())
        with pytest.raises(ValueError, match="non-empty"):
            ChunkingConfig(mode="punctuation", delimiters=("",))

    def test_verse_rejects_size(self):
        with pytest.raises(ValueError, match="does not accept 'size'"):
            ChunkingConfig(mode="verse", size=7)
        ChunkingConfig(mode="verse")  # ok

    def test_smart_requires_all_knobs(self):
        with pytest.raises(ValueError, match="requires"):
            ChunkingConfig(mode="smart", size=7, smart_unit="verse", grow_factor=2)
        ChunkingConfig(mode="smart", size=7, smart_unit="verse", grow_factor=2, remainder_ratio=0.6)

    def test_bad_mode(self):
        with pytest.raises(ValueError, match="chunk mode must be"):
            ChunkingConfig(mode="bogus")

    def test_remainder_ratio_bounds(self):
        with pytest.raises(ValueError, match="remainder_ratio"):
            ChunkingConfig(mode="smart", size=7, smart_unit="verse", grow_factor=2, remainder_ratio=1.5)


class TestWordMode:
    def test_offsets_and_count(self):
        text = "the quick brown fox jumps over the lazy dog and the cat"  # 12 words
        chunks = chunk_words(text, 4)
        _assert_offsets(text, chunks)
        assert len(chunks) == 3
        assert all(len(c["words"]) == 4 for c in chunks)

    def test_short_tail_kept(self):
        text = "one two three four"  # 4 words, size 5
        chunks = chunk_words(text, 5)
        assert len(chunks) == 1
        assert chunks[0]["words"] == ["one", "two", "three", "four"]

    def test_repeated_words_offsets(self):
        text = "the fox and the cat and the dog and the bird here"
        _assert_offsets(text, chunk_words(text, 3))


class TestSlideMode:
    def test_overlap_stride(self):
        text = " ".join(f"w{i}" for i in range(20))
        chunks = chunk_slide(text, 10)  # stride 5
        _assert_offsets(text, chunks)
        # windows start at words 0, 5, 10 (15 would only cover 5 words -> still emitted as tail)
        assert chunks[0]["words"][0] == "w0"
        assert chunks[1]["words"][0] == "w5"
        # consecutive windows overlap by half
        assert chunks[0]["words"][5] == chunks[1]["words"][0]


class TestPunctuationMode:
    def test_clause_split(self):
        text = "In the beginning, God created; the earth was void: darkness covered the deep."
        chunks = chunk_punctuation(text, (".", ",", ";", ":"))
        _assert_offsets(text, chunks)
        assert len(chunks) == 4
        assert chunks[0]["text"].startswith("In the beginning")

    def test_custom_delimiters(self):
        text = "a|b|c"
        chunks = chunk_punctuation(text, ("|",))
        assert [c["text"] for c in chunks] == ["a|", "b|", "c"]

    def test_multi_char_delimiters(self):
        # R4: delimiters are full strings, not single characters — each is regex-alternated, so a
        # multi-character delimiter like "::" or "||" splits as one unit.
        text = "alpha :: beta || gamma"
        chunks = chunk_punctuation(text, ("::", "||"))
        assert [c["text"] for c in chunks] == ["alpha ::", "beta ||", "gamma"]


class TestVerseMode:
    def test_spans_to_chunks(self):
        text = "alpha beta gamma delta epsilon zeta"
        spans = [(0, 16), (17, len(text))]  # "alpha beta gamma" | "delta epsilon zeta"
        chunks = chunk_verse(text, spans)
        _assert_offsets(text, chunks)
        assert chunks[0]["text"] == "alpha beta gamma"
        assert chunks[1]["text"] == "delta epsilon zeta"


class TestSmartMode:
    def test_unit_sizes_grows_to_avoid_tiny_remainder(self):
        assert smart_unit_sizes(20, 7, 2, 0.6) == [7, 7, 6]
        assert smart_unit_sizes(22, 7, 2, 0.6) == [8, 8, 6]
        assert smart_unit_sizes(8, 7, 2, 0.6) == [8]   # absorbs the 1-word remainder
        assert smart_unit_sizes(5, 7, 2, 0.6) == [5]   # unit smaller than target

    def test_respects_unit_boundaries(self):
        text = " ".join(f"w{i}" for i in range(30))
        # two paragraph units of 15 words each
        positions = build_word_positions(text)[1]
        mid = positions[15][0]
        units = [(0, positions[14][1]), (mid, len(text))]
        chunks = chunk_smart(text, 7, units, 2, 0.6)
        _assert_offsets(text, chunks)
        # no chunk straddles the boundary between the two units
        for c in chunks:
            assert not (c["start"] < positions[14][1] < c["end"])


class TestDispatchFailLoud:
    def test_verse_without_spans_raises(self):
        with pytest.raises(ValueError, match="verse_spans"):
            chunk_text("a b c", ChunkingConfig(mode="verse"))

    def test_smart_without_units_raises(self):
        cfg = ChunkingConfig(mode="smart", size=7, smart_unit="sentence", grow_factor=2, remainder_ratio=0.6)
        with pytest.raises(ValueError, match="sentence_spans"):
            chunk_text("a b c d e f g h", cfg)


class TestEmbeddingConfig:
    def test_rejects_bad_provider(self):
        with pytest.raises(ValueError, match="provider"):
            EmbeddingConfig(provider="bogus", endpoint="http://x", model="m", batch_size=8)

    def test_rejects_empty_endpoint(self):
        with pytest.raises(ValueError, match="endpoint"):
            EmbeddingConfig(provider="ollama", endpoint="", model="m", batch_size=8)

    def test_rejects_bad_batch(self):
        with pytest.raises(ValueError, match="batch_size"):
            EmbeddingConfig(provider="ollama", endpoint="http://x", model="m", batch_size=0)

    def test_provenance(self):
        c = EmbeddingConfig(provider="mlx", endpoint="http://x", model="m", batch_size=32)
        assert c.provenance() == {
            "provider": "mlx", "endpoint": "http://x", "model": "m", "batch_size": 32,
        }
