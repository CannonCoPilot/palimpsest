#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apparatus_eval.py — do the geometric apparatus variants actually improve per-verse identity?

Measured END TO END against the FAIR gold (gold_grid, printed markers): strip the predicted apparatus lines,
re-segment with the production hybrid, score every verse. A variant only counts if it beats the baseline
WITHOUT destroying a page — the symbol-only prototype's failure (proverbs 0.943 -> 0.337) is the thing to
avoid, so the per-page worst case is reported alongside the mean.

Usage: ../ocr-venv/bin/python apparatus_eval.py
"""
from __future__ import annotations
import json, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from statistics import mean
from pathlib import Path
import verse_seg as VS, verse_locate, gold_grid, apparatus_geom, layout_profile
from char_identity import evaluate_locus
from gate_calibrate import LOCI, gold_by_chapter, cached_page

GT = Path("ground-truth")
VARIANTS = ["baseline", "v1", "v2", "v3", "v4", "v5", "v6"]


def score_page(slug, book, variant):
    gt = json.loads((GT / f"{slug}.json").read_text())
    r = cached_page(slug, gt.get("ocr_dir"), gt.get("page_index"))
    W = r["page_px"][0]
    if variant == "baseline":
        pr = r
    else:
        kept = {c["idx"] for c in apparatus_geom.classify_lines(r["lines"], variant=variant, page_w=W)
                if c["kind"] != "apparatus"}
        lines = [l for i, l in enumerate(r["lines"]) if l.get("role") != "body" or i in kept]
        import layout
        body = layout.strip_verse_numbers(" ".join(l["text"] for l in lines if l.get("role") == "body"))
        pr = {"page_px": r["page_px"], "r2_body": body, "lines": lines}
    ids = []
    for ch in sorted(gold_by_chapter(gt)):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            continue
        g = gold_grid.build_grid(gt, ch, book)
        try:
            hyb = verse_locate.best_spans(pr, book, ch)
        except ValueError:
            hyb = {}
        for v, t in g["verses"].items():
            if not t:
                continue
            ids.append(evaluate_locus((hyb.get(v) or {}).get("text", ""), janv.get(v), t)["archaic_id"])
    return ids


def main():
    per_variant = {v: {} for v in VARIANTS}
    for slug, book in sorted(LOCI.items()):
        for v in VARIANTS:
            per_variant[v][slug] = score_page(slug, book, v)
    base = per_variant["baseline"]
    print(f"{'variant':<9} {'mean':>7} {'pass':>10} {'Δmean':>8} {'pages worse':>12} {'worst page Δ':>14}")
    for v in VARIANTS:
        allids = [x for s in per_variant[v].values() for x in s]
        if not allids:
            continue
        dm = mean(allids) - mean([x for s in base.values() for x in s])
        deltas = {s: (mean(per_variant[v][s]) - mean(base[s])) for s in base if base[s] and per_variant[v][s]}
        worse = sum(1 for d in deltas.values() if d < -0.005)
        worst = min(deltas.items(), key=lambda kv: kv[1]) if deltas else ("-", 0.0)
        print(f"{v:<9} {mean(allids):>7.4f} {sum(1 for x in allids if x>=0.9):>4}/{len(allids):<5} "
              f"{dm:>+8.4f} {worse:>12} {worst[1]:>+9.3f} {worst[0].replace('scripture-','')}")
    print("\nPER-PAGE (best variant vs baseline), with the page's detected schema:")
    for slug, book in sorted(LOCI.items()):
        gt = json.loads((GT / f"{slug}.json").read_text())
        r = cached_page(slug, gt.get("ocr_dir"), gt.get("page_index"))
        chs = sorted(gold_by_chapter(gt))
        sch = layout_profile.classify(layout_profile.profile(r, book, chs[0] if chs else None))["schema"]
        b = mean(base[slug]) if base[slug] else 0.0
        row = []
        for v in VARIANTS[1:]:
            s = per_variant[v][slug]
            row.append((mean(s) - b) if s else 0.0)
        bi = max(range(len(row)), key=lambda i: row[i])
        print(f"  {slug:<27} {sch:<26} base {b:.3f}  best {VARIANTS[1:][bi]} {row[bi]:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
