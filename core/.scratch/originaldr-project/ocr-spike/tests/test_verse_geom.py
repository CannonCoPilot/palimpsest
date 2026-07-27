# -*- coding: utf-8 -*-
"""TDD spec for verse_geom — the verse -> pixel-band crop geometry (§8 R3-4).

The gate flags which janvier verses diverge; olmOCR only beats R2 on CROPS. verse_geom is the bridge: it
reconstructs, for a reocr_page result, the map (verse -> body-line indices -> union bbox -> fractional crop),
so R3 re-reads exactly the flagged span. These tests are hermetic — synthetic page dicts carrying real janvier
text on known pixel bands, no kraken / no image — so the geometry logic is pinned exactly and runs instantly.

Key invariants under test:
  * build_body_tokmap reproduces reocr_core's r2_body construction TOKEN-FOR-TOKEN (verse numbers stripped,
    non-body roles skipped) and returns a token->line index parallel to it;
  * a verse's crop covers the pixel band of every line carrying it (single- and multi-line), ordered top->bottom,
    fractional in [0,1];
  * NO SILENT DEGRADATION guard: if the reconstructed body text disagrees with the stored r2_body (a sign the
    line set / stripping drifted), verse_crops RAISES rather than emit geometry keyed to the wrong pixels.
"""
from __future__ import annotations

import re

import pytest

import layout
import verse_geom
import verse_seg


# --------------------------------------------------------------------------- #
# helpers to build a synthetic reocr_page-shaped result
# --------------------------------------------------------------------------- #
def _r2_body(body_line_texts):
    """Exactly reocr_core's construction: join body lines, normalize ws, strip pure verse-number tokens."""
    return layout.strip_verse_numbers(re.sub(r"\s+", " ", " ".join(body_line_texts)).strip())


def _page(lines, page_px=(1000, 2000)):
    """lines: list of (text, role, bbox|None). Returns a reocr_page-shaped dict."""
    body = [t for (t, r, _b) in lines if r == "body"]
    return {
        "page_px": page_px,
        "r2_body": _r2_body(body),
        "lines": [{"text": t, "role": r, "conf": 0.9, "bbox": b} for (t, r, b) in lines],
    }


def _janvier_slice(lo=9, hi=16):
    cv = verse_seg.chapter_verses("psalms", 118, verse_seg.JANVIER)
    return cv, list(range(lo, hi + 1))


# --------------------------------------------------------------------------- #
# build_body_tokmap
# --------------------------------------------------------------------------- #
def test_build_body_tokmap_reproduces_r2_body_and_maps_lines():
    cv, vv = _janvier_slice()
    # one verse per body line; a header (skipped) and a bare verse-number token (stripped)
    lines = [("THE PSALME", "header", (100, 10, 900, 60))]
    for i, v in enumerate(vv):
        lines.append((f"{v} " + cv[v], "body", (100, 100 + i * 100, 900, 100 + i * 100 + 80)))
    page = _page(lines)
    body_text, tok_line = verse_geom.build_body_tokmap(page["lines"])
    assert body_text == page["r2_body"], "tokmap body must reproduce r2_body verbatim"
    toks = re.findall(r"\S+", body_text)
    assert len(tok_line) == len(toks), "one line-index per raw token"
    # every token index points at a BODY line (index >= 1, since line 0 is the header)
    assert all(page["lines"][li]["role"] == "body" for li in tok_line)
    # the verse-number tokens ("9".."16") are stripped, so no token maps via a digit
    assert not any(re.fullmatch(r"\d{1,3}\.?", t) for t in toks)


def test_build_body_tokmap_first_verse_tokens_map_to_first_body_line():
    cv, vv = _janvier_slice()
    lines = [(cv[v], "body", (100, 100 + i * 100, 900, 100 + i * 100 + 80)) for i, v in enumerate(vv)]
    page = _page(lines)
    body_text, tok_line = verse_geom.build_body_tokmap(page["lines"])
    n0 = len(cv[vv[0]].split())               # tokens of verse 9 -> line 0
    assert set(tok_line[:n0]) == {0}
    assert set(tok_line[n0:n0 + len(cv[vv[1]].split())]) == {1}


