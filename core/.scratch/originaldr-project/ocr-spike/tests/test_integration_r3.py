# -*- coding: utf-8 -*-
"""SLOW integration: the full productionized R3 rescue on a real page (real olmOCR via the load-once worker).

Marked `slow` — loads the 15GB olmOCR model. Run with `-m slow` and NOT concurrently with another olmOCR job
(two 15GB loads = memory pressure). Pins the empirically-validated 2026-07-25 genesis-24 region-rescue result so
a regression in geometry / region-grouping / janvier-cut-scoring / the ſ-companion / the ledger is caught:

  gate flags {12,27,28,29,30}; olmOCR content-rescues v27/v28/v29 above τx with real lift, but drops ſ so they
  are RESCUED_CONTENT_S_OPEN (ſ surface owed to the arbiter); v12/v30 stay OPEN (cross-page fragments); the OPEN
  ledger holds all 5 and blocks the deliverable. olmOCR at temp 0 is deterministic, so these hold run-to-run.
"""
from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.slow

OCR_DIR, PI, BOOK, CH = "archive-ot1-1609", 99, "genesis", 24


@pytest.fixture(scope="module")
def batch_out(tmp_path_factory):
    import reocr_core
    out = tmp_path_factory.mktemp("r3out")
    reocr_core.reocr_batch(OCR_DIR, [PI], locus_map={PI: (BOOK, CH)}, run_r3=True,
                           want_r1=False, out_dir=str(out), progress=False)
    return out


@pytest.fixture(scope="module")
def verses(batch_out):
    page = json.loads((batch_out / f"page_{PI:04d}.json").read_text())
    return page["r3_route"]["verses"]        # keys are strings after JSON round-trip


def test_flagged_set(verses):
    assert {int(k) for k in verses} == {12, 27, 28, 29, 30}


def test_content_rescued_verses_lift_over_bar_but_stay_s_open(verses):
    """v27/v28/v29: olmOCR content lift clears τx=0.90, but ſ is dropped -> RESCUED_CONTENT_S_OPEN (not accepted)."""
    for v in (27, 28, 29):
        d = verses[str(v)]
        assert d["r3_xsrc"] >= 0.90, f"v{v} olmOCR content should clear τx: {d['r3_xsrc']}"
        assert d["r3_xsrc"] > d["r2_xsrc"], f"v{v} R3 must lift over R2 ({d['r3_xsrc']} !> {d['r2_xsrc']})"
        assert d["s_deficient"] is True, f"v{v} olmOCR drops ſ -> must be flagged ſ-deficient"
        assert d["state"] == "RESCUED_CONTENT_S_OPEN"


def test_cross_page_fragments_stay_open(verses):
    for v in (12, 30):
        assert verses[str(v)]["state"] == "OPEN", f"v{v} is a cross-page fragment R3 cannot close on this page"


def test_open_ledger_blocks_deliverable(batch_out):
    led = json.loads((batch_out / "_open_ledger.json").read_text())
    assert led["blocks_deliverable"] is True
    assert led["n_open"] == 5, "every flagged verse that R3 didn't fully close stays OPEN (No Silent Degradation)"
    # 3 are ſ-surface debt, 2 are content-open
    reasons = led["by_reason"]
    assert sum(reasons.values()) == 5
    assert any("s-surface" in k for k in reasons), "the ſ-surface residual must be a named, tracked debt"
