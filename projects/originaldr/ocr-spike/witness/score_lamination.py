#!/usr/bin/env python3
"""R16.16 — HOW MUCH OF THE OVERLAP PROBLEM DOES ORDERING ALONE SOLVE?

Masterplan §3.0 requires S4 to emit a LAMINATION: z-ordered typed regions where a region owns the
ink inside it that no higher region claims, and **no region contains ink lying inside another at the
same or higher z-order**. Sir restated it on 2026-08-31 as "layers", which is the same concept.

⚠️ THIS SCRIPT MEASURES. IT REPAIRS NOTHING. No boundary is adjusted, no box is moved, no label
changes. It exists because R16.17's acceptance forbids the plate book from computing its own
violation count — two implementations of one invariant is the R14.10a defect — so the viewer must
read a number this file produced.

--------------------------------------------------------------------------------------------
THE QUESTION, AND WHY IT IS NOT RHETORICAL

"Layers solve the problem of overlapping boxes" is a hypothesis with a measurable size. A z-order
resolves overlap **by containment**: if box A contains box B, putting B on top gives every contested
pixel an unambiguous owner and the ragged remainder in A is permitted (§3.0 clause 2). But a z-order
CANNOT resolve a **partial** overlap — two boxes each holding ink the other also holds, neither
containing the other. There is no stacking of those two that gives every pixel one owner. Those
pairs are exactly the ones that need §3.0 clause 4, *the agent adjusts boundaries until the invariant
holds*, and they are the real cost of the lamination.

So the measurement splits the problem in two, and the split IS the finding:

  CONTAINED   — one box inside the other. Ordering alone fixes it. Free.
  PARTIAL     — neither contains the other, and they share INK. Ordering cannot fix it.
                Boundary adjustment or an abstention is required, per leaf, per pair.

⚠️ OVER INK, NEVER OVER RECTANGLES. §3.0 is explicit: two boxes may overlap in white space with no
consequence, because a page is not tiled by its type. A body block's rectangle legitimately spans the
gutter-side white a side-note sits in. Every count below is therefore taken over INK PIXELS, and the
rectangle-overlap count is reported ALONGSIDE it purely to show how far the two diverge.

PRE-REGISTERED, BEFORE THE FIRST RUN:

  L1  The rectangle count OVERSTATES the problem. Ink-overlapping pairs are strictly fewer than
      rectangle-overlapping pairs, and the gap is large — median leaf loses >= 25% of its pairs
      when the test moves from rectangles to ink.
      ⚠️ If L1 fails, then §3.0's insistence on ink over rectangles bought nothing measurable and
      the simpler rectangle rule should be reconsidered.

  L2  ORDERING ALONE IS NOT ENOUGH. On the full 208 leaves, PARTIAL ink pairs are present on more
      than 20% of leaves. ⚠️ If L2 fails — if almost every overlap is containment — then the
      lamination is a sorting problem and R16.16 is far cheaper than it has been costed.
      Either outcome is a result. This leg is written so the cheap answer can win.

  L3  THE TWO RIVAL BINDING RULES ARE EXPLAINED BY CONTAINMENT. `BIND_OVERLAP` and
      `BIND_TIGHTEST` disagree only where a gold entry falls in a CONTAINED pair, never in a
      PARTIAL one. ⚠️ This is the mechanism R14.12 clause (3) asserts without evidence. If it
      fails, the two rules differ for a reason nobody has diagnosed and R16.16's clause (3) is
      not a safe acceptance test.
--------------------------------------------------------------------------------------------
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import score_detection as SD              # noqa: E402

PLATES = _HERE / "plates"
BUNDLE = PLATES / "bundle.json"
OUT = PLATES / "lamination-scores.json"

# A pair counts as CONTAINED when one box lies this far inside the other. ⚠️ Not 1.0: a detector
# box drawn a pixel proud of its parent is still nested in every sense that matters, and demanding
# exact containment would misfile real nesting as PARTIAL and inflate the expensive category.
CONTAIN = 0.95
# Ink below this many pixels in the contested region is speckle or a shared serif, not a shared
# object. Reported so its effect is visible; the same floor `score_detection` uses, in absolute px.
MIN_CONTESTED = 8

L1_BAR = 0.25          # median share of pairs that must fall away when rectangles become ink
L2_BAR = 0.20          # share of leaves that must carry a PARTIAL pair


def _px(b: dict, w: int, h: int) -> tuple[int, int, int, int]:
    x0, x1 = max(0, int(b["x0"] * w)), min(w, int(np.ceil(b["x1"] * w)))
    y0, y1 = max(0, int(b["y0"] * h)), min(h, int(np.ceil(b["y1"] * h)))
    return x0, y0, x1, y1


def measure(plate: dict) -> dict | None:
    path = PLATES / plate["img"]
    if not path.is_file():
        return None
    with Image.open(path) as im:
        mask = SD._ink(im)
    h, w = mask.shape
    boxes = plate["boxes"]
    ink = [int(mask[_px(b, w, h)[1]:_px(b, w, h)[3], _px(b, w, h)[0]:_px(b, w, h)[2]].sum())
           for b in boxes]

    rect_pairs = ink_pairs = contained = partial = 0
    contested_px = 0
    worst = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ax0, ay0, ax1, ay1 = _px(a, w, h)
            bx0, by0, bx1, by1 = _px(b, w, h)
            ix0, iy0 = max(ax0, bx0), max(ay0, by0)
            ix1, iy1 = min(ax1, bx1), min(ay1, by1)
            if ix1 <= ix0 or iy1 <= iy0:
                continue
            rect_pairs += 1
            shared = int(mask[iy0:iy1, ix0:ix1].sum())
            if shared < MIN_CONTESTED:
                # ⚠️ RECTANGLES OVERLAP, INK DOES NOT. This is the case §3.0 exists to permit, and
                # counting it as a violation is precisely the geometric tidiness the page lacks.
                continue
            ink_pairs += 1
            contested_px += shared
            # Containment is judged over INK too: box B is inside A when nearly all of B's own ink
            # is ink A also covers. A rectangle sticking out over blank paper does not make a pair
            # partial, because the blank overhang is not ink anyone is contesting.
            a_in = shared / max(1, ink[i])
            b_in = shared / max(1, ink[j])
            if max(a_in, b_in) >= CONTAIN:
                contained += 1
            else:
                partial += 1
                worst.append({"i": i, "j": j, "shared_px": shared,
                              "a_frac": round(a_in, 4), "b_frac": round(b_in, 4),
                              "a_surya": a.get("surya"), "b_surya": b.get("surya"),
                              "a_label": a.get("label"), "b_label": b.get("label")})
    worst.sort(key=lambda d: -d["shared_px"])
    total_ink = int(mask.sum())
    return {"id": plate["id"], "witness": plate["witness"], "n_boxes": len(boxes),
            "rect_pairs": rect_pairs, "ink_pairs": ink_pairs,
            "contained": contained, "partial": partial,
            "contested_px": contested_px,
            "contested_frac": round(contested_px / max(1, total_ink), 5),
            "partial_pairs": worst[:12]}


def main() -> int:
    print(__doc__)
    import statistics as st
    bundle = json.loads(BUNDLE.read_text())
    rows = [r for r in (measure(p) for p in bundle["plates"]) if r]
    if not rows:
        print("🔴 no plates measured — bundle or images missing.")
        return 1

    rect = sum(r["rect_pairs"] for r in rows)
    inkp = sum(r["ink_pairs"] for r in rows)
    cont = sum(r["contained"] for r in rows)
    part = sum(r["partial"] for r in rows)
    # L1 is a per-leaf median, not a pooled ratio: a pooled figure lets one twelve-pair leaf speak
    # for two hundred others, which is the shape R16.12 caught with per-setting reporting.
    drops = [1.0 - r["ink_pairs"] / r["rect_pairs"] for r in rows if r["rect_pairs"]]
    l1 = st.median(drops) if drops else None
    leaves_partial = sum(1 for r in rows if r["partial"])
    l2 = leaves_partial / len(rows)

    print("=" * 92)
    print(f"MEASURED {len(rows)} leaves, {sum(r['n_boxes'] for r in rows)} boxes.\n")
    print(f"  rectangle-overlapping pairs  {rect:5d}")
    print(f"  INK-overlapping pairs        {inkp:5d}   ({inkp / max(1, rect):.1%} of them)")
    print(f"     of which CONTAINED        {cont:5d}   ordering alone resolves these")
    print(f"     of which PARTIAL          {part:5d}   🔴 ordering CANNOT resolve these")
    print(f"\n  leaves carrying a PARTIAL pair  {leaves_partial}/{len(rows)} = {l2:.1%}")
    print(f"  median leaf contested ink share {st.median([r['contested_frac'] for r in rows]):.4f}")

    l1_pass = l1 is not None and l1 >= L1_BAR
    l2_pass = l2 > L2_BAR
    print(f"\n  L1 ink beats rectangles   median pair drop {l1:.1%} vs bar {L1_BAR:.0%}"
          f"   {'✅ PASS' if l1_pass else '🔴 FAIL'}")
    print(f"  L2 ordering insufficient  {l2:.1%} of leaves vs bar >{L2_BAR:.0%}"
          f"   {'✅ PASS' if l2_pass else '🔴 FAIL — the cheap answer wins, see below'}")
    if not l2_pass:
        print("     ⚠️ NOT A DEFECT. L2 was written so the cheap answer COULD win: if nearly every")
        print("        overlap is containment, the lamination is a SORTING problem and R16.16 is")
        print("        far cheaper than it was costed. Re-cost the step; do not relax the bar.")

    print("\n  PER SETTING — a pooled mean would hide a setting whose layout overlaps differently.")
    for wid in sorted({r["witness"] for r in rows}):
        g = [r for r in rows if r["witness"] == wid]
        gp = sum(1 for r in g if r["partial"])
        print(f"    {wid:14s} n={len(g):3d}  ink pairs {sum(r['ink_pairs'] for r in g):4d}"
              f"  contained {sum(r['contained'] for r in g):4d}"
              f"  PARTIAL {sum(r['partial'] for r in g):4d}"
              f"  leaves w/ partial {gp:3d} ({gp / len(g):.0%})")

    print("\n  WORST LEAVES BY PARTIAL PAIRS — where boundary adjustment will actually be needed:")
    for r in sorted(rows, key=lambda r: -r["partial"])[:10]:
        print(f"    {r['id']:18s} partial {r['partial']:3d}  contained {r['contained']:3d}"
              f"  contested {r['contested_frac']:.3f}  boxes {r['n_boxes']}")

    # 🔴 L3 IS PRE-REGISTERED AND NOT RUN, AND IT SAYS SO. It needs the gold entries and both
    # binding rules, which live in `visual_agent.headband_score`; wiring them here would give this
    # file a second copy of the addressing rule, the exact defect R14.10a filed. It is therefore
    # deferred to R16.16 clause (3), where the rules already are — NOT quietly dropped. Run 1 of the
    # tile probe printed a verdict for a leg that never ran; this is that lesson applied forward.
    print("\n  L3 binding-rule mechanism   ⚠️ NOT RUN — pre-registered, deferred to R16.16(3)")
    print("     (wiring the two binding rules here would duplicate the addressing rule; it must be")
    print("      measured where `headband_score` already declares it, not reimplemented.)")

    OUT.write_text(json.dumps({
        "_doc": "R16.16 lamination diagnostic. MEASURES ONLY — repairs nothing. "
                "Pre-registration in score_lamination.py's docstring. "
                "⚠️ The plate book must READ this file, never recompute the invariant.",
        "bars": {"CONTAIN": CONTAIN, "MIN_CONTESTED": MIN_CONTESTED,
                 "L1": L1_BAR, "L2": L2_BAR},
        "verdict": {"L1": "PASS" if l1_pass else "FAIL",
                    "L2": "PASS" if l2_pass else "FAIL",
                    "L3": "NOT_RUN — deferred to R16.16(3), see script comment",
                    "l1_median_drop": None if l1 is None else float(l1),
                    "l2_leaf_share": float(l2)},
        "totals": {"rect_pairs": rect, "ink_pairs": inkp,
                   "contained": cont, "partial": part},
        "leaves": rows,
    }, indent=2, default=float))
    print(f"\n  → {OUT.relative_to(_HERE)}")
    # ⚠️ EXIT 1 WHILE PARTIAL PAIRS SURVIVE. The invariant is not met; that is the honest state and
    # a green exit here would be the silent-degradation move this project bans.
    return 0 if part == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
