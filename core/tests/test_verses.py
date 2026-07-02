"""Tests for verse-coordinate detection — the Geneva ``<num>\\xa0`` dialect in particular."""

from palimpsest.verses import (
    _geneva_book_headers,
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
