"""Tests for layout sections + the deepest-section-wins masking rule."""

from palimpsest.layout import (
    DEFAULT_MASK_BY_TYPE,
    LayoutSection,
    _MIN_SCHOLARLY_WORKS,
    _classify_heading,
    _parse_chapter_heading,
    detect_layout_sections,
    detect_siglum_regions,
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


def test_incidental_numbered_notes_get_no_translation_overlay():
    # A novel whose only verse-like lines are a short run of editorial endnotes
    # ("1 When our forefathers...") sequential and length-passing, so they DO cluster
    # as a verse run — but they are a negligible share of the work, so the min-fraction
    # gate must suppress the overlay rather than mark the notes as scripture.
    prose = "The narrative continues in plain prose without any verse numbering here. " * 200
    notes = "".join(
        f"{i} When our forefathers first came to the new land they found much there.\n\n"
        for i in range(1, 9)
    )
    text = prose + "\n\n" + notes
    # The notes really do look like a verse run to the content scanner...
    assert detect_verse_regions(text) != []
    # ...but as <5% of the body they are incidental, so no translation mask is emitted.
    boundaries = [(0, 9, "Chapter 1")]
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    assert not any(s.type == "translation" for s in sections)


def test_backmatter_apparatus_before_body_does_not_swallow_it():
    # A heading-less work with back-matter-typed apparatus ("List of Illustrations")
    # printed AHEAD of the narrative must not let the back-matter region bleed forward
    # across the whole body. Only the trailing "Index", contiguous with the end, is
    # back matter; the narrative between them stays in the analyzable body. (Regression:
    # this layout masked ~90% of Pilgrim's Progress as back matter.)
    front = "Title Page\n\nContents\n\nList of Illustrations\n\n"
    narrative = "Christian walked on through the wilderness toward the light. " * 6000
    index = "\n\nIndex\n\nApollyon 61 Atheist 138 Beulah 200\n\n"
    text = front + narrative + index
    pos = text.index
    loi = "List of Illustrations"
    boundaries = [
        (pos("Title Page"), pos("Title Page") + 10, "Title Page"),
        (pos("Contents"), pos("Contents") + 8, "Contents"),
        (pos(loi), pos(loi) + 21, loi),
        (pos("Index"), pos("Index") + 5, "Index"),
    ]
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    body = next(s for s in sections if s.type == "body")
    back = next(s for s in sections if s.type == "back_matter")
    assert body.end - body.start > len(narrative) * 0.9
    assert back.start >= pos("Index") - 5


def test_scholarly_anthology_carves_commentary_and_translation():
    # An anthology of translated ancient works: each opens with a scholar's work header
    # (the commentary) then a bare "Translation" heading (the rendered source text, running
    # to the next work). The repeating template (>=3 works) carves alternating commentary +
    # translation layers — commentary analyzable, translation masked.
    seg = "Scholarly analysis of the ancient source text follows here. " * 800  # > body gap
    parts = []
    for _ in range(3):
        parts.append("A new translation and introduction\n\n" + seg)
        parts.append("Translation\n\n" + seg)
    text = "Front matter\n\n" + "\n\n".join(parts) + "\n\n"
    boundaries = []
    for marker in ("A new translation and introduction", "Translation"):
        i = text.find(marker)
        while i >= 0:
            boundaries.append((i, i + len(marker), marker))
            i = text.find(marker, i + len(marker))
    sections = detect_layout_sections(sorted(boundaries), text_len=len(text), text=text)
    assert sum(s.type == "commentary" for s in sections) == 3
    assert sum(s.type == "translation" for s in sections) == 3
    assert DEFAULT_MASK_BY_TYPE["translation"] is True
    assert DEFAULT_MASK_BY_TYPE["commentary"] is False


def test_single_translation_heading_is_not_treated_as_anthology():
    # One stray "Translation" heading (below the repetition gate) must NOT carve a
    # translation/commentary layer that would mask everything after it.
    seg = "Ordinary narrative prose continues for a while. " * 50
    text = "Chapter 1\n\n" + seg + "Translation\n\n" + seg
    i = text.find("Translation")
    boundaries = [(0, 9, "Chapter 1"), (i, i + 11, "Translation")]
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    assert not any(s.type == "commentary" for s in sections)
    assert not any(s.type == "translation" for s in sections)


def test_inline_anthology_template_recovered_without_headings():
    # Some EPUBs flatten the per-work headers into inline body text and emit no heading
    # track, so the structural pass sees zero markers. The repeating template is then
    # recovered from the text directly, carving the same alternating commentary +
    # translation layers — even with NO structural boundaries supplied.
    seg = "Scholarly analysis of the ancient source text follows here. " * 60
    parts = []
    for _ in range(3):
        parts.append("A new translation and introduction\n\n" + seg)
        parts.append("Translation\n\n" + seg)
    text = "\n\n".join(parts) + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert sum(s.type == "commentary" for s in sections) == 3
    assert sum(s.type == "translation" for s in sections) == 3


def test_title_template_anthology_recovered_without_translation_headings():
    # An anthology whose works carry NO bare "Translation" divider (the Eerdmans OT
    # Pseudepigrapha): each work is "<Title> / A new translation and introduction / by X /
    # intro / Bibliography / <Title> (repeated) / rendered text". The repeated title opens
    # the translation, so the commentary/translation layers are recovered from it. A few
    # stray chapter headings inside one constituent work must NOT anchor the body ahead of
    # the anthology, so they are demoted.
    intro = "Scholarly analysis of the ancient source text follows here at length. " * 30
    biblio = "Bibliography\n\nSmith, J. A Study of the Source. 1990.\n\n"
    rendered = "And the ancient words were rendered thus in this place for the reader. " * 30
    titles = ["The Book of Alpha", "The Book of Beta", "The Apocryphon of Gamma",
              "The Vision of Delta"]
    parts = ["FRONT MATTER\n\nGeneral preface to the whole collection here.\n\n"]
    for i, t in enumerate(titles):
        body = rendered
        if i == 1:  # one constituent work carries internal chapter headings
            body = "\n\n".join(f"Chapter {n}\n\n{rendered}" for n in (1, 2, 3))
        parts.append(f"{t}\n\nA new translation and introduction\n\nby Scholar {i}\n\n"
                     f"{intro}\n\n{biblio}{t}\n\n{body}")
    text = "\n\n".join(parts) + "\n\n"
    boundaries = []
    for t in titles:  # the EPUB exposes the work header (classifier types it 'introduction')
        h = text.index(f"{t}\n\nA new translation and introduction") + len(f"{t}\n\n")
        boundaries.append((h, h + 34, "A new translation and introduction"))
    for n in (1, 2, 3):  # and the stray chapter headings of the one constituent work
        c = text.index(f"Chapter {n}\n\n")
        boundaries.append((c, c + 9, f"Chapter {n}"))
    sections = detect_layout_sections(sorted(boundaries), text_len=len(text), text=text)
    assert sum(s.type == "commentary" for s in sections) == len(titles)
    assert sum(s.type == "translation" for s in sections) >= _MIN_SCHOLARLY_WORKS
    assert not any(s.type == "chapter" for s in sections)  # stray chapters demoted
    body = next(s for s in sections if s.type == "body")
    assert body.start < text.index("Chapter 1\n\n")  # body anchored at work 1, not the stray chapters
    # the rendered text of the first work is masked translation; its intro is analyzable.
    mi = masked_intervals(sections, DEFAULT_MASK_BY_TYPE, len(text))
    assert range_is_masked(mi, text.rindex("The Book of Alpha") + 40, text.rindex("The Book of Alpha") + 200)


def test_title_template_needs_repeated_titles_not_just_work_headers():
    # Work headers WITHOUT the repeated-title template (no recurrence to open a translation)
    # must not be carved into translation layers — the recurrence is the required signal.
    intro = "Scholarly analysis of the ancient source text continues here plainly. " * 30
    titles = ["The Book of Alpha", "The Book of Beta", "The Apocryphon of Gamma"]
    parts = []
    for i, t in enumerate(titles):  # title appears ONCE; no recurrence after the intro
        parts.append(f"{t}\n\nA new translation and introduction\n\nby Scholar {i}\n\n{intro}")
    text = "\n\n".join(parts) + "\n\n"
    boundaries = []
    for t in titles:
        h = text.index(f"{t}\n\nA new translation and introduction") + len(f"{t}\n\n")
        boundaries.append((h, h + 34, "A new translation and introduction"))
    sections = detect_layout_sections(sorted(boundaries), text_len=len(text), text=text)
    assert not any(s.type == "translation" for s in sections)  # no recurrence ⇒ no translation layer


def test_inline_translation_words_in_prose_do_not_carve():
    # The line-anchored text scan must ignore the words appearing inside running prose:
    # a novel that happens to discuss "a new translation and introduction" mid-sentence
    # has no standalone marker lines, so nothing is carved (no false positive).
    sentence = (
        "The editor prepared a new translation and introduction to the work, "
        "and the translation that resulted was widely praised. "
    )
    text = "Chapter 1\n\n" + sentence * 80
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert not any(s.type == "commentary" for s in sections)
    assert not any(s.type == "translation" for s in sections)


def test_attribution_anthology_masks_translated_works():
    # An attribution-delimited anthology (e.g. the Nag Hammadi Library): many translated
    # works, each opening with a "Translated by <Name>" line and no per-work commentary.
    # The run of attributions (>= the gate) opens a translation region per work; the
    # leading scholarly introduction before the first attribution stays unmasked.
    seg = "The translated ancient text of this tractate continues at length here. " * 60
    parts = [f"Translated by Scholar Number {i}\n\n{seg}" for i in range(9)]
    text = "General Introduction to the collection.\n\n" + "\n\n".join(parts)
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert sum(s.type == "translation" for s in sections) == 9
    assert DEFAULT_MASK_BY_TYPE["translation"] is True
    # The introduction before the first attribution is not masked.
    assert not any(s.type == "translation" and s.start == 0 for s in sections)


def test_lone_translator_credit_does_not_mask():
    # A translated novel with a single title-page "Translated by" credit stays below the
    # attribution gate, so nothing is masked as translation.
    seg = "Ordinary narrative prose continues for a while. " * 80
    text = "Translated by A. Translator\n\n" + seg
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert not any(s.type == "translation" for s in sections)


def test_inline_chapters_recovered_without_heading_track():
    # An edition whose EPUB exposes no chapter-level heading track but carries its chapters
    # as line-anchored "Chapter N" body text (e.g. the Global Grey Ante-Nicene volumes): the
    # content scan recovers them so the work segments instead of collapsing into one body
    # blob, and the body begins at the first recovered chapter (the leading editorial intro
    # stays front matter).
    body = "The translated text of this chapter runs on for several lines here. " * 20
    intro = "Editorial introduction to the whole collection.\n\n" * 5
    parts = [f"Chapter {r}.\n\n{body}" for r in ("I", "II", "III", "IV", "V", "VI")]
    text = intro + "\n\n".join(parts) + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == 6
    body_sec = next(s for s in sections if s.type == "body")
    assert body_sec.start > 0  # the leading intro is masked front matter, not body


def test_inline_chapter_contents_listing_not_recovered_as_chapters():
    # A bare "Chapter I. / Chapter II. / …" contents listing (entries a heading apart, with
    # no body between them) must not be recovered as chapters: _drop_toc_chapter_runs strips
    # the compact run, so only the real chapters that follow (separated by their body) remain.
    toc = "".join(f"Chapter {r}.\n\n" for r in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII"))
    sep = "Introductory matter between the contents and the body.\n\n" + ("x " * 200) + "\n\n"
    body = "The actual chapter text continues for several lines in this work. " * 20
    real = "\n\n".join(f"Chapter {r}.\n\n{body}" for r in ("I", "II", "III", "IV", "V"))
    text = toc + sep + real + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == 5  # the 8-entry TOC run dropped; 5 real chapters kept


def test_heading_track_chapters_suppress_inline_recovery():
    # When the EPUB already supplies a chapter-level heading track (>= the gate), inline
    # "Chapter N" recovery does not fire, so a standard chaptered work is neither
    # re-segmented nor double-counted from its own body text.
    body = "Chapter narrative prose continues here for a good while. " * 20
    text = "\n\n".join(f"Chapter {n}\n\n{body}" for n in range(1, 7)) + "\n\n"
    boundaries, pos = [], 0
    for n in range(1, 7):
        h = f"Chapter {n}"
        s = text.index(h, pos)
        boundaries.append((s, s + len(h), h))
        pos = s + len(h)
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    assert sum(s.type == "chapter" for s in sections) == 6  # not doubled by recovery


def test_numbered_named_divisions_segment_as_chapters():
    # A scripture whose divisions are numbered and named in English with the original name in
    # parentheses on the FOLLOWING line ("2. The Cow\n\n( Al-Baqarah)") — the Quran's surahs.
    # The next-line parenthetical opens each division as a chapter, while an inline contents
    # entry (paren on the SAME line) is not segmented.
    names = [("The Opener", "Al-Fatihah"), ("The Cow", "Al-Baqarah"), ("Women", "An-Nisa"),
             ("The Table", "Al-Maidah"), ("The Cattle", "Al-Anam"), ("The Heights", "Al-Araf")]
    body = "Scripture prose for this division continues at some length here. " * 8
    parts = [f"{i + 1}. {names[i % len(names)][0]}\n\n( {names[i % len(names)][1]})\n\n{body}"
             for i in range(22)]
    toc = "".join(f"{i + 1}. {names[i % len(names)][0]} ( {names[i % len(names)][1]})\n"
                  for i in range(22))
    text = "Front matter introduction.\n\n" + toc + "\n\n" + "\n\n".join(parts) + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == 22  # the 22 body divisions; the inline TOC is not segmented


def test_few_named_divisions_below_gate_not_segmented():
    # A handful of "N. Name\n\n( Other)" lines (below the division gate) is not a structured
    # scripture, so nothing is segmented — the gate keeps the mechanism scripture-specific.
    body = "Ordinary prose continues here for a while without any divisions. " * 8
    parts = [f"{n}. A Heading\n\n( Note)\n\n{body}" for n in range(1, 4)]
    text = "\n\n".join(parts) + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert not any(s.type == "chapter" for s in sections)


def test_ordinal_worded_divisions_segment_as_chapters():
    # An edition that heads each scripture division with an English ordinal WORD instead of a
    # digit ("THE FIRST SURAH", "THE SECOND SURAH" …, Asad's Qur'an), the division's name on the
    # following line. The ordinal carries no numeral, so the divisions are numbered by sequence;
    # a page-numbered contents listing ("THE FIRST SURAH 1") is excluded by the end-of-line anchor.
    ordinals = ["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH", "SEVENTH", "EIGHTH",
                "NINTH", "TENTH", "ELEVENTH", "TWELFTH", "THIRTEENTH", "FOURTEENTH", "FIFTEENTH",
                "SIXTEENTH", "SEVENTEENTH", "EIGHTEENTH", "NINETEENTH", "TWENTIETH",
                "TWENTY-FIRST", "TWENTY-SECOND"]
    body = "Scripture prose for this surah continues at some length here. " * 8
    parts = [f"THE {o} SURAH\n\nName{i}(The Meaning)\n\nMecca Period\n\n{body}"
             for i, o in enumerate(ordinals)]
    toc = "".join(f"THE {o} SURAH {i + 1}\n" for i, o in enumerate(ordinals))
    text = "Front matter foreword.\n\n" + toc + "\n\n" + "\n\n".join(parts) + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == 22  # 22 divisions; the page-numbered contents listing is not segmented
    assert chapters[0].metadata.get("number") == "1"
    assert chapters[-1].metadata.get("number") == "22"
    body_sec = next(s for s in sections if s.type == "body")
    assert body_sec.start > 0  # the foreword and contents listing stay front matter


def test_versed_chapter_verse_openings_segment_as_chapters():
    # Versed scripture printed as "<chapter>. <verse>. text" with only the first verse line-
    # anchored (R.H. Charles' Book of Enoch). Each chapter.verse opening starts a chapter, and
    # the leading editorial introduction stays masked front matter.
    verse = "And the word of righteousness continued through these days of old. "
    intro = "Editorial introduction discussing the whole work at length.\n\n" * 5
    parts = [f"{n}.   1. {verse * 3}" for n in range(1, 25)]
    text = intro + "\n".join(parts) + "\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == 24
    assert chapters[0].metadata.get("number") == "1"
    body_sec = next(s for s in sections if s.type == "body")
    assert body_sec.start > 0


def test_editorial_numbered_notes_do_not_segment_as_versed_chapters():
    # Single-number editorial notes ("1. His desire of a greater benefice…") carry no inner
    # verse number, so the versed-chapter recovery (which requires the second number) does not
    # fire — the false positive that would mask a work's annotations as scripture chapters.
    note = "His desire of a greater benefice is here recorded at some length indeed. "
    parts = [f"{n}. {note * 2}" for n in range(1, 25)]
    text = "Body prose introducing these editorial notes.\n\n" + "\n".join(parts) + "\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert not any(s.type == "chapter" for s in sections)


def test_versed_chapters_suppress_stray_chapter_mentions():
    # When a chapter.verse run is present it is the chapter track, and the loose "Chapter N"
    # scan is skipped — so spread-out prose mentions of chapter numbers in an introduction
    # (which _drop_toc_chapter_runs would NOT strip, being non-compact) are not recovered.
    verse = "And the vision was shown to me in that place of the righteous ones. "
    filler = "Some sentences of editorial discussion go here for a while now. " * 5
    intro = "".join(f"Chapter {n} is discussed here in the scholarly preface.\n\n{filler}\n\n"
                    for n in (108, 12, 14, 6, 7))
    parts = [f"{n}.   1. {verse * 3}" for n in range(1, 25)]
    text = intro + "\n".join(parts) + "\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == 24  # only the versed chapters; the intro's "Chapter N" lines excluded
    assert all(c.metadata.get("number") in {str(n) for n in range(1, 25)} for c in chapters)


_BOM_BOOKS = [
    "THE FIRST BOOK OF NEPHI", "THE SECOND BOOK OF NEPHI", "THE BOOK OF JACOB",
    "THE BOOK OF ENOS", "THE BOOK OF MOSIAH", "THE BOOK OF ALMA", "THE BOOK OF HELAMAN",
    "BOOK OF MORMON", "BOOK OF ETHER", "THE BOOK OF MORONI",
]


def test_inline_books_recovered_with_per_book_chapter_runs():
    # An edition whose EPUB exposes no book-level heading track and carries its books as
    # upper-case "THE [ordinal] BOOK OF <NAME>" lines, across which chapter numbering restarts
    # (the Book of Mormon). The books are recovered so the repeating per-book "CHAPTER I" runs
    # nest under a disambiguating book instead of colliding in one flat sequence.
    body = "The scripture text of this chapter continues at length in this place. " * 12
    intro = "Editorial introduction to the whole record.\n\n" * 5
    parts = []
    for bk in _BOM_BOOKS:
        chs = "\n\n".join(f"CHAPTER {r}\n\n{body}" for r in ("I", "II", "III"))
        parts.append(f"{bk}\n\n{chs}")
    text = intro + "\n\n".join(parts) + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    books = [s for s in sections if s.type == "book"]
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(books) == len(_BOM_BOOKS)  # every book recovered
    assert len(chapters) == 3 * len(_BOM_BOOKS)  # 3 chapters per book, numbering restarts
    by_id = {s.id: s for s in sections}

    def book_ancestor(sec):
        pid = sec.parent_id
        while pid and pid in by_id:
            if by_id[pid].type == "book":
                return by_id[pid].id
            pid = by_id[pid].parent_id
        return None

    # The eight "CHAPTER I" headings are disambiguated by nesting under distinct books.
    first_chapter_books = {book_ancestor(c) for c in chapters if c.metadata.get("number") == "I"}
    assert len(first_chapter_books) == len(_BOM_BOOKS)
    assert all(book_ancestor(c) is not None for c in chapters)  # every chapter parented to a book
    body_sec = next(s for s in sections if s.type == "body")
    assert body_sec.start > 0  # the leading editorial intro stays masked front matter


def test_book_contents_listing_dropped_and_modern_intro_title_excluded():
    # A front contents listing interleaves each book with its chapter entries; merged with the
    # chapter markers it is one compact run and drops, so only the real body books survive. A
    # modern introduction titled "THE MEANING OF THE BOOK OF MORMON TODAY" is not a "BOOK OF"
    # heading and stays front matter rather than being misread as a book.
    toc = "".join(f"{bk}\n" + "".join(f"CHAPTER {r}\n" for r in ("I", "II", "III"))
                  for bk in _BOM_BOOKS)
    intro = "THE MEANING OF THE BOOK OF MORMON TODAY\n\n" + ("Scholarly framing prose. " * 40)
    body = "The scripture text of this chapter continues at length in this place. " * 12
    real = "\n\n".join(
        f"{bk}\n\n" + "\n\n".join(f"CHAPTER {r}\n\n{body}" for r in ("I", "II", "III"))
        for bk in _BOM_BOOKS
    )
    text = toc + "\n\n" + intro + "\n\n" + real + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    books = [s for s in sections if s.type == "book"]
    assert len(books) == len(_BOM_BOOKS)  # contents listing dropped; real books kept
    assert all("MEANING" not in s.label.upper() for s in books)  # intro title is not a book
    intro_off = text.index("THE MEANING OF THE BOOK OF MORMON TODAY")
    covering = [s for s in sections
                if s.type in ("book", "chapter") and s.start <= intro_off < s.end]
    assert not covering  # the modern intro is not inside any recovered book/chapter


def test_few_book_headings_below_gate_not_recovered():
    # A handful of "BOOK OF <Name>" lines (below the book gate) is not a structured canon, so no
    # book track is synthesized — the gate keeps the mechanism scripture-scale.
    body = "Ordinary narrative prose continues here for a good while now. " * 12
    parts = [f"THE BOOK OF {n}\n\n{body}" for n in ("ALPHA", "BETA", "GAMMA")]
    text = "\n\n".join(parts) + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert not any(s.type == "book" for s in sections)


def test_titlecase_book_mentions_do_not_recover_books():
    # The recovery is upper-case (no re.I): a novel's title-case "The Book of <Name>" lines are
    # ordinary prose, not scripture-book headings, so they are never recovered as books.
    body = "The chapter narrative continues for a while in this novel here. " * 12
    parts = [f"The Book of {n}\n\n{body}"
             for n in ("Dreams", "Shadows", "Names", "Hours", "Rivers", "Stones",
                       "Ashes", "Roads", "Doors", "Tides")]
    text = "\n\n".join(parts) + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert not any(s.type == "book" for s in sections)


def test_trailing_scripture_index_typed_back_matter_not_books():
    # A scholarly work whose EPUB nav exposes each book name in a trailing "Index of Ancient
    # Sources" (book + verse:page citations). Those headings match the canon lexicon but open an
    # index, not the books — typing them structural 'book' would drag body_start to the tail and
    # mask the whole work as front matter. They must be back-matter 'index' instead.
    book_names = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
                  "Joshua", "Judges", "Ruth", "Samuel", "Kings"]
    cites = "\n\n".join(f"{v}:{v}\n\n{100 + v * 7}, {200 + v * 3}, {300 + v}" for v in range(1, 12))
    body = "Scholarly discussion of the targumic tradition continues at length here. " * 400
    front = "Title Page\n\nCopyright 2024 Some Publisher\n\n"
    index_block = "INDEX OF ANCIENT SOURCES\n\n" + "\n\n".join(f"{bk}\n\n{cites}" for bk in book_names)
    text = front + body + "\n\n" + index_block + "\n\n"
    boundaries = [(0, 10, "Title Page"), (12, 21, "Copyright")]
    for bk in book_names:
        off = text.index(f"\n\n{bk}\n\n") + 2
        boundaries.append((off, off + len(bk), bk))
    sections = detect_layout_sections(sorted(boundaries), text_len=len(text), text=text)
    assert not any(s.type == "book" for s in sections)       # no spurious book divisions
    assert any(s.type == "index" for s in sections)          # the run is back-matter index
    body_sec = next(s for s in sections if s.type == "body")
    assert body_sec.end - body_sec.start > len(body)         # body not collapsed to a tail
    assert body_sec.start < text.index("INDEX OF ANCIENT SOURCES")


def test_head_book_nav_cluster_still_promoted_to_books():
    # A Bible whose EPUB lists every book at the HEAD with a digit-dense chapter-number strip
    # ("Genesis 1 2 3 …") must still be promoted to structural books: the scripture-index guard is
    # trailing-and-compact, so a head nav cluster (the Strong's-Bible regression) is unaffected.
    book_names = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
                  "Joshua", "Judges", "Ruth", "Samuel", "Kings"]
    nav = "\n\n".join(f"{bk}\n\n" + " ".join(str(i) for i in range(1, 30)) for bk in book_names)
    text = nav + "\n\n" + ("And it came to pass in those days that the word continued. " * 300)
    boundaries = [(text.index(f"{bk}\n\n"), text.index(f"{bk}\n\n") + len(bk), bk) for bk in book_names]
    sections = detect_layout_sections(sorted(boundaries), text_len=len(text), text=text)
    assert any(s.type == "book" for s in sections)           # head nav cluster → real books
    assert not any(s.type == "index" for s in sections)


