"""Tests for verse-coordinate detection — the Geneva ``<num>\\xa0``, KJV ``<num> ``, and canonical
explicit-marker (``#`` / ``##``) dialects."""

from palimpsest.verses import (
    _geneva_book_headers,
    _kjv_book_headers,
    _marker_book_headers,
    _marker_verses,
    detect_verses,
    verse_number_intervals,
)

NBSP = "\xa0"


def _chapter(verses: list[int]) -> str:
    """One paragraph per verse, line-anchored ``<num>\\xa0 <prose>`` (the Geneva print form)."""
    return "\n\n".join(f"{v}{NBSP} Verse {v} prose text here for length." for v in verses)


def _geneva_sample() -> str:
    """A synthetic Geneva-format Bible with enough chapters to pass the run-density gate.

    Exercises: the copyright-page number grid (excluded), a Pentateuch wrapper with a stray "1"
    artifact on the name line (Genesis, NOT "1 Genesis"), an ordinal wrapper (1 Samuel), and a
    chapter whose lead verse is unnumbered (first marker is verse 2).
    """
    blocks = [
        "Copyright page, all rights reserved.",
        # Decrementing print-run grid — line-anchored numerals that must not be read as verses.
        f"12{NBSP}{NBSP} 11{NBSP}{NBSP} 10\n\n8{NBSP}{NBSP} 7",
        # Genesis: Pentateuch wrapper numbers the books of Moses, not Genesis; name line carries a
        # stray leading "1" print artifact.
        "THE FIRST BOOK OF MOSES, CALLED\n\n1 GENESIS",
    ]
    for _ in range(12):
        blocks.append(_chapter([1, 2, 3, 4]))
    # 1 Samuel: a genuinely-numbered book introduced by an ordinal word in the wrapper.
    blocks.append("THE FIRST BOOK OF\n\nSAMUEL")
    for c in range(12):
        # One chapter's first verse is unnumbered, so its markers start at verse 2.
        blocks.append(_chapter([2, 3, 4] if c == 0 else [1, 2, 3, 4]))
    return "\n\n".join(blocks)


def test_geneva_books_and_chapters():
    text = _geneva_sample()
    recs = detect_verses(text)
    assert recs, "Geneva dialect should fire on run-dense NBSP scripture"

    by_book: dict[str, set[int]] = {}
    for r in recs:
        by_book.setdefault(r["book"], set()).add(r["chapter"])

    assert set(by_book) == {"Genesis", "1 Samuel"}
    assert len(by_book["Genesis"]) == 12
    assert len(by_book["1 Samuel"]) == 12


def test_geneva_unnumbered_lead_verse_still_starts_a_chapter():
    text = _geneva_sample()
    recs = detect_verses(text)
    sam_ch1 = [r for r in recs if r["book"] == "1 Samuel" and r["chapter"] == 1]
    # The chapter is detected by the verse-number reset even though its first printed verse is 2.
    assert min(r["verse"] for r in sam_ch1) == 2


def test_geneva_mask_token_is_number_plus_nbsp():
    text = _geneva_sample()
    recs = detect_verses(text)
    r = next(r for r in recs if r["book"] == "Genesis" and r["chapter"] == 1 and r["verse"] == 1)
    token = text[r["num_start"]:r["num_end"]]
    assert token.startswith("1")
    assert NBSP in token
    # The verse prose (analyzable span) begins right after the masked number token.
    assert text[r["text_start"]:].startswith("Verse 1")


def test_geneva_copyright_grid_not_masked():
    text = _geneva_sample()
    intervals = verse_number_intervals(detect_verses(text))
    grid_pos = text.find(f"12{NBSP}")
    assert grid_pos >= 0
    assert not any(s <= grid_pos < e for s, e in intervals), "print-run grid must not be masked"


