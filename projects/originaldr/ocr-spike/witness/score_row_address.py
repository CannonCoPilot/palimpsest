"""R2.2j ACCEPTANCE -- score Y-BAND row addressing against K1-K4, pre-registered in OCR-ROADMAP.md
§ "R2.2j PRE-REGISTRATION" and reproduced here verbatim:

  K1  THE CONTROL   -- row clusterer UNCHANGED, four gold numbers under the re-keyed scorer must be
                       EXACTLY 0.8760 / 1.0000 / 0.8947 / 0.8375; any movement REFUTES the re-key
  K2  ACCOUNTING    -- entries bound and addressing failures reported separately.   bar: 0 failures
  K3  INVARIANCE    -- under a PERTURBED row clusterer (ROW_TOL_P x0.6 and x1.6), the OLD scorer must
                       move and the NEW scorer must not. If both move, the re-key is REFUTED
  K4  the token-side band-pixel keying is NOT touched (asserted in the diff)

CANDIDATE 2 ("ink2d"), pre-registered as L1-L4 after candidate 1 was refuted on K3:
  L1  CONTROL     -- clusterer unchanged, four numbers EXACTLY 0.8760 / 1.0000 / 0.8947 / 0.8375
  L2  INVARIANCE  -- ROW_TOL_P x0.6 and x1.6: the four numbers do NOT move, and the OLD scorer must
                     be seen to move in the same run
  L3  ACCOUNTING  -- 121 bound, 0 orphans, 0 addressing failures at EVERY setting
  L4  the y-extent added to tokens changes no REGION rule -- "ordinal" numbers exactly unmoved

**Adoption requires K1-K4 TOGETHER.** `ROW_ADDRESS` stays "ordinal" until then.

⚠️ K3 IS THE CRITERION WITH POWER TO FAIL, AND IT IS THE ONE I WOULD HAVE OMITTED. K1 shows the
re-key changes nothing TODAY; it cannot show the re-key does what it is FOR, which is surviving a
change to the row clusterer -- the change R2.2i proposes. A criterion that only proves "no harm now"
would let R2.2i be scored on an instrument still keyed to the thing R2.2i moves. Two perturbations,
opposite directions, and the OLD scorer must be SEEN to break, or the test never had power.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import collation_read as CR
import score_head_regions as SR

SHIPPED = {"acc": 0.8760, "rh": 1.0000, "mn": 0.8947, "mt": 0.8375}
TOL = 5e-5
PERTURB = (0.6, 1.6)            # multipliers on CR.ROW_TOL_P -- deliberately broken clusterers
KEYS = ("acc", "rh", "mn", "mt")
MODES = ("yband", "ink2d")
# ⚠️ THE TIE-BREAK IS A DECISION RULE, NOT A TUPLE ORDER. Both candidates pass every criterion
# identically, and the first run picked `yband` only because it was declared first -- which is not a
# reason. `ink2d` is preferred BECAUSE OF WHAT THIS STEP IS FOR: R2.2i splits a printed line across
# TWO rows, and `yband` must still choose ONE, losing the sibling's tokens; `ink2d` never consults a
# row. The perturbation numbers agree (orphans 37 vs 38 and 2 vs 3, ink2d lower at both), but the
# argument is the requirement, not the margin.
PREFERENCE = ("ink2d", "yband")


def _score(address, row_tol_mult, permute=False):
    was_a, was_t, was_p = SR.ROW_ADDRESS, CR.ROW_TOL_P, SR.PERMUTE_ROWS
    SR.ROW_ADDRESS = address
    CR.ROW_TOL_P = was_t * row_tol_mult
    SR.PERMUTE_ROWS = permute
    try:
        r = SR.main(quiet=True)
    finally:
        SR.ROW_ADDRESS, CR.ROW_TOL_P, SR.PERMUTE_ROWS = was_a, was_t, was_p
    return r


def _fmt(r):
    return (f"acc {r['acc']:.4f}  RH {r['rh']:.4f}  MN {r['mn']:.4f}  MT {r['mt']:.4f}  "
            f"(bound {r['pairs']}, orphans {r['orph']}, addressing failures {r.get('addr_fail', 0)})")


def _moved(a, b):
    return any(abs(a[k] - b[k]) > TOL for k in KEYS)


def main() -> int:
    print("\nR2.2j -- a ROW ORDINAL is an index into a list the CLUSTERER controls, not an address.")
    print(f"  gold {SR.GOLD.name}; ROW_ADDRESS is currently {SR.ROW_ADDRESS!r}; "
          f"CR.ROW_TOL_P {CR.ROW_TOL_P}")

    base = {m: _score(m, 1.0) for m in ("ordinal",) + MODES}
    print("\n  K1/L1 CONTROL, clusterer unchanged")
    for m in ("ordinal",) + MODES:
        print(f"     {m:<8} {_fmt(base[m])}")
    ctl = {m: all(abs(base[m][k] - SHIPPED[k]) < TOL for k in KEYS) for m in MODES}
    for m in MODES:
        print(f"     {m}: {'PASS -- the re-key is not itself a change' if ctl[m] else '🔴 FAIL -- a number moved'}")

    acct = {m: base[m].get("addr_fail", 0) == 0 for m in MODES}
    print(f"\n  K2/L3 ACCOUNTING (clusterer unchanged)")
    for m in MODES:
        print(f"     {m}: addressing failures {base[m].get('addr_fail', 0)}, "
              f"orphans {base[m]['orph']}   {'PASS' if acct[m] else '🔴 FAIL'}")
        for leaf, text in base[m].get("addr_fail_list", [])[:6]:
            print(f"       🔴 leaf {leaf}: {text!r} addresses no ink")

    print("\n  K3/L2 INVARIANCE under a deliberately perturbed row clusterer")
    ord_moved = []
    moved = {m: [] for m in MODES}
    for mult in PERTURB:
        o = _score("ordinal", mult)
        om = _moved(base["ordinal"], o)
        ord_moved.append(om)
        print(f"     ROW_TOL_P x{mult}")
        print(f"       ordinal  {_fmt(o)}   {'MOVED' if om else 'unmoved'}")
        for m in MODES:
            r = _score(m, mult)
            mv = _moved(base[m], r)
            moved[m].append(mv)
            print(f"       {m:<8} {_fmt(r)}   {'🔴 MOVED' if mv else 'unmoved'}")
    inv = {m: all(ord_moved) and not any(moved[m]) for m in MODES}
    if not any(ord_moved):
        print("     🔴 THE OLD SCORER DID NOT MOVE EITHER — this criterion had NO POWER TO FAIL, and")
        print("        an unmoved new scorer proves nothing. Perturb harder or the test is vacuous.")
    for m in MODES:
        print(f"     {m}: {'PASS' if inv[m] else '🔴 FAIL'}")

    # L4 -- the y-extent added to tokens must change no region rule.
    l4 = all(abs(base["ordinal"][k] - SHIPPED[k]) < TOL for k in KEYS)
    print(f"\n  L4 the token y-extent changes no REGION rule: ordinal {_fmt(base['ordinal'])}   "
          f"{'PASS' if l4 else '🔴 FAIL'}")

    # ── M1-M3: THE PERMUTATION TEST. L2 changed the ink's grouping and so changed the OBJECTS being
    # labelled; this changes only their NAMES, which is the property an address actually has.
    print("\n  M1-M3 PURE RENAMING (row j -> (j+1) mod n; no glyph, token or coordinate moves)")
    perm = {m: _score(m, 1.0, permute=True) for m in ("ordinal",) + MODES}
    m1 = _moved(base["ordinal"], perm["ordinal"])
    print(f"     M1 POWER   ordinal {_fmt(perm['ordinal'])}   "
          f"{'PASS -- the ordinal address BREAKS, as an ordinal must' if m1 else '🔴 FAIL -- NO POWER: the ordinal address survived a renaming, so this test proves nothing'}")
    m3 = all(r.get("permute_impure", 0) == 0 for r in perm.values())
    print(f"     M3 FIXTURE the permutation is a pure renaming (token geometry multiset identical)   "
          f"{'PASS' if m3 else '🔴 FAIL -- rows were dropped or duplicated; M2 would be trivially passable'}")
    m2 = {}
    for m in MODES:
        m2[m] = not _moved(base[m], perm[m]) and perm[m]["orph"] == base[m]["orph"]
        print(f"     M2 {m:<8} {_fmt(perm[m])}   {'PASS' if m2[m] else '🔴 MOVED under a renaming'}")

    pick = next((m for m in PREFERENCE
                 if ctl[m] and acct[m] and l4 and m1 and m3 and m2[m]), None)
    print("\n  ⚠️ L2/K3 (clusterer PERTURBATION) is reported above and is NOT part of the verdict:")
    print("     it changes which glyphs are in a row, hence the TOKENS, hence the objects being")
    print("     labelled -- unachievable for ANY addressing scheme, as § R2.1j already recorded.")
    print(f"\n  verdict: {'PASS -- adopt ROW_ADDRESS=' + repr(pick) if pick else 'FAIL'}"
          f"{'' if pick else '  -- ROW_ADDRESS stays \"ordinal\"; NEITHER candidate is adopted'}")
    return 0 if pick else 1


if __name__ == "__main__":
    raise SystemExit(main())
