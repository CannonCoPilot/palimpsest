"""R2.2g ACCEPTANCE -- score ONE-SIDED FLUSHNESS against H1-H5, pre-registered in OCR-ROADMAP.md
§ "R2.2g PRE-REGISTRATION" and reproduced here verbatim:

  H1  THE CONSUMER   -- span qualifier ON, each of the 43 swallowed BODY rows carries a MainText
                        token. The chain predicts 23 + 20 = 43.                     bar: all 43
  H2  NO REGRESSION  -- region gold reported for EVERY FLUSH_MODE in BOTH qualifier states against
                        the shipped 0.8760 / 1.0000 / 0.8947 / 0.8375. acc, RH, MT may not fall;
                        MN exempted ONLY to the 1 entry R2.2f owns, which H4 must then recover
  H3  THE RUNNING HEAD -- RH recall with the flush change and the qualifier OFF.  bar: 1.0000
  H4  THE CHAIN      -- all three flags ON: leaf 412 r2 `pinces are` is MarginNote AND MN >= 0.8947
  H5  GOLD-ARGUMENT D1 (52/81, 55/81 with the qualifier on) may not FALL.          bar: >= 52

**Adoption of `FLUSH_MODE` requires H1 + H2 + H3 + H5.** H4 additionally decides whether R2.2f may be
adopted alongside it, by re-running `score_r4_segment` UNCHANGED.

⚠️ A configuration that raises MainText while LOWERING accuracy is NOT adopted whatever H1 says --
mislabelled marginalia is scored somewhere, so MT can rise on exactly the failure H3 guards against.

⚠️ WHY THIS SCORER EXISTS RATHER THAN A WIDER `score_block_span`. R2.2f measured that these links form
a CYCLE: each is unreachable while the other is open, so a scorer that varies one flag cannot see
either. H4 varies all three at once and is the only criterion in the chain that can come back clean.
"""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W
import region_head as RG
import score_head_regions as SR
import score_region_gap_tokens as SG
import score_block_span as SB
import score_r4_segment as S4

SHIPPED = {"acc": 0.8760, "rh": 1.0000, "mn": 0.8947, "mt": 0.8375}
TOL = 5e-5              # the bars are 4-dp transcriptions -- see score_r4_segment, G3
MODES = ("both", "reach", "reach_right")
D1_BAR = 52


def _row(leaves, want, mode, span_on, seg_on):
    """-> dict of every number the criteria read, for one (FLUSH_MODE, flags) configuration."""
    RG.FLUSH_MODE = mode
    RG.BLOCK_SPAN_QUALIFIES, RG.R4_PER_SEGMENT = span_on, seg_on
    RG.REGION_GAP_TOKENS = RG.ARGUMENT_RULE = False
    reg = SR.main(quiet=True)
    hit, tot, miss, _merges = SB._consumer_and_merges(leaves, want)
    lab, why, _diag = S4._entry_label(leaves)
    RG.ARGUMENT_RULE = True
    d1 = SG._argument_recall(leaves)
    RG.ARGUMENT_RULE = False
    return {"reg": reg, "hit": hit, "tot": tot, "miss": miss, "entry": lab or f"?({why})", "d1": d1}


