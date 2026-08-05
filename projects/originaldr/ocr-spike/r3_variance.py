#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r3_variance.py — EXPERIMENT: how much of the R3 score is crop geometry, and how much is chaos?

WHY THIS EXISTS (2026-07-25). The wide-line `body_column` fix repaired exactly the failures it targeted
(3 hard 0.000s -> 0.99/0.86/0.70) yet the aggregate barely moved, because verses whose crop geometry changed
by <0.001 of page width ALSO moved by up to 0.25. olmOCR at temperature 0 is deterministic in the input, but
the map from crop rectangle to transcript is CHAOTIC: a one-pixel change in the rendered crop can flip a whole
verse. A single-run A/B therefore cannot attribute a geometry change — the noise term dominates the signal.

So before building any more geometry, measure the noise. For each region this runs K crop VARIANTS (small,
label-preserving perturbations of the same region: pad and column-width jitter — every variant still contains
the whole region) and records, per flagged verse, the score of every variant on BOTH axes:

  * gold-free  xsrc_id vs the reference witness   (what production can see -> what a selector may use)
  * gold-anchored archaic_id vs the Jarvis gold    (the truth -> what a selector must be judged by)

That yields the three numbers that decide the next lever:
  SPREAD          max-min across variants        — the size of the chaos term
  ORACLE(gold)    best variant chosen by gold     — the ceiling multi-crop could ever reach
  SELECTED(xsrc)  best variant chosen gold-free   — what a REAL production selector achieves

If SELECTED tracks ORACLE, best-of-N crop consensus is a real, production-legal lever (the selector is
gold-free and acceptance still requires >= taux, so nothing sub-threshold is accepted -- No Silent
Degradation holds). If SELECTED instead sits at or below the single-run mean, the witness is too weak to
choose among variants and the honest conclusion is that olmOCR-on-crops is variance-limited, not geometry-
limited -- which would make R3-vision a dead end at this rung and send the effort to the arbiter instead.
Either way the answer is measured, not assumed.

Checkpoints per page to `.r3-variance/<slug>.json`; `--aggregate` recomputes without olmOCR.
Usage: ../ocr-venv/bin/python r3_variance.py [--aggregate] [--variants N] [slug ...]
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path
from statistics import mean, median

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import reocr_core as core          # noqa: E402
import verse_seg as VS             # noqa: E402
import xsrc_gate                   # noqa: E402
import verse_geom                  # noqa: E402
import r3_route                    # noqa: E402
import reocr_r3                    # noqa: E402
from char_identity import evaluate_locus            # noqa: E402
from gate_calibrate import LOCI, gold_by_chapter    # noqa: E402

OUT = HERE / ".r3-variance"
GT = HERE / "ground-truth"
CACHE = HERE / ".page-cache"          # reocr_page results dumped by .diag_cols.py (skips kraken on re-runs)


def crop_variants(crop, n: int = 4):
    """n label-preserving perturbations of a region crop. Every variant still CONTAINS the region (we only ever
    grow, never shrink, the box) so the verse text present is identical across variants and any score difference
    is attributable to the model's sensitivity, not to lost content. Variant 0 is the production crop."""
    x0, y0, x1, y1 = crop

    def cl(v):
        return max(0.0, min(1.0, v))

    grows = [(0.0, 0.0), (0.010, 0.004), (0.022, 0.008), (0.035, 0.012), (0.050, 0.016)]
    return [(cl(x0 - dx), cl(y0 - dy), cl(x1 + dx), cl(y1 + dy)) for dx, dy in grows[:n]]


def _page_result(slug, gt):
    """reocr_page for a gold page, preferring the .page-cache dump (kraken is ~10s/page and unchanged here)."""
    ck = CACHE / f"{slug}.json"
    if ck.exists():
        d = json.loads(ck.read_text())
        return {"page_px": tuple(d["page_px"]), "r2_body": d["r2_body"], "lines": d["lines"]}
    return core.reocr_page(gt["ocr_dir"], gt["page_index"], want_base=False, want_r1=False)


