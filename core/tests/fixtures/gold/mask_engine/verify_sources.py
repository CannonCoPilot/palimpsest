#!/usr/bin/env python
"""Verify the local (gitignored) Bible source corpus against ``sources.manifest.json``.

Enforces the "preserve, don't push" policy: the raw epub/pdf/txt live only in the local
``imports/`` corpus, but the manifest ships their sha256 fingerprints. Anyone holding the
corpus can run this to prove their binaries are byte-identical to the sources each gold
was keyed to — provenance without redistribution.

Exit 0 iff every locally-present source matches its manifest hash. Sources marked
``source_present: false`` in the manifest (kept in pipeline-local scratch, not the
preserved corpus) are reported but do not fail the check.

Usage:
  verify_sources.py            # verify all Bible sources present in imports/
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLD = HERE.parent
REPO = HERE.parents[4]
IMPORTS = REPO / "imports"
MANIFEST = GOLD / "sources.manifest.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _index() -> dict[str, Path]:
    idx: dict[str, Path] = {}
    if IMPORTS.is_dir():
        for p in IMPORTS.rglob("*"):
            if p.is_file():
                idx.setdefault(p.name, p)
    return idx


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    local = _index()
    ok = mismatch = absent = 0
    problems: list[str] = []
    for b in manifest["bibles"]:
        name, want = b["source_file"], b["source_sha256"]
        path = local.get(name)
        if path is None:
            absent += 1
            tag = "ABSENT-EXPECTED" if not b["source_present"] else "MISSING"
            if b["source_present"]:
                problems.append(f"[{b['id']}] {name}: manifest says present but not found locally")
            print(f"  {b['id']:>3}  {tag:16} {name[:50]}")
            continue
        got = _sha256(path)
        if want and got == want:
            ok += 1
            print(f"  {b['id']:>3}  OK               {name[:50]}")
        else:
            mismatch += 1
            problems.append(f"[{b['id']}] {name}: sha256 {got[:12]} != manifest {str(want)[:12]}")
            print(f"  {b['id']:>3}  SHA-MISMATCH     {name[:50]}")
    print(f"\n{ok} OK · {mismatch} mismatch · {absent} absent (of {manifest['count']})")
    for p in problems:
        print(f"  ⚠ {p}")
    return 0 if mismatch == 0 and not any("MISSING" in p or "present but not found" in p for p in problems) else 1


if __name__ == "__main__":
    sys.exit(main())