def main() -> int:
    gap = json.loads(SB.GOLD.read_text())
    want = {}
    for e in gap["rows"]:
        if not e["is_argument_row"]:
            want.setdefault(e["leaf"], []).append((e["y0f"], e["y1f"], e["read"]))
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)
    was = (RG.FLUSH_MODE, RG.BLOCK_SPAN_QUALIFIES, RG.REGION_GAP_TOKENS,
           RG.R4_PER_SEGMENT, RG.ARGUMENT_RULE)

    print("\nR2.2g -- FLUSHNESS IS ONE-SIDED: a justified line REACHES its edge, and running PAST the")
    print("  modal edge is not a failure to be flush. OT1-1609-B leaves 400-419.")
    print(f"  FLUSH_MODE is currently {RG.FLUSH_MODE!r}; shipped bars "
          f"{SHIPPED['acc']:.4f} / {SHIPPED['rh']:.4f} / {SHIPPED['mn']:.4f} / {SHIPPED['mt']:.4f}")

    grid = {}
    for mode in MODES:
        for span_on in (False, True):
            r = _row(leaves, want, mode, span_on, False)
            grid[(mode, span_on)] = r
            reg = r["reg"]
            print(f"\n  ── FLUSH_MODE={mode!r}  span qualifier {'ON ' if span_on else 'OFF'} ──")
            print(f"     acc {reg['acc']:.4f}  RH {reg['rh']:.4f}  MN {reg['mn']:.4f}  "
                  f"MT {reg['mt']:.4f}   consumer {r['hit']}/{r['tot']}   D1 {r['d1']}/81   "
                  f"entry {r['entry']}")

    # H4 -- THE CHAIN. All three flags on, for each candidate mode.
    chain = {}
    print("\n  ══ H4 THE CHAIN (FLUSH_MODE + span qualifier + per-segment R4, all ON) ══")
    for mode in MODES[1:]:
        r = _row(leaves, want, mode, True, True)
        chain[mode] = r
        reg = r["reg"]
        print(f"     {mode!r}: acc {reg['acc']:.4f}  RH {reg['rh']:.4f}  MN {reg['mn']:.4f}  "
              f"MT {reg['mt']:.4f}   consumer {r['hit']}/{r['tot']}   entry {r['entry']}")

    RG.FLUSH_MODE, RG.BLOCK_SPAN_QUALIFIES, RG.REGION_GAP_TOKENS, \
        RG.R4_PER_SEGMENT, RG.ARGUMENT_RULE = was

    print("\n  ══ VERDICT, per candidate mode ══")
    pick = None
    for mode in MODES[1:]:
        on, off, ch = grid[(mode, True)], grid[(mode, False)], chain[mode]
        h1 = on["hit"] == on["tot"]
        # MN is exempted only DOWNWARD to the single entry R2.2f owns; acc/RH/MT may not fall.
        h2 = all(on["reg"][k] >= SHIPPED[k] - TOL for k in ("acc", "rh", "mt")) and \
            all(off["reg"][k] >= SHIPPED[k] - TOL for k in ("acc", "rh", "mt"))
        h3 = off["reg"]["rh"] >= 1.0 - TOL
        h4 = ch["entry"] == RG.MARGIN_NOTE and ch["reg"]["mn"] >= SHIPPED["mn"] - TOL
        h5 = on["d1"] >= D1_BAR and off["d1"] >= D1_BAR
        # ⚠️ The clause that outranks H1: MT up while accuracy down is the promoted-row failure.
        traded = on["reg"]["mt"] > SHIPPED["mt"] and on["reg"]["acc"] < SHIPPED["acc"] - TOL
        ok = h1 and h2 and h3 and h5 and not traded
        print(f"\n   {mode!r}")
        print(f"     H1 consumer {on['hit']}/{on['tot']}          {'PASS' if h1 else '🔴 FAIL'}")
        for i, y, labs, rd in on["miss"][:4]:
            print(f"        🔴 leaf {i} y {y:.4f} labels {labs} {rd!r}")
        print(f"     H2 acc/RH/MT not falling      {'PASS' if h2 else '🔴 FAIL'}"
              f"   (MN {on['reg']['mn']:.4f}, exempt only to R2.2f's 1 entry)")
        print(f"     H3 RH qualifier OFF {off['reg']['rh']:.4f}   {'PASS' if h3 else '🔴 FAIL'}")
        print(f"     H4 chain  entry {ch['entry']}  MN {ch['reg']['mn']:.4f}   "
              f"{'PASS -- R2.2f adoptable too' if h4 else '🔴 the cycle is NOT resolved'}")
        print(f"     H5 D1 {off['d1']}/81 off, {on['d1']}/81 on   {'PASS' if h5 else '🔴 FAIL'}")
        if traded:
            print("     🔴 MT ROSE WHILE ACCURACY FELL -- rows were promoted, not repaired. "
                  "NOT adopted whatever H1 says.")
        if ok and pick is None:
            pick = mode
    print(f"\n  verdict: {'PASS -- adopt FLUSH_MODE=' + repr(pick) if pick else 'FAIL'}"
          f"{'' if pick else '  -- FLUSH_MODE stays \"both\"; the candidate is NOT adopted'}")
    return 0 if pick else 1


if __name__ == "__main__":
    raise SystemExit(main())
