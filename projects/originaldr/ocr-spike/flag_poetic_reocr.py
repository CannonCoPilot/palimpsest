#!/usr/bin/env python3
"""Flag every poetic-OT book in every OT-covering scan source for layout-aware re-OCR.

The 8 poetic OT books are printed in two columns and/or verse-structured layouts that defeat the
default top->bottom baseline segmentation + the sequential verse locate (e.g. Psalms located 0 in
the columnar EEBO vol4). This enumerates, per scan source that covers the OT, each poetic book with
its located page range (a re-OCR target) or a MISSING flag (physically expected but the locate
failed on the columns -> highest priority). Output drives a column-aware re-OCR pass (half-page
split, or kraken with a 2-column region/reading-order model). Written to poetic-reocr-flags.json.

Note: the downstream reading-order fix (detect_our_ocr._reading_order, column-major sort) already
recovers many located-but-scrambled poetic pages WITHOUT re-OCR; this flag list is the belt-and-
suspenders re-OCR worklist for the columnar sources the sort alone cannot rescue.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/"
             "gold/mask_engine/originaldr_reconstruction")
SKELETON = json.loads((RECON / "skeleton.json").read_text(encoding="utf-8"))
BOOK_CH = {b["slug"]: b["chapters"] for b in SKELETON["books"]}

POETIC = ["job", "psalms", "proverbs", "ecclesiastes", "canticle-of-canticles",
          "wisdom", "ecclesiasticus", "lamentations"]
MIN_RECALL = 0.5
MSL_PATH = HERE / "master-source-list.json"

# Free-text coverage -> poetic-book aliases. Used ONLY for zero-located sources, whose physical
# coverage is knowable only from the master source list (no located book span to bound them).
_POETIC_ALIASES = {
    "job": ("job",),
    "psalms": ("psalm",),
    "proverbs": ("proverb",),
    "ecclesiastes": ("ecclesiastes",),
    "canticle-of-canticles": ("canticle", "song of songs", "song of solomon"),
    "wisdom": ("wisdom",),
    "ecclesiasticus": ("ecclesiasticus", "sirach"),
    "lamentations": ("lamentation",),
}


def _load_ocr_dir_index() -> dict:
    """ocr_dir -> master-source-list entry (physical coverage for sources the locate missed)."""
    if not MSL_PATH.exists():
        return {}
    msl = json.loads(MSL_PATH.read_text(encoding="utf-8"))
    return {e["ocr_dir"]: e for e in msl.get("entries", []) if e.get("ocr_dir")}


def _zero_located_flags(sid: str, entry: dict) -> list:
    """Flags for a source that located ZERO books (no span to derive poetic presence from).

    Falls back to the master-source-list physical `coverage` string. If it names specific poetic
    book(s) — e.g. EEBO vol4 = 'Psalms', OCR'd (263pg) and voting in consensus yet 0 chapters
    located: the columnar poster-child — flag each as MISSING at CRITICAL priority. If coverage is
    only a coarse OT span (e.g. benched S2 'OT part 1'), emit ONE honest OCR-gap advisory rather
    than fabricating per-book flags. Either way the source is no longer silently dropped.
    """
    cov = entry.get("coverage") or ""
    covl = cov.lower()
    used = bool(entry.get("used_in_consensus"))
    ctx = {"physical_coverage": cov, "ocr_status": entry.get("ocr_status"),
           "ocr_pages": entry.get("ocr_pages"), "used_in_consensus": used}
    named = [bk for bk in POETIC if any(a in covl for a in _POETIC_ALIASES[bk])]
    out = []
    if named:
        for bk in named:
            note = ("physically a poetic book of this source (per master-source-list coverage) but "
                    "the locate found ZERO chapters")
            note += (" while the source IS voting in consensus — it contributes no located content "
                     "and must be re-OCR'd/re-located layout-aware (columnar)."
                     if used else " — re-OCR/re-locate layout-aware (columnar) before use.")
            out.append({"source": sid, "book": bk, "testament": "OT",
                        "canonical_chapters": BOOK_CH[bk], "status": "MISSING",
                        "priority": "critical", "page_range": None, "n_pages": None,
                        "n_chapters_located": 0, "mean_chapter_recall": None, "note": note, **ctx})
        return out
    if "ot" in covl or "whole" in covl:
        out.append({"source": sid, "book": None, "testament": "OT",
                    "status": "OCR_GAP_UNLOCATED",
                    "priority": "medium" if used else "advisory",
                    "note": ("source located ZERO books; coverage is a coarse OT span naming no "
                             "individual poetic book, so specific poetic cells cannot be enumerated. "
                             "Needs full (re-)OCR + re-locate before poetic-layout assessment. "
                             "Surfaced here so it is not silently dropped from the completeness "
                             "picture."), **ctx})
    return out


def _page_num(stem: str) -> int:
    tail = stem.rsplit("_", 1)[-1]
    return int(tail) if tail.isdigit() else -1


def main() -> int:
    tm = json.loads((HERE / "tome-map.json").read_text(encoding="utf-8"))
    sources = tm.get("sources", {})

    order_idx = {b["slug"]: i for i, b in enumerate(SKELETON["books"])}
    ocr_dir_index = _load_ocr_dir_index()
    flags = []
    for sid, sinfo in sources.items():
        located_books = sinfo.get("books", {})
        # A source physically contains a poetic book only if it falls within the canonical span of
        # the books this source DID locate. Genesis-only sources thus don't get spurious Psalms
        # flags; a poetic book INSIDE the span but not located is a real locate failure (the signal).
        idxs = [order_idx[b] for b in located_books if b in order_idx]
        if not idxs:
            # Zero located books: no span to derive from. Fall back to master-source-list physical
            # coverage so columnar total-locate failures (EEBO vol4 Psalms) are NOT silently dropped.
            flags.extend(_zero_located_flags(sid, ocr_dir_index.get(sid, {})))
            continue
        lo, hi = min(idxs), max(idxs)
        for bk in POETIC:
            if not (lo <= order_idx[bk] <= hi):
                continue  # poetic book outside this source's physical book span — not present here
            bi = located_books.get(bk)
            entry = {"source": sid, "book": bk, "testament": "OT",
                     "canonical_chapters": BOOK_CH[bk]}
            if not bi:
                entry.update({
                    "status": "MISSING", "priority": "high", "page_range": None, "n_pages": None,
                    "n_chapters_located": 0, "mean_chapter_recall": None,
                    "note": "poetic book physically expected but NOT located — columnar layout "
                            "likely defeated the sequential locate; re-OCR the OT section then "
                            "re-locate (layout-aware).",
                })
            else:
                fp, lp = bi.get("first_page"), bi.get("last_page")
                npages = (_page_num(lp) - _page_num(fp) + 1) if fp and lp else None
                recall = bi.get("mean_chapter_recall")
                nloc = bi.get("n_chapters_located", 0)
                ntot = bi.get("n_chapters_total", BOOK_CH[bk])
                partial = (recall is not None and recall < MIN_RECALL) or (nloc < ntot)
                entry.update({
                    "status": "partial" if partial else "located",
                    "priority": "high" if partial else "medium",
                    "page_range": [fp, lp], "n_pages": npages,
                    "n_chapters_located": nloc, "n_chapters_total": ntot,
                    "mean_chapter_recall": recall,
                    "note": "re-OCR with column-aware segmentation (half-page split) to lift "
                            "reading-order recall on the 2-column poetic layout.",
                })
            flags.append(entry)

    by_status = {}
    by_priority = {}
    reocr_pages = 0
    for f in flags:
        by_status[f["status"]] = by_status.get(f["status"], 0) + 1
        by_priority[f["priority"]] = by_priority.get(f["priority"], 0) + 1
        if f.get("n_pages"):
            reocr_pages += f["n_pages"]
    prio_rank = {"critical": 0, "high": 1, "medium": 2, "advisory": 3}
    out = {
        "schema": "poetic-reocr-flags/v2",
        "note": "All poetic OT books x every OT-covering scan source, flagged for layout-aware "
                "re-OCR. status=located|partial|MISSING|OCR_GAP_UNLOCATED. v2: zero-located sources "
                "(no located span) fall back to master-source-list physical coverage so columnar "
                "total-locate failures (e.g. EEBO vol4 Psalms) are captured, not silently dropped. "
                "critical+MISSING+partial are the priority targets.",
        "poetic_books": POETIC,
        "method_recommended": "kraken -bl with a 2-column region/reading-order model, OR pre-split "
                              "each page into left/right half-images and OCR each separately, then "
                              "concatenate (guarantees column reading order, no trained model).",
        "summary": {"n_flags": len(flags), "by_status": by_status, "by_priority": by_priority,
                    "sources_touched": sorted({f["source"] for f in flags}),
                    "located_page_span_total": reocr_pages},
        "flags": sorted(flags, key=lambda f: (prio_rank.get(f["priority"], 4),
                                              f["source"], f.get("book") or "")),
    }
    (HERE / "poetic-reocr-flags.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"poetic re-OCR flags: {len(flags)} (by status: {by_status})")
    print(f"sources touched: {out['summary']['sources_touched']}")
    print("wrote -> poetic-reocr-flags.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
