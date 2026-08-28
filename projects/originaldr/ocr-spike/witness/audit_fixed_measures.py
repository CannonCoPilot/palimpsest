#!/usr/bin/env python3
"""R14.11 -- EVERY FIXED NUMBER IN THE AGENT, AND WHETHER THE ANSWER DEPENDS ON IT.

Sir's standing requirement, 2026-08-27: *"I want to make sure that nothing on the page as assumed by
or produced by the model is a predetermined fixed measure."*

§3.0 permits a fitted constant to INITIALISE or CLAMP and forbids it to DECIDE. That permission has
been asserted in comments all over `visual_agent.py` and NEVER MEASURED. This audit measures it.

THE INSTRUMENT. For each constant, sweep it across a plausible range, re-run the whole agent at each
value, and compare the resulting label vector -- every box on every leaf -- against the shipped one.
Then report:

  SLACK   the widest contiguous band around the shipped value over which NOT ONE LABEL CHANGES.
  VERDICT  GUARD    wide slack -- the value sits in an empty band; any value in it gives one answer.
           DECIDING zero or near-zero slack -- the agent's output turns on this number, so it is a
                    threshold wearing a cue's clothes and MUST be derived from the page or retired.

⚠️ THIS IS THE HONEST FORM OF THE CLAIM `visual_agent.py` MAKES ABOUT ITSELF. A comment saying "this
decides nothing" is a hypothesis; a sweep showing the label vector is invariant across a band is a
measurement. Where the two disagree, the sweep wins and the comment is a defect.

⚠️ SLACK IS NOT VIRTUE. A wide empty band on TWENTY LEAVES OF ONE WITNESS is evidence about this
window and nothing more -- a guard can sit in an empty band here and decide real boxes on a leaf
this window does not contain. The audit reports the band; it does not certify the constant.

    ../ocr-venv/bin/python witness/audit_fixed_measures.py

Exits 1 while ANY constant is DECIDING -- the healthy state is that every remaining fixed number is
a guard with measured slack, and that is not yet true.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

import visual_agent as VA          # noqa: E402

# name -> (lo, hi, steps). Ranges are the PLAUSIBLE span of the quantity, chosen from what the thing
# means, not from where the answer is stable -- picking the range after seeing the sweep would make
# the slack a description of the range.
SWEEP = {
    "SMALL_AREA":         (0.005, 0.30, 60),
    "OUTSIDE_FRAC":       (0.05, 0.95, 46),
    "THIN_MARGIN":        (0.005, 0.30, 60),
    "AR_ITALIC_MAJORITY": (0.05, 0.95, 46),
    "AR_MEASURE_SPAN":    (0.05, 0.95, 46),
    "PN_MAX_AREA":        (0.0002, 0.010, 50),
    "PN_EDGE":            (0.02, 0.48, 47),
    "COLUMN_OVERLAP":     (0.05, 0.95, 46),
    "FOOT_CATCHWORD_REL": (0.10, 0.90, 41),
    # R14.11 -- replaced `CENTRED_LO/HI`, whose slack this audit measured at 0.00x. The cue itself
    # is now the parameter-free predicate "the measure's centre-line falls inside the box"
    # (`visual_agent.centre_offset`), and this is only the ABSTENTION tolerance around it, in units
    # of a box's own width. Range is the plausible span of such a tolerance: below 0.005 it is finer
    # than any edge this detector resolves, and at 0.5 it would swallow the entire predicate.
    "CENTRED_ABSTAIN":    (0.005, 0.40, 40),
}
# Pairs swept together because they are one symmetric band, not two numbers.
BANDS = {
    "HEADING_LO/HI":  ("HEADING_LO", "HEADING_HI", 0.02, 0.48, 47),
}
INT_SWEEP = {"AR_MIN_SEGMENTS": (1, 8)}


def vector():
    """The agent's whole answer: (leaf, box index) -> label, for every box on every leaf."""
    return tuple(b.label for lf in VA.load_leaves() for b in lf.boxes)


def _restore(names, vals):
    for n, v in zip(names, vals):
        setattr(VA, n, v)


