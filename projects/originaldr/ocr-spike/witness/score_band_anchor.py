"""R2.2b ACCEPTANCE -- score the ANCHORED head band against A1-A4, pre-registered in OCR-ROADMAP.md.

⚠️ THE CRITERIA WERE WRITTEN BEFORE THE ANCHOR WAS BUILT and are reproduced here verbatim. This
module does not get to choose what counts as success:

  A1  the band CONTAINS THE FIRST BODY LINE, per leaf, against the hand-labelled set -- directly,
      never through continuity.                                    bar 20/20
  A2  the band CONTAINS EVERY LABELLED GOLD ENTRY (R2.2c's C3, inherited).
                                                                   bar 121/121, RunningHead 20/20
  A3  the anchor is GENUINELY ANCHORED: no page fraction in its derivation, and the resulting bounds
      DIFFER ACROSS LEAVES. Constant bounds ⇒ FAIL -- a "measured" anchor that lands in the same
      place every time is a fraction with extra steps.
  A4  the reader is NOT MADE WORSE: `read_first_words_typed` abstains no more often on the anchored
      band than on the frozen one.                                 both reported

**Adoption requires A1-A4 TOGETHER.** Any one failing means the anchored band is NOT adopted,
`HEAD_BAND` stays frozen, and the failure is the finding.

⚠️ EXPLICIT NON-CRITERION, from the pre-registration: THE CONTINUITY RATE IS NOT THE ACCEPTANCE and
may not be quoted as one. R2.1f fired precisely because 0.312 is a joint measure of two readers and
a scorer. This module does not compute it, and a band that raised it while failing A1-A4 would still
be refused.

⚠️ A1 IS SCORED OFF THE GOLD'S PAGE-ANCHORED ADDRESS (R2.2c's `y0f`/`y1f`), which is the whole reason
that address had to exist: "does this band contain that line" is a question about the PAGE, and it
cannot even be asked while the gold's only address is pixels in a different crop.

    python witness/score_band_anchor.py            # A1-A3 (fast)
    python witness/score_band_anchor.py --with-a4  # adds A4; runs the recogniser, several minutes
"""

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import witnesses as W
import collation_read as CR
import region_head as RG

GOLD = _HERE / "gold/head_regions_OT1-1609-B_400-419.json"
# R2.2b -- A1's own reference set. ⚠️ It exists because A1 could not be evaluated against the region
# gold at all: on a CHAPTER-OPENING leaf the first line of scripture lies BELOW that gold's 3-row
# window, so leaves 403 and 411 had no MainText entry and the criterion fell silent on exactly the
# two leaves where it binds hardest. See that file's `_doc`.
FBGOLD = _HERE / "gold/first_body_line_OT1-1609-B_400-419.json"
MODEL = _HERE.parent / "models/reichenau_dr.mlmodel"
LEAVES = range(400, 420)

BAR_A1 = 20         # leaves whose first body line the band must contain
BAR_A2_RH = 20      # RunningHead entries the band must contain


def first_body_lines():
    """-> {leaf: (y0f, y1f, text, basis)} from GOLD-FIRSTBODY, one entry per leaf in the window."""
    d = json.loads(FBGOLD.read_text())
    return {e["leaf"]: (e["y0f"], e["y1f"], e["text"], e["basis"]) for e in d["leaves"]}


