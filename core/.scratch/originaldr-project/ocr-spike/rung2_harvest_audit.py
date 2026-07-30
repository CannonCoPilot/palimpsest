#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_harvest_audit.py — WHERE DO 2,300 HAND-MADE GT LINES GO? (item 2, 2026-07-29)

`reichenau_dr` — the R2 recognizer — was fine-tuned on **311 line pairs**, and its own comparison report says so
as though 311 were the available data. It is not: the `ground-truth/` files hold **2,611 hand-transcribed body
lines**, so `rung2_prepare.py` is converting **12%** of the diplomatic ground truth this project already paid for
into training pairs. For a fine-tune whose measured ceiling is small-data (93.96% val, base 93.0%), recovering
even half of the remainder is a bigger lever than any new data source.

(The alternative source tried first — harvesting targets from the two fully-worked chapters — is a DEAD END and
`rung2_chapter_pairs.py` records why: only 6.4% of its rows carry any signal, and some of those targets are
wrong, because text validated at VERSE grain against references is not line-level diplomatic ground truth.)

This audit attributes every lost line to one cause, per gold page, WITHOUT changing the harvester:

  skipped_multipage  the GT file's `page_index` is a LIST — `rung2_prepare.page_lines` returns [] outright
  no_raster          the source image could not be loaded
  seg_shortfall      kraken segmented FEWER lines than the page has GT body lines
  below_min_sim      a segmented line's best GT match scored under `--min-sim`
  lost_to_greedy     both the line and its GT partner were already claimed by a better-scoring pair

Usage: ../ocr-venv/bin/python rung2_harvest_audit.py [--limit 8] [--min-sim 0.45] [--json-out ...]
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from PIL import Image                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None

from char_identity import edit_ratio, fold_archaic        # noqa: E402
import jp2_page                                          # noqa: E402
from kraken import blla, rpred                           # noqa: E402
from kraken.lib import models                            # noqa: E402

GT = HERE / "ground-truth"
BASE = HERE / "models" / "reichenau_lat.mlmodel"
MAXW = 2000          # matches rung2_prepare.MAXW so the audit sees the same segmentation


def audit_page(path: Path, model, min_sim: float) -> dict:
    d = json.loads(path.read_text())
    gold = [b.get("text", "").strip() for b in (d.get("body") or [])
            if (b.get("text") or "").strip() and b.get("role") not in ("catchword", "signature")]
    r = {"slug": path.stem, "n_gold": len(gold), "cause": None, "n_seg": 0, "n_matched": 0}
    if not gold:
        r["cause"] = "no_gold_body"
        return r
    od, pi = d.get("ocr_dir"), d.get("page_index")
    if od is None or pi is None or isinstance(pi, list):
        r["cause"] = "skipped_multipage"
        return r
    try:
        im = jp2_page.load(od, pi).convert("L")
    except Exception as e:                                       # noqa: BLE001
        r["cause"] = "no_raster"
        r["detail"] = str(e)[:120]
        return r
    if im.width > MAXW:
        im = im.resize((MAXW, int(im.height * MAXW / im.width)), Image.LANCZOS)
    seg = blla.segment(im)
    recs = list(rpred.rpred(model, im, seg))
    r["n_seg"] = len(recs)
    cands = []
    for si, rec in enumerate(recs):
        rtxt = fold_archaic(str(rec))
        if len(rtxt) < 4:
            continue
        best = 0.0
        for gi, g in enumerate(gold):
            sim = edit_ratio(rtxt, fold_archaic(g))
            best = max(best, sim)
            if sim >= min_sim:
                cands.append((sim, si, gi))
        r.setdefault("best_sims", []).append(round(best, 3))
    cands.sort(reverse=True)
    used_s, used_g = set(), set()
    for sim, si, gi in cands:
        if si in used_s or gi in used_g:
            continue
        used_s.add(si); used_g.add(gi)
    r["n_matched"] = len(used_g)
    # attribute the shortfall for THIS page to its dominant cause
    lost = len(gold) - r["n_matched"]
    if lost <= 0:
        r["cause"] = "complete"
    elif r["n_seg"] < len(gold):
        r["cause"] = "seg_shortfall"
    elif sum(1 for s in r.get("best_sims", []) if s < min_sim) >= lost:
        r["cause"] = "below_min_sim"
    else:
        r["cause"] = "lost_to_greedy"
    r["lost"] = lost
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--min-sim", type=float, default=0.45)
    ap.add_argument("--json-out", default="rung2-harvest-audit.json")
    a = ap.parse_args()
    files = sorted(GT.glob("*.json"))
    if a.limit:
        files = files[:a.limit]
    model = models.load_any(str(BASE))
    rows = []
    for f in files:
        r = audit_page(f, model, a.min_sim)
        rows.append(r)
        print(f"  {r['slug']:<30} gold {r['n_gold']:>3}  seg {r['n_seg']:>3}  matched {r['n_matched']:>3}  "
              f"lost {r.get('lost', r['n_gold']):>3}  {r['cause']}", flush=True)
    g = sum(r["n_gold"] for r in rows)
    m = sum(r["n_matched"] for r in rows)
    print(f"\n=== {len(rows)} gold pages: {g} GT body lines, {m} harvested = {m/g:.1%} ===")
    print("  lost lines by dominant cause:")
    by = Counter()
    for r in rows:
        by[r["cause"]] += r.get("lost", r["n_gold"]) if r["cause"] != "complete" else 0
    for k, v in by.most_common():
        if v:
            print(f"    {k:<20} {v}")
    (HERE / a.json_out).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"\n[wrote] {a.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
