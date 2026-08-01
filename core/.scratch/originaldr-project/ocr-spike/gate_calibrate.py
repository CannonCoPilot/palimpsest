#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_calibrate.py — M5: calibrate the R3 escalation gate on the gold pages (2026-07-22).

The confidence gate is the gold-free router: it must flag the loci where R2 failed (< 0.90) so they escalate
to R3, WITHOUT gold at runtime. §7's core worry is that recognizer confidence is a SELF-REPORT blind to
systematic (confident-wrong) misreads. This harness measures, on the gold pages (the only place "R2 failed"
is checkable), whether per-verse recognizer confidence actually predicts the per-verse identity failure —
and calibrates the threshold τ at RECALL = 1 on the known-bad set (every R2<0.90 verse flagged), reporting the
resulting escalation rate. If recall=1 forces the escalation rate too high, that is an ALERT to strengthen the
gate with the external alarms (length-anomaly, cross-source divergence) — never to lower recall (No Silent
Degradation: a known-bad verse must never be silently accepted).

Signals measured per janvier verse (all gold-free):
  conf     — length-weighted mean recognizer confidence of the R2 body lines assigned to the verse (alarm 1).
  open     — verse_seg length-sanity OPEN flag (structural anomaly; alarm 3).
  s_susp   — suspected long-ſ-as-f (ſ-fidelity alarm; alarm 4).
  xsrc_id  — CROSS-SOURCE alarm 2 (§7): R2's per-verse identity vs the reference-WITNESS cascade
             (s_dismas→odr_com archaic; janvier/sabates_a modern), janvier-cut, archaic-preeminent. This is
             the only alarm with visibility into SYSTEMATIC (confident-wrong) misreads: the witness is an
             independent, ~0.97-faithful (DIV-1) reading available at runtime for all 76 books, so it is
             gold-free yet a strong proxy for "did R2 diverge from the true text here?". It NEVER accepts a
             reading (low → flag-IN → escalate; high → not-flagged, but never a pass — agreement≠truth).
Target (gold, eval-only): archaic-id vs janvier-cut GOLD; a verse is KNOWN-BAD iff archaic-id < 0.90. Note the
gold (target) and the witness (xsrc signal) are DIFFERENT texts — the witness is available in production, gold
is not; xsrc predicting known-bad is a legitimate gold-free proxy, not circular.

