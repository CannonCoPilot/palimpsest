#!/usr/bin/env python
"""R2.1d'(A) -- catchword continuity: catchword(leaf N) == first word of leaf N+1.

WHY THIS METRIC (R2.1-CRIT). R2.1 read "≥95% of rectos yield a parsed signature" since the
roadmap was written, and no reader can ever achieve it: signatures are set on the rectos of the
FIRST HALF of each gathering only. Measured on OT1-1609-B leaves 400-431, signatures print on 7
of 16 rectos (44%), all at odd leaf index. A 44% incidence and a 44%-recall reader produce the
IDENTICAL observable, so the criterion could not separate "the leaf prints nothing" from "the
reader missed it". A criterion that cannot separate absence from failure is not a test.

The catchword can. It prints on EVERY leaf, and the next leaf prints the answer, so the relation
is self-checking without any hand-keyed gold: one comparison scores the reader, proves leaf
order, and tests every leaf boundary rather than one recto in five.

⚠️ WHAT IT DOES NOT DO. Agreement is not fully independent of the recogniser: a model that
misreads the same ligature the same way at both the foot of leaf N and the head of leaf N+1
inflates the score. Treat the rate as a JOINT measure of reader and leaf order, and read
DISAGREE lists by hand before concluding anything about order.

Bar: ≥95% on the WILSON 95% LOWER BOUND, not the point estimate. Below it, R2.1f fires.

Run: ../ocr-venv/bin/python witness/r2_1d_continuity.py [START] [N]
"""
from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import witnesses as W  # noqa: E402
import collation_read as C  # noqa: E402
from kraken.lib import models  # noqa: E402

MODEL = HERE.parent / "models" / "reichenau_dr.mlmodel"
WITNESS = "OT1-1609-B"


def norm(s: str) -> str:
    """Letters only, case-folded, long-s folded, hyphens dropped.

    The catchword is set in the next leaf's fount and often carries the turn-line hyphen; a
    long-s rendering or a hyphen must not be scored as a leaf-ORDER defect. This is a
    deliberate loosening on ORTHOGRAPHY only -- it never merges two different words.
    """
    s = (s or "").lower().replace("ſ", "s").replace("‐", "").replace("-", "")
    return re.sub(r"[^a-z]", "", s)


def norm_words(s: str) -> list[str]:
    """The catchword's WORDS, after normalisation, dropping anything that normalises empty.

    A catchword may be set as more than one word ('of flowre'). Word count is taken here, from
    the foot side, and drives how many head tokens the head reader is asked for.
    """
    return [w for w in (norm(t) for t in (s or "").split()) if w]


def agrees(catch: str, first: str) -> bool:
    """The catchword must be a PREFIX relation with the next leaf's first word.

    ⚠️ Tightened 2026-08-14. The prototype accepted `a.startswith(b[:max(3, len(a))])`, which
    for a 2-character misread like 'wl' compares a 2-char prefix and calls almost anything a
    match. A metric that cannot fail does not measure. Now: equal, or one is a prefix of the
    other AND the shorter is at least 4 characters.
    """
    a, b = norm(catch), norm(first)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= 4 and long_.startswith(short)


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (0.0, 0.0, 0.0)
    ph = hits / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    hw = z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** 0.5) / den
    return ph, c - hw, c + hw