def test_geneva_pentateuch_wrapper_does_not_number_genesis():
    # "THE FIRST BOOK OF MOSES, CALLED / GENESIS" numbers the Pentateuch, not Genesis.
    headers = _geneva_book_headers("THE FIRST BOOK OF MOSES, CALLED\n\n1 GENESIS\n\n")
    assert [name for _, name in headers] == ["Genesis"]


def test_geneva_ordinal_wrapper_numbers_book():
    headers = _geneva_book_headers("THE SECOND EPISTLE OF\n\nJOHN\n\n")
    assert [name for _, name in headers] == ["2 John"]


def test_geneva_song_of_solomon_recovered_from_split_title():
    headers = _geneva_book_headers("AN 1 EXCELLENT\n\nSONG\n\nWHICH WAS SOLOMON'S\n\n")
    assert ("Song of Solomon" in [name for _, name in headers])


def test_non_scripture_text_yields_no_verses():
    prose = "\n\n".join("It was a bright cold day in April and the clocks were striking." for _ in range(50))
    assert detect_verses(prose) == []


# --- KJV dialect (regular-space verse markers, reset-chaptered) ----------------------------

# Enough distinct book-name lines to clear the canon gate (_KJV_MIN_BOOKS); "1. Samuel" exercises
# the ordinal-with-period spelling the epub prints.
_KJV_BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Joshua", "Judges", "Ruth", "1. Samuel"]


def _kjv_chapter(book: str, ch: int, verses: list[int]) -> str:
    """A ``BookName N`` heading line then one paragraph per verse, line-anchored ``<num> <prose>``
    (the KJV print form after PROFILE_KJV splits the chapter paragraph)."""
    body = "\n\n".join(f"{v} Verse {v} prose text here for length." for v in verses)
    return f"{book} {ch}\n\n{body}"


def _kjv_sample() -> str:
    """A synthetic KJV-format Bible: bare book-name lines, ``BookName N`` chapter headings, and
    regular-space verse markers, with enough chapters/books to pass both density gates."""
    blocks: list[str] = []
    for book in _KJV_BOOKS:
        blocks.append(book)  # bare book-name (h1) line
        for ch in range(1, 4):
            blocks.append(_kjv_chapter(book, ch, [1, 2, 3, 4]))
    return "\n\n".join(blocks)


def test_kjv_books_and_chapters():
    text = _kjv_sample()
    recs = detect_verses(text)
    assert recs, "KJV dialect should fire on run-dense regular-space scripture"

    by_book: dict[str, set[int]] = {}
    for r in recs:
        by_book.setdefault(r["book"], set()).add(r["chapter"])

    # The ordinal "1. Samuel" heading normalises to "1 Samuel"; every book has its 3 chapters.
    assert set(by_book) == {"Genesis", "Exodus", "Leviticus", "Numbers",
                            "Joshua", "Judges", "Ruth", "1 Samuel"}
    assert all(len(chs) == 3 for chs in by_book.values())


def test_kjv_mask_token_is_number_plus_regular_space():
    text = _kjv_sample()
    recs = detect_verses(text)
    r = next(r for r in recs if r["book"] == "Genesis" and r["chapter"] == 1 and r["verse"] == 1)
    token = text[r["num_start"]:r["num_end"]]
    assert token.startswith("1")
    assert " " in token and NBSP not in token  # regular space, unlike Geneva's NBSP
    # The verse prose (analyzable span) begins right after the masked number token.
    assert text[r["text_start"]:].startswith("Verse 1")


def test_kjv_ordinal_book_heading_normalized():
    headers = _kjv_book_headers("1. Samuel\n\n")
    assert [name for _, name in headers] == ["1 Samuel"]


# --- Explicit-marker dialect (canonical import format) -------------------------------------

# Books and chapters are read straight from "#"/"##" markers, so no book lexicon is needed;
# "Ecclesiasticus" is a deuterocanonical name the KJV/Geneva lexicons do not carry, proving it.
_MARKER_BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Joshua", "Judges",
                 "Ruth", "1 Samuel", "Ecclesiasticus"]


