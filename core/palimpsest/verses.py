"""Verse coordinate index — a reference-based position layer atop raw character offsets.

For scripture that prints line-anchored ``chapter:verse.`` markers (e.g. the Douay-Rheims:
``1:1. In the beginning…``), this derives one record per verse straight from the text:

    {book, chapter, verse, num_start, num_end, text_start, text_end}

The ``num`` span is the verse-number marker token (masked from analysis via the verse-number
interval layer); the ``text`` span is the verse prose (analysed). Keyed by (book, chapter,
verse), the index lets a verse be addressed by *reference* — so DR John 3:16 can be located,
and aligned to another edition's John 3:16, without character-level full-text alignment.

The index is the single source: the lazy verse *track* renders from it, and the verse-number
*mask layer* is the union of its ``num`` spans. Detection is purely text-based, so a work with
no recognised verse markers simply yields an empty index (no verses), and the layer is a no-op.

Four marker dialects are recognised:
  * **Canonical** — line-anchored ``C:V.`` (the Challoner main text), keyed off ``X Chapter N``
    headings; safe and generic.
  * **Appendix** — the Douay-Rheims end-matter (Manasses, 3 & 4 Esdras incl. the Bensly
    fragment, and the 1582 Abdias / Jude) prints verses *inline* in three styles: bracketed
    ``[2]`` (Manasses), ``A:1.`` (Bensly), and bare ``2 `` runs (Esdras / Abdias / Jude).
    The appendix pass is gated on the DR end-matter anchors, so it is inert for other works;
    the bare-inline style is guarded by parenthetical-cross-reference exclusion and a
    monotonic-increase check to suppress false positives.
  * **Geneva (1599)** — no ``C:V.`` markers or ``Chapter N`` headings: each verse is a
    paragraph line-anchored ``<num>\xa0`` (non-breaking space); chapters are inferred from
    verse-number resets and books from bare upper-case name lines.
  * **KJV** — after the import splits each chapter paragraph into one paragraph per verse (see
    ``content_filters.PROFILE_KJV``), verses are line-anchored ``<num> `` (regular space).
    Chapters are inferred from verse-number resets (like Geneva); books from the mixed-case
    ``Genesis`` / ``1. Samuel`` heading lines the epub already carries.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# A line-anchored "C:V." marker: chapter:verse, a period, then spacing. The whole match
# (including trailing spaces) is the masked number token; the verse prose follows.
_VERSE_NUM_LINE = re.compile(r"(?m)^(\d{1,3}):(\d{1,3})\.[ \t]*")
# A chapter heading naming its book ("Genesis Chapter 1", "1 Kings Chapter 5"); the text
# before " Chapter " is the book name each following verse inherits until the next heading.
_CHAPTER_HEADING = re.compile(r"(?m)^.{0,40}?\bChapter \d+\b")


def _canonical_verses(text: str) -> list[dict[str, Any]]:
    """One record per line-anchored ``C:V.`` verse (the Challoner main text)."""
    headers: list[tuple[int, str]] = []  # (position, book) — verses inherit the latest book
    for m in _CHAPTER_HEADING.finditer(text):
        nl = text.find("\n", m.start())
        line = text[m.start(): nl if nl >= 0 else m.start() + 60]
        headers.append((m.start(), line.partition(" Chapter ")[0].strip()))

    records: list[dict[str, Any]] = []
    hi = 0
    cur_book = ""
    for m in _VERSE_NUM_LINE.finditer(text):
        num_start, num_end = m.start(), m.end()
        while hi < len(headers) and headers[hi][0] <= num_start:
            cur_book = headers[hi][1]
            hi += 1
        para_end = text.find("\n\n", num_end)
        records.append({
            "book": cur_book,
            "chapter": int(m.group(1)),
            "verse": int(m.group(2)),
            "num_start": num_start,
            "num_end": num_end,
            "text_start": num_end,
            "text_end": para_end if para_end >= 0 else len(text),
        })
    return records


# --- Appendix (Douay-Rheims end-matter) verse detection -------------------------------

# End-matter anchors (each unique in the DR text). Their presence gates the appendix pass.
_APX = dict(
    comparison="BOOKS FOR COMPARISON",
    supplemental="SUPPLEMENTAL MATERIAL",
    manasses="THE PRAYER OF MANASSES",
    esdras3="THE THIRD BOOKE OF ESDRAS",
    esdras4="THE FOVRTH BOOKE OF ESDRAS",
    bensly="Note: This translation comes from the Latin text",
    abdias="THE PROPHECIE OF ABDIAS",
    jude="THE CATHOLIKE EPISTLE OF IVDE",
)
_APX_CHAP = re.compile(r"(?m)^CHAP\. ([IVXLC]+)\.")
_V_BRACKET = re.compile(r"\[(\d{1,3})\]")                       # Manasses "[2]"
_V_BENSLY = re.compile(r"\bA:(\d{1,3})\.")                      # Bensly fragment "A:2."
# A bare inline verse number: digits at a clause boundary, whitespace, then a word — e.g.
# "battel. 2 Behold". A number followed by a period ("7.") is an argument cross-reference,
# not a verse marker, so it does not match.
_V_INLINE = re.compile(r"(?:(?<=^)|(?<=[\s.;:&]))(\d{1,3})\s+(?=[A-Za-z'\"&])")
_ROM = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _roman(s: str) -> int:
    total = prev = 0
    for ch in reversed(s):
        v = _ROM[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def _second_para(text: str, pos: int) -> int:
    """Offset after the 2nd ``\\n\\n`` from pos (heading P0, argument P1 → verse body P2)."""
    p0 = text.find("\n\n", pos)
    if p0 < 0:
        return pos
    p1 = text.find("\n\n", p0 + 2)
    return (p1 + 2) if p1 >= 0 else (p0 + 2)


def _ref_zones(seg: str) -> list[tuple[int, int]]:
    """Top-level parenthesis spans — scripture cross-references like ``(2 Par 35:1)`` whose
    digits must not be mistaken for verse numbers when splitting an inline-numbered body."""
    zones: list[tuple[int, int]] = []
    depth = start = 0
    for i, ch in enumerate(seg):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1
            if depth == 0:
                zones.append((start, i + 1))
    return zones


def _markers(seg: str, base: int, style: str) -> list[tuple[int, int, int]]:
    """Verse-number markers in a chapter body as (verse_number, num_start, num_end), absolute.

    ``num_end`` ends after any trailing whitespace so the masked token mirrors the canonical
    ``C:V. `` span (number glyphs + trailing space). Bare-inline markers exclude digits inside
    cross-reference parentheses and, when there are several, must mostly increase to count."""
    if style == "bracket":
        ms = [(int(m.group(1)), base + m.start(), base + m.end()) for m in _V_BRACKET.finditer(seg)]
    elif style == "bensly":
        ms = [(int(m.group(1)), base + m.start(), base + m.end()) for m in _V_BENSLY.finditer(seg)]
    else:  # inline
        zones = _ref_zones(seg)
        ms = [
            (int(m.group(1)), base + m.start(1), base + m.end())
            for m in _V_INLINE.finditer(seg)
            if not any(a <= m.start(1) < b for a, b in zones)
        ]
        nums = [n for n, _, _ in ms]
        if len(nums) >= 3:
            inc = sum(1 for a, b in zip(nums, nums[1:]) if b > a) / (len(nums) - 1)
            if inc < 0.7:
                ms = []
    if style in ("bracket", "bensly"):
        ext: list[tuple[int, int, int]] = []
        for num, ns, ne in ms:
            while ne - base < len(seg) and seg[ne - base] in " \t":
                ne += 1
            ext.append((num, ns, ne))
        ms = ext
    return ms


def _chapter_verses(
    text: str, book: str, chapter: Any, v1: int, c_end: int, style: str
) -> list[dict[str, Any]]:
    """Records for one appendix chapter body [v1, c_end). The lead verse is unnumbered in the
    print (verse 1 begins the body), so it is emitted with a zero-width ``num`` span unless the
    first printed marker is already verse 1 (the Bensly fragment, which starts at A:1)."""
    if v1 >= c_end:
        return []
    markers = _markers(text[v1:c_end], v1, style)

    def rec(verse: int, ns: int, ne: int, ts: int, te: int) -> dict[str, Any]:
        return {"book": book, "chapter": chapter, "verse": verse,
                "num_start": ns, "num_end": ne, "text_start": ts, "text_end": te}

    out: list[dict[str, Any]] = []
    if not markers or markers[0][0] > 1:
        first = markers[0][1] if markers else c_end
        out.append(rec(1, v1, v1, v1, first))
    for i, (num, ns, ne) in enumerate(markers):
        nxt = markers[i + 1][1] if i + 1 < len(markers) else c_end
        out.append(rec(num, ns, ne, ne, nxt))
    return out


def _single_chapter(text: str, book: str, b_start: int, b_end: int, has_arg: bool, style: str
                    ) -> list[dict[str, Any]]:
    """A one-chapter appendix book (Manasses prayer; 1582 Abdias / Jude)."""
    if has_arg:
        v1 = _second_para(text, b_start)
    else:
        nl = text.find("\n\n", b_start)
        v1 = (nl + 2) if nl >= 0 else b_start
    return _chapter_verses(text, book, 1, min(v1, b_end), b_end, style)


def _chaptered_book(text: str, book: str, b_start: int, b_end: int, bensly: int
                    ) -> list[dict[str, Any]]:
    """A ``CHAP. <ROMAN>.``-chaptered appendix book (3 / 4 Esdras), plus the trailing Bensly
    fragment when it falls in this book's span (it is the 4 Esdras continuation, chapter "A")."""
    chaps = [(m.start(), m.group(1)) for m in _APX_CHAP.finditer(text) if b_start <= m.start() < b_end]
    markers = chaps + ([(bensly, "A")] if b_start <= bensly < b_end else [])
    markers.sort()
    out: list[dict[str, Any]] = []
    for j, (cs, rom) in enumerate(markers):
        c_end = markers[j + 1][0] if j + 1 < len(markers) else b_end
        if rom == "A":
            nl = text.find("\n\n", cs)
            v1 = (nl + 2) if nl >= 0 else cs
            out += _chapter_verses(text, book, "A", min(v1, c_end), c_end, "bensly")
        else:
            out += _chapter_verses(text, book, _roman(rom), min(_second_para(text, cs), c_end), c_end, "inline")
    return out


