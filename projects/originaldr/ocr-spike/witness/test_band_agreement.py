"""R2.2c GUARD -- does the band the READER receives contain what the GOLD labels?

⚠️ NO GUARD EXISTED FOR THIS, WHICH IS WHY IT RAN FOR A WEEK. `score_head_regions.py` reports
RunningHead recall 1.0000 over 20 leaves and exits 0; `read_first_words_typed` runs on a band in
which, measured, there is no running head on ANY of those 20 leaves. Both statements were true
simultaneously and nothing in the suite could hold them next to each other, because each module
cropped its own band and no module compared two. This one does exactly that and nothing else.

THE EIGHTH INSTANCE OF THE SIGNATURE DEFECT -- a correct rule nothing downstream reads. The
separator is not wrong. It is SCORED WHERE ITS MAIN JOB EXISTS AND DEPLOYED WHERE IT DOES NOT, and
in deployment the job that actually runs is MainText-vs-MarginNote (leaf 412's `Temporal`).

CRITERIA, pre-registered, written before this guard was first run:
  C1 ADDRESS     every gold entry carries the page-anchored address (`y0f`,`y1f`,`xlf`,`xrf`).
                 Without it this guard cannot ask its question, so a missing address is a HARD
                 FAIL, never a skip -- a guard that quietly declines to run is worse than absent.
  C2 IDENTITY    the band the SCORERS cut is the band the READER cuts.
  C3 CONTAINMENT every labelled entry's ink lies inside the reader's band.
  C4 COVERAGE    the CONVERSE, and REPORTED rather than pass/fail: how much of the band the reader
                 actually reads does the gold say anything about at all. Closing it means
                 labelling more of the page, which must not hide inside a band fix -- so it is
                 named and left OPEN rather than folded into a verdict it would silently soften.
Exit 0 iff C1-C3 hold. 🔴 C2 and C3 FAIL TODAY and that failure IS R2.2c; this guard lands open,
in the same state as `audit_prefix_rule` and `audit_prereq_ceilings`.

🔴 IT ALSO MEASURES MORE THAN R2.2c WAS RAISED ON. R2.2c is recorded as a RunningHead finding, with
the consolation that the job deployment really runs is MainText-vs-MarginNote. Measured: only 2 of
19 MarginNote entries lie inside the reader's band, and the gold speaks to 21.4% of that band. So
the MN recall the suite reports is ALSO measured almost entirely outside deployment, and the
consolation does not hold.

⚠️ AND THE GUARD IS ITSELF CHECKED, because a test that does not move is not evidence until it is
shown it COULD have moved. This session I mis-designed two injection tests and wrote one closing
criterion that was unfalsifiable in the direction that counted. So C3 is run a SECOND time against
the band the gold was LABELLED in, where it must PASS. If both runs failed, the finding would be an
arithmetic error in the address rather than a fact about the reader's band, and this guard would be
reporting its own bug as a defect in the pipeline.

⚠️ THIS GUARD DOES NOT PROPOSE A BAND. Choosing one is R2.2b (anchor the band to the type block),
and R2.1f pre-registered exactly ONE band re-cut which is already spent on the word-gap fix.
Widening `HEAD_BAND` here to make a guard pass would be that second re-cut under another name, and
would convert a below-threshold result into an accepted one -- which is the one thing that is never
done. What this guard reports is the SHORTFALL, in the vocabulary a fix would have to satisfy.
"""

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import collation_read as CR
import region_head as RG
import score_head_regions as SR
import score_head_tokens as ST

GOLD = _HERE / "gold/head_regions_OT1-1609-B_400-419.json"
ADDRESS = ("y0f", "y1f", "xlf", "xrf")


def contained(e, lo, hi):
    return e["y0f"] >= lo and e["y1f"] <= hi


def containment(entries, lo, hi):
    """-> (n_inside, n_total, per-label dict). By ENTRY, because a label is what the gold asserts."""
    per = {}
    for e in entries:
        lab = e.get("label")
        ins, tot = per.get(lab, (0, 0))
        per[lab] = (ins + (1 if contained(e, lo, hi) else 0), tot + 1)
    n = sum(v[0] for v in per.values())
    return n, len(entries), per