Usage: ocr-venv/bin/python ocr-spike/gate_calibrate.py [slug ...]
"""
from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path
from statistics import mean

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from char_identity import evaluate_locus, fold_archaic, edit_ratio, suspected_long_s_as_f  # noqa: E402
import verse_seg as VS  # noqa: E402
import reocr_core as core  # noqa: E402
import verse_locate  # noqa: E402
import gold_grid  # noqa: E402  # the FAIR per-verse reference (printed markers, not the aligner)  # hybrid localizer (best_spans) — the production segmentation as of 2026-07-27
from xsrc_gate import archaic_cut, verse_xsrc, anchor_disagreement  # noqa: E402  # single source of truth for §7 alarm-2

GT = HERE / "ground-truth"
_VTAG = re.compile(r"^(\d+):(\d+)([a-c])?$")
# LOCI comes from gt_registry (the GT files' own `locus` field), never a hand-typed literal. The literal that
# stood here had drifted: it omitted scripture-2john entirely and, separately, colossians-3.
#
# EXCLUSIONS ARE NOW DECLARED, NOT ABSENT. A page dropped by omission is invisible in the output and reads as
# a page that passed; a page dropped by DECLARATION is printed with its reason every run. colossians-3 stays
# out of the CALIBRATION arithmetic (a known §4-addressing / §11-layout confound would corrupt a threshold
# fitted on it) but it is reported in its own bucket, which is the difference between an exclusion and a
# disappearance.
import gt_registry as _REG  # noqa: E402
CALIB_EXCLUDE = {
    "scripture-colossians-3": "FLAGGED §4 ADDR / §11 greek-margins confound (§13 Q5) — would corrupt a fitted "
                              "threshold; reported separately, never silently dropped",
}
LOCI = {k: v for k, v in _REG.loci("scripture").items() if k not in CALIB_EXCLUDE}
LOCI_EXCLUDED = {k: (_REG.loci("scripture").get(k), why) for k, why in CALIB_EXCLUDE.items()}


def gold_by_chapter(gt: dict) -> dict[int, str]:
    by: dict[int, list[str]] = {}
    for L in gt.get("body", []):
        if L.get("role") in ("catchword", "excluded", "signature"):
            continue
        m = _VTAG.match((L.get("verse") or "").strip())
        if m and isinstance(L.get("text"), str) and L["text"].strip():
            by.setdefault(int(m.group(1)), []).append(L["text"].strip())
    return {ch: re.sub(r"-\s+", "", " ".join(v)) for ch, v in by.items()}


CACHE = HERE / ".page-cache"
# Which localizer cuts R2 into verses for the calibration. 'hybrid' = verse_locate.best_spans (production as of
# 2026-07-27); 'align' = the incumbent global aligner (the 2026-07-23 operating point). Kept switchable because
# the recall/escalation trade-off is a property of the SEGMENTER as much as of τx, so the two must be
# comparable on identical inputs rather than across two differently-built runs.
ENGINE = "hybrid"
# Reference grid for the known-bad labels: True = gold_grid (printed markers), False = legacy aligner cut.
GOLD_GRID = True
# Use recovered printed verse numbers as self-labelling anchors + the alarm-5 input.
# ALARM 5 IS OFF BY DEFAULT — MEASURED, not assumed (2026-07-27).
#   four alarms, fair reference:  recall 1.000 @ tx=0.90 -> 24% escalation, 18 false alarms
#   + alarm 5:                    recall 1.000 @ tx=0.90 -> 40% escalation, 44 false alarms
# It was built for the one known-bad verse invisible to the other four (psalms-118 118:109) — which turned
# out to be a REFERENCE defect, not a segmentation one: the span was correct and gold_grid had mislabelled
# the verse. With the instrument fixed, alarm 5 catches nothing additional here and costs 16 points of
# escalation, because its precision is bounded by anchor recovery (45 accepted of 145 openings = 31%) and its
# firings are dominated by sparse/imperfect anchors rather than genuine disagreements.
# It is KEPT, not deleted: the failure class it detects — a span pointed at the wrong place while reading as
# fluent scripture — is real and invisible to every content-based alarm; this gold set simply contains no
# instance of it. Turn it on when anchor recovery improves, or on a page where the two disagree.
USE_ANCHORS = False
# Anchors have TWO possible uses and they are NOT equally safe (measured 2026-07-27):
#   ALARM  (alarm 5) — flag-in only, never alters text.        SAFE: it can only escalate.
#   SPANS  (rewrite a verse's start)                           NOT SAFE YET: known-bad 24 -> 45.
# A lone accepted anchor moves ONE verse's start without moving its neighbour's, so the two spans become
# mutually inconsistent and both degrade. The anchor is right about its own verse and silent about the rest;
# using it to rewrite spans needs a joint re-solve (every verse re-placed subject to all anchors at once),
# which is not built. Until then the anchor earns its keep as the fifth ALARM and does not touch the output.
ANCHOR_SPANS = False


def cached_page(slug: str, od: str, pi: int) -> dict:
    """The page's R2 result, from `.page-cache/` when present. Kraken re-recognition is ~10s/page and cannot
    change any segmentation or threshold question asked here, so reading the cache makes a full recalibration
    instant. Falls back to a live `reocr_page` — deleting the cache costs time, never correctness."""
    f = CACHE / f"{slug}.json"
    if f.exists():
        d = json.loads(f.read_text())
        return {"page_px": tuple(d["page_px"]), "r2_body": d["r2_body"], "lines": d["lines"]}
    return core.reocr_page(od, pi, want_base=False, want_r1=False)


VNUM = HERE / ".verse-numbers"


def page_anchors(slug: str, chapter: int, book: str) -> dict[int, int]:
    """Recovered printed verse numbers for this page, restricted to the chapter being scored.

    Cached by `build_verse_numbers.py` — a recovered number cannot change unless the page image does, so the
    olmOCR gutter reads are paid for once."""
    f = VNUM / f"{slug}.json"
    if not USE_ANCHORS or not f.exists():
        return {}
    d = json.loads(f.read_text())
    janv = set(VS.chapter_verses(book, chapter, VS.JANVIER))
    return {int(v): li for v, li in d.get("anchors", {}).items() if int(v) in janv}


def page_spans(page_result: dict, book: str, ch: int, anchors: dict | None = None) -> dict[int, dict]:
    """Cut this page's R2 body into janvier verses with the configured engine (see ENGINE)."""
    if ENGINE == "hybrid":
        return verse_locate.best_spans(page_result, book, ch, anchors=anchors)
    janv = VS.chapter_verses(book, ch, VS.JANVIER)
    return VS.segment(page_result["r2_body"], janv, drop_apparatus=True) if janv else {}