def main(with_a4=False) -> int:
    g = json.loads(GOLD.read_text())
    entries = g["labels"]
    if not all("y0f" in e for e in entries):
        print("🔴 the gold carries no page-anchored address -- run witness/gold_rekey_pagefrac.py")
        return 1
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == "OT1-1609-B"][0]
    leaves = W.leaves(vol, sig)

    print("\nR2.2b -- the ANCHORED head band, OT1-1609-B leaves 400-419")
    print(f"  mechanism: the first {CR.ANCHOR_ROWS} rows of type on the WHOLE PAGE, padded "
          f"{CR.ANCHOR_PAD_P} pitch\n  N is fixed from the EDITION's design (≤3 non-body head rows), "
          f"doubled; not from any leaf.\n")

    bounds, abstains = {}, []
    for i in LEAVES:
        band, frame, why = CR.anchored_head_band(leaves[i])
        if band is None:
            abstains.append((i, why))
            print(f"  ⚠️ ABSTAIN leaf {i}: {why}")
            continue
        bounds[i] = (frame["lo"], frame["hi"])

    if not bounds:
        print("🔴 the anchor abstained on every leaf -- nothing to score")
        return 1

    # ── A3 ────────────────────────────────────────────────────────────────────────────────────
    uniq = sorted(set(bounds.values()))
    los = [lo for lo, _ in bounds.values()]
    his = [hi for _, hi in bounds.values()]
    a3 = len(uniq) > 1
    print(f"  A3 ANCHORED    distinct bounds across {len(bounds)} leaves: {len(uniq)}")
    print(f"                 top    {min(los):.4f}h .. {max(los):.4f}h   "
          f"(spread {max(los) - min(los):.4f}h)")
    print(f"                 bottom {min(his):.4f}h .. {max(his):.4f}h   "
          f"(spread {max(his) - min(his):.4f}h)")
    print(f"                 frozen HEAD_BAND for contrast: {CR.HEAD_BAND[0]:.4f}h .. "
          f"{CR.HEAD_BAND[1]:.4f}h on every leaf")
    print(f"                 {'ok' if a3 else '🔴 CONSTANT -- a fraction with extra steps'}")

    # ── A1 ────────────────────────────────────────────────────────────────────────────────────
    fbl = first_body_lines()
    a1_hit, a1_miss, a1_blind = 0, [], []
    for i, (lo, hi) in bounds.items():
        fb = fbl.get(i)
        if fb is None:
            # ⚠️ NOT a pass and NOT a fail -- the GOLD does not label a body line on this leaf, so
            # the criterion cannot be evaluated here. Counted and named, never skipped (R1.4).
            a1_blind.append(i)
            continue
        if lo <= fb[0] and fb[1] <= hi:
            a1_hit += 1
        else:
            a1_miss.append((i, fb, (lo, hi)))
    a1_eval = a1_hit + len(a1_miss)
    # 🔴 THE PRE-REGISTERED BAR IS 20/20 AND IT IS NOT LOWERED TO THE NUMBER THAT CAN BE MEASURED.
    # A1 passes only if every leaf is evaluable AND every one contains its body line. Where leaves
    # are blind the criterion is UNEVALUABLE, which is a distinct outcome from FAIL and is reported
    # as such -- calling `a1_hit/a1_eval` a pass would silently redefine the bar as "of the leaves
    # that happened to be scorable", which is the part-selection defect R2.1j already caught once.
    a1 = (len(a1_blind) == 0) and a1_hit >= BAR_A1
    print(f"\n  A1 FIRST BODY LINE contained on {a1_hit}/{a1_eval} EVALUABLE leaves; "
          f"{len(a1_blind)} leaf/leaves NOT EVALUABLE")
    for i, fb, b in a1_miss:
        where = "ABOVE" if fb[0] < b[0] else "BELOW"
        frozen = "contains it" if (CR.HEAD_BAND[0] <= fb[0] and fb[1] <= CR.HEAD_BAND[1]) \
            else "misses it too"
        print(f"    🔴 leaf {i}: body line {fb[0]:.4f}h..{fb[1]:.4f}h lies {where} the band "
              f"{b[0]:.4f}h..{b[1]:.4f}h")
        print(f"       basis {fb[3]}  {fb[2][:56]!r}")
        print(f"       ⚠️ the FROZEN band {frozen}.")
    if a1_blind:
        print(f"    🔴 A1 IS UNEVALUABLE AT ITS PRE-REGISTERED BAR OF {BAR_A1}/20. The gold labels no")
        print(f"    MainText on leaf/leaves {a1_blind} -- so the denominator is {a1_eval}, not 20, and")
        print(f"    {a1_hit}/{a1_eval} is SILENCE about those leaves rather than success on them.")
        print("    ⚠️ AND THE BLIND LEAVES ARE THE ONES THAT WOULD BIND HARDEST. A leaf the gold")
        print("    labels with no body line in its 3-row window is a leaf whose head matter FILLS")
        print("    that window -- a CHAPTER OPENING (leaf 411: `NVMERI` / `CHAP.` / `XXVII.` and a")
        print("    summary note). Those are precisely the leaves whose first body line sits lowest,")
        print("    which is the case N was sized for. The gold excludes the failure it is being used")
        print("    to rule out. ⚠️ The bar is NOT lowered to 18 and the band is NOT adopted; the")
        print("    remedy is to LABEL the first body line on those leaves and re-run this criterion.")

    # ── A2 ────────────────────────────────────────────────────────────────────────────────────
    per, inside, tot = {}, 0, 0
    a2_miss = []
    for e in entries:
        if e["leaf"] not in bounds:
            continue
        lo, hi = bounds[e["leaf"]]
        ok_e = lo <= e["y0f"] and e["y1f"] <= hi
        lab = e["label"]
        h_, t_ = per.get(lab, (0, 0))
        per[lab] = (h_ + (1 if ok_e else 0), t_ + 1)
        tot += 1
        inside += 1 if ok_e else 0
        if not ok_e:
            a2_miss.append(e)
    rh_hit, rh_tot = per.get(RG.RUNNING_HEAD, (0, 0))
    a2 = inside == tot and rh_hit >= BAR_A2_RH
    print(f"\n  A2 GOLD CONTAINMENT {inside}/{tot} entries inside the band   "
          f"{'ok' if a2 else '🔴 BELOW BAR (must be all, RH 20/20)'}")
    for lab in (RG.RUNNING_HEAD, RG.CHAPTER_HEAD, RG.MARGIN_NOTE, RG.MAIN_TEXT):
        if lab in per:
            h_, t_ = per[lab]
            print(f"      {lab}  {h_}/{t_}{'' if h_ == t_ else '   🔴'}")
    for e in a2_miss[:12]:
        lo, hi = bounds[e["leaf"]]
        where = "ABOVE" if e["y0f"] < lo else "BELOW"
        print(f"    🔴 leaf {e['leaf']} row {e['row']} {e['label']} {where} the band: "
              f"{e['y0f']:.4f}..{e['y1f']:.4f} vs {lo:.4f}..{hi:.4f}  {e['text'][:38]!r}")
    if len(a2_miss) > 12:
        print(f"    ... and {len(a2_miss) - 12} more")

    # ── A4 ────────────────────────────────────────────────────────────────────────────────────
    a4 = None
    if with_a4:
        from kraken.lib import models
        m = models.load_any(str(MODEL))
        froze = anch = 0
        for i in LEAVES:
            got, why = CR.read_first_words_typed(m, leaves[i], 1)
            if got is None:
                froze += 1
            if i in bounds:
                # ⚠️ The anchored bound is a (lo, hi) PAIR, so it drives the existing reader through
                # `head_band(frac=...)` -- the parameter reserved for exactly this diagnostic. No
                # second reader is built, so an A4 difference is attributable to the BAND alone.
                got, why = CR.read_first_words_typed(m, leaves[i], 1, band=bounds[i])
                if got is None:
                    anch += 1
            else:
                anch += 1
        a4 = anch <= froze
        print(f"\n  A4 READER ABSTENTIONS  frozen band {froze}/20   anchored band {anch}/20   "
              f"{'ok' if a4 else '🔴 THE ANCHORED BAND MAKES THE READER WORSE'}")
    else:
        print("\n  A4 READER ABSTENTIONS  not run (pass --with-a4; it runs the recogniser)")

    passed = a1 and a2 and a3 and (a4 is not False)
    print(f"\n  A1 {'PASS' if a1 else 'FAIL'} · A2 {'PASS' if a2 else 'FAIL'} · "
          f"A3 {'PASS' if a3 else 'FAIL'} · A4 "
          f"{'PASS' if a4 else ('FAIL' if a4 is False else 'NOT RUN')}")
    if passed and a4 is None:
        print("  ⚠️ A4 HAS NOT BEEN RUN, so adoption is NOT yet earned. The pre-registration "
              "requires\n  A1-A4 TOGETHER; three of four is not a pass.")
    print(f"\n  verdict: {'PASS' if (passed and a4 is True) else 'FAIL'}"
          f"{'' if (passed and a4 is True) else '  -- the anchored band is NOT adopted; HEAD_BAND stays frozen'}")
    return 0 if (passed and a4 is True) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--with-a4", action="store_true")
    raise SystemExit(main(ap.parse_args().with_a4))