# --------------------------------------------------------------------------- #
# verse_crops
# --------------------------------------------------------------------------- #
def test_verse_crops_cover_each_line_and_are_ordered():
    cv, vv = _janvier_slice()
    W, H = 1000, 2000
    lines = [(cv[v], "body", (100, 100 + i * 100, 900, 100 + i * 100 + 80)) for i, v in enumerate(vv)]
    page = _page(lines, (W, H))
    crops = verse_geom.verse_crops(page, "psalms", 118)
    assert set(crops) == set(vv), "every laid-out verse gets a crop"
    prev_y0 = -1.0
    for i, v in enumerate(vv):
        x0, y0, x1, y1 = crops[v]["crop"]
        assert 0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0, f"v{v} crop out of unit box: {crops[v]['crop']}"
        # the crop must contain the line's own y-band (fractional), modulo padding
        line_y0f, line_y1f = (100 + i * 100) / H, (100 + i * 100 + 80) / H
        assert y0 <= line_y0f + 1e-9 and y1 >= line_y1f - 1e-9, f"v{v} crop {(y0,y1)} misses line {(line_y0f,line_y1f)}"
        assert y0 > prev_y0, "crops ordered top->bottom"
        prev_y0 = y0
        assert crops[v]["lines"] == [i], f"v{v} should map to exactly line {i}"


def test_verse_crops_multiline_verse_unions_its_lines():
    """A verse split across two lines must yield ONE crop spanning both bands."""
    cv, vv = _janvier_slice()
    W, H = 1000, 2000
    toks = cv[9].split()
    half = len(toks) // 2
    lines = [
        (" ".join(toks[:half]), "body", (100, 100, 900, 180)),      # verse 9, part 1 (line 0)
        (" ".join(toks[half:]), "body", (100, 200, 900, 280)),      # verse 9, part 2 (line 1)
    ]
    for i, v in enumerate(vv[1:], start=2):                          # remaining verses one-per-line below
        lines.append((cv[v], "body", (100, 100 + i * 100, 900, 100 + i * 100 + 80)))
    page = _page(lines, (W, H))
    crops = verse_geom.verse_crops(page, "psalms", 118)
    assert 9 in crops
    assert crops[9]["lines"] == [0, 1], "verse 9 must union both of its lines"
    _, y0, _, y1 = crops[9]["crop"]
    assert y0 <= 100 / H + 1e-9 and y1 >= 280 / H - 1e-9, "crop must span line0.top..line1.bottom"


def test_verse_crops_raises_on_body_mismatch():
    """No Silent Degradation: if the reconstructed body != stored r2_body, refuse to emit geometry."""
    cv, vv = _janvier_slice()
    lines = [(cv[v], "body", (100, 100 + i * 100, 900, 100 + i * 100 + 80)) for i, v in enumerate(vv)]
    page = _page(lines)
    page["r2_body"] = page["r2_body"] + " INTRUDER"      # simulate drift between lines and stored body
    with pytest.raises(ValueError, match="body"):
        verse_geom.verse_crops(page, "psalms", 118)


def test_verse_crops_box_invariant_to_drop_apparatus():
    """The crop BOX must not depend on drop_apparatus (that flag only changes the emitted verse TEXT, never the
    tok_lo/tok_hi boundary extents). This is what makes it safe to key crops off the gate's drop_apparatus=True
    segmentation — the pixel band is the same either way."""
    cv, vv = _janvier_slice()
    W, H = 1000, 2000
    foot = "this is an interleaved footnote annotation gloss commentary paratext insertion here"
    lines, y = [], 100
    for v in vv:
        lines.append((cv[v], "body", (100, y, 900, y + 80))); y += 100
        if v == 12:                                          # interleave an apparatus line after v12
            lines.append((foot, "body", (100, y, 900, y + 80))); y += 100
    page = _page(lines, (W, H))
    a = verse_geom.verse_crops(page, "psalms", 118, seg_kwargs={"drop_apparatus": True})
    b = verse_geom.verse_crops(page, "psalms", 118, seg_kwargs={"drop_apparatus": False})
    common = set(a) & set(b)
    assert common, "verses must localize under both settings"
    for v in common:
        assert a[v]["crop"] == b[v]["crop"], f"v{v} crop differs by drop_apparatus: {a[v]['crop']} vs {b[v]['crop']}"


