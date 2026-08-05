#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coverage_alarm.py — the CATASTROPHIC-FAILURE alarm: is the grammar failing on this page?

WHAT THIS IS FOR. The block grammar dispatches a page to a regime and reads it accordingly. When the regime is
wrong — an unseen book that only LOOKS like Matthew, a section whose layout changes mid-chapter, a treatise
page mistaken for scripture — the failure is not subtle: the page's text stops corresponding to what the
reference sources say should be there. We need one cheap number that says so, because the expensive per-verse
machinery downstream assumes the page was read in the right regime at all.

This is a PAGE-LEVEL alarm, deliberately distinct from `xsrc_gate`'s per-verse escalation:

    xsrc_gate      per VERSE, fine-grained, routes a verse to R3           "is this verse misread?"
    coverage_alarm per PAGE, coarse, blocks the page                       "did we read this page at all?"

A per-verse gate cannot raise this alarm: if the grammar misfires, every verse looks bad individually and the
gate escalates all of them to an expensive rung that cannot help, instead of reporting that the PAGE was read
under the wrong grammar.

THE REFERENCES. Everything the reference sources know about this locus is used, not just janvier:

    janvier (sabates_a)  modern verse text, all 76 books — the completeness reference (how many verses)
    s_dismas / odr_com   archaic verse text — the surface reference where it exists
    madueke_b            modern verse text — a further independent witness

Coverage is asked in BOTH directions, because the two failures are different and a single number hides one:

  * RECALL   — of the verses the references say belong to this page's chapter range, how many did we find?
               Low recall = the grammar did not FIND the text (wrong regime, treatise page, missed markers).
  * FIDELITY — of what we did find, how well does it match the reference?
               Low fidelity = we found text but read it wrongly (recognizer or crop failure).

Reporting them separately is what makes the alarm actionable: low recall says fix the GRAMMAR, low fidelity
says fix the READING. A single blended score would send both to the same (wrong) remedy.

