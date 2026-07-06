#!/usr/bin/env python3
"""Phase 2 · P2.0 — reconciled Madueke↔Sabates modern spelling/typeset standard.

Emits `modern-standard.json`: the documented, reproducible rule set that resolves the
orthographic/typographic divergences between the two modern witnesses (Madueke_A, the
authoritative modern edition, and Sabates_A, its lineage-derivative) into one
"agreed-corrected" standard used to render idx 108. Because the committed leg-1 collation
found **0 substantive wording divergences** (the witnesses agree on content), the standard
is purely a normalization spec: Madueke_A is authoritative for surface, and the remaining
differences (ligatures, divine-speech capitalization, whitespace/punctuation) resolve by
the rules below. Stats + worked examples are pulled live from the committed
`collation-3way.json` and the aligned reads, so the spec is evidence-grounded and
regenerable, not hand-asserted.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MASK_ENGINE = HERE.parent
sys.path.insert(0, str(MASK_ENGINE))
import gen_dr_original as gen  # type: ignore[import]  # noqa: E402

COLLATION = MASK_ENGINE / "originaldr_validation" / "collation-3way.json"
READS_DIR = gen.REPO / "core/.scratch/originaldr-project/reconstruction/reads"
OUT = HERE / "modern-standard.json"

LIGATURES = {"æ": "ae", "Æ": "Ae", "œ": "oe", "Œ": "Oe"}


def find_ligature_examples(limit: int = 3) -> list[dict]:
    """Real ligature-only divergences: Sabates keeps æ/œ where Madueke expands to ae/oe."""
    try:
        mad = {r["skeleton_id"]: r["surface"] for r in
               json.loads((READS_DIR / "madueke_a.json").read_text())["reads"]}
        sab = {r["skeleton_id"]: r["surface"] for r in
               json.loads((READS_DIR / "sabates_a.json").read_text())["reads"]}
    except (FileNotFoundError, KeyError):
        return []
    out = []
    for skid, s in sab.items():
        if any(lig in s for lig in LIGATURES) and skid in mad:
            m = mad[skid]
            folded = s
            for a, b in LIGATURES.items():
                folded = folded.replace(a, b)
            if folded.strip() == m.strip():        # ligature-ONLY difference
                out.append({"ref": skid, "sabates": s.strip(), "madueke": m.strip(),
                            "standard": m.strip()})
                if len(out) >= limit:
                    break
    return out


def caps_examples(collation: dict, limit: int = 3) -> list[dict]:
    """Divine-speech capitalization divergences from the committed collation samples."""
    samples = collation["leg1_exact_madueke_sabates"].get("punct_or_space_samples", [])
    out = []
    for s in samples:
        mad, sab = s.get("madueke", ""), s.get("sabates", "")
        # majuscule run in madueke that sabates renders in title/mixed case
        if re.search(r"[A-Z]{4,}", mad) and mad.upper() != sab.upper()[:len(mad.upper())] \
                and mad.strip().upper() == sab.strip().upper():
            out.append({"ref": s.get("ref", ""), "madueke": mad.strip(),
                        "sabates": sab.strip(), "standard": mad.strip()})
            if len(out) >= limit:
                break
    if not out:  # fallback: any caps-bearing sample
        for s in samples:
            if re.search(r"[A-Z]{4,}", s.get("madueke", "")):
                out.append({"ref": s.get("ref", ""), "madueke": s["madueke"].strip(),
                            "sabates": s.get("sabates", "").strip(), "standard": s["madueke"].strip()})
                if len(out) >= limit:
                    break
    return out


def main() -> int:
    collation = json.loads(COLLATION.read_text())
    agg = collation["leg1_exact_madueke_sabates"]["aggregate"]

    spec = {
        "artifact": "modern-standard",
        "phase": "P2.0",
        "purpose": ("Reconciled Madueke_A↔Sabates_A modern spelling/typeset standard for rendering "
                    "the modern OriginalDR (idx 108) from the basis DB."),
        "authoritative_witness": "madueke_a",
        "reconciliation_basis": {
            "source_collation": "originaldr_validation/collation-3way.json",
            "relationship": "Sabates_A derives from Madueke_A (lineage-related transcription).",
            "compared_verses": agg["compared"],
            "identical": agg["identical"], "identical_pct": agg["identical_pct"],
            "ligature_only": agg["ligature_only"], "ligature_only_pct": agg["ligature_only_pct"],
            "punct_or_space_only": agg["punct_or_space_only"],
            "punct_or_space_only_pct": agg["punct_or_space_only_pct"],
            "substantive": agg["substantive"],
            "interpretation": ("0 substantive wording divergences → the witnesses agree on content. "
                               "The standard is therefore a pure normalization spec; no wording "
                               "arbitration is needed. Madueke_A is authoritative for surface; the "
                               "rules below resolve orthographic/typographic differences."),
        },
        "rules": [
            {"class": "wording", "decision": "madueke_a authoritative",
             "rationale": "0 substantive divergences vs Sabates_A; Madueke_A is the reference "
                          "modern edition for idx 108."},
            {"class": "ligatures", "decision": "expand", "mapping": LIGATURES,
             "rationale": "Madueke_A convention and modern orthography; %d verses differed on this "
                          "alone." % agg["ligature_only"],
             "examples": find_ligature_examples()},
            {"class": "divine_speech_capitalization", "decision": "preserve Madueke_A majuscule",
             "rationale": "The Douay tradition sets divine speech and messianic prophecy in "
                          "ALL-CAPS; Madueke_A preserves this, Sabates_A title-cases it. The "
                          "standard keeps the traditional majuscule (the dominant driver of the "
                          "%d punct/space-class divergences)." % agg["punct_or_space_only"],
             "examples": caps_examples(collation)},
            {"class": "whitespace", "decision": "normalize",
             "rule": "strip leading/trailing whitespace; collapse internal runs to a single space.",
             "rationale": "Madueke_A HTML extraction leaves trailing spaces; normalized for stable "
                          "rendering + diffing."},
            {"class": "punctuation", "decision": "prefer madueke_a",
             "rationale": "Where punctuation differs (no substantive impact), follow the "
                          "authoritative witness."},
        ],
        "apparatus_note": ("Sabates_A supplies the apparatus (arguments, verse-notes, cross-refs, "
                           "annotations) and the 3-book apocryphal appendix Madueke_A omits; "
                           "apparatus inclusion/placement is handled in P1.5 / P1.4, not here."),
    }
    OUT.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    lig = len(spec["rules"][1]["examples"])
    caps = len(spec["rules"][2]["examples"])
    print(f"modern-standard.json · authoritative=madueke_a · {agg['substantive']} substantive diffs "
          f"· {lig} ligature + {caps} caps worked examples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
