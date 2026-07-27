#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xsrc_gate.py — §7 ALARM 2: cross-source-disagreement routing, the gold-free R3 gate (2026-07-22).

THE finding this module operationalizes (calibrated in `gate_calibrate.py`, 165 gold verses): recognizer
confidence is SELF-REPORT-BLIND to systematic misreads — mean conf on known-bad R2 verses 0.9798 vs good
0.9878 (indistinguishable); conf=1 recall forces 88% escalation. The one signal with visibility into the
confident-wrong tail is CROSS-SOURCE divergence: R2's per-verse reading vs an INDEPENDENT reference witness.

  mean xsrc_id  known-bad 0.7143  vs  good 0.9357   (gap 0.22 — where conf's gap was 0.008)
  confident-wrong tail (40 verses, conf>=0.92, internal alarms catch 0): alarm-2 catches 40/40
  FULL gate recall=1 (all 43 known-bad) at tx=0.90 -> 34% escalation (vs conf-only 88%), 0 blind spots.

WHY a witness, not the other scan sources' OCR (§7's literal "other curated sources"): No Silent Degradation
demands the gate flag EVERY truly-failed verse, so the independent reference must be the highest-quality
estimate of the true text available at runtime. The reference witnesses (s_dismas->odr_com archaic;
sabates_a/madueke_b modern) are ~0.97-faithful (DIV-1) and cover all 76 books — a strictly better independent
estimate than base OCR (~0.5). Comparing R2 to the witness cascade IS "cross-source disagreement", instantiated
with the strongest source. It is GOLD-FREE (a witness is not gold) and it NEVER accepts a reading: low xsrc ->
flag-IN (escalate); high xsrc -> not-flagged, but never a pass (agreement != truth; §7 P3).

