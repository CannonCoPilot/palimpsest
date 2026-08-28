#!/usr/bin/env python3
"""R14.13/R14.17 -- STRUCTURAL SCREEN over EVERY plate, to aim a human's eyes.

⚠️ THIS IS NOT THE REVIEW AND MUST NOT BE MISTAKEN FOR IT. It finds defects that are visible in the
GEOMETRY. Leaf 417's annotation block boxed `MT` is the standing counter-example: it scores as
correct, violates no structural rule, and was found only by DRAWING the page. A screen that returns
nothing on a leaf is evidence about the geometry, never a verdict on the leaf.

Writes `plates/review-flags.json`, which the review tool loads and shows per leaf.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
_H = Path(__file__).resolve().parent
B = json.loads((_H / "plates" / "bundle.json").read_text())

def ink_ov(a, b):
    w = max(0.0, min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]))
    h = max(0.0, min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]))
    return w * h

flags, tally = {}, {}
def add(pid, kind, sev, what):
    flags.setdefault(pid, []).append({"kind": kind, "sev": sev, "what": what})
    tally[kind] = tally.get(kind, 0) + 1

for p in B["plates"]:
    bx, pid = p["boxes"], p["id"]
    n = len(bx)
    if n == 0:
        add(pid, "NO BOXES", "bad", "the detector localised nothing at all")
        continue
    if n <= 3:
        add(pid, "SPARSE", "warn", f"only {n} box(es) — a printed page of this book rarely has so few")
    ab = [b for b in bx if b["label"] in ("", "??")]
    if len(ab) / n > 0.30:
        add(pid, "ABSTAIN-HEAVY", "warn",
            f"{len(ab)}/{n} boxes unnamed ({len(ab)/n:.0%})")
    # every leaf of this book prints a running head and a page number
    labs = {b["label"] for b in bx}
    if "RH" not in labs:
        add(pid, "NO RUNNING HEAD", "warn", "no RH named; every leaf here prints one")
    if "PN" not in labs:
        add(pid, "NO PAGE NUMBER", "note",
            "no PN named — expected while the reading record is absent for this witness")
    # boxes straddling the head/foot line: R14.12's lamination target
    st = sum(1 for b in bx if b["y0"] < p["head_y"] < b["y1"])
    if st >= 3:
        add(pid, "HEAD LINE CUTS", "warn", f"{st} boxes straddle the head line (R14.12)")
    # ink overlap between same-class boxes that are not containment
    ov = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bx[i], bx[j]
            o = ink_ov(a, b)
            if o <= 0: continue
            aa = (a["x1"]-a["x0"])*(a["y1"]-a["y0"]); ba = (b["x1"]-b["x0"])*(b["y1"]-b["y0"])
            if o > 0.5*min(aa, ba) and not (o > 0.95*min(aa, ba)):
                ov += 1
    if ov >= 4:
        add(pid, "OVERLAP DENSE", "warn", f"{ov} partial box overlaps (R14.12 lamination)")
    # a box larger than most of the page called anything but MainText
    for b in bx:
        a = (b["x1"]-b["x0"])*(b["y1"]-b["y0"])
        if a > 0.45 and b["label"] not in ("MT", "", "??"):
            add(pid, "GIANT NON-BODY", "bad",
                f"box {b['i']} covers {a:.0%} of the page but is named {b['label']}")
        if b["x1"] <= b["x0"] or b["y1"] <= b["y0"]:
            add(pid, "DEGENERATE BOX", "bad", f"box {b['i']} has zero or negative extent")
        if b["y1"] > 1.001 or b["x1"] > 1.001 or b["x0"] < -0.001 or b["y0"] < -0.001:
            add(pid, "OFF-PAGE BOX", "bad", f"box {b['i']} extends outside the leaf")
    # 🔴 THE FRAME'S OWN PREMISE, CHECKED PER LEAF. `visual_agent.frame` anchors the measure on the
    # SINGLE LARGEST box because on OT1-1609-B that box IS the body block (median area 0.562). On
    # the witnesses added 2026-08-28 it often is not: NT-1582-B's median largest box is 0.192.
    # Where the largest box is small, the measure has been anchored on something that is not the
    # body — usually a marginal column — and EVERY cue downstream is expressed in that wrong frame.
    big = max(((b["x1"]-b["x0"])*(b["y1"]-b["y0"]) for b in bx), default=0.0)
    if big < 0.25:
        add(pid, "NO BODY BLOCK", "bad",
            f"largest box is only {big:.0%} of the leaf — the measure is almost certainly anchored "
            f"on marginalia, which inverts every label on the page")
    if p["archetype"] == "?":
        add(pid, "NO ARCHETYPE", "warn", "the archetype call abstained")
    m = p["measure"]
    if m[1] - m[0] < 0.35:
        add(pid, "NARROW MEASURE", "bad",
            f"measure spans only {m[1]-m[0]:.2f} of the leaf — the body block was probably missed")
    if p["head_y"] >= p["foot_y"]:
        add(pid, "FRAME INVERTED", "bad", "head line is at or below the foot line")

(_H / "plates" / "review-flags.json").write_text(json.dumps(flags, indent=1))
print(f"screened {len(B['plates'])} plate(s); {len(flags)} carry >=1 flag\n")
for k, v in sorted(tally.items(), key=lambda x: -x[1]):
    print(f"  {v:>4}  {k}")
print("\n⚠️ A clean screen is NOT a clean leaf — this sees geometry only.")