def page_variance(slug, transcribe, n_variants: int = 4) -> list[dict]:
    gt = json.loads((GT / f"{slug}.json").read_text())
    book = LOCI.get(slug)
    od, pi = gt.get("ocr_dir"), gt.get("page_index")
    if not book or od is None:
        return []
    r = _page_result(slug, gt)
    recs = []
    for ch, gold_text in sorted(gold_by_chapter(gt).items()):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            continue
        gold_j = VS.segment(gold_text, janv)
        scores = xsrc_gate.cross_source_verse_scores(r["r2_body"], book, ch)
        flagged = [v for v in scores if scores[v].get("escalate")]
        if not flagged:
            continue
        regions = verse_geom.region_crops(r, book, ch, flagged)["regions"]
        for reg in regions:
            rverses = [v for v in reg["verses"] if v in scores]
            if not rverses:
                continue
            per_variant = []
            for ci, c in enumerate(crop_variants(reg["crop"], n_variants)):
                try:
                    blob = transcribe(od, pi, crop=c, verse=rverses[0])
                    cut = VS.segment_book_chapter(blob, book, ch, drop_apparatus=True)
                except Exception as e:                      # contain: a failed variant is a missing sample,
                    per_variant.append({"i": ci, "crop": c, "error": f"{type(e).__name__}: {e}"})
                    continue                                # never an aborted region (No Silent Degradation)
                per_variant.append({"i": ci, "crop": c, "cut": {v: (cut.get(v) or {}).get("text", "")
                                                               for v in rverses}})
            for v in rverses:
                s = scores[v]
                gold_v = (gold_j.get(v) or {}).get("text")
                samples = []
                for pv in per_variant:
                    if "error" in pv:
                        samples.append({"i": pv["i"], "error": pv["error"], "xsrc": None, "gold": None})
                        continue
                    span = pv["cut"][v]
                    xs = xsrc_gate.verse_xsrc(span, s.get("ref_modern"), s.get("ref_archaic"))["xsrc_id"]
                    gd = (None if gold_v is None
                          else evaluate_locus(span or "", janv.get(v), gold_v)["archaic_id"])
                    # RECORD THE SPAN TEXT, not just its scores: olmOCR is the expensive step (~7s/crop), and
                    # every post-hoc question worth asking about these variants — medoid/ROVER consensus,
                    # character-level voting, a different reference or scorer, the ſ-surface residual — needs
                    # the text. Scores alone would force a full re-run per question.
                    samples.append({"i": pv["i"], "xsrc": xs, "gold": gd, "span": span,
                                    "span_len": len(span), "s_count": span.count("ſ")})
                r2_gold = (None if gold_v is None
                           else evaluate_locus(s.get("r2_text", "") or "", janv.get(v), gold_v)["archaic_id"])
                recs.append({"slug": slug, "book": book, "ch": ch, "v": v,
                             "taux": s.get("taux"), "r2_xsrc": s.get("xsrc_id"), "r2_gold_aid": r2_gold,
                             "known_bad_gold": (None if gold_v is None
                                                else (r2_gold is None or r2_gold < 0.90)),
                             "has_gold": gold_v is not None, "samples": samples})
    OUT.mkdir(exist_ok=True)
    (OUT / f"{slug}.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1))
    return recs


def aggregate() -> dict:
    recs = []
    for f in sorted(OUT.glob("*.json")):
        if f.name.startswith("_"):
            continue
        recs += json.loads(f.read_text())
    kb = [r for r in recs if r.get("known_bad_gold")]
    spreads, singles, oracles, selected, r2s = [], [], [], [], []
    sel_at_taux, oracle_at_taux, single_at_taux = 0, 0, 0
    for r in kb:
        golds = [s["gold"] for s in r["samples"] if s.get("gold") is not None]
        pairs = [(s["xsrc"], s["gold"]) for s in r["samples"]
                 if s.get("gold") is not None and s.get("xsrc") is not None]
        if not golds or not pairs:
            continue
        base = next((s["gold"] for s in r["samples"] if s["i"] == 0 and s.get("gold") is not None), None)
        if base is None:
            continue
        sel_x, sel_g = max(pairs, key=lambda p: p[0])        # production selector: argmax gold-free witness
        spreads.append(max(golds) - min(golds))
        singles.append(base)
        oracles.append(max(golds))
        selected.append(sel_g)
        r2s.append(r["r2_gold_aid"])
        t = r.get("taux") or 0.90
        single_at_taux += base >= 0.90
        oracle_at_taux += max(golds) >= 0.90
        # a real selector may only ACCEPT when its own gold-free score clears taux
        sel_at_taux += (sel_x >= t and sel_g >= 0.90)
    n = len(spreads)
    summary = {
        "n_known_bad_with_samples": n,
        "n_variants_per_region": max((len(r["samples"]) for r in recs), default=0),
        "gold_spread_across_variants": {
            "mean": round(mean(spreads), 4) if n else None,
            "median": round(median(spreads), 4) if n else None,
            "max": round(max(spreads), 4) if n else None,
            "n_spread_gt_0.1": sum(1 for s in spreads if s > 0.1),
            "n_spread_gt_0.3": sum(1 for s in spreads if s > 0.3),
        },
        "mean_gold": {
            "r2": round(mean(r2s), 4) if n else None,
            "single_run_variant0": round(mean(singles), 4) if n else None,
            "selected_gold_free_argmax_xsrc": round(mean(selected), 4) if n else None,
            "oracle_best_by_gold": round(mean(oracles), 4) if n else None,
        },
        "pass_rate_ge_0.90_vs_gold": {
            "single_run_variant0": round(single_at_taux / n, 3) if n else None,
            "selected_gold_free": round(sel_at_taux / n, 3) if n else None,
            "oracle_best_by_gold": round(oracle_at_taux / n, 3) if n else None,
        },
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "_summary.json").write_text(json.dumps({"summary": summary, "records": recs},
                                                  ensure_ascii=False, indent=1))
    return summary


def _print(s):
    sp, mg, pr = s["gold_spread_across_variants"], s["mean_gold"], s["pass_rate_ge_0.90_vs_gold"]
    print("\n" + "=" * 84)
    print("R3 CROP-VARIANCE EXPERIMENT — is R3 geometry-limited or variance-limited?")
    print("=" * 84)
    print(f"known-bad verses sampled: {s['n_known_bad_with_samples']}   variants/region: {s['n_variants_per_region']}")
    print(f"\nCHAOS TERM — gold-score spread across label-preserving crop variants of the SAME region:")
    print(f"  mean {sp['mean']}  median {sp['median']}  max {sp['max']}   "
          f"(>0.1 on {sp['n_spread_gt_0.1']}, >0.3 on {sp['n_spread_gt_0.3']} verses)")
    print(f"\nMEAN GOLD SCORE:  R2 {mg['r2']}  ->  single-run {mg['single_run_variant0']}  ->  "
          f"gold-free-SELECTED {mg['selected_gold_free_argmax_xsrc']}  (oracle ceiling {mg['oracle_best_by_gold']})")
    print(f"PASS-RATE >=0.90: single-run {pr['single_run_variant0']}  ->  "
          f"gold-free-SELECTED {pr['selected_gold_free']}  (oracle ceiling {pr['oracle_best_by_gold']})")
    print("\nREAD: 'gold-free-SELECTED' is what production could actually achieve (argmax on the witness, and it")
    print("      may only accept when its own witness score clears taux). If it tracks the oracle, multi-crop")
    print("      consensus is a real lever; if it sits at the single-run number, R3 is variance-limited.")


def main():
    args = sys.argv[1:]
    if "--aggregate" in args:
        _print(aggregate())
        return 0
    nv = 4
    if "--variants" in args:
        nv = int(args[args.index("--variants") + 1])
    slugs = [a for a in args if not a.startswith("--") and not a.isdigit()] or sorted(LOCI)
    t0 = time.time()
    for slug in slugs:
        ck = OUT / f"{slug}.json"
        if ck.exists() and "--force" not in args:
            print(f"[skip] {slug}"); continue
        print(f"[run ] {slug} ...", flush=True)
        try:
            recs = page_variance(slug, r3_route._default_transcribe, nv)
            print(f"       {slug}: {len(recs)} flagged verses x {nv} variants ({time.time()-t0:.0f}s)", flush=True)
        except Exception as e:
            print(f"       {slug} ERROR: {type(e).__name__}: {e}", flush=True)
    reocr_r3.shutdown_mlx()
    _print(aggregate())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
