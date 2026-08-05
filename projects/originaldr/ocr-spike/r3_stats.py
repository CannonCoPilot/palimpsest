#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r3_stats.py — statistical validation of the productionized R3 rung across the gold scripture pages.

For EVERY gate-flagged verse on the gold pages, run the region-based R3 (olmOCR, load-once) and measure the
content lift TWO ways:
  * GOLD-ANCHORED   r2_gold_aid -> r3_gold_aid   (archaic_id vs the Jarvis diplomatic GOLD — the truth; the
                    rigorous measure of how much R3 actually recovered);
  * GOLD-FREE       r2_xsrc     -> r3_xsrc        (vs the reference witness — what PRODUCTION sees at runtime).
Reporting both lets us validate the gold-free proxy against the truth (does the witness-measured lift track the
gold-measured lift?) and quantify the ſ-surface residual olmOCR leaves (it modernizes ſ).

Gold-anchored `archaic_id` folds ſ->s (ſ-blind, per char_identity) so it measures CONTENT+spelling recovery —
the axis olmOCR can lift; the ſ surface is a separate track (r2_s vs r3_s counts + the terminal state).

Per-page results are checkpointed to `.r3-stats/<slug>.json` (resumable). `--aggregate` recomputes the summary
from the checkpoints without re-running olmOCR.

Usage: ocr-venv/bin/python ocr-spike/r3_stats.py [--aggregate] [slug ...]
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
import verse_locate                # noqa: E402
import gate_calibrate as calib      # noqa: E402  (cached_page: the shared cache-aware page loader)
import r3_route                    # noqa: E402
import reocr_r3                     # noqa: E402
import open_ledger                 # noqa: E402
from char_identity import evaluate_locus  # noqa: E402
from gate_calibrate import LOCI, gold_by_chapter  # noqa: E402  # reuse the gold-per-verse machinery

OUT = HERE / ".r3-stats"
GT = HERE / "ground-truth"


def _gold_aid(ocr_text, janv_v, gold_v):
    """Gold-anchored archaic identity (ſ-blind content+spelling) of an OCR span vs the gold verse."""
    if not gold_v:
        return None
    return evaluate_locus(ocr_text or "", janv_v, gold_v)["archaic_id"]


