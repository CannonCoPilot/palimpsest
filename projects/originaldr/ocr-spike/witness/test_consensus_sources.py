#!/usr/bin/env python3
"""test_consensus_sources.py -- R9.4b: nothing enters the consensus fusion that the corpus does not
admit as verse evidence.

`consensus_v2.load_all_streams` discovers its sources by GLOBBING a directory.  That is precisely the
re-entry route `curated_sources.py` was written to close -- its own docstring says "a banned folder can
never re-enter by a directory glob" and names `consensus_v2` as a builder that MUST filter.  It did not
import that module at all.  `consensus-full/matthew.json` recorded, as of 2026-08-08:

    scan_sources = [archive-nt-1582, eebo-nt, eebo-vol1, jp2-S04, jp2-S06, jp2-S08, pdf-S09nt]

which is inadmissible on three independent grounds at once: `eebo-nt`/`eebo-vol1` are BANNED (S10-S15);
`jp2-S08` is `NT-1582-X`, B upscaled 2.000x, so B was counted TWICE as two witnesses; and `jp2-S06` is
the retired ambiguous id naming one file that carries two settings 53 years apart.

The module's own de-duplication could not have caught the S08 case, and the reason is worth keeping:
supersession is keyed on the FILENAME (`jp2-<key>` supersedes `pdf-/eebo-/archive-<key>`).  X is
`jp2-S08` and B is `pdf-S09nt` -- the same physical copy under two unrelated keys -- so the key test
cannot express the relation.  A filter cannot enforce a distinction it cannot state.  Hence the scope
gate is keyed on the WITNESS (Gate 0f), not on the directory name.

This guard holds three things, and the third is the one that matters:

  (a) every stream the builder actually returns is curated AND verse-admitted -- asserted by CALLING
      `load_all_streams()`, not by reading the source
  (b) the exclusion is not vacuous, and an admitted source still survives it (a filter that rejects
      everything passes (a) for the wrong reason -- the R7.5 `test_raster_routing` failure)
  (c) the BANNED and `none`-scope branches are exercised BY INJECTION against a synthetic source
      tree.  This is not optional here: after the `2633cbb` migration the `eebo-*` directories are
      not present on disk at all, so on live data that branch never runs.  Its correctness would
      otherwise rest on the absence of the input rather than on the presence of the filter -- an
      agreement nobody checks, which is the same shape as the defect.

Exit 0 when the gate holds.  Exit 1 naming what broke.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SPIKE))
import witnesses as W  # noqa: E402
import curated_sources as CS  # noqa: E402
import consensus_v2 as C  # noqa: E402


def _reset_streams() -> None:
    """Drop the module's whole-Bible stream cache and its exclusion ledger."""
    C._STREAMS = None
    C._EXCLUDED_STREAMS.clear()