def test_verse_crops_carries_seg_open_flags():
    """Each crop carries the verse's seg OPEN state so the caller can distinguish clean vs flagged spans."""
    cv, vv = _janvier_slice()
    lines = [(cv[v], "body", (100, 100 + i * 100, 900, 100 + i * 100 + 80)) for i, v in enumerate(vv)]
    page = _page(lines)
    crops = verse_geom.verse_crops(page, "psalms", 118)
    for v in vv:
        assert "open" in crops[v] and "ref" in crops[v]
        assert crops[v]["open"] is False       # clean synthetic page -> nothing OPEN


# --------------------------------------------------------------------------- #
# region grouping (contiguous flagged verses -> one body-column-clipped crop)
# --------------------------------------------------------------------------- #
def test_group_contiguous_runs():
    assert verse_geom.group_contiguous([27, 28, 29, 30]) == [[27, 28, 29, 30]]
    assert verse_geom.group_contiguous([12, 27, 28, 30]) == [[12], [27, 28], [30]]  # gap>1 splits; 28..30 gap2 splits
    assert verse_geom.group_contiguous([12, 27, 28, 29, 30], max_gap=1) == [[12], [27, 28, 29, 30]]
    assert verse_geom.group_contiguous([]) == []


def test_body_column_is_not_dragged_out_by_a_lone_margin_reaching_line():
    """The genesis-24 concern, restated for the ENVELOPE estimator: one body line that reaches into the outer
    margin (a swallowed margin note) must not define the column edge. A high quantile over a well-populated
    column ignores a lone outlier — which is the realistic case (these pages carry 20-60 body lines)."""
    W, H = 1000, 2000
    lines = [{"text": "body", "role": "body", "bbox": (100, 100 + i * 40, 800, 140 + i * 40)} for i in range(20)]
    lines.append({"text": "wide margin-reaching line", "role": "body", "bbox": (100, 1000, 950, 1040)})
    page = {"page_px": (W, H), "r2_body": "", "lines": lines}
    x0, x1 = verse_geom.body_column(page)
    assert abs(x0 - 0.1) < 1e-6 and abs(x1 - 0.8) < 1e-6, "the lone 0.95 outlier must not define the edge"


def test_body_column_not_dragged_right_by_short_gloss_fragments():
    """REGRESSION (psalms R3 hard-zero, 2026-07-25): the DR psalms pages set short italic GLOSS fragments
    flush-right inside the text block. A page-wide median over ALL body lines is dragged rightward by that
    population, so the crop's left edge lands INSIDE the scripture column and clips the opening of every full
    line — olmOCR then reads a headless verse and the janvier-cut span scores ~0 (measured: psalms-001 median
    x0 = 0.310 vs the true column left edge 0.161, i.e. 15% of page width of scripture silently cut off).

    The column must be estimated from the FULL-MEASURE lines (the only lines that actually define the column's
    margins), exactly as layout.type_lines does — short fragments never define a column edge."""
    W, H = 1000, 2000
    lines = []
    # 8 full-measure scripture lines: the true column is x 0.16 .. 0.92
    for i in range(8):
        lines.append({"text": "full measure scripture line", "role": "body",
                      "bbox": (160, 100 + i * 60, 920, 140 + i * 60)})
    # 12 short right-hand gloss fragments (majority of the line COUNT, none full measure)
    for i in range(12):
        lines.append({"text": "gloſſe", "role": "body", "bbox": (560, 120 + i * 60, 900, 155 + i * 60)})
    page = {"page_px": (W, H), "r2_body": "", "lines": lines}
    x0, x1 = verse_geom.body_column(page)
    assert abs(x0 - 0.16) < 1e-6, f"left edge {x0} must come from the full-measure lines (0.16), not the gloss median"
    assert abs(x1 - 0.92) < 1e-6, f"right edge {x1} must come from the full-measure lines (0.92)"


