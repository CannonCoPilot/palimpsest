"""Tests for project directory management."""

from pathlib import Path

import pytest

from palimpsest.project import Project, _make_slug, ingest_file


class TestMakeSlug:
    def test_basic(self):
        assert _make_slug("Pride and Prejudice") == "pride-and-prejudice"

    def test_filename(self):
        assert _make_slug("pride-prejudice-ch1.txt") == "pride-prejudice-ch1"

    def test_special_chars(self):
        assert _make_slug("Hello, World!") == "hello-world"


class TestIngestFile:
    def test_creates_project_directory(self, pp_ch1_txt: Path, tmp_path: Path):
        project = ingest_file(pp_ch1_txt, tmp_path, title="Pride Chapter 1")
        assert project.path.exists()
        assert (project.path / "reference.txt").exists()
        assert (project.path / "metadata.json").exists()
        assert (project.path / "tracks" / "segments.jsonl").exists()

    def test_creates_all_subdirectories(self, pp_ch1_txt: Path, tmp_path: Path):
        project = ingest_file(pp_ch1_txt, tmp_path)
        for subdir in ["tracks", "signals", "manifests", "cache", "x-config", "exports"]:
            assert (project.path / subdir).is_dir()

    def test_metadata_fields(self, pp_ch1_txt: Path, tmp_path: Path):
        project = ingest_file(
            pp_ch1_txt, tmp_path,
            title="Pride and Prejudice Ch1",
            author="Jane Austen",
            year=1813,
        )
        m = project.metadata
        assert m.title == "Pride and Prejudice Ch1"
        assert m.author == "Jane Austen"
        assert m.year == 1813
        assert m.language == "en"
        assert m.word_count > 100
        assert m.paragraph_count >= 5
        assert m.sentence_count > 0
        assert m.character_count > 0
        assert len(m.reference_sha256) == 64

    def test_reference_text_normalized(self, pp_ch1_txt: Path, tmp_path: Path):
        project = ingest_file(pp_ch1_txt, tmp_path)
        text = project.reference_text()
        assert "Mr. Bennet" in text
        # Curly quotes should be normalized to straight
        assert "“" not in text  # left double curly
        assert "”" not in text  # right double curly

    def test_duplicate_ingest_raises(self, pp_ch1_txt: Path, tmp_path: Path):
        ingest_file(pp_ch1_txt, tmp_path, title="test")
        with pytest.raises(FileExistsError):
            ingest_file(pp_ch1_txt, tmp_path, title="test")

    def test_segments_jsonl_has_paragraphs(self, pp_ch1_txt: Path, tmp_path: Path):
        project = ingest_file(pp_ch1_txt, tmp_path)
        from palimpsest.annotation.serializer import read_track
        anns = read_track(project.path / "tracks" / "segments.jsonl")
        para_anns = [a for a in anns if "paragraph" in a.body.lfo_type]
        assert len(para_anns) >= 5
        assert all(a.evidence_level == "E1" for a in para_anns)

    def test_paragraphs_method(self, pp_ch1_txt: Path, tmp_path: Path):
        project = ingest_file(pp_ch1_txt, tmp_path)
        paras = project.paragraphs()
        assert len(paras) >= 5
        for start, end, text in paras:
            assert start < end
            assert len(text) > 0


class TestProjectLoad:
    def test_load_existing(self, pp_ch1_txt: Path, tmp_path: Path):
        original = ingest_file(pp_ch1_txt, tmp_path)
        loaded = Project.load(original.path)
        assert loaded.metadata.id == original.metadata.id
        assert loaded.metadata.word_count == original.metadata.word_count

    def test_load_missing_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            Project.load(tmp_path / "nonexistent")
