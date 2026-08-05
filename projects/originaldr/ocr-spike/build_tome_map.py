#!/usr/bin/env python3
"""build_tome_map.py -- per-volume page->section map (task 6).

For every OCR'd source volume, record which PAGE RANGE holds each scripture book and each
frontmatter/backmatter matter-region. Reuses the detect_our_ocr locating primitives via the
consensus_v2 stream cache: `locate_region` gives a chapter's token span in a source's folded
stream, and `Stream.page` (index-aligned to `fold`) maps those tokens back to page ids.

Two tiers:
  * Tier 1 (deterministic): scripture book -> page range, per source, from chapter locates.
  * Tier 2 (structural): matter regions (ot_front/ot_back/nt_front/nt_back) bounded by the
    located book spans -- the non-scripture pages before/between/after the books. Reference-doc
    (title-page, preface, censura, ...) labelling within those regions is left to a best-effort
    pass (see label_reference_docs) since those sections are not in the scripture grid.

Run:  core/.venv/bin/python build_tome_map.py            # all sources -> tome-map.json
      core/.venv/bin/python build_tome_map.py --source pdf-S03a   # one source, verbose
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import consensus_v2 as C  # noqa: E402  # type: ignore[import-not-found]  # harness: streams+anchor
D = C.D                    # detect_our_ocr module (locate_region, _probe, _page_index, _BOOK_*)

OUT = HERE / "tome-map.json"

CH_FLOOR = 0.35     # per-CHAPTER span-quality threshold. Below it a chapter's located window is too
                    # weak to trust as a page span, so the chapter is recorded in `chapters_below_floor`
                    # (visible to qc_audit) INSTEAD of a page range. This RECORDS chapter status — it
                    # never drops a book, and weak chapters stay visible rather than silently vanishing.
# BOOK_FLOOR + NOISE_FRACTION (book-level drops) REMOVED per QC contract (Sir 2026-07-08, plan §Part 3).
# No book is skipped or dropped by a coverage/chapter-fraction heuristic. Every book is attempted against
# every source; raw chapter_fraction + confidence are RECORDED for qc_audit, never used to delete a book.
# (enforced by guard_no_book_gates.py)


def _pidx(pageid: str) -> int:
    """Numeric page index from a page id like 'S03a_0030' (fallback: hash-stable large)."""
    try:
        return D._page_index(pageid)
    except Exception:  # noqa: BLE001
        return 10**9


def book_page_span(st, book: str, chapters: dict[int, dict[int, str]],
                   cursor: int) -> tuple[dict | None, int]:
    """Locate each chapter of `book` in stream `st`, collecting the pages its body spans.
    Returns (record|None, new_cursor). Advances cursor through the volume so sequential books
    locate forward (DR volumes lay books out in canonical order)."""
    maxch = D._BOOK_CH.get(book, 0)
    ch_pages: dict[int, list[str]] = {}
    all_pages: list[str] = []
    recalls: list[float] = []
    below_floor: list[dict] = []  # chapters probed but too weak for a trusted span (RECORD, not drop)
    for ch in sorted(chapters):
        if maxch and ch > maxch:
            continue
        verses = chapters[ch]
        probe = D._probe(" ".join(verses[v] for v in sorted(verses)))
        if not probe:
            continue
        rec, a, b = D.locate_region(probe, st.fold, cursor)
        if rec < CH_FLOOR:
            below_floor.append({"chapter": ch, "recall": round(rec, 4)})
            continue
        cursor = a
        seen: set[str] = set()
        pgs: list[str] = []
        for i in range(a, min(b, len(st.page))):
            pg = st.page[i]
            if pg not in seen:
                seen.add(pg)
                pgs.append(pg)
        if pgs:
            ch_pages[ch] = pgs
            all_pages.extend(pgs)
            recalls.append(rec)
    if not all_pages:
        return None, cursor
    idxs = sorted({p for p in all_pages}, key=_pidx)
    rec = {
        "first_page": idxs[0],
        "last_page": idxs[-1],
        "n_chapters_located": len(ch_pages),
        "n_chapters_total": len(chapters),
        "n_chapters_below_floor": len(below_floor),
        "chapters_below_floor": below_floor,
        "mean_chapter_recall": round(sum(recalls) / len(recalls), 4) if recalls else 0.0,
        "chapter_pages": {str(ch): ch_pages[ch] for ch in sorted(ch_pages)},
    }
    return rec, cursor


def matter_regions(src_books: dict[str, dict], all_pages_sorted: list[str]) -> dict:
    """Bound the non-scripture matter regions from the located book spans.
    ot_front = pages before first OT book; ot_back__nt_front = the gap between last OT and first
    NT book; nt_back = pages after last NT book. Only the regions this volume actually spans."""
    idx_of = {p: _pidx(p) for p in all_pages_sorted}
    ot = [b for b in src_books if D._BOOK_TESTAMENT.get(b) == "OT"]
    nt = [b for b in src_books if D._BOOK_TESTAMENT.get(b) == "NT"]

    def span(books: list[str]) -> tuple[int, int]:
        firsts = [idx_of[src_books[b]["first_page"]] for b in books]
        lasts = [idx_of[src_books[b]["last_page"]] for b in books]
        return min(firsts), max(lasts)

    pages = all_pages_sorted
    out: dict = {}
    if ot:
        ot_lo, ot_hi = span(ot)
        out["ot_front"] = [p for p in pages if idx_of[p] < ot_lo]
        if nt:
            nt_lo, nt_hi = span(nt)
            out["ot_back__nt_front"] = [p for p in pages if ot_hi < idx_of[p] < nt_lo]
            out["nt_back"] = [p for p in pages if idx_of[p] > nt_hi]
        else:
            out["ot_back"] = [p for p in pages if idx_of[p] > ot_hi]
    elif nt:
        nt_lo, nt_hi = span(nt)
        out["nt_front"] = [p for p in pages if idx_of[p] < nt_lo]
        out["nt_back"] = [p for p in pages if idx_of[p] > nt_hi]
    return {k: v for k, v in out.items() if v}


def build(only: str | None = None) -> dict:
    streams = C.load_all_streams()
    anchor = C.anchor_all()
    sources: dict[str, dict] = {}
    book_to_sources: dict[str, list[dict]] = {}

    for src in sorted(streams):
        if only and src != only:
            continue
        st = streams[src]
        # page inventory for this source
        inv = sorted({p for p in st.page}, key=_pidx)
        src_books: dict[str, dict] = {}
        cursor = 0
        for book in D._BOOK_ORDER:
            chapters = anchor.get(book, {})
            if not chapters:
                continue
            cov = C.book_coverage(chapters, st)  # RECORDED signal only — never gates a book
            rec, cursor = book_page_span(st, book, chapters, cursor)
            if rec is None:
                continue  # zero chapters located here = genuine absence (no page span to record);
                          # qc_audit's source-index (ought-to-contain) + backward E(v) gate catch a real miss
            frac = rec["n_chapters_located"] / rec["n_chapters_total"] if rec["n_chapters_total"] else 0.0
            rec["coverage_recall"] = cov
            rec["chapter_fraction"] = round(frac, 3)
            rec["confidence"] = ("high" if frac >= 0.7 and cov >= 0.6
                                 else "medium" if frac >= 0.5
                                 else "low")
            src_books[book] = rec
            book_to_sources.setdefault(book, []).append(
                {"source": src, "confidence": rec["confidence"],
                 "first_page": rec["first_page"], "last_page": rec["last_page"]})
        testaments = sorted({D._BOOK_TESTAMENT.get(b) for b in src_books
                             if D._BOOK_TESTAMENT.get(b)})
        sources[src] = {
            "n_pages": st.n_pages,
            "n_body_tokens": len(st.fold),
            "page_range": [inv[0], inv[-1]] if inv else [],
            "testaments_covered": testaments,
            "n_books_covered": len(src_books),
            "books": src_books,
            "matter_regions": matter_regions(src_books, inv),
        }

    return {
        "schema": "originaldr-tome-map/v1",
        "note": ("per-source page->section map. Tier1 books deterministic (locate_region+page); "
                 "matter_regions structural (page gaps around book spans). reference_doc labels "
                 "= best-effort follow-up (label_reference_docs)."),
        "n_sources": len(sources),
        "sources": sources,
        "book_to_sources": {
            b: sorted(v, key=lambda e: ({"high": 0, "medium": 1, "low": 2}.get(e["confidence"], 9),
                                        e["source"]))
            for b, v in sorted(book_to_sources.items())},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None, help="only this source dir (verbose)")
    args = ap.parse_args()
    tm = build(args.source)
    if args.source:
        s = tm["sources"].get(args.source, {})
        print(f"=== {args.source} ===")
        print(f"pages={s.get('n_pages')} range={s.get('page_range')} "
              f"testaments={s.get('testaments_covered')} books={s.get('n_books_covered')}")
        for b, r in s.get("books", {}).items():
            print(f"  {b:22s} {r['first_page']}..{r['last_page']} "
                  f"ch={r['n_chapters_located']}/{r['n_chapters_total']} "
                  f"cov={r['coverage_recall']} rec={r['mean_chapter_recall']}")
        for reg, pgs in s.get("matter_regions", {}).items():
            print(f"  [{reg}] {len(pgs)} pages: {pgs[0] if pgs else ''}..{pgs[-1] if pgs else ''}")
        return 0
    OUT.write_text(json.dumps(tm, ensure_ascii=False, indent=2))
    print(f"wrote {OUT}")
    print(f"sources={tm['n_sources']} books_mapped={len(tm['book_to_sources'])}")
    for src, s in tm["sources"].items():
        print(f"  {src:26s} pages={s['n_pages']:>4} books={s['n_books_covered']:>2} "
              f"T={','.join(s['testaments_covered'])} "
              f"matter={list(s['matter_regions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