def _appendix_verses(text: str) -> list[dict[str, Any]]:
    """Verse records for the Douay-Rheims appendix books, or ``[]`` if this is not that corpus."""
    pos = {k: text.find(v) for k, v in _APX.items()}
    if pos["manasses"] < 0:
        return []  # not the DR end-matter — appendix pass is inert
    out: list[dict[str, Any]] = []
    if pos["esdras3"] > pos["manasses"]:
        out += _single_chapter(text, "Prayer of Manasses", pos["manasses"], pos["esdras3"], False, "bracket")
    if 0 <= pos["esdras3"] < pos["esdras4"]:
        out += _chaptered_book(text, "Third Booke of Esdras", pos["esdras3"], pos["esdras4"], pos["bensly"])
    end4 = pos["comparison"] if pos["comparison"] > 0 else pos["supplemental"]
    if 0 <= pos["esdras4"] < end4:
        out += _chaptered_book(text, "Fourth Booke of Esdras", pos["esdras4"], end4, pos["bensly"])
    if 0 <= pos["abdias"] < pos["jude"]:
        out += _single_chapter(text, "Abdias (1582)", pos["abdias"], pos["jude"], True, "inline")
    if 0 <= pos["jude"] < pos["supplemental"]:
        out += _single_chapter(text, "Jude (1582)", pos["jude"], pos["supplemental"], True, "inline")
    return out


