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


# The weakest floor that separates "addressed badly" from "not addressed at all".
# Deliberately not tuned: every real volume clears it on 45-77% of pages, the degenerate
# one on 0%, so nothing between 0.05 and 0.44 would change a single verdict.
FIT_FLOOR = 0.5


def build() -> dict:
    inv = SIA.audit()
    sources = {}
    unaddressable = {}
    for od in inv["admitted"]:
        af = HERE / f".page-address-{od}.json"
        if not af.exists():
            continue
        recs = json.loads(af.read_text())["records"]
        # DEGENERATE ADDRESSING (R7.5a-3, 2026-08-08). A volume every one of whose pages
        # was force-fitted to the nearest book in a set that does not contain its books
        # still produces a complete-looking address record: every page gets a book, a
        # chapter and a `fit`. `jp2-S06nt` is the live case -- 800 New Testament leaves
        # (`ACCORDING TO S. IOHN`, `TO TIMOTHEE`) addressed to Machabees and Daniel,
        # because `witness_inventory` drops S6's NT and the addressing therefore ran
        # against the Old Testament book set alone.
        #
        # The tell was in the artefact the whole time: **not one of its 800 records clears
        # fit 0.5**, where every other admitted volume clears it on 45-77% of pages. So
        # the floor here is the weakest statement that separates them -- not "the fit is
        # low" but "NOTHING in this volume matched anything", which no real addressing
        # produces. This is R1.4 again: an unaddressed page must not present as addressed.
        fits = [r.get("fit") or 0 for r in recs]
        if recs and not any(f > FIT_FLOOR for f in fits):
            unaddressable[od] = {
                "n_pages": len(recs),
                "why": (f"DEGENERATE ADDRESSING: not one of {len(recs)} records clears fit "
                        f"{FIT_FLOOR} (max {max(fits):.3f}). Every other admitted volume "
                        f"clears it on 45-77% of pages. These pages were force-fitted to "
                        f"the nearest book in a set that does not contain their books, so "
                        f"the addressing is absent, not merely poor. Re-address this "
                        f"volume against its own testament (R7.5a-3)."),
            }
            continue
        try:
            jp2_page.witness_of(od)
        except KeyError as e:
            # R7.5b/R7.5a. An admitted volume whose identifier does not name a witness is RECORDED AS
            # UNBUILT, and `main` refuses to write the map. It is not skipped: skipping would produce a
            # tome map that is short by this volume's leaves and says nothing about it, which is a
            # below-threshold result wearing a completed one's clothes. `jp2-S06` is the live case —
            # 2,872 leaves over two settings 53 years apart, awaiting the R7.5a re-key.
            unaddressable[od] = {"n_pages": len(recs), "why": str(e)}
            continue
        # R7.5b: STRUCTURE. The tome map is an ADDRESS book — which leaf carries which book and chapter —
        # and addressing is admissible for every witness because a render preserves page order.
        #
        # What it must NOT do is write a raster PATH into the map. A stored path is a route to the pixels
        # that no guard sits on, and a consumer reading `jp2_file` out of a JSON file would be doing exactly
        # what the retired routing table did, one indirection further away. So the map records the WITNESS
        # and the LEAF INDEX, and a consumer that wants the image asks the resolver for it.
        witness = jp2_page.wid_of(od)
        n_leaves = len(jp2_page.structure_leaves(od))
        offset = jp2_page.leaf_index(od, 0)
        books: dict = defaultdict(lambda: defaultdict(list))
        pages = {}
        for r in recs:
            pi = r["page_index"]
            jp2_idx = pi + offset
            pages[str(pi)] = {
                "ocr_page_index": pi,
                "leaf_index": jp2_idx,
                "jp2_page_index": jp2_idx,        # retained name; consumers predate `leaf_index`
                # NO raster path here, deliberately (R7.5b). `witness` + `leaf_index` is a complete
                # address; resolving it to an image is `jp2_page.pixel_path()`'s job, and routing it
                # through the resolver is what puts the guard between a consumer and F's renders.
                "witness": witness,
                "source_page_index": pi,          # the index every OCR artifact and the audit already use
                "book": r["book"], "chapters": r["chapters_on_page"],
                "tome": tome_of(r["book"]), "kind": r["kind"],
                "address_source": r["source"], "fit": r["fit"],
            }
            for ch in r["chapters_on_page"] or []:
                books[r["book"]][str(ch)].append(pi)
        sources[od] = {
            "ocr_dir": od,
            "witness": witness,
            "n_leaves": n_leaves,
            "jp2_index_offset": offset,
            "jp2_backed": bool(n_leaves),
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
        # Present and non-empty means the map is INCOMPLETE and must not be consumed as if it were not.
        "unaddressable_volumes": unaddressable,
    }


if __name__ == "__main__":
    m = build()
    out = HERE / "tome-map-v2.json"
    if m["unaddressable_volumes"]:
        # NOT written. A tome map missing a volume looks exactly like a tome map, and every consumer
        # downstream would read "100% of pages addressed" off a file that had silently dropped 2,872
        # leaves. The build stays OPEN and blocks, and the fix is R7.5a, not a smaller map.
        print("REFUSING TO WRITE tome-map-v2.json — the map would be INCOMPLETE.\n")
        for od, u in sorted(m["unaddressable_volumes"].items()):
            print(f"  {od}: {u['n_pages']} addressed pages cannot be placed\n"
                  f"    {u['why']}\n")
        print(f"built {len(m['sources'])} of {len(m['sources']) + len(m['unaddressable_volumes'])} "
              f"admitted volumes. Fix the reason given above, then rebuild — the map is "
              f"blocked, not degraded, and a partial map is not written.")
        raise SystemExit(1)
    out.write_text(json.dumps(m, ensure_ascii=False, indent=1))
    print(f"{'volume':24} {'tomes':12} {'pages':>6} {'books':>6} {'jp2':>5} {'offset':>7}")
    print("-" * 66)
    for od, s in m["sources"].items():
        print(f"{od:24} {'+'.join(s['tomes']):12} {s['n_pages']:6} {len(s['books']):6} "
              f"{'yes' if s['jp2_backed'] else 'NO':>5} {s['jp2_index_offset']:>7}")
    tot_pages = sum(s["n_pages"] for s in m["sources"].values())
    print(f"\n{len(m['sources'])} volumes · {tot_pages} pages · all addressed · -> {out.name}")
