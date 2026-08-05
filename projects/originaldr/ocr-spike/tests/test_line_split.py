# -*- coding: utf-8 -*-
"""One row, one printed line — and the three ways this went wrong before it went right.

The symptom that started it reads exactly like a column problem: `that excerciſe the direction much addicted
of a young to hunting, man his and nephew, his eyes decaying,` on `archive-holiebible-ot1` p47, where S9
scores 0.226 against 0.927 across the book. It is not columns. It is two consecutive printed lines on a leaf
scanned askew, whose glyph boxes overlap in y while their baselines stay ~35px apart, merged by a row grouper
that groups on vertical overlap and then sorted by x.

Pinned here so the diagnosis cannot be re-litigated from the symptom, and so the two bugs found while building
it stay fixed.
"""
from __future__ import annotations

import line_split as LS


def _w(t: str, x0: int, y1: int, h: int = 55, wd: int = 60) -> dict:
    return {"t": t, "x0": x0, "x1": x0 + wd, "y0": y1 - h, "y1": y1}


def _row(words: list[str], x0: int, y1: int, slope: float = 0.0, step: int = 95) -> list[dict]:
    return [_w(t, x0 + i * step, int(y1 + slope * (x0 + i * step))) for i, t in enumerate(words)]


def test_two_printed_lines_are_separated():
    """The genesis 5 row, reduced: two lines ~35px apart in baseline, interleaved by the x-sort."""
    upper = _row(["much", "addicted", "to", "hunting,"], 765, 311, slope=0.010)
    lower = _row(["in", "that", "excerciſe", "the", "direction"], 365, 345, slope=0.010)
    merged = sorted(upper + lower, key=lambda w: w["x0"])
    out = LS.split_rows([merged])
    assert len(out) == 2, f"expected two lines, got {[[w['t'] for w in r] for r in out]}"
    assert [w["t"] for w in out[0]] == ["much", "addicted", "to", "hunting,"]
    assert [w["t"] for w in out[1]] == ["in", "that", "excerciſe", "the", "direction"]


def test_a_single_sloping_line_is_not_split():
    """The failure mode a naive baseline test walks into: these leaves are photographed off bound volumes and
    one printed line can rise 35px across the measure — as much as the leading."""
    row = _row(["and", "the", "earth", "was", "voide", "and", "vacant"], 400, 1200, slope=0.030)
    assert len(LS.split_rows([row])) == 1


def test_the_skew_is_estimated_from_the_leaf_not_the_row():
    """Fitting the slope from the row itself CANNOT work, and the way it fails is the point: on the real
    genesis 5 row a least-squares fit over its nineteen words returns -0.0159 — it is reconciling two
    interleaved lines rather than measuring one — and de-skewing by that smears both baselines into a
    continuum whose largest gap is 5.7px. Nothing splits. The leaf's clean rows carry the true skew."""
    clean = [_row(["a", "b", "c", "d", "e"], 400, 200 + 90 * i, slope=0.010) for i in range(6)]
    assert abs(LS.leaf_skew(clean) - 0.010) < 0.004
    merged = sorted(_row(["x", "y", "z", "w"], 800, 700, slope=0.010)
                    + _row(["p", "q", "r", "s"], 400, 735, slope=0.010), key=lambda w: w["x0"])
    assert len(LS.split_rows(clean + [merged])) == len(clean) + 2


def test_equal_baselines_do_not_raise():
    """Sorting (residual, word) tuples ties-breaks by comparing the word DICTS, which raises
    `'<' not supported between instances of 'dict' and 'dict'`. Every leaf has two words sharing a baseline,
    so this took out all fifty chapters at once — every one measured 0/0 NO-VERSES."""
    row = [_w("a", 100, 500), _w("b", 200, 500), _w("c", 300, 500), _w("d", 400, 500)]
    assert LS.split_rows([row]) == [row]


def test_nothing_is_ever_deleted():
    """The distinction from `row_interrupt`, which is pinned for deleting scripture (ch1 124 -> 107). A split
    re-orders; it never drops a word."""
    rows = [sorted(_row(["one", "two", "three", "four"], 700, 400, slope=0.008)
                   + _row(["five", "six", "seven", "eight"], 380, 436, slope=0.008), key=lambda w: w["x0"]),
            _row(["nine", "ten", "eleven", "twelve"], 400, 600)]
    before = sorted(w["t"] for r in rows for w in r)
    after = sorted(w["t"] for r in LS.split_rows(rows) for w in r)
    assert before == after
