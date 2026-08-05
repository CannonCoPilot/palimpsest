#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""open_ledger.py — the terminal OPEN worklist (§7 escalation-ladder terminal / §8 R3-5).

No Silent Degradation, made into an artifact. The escalation ladder is R2 -> [gate] -> R3-local -> R3-Claude ->
TERMINAL. When no rung lifts a flagged verse above its axis τx, the verse is NOT accepted: it becomes an OPEN
entry here. Each entry records the locus, the source page, every rung tried, the BEST (still sub-threshold)
score reached and by which rung, and the reference it was measured against. The ledger:

  * is the human-review worklist (a reviewer re-transcribes / the approach gets redesigned — never "accept the
    gap", per the guardrail);
  * BLOCKS the deliverable while non-empty;
  * dedupes by locus and keeps the HIGHEST score seen (the honest "closest we got"), so re-runs converge instead
    of duplicating or silently overwriting downward.

This module is pure bookkeeping — no gold, no model, no I/O beyond the JSON worklist it writes.
"""
from __future__ import annotations

import json
from pathlib import Path

GENERATED_BY = "reOCR escalation ladder (reocr_core + xsrc_gate + reocr_r3); No Silent Degradation terminal"


def _locus_key(locus) -> str:
    """A JSON-stable string key for a locus tuple, e.g. ('genesis',24,30) -> 'genesis/24/30',
    ('matter','ot1-preface') -> 'matter/ot1-preface'. Used to dedupe across re-runs."""
    return "/".join(str(x) for x in locus)


class OpenLedger:
    def __init__(self):
        self.entries: list[dict] = []
        self._by_key: dict[str, dict] = {}

    def add_open(self, *, locus, source, page_index, rungs_tried, best_score, best_rung,
                 reference_used, reference_axis, taux, reason) -> dict:
        """Record (or update) a terminal-OPEN verse. Idempotent by locus: a second call for the same locus
        UNIONS the rungs tried, keeps the highest best_score (with its rung), and refreshes reason/refs."""
        key = _locus_key(locus)
        rungs_tried = list(rungs_tried)
        existing = self._by_key.get(key)
        if existing is None:
            entry = {
                "locus_key": key,
                "locus": list(locus),
                "source": source,
                "page_index": page_index,
                "rungs_tried": rungs_tried,
                "best_score": best_score,
                "best_rung": best_rung,
                "reference_used": reference_used,
                "reference_axis": reference_axis,
                "taux": taux,
                "reason": reason,
                "state": "OPEN",
            }
            self.entries.append(entry)
            self._by_key[key] = entry
            return entry
        # merge into the existing entry. rungs_tried is a UNION (independent of which attempt scored best).
        for r in rungs_tried:
            if r not in existing["rungs_tried"]:
                existing["rungs_tried"].append(r)
        # Provenance (source/page_index/reason/refs/taux) tracks the BEST attempt so best_score never mismatches
        # the page/reason a reviewer reads (code-review MEDIUM-3). Only overwrite when this call is the new best;
        # a worse later attempt (e.g. the same a/b-split verse re-escalated on an adjacent page) leaves it intact.
        if best_score is not None and (existing["best_score"] is None or best_score > existing["best_score"]):
            existing.update(best_score=best_score, best_rung=best_rung, source=source, page_index=page_index,
                            reason=reason, reference_used=reference_used, reference_axis=reference_axis, taux=taux)
        return existing

    def summary(self) -> dict:
        by_reason: dict[str, int] = {}
        for e in self.entries:
            by_reason[e["reason"]] = by_reason.get(e["reason"], 0) + 1
        return {
            "n_open": len(self.entries),
            "by_reason": by_reason,
            "blocks_deliverable": len(self.entries) > 0,
        }

    def to_doc(self) -> dict:
        s = self.summary()
        return {
            "state": "OPEN" if self.entries else "CLEAR",
            "generated_by": GENERATED_BY,
            "n_open": s["n_open"],
            "by_reason": s["by_reason"],
            "blocks_deliverable": s["blocks_deliverable"],
            "entries": self.entries,
        }

    def write(self, path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_doc(), ensure_ascii=False, indent=1))
        return path

    @classmethod
    def load(cls, path) -> "OpenLedger":
        doc = json.loads(Path(path).read_text())
        led = cls()
        for e in doc.get("entries", []):
            led.entries.append(e)
            led._by_key[e.get("locus_key") or _locus_key(e["locus"])] = e
        return led


if __name__ == "__main__":
    # tiny smoke: two OPEN verses + one dedup update -> one merged entry, deliverable blocked
    led = OpenLedger()
    led.add_open(locus=("genesis", 24, 30), source="archive-ot1-1609", page_index=99, rungs_tried=["R2"],
                 best_score=0.71, best_rung="R2", reference_used="s_dismas", reference_axis="archaic",
                 taux=0.90, reason="xsrc<taux")
    led.add_open(locus=("genesis", 24, 30), source="archive-ot1-1609", page_index=99, rungs_tried=["R3-mlx"],
                 best_score=0.86, best_rung="R3-mlx", reference_used="s_dismas", reference_axis="archaic",
                 taux=0.90, reason="xsrc<taux")
    s = led.summary()
    ok = s["n_open"] == 1 and led.entries[0]["best_score"] == 0.86 and \
        led.entries[0]["rungs_tried"] == ["R2", "R3-mlx"] and s["blocks_deliverable"]
    print("SELF-CHECK:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
