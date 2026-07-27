# -*- coding: utf-8 -*-
"""TDD spec for r3_route.rescue_flagged — the escalation routing that ties gate -> crop -> R3 -> re-score.

The decision logic is separated from the gate/geometry computation so it is hermetically testable: we hand it a
crafted `scores` dict (as xsrc_gate.cross_source_verse_scores would return — real refs, controlled R2 text) and
a fake transcriber (no MLX), and pin every terminal state:

  * content lifted >= τx AND ſ preserved            -> RESCUED            (no ledger entry)
  * content lifted >= τx BUT ſ dropped vs R2        -> RESCUED_CONTENT_S_OPEN (ledger: ſ-surface owed -> arbiter)
  * content still < τx after R3                     -> OPEN               (ledger: content not rescued)
  * flagged verse with no crop geometry             -> OPEN               (ledger: no-geometry)

The ſ axis is scored against the ſ-faithful R2 (not gold, not the witness — the witnesses are pdftotext-modern):
olmOCR modernizes ſ, so a content rescue that drops ſ is NOT a full accept — No Silent Degradation keeps the
diplomatic surface OPEN and blocks the deliverable until the ſ-faithful arbiter closes it.
"""
from __future__ import annotations

import open_ledger
import r3_route
import verse_seg
import xsrc_gate

BOOK, CH = "genesis", 24


def _refs():
    janv = verse_seg.chapter_verses(BOOK, CH, verse_seg.JANVIER)
    arc, _src = xsrc_gate.archaic_cut(BOOK, CH, janv)
    return janv, arc


def _score_entry(v, janv, arc, *, r2_text, xsrc_id, taux=0.90):
    """Shape one verse the way cross_source_verse_scores does (the fields rescue_flagged consumes)."""
    return {
        "xsrc_id": xsrc_id, "xsrc_gate": "archaic", "escalate": True, "xsrc_below_taux": True,
        "seg_open": False, "arc_src": "s_dismas", "taux": taux, "r2_text": r2_text,
        "ref_archaic": arc.get(v), "ref_modern": janv.get(v),
    }


def _fake_transcriber(mapping):
    """Return a transcribe(ocr_dir, page_index, *, crop, verse) that yields mapping[verse]."""
    def _t(ocr_dir, page_index, *, crop=None, verse=None):
        return mapping[verse]
    return _t


def test_content_rescue_with_s_preserved_is_rescued():
    janv, arc = _refs()
    v = 5
    scores = {v: _score_entry(v, janv, arc, r2_text="garbled wholly other reading zzz", xsrc_id=0.62)}
    crops = {v: {"crop": (0.0, 0.1, 1.0, 0.2), "open": False}}
    # fake R3 returns a ſ-bearing correct reading (>= the R2 ſ-count of 0, so not deficient)
    fix = (arc.get(v) or janv[v])
    if "ſ" not in fix:
        fix = "ſ" + fix              # ensure at least one ſ so the ſ-companion sees a faithful surface
    led = open_ledger.OpenLedger()
    out = r3_route.rescue_flagged("archive-ot1-1609", 99, BOOK, CH, scores, crops,
                                  transcribe=_fake_transcriber({v: fix}), ledger=led)
    assert out["verses"][v]["state"] == "RESCUED"
    assert out["n_rescued"] == 1 and out["n_open"] == 0
    assert led.summary()["n_open"] == 0, "a full rescue adds nothing to the OPEN worklist"


def test_content_rescue_but_s_dropped_is_s_open():
    janv, arc = _refs()
    v = 6
    scores = {v: _score_entry(v, janv, arc, r2_text="ſome ſtuff garbled here zzz", xsrc_id=0.55)}  # r2 has 2 ſ
    crops = {v: {"crop": (0.0, 0.2, 1.0, 0.3), "open": False}}
    fix_no_s = (arc.get(v) or janv[v]).replace("ſ", "s")            # correct content, ſ MODERNIZED (0 ſ)
    led = open_ledger.OpenLedger()
    out = r3_route.rescue_flagged("archive-ot1-1609", 99, BOOK, CH, scores, crops,
                                  transcribe=_fake_transcriber({v: fix_no_s}), ledger=led)
    st = out["verses"][v]
    assert st["state"] == "RESCUED_CONTENT_S_OPEN", f"content ok + ſ dropped must be ſ-open, got {st['state']}"
    assert st["s_deficient"] is True
    assert out["n_content_rescued_s_open"] == 1
    assert led.summary()["n_open"] == 1
    assert "s-surface" in led.entries[0]["reason"], "ledger must name the ſ-surface debt"


