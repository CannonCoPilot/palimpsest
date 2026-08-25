"""GUARD -- a step cannot be DONE in its row and OPEN in the register. Exit 0 healthy, 1 on conflict.

⚠️ WHY, MEASURED 2026-08-17. R2.1g and R2.1i were marked done by STRIKING them in the OPEN register
(`~~R2.1g~~ **DONE**`). `audit_prereq_ceilings.STEP_RE` matches the id INSIDE the strikethrough, so
both were still counted OPEN and the register over-reported for two whole steps. I then quoted the
resulting totals ("59 -> 60 -> 61") as if they described the work -- a number reported without
confirming it could move, which is the habit this project has already paid for twice.

⚠️ STRIKETHROUGH IS NOT REMOVAL. A closed step must be REMOVED from the register line, exactly as
R4.6 was. This is the same class of inconsistency R4.6 hit ("closed in its row but still sitting in
the OPEN register -- that inconsistency is exactly what the register exists to prevent"), and the
lesson there was recorded but not ENFORCED, so it recurred. Enforced now.
"""

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import audit_prereq_ceilings as A

DONE_MARKS = ("**DONE**", "CLOSED", "DISSOLVED")


def main() -> int:
    text = A.ROADMAP.read_text()
    m = A.OPEN_BLOCK.search(text)
    if not m:
        print("🔴 no OPEN register block found")
        return 1
    register = m.group(1)

    bad = []
    if "~~" in register:
        for s in re.findall(r"~~\s*(R\d+(?:\.\d+)*[a-z]?)\s*~~", register):
            bad.append((s, "STRUCK inside the OPEN register -- strikethrough is not removal; "
                           "delete the id from the line"))

    rows = A.own_rows(text)
    for step in A.open_steps(text):
        row = rows.get(step, "")
        for mark in DONE_MARKS:
            if mark in row and not row.lstrip("| ").startswith(step + " | 🔴"):
                bad.append((step, f"row carries {mark!r} but the step is still in the OPEN register"))
                break

    print("register consistency -- a step marked done must not remain OPEN\n")
    print(f"  OPEN register holds {len(A.open_steps(text))} step(s)")
    if not bad:
        print("\n✅ no step is both closed in its row and open in the register")
        return 0
    print(f"\n🔴 {len(bad)} conflict(s):")
    for s, why in bad:
        print(f"    {s:8} {why}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
