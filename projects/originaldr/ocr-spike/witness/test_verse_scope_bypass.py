#!/usr/bin/env python3
"""test_verse_scope_bypass.py -- R9.2c: Gate 0f is only as strong as its narrowest route.

`corpus_localize.load()` refuses a witness the corpus does not admit for verse text (R9.2).  That
refusal guards every consumer that calls it -- and **nothing else**.  A module that opens
`.corpus-localize-<dir>.json` and reads `["verses"]` itself has the same data with none of the gate.

The R9.2 plan asserted that `load()` was "the function every verse consumer already goes through."
It was not, and the way that claim was reached is worth recording: the check was a grep for modules
*mentioning* `corpus_localize`, which is a test of imports, not of call sites.  Nine modules read the
path directly.  **Two routes to the data, one guarded, is R7.5 exactly** -- the defect where
`OCR_DIR_TO_JP2` and `pixel_source()` both reached the pixels and only one was checked.

This guard exits 1 while any direct reader remains, and names them.  It does not attempt to rewrite
them: converting a consumer is a judgement about what that consumer is for -- `integrity_sweep` reads
the artefact to COUNT it, which is bookkeeping and legitimately outside the gate, while `gen1_rescore`
reads it to SCORE with, which is not.  The list is the worklist.

Exit 0 when every reader outside `corpus_localize` goes through `load()`.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent

# The artefact path, built by f-string or by name. Both forms are how the direct readers spell it.
DIRECT = re.compile(r'["\']\.corpus-localize-|corpus-localize-\{')

# `corpus_localize` itself must read and write the path -- it is the module that owns it.
OWNER = {"corpus_localize.py"}

# Readers that are legitimately OUTSIDE the gate, each with the reason. Bookkeeping is not evidence:
# scope governs what a verse may COUNT AS, not whether a file may be counted (R9.2b). Anything added
# here must state why the read is not a verse-grain evidential read.
STRUCTURAL_EXEMPT = {
    "integrity_sweep.py": "counts records to reconcile volumes; never scores a verse (R9.2b)",
}


def main() -> int:
    offenders: dict[str, int] = {}
    exempt_seen: set[str] = set()
    for p in sorted(SPIKE.rglob("*.py")):
        rel = str(p.relative_to(SPIKE))
        if "__pycache__" in rel or rel.startswith(".superseded") or rel.startswith("witness/"):
            continue
        if p.name in OWNER:
            continue
        try:
            t = p.read_text()
        except OSError:
            continue
        n = len(DIRECT.findall(t))
        if not n:
            continue
        if p.name in STRUCTURAL_EXEMPT:
            exempt_seen.add(p.name)
            continue
        offenders[rel] = n

    print("Gate 0f — routes to the localization artefact:")
    print(f"  owner (may read the path directly): {sorted(OWNER)}")
    for name in sorted(exempt_seen):
        print(f"  exempt  {name:26} {STRUCTURAL_EXEMPT[name]}")
    stale = sorted(set(STRUCTURAL_EXEMPT) - exempt_seen)
    if stale:
        # An exemption for a file that no longer reads the path is a standing permission with no
        # subject -- exactly the shape of the drop rule that was cited for months and read by nothing.
        print(f"  ⚠ stale exemption(s), no longer reading the artefact: {stale} — remove them")

    if not offenders:
        print("\nevery verse-grain reader goes through corpus_localize.load(); the gate has one route.")
        return 0

    print(f"\nBYPASSING load() — {len(offenders)} module(s), {sum(offenders.values())} direct read(s):")
    for f, n in sorted(offenders.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3}  {f}")
    print("\nOPEN (R9.2c) — these read the localization artefact without passing Gate 0f. Two routes to\n"
          "the data with one guarded is R7.5 restated: the guard is not wrong, it is merely not on the\n"
          "path the caller took. Route each through `load()` (or a `load_admitted()` for sweeps), or\n"
          "add it to STRUCTURAL_EXEMPT with the reason its read is not evidential. Exit 1 until then.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