def test_spanish_volume_chapter_headings_recognized_and_midword_roman_demoted():
    # A Spanish edition: "VOLUMEN <roman>" volumes and "Capítulo <word>" chapters are
    # recognized (i18n, like the multilingual contents regex), while a bare-Roman heading
    # whose EPUB boundary split a word (nav label "I" pointing into "Ilustración") is demoted
    # so it neither becomes a chapter nor anchors the body before the first real volume.
    body = "El texto de este capitulo continua aqui durante un buen rato mas. " * 20
    chapters = ["Capítulo uno", "Capítulo dos", "Capítulo tres",
                "Capítulo cuatro", "Capítulo cinco", "Capítulo seis"]
    parts = ["Prologo del traductor con notas y creditos editoriales.\n\n",
             "Ilustración de portada y demas creditos del libro aqui.\n\n"]
    parts.append("VOLUMEN I\n\n")
    for c in chapters[:3]:
        parts.append(f"{c}\n\n{body}\n\n")
    parts.append("VOLUMEN II\n\n")
    for c in chapters[3:]:
        parts.append(f"{c}\n\n{body}\n\n")
    text = "".join(parts)
    il = text.index("Ilustración")
    boundaries = [(il, il + 1, "I")]  # nav label "I" splits "Il…" → demoted
    for v in ("VOLUMEN I", "VOLUMEN II"):
        o = text.index(v + "\n\n")
        boundaries.append((o, o + len(v), v))
    for c in chapters:
        o = text.index(c + "\n\n")
        boundaries.append((o, o + len(c), c))
    sections = detect_layout_sections(sorted(boundaries), text_len=len(text), text=text)
    assert sum(s.type == "volume" for s in sections) == 2     # VOLUMEN I/II recognized
    assert sum(s.type == "chapter" for s in sections) == 6    # 6 Capítulos; the mid-word "I" demoted
    body_sec = next(s for s in sections if s.type == "body")
    assert body_sec.start == text.index("VOLUMEN I")          # body anchored at the first volume


