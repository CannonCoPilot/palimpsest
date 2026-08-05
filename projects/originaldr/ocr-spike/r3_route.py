#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r3_route.py — the Rung-3 escalation router (§7 ladder / §8; wires gate -> crop -> R3 -> re-score -> ledger).

This is the piece that makes the gate ACTIONABLE. `reocr_core.reocr_page` flags which janvier verses diverge;
`verse_geom` turns each into a pixel crop; `reocr_r3` re-reads the crop with olmOCR; and THIS module re-scores
the R3 reading against the same reference the gate used and decides the verse's terminal state — recording every
sub-threshold residual in the OPEN ledger so nothing is silently accepted.

Two axes, kept separate (see char_identity / the AI_OCR DUAL-TRACK rule):
  * CONTENT (xsrc_id, ſ-blind): the axis the gate flagged on. olmOCR CAN lift this (it is a content rung).
  * ſ SURFACE: scored against the ſ-faithful R2 (the recognizer, gold-free) — olmOCR modernizes ſ, so a content
    rescue that drops ſ is NOT a full accept; the diplomatic surface stays OPEN and routes to the ſ-faithful
    arbiter (backend='claude', R3-3). This is No Silent Degradation at the sub-verse grain.

Terminal states per flagged verse:
  RESCUED                 content >= τx AND ſ preserved vs R2   -> accepted at R3-mlx (recorded), no ledger entry
  RESCUED_CONTENT_S_OPEN  content >= τx BUT ſ dropped vs R2     -> content closed; ſ owed -> ledger (blocks)
  OPEN                    content < τx after R3, or no geometry -> not accepted -> ledger (blocks)

`rescue_flagged` is the pure decision logic (crafted scores + injected transcriber -> hermetically testable);
`rescue_page` computes the real scores (xsrc_gate) + crops (verse_geom) and drives it (used by reocr_batch).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import verse_geom  # noqa: E402
import verse_locate # noqa: E402
import verse_seg   # noqa: E402
import xsrc_gate   # noqa: E402


def _default_transcribe(ocr_dir, page_index, *, crop=None, verse=None):
    """Real R3 transcriber: olmOCR on the verse's pixel crop (verse arg ignored — the crop already targets it)."""
    import reocr_r3
    return reocr_r3.r3_transcribe(ocr_dir, page_index, crop=crop)


def _score_and_decide(v, s, crop, lines, blob, r3_cut, ocr_dir, page_index, book, chapter, *, ledger, s_ratio):
    """Score one verse's janvier-cut R3 span, assign its terminal state, and record any residual in the ledger.

    P5 LINCHPIN: the crop is a multi-verse REGION, so `blob` is multi-verse; `r3_cut` (janvier-cut of the blob)
    supplies verse v's span. Score BOTH sides on the one grid — else a correct reading of v scores ~0 against
    v's single-verse reference merely for being longer (the genesis-24 e2e: v27 blob-scored 0.0 -> region-cut
    1.0). Two axes, kept separate: CONTENT (xsrc, ſ-blind) is what olmOCR can lift; ſ SURFACE is scored vs the
    ſ-faithful R2 and, if dropped, stays OPEN (routes to the ſ-faithful arbiter) — never a silent accept."""
    r2_xsrc = s.get("xsrc_id")
    vtaux = s.get("taux", xsrc_gate.TAUX)
    r3_span = (r3_cut.get(v) or {}).get("text", "")
    r3 = xsrc_gate.verse_xsrc(r3_span, s.get("ref_modern"), s.get("ref_archaic"))
    r3_xsrc = r3["xsrc_id"]
    r2_s = (s.get("r2_text") or "").count("ſ")
    r3_s = r3_span.count("ſ")
    s_deficient = bool(r2_s > 0 and r3_s < s_ratio * r2_s)
    content_ok = r3_xsrc is not None and r3_xsrc >= vtaux
    best = max([x for x in (r2_xsrc, r3_xsrc) if x is not None], default=None)
    best_rung = "R3-mlx" if (r3_xsrc is not None and (r2_xsrc is None or r3_xsrc >= r2_xsrc)) else "R2"

    if content_ok and not s_deficient:
        state, reason = "RESCUED", ""
    elif content_ok and s_deficient:
        state, reason = "RESCUED_CONTENT_S_OPEN", "s-surface (R3-mlx content ok; ſ-faithful surface owed -> R3-claude)"
        _ledger_open(ledger, book, chapter, v, s, ocr_dir, page_index, rungs=["R2", "R3-mlx"],
                     best=best, best_rung=best_rung, reason=reason)
    else:
        state, reason = "OPEN", "xsrc<taux-after-R3"
        _ledger_open(ledger, book, chapter, v, s, ocr_dir, page_index, rungs=["R2", "R3-mlx"],
                     best=best, best_rung=best_rung, reason=reason)

    return {"state": state, "reason": reason, "r2_xsrc": r2_xsrc, "r3_xsrc": r3_xsrc, "taux": vtaux,
            "s_deficient": s_deficient, "r2_s_count": r2_s, "r3_s_count": r3_s, "rung": "R3-mlx",
            "r3_span": r3_span, "r3_text": blob, "crop": crop, "lines": lines}


