#!/usr/bin/env python
"""TWO-AXIS BOUND PROBE FOR `jp2-S06` — read BOTH of a leaf's body bounds off that leaf's own histogram.

WHY THIS EXISTS. `gen1_pagemodel.PAGE_OVERRIDE` records the campaign's history, and read as a table it
convicts itself:

    ("jp2-S06",  18): {"body": (0.165, 0.765)}   # both axes tuned
    ("jp2-S06",  50): {"body": (0.15,  0.754)}   # both axes tuned
    ("jp2-S06",  74): {"body": (0.215, 0.746)}   # RIGHT tuned, left = the default
    ("jp2-S06", 128): {"body": (0.215, 0.7544)}  # RIGHT tuned, left = the default
    ("jp2-S06",  90): {"body": (0.14,  0.825)}   # LEFT tuned, right = the default
    ("jp2-S06",  92): {"body": (0.14,  0.825)}   # LEFT tuned, right = the default

Every one of those entries was produced by a hunt for ONE defect, which varied the axis it was hunting and
left the other at its default. WALKTHROUGH-PROTOCOL rule C: when a table varies on one axis and is constant
on another, the constant axis was never tested — it was not measured and found correct. `left_strip_probe`
inherits the same blindness by construction: it is a LEFT probe, so on p130 it correctly reported 55 clipped
body tokens and could not see the virtue-gloss column at 0.76 that was splicing `Fortitude.` and `ePrudence.`
into the middle of Genesis 39.

WHAT IT MEASURES. Nothing is assumed about which side this edition puts its notes on — that is the fact to
recover, and on `jp2-S06` it ALTERNATES by leaf parity (even leaves: notes right, body reaching left to
~0.15; odd leaves: notes left at 0.10-0.21, body reaching right to ~0.82). Both bounds come from the same
one-dimensional signature, applied to the two ends of the token histogram:

  A COLUMN IS SEPARATED FROM THE BODY BY WHITE PAPER. On a leaf whose notes are on the left, the x0
  histogram is dense from 0.10, then EMPTY for a bin or two, then the body's dense mass. On a leaf with no
  left column, there is no gap: the body's own first-token mass simply begins, and any bound set above it is
  clipping scripture.

  A RIGHT COLUMN SHOWS AS DIP-THEN-SPIKE. Body line-ENDS spread smoothly over the last quarter of the
  measure and taper; they never spike. A note column stacks many tokens at one x0. So the right edge of the
  body is the trough between the taper and the spike. Without a spike there is no column and the body simply
  runs to its natural end.

THE LEFT AXIS IS NOT DECIDED HERE, AND THAT IS DELIBERATE. A histogram cannot tell "the body begins at
0.11" from "a note PARAGRAPH begins at 0.11": ch23 p89 carries a full-width annotation block whose tokens
span the bound continuously and leave no white gap, and the first version of this probe read that as a
clipped body and proposed importing all 88 of its tokens into scripture. `left_strip_probe`'s LINE-MEMBERSHIP
test is the instrument that separates those — a clipped body head leaves a line straddling the bound, a note
block leaves lines lying wholly inside the strip — and it scored p89 as 0 continuation / 88 note. So the two
compose: LINE MEMBERSHIP decides WHETHER a left bound moves, the HISTOGRAM decides WHERE TO. The right axis
is this probe's own, because a left probe cannot see it at all.

WHAT IT DOES NOT DO. It does not classify text. It never asks whether a token "looks like" apparatus, which
is the test that returned the exactly-opposite answer in the first S6 cause classifier and was entirely
convincing. Geometry only; the eye confirms on the emitted examples.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OD = "jp2-S06"
# NAMED FOR ONE WITNESS UNTIL 2026-08-02 (ch41). It was written to escape exactly the failure it then
# embodied: `left_strip_probe` could only see the 1609 layout, reported "no defect" on `jp2-S06` and was
# believed; this probe could only see `jp2-S06`, and ch41's S1/S3/S9 were losing whole words off the ENDS of
# body lines -- `He ſaid [ther]fore`, `a dreame [per]teining`, `shal not be [con]ſumed` -- to a right bound
# tuned tight against their annotation column, on the one axis nobody had varied for those sources.

BIN = 0.01
EDGE = 0.02          # below this is page edge / bleed, never a column
LEFT_SCAN_HI = 0.26  # a left column, if present, lies below this
RIGHT_SCAN_LO = 0.68 # body line-ends and any right column both live above this

# A gap is a run of empty bins. One 0.01 bin can fall empty by chance in a 40-line leaf, so require two.
MIN_GAP_BINS = 2
# ...AND A GAP IS ONLY A COLUMN EDGE IF A COLUMN STANDS ON THE FAR SIDE OF IT. p132 carries one stray token
# at 0.09 and one at 0.13, and the first version of this probe read the emptiness after them as the end of a
# note column and proposed 0.130 — importing the page edge. A real S6 left column runs 19-46 tokens.
MIN_COL_MASS = 8
# A spike must stand this far above the trough that precedes it to count as a column rather than a ripple in
# the taper of body line-ends.
SPIKE_RATIO = 3.0
MIN_SPIKE = 6
# ONE INSTRUMENT IS NOT ENOUGH TO CUT SCRIPTURE. The dip-then-spike test alone proposed cutting p105 at 0.715
# and p159 at 0.77, and the eye refuses both: p105's "spike" is nine body tokens (`wil ſaid to for went that
# vpon idololatrical thoſe`) with scripture running smoothly on either side. The risk is asymmetric — keeping
# a gloss leaves the board where it is, cutting body destroys verses — so a right bound moves only when the
# spike is unmistakable ON ITS OWN (a gloss column sets one token per line, so a tall stack), or when a
# SECOND, ORTHOGONAL instrument attests the two-column layout: line-membership finding the body clipped on
# the left says this leaf is set in two columns, whatever the histogram's confidence.
# 12 IS NOT A THRESHOLD THAT DISCRIMINATES: p35 (a real citation column, `Gen. S.Chriſ. Theod. Moral.`) and
# p79 (nine body tokens, `him. God ſelt. into My ... derogateth Baptiſme`) both spike exactly 12 on
# uncorroborated odd leaves, and one is right and one is wrong. So the standalone bar sits above both, the
# probe declines the pair, and any leaf the EYE confirms is carried in `PAGE_OVERRIDE` with its reason —
# rather than tuning a constant until it happens to admit the example that motivated it.
STANDALONE_SPIKE = 18
# `left_strip_probe`'s BAND_MIN, reused so the mirrored right-edge test uses the same definition of "a line
# that lives in the band" as the left one does.
LSP_BAND_MIN = 2


def hist(rec: dict) -> collections.Counter:
    W = rec["page_px"][0]
    h: collections.Counter = collections.Counter()
    for L in rec["lines"]:
        for w in L["words"]:
            f = w["x0"] / W
            if f >= EDGE:
                h[round(f / BIN)] += 1
    return h


def left_bound(h: collections.Counter) -> tuple[float, str]:
    """The body's left edge = the far side of the gap, or the first mass if there is no gap."""
    lo, hi = int(EDGE / BIN), int(LEFT_SCAN_HI / BIN)
    bins = [(b, h.get(b, 0)) for b in range(lo, hi + 1)]
    first = next((b for b, n in bins if n > 0), None)
    if first is None:
        return LEFT_SCAN_HI, "empty"
    run = 0
    for b in range(first + 1, hi + 1):
        if h.get(b, 0) == 0:
            run += 1
            continue
        if run >= MIN_GAP_BINS:
            mass = sum(h.get(x, 0) for x in range(first, b - run))
            if mass >= MIN_COL_MASS:
                # dense mass, white paper, then the body: a genuine left note column. Stand in the MIDDLE of
                # the white paper, not on the body's first bin — a bound set flush against the mass it must
                # admit is one pixel of skew from clipping it again.
                mid = (b + (b - run - 1)) / 2.0
                return round(mid * BIN, 3), (f"column {first*BIN:.2f}-{(b-run-1)*BIN:.2f}"
                                             f" ({mass} tok), gap {run} bins")
        run = 0
    # NO COLUMN — the body simply begins, and any bound above it is clipping scripture. Its start is where
    # the DENSE mass begins, not where the first token sits: p132 carries a lone edge token at 0.09 and the
    # body proper at 0.15, and honouring that stray would have swept the page edge into the verse.
    for b in range(first, hi + 1):
        if sum(h.get(x, 0) for x in range(b, b + 3)) >= MIN_COL_MASS:
            return round(b * BIN, 3), f"no gap; dense mass begins {b*BIN:.2f}"
    return round(first * BIN, 3), f"no gap, no dense mass; first token {first*BIN:.2f}"


