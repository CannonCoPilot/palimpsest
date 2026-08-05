#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gt2_restandardize.py — GT-2: re-standardize every scripture GT's versification to the janvier grid (2026-07-22).

Rewrites each scripture GT's `verses_aligned` by janvier-cutting the page body (via verse_seg), replacing the
old align_coords output whose whole-chapter drift produced the tail-spill artifact (118:176 / 24:67 stuffed
with bottom-of-page text). NON-DESTRUCTIVE + REVERSIBLE (No Silent Degradation / no hidden fails):
  * the whole file is backed up to ground-truth/.gt2-backup/<slug>.json BEFORE any change;
  * the prior `verses_aligned` is preserved as `_verses_aligned_pre_gt2` (never silently dropped);
  * the hand-curated `verses_on_page` is KEPT; a derived `verses_on_page_derived` is added and CHECKED against
    it, with any mismatch recorded (not overwritten) so a reviewer can adjudicate;
  * OPEN/partial verses (cross-page fragments, len-anomalies) are flagged in `_gt2`, never silently accepted.

Scoring never reads the persisted field — M3 calls verse_seg on-demand (one source of truth). This artifact is
for the review tool + gt_match_report display.

Usage: ocr-venv/bin/python ocr-spike/gt2_restandardize.py [--apply]   (dry-run without --apply)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verse_seg as VS  # noqa: E402

GT = HERE / "ground-truth"
BACKUP = GT / ".gt2-backup"
_VTAG = re.compile(r"^(\d+):(\d+)([a-c])?$")

LOCI = {
    "scripture-genesis-24": "genesis", "scripture-genesis-16-p081": "genesis",
    "scripture-genesis-16-p082": "genesis", "scripture-psalms-001": "psalms",
    "scripture-psalms-074-p137": "psalms", "scripture-psalms-074-p138": "psalms",
    "scripture-psalms-115-116": "psalms", "scripture-psalms-118": "psalms",
    "scripture-psalms-150-p265": "psalms", "scripture-psalms-150-p266": "psalms",
    "scripture-matthew-28-p102": "matthew", "scripture-2john": "2-john",
    "scripture-proverbs-16": "proverbs", "scripture-colossians-3": "colossians",
    "scripture-2esdras-07": "2-esdras",
}


def body_by_chapter(gt: dict) -> dict[int, str]:
    by: dict[int, list[str]] = {}
    for L in gt.get("body", []):
        if L.get("role") in ("catchword", "excluded", "signature"):
            continue
        m = _VTAG.match((L.get("verse") or "").strip())
        if m and isinstance(L.get("text"), str) and L["text"].strip():
            by.setdefault(int(m.group(1)), []).append(L["text"].strip())
    return {ch: re.sub(r"-\s+", "", " ".join(v)) for ch, v in by.items()}


def restandardize(slug: str, book: str) -> dict:
    gt = json.loads((GT / f"{slug}.json").read_text())
    aligned: dict[str, str] = {}
    open_verses: list[dict] = []
    derived_on_page: list[str] = []
    for ch, body in sorted(body_by_chapter(gt).items()):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            open_verses.append({"chapter": ch, "reason": "janvier-lacks-chapter"}); continue
        seg = VS.segment(body, janv)                    # janvier-cut of the page body (drop_apparatus off: gold is clean)
        if not seg:
            open_verses.append({"chapter": ch, "reason": "no-locate"}); continue
        for v, d in sorted(seg.items()):
            key = f"{ch}:{v}"
            aligned[key] = d["text"]
            derived_on_page.append(key)
            if d["open"]:
                open_verses.append({"verse": key, "reason": d["reason"], "len_ratio": d["len_ratio"]})
    # check derived vs the hand-curated verses_on_page (strip a/b suffixes for the comparison)
    orig_on_page = gt.get("verses_on_page") or []
    orig_base = sorted({f"{m.group(1)}:{m.group(2)}" for s in orig_on_page if (m := _VTAG.match(str(s).strip()))})
    derived_base = sorted(set(derived_on_page))
    missing = [v for v in orig_base if v not in derived_base]   # on page per human, not localized by engine
    extra = [v for v in derived_base if v not in orig_base]     # localized by engine, not in human list
    return {"slug": slug, "book": book, "aligned": aligned, "derived_on_page": derived_base,
            "open_verses": open_verses, "on_page_missing": missing, "on_page_extra": extra,
            "n_aligned": len(aligned), "gt": gt}


def apply(res: dict):
    BACKUP.mkdir(exist_ok=True)
    slug, gt = res["slug"], res["gt"]
    (BACKUP / f"{slug}.json").write_text(json.dumps(gt, ensure_ascii=False, indent=2))  # full reversible backup
    if "verses_aligned" in gt and "_verses_aligned_pre_gt2" not in gt:
        gt["_verses_aligned_pre_gt2"] = gt["verses_aligned"]     # preserve prior (never silently drop)
    gt["verses_aligned"] = res["aligned"]
    gt["verses_on_page_derived"] = res["derived_on_page"]        # ADD (keep hand-curated verses_on_page intact)
    gt["_gt2"] = {
        "note": "verses_aligned re-standardized to janvier boundaries by verse_seg.segment (janvier-cut); "
                "DERIVED + regenerable; scoring uses verse_seg on-demand, not this field.",
        "engine": "verse_seg.py", "n_aligned": res["n_aligned"],
        "open_verses": res["open_verses"], "on_page_missing_vs_human": res["on_page_missing"],
        "on_page_extra_vs_human": res["on_page_extra"],
    }
    (GT / f"{slug}.json").write_text(json.dumps(gt, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    a = ap.parse_args()
    slugs = sorted(p.stem for p in GT.glob("scripture-*.json"))
    print(f"GT-2 re-standardize {'(APPLY)' if a.apply else '(dry-run)'} — {len(slugs)} scripture GT\n")
    print(f"{'slug':30} {'book':10} {'aligned':>7} {'open':>5} {'miss':>5} {'extra':>5}  notes")
    print("-" * 88)
    tot_open = 0
    for slug in slugs:
        book = LOCI.get(slug)
        if not book:
            print(f"{slug:30} {'?':10} — no book mapping (skip)"); continue
        res = restandardize(slug, book)
        tot_open += len(res["open_verses"])
        note = ""
        if res["on_page_missing"]:
            note += f"human-onpage-not-localized={res['on_page_missing']} "
        if res["on_page_extra"]:
            note += f"engine-extra={res['on_page_extra']} "
        print(f"{slug:30} {book:10} {res['n_aligned']:>7} {len(res['open_verses']):>5} "
              f"{len(res['on_page_missing']):>5} {len(res['on_page_extra']):>5}  {note}")
        if a.apply:
            apply(res)
    print(f"\n{'APPLIED — backups in .gt2-backup/' if a.apply else 'DRY-RUN — pass --apply to write'}. "
          f"total OPEN/partial verses flagged: {tot_open}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