# --- Geneva (1599) verse detection --------------------------------------------------------
#
# The 1599 Geneva Bible prints no line-anchored "C:V." markers and no "Chapter N" headings, so
# neither the canonical nor the appendix pass sees it. Instead each verse is its own paragraph,
# line-anchored "<num>\xa0 <prose>" — the verse number followed by a NON-BREAKING SPACE (U+00A0),
# which the chapter *argument* paragraphs (digit + a regular space) never use, so the two never
# collide. A chapter carries no printed heading: it is a run of verses whose numbering starts at
# 1 and increases; the next reset to 1 begins the next chapter. Book names print as bare
# upper-case lines ("MATTHEW") or wrapper blocks ("THE FIRST BOOK OF MOSES, CALLED\nGENESIS").
_GENEVA_VERSE_LINE = re.compile(r"(?m)^(\d{1,3})\xa0+[ \t]*")
_GENEVA_MIN_CHAPTERS = 20  # this many reset-anchored verse runs ⇒ Geneva-style scripture
_GENEVA_MIN_CHAPTER_VERSES = 2  # a real chapter has ≥2 verses; filters stray front-matter numerals
# An upper-case standalone line naming a book. Geneva prefixes many name lines with a stray "1 "
# print artifact ("1 GENESIS", "1 PSALMS", "1 CHRONICLES,"), so an optional leading numeral is
# consumed before the name. The wrapper block that introduces an ordinal ("THE FIRST BOOK OF … /
# SAMUEL") is itself an upper-case line, so it is captured as the *preceding* caps line.
_GENEVA_CAPS_LINE = re.compile(r"(?m)^(?:\d{1,3}[ \xa0]+)?([A-Z][A-Z0-9 ,.'’&-]{1,45})$")
_GENEVA_ORDINAL_WORD = re.compile(r"\b(FIRST|SECOND|THIRD|FOURTH)\b")
_GENEVA_ORD_VALUE = {"FIRST": "1", "SECOND": "2", "THIRD": "3", "FOURTH": "4"}
# Only these bases are actually numbered in the canon. Gates out false ordinals: "THE FIRST BOOK
# OF MOSES, CALLED GENESIS" numbers the Pentateuch, not Genesis, so Genesis must not become
# "1 Genesis"; likewise "THE 1 GENERAL EPISTLE OF JAMES" must stay "James".
_GENEVA_NUMBERED_BASES = frozenset({
    "samuel", "kings", "chronicles", "paralipomenon", "corinthians", "thessalonians",
    "timothy", "peter", "john", "esdras", "maccabees", "machabees",
})


