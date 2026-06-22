#!/usr/bin/env python
"""Column-aware extractor for the 2013 LDS Triple Combination PDF (idx101).

The naive linear PDF text dump scrambles this work: per page the footnote
apparatus is emitted *before* the chapter it annotates, and the two verse
columns interleave. This extractor uses pymupdf block geometry to recover true
reading order and to split body from apparatus.

Page model (consistent across BoM / D&C / PoGP, observed empirically):
  - running header band:  y0 < HEADER_Y  ("32 / Abraham 2:1-10" = printed page# + ref)
  - footnote apparatus:   3 columns whose middle column starts at x0 ~= 159, an
                          x-band the verse body never uses. The top of the
                          apparatus = min y0 among blocks in that x-band.
  - body band:            everything between -> full-width headers (book title,
                          book summary) + two verse columns (left x0~=36,
                          right x0~=222), read left-column-then-right-column.

Usage:
  lds_extract.py page <pdf_page_idx> [...]   # show reconstructed reading order
  lds_extract.py header <pdf_page_idx> [...]  # show parsed running-head ref
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field

import fitz

PDF = "imports/Scripture/BooksOfMormons/LDS_eng.pdf"

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
    return t.replace("­", "").replace(" ", "").replace("\xa0", " ").strip()


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


CH_RE = re.compile(r"^(Chapter|Section|Psalm)\s+\d+\b", re.I)
DECL_RE = re.compile(r"^OFFICIAL DECLARATION", re.I)
BOOK_RE = re.compile(
    r"^(The (First|Second|Third|Fourth) Book of |The Book of |"
    r"(Third|Fourth) Nephi$|The Words of Mormon$|"
    r"Selections from the\s+Book of Moses|"
    r"The Book of Abraham$|Joseph Smith—(Matthew|History)$|"
    r"The Articles of Faith$)",
)


def _is_book_title(first: str) -> bool:
    if "  ." in first or len(first) > 45:   # contents dot-leaders / sentences
        return False
    return bool(BOOK_RE.match(first))


def book_titles(p: Page) -> list[str]:
    """Book titles on this page, from the top band and full-width body headers."""
    out = []
    for cand in ([p.book_title] if p.book_title else []) + p.headers:
        first = cand.split("\n", 1)[0].strip()
        if first not in out and _is_book_title(first):
            out.append(first)
    return out


def chapter_labels(p: Page) -> list[str]:
    """Structural chapter/section labels appearing on this page, in order."""
    out = []
    for s in p.headers + p.body:
        first = s.split("\n", 1)[0].strip()
        if CH_RE.match(first) or DECL_RE.match(first):
            out.append(first)
    return out


def scan(doc, lo: int, hi: int):
    """Emit a compact structural skeleton: book-title + chapter/section labels."""
    for i in range(lo, hi):
        p = parse_page(doc[i])
        marks = [f"<<BOOK: {t}>>" for t in book_titles(p)]
        marks += chapter_labels(p)
        if marks:
            tag = f"p{i} (pr.{p.printed or '-'}|{p.ref or ''})"
            print(f"{tag:42} {' | '.join(marks)}")


NUM_RE = re.compile(r"^(?:Chapter|Section|Psalm)\s+(\d+)", re.I)


def books(doc, lo: int, hi: int):
    """Per-book chapter/section count + page span (max sequential number)."""
    cur = None
    rows = []
    for i in range(lo, hi):
        p = parse_page(doc[i])
        for t in book_titles(p):
            cur = {"title": t, "start": i, "printed_start": p.printed, "maxch": 0}
            rows.append(cur)
        if cur is None:
            continue
        cur["end"] = i
        for lab in chapter_labels(p):
            m = NUM_RE.match(lab)
            if m:
                cur["maxch"] = max(cur["maxch"], int(m.group(1)))
            elif lab.upper().startswith("OFFICIAL"):
                cur.setdefault("decls", 0)
                cur["decls"] += 1
    for r in rows:
        span = f"p{r['start']}-{r.get('end', r['start'])}"
        extra = f" +{r['decls']} decl" if r.get("decls") else ""
        print(f"  {r['title'][:38]:40} {span:14} chapters={r['maxch']}{extra}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "page"
    doc = fitz.open(PDF)
    if cmd in ("scan", "books"):
        lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        hi = int(sys.argv[3]) if len(sys.argv) > 3 else doc.page_count
        (scan if cmd == "scan" else books)(doc, lo, hi)
        return
    idxs = [int(a) for a in sys.argv[2:]] or [19]
    for i in idxs:
        p = parse_page(doc[i])
        print(f"\n===== pdf page {i}  printed={p.printed!r}  ref={p.ref!r} =====")
        if cmd == "header":
            continue
        print("  -- HEADERS (full-width) --")
        for h in p.headers:
            print(f"    | {h[:90]!r}")
        print("  -- BODY (reading order) --")
        for b in p.body:
            print(f"    > {b[:90]!r}")
        print(f"  -- APPARATUS ({len(p.apparatus)} blocks, first 2) --")
        for a in p.apparatus[:2]:
            print(f"    . {a[:70]!r}")


if __name__ == "__main__":
    main()
