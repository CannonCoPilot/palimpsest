"""R2.2e ACCEPTANCE -- score the REGION-GAP token post-condition against E1-E4, pre-registered in
OCR-ROADMAP.md § "R2.2e PRE-REGISTRATION" and reproduced here verbatim:

  E1  THE DEFECT   -- no token spans a gap wider than the line pitch.   bar: 0 of the 142
  E2  NO REGRESSION on the region gold: acc 0.8760, RH 1.0000, MN 0.8947, MT 0.8375. none may FALL
  E3  THE CONSUMER -- of the 49 rows swallowed whole, the 44 that are NOT argument rows must carry
                      at least one MainText token instead of being typed MarginNote. bar: all 44
  E4  GOLD-ARGUMENT D1 recall (52/81) may not FALL; the 6 misses blamed on R2.2e should clear

**Adoption requires E1-E4 TOGETHER.** `region_head.REGION_GAP_TOKENS` stays False until they hold.

⚠️ NON-CRITERION: the continuity rate, on the same terms as R2.2b and R2.2d.

⚠️ THE 49 ROWS ARE NAMED IN THIS FILE, from the run that raised the step. They are addressed by PAGE
FRACTION, never by row ordinal -- the defect R2.1i, R2.1j and R2.2c each had to remove once, and
which the argument gold's scorer then hit again as a float-EQUALITY (see `score_argument_region`).
Matching here is by BEST OVERLAP for the same reason.
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
import score_argument_region as SA

GOLD = _HERE / "gold/region_gap_rows_OT1-1609-B_400-419.json"
BAR = {"acc": 0.8760, "rh": 1.0000, "mn": 0.8947, "mt": 0.8375}
D1_BAR = 52


def main() -> int:
    g = json.loads(GOLD.read_text())
    want = {}
    for e in g["rows"]:
        want.setdefault(e["leaf"], []).append((e["y0f"], e["y1f"], e["is_argument_row"], e["read"]))
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)

    print("\nR2.2e -- a token may never span a REGION GAP, OT1-1609-B leaves 400-419")
    print("  rule: whatever `split_fn` returns is cut at gaps wider than the line pitch "
          "(`CR.REGION_GAP_P`),\n  the same rule `region_segments` is built on. It can only CUT, "
          "never merge.")
    print(f"  REGION_GAP_TOKENS is currently {RG.REGION_GAP_TOKENS}")

    was_rgt, was_arg = RG.REGION_GAP_TOKENS, RG.ARGUMENT_RULE

    # ── E2 first: it is the one criterion that needs no artefact of this step ──────────────────
    RG.ARGUMENT_RULE = False
    RG.REGION_GAP_TOKENS = False
    off = SR.main(quiet=True)
    RG.REGION_GAP_TOKENS = True
    on = SR.main(quiet=True)
    e2 = all(on[k] >= BAR[k] - 1e-9 for k in BAR)
    print("\n  E2 NO REGRESSION on the 121-token region gold")
    print(f"     rule OFF   acc {off['acc']:.4f}  RH {off['rh']:.4f}  MN {off['mn']:.4f}  "
          f"MT {off['mt']:.4f}")
    print(f"     rule ON    acc {on['acc']:.4f}  RH {on['rh']:.4f}  MN {on['mn']:.4f}  "
          f"MT {on['mt']:.4f}   {'ok' if e2 else '🔴 A NUMBER FELL'}")
    for k in ("scored", "orphans", "unlabelled"):
        if k in off or k in on:
            print(f"     {k:11s} OFF {off.get(k, '-')}  ->  ON {on.get(k, '-')}")

    # ── E1 and E3, with the rule ON ───────────────────────────────────────────────────────────
    RG.REGION_GAP_TOKENS = True
    spanning, e3_hit, e3_tot, e3_miss = 0, 0, 0, []
    for i in range(400, 420):
        band, frame = CR.band_frame(leaves[i], 0.0, 1.0)
        p, src = CR.scale(band)
        if p is None:
            print(f"  ⚠️ ABSTAIN leaf {i}: no type scale ({src})")
            continue
        toks, why = RG.classify(band, p)
        if toks is None:
            print(f"  ⚠️ ABSTAIN leaf {i}: {why}")
            continue
        rows = CR._rows_and_lines(CR.glyph_boxes(band, 0, p), p)
        cut = CR.REGION_GAP_P * float(p)
        ys = {j: (CR.page_y_frac(frame, min(x[0] for x in r)),
                  CR.page_y_frac(frame, max(x[1] for x in r))) for j, r in enumerate(rows)}
        # E1 -- the post-condition itself
        for t in toks:
            gs = sorted([x for x in rows[t["row"]] if x[2] >= t["l"] - 1 and x[3] <= t["r"] + 1],
                        key=lambda x: x[2])
            if len(gs) < 2:
                continue
            if any(gs[k + 1][2] - max(x[3] for x in gs[:k + 1]) > cut for k in range(len(gs) - 1)):
                spanning += 1
        # E3 -- the consumer, over the rows this step was raised on
        by_row = {}
        for t in toks:
            by_row.setdefault(t["row"], []).append(t["label"])
        for y0, y1, is_arg, rd in want.get(i, []):
            if is_arg:
                continue
            e3_tot += 1
            j = SA.best_overlap((y0, y1), ys)
            if j is not None and RG.MAIN_TEXT in by_row.get(j, ()):
                e3_hit += 1
            else:
                e3_miss.append((i, y0, sorted(set(by_row.get(j, ()))) if j is not None else "?", rd))

    e1 = spanning == 0
    print(f"\n  E1 THE DEFECT  {spanning} token(s) still span a region gap "
          f"(142 with the rule off)   {'ok' if e1 else '🔴 BELOW BAR (0)'}")
    print(f"\n  E3 CONSUMER    {e3_hit}/{e3_tot} of the swallowed non-argument rows now carry a "
          f"MainText token   {'ok' if e3_hit == e3_tot else '🔴 BELOW BAR (all of them)'}")
    for i, y, labs, rd in e3_miss[:10]:
        print(f"    🔴 leaf {i} y {y:.4f}  labels {labs}  {rd!r}")
    if len(e3_miss) > 10:
        print(f"       ... and {len(e3_miss) - 10} more")
    e3 = e3_hit == e3_tot

    # ── E4 -- GOLD-ARGUMENT recall, the one gold that can see the argument rows ────────────────
    RG.ARGUMENT_RULE = True
    d1 = _argument_recall(leaves)
    e4 = d1 >= D1_BAR
    print(f"\n  E4 GOLD-ARGUMENT D1 recall {d1}/81 (was {D1_BAR}/81 with the rule off)   "
          f"{'ok' if e4 else '🔴 FELL'}")

    RG.REGION_GAP_TOKENS, RG.ARGUMENT_RULE = was_rgt, was_arg
    ok = e1 and e2 and e3 and e4
    print(f"\n  E1 {'PASS' if e1 else 'FAIL'} · E2 {'PASS' if e2 else 'FAIL'} · "
          f"E3 {'PASS' if e3 else 'FAIL'} · E4 {'PASS' if e4 else 'FAIL'}")
    print(f"\n  verdict: {'PASS' if ok else 'FAIL'}"
          f"{'' if ok else '  -- REGION_GAP_TOKENS stays False; the candidate is NOT adopted'}")
    return 0 if ok else 1


def _argument_recall(leaves):
    """D1 from `score_argument_region`'s gold, recomputed under whatever flags are set."""
    ag = json.loads((_HERE / "gold/argument_rows_OT1-1609-B_400-419.json").read_text())
    want = {}
    for e in ag["rows"]:
        want.setdefault(e["leaf"], []).append((e["y0f"], e["y1f"]))
    hit = 0
    for i in range(400, 420):
        if i not in want:
            continue
        band, frame = CR.band_frame(leaves[i], 0.0, 1.0)
        p, src = CR.scale(band)
        if p is None:
            continue
        toks, why = RG.classify(band, p)
        if toks is None:
            continue
        rows, _f, _p, _w = CR.page_type_rows(leaves[i])
        ys = {j: (CR.page_y_frac(frame, min(x[0] for x in r)),
                  CR.page_y_frac(frame, max(x[1] for x in r))) for j, r in enumerate(rows)}
        got = {t["row"] for t in toks if t["label"] == RG.ARGUMENT}
        for s in want[i]:
            j = SA.best_overlap(s, ys)
            if j is not None and j in got:
                hit += 1
    return hit


if __name__ == "__main__":
    raise SystemExit(main())