def test_bare_roman_fragment_run_not_demoted_when_clean():
    # A treatise's numbered fragment run ("I", "II", "III" on their own lines) is real
    # structure: the mid-word guard must only drop word-splitting Romans, never a clean run.
    body = "The fragment text of this section continues for a while here in place. " * 12
    parts = ["Chapter 1\n\n" + body]  # a keyworded chapter coexists with the fragment run
    for r in ("I", "II", "III", "IV", "V"):
        parts.append(f"{r}\n\n{body}")
    text = "\n\n".join(parts) + "\n\n"
    boundaries = [(text.index("Chapter 1"), text.index("Chapter 1") + 9, "Chapter 1")]
    for r in ("I", "II", "III", "IV", "V"):
        o = text.index(f"\n\n{r}\n\n") + 2
        boundaries.append((o, o + len(r), r))
    sections = detect_layout_sections(sorted(boundaries), text_len=len(text), text=text)
    roman_chapters = [s for s in sections if s.type == "chapter"
                      and s.metadata.get("number") in ("I", "II", "III", "IV", "V")]
    assert len(roman_chapters) == 5  # clean bare-Roman run preserved, not demoted


def _splits_a_word(text, lo, hi):
    n = len(text)
    start_mid = 0 < lo < n and text[lo - 1].isalnum() and text[lo].isalnum()
    end_mid = 0 < hi < n and text[hi - 1].isalnum() and text[hi].isalnum()
    return start_mid or end_mid