def main() -> int:
    fail: list[str] = []

    # The filter can be removed wholesale, and that is the likeliest way it dies: a revert, a
    # merge, someone "simplifying" a glob. Proven by injection -- reverting `consensus_v2.py` to
    # its pre-R9.4b commit made this guard die of AttributeError deep in a helper, which is a
    # non-zero exit that names a missing attribute rather than a missing GATE. Check for the
    # machinery first and say what is actually wrong.
    print("the filter machinery is present in the builder:")
    for attr, what in (("_EXCLUDED_STREAMS", "the exclusion ledger"),
                       ("CS", "the curated-source allowlist import"),
                       ("W", "the witness registry import")):
        if not hasattr(C, attr):
            fail.append(f"consensus_v2 has no {attr} -- {what} is GONE. The source filter has been "
                        f"removed, not merely broken: the fusion is once again a bare directory "
                        f"glob, which is the R9.4b defect itself.")
            print(f"  FAIL  consensus_v2.{attr:18} MISSING ({what})")
        else:
            print(f"  ok    consensus_v2.{attr:18} present ({what})")
    if fail:
        return _report(fail)

    # ---- (a) what the builder actually returns, on the real tree
    print("every fused stream is curated and verse-admitted (load_all_streams called, not read):")
    _reset_streams()
    streams = C.load_all_streams()
    if not streams:
        fail.append("load_all_streams returned nothing -- this guard cannot pass vacuously")
        print("  FAIL  no streams at all; the source tree is missing or the filter rejects everything")
    for name in sorted(streams):
        curated = CS.is_curated(name)
        try:
            admitted = W.verse_admitted(name)
            scope = W.verse_scope_of(name)
        except KeyError as e:
            fail.append(f"{name} is fused but does not resolve to a witness: {e}")
            print(f"  FAIL  {name:22} unresolvable")
            continue
        ok = curated and admitted
        if not ok:
            fail.append(f"{name} is FUSED but curated={curated} verse_scope={scope!r}")
        print(f"  {'ok  ' if ok else 'FAIL'}  {name:22} curated={str(curated):5} scope={scope}")

    # ---- (b) the exclusion actually fired, and it is recorded with a reason
    print("\nthe exclusion is non-vacuous and every drop carries its reason:")
    if not C._EXCLUDED_STREAMS:
        fail.append("nothing was excluded on the live tree -- the drop path is untested here; "
                    "(c) below must still exercise it, but a silent empty ledger is not a pass")
        print("  FAIL  nothing excluded")
    for name, why in sorted(C._EXCLUDED_STREAMS.items()):
        ok = bool(why)
        if not ok:
            fail.append(f"{name} was dropped with no recorded reason (R1.4)")
        print(f"  {'ok  ' if ok else 'FAIL'}  {name:22} {why}")
        if name in streams:
            fail.append(f"{name} is in BOTH the fused set and the excluded ledger")

    # ---- (c) INJECTION. The branches live data no longer reaches.
    #
    # A synthetic DIPL_ROOT: one banned source, one `none`-scope witness, one id that resolves to no
    # witness at all, and -- the control -- a symlink to a real admitted source, which must survive.
    print("\ninjection: banned / inadmissible / unresolvable sources are refused, admitted survives:")
    real_root = C.D.DIPL_ROOT
    admitted_real = sorted(
        d.name for d in real_root.glob("*")
        if d.is_dir() and CS.is_curated(d.name) and _safe_admitted(d.name)
    )
    if not admitted_real:
        fail.append("no admitted source on the real tree to use as the injection control")
        print("  FAIL  no control source available")
        return _report(fail)
    control = admitted_real[0]

    INJECTED = {
        "eebo-nt":     "BANNED (S10-S15, REP-1) -- the case consensus-full actually fused",
        "eebo-vol1":   "BANNED (S10-S15, REP-1) -- the case consensus-full actually fused",
        "jp2-S08":     "NT-1582-X, B upscaled 2.000x -- fusing it double-counts B",
        "jp2-S06":     "the retired ambiguous id; the registry refuses to resolve it",
        "not-a-source": "resolves to no witness at all",
    }

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        for name in INJECTED:
            (tmp / name).mkdir()
            # a page apiece, so an empty directory is not what causes the drop
            (tmp / name / "0000.json").write_text(json.dumps({"lines": []}))
        (tmp / control).symlink_to(real_root / control)

        C.D.DIPL_ROOT = tmp
        try:
            _reset_streams()
            got = C.load_all_streams()
        finally:
            C.D.DIPL_ROOT = real_root

        for name, why in sorted(INJECTED.items()):
            refused = name not in got
            if not refused:
                fail.append(f"INJECTED {name} was FUSED -- {why}")
            print(f"  {'ok  ' if refused else 'FAIL'}  {name:22} refused={refused}  ({why})")

        # the control. Without this the whole injection passes if the filter rejects everything.
        survived = control in got
        if not survived:
            fail.append(f"the admitted control {control} was refused -- the filter rejects all, so "
                        f"the refusals above prove nothing")
        print(f"  {'ok  ' if survived else 'FAIL'}  {control:22} survived={survived}  (control: an "
              f"admitted source must NOT be refused)")

    _reset_streams()
    return _report(fail)


def _safe_admitted(name: str) -> bool:
    try:
        return W.verse_admitted(name)
    except KeyError:
        return False


def _report(fail: list[str]) -> int:
    print()
    if fail:
        print(f"FAILED — {len(fail)} defect(s):")
        for f in fail:
            print(f"  {f}")
        return 1
    print("R9.4b holds: the fusion admits only curated, verse-admitted sources, and the banned and "
          "inadmissible branches are proven by injection rather than by the absence of the input.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
