#!/usr/bin/env python3
"""test_verse_scope.py -- Gate 0f: every witness declares what its verse text may count as, and a
consumer reads the declaration.

`OCR-MASTERPLAN.md` §1.1a has stated a permission and a limit for every witness role since it was
written, and until 2026-08-08 NO CODE READ ONE.  `OT-1635-M` -- a 1635 Rouen reprint, excluded from
the verse text in four documents -- was attesting psalms 2,515 and genesis 1,530 in
`coverage-audit-verse.json` for as long as that audit has run.  Nothing had gone wrong in the prose.
The prose simply had nothing downstream of it.

This guard holds four things at once, because three of them can pass while the fourth is broken:

  (a) every registered witness resolves a verse scope
  (b) the scope agrees with the role table in §1.1a
  (c) `qc_audit`'s own choke point excludes `none` -- asserted by CALLING it, not by reading it
  (d) `corpus_localize.load()` REFUSES a `none` witness

(c) and (d) are separate on purpose.  (c) is the sweep that must skip cleanly; (d) is the read path
that must refuse even when someone reaches it directly.  A guard that checked only the table would be
the same shape as the failure it exists to prevent -- a declaration nothing consults.

Exit 0 when the gate holds.  Exit 1 naming what broke.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SPIKE))
import witnesses as W  # noqa: E402

# §1.1a, restated here as an INDEPENDENT copy of the role table on purpose. This is the one place a
# duplicate is wanted: if `ROLE_VERSE_SCOPE` is edited, this guard must fail rather than agree, because
# the two are meant to be checked against the document and not against each other. Everywhere else in
# this project a second copy of a map is a defect (R7.5b/c); here it is the test.
EXPECTED = {
    "base":        "full",
    "surrogate":   "full",
    "lowres":      "collation",
    "support":     "collation",
    "frontmatter": "none",
    "excluded":    "none",
}

# 🔴 THE ROLE ASSIGNMENT ITSELF, not merely the role->scope mapping.
#
# The first version of this guard checked only that each witness's scope matched its role, and it
# PASSED every injection: flipping `OT-1635-M` from `frontmatter` to `lowres` moved it to the other
# branch of a table it agreed with either way, so a 1635 reprint quietly became admissible for 1609
# verse text and the guard congratulated itself.  That is the exact shape of the R7.5 defect --
# `test_raster_routing.py` passed when `F` was deleted from the bar list -- and the remedy is the same:
# **assert the SET, not the branch.**
#
# So the three scope-critical assignments are pinned here with the evidence that fixes them, and the
# `none` set is asserted to be EXACTLY these two.  A future witness may of course be scoped `none`;
# doing so must require editing this line, which is the point.
PINNED = {
    "OT-1635-M": ("frontmatter", "none",
                  "1635 Rouen, a DIFFERENT EDITION from the 1609/1610 Douai printing being "
                  "transcribed. No capture of it could ever make it a witness here, so the limit is "
                  "bibliographic and permanent (§1.1, §1.1a)."),
    "NT-1582-X": ("excluded", "none",
                  "not a distinct copy: B-NT re-wrapped and upscaled exactly 2.000x, NCC 0.9847 to B's "
                  "own grid, top-octave energy 0.0002 against B's own 0.0074-0.0097. Admitting it "
                  "double-counts B under a second name (§1.1a)."),
    "NT-1582-M": ("lowres", "collation",
                  "the SAME SETTING as the base exemplar (1582 Rheims Fogny), limited only by a 1-bit "
                  "CCITT raster at ~380 ppi. It attests and collates; it never adjudicates a glyph "
                  "(R9.0, and GLYPH_BARRED is unchanged)."),
}

NONE_SCOPED = {"OT-1635-M", "NT-1582-X"}


def main() -> int:
    fail: list[str] = []

    # ---- (a) + (b) every record scopes, and the scope matches §1.1a
    print("every witness declares a verse scope, and it agrees with §1.1a:")
    for (vol, sig), rec in sorted(W.WITNESSES.items()):
        role = rec["role"]
        try:
            got = W.verse_scope(vol, sig)
        except KeyError:
            fail.append(f"{W.wid(vol, sig)}: role {role!r} has no verse scope")
            print(f"  FAIL  {W.wid(vol, sig):14} role={role:12} NO SCOPE")
            continue
        want = EXPECTED.get(role)
        ok = got == want
        if not ok:
            fail.append(f"{W.wid(vol, sig)}: role {role!r} scopes {got!r}, §1.1a says {want!r}")
        print(f"  {'ok  ' if ok else 'FAIL'}  {W.wid(vol, sig):14} role={role:12} scope={got}")

    if set(EXPECTED) != set(W.ROLE_VERSE_SCOPE):
        d = set(EXPECTED) ^ set(W.ROLE_VERSE_SCOPE)
        fail.append(f"role vocabulary drifted between §1.1a and the registry: {sorted(d)}")

    # ---- the ASSIGNMENT, pinned. Without this the checks above pass under any relabelling.
    print("\nthe scope-critical role assignments are what the evidence says (set, not branch):")
    by_wid = {W.wid(v, s): (v, s) for (v, s) in W.WITNESSES}
    for widx, (want_role, want_scope, why) in sorted(PINNED.items()):
        if widx not in by_wid:
            fail.append(f"{widx} is pinned here but absent from the registry")
            print(f"  FAIL  {widx:14} not in the registry")
            continue
        v, s = by_wid[widx]
        got_role = W.WITNESSES[(v, s)]["role"]
        got_scope = W.verse_scope(v, s)
        ok = (got_role, got_scope) == (want_role, want_scope)
        if not ok:
            fail.append(f"{widx}: role/scope is {got_role}/{got_scope}, must be "
                        f"{want_role}/{want_scope} — {why}")
        print(f"  {'ok  ' if ok else 'FAIL'}  {widx:14} {got_role:12} {got_scope}")

    got_none = {W.wid(v, s) for (v, s) in W.WITNESSES if W.verse_scope(v, s) == "none"}
    ok = got_none == NONE_SCOPED
    if not ok:
        fail.append(f"the set of verse-inadmissible witnesses is {sorted(got_none)}, "
                    f"declared {sorted(NONE_SCOPED)}. Changing it is a decision about EVIDENCE and "
                    f"must be made here, in the open, with its reason.")
    print(f"  {'ok  ' if ok else 'FAIL'}  verse-inadmissible set == {sorted(NONE_SCOPED)}")

    # ---- (c) the audit's choke point actually drops them. Called, not read.
    print("\nthe scorer's choke point excludes 'none' (called, not inspected):")
    sys.path.insert(0, str(SPIKE))
    import qc_audit as Q  # noqa: E402  -- imported here: heavy, and only this check needs it

    none_dirs = sorted(od for od in W.OCR_DIR_TO_WITNESS if W.verse_scope_of(od) == "none")
    for od in none_dirs:
        vol, sig = W.witness_of(od)
        fake = {"volumes": [{"ocr_dir": od}]}
        got = Q.scan_ocr_dirs(fake)
        ok = got == []
        if not ok:
            fail.append(f"qc_audit.scan_ocr_dirs admitted {od} ({W.wid(vol, sig)}, scope 'none')")
        print(f"  {'ok  ' if ok else 'FAIL'}  {od:14} {W.wid(vol, sig):14} -> {got}")
    if not none_dirs:
        fail.append("no witness has scope 'none' -- this guard would pass vacuously, which is not a pass")
        print("  FAIL  nothing is scoped 'none'; the exclusion path is untested")

    # An admitted volume must still come back, or the filter is refusing everything and (c) passes
    # for the wrong reason -- the self-consistent-check failure R7.5's guard had.
    adm = sorted(od for od in W.OCR_DIR_TO_WITNESS if W.verse_scope_of(od) != "none")
    probe = adm[0]
    got = Q.scan_ocr_dirs({"volumes": [{"ocr_dir": probe}]})
    ok = got == [probe]
    if not ok:
        fail.append(f"qc_audit.scan_ocr_dirs dropped {probe}, which IS admitted -- the filter rejects all")
    print(f"  {'ok  ' if ok else 'FAIL'}  {probe:14} is admitted and survives the filter -> {got}")

    # ---- (d) the read path refuses even when reached directly
    print("\ncorpus_localize.load() refuses a 'none' witness:")
    import corpus_localize as CL  # noqa: E402

    for od in none_dirs:
        try:
            CL.load(od)
        except W.VerseScopeError:
            print(f"  ok    {od:14} raises VerseScopeError")
        except Exception as e:                                     # noqa: BLE001
            fail.append(f"load({od}) raised {type(e).__name__}, not VerseScopeError")
            print(f"  FAIL  {od:14} raised {type(e).__name__}: {e}")
        else:
            fail.append(f"load({od}) returned data for a 'none'-scope witness")
            print(f"  FAIL  {od:14} returned data")
        # and the documented opt-out must work, or auditing the artefact becomes impossible
        try:
            CL.load(od, scope_check=False)
        except W.VerseScopeError:
            fail.append(f"load({od}, scope_check=False) still refused -- the opt-out is broken")
            print(f"  FAIL  {od:14} scope_check=False still refused")
        else:
            print(f"  ok    {od:14} scope_check=False is honoured (artefact audit stays possible)")

    print()
    if fail:
        print(f"FAILED — {len(fail)} defect(s):")
        for f in fail:
            print(f"  {f}")
        return 1
    print("Gate 0f holds: every witness is scoped, the scopes match §1.1a, and two independent "
          "consumers enforce them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