def test_versed_scripture_split_anchors_snap_to_verse_marker():
    # Friedman's Commentary on the Torah: each verse opens with a "<chapter>:<verse>" reference
    # then the verse body, but some EPUB nav anchors land *inside* the marker and expose only a
    # 1-char heading window — splitting the number mid-token. The boundary must snap to span the
    # whole verse marker so neither the carved header nor the chapter body cuts a number in half.
    vb = "And the priest shall look and consider the matter at some length here. "
    text = (
        "Commentary front matter introduction prose runs on here for a good while.\n\n"
        f"Leviticus 13:51\n\n51 {vb * 2}\n\n"
        f"Leviticus 13:52\n\n52 {vb * 2}\n\n"
        f"Leviticus 13:53\n\n53 {vb * 2}\n\n"
        f"Leviticus 13:54\n\n54 {vb * 2}\n\n"
    )
    # Reproduce the three broken anchor styles seen in the EPUB nav, all 1-char windows.
    i51 = text.index("13:51")           # anchor at the reference start ("1" of "13:51")
    i52 = text.index("13:52")           # anchor at the reference end (final "2" of "13:52")
    i53 = text.index("13:53")           # anchor one digit in ("3" of "13:53")
    j54 = text.index("54 And")          # anchor in the bare verse-body number ("5" of "54")
    boundaries = [
        (i51, i51 + 1, "1"),
        (i52 + 4, i52 + 5, "2"),
        (i53 + 1, i53 + 2, "3"),
        (j54, j54 + 1, "5"),
    ]
    sections = detect_layout_sections(sorted(boundaries), text_len=len(text), text=text)
    # No carved boundary may split a word after the snap.
    assert not any(_splits_a_word(text, s.start, s.end) for s in sections)
    # The first reference-style header spans the whole "13:51" marker, not a single digit.
    headers = sorted((s for s in sections if s.type == "header"), key=lambda s: s.start)
    assert text[headers[0].start:headers[0].end] == "13:51"
    assert sum(s.type == "chapter" for s in sections) == 4