def slack_of(names, shipped, values):
    """Sweep `values`; -> (n_changed, lo_edge, hi_edge) of the invariant band around `shipped`."""
    base = vector()
    ok = []
    for v in values:
        _restore(names, v if isinstance(v, tuple) else (v,))
        try:
            ok.append((v, vector() == base))
        except Exception:                                  # noqa: BLE001
            ok.append((v, False))
    _restore(names, shipped)
    # walk out from the shipped value in both directions while the answer holds
    scal = [(x[0] if isinstance(x[0], tuple) else x[0], x[1]) for x in ok]
    keys = [k if not isinstance(k, tuple) else k[0] for k, _ in scal]
    hold = [h for _, h in scal]
    s0 = shipped[0]
    i = min(range(len(keys)), key=lambda k: abs(keys[k] - s0))
    lo = hi = i
    while lo > 0 and hold[lo - 1]:
        lo -= 1
    while hi < len(keys) - 1 and hold[hi + 1]:
        hi += 1
    return sum(1 for h in hold if not h), keys[lo], keys[hi]


def main() -> int:
    print("R14.11 — EVERY FIXED NUMBER IN THE AGENT, SWEPT\n")
    print(f"{VA.WITNESS} leaves {VA.LEAF_LO}-{VA.LEAF_HI - 1}; the answer compared is the FULL label")
    print("vector — every box on every leaf. A constant is a GUARD only if a band around its shipped")
    print("value leaves that vector untouched.\n")

    rows = []
    hdr = (f"{'constant':>20} {'shipped':>10} {'invariant band':>22} {'rel. slack':>11}  verdict")
    print(hdr); print("-" * (len(hdr) + 8))

    for name, (lo, hi, n) in SWEEP.items():
        shipped = (getattr(VA, name),)
        vals = [lo + (hi - lo) * k / (n - 1) for k in range(n)]
        _, blo, bhi = slack_of((name,), shipped, vals)
        rel = (bhi - blo) / max(1e-12, shipped[0])
        rows.append((name, shipped[0], blo, bhi, rel))

    for label, (n1, n2, lo, hi, n) in BANDS.items():
        shipped = (getattr(VA, n1), getattr(VA, n2))
        vals = [(lo + (hi - lo) * k / (n - 1), 1.0 - (lo + (hi - lo) * k / (n - 1)))
                for k in range(n)]
        _, blo, bhi = slack_of((n1, n2), shipped, vals)
        rel = (bhi - blo) / max(1e-12, shipped[0])
        rows.append((label, shipped[0], blo, bhi, rel))

    for name, (lo, hi) in INT_SWEEP.items():
        shipped = (getattr(VA, name),)
        vals = list(range(lo, hi + 1))
        _, blo, bhi = slack_of((name,), shipped, vals)
        rel = (bhi - blo) / max(1e-12, shipped[0])
        rows.append((name, shipped[0], blo, bhi, rel))

    deciding = []
    for name, ship, blo, bhi, rel in rows:
        guard = rel >= 0.25
        verdict = "GUARD" if guard else "🔴 DECIDING"
        if not guard:
            deciding.append(name)
        print(f"{name:>20} {ship:>10.4f} {f'{blo:.4f} … {bhi:.4f}':>22} "
              f"{rel:>10.2f}x  {verdict}")

    print(f"\n```\nfixed measures that DECIDE -> {len(deciding)}/{len(rows)}\n```")
    print("\nA constant is called DECIDING when the band over which the agent's answer is")
    print("unchanged is narrower than a quarter of the value itself — i.e. a modest change to")
    print("the number changes what the page is said to contain.\n")
    if deciding:
        print("🔴 DECIDING, and each must be DERIVED FROM THE PAGE or retired:")
        for d in deciding:
            print(f"    · {d}")
        print("\n⚠️ These are the numbers the agent's own docstring claims it does not have. The")
        print("   claim is measured here for the first time and it does not hold.")
    else:
        print("✅ every remaining fixed number sits in a measured empty band on this window.")

    print("\n⚠️ SLACK IS EVIDENCE ABOUT THIS WINDOW, NOT A CERTIFICATE. Twenty leaves of one")
    print("   witness; a constant with an empty band here can still decide real boxes on a leaf")
    print("   this window does not contain. R14.11 tracks the derivation work, not this audit.")
    return 1 if deciding else 0


if __name__ == "__main__":
    raise SystemExit(main())