def test_content_not_rescued_is_open():
    janv, arc = _refs()
    v = 7
    scores = {v: _score_entry(v, janv, arc, r2_text="garbled reading zzz", xsrc_id=0.40)}
    crops = {v: {"crop": (0.0, 0.3, 1.0, 0.4), "open": False}}
    led = open_ledger.OpenLedger()
    out = r3_route.rescue_flagged("archive-ot1-1609", 99, BOOK, CH, scores, crops,
                                  transcribe=_fake_transcriber({v: "xqz mmm lll ttt zzz qqq"}), ledger=led)
    assert out["verses"][v]["state"] == "OPEN"
    assert out["n_open"] == 1
    e = led.entries[0]
    assert e["reason"].startswith("xsrc<taux") and e["best_rung"] in ("R2", "R3-mlx")


def test_flagged_verse_without_geometry_is_open_no_transcribe():
    janv, arc = _refs()
    v = 8
    scores = {v: _score_entry(v, janv, arc, r2_text="garbled zzz", xsrc_id=0.50)}
    crops = {v: {"crop": None, "open": True, "reason": "no-geometry"}}
    called = []
    def _t(ocr_dir, page_index, *, crop=None, verse=None):
        called.append(verse); return "should not be called"
    led = open_ledger.OpenLedger()
    out = r3_route.rescue_flagged("archive-ot1-1609", 99, BOOK, CH, scores, crops, transcribe=_t, ledger=led)
    assert out["verses"][v]["state"] == "OPEN"
    assert called == [], "a verse with no crop must not invoke R3 (nothing to re-read)"
    assert "no-geometry" in led.entries[0]["reason"]


def test_region_transcribe_failure_is_contained_and_ledgered():
    """No Silent Degradation: an R3 transcribe failure on ONE region must not abort the whole page — earlier
    regions keep their verdicts, and every verse in the failed region stays OPEN + in the ledger (code-review
    HIGH-2). The MLXWorker timeout path is unconditional, so this failure mode is live on any slow crop."""
    janv, arc = _refs()
    scores = {
        5: _score_entry(5, janv, arc, r2_text="garbled zzz other", xsrc_id=0.5),
        27: _score_entry(27, janv, arc, r2_text="garbled zzz other", xsrc_id=0.5),
    }
    crops = {5: {"crop": (0, 0.1, 1, 0.2), "lines": [0]}, 27: {"crop": (0, 0.3, 1, 0.4), "lines": [5]}}
    fix5 = arc.get(5) or janv[5]

    def _t(ocr_dir, page_index, *, crop=None, verse=None):
        if verse == 27:
            raise TimeoutError("simulated worker death")     # region for v27 fails
        return fix5                                          # region for v5 succeeds

    led = open_ledger.OpenLedger()
    out = r3_route.rescue_flagged("archive-ot1-1609", 99, BOOK, CH, scores, crops,
                                  transcribe=_t, ledger=led)  # must NOT raise
    assert set(out["verses"]) == {5, 27}, "both flagged verses must be accounted for despite the failure"
    assert out["verses"][5]["r3_xsrc"] is not None, "the succeeding region keeps its computed verdict"
    assert out["verses"][27]["state"] == "OPEN"
    assert "TimeoutError" in out["verses"][27]["reason"]
    assert ["genesis", 24, 27] in [e["locus"] for e in led.entries], "failed region's verse must be ledgered, not lost"
    assert led.summary()["blocks_deliverable"] is True


def test_non_escalated_verses_are_ignored():
    janv, arc = _refs()
    scores = {
        5: _score_entry(5, janv, arc, r2_text="garbled zzz", xsrc_id=0.50),
        6: {**_score_entry(6, janv, arc, r2_text=janv[6], xsrc_id=0.99), "escalate": False},
    }
    crops = {5: {"crop": (0, 0.1, 1, 0.2)}, 6: {"crop": (0, 0.2, 1, 0.3)}}
    seen = []
    def _t(ocr_dir, page_index, *, crop=None, verse=None):
        seen.append(verse); return "xqz mmm lll"
    led = open_ledger.OpenLedger()
    out = r3_route.rescue_flagged("archive-ot1-1609", 99, BOOK, CH, scores, crops, transcribe=_t, ledger=led)
    assert seen == [5], "only escalated verses are re-read"
    assert set(out["verses"]) == {5}
