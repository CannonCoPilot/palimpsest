"""Verse coordinate index — a reference-based position layer atop raw character offsets.

For scripture that prints line-anchored ``chapter:verse.`` markers (e.g. the Douay-Rheims:
``1:1. In the beginning…``), this derives one record per verse straight from the text:

    {book, chapter, verse, num_start, num_end, text_start, text_end}

The ``num`` span is the ``C:V.`` marker token (masked from analysis via the verse-number
interval layer); the ``text`` span is the verse prose (analysed). Keyed by (book, chapter,
verse), the index lets a verse be addressed by *reference* — so DR John 3:16 can be located,
and aligned to another edition's John 3:16, without character-level full-text alignment.

The index is the single source: the lazy verse *track* renders from it, and the verse-number
*mask layer* is the union of its ``num`` spans. Detection is purely text-based, so a work with
no ``C:V.`` markers simply yields an empty index (no verses), and the layer is a no-op.
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


def detect_verses(text: str) -> list[dict[str, Any]]:
    """Verse index records for ``text`` (one per line-anchored ``C:V.`` verse).

    Returns ``[{book, chapter, verse, num_start, num_end, text_start, text_end}]`` in document
    order. ``book`` is the most recent preceding chapter-heading's book name (``""`` if none).
    """
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


def verse_number_intervals(records: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """The masked verse-number token spans — the ``C:V.`` markers — as [start, end) pairs.

    This is the verse-number interval mask-layer: union it into ``masked_intervals`` (via its
    ``extra_masked`` parameter) to exclude verse numbers from analysis while leaving the verse
    prose intact.
    """
    return [(r["num_start"], r["num_end"]) for r in records]
