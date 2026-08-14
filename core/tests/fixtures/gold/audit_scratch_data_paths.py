#!/usr/bin/env python
"""AUDIT (R11.2a) -- tracked modules naming gitignored ``.scratch/`` DATA paths.

This is an AUDIT, not a guard, and the distinction is load-bearing (R10.1).

``test_no_scratch_deps.py`` forbids the thing that is unambiguously wrong: importing
CODE from a gitignored directory. This file measures the softer thing -- tracked
modules that name gitignored DATA. Some of those are legitimate (a 2 GB ingest cache,
a regenerable sqlite basis-db) and some are defects (R9.6's dead-tree reads, which
``mkdir(parents=True)`` and WRITE where nothing reads). Telling them apart requires
reading each one, so a blanket pass/fail would force either a bulk rewrite nobody
reasoned about or a threshold weakened until it passed. Both are forbidden.

So: exit 1 is the HEALTHY state while any remain, and **the count must FALL**. A
below-threshold result is never converted into an accepted one -- each reference is
dispositioned individually, into one of:

  (a) MACHINE-LOCAL DATA ROOT -- keep, but make it env-overridable with a default,
      and RAISE when absent naming the path. Never degrade to an empty result: a
      missing cache that returns `None` reads downstream as "nothing was there",
      which is R1.4 and `_empty_because` (§1.4). Then add it to SANCTIONED below.
  (b) DEAD TREE -- the path no longer exists post-migration. Fix under R9.6.
  (c) SHOULD BE TRACKED -- it is code or a pin, not bulk data. Move it (R11.1).

⚠️ Do NOT add entries to SANCTIONED to make the number fall. The number falling by
sanction rather than by disposition is the metric measuring vocabulary instead of
call sites -- the R9.2c failure, one level up.

Baseline 2026-08-14: 71 references across 38 tracked files, 2 sanctioned.

Exit 1 = references remain (healthy, expected). Exit 0 = all dispositioned.

Run: ../ocr-venv/bin/python core/tests/fixtures/gold/audit_scratch_data_paths.py
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]

SCRATCH = re.compile(r"\.scratch\b")

# Dispositioned as (a): env-overridable machine-local DATA root that RAISES when
# absent. Each entry names the file and the reason it is permitted. Additions
# require the raise to exist -- see the warning in the module docstring.
SANCTIONED: dict[str, str] = {
    "core/tests/fixtures/gold/harness/harness.py":
        "R11.1: MASK_EVAL_DATA default; require_data() raises naming the path",
    "core/tests/fixtures/gold/mask_engine/text_source.py":
        "R11.1: ingest workspace list; project_for() raises when no workspace exists",
}

# The two detectors must NAME the pattern in order to find it, so they match
# themselves. Excluding them is not a weakening -- a detector's own search pattern
# is not a dependency on gitignored data. (Found by running this audit against a
# tree that included it: exactly the R9.2c shape, one level up.) Nothing else may
# be added here; a real reference goes to SANCTIONED with a raise, or gets fixed.
SELF = {
    "core/tests/fixtures/gold/audit_scratch_data_paths.py",
    "core/tests/fixtures/gold/test_no_scratch_deps.py",
}

BASELINE_REFS = 71
BASELINE_FILES = 38


def tracked_python_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "*.py"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
    return [REPO / p for p in out.split("\0") if p]


def refs(path: Path) -> list[tuple[int, str]]:
    """String constants naming a .scratch path. Docstrings excluded -- they describe,
    they do not bind, and a check a comment can trip measures vocabulary (R9.2c)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not SCRATCH.search(text):
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [
            (i, f"[unparseable] {ln.strip()}")
            for i, ln in enumerate(text.splitlines(), 1)
            if SCRATCH.search(ln) and not ln.lstrip().startswith("#")
        ]

    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    docstrings.add(id(body[0].value))

    return [
        (n.lineno, n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and id(n) not in docstrings
        and SCRATCH.search(n.value)
    ]


def main() -> int:
    open_files: dict[str, list[tuple[int, str]]] = {}
    sanctioned_files = 0
    for path in tracked_python_files():
        rel = path.relative_to(REPO).as_posix()
        if rel in SELF:
            continue
        hits = refs(path)
        if not hits:
            continue
        if rel in SANCTIONED:
            sanctioned_files += 1
            continue
        open_files[rel] = hits

    n_refs = sum(len(v) for v in open_files.values())
    for rel, hits in sorted(open_files.items()):
        print(f"{rel}")
        for lineno, val in hits:
            print(f"  :{lineno}  {val}")

    print()
    print(f"OPEN: {n_refs} references across {len(open_files)} tracked files")
    print(f"SANCTIONED: {sanctioned_files}/{len(SANCTIONED)} declared files present")
    print(f"BASELINE (2026-08-14): {BASELINE_REFS} refs / {BASELINE_FILES} files "
          f"-- the number must FALL")

    if n_refs > BASELINE_REFS:
        print(f"\n⚠️  ROSE by {n_refs - BASELINE_REFS} against the baseline. A new "
              f"tracked module started reading gitignored data.")

    if not open_files:
        print("\nAll references dispositioned. R11.2a can close.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