def test_clean_verse_anchor_is_not_snapped():
    # A clean nav anchor — landing exactly on the verse number after the colon ("48" of
    # "13:48"), splitting no word — must be left untouched: the snap is gated on an actual
    # mid-word split, so it never grows a well-placed heading window.
    vb = "And the priest shall look and consider the matter at some length here. "
    text = (
        "Commentary front matter introduction prose runs on here for a good while.\n\n"
        f"Leviticus 13:48\n\n48 {vb * 2}\n\n"
        f"Leviticus 13:49\n\n49 {vb * 2}\n\n"
    )
    i48 = text.index("13:48")
    i49 = text.index("13:49")
    boundaries = [(i48 + 3, i48 + 5, "48"), (i49 + 3, i49 + 5, "49")]  # window on the verse part
    sections = detect_layout_sections(sorted(boundaries), text_len=len(text), text=text)
    assert not any(_splits_a_word(text, s.start, s.end) for s in sections)
    header = next(s for s in sections if s.type == "header")
    assert text[header.start:header.end] == "48"  # unchanged: not grown to "13:48"


def test_explicit_chapter_prefix_wins_over_matter_word_title():
    # A chapter whose title contains a matter word ("Chapter XXV — Conclusion", "Chapter 8.
    # Appendix") classifies as a chapter on the strength of its explicit "Chapter <N>" prefix,
    # not mis-typed afterword/appendix/introduction from the trailing word.
    titles = ["Chapter I — The Start", "Chapter II — Introduction to the Town",
              "Chapter III — The Appendix Affair", "Chapter IV — Conclusion"]
    body = "The narrative of this chapter continues at length for a while here. " * 20
    boundaries, text, cursor = [], "", 0
    for t in titles:
        s = cursor
        text += t + "\n\n" + body + "\n\n"
        boundaries.append((s, s + len(t), t))
        cursor = len(text)
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    assert sum(s.type == "chapter" for s in sections) == 4
    assert not any(s.type in ("afterword", "appendix", "introduction") for s in sections)