def rescue_flagged(ocr_dir: str, page_index: int, book: str, chapter: int, scores: dict, crops: dict, *,
                   transcribe=_default_transcribe, ledger=None, s_ratio: float = 1.0, regions=None) -> dict:
    """Route every ESCALATED verse in `scores` through R3 (one olmOCR pass per contiguous REGION) and assign a
    terminal state; update `ledger`.

    scores: {verse -> gate entry} as xsrc_gate.cross_source_verse_scores returns (escalate, xsrc_id, taux,
            r2_text, ref_modern, ref_archaic, arc_src).
    crops:  {verse -> {crop, lines, ...}} as verse_geom.verse_crops returns (crop None -> no geometry).
    regions: [{crop, verses, lines}] from verse_geom.region_crops (contiguous flagged verses -> one crop). When
            None, each flagged verse falls back to its own singleton region (its per-verse crop).
    transcribe: callable(ocr_dir, page_index, *, crop, verse) -> R3 text for a crop (injectable; default olmOCR).
    s_ratio: a verse is ſ-deficient if r3_ſ < s_ratio * r2_ſ (default 1.0: any ſ lost vs R2 is a regression).
    Returns a per-verse verdict dict + counts. Fully gold-free (witness + R2 references only)."""
    flagged = [v for v in sorted(scores) if scores[v].get("escalate")]
    verses: dict = {}

    # (1) flagged verses with no pixel geometry -> terminal OPEN (nothing to re-read); never a transcribe call.
    geo = []
    for v in flagged:
        if (crops.get(v) or {}).get("crop") is None:
            verses[v] = {"state": "OPEN", "reason": "no-geometry", "r2_xsrc": scores[v].get("xsrc_id"),
                         "r3_xsrc": None, "taux": scores[v].get("taux", xsrc_gate.TAUX), "s_deficient": None,
                         "rung": None, "r3_span": None, "r3_text": None, "crop": None,
                         "lines": (crops.get(v) or {}).get("lines")}
            _ledger_open(ledger, book, chapter, v, scores[v], ocr_dir, page_index, rungs=["R2"],
                         best=scores[v].get("xsrc_id"), best_rung="R2", reason="no-geometry")
        else:
            geo.append(v)

    # (2) group into regions (one olmOCR pass + one janvier-cut per region -> sharp boundaries, no margin bleed).
    if regions is None:
        regions = [{"crop": crops[v]["crop"], "verses": [v], "lines": crops[v].get("lines")} for v in geo]

    # (3) transcribe each region once, janvier-cut, score each flagged verse in it.
    for reg in regions:
        rverses = [v for v in reg["verses"] if v in geo]
        if not rverses:
            continue
        try:
            blob = transcribe(ocr_dir, page_index, crop=reg["crop"], verse=rverses[0])
            r3_cut = verse_seg.segment_book_chapter(blob, book, chapter, drop_apparatus=True)
        except Exception as e:
            # No Silent Degradation (code-review HIGH-2): an R3 failure on THIS region must not abort the loop —
            # that would discard already-scored regions AND drop this region's verses with no ledger trace. The
            # MLXWorker timeout path is unconditional, so this fires on any crop slower than call_timeout. Keep
            # every verse in the region OPEN + ledgered (naming the failure), then continue to the next region.
            reason = f"r3-transcribe-failed: {type(e).__name__}"
            for v in rverses:
                s = scores[v]
                verses[v] = {"state": "OPEN", "reason": reason, "r2_xsrc": s.get("xsrc_id"), "r3_xsrc": None,
                             "taux": s.get("taux", xsrc_gate.TAUX), "s_deficient": None, "rung": None,
                             "r3_span": None, "r3_text": None, "crop": reg["crop"], "lines": reg.get("lines")}
                _ledger_open(ledger, book, chapter, v, s, ocr_dir, page_index, rungs=["R2", "R3-mlx"],
                             best=s.get("xsrc_id"), best_rung="R2", reason=reason)
            continue
        for v in rverses:
            verses[v] = _score_and_decide(v, scores[v], reg["crop"], reg.get("lines"), blob, r3_cut,
                                          ocr_dir, page_index, book, chapter, ledger=ledger, s_ratio=s_ratio)

    n = lambda st: sum(1 for x in verses.values() if x["state"] == st)  # noqa: E731
    return {
        "page": [ocr_dir, page_index], "locus": [book, chapter],
        "flagged": sorted(verses),
        "verses": verses,
        "n_flagged": len(verses),
        "n_rescued": n("RESCUED"),
        "n_content_rescued_s_open": n("RESCUED_CONTENT_S_OPEN"),
        "n_open": n("OPEN") + n("RESCUED_CONTENT_S_OPEN"),   # anything blocking the deliverable
    }