def verse_records(slug: str) -> list[dict]:
    gt = json.loads((GT / f"{slug}.json").read_text())
    book = LOCI.get(slug)
    od, pi = gt.get("ocr_dir"), gt.get("page_index")
    if not book or od is None:
        return []
    r = cached_page(slug, od, pi)
    body_lines = [l for l in r["lines"] if l["role"] == "body"]
    recs = []
    for ch, gold_text in sorted(gold_by_chapter(gt).items()):
        janv = VS.chapter_verses(book, ch, VS.JANVIER)
        if not janv:
            continue
        # THE REFERENCE. `gold_grid` cuts the gold at the PRINTED verse markers; the legacy path cut it with
        # `verse_seg.segment` — the incumbent aligner — which charged every boundary-word disagreement to the
        # challenger and mislabelled real verses as known-bad (measured 2026-07-27: on the fair grid the
        # hybrid worsens ZERO verses, where the aligner-cut grid showed 11). Verses the printed markers could
        # not resolve are returned EMPTY by the grid and skipped, never silently aligner-cut.
        if GOLD_GRID:
            gg = gold_grid.build_grid(gt, ch, book)
            gold_j = {v: {"text": t} for v, t in gg["verses"].items() if t}
        else:
            gold_j = VS.segment(gold_text, janv)
        anc = page_anchors(slug, ch, book)
        r2_j = page_spans(r, book, ch, anchors=(anc if ANCHOR_SPANS else None))
        arc_cut, arc_src = archaic_cut(book, ch, janv)   # gold-free archaic witness ref (§7 alarm-2), janvier-cut
        # assign each body LINE to the localized janvier verse its text best matches → per-verse conf
        loc_v = sorted(r2_j)
        conf_num: dict[int, float] = {v: 0.0 for v in loc_v}
        conf_den: dict[int, float] = {v: 0.0 for v in loc_v}
        for l in body_lines:
            lf = fold_archaic(l["text"])
            if not lf.strip() or not loc_v:
                continue
            bestv = max(loc_v, key=lambda v: edit_ratio(lf, fold_archaic(janv.get(v, ""))))
            w = max(1, l.get("nchars") or len(l["text"]))   # cached lines store nchars=None -> fall back to text
            conf_num[bestv] += l["conf"] * w
            conf_den[bestv] += w
        for v in sorted(gold_j):
            r2_text = r2_j[v]["text"] if v in r2_j else ""      # "" when R2 failed to localize the verse
            aid = evaluate_locus(r2_text, janv.get(v), gold_j[v]["text"])["archaic_id"] if v in r2_j else None
            # §7 alarm-2 (GOLD-FREE): R2 vs the reference-witness cascade, archaic-preeminent — via xsrc_gate,
            # the SAME module production uses (calibrator and production share one implementation → no drift).
            xs = verse_xsrc(r2_text, janv.get(v), arc_cut.get(v))
            anc_bad = anchor_disagreement(r2_j, anc).get(v) if anc else None
            conf = (conf_num.get(v, 0.0) / conf_den[v]) if conf_den.get(v) else None
            recs.append({
                "slug": slug, "ch": ch, "v": v,
                "archaic_id": aid, "known_bad": (aid is None or aid < 0.90),
                "conf": round(conf, 4) if conf is not None else None,
                "open": (v in r2_j and bool(r2_j[v].get("open"))),
                "s_susp": suspected_long_s_as_f(r2_text, gold_j[v]["text"])["suspected_long_s_as_f"],
                # cross-source alarm-2 signal + provenance (which witness axis governed), from xsrc_gate
                **{k: xs[k] for k in ("xsrc_id", "xsrc_gate", "xsrc_archaic_id", "xsrc_modern_id")},
                "arc_src": (arc_src if v in arc_cut else None),
                "anchor_mismatch": anc_bad,          # alarm 5 (structural: identity, not quality)
            })
    return recs


