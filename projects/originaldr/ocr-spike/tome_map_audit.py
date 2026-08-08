#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tome_map_audit.py — is the page->locus map actually right, for every admitted volume? (2026-07-27)

WHAT THIS CHECKS, AND WHY EACH CHECK EARNED ITS PLACE. Every one of these was a real defect found by hand
before it was automated here — which is the argument for automating it.

  1. OCR-vs-JP2 COMPLETENESS. `archive-holiebible-ot1` has 1160 jp2 pages and 780 OCR files, stopping dead at
     page 779: **380 pages (33% of S9's first OT volume) were never OCR'd at all.** A contiguous truncation, so
     a run that died and was never resumed. Nothing downstream reported it because a page that was never OCR'd
     simply is not in any denominator.

  2. INDEX ALIGNMENT. `jp2_page.jp2_path` matches OCR page N to the jp2 file whose name ends `_N`, so a volume
     whose OCR was written under a DIFFERENT naming convention silently rasterizes the WRONG LEAF. Verified by
     eye on both S9 volumes and they disagree with each other:
         pdf-S09nt    OCR `S09nt_0035`  == jp2 `nevvtestamentofi00mart_0035`   ALIGNED
         jp2-S09ot2   OCR `S09ot2_0040` == jp2 `holiebiblefaithf00mart_0039`   **OFFSET +1**
     Two volumes of the same source, two conventions. This is exactly why it cannot be assumed.

  3. TOME-MAP vs ADDRESSING. `tome-map.json` is the incumbent page->book/chapter claim (`mean_chapter_recall`
     0.84, and it claims `archive-nt-1582` holds only matthew/mark/john — for a 765-page New Testament). The
     addressing now assigns every page independently and is validated at 1865/1865 held-out chapter labels, so
     the two can be compared and the tome-map's error rate quantified rather than trusted.

  4. TOME INDICATOR. Every volume is labelled OT1 / OT2 / NT / MIXED from the canonical testament + book span
     of the pages actually addressed to it, so a reader can see which tome a volume really carries instead of
     inferring it from the directory name (which, as `pdf-S03a`, is not reliable).
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import jp2_page                       # noqa: E402
import page_address as PA             # noqa: E402
import source_inventory_audit as SIA  # noqa: E402

TOME = json.loads((HERE / "tome-map.json").read_text())
STORE = HERE.parent / "sources" / "our-ocr-diplomatic"
_NUM = re.compile(r"_(\d{4})$")

# VERIFIED index offsets (OCR page index -> jp2 page index). Established by rendering the jp2 and reading it
# against the OCR text, not by assumption. A volume absent here is asserted to be aligned and check 2 tests it.
#
# R7.5b: this was a SECOND, hand-kept copy of `jp2_page.JP2_INDEX_OFFSET` holding the same verified
# `jp2-S09ot2 = -1`. Two copies of an offset is R7.5 in miniature: the day one of them gains an entry the
# other does not, this audit certifies an alignment that the raster resolver does not use — and the failure
# is silent, because both numbers are plausible. It is now the same object, and the guard fails if a second
# definition reappears anywhere in the tree.
VERIFIED_OFFSET = jp2_page.JP2_INDEX_OFFSET


def _idx(stem: str):
    m = _NUM.search(stem)
    return int(m.group(1)) if m else None


def volume_report(ocr_dir: str) -> dict:
    ocr = sorted(filter(None, (_idx(Path(p).stem) for p in glob.glob(str(STORE / ocr_dir / "*.json")))))
    ocr_stems = {Path(p).stem for p in glob.glob(str(STORE / ocr_dir / "*.json"))}

    # R7.5b. An identifier that names no witness cannot be aligned against anything, and this audit's whole
    # subject is alignment. It reports as a DEFECT with its OCR count intact -- the volume stays visible and
    # stays counted -- rather than raising (which would take the other ten volumes down with it) or being
    # skipped (which would quietly shrink the denominator and let "0 volumes with a defect" mean nothing).
    try:
        witness = jp2_page.wid_of(ocr_dir)
    except KeyError as e:
        return {
            "ocr_dir": ocr_dir, "witness": None, "unaddressable": str(e),
            "detected_offset_vs_tome_map": None, "offset_profile": None,
            "tome": None, "books_addressed": [],
            "n_jp2": 0, "n_ocr": len(ocr),
            "ocr_range": [min(ocr), max(ocr)] if ocr else None, "jp2_range": None,
            "naming_convention": "UNADDRESSABLE", "verified_offset": None,
            "n_missing_ocr": 0, "missing_is_contiguous_tail": False,
            "tome_map_agree": 0, "tome_map_disagree": 0, "tome_map_accuracy": None,
        }
    # R7.5b: STRUCTURE. This audit compares leaf STEMS and leaf INDICES against the OCR corpus to establish
    # index alignment. It never opens a leaf, so every witness is admissible — and it must stay that way,
    # because the volumes whose alignment is least certain are exactly the ones barred from pixel work.
    files = jp2_page.structure_leaves(ocr_dir)
    jp2 = sorted(filter(None, (_idx(p.stem) for p in files)))
    jp2_stems = {p.stem for p in files}

    # naming convention: identical stems => alignment holds by construction; a rename must be verified.
    shared_stems = len(ocr_stems & jp2_stems)
    convention = ("name-matched" if shared_stems and shared_stems >= 0.9 * len(ocr_stems)
                  else "renamed" if files else "no-jp2-mapping")
    offset = VERIFIED_OFFSET.get(ocr_dir, 0 if convention == "name-matched" else None)

    missing = sorted(set(jp2) - set(x + (offset or 0) for x in ocr)) if jp2 else []
    contiguous_tail = bool(missing) and missing == list(range(missing[0], max(jp2) + 1))

    # addressing: what this volume actually carries
    af = HERE / f".page-address-{ocr_dir}.json"
    books, tome = [], None
    agree = disagree = 0
    if af.exists():
        recs = json.loads(af.read_text())["records"]
        bc = Counter(r["book"] for r in recs)
        books = [b for b, _ in bc.most_common()]
        tt = {PA.BOOK_TESTAMENT.get(b) for b in books}
        if tt == {"NT"}:
            tome = "NT"
        elif tt == {"OT"}:
            # OT1 = Genesis..Job in this edition's split; OT2 = Psalms onward.
            ot2 = {"psalms", "proverbs", "ecclesiastes", "canticle-of-canticles", "wisdom", "ecclesiasticus"}
            top = [b for b, _ in bc.most_common(4)]
            tome = "OT2" if any(b in ot2 for b in top) else "OT1"
        else:
            tome = "MIXED"
        addr = {r["page_index"]: set(r["chapters_on_page"]) for r in recs}
        addr_book = {r["page_index"]: r["book"] for r in recs}
        claims = []
        for book, bd in (TOME.get("sources", {}).get(ocr_dir, {}).get("books", {}) or {}).items():
            for ch, pages in (bd.get("chapter_pages") or {}).items():
                for pg in pages:
                    i = _idx(str(Path(str(pg)).stem))
                    if i is not None:
                        claims.append((i, book, int(ch)))

        # DETECT THE INDEX OFFSET INSTEAD OF ASSUMING IT. tome-map records pages by the ORIGINAL scan stem while
        # several volumes' OCR files were written under a different name and numbering. Joining the two on a raw
        # index then compares the wrong leaves and reports 0% agreement — which reads as "tome-map is worthless"
        # when it actually means "these two indexes are shifted". Scoring every small shift and keeping the best
        # separates the two readings: a real disagreement stays low at EVERY offset, a shift peaks sharply at one.
        def score(off):
            a = d = 0
            for i, book, ch in claims:
                j = i + off
                if j not in addr:
                    continue
                if addr_book.get(j) == book and ch in addr[j]:
                    a += 1
                else:
                    d += 1
            return a, d
        cand = {off: score(off) for off in (-2, -1, 0, 1, 2)}
        best_off = max(cand, key=lambda o: (cand[o][0] / max(1, cand[o][0] + cand[o][1]), cand[o][0]))
        agree, disagree = cand[best_off]
        detected_offset = best_off
        offset_profile = {str(o): round(cand[o][0] / max(1, sum(cand[o])), 3) for o in cand}
    return {
        "ocr_dir": ocr_dir, "witness": witness,
        "detected_offset_vs_tome_map": locals().get("detected_offset"),
        "offset_profile": locals().get("offset_profile"),
        "tome": tome, "books_addressed": books[:6],
        "n_jp2": len(jp2), "n_ocr": len(ocr),
        "ocr_range": [min(ocr), max(ocr)] if ocr else None,
        "jp2_range": [min(jp2), max(jp2)] if jp2 else None,
        "naming_convention": convention, "verified_offset": offset,
        "n_missing_ocr": len(missing),
        "missing_is_contiguous_tail": contiguous_tail,
        "missing_first": missing[:5], "missing_last": missing[-3:],
        "tome_map_agree": agree, "tome_map_disagree": disagree,
        "tome_map_accuracy": round(agree / (agree + disagree), 4) if (agree + disagree) else None,
    }


def main():
    inv = SIA.audit()
    rows = [volume_report(v) for v in inv["admitted"]]
    print(f"\n{'vol':24} {'tome':5} {'jp2':>6} {'ocr':>6} {'missing':>8} {'naming':>13} {'off/det':>8} "
          f"{'tome-map acc':>13}")
    print("-" * 92)
    for r in rows:
        acc = "n/a" if r["tome_map_accuracy"] is None else f"{100*r['tome_map_accuracy']:.1f}%"
        off = ("?" if r["verified_offset"] is None else str(r["verified_offset"]))
        det = r.get("detected_offset_vs_tome_map")
        off = f"{off}/{det}" if det is not None else off
        print(f"{r['ocr_dir']:24} {str(r['tome']):5} {r['n_jp2']:6} {r['n_ocr']:6} {r['n_missing_ocr']:8} "
              f"{r['naming_convention']:>13} {off:>8} {acc:>13}")
    bad = [r for r in rows if r.get("unaddressable") or r["n_missing_ocr"] or r["verified_offset"] is None
           or (r["tome_map_accuracy"] is not None and r["tome_map_accuracy"] < 0.99)]
    print(f"\nvolumes with a defect: {len(bad)} of {len(rows)}")
    for r in bad:
        why = []
        if r.get("unaddressable"):
            why.append(f"UNADDRESSABLE — {r['n_ocr']} OCR'd pages cannot be aligned to any leaf, because "
                       f"{r['unaddressable'].splitlines()[0]}")
        if r["n_missing_ocr"]:
            why.append(f"{r['n_missing_ocr']} pages never OCR'd"
                       + (" (CONTIGUOUS TAIL — a run that died)" if r["missing_is_contiguous_tail"] else ""))
        if r["verified_offset"] is None:
            why.append("index offset UNVERIFIED (renamed OCR files)")
        if r["tome_map_accuracy"] is not None and r["tome_map_accuracy"] < 0.99:
            why.append(f"tome-map disagrees with the addressing on {r['tome_map_disagree']} page-chapter claims")
        print(f"  {r['ocr_dir']:24} " + " · ".join(why))
    (HERE / "tome-map-audit.json").write_text(json.dumps(
        {"rule": "every admitted volume: complete OCR of its jp2, verified index alignment, tome-map agreement",
         "volumes": rows}, ensure_ascii=False, indent=1))
    print("\n-> wrote tome-map-audit.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
