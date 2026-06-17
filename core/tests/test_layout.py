"""Tests for layout sections + the deepest-section-wins masking rule."""

from palimpsest.layout import (
    DEFAULT_MASK_BY_TYPE,
    LayoutSection,
    detect_layout_sections,
    detect_verse_regions,
    effective_mask,
    masked_intervals,
    range_is_masked,
)


_SCRIPTURE = (
    "1 In the beginning God created the heaven and the earth.\n\n"
    "2 And the earth was without form, and void; and darkness was on the deep.\n\n"
    "3 And God said, Let there be light: and there was light.\n\n"
    "4 And God saw the light, that it was good: and divided light from darkness.\n\n"
    "5 And God called the light Day, and the darkness he called Night.\n\n"
    "6 And God said, Let there be a firmament in the midst of the waters.\n\n"
)


def _sec(id_, type_, start, end, masked=None):
    return LayoutSection(id=id_, type=type_, start=start, end=end, masked=masked)


def test_basic_front_matter_masked_chapter_not():
    sections = [_sec("a", "front_matter", 0, 100), _sec("b", "chapter", 100, 500)]
    assert masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 500) == [(0, 100)]


def test_chapter_nested_in_book_keeps_prose_unmasked():
    # New model: book/chapter are analyzable text (mask=no); only a carved header
    # masks the title label that sits at the book's start.
    sections = [
        _sec("book", "book", 0, 1000),
        _sec("ch", "chapter", 100, 900),
        _sec("hd", "header", 0, 8),
    ]
    assert masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 1000) == [(0, 8)]


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
    # The chapter element starts after its heading line; the heading is a header window.
    assert ("chapter", 210, 500) in by_type
    assert ("header", 200, 210) in by_type
    assert ("chapter", 510, 700) in by_type
    assert ("header", 500, 510) in by_type
    assert ("endnotes", 700, 800) in by_type


def test_detect_handles_spaceless_and_part_headings():
    # Real EPUBs emit "Chapter1" (no space) and "Part 1" as a volume-level division.
    boundaries = [
        (0, 4, "Emma"), (10, 16, "Part 1"), (20, 28, "Chapter1"), (200, 208, "Chapter2"),
    ]
    sections = detect_layout_sections(boundaries, text_len=400)
    types = [s.type for s in sections]
    assert "part" in types  # "Part 1"
    assert types.count("chapter") == 2  # Chapter1, Chapter2 despite missing space


def test_detect_book_contains_chapters_via_nesting():
    boundaries = [
        (0, 6, "Book I"), (100, 110, "Chapter 1"), (300, 310, "Chapter 2"),
        (500, 506, "Book II"), (600, 610, "Chapter 1"),
    ]
    sections = detect_layout_sections(boundaries, text_len=800)
    book1 = next(s for s in sections if s.type == "book" and s.start == 0)
    assert book1.end == 500  # extends to the next equal-level division (Book II)
    # Chapter starts after its carved heading ("Chapter 1" → header 100–110).
    ch1 = next(s for s in sections if s.type == "chapter" and s.start == 110)
    assert ch1.parent_id == book1.id
    # New model: book/chapter prose is analyzable; only the carved heading labels
    # ("Book I", "Chapter 1", ...) are masked windows.
    assert masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 800) == [
        (0, 6), (100, 110), (300, 310), (500, 506), (600, 610),
    ]


def test_chapterless_work_keeps_body_unmasked():
    # Regression for the epistolary-novel bug: a work with no chapter headings must
    # still get an analyzable body — only its front/back matter is masked.
    boundaries = [
        (0, 8, "Contents"),
        (40, 49, "A Preface"),
        (300, 340, "Letter one — part of the work, no heading match"),
        (9500, 9515, "Acknowledgments"),
    ]
    sections = detect_layout_sections(boundaries, text_len=10000)
    body = next(s for s in sections if s.type == "body")
    assert (body.start, body.end) == (300, 9500)
    mi = masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 10000)
    assert sum(b - a for a, b in mi) < 10000          # NOT masked end to end
    assert not range_is_masked(mi, 1000, 2000)        # the body prose is analyzable


