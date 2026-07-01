"""Unit tests for the synoptic precision/recall scorer (fixtures/validation-mm/score_synoptic.py).

The scorer itself runs against a locally-built collection whose text bodies are gitignored, so it
cannot run in CI. These tests exercise its logic on synthetic geometries + records so the metric is
regression-guarded: verse-ref parsing, cross-book classification, pooled recall, record-level
precision, and the true-negative false-link rate."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from palimpsest.alignment.records import AlignmentRecord

_MOD = Path(__file__).parent / "fixtures" / "validation-mm" / "score_synoptic.py"
_spec = importlib.util.spec_from_file_location("score_synoptic", _MOD)
assert _spec is not None and _spec.loader is not None
ss = importlib.util.module_from_spec(_spec)
sys.modules["score_synoptic"] = ss  # register before exec so @dataclass can resolve its module
_spec.loader.exec_module(ss)


def test_parse_ref_handles_ranges_singles_suffixes_and_cross_chapter() -> None:
    assert ss.parse_ref("3:1-6") == [(3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6)]
    assert ss.parse_ref("10:42") == [(10, 42)]
    full = ss.parse_ref("1:1-17")
    assert full[0] == (1, 1) and full[-1] == (1, 17) and len(full) == 17
    assert ss.parse_ref("3:16a") == [(3, 16)]            # scholarly letter suffix
    assert ss.parse_ref("3:1-6a")[-1] == (3, 6)          # letter suffix on a range end
    assert ss.parse_ref("26:1-27:2") == [(26, 1), (27, 2)]  # cross-chapter keeps endpoints


def _geom(book_verses: list[tuple[str, int, int]]):
    """Build a MemberGeometry from an ordered list of (book, chapter, verse) — index == paragraph."""
    para_book = [b for (b, _c, _v) in book_verses]
    verse_para = {(b, c, v): i for i, (b, c, v) in enumerate(book_verses)}
    return ss.MemberGeometry(para_book=para_book, verse_para=verse_para)


def _rec(qs: int, qe: int, ts: int, te: int, score: float = 5.0) -> AlignmentRecord:
    return AlignmentRecord(query_id="a", query_start=qs, query_end=qe,
                           target_id="b", target_start=ts, target_end=te, score=score)


def test_score_detects_shared_pericope_and_flags_unique_false_link() -> None:
    # Member a = Matthew subtext: paras 0-2 = Mt 3:1-3 (shared), para 3 = Mt 5:1 (unique).
    a = _geom([("Matthew", 3, 1), ("Matthew", 3, 2), ("Matthew", 3, 3), ("Matthew", 5, 1)])
    # Member b = Mark subtext: paras 0-1 = Mk 1:2-3 (shared), para 2 = Mk 16:9 (unique).
    b = _geom([("Mark", 1, 2), ("Mark", 1, 3), ("Mark", 16, 9)])
    geoms = {"a": a, "b": b}
    shared = [{"title": "JtB", "matthew": "3:1-3", "mark": "1:2-3", "confidence": "high"}]
    m_unique = [{"title": "Genealogy", "matthew": "5:1", "confidence": "high"}]
    k_unique = [{"title": "Capernaum demoniac", "mark": "16:9", "confidence": "high"}]

    tp = _rec(0, 3, 0, 2)   # Mt 3:1-3  <->  Mk 1:2-3   (true synoptic link)
    fp = _rec(3, 4, 0, 1)   # Mt 5:1 (unique)  <->  Mk 1:2   (spurious cross-book link)
    s = ss.score_synoptic(shared, m_unique, k_unique, geoms, {("a", "b"): [tp, fp]})

    assert s.total_shared == 1 and s.detected_shared == 1
    assert s.recall == pytest.approx(1.0)
    assert s.crossbook_records == 2
    assert s.crossbook_hits_shared == 1 and s.crossbook_on_unique == 1
    assert s.precision == pytest.approx(0.5)             # 1 hit / (1 hit + 1 on-unique)
    assert s.total_unique == 2 and s.unique_falsely_linked == 1
    assert s.tn_false_link_rate == pytest.approx(0.5)


def test_same_book_translation_edge_is_not_a_synoptic_detection() -> None:
    # Two Matthew translations aligning end-to-end: a same-book edge, NOT a cross-book synoptic hit.
    a = _geom([("Matthew", 3, 1), ("Matthew", 3, 2)])
    b = _geom([("Matthew", 3, 1), ("Matthew", 3, 2)])
    shared = [{"matthew": "3:1-2", "mark": "1:1", "confidence": "high"}]
    s = ss.score_synoptic(shared, [], [], {"a": a, "b": b}, {("a", "b"): [_rec(0, 2, 0, 2, score=500.0)]})
    assert s.crossbook_records == 0     # both sides Matthew -> not cross-book
    assert s.detected_shared == 0       # no Mark side exists to link


def test_missed_pericope_lowers_recall_without_false_positive() -> None:
    a = _geom([("Matthew", 3, 1), ("Matthew", 3, 2)])
    b = _geom([("Mark", 1, 2), ("Mark", 1, 3)])
    shared = [
        {"matthew": "3:1", "mark": "1:2", "confidence": "high"},   # will be detected
        {"matthew": "3:2", "mark": "1:3", "confidence": "high"},   # left undetected
    ]
    s = ss.score_synoptic(shared, [], [], {"a": a, "b": b}, {("a", "b"): [_rec(0, 1, 0, 1)]})
    assert s.total_shared == 2 and s.detected_shared == 1
    assert s.recall == pytest.approx(0.5)
    assert s.crossbook_on_unique == 0   # no unique regions touched -> precision stays perfect
    assert s.precision == pytest.approx(1.0)
