#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rung2_pair_verify.py — verify every harvested pair by RE-READING its crop (§13 Q39, 2026-07-29).

Hand-checking 40 pairs found **11 mislabelled**, in two forms (see `rung2_pair_filter.py` for the full account):
a GT entry that spans MORE than its crop (columnar / wrapped table rows), and a WRONG GT line assigned to a crop
(formulaic table rows, made worse by the greedy 1:1 assignment cascading).

`rung2_pair_filter.py` tried to catch both from geometry alone — characters per em against the file median — and
**caught only 27%** (3 of 11). The reason is worth recording: when the defect is SYSTEMATIC WITHIN A FILE, a
within-file median absorbs it, so the anomaly has nothing to stand out against. A relative measure cannot detect a
uniform bias.

So this reads the pixels instead, and applies two tests that separate a bad LABEL from a bad READING — which
matters because a hard-to-read line is the most valuable training data there is and must NOT be filtered out:

  1. LENGTH — `len(recognized) / len(gt)` must be near 1. A correct pair keeps its length even when every letter
     is misread; a columnar GT is ~2x the text its crop can hold.
  2. ARGMAX — among ALL gold lines of that GT file, the assigned one must be (near) the best match for this crop.
     A cascaded misassignment fails here even when its length looks fine, because the crop's real gold line
     matches it better.

Neither test looks at how GOOD the reading is, only at whether the label describes the same ink. That is the whole
point: `scripture-abdias-01` has mean match similarity 0.575 because the page is hard, and every one of its pairs
should be kept.

Validated against the 40 hand-read lines of `rung2-calib40.json` (`--validate`), which are a real labelled test
set: read blind, scored against the human transcription.

Usage: ../ocr-venv/bin/python rung2_pair_verify.py [--data .rung2-data-v2] [--limit N] [--validate]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from PIL import Image                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None

from char_identity import edit_ratio, fold_archaic        # noqa: E402
from kraken.lib import models                            # noqa: E402
from rung2_eval_lines import read_line                   # noqa: E402

GT = HERE / "ground-truth"
BASE = HERE / "models" / "reichenau_lat.mlmodel"
LEN_LO, LEN_HI = 0.72, 1.30
ARGMAX_MARGIN = 0.02        # the assigned gold may trail the best by this much (ties are common and harmless)


def gold_lines(slug: str) -> list[str]:
    d = json.loads((GT / f"{slug}.json").read_text())
    return [b.get("text", "").strip() for b in (d.get("body") or [])
            if (b.get("text") or "").strip() and b.get("role") not in ("catchword", "signature")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".rung2-data-v2")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--out", default="rung2-pair-verify.json")
    a = ap.parse_args()
    data = HERE / a.data
    man = json.loads((data / "_manifest.json").read_text())
    if a.limit:
        man = man[:a.limit]
    model = models.load_any(str(BASE))
    golds = {}
    rows, t0 = [], time.time()
    for i, m in enumerate(man):
        png = data / f"line_{m['id']:04d}.png"
        gtf = data / f"line_{m['id']:04d}.gt.txt"
        if not (png.exists() and gtf.exists()):
            continue
        gt = gtf.read_text().strip()
        try:
            rec = read_line(model, png)
        except Exception:                                        # noqa: BLE001
            continue
        if m["slug"] not in golds:
            golds[m["slug"]] = gold_lines(m["slug"])
        pool = golds[m["slug"]] or [gt]
        f_rec = fold_archaic(rec)
        sim_assigned = edit_ratio(f_rec, fold_archaic(gt))
        best, best_sim = gt, sim_assigned
        for g in pool:
            s = edit_ratio(f_rec, fold_archaic(g))
            if s > best_sim:
                best, best_sim = g, s
        lr = len(rec) / max(1, len(gt))
        ok_len = LEN_LO <= lr <= LEN_HI
        ok_arg = sim_assigned >= best_sim - ARGMAX_MARGIN
        rows.append({**m, "rec": rec, "gt": gt, "len_ratio": round(lr, 3),
                     "sim_assigned": round(sim_assigned, 4), "sim_best": round(best_sim, 4),
                     "ok_len": ok_len, "ok_argmax": ok_arg, "keep": ok_len and ok_arg})
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(man)} · {time.time()-t0:.0f}s", flush=True)
    kept = [r for r in rows if r["keep"]]
    print(f"\npairs {len(rows)} -> KEEP {len(kept)} ({len(kept)/max(1,len(rows)):.1%})")
    print(f"  failed LENGTH  {sum(1 for r in rows if not r['ok_len'])}")
    print(f"  failed ARGMAX  {sum(1 for r in rows if not r['ok_argmax'])}")
    drop = collections.Counter(r["slug"] for r in rows if not r["keep"])
    print("  most-dropped GT files:")
    for s, n in drop.most_common(10):
        tot = sum(1 for r in rows if r["slug"] == s)
        print(f"    {s:<44} {n}/{tot}")
    (HERE / a.out).write_text(json.dumps(rows, ensure_ascii=False))
    print(f"[wrote] {a.out}")

    if a.validate:
        calib = {c["id"]: c for c in json.loads((HERE / "rung2-calib40.json").read_text())}
        tp = fp = tn = fn = 0
        for r in rows:
            k = f"{r['id']:04d}"
            if k not in calib:
                continue
            good = calib[k]["content"] >= 0.90
            if r["keep"] and good:
                tp += 1
            elif r["keep"]:
                fp += 1
            elif not good:
                tn += 1
            else:
                fn += 1
        print(f"\n  VALIDATION on {tp+fp+tn+fn} hand-read lines:")
        print(f"    kept & good {tp}   kept & MISLABELLED {fp}")
        print(f"    dropped & mislabelled {tn}   dropped & good {fn}")
        if tn + fp:
            print(f"    mislabelled caught {tn}/{tn+fp} = {tn/(tn+fp):.0%}")
        if tp + fn:
            print(f"    good retained      {tp}/{tp+fn} = {tp/(tp+fn):.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
