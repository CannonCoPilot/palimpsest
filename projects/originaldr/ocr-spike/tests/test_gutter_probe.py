"""`gutter_probe.py` — the detector must SEPARATE only when the columns are genuinely disjoint (2026-07-31).

WHAT THIS GUARDS. Four geometric apparatus separations are pinned dead (§13 Q50) because each sought one rule
to decide, on every leaf, which words are apparatus. `gutter_probe` is allowed to exist only because it
REFUSES that question: it reports SEPARABLE when no body row and no margin word can be told apart by any x,
and OVERLAP otherwise. If it ever starts guessing on an OVERLAP leaf it becomes the fifth pinned negative, so
the refusal is tested as carefully as the acceptance.

Both misclassifications below are REAL — each was produced by an earlier version of the probe against
`jp2-S06` p74 and each reversed the verdict on a leaf whose correct bound had already been established
independently by sweep.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import gutter_probe as GP  # noqa: E402

W, H = 2200, 2847


def _w(t, x0, x1, y):
    return {"t": t, "x0": x0, "x1": x1, "y0": y, "y1": y + 40}


def _page(lines):
    return {"page_px": [W, H], "lines": [{"words": ws} for ws in lines]}


def _body_row(y, x_end=1640):
    """An ordinary body row: starts at the measure's left, ends just short of the gutter."""
    return [_w("and", 500, 560, y), _w("the", 900, 960, y), _w("word", 1400, x_end, y)]


def _margin_row(y, x0=1680):
    """A narrow right-hand annotation row."""
    return [_w("note", x0, x0 + 90, y), _w("here", x0 + 120, x0 + 220, y)]


def test_disjoint_columns_are_separable_and_the_bound_is_the_gutter_midpoint():
    lines = [_body_row(300 + 60 * i) for i in range(10)] + [_margin_row(300 + 60 * i) for i in range(8)]
    r = GP.probe_leaf("jp2-S06", "74", _page(lines), 0.0, 0.520)
    assert r["verdict"] == "SEPARABLE"
    # The bound is the midpoint of the CENTRE gap, not of the x0/x1 gap — the right band edge tests centres.
    body_ctr = (1400 + 1640) / 2
    marg_ctr = (1680 + 1770) / 2
    assert r["bound_px"] == (body_ctr + marg_ctr) / 2
    assert 0.0 < r["bound_frac"] < 1.0


def test_a_row_merging_both_columns_is_refused():
    """The p76 case: one kraken line holds body AND margin (`...perceiuing that ſhe Some obey`).

    No x separates them, and a bound chosen anyway would truncate scripture. The probe must say OVERLAP and
    name the offending row rather than pick a threshold."""
    lines = [_body_row(300 + 60 * i) for i in range(10)] + [_margin_row(300 + 60 * i) for i in range(8)]
    lines.append(_body_row(1000) + [_w("Some", 1700, 1800, 1000), _w("obey", 1830, 1900, 1000)])
    r = GP.probe_leaf("jp2-S06", "76", _page(lines), 0.0, 0.520)
    assert r["verdict"] == "OVERLAP"
    assert r["offenders"], "an OVERLAP verdict must name the rows that make it inseparable"
    assert "Some" in r["offenders"][0]["text"]


def test_a_lone_far_right_body_row_does_not_defeat_the_column():
    """REGRESSION, and it reversed a correct verdict. `jp2-S06` p74's last row is `17.Ther-` at x1490-1653 —
    the hyphenated opening of verse 17, lying wholly right of any sane probe. The first version of the probe
    counted it as a margin row, took the column's left edge to be 1490, and reported the leaf OVERLAP; the
    sweep had already shown a bound at 0.746 gains two cells there. A margin ROW must belong to a COLUMN, so a
    row starting well LEFT of the column's median edge is not one."""
    lines = [_body_row(300 + 60 * i) for i in range(10)] + [_margin_row(300 + 60 * i) for i in range(8)]
    lines.append([_w("17.Ther-", 1490, 1653, 2589)])
    r = GP.probe_leaf("jp2-S06", "74", _page(lines), 0.0, 0.520)
    assert r["verdict"] == "SEPARABLE", "a lone outdented body row must not be read as the margin column"
    assert r["col_left"] == 1680


def test_an_indented_margin_row_stays_in_the_column():
    """REGRESSION, the opposite error. Requiring the column's left edges to agree within a two-sided window
    ejected `.and odde` (x1746, where the column edge is x1673) back into the BODY, whose maximum centre then
    sat inside the margin and again reported OVERLAP. A narrow column indents freely; what it does not do is
    start left of its own edge. The membership test is therefore ONE-SIDED."""
    lines = [_body_row(300 + 60 * i) for i in range(10)] + [_margin_row(300 + 60 * i) for i in range(6)]
    lines.append([_w(".and", 1746, 1795, 900), _w("odde", 1825, 1887, 900)])
    r = GP.probe_leaf("jp2-S06", "74", _page(lines), 0.0, 0.520)
    assert r["verdict"] == "SEPARABLE", "an indented row of the margin column must not be classed as body"
    assert r["n_margin"] == 7


def test_a_column_needs_enough_rows_to_be_a_column():
    """Two stray right-hand fragments are a coincidence, not an apparatus column, and nothing should be cut."""
    lines = [_body_row(300 + 60 * i) for i in range(10)] + [_margin_row(300), _margin_row(360)]
    r = GP.probe_leaf("jp2-S06", "99", _page(lines), 0.0, 0.520)
    assert r["verdict"] == "NO-COLUMN"


def test_rows_above_the_chapter_cut_do_not_vote():
    """Matter above `chapter_open_y` — running head, the previous chapter's annotation tail, the argument — is
    not scripture, so its geometry must not decide the body's bound."""
    lines = [[_w("ANNOTATIONS", 500, 1900, 100)]] + [_body_row(1200 + 60 * i) for i in range(10)] \
        + [_margin_row(1200 + 60 * i) for i in range(8)]
    hi = GP.probe_leaf("jp2-S06", "74", _page(lines), 0.33, 0.520)
    assert hi["verdict"] == "SEPARABLE", "the pre-chapter row must be excluded before the columns are compared"
