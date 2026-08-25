"""R2.2h ACCEPTANCE -- score the FULL R2.2e CHAIN against J1-J7, pre-registered in OCR-ROADMAP.md
§ "R2.2h PRE-REGISTRATION" and reproduced here verbatim:

  J1  THE CONSUMER over the full chain -- all 43 swallowed body rows carry MainText.   bar: 43/43
  J2  THE REGION GOLD over the full chain vs shipped 0.8760 / 1.0000 / 0.8947 / 0.8375.
                                                 bar: none may fall, and acc must EXCEED 0.8760
  J3  THE RUNNING HEAD -- RH recall with R2.2h ALONE, every other flag off.             bar: 1.0000
  J4  THE ESTIMATOR -- rows starting left of L / ending right of R, per leaf, before and after; the
      out-of-block row count must DROP on 403, 409 and 411
  J5  ABSTENTIONS -- leaves where the fixed point does not settle or edge support fails.  bar: 0
  J6  GOLD-ARGUMENT D1 (52/81) may not fall.                                             bar: >= 52
  J7  ATTRIBUTION -- J1/J2 for R2.2h ALONE and for each flag combination

**Adoption requires J1-J6 TOGETHER and adopts all four flags as ONE change or none.** Accuracy
outranks the consumer count when choosing between FLUSH_MODE settings (J2 before J1): a promoted row
raises the consumer while corrupting the label.

⚠️ WHY THIS SCORER VARIES COMBINATIONS RATHER THAN ONE FLAG. R2.2f and R2.2g were each scored alone
and each was refuted alone; R2.2g's H4 then showed the three together produce a repair on every gold
number. A criterion set that varies one flag cannot see a cycle. J7 keeps that from becoming a
licence to credit the chain's repair to whichever link is being written up.
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
import score_region_gap_tokens as SG
import score_block_span as SB
import score_r4_segment as S4

SHIPPED = {"acc": 0.8760, "rh": 1.0000, "mn": 0.8947, "mt": 0.8375}
TOL = 5e-5
D1_BAR = 52
PROBE_LEAVES = (403, 409, 411)          # J4 -- the three the survivors came from

# (label, EDGE_FIXED_POINT, FLUSH_MODE, BLOCK_SPAN_QUALIFIES, R4_PER_SEGMENT)
COMBOS = (
    ("shipped            ", False, "both", False, False),
    ("R2.2h ALONE        ", True, "both", False, False),
    ("h + reach          ", True, "reach", False, False),
    ("h + reach + span   ", True, "reach", True, False),
    ("FULL CHAIN reach   ", True, "reach", True, True),
    ("FULL CHAIN r_right ", True, "reach_right", True, True),
)


def _edges(leaves):
    """J4 -- per leaf: rows outside the estimated block on each side, and any abstention."""
    out = {}
    for i in PROBE_LEAVES:
        band, _f = CR.band_frame(leaves[i], 0.0, 1.0)
        p, _s = CR.scale(band)
        if p is None:
            out[i] = ("no type scale", None)
            continue
        allt, _w = RG.tokens(band, p)
        LR, why = RG.block_measure(allt, p)
        if LR is None:
            out[i] = (why, None)
            continue
        L, R = LR
        tol = max(RG.EDGE_TOL_P * p, RG.FLUSH_TOL_M * (R - L))
        rows = {}
        for t in allt:
            if t["n_glyphs"] < RG.MIN_GLYPHS:
                continue
            a, b = rows.get(t["row"], (t["l"], t["r"]))
            rows[t["row"]] = (min(a, t["l"]), max(b, t["r"]))
        out[i] = (None, {
            "L": L, "R": R, "n": len(rows),
            "left_of": sum(1 for a, _ in rows.values() if a < L - tol),
            "right_of": sum(1 for _, b in rows.values() if b > R + tol),
        })
    return out


def _run(leaves, want, combo):
    _lab, fp, mode, span_on, seg_on = combo
    RG.EDGE_FIXED_POINT, RG.FLUSH_MODE = fp, mode
    RG.BLOCK_SPAN_QUALIFIES, RG.R4_PER_SEGMENT = span_on, seg_on
    RG.REGION_GAP_TOKENS = RG.ARGUMENT_RULE = False
    reg = SR.main(quiet=True)
    hit, tot, miss, _m = SB._consumer_and_merges(leaves, want)
    entry, why, _d = S4._entry_label(leaves)
    edges = _edges(leaves)
    RG.ARGUMENT_RULE = True
    d1 = SG._argument_recall(leaves)
    RG.ARGUMENT_RULE = False
    return {"reg": reg, "hit": hit, "tot": tot, "miss": miss, "d1": d1,
            "entry": entry or f"?({why})", "edges": edges}


def main() -> int:
    gap = json.loads(SB.GOLD.read_text())
    want = {}
    for e in gap["rows"]:
        if not e["is_argument_row"]:
            want.setdefault(e["leaf"], []).append((e["y0f"], e["y1f"], e["read"]))
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)
    was = (RG.EDGE_FIXED_POINT, RG.FLUSH_MODE, RG.BLOCK_SPAN_QUALIFIES,
           RG.REGION_GAP_TOKENS, RG.R4_PER_SEGMENT, RG.ARGUMENT_RULE)

    print("\nR2.2h -- ONE TOLERANCE FOR ONE EDGE, by fixed point. The FULL R2.2e chain, "
          "OT1-1609-B 400-419")
    print("  the estimator's window was EDGE_TOL_P*p (13px at pitch 38); the in-block test uses\n"
          "  max(0.35p, 0.03*measure) (27px). They are iterated to a common value. J7 varies\n"
          "  COMBINATIONS, because R2.2f and R2.2g are each unreachable while the other is open.")

    got = {}
    for combo in COMBOS:
        lab = combo[0]
        r = _run(leaves, want, combo)
        got[lab] = r
        reg = r["reg"]
        print(f"\n  ── {lab.strip()} ──")
        print(f"     acc {reg['acc']:.4f}  RH {reg['rh']:.4f}  MN {reg['mn']:.4f}  MT {reg['mt']:.4f}"
              f"   consumer {r['hit']}/{r['tot']}   D1 {r['d1']}/81   entry {r['entry']}")
        for i, (why, e) in r["edges"].items():
            if why:
                print(f"     🔴 leaf {i} ABSTAINED: {why}")
            else:
                print(f"     leaf {i}: L={e['L']:.0f} R={e['R']:.0f} of {e['n']} rows — "
                      f"{e['left_of']} start LEFT of the block, {e['right_of']} end RIGHT of it")

    RG.EDGE_FIXED_POINT, RG.FLUSH_MODE, RG.BLOCK_SPAN_QUALIFIES, \
        RG.REGION_GAP_TOKENS, RG.R4_PER_SEGMENT, RG.ARGUMENT_RULE = was

    ship, alone = got[COMBOS[0][0]], got[COMBOS[1][0]]
    print("\n  ══ VERDICT ══")
    print(f"     J3 RH, R2.2h alone  {alone['reg']['rh']:.4f}   "
          f"{'PASS' if alone['reg']['rh'] >= 1.0 - TOL else '🔴 FAIL'}")
    j4 = all(alone["edges"][i][1] and ship["edges"][i][1]
             and (alone["edges"][i][1]["left_of"] + alone["edges"][i][1]["right_of"])
             < (ship["edges"][i][1]["left_of"] + ship["edges"][i][1]["right_of"])
             for i in PROBE_LEAVES)
    print(f"     J4 out-of-block rows drop on 403/409/411   {'PASS' if j4 else '🔴 FAIL'}")
    j5 = all(e[0] is None for r in got.values() for e in r["edges"].values())
    print(f"     J5 abstentions      {'PASS (none)' if j5 else '🔴 at least one leaf abstained'}")

    pick = None
    for lab in (COMBOS[5][0], COMBOS[4][0]):        # J2 before J1: accuracy outranks the consumer
        r = got[lab]
        j1 = r["hit"] == r["tot"]
        j2 = all(r["reg"][k] >= SHIPPED[k] - TOL for k in SHIPPED) and \
            r["reg"]["acc"] > SHIPPED["acc"] + TOL
        j6 = r["d1"] >= D1_BAR
        print(f"\n   {lab.strip()}")
        print(f"     J1 consumer {r['hit']}/{r['tot']}   {'PASS' if j1 else '🔴 FAIL'}")
        for i, y, labs, rd in r["miss"][:6]:
            print(f"        🔴 leaf {i} y {y:.4f} labels {labs} {rd!r}")
        print(f"     J2 gold acc {r['reg']['acc']:.4f} RH {r['reg']['rh']:.4f} "
              f"MN {r['reg']['mn']:.4f} MT {r['reg']['mt']:.4f}   {'PASS' if j2 else '🔴 FAIL'}")
        print(f"     J6 D1 {r['d1']}/81   {'PASS' if j6 else '🔴 FAIL'}")
        if j1 and j2 and j6 and j4 and j5 and alone["reg"]["rh"] >= 1.0 - TOL and pick is None:
            pick = lab.strip()
    print(f"\n  verdict: {'PASS -- adopt the CHAIN as one change: ' + pick if pick else 'FAIL'}"
          f"{'' if pick else '  -- all four flags stay OFF; the chain is NOT adopted'}")
    return 0 if pick else 1


if __name__ == "__main__":
    raise SystemExit(main())