def page_stats(slug, ledger, transcribe) -> list[dict]:
    gt = json.loads((GT / f"{slug}.json").read_text())
    book = LOCI.get(slug)
    od, pi = gt.get("ocr_dir"), gt.get("page_index")
    if not book or od is None:
        return []
    r = calib.cached_page(slug, od, pi)     # .page-cache when present: kraken cannot change any question here
    recs = []
    for ch, gold_text in sorted(gold_by_chapter(gt).items()):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            continue
        gold_j = VS.segment(gold_text, janv)
        # SEGMENT ONCE with the production hybrid localizer, then hand the SAME spans to the gate and to the
        # geometry — the harness must measure the pipeline that ships, and a re-segmentation here would let the
        # scored verse and the cropped verse diverge (see r3_route.rescue_page).
        spans = verse_locate.best_spans(r, book, ch)
        scores = xsrc_gate.cross_source_verse_scores(r["r2_body"], book, ch, spans=spans)   # gold-free gate
        flagged = [v for v in scores if scores[v].get("escalate")]
        if not flagged:
            continue
        crops = verse_geom.verse_crops(r, book, ch, spans=spans)
        regions = verse_geom.region_crops(r, book, ch, flagged, spans=spans)["regions"]
        rr = r3_route.rescue_flagged(od, pi, book, ch, scores, crops,
                                     transcribe=transcribe, ledger=ledger, regions=regions)
        for v in flagged:
            s = scores[v]
            vd = rr["verses"].get(v, {})
            gold_v = (gold_j.get(v) or {}).get("text")
            r2_gold = _gold_aid(s.get("r2_text", ""), janv.get(v), gold_v)
            r3_gold = _gold_aid(vd.get("r3_span", ""), janv.get(v), gold_v)
            recs.append({
                "slug": slug, "book": book, "ch": ch, "v": v,
                "r2_xsrc": s.get("xsrc_id"), "r3_xsrc": vd.get("r3_xsrc"),
                "r2_gold_aid": r2_gold, "r3_gold_aid": r3_gold,
                "has_gold": gold_v is not None,
                "known_bad_gold": (None if gold_v is None else (r2_gold is None or r2_gold < 0.90)),
                "state": vd.get("state"), "s_deficient": vd.get("s_deficient"),
                "r2_s": vd.get("r2_s_count"), "r3_s": vd.get("r3_s_count"),
                "taux": s.get("taux"), "arc_src": s.get("arc_src"),
            })
    OUT.mkdir(exist_ok=True)
    (OUT / f"{slug}.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1))
    return recs


def aggregate() -> dict:
    recs = []
    for f in sorted(OUT.glob("*.json")):
        if f.name.startswith("_"):          # skip _summary.json / _open_ledger.json (not per-page record lists)
            continue
        recs += json.loads(f.read_text())
    gold = [r for r in recs if r.get("has_gold")]
    kb = [r for r in gold if r["known_bad_gold"]]                 # truly-bad-vs-gold among the flagged
    # gate precision on gold pages: of the flagged verses that HAVE gold, how many were truly known-bad
    precision = (len(kb) / len(gold)) if gold else None

    def _liftset(rs, a, b):
        return [(r[a], r[b]) for r in rs if r.get(a) is not None and r.get(b) is not None]

    gl = _liftset(kb, "r2_gold_aid", "r3_gold_aid")               # gold-anchored lift on the truly-bad verses
    deltas = [b - a for a, b in gl]
    r2_pass = sum(1 for a, _ in gl if a >= 0.90)
    r3_pass = sum(1 for _, b in gl if b >= 0.90)
    xl = _liftset(kb, "r2_xsrc", "r3_xsrc")
    xdeltas = [b - a for a, b in xl]

    states = {}
    for r in recs:
        states[r["state"]] = states.get(r["state"], 0) + 1
    s_def = [r for r in recs if r.get("s_deficient") is True]

    summary = {
        "n_flagged_total": len(recs),
        "n_flagged_with_gold": len(gold),
        "gate_precision_vs_gold": round(precision, 3) if precision is not None else None,
        "n_known_bad_vs_gold": len(kb),
        "gold_anchored_lift": {
            "n": len(gl),
            "r2_mean": round(mean([a for a, _ in gl]), 4) if gl else None,
            "r3_mean": round(mean([b for _, b in gl]), 4) if gl else None,
            "mean_delta": round(mean(deltas), 4) if deltas else None,
            "median_delta": round(median(deltas), 4) if deltas else None,
            "max_delta": round(max(deltas), 4) if deltas else None,
            "min_delta": round(min(deltas), 4) if deltas else None,
            "n_positive_lift": sum(1 for d in deltas if d > 0),
            "r2_pass_rate": round(r2_pass / len(gl), 3) if gl else None,
            "r3_pass_rate": round(r3_pass / len(gl), 3) if gl else None,
        },
        "gold_free_lift_witness": {
            "n": len(xl),
            "mean_delta": round(mean(xdeltas), 4) if xdeltas else None,
            "median_delta": round(median(xdeltas), 4) if xdeltas else None,
        },
        "terminal_states": states,
        "s_deficiency_rate": round(len(s_def) / len(recs), 3) if recs else None,
        "s_deficient_count": len(s_def),
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "_summary.json").write_text(json.dumps({"summary": summary, "records": recs}, ensure_ascii=False, indent=1))
    return summary


def _print_summary(s: dict):
    g = s["gold_anchored_lift"]
    print("\n" + "=" * 84)
    print("R3 STATISTICAL VALIDATION — region-based olmOCR across the gold scripture pages")
    print("=" * 84)
    print(f"flagged verses total: {s['n_flagged_total']}  (with gold: {s['n_flagged_with_gold']})")
    print(f"gate precision vs gold: {s['gate_precision_vs_gold']}  "
          f"({s['n_known_bad_vs_gold']} of the flagged are truly R2<0.90 vs gold)")
    print(f"\nGOLD-ANCHORED CONTENT LIFT on the {g['n']} truly-known-bad flagged verses (archaic_id vs gold):")
    print(f"  R2 mean {g['r2_mean']} -> R3 mean {g['r3_mean']}   mean Δ {g['mean_delta']:+}  median Δ {g['median_delta']:+}  "
          f"(range {g['min_delta']:+}..{g['max_delta']:+})")
    print(f"  positive-lift verses: {g['n_positive_lift']}/{g['n']}")
    print(f"  content pass-rate (≥0.90 vs gold):  R2 {g['r2_pass_rate']}  ->  R3 {g['r3_pass_rate']}")
    xw = s["gold_free_lift_witness"]
    print(f"\nGOLD-FREE (production) witness lift: mean Δ {xw['mean_delta']:+} median Δ {xw['median_delta']:+} "
          f"(n={xw['n']}) — sanity vs the gold-anchored measure")
    print(f"\nterminal states: {s['terminal_states']}")
    print(f"ſ-deficiency (olmOCR drops ſ): {s['s_deficient_count']}/{s['n_flagged_total']} "
          f"= {s['s_deficiency_rate']} → the ſ-surface residual owed to the arbiter")


def main():
    args = sys.argv[1:]
    if "--aggregate" in args:
        _print_summary(aggregate())
        return 0
    slugs = [a for a in args if not a.startswith("--")] or [s for s in sorted(LOCI)]
    ledger = open_ledger.OpenLedger()
    t0 = time.time()
    done = 0
    for slug in slugs:
        ck = OUT / f"{slug}.json"
        if ck.exists() and "--force" not in args:
            print(f"[skip] {slug} (checkpoint exists)"); continue
        print(f"[run ] {slug} ...", flush=True)
        try:
            recs = page_stats(slug, ledger, r3_route._default_transcribe)
            done += 1
            fl = len(recs); rescued = sum(1 for r in recs if r["state"] == "RESCUED")
            sopen = sum(1 for r in recs if r["state"] == "RESCUED_CONTENT_S_OPEN")
            print(f"       {slug}: {fl} flagged, {rescued} rescued, {sopen} content-rescued-ſ-open "
                  f"({time.time()-t0:.0f}s elapsed)", flush=True)
        except Exception as e:
            print(f"       {slug} ERROR: {type(e).__name__}: {e}", flush=True)
    reocr_r3.shutdown_mlx()
    ledger.write(OUT / "_open_ledger.json")
    print(f"\nran {done} pages in {time.time()-t0:.0f}s; OPEN ledger: {ledger.summary()}")
    _print_summary(aggregate())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