NO SILENT DEGRADATION: the alarm never accepts a page. It is flag-IN only — a page that fires is OPEN and
blocks, exactly as the per-verse ledger does.
"""
from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import verse_seg as VS  # noqa: E402

# Every reference source that may have something to say about a locus. Ordered by surface preference: the
# archaic witnesses first (they share the page's orthography), then the modern ones.
REFERENCES = ("s_dismas", "odr_com", "sabates_a", "madueke_b")

# Operating points. These are ALARM thresholds, not quality bars — they fire on catastrophe, not on a bad
# verse. A page reading at 0.55 mean fidelity is not "acceptable at 0.60"; it is below the per-verse bar and
# its verses are individually OPEN. This alarm exists to catch the 0.1-and-below case that means the grammar
# itself misfired.
RECALL_FLOOR = 0.50        # found fewer than half the verses the references place here
FIDELITY_FLOOR = 0.55      # what we found does not read like the chapter at all


def reference_verses(book: str, chapter: int) -> tuple[dict[int, str], str | None]:
    """The best available reference text for a chapter, and which source supplied it.

    Cascades over every source that has anything to say about this locus, so a book missing from one witness
    is still covered by another — the archaic gap (17 books) falls through to the modern witnesses rather
    than losing coverage entirely."""
    for name in REFERENCES:
        cv = VS.chapter_verses(book, chapter, name)
        if cv:
            return cv, name
    return {}, None


def page_coverage(spans: dict[int, dict], book: str, chapter: int, *,
                  expected_verses: list[int] | None = None) -> dict:
    """Score one chapter's worth of a page against the reference cascade.

    `spans`: {verse -> {text, ...}} as the segmenters emit (verse_locate.best_spans / verse_seg.segment).
    `expected_verses`: the verses the page is believed to hold. When None, recall is measured against the
    verses the segmenter itself localized, which measures FIDELITY only — recall then needs a caller who knows
    the page's expected range (the tome map or the previous page's tail).

    Returns {recall, fidelity, n_expected, n_found, ref_source, alarm, reasons}.
    """
    from char_identity import evaluate_locus

    # SCORE AGAINST EVERY REFERENCE THAT COVERS THIS LOCUS, then take the best. The sources do not share a
    # verse NUMBERING everywhere: s_dismas gives 2-Esdras 7 seventy verses where sabates_a and madueke_b give
    # seventy-three, so scoring that chapter against s_dismas alone compared our v27 to a different verse and
    # produced fidelity 0.06 on a page that reads correctly. A single-source alarm therefore reports a
    # REFERENCE-mapping fault as a PAGE failure — the most expensive kind of false alarm, because it sends a
    # correct page to an expensive rung that cannot help it. Consulting every witness and keeping the best
    # makes the alarm fire only when NO reference recognises the page, which is the catastrophe we want.
    per_ref = {}
    for name in REFERENCES:
        ref = VS.chapter_verses(book, chapter, name)
        if not ref:
            continue
        exp_r = [v for v in (expected_verses if expected_verses is not None else sorted(spans)) if v in ref]
        if not exp_r:
            continue
        found_r = [v for v in exp_r if (spans.get(v) or {}).get("text")]
        fids_r = [evaluate_locus(spans[v]["text"], ref.get(v), ref.get(v))["archaic_id"] for v in found_r]
        per_ref[name] = {"recall": len(found_r) / len(exp_r), "fidelity": mean(fids_r) if fids_r else 0.0,
                         "n_expected": len(exp_r), "n_found": len(found_r)}
    if not per_ref:
        return {"recall": None, "fidelity": None, "n_expected": 0, "n_found": len(spans),
                "ref_source": None, "alarm": True, "per_ref": {},
                "reasons": ["no reference source covers this locus — cannot verify the page was read at all"]}
    src = max(per_ref, key=lambda k: per_ref[k]["fidelity"])
    best = per_ref[src]
    recall, fidelity = best["recall"], best["fidelity"]
    exp, found = [None] * best["n_expected"], [None] * best["n_found"]

    reasons = []
    # LOW EVIDENCE: a page boundary leaves one or two verses of a chapter on the page. Two verses cannot
    # distinguish "the grammar misfired" from "one verse is a fragment", so the catastrophic alarm does not
    # fire on them — it would cry wolf on every page boundary in the corpus, and an alarm that fires
    # constantly is one that gets ignored. Those verses are still individually gated by xsrc_gate, which is
    # the right instrument at that grain; the page alarm only claims to catch PAGE-level failure.
    low_evidence = best["n_found"] < 3
    spread = max(d["fidelity"] for d in per_ref.values()) - min(d["fidelity"] for d in per_ref.values())
    if low_evidence:
        return {"recall": round(recall, 4), "fidelity": round(fidelity, 4),
                "n_expected": best["n_expected"], "n_found": best["n_found"], "ref_source": src,
                "per_ref": {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in per_ref.items()},
                "low_evidence": True, "alarm": False,
                "reasons": [f"only {best['n_found']} verse(s) of this chapter on the page — too few for a "
                            f"page-level verdict; per-verse gating still applies"]}
    if len(per_ref) > 1 and spread > 0.30:
        reasons.append(f"references DISAGREE on this locus (fidelity spread {spread:.2f} across "
                       f"{len(per_ref)} sources; best={src}) — suspect a verse-NUMBERING divergence between "
                       f"witnesses, not the page")
    if recall is not None and recall < RECALL_FLOOR:
        reasons.append(f"recall {recall:.2f} < {RECALL_FLOOR}: the grammar did not FIND most of the verses "
                       f"the references place here — suspect the REGIME, not the recognizer")
    if fidelity < FIDELITY_FLOOR:
        reasons.append(f"fidelity {fidelity:.2f} < {FIDELITY_FLOOR}: what was found does not read like this "
                       f"chapter — suspect the READING (recognizer/crop) or a mislabelled page")
    return {"recall": round(recall, 4) if recall is not None else None,
            "fidelity": round(fidelity, 4), "n_expected": len(exp), "n_found": len(found),
            "ref_source": src, "per_ref": {k: {kk: round(vv, 4) for kk, vv in v.items()}
                                           for k, v in per_ref.items()},
            "low_evidence": False, "alarm": bool(reasons), "reasons": reasons}


def page_alarm(page_result: dict, book: str, chapter: int, *, spans: dict | None = None,
               expected_verses: list[int] | None = None) -> dict:
    """Full page check: regime + coverage. The one call a pipeline makes to ask 'did we read this page?'.

    A page whose regime is 'no-scripture' is NOT alarmed for empty coverage — that is the grammar working:
    ot2-1610 p216 sits inside the Psalm 118 range and carries no scripture at all. Forcing verse localization
    onto such a page and then alarming would be the pipeline failing to believe its own detector."""
    import block_grammar
    import verse_locate

    d = block_grammar.dispatch(page_result)
    if d["regime"] == "no-scripture":
        return {"regime": d["regime"], "schema": d["schema"], "alarm": False,
                "reasons": ["page carries no verse markers — treated as apparatus/treatise, not scripture"],
                "coverage": None}
    if spans is None:
        try:
            spans = verse_locate.best_spans(page_result, book, chapter)
        except ValueError as e:
            return {"regime": d["regime"], "schema": d["schema"], "alarm": True,
                    "reasons": [f"segmentation refused this page: {e}"], "coverage": None}
    cov = page_coverage(spans, book, chapter, expected_verses=expected_verses)
    reasons = list(cov["reasons"])
    # The coverage verdict is authoritative: a low-evidence page carries an explanatory reason but is NOT an
    # alarm, so rebuilding the verdict from the presence of reasons would re-fire it. Only an unmatched
    # regime adds an alarm of its own here.
    alarm = bool(cov["alarm"])
    if d["regime"] == "unmatched":
        reasons.append("no marker grammar matched this page — it is being read by text anchoring alone")
        alarm = True
    return {"regime": d["regime"], "schema": d["schema"], "confidence": d.get("confidence"),
            "alarm": alarm, "reasons": reasons, "coverage": cov}