def test_bare_matter_word_without_chapter_prefix_still_typed():
    # The explicit-chapter override is narrow: it requires the "Chapter <N>" keyword, so a
    # bare "Conclusion" heading (no chapter prefix) still classifies as its matter type.
    body = "Closing reflections on the whole matter continue for a while here. " * 20
    chap = "The narrative of this chapter continues at length for a while here. " * 20
    boundaries, text, cursor = [], "", 0
    for head, content in [("Chapter I", chap), ("Chapter II", chap), ("Conclusion", body)]:
        s = cursor
        text += head + "\n\n" + content + "\n\n"
        boundaries.append((s, s + len(head), head))
        cursor = len(text)
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    assert any(s.type == "afterword" for s in sections)  # bare "Conclusion" stays afterword
    assert sum(s.type == "chapter" for s in sections) == 2


def test_trailing_numbered_endnote_list_is_back_matter_not_chapters():
    # An annotated edition prints its notes as a run of bare numerals (1, 2, 3, …) each alone on
    # a line, the note text between. A lone such numeral in a sparse heading track must be back
    # matter (the notes), not a body chapter — and must not drag the narrative into front matter.
    novel = "The narrative of this work continues at length for many lines here. " * 200
    notes = "".join(f"{n}\n\nDefinition of term number {n} goes here.\n\n" for n in range(1, 12))
    text = novel + "\n\n" + notes
    en_pos = text.index("1\n\nDefinition")
    boundaries = [(en_pos, en_pos + 1, "1")]  # the only heading-track item is the notes' "1"
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    body = next(s for s in sections if s.type == "body")
    assert body.start == 0 and body.end <= en_pos + 5  # the novel is the body, not front matter
    assert any(s.type == "endnotes" for s in sections)  # the notes list typed back matter
    assert not any(s.type == "chapter" for s in sections)  # the bare "1" is not a chapter


