#!/usr/bin/env python3
"""R14.14 -- the ROTATED FRAME, scored, INCLUDING THE REFUTATION OF ITS OWN PREMISE.

🔴 THE STEP WAS FILED ON A CAUSE THAT MEASUREMENT DOES NOT SUPPORT, AND THAT IS THE HEADLINE RESULT.
R14.14 was written because *"the horizontal head line CUTS THROUGH 41 BOXES"*, and the cutting was
attributed to the agent having no angle. Both halves were checked here:

  · the tilt is REAL and per-leaf -- -0.901° to +1.636° over leaves 400-419, measured from row
    geometry, and it is NOT the fount record's `slant_mode`, which reads 0.00 on every leaf;
  · the tilt DOES NOT CAUSE THE CUTTING. Correlation between |skew| and head-line straddles is
    **+0.051** over 20 leaves. Nearly-flat leaves straddle 2.50 boxes on average and tilted leaves
    2.44 -- indistinguishable. Rotating the frame moved the count 41 -> 50, i.e. the WRONG WAY.

⇒ **The 41 cut boxes belong to R14.12, not here.** The head line is the extreme edge of the BODY
BLOCK, and page furniture sits at overlapping heights, so ANY scalar boundary between them is
straddled whatever its angle. That is the nesting problem, and it needs ownership of ink, not
trigonometry. ⚠️ The original acceptance clause "straddles 41 -> 0" is therefore RETIRED as
unreachable by this step, and is NOT quietly reinterpreted into something the step does satisfy.

WHAT THE TILT ACTUALLY COSTS, and it is a real defect: Surya's boxes are AXIS-ALIGNED, so an
axis-aligned rectangle around a tilted line is taller than the type it holds by `width * tan(angle)`.
Measured: on leaf 409 (+1.64°) that inflation is **17% of a median box height**, on 419 (+1.60°)
16%, and on 406 (+0.03°) 0%. That is a BOUNDARY error (Gate 9.3), and every gold this project holds
scores LABELS rather than boundaries -- which is exactly why it has never shown up in a number.

    ../ocr-venv/bin/python witness/score_skew_frame.py             # the four criteria
    ../ocr-venv/bin/python witness/score_skew_frame.py --withheld  # S4, the negative

⚠️ NO-ARGUMENT BEHAVIOUR IS THE FULL SCORE and mutates nothing.
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SPIKE = _HERE.parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(SPIKE))

import visual_agent as VA          # noqa: E402

# 🔴 R14.11, 2026-08-28 — S2 USED TO PIN A LITERAL AND THAT WAS THE WRONG INSTRUMENT.
# It read `S2_EXPECT = {"overall": (115, 121), "MN": (16, 19), ...}` and compared the agent to those
# frozen numbers. The intent was right — a frame change that moves a label has changed what the page
# is said to contain, and "it improved" is not evidence it is right — but the TEST did not measure
# that. It measured "does the label vector still equal the value frozen on 2026-08-28", so ANY later
# step that improves the agent for reasons having nothing to do with the rotation trips it. That is
# exactly what happened: R14.11 retired `CENTRED_LO/HI`, GOLD-HEADBAND moved 115/121 -> 117/121, and
# S2 reported the ROTATION had broken neutrality. A FALSE FAIL, attributing another step's result to
# this one.
#
# ⚠️ THE HONEST FORM COMPARES THE TWO STATES IN ONE RUN: label the window with the rotation ON and
# again with it OFF, and require the vectors to be identical. That is what "the rotation moves no
# label" MEANS, it is immune to every unrelated improvement, and it needs no frozen number at all.
# Same shape as the defect this file's own S3 records: a criterion can look rigorous and still not
# test the thing it names.


def _labels_unrotated():
    """The full label vector with the skew record withheld — the agent's pre-R14.14 behaviour."""
    keep = VA.SKEW
    VA.SKEW = keep.with_name("__no_such_skew_record__.json")
    VA._SKEW_CACHE = None
    try:
        return tuple(b.label for lf in VA.load_leaves() for b in lf.boxes)
    finally:
        VA.SKEW = keep
        VA._SKEW_CACHE = None