def _geneva_book_headers(text: str) -> list[tuple[int, str]]:
    """(position, display-name) for Geneva book-name lines, in document order.

    Matches standalone upper-case lines against the scripture-book lexicon. For a canonically
    numbered book (1/2 Samuel, 1/2/3 John, …) an ordinal *word* in the immediately preceding
    wrapper line ("THE SECOND EPISTLE OF … / JOHN") is folded in so the members stay distinct;
    the ordinal is applied only to numbered bases, so the Pentateuch's "FIRST BOOK OF MOSES" and
    a stray "1" artifact never mis-number Genesis or James. Non-book caps lines (front-matter
    titles, Psalm 119 Hebrew acrostic labels) don't match the lexicon and are dropped.
    """
    from palimpsest.layout import _match_bible_book

    prev_line = ""
    out: list[tuple[int, str]] = []
    for m in _GENEVA_CAPS_LINE.finditer(text):
        line = m.group(1).strip()
        name = _match_bible_book(line)
        # Song of Solomon prints its title across three lines ("AN 1 EXCELLENT / SONG / WHICH WAS
        # SOLOMON'S"); the bare "SONG" line isn't in the lexicon, so recover it from the SOLOMON
        # that follows.
        if not name and line == "SONG" and "SOLOMON" in text[m.end():m.end() + 60]:
            name = "Song of Solomon"
        if name and not name[0].isdigit() and name.lower() in _GENEVA_NUMBERED_BASES:
            om = _GENEVA_ORDINAL_WORD.search(prev_line)
            if om:
                name = f"{_GENEVA_ORD_VALUE[om.group(1)]} {name}"
        if name:
            out.append((m.start(), name))
        prev_line = line
    return out


