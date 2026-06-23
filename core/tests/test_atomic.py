"""Tests for atomic filesystem writes + run-provenance records (guard-rail G3)."""

import json

import pytest

from palimpsest.atomic import atomic_write_bytes, atomic_write_text, write_run_provenance


class TestAtomicWrite:
    def test_write_text_creates_file_and_parent_dirs(self, tmp_path):
        p = tmp_path / "sub" / "f.txt"
        atomic_write_text(p, "hello")
        assert p.read_text() == "hello"

    def test_write_bytes_roundtrip(self, tmp_path):
        p = tmp_path / "f.bin"
        atomic_write_bytes(p, b"\x00\x01\x02")
        assert p.read_bytes() == b"\x00\x01\x02"

    def test_overwrite_replaces_content(self, tmp_path):
        p = tmp_path / "f.txt"
        atomic_write_text(p, "old")
        atomic_write_text(p, "new")
        assert p.read_text() == "new"

    def test_no_temp_file_left_behind_on_success(self, tmp_path):
        p = tmp_path / "f.txt"
        atomic_write_text(p, "x")
        assert [c.name for c in tmp_path.iterdir()] == ["f.txt"]

    def test_failed_replace_leaves_original_intact_and_no_temp(self, tmp_path, monkeypatch):
        # The whole point of the temp+replace dance: a failure mid-write must not corrupt the existing
        # file or leave junk. Force os.replace to fail after the temp is written.
        import palimpsest.atomic as atomic_mod

        p = tmp_path / "f.txt"
        atomic_write_text(p, "original")

        def boom(src, dst):
            raise OSError("replace failed")

        monkeypatch.setattr(atomic_mod.os, "replace", boom)
        with pytest.raises(OSError, match="replace failed"):
            atomic_write_text(p, "new-but-doomed")

        assert p.read_text() == "original"
        assert [c.name for c in tmp_path.iterdir()] == ["f.txt"]


class TestRunProvenance:
    def test_writes_run_json_with_required_fields(self, tmp_path):
        path = write_run_provenance(tmp_path, "topics", {"n_topics": 25, "method": "nmf"})
        assert path == tmp_path / "topics.run.json"
        rec = json.loads(path.read_text())
        assert rec["track"] == "topics"
        assert rec["parameters"] == {"n_topics": 25, "method": "nmf"}
        assert rec["run_id"]
        assert rec["timestamp"]
        assert rec["palimpsest_version"]

    def test_extra_fields_merged(self, tmp_path):
        path = write_run_provenance(tmp_path, "x", {}, extra={"note": "hi"})
        rec = json.loads(path.read_text())
        assert rec["note"] == "hi"
