#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verse_locate_eval.py — does the anchor-walk localizer beat the incumbent global-alignment segmenter?

Scores BOTH `verse_seg.segment_book_chapter` (global difflib over the whole chapter) and
`verse_locate.locate` (monotone anchor-walk) against the Jarvis diplomatic gold on the 13 gold pages, on the
axis that matters: per-verse `archaic_id` of the produced span vs the gold verse (ſ-blind content+spelling).

Runs entirely off `.page-cache/` — NO kraken, NO olmOCR, so a full sweep is seconds and every geometry or
parameter idea can be tested immediately.

Two failure modes are reported separately, because they need opposite fixes:
  * LOCALIZATION  — did we point at the right place at all? (a runaway or missing span)
  * READING       — given the right place, how good is the page's own text there?
A span that is 3 lines and 1.00 coverage but scores 0.6 vs gold is a RECOGNIZER problem; a span that is 53
lines is a LOCALIZATION problem. Conflating them is what made "psalms are broken" look like an OCR failure.

Usage: ../ocr-venv/bin/python verse_locate_eval.py [--verbose] [slug ...]
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from statistics import mean

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verse_seg as VS          # noqa: E402
import verse_locate             # noqa: E402
import gold_grid                # noqa: E402
from char_identity import evaluate_locus              # noqa: E402
from gate_calibrate import LOCI, gold_by_chapter      # noqa: E402

CACHE = HERE / ".page-cache"
GT = HERE / "ground-truth"


def page_result(slug):
    d = json.loads((CACHE / f"{slug}.json").read_text())
    return {"page_px": tuple(d["page_px"]), "r2_body": d["r2_body"], "lines": d["lines"]}


FAIR_GRID = True     # score against gold_grid (printed markers). --aligner-grid restores the old reference.


def eval_page(slug, verbose=False):
    gt = json.loads((GT / f"{slug}.json").read_text())
    book = LOCI.get(slug)
    if not book or not (CACHE / f"{slug}.json").exists():
        return []
    pr = page_result(slug)
    rows = []
    for ch, gold_text in sorted(gold_by_chapter(gt).items()):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            continue
        if FAIR_GRID:
            # THE FAIR REFERENCE (gold_grid): the gold is cut at the PRINTED verse markers, not by the
            # incumbent aligner. Scoring the challenger on a grid the incumbent produced charged every
            # boundary-word disagreement to the challenger (genesis 16:15/16 "Eightie"). Verses the printed
            # markers could not resolve are reported EMPTY by the grid and are skipped here rather than
            # silently falling back to an aligner cut.
            g = gold_grid.build_grid(gt, ch, book)
            gold_j = {v: {"text": t} for v, t in g["verses"].items() if t}
        else:
            gold_j = VS.segment(gold_text, janv)
        old = VS.segment_book_chapter(pr["r2_body"], book, ch, drop_apparatus=True)
        new = verse_locate.locate(pr, book, ch)["verses"]
        hyb = verse_locate.best_spans(pr, book, ch)
        for v in sorted(gold_j):
            g = (gold_j.get(v) or {}).get("text")
            if not g:
                continue
            o = (old.get(v) or {}).get("text", "")
            n = (new.get(v) or {}).get("text", "")
            h = (hyb.get(v) or {}).get("text", "")
            ids = {k: evaluate_locus(t, janv.get(v), g)["archaic_id"] for k, t in
                   (("old_id", o), ("new_id", n), ("hyb_id", h))}
            rows.append({
                "slug": slug, "ch": ch, "v": v, **ids,
                # ORACLE = pick the better of the two engines KNOWING the gold. Not a deliverable — the
                # ceiling the gold-free selector is measured against, so "how much of the available gain did
                # the selector capture?" stays an answered question rather than an assumption.
                "orc_id": max(ids["old_id"] or 0.0, ids["new_id"] or 0.0),
                "src": (hyb.get(v) or {}).get("source", "-"),
                "old_lines": len((old.get(v) or {}).get("lines", []) or []),
                "new_lines": len((new.get(v) or {}).get("lines", [])),
                "hyb_lines": len((hyb.get(v) or {}).get("lines", []) or []),
                "cov": (new.get(v) or {}).get("coverage", 0.0),
            })
            if verbose:
                r = rows[-1]
                print(f"    {slug} {ch}:{v}  old {r['old_id']:.3f} -> new {r['new_id']:.3f}  "
                      f"(cov {r['cov']:.2f}, lines {r['new_lines']})")
    return rows


