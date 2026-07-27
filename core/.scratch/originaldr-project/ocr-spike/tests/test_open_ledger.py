# -*- coding: utf-8 -*-
"""TDD spec for open_ledger — the terminal OPEN worklist (§7 ladder terminal / §8 R3-5).

No Silent Degradation made concrete: when the escalation ladder (R2 -> gate -> R3) cannot lift a flagged verse
above its axis τx, the verse does NOT get accepted — it becomes an OPEN entry that (a) records what was tried
and the best score reached, (b) names the reference it was measured against, (c) is a human-review worklist item
that BLOCKS the deliverable. The ledger is the artifact that proves nothing sub-threshold was laundered through.
"""
from __future__ import annotations

import json

import open_ledger


def _entry(**over):
    base = dict(locus=("genesis", 24, 30), source="archive-ot1-1609", page_index=99,
                rungs_tried=["R2", "R3-mlx"], best_score=0.71, best_rung="R2",
                reference_used="s_dismas", reference_axis="archaic", taux=0.90, reason="xsrc<taux")
    base.update(over)
    return base


def test_add_open_and_roundtrip(tmp_path):
    led = open_ledger.OpenLedger()
    led.add_open(**_entry())
    led.add_open(**_entry(locus=("genesis", 24, 12), reason="len-short"))
    p = tmp_path / "open.json"
    led.write(p)
    back = open_ledger.OpenLedger.load(p)
    assert len(back.entries) == 2
    e = back.entries[0]
    for k in ("locus", "source", "page_index", "rungs_tried", "best_score", "best_rung",
              "reference_used", "reference_axis", "taux", "reason", "state"):
        assert k in e
    assert e["state"] == "OPEN"


def test_locus_is_normalized_to_a_stable_key():
    """A locus key must be JSON-stable and comparable so re-runs dedupe instead of duplicating."""
    led = open_ledger.OpenLedger()
    led.add_open(**_entry())
    led.add_open(**_entry())                    # exact same verse escalated on a second run
    assert len(led.entries) == 1, "the same OPEN locus must not be duplicated"
    # a different verse is distinct
    led.add_open(**_entry(locus=("genesis", 24, 27)))
    assert len(led.entries) == 2


def test_best_score_kept_is_the_highest_seen():
    """If a verse is re-tried and reaches a higher (still sub-τx) score, the ledger keeps the BEST — the honest
    'closest we got', never overwritten downward."""
    led = open_ledger.OpenLedger()
    led.add_open(**_entry(best_score=0.71, best_rung="R2"))
    led.add_open(**_entry(best_score=0.86, best_rung="R3-mlx"))
    assert len(led.entries) == 1
    assert led.entries[0]["best_score"] == 0.86 and led.entries[0]["best_rung"] == "R3-mlx"
    # a lower re-score does NOT lower the recorded best
    led.add_open(**_entry(best_score=0.60, best_rung="R3-mlx"))
    assert led.entries[0]["best_score"] == 0.86


def test_merge_keeps_provenance_consistent_with_best_score():
    """code-review MEDIUM-3: source/page_index/reason must track the BEST attempt, not whichever call ran last —
    else a reviewer opening the ledger sees best_score from attempt A next to the page/reason of attempt B.
    Reachable for an a/b split verse escalated on two adjacent pages of one batch (shared ledger)."""
    led = open_ledger.OpenLedger()
    led.add_open(**_entry(page_index=99, best_score=0.71, best_rung="R2", reason="xsrc<taux"))
    # a better attempt on a different page -> ALL provenance moves with the score
    led.add_open(**_entry(page_index=100, best_score=0.86, best_rung="R3-mlx", reason="s-surface"))
    e = led.entries[0]
    assert (e["best_score"], e["best_rung"]) == (0.86, "R3-mlx")
    assert e["page_index"] == 100 and e["reason"] == "s-surface", "provenance must track the best attempt"
    # a WORSE later attempt must not move provenance
    led.add_open(**_entry(page_index=101, best_score=0.60, best_rung="R2", reason="stale"))
    assert e["page_index"] == 100 and e["best_score"] == 0.86 and e["reason"] == "s-surface"


def test_rungs_tried_accumulate_across_updates():
    led = open_ledger.OpenLedger()
    led.add_open(**_entry(rungs_tried=["R2"]))
    led.add_open(**_entry(rungs_tried=["R3-mlx"]))
    assert led.entries[0]["rungs_tried"] == ["R2", "R3-mlx"], "union of rungs tried, in order, no dupes"


def test_summary_counts_and_blocks(tmp_path):
    led = open_ledger.OpenLedger()
    led.add_open(**_entry(locus=("genesis", 24, 30), reason="xsrc<taux"))
    led.add_open(**_entry(locus=("genesis", 24, 12), reason="len-short"))
    led.add_open(**_entry(locus=("psalms", 118, 107), reason="no-geometry"))
    s = led.summary()
    assert s["n_open"] == 3
    assert s["by_reason"]["xsrc<taux"] == 1 and s["by_reason"]["len-short"] == 1
    assert s["blocks_deliverable"] is True       # any OPEN blocks
    assert open_ledger.OpenLedger().summary()["blocks_deliverable"] is False


def test_write_is_valid_json_worklist(tmp_path):
    led = open_ledger.OpenLedger()
    led.add_open(**_entry())
    p = tmp_path / "open.json"
    led.write(p)
    doc = json.loads(p.read_text())
    assert doc["state"] == "OPEN" and isinstance(doc["entries"], list) and doc["n_open"] == 1
    assert "generated_by" in doc                 # provenance so a reviewer knows what produced the worklist
