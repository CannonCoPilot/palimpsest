"""Collections tier — phase C5 (liftover leaf: project features across an A↔B alignment).

``alignment.liftover`` is a pure leaf — it never touches disk. These tests drive :class:`AlignmentMap`
with hand-built paragraph-indexed records plus each side's per-paragraph character spans, and assert
the block-granular projection maths and the drop-reporting directly.

Fixture: text A has 4 paragraphs at char spans A_SPANS, text B has 3 at B_SPANS. The alignment
(query=A, target=B) has two blocks: A-paras [0,2)↔B-paras [0,1) and A-paras [2,4)↔B-paras [1,3),
i.e. A-chars (0,25)↔B-chars (0,8) and A-chars (25,55)↔B-chars (8,45).
"""
from __future__ import annotations

import pytest

from palimpsest.alignment.liftover import AlignmentMap, Block
from palimpsest.alignment.records import AlignmentRecord

A_SPANS = [(0, 10), (10, 25), (25, 40), (40, 55)]
B_SPANS = [(0, 8), (8, 30), (30, 45)]


def _records() -> list[AlignmentRecord]:
    return [
        AlignmentRecord("A", 0, 2, "B", 0, 1, score=9.0),
        AlignmentRecord("A", 2, 4, "B", 1, 3, score=8.0),
    ]


def test_from_records_builds_char_blocks() -> None:
    amap = AlignmentMap.from_records(_records(), A_SPANS, B_SPANS, source="query")
    assert amap.blocks == [Block(0, 25, 0, 8), Block(25, 55, 8, 45)]


def test_project_span_single_block() -> None:
    amap = AlignmentMap.from_records(_records(), A_SPANS, B_SPANS, source="query")
    # A-chars [5,12) sit wholly in the first block → its whole B span (block-granular).
    assert amap.project_span(5, 12) == [(0, 8)]


def test_project_span_spanning_two_blocks_merges_adjacent_dst() -> None:
    amap = AlignmentMap.from_records(_records(), A_SPANS, B_SPANS, source="query")
    # [20,30) overlaps both blocks → (0,8)+(8,45) are adjacent → merged.
    assert amap.project_span(20, 30) == [(0, 45)]


def test_project_span_no_overlap_is_empty() -> None:
    amap = AlignmentMap.from_records(_records(), A_SPANS, B_SPANS, source="query")
    assert amap.project_span(60, 70) == []
    assert amap.project_span(30, 30) == []  # empty interval


def test_lift_intervals_reports_dropped() -> None:
    amap = AlignmentMap.from_records(_records(), A_SPANS, B_SPANS, source="query")
    lifted, dropped = amap.lift_intervals([(5, 12), (60, 70)])
    assert lifted == [(0, 8)]
    assert dropped == [(60, 70)]  # touched no aligned block — reported, not silent


def test_reverse_direction_lifts_target_to_query() -> None:
    amap = AlignmentMap.from_records(_records(), B_SPANS, A_SPANS, source="target")
    # Now source frame is B: B-chars [1,5) → A block (0,25).
    assert amap.blocks == [Block(0, 8, 0, 25), Block(8, 45, 25, 55)]
    assert amap.project_span(1, 5) == [(0, 25)]


def test_exclusive_end_is_clamped_not_dropped() -> None:
    # Record runs one paragraph past the last (query_end=5, only 4 paras) → clamped to cover para 3.
    rec = [AlignmentRecord("A", 3, 5, "B", 2, 3, score=1.0)]
    amap = AlignmentMap.from_records(rec, A_SPANS, B_SPANS, source="query")
    assert amap.blocks == [Block(40, 55, 30, 45)]


def test_out_of_range_record_is_skipped() -> None:
    # query_start=4 is >= paragraph count (4) → no valid source span → skipped, not mis-projected.
    rec = [AlignmentRecord("A", 4, 6, "B", 0, 1, score=1.0)]
    amap = AlignmentMap.from_records(rec, A_SPANS, B_SPANS, source="query")
    assert amap.blocks == []


def test_empty_and_covered_spans() -> None:
    empty = AlignmentMap([])
    assert empty.project_span(0, 100) == []
    assert empty.lift_intervals([(0, 10)]) == ([], [(0, 10)])

    amap = AlignmentMap.from_records(_records(), A_SPANS, B_SPANS, source="query")
    assert amap.src_covered == [(0, 55)]
    assert amap.dst_covered == [(0, 45)]


def test_invalid_source_raises() -> None:
    with pytest.raises(ValueError):
        AlignmentMap.from_records(_records(), A_SPANS, B_SPANS, source="sideways")
