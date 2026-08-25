"""R2.2d ACCEPTANCE -- score the ARGUMENT region rule against D1-D4, pre-registered in OCR-ROADMAP.md.

⚠️ THE CRITERIA WERE WRITTEN BEFORE THE DISCRIMINATOR WAS BUILT and are reproduced here verbatim:

  D1  RECALL     -- every gold ARGUMENT row is labelled ARGUMENT.          bar: all of them
  D2  PRECISION  -- no non-argument row anywhere in the window is ARGUMENT. bar: 0 false positives
  D3  NO REGRESSION on the region gold: acc 0.8760, RH 1.0000, MN 0.8947, MT 0.8375. none may FALL
  D4  THE CONSUMER -- no token on a gold argument row may remain MainText.  bar: all such leaves

**Adoption requires D1-D4 TOGETHER.** `region_head.ARGUMENT_RULE` stays False until they all hold.

⚠️ NON-CRITERION: the continuity rate, on the same terms as R2.2b.

⚠️ D2's SCOPE, AND HOW IT CHANGED. The gold once covered FOUR chapter openings while the whole-page
censuses put argument blocks on TEN, so D2 was a SUBSET result and every ARGUMENT row elsewhere was
reported UNADJUDICATED -- truth unknown, counted neither way. **That caveat is discharged**: the gold
now labels all ten openings row by row and carries `negatives`, the rows adjudicated NOT-ARGUMENT.

⚠️ The negatives were enumerated by RUNNING THE RULE AT A WIDENED NET (`.scratch/r2/
probe_seg_census_all.py`) and adjudicating every hit that fell outside an argument block, so D2 is
now measured against what the rule ACTUALLY EMITS rather than against a row-slant proxy. An ARGUMENT
row matching a negative is a FALSE POSITIVE. One that matches neither gold nor negatives is still
reported UNADJUDICATED -- that can only happen if the rule changes and starts firing somewhere no eye
has been, which is precisely when the label must not be guessed.
"""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W
import collation_read as CR
import region_head as RG
import score_head_regions as SR

GOLD = _HERE / "gold/argument_rows_OT1-1609-B_400-419.json"
BAR = {"acc": 0.8760, "rh": 1.0000, "mn": 0.8947, "mt": 0.8375}


def best_overlap(span, rows_yf):
    """The detected row a gold entry ADDRESSES: the one it overlaps most, or None if none at all.

    ⚠️ EXACT EQUALITY ON A PAGE FRACTION IS NOT AN ADDRESS, and this function exists because that
    was tried and failed on its first run. The gold stores `round(y, 6)` and the scorer compared
    `round(that, 4)` against `round(y, 4)` computed from the page: leaf 417 r51 sits at
    0.66504975, which rounds DIRECTLY to 0.6650 but rounds THROUGH 6 dp to 0.66505 -> 0.6651. One
    row in 81 fell down that crack, and the old code would have counted it as a RECALL MISS -- the
    rule blamed for a defect in the arithmetic. The gold's own `address` note already prescribed
    the fix: **score by page-fraction OVERLAP, never by an equality**.

    ⚠️ BEST overlap, not ANY overlap: curvature makes 39 of 140 consecutive row-pairs overlap by
    more than half (R2.2b), so "any" would let a gold row be satisfied by its NEIGHBOUR and inflate
    D1. One gold row addresses exactly one detected row -- the one it shares the most ink-height
    with.
    """
    a0, a1 = span
    best, best_ov = None, 0.0
    for j, (b0, b1) in rows_yf.items():
        ov = min(a1, b1) - max(a0, b0)
        if ov > best_ov:
            best, best_ov = j, ov
    return best


def leaf_rows(leaf_path):
    rows, frame, p, why = CR.page_type_rows(leaf_path)
    return rows, frame, p, why