def test_body_column_defaults_to_the_median_not_a_wide_envelope():
    """MEASURED NEGATIVE RESULT, pinned so it is not silently re-"fixed" (2026-07-25).

    Widening the column to a near-full envelope (q=0.90) raises geometric containment of the region's own body
    lines from 0.456 to 0.949, and the argument for doing so is seductive: clipped scripture is unrecoverable,
    while over-inclusion should be recoverable via the P5 janvier-cut. The experiment refutes it — scored as
    the mean over 4 crop variants on the 46 known-bad gold verses, q=0.90 came out WORSE than the median
    (0.6875 -> 0.6631; 18 worsened vs 5 improved; Wilcoxon p=0.018), because what the wider crop admits on
    psalms pages is the interleaved annotation apparatus, which the cut does not reliably discard.

    The default must therefore stay at the median. `q` remains tunable so the experiment is reproducible."""
    W, H = 1000, 2000
    lines = [{"text": "scripture", "role": "body", "bbox": (150, 100 + i * 60, 700 + i * 20, 140 + i * 60)}
             for i in range(11)]
    page = {"page_px": (W, H), "r2_body": "", "lines": lines}
    assert verse_geom.body_column(page) == pytest.approx((0.15, 0.80)), "default must be the median column"


def test_body_column_quantile_is_tunable_and_1_0_is_the_full_envelope():
    W, H = 1000, 2000
    lines = [{"text": "scripture", "role": "body", "bbox": (150, 100 + i * 60, 700 + i * 20, 140 + i * 60)}
             for i in range(11)]
    page = {"page_px": (W, H), "r2_body": "", "lines": lines}
    assert verse_geom.body_column(page, q=1.0) == pytest.approx((0.15, 0.90))
    assert verse_geom.body_column(page, q=0.5) == pytest.approx((0.15, 0.80))   # the old median behaviour


def test_body_column_falls_back_to_all_lines_when_none_are_full_measure():
    """A page of only short lines (a verse-per-line poetic page) has no full-measure population; the estimator
    must fall back to all body lines rather than returning the (0,1) default and crop the whole page width."""
    W, H = 1000, 2000
    lines = [{"text": "short", "role": "body", "bbox": (200, 100 + i * 60, 600, 140 + i * 60)} for i in range(6)]
    page = {"page_px": (W, H), "r2_body": "", "lines": lines}
    assert verse_geom.body_column(page) == pytest.approx((0.2, 0.6))


def test_region_crops_group_contiguous_and_clip_to_body_column():
    cv, vv = _janvier_slice()                 # vv = 9..16
    W, H = 1000, 2000
    # verses 9..16 on contiguous body lines; a single line at v12 reaching into the margin (x1=950). The column
    # envelope must still come from the bulk of the lines (0.80), not from that one margin-reaching line.
    lines = []
    for i, v in enumerate(vv):
        x1 = 950 if v == 12 else 800
        lines.append((cv[v], "body", (100, 100 + i * 100, x1, 100 + i * 100 + 80)))
    page = _page(lines, (W, H))
    out = verse_geom.region_crops(page, "psalms", 118, [9, 10, 11, 12])
    assert out["no_geometry"] == []
    assert len(out["regions"]) == 1, "9..12 are contiguous -> a single region"
    reg = out["regions"][0]
    assert reg["verses"] == [9, 10, 11, 12]
    # x clipped to the body-column envelope, NOT dragged out to the one margin-reaching line's 0.95. With only
    # 8 lines a single outlier still sits inside the 0.90 quantile, so the edge lands between the bulk (0.80)
    # and the outlier — the invariant that matters is that the outlier does not DEFINE the edge. (On a real
    # page, 20-60 body lines put a lone outlier well outside the quantile; see the dedicated test above.)
    assert reg["crop"][2] < 0.93, f"region x1 {reg['crop'][2]} must not be defined by the margin-reaching line"
    assert reg["crop"][2] >= 0.80, "the envelope must still cover the bulk of the column's line ends"
    # y spans all four verses' bands
    assert reg["crop"][1] <= 0.05 + 1e-9 and reg["crop"][3] >= (100 + 3 * 100 + 80) / H - 1e-9