def _leaves():
    VA._SKEW_CACHE = None
    return VA.load_leaves()


def straddles(lf):
    return [b for b in lf.boxes
            if VA.ry(b.cx, b.y0, lf) < lf.head_y < VA.ry(b.cx, b.y1, lf)]


def withheld() -> int:
    print("S4 — THE WITHHELD-RECORD NEGATIVE\n")
    print("The skew record is hidden for this run only. Every leaf must report an UNROTATED frame")
    print("and NAME the absence — an unmeasured page and a square page are different states, and a")
    print("silent zero collapses them into the second.\n")
    VA._SKEW_CACHE = None
    VA._skew_record = lambda: None            # type: ignore[assignment]
    seen, caused = 0, 0
    for lf in VA.load_leaves():
        if lf.skew_seen:
            seen += 1
        if "skew record not built" in lf.skew_why:
            caused += 1
    print(f"    leaves reporting a measured angle : {seen}    (must be 0)")
    print(f"    leaves naming the absence         : {caused}   (must be 20)")
    ok = seen == 0 and caused == 20
    print(f"\n```\nS4 withheld-record leaves claiming an angle -> {seen}/20\n```")
    print(f"\n{'✅ S4 PASS' if ok else '🔴 S4 FAIL'}")
    return 0 if ok else 1


