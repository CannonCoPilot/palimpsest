"""Tests for the ingestion pipeline: extraction, normalization, segmentation."""

from pathlib import Path

import pytest

from palimpsest.ingest.extractor import extract_text
from palimpsest.ingest.normalizer import compute_sha256, count_characters, count_words, normalize
from palimpsest.ingest.segmenter import (
    Segment,
    _validate_segments,
    segment_paragraphs,
    segment_sections,
    segment_sentences,
)


def _assert_segment_contract(segments: list[Segment], text: str) -> None:
    """Assert the segmentation contract holds for a producer's output."""
    n = len(text)
    prev_end = 0
    for i, seg in enumerate(segments):
        assert seg.index == i, f"index {seg.index} out of sequence at {i}"
        assert 0 <= seg.start < seg.end <= n, f"segment {i} span ({seg.start}, {seg.end}) oob/{n}"
        assert seg.start >= prev_end, f"segment {i} overlaps prior end {prev_end}"
        assert seg.text == text[seg.start : seg.end].strip(), f"segment {i} text not anchored"
        prev_end = seg.end


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

    def test_extract_html(self, tmp_path: Path):
        html = tmp_path / "test.html"
        html.write_text("<html><body><h1>Title</h1><p>Hello world.</p><script>var x=1;</script></body></html>")
        text = extract_text(html)
        assert "Hello world" in text
        assert "var x" not in text

    def test_extract_markdown(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("# Heading\n\nSome **bold** text with a [link](http://example.com).\n\n- item one\n- item two\n")
        text = extract_text(md)
        assert "bold" in text
        assert "**" not in text
        assert "http://example.com" not in text


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

    def test_se_colophon_stripped(self):
        text = (
            "The story ends here.\n\n"
            "This particular edition is based on a transcription produced for Project Gutenberg."
        )
        result = normalize(text)
        assert "The story ends here." in result
        assert "This particular edition is based on" not in result

    def test_particular_edition_prose_not_stripped(self):
        # W8: "This particular edition" in narrative prose must survive — only the
        # colophon's "is based on" phrasing should trigger stripping.
        text = (
            "He examined the rare book.\n"
            "This particular edition fascinated the collector beyond measure."
        )
        result = normalize(text)
        assert "This particular edition fascinated the collector" in result


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

    def test_paragraph_contract_holds(self):
        # Leading spaces + triple newlines stress the offset/anchor invariant.
        text = "  First paragraph.\n\n\nSecond paragraph here.\n\nThird."
        _assert_segment_contract(segment_paragraphs(text), text)

    def test_section_contract_holds(self):
        text = "CHAPTER I.\n\nSome text.\n\nTHE GREAT BEGINNING\n\nCHAPTER II.\n\nMore."
        _assert_segment_contract(segment_sections(text), text)

    def test_sentence_contract_holds(self):
        text = "First sentence. Second sentence here.\n\nA new paragraph's sentence."
        _assert_segment_contract(segment_sentences(text), text)

    def test_validate_segments_rejects_out_of_bounds(self):
        text = "abcdefghij"
        with pytest.raises(ValueError, match="out of bounds"):
            _validate_segments([Segment("x", 0, 0, 12, "abcde")], text)

    def test_validate_segments_rejects_overlap(self):
        text = "abcdefghij"
        bad = [Segment("x", 0, 0, 5, "abcde"), Segment("x", 1, 3, 8, "defgh")]
        with pytest.raises(ValueError, match="ordered and disjoint"):
            _validate_segments(bad, text)

    def test_validate_segments_rejects_bad_index(self):
        text = "abcdefghij"
        with pytest.raises(ValueError, match="out of sequence"):
            _validate_segments([Segment("x", 5, 0, 5, "abcde")], text)

    def test_validate_segments_rejects_unanchored_text(self):
        text = "abcdefghij"
        with pytest.raises(ValueError, match="not anchored"):
            _validate_segments([Segment("x", 0, 0, 5, "WRONG")], text)