def main() -> int:
    g = json.loads(GOLD.read_text())
    entries = g["labels"]
    ok = True

    print("\nR2.2c -- BAND AGREEMENT, OT1-1609-B leaves 400-419")

    # ── C1 ADDRESS ────────────────────────────────────────────────────────────────────────────
    missing = [e for e in entries + g["ambiguous"] if not all(k in e for k in ADDRESS)]
    print(f"\n  C1 ADDRESS      {len(entries) + len(g['ambiguous']) - len(missing)}"
          f"/{len(entries) + len(g['ambiguous'])} entries carry the page-anchored address")
    if missing:
        print(f"    🔴 {len(missing)} entr(ies) carry only the band-pixel key -- run "
              f"`witness/gold_rekey_pagefrac.py --write`.")
        print("    This guard CANNOT ask its question without it, and declines to report a "
              "verdict on\n    a subset. HARD FAIL.")
        return 1

    # ── C2 IDENTITY ───────────────────────────────────────────────────────────────────────────
    reader = tuple(float(x) for x in CR.HEAD_BAND)
    scorers = {"score_head_regions": (0.0, float(SR.TOP_FRAC)),
               "score_head_tokens": (0.0, float(ST.TOP_FRAC))}
    print(f"\n  C2 IDENTITY     reader band (CR.HEAD_BAND, frozen)   "
          f"{reader[0]:.4f}h .. {reader[1]:.4f}h")
    for name, b in scorers.items():
        same = b == reader
        ok = ok and same
        print(f"                  {name:<20} {b[0]:.4f}h .. {b[1]:.4f}h   "
              f"{'ok' if same else '🔴 DIFFERENT BAND'}")
    if not all(b == reader for b in scorers.values()):
        print("    🔴 Every region number in the suite is measured on a crop the production reader\n"
              "    never receives. No region number transfers to the reader while this holds.")

    # ── C3 CONTAINMENT ────────────────────────────────────────────────────────────────────────
    n, tot, per = containment(entries, *reader)
    print(f"\n  C3 CONTAINMENT  gold entries whose ink lies inside the READER's band: {n}/{tot}")
    for lab in (RG.RUNNING_HEAD, RG.CHAPTER_HEAD, RG.MARGIN_NOTE, RG.MAIN_TEXT):
        if lab in per:
            ins, t = per[lab]
            flag = "" if ins == t else "   🔴"
            print(f"      {lab}  {ins}/{t}{flag}")
    ok = ok and n == tot
    if n < tot:
        y0 = min(e["y0f"] for e in entries)
        y1 = max(e["y1f"] for e in entries)
        rh = [e for e in entries if e.get("label") == RG.RUNNING_HEAD]
        print(f"\n    the gold's own ink spans          {y0:.4f}h .. {y1:.4f}h")
        print(f"    the RunningHead entries span      "
              f"{min(e['y0f'] for e in rh):.4f}h .. {max(e['y1f'] for e in rh):.4f}h")
        print(f"    SHORTFALL AT THE TOP              {reader[0] - y0:.4f}h -- the reader's band "
              f"opens BELOW the\n                                      running head on every leaf "
              f"that has one.")
        print("    ⚠️ Reported, NOT fixed by widening the band here: R2.1f pre-registered ONE "
              "re-cut and\n    it is spent. Anchoring the band is R2.2b. See this module's "
              "docstring.")
        # ⚠️ MEASURED HERE AND NOT ANTICIPATED BY R2.2c AS FIRST WRITTEN. R2.2c was raised as a
        # RunningHead finding -- "the reader's band has no running head in it" -- with the
        # consolation that the job actually running in deployment is MainText-vs-MarginNote. That
        # consolation does not survive this measurement.
        mi, mt_ = per.get(RG.MARGIN_NOTE, (0, 0))
        if mt_ and mi < mt_:
            print(f"\n    🔴 AND THE FALLBACK POSITION FAILS TOO. R2.2c's own consolation was that "
                  f"the job\n    deployment really runs is MainText-vs-MarginNote. But only {mi} of "
                  f"{mt_} MarginNote entries\n    lie inside the reader's band, so the MN recall the "
                  f"suite reports is itself measured\n    almost entirely OUTSIDE deployment. The "
                  f"band mismatch does not spare the MT-vs-MN\n    job; it undercuts that one too.")

    # ── C4 COVERAGE -- the CONVERSE question, and it is not the same question ─────────────────
    # C3 asks whether the reader's band contains what the gold labels. C4 asks whether the gold
    # says anything about what the reader's band CONTAINS. Both must hold before a region number
    # transfers, and only C3 was even askable before the page-anchored address existed.
    y0 = min(e["y0f"] for e in entries)
    y1 = max(e["y1f"] for e in entries)
    lo_r, hi_r = reader
    cov = max(0.0, min(hi_r, y1) - max(lo_r, y0)) / (hi_r - lo_r)
    print(f"\n  C4 COVERAGE     the gold's ink spans {y0:.4f}h..{y1:.4f}h; the reader's band is "
          f"{lo_r:.4f}h..{hi_r:.4f}h")
    print(f"                  ⇒ gold speaks to {cov:.1%} of the band the reader actually reads")
    print("    🔴 REPORTED, NOT PASS/FAIL, and the distinction is deliberate. Closing C4 means "
          "LABELLING\n    MORE OF THE PAGE, which is a separate piece of work and must not hide "
          "inside a band fix.\n    It is named here so it cannot be lost: it stays OPEN. What it "
          "says is that even the\n    entries C3 counts as INSIDE sit in the top fifth of the "
          "reader's band, and the rest of\n    what the reader types on every leaf is unlabelled "
          "territory.")

    # ── the guard's own control ───────────────────────────────────────────────────────────────
    lab_band = (0.0, float(SR.TOP_FRAC))
    ctl_n, ctl_tot, _ = containment(entries, *lab_band)
    print(f"\n  CONTROL         C3 re-run against the band the gold was LABELLED in "
          f"({lab_band[0]:.2f}h..{lab_band[1]:.2f}h):\n                  {ctl_n}/{ctl_tot} contained"
          f" -- {'ok, so C3 HAS a passing direction and is' if ctl_n == ctl_tot else '🔴 THIS MUST PASS'}"
          f" measuring the\n                  band, not the address arithmetic.")
    if ctl_n != ctl_tot:
        print("    🔴 THE GUARD IS INDICTING ITSELF. The gold does not sit inside the band it was\n"
              "    labelled in, so the page-anchored address is wrong and the C3 failure above is\n"
              "    NOT evidence about the reader's band. Fix the address before reading any verdict.")
        ok = False

    print(f"\n  verdict: {'PASS' if ok else 'FAIL'}   "
          f"{'' if ok else '-- R2.2c is OPEN and BLOCKING; no region number transfers to the reader'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
