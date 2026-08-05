#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_tome_map_v2.py — regenerate the page->locus map FROM the validated addressing (2026-07-27).

WHY REGENERATE RATHER THAN PATCH. `tome-map.json` v1 was built by `locate_region` probing and is not close to
right on several volumes — audited against the addressing (`tome_map_audit.py`):

    pdf-S03a          95.9%   offset profile peaks sharply at 0  -> correctly aligned; the control
    archive-nt-1582   25.5%   claims only matthew/mark/john for a 765-page New Testament
    jp2-S04            0.0%   claims `jeremie` and `john` for the 1633 Rheims NEW TESTAMENT — `jeremie` is an
                              OT book and cannot be in that volume at all
    pdf-S03b           0.0%   claims `1-esdras` alone for an 1134-page OT second tome

The 0.0% cases are flat at EVERY candidate offset (-2..+2), which is what distinguishes a genuinely wrong claim
from a merely shifted index — `pdf-S03a` peaks at one offset and falls away, these do not peak at all.

`page_address` assigns every page of every admitted volume and is validated at 1865/1865 held-out printed
chapter labels across 13 volumes, so it is simply the better instrument for the job tome-map was doing.

WHAT v2 ADDS, per Sir: every page carries BOTH its jp2 reference AND its pdf/source page reference, plus a
TOME indicator (OT1 / OT2 / NT) for the locus, so a consumer can go from a book:chapter to the exact image in
either rendering without guessing. The verified OCR->jp2 index offset is applied and recorded per volume, so
`jp2-S09ot2`'s +1 shift can never silently rasterize the neighbouring leaf again.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import jp2_page                       # noqa: E402
import page_address as PA             # noqa: E402
import source_inventory_audit as SIA  # noqa: E402
import tome_map_audit as TMA          # noqa: E402
import witness_inventory as WI        # noqa: E402

# NO SECOND COPY OF THIS LIST. It was duplicated here and drifted from `witness_inventory`'s — the FOURTH
# instance of one hand-typed list silently disagreeing with another in this project (three LOCI dicts, the
# GT's 2john vs the canon's 2-john, OT2_BOOKS' `zacharie` vs the canon's `zacharias`, and now this). There is
# exactly one tome classification and it lives in witness_inventory, which validates itself against the canon.
OT2_BOOKS = WI.OT2_BOOKS


def tome_of(book: str) -> str:
    if PA.BOOK_TESTAMENT.get(book) == "NT":
        return "NT"
    return "OT2" if book in OT2_BOOKS else "OT1"


def build() -> dict:
    inv = SIA.audit()
    sources = {}
    for od in inv["admitted"]:
        af = HERE / f".page-address-{od}.json"
        if not af.exists():
            continue
        recs = json.loads(af.read_text())["records"]
        entry = jp2_page.OCR_DIR_TO_JP2.get(od)
        jp2_dir = entry[1] if entry else None
        offset = TMA.VERIFIED_OFFSET.get(od, 0)
        books: dict = defaultdict(lambda: defaultdict(list))
        pages = {}
        for r in recs:
            pi = r["page_index"]
            jp2_idx = pi + offset if jp2_dir else None
            pages[str(pi)] = {
                "ocr_page_index": pi,
                "jp2_page_index": jp2_idx,
                "jp2_file": (f"{Path(jp2_dir).name.replace('_jp2','')}_{jp2_idx:04d}.jp2"
                             if jp2_dir and jp2_idx is not None else None),
                "source_page_index": pi,          # the index every OCR artifact and the audit already use
                "book": r["book"], "chapters": r["chapters_on_page"],
                "tome": tome_of(r["book"]), "kind": r["kind"],
                "address_source": r["source"], "fit": r["fit"],
            }
            for ch in r["chapters_on_page"] or []:
                books[r["book"]][str(ch)].append(pi)
        sources[od] = {
            "ocr_dir": od, "jp2_dir": jp2_dir,
            "jp2_index_offset": offset,
            "jp2_backed": bool(jp2_dir),
            "n_pages": len(recs),
            "tomes": sorted({tome_of(r["book"]) for r in recs}),
            "books": {b: {"chapter_pages": {c: sorted(set(p)) for c, p in sorted(ch.items(), key=lambda kv: int(kv[0]))},
                          "tome": tome_of(b), "n_chapters_located": len(ch)}
                      for b, ch in sorted(books.items())},
            "pages": pages,
        }
    return {
        "schema": "originaldr-tome-map/v2",
        "note": ("Regenerated from page_address (monotone volume alignment): every page of every admitted "
                 "volume carries a book:chapter address, a TOME indicator, and both its jp2 and source page "
                 "reference. Supersedes v1, which was audited at 0.0-25.5% on three volumes. Coverage is 100% "
                 "of pages by construction; chapter accuracy is validated at 1865/1865 held-out printed "
                 "chapter labels (page_address_eval)."),
        "admitted_volumes": inv["admitted"],
        "n_sources": len(sources),
        "sources": sources,
    }


if __name__ == "__main__":
    m = build()
    out = HERE / "tome-map-v2.json"
    out.write_text(json.dumps(m, ensure_ascii=False, indent=1))
    print(f"{'volume':24} {'tomes':12} {'pages':>6} {'books':>6} {'jp2':>5} {'offset':>7}")
    print("-" * 66)
    for od, s in m["sources"].items():
        print(f"{od:24} {'+'.join(s['tomes']):12} {s['n_pages']:6} {len(s['books']):6} "
              f"{'yes' if s['jp2_backed'] else 'NO':>5} {s['jp2_index_offset']:>7}")
    tot_pages = sum(s["n_pages"] for s in m["sources"].values())
    print(f"\n{len(m['sources'])} volumes · {tot_pages} pages · all addressed · -> {out.name}")