Archaic-preeminent (mirrors char_identity.evaluate_locus + reference_construction): where an archaic witness
exists, xsrc = archaic surface identity vs s_dismas (the sharp signal for the ſ/f + spelling misreads that are
R2's failure mode); in the 17-book / 22.6%-loci archaic GAP, xsrc falls back to modern content identity vs
janvier. The gap fallback is UNCALIBRATED (all 5 current gold books carry s_dismas) — GT-3 must add an
archaic-gap book before the fallback tx is trusted (tracked in §7 / §12 M2).

Everything here is a WITNESS + janvier computation — no gold, no recognizer. Pair it with verse_seg (which cuts
R2 to the janvier grid) + char_identity (the identity metric). Boundary-fair by P5: witness and R2 are cut by
the SAME janvier grid.

Usage:
  ocr-venv/bin/python ocr-spike/xsrc_gate.py            # self-check (recognizer-free: witness-side determinism)
  from xsrc_gate import cross_source_verse_scores, page_escalates   # production routing
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from char_identity import evaluate_locus  # noqa: E402
import verse_seg as VS  # noqa: E402

# Calibrated operating points (gate_calibrate.py, 2026-07-22/23, 15 gold pages / 165 verses):
#   ARCHAIC axis (R2 vs s_dismas surface): recall=1 at τx=0.90 → 34% escalation, 0 blind spots (max-bad 0.8954).
#   MODERN-fallback axis (R2 vs janvier content — the archaic-GAP books, 17 books / 22.6% loci, no archaic
#     witness): the axis still SEPARATES (mean bad 0.720 vs good 0.926, gap 0.21) but the archaic↔modern surface
#     noise pushes the max-bad to 0.9044, so recall=1 needs τx=0.92 → 38% escalation (2026-07-23 calibration on
#     the existing gold's modern axis, which simulates the fallback: R2 is archaic, janvier modern either way).
# The gate is AXIS-AWARE: it applies the τx of whichever reference governed each verse. Re-validate every GT-3
# expansion (DIV-2 cadence); a known-bad above its axis τx must ALERT, never be silently missed.
TAUX_ARCHAIC = 0.90
TAUX_MODERN = 0.92
TAUX = TAUX_ARCHAIC        # back-compat default (archaic-preeminent); axis-aware logic overrides per verse

# archaic witness cascade for the cross-source reference (NOT gold): s_dismas preeminent, odr_com backfill.
ARCHAIC_WITNESSES = ("s_dismas", "odr_com")


def archaic_cut(book: str, chapter: int, janv: dict[int, str]) -> tuple[dict[int, str], str | None]:
    """The best archaic WITNESS's chapter, re-cut to the janvier grid -> ({verse->text}, source name).

    Cascade s_dismas->odr_com. Gold-free (a witness, not gold). Cutting the witness to the SAME janvier grid
    R2 is cut to (P5 linchpin) makes the per-verse comparison boundary-fair. ({}, None) in the archaic gap
    (caller falls back to the modern content axis via janvier)."""
    for name in ARCHAIC_WITNESSES:
        cv = VS.chapter_verses(book, chapter, name)
        if cv:
            body = " ".join(cv[v] for v in sorted(cv))
            seg = VS.segment(body, janv)          # janvier-cut; witness text is clean -> drop_apparatus off
            return {v: d["text"] for v, d in seg.items()}, name
    return {}, None


def verse_xsrc(r2_text: str, janv_v: str | None, arc_v: str | None) -> dict:
    """Cross-source identity for ONE janvier verse: R2's text vs the witness cascade, archaic-preeminent.

    janv_v = janvier (sabates_a) verse surface (the MODERN content reference);
    arc_v  = the janvier-cut archaic witness verse surface (s_dismas/odr_com), or None in the archaic gap.
    Returns the archaic-preeminent xsrc_id (archaic where an archaic ref exists, else modern) plus both axes
    and which gate governed — so a caller can see the provenance. r2_text='' (R2 missed the verse) -> xsrc 0.0."""
    xs = evaluate_locus(r2_text, janv_v, arc_v)
    xsrc_id = xs["archaic_id"] if xs["archaic_ref_exists"] else xs["modern_id"]
    return {
        "xsrc_id": round(xsrc_id, 4) if xsrc_id is not None else None,
        "xsrc_gate": xs["governing_gate"],                 # 'archaic' | 'modern' | 'needs-reference'
        "xsrc_archaic_id": xs["archaic_id"],
        "xsrc_modern_id": xs["modern_id"],
    }


def axis_taux(xsrc_gate: str, override: float | None = None) -> float:
    """The calibrated τx for the axis that governed a verse: modern-fallback books need a higher bar (0.92)
    than the archaic-witness case (0.90), per the 2026-07-23 calibration. `override` forces a single τx."""
    if override is not None:
        return override
    return TAUX_MODERN if xsrc_gate == "modern" else TAUX_ARCHAIC


def anchor_disagreement(spans: dict[int, dict], anchors: dict[int, int]) -> dict[int, str]:
    """ALARM 5 — a verse's span disagrees with its own PRINTED verse number.

    WHY THE OTHER FOUR CANNOT RAISE THIS. Alarms 1-4 (confidence, length-sanity, ſ-suspicion, cross-source
    identity) all ask "does this TEXT look right?". They are structurally blind to a span that is pointed at
    the wrong place but reads as fluent scripture: psalms-118 118:109 scored 0.0 against gold while its
    cross-source identity was 0.985 and its recognizer confidence 0.973 — every content alarm saw a clean
    verse, because the text WAS clean; it simply belonged to a different verse.

    A printed verse number is the one signal that is about IDENTITY rather than quality. If the printer says
    verse 109 opens on line 34 and the segmenter has put verse 109 somewhere else, exactly one of them is
    wrong and the verse must not be accepted either way. That is a gold-free structural check, and it is the
    alarm the four content-based ones leave open.

    Returns {verse -> reason} for every disagreement. Flag-IN only: it escalates, it never accepts.
    """
    out: dict[int, str] = {}
    for v, line in anchors.items():
        d = spans.get(v)
        if d is None:
            out[v] = (f"the page prints verse {v} (line {line}) but the segmenter did not localize it — "
                      "a verse the printer says is here was not found")
            continue
        lines = d.get("lines") or []
        if line not in lines:
            out[v] = (f"the page prints verse {v} at line {line}, but its span covers lines "
                      f"{lines[:4]}{'…' if len(lines) > 4 else ''} — span and printed number disagree")
    # a printed number falling INSIDE another verse's span is the same fault seen from the other side, and
    # catches the case where the mislabelled verse was never anchored itself.
    for v, d in spans.items():
        for w, line in anchors.items():
            if w != v and line in (d.get("lines") or []) and v not in out:
                out[v] = (f"verse {v}'s span covers line {line}, where the page prints verse {w} — "
                          "the span has absorbed a neighbour's opening")
    return out


def cross_source_verse_scores(r2_body: str, book: str, chapter: int, *, taux: float | None = None,
                              drop_apparatus: bool = True,
                              spans: dict[int, dict] | None = None,
                              anchors: dict[int, int] | None = None) -> dict[int, dict]:
    """PRODUCTION alarm-2 (gold-free): per-verse cross-source escalation for one page's R2 body text.

    Cuts `r2_body` to the janvier grid (verse_seg localizes which verses are on the page — VS-2), pulls the
    archaic witness cascade + janvier for those verses, and scores each. A verse ESCALATES iff its cross-source
    identity is below `taux` (R2 diverges from the independent witness beyond the calibrated bar) OR verse_seg
    flagged it structurally OPEN. Escalation is flag-IN only: it routes the verse to R3; it never accepts one.

    `spans`: a PRE-COMPUTED segmentation of this page ({verse -> {text, open, reason, tok_lo, tok_hi, source,
    fit}}), normally `verse_locate.best_spans` — the HYBRID localizer, which picks per verse between global
    alignment and the anchor-walk on their gold-free janvier fit (measured +3.3pp mean identity / +16 passing
    verses over alignment alone on the 177 gold verses, Wilcoxon p=0.00007). Segmentation quality is a GATE
    input, not a detail: a verse whose span points at the wrong place scores low against the witness and is
    escalated as an OCR failure, so better localization shrinks the flagged set to verses that are genuinely
    misread. The same dict must be handed to `verse_geom` so the crop is cut from the span that was scored.
    Omit it and the gate re-segments with the incumbent aligner (the calibrated 2026-07-23 behaviour, and the
    only option when a caller has body text but no page geometry).

    Returns {verse -> {xsrc_id, xsrc_gate, escalate, seg_open, arc_src, r2_text, ...}} for the localized verses.
    Empty dict if R2's body localizes to no verse of this chapter (itself a page-level OPEN the caller surfaces)."""
    janv = VS.chapter_verses(book, chapter, VS.JANVIER)
    if not janv:
        return {}                                          # janvier lacks the chapter -> caller surfaces OPEN
    r2_j = spans if spans is not None else VS.segment(r2_body, janv, drop_apparatus=drop_apparatus)
    if not r2_j:
        return {}
    arc_cut, arc_src = archaic_cut(book, chapter, janv)
    anchor_bad = anchor_disagreement(r2_j, anchors) if anchors else {}
    out: dict[int, dict] = {}
    for v in sorted(r2_j):
        r2_text = r2_j[v].get("text", "")
        seg_open = bool(r2_j[v].get("open"))
        xs = verse_xsrc(r2_text, janv.get(v), arc_cut.get(v))
        vtaux = axis_taux(xs["xsrc_gate"], override=taux)   # 0.90 archaic / 0.92 modern-fallback (calibrated)
        below = xs["xsrc_id"] is None or xs["xsrc_id"] < vtaux
        anc_bad = anchor_bad.get(v)
        out[v] = {
            **xs,
            "anchor_mismatch": anc_bad,                    # alarm-5 (structural, identity not quality)
            "escalate": bool(below or seg_open or anc_bad),  # alarm-2 OR structural OPEN OR alarm-5 -> flag-IN
            "xsrc_below_taux": bool(below),
            "seg_open": seg_open,
            "arc_src": (arc_src if v in arc_cut else None),
            "taux": vtaux,
            "r2_text": r2_text,
            "ref_archaic": arc_cut.get(v),
            "ref_modern": janv.get(v),
            # segmentation provenance: WHICH localizer produced the span this score is about. A flagged verse
            # is an OCR verdict only if its span is in the right place, so the router and the OPEN ledger need
            # to see the engine behind it rather than inherit an anonymous string.
            "seg_source": r2_j[v].get("source", "align"),
            "seg_fit": r2_j[v].get("fit"),
        }
    return out


def page_escalates(r2_body: str, book: str, chapter: int, *, taux: float | None = None,
                   spans: dict[int, dict] | None = None) -> dict:
    """Page-level roll-up of alarm-2: does ANY localized verse fire? Returns {escalate, n_verses, n_flagged,
    flagged_verses, worst_xsrc}. A page with no localizable verse is escalate=True (a no-locate OPEN — never
    silently clean). `spans` as in cross_source_verse_scores (pass the page's hybrid segmentation)."""
    scores = cross_source_verse_scores(r2_body, book, chapter, taux=taux, spans=spans)
    if not scores:
        return {"escalate": True, "reason": "no-locate", "n_verses": 0, "n_flagged": 0,
                "flagged_verses": [], "worst_xsrc": None}
    flagged = [v for v, s in scores.items() if s["escalate"]]
    xs_vals = [s["xsrc_id"] for s in scores.values() if s["xsrc_id"] is not None]
    return {
        "escalate": bool(flagged),
        "n_verses": len(scores), "n_flagged": len(flagged),
        "flagged_verses": sorted(flagged),
        "worst_xsrc": round(min(xs_vals), 4) if xs_vals else None,
    }


# --------------------------------------------------------------------------- #
# self-check (recognizer-free: exercises the witness side deterministically) — no gold, no OCR needed.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    ok = True
    book, ch = "genesis", 24
    janv = VS.chapter_verses(book, ch, VS.JANVIER)
    arc_cut, arc_src = archaic_cut(book, ch, janv)
    print(f"[witness] {book} {ch}: janvier {len(janv)} verses; archaic witness = {arc_src} "
          f"({len(arc_cut)} verses janvier-cut)  (expect s_dismas, ~janvier count)")
    ok = ok and arc_src == "s_dismas" and len(arc_cut) >= 0.8 * len(janv)

    # (1) a PERFECT R2 (= the janvier text itself) must score HIGH vs the witness (both ~the true text) and
    #     NOT escalate — content agrees even though janvier is modern and the witness archaic.
    perfect_body = " ".join(janv[v] for v in sorted(janv))
    sc = cross_source_verse_scores(perfect_body, book, ch)
    hi = [s["xsrc_id"] for s in sc.values() if s["xsrc_id"] is not None]
    hi_mean = sum(hi) / len(hi) if hi else 0.0
    n_esc = sum(1 for s in sc.values() if s["escalate"])
    print(f"[perfect->high] {len(sc)} verses, mean xsrc={hi_mean:.3f}, escalated={n_esc}/{len(sc)}  "
          f"(expect mean high, few escalate)")
    ok = ok and hi_mean >= 0.90

    # (2) GARBAGE R2 over the same grid must localize to nothing OR score LOW and escalate (never silently pass).
    pe = page_escalates("xqz mmm lll ttt zzz qqq vbn plmk foo bar baz qux", book, ch)
    print(f"[garbage->escalate] page_escalates={pe['escalate']} reason/flagged={pe.get('reason', pe['n_flagged'])}  "
          f"(expect escalate=True)")
    ok = ok and pe["escalate"]

    # (3) a single MISREAD verse (corrupt one verse's text) must escalate that verse while clean ones don't —
    #     the per-verse routing the gate promises. Corrupt v3 by replacing its words with junk.
    v_ids = sorted(janv)
    corrupt_v = v_ids[2]
    body2 = " ".join((janv[v] if v != corrupt_v else "zzzq wwxy vbnm plkj hgfd sart qwer") for v in v_ids)
    sc2 = cross_source_verse_scores(body2, book, ch)
    cflag = sc2.get(corrupt_v, {}).get("escalate")
    print(f"[per-verse misread] v{corrupt_v} escalate={cflag} xsrc={sc2.get(corrupt_v, {}).get('xsrc_id')}  "
          f"(expect escalate=True for the corrupted verse)")
    ok = ok and cflag is True

    # (4) gold-free contract: this module imports NO ground-truth; the reference is a reads/ witness. Assert the
    #     archaic reference text is the witness, not gold (sanity: it differs from janvier on a genuinely
    #     archaic-spelled verse). This is a smoke test that arc_cut carries archaic surface.
    print(f"[gold-free] archaic ref source = {arc_src} (a reads/ WITNESS; module never opens ground-truth/)")
    ok = ok and arc_src in ARCHAIC_WITNESSES

    print("\nSELF-CHECK:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