def right_bound(h: collections.Counter, default: float) -> tuple[float, str]:
    """The body's right edge = the trough before a spike, or the default if no column spikes."""
    lo, hi = int(RIGHT_SCAN_LO / BIN), int(0.95 / BIN)
    best = None
    for b in range(lo + 1, hi + 1):
        n = h.get(b, 0)
        if n < MIN_SPIKE:
            continue
        trough = min(h.get(x, 0) for x in range(max(lo, b - 3), b))
        if n >= SPIKE_RATIO * max(trough, 1) and trough <= 2:
            # THE DOMINANT SPIKE, NOT THE FIRST. Taking the first fired on p132's 0.73 — eight body
            # line-ends sitting above a two-token dip — and set the bound inside scripture, while the actual
            # gloss column stood 22 tokens high at 0.76. A column is the tallest thing on this side of a leaf.
            if best is None or n > best[1]:
                best = (b, n, trough)
    if best is None:
        return default, "no spike; no right column"
    b, n, trough = best
    return round((b - 0.5) * BIN, 3), f"spike {n} at {b*BIN:.2f} over trough {trough}"


def right_strip_verdict(recs: list[dict], lo: float, hi: float) -> tuple[int, int]:
    """`left_strip_probe`'s line-membership test, mirrored onto the right edge.

    A token in the strip (lo, hi] is CONTINUATION if its line carries body inside the band — the bound
    clipped the tail off a body line — and NOTE if the line lies wholly outside. Merged across every cache
    that holds this leaf, worst-case note and best-case continuation, as `--emit` does on the left.
    """
    cont = note = 0
    for rec in recs:
        W = rec["page_px"][0]
        c = n = 0
        for L in rec["lines"]:
            ws = L["words"]
            strip = [w for w in ws if lo < w["x0"] / W <= hi]
            if not strip:
                continue
            if len([w for w in ws if w["x0"] / W <= lo]) >= LSP_BAND_MIN:
                c += len(strip)
            else:
                n += len(strip)
        cont, note = max(cont, c), max(note, n)
    return cont, note


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--source", default=DEFAULT_OD, help="ocr_dir to probe")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--emit", action="store_true", help="print PAGE_OVERRIDE entries for leaves that differ")
    ap.add_argument("--fresh", action="store_true",
                    help="derive from the SOURCE default, ignoring accumulated per-leaf tuning — "
                         "so the proposal is independent of the campaign's history")
    ap.add_argument("--deskew", action="store_true",
                    help="rotate each leaf upright before measuring it (see deskew.py). A fractional\n                          bound only means anything on a leaf whose columns are vertical.")
    ap.add_argument("--right-only", action="store_true",
                    help="propose the RIGHT bound alone, holding each leaf's left bound as it stands")
    ap.add_argument("--examples", type=int, default=0, help="show N tokens either side of each proposed bound")
    a = ap.parse_args(argv)

    import gen1_pagemodel as PM
    od = a.source
    dfl = PM.SOURCE_MODEL[od]["body"]

    files = (sorted(glob.glob(str(HERE / ".wordboxes-genesis-*.json"))) if a.all
             else [str(HERE / f".wordboxes-genesis-{a.chapter}.json")])

    # A leaf is carried by several chapters and each cache holds its own recognition of it. Merge the
    # histograms rather than picking one cache's answer.
    import left_strip_probe as LSP

    merged: dict[int, collections.Counter] = {}
    recs: dict[int, list] = {}
    verdict: dict[int, tuple[int, int]] = {}
    for f in files:
        try:
            d = json.load(open(f))
        except FileNotFoundError:
            continue
        for p, rec in d.get(od, {}).items():
            p = int(p)
            if a.deskew:
                import deskew as _dk
                rec = _dk.deskew(rec)
            merged.setdefault(p, collections.Counter()).update(hist(rec))
            recs.setdefault(p, []).append(rec)
            # AT THE DEFAULT BOUND, NOT THIS LEAF'S CURRENT ONE. "Is this leaf set in two columns?" is a fact
            # about the page; asking it at the current override makes it a fact about the campaign's history
            # instead. p90 and p92 were moved to 0.14 yesterday, so at their current bound nothing lies in the
            # strip, they score 0/0, and the leaf that MOTIVATED this probe reads as uncorroborated.
            r = LSP.leaf_report(rec, dfl[0], LSP.EDGE_FLOOR)
            nc, nn = len(r["continuation"]), len(r["note"])
            if p in verdict:  # worst-case note, best-case continuation across caches, as LSP --emit does
                nc, nn = max(nc, verdict[p][0]), max(nn, verdict[p][1])
            verdict[p] = (nc, nn)

    rows, changed = [], []
    for p in sorted(merged):
        h = merged[p]
        explicit = (not a.fresh) and "body" in PM.PAGE_OVERRIDE.get((od, p), {})
        cur = dfl if a.fresh else PM.PAGE_OVERRIDE.get((od, p), {}).get("body", dfl)
        nc, nn = verdict[p]
        clipped = nc >= 3 * max(nn, 1) and nc >= 3
        if clipped:
            lb, lwhy = left_bound(h)
            lwhy = f"CLIPPED ({nc} cont / {nn} note); {lwhy}"
            if explicit and lb > cur[0]:
                # AN ESTIMATE DOES NOT OVERTURN A MEASUREMENT. p90's 0.14 was not guessed — it was applied,
                # measured at +15 cells and passed through the faithfulness audit. "Dense mass begins at
                # 0.16" is a weaker claim than that, and tightening onto it would silently drop whatever
                # sits in 0.14-0.16. An explicit entry is only ever widened here.
                lb, lwhy = cur[0], f"{lwhy}; held at the measured {cur[0]}"
        else:
            # line membership says the strip is apparatus, or that nothing is being cut. Do not move a left
            # bound on a histogram alone — see the p89 note in the docstring.
            lb, lwhy = cur[0], f"held ({nc} cont / {nn} note)"
        if a.right_only:
            # THE 1609 WITNESSES' LEFT BOUND WAS ALREADY MEASURED BOOK-WIDE by `left_strip_probe
            # --emit`, and adopted at +57 cells. "Dense mass begins at 0.10" is a weaker claim than
            # that, so on those sources this probe changes only the axis nobody ever varied.
            lb, lwhy = cur[0], f"right-only; {lwhy}"
        rb, rwhy = right_bound(h, dfl[1])
        if rb > cur[1]:
            # WIDENING IS SOMETIMES THE WHOLE FIX, so this cannot simply be refused — ch41's S1/S3/S9 lose
            # `[ther]fore`, `[per]teining`, `[con]ſumed` off the ENDS of body lines to a right bound tuned
            # tight against their annotation column. But it must not be granted on the histogram alone
            # either: p25's column stands outside the band already, and taking the trough before it would
            # hand the band a strip it is right to refuse. Same instrument as the left, mirrored — the
            # strip between the current bound and the proposal is CLIPPED BODY if its tokens sit on lines
            # that continue back inside the band, and APPARATUS if those lines lie wholly outside it.
            rc, rn = right_strip_verdict(recs[p], cur[1], rb)
            if not (rc >= 3 * max(rn, 1) and rc >= 3):
                rb, rwhy = cur[1], f"held; {rwhy} — strip is apparatus ({rc} cont / {rn} note)"
            else:
                rwhy = f"WIDENED ({rc} cont / {rn} note); {rwhy}"
        if rb != dfl[1]:
            n = int(rwhy.split()[1]) if rwhy.startswith("spike") else STANDALONE_SPIKE
            if n < STANDALONE_SPIKE and not clipped:
                rb, rwhy = cur[1], f"held; {rwhy} — uncorroborated, under {STANDALONE_SPIKE}"
        moved = (abs(lb - cur[0]) > 0.005, abs(rb - cur[1]) > 0.005)
        rows.append((p, cur, (lb, rb), moved, lwhy, rwhy))
        if any(moved):
            changed.append((p, cur, (lb, rb)))

    if a.emit:
        for p, cur, new in changed:
            extra = {k: v for k, v in PM.PAGE_OVERRIDE.get((od, p), {}).items() if k != "body"}
            tail = "".join(f", {k!r}: {v!r}" for k, v in extra.items())
            print(f'    ({od!r}, {p}): {{"body": ({new[0]}, {new[1]}){tail}}},   # was {cur}')
        print(f"    # {len(changed)} leaves differ, of {len(rows)} measured")
        return

    print(f"{'leaf':>5} {'current':>16} {'proposed':>16}  why-left / why-right")
    for p, cur, new, moved, lwhy, rwhy in rows:
        mark = ("L" if moved[0] else ".") + ("R" if moved[1] else ".")
        print(f"{p:>5} ({cur[0]:.3f},{cur[1]:.3f}) ({new[0]:.3f},{new[1]:.3f}) {mark}  {lwhy}  |  {rwhy}")
        if a.examples and any(moved):
            rec = recs[p][0]
            W = rec["page_px"][0]
            # what the PROPOSAL changes, in both directions: tokens the new left admits that the old
            # refused, and tokens the new right refuses that the old admitted.
            out = [w["t"] for L in rec["lines"] for w in L["words"]
                   if new[0] <= w["x0"] / W < cur[0]]
            rgt = [w["t"] for L in rec["lines"] for w in L["words"]
                   if new[1] <= w["x0"] / W < cur[1]]
            print(f"        newly ADMITTED at left : {' '.join(out[:a.examples])}")
            print(f"        newly REFUSED at right : {' '.join(rgt[:a.examples])}")
    print(f"\n{len(changed)} of {len(rows)} leaves differ from the model")


if __name__ == "__main__":
    main()