def main():
    global FAIR_GRID
    args = sys.argv[1:]
    verbose = "--verbose" in args
    if "--aligner-grid" in args:
        FAIR_GRID = False
    slugs = [a for a in args if not a.startswith("--")] or sorted(LOCI)
    print(f"[reference grid] {'FAIR (printed markers, gold_grid)' if FAIR_GRID else 'ALIGNER-CUT (legacy)'}")
    allrows = []
    print(f"{'slug':<27} {'ch':>4} {'n':>3} {'ALIGN':>7} {'WALK':>7} {'HYBRID':>7} {'Δhyb':>8}  {'pass align→hyb':>15}")
    for slug in slugs:
        rows = eval_page(slug, verbose)
        allrows += rows
        bych = {}
        for r in rows:
            bych.setdefault(r["ch"], []).append(r)
        for ch, rs in sorted(bych.items()):
            o = mean(r["old_id"] for r in rs); n = mean(r["new_id"] for r in rs)
            hb = mean(r["hyb_id"] for r in rs)
            po = sum(1 for r in rs if r["old_id"] >= 0.90); ph = sum(1 for r in rs if r["hyb_id"] >= 0.90)
            mark = "  <<<" if hb - o > 0.02 else ("  !!!" if hb - o < -0.02 else "")
            print(f"{slug:<27} {ch:>4} {len(rs):>3} {o:>7.3f} {n:>7.3f} {hb:>7.3f} {hb-o:>+8.3f}  "
                  f"{po:>6}/{len(rs)} → {ph}/{len(rs)}{mark}")
    if not allrows:
        return 1
    o = [r["old_id"] for r in allrows]; n = [r["new_id"] for r in allrows]
    h = [r["hyb_id"] for r in allrows]; orc = [r["orc_id"] for r in allrows]
    print("\n" + "=" * 84)
    print(f"OVERALL  n={len(allrows)}   OLD {mean(o):.4f}  ->  NEW {mean(n):.4f}   Δ {mean(n)-mean(o):+.4f}")
    print(f"  pass (id>=0.90): {sum(1 for x in o if x>=0.9)}/{len(o)} -> {sum(1 for x in n if x>=0.9)}/{len(n)}")
    print(f"  improved {sum(1 for a,b in zip(o,n) if b-a>0.01)}   worsened {sum(1 for a,b in zip(o,n) if a-b>0.01)}")
    for name, arm in (("align (incumbent)", o), ("walk", n), ("HYBRID best_spans", h), ("oracle (uses gold)", orc)):
        print(f"  {name:<20} mean {mean(arm):.4f}   pass {sum(1 for x in arm if x >= 0.9):>3}/{len(arm)} "
              f"= {sum(1 for x in arm if x >= 0.9)/len(arm):.3f}")
    gap = mean(orc) - mean(o)
    if gap > 1e-9:
        print(f"  selector captured {(mean(h)-mean(o))/gap:.0%} of the oracle's available gain over the incumbent")
    print(f"  hybrid chose:  walk {sum(1 for r in allrows if r['src']=='walk')}  "
          f"align {sum(1 for r in allrows if r['src']=='align')}")
    try:
        from scipy.stats import wilcoxon
        for label, arm in (("walk", n), ("HYBRID", h)):
            if any(abs(a - b) > 1e-9 for a, b in zip(o, arm)):
                st, p = wilcoxon(o, arm)
                print(f"  Wilcoxon incumbent vs {label}: W={st:.1f}  p={p:.5f}  "
                      f"(improved {sum(1 for a,b in zip(o,arm) if b-a>0.01)} / "
                      f"worsened {sum(1 for a,b in zip(o,arm) if a-b>0.01)})")
    except Exception as e:
        print("  (scipy unavailable:", e, ")")
    big_old = [r for r in allrows if r["old_lines"] > 20]
    print(f"\nRUNAWAY SPANS (>20 lines for one verse):  OLD {len(big_old)}   "
          f"NEW {sum(1 for r in allrows if r['new_lines'] > 20)}")
    print(f"NOT-LOCATED by the walk: {sum(1 for r in allrows if r['cov'] == 0.0)}/{len(allrows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