def test_region_crops_reports_no_geometry_verses():
    cv, vv = _janvier_slice()
    lines = [(cv[v], "body", (100, 100 + i * 100, 800, 100 + i * 100 + 80)) for i, v in enumerate(vv[:3])]
    page = _page(lines, (1000, 2000))
    # ask for a verse (16) that isn't laid out on this page -> reported as no_geometry, not silently dropped
    out = verse_geom.region_crops(page, "psalms", 118, [9, 10, 16])
    assert 16 in out["no_geometry"]
    assert any(r["verses"] == [9, 10] for r in out["regions"])


# --------------------------------------------------------------------------- #
# layout.line_bbox (kraken line -> pixel bbox) — duck-typed line objects
# --------------------------------------------------------------------------- #
class _Line:
    def __init__(self, baseline=None, boundary=None):
        self.baseline = baseline
        self.boundary = boundary


def test_line_bbox_prefers_boundary_full_extent():
    ln = _Line(baseline=[(100, 500), (900, 500)],
               boundary=[(100, 460), (900, 460), (900, 540), (100, 540)])
    assert layout.line_bbox(ln) == (100, 460, 900, 540)      # full polygon extent, not the flat baseline


def test_line_bbox_falls_back_to_baseline():
    ln = _Line(baseline=[(120, 500), (880, 505)], boundary=None)
    x0, y0, x1, y1 = layout.line_bbox(ln)
    assert (x0, x1) == (120, 880) and y0 == 500 and y1 == 505


def test_line_bbox_none_without_geometry():
    assert layout.line_bbox(_Line()) is None


# --------------------------------------------------------------------------- #
# ONE SEGMENTATION PER PAGE — the gate and the geometry must judge the same span (2026-07-27 wiring)
# --------------------------------------------------------------------------- #
def test_precomputed_spans_drive_both_the_gate_and_the_crops():
    """The gate decides WHICH verse is bad; the geometry decides WHICH PIXELS get re-read. If each re-segments
    the page independently they can disagree — the hybrid localizer picks per verse between two engines, so a
    verse can be scored on the align span and cropped from the walk span. Then the verse we judged bad is not
    the verse we re-read, and R3's answer is about the wrong pixels. Threading one `spans` dict through both is
    what makes that impossible; this test pins the contract on both consumers."""
    import verse_locate
    import xsrc_gate
    cv = verse_seg.chapter_verses("psalms", 118, verse_seg.JANVIER)
    vv = list(range(9, 15))
    lines = [(cv[v], "body", (100, 100 + i * 100, 900, 100 + i * 100 + 80)) for i, v in enumerate(vv)]
    page = _page(lines)

    spans = verse_locate.best_spans(page, "psalms", 118)
    scores = xsrc_gate.cross_source_verse_scores(page["r2_body"], "psalms", 118, spans=spans)
    crops = verse_geom.verse_crops(page, "psalms", 118, spans=spans)

    assert set(scores) == set(spans), "the gate scored a different verse set than the segmentation produced"
    assert set(crops) == set(spans), "the geometry cropped a different verse set than the segmentation produced"
    for v, s in spans.items():
        assert scores[v]["r2_text"] == s.get("text", ""), f"v{v}: the gate scored text the segmenter did not emit"
        if s.get("tok_lo") is not None:
            assert crops[v]["lines"] == s["lines"], f"v{v}: the crop is keyed to different lines than the span"
        assert scores[v].get("seg_source") in ("walk", "align"), "the gate must record which engine it judged"


def test_a_span_with_no_extent_is_open_not_dropped():
    """A hybrid span the walk placed nowhere has no token extent. It must come back as an explicit OPEN with a
    reason — dropping it would remove a verse from the deliverable silently, which is the exact failure mode
    the OPEN ledger exists to prevent."""
    cv = verse_seg.chapter_verses("psalms", 118, verse_seg.JANVIER)
    page = _page([(cv[9], "body", (100, 100, 900, 180))])
    spans = {9: {"tok_lo": None, "tok_hi": None, "text": "", "open": True, "reason": "not-located"}}
    got = verse_geom.verse_crops(page, "psalms", 118, spans=spans)
    assert 9 in got, "the verse was dropped instead of surfaced"
    assert got[9]["crop"] is None and got[9]["open"] is True
    assert "no-extent" in got[9]["reason"]
