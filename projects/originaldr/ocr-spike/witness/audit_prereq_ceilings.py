#!/usr/bin/env python3
"""audit_prereq_ceilings.py -- R10.1: §0.5's hour ceilings, given a consumer at last.

Master Plan §0.5, since it was written: *"Every prerequisite carries a stated hour ceiling and a
pre-registered decision rule before it starts."*  **No step had ever carried either.**  §0.5 names
**unstartability** as forbidden precisely because it *"produces the same observable outcome as
preserving the status quo"* -- and R2 and R3, on which Gate 0b, Gate 0c and therefore all
transcription depend, stood at "NEXT, nothing built" for the life of the project.  That is the
named failure mode sitting in the roadmap, uncaught, because the rule forbidding it had no reader.
Third instance in one review of a rule that was correct and unwired (Gate 0f, Gate 0d, this).

⚠️ **THIS IS AN AUDIT, NOT A GUARD, AND THE FILING IS DELIBERATE.**  It exits **1** while any OPEN
step lacks a ceiling, and today that is most of them.  Filed as a guard it would force one of the
two things this project forbids by name: bulk-inventing ceilings nobody reasoned about, or
weakening the check until it passes.  Coverage is therefore reported as a **fraction that must
rise**, and a rising fraction is the only evidence accepted that the rule is being obeyed.

Reaching a ceiling **ALERTS that the approach needs redesign**; it never closes a step and never
lowers a bar (§0.5, and the No Silent Degradation rule the whole corpus is held to).

Exit 0 only when every OPEN step carries both. Exit 1 listing the ones that do not.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent
ROADMAP = SPIKE / "OCR-ROADMAP.md"

# A step id as the register writes it: R2.1, R7.5a-2, R9.6a, R10.1.
STEP_RE = re.compile(r"\bR\d+(?:\.\d+)*[a-z]?(?:-\d+)?\b")
OPEN_BLOCK = re.compile(r"\*\*OPEN\*\*\s*—(.+?)\n\n", re.S)
SECTION_RE = re.compile(r"^## (R\d+(?:\.\d+)?)\s+—\s+(.+)$", re.M)

CEILING_RE = re.compile(r"hour ceiling", re.I)
RULE_RE = re.compile(r"decision rule", re.I)


def open_steps(text: str) -> list[str]:
    m = OPEN_BLOCK.search(text)
    if not m:
        return []
    # De-duplicate while preserving order; the register repeats a few ids in prose asides.
    seen, out = set(), []
    for s in STEP_RE.findall(m.group(1)):
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def sections(text: str) -> dict[str, str]:
    """Section id -> its body, so a ceiling stated once covers the steps it governs."""
    marks = [(m.group(1), m.start()) for m in SECTION_RE.finditer(text)]
    out: dict[str, str] = {}
    for i, (sid, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        out[sid] = text[start:end]
    return out


def root_of(step: str) -> str:
    """`R7.5a-2` -> `R7`; the section that would carry the ceiling."""
    return re.match(r"R\d+", step).group(0)  # type: ignore[union-attr]


def main() -> int:
    text = ROADMAP.read_text()
    steps = open_steps(text)
    if not steps:
        print("FAILED — could not parse the OPEN register block; this audit cannot pass vacuously")
        return 1

    secs = sections(text)
    covered: list[str] = []
    missing: list[tuple[str, str]] = []

    for step in steps:
        body = secs.get(root_of(step), "")
        has_c = bool(CEILING_RE.search(body))
        has_r = bool(RULE_RE.search(body))
        if has_c and has_r:
            covered.append(step)
        else:
            lack = "no ceiling and no decision rule" if not (has_c or has_r) else (
                "no hour ceiling" if not has_c else "no decision rule")
            missing.append((step, lack))

    total = len(steps)
    print(f"§0.5 coverage over the OPEN register: {len(covered)}/{total} step(s) sit in a section "
          f"carrying both an hour ceiling and a pre-registered decision rule.\n")
    if covered:
        print("  covered:")
        for s in covered:
            print(f"    ok    {s}")
    print("\n  NOT YET COVERED — each needs a ceiling and a rule written BEFORE work starts:")
    for s, why in missing:
        print(f"    --    {s:10} {why}")

    print()
    if not missing:
        print("R10.1 holds: every OPEN step carries an hour ceiling and a pre-registered decision "
              "rule.")
        return 0
    print(f"OPEN (R10.1) — {len(missing)} of {total} OPEN steps carry no ceiling. **Exit 1 is the "
          f"healthy state**: §0.5 has had no consumer since it was written, and the remedy is to "
          f"add ceilings section by section as each is next touched, NOT to invent {len(missing)} "
          f"of them now. The number above must RISE; it is not a pass/fail.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