def test_numbered_list_in_first_half_is_not_treated_as_endnotes():
    # A numbered list in the first half of a work (an in-text enumeration) is not a trailing
    # notes glossary, so the endnote-list recovery does not fire (the trailing-position gate).
    lst = "".join(f"{n}\n\nItem {n}.\n\n" for n in range(1, 12))
    body = "Ordinary prose continues here for a good long while in this work. " * 200
    text = lst + "\n\n" + body  # the list is at the FRONT, not trailing
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert not any(s.type == "endnotes" for s in sections)


_DESCRIPTIVE_TITLES = [
    "I Go to Sea", "I Build My Fortress", "I Make Myself a Canoe",
    "I Call Him Friday", "We Quell a Mutiny", "I Revisit My Island",
]


def test_toc_descriptive_titles_recovered_via_contents_match():
    # An edition whose chapters carry descriptive titles ("I Go to Sea") and that exposes no
    # heading track: the leading contents block lists the titles and each repeats verbatim as a
    # body heading, so matching the two recovers them as chapters with the full title as name.
    para = "The narrative of this chapter continues at length for a while here. " * 30
    contents = "Table of Contents\n\n" + "\n\n".join(_DESCRIPTIVE_TITLES) + "\n\n"
    intro = "Introduction\n\n" + ("A long introductory paragraph runs on here. " * 40) + "\n\n"
    body = "\n\n".join(f"{t}\n\n{para}" for t in _DESCRIPTIVE_TITLES)
    text = contents + intro + body + "\n\n"
    sections = detect_layout_sections([], text_len=len(text), text=text)
    chapters = [s for s in sections if s.type == "chapter"]
    assert len(chapters) == len(_DESCRIPTIVE_TITLES)
    assert chapters[0].metadata.get("name") == "I Go to Sea"  # full title kept
    assert not chapters[0].metadata.get("number")  # leading "I" is not a chapter number
    body_sec = next(s for s in sections if s.type == "body")
    assert body_sec.start > 0  # the contents block stays masked front matter


