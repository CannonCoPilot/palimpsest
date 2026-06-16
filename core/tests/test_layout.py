"""Tests for layout sections + the deepest-section-wins masking rule."""

from palimpsest.layout import (
    DEFAULT_MASK_BY_TYPE,
    LayoutSection,
    detect_layout_sections,
    effective_mask,
    masked_intervals,
    range_is_masked,
)


def _sec(id_, type_, start, end, masked=None):
    return LayoutSection(id=id_, type=type_, start=start, end=end, masked=masked)


def test_basic_front_matter_masked_chapter_not():
    sections = [_sec("a", "front_matter", 0, 100), _sec("b", "chapter", 100, 500)]
    assert masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 500) == [(0, 100)]


def test_chapter_nested_in_book_keeps_prose_unmasked():
    # book masked by default; the chapter inside it is the analyzable core.
    sections = [_sec("book", "book", 0, 1000), _sec("ch", "chapter", 100, 900)]
    assert masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 1000) == [(0, 100), (900, 1000)]


def test_footnote_nested_in_chapter_is_remasked():
    sections = [_sec("ch", "chapter", 0, 1000), _sec("fn", "footnotes", 400, 450)]
    assert masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 1000) == [(400, 450)]


def test_per_section_override_beats_type_default():
    # chapter type defaults to unmasked, but this instance is overridden to masked.
    sections = [_sec("ch", "chapter", 0, 100, masked=True)]
    assert masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 100) == [(0, 100)]


def test_uncovered_text_is_unmasked():
    sections = [_sec("tp", "title_page", 0, 50)]
    assert masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 200) == [(0, 50)]


def test_effective_mask_inherits_then_overrides():
    assert effective_mask(_sec("a", "chapter", 0, 1), DEFAULT_MASK_BY_TYPE) is False
    assert effective_mask(_sec("a", "endnotes", 0, 1), DEFAULT_MASK_BY_TYPE) is True
    assert effective_mask(_sec("a", "chapter", 0, 1, masked=True), DEFAULT_MASK_BY_TYPE) is True


def test_range_is_masked_uses_midpoint():
    intervals = [(0, 100), (400, 450)]
    assert range_is_masked(intervals, 10, 20) is True
    assert range_is_masked(intervals, 150, 160) is False
    assert range_is_masked(intervals, 420, 440) is True


def test_detect_front_matter_chapters_endnotes():
    boundaries = [(0, 10, "Half Title"), (200, 210, "Chapter 1"), (500, 510, "Chapter 2")]
    sections = detect_layout_sections(boundaries, text_len=800, endnote_separator=700)
    by_type = [(s.type, s.start, s.end) for s in sections]
    assert ("front_matter", 0, 200) in by_type
    assert ("chapter", 200, 500) in by_type
    assert ("chapter", 500, 700) in by_type
    assert ("endnotes", 700, 800) in by_type


def test_detect_handles_spaceless_and_part_headings():
    # Real EPUBs emit "Chapter1" (no space) and "Part 1" as a volume-level division.
    boundaries = [
        (0, 4, "Emma"), (10, 16, "Part 1"), (20, 28, "Chapter1"), (200, 208, "Chapter2"),
    ]
    sections = detect_layout_sections(boundaries, text_len=400)
    types = [s.type for s in sections]
    assert "volume" in types  # "Part 1"
    assert types.count("chapter") == 2  # Chapter1, Chapter2 despite missing space


def test_detect_book_contains_chapters_via_nesting():
    boundaries = [
        (0, 6, "Book I"), (100, 110, "Chapter 1"), (300, 310, "Chapter 2"),
        (500, 506, "Book II"), (600, 610, "Chapter 1"),
    ]
    sections = detect_layout_sections(boundaries, text_len=800)
    book1 = next(s for s in sections if s.type == "book" and s.start == 0)
    assert book1.end == 500
    ch1 = next(s for s in sections if s.type == "chapter" and s.start == 100)
    assert ch1.parent_id == book1.id
    # Book title regions masked, chapter prose analyzed.
    assert masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 800) == [(0, 100), (500, 600)]