def _geneva_verses(text: str) -> list[dict[str, Any]]:
    """One record per Geneva "<num>\\xa0 <prose>" verse, chaptered by verse-number resets.

    Returns ``[]`` unless the text carries enough reset-anchored verse runs to be Geneva-style
    scripture (so this pass is inert for every other corpus). Verse numbers reset to 1 at each
    chapter; chapters are numbered sequentially within each book. The masked ``num`` token spans
    the number plus its trailing non-breaking/regular spaces, mirroring the canonical ``C:V. ``
    span so the verse prose stays analyzable.
    """
    markers = [(m.start(), m.end(), int(m.group(1))) for m in _GENEVA_VERSE_LINE.finditer(text)]
    if not markers:
        return []

    # Group into chapters by verse-number resets: a chapter is a maximal run of increasing verse
    # numbers. A marker that does not exceed its predecessor starts a new chapter — normally a
    # reset to 1, or to 2 when the chapter's first verse is unnumbered (Obadiah embeds verse 1 in
    # its argument; 19 Proverbs chapters and 3 of Lamentations print no verse-1 numeral). The
    # decrementing print-run grids on the copyright page ("12 … 8 … 7") fall into length-1 runs.
    # Runs shorter than the minimum are discarded.
    runs: list[list[tuple[int, int, int]]] = []
    cur: list[tuple[int, int, int]] = []
    for mk in markers:
        if cur and mk[2] <= cur[-1][2]:
            runs.append(cur)
            cur = []
        cur.append(mk)
    if cur:
        runs.append(cur)
    chapters = [r for r in runs if len(r) >= _GENEVA_MIN_CHAPTER_VERSES]
    if len(chapters) < _GENEVA_MIN_CHAPTERS:
        return []

    headers = _geneva_book_headers(text)
    records: list[dict[str, Any]] = []
    hi = 0
    cur_book = ""
    chapter_in_book = 0
    for run in chapters:
        c_start = run[0][0]
        # Advance the book cursor to the latest header preceding this chapter; a new book resets
        # the per-book chapter counter.
        while hi < len(headers) and headers[hi][0] <= c_start:
            if headers[hi][1] != cur_book:
                cur_book = headers[hi][1]
                chapter_in_book = 0
            hi += 1
        chapter_in_book += 1
        for k, (ns, num_end, verse) in enumerate(run):
            nxt = run[k + 1][0] if k + 1 < len(run) else None
            para_end = text.find("\n\n", num_end)
            if para_end < 0:
                para_end = len(text)
            text_end = min(nxt, para_end) if nxt is not None else para_end
            records.append({
                "book": cur_book,
                "chapter": chapter_in_book,
                "verse": verse,
                "num_start": ns,
                "num_end": num_end,
                "text_start": num_end,
                "text_end": text_end,
            })
    return records


