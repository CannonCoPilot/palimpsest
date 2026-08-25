#!/usr/bin/env python3
"""audit_prereq_ceilings.py -- R10.1: §0.5's prerequisite sizing, given a consumer at last.

Master Plan §0.5, since it was written: *"Every prerequisite carries a stated ceiling and a
pre-registered decision rule before it starts."*  The UNIT became a COMPLEXITY CLASS on 2026-08-17
(hours abolished project-wide); the force of the clause is unchanged.  **No step had ever carried either.**  §0.5 names
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

# R10.3 — hours were abolished as a unit 2026-08-17, so a section now declares a COMPLEXITY CLASS
# instead of an hour ceiling.
#
# ⚠️ WHY THE OLD PATTERN HAD TO GO, AND WHY IT WAS WORSE THAN BROKEN. `hour ceiling` matched the PROSE,
# not the DECLARATION. After the conversion, sections that no longer size anything still carried the
# phrase in their own explanation of the change ("restated 2026-08-17 from a 12h ceiling"), so the audit
# went on counting them as covered. It did not collapse to zero — which would at least have been visible.
# It reported 19 of 55 while the thing it was checking for had been deleted from those very sections:
# a metric passing on the residue of what it used to measure. Same shape as the parity spread that was
# silently restating the best witness's own pass rate (R9.2c-4).
#
# So the declaration is anchored, not merely mentioned: `**Complexity:` or `**Complexity per sub-step**`
# introducing a C1–C4 class. Discussing complexity, or narrating the unit change, does not satisfy it.
CEILING_RE = re.compile(r"\*\*Complexity(?::| per sub-step\*\*)[^\n]*?\bC[1-4]\b", re.I)
RULE_RE = re.compile(r"decision rule", re.I)

# A class declared inside a step's OWN table row, in the house style: `C2 — assembly`, `C4 — open
# problem`. The trailing dash-and-name is required deliberately: a bare `C2` can occur in prose (a
# column label, a citation), whereas the class token followed by its name is the declaration form and
# nothing else in these files is written that way.
ROW_CLASS_RE = re.compile(r"\bC[1-4]\b\s*[—–-]\s*\w")


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


def own_rows(text: str) -> dict[str, str]:
    """Step id -> the text of ITS OWN table row, for steps that have one.

    ⚠️ WHY THIS EXISTS (found 2026-08-17, the same day the string-granularity defect was fixed).
    Resolving a complexity class at SECTION granularity -- "a class stated once covers the steps it
    governs" -- means adding ONE sized step beside unsized ones marks them all covered. R3.6 and R3.7
    were added with classes and coverage jumped 14/56 -> 22/58: six of the eight were unearned, because
    R3.1-R3.5c have no class of their own and never did.

    That is the SAME laundering shape one level down: the earlier defect was a pattern matching prose
    instead of a declaration; this one is a scope wide enough that an unsized step inherits a sibling's
    sizing. A number that rises when nothing was sized is not a coverage number.

    So both are reported, and the STRICT one leads. Section inheritance is still shown, because a class
    genuinely stated once for a whole section is legitimate -- but it must be visible as inheritance
    rather than counted as if each step had been reasoned about.
    """
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"\|\s*(R\d+(?:\.\d+)*[a-z]?(?:-\d+)?)\s*\|", line)
        if m:
            out.setdefault(m.group(1), line)
    return out


def main() -> int:
    text = ROADMAP.read_text()
    steps = open_steps(text)
    if not steps:
        print("FAILED — could not parse the OPEN register block; this audit cannot pass vacuously")
        return 1

    secs = sections(text)
    rows = own_rows(text)
    covered: list[str] = []
    inherited: list[str] = []
    missing: list[tuple[str, str]] = []

    for step in steps:
        body = secs.get(root_of(step), "")
        row = rows.get(step, "")
        has_c = bool(CEILING_RE.search(body))
        has_r = bool(RULE_RE.search(body))
        if has_c and has_r:
            # Strict: the step's OWN row declares the class. Otherwise it is inheriting a sibling's.
            (covered if ROW_CLASS_RE.search(row) else inherited).append(step)
        else:
            lack = "no complexity class and no decision rule" if not (has_c or has_r) else (
                "no complexity class" if not has_c else "no decision rule")
            missing.append((step, lack))

    total = len(steps)
    print(f"§0.5 coverage over the OPEN register — STRICT: {len(covered)}/{total} step(s) declare a "
          f"complexity class in their OWN row, in a section carrying a pre-registered decision rule.")
    print(f"  (+{len(inherited)} inherit a class from their section rather than declaring one; "
          f"shown separately because a step nobody sized is not a step that was reasoned about.)\n")
    if covered:
        print("  covered — own declaration:")
        for s in covered:
            print(f"    ok    {s}")
    if inherited:
        print("\n  INHERITED — the section carries a class, this step does not:")
        for s in inherited:
            print(f"    ~~    {s}")
    print("\n  NOT YET COVERED — each needs a ceiling and a rule written BEFORE work starts:")
    for s, why in missing:
        print(f"    --    {s:10} {why}")

    print()
    if not missing:
        print("R10.1 holds: every OPEN step carries a complexity class and a pre-registered decision "
              "rule.")
        return 0
    print(f"OPEN (R10.1) — {len(missing)} of {total} OPEN steps carry no ceiling. **Exit 1 is the "
          f"healthy state**: §0.5 has had no consumer since it was written, and the remedy is to "
          f"add ceilings section by section as each is next touched, NOT to invent {len(missing)} "
          f"of them now. The number above must RISE; it is not a pass/fail.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