def main() -> int:
    g = json.loads(GOLD.read_text())
    want, nope = {}, {}
    for e in g["rows"]:
        want.setdefault(e["leaf"], []).append((e["y0f"], e["y1f"]))
    for e in g.get("negatives", []):
        nope.setdefault(e["leaf"], []).append((e["y0f"], e["y1f"], e["why"]))
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)

    print("\nR2.2d -- the ARGUMENT region, OT1-1609-B leaves 400-419")
    print(f"  rule: a row SEGMENT whose deslanting angle is >= {RG.ARGUMENT_SLANT_MIN:.0f} deg with "
          f">= {RG.ARGUMENT_MIN_COMPONENTS} components is\n  set in ITALIC, and its in-block tokens "
          f"are ARGUMENT. Fount, not position.")
    print(f"  ARGUMENT_RULE is currently {RG.ARGUMENT_RULE}")

    # ── D3, first: it is the one that can be run without the argument gold at all ──────────────
    was = RG.ARGUMENT_RULE
    RG.ARGUMENT_RULE = False
    off = SR.main(quiet=True)
    RG.ARGUMENT_RULE = True
    on = SR.main(quiet=True)
    RG.ARGUMENT_RULE = was
    d3 = all(on[k] >= BAR[k] - 1e-9 for k in BAR)
    print(f"\n  D3 NO REGRESSION on the 121-token region gold")
    print(f"     rule OFF   acc {off['acc']:.4f}  RH {off['rh']:.4f}  MN {off['mn']:.4f}  "
          f"MT {off['mt']:.4f}")
    print(f"     rule ON    acc {on['acc']:.4f}  RH {on['rh']:.4f}  MN {on['mn']:.4f}  "
          f"MT {on['mt']:.4f}   {'ok' if d3 else '🔴 A NUMBER FELL'}")
    print("     ⚠️ That gold holds NO argument rows, so it cannot reward this rule -- it can only "
          "detect\n     collateral damage, which is exactly what it is for here.")

    # ── D1 / D2 / D4, with the rule ON ────────────────────────────────────────────────────────
    RG.ARGUMENT_RULE = True
    hit, miss, fp, unadj, d4_mt, d4_tot = 0, [], [], [], 0, 0
    unplaced, collide = [], []   # gold rows that address no detected row / two that address one
    for i in range(400, 420):
        page, frame = CR.band_frame(leaves[i], 0.0, 1.0)
        p, src = CR.scale(page)
        if p is None:
            print(f"  ⚠️ ABSTAIN leaf {i}: no type scale ({src})")
            continue
        toks, why = RG.classify(page, p)
        if toks is None:
            print(f"  ⚠️ ABSTAIN leaf {i}: {why}")
            continue
        rows, _f, _p, _w = leaf_rows(leaves[i])
        ys = {j: (CR.page_y_frac(frame, min(g_[0] for g_ in r)),
                  CR.page_y_frac(frame, max(g_[1] for g_ in r)))
              for j, r in enumerate(rows)}
        got = {t["row"] for t in toks if t["label"] == RG.ARGUMENT and t["row"] in ys}
        # ⚠️ a LIST, not a dict keyed by the matched row: if two gold rows ever addressed the same
        # detected row, a dict would silently drop one and shrink D1's DENOMINATOR -- a gold that
        # gets easier the worse the addressing gets. Collisions are reported instead.
        mine = [(s, best_overlap(s, ys)) for s in want.get(i, [])]
        neg = {best_overlap((n[0], n[1]), ys): n[2] for n in nope.get(i, [])}
        seen_rows = [j for _s, j in mine if j is not None]
        for j in {j for j in seen_rows if seen_rows.count(j) > 1}:
            collide.append((i, j, seen_rows.count(j)))
        # ⚠️ ADDRESSING GUARD, and it is NOT part of D1. The gold is matched to a detected row by
        # EXACT page-fraction equality, which is stricter than the overlap its own `address` note
        # prescribes. If the row clusterer ever moves a baseline, an entry stops matching anything
        # and would silently be counted as a RECALL MISS -- the rule blamed for a defect in the
        # addressing. A gold row that lands on no detected row at all is an ADDRESSING FAILURE and
        # is reported as one. (Same shape as `test_region_gold_addressing` for the region gold.)
        for s, j in mine:
            if j is None:
                unplaced.append((i, s[0]))
            elif j in got:
                hit += 1
            else:
                miss.append((i, s[0], j))
        gold_rows = {j for _s, j in mine}
        for j in sorted(got - gold_rows):
            (fp if j in neg else unadj).append((i, ys[j][0], neg.get(j, "")))
        # D4 -- the consumer question, at token grain
        for t in toks:
            if t["row"] in gold_rows:
                d4_tot += 1
                if t["label"] == RG.MAIN_TEXT:
                    d4_mt += 1
    RG.ARGUMENT_RULE = was

    tot = sum(len(v) for v in want.values())
    n_neg = sum(len(v) for v in nope.values())
    leaves_g = sorted(want)
    d1 = hit == tot
    d2 = not fp
    d4 = d4_mt == 0
    if collide:
        print(f"\n  🔴 ADDRESSING COLLISION -- {len(collide)} detected row(s) are addressed by more "
              f"than one gold row.\n     D1's denominator is still {tot}; the gold needs re-keying.")
        for i, j, n in collide[:8]:
            print(f"    🔴 leaf {i} row {j} claimed by {n} gold entries")
    if unplaced:
        print(f"\n  🔴 ADDRESSING FAILURE -- {len(unplaced)} gold row(s) overlap no detected row at "
              f"all.\n     NOT a D1 miss; the gold cannot be scored until it is re-keyed to the "
              f"page.")
        for i, y in unplaced[:8]:
            print(f"    🔴 leaf {i} y {y:.4f} unplaced")
    print(f"\n  D1 RECALL      {hit}/{tot} gold argument rows carry an ARGUMENT token   "
          f"{'ok' if d1 else '🔴 BELOW BAR (all of them)'}")
    for i, y, j in miss:
        print(f"    🔴 leaf {i} y {y:.4f} (row {j}) missed")
    print(f"\n  D2 PRECISION   {len(fp)} false positive(s) over the WHOLE 20-leaf window   "
          f"{'ok' if d2 else '🔴 BELOW BAR (0)'}")
    print(f"     scope: all {len(leaves_g)} chapter openings {leaves_g} are labelled row by row, "
          f"and\n     {n_neg} further rows are adjudicated NOT-ARGUMENT. ⚠️ The gold once covered "
          f"FOUR openings,\n     so D2 was a subset result; it is now a whole-window one.")
    for i, y, whyn in fp:
        print(f"    🔴 leaf {i} y {y:.4f}  {whyn}")
    print(f"\n     UNADJUDICATED  {len(unadj)} row(s) labelled ARGUMENT that match neither the gold "
          f"nor a\n     recorded negative -- truth UNKNOWN, so NOT counted either way. ⚠️ A non-zero "
          f"count here\n     means the rule now fires where no eye has been: adjudicate before "
          f"reading D2.")
    for i, y, _w in unadj[:8]:
        print(f"       leaf {i} y {y:.4f}")
    if len(unadj) > 8:
        print(f"       ... and {len(unadj) - 8} more")

    print(f"\n  D4 CONSUMER    tokens on gold argument rows still labelled MainText: "
          f"{d4_mt}/{d4_tot}   {'ok' if d4 else '🔴 BELOW BAR (0)'}")
    print(f"     with the rule OFF this number is 46 -- the defect R2.2d was raised on.")

    ok = d1 and d2 and d3 and d4
    print(f"\n  D1 {'PASS' if d1 else 'FAIL'} · D2 {'PASS' if d2 else 'FAIL'} · "
          f"D3 {'PASS' if d3 else 'FAIL'} · D4 {'PASS' if d4 else 'FAIL'}")
    print(f"\n  verdict: {'PASS' if ok else 'FAIL'}"
          f"{'' if ok else '  -- ARGUMENT_RULE stays False; the rule is NOT adopted'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
