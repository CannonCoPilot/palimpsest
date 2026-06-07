"""Tests for the ingestion pipeline: extraction, normalization, segmentation."""

from pathlib import Path

import pytest

from palimpsest.ingest.extractor import extract_text
from palimpsest.ingest.normalizer import compute_sha256, count_characters, count_words, normalize
from palimpsest.ingest.segmenter import segment_paragraphs, segment_sections


class TestExtractor:
    def test_extract_txt(self, pp_ch1_txt: Path):
        text = extract_text(pp_ch1_txt)
        assert len(text) > 100
        assert "Mr. Bennet" in text

    def test_extract_unsupported_raises(self, tmp_path: Path):
        bad = tmp_path / "test.xyz"
        bad.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported"):
            extract_text(bad)


class TestNormalizer:
    def test_normalize_idempotent(self):
        text = 'He said "hello"  to   her.'
        n1 = normalize(text)
        n2 = normalize(n1)
        assert n1 == n2

    def test_curly_quotes_to_straight(self):
        text = "“Hello” she said"
        result = normalize(text)
        assert '"Hello"' in result

    def test_whitespace_collapse(self):
        text = "word1   word2\t\tword3"
        result = normalize(text)
        assert result == "word1 word2 word3"

    def test_triple_newlines_collapsed(self):
        text = "para1\n\n\npara2"
        result = normalize(text)
        assert result == "para1\n\npara2"

    def test_sha256_deterministic(self):
        text = "test string"
        h1 = compute_sha256(text)
        h2 = compute_sha256(text)
        assert h1 == h2
        assert len(h1) == 64

    def test_count_words(self):
        assert count_words("one two three") == 3

    def test_count_characters(self):
        assert count_characters("hello") == 5

    def test_normalize_pp_chapter(self, pp_ch1_txt: Path):
        raw = pp_ch1_txt.read_text()
        normalized = normalize(raw)
        assert "Mr. Bennet" in normalized
        assert len(normalized) > 100


class TestSegmenter:
    def test_paragraph_offsets_accurate(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        paras = segment_paragraphs(text)
        assert len(paras) == 3
        for p in paras:
            assert text[p.start : p.end].strip() == p.text

    def test_paragraph_offsets_with_triple_newlines(self):
        text = "Para one.\n\n\nPara two."
        paras = segment_paragraphs(text)
        assert len(paras) == 2
        for p in paras:
            assert text[p.start : p.end].strip() == p.text

    def test_paragraph_count_pp(self, pp_ch1_txt: Path):
        text = normalize(pp_ch1_txt.read_text())
        paras = segment_paragraphs(text)
        assert len(paras) >= 5

    def test_section_detection_chapter(self):
        text = "CHAPTER I.\n\nSome text here.\n\nCHAPTER II.\n\nMore text."
        sections = segment_sections(text)
        assert len(sections) >= 2
        assert "CHAPTER" in sections[0].text

    def test_section_detection_allcaps(self):
        text = "Regular text.\n\nTHE GREAT BEGINNING\n\nMore text."
        sections = segment_sections(text)
        assert len(sections) >= 1
