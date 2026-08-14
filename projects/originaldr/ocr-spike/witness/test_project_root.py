#!/usr/bin/env python
"""GUARD (R9.6 / R11.4) -- the OriginalDR project root is derived once, never restated.

Commit `2633cbb` moved the OCR project out of gitignored scratch into
``projects/originaldr/``. Modules that had written the old root as a literal did not
move with it, and every path below them resolved into a directory that does not
exist. It resolved SILENTLY: readers guarded on ``.exists()`` and skipped, so
``detect_our_ocr`` reported ``{"verses_scored": 0, "error": "no anchor text"}`` for
every book -- a well-formed empty answer standing in for a source never opened.

Measured 2026-08-14, before the fix:
  * ``core/.scratch/originaldr-project`` -- ABSENT ENTIRELY
  * ``projects/originaldr/reconstruction/reads`` -- 10 entries
  * ``projects/originaldr/reconstruction/consensus`` -- 76 entries
  * **20 modules / 33 literals** restated the dead root (R9.6 recorded six)
  * **FOUR** of them ``mkdir(parents=True)`` and WRITE (R9.6 recorded two):
    detect_sources, detect_s_dismas, detect_ocr_consensus, build_consensus

⚠️ R11.4 is why the original count was low. ``purge_empty_ocr.py`` reached the dead
tree by RELATIVE TRAVERSAL (``../../../../../.scratch/...``) rather than by naming the
root, so a sweep written against modules that *restate* the root could not see it.
**A search shaped by the fix's vocabulary finds only the instances that share it.**

This guard checks three things:
  1. no tracked module names the legacy root as a string constant (``ast``, docstrings
     excluded -- a check a comment can trip measures vocabulary, not call sites, R9.2c);
  2. no tracked module reaches it by relative traversal (the R11.4 form);
  3. the legacy tree has not REAPPEARED on disk -- if it has, a writer recreated it and
     every artefact written since is suspect.

Exit 0 = clean. Exit 1 = the root is restated, traversed to, or has come back.

Run: ../ocr-venv/bin/python witness/test_project_root.py
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # HERE=witness; parents = [0]ocr-spike [1]originaldr [2]projects [3]<repo>

LEGACY = REPO / "core" / ".scratch" / "originaldr-project"
LIVE = REPO / "projects" / "originaldr"

# The module that is ALLOWED to name the legacy root: it names it in order to refuse it.
ROOT_MODULE = "core/tests/fixtures/gold/mask_engine/originaldr_reconstruction/project_root.py"
SELF = "projects/originaldr/ocr-spike/witness/test_project_root.py"

LEGACY_LITERAL = re.compile(r"\.scratch/originaldr-project")
# R11.4: three-or-more parent hops followed by a .scratch segment.
TRAVERSAL = re.compile(r"(?:\.\./){3,}[^\"']*\.scratch")


def tracked_py() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z", "*.py"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    return [REPO / p for p in out.split("\0") if p]


def offending_constants(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not (LEGACY_LITERAL.search(text) or TRAVERSAL.search(text)):
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [(i, f"[unparseable] {ln.strip()}")
                for i, ln in enumerate(text.splitlines(), 1)
                if (LEGACY_LITERAL.search(ln) or TRAVERSAL.search(ln))
                and not ln.lstrip().startswith("#")]

    doc_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
               and isinstance(body[0].value.value, str):
                doc_ids.add(id(body[0].value))

    hits = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_ids:
            if LEGACY_LITERAL.search(n.value):
                hits.append((n.lineno, f"restates the legacy root: {n.value!r}"))
            elif TRAVERSAL.search(n.value):
                hits.append((n.lineno, f"reaches .scratch by traversal (R11.4): {n.value!r}"))
    return hits


def main() -> int:
    problems: list[str] = []

    files = tracked_py()
    for path in files:
        rel = path.relative_to(REPO).as_posix()
        if rel in (ROOT_MODULE, SELF):
            continue
        for lineno, why in offending_constants(path):
            problems.append(f"  {rel}:{lineno}  {why}")

    print(f"scanned {len(files)} tracked .py files")

    if LEGACY.exists():
        problems.append(
            f"  THE LEGACY TREE HAS REAPPEARED: {LEGACY}\n"
            f"    Nothing reads it. It is created only by a module still restating the old\n"
            f"    root and calling mkdir(parents=True). Find that writer before trusting any\n"
            f"    artefact written since.")
    else:
        print(f"legacy root absent, as required: {LEGACY}")

    if not LIVE.is_dir():
        problems.append(f"  the LIVE root is missing: {LIVE}")
    else:
        print(f"live root present: {LIVE}")

    if problems:
        print(f"\nFAIL -- {len(problems)} problem(s):")
        for p in problems:
            print(p)
        print("\nImport the root from project_root.py; do not restate it and do not "
              "traverse to it. One derived root (R9.6).")
        return 1

    print("OK -- one derived root; no module restates or traverses to the legacy tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