def _ledger_open(ledger, book, chapter, verse, s, ocr_dir, page_index, *, rungs, best, best_rung, reason):
    if ledger is None:
        return
    ledger.add_open(locus=(book, chapter, verse), source=ocr_dir, page_index=page_index,
                    rungs_tried=rungs, best_score=best, best_rung=best_rung,
                    reference_used=s.get("arc_src") or verse_geom.verse_seg.JANVIER,
                    reference_axis=s.get("xsrc_gate", "archaic"), taux=s.get("taux"), reason=reason)


def rescue_page(page_result: dict, ocr_dir: str, page_index: int, book: str, chapter: int, *,
                transcribe=_default_transcribe, ledger=None, taux=None) -> dict:
    """Compute the real gate scores + crops for a page and route its flagged verses through R3. This is what
    reocr_batch calls when run_r3=True. `page_result` is a reocr_core.reocr_page dict (needs r2_body + lines
    with bbox).

    SEGMENT ONCE, USE EVERYWHERE. The page is localized a single time with the hybrid `verse_locate.best_spans`
    and that one dict feeds BOTH the gate (which scores the span) and the geometry (which crops it). Letting
    each re-segment independently would allow the flagged text and the re-read pixels to come from different
    engines — the verse we judged bad would not be the verse we re-read."""
    spans = verse_locate.best_spans(page_result, book, chapter)
    scores = xsrc_gate.cross_source_verse_scores(page_result["r2_body"], book, chapter, taux=taux, spans=spans)
    crops = verse_geom.verse_crops(page_result, book, chapter, spans=spans)
    flagged = [v for v in scores if scores[v].get("escalate")]
    regions = verse_geom.region_crops(page_result, book, chapter, flagged, spans=spans)["regions"]
    return rescue_flagged(ocr_dir, page_index, book, chapter, scores, crops,
                          transcribe=transcribe, ledger=ledger, regions=regions)


if __name__ == "__main__":
    # smoke: one crafted flagged verse + an injected fix -> RESCUED, nothing left OPEN.
    import open_ledger
    VS = verse_geom.verse_seg
    janv = VS.chapter_verses("genesis", 24, VS.JANVIER)
    arc, _ = xsrc_gate.archaic_cut("genesis", 24, janv)
    def mk(v, r2_text, xid):
        return {v: {"xsrc_id": xid, "xsrc_gate": "archaic", "escalate": True, "taux": 0.90,
                    "arc_src": "s_dismas", "r2_text": r2_text, "ref_archaic": arc.get(v), "ref_modern": janv.get(v)}}
    crops = {5: {"crop": (0, 0.1, 1, 0.2)}}
    fix = (arc.get(5) or janv[5]); fix = fix if "ſ" in fix else "ſ" + fix
    led = open_ledger.OpenLedger()
    out = rescue_flagged("archive-ot1-1609", 99, "genesis", 24, mk(5, "garbled zzz other", 0.6), crops,
                         transcribe=lambda *a, crop=None, verse=None: fix, ledger=led)
    ok = out["verses"][5]["state"] == "RESCUED" and led.summary()["n_open"] == 0
    print("SELF-CHECK:", "PASS" if ok else "FAIL", "| state =", out["verses"][5]["state"])
    raise SystemExit(0 if ok else 1)
