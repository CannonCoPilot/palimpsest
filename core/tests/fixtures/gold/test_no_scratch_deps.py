#!/usr/bin/env python
"""GUARD (R11.2) -- tracked code may not IMPORT code from a gitignored ``.scratch/``.

Why this exists. Until R11.1 the gold verification suite -- three tracked, committed
scripts -- ``sys.path.insert``-ed into ``.scratch/mask-eval`` and imported a harness
that existed on exactly one machine, in a gitignored directory. The suite was
therefore un-runnable on any other checkout, and nothing said so: the import simply
resolved locally and the tests passed. That violates §0.2 rule 6, *"every reading is
addressable and checkable"* -- a verifier only one machine can run is checkable by
nobody -- and it is invisible precisely on the machine where the work is done.

Moving the code was the fix. THIS is what keeps it fixed: without a consumer, the
rule is not a rule (the Gate 0f lesson -- R9 found that no code had ever read a
witness role, so the roles were decoration).

SCOPE, and why it is drawn here. This guard covers **executable dependency**: a
tracked module putting a gitignored directory on ``sys.path`` and importing from it.
That is the R11.1 defect exactly, it is currently at ZERO, and it must stay there.

It does NOT cover string constants naming gitignored **data** paths. Those are a
different question -- a 2 GB ingest cache or a rebuildable sqlite basis-db is
legitimately machine-local -- and there are 71 such references across 38 tracked
files as of 2026-08-14. They are tracked by ``audit_scratch_data_paths.py``, which
REPORTS (exit 1, healthy) a count that must FALL, and are R11.2a in the roadmap.

Filing those under this guard would force one of the two things the project forbids:
bulk-rewriting 39 files nobody has reasoned about, or weakening the check until it
passes. Same reasoning as R10.1's audit/guard split, and the same rule -- a below-
threshold result is never converted into an accepted one.

METHOD. ``sys.path`` mutations are found via ``ast``, so a docstring or comment
mentioning the path cannot trip the check: R9.2c's first version WAS tripped by its
own docstring quoting the glob it had just removed, and *a check a comment can trip
measures vocabulary, not call sites.* A file that will not parse is NOT reported
clean -- it falls back to a raw regex, because an unreadable file must not pass.

Exit 0 = clean. Exit 1 = a tracked module imports gitignored code.

Run: ../ocr-venv/bin/python core/tests/fixtures/gold/test_no_scratch_deps.py
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
PATH_MUTATORS = {"insert", "append", "extend"}


def tracked_python_files() -> list[Path]:
    """Every tracked .py file. Untracked files are out of scope BY DEFINITION --
    the subject of this guard is what a fresh checkout actually receives."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "*.py"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
    return [REPO / p for p in out.split("\0") if p]


def _mentions_scratch(node: ast.AST) -> bool:
    """True if any string constant anywhere inside `node` names a .scratch path."""
    return any(
        isinstance(n, ast.Constant) and isinstance(n.value, str) and SCRATCH.search(n.value)
        for n in ast.walk(node)
    )


def violations(path: Path) -> list[tuple[int, str]]:
    """(lineno, evidence) for each sys.path mutation naming a .scratch path."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if not SCRATCH.search(text):
        return []  # cheap reject; nothing to parse

    try:
        tree = ast.parse(text)
    except SyntaxError:
        # UNPARSEABLE IS NOT CLEAN. Fall back to the blunt instrument, and say so.
        return [
            (i, f"[unparseable file; raw match] {ln.strip()}")
            for i, ln in enumerate(text.splitlines(), 1)
            if SCRATCH.search(ln) and "sys.path" in ln and not ln.lstrip().startswith("#")
        ]

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in PATH_MUTATORS:
            continue
        # ...on sys.path specifically
        tgt = node.func.value
        is_syspath = (
            isinstance(tgt, ast.Attribute)
            and tgt.attr == "path"
            and isinstance(tgt.value, ast.Name)
            and tgt.value.id == "sys"
        )
        if is_syspath and any(_mentions_scratch(a) for a in node.args):
            found.append((node.lineno, f"sys.path.{node.func.attr}(...) names a .scratch path"))
    return found


def main() -> int:
    files = tracked_python_files()
    offenders: dict[str, list[tuple[int, str]]] = {}
    for path in files:
        hits = violations(path)
        if hits:
            offenders[path.relative_to(REPO).as_posix()] = hits

    print(f"scanned {len(files)} tracked .py files for imports out of .scratch/")

    if not offenders:
        print("OK -- no tracked module puts a gitignored .scratch/ path on sys.path")
        print("(data-path references are a separate question: audit_scratch_data_paths.py)")
        return 0

    print(f"\nFAIL -- {len(offenders)} tracked file(s) import gitignored code:")
    for rel, hits in sorted(offenders.items()):
        for lineno, evidence in hits:
            print(f"  {rel}:{lineno}  {evidence}")
    print("\nMove the code into the repo (R11.1). Tracked code that imports from a "
          "gitignored directory is runnable on one machine and checkable by nobody.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
