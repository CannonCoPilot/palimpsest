"""R2.2e-b ACCEPTANCE -- score the SPAN QUALIFIER against F1-F4, pre-registered in OCR-ROADMAP.md
§ "R2.2e-b PRE-REGISTRATION" and reproduced here verbatim:

  F1  THE CONSUMER   -- each of the 43 swallowed BODY rows carries a MainText token.  bar: all 43
  F2  NO REGRESSION  -- region gold acc 0.8760, RH 1.0000, MN 0.8947, MT 0.8375. none may FALL
  F3  GOLD-ARGUMENT D1 recall (52/81) may not FALL.                                   bar: >= 52
  F4  THE INTERACTION -- F1/F2/F3 and the merge count reported for the qualifier ALONE and COMPOSED
      with the region-gap cut; a composition is adopted only if it beats the qualifier alone on F1
      WITHOUT losing F2

**Adoption requires F1-F3 TOGETHER**, F4 decides WHICH configuration. `BLOCK_SPAN_QUALIFIES` stays
False until then.

⚠️ WHY BOTH CONFIGURATIONS RUN. A token merged across a region gap (body + marginal note) also spans
the measure, so the qualifier ALONE would call the merge in-block and MASK the defect E1 measured.
Reporting one configuration would let a masked defect read as a pass.
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
import score_region_gap_tokens as SG

GOLD = _HERE / "gold/region_gap_rows_OT1-1609-B_400-419.json"
BAR = {"acc": 0.8760, "rh": 1.0000, "mn": 0.8947, "mt": 0.8375}
D1_BAR = 52
CONFIGS = (("qualifier ALONE", True, False), ("COMPOSED with the region-gap cut", True, True))


def _consumer_and_merges(leaves, want):
    """-> (rows carrying MainText, rows total, misses, tokens still spanning a region gap)."""
    hit, tot, miss, spanning = 0, 0, [], 0
    for i in range(400, 420):
        band, frame = CR.band_frame(leaves[i], 0.0, 1.0)
        p, src = CR.scale(band)
        if p is None:
            continue
        toks, why = RG.classify(band, p)
        if toks is None:
            continue
        rows = CR._rows_and_lines(CR.glyph_boxes(band, 0, p), p)
        cut = CR.REGION_GAP_P * float(p)
        ys = {j: (CR.page_y_frac(frame, min(x[0] for x in r)),
                  CR.page_y_frac(frame, max(x[1] for x in r))) for j, r in enumerate(rows)}
        by_row = {}
        for t in toks:
            by_row.setdefault(t["row"], []).append(t["label"])
            gs = sorted([x for x in rows[t["row"]] if x[2] >= t["l"] - 1 and x[3] <= t["r"] + 1],
                        key=lambda x: x[2])
            if len(gs) > 1 and any(
                    gs[k + 1][2] - max(x[3] for x in gs[:k + 1]) > cut for k in range(len(gs) - 1)):
                spanning += 1
        for y0, y1, rd in want.get(i, []):
            tot += 1
            j = SA.best_overlap((y0, y1), ys)
            if j is not None and RG.MAIN_TEXT in by_row.get(j, ()):
                hit += 1
            else:
                miss.append((i, y0, sorted(set(by_row.get(j, ()))) if j is not None else "?", rd))
    return hit, tot, miss, spanning


def main() -> int:
    g = json.loads(GOLD.read_text())
    want = {}
    for e in g["rows"]:
        if not e["is_argument_row"]:
            want.setdefault(e["leaf"], []).append((e["y0f"], e["y1f"], e["read"]))
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)
    was = (RG.BLOCK_SPAN_QUALIFIES, RG.REGION_GAP_TOKENS, RG.ARGUMENT_RULE)

    print("\nR2.2e-b -- a token that SPANS THE MEASURE is in the block, OT1-1609-B leaves 400-419")
    print(f"  rule: `in_block` also holds when (r - l) >= BODY_SPAN_M ({RG.BODY_SPAN_M}) x measure. "
          f"R3's\n  existing constant, not a new one -- a justified line is FULL, and marginalia is "
          f"set BESIDE\n  the measure, not across it.")
    print(f"  BLOCK_SPAN_QUALIFIES is currently {RG.BLOCK_SPAN_QUALIFIES}")

    RG.ARGUMENT_RULE = False
    RG.BLOCK_SPAN_QUALIFIES = RG.REGION_GAP_TOKENS = False
    base = SR.main(quiet=True)
    _h, _t, _m, base_merges = _consumer_and_merges(leaves, want)
    print(f"\n  BASELINE (both rules off)  acc {base['acc']:.4f}  RH {base['rh']:.4f}  "
          f"MN {base['mn']:.4f}  MT {base['mt']:.4f}   consumer {_h}/{_t}   merges {base_merges}")

    results = {}
    for name, span_on, gap_on in CONFIGS:
        RG.BLOCK_SPAN_QUALIFIES, RG.REGION_GAP_TOKENS = span_on, gap_on
        RG.ARGUMENT_RULE = False
        reg = SR.main(quiet=True)
        hit, tot, miss, merges = _consumer_and_merges(leaves, want)
        RG.ARGUMENT_RULE = True
        d1 = SG._argument_recall(leaves)
        RG.ARGUMENT_RULE = False
        f1, f2, f3 = hit == tot, all(reg[k] >= BAR[k] - 1e-9 for k in BAR), d1 >= D1_BAR
        results[name] = (f1, f2, f3, hit, tot, reg, d1, merges, miss)
        print(f"\n  ── {name} ──")
        print(f"     F1 CONSUMER   {hit}/{tot} swallowed body rows carry a MainText token   "
              f"{'ok' if f1 else '🔴 BELOW BAR (all of them)'}")
        for i, y, labs, rd in miss[:6]:
            print(f"       🔴 leaf {i} y {y:.4f}  labels {labs}  {rd!r}")
        if len(miss) > 6:
            print(f"          ... and {len(miss) - 6} more")
        print(f"     F2 REGION GOLD  acc {reg['acc']:.4f}  RH {reg['rh']:.4f}  MN {reg['mn']:.4f}  "
              f"MT {reg['mt']:.4f}   {'ok' if f2 else '🔴 A NUMBER FELL'}")
        print(f"     F3 GOLD-ARGUMENT D1 {d1}/81   {'ok' if f3 else '🔴 FELL'}")
        print(f"     F4 merges still spanning a region gap: {merges} "
              f"(baseline {base_merges})")

    RG.BLOCK_SPAN_QUALIFIES, RG.REGION_GAP_TOKENS, RG.ARGUMENT_RULE = was

    alone, comp = results[CONFIGS[0][0]], results[CONFIGS[1][0]]
    print("\n  F4 THE INTERACTION")
    print(f"     consumer   alone {alone[3]}/{alone[4]}   composed {comp[3]}/{comp[4]}")
    print(f"     merges     alone {alone[7]}          composed {comp[7]}")
    print("     ⚠️ A merged token spans the measure too, so the qualifier ALONE calling a merge")
    print("     in-block is the masking this criterion exists to expose.")
    pick = None
    if comp[0] and comp[1] and comp[2] and (comp[3] >= alone[3]):
        pick = CONFIGS[1][0]
    elif alone[0] and alone[1] and alone[2]:
        pick = CONFIGS[0][0]
    ok = pick is not None
    for name, r in results.items():
        print(f"\n  {name}: F1 {'PASS' if r[0] else 'FAIL'} · F2 {'PASS' if r[1] else 'FAIL'} · "
              f"F3 {'PASS' if r[2] else 'FAIL'}")
    print(f"\n  verdict: {'PASS -- adopt: ' + pick if ok else 'FAIL'}"
          f"{'' if ok else '  -- BLOCK_SPAN_QUALIFIES stays False; the candidate is NOT adopted'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