# --- KJV verse detection ------------------------------------------------------------------
#
# The KJV epub packs a whole chapter into one <p> with inline "<span class=verses>N</span>"
# markers; PROFILE_KJV splits that paragraph so each verse becomes its own paragraph,
# line-anchored "<num> <prose>" — the verse number followed by a REGULAR space (unlike Geneva's
# non-breaking space). The epub carries real book ("Genesis", "1. Samuel") and chapter
# ("Genesis 1") headings, but the printed heading text is format-quirky ("1. Samuel" with a
# period), so chapters are inferred from verse-number resets (robust and format-free, like
# Geneva) while books are read from the bare mixed-case name lines the headings leave in the text.
_KJV_VERSE_LINE = re.compile(r"(?m)^(\d{1,3})[ \t]+")
_KJV_MIN_CHAPTERS = 20  # this many reset-anchored verse runs ⇒ KJV-style scripture
_KJV_MIN_CHAPTER_VERSES = 2  # a real chapter has ≥2 verses; filters stray front-matter numerals
_KJV_MIN_BOOKS = 8  # this many distinct book-name lines ⇒ a scripture canon, not incidental text
# A standalone book-name line: the whole line is a book name, optionally prefixed by an ordinal
# printed "1. " / "2. " (period or space separator). It ends in letters — never a trailing chapter
# number — so chapter headings ("Genesis 1") and verse lines ("1 In the beginning…") never match.
_KJV_BOOK_LINE = re.compile(r"(?m)^((?:[123][.\s]+)?[A-Za-z][A-Za-z’' ]{1,40})$")
_KJV_BOOK_ORDINAL = re.compile(r"^([123])[.\s]+(.+)$")


def _kjv_book_name(line: str) -> str | None:
    """Canonical display name if ``line`` is a KJV book heading, else None.

    Normalises the epub's "1. Samuel" ordinal spelling to "1 Samuel" so the shared book lexicon
    (which accepts "1 Samuel" / "Second Kings" style) resolves the numbered books.
    """
    from palimpsest.layout import _match_bible_book

    s = line.strip()
    m = _KJV_BOOK_ORDINAL.match(s)
    return _match_bible_book(f"{m.group(1)} {m.group(2)}" if m else s)


def _kjv_book_headers(text: str) -> list[tuple[int, str]]:
    """(position, display-name) for KJV book-name lines, in document order."""
    out: list[tuple[int, str]] = []
    for m in _KJV_BOOK_LINE.finditer(text):
        name = _kjv_book_name(m.group(1))
        if name:
            out.append((m.start(), name))
    return out


def _kjv_verses(text: str) -> list[dict[str, Any]]:
    """One record per KJV "<num> <prose>" verse, chaptered by verse-number resets.

    Returns ``[]`` unless the text carries enough reset-anchored verse runs *and* book-name lines
    to be KJV-style scripture, so this pass is inert for every other corpus (and, in particular,
    Geneva — whose verses use a non-breaking space and so never match ``_KJV_VERSE_LINE``). Verse
    numbers reset to 1 at each chapter; chapters are numbered sequentially within each book. The
    masked ``num`` token spans the number plus its trailing spaces so the verse prose stays
    analyzable, mirroring the Douay-Rheims ``C:V. `` treatment.
    """
    markers = [(m.start(), m.end(), int(m.group(1))) for m in _KJV_VERSE_LINE.finditer(text)]
    if not markers:
        return []

    # Group into chapters by verse-number resets: a chapter is a maximal run of increasing verse
    # numbers; a marker that does not exceed its predecessor starts a new chapter. Runs shorter
    # than the minimum (stray front-matter numerals) are discarded.
    runs: list[list[tuple[int, int, int]]] = []
    cur: list[tuple[int, int, int]] = []
    for mk in markers:
        if cur and mk[2] <= cur[-1][2]:
            runs.append(cur)
            cur = []
        cur.append(mk)
    if cur:
        runs.append(cur)
    chapters = [r for r in runs if len(r) >= _KJV_MIN_CHAPTER_VERSES]
    if len(chapters) < _KJV_MIN_CHAPTERS:
        return []

    headers = _kjv_book_headers(text)
    if len({name for _, name in headers}) < _KJV_MIN_BOOKS:
        return []

    records: list[dict[str, Any]] = []
    hi = 0
    cur_book = ""
    chapter_in_book = 0
    for run in chapters:
        c_start = run[0][0]
        # Advance the book cursor to the latest header preceding this chapter; a new book resets
        # the per-book chapter counter.
        while hi < len(headers) and headers[hi][0] <= c_start:
            if headers[hi][1] != cur_book:
                cur_book = headers[hi][1]
                chapter_in_book = 0
            hi += 1
        chapter_in_book += 1
        for k, (ns, num_end, verse) in enumerate(run):
            nxt = run[k + 1][0] if k + 1 < len(run) else None
            para_end = text.find("\n\n", num_end)
            if para_end < 0:
                para_end = len(text)
            text_end = min(nxt, para_end) if nxt is not None else para_end
            records.append({
                "book": cur_book,
                "chapter": chapter_in_book,
                "verse": verse,
                "num_start": ns,
                "num_end": num_end,
                "text_start": num_end,
                "text_end": text_end,
            })
    return records


