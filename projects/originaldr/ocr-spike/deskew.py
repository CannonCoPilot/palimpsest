#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deskew.py — remove a leaf's rotation in COORDINATE SPACE, before any bound is applied.

WHY THIS EXISTS, AND WHY EVERY BOUND IN `PAGE_OVERRIDE` IS A SYMPTOM OF ITS ABSENCE.

Every horizontal bound this project owns is a single fraction of page width, applied to the whole height of
the leaf. That is only correct on a leaf whose columns are vertical. Measured over every wordbox cache:

    archive-ot1-1609        median |skew| 0.0029   p90 0.0063   max 0.0113
    pdf-S03a                median |skew| 0.0028   p90 0.0059   max 0.0096
    archive-holiebible-ot1  median |skew| 0.0105   p90 0.0214   max 0.0370
    jp2-S06                 median |skew| 0.0019   p90 0.0120   max 0.0302

`archive-holiebible-ot1` is 3.6x more crooked than the others at the median, and adjacent leaves lean
OPPOSITE ways: genesis 5 has p47 at +0.0140 and p48 at -0.0298. On p48 the body's left edge migrates from
0.212 at the head of the leaf to 0.226 at the foot while the note column's right edge falls from 0.210 to
0.192 — so at the top of that page the white channel between apparatus and scripture is 0.002 of page width,
about four pixels. NO VERTICAL LINE SEPARATES THEM. A single bound is not a badly-chosen constant there; it
is the wrong kind of object.

That is the common cause behind a run of separately-diagnosed defects:

  * `_trim_left_margin` (pinned, rejected) concluded "one threshold cannot serve a ragged edge" and inferred a
    SEGMENTATION problem. The edge is ragged because the leaf is rotated.
  * `gen1_r3.widen_to_measure` pads its vision-model crop by 6% because at 2% "does not clear the scan's skew"
    and the crop beheaded words — `dwelled` -> `ed`, `Behold` -> `hold`. A hand-tuned skew allowance.
  * The ch5 walk's 73-leaf sweep of left bounds cost 24 cells: a constant fitted to a rotation, 73 times.

THE ESTIMATOR, AND WHY NOT THE OBVIOUS ONE. The obvious estimator is the median slope of the lines, which
`line_split.leaf_skew` already computes for a different purpose. It is the wrong number here: fitted from
glyph-box bottoms it is dominated by descenders, long-ſ and capitals, and on p48 it returns -0.0298 where the
MARGIN actually drifts by -0.0128. Correcting by it overshoots and leaves the page bent the other way.

So the skew is estimated from the thing the bounds actually care about: the sharpness of the vertical
structure. This is the classical projection-profile method, done on coordinates rather than pixels. Rotate
the word x-positions through a range of angles; at each angle build a histogram of x and score it by the sum
of squared bin counts. A page whose columns are vertical stacks its line-starts, its margin column and its
verse numerals into tall narrow peaks; a rotated one smears them. The angle that maximises that score is the
one that makes the page's own vertical structure sharpest — which is precisely the condition a fractional
bound needs in order to be meaningful.

IT IS A COORDINATE TRANSFORM, NOT AN IMAGE ONE. Nothing is re-rendered and nothing is re-recognised: the
recognizer already read the glyphs correctly on the rotated page. Only the boxes move, which costs no GPU
time and cannot change a single character.
"""
from __future__ import annotations

import statistics

# Search range and resolution. |skew| never exceeds 0.037 anywhere in the corpus, so +/-0.05 covers it with
# room; 0.001 is a fifth of the 0.005 bin the bounds are quoted to.
THETA_MAX = 0.05
THETA_STEP = 0.001
# Histogram bin for the sharpness score, as a fraction of page width. 0.004 is fine enough to resolve a
# margin column from the body's first-token stack (they sit ~0.01 apart) without becoming shot noise.
SCORE_BIN = 0.004
# A leaf needs enough words for a projection profile to mean anything.
MIN_WORDS = 120


def _score(xs: list[float], W: float) -> float:
    """Sharpness of the vertical structure: sum of squared bin counts of the x profile.

    Maximised when line-starts, margin column and numeral column each stack into one bin. This is the
    standard projection-profile criterion; squaring is what rewards concentration.
    """
    nb = int(1.0 / SCORE_BIN) + 2
    h = [0] * nb
    for x in xs:
        b = int((x / W) / SCORE_BIN)
        if 0 <= b < nb:
            h[b] += 1
    return sum(n * n for n in h)


def leaf_theta(rec: dict) -> float:
    """The rotation that makes THIS leaf's vertical structure sharpest. 0.0 if it cannot be estimated."""
    words = [w for L in rec["lines"] for w in L["words"]]
    if len(words) < MIN_WORDS:
        return 0.0
    W, H = rec["page_px"]
    yc = H / 2.0
    # x0 AND x1 both carry the structure — line starts stack on the left, the justified right edge and any
    # numeral column stack on the right. Using both doubles the signal at no cost.
    pts = [(w["x0"], (w["y0"] + w["y1"]) / 2.0 - yc) for w in words]
    pts += [(w["x1"], (w["y0"] + w["y1"]) / 2.0 - yc) for w in words]

    best, best_t = -1.0, 0.0
    t = -THETA_MAX
    while t <= THETA_MAX + 1e-12:
        s = _score([x + t * dy for x, dy in pts], W)
        if s > best:
            best, best_t = s, t
        t += THETA_STEP
    return round(best_t, 4)