def main() -> int:
    if "--withheld" in sys.argv:
        return withheld()

    rec = VA._skew_record()
    if rec is None:
        print("🔴 NO SKEW RECORD — run witness/build_skew_record.py --build.")
        return 1
    leaves = _leaves()

    print("R14.14 — THE ROTATED FRAME, and the refutation of the cause it was filed on\n")

    print("S1 — IS THE TILT REAL, AND MEASURED PER LEAF?\n")
    ang = {lf.leaf: lf.skew for lf in leaves if lf.skew_seen}
    print(f"    leaves measured  {len(ang)}/20")
    print(f"    range            {min(ang.values()):+.3f}° … {max(ang.values()):+.3f}°")
    print(f"    median           {st.median(list(ang.values())):+.3f}°")
    print(f"    |angle| > 0.8°   {sum(1 for v in ang.values() if abs(v) > 0.8)} leaf/leaves")
    s1 = len(ang) == 20 and (max(ang.values()) - min(ang.values())) > 1.0
    print(f"\n```\nS1 leaves with a measured baseline angle -> {len(ang)}/20\n```")
    print(f"{'✅' if s1 else '🔴'} S1 {'PASS' if s1 else 'FAIL'} — the tilt exists and it VARIES; a "
          f"single corpus angle could not describe it.")

    print("\n\nS2 — DOES THE ROTATION MOVE A LABEL? (it must not, and this is EXACT equality)\n")
    gold = json.loads(VA.GOLD.read_text())
    by_leaf = {}
    for e in gold["labels"]:
        if "xlf" in e:
            by_leaf.setdefault(e["leaf"], []).append(e)
    lm = {lf.leaf: lf for lf in leaves}
    per, tot_ok, tot = {}, 0, 0
    for i, entries in by_leaf.items():
        lf = lm.get(i)
        if lf is None:
            continue
        for e in entries:
            b, _ = VA._bind(e, lf.boxes, VA.BIND_OVERLAP)
            if b is None:
                continue
            g = e["label"]
            per.setdefault(g, [0, 0])
            per[g][1] += 1
            tot += 1
            if b.label == g:
                per[g][0] += 1
                tot_ok += 1
    rows = [("overall", tot_ok, tot)] + [(k, per[k][0], per[k][1]) for k in ("MN", "RH", "MT", "CH")
                                         if k in per]
    for name, got, n in rows:
        print(f"    {name:<8} {got:>3}/{n:<4}")
    print("\n    ⚠️ The figures above are REPORTED, not tested. They are the agent's current score "
          "and\n       they move whenever ANY step improves it; pinning them here would attribute "
          "another\n       step's result to this one, which is precisely the false fail R14.11 "
          "produced.\n")

    rot = tuple(b.label for lf in leaves for b in lf.boxes)
    unrot = _labels_unrotated()
    moved = sum(1 for a, b in zip(rot, unrot) if a != b)
    s2 = len(rot) == len(unrot) and moved == 0
    print(f"    rotation ON  vs OFF, same run, same window: {len(rot)} boxes compared, "
          f"{moved} label(s) moved")
    print(f"\n```\nS2 labels moved by the rotation -> {moved}/{len(rot)}\n```")
    print(f"{'✅' if s2 else '🔴'} S2 {'PASS' if s2 else 'FAIL'} — the rotation is LABEL-NEUTRAL on "
          f"this window.")
    print("    ⚠️ Neutral is the honest word. It is not evidence the rotation helps; it is evidence")
    print("       it breaks nothing, which is what a groundwork change is entitled to claim.")

    print("\n\nS3 — 🔴 THE PREMISE, TESTED AND REFUTED\n")
    xs = [abs(lf.skew) for lf in leaves]
    ys = [len(straddles(lf)) for lf in leaves]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    corr = num / den if den else float("nan")
    flat = [y for x, y in zip(xs, ys) if x < 0.3]
    tilt = [y for x, y in zip(xs, ys) if x > 0.8]
    print(f"    head-line straddles, rotated frame : {sum(ys)}   (unrotated: 41)")
    print(f"    corr(|skew|, straddles)            : {corr:+.3f}   over 20 leaves")
    print(f"    nearly-flat leaves (|skew|<0.3)    : mean {sum(flat)/len(flat):.2f} straddles")
    print(f"    tilted leaves      (|skew|>0.8)    : mean {sum(tilt)/len(tilt):.2f} straddles")
    print(f"\n```\nS3 corr between skew and head-line straddles -> {corr:+.3f}\n```")
    print("🔴 THE CUTTING IS NOT CAUSED BY THE ANGLE. Flat leaves are cut as often as tilted ones,")
    print("   and rotating the frame moved the count the WRONG WAY. The head line is the extreme")
    print("   edge of the BODY BLOCK and page furniture sits at overlapping heights, so any scalar")
    print("   boundary there is straddled whatever its angle. ⇒ THE 41 BOXES BELONG TO R14.12, the")
    print("   lamination: they need ownership of ink, not trigonometry.")
    print("   ⚠️ The original acceptance clause `straddles 41 -> 0` is RETIRED as unreachable by")
    print("      this step, not reinterpreted into something this step happens to satisfy.")

    print("\n\nS5 — WHAT THE TILT DOES COST, which no gold here can see\n")
    print("    An axis-aligned box around a tilted line is taller than its type by width*tan(angle).")
    for lf in leaves:
        if abs(lf.skew) < 0.8 and lf.leaf not in (406,):
            continue
        infl = [(b.x1 - b.x0) * abs(math.tan(math.radians(lf.skew))) for b in lf.boxes]
        hs = [b.y1 - b.y0 for b in lf.boxes]
        print(f"    leaf {lf.leaf} {lf.skew:+.2f}°  median inflation {st.median(infl):.4f} = "
              f"{st.median(infl)/max(1e-9, st.median(hs)):.0%} of a median box height")
    print("\n    ⚠️ This is a BOUNDARY error (Gate 9.3). Every gold this project holds scores")
    print("       LABELS, not boundaries, which is precisely why it has never appeared in a number")
    print("       and why S2 can be exactly unchanged while a real defect is present.")

    ok = s1 and s2
    print(f"\n{'✅ S1 and S2 PASS' if ok else '🔴 NOT ALL CRITERIA PASS'}; S3 is a REFUTATION and is "
          f"reported as one; S4 is `--withheld`.")
    print("🔴 R14.14 REMAINS OPEN: the frame is rotated and label-neutral, the boundary defect S5")
    print("   names is unmeasured by any gold, and the cause the step was filed on was wrong.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