def detect_verses(text: str) -> list[dict[str, Any]]:
    """Verse index records for ``text``, in document order.

    Returns ``[{book, chapter, verse, num_start, num_end, text_start, text_end}]`` covering the
    canonical line-anchored ``C:V.`` verses, the Douay-Rheims appendix books, and the Geneva /
    KJV reset-chaptered dialects. ``book`` is the most recent preceding book heading's name
    (``""`` if none); ``chapter`` is an int, except the Bensly fragment's ``"A"``.
    """
    records = _canonical_verses(text) + _appendix_verses(text)
    # DR prints "C:V." markers; Geneva and KJV do not, so the canonical/appendix passes yield
    # nothing for them. Fall back to the reset-chaptered dialects only then — Geneva first (its
    # non-breaking-space markers never match the KJV regular-space regex, so the two are mutually
    # exclusive), each self-gating on run/book density so both stay inert for every other corpus.
    if not records:
        records = _geneva_verses(text) or _kjv_verses(text)
    records.sort(key=lambda r: (r["num_start"], r["text_start"]))
    return records


def verse_number_intervals(records: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """The masked verse-number token spans — the printed verse-number markers — as [start, end)
    pairs (empty spans, e.g. an unnumbered lead verse, are dropped).

    This is the verse-number interval mask-layer: union it into ``masked_intervals`` (via its
    ``extra_masked`` parameter) to exclude verse numbers from analysis while leaving the verse
    prose intact.
    """
    return [(r["num_start"], r["num_end"]) for r in records if r["num_end"] > r["num_start"]]


def cached_verse_number_intervals(project_dir: Path) -> list[tuple[int, int]] | None:
    """Verse-number mask-layer intervals from a project's cached ``tracks/verses.jsonl``.

    Returns one ``(num_start, text_start)`` pair per verse — equivalently the masked ``num``
    token spans, since each token abuts its prose (``num_end == text_start``) — or ``None`` if
    the project has no verse track, letting callers fall back to computing from text. Reading the
    cache avoids re-running ``detect_verses`` over the full reference text on every call.
    """
    track_path = project_dir / "tracks" / "verses.jsonl"
    if not track_path.exists():
        return None
    out: list[tuple[int, int]] = []
    for line in track_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            r = json.loads(line)
            out.append((r["ns"], r["s"]))
    return out


def cached_verse_text_spans(project_dir: Path) -> list[tuple[int, int]] | None:
    """Verse-prose ``[text_start, text_end)`` spans from a project's cached ``tracks/verses.jsonl``,
    in document order — the verse bodies (number tokens excluded), used as verse-mode chunk units.

    Returns ``None`` if the project has no verse track, so callers can fall back or skip verse-based
    chunking. Empty spans are dropped.
    """
    track_path = project_dir / "tracks" / "verses.jsonl"
    if not track_path.exists():
        return None
    out: list[tuple[int, int]] = []
    for line in track_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            r = json.loads(line)
            if r["e"] > r["s"]:
                out.append((r["s"], r["e"]))
    return out
