"""Column-aware extractor for the 2013 LDS Triple Combination PDF (idx101).

The naive linear PDF text dump scrambles this work: per page the footnote
apparatus is emitted *before* the chapter it annotates, and the two verse
columns interleave. This module uses pymupdf block geometry to recover true
reading order and split body from apparatus, then assembles a de-scrambled
canonical text via :func:`extract_fulltext`.

It is deliberately work-specific: the band constants below are tuned to this
PDF's fixed two-column-verse-over-three-column-footnote layout, validated to
the exact canon (Book of Mormon 239 chapters, D&C 138 sections, PoGP 16). It is
NOT a general PDF path — only idx101's ingest should route through it.

Page model (consistent across BoM / D&C / PoGP, observed empirically):
  - running header band:  y0 < HEADER_Y  ("32 / Abraham 2:1-10" = printed page# + ref)
  - footnote apparatus:   3 columns whose middle column starts at x0 ~= 159, an
                          x-band the verse body never uses. The top of the
                          apparatus = min y0 among blocks in that x-band.
  - body band:            everything between -> full-width headers (book title,
                          book summary) + two verse columns (left x0~=36,
                          right x0~=222), read left-column-then-right-column.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

HEADER_Y = 36.0      # blocks starting above this are the running head
GUTTER_X = 217.0     # split between left and right verse columns
FN_MID_LO, FN_MID_HI = 154.0, 166.0   # middle footnote column x0 signature
FN_RT_LO, FN_RT_HI = 278.0, 288.0     # right footnote column x0 signature


@dataclass
class Page:
    idx: int
    printed: str | None          # printed page number from running head
    ref: str | None              # "Abraham 2:1-10" running-head reference
    book_title: str | None = None  # set only on a book's opening page
    headers: list[str] = field(default_factory=list)   # full-width body headers
    body: list[str] = field(default_factory=list)      # verse columns, reading order
    apparatus: list[str] = field(default_factory=list)  # footnote columns


def _clean(t: str) -> str:
    return t.replace("­", "").replace("​", "").replace("\xa0", " ").strip()


def _fn_top(blocks) -> float:
    """y0 of the apparatus band = topmost block in the middle/right fn columns."""
    ys = [b[1] for b in blocks
          if FN_MID_LO <= b[0] <= FN_MID_HI or FN_RT_LO <= b[0] <= FN_RT_HI]
    return min(ys) if ys else float("inf")


def parse_page(pg) -> Page:
    raw = [b for b in pg.get_text("blocks") if b[6] == 0 and b[4].strip()]
    fn_top = _fn_top(raw)

    head_blocks, body_blocks, app_blocks = [], [], []
    for b in raw:
        y0 = b[1]
        if y0 < HEADER_Y:
            head_blocks.append(b)
        elif y0 >= fn_top - 5:
            app_blocks.append(b)
        else:
            body_blocks.append(b)

    # running head: "<printed#>\n<book chap:verse-range>". On a book's opening
    # page there is no page-number head; the top block is the book *title*
    # (no leading digit) -> promote it to a structural header instead.
    printed = ref = None
    book_title = None
    if head_blocks:
        htxt = _clean(head_blocks[0][4])
        m = re.match(r"^(\d+)\s+(.*)$", htxt, re.S)
        if m:
            printed, ref = m.group(1), m.group(2).replace("\n", " ").strip()
        else:
            book_title = htxt.replace("\n", " ").strip()

    def col(b):
        x0, x1 = b[0], b[2]
        if x0 < FN_MID_LO and x1 > GUTTER_X:
            return 0          # full-width header (spans the gutter)
        return 1 if x0 < GUTTER_X else 2   # left / right column

    full = sorted([b for b in body_blocks if col(b) == 0], key=lambda b: b[1])
    left = sorted([b for b in body_blocks if col(b) == 1], key=lambda b: b[1])
    right = sorted([b for b in body_blocks if col(b) == 2], key=lambda b: b[1])

    page = Page(idx=pg.number, printed=printed, ref=ref, book_title=book_title)
    page.headers = ([book_title] if book_title else []) + [_clean(b[4]) for b in full]
    page.body = [_clean(b[4]) for b in (left + right)]
    page.apparatus = [_clean(b[4]) for b in
                      sorted(app_blocks, key=lambda b: (b[0], b[1]))]
    return page


def extract_fulltext(pdf_path: str | Path) -> str:
    """De-scrambled canonical text: per page, headers -> body -> apparatus.

    Reading order is recovered per page (book title + full-width headers, then
    left then right verse column), and the footnote apparatus is placed *after*
    the body it annotates -- reversing the linear dump's apparatus-before-chapter
    scramble. The running-head printed#/reference (page furniture, repeated every
    page) is dropped; the book-opening title block is kept as a structural header.
    """
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    page_chunks: list[str] = []
    try:
        for i in range(doc.page_count):
            p = parse_page(doc[i])
            parts = [s for s in (*p.headers, *p.body, *p.apparatus) if s.strip()]
            if parts:
                page_chunks.append("\n\n".join(parts))
    finally:
        doc.close()
    return "\n\n".join(page_chunks)