def _marker_sample() -> str:
    """A synthetic canonical-format Bible: ``# Book`` / ``## Book N`` / ``<num> prose`` blocks,
    with enough books and chapters to pass both density gates."""
    blocks: list[str] = []
    for book in _MARKER_BOOKS:
        blocks.append(f"# {book}")
        for ch in range(1, 4):
            blocks.append(f"## {book} {ch}")
            for v in range(1, 5):
                blocks.append(f"{v} Verse {v} of chapter {ch} prose text here.")
    return "\n\n".join(blocks)


def test_marker_books_and_chapters():
    text = _marker_sample()
    recs = detect_verses(text)
    assert recs, "explicit-marker dialect should fire on #/##-marked scripture"

    by_book: dict[str, set[int]] = {}
    for r in recs:
        by_book.setdefault(r["book"], set()).add(r["chapter"])

    # Names are read verbatim from the markers — including the deuterocanonical book no lexicon has.
    assert set(by_book) == set(_MARKER_BOOKS)
    assert all(chs == {1, 2, 3} for chs in by_book.values())


def test_marker_mask_token_is_number_plus_space():
    text = _marker_sample()
    recs = detect_verses(text)
    r = next(r for r in recs if r["book"] == "Genesis" and r["chapter"] == 1 and r["verse"] == 1)
    assert text[r["num_start"]:r["num_end"]] == "1 "  # number plus its trailing space
    assert text[r["text_start"]:].startswith("Verse 1")  # prose begins after the masked token


def test_marker_book_headers_verbatim_lexicon_free():
    headers = _marker_book_headers("# Ecclesiasticus\n\n## Ecclesiasticus 1\n\n1 Prose.\n\n")
    assert [name for _, name in headers] == ["Ecclesiasticus"]


def test_marker_inert_below_density_gate():
    # A handful of "#"/"##" lines — far below the book/chapter density gates — so the dialect stays
    # inert and an incidental markdown-ish document is never mis-read as scripture.
    text = "# Intro\n\n## Notes 1\n\n1 A numbered item, not a verse.\n\n2 Another item."
    assert _marker_verses(text) == []


def _marker_harmony_sample() -> str:
    """A 4-book Gospel harmony in canonical-marker format: below the old 8-book floor but well
    above the 20-chapter guard, so the dialect must fire (partial canons are still scripture)."""
    blocks: list[str] = []
    for book in ["Matthew", "Mark", "Luke", "John"]:
        blocks.append(f"# {book}")
        for ch in range(1, 7):  # 4 books x 6 chapters = 24 chapters (>= 20)
            blocks.append(f"## {book} {ch}")
            for v in range(1, 4):
                blocks.append(f"{v} Verse {v} of {book} chapter {ch}.")
    return "\n\n".join(blocks)


def test_marker_gospel_harmony_fires_partial_canon():
    # 4 books is below the old 8-book floor but a Gospel harmony is genuine scripture; the
    # 20-chapter guard (24 here) is what confirms it, so the marker dialect must fire.
    recs = detect_verses(_marker_harmony_sample())
    assert {r["book"] for r in recs} == {"Matthew", "Mark", "Luke", "John"}
    assert all(r["chapter"] in range(1, 7) for r in recs)


def test_marker_chapter_gate_still_guards_book_rich_doc():
    # 4 "# " headings but only 8 "## " lines: clears the book floor yet fails the 20-chapter
    # guard, so an incidental structured doc is still never mis-read as scripture.
    blocks: list[str] = []
    for book in ["Alpha", "Beta", "Gamma", "Delta"]:
        blocks.append(f"# {book}")
        for ch in range(1, 3):  # 4 x 2 = 8 chapters (< 20)
            blocks.append(f"## {book} {ch}")
            blocks.append(f"1 A line under {book} {ch}.")
    assert _marker_verses("\n\n".join(blocks)) == []
