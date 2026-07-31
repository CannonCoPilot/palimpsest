#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""line_split.py — one row, one printed line. Separating two lines a skewed scan merged into one.

WHAT THIS IS NOT, AND THE MEASUREMENT THAT SETTLED IT. The symptom looks exactly like a column problem:

    that excerciſe the direction much addicted of a young to hunting, man his and nephew, his eyes decaying,

— `archive-holiebible-ot1` p47, genesis 5, where S9 scores 0.226 against 0.927 across the book. Eight pinned
attempts have tried to separate columns with a band or a gap rule, and the natural ninth was a recursive XY-cut
(the standard layout algorithm: cut on blank horizontal bands, then on blank vertical gutters, recurse). It was
built and run on this very leaf, and it returned ONE BLOCK: there is no gutter, because there are no columns.

The coordinates say what is actually there:

    in that excerciſe the direction of a young man his nephew,   y1 = 345 347 349 350 352 353 353 355 356 357
    much addicted to hunting, and his eyes decaying,             y1 = 311 313 315 316 317 317 318 319

TWO CONSECUTIVE PRINTED LINES, each sloping gently down to the right because the leaf was scanned askew. Their
BASELINES sit ~35px apart while the glyph boxes are ~55px tall, so the boxes overlap in y and the row grouper
— which groups on vertical overlap — merges them. Sorting the merged row by x then interleaves the two lines
word by word, which is what makes it read like two columns.

WHY IT IS S9'S PROBLEM. Measured over all 50 chapters: 701 merged rows, and 13 of the 14 worst
(chapter, source) pairs are `archive-holiebible-ot1` — 5% to 13% of its rows on the affected leaves, against
almost nothing elsewhere. It is a property of that scan's skew and leading, not of any chapter.

THE SEPARATION, AND THE CHICKEN-AND-EGG IT HAS TO AVOID. Clustering on raw baselines would split a strongly
sloping SINGLE line, so the skew must be removed first — but fitting the slope FROM THE ROW does not work, and
failing at it is instructive: on the row above, a least-squares fit over its nineteen words returns a slope of
-0.0159, because it is reconciling two interleaved lines rather than measuring one. De-skewing by that slope
smears the two baselines into a continuum whose largest gap is 5.7px, and nothing splits.

The skew belongs to the LEAF, not the row, so it is estimated from the leaf: rows that do not split on raw
baselines are by definition single lines, their slopes are fitted individually, and the MEDIAN of those is the
leaf's skew. Every row is then de-skewed by that one number and clustered. A leaf with no clean rows at all
gets no split, which is the right refusal — there is nothing to estimate from.

NOTHING IS DELETED. A merged row becomes two rows in printed order. Every word survives, which is the
difference between this and `row_interrupt` (pinned: it deleted scripture, ch1 124->107).
"""
from __future__ import annotations

import statistics

# The residual gap that separates two baselines, as a fraction of the median glyph height. The leading on
# these leaves is ~0.6 of the glyph box; a single sloping line's residuals stay well under 0.2 once its slope
# is removed. 0.45 sits between them with room on both sides.
SPLIT_FRAC = 0.45
# Below this many words a row has no reliable slope fit, and a two-word row cannot be two lines worth having.
MIN_ROW_WORDS = 4
MAX_SPLITS = 3


def _fit_slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    return (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den) if den > 1e-9 else 0.0


def split_row(row: list[dict], skew: float = 0.0) -> list[list[dict]]:
    """One row in, one or more rows out — in printed (top-to-bottom) order. `skew` is the LEAF's slope."""
    if len(row) < MIN_ROW_WORDS:
        return [row]
    hs = [w["y1"] - w["y0"] for w in row if w["y1"] > w["y0"]]
    h = statistics.median(hs) if hs else 30.0
    xs = [(w["x0"] + w["x1"]) / 2 for w in row]
    ys = [float(w["y1"]) for w in row]
    b = skew
    # Sort on the residual ALONE. Sorting (residual, word) tuples ties-breaks by comparing the word dicts,
    # which raises `'<' not supported between instances of 'dict' and 'dict'` the moment two words share a
    # baseline — and every leaf has such a pair, so this took out every chapter at once.
    res = sorted((((y - b * x), i, w) for i, (x, y, w) in enumerate(zip(xs, ys, row))), key=lambda t: t[0])
    gaps = [(res[i + 1][0] - res[i][0], i) for i in range(len(res) - 1)]
    gap, at = max(gaps, key=lambda t: t[0]) if gaps else (0.0, -1)
    if gap <= SPLIT_FRAC * h:
        return [row]
    parts = [[t[2] for t in res[:at + 1]], [t[2] for t in res[at + 1:]]]
    out: list[list[dict]] = []
    for p in parts:
        out += split_row(p, skew) if len(p) >= MIN_ROW_WORDS else [p]
    return sorted((sorted(p, key=lambda w: w["x0"]) for p in out if p),
                  key=lambda p: statistics.median([w["y1"] for w in p]))


def leaf_skew(rows: list[list[dict]]) -> float:
    """The leaf's own slope, estimated only from rows that are unambiguously ONE line.

    A row whose raw baselines hold no gap wider than the split threshold cannot be two printed lines, so its
    slope is a measurement of the scan's skew and nothing else. The median over such rows is robust to the few
    that are merged, and to the odd row of two words with a wild fit."""
    slopes = []
    for r in rows:
        if len(r) < MIN_ROW_WORDS:
            continue
        hs = [w["y1"] - w["y0"] for w in r if w["y1"] > w["y0"]]
        h = statistics.median(hs) if hs else 30.0
        ys = sorted(float(w["y1"]) for w in r)
        if any(b - a > SPLIT_FRAC * h for a, b in zip(ys, ys[1:])):
            continue                                   # possibly two lines — cannot measure skew from it
        xs = [(w["x0"] + w["x1"]) / 2 for w in r]
        slopes.append(_fit_slope(xs, [float(w["y1"]) for w in r]))
    return statistics.median(slopes) if len(slopes) >= 4 else 0.0


def split_rows(rows: list[list[dict]]) -> list[list[dict]]:
    """Every row of a leaf, with merged printed lines separated. Order is preserved."""
    skew = leaf_skew(rows)
    out: list[list[dict]] = []
    for r in rows:
        out += split_row(r, skew)
    return out
