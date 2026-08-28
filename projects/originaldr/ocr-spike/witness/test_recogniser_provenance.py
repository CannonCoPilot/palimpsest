#!/usr/bin/env python3
"""R13.1 ACCEPTANCE -- the injection proof: swap the model, and the artefact says so.

R13.1's acceptance is written in the Roadmap as *"a reading's provenance names its model;
INJECTION-PROVEN -- swap the model, and the artefact says so."* This guard performs the swap.

⚠️ WHY A SWAP AND NOT AN INSPECTION. A provenance field can be present, well-named, populated and
STILL not describe what produced the reading -- that is R13's entire finding one level up, where a
fine-tuned recogniser could be pointed at in five documents and loaded by no code. **The only way to
show a stamp tracks the instrument is to move the instrument and watch the stamp move.** A field
that does not move when the model moves is decoration, and it would let a reading produced by one
model be published under another's name.

WHAT IS CHECKED:

  1. NO SILENT DEFAULT -- with the selection file hidden, reading RAISES rather than falling back.
     ⚠️ This is the load-bearing one. R2.1b's whole purpose is defeated by a default, because an
     arbitrary model wearing the selected model's authority is harder to see than no model at all.
  2. THE STAMP NAMES THE SELECTED MODEL, and carries its DIGEST, not merely its path.
  3. INJECTION MOVES THE STAMP -- swapping to another candidate changes `model` AND `model_sha`.
  4. INJECTION MOVES THE READING -- the two models return different text on at least one crop of
     R2.1b's own keyed set. ⚠️ Without this, (3) would pass on a stamp that is correctly plumbed to
     a recogniser that is never actually consulted: when broken output equals healthy output, the
     MECHANISM has to be validated, not the label.

    ../ocr-venv/bin/python witness/test_recogniser_provenance.py

Exit 0 when the stamp is proven to track the model. Exit 1 otherwise -- and a failure here means
every reading's provenance is unfalsifiable, which is worse than an absent field.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

import recogniser as RG                                    # noqa: E402
from audit_recog_holdout import MODELS                     # noqa: E402
from build_recog_gold import OUT, MANIFEST                 # noqa: E402

FAILURES: list[str] = []


def check(label: str, ok: bool, why: str = "") -> bool:
    print(f"  {'ok   ' if ok else '🔴 FAIL'}  {label}")
    if not ok:
        print(f"          {why}")
        FAILURES.append(label)
    return ok


def main() -> int:
    print("R13.1 — THE INJECTION PROOF: does the provenance stamp track the model?\n")

    # ── 1. no silent default ──────────────────────────────────────────────────────────────────
    real = RG.SELECTION
    RG.SELECTION = _HERE / "__no_such_selection__.json"
    RG.inject(None)
    try:
        RG.provenance()
        raised = False
    except RG.NoSelectedModel:
        raised = True
    except Exception:
        raised = False
    RG.SELECTION = real
    RG.inject(None)
    check("with no selection on disk, reading RAISES rather than defaulting", raised,
          "a default here is an UNSELECTED model wearing the selected model's authority — "
          "the exact defect R2.1b exists to prevent")

    # ── 2. the stamp names the selected model and carries a digest ────────────────────────────
    sel = json.loads(real.read_text())["selected"]
    p = RG.provenance()
    check(f"the stamp names R2.1b's selection ({sel})", p["model"] == sel,
          f"stamp says {p['model']!r}")
    check("the stamp carries the artefact's DIGEST, not only its path",
          bool(p.get("model_sha")) and len(p["model_sha"]) >= 8,
          "a path is a label a human chose; the digest is what was opened")
    print(f"          {p}")

    # ── 3 + 4. injection moves the stamp AND the reading ──────────────────────────────────────
    other = next((k for k in MODELS if k != sel), None)
    lines = [e for e in json.loads(MANIFEST.read_text())["lines"] if not e.get("excluded")]
    crops = [OUT / f"{e['stem']}.png" for e in lines]
    crops = [c for c in crops if c.is_file()][:12]

    base = [RG.read_stamped(c) for c in crops]
    RG.inject(other, str(SPIKE / MODELS[other][0]))
    inj_prov = RG.provenance()
    inj = [RG.read_stamped(c) for c in crops]
    RG.inject(None)
    back = RG.provenance()

    check(f"injecting {other} CHANGES the model name in the stamp",
          inj_prov["model"] == other and inj_prov["model"] != sel,
          f"stamp did not move: {inj_prov['model']}")
    check("injecting CHANGES the digest too", inj_prov["model_sha"] != p["model_sha"],
          "same sha for two different artefacts — the digest is not being taken from the file read")
    diff = sum(1 for a, b in zip(base, inj) if a["text"] != b["text"])
    check(f"injecting CHANGES the READING on at least one crop ({diff} of {len(crops)} differ)",
          diff > 0,
          "the stamp moved but the text did not — the provenance would be plumbed to a recogniser "
          "that is never actually consulted. When broken output equals healthy output, validate "
          "the MECHANISM, not the label")
    check("restoring returns the stamp to R2.1b's selection", back["model"] == sel,
          f"left injected as {back['model']}")

    print("\n  a sample the proof rests on:")
    for a, b in list(zip(base, inj))[:3]:
        if a["text"] != b["text"]:
            print(f"    {a['model']:14s} {a['text'][:56]!r}")
            print(f"    {b['model']:14s} {b['text'][:56]!r}")

    print("\n⚠️ WHAT THIS PROVES AND WHAT IT DOES NOT. It proves a reading produced through")
    print("   `witness/recogniser.py` cannot be separated from the model that made it, and that")
    print("   the stamp is falsifiable. It does NOT convert the attesting arm: `gen1_r3.py` still")
    print("   sets `old_text` from the stored corpus OCR, and that conversion changes campaign")
    print("   artefacts, so it is the deliberate REMAINDER of R13.1. ⚠️ And it measures nothing")
    print("   about ſ recovery — R13.2 does that, and the 1,142 open cells may not be called")
    print("   recovered before it runs.")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)}")
        return 1
    print("\n✅ the provenance stamp TRACKS the model, proven by swapping it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
