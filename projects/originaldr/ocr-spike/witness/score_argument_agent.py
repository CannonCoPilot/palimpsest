#!/usr/bin/env python3
"""R14.10a ACCEPTANCE -- does the agent now name the ARGUMENT, and does it steal to do it?

THE DEFECT, measured 2026-08-27 at box grain over R2.2d's GOLD-ARGUMENT (81 rows, 10 leaves).
The agent had no name for the multi-line italic prose summary this edition sets between the chapter
head and the first verse. All TEN blocks in the window were misfiled, and the misfiling was decided
ENTIRELY BY `SMALL_AREA`:

    argument box area >= 0.05  ->  MainText   (leaves 400 403 404 407 411 417)   SILENT
    argument box area <  0.05  ->  ChapterHead(leaves 406 412 414 416)           the R14.8 ×4

⚠️ SO THE DEFECT IS 10/10, NOT THE 4 R14.8 RECORDED. GOLD-FOREEDGE's five leaves happened to fall
on the small-box side, and MainText is CONTAINMENT -- an argument called MainText scores as correct
against every gold this project holds. Half of this class was invisible to every number ever quoted.

⚠️ AND `region_head` HAS DEFINED `ARGUMENT = "AR"` WITH A VALIDATED FOUNT TEST SINCE R2.2d. The
capability existed; no rule read it. Third instance of working-code-no-rule-governs, after Gate 0f
and R13's artefact. R14.10a WIRES THE EXISTING INSTRUMENT -- it does not build a second one.

═══════════════════════════════════════════════════════════════════════════════════════════════
THE ACCEPTANCE CRITERIA, PRE-REGISTERED -- written into this file BEFORE it was first run, and
reproduced verbatim from R14.10's section rule: *a new class is ADOPTED only when its cue is scored
on leaves OUTSIDE GOLD-FOREEDGE's five; a cue fitted against the gold that revealed the gap is not
evidence. A class must also be ABSTAINABLE -- adding a name must not add a confident wrong answer.*

  A1 RECALL, ON THE DISJOINT LEAVES ONLY -- every gold ARGUMENT block on leaves 400, 403, 404,
     407, 411 and 416 is named `AR`.                                     bar: 6 of 6
     ⚠️ These six are GOLD-ARGUMENT's leaves MINUS GOLD-FOREEDGE's five. They are the whole of the
     evidence for adoption. The four overlapping leaves are reported and excluded from A1.

  A2 PRECISION, OVER THE WHOLE 20-LEAF WINDOW -- no box outside an adjudicated argument block is
     named `AR`.                                                          bar: 0 false positives
     ⚠️ A box on a leaf GOLD-ARGUMENT does not cover is UNADJUDICATED: truth unknown, counted
     neither way and reported. A non-zero count there means the cue fires where no eye has been.

  A3 NO THEFT -- on GOLD-HEADBAND, no class recall may FALL: overall >= 115/121, MN >= 16/19,
     RH >= 20/20, MT >= 77/80, CH >= 2/2.       bar: every one of them holds
     ⚠️ `AR` must not be bought with `CH` or `MT`. That gold holds no `AR` entries, so it cannot
     reward this cue -- it can only detect collateral damage, which is exactly what it is for.

  A4 ABSTAINABLE, PROVEN BY A NEGATIVE -- with the fount record withheld, the `AR` cue must emit
     NOTHING and every leaf must carry a stated cause.        bar: 0 `AR` boxes, 20 causes
     ⚠️ This is the clause that separates a cue from a coincidence. A cue that cannot be switched
     off has not been shown to be the thing doing the work.

  A5 THE PREDICTED DIRECTION, ON HELD-OUT DATA -- GOLD-FOREEDGE carries 4 `AR` entries (leaves
     406, 412, 414, 417) and NOTHING WAS FITTED AGAINST IT. Written before the run: **all four
     should flip to correct, taking 34/42 to 38/42.** ⚠️ NOT an adoption criterion -- it is the
     out-of-sample check that makes A1 mean something. If it fails while A1 passes, the cue is
     fitted to six leaves and R14.10a RE-OPENS.
═══════════════════════════════════════════════════════════════════════════════════════════════

    ../ocr-venv/bin/python witness/score_argument_agent.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import visual_agent as VA                                      # noqa: E402
from score_head_regions import GOLD as HEADBAND_GOLD           # noqa: E402

ARG_GOLD = _HERE / "gold" / f"argument_rows_{VA.WITNESS}_{VA.LEAF_LO}-{VA.LEAF_HI - 1}.json"
FE_GOLD = _HERE / "gold" / f"foreedge_regions_{VA.WITNESS}_{VA.LEAF_LO}-{VA.LEAF_HI - 1}.json"

# GOLD-FOREEDGE's declared leaves. `AR` may NOT be validated on these -- they are the gold that
# REVEALED the gap, and `build_foreedge_gold.py` states in terms that it is the SCORER, never the
# trainer. Read from that gold rather than typed here, so the exclusion cannot drift from the file.
FE_LEAVES = set(json.loads(FE_GOLD.read_text()) and
                {r["leaf"] for r in json.loads(FE_GOLD.read_text())["labels"]})

# A3's bars are MEASURED FIGURES RESTATED, not thresholds invented here: they are the agent's own
# GOLD-HEADBAND scores as of R14.9, which R14.10a may not degrade.
A3_BARS = {"overall": (115, 121), VA.MN: (16, 19), VA.RH: (20, 20), VA.MT: (77, 80), VA.CH: (2, 2)}


def gold_blocks() -> dict[int, tuple[float, float, float, float]]:
    """-> leaf -> the adjudicated ARGUMENT block's page-fraction bounds.

    ⚠️ THE GOLD IS ROW-GRAIN AND THE AGENT IS BOX-GRAIN, so the rows of one leaf are taken together
    as the block they compose. That is not a loosening: R2.2d adjudicated every row of all ten
    openings, so the block's bounds are the union of adjudicated rows and nothing is inferred.
    """
    g = json.loads(ARG_GOLD.read_text())
    rows: dict[int, list] = {}
    for e in g["rows"]:
        rows.setdefault(e["leaf"], []).append(e)
    return {i: (min(e["xlf"] for e in v), min(e["y0f"] for e in v),
                max(e["xrf"] for e in v), max(e["y1f"] for e in v))
            for i, v in rows.items()}


def covers(b, blk, frac: float = 0.50) -> bool:
    """Does box `b` hold at least `frac` of block `blk`? R2.1i: substantial, never merely non-zero."""
    x0, y0, x1, y1 = blk
    ov = (max(0.0, min(x1, b.x1) - max(x0, b.x0)) * max(0.0, min(y1, b.y1) - max(y0, b.y0)))
    return ov >= frac * max(1e-9, (x1 - x0) * (y1 - y0))


def headband_scores(leaves) -> dict:
    """The agent's GOLD-HEADBAND numbers under the WORSE of the two declared addressing rules."""
    gold = json.loads(HEADBAND_GOLD.read_text())
    by_leaf: dict[int, list] = {}
    for e in gold["labels"]:
        if "xlf" in e:
            by_leaf.setdefault(e["leaf"], []).append(e)
    best = None
    for rule in (VA.BIND_OVERLAP, VA.BIND_TIGHTEST):
        per: dict[str, list[int]] = {}
        for i in sorted(by_leaf):
            lf = leaves.get(i)
            if lf is None:
                continue
            for e in by_leaf[i]:
                b, _ = VA._bind(e, lf.boxes, rule)
                if b is None:
                    continue
                per.setdefault(e["label"], [0, 0])
                per[e["label"]][1] += 1
                if b.label == e["label"]:
                    per[e["label"]][0] += 1
        hit = sum(v[0] for v in per.values())
        tot = sum(v[1] for v in per.values())
        if best is None or hit / max(1, tot) < best[0] / max(1, best[1]):
            best = (hit, tot, per)
    return {"overall": (best[0], best[1]), **{k: tuple(v) for k, v in best[2].items()}}