def test_header_carved_from_chapter_heading():
    # The "Chapter I.—…" label is masked while the chapter prose stays analyzable.
    boundaries = [(0, 22, "Chapter I.—The salutation"), (2000, 2010, "Chapter II")]
    sections = detect_layout_sections(boundaries, text_len=4000)
    header = next(s for s in sections if s.type == "header" and s.start == 0)
    assert header.end == 22
    mi = masked_intervals(sections, DEFAULT_MASK_BY_TYPE, 4000)
    assert range_is_masked(mi, 0, 22)          # the heading label is masked
    assert not range_is_masked(mi, 500, 600)   # the chapter prose is not


def test_chapter_heading_split_into_header_and_metadata():
    # The heading line is excluded from the chapter span and becomes a header; the
    # chapter element carries the parsed number/title in metadata.
    boundaries = [(0, 26, "Chapter IV.—The Reckoning"), (2000, 2010, "Chapter V")]
    sections = detect_layout_sections(boundaries, text_len=4000)
    chapter = next(s for s in sections if s.type == "chapter" and s.start == 26)
    assert chapter.start == 26 and chapter.end == 2000
    assert chapter.metadata == {"number": "IV", "name": "The Reckoning"}
    assert chapter.label == "The Reckoning"  # heading line, not in the chapter span
    header = next(s for s in sections if s.type == "header" and s.start == 0)
    assert (header.start, header.end) == (0, 26)
    assert header.label == "Chapter IV.—The Reckoning"


def test_parse_chapter_heading_variants():
    from palimpsest.layout import _parse_chapter_heading
    assert _parse_chapter_heading("Chapter 5: The Reckoning") == {"number": "5", "name": "The Reckoning"}
    assert _parse_chapter_heading("Chapter X - The Reckoning") == {"number": "X", "name": "The Reckoning"}
    assert _parse_chapter_heading("Chapter VI.—Continuation.") == {"number": "VI", "name": "Continuation"}
    assert _parse_chapter_heading("Chapter 12") == {"number": "12"}
    assert _parse_chapter_heading("The Untitled") == {"name": "The Untitled"}


def test_elements_get_unique_names():
    boundaries = [(0, 10, "Chapter 1"), (1000, 1010, "Chapter 2"), (2000, 2010, "Chapter 3")]
    sections = detect_layout_sections(boundaries, text_len=3000)
    chapter_names = {s.name for s in sections if s.type == "chapter"}
    assert chapter_names == {"chapter_1", "chapter_2", "chapter_3"}
    all_names = [s.name for s in sections]
    assert len(all_names) == len(set(all_names))  # every element name is unique


def test_inline_toc_entries_are_suppressed():
    # #6 — a contents page whose entries are inlined as boundaries must NOT create
    # spurious chapters or drag the body start into the TOC.
    boundaries = [
        (0, 8, "Contents"),
        (20, 30, "Chapter 1"),     # packed TOC links (small gaps)
        (60, 70, "Chapter 2"),
        (100, 110, "Chapter 3"),
        (140, 150, "Chapter 4"),
        (5000, 5012, "Chapter 1"),  # the real first chapter, far away
        (12000, 12012, "Chapter 2"),
    ]
    sections = detect_layout_sections(boundaries, text_len=20000)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == 2                       # only the two real chapters
    body = next(s for s in sections if s.type == "body")
    assert body.start == 5000                        # body starts at the real chapter


def test_inline_toc_suppressed_in_long_novel():
    # Regression for the absolute-cap bug: a dense inline TOC in a full-length novel
    # has a large absolute span but a tiny ratio — the ratio gate must still suppress.
    text_len = 400_000
    boundaries = [(0, 8, "Contents")]
    boundaries += [(200 * (i + 1), 200 * (i + 1) + 10, f"Chapter {i + 1}") for i in range(50)]
    boundaries += [(40_000, 40_012, "Chapter 1"), (120_000, 120_012, "Chapter 2")]
    sections = detect_layout_sections(boundaries, text_len=text_len)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == 2  # 50 TOC links suppressed, two real chapters kept