def apply_theta(rec: dict, theta: float) -> dict:
    """Return a copy of `rec` with every word box rotated by `theta` about the page centre.

    x' = x + theta * (y - y_centre). Only x moves: the bounds this feeds are horizontal, and leaving y alone
    keeps every row-grouping and line-splitting decision downstream bit-identical to the un-deskewed run —
    so any change in the board is attributable to the bounds and to nothing else.
    """
    if not theta:
        return rec
    W, H = rec["page_px"]
    yc = H / 2.0
    out = {**rec, "lines": [], "theta": theta}
    for L in rec["lines"]:
        ws = []
        for w in L["words"]:
            dy = (w["y0"] + w["y1"]) / 2.0 - yc
            sh = theta * dy
            ws.append({**w, "x0": w["x0"] + sh, "x1": w["x1"] + sh})
        b = L.get("bbox")
        nb = ([min(x["x0"] for x in ws), b[1], max(x["x1"] for x in ws), b[3]] if b and ws else b)
        out["lines"].append({**L, "words": ws, "bbox": nb})
    return out


def deskew(rec: dict) -> dict:
    """Estimate and apply in one step."""
    return apply_theta(rec, leaf_theta(rec))


def margin_spread(rec: dict, lo: float = 0.05, hi: float = 0.5) -> float:
    """Diagnostic: how much the leaf's line-start column drifts, in fractions of page width.

    The number a correct deskew should drive toward zero. Measured as the interquartile spread of row-start
    x0 within the given band, which is robust to the rows that begin indented (arguments, drop caps).
    """
    W = rec["page_px"][0]
    starts = []
    for L in rec["lines"]:
        ws = [w for w in L["words"] if lo <= w["x0"] / W <= hi]
        if len(ws) >= 3:
            starts.append(min(w["x0"] for w in ws) / W)
    if len(starts) < 8:
        return float("nan")
    starts.sort()
    q1, q3 = starts[len(starts) // 4], starts[3 * len(starts) // 4]
    return q3 - q1


if __name__ == "__main__":
    import argparse, glob, json, collections
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--source", default="")
    a = ap.parse_args()
    files = sorted(glob.glob(".wordboxes-genesis-*.json")) if a.all else [f".wordboxes-genesis-{a.chapter}.json"]
    seen, rows = set(), []
    for f in files:
        try:
            d = json.load(open(f))
        except FileNotFoundError:
            continue
        for od, leaves in d.items():
            if a.source and od != a.source:
                continue
            for p, rec in leaves.items():
                if (od, int(p)) in seen:
                    continue
                seen.add((od, int(p)))
                th = leaf_theta(rec)
                before, after = margin_spread(rec), margin_spread(apply_theta(rec, th))
                rows.append((od, int(p), th, before, after))
    by = collections.defaultdict(list)
    for od, p, th, b, af in rows:
        if b == b and af == af:
            by[od].append((b, af, th))
    print(f"{'source':26} {'leaves':>6} {'spread before':>14} {'after':>9} {'improved':>9}")
    for od, v in by.items():
        b = statistics.median(x[0] for x in v)
        af = statistics.median(x[1] for x in v)
        imp = sum(1 for x in v if x[1] < x[0] - 1e-6)
        print(f"{od:26} {len(v):6d} {b:14.4f} {af:9.4f} {imp:6d}/{len(v)}")
