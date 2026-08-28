#!/usr/bin/env python3
"""audit_gate_register.py -- R15.1: the gate crosswalk, as an instrument rather than a paragraph.

On 2026-08-25 a review of every Masterplan and Roadmap section found three defects of ONE shape:

  1. TWO GATE REGISTERS NAMED THE SAME CHECKS DIFFERENTLY. §3.2/§3.0 publish the geometry gate as
     "Gate 9" with clauses 9.1-9.8; §7.8's table publishes the same checks as rows 10a-10f. The
     document had ALREADY contradicted itself -- §2 cited "Gate 10c's threshold" for the check
     §3.2b calls 9.5.
  2. THREE CLAUSES HAD NO ROW AT ALL. Gate 9.6 (abstention), 9.7 (relations) and 9.8 (the loop)
     were written into §3.2 and existed nowhere in §7.8 -- so by §7.8's OWN document-level
     invariant ("no step enters the build order until its row carries metric · threshold · named
     set · n · pre-registered effect size") they had not entered the build order.
  3. THE ROADMAP CITED §7.8 ZERO TIMES. The canonical gate register was invisible to the work plan,
     and the consequence was concrete: **Gate 11 -- G1 recognition, the gate for the character
     recognition model -- had NO Roadmap step of any kind**, while "what progress on the
     recogniser?" was a live question being answered from validation figures §7.8 states in terms
     are "neither Gate 11 measurements nor layout measurements".

⚠️ ALL THREE WERE FIXED BY HAND THAT DAY, AND THAT IS EXACTLY WHY THIS FILE EXISTS. R15's
pre-registered decision rule: *a register defect is closed only when an EXECUTABLE check would have
caught it; a crosswalk written in prose and maintained by hand is the defect restated, not the
remedy.* This project's signature defect -- now at 16 recorded instances -- is a correct rule that
nothing reads. §7.8 was never wrong. It was simply never consulted.

WHAT IT CHECKS
  (a) every geometry clause (`Gate 9.N`, `Gate 4.1`) cited in the Masterplan resolves through the
      §7.8 crosswalk to a canonical row;
  (b) every §7.8 row names the Roadmap step that discharges it, or is explicitly NOT YET PLANNED --
      and a named step must actually EXIST in the Roadmap;
  (c) every gate id cited in the Roadmap is defined by §7.8;
  (d) the Roadmap cites §7.8 at all.

EXIT CODES
  0  nothing outstanding -- not expected for a long time, and not the healthy state today
  1  outstanding NOT YET PLANNED rows, or gate ids cited outside the canonical register.
     ⚠️ THIS IS THE HEALTHY STATE, as with `audit_prereq_ceilings`. Exit 1 keeps the pressure
     visible. R15 MAY NOT close a finding by deleting the row that carries it: an unplanned row is
     closed by PLANNING it.
  2  a HARD defect: a `discharged by` entry naming a step the Roadmap does not define, or a
     Masterplan clause with no canonical row. These are not "pressure"; they are the register
     lying, and they must be fixed rather than tolerated.

    ../ocr-venv/bin/python witness/audit_gate_register.py
    ../ocr-venv/bin/python witness/audit_gate_register.py --selftest   # R15.1's acceptance
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKE = HERE.parent
MASTERPLAN = SPIKE / "OCR-MASTERPLAN.md"
ROADMAP = SPIKE / "OCR-ROADMAP.md"

UNPLANNED = "NOT YET PLANNED"
_MALFORMED = "<MALFORMED ROW: {n} cells, expected 6>"

# A §7.8 row id as the table writes it: 0a, 1, 10a, 14. Bold-delimited in the first cell.
ROW_RE = re.compile(r"^\|\s*\*\*([0-9]+[a-f]?)\*\*\s*\|(.*)$")
# The crosswalk's clause cell: `Gate 9.2 · 9.3 · 9.4` or `Gate 4.1` (§4.1).
CROSSWALK_RE = re.compile(r"^\|[^|]*\|\s*\*{0,2}Gate\s+([0-9.]+(?:\s*·\s*[0-9.]+)*)\*{0,2}[^|]*\|\s*\*{0,2}([0-9]+[a-f]?)\*{0,2}")
# ⚠️ A BARE FAMILY ID IS NOT A CHECK. `Gate 0` and `Gate 9` name the gate, not a clause of it, and
# demanding a §7.8 row for a family would manufacture noise that then gets suppressed by relaxing
# the audit — which is how a check stops checking. The exclusion is DECLARED here rather than
# absorbed silently into a regex, because an undeclared exclusion is the bounded search that
# reports itself as exhaustive (R14.6a).
GATE_FAMILIES = {"0", "9"}
# A clause citation anywhere in the Masterplan. Bare `Gate 9` (the family) is deliberately NOT a
# clause -- it names the gate, not a check, and demanding a row for it would be noise.
CLAUSE_CITE_RE = re.compile(r"\bGate\s+(\d+\.\d+)\b")
# A gate citation in the Roadmap: `Gate 0b`, `Gate 9.7`, `Gate 10b`, `Gate 11`.
GATE_CITE_RE = re.compile(r"\bGate\s+(\d+(?:\.\d+)?[a-f]?)\b")
# A Roadmap step id, in the two places the Roadmap DEFINES one: a `## RN — ` / `### RN.x — `
# section heading, or the leading cell of a step table row.
STEP_DEF_RE = re.compile(r"^#{2,4}\s+.*?\b(R\d+(?:\.\d+)*[a-z]?(?:-\d+)?)\b", re.M)
STEP_ROW_RE = re.compile(r"^\|\s*\*{0,2}(R\d+(?:\.\d+)*[a-z]?(?:-\d+)?)\*{0,2}\s*\|", re.M)
STEP_TOKEN_RE = re.compile(r"\bR\d+(?:\.\d+)*[a-z]?(?:-\d+)?\b")


def parse_gate_rows(masterplan: str) -> dict[str, str]:
    """§7.8's table -> {row id: the `discharged by` cell, verbatim}.

    ⚠️ Bounded on purpose, and the bound is STATED: only the block between `### 7.8 Gates` and the
    next `## ` heading is read. §7.8 is declared canonical, so a gate table anywhere else is not a
    rival register to be merged -- it is the defect this audit exists to find.
    """
    lines = masterplan.split("\n")
    try:
        i0 = next(i for i, l in enumerate(lines) if l.startswith("### 7.8 Gates"))
    except StopIteration:
        return {}
    i1 = next((i for i, l in enumerate(lines) if i > i0 and l.startswith("## ")), len(lines))
    rows: dict[str, str] = {}
    for l in lines[i0:i1]:
        m = ROW_RE.match(l)
        if not m:
            continue
        # The crosswalk sits in the same block and its rows are `| check | Gate x | **10a** |`,
        # which ROW_RE cannot match, because its first cell is prose rather than a bold row id.
        #
        # ⚠️ POSITIONAL, NOT "THE LAST NON-EMPTY CELL", AND THE DIFFERENCE IS THE WHOLE POINT.
        # Taking the last non-empty cell silently returns the `n` cell when `discharged by` is
        # blank -- so a row with NO owner would be read as owned by whatever its n cell happens to
        # say, and the audit built to find unowned rows would hide one. That is this project's
        # signature defect committed by its own remedy. The arity is therefore checked and a
        # malformed row is REPORTED, never guessed at.
        cells = [c.strip() for c in m.group(2).split("|")]
        while cells and not cells[-1]:
            cells.pop()                      # trailing empty from the row's closing pipe
        if len(cells) != 6:                  # step · metric · threshold · set · n · discharged by
            rows[m.group(1)] = _MALFORMED.format(n=len(cells))
            continue
        rows[m.group(1)] = cells[5].replace("*", "").strip()
    return rows


def parse_crosswalk(masterplan: str) -> dict[str, str]:
    """The §7.8 crosswalk -> {clause id: canonical row id}. `Gate 9.2 · 9.3 · 9.4` fans out."""
    out: dict[str, str] = {}
    for line in masterplan.split("\n"):
        m = CROSSWALK_RE.match(line)
        if not m:
            continue
        for clause in re.split(r"\s*·\s*", m.group(1)):
            clause = clause.strip()
            if not clause:
                continue
            # `9.2 · 9.3` -- the trailing ids inherit the leading id's family.
            if "." not in clause:
                continue
            out[clause] = m.group(2)
    return out


def parse_roadmap_steps(roadmap: str) -> set[str]:
    return set(STEP_DEF_RE.findall(roadmap)) | set(STEP_ROW_RE.findall(roadmap))


def audit(masterplan: str, roadmap: str) -> tuple[list[str], list[str], dict]:
    """-> (hard defects, outstanding items, counts). Pure, so --selftest can drive it."""
    hard: list[str] = []
    soft: list[str] = []

    rows = parse_gate_rows(masterplan)
    crosswalk = parse_crosswalk(masterplan)
    steps = parse_roadmap_steps(roadmap)

    # (a) every clause cited in the Masterplan resolves to a canonical row.
    for clause in sorted(set(CLAUSE_CITE_RE.findall(masterplan))):
        row = crosswalk.get(clause)
        if row is None:
            hard.append(f"(a) Masterplan cites `Gate {clause}` and the §7.8 crosswalk gives it NO ROW "
                        f"— by §7.8's own invariant it has not entered the build order")
        elif row not in rows:
            hard.append(f"(a) crosswalk maps `Gate {clause}` -> row {row}, and §7.8 has no such row")

    # (b) every row names a step that exists, or says NOT YET PLANNED.
    planned = 0
    for rid, cell in sorted(rows.items()):
        if not cell:
            hard.append(f"(b) §7.8 row {rid} has an EMPTY `discharged by` cell — a silent absence is "
                        f"the state this column replaces; write the step or write {UNPLANNED}")
            continue
        if cell.startswith("<MALFORMED"):
            hard.append(f"(b) §7.8 row {rid} {cell} — the `discharged by` column is read POSITIONALLY "
                        f"on purpose, so a row that does not carry it is reported rather than guessed")
            continue
        if cell == UNPLANNED:
            soft.append(f"(b) §7.8 row {rid} is {UNPLANNED}")
            continue
        named = STEP_TOKEN_RE.findall(cell)
        if not named:
            hard.append(f"(b) §7.8 row {rid} `discharged by` = {cell!r}, which names no step id")
            continue
        missing = [s for s in named if s not in steps]
        if missing:
            hard.append(f"(b) §7.8 row {rid} is discharged by {', '.join(missing)}, "
                        f"which the Roadmap does not define")
        else:
            planned += 1

    # (c) every gate the Roadmap cites is defined by §7.8 (directly, or as a crosswalked alias).
    for gid in sorted(set(GATE_CITE_RE.findall(roadmap))):
        if gid in rows or gid in crosswalk or gid in GATE_FAMILIES:
            continue
        soft.append(f"(c) the Roadmap cites `Gate {gid}` and §7.8 defines no such row — it is being "
                    f"tracked outside the canonical register")

    # (d) the Roadmap must read the register at all. This is finding 3, made permanent.
    n78 = len(re.findall(r"§7\.8", roadmap))
    if n78 == 0:
        hard.append("(d) the Roadmap cites §7.8 ZERO times — the canonical gate register is invisible "
                    "to the work plan, which is exactly how Gate 11 came to have no step")

    return hard, soft, {"rows": len(rows), "planned": planned,
                        "unplanned": sum(1 for c in rows.values() if c == UNPLANNED),
                        "clauses": len(crosswalk), "steps": len(steps), "cites_7_8": n78}


# --------------------------------------------------------------------------- selftest
# R15.1's acceptance: *the audit reproduces today's three findings from the documents alone, and
# would have failed before this session's edits.* The second half cannot be shown against the live
# files, because the live files are already fixed -- so the PRE-FIX state is reconstructed here and
# the audit is run against it. ⚠️ An audit that has never rejected anything is not known to work;
# this project holds every guard to a proven negative and holds this one to the same bar.

_PRE_FIX_MASTERPLAN = """
### 7.8 Gates

