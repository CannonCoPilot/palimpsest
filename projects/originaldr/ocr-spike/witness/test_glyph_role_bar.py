#!/usr/bin/env python3
"""R9.7 -- Gate 0f's last hole: the ROLE bar on glyph work is now ENFORCED, not merely written.

THE DEFECT, as `OCR-OVERVIEW.md` recorded it and nothing closed:

    "`GLYPH_BARRED` in the registry holds exactly `F` and `X` -- NOT `M` -- so `admissible("NT")`
     names `M` and `glyph_source("NT", "M")` returns a usable PDF path, although the `lowres` role
     bars `M` from training data, from CER evaluation and from adjudicating long-ſ. The bar is
     written in `ROLES` and ENFORCED BY NOTHING: the same shape as Gate 0f and Gate 0d before their
     consumers were built."

⚠️ WHY A SIGLUM-LEVEL BAR COULD NEVER HAVE CLOSED IT. `M` is ONE file holding TWO books -- a 1635
Rouen Old Testament (`frontmatter`) and a 1582 Rheims New Testament (`lowres`). No entry keyed on
the letter `M` can state a bar that is true of both halves. The bar has to be derived PER RECORD
from the role, which is what `glyph_witnesses` already did correctly while being a counter rather
than a gate.

⚠️ AND THE BAR IS ON ONE GRAIN, NEVER ON THE WITNESS. `M`'s New Testament is the SAME 1582 SETTING
as the base exemplar and is wanted, positively, for page LAYOUT and GEOMETRY -- region boundaries,
archetype classification, reading order -- none of which resolves a glyph, and all of which the
adaptive visual agent (§3.0) needs. This guard asserts that `structural_witnesses` still names it.
A guard that closed the glyph hole by deleting the witness would have cost the agent a witness.

WHAT IS CHECKED
  1. every record whose role is not a GLYPH_ROLE is REFUSED by `glyph_source`;
  2. every record whose role IS a GLYPH_ROLE and carries no other bar is ADMITTED;
  3. `admissible()` never names a witness `glyph_source()` would itself refuse -- the two carry the
     same clause and must not drift;
  4. the bar is grain-specific: a glyph-barred `lowres` record is STILL a structural witness;
  5. THE PROVEN NEGATIVE -- with the role clause removed, `NT-1582-M` is admitted. A guard that has
     never rejected anything is not known to work.

    ../ocr-venv/bin/python witness/test_glyph_role_bar.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import witnesses as W  # noqa: E402

FAIL: list[str] = []


def check(label, ok, detail=""):
    print(f"  {'ok  ' if ok else '🔴 FAIL'}  {label}")
    if not ok:
        FAIL.append(f"{label}: {detail}")


def main() -> int:
    print("Gate 0f — the ROLE bar on glyph-level work\n")

    refused, admitted = [], []
    for key in sorted(W.WITNESSES):
        try:
            W.glyph_source(*key)
            admitted.append(key)
        except ValueError:
            refused.append(key)

    print("1. a role outside GLYPH_ROLES must be REFUSED:")
    for key in sorted(W.WITNESSES):
        role = W.WITNESSES[key]["role"]
        if role in W.GLYPH_ROLES:
            continue
        check(f"{W.wid(*key):14s} role={role:11s} refused", key in refused,
              "a role the registry bars from glyph work returned a usable path")

    print("\n2. a GLYPH_ROLE with no other bar must be ADMITTED (the bar must not over-reach):")
    for key in sorted(W.WITNESSES):
        role = W.WITNESSES[key]["role"]
        if role not in W.GLYPH_ROLES or key[1] in W.GLYPH_BARRED or key in W.NO_READING:
            continue
        check(f"{W.wid(*key):14s} role={role:11s} admitted", key in admitted,
              "a witness that MAY carry a glyph call was refused — the bar over-reaches")

    print("\n3. `admissible()` must never name a witness `glyph_source()` would refuse:")
    for vol in sorted({v for v, _ in W.WITNESSES}):
        named = set(W.admissible(vol))
        bad = [W.wid(*k) for k in refused if k[0] == vol and W.wid(*k) in named]
        check(f"admissible({vol!r}) is self-consistent", not bad,
              f"names {bad}, which glyph_source refuses — the caller is sent round a loop")

    print("\n4. THE BAR IS ON ONE GRAIN: a glyph-barred `lowres` record is STILL structural:")
    for key in sorted(k for k in refused if W.WITNESSES[k]["role"] == "lowres"):
        vol, sig = key
        try:
            struct = set(W.structural_witnesses(vol, W.WITNESSES[key].get("year")))
        except Exception:
            struct = set(W.structural_witnesses(vol))
        check(f"{W.wid(*key):14s} still a STRUCTURAL witness",
              W.wid(*key) in struct or sig in struct,
              "closing the glyph hole must not cost the agent a layout witness")

    print("\n5. PROVEN NEGATIVE — remove the role clause and the hole reopens:")
    saved = W.GLYPH_ROLES
    try:
        # Restore the pre-fix behaviour exactly: every role admitted, siglum bars only.
        W.GLYPH_ROLES = frozenset(W.ROLES)
        leaked = []
        for key in sorted(W.WITNESSES):
            if W.WITNESSES[key]["role"] in saved:
                continue
            try:
                W.glyph_source(*key)
                leaked.append(W.wid(*key))
            except ValueError:
                pass
        check(f"without the clause, {len(leaked)} record(s) leak: {leaked}", bool(leaked),
              "the guard cannot demonstrate a rejection — it is not known to work")
    finally:
        W.GLYPH_ROLES = saved

    print()
    if FAIL:
        print(f"FAILED: {len(FAIL)}")
        for f in FAIL:
            print(f"  {f}")
        return 1
    # ⚠️ Printed as a FRACTION on purpose: the verification standard only enforces a claim whose
    # first `N/M` it can find in this output (R11.2c). "6 of 12" is prose and is not checkable.
    print(f"Gate 0f role bar ENFORCED — {len(refused)}/{len(W.WITNESSES)} records refused at "
          f"glyph grain, and the bar is grain-specific, not witness-wide")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