def calibrate(recs: list[dict]):
    bad = [r for r in recs if r["known_bad"]]
    good = [r for r in recs if not r["known_bad"]]
    print(f"\n{'='*80}\nM5 GATE CALIBRATION — {len(recs)} gold verses ({len(bad)} known-bad R2<0.90, {len(good)} good)\n")

    # 1) Is confidence predictive at all? mean conf of bad vs good.
    cb = [r["conf"] for r in bad if r["conf"] is not None]
    cg = [r["conf"] for r in good if r["conf"] is not None]
    print(f"mean recognizer conf:  known-bad={round(mean(cb),4) if cb else None}   "
          f"good={round(mean(cg),4) if cg else None}   "
          f"(if ~equal → conf is self-report-BLIND, §7 alarm-1)")

    # 2) conf-only gate at RECALL=1: τ = just above the highest-conf known-bad verse; escalation rate at that τ.
    if cb:
        tau = max(cb)  # to catch ALL bad, must flag conf <= tau
        flagged = [r for r in recs if r["conf"] is not None and r["conf"] <= tau]
        fb = sum(1 for r in flagged if r["known_bad"])
        print(f"\nconf-only gate @ recall=1: τ={tau:.4f} (flag conf ≤ τ) → flags {len(flagged)}/{len(recs)} "
              f"({100*len(flagged)/len(recs):.0f}% escalate), catches {fb}/{len(bad)} bad. "
              f"false-alarm={len(flagged)-fb} good verses.")
        worst_bad_conf = sorted(cb, reverse=True)[:3]
        print(f"  highest-conf known-bad verses (the confident-wrong tail): {[round(x,3) for x in worst_bad_conf]}")

    # 3) OR-combined gate: conf<τ0 OR verse_seg-OPEN OR ſ-suspect. Sweep τ0 for best recall/escalation tradeoff.
    print(f"\nOR-gate (conf<τ0 OR open OR ſ-suspect) — recall & escalation vs τ0:")
    print(f"  {'τ0':>6} {'recall':>7} {'escalate%':>10} {'caught/bad':>11}")
    for tau0 in (0.80, 0.85, 0.90, 0.92, 0.95, 0.98):
        def fires(r):
            return (r["conf"] is not None and r["conf"] < tau0) or r["open"] or r["s_susp"]
        flagged = [r for r in recs if fires(r)]
        caught = sum(1 for r in flagged if r["known_bad"])
        recall = caught / len(bad) if bad else 1.0
        print(f"  {tau0:>6} {recall:>7.3f} {100*len(flagged)/len(recs):>9.0f}% {f'{caught}/{len(bad)}':>11}")
    # external-alarm coverage of the confident-wrong tail (bad verses conf-gate misses)
    tail = []
    if cb:
        conf_thresh = 0.92
        tail = [r for r in bad if r["conf"] is not None and r["conf"] >= conf_thresh]
        ext_caught = sum(1 for r in tail if r["open"] or r["s_susp"])
        print(f"\nconfident-wrong tail (known-bad with conf≥{conf_thresh}): {len(tail)}; "
              f"of these, internal alarms 1+3+4 (conf/open/ſ) catch {ext_caught}. "
              f"{'→ external alarm 2 needed' if tail else ''}")

    # ---- alarm 2: CROSS-SOURCE divergence (R2 vs the reference-witness cascade, janvier-cut) ----
    # The §7 thesis under test: unlike conf (self-report-blind), the witness signal SEPARATES bad from good
    # because the witness is an independent ~0.97-faithful reading of the true text (DIV-1) available in
    # production. Gold-free: the witness is not gold.
    from collections import Counter
    xb = [r["xsrc_id"] for r in bad if r.get("xsrc_id") is not None]
    xg = [r["xsrc_id"] for r in good if r.get("xsrc_id") is not None]
    print(f"\n{'-'*80}\nALARM 2 — cross-source (R2 vs witness cascade, janvier-cut, archaic-preeminent):")
    print(f"mean xsrc_id:  known-bad={round(mean(xb),4) if xb else None}   good={round(mean(xg),4) if xg else None}"
          f"   (bad << good ⇒ SEPARATES — the signal conf lacks)")
    gates = Counter(r.get("xsrc_gate") for r in recs)
    n_mod = gates.get("modern", 0)
    mod_bad = [r["xsrc_id"] for r in bad if r.get("xsrc_gate") == "modern" and r.get("xsrc_id") is not None]
    print(f"witness axis: {dict(gates)}  (archaic-gap verses use the MODERN fallback; "
          + (f"{n_mod} present incl. GT-3 abdias — fallback CALIBRATED, axis τx=0.92, max modern known-bad "
             f"xsrc={max(mod_bad):.4f})" if mod_bad else
             f"{n_mod} present, none known-bad → add more archaic-gap gold to stress the fallback)"))

    if xb:
        # xsrc-only gate @ recall=1: flag xsrc_id ≤ τx; τx = the HIGHEST-xsrc known-bad (the witness-blind tail)
        taux = max(xb)
        fl = [r for r in recs if r.get("xsrc_id") is not None and r["xsrc_id"] <= taux]
        fb = sum(1 for r in fl if r["known_bad"])
        print(f"\nxsrc-only gate @ recall=1: τx={taux:.4f} → flags {len(fl)}/{len(recs)} "
              f"({100*len(fl)/len(recs):.0f}% escalate), catches {fb}/{len(bad)} bad, "
              f"false-alarm={len(fl)-fb}.   [conf-only needed 88% for the same recall]")
        # the highest-xsrc known-bad verses set the τx FLOOR (the thinnest-margin catches). They are still
        # caught at τx=0.90, but the margin is small → the operating-point risk to track: if GT expansion ever
        # surfaces a known-bad with xsrc ABOVE τx, the FULL-gate sweep below reports recall<1 and ALERTs
        # (approach redesign), never a silent miss. Surface them so the margin is visible, never hidden.
        wb = sorted((r for r in bad if r.get("xsrc_id") is not None), key=lambda r: -r["xsrc_id"])[:3]
        print(f"  thinnest-margin known-bad (set the τx floor at {taux:.4f}; caught at τx=0.90, margin "
              f"{0.90-taux:.4f}): "
              + ", ".join(f"{r['slug'].split('scripture-')[-1]} {r['ch']}:{r['v']}=xsrc{r['xsrc_id']}(arc={r['arc_src']})" for r in wb))

    # confident-wrong tail: does alarm 2 catch what conf misses? (the headline of finding #1)
    if tail:
        for tx in (0.90, 0.92, 0.95):
            c = sum(1 for r in tail if r.get("xsrc_id") is not None and r["xsrc_id"] < tx)
            print(f"  confident-wrong tail (n={len(tail)}): alarm-2 xsrc<{tx} catches {c}/{len(tail)}  "
                  f"({100*c/len(tail):.0f}%)")

    # ---- FULL four-alarm gate: escalate = conf<0.92 OR open OR ſ OR xsrc<τx. Find smallest escalation @ recall=1.
    print(f"\nFULL gate (conf<0.92 OR open OR ſ OR xsrc<τx) — recall & escalation vs τx:")
    print(f"  {'τx':>6} {'recall':>7} {'escalate%':>10} {'caught/bad':>11} {'false-alarm':>12}")

    def fires_full(r, taux):
        # ALARM 5 included: a span that contradicts its own printed verse number is escalated on IDENTITY
        # grounds, which no content-based alarm can see (psalms-118 118:109: xsrc 0.985, conf 0.973, gold 0.0).
        return (bool(r.get("anchor_mismatch")) or (r["conf"] is not None and r["conf"] < 0.92)
                or r["open"] or r["s_susp"]
                or (r.get("xsrc_id") is not None and r["xsrc_id"] < taux))
    best = None
    for taux in (0.80, 0.85, 0.90, 0.92, 0.95, 0.98):
        fl = [r for r in recs if fires_full(r, taux)]
        caught = sum(1 for r in fl if r["known_bad"])
        recall = caught / len(bad) if bad else 1.0
        print(f"  {taux:>6} {recall:>7.3f} {100*len(fl)/len(recs):>9.0f}% {f'{caught}/{len(bad)}':>11} {len(fl)-caught:>12}")
        if recall >= 1.0 and best is None:
            best = (taux, len(fl), len(fl) - caught)
    if best:
        print(f"\n⇒ recall=1 (ALL {len(bad)} known-bad flagged, No-Silent-Degradation MET) at τx={best[0]} → "
              f"{100*best[1]/len(recs):.0f}% escalation, {best[2]} false-alarms — a REAL gate vs conf-only's 88%.")
    else:
        # No τx reaches recall=1 → some known-bad is invisible to ALL four alarms. ALERT, never accept.
        missed = [r for r in bad if not fires_full(r, 0.98)]
        print(f"\n⚠ ALERT (No Silent Degradation): recall<1 at every τx — {len(missed)} known-bad verse(s) invisible "
              f"to all four alarms. NOT accepted; the approach (recognizer/preproc/reference) needs redesign:")
        for r in missed[:12]:
            print(f"    MISSED {r['slug'].split('scripture-')[-1]} {r['ch']}:{r['v']}  gold-archaic_id={r['archaic_id']} "
                  f"xsrc_id={r.get('xsrc_id')} conf={r['conf']} open={r['open']} ſ={r['s_susp']}")


def main():
    global ENGINE, GOLD_GRID
    args = sys.argv[1:]
    if "--aligner-grid" in args:
        GOLD_GRID = False
        args.remove("--aligner-grid")
    for a in list(args):
        if a.startswith("--engine="):
            ENGINE = a.split("=", 1)[1]
            args.remove(a)
    if ENGINE not in ("hybrid", "align"):
        print(f"unknown --engine={ENGINE} (expected 'hybrid' or 'align')")
        return 2
    slugs = args or [s for s in sorted(p.stem for p in GT.glob('scripture-*.json')) if s in LOCI]
    recs = []
    for slug in slugs:
        recs += verse_records(slug)
    print(f"[segmentation] engine = {ENGINE}   [reference] {'gold_grid (printed markers)' if GOLD_GRID else 'aligner-cut (legacy)'}")
    calibrate(recs)
    out = HERE / (".gate-calibration.json" if ENGINE == "hybrid" else f".gate-calibration-{ENGINE}.json")
    out.write_text(json.dumps(recs, ensure_ascii=False, indent=2))
    print(f"\nwrote {out.name} ({len(recs)} verse records, engine={ENGINE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