| # | step | metric | threshold | set | n |
|---|---|---|---|---|---|
| **10a** | G1 archetype classification | acc | >=0.95 | GOLD-LAYOUT | 125 |
| **10b** | G1 geometry — regions | recall | >=0.85 | GOLD-LAYOUT | 125 |
| **10c** | G1 geometry — slant | slope err | pre-registered | GOLD-LAYOUT | pre-registered |
| **11** | G1 recognition | CER | <=1.0% | GOLD-TEXT | bootstrap |

| the check | §3.2's clause | canonical row |
|---|---|---|
| archetype classification | Gate 9.1 | **10a** |
| marginalia recall | Gate 9.2 · 9.3 · 9.4 | **10b** |
| slant | Gate 9.5 | **10c** |

## 8. THE BOARD

Elsewhere: S4 carries **Gate 9.6 abstention**, S5 carries **Gate 9.7**, S8 carries **Gate 9.8**.
"""

_PRE_FIX_ROADMAP = """
## R13 — The trained recogniser is not in the path that needs it
| # | step | deliverable | acceptance |
| R13.1 | wire it | ... | ... |
| R13.2 | measure it | ... | ... |
"""


def selftest() -> int:
    hard, soft, counts = audit(_PRE_FIX_MASTERPLAN, _PRE_FIX_ROADMAP)
    blob = "\n".join(hard + soft)
    checks = [
        ("finding 2 — Gate 9.6 has no row", "Gate 9.6" in blob and "NO ROW" in blob),
        ("finding 2 — Gate 9.7 has no row", "Gate 9.7" in blob),
        ("finding 2 — Gate 9.8 has no row", "Gate 9.8" in blob),
        ("finding 3 — the Roadmap cites §7.8 zero times", any("(d)" in h for h in hard)),
        # Pre-fix the table had NO `discharged by` column at all, so row 11 is reported MALFORMED
        # rather than unplanned — which is the more precise diagnosis and the one the positional
        # read exists to give. `Gate 11 has no Roadmap step` was finding 3's concrete consequence.
        ("finding 3 — Gate 11's row cannot name a step (no such column existed)",
         any("row 11" in s for s in soft) or any("row 11" in h for h in hard)),
        ("finding 1 — two registers: §3.2 clauses are aliases, and every alias must resolve",
         counts["clauses"] == 5),
    ]
    ok = True
    print("R15.1 SELFTEST — the pre-fix documents, replayed\n")
    for name, passed in checks:
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        ok &= passed
    print(f"\n  pre-fix hard defects: {len(hard)}   outstanding: {len(soft)}")
    for h in hard:
        print(f"    HARD  {h}")
    print("\nSELFTEST " + ("PASSED — the audit would have caught all three." if ok else "FAILED."))
    return 0 if ok else 2


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    masterplan = MASTERPLAN.read_text()
    roadmap = ROADMAP.read_text()
    hard, soft, c = audit(masterplan, roadmap)

    print("R15.1 — GATE REGISTER CROSSWALK AUDIT")
    print(f"  §7.8 canonical rows ........ {c['rows']}")
    print(f"  crosswalked §3.2 clauses ... {c['clauses']}")
    print(f"  Roadmap step ids ........... {c['steps']}")
    print(f"  Roadmap cites §7.8 ......... {c['cites_7_8']} time(s)")
    print(f"  rows DISCHARGED BY a step .. {c['planned']}/{c['rows']}")
    print(f"  rows {UNPLANNED} ...... {c['unplanned']}/{c['rows']}\n")

    if hard:
        print(f"🔴 {len(hard)} HARD DEFECT(S) — the register is lying; fix, do not tolerate:")
        for h in hard:
            print(f"    {h}")
        print()
    if soft:
        print(f"⚠️  {len(soft)} OUTSTANDING — exit 1 is the HEALTHY state while these stand:")
        for s in soft:
            print(f"    {s}")
        print()
    print("⚠️ R15 MAY NOT close a finding by deleting the row that carries it. An unplanned row is\n"
          "   closed by PLANNING it; a gate tracked outside §7.8 is closed by giving it a row.")

    if hard:
        return 2
    return 1 if soft else 0


if __name__ == "__main__":
    raise SystemExit(main())