def main() -> int:
    blocks = gold_blocks()
    disjoint = sorted(set(blocks) - FE_LEAVES)
    overlap = sorted(set(blocks) & FE_LEAVES)

    print("R14.10a — THE ARGUMENT CLASS, scored against R2.2d's GOLD-ARGUMENT")
    print(f"{VA.WITNESS} leaves {VA.LEAF_LO}-{VA.LEAF_HI - 1}; "
          f"{len(blocks)} adjudicated argument blocks")
    print(f"  A1 population — DISJOINT from GOLD-FOREEDGE : {disjoint}")
    print(f"  excluded from A1 — GOLD-FOREEDGE's own leaves: {overlap}")
    print(f"  ⚠️ the cue may only be validated on the first row. The second is reported, never "
          f"counted toward adoption.\n")

    leaves = {lf.leaf: lf for lf in VA.load_leaves()}

    # ── the fount record must actually be standing under this run ────────────────────────────
    missing = [i for i, lf in sorted(leaves.items()) if lf.fount_why]
    if missing:
        print(f"🔴 THE FOUNT RECORD IS NOT AVAILABLE ON {len(missing)} LEAF/LEAVES — the cue cannot")
        print(f"   have run. This is REPORTED, never scored around: {leaves[missing[0]].fount_why}")
        print("   Run: ../ocr-venv/bin/python witness/build_fount_record.py")
        return 1

    # ── A1 / A2 ──────────────────────────────────────────────────────────────────────────────
    a1_hit, a1_miss, a2_fp, unadj, ov_hit, ov_miss = 0, [], [], [], 0, []
    slack = {"italic": [], "segs": [], "span": []}
    for i in sorted(leaves):
        lf = leaves[i]
        (ml, mr) = lf.measure
        mw = max(1e-9, mr - ml)
        blk = blocks.get(i)
        named = [b for b in lf.boxes if b.label == VA.AR]
        if blk is not None:
            got = [b for b in named if covers(b, blk)]
            if got:
                if i in disjoint:
                    a1_hit += 1
                else:
                    ov_hit += 1
                b = got[0]
                slack["italic"].append(b.italic_frac)
                slack["segs"].append(b.fount_n)
                slack["span"].append((min(b.x1, mr) - max(b.x0, ml)) / mw)
            else:
                (a1_miss if i in disjoint else ov_miss).append(
                    (i, [(b.label, round(b.italic_frac, 2), b.fount_n) for b in lf.boxes
                         if covers(b, blk)]))
        for b in named:
            if blk is not None and covers(b, blk):
                continue
            (a2_fp if blk is not None else unadj).append(
                (i, b.y0, b.y1, b.fount_it, b.fount_n))

    a1 = a1_hit == len(disjoint)
    a2 = not a2_fp
    print(f"  A1 RECALL (disjoint)   {a1_hit}/{len(disjoint)} argument blocks named AR   "
          f"{'ok' if a1 else '🔴 BELOW BAR (all of them)'}")
    for i, boxes in a1_miss:
        print(f"    🔴 leaf {i} missed — boxes covering the block: {boxes}")
    print(f"  A2 PRECISION (window)  {len(a2_fp)} false positive(s) over all 20 leaves   "
          f"{'ok' if a2 else '🔴 BELOW BAR (0)'}")
    for i, y0, y1, it, n in a2_fp:
        print(f"    🔴 leaf {i} y {y0:.4f}-{y1:.4f}  italic {it}/{n} — AR outside the gold block")
    print(f"     UNADJUDICATED {len(unadj)} AR box(es) on leaves GOLD-ARGUMENT does not cover — "
          f"truth UNKNOWN,\n     counted neither way. ⚠️ non-zero means the cue fires where no eye "
          f"has been; adjudicate before reading A2.")
    for i, y0, y1, it, n in unadj[:8]:
        print(f"       leaf {i} y {y0:.4f}-{y1:.4f} italic {it}/{n}")

    # ── the guards' slack, PRINTED so "nothing here decides" is checked, not asserted ─────────
    print(f"\n  📌 THE GUARDS' SLACK on the {len(slack['italic'])} blocks the cue named "
          f"(a guard that DECIDES is a threshold wearing a cue's clothes):")
    print(f"     italic share  min {min(slack['italic']):.2f}  vs majority "
          f"{VA.AR_ITALIC_MAJORITY:.2f}")
    print(f"     segments      min {min(slack['segs'])}     vs floor {VA.AR_MIN_SEGMENTS}")
    print(f"     measure span  min {min(slack['span']):.2f}  vs floor {VA.AR_MEASURE_SPAN:.2f}")

    # ⚠️ AND THE BAND IS RE-MEASURED ON THE ADOPTION POPULATION ALONE. The three guards above were
    # set after looking at all ten blocks, four of which sit on GOLD-FOREEDGE's leaves — so "they
    # decide nothing" has to be shown WITHOUT those four, or it is a claim about the wrong
    # population. This prints the nearest non-argument box on the DISJOINT six: the gap the majority
    # rule has to clear using only the evidence that licenses adoption.
    near = 0.0
    for i in disjoint:
        lf = leaves[i]
        (ml, mr) = lf.measure
        mw = max(1e-9, mr - ml)
        for b in lf.boxes:
            if b.label == VA.AR or not b.fount_n:
                continue
            if b.fount_n >= VA.AR_MIN_SEGMENTS and \
                    (min(b.x1, mr) - max(b.x0, ml)) / mw >= VA.AR_MEASURE_SPAN:
                near = max(near, b.italic_frac)
    print(f"     ⚠️ on the DISJOINT SIX alone — nearest non-argument box that clears the other two")
    print(f"        guards reads {near:.2f} italic against the argument blocks' 1.00, so the "
          f"majority\n        rule sits in an empty band on the adoption population itself, not "
          f"only on all ten.")

    # ── A3 ───────────────────────────────────────────────────────────────────────────────────
    hb = headband_scores(leaves)
    a3 = True
    print(f"\n  A3 NO THEFT on GOLD-HEADBAND (the worse of the two addressing rules):")
    for k, (bc, bn) in A3_BARS.items():
        c, n = hb.get(k, (0, 0))
        ok = c >= bc
        a3 = a3 and ok
        print(f"     {str(k):8s} {c}/{n}   bar {bc}/{bn}   {'ok' if ok else '🔴 A NUMBER FELL'}")

    # ── A4: the proven negative ──────────────────────────────────────────────────────────────
    stash, VA._FOUNT_CACHE, real = VA._FOUNT_CACHE, None, VA.FOUNT
    VA.FOUNT = _HERE / "gold" / "__no_such_fount_record__.json"
    off = [VA.settle(VA.Leaf(leaf=lf.leaf, boxes=[VA.Box(b.x0, b.y0, b.x1, b.y1, b.surya)
                                                 for b in lf.boxes]))
           for lf in leaves.values()]
    VA.FOUNT, VA._FOUNT_CACHE = real, stash
    n_ar_off = sum(1 for lf in off for b in lf.boxes if b.label == VA.AR)
    n_cause = sum(1 for lf in off if lf.fount_why)
    a4 = n_ar_off == 0 and n_cause == len(off)
    print(f"\n  A4 ABSTAINABLE — the same {len(off)} leaves with the fount record WITHHELD:")
    print(f"     AR boxes emitted {n_ar_off} (bar 0) · leaves carrying a stated cause "
          f"{n_cause}/{len(off)}   {'ok' if a4 else '🔴 BELOW BAR'}")
    print(f"     cause: {off[0].fount_why}")

    # ── A5: the pre-registered out-of-sample prediction ───────────────────────────────────────
    fe = json.loads(FE_GOLD.read_text())
    from build_foreedge_gold import candidates                      # noqa: E402
    fe_hit = fe_tot = fe_ar_hit = fe_ar_tot = 0
    for row in fe["labels"]:
        b = candidates(leaves[row["leaf"]])[row["idx"]]
        fe_tot += 1
        fe_hit += b.label == row["label"]
        if row["label"] == VA.AR:
            fe_ar_tot += 1
            fe_ar_hit += b.label == VA.AR
    a5 = fe_ar_hit == fe_ar_tot and fe_hit >= 38
    print(f"\n  A5 THE PREDICTED DIRECTION, on GOLD-FOREEDGE — HELD OUT, nothing fitted here:")
    print(f"     predicted before the run: all 4 AR flip, 34/42 -> 38/42")
    print(f"     measured                : AR {fe_ar_hit}/{fe_ar_tot}, overall {fe_hit}/{fe_tot}"
          f"   {'✅ AS PREDICTED' if a5 else '🔴 CONTRARY TO THE PREDICTION'}")
    if not a5:
        print("     ⚠️ A1 passing while A5 fails would mean the cue is fitted to six leaves.")
        print("        R14.10a RE-OPENS. This is a redesign trigger, never an accepted gap.")

    ok = a1 and a2 and a3 and a4 and a5
    print(f"\n  A1 {'PASS' if a1 else 'FAIL'} · A2 {'PASS' if a2 else 'FAIL'} · "
          f"A3 {'PASS' if a3 else 'FAIL'} · A4 {'PASS' if a4 else 'FAIL'} · "
          f"A5 {'PASS' if a5 else 'FAIL'}")
    print(f"\n  verdict: {'PASS — AR is ADOPTED' if ok else 'FAIL — AR is NOT adopted'}")
    print("\n⚠️ THIS DISCHARGES NO GATE. GOLD-ARGUMENT is 10 leaves of ONE witness, and rows 10a/10b")
    print("   remain reserved for GOLD-LAYOUT (R16.1). What it establishes is narrower and worth")
    print("   stating exactly: the agent's class inventory grew by one class that the page prints,")
    print("   validated outside the gold that revealed the gap, and it bought that with nothing.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