def main() -> int:
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    # R2.1g. `legacy` is the head reader R2.1d'(A) scored 0.312 with; `typed` is the same reader
    # rebuilt on the region primitive. Both are kept and BOTH are runnable on the same window,
    # because a redesign that cannot be compared against what it replaced has not been measured.
    # `typed-anchored` is the R2.2b DIAGNOSTIC and its number is NOT comparable to 0.312: it moves
    # the band as well as the reader, so it measures the two changes jointly. It exists to size what
    # the frozen bound costs, and is labelled at every point it is printed or written.
    mode = sys.argv[3] if len(sys.argv) > 3 else "typed"
    if mode not in ("typed", "legacy", "typed-anchored"):
        print(f"unknown mode {mode!r} -- expected 'typed', 'legacy' or 'typed-anchored'")
        return 2
    if mode == "legacy":
        head_reader = C.read_first_words
    elif mode == "typed":
        head_reader = C.read_first_words_typed
    else:
        def head_reader(m, path, k=1):
            return C.read_first_words_typed(m, path, k=k, band=(0.0, 0.35))
    print(f"== head reader: {mode}  ({head_reader.__name__})")
    if mode == "typed-anchored":
        print("== ⚠️ DIAGNOSTIC ONLY (R2.2b). This run changes the BAND as well as the reader, so "
              "the rate below\n==    is NOT comparable to 0.312 and must not be reported as the "
              "R2.1g result.")
    print()
    model = models.load_any(str(MODEL))
    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == WITNESS][0]
    leaves = W.leaves(vol, sig)

    rows, agree, disagree, unscored = [], 0, 0, 0
    for i in range(start, start + n):
        d = C.read_direction_line(model, leaves[i])
        cw = d.get("catchword")
        # ⚠️ R2.1f defect 2. The catchword governs how many head tokens are compared: leaf 414
        # sets 'of flowre', and reading one head token scored that TRUE agreement as DISAGREE.
        # k comes from the FOOT side, never from the head side -- letting the head reader pick
        # the width would let it choose the comparison that flatters it.
        k = max(1, len(norm_words(cw))) if cw else 1
        fw, why = head_reader(model, leaves[i + 1], k=k)
        if cw is None or fw is None:
            unscored += 1
            r = {"pair": f"{i}->{i+1}", "scored": False,
                 "catch_reason": d.get("abstain_reason") or "no token in catchword position",
                 "first_reason": why}
            rows.append(r)
            print(f"{i}->{i+1}: UNSCORED  catch: {r['catch_reason']}  |  first: {why}", flush=True)
            continue
        head = " ".join(t for t, _ in fw)
        head_conf = min(c for _, c in fw)
        hit = agrees(cw, head)
        agree += hit
        disagree += not hit
        rows.append({"pair": f"{i}->{i+1}", "scored": True, "agree": hit,
                     "catchword": cw, "catchword_words": k, "first_words": head,
                     "catch_conf": d["confidence"].get("catchword"),
                     "first_conf": round(head_conf, 3)})
        print(f"{i}->{i+1}: catch={cw!r}@{d['confidence'].get('catchword')}  "
              f"first={head!r}@{head_conf:.2f} (k={k})  "
              f"{'AGREE' if hit else 'DISAGREE'}", flush=True)

    scored = agree + disagree
    ph, lo, hi = wilson(agree, scored)
    print(f"\n== pairs scored {scored}/{n}  (unscored {unscored})  AGREE {agree}  DISAGREE {disagree}")
    print(f"== agreement {ph:.3f}   Wilson95 [{lo:.3f}, {hi:.3f}]   bar 0.95 on the LOWER bound")
    verdict = "PASS" if lo >= 0.95 else "BELOW BAR -- R2.1f fires"
    print(f"== {verdict}")
    # ⚠️ unscored pairs are reported, never silently dropped: a reader that abstains on half
    # the leaves and scores 100% on the rest has not measured the collation (R1.4).
    if scored < n:
        print(f"== ⚠️ {unscored} pair(s) unscored -- the rate above describes {scored} of {n} "
              f"boundaries, and the abstentions are part of the result, not excluded from it")
    # ⚠️ One file per mode. Writing both readers to one path would let the second run silently
    # overwrite the number the first was meant to be compared against.
    out = HERE.parent / ".scratch" / "r2" / f"r2_1d_continuity_{mode}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"witness": WITNESS, "head_reader": mode,
         "start": start, "n": n, "agree": agree, "disagree": disagree,
         "unscored": unscored, "agreement": ph, "wilson95": [lo, hi], "bar": 0.95,
         "verdict": verdict, "rows": rows}, indent=2))
    print(f"\nwrote {out}")
    return 0 if lo >= 0.95 else 1


if __name__ == "__main__":
    sys.exit(main())