def test_toc_short_fragment_lines_not_recovered_as_chapters():
    # A leading run of short narrative fragments ("The", "I", "Now") that happen to recur in
    # the body is not a contents block — the substantial-multi-word-title gate keeps the
    # fragments from being recovered as a spurious chapter track.
    frags = ["The", "I", "Now", "Well", "He", "It"]
    para = "Narrative prose continues here for a good while in this work now. " * 30
    lead = "\n\n".join(frags) + "\n\n"
    body = "\n\n".join(f"{f}\n\n{para}" for f in frags)
    text = lead + ("A long opening paragraph of the work begins here now. " * 40) + "\n\n" + body
    sections = detect_layout_sections([], text_len=len(text), text=text)
    assert not any(s.type == "chapter" for s in sections)


def test_descriptive_title_leading_pronoun_is_name_not_number():
    # "I Go to Sea" — the leading "I" is the narrator pronoun, not roman numeral 1, so the
    # whole phrase is the name with no number. A genuine "1. Title" or keyworded "Chapter IV"
    # still yields its number.
    assert _parse_chapter_heading("I Go to Sea") == {"name": "I Go to Sea"}
    assert _parse_chapter_heading("1. The Beginning").get("number") == "1"
    assert _parse_chapter_heading("Chapter IV - The Reckoning").get("number") == "IV"
    assert _parse_chapter_heading("XIV").get("number") == "XIV"


def _build_chaptered(heads_and_bodies):
    """Build text + EPUB-style boundaries from (heading, body) pairs."""
    boundaries, text, cursor = [], "", 0
    for head, content in heads_and_bodies:
        s = cursor
        text += head + "\n\n" + content + "\n\n"
        boundaries.append((s, s + len(head), head))
        cursor = len(text)
    return boundaries, text


def test_translation_edition_chapters_mask_as_translation_layer():
    # In a translation edition (flagged here by a run of "Elucidation" editorial afterwords),
    # the ancient chapters carry mask_as="translation": they hide when the translation layer is
    # on and show when it is off, while staying chapters (number/nesting) for navigation.
    body = "The rendered ancient text of this work continues at length here. " * 30
    elu = "Editorial discussion of the foregoing text and its sources. " * 20
    pairs = [("Introduction", "Editorial introduction to the collection. " * 10)]
    for n in range(1, 6):
        pairs.append((f"Chapter {n}", body))
        pairs.append(("Elucidation", elu))
    boundaries, text = _build_chaptered(pairs)
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    chapters = [s for s in sections if s.type == "chapter"]
    assert chapters and all(c.mask_as == "translation" for c in chapters)
    on = masked_intervals(sections, {**DEFAULT_MASK_BY_TYPE, "translation": True}, len(text))
    off = masked_intervals(sections, {**DEFAULT_MASK_BY_TYPE, "translation": False}, len(text))
    mid = (chapters[0].start + chapters[0].end) // 2
    assert any(a <= mid < b for a, b in on)        # masked when the translation layer is on
    assert not any(a <= mid < b for a, b in off)   # shown when the layer is off


def test_plain_chaptered_work_has_no_translation_mask_layer():
    # Without patristic signposts, a chaptered work is not a translation edition — its chapters
    # carry no mask_as override and stay analyzable.
    body = "Ordinary chapter prose continues here for a while. " * 30
    boundaries, text = _build_chaptered([(f"Chapter {n}", body) for n in range(1, 7)])
    sections = detect_layout_sections(boundaries, text_len=len(text), text=text)
    chapters = [s for s in sections if s.type == "chapter"]
    assert chapters and all(c.mask_as is None for c in chapters)


def test_detect_siglum_regions_masks_corpus_excluding_catalog():
    # A Qumran-siglum corpus (the Dead Sea Scrolls): scrolls headed by sigla cluster into
    # one translation span, while the trailing dense manuscript catalogue (its own run,
    # set off by a body-scale gap) is rejected by the density cap so the apparatus is not
    # masked as translated text.
    scroll = "1 And the Instructor spoke concerning the way of the community. " * 40
    body = "\n\n".join(f"4Q{500 + i}\n\n{scroll}" for i in range(8))
    text = "Introduction to the scrolls.\n\n" + body + "\n\n"
    text += "A closing editorial discussion with no sigla at all. " * 400  # > run-gap
    text += "\n"
    catalog_start = len(text)
    text += "\n".join(f"4Q{n}" for n in range(200, 400))  # dense manuscript index
    regions = detect_siglum_regions(text, 0, len(text))
    assert len(regions) == 1
    start, end = regions[0]
    assert start < catalog_start            # the translated scrolls are covered
    assert end <= catalog_start             # the dense catalogue is excluded


def test_manuscript_catalog_classified_as_index():
    # A manuscript catalogue/list is index-type back matter, not a body division.
    assert _classify_heading("List of the Manuscripts from Qumran") == "index"
    assert _classify_heading("Catalogue of Manuscripts") == "index"
    assert _classify_heading("Chapter 4") != "index"