def test_micro_chapters_not_mistaken_for_toc():
    # The compactness gate keeps genuine short-chapter works (whose chapters span the
    # whole text) from being demoted even when a contents page is present.
    boundaries = [(0, 8, "Contents")] + [
        (200 * (i + 1), 200 * (i + 1) + 10, f"Chapter {i + 1}") for i in range(20)
    ]
    sections = detect_layout_sections(boundaries, text_len=4400)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == 20                       # all real chapters preserved


def test_headingless_frontmatter_sublabeled():
    # #7 — copyright / title pages with no heading are recovered by content scan.
    front = "The Great Work\nby An Author\n\nCopyright 2020. All rights reserved.\n\n"
    full = front + "Chapter 1\n\n" + "prose. " * 400
    boundaries = [(len(front), len(front) + 9, "Chapter 1")]
    sections = detect_layout_sections(boundaries, text_len=len(full), text=full)
    types = {s.type for s in sections}
    assert "copyright" in types
    assert "title_page" in types
    cp = next(s for s in sections if s.type == "copyright")
    assert cp.start < len(front)                     # lives in the front-matter run


def test_sublabel_skipped_without_text():
    # Without the reference text the content scan is a no-op (back-compat).
    boundaries = [(500, 510, "Chapter 1")]
    sections = detect_layout_sections(boundaries, text_len=4000)
    assert not any(s.type in {"copyright", "title_page"} for s in sections)


def test_detect_verse_regions_finds_scripture_run():
    regions = detect_verse_regions(_SCRIPTURE)
    assert len(regions) == 1
    start, end = regions[0]
    assert _SCRIPTURE[start:].startswith("1 In the beginning")
    assert "firmament" in _SCRIPTURE[start:end]


def test_detect_verse_regions_ignores_prose():
    prose = (
        "It is a truth universally acknowledged, that a single man in possession "
        "of a good fortune, must be in want of a wife.\n\n"
        "However little known the feelings of such a man may be on first entering "
        "a neighbourhood, this truth is well fixed in the minds of families.\n\n"
    )
    assert detect_verse_regions(prose) == []


def test_detect_verse_regions_rejects_book_name_cluster():
    # A table of contents lists digit-prefixed book names; each line is too short to
    # be a verse, so the length floor keeps them from clustering into a false run.
    toc = "1 Samuel\n\n2 Samuel\n\n1 Kings\n\n2 Kings\n\n1 Chronicles\n\n2 Chronicles\n\n"
    assert detect_verse_regions(toc) == []


def test_detect_verse_regions_rejects_number_table():
    # An apparatus table has long, numbered, but non-sequential lines: the sequence
    # check rejects it even though it clears the length floor.
    table = (
        "4 days' wages equal two bekas in the table of measures.\n\n"
        "2 days' wages equal one half of a Jewish silver shekel.\n\n"
        "60 minas are reckoned as three thousand silver shekels.\n\n"
        "9 feet, or ten and a half feet as measured in Ezekiel.\n\n"
    )
    assert detect_verse_regions(table) == []


# A block of commentary/apparatus so a study-edition body is not all-scripture.
_ANNOTATIONS = (
    "Annotations for Genesis\n\n"
    + "".join(
        f"1:{v}. This study note explains verse {v} at some interpretive length.\n\n"
        for v in range(1, 12)
    )
)


def test_translation_overlay_added_for_verse_run():
    # A study-edition body: scripture set against commentary → masked 'translation'.
    front = "Title Page\n\nby Some Editor\n\n"
    text = front + _SCRIPTURE + _ANNOTATIONS
    boundaries = [(0, 10, "Title Page"), (len(front), len(front) + 9, "Chapter 1")]
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    translations = [s for s in sections if s.type == "translation"]
    assert len(translations) == 1
    assert translations[0].start >= len(front)
    assert DEFAULT_MASK_BY_TYPE["translation"] is True


def test_mono_scripture_work_gets_no_translation_overlay():
    # A work that is almost entirely verses (a plain Bible) is mono-scriptural: the
    # body itself is the scripture, so no 'translation' overlay should be added.
    text = _SCRIPTURE * 6
    boundaries = [(0, 9, "Chapter 1")]
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    assert not any(s.type == "translation" for s in sections)
