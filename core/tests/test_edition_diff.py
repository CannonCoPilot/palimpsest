"""Tests for edition comparison (paragraph-level diff)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from palimpsest.alignment.edition_diff import (
    DiffRecord,
    DiffSummary,
    compute_edition_diff,
    write_diff_results,
    read_diff_results,
)


def _make_project(paragraphs: list[str]) -> MagicMock:
    """Create a mock Project with given paragraph texts."""
    project = MagicMock()
    result = []
    offset = 0
    for text in paragraphs:
        start = offset
        end = offset + len(text)
        result.append((start, end, text))
        offset = end + 2  # \n\n separator
    project.paragraphs.return_value = result
    return project


class TestDiffRecord:
    def test_to_dict_camelcase(self):
        r = DiffRecord(para_index_a=0, para_index_b=1, change_type="replace", text_a="old", text_b="new")
        d = r.to_dict()
        assert d["paraIndexA"] == 0
        assert d["paraIndexB"] == 1
        assert d["changeType"] == "replace"
        assert d["textA"] == "old"
        assert d["textB"] == "new"

    def test_from_dict_camelcase(self):
        r = DiffRecord.from_dict({"paraIndexA": 5, "paraIndexB": 3, "changeType": "insert", "textA": "", "textB": "added"})
        assert r.para_index_a == 5
        assert r.para_index_b == 3
        assert r.change_type == "insert"

    def test_from_dict_snake_case(self):
        r = DiffRecord.from_dict({"para_index_a": 2, "para_index_b": 4, "change_type": "delete", "text_a": "gone", "text_b": ""})
        assert r.para_index_a == 2
        assert r.change_type == "delete"


class TestDiffSummary:
    def test_to_dict_camelcase(self):
        s = DiffSummary(total_paragraphs_a=10, total_paragraphs_b=12, aligned_pairs=8, insertions=2, deletions=1, replacements=1, unchanged=6)
        d = s.to_dict()
        assert d["totalParagraphsA"] == 10
        assert d["totalParagraphsB"] == 12
        assert d["replacements"] == 1
        assert d["unchanged"] == 6


class TestComputeEditionDiff:
    def test_identical_texts(self):
        texts = ["Hello world", "Second paragraph", "Third paragraph"]
        proj_a = _make_project(texts)
        proj_b = _make_project(texts)
        records, summary = compute_edition_diff(proj_a, proj_b)
        assert summary.unchanged == 3
        assert summary.insertions == 0
        assert summary.deletions == 0
        assert summary.replacements == 0
        assert len(records) == 0  # equal records are not emitted

    def test_single_insertion(self):
        proj_a = _make_project(["A", "B"])
        proj_b = _make_project(["A", "NEW", "B"])
        records, summary = compute_edition_diff(proj_a, proj_b)
        assert summary.insertions >= 1
        insert_records = [r for r in records if r.change_type == "insert"]
        assert len(insert_records) >= 1

    def test_single_deletion(self):
        proj_a = _make_project(["A", "REMOVED", "B"])
        proj_b = _make_project(["A", "B"])
        _records, summary = compute_edition_diff(proj_a, proj_b)
        assert summary.deletions >= 1

    def test_replacement(self):
        proj_a = _make_project(["Hello", "World"])
        proj_b = _make_project(["Hello", "Earth"])
        records, summary = compute_edition_diff(proj_a, proj_b)
        assert summary.replacements >= 1
        replace_records = [r for r in records if r.change_type == "replace"]
        assert len(replace_records) >= 1
        assert replace_records[0].text_a == "World"
        assert replace_records[0].text_b == "Earth"

    def test_text_truncation(self):
        long_text = "x" * 1000
        proj_a = _make_project([long_text])
        proj_b = _make_project(["short"])
        records, _ = compute_edition_diff(proj_a, proj_b)
        for r in records:
            assert len(r.text_a) <= 500
            assert len(r.text_b) <= 500


class TestDiffRoundtrip:
    def test_write_read_roundtrip(self, tmp_path: Path):
        records = [
            DiffRecord(para_index_a=0, para_index_b=0, change_type="replace", text_a="old", text_b="new"),
            DiffRecord(para_index_a=-1, para_index_b=1, change_type="insert", text_a="", text_b="added"),
        ]
        summary = DiffSummary(total_paragraphs_a=5, total_paragraphs_b=6, aligned_pairs=4, insertions=1, deletions=0, replacements=1, unchanged=3)

        path = tmp_path / "diff.json"
        write_diff_results(path, records, summary)

        loaded_records, loaded_summary = read_diff_results(path)
        assert len(loaded_records) == 2
        assert loaded_records[0].change_type == "replace"
        assert loaded_summary.total_paragraphs_a == 5
        assert loaded_summary.unchanged == 3
