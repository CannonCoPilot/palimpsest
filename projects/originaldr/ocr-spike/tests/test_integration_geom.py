# -*- coding: utf-8 -*-
"""SLOW integration: the real geometry chain on a real page (kraken segmentation + R2 + gate + verse_geom).

Marked `slow` (loads kraken models, segments a real jp2) — run with `-m slow`. Pins the empirically-observed
2026-07-23 result so a regression in segmentation/layout/gate/geometry is caught: genesis-24 (archive-ot1-1609
p99) flags exactly {12,27,28,29,30} and every flagged verse resolves to a usable pixel crop.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

OCR_DIR, PI, BOOK, CH = "archive-ot1-1609", 99, "genesis", 24
KNOWN_FLAGGED = {12, 27, 28, 29, 30}


@pytest.fixture(scope="module")
def page_result():
    import reocr_core
    return reocr_core.reocr_page(OCR_DIR, PI, locus=(BOOK, CH), want_base=False, want_r1=False)


def test_gate_flags_the_known_bad_set(page_result):
    cs = page_result.get("cross_source") or {}
    assert set(cs.get("flagged_verses") or []) == KNOWN_FLAGGED, "gate must reproduce the calibrated known-bad set"
    assert page_result["escalate_r3"] is True


def test_every_body_line_has_bbox(page_result):
    body = [l for l in page_result["lines"] if l["role"] == "body"]
    assert body and all(l.get("bbox") for l in body), "reocr_page must attach a bbox to every body line"


def test_every_flagged_verse_maps_to_a_usable_crop(page_result):
    import verse_geom
    crops = verse_geom.verse_crops(page_result, BOOK, CH)
    cs = page_result.get("cross_source") or {}
    for v in cs.get("flagged_verses") or []:
        assert v in crops, f"flagged verse {v} not mapped by verse_geom"
        box = crops[v]["crop"]
        assert box is not None, f"flagged verse {v} has no crop geometry (would force an OPEN)"
        x0, y0, x1, y1 = box
        assert 0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0, f"v{v} crop out of unit box: {box}"


def test_crops_are_vertically_ordered_by_verse(page_result):
    """Verse order == top->bottom reading order on this single-column prose page (a sanity check on geometry)."""
    import verse_geom
    crops = verse_geom.verse_crops(page_result, BOOK, CH)
    ys = [(v, crops[v]["crop"][1]) for v in sorted(crops) if crops[v]["crop"]]
    # verses 13..26 are the clean single-column midbody; their crop tops must increase with verse number
    mid = [(v, y) for v, y in ys if 13 <= v <= 26]
    for (va, ya), (vb, yb) in zip(mid, mid[1:]):
        assert ya <= yb + 1e-6, f"v{va}(y={ya:.3f}) should sit at/above v{vb}(y={yb:.3f})"
