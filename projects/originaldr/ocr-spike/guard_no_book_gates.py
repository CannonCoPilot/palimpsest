#!/usr/bin/env python3
"""guard_no_book_gates.py -- anti-drift guard for the OriginalDR QC contract (Sir 2026-07-08).

Fails (exit 1) if any BOOK-LEVEL pass/drop gate reappears in the live locate/consensus pipeline.
The QC contract moved ALL gating to the locus level (per-verse ATTEST_THRESHOLD + per-chapter/element
char-identity in qc_audit); no book may be accepted or dropped by a coverage / chapter-fraction
heuristic. This encodes plan Definition-of-Done "no book-level pass/drop survives (grep the removed
gates)" as an executable check so the four extirpated gates cannot silently creep back.

Checks (AST-based, so comments and string literals are ignored -- only real code counts):
  1. None of the four removed gate constants is (re)defined or referenced anywhere in code:
       COVER_FLOOR, NOISE_FRACTION, BOOK_FLOOR, BOOK_ALIAS_FLOOR
  2. book_coverage(...) is never used inside a branch test or comparison. Mid-chapter book coverage
     may be RECORDED (assigned into an output record) but must NEVER gate control flow.

Scope (stated honestly, no silent caps): this catches reintroduction of the *named* gates and of
coverage-branching. It does NOT prove the absence of an arbitrarily-renamed new heuristic -- that
remains the job of code review and the Phase-2 pilot audit. consensus_spike.py is intentionally NOT
scanned: it is dead (no importers) and banner-marked SUPERSEDED.

Run:  core/.venv/bin/python guard_no_book_gates.py   # exit 0 = clean, 1 = a book gate is back
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/"
             "mask_engine/originaldr_reconstruction")

LIVE_FILES = [
    HERE / "consensus_v2.py",
    HERE / "build_tome_map.py",
    RECON / "detect_our_ocr.py",
]

FORBIDDEN = {"COVER_FLOOR", "NOISE_FRACTION", "BOOK_FLOOR", "BOOK_ALIAS_FLOOR"}
COVERAGE_FN = "book_coverage"


def _calls_book_coverage(node: ast.AST) -> bool:
    """True if the subtree contains a call to book_coverage() (as name or attribute)."""
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
            if name == COVERAGE_FN:
                return True
    return False


def check_file(path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN:
            violations.append(
                f"{path.name}:{node.lineno}: references removed book-gate constant {node.id!r}")
        elif isinstance(node, ast.If) and _calls_book_coverage(node.test):
            violations.append(
                f"{path.name}:{node.lineno}: book_coverage() used in an if-test (book-level gate)")
        elif isinstance(node, ast.Compare) and _calls_book_coverage(node):
            violations.append(
                f"{path.name}:{node.lineno}: book_coverage() used in a comparison (book-level gate)")
    return violations


def main() -> int:
    all_v: list[str] = []
    missing: list[str] = []
    for p in LIVE_FILES:
        if not p.exists():
            missing.append(str(p))
            continue
        all_v.extend(check_file(p))

    if missing:
        print("ERROR: live file(s) missing -- guard cannot verify:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 2
    if all_v:
        print("FAIL: book-level gate(s) detected -- the QC contract forbids book-level pass/drop:")
        for v in all_v:
            print(f"  - {v}")
        print("\nGating must live at the locus level: per-verse ATTEST_THRESHOLD (detect/consensus) "
              "+ per-chapter/element char-identity in qc_audit. book_coverage() may be recorded, "
              "never branched on.")
        return 1
    print(f"PASS: no book-level gates across {len(LIVE_FILES)} live files "
          f"(COVER_FLOOR / NOISE_FRACTION / BOOK_FLOOR / BOOK_ALIAS_FLOOR extirpated; "
          f"book_coverage() recorded-only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
