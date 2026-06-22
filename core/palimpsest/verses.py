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

Two marker dialects are recognised:
  * **Canonical** — line-anchored ``C:V.`` (the Challoner main text), keyed off ``X Chapter N``
    headings; safe and generic.
  * **Appendix** — the Douay-Rheims end-matter (Manasses, 3 & 4 Esdras incl. the Bensly
    fragment, and the 1582 Abdias / Jude) prints verses *inline* in three styles: bracketed
    ``[2]`` (Manasses), ``A:1.`` (Bensly), and bare ``2 `` runs (Esdras / Abdias / Jude).
    The appendix pass is gated on the DR end-matter anchors, so it is inert for other works;
    the bare-inline style is guarded by parenthetical-cross-reference exclusion and a
    monotonic-increase check to suppress false positives.
"""

from __future__ import annotations

import re
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


def detect_verses(text: str) -> list[dict[str, Any]]:
    """Verse index records for ``text``, in document order.

    Returns ``[{book, chapter, verse, num_start, num_end, text_start, text_end}]`` covering the
    canonical line-anchored ``C:V.`` verses and the Douay-Rheims appendix books. ``book`` is the
    most recent preceding chapter-heading's book name (``""`` if none); ``chapter`` is an int,
    except the Bensly fragment's ``"A"``.
    """
    records = _canonical_verses(text) + _appendix_verses(text)
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
