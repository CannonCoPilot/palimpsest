#!/usr/bin/env python
"""Migrate the verified corrections + per-instance rules into the durable gold contracts.

For every gold/work-<idx>.json:
  * apply the count corrections discovered during the masking-map build (old->new + evidence),
  * append the reconciliation note to the relevant count_cue,
  * attach an `instance_rule` descriptor to each repeating annotation (how its per-instance
    edges are materialized from reference_text() at eval time — the executable form lives in
    instance_edges.RULES; this records it durably),
  * stamp a top-level `map_status`.

Preserves all existing hand-authored fields/notes. Idempotent on count (guards old value).
"""
import json
import sys
from pathlib import Path

import instance_edges as ie  # noqa: E402

GOLD = Path("core/tests/fixtures/gold")

# idx -> {(type, old_count): (new_count, evidence)}
CORR = {
    6: {("chapter", None): (1133, "66-book Protestant canon; this e-text is physically scrambled (1133 materialized chapter units vs 1189 canonical)"),
        ("chapter_heading", None): (1133, "one numbered 'argument'/superscription block precedes each chapter's verse 1"),
        ("book", None): (66, "39 OT + 27 NT; the Apocrypha (Ecclesiasticus, Maccabees, Esdras, Tobit, Judith, Wisdom, Baruch, Manasses) are entirely ABSENT in this e-text")},
    18: {("chapter", 737): (743, "in-body 'Chapter <roman>.' headings, negative-lookahead isolated from contents-list echoes, leakage-free (737 was the detector's de-dup count)")},
    19: {("letter", 102): (124, "salutation discriminator (115 greeting-prefix + 9 bare-name forms); the prior 102 was a 'Dear'-only proxy lower bound")},
    64: {("chapter", 228): (230, "3 Enoch chapters 5 & 8 ARE present in this Lumpkin text, OCR'd 'CHAPTER S'; 108+68+54=230")},
    80: {("translation", 270): (271, "Genesis Apocryphon (1Q20) is two distinct units (main scroll + Milik's fragments) per the back-matter MS list; 270 was the editor's round figure")},
    106: {("translation", 121): (126, "126 body source-entry units (author-header lines) vs 121 distinct authors in the front index")},
}

_RULE_KEYS = ["kind", "pattern", "titles", "span_start", "span_end",
              "extra_anchors", "at", "tile", "expected_count"]


def serialize(r):
    return {k: r[k] for k in _RULE_KEYS if k in r}


def main():
    for p in sorted(GOLD.glob("work-*.json"), key=lambda x: int(x.stem.split("-")[1])):
        idx = int(p.stem.split("-")[1])
        d = json.loads(p.read_text())
        rules = ie.RULES.get(idx, [])
        log = []
        for a in d.get("annotations", []):
            if a.get("structure") != "repeating":
                continue
            t = a["type"]
            cur = a.get("expected_count")
            for (ct, co), (new, ev) in CORR.get(idx, {}).items():
                if ct == t and co == cur:
                    a["expected_count"] = new
                    a["count_cue"] = (a.get("count_cue", "")
                                      + f" || RECONCILED 2026-06-19 ({co}→{new}): {ev}.")
                    log.append(f"{t} {co}→{new}")
                    break
            matching = [serialize(r) for r in rules if r.get("type") == t]
            if matching:
                a["instance_rule"] = matching[0] if len(matching) == 1 else matching
            elif idx in (29, 42):
                a["instance_rule"] = {"kind": "computed_offsets",
                                      "note": "materialized via masking_map.CUSTOM_ELEMENTS "
                                              "(interleaved/offset sub-blocks)"}
        d["map_status"] = ("complete 2026-06-19: every character covered by >=1 generic "
                           "(body/volume/book/part) and >=1 specific mask-type; per-instance "
                           "edges materialized, 100% two-layer (see docs/development/audits/masking-map/)")
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        print(f"idx{idx:>3}: {', '.join(log) if log else 'counts ok'}; "
              f"{sum('instance_rule' in a for a in d['annotations'])} rules attached")


if __name__ == "__main__":
    main()
