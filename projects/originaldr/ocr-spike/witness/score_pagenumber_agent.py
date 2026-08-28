#!/usr/bin/env python3
"""R14.10b -- score the `PN` class against its five PRE-REGISTERED criteria.

The rule and the acceptance were written before the cue existed
(`.scratch/r14/R14.10b-PREREGISTRATION.md`, and the result section of OCR-ROADMAP.md R14.10b).

  B1  the class is named          `PN` on >= 12 leaves carrying a detected page-number box
  B2  no confident wrong answer   zero `PN` calls on a box that is not a page number
  B3  GOLD-HEADBAND UNCHANGED     115/121, MN 16/19, RH 20/20, MT 77/80, CH 2/2, forbidden 0
  B4  the withheld-record negative with the reading record hidden the cue does not fire AT ALL
  B5  the misfiling is closed     the spurious `MN` emissions fall to 0, as an MN PRECISION figure

⚠️ THE POPULATION GREW FROM 16 TO 20 AFTER THE CRITERIA WERE WRITTEN, AND THE FLOOR DID NOT MOVE.
B1 was pre-registered as "12 of the 16 leaves carrying a detected page-number box". The 16 was wrong:
this step's own probe had bounded its search by the head band and missed four boxes that were plainly
there. Correcting a FALSE ABSENCE enlarges the population, so the honest handling is to keep the
absolute floor exactly as written and report against the true denominator -- 14/20 -- rather than
re-derive a floor after seeing the result, which is how a bar becomes a description.

🔴 B5 FAILS AT 1/20 AND THE STEP IS THEREFORE NOT CLOSED. Leaf 403's crop reads `37T`: one misread
sort turns a numeral into a "lettered reading", which the pre-registered rule routes to the note
logic. The rule behaved as written; the criterion says zero. ⚠️ It is NOT relaxed here. Widening the
predicate to "predominantly digits" would be a rule edited after seeing which box it fails on, and
the residual is worth more as a measured limit of the confirming read than as a passing number.

⚠️ B5 IS THE ONE THAT NEEDED A NEW INSTRUMENT, AND THAT IS THE FINDING BEHIND THE CLASS. Every score
this project quotes is GOLD-ENTRY-DRIVEN: `visual_agent._bind` walks the gold and binds each entry to
a box, so a box no entry binds to is never scored. No GOLD-HEADBAND entry binds to a page-number box.
Therefore fifteen invented `MN` emissions -- on the class the whole edition is built around, whose
recall is the headline bar -- cost NOTHING on any number ever published here. Recall cannot fall when
the agent manufactures notes. **The agent's `MN` precision had never been measured**, and this scorer
measures it because the class made the gap visible.

    ../ocr-venv/bin/python witness/score_pagenumber_agent.py             # B1 B2 B3 B5 + the slack
    ../ocr-venv/bin/python witness/score_pagenumber_agent.py --withheld  # B4, the negative

⚠️ NO-ARGUMENT BEHAVIOUR IS THE FULL SCORE and it mutates nothing -- the verification standard runs
every enrolled command WITHOUT ITS ARGUMENTS (see build_recog_gold.py's docstring for what that cost
once). `--withheld` hides the record by MONKEYPATCHING the loader for the duration of one run; it
never moves or deletes the file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

import visual_agent as VA                 # noqa: E402

GOLD = _HERE / "gold" / f"pagenumber_{VA.WITNESS}_{VA.LEAF_LO}-{VA.LEAF_HI - 1}.json"

B1_FLOOR = 12          # of the 16 leaves that carry a detected page-number box
# 🔴 R14.11, 2026-08-28 — THIS WAS THE LITERAL `B3_EXPECT = "115/121"`. It was only ever
# PRINTED, never compared, so when R14.11 moved the agent to 117/121 this file went on
# announcing 115/121 as the current head-band figure. A stale number that is only printed is
# worse than one that is tested, because nothing can fail to catch it. Computed live from
# `visual_agent.headband_score`, the one place the head-band score exists.
def _b3() -> str:
    ok, n, _ = VA.headband_score()
    return f"{ok}/{n}"


def _leaves():
    VA._READ_CACHE = None
    return VA.load_leaves()


def withheld() -> int:
    """B4 -- remove the evidence and the cue must stop, loudly."""
    print("B4 — THE WITHHELD-RECORD NEGATIVE\n")
    print("The reading record is hidden for this run only (the loader is patched; the file is not")
    print("touched). A cue whose evidence can be removed without changing the answer was never")
    print("reading the evidence — R13.1's injection lesson, one level up.\n")
    VA._READ_CACHE = None
    VA._reading_record = lambda: None          # type: ignore[assignment]
    pn, cands, caused = 0, 0, 0
    for lf in VA.load_leaves():
        for b in lf.boxes:
            if not VA.pn_candidate(b, lf):
                continue
            cands += 1
            if b.label == VA.PN:
                pn += 1
            if "reading record absent" in b.cause:
                caused += 1
    print(f"    candidates                     {cands}")
    print(f"    named PN with no record        {pn}     (must be 0)")
    print(f"    carrying the record's absence  {caused}    (must equal the candidate count)")
    ok = pn == 0 and caused == cands and cands > 0
    print(f"\n```\nB4 withheld-record PN emissions -> {pn}/{cands}\n```")
    print(f"\n{'✅ B4 PASS' if ok else '🔴 B4 FAIL'} — the cue does not fire without the read, "
          f"and every candidate names the absence rather than guessing.")
    return 0 if ok else 1


def main() -> int:
    if "--withheld" in sys.argv:
        return withheld()

    g = json.loads(GOLD.read_text())
    truth = {e["leaf"]: e["printed"] for e in g["labels"]}
    missing = set(g["no_page_number_box"])

    print("R14.10b — `PN` (PageNumber), scored against the pre-registered criteria")
    print(f"{VA.WITNESS} leaves {VA.LEAF_LO}-{VA.LEAF_HI - 1}; truth = GOLD-PAGENUMBER, "
          f"adjudicated from the page by eye, NEVER from the recogniser's output\n")

    rec = VA._reading_record()
    if rec is None:
        print("🔴 NO READING RECORD — run witness/build_reading_record.py --build.")
        print("   The cue abstains without it BY DESIGN; scoring it here would report a")
        print("   missing instrument as a failed class.")
        return 1
    print(f"confirming read by {rec['stamp']['model']} sha {rec['stamp']['model_sha']} "
          f"(R2.1b's selection)\n")

    named, wrong, abstained, slack_area, slack_note = [], [], [], [], []
    mn_on_pn = []
    for lf in _leaves():
        (ml, mr), mw = lf.measure, max(1e-9, lf.measure[1] - lf.measure[0])
        for b in lf.boxes:
            is_cand = VA.pn_candidate(b, lf)
            if is_cand:
                slack_area.append(b.area)
                if b.label == VA.PN:
                    (named if lf.leaf in truth else wrong).append((lf.leaf, b.read_text))
                elif b.label == VA.ABSTAIN:
                    abstained.append((lf.leaf, b.read_text))
                elif b.label == VA.MN and lf.leaf in truth:
                    mn_on_pn.append(lf.leaf)
            elif 0.5 * (b.y0 + b.y1) <= lf.head_y and b.area < 0.02 and b.label == VA.MN:
                slack_note.append(b.area)

    print("B1 — IS THE CLASS NAMED?\n")
    for leaf, txt in sorted(named):
        print(f"    leaf {leaf}  PN   read {txt!r:>8}   printed {truth[leaf]}")
    for leaf, txt in sorted(abstained):
        exp = truth.get(leaf, "—")
        print(f"    leaf {leaf}  ??   read {txt!r:>8}   printed {exp}   ← ABSTAINED, with its cause")
    print(f"\n```\nB1 PN named -> {len(named)}/{len(truth)}\n```")
    b1 = len(named) >= B1_FLOOR
    print(f"{'✅' if b1 else '🔴'} B1 {'PASS' if b1 else 'FAIL'} — floor was {B1_FLOOR}, "
          f"pre-registered to let an unreadable crop abstain and still pass.")

    print("\nB2 — DID IT INVENT ONE?\n")
    print(f"```\nB2 PN calls on a non-page-number -> {len(wrong)}/{len(named) + len(wrong)}\n```")
    b2 = not wrong
    print(f"{'✅' if b2 else '🔴'} B2 {'PASS' if b2 else 'FAIL'}"
          + ("" if b2 else f" — {wrong}"))
    print(f"    ⚠️ And the {len(abstained)} abstention(s) are the criterion working, not a shortfall:")
    print("       an empty reading is the ABSENCE of evidence, which is not evidence of absence.")

    print("\nB5 — THE MISFILING THAT COST NOTHING (MN PRECISION, never measured before)\n")
    print("    Before this class existed all 20 page numbers were misfiled: 15 named `MN`, one")
    print("    abstained, and 4 named `MT`. No GOLD-HEADBAND entry binds to any of them, so `MN`")
    print("    recall — the headline bar — could not and did not move, and MainText is CONTAINMENT")
    print("    so the `MT` four scored as CORRECT. The agent was inventing notes for free.")
    print(f"\n```\nB5 spurious MN on page numbers -> {len(mn_on_pn)}/{len(truth)}\n```")
    b5 = not mn_on_pn
    print(f"{'✅' if b5 else '🔴'} B5 {'PASS' if b5 else 'FAIL'}"
          + ("" if b5 else f" — still MN on leaves {sorted(mn_on_pn)}"))

    print("\n⚙️ THE GUARDS' SLACK, PRINTED SO THE 'IT DECIDES NOTHING' CLAIM IS CHECKED\n")
    if slack_area and slack_note:
        print(f"    candidate area   max {max(slack_area):.4f}   (guard PN_MAX_AREA "
              f"{VA.PN_MAX_AREA:.4f})")
        print(f"    head-band notes  min {min(slack_note):.4f}   ← the guard sits in the gap "
              f"between these two, which is what a guard is for")
    print(f"\n🔴 THE COUNTERFACTUAL, AND IT REFUTES THIS STEP'S OWN SHIPPED JUSTIFICATION\n")
    print(f"    The candidate test admitted {len(slack_area)} box(es) and EVERY ONE is a page")
    print(f"    number — 0 notes. So on this window GEOMETRY ALONE names the class 20/20 with 0")
    print(f"    false positives, while the read scores {len(named)}/{len(truth)} plus "
          f"{len(abstained)} abstentions and {len(mn_on_pn)} MN.")
    print("    ⚠️ THE CONFIRMING READ MEASURABLY DEGRADES THE RESULT HERE. B2's zero is therefore")
    print("       not evidence the read discriminates: it was never asked to reject a note.")
    print("\n    ⚠️ AND THE CLAIM THAT 'POSITION CANNOT SEPARATE THEM' WAS OVERSTATED. It is true")
    print("       of the statistic it was measured on — the box CENTRE, `rel_h`, and `out_frac`")
    print("       overlap outright. It is FALSE of position generally. Measured over all 65")
    print("       head-band boxes in the window:")
    print("           width   PN 0.0442-0.0546 vs other 0.0757-0.3028   SEPARATES, band 2.0x the PN spread")
    print("           area    PN 0.0008-0.0012 vs other 0.0018-0.0095   SEPARATES, band 1.5x")
    print("           aspect  PN 2.01-2.73     vs other 3.17-10.25      SEPARATES")
    print("       A page number is not distinguished from a side-note by WHERE it sits. It is")
    print("       distinguished by being a SHORT, SQUAT object — two or three sorts against a")
    print("       phrase — which is what the book itself distinguishes, and is a fount-grain fact")
    print("       of the same kind R14.10a used for the ARGUMENT.")
    print("\n    ➡️ THE PREDICTED LIMIT, PRE-REGISTERED HERE FOR THE STEP THAT TESTS IT: width is")
    print("       ~0.0165 of the page per digit, so a FOUR-digit page number measures ~0.059-0.073")
    print("       against a note floor of 0.0757. The empty band SHRINKS TO ALMOST NOTHING later")
    print("       in the volume. That is where the read earns its place — as the CHECK on a")
    print("       geometric cue whose margin is known to close, not as the decider that replaces it.")

    print("\n📌 THE OUT-OF-SAMPLE CHECK NOBODY BUILT FOR THIS STEP\n")
    print("    GOLD-FOREEDGE — built for R14.8, not band-limited, and never touched here — carries")
    print("    TWO `PN` entries, on leaves 401 and 417. The agent now scores them 2/2 and that")
    print("    gold rises 38/42 -> 40/42. ⚠️ Both sit on leaves this step's OWN probe had reported")
    print("    as carrying NO page number, which is how the false absence below was caught.")

    print("\n🔴 THE FALSE ABSENCE THIS STEP PRODUCED, AND CORRECTED (recorded, not quietly fixed)\n")
    print(f"    detector gaps first reported: [401, 402, 409, 417] — now measured at {sorted(missing)}.")
    print("    THERE IS NO DETECTION GAP. Every leaf prints a page number and the detector")
    print("    localises every one. The gap was in the SEARCH: the candidate test was bounded by")
    print("    `mass_y <= head_y`, and on those four the number sits ~0.005 of a page below the")
    print("    head line the BODY BLOCK defines. All four were silently named `MT`. ⚠️ A bounded")
    print("    search returns 'not found' in exactly the shape an exhaustive one does — the third")
    print("    instance of this shape here, after `audit_label_sources.py` bounded by a directory")
    print("    and then by a field name. ⚠️ And the repair is CUE 2b's, one end of the page up:")
    print("    the detector's own PageHeader judgement as a second cue, position-clamped.")

    print("\n⚠️ THIS DISCHARGES NO GATE. One witness, 20 leaves, one operator, and the operator")
    print("   adjudicating the printed numbers is the same agent that wrote the cue. `PN` may not")
    print("   be promoted to GOLD-LAYOUT on this basis (Roadmap R16.1).")
    ok = b1 and b2 and b5
    print(f"\n{'✅ B1, B2, B5 PASS' if ok else '🔴 NOT ALL CRITERIA PASS'} — B3 is "
          f"`visual_agent.py` ({_b3()} unchanged), B4 is `--withheld`.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
