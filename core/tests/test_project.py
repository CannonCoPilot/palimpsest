"""Tests for project directory management."""

from pathlib import Path
from types import SimpleNamespace

import pytest

import palimpsest.project as pj
from palimpsest.project import Project, _make_slug, _relocate_sections, ingest_file


class TestRelocateSections:
    def test_reanchors_headings_to_normalized_text(self):
        # The raw .offset values are deliberately bogus. Each heading is unique, so
        # its lone occurrence is chosen regardless of the (mis)hint — relocation
        # tolerates bad offsets when the heading is unambiguous.
        normalized = (
            "Front matter.\n\nGenesis Chapter 1\n\nIn the beginning.\n\n"
            "Genesis Chapter 2\n\nThus the heavens were finished."
        )
        secs = [
            SimpleNamespace(heading_text="Genesis Chapter 1", offset=9991),
            SimpleNamespace(heading_text="Genesis Chapter 2", offset=99992),
        ]
        out = _relocate_sections(secs, normalized)
        assert len(out) == 2
        assert [normalized[a:b] for _, a, b in out] == ["Genesis Chapter 1", "Genesis Chapter 2"]

    def test_anchors_to_body_not_inlined_toc(self):
        # An inlined TOC repeats every heading near the front, then the real
        # divisions follow. Given the body offsets as hints, relocation must pick
        # the body occurrence, not the TOC link — the TOC-relocation misfire that
        # a plain first-match search caused.
        normalized = (
            "Contents\nChapter One\nChapter Two\n\n"          # inlined TOC up front
            "Chapter One\n" + ("aaa " * 30) + "\n\n"
            "Chapter Two\n" + ("bbb " * 30)
        )
        toc_end = normalized.index("\n\n")
        c1 = normalized.index("Chapter One", toc_end)
        c2 = normalized.index("Chapter Two", toc_end)
        secs = [
            SimpleNamespace(heading_text="Chapter One", offset=c1),
            SimpleNamespace(heading_text="Chapter Two", offset=c2),
        ]
        out = _relocate_sections(secs, normalized, len(normalized))
        assert [normalized[a:b] for _, a, b in out] == ["Chapter One", "Chapter Two"]
        assert all(start >= toc_end for _, start, _ in out), "headings anchored inside the TOC"

    def test_drops_unlocatable_heading(self):
        normalized = "Genesis Chapter 1\n\nIn the beginning."
        secs = [
            SimpleNamespace(heading_text="Genesis Chapter 1", offset=0),
            SimpleNamespace(heading_text="Nonexistent Heading", offset=0),
        ]
        out = _relocate_sections(secs, normalized)
        assert [s.heading_text for s, _, _ in out] == ["Genesis Chapter 1"]

    def test_monotonic_resolves_duplicate_headings_in_order(self):
        normalized = "Chapter 1\n\naaa\n\nChapter 1\n\nbbb"
        secs = [
            SimpleNamespace(heading_text="Chapter 1", offset=0),
            SimpleNamespace(heading_text="Chapter 1", offset=0),
        ]
        out = _relocate_sections(secs, normalized)
        assert len(out) == 2
        assert out[0][1] == 0  # first occurrence
        assert out[1][1] == normalized.index("Chapter 1", 5)  # second, found forward


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

    def test_reimport_same_file_replaces(self, pp_ch1_txt: Path, tmp_path: Path):
        # Re-importing the same source file replaces it in place — one project, no error.
        p1 = ingest_file(pp_ch1_txt, tmp_path, title="test")
        p2 = ingest_file(pp_ch1_txt, tmp_path, title="test")
        assert p1.metadata.id == p2.metadata.id
        dirs = [d for d in tmp_path.iterdir() if (d / "metadata.json").exists()]
        assert len(dirs) == 1

    def test_slug_is_deterministic_from_filename_not_title(self, pp_ch1_txt: Path, tmp_path: Path):
        # The same file under different titles maps to one project (slug from filename),
        # so a title-only difference can never create a duplicate.
        p1 = ingest_file(pp_ch1_txt, tmp_path, title="First Title")
        p2 = ingest_file(pp_ch1_txt, tmp_path, title="A Completely Different Title")
        assert p1.metadata.id == p2.metadata.id == _make_slug(pp_ch1_txt.name)
        dirs = [d for d in tmp_path.iterdir() if (d / "metadata.json").exists()]
        assert len(dirs) == 1

    def test_legacy_slug_duplicate_is_replaced(self, pp_ch1_txt: Path, tmp_path: Path):
        # A pre-existing project for the same source file under a *different* (legacy)
        # slug is removed on re-import, not left behind as a duplicate.
        first = ingest_file(pp_ch1_txt, tmp_path, title="test")
        legacy = tmp_path / "legacy-title-slug"
        first.path.rename(legacy)  # simulate a project saved under an old title-based id
        again = ingest_file(pp_ch1_txt, tmp_path, title="test")
        assert not legacy.exists()
        dirs = [d for d in tmp_path.iterdir() if (d / "metadata.json").exists()]
        assert [d.name for d in dirs] == [again.metadata.id]

    def test_source_name_overrides_identity(self, pp_ch1_txt: Path, tmp_path: Path):
        # Uploads pass the original filename via source_name; the temp path name is ignored.
        proj = ingest_file(pp_ch1_txt, tmp_path, source_name="My Real Book.txt")
        assert proj.metadata.id == _make_slug("My Real Book.txt")
        assert proj.metadata.source_file == "My Real Book.txt"

    def test_slug_collision_different_source_raises_without_overwrite(
        self, pp_ch1_txt: Path, tmp_path: Path
    ):
        # Two *different* source files that slug to the same id must not clobber silently.
        ingest_file(pp_ch1_txt, tmp_path, source_name="Clash.txt")
        with pytest.raises(FileExistsError):
            ingest_file(pp_ch1_txt, tmp_path, source_name="clash.txt", overwrite=False)

    def test_segments_jsonl_has_paragraphs(self, pp_ch1_txt: Path, tmp_path: Path):
        project = ingest_file(pp_ch1_txt, tmp_path)
        from palimpsest.annotation.serializer import read_track
        anns = read_track(project.path / "tracks" / "segments.jsonl")
        para_anns = [a for a in anns if "paragraph" in a.body.lfo_type]
        assert len(para_anns) >= 5
        assert all(a.evidence_level == "E1" for a in para_anns)

    def test_segments_manifest_created(self, pp_ch1_txt: Path, tmp_path: Path):
        project = ingest_file(pp_ch1_txt, tmp_path)
        manifest_path = project.path / "manifests" / "segments.manifest.json"
        assert manifest_path.exists(), "segments.manifest.json not created during ingest"
        import json
        manifest = json.loads(manifest_path.read_text())
        assert manifest["trackName"] == "segments"
        assert "colorScheme" in manifest

    def test_paragraphs_method(self, pp_ch1_txt: Path, tmp_path: Path):
        project = ingest_file(pp_ch1_txt, tmp_path)
        paras = project.paragraphs()
        assert len(paras) >= 5
        for start, end, text in paras:
            assert start < end
            assert len(text) > 0


class TestLoadSpacyModel:
    """A missing spaCy model must fall back *loudly* (RuntimeWarning), never silently —
    a quiet model swap changes entity/syntax analysis with no trace (finding 305)."""

    @pytest.fixture(autouse=True)
    def _clean_model_cache(self):
        # _NLP_MODEL_CACHE is process-wide; clear before and after so a stub model
        # loaded here can't leak into other tests (or vice versa).
        pj._NLP_MODEL_CACHE.clear()
        yield
        pj._NLP_MODEL_CACHE.clear()

    def test_missing_model_warns_and_falls_back(self, monkeypatch):
        sentinel = object()

        def fake_load(name, *args, **kwargs):
            if name == pj._SPACY_FALLBACK:
                return sentinel
            raise OSError(f"[E050] Can't find model '{name}'")

        monkeypatch.setattr("spacy.load", fake_load)
        with pytest.warns(RuntimeWarning, match="falling back"):
            nlp = pj._load_spacy_model("en_core_web_lg")
        assert nlp is sentinel

    def test_missing_fallback_reraises(self, monkeypatch):
        # If the fallback itself is unavailable, a retry can't help — let spaCy's
        # own OSError (carrying its install hint) propagate instead of masking it.
        def fake_load(name, *args, **kwargs):
            raise OSError(f"[E050] Can't find model '{name}'")

        monkeypatch.setattr("spacy.load", fake_load)
        with pytest.raises(OSError):
            pj._load_spacy_model(pj._SPACY_FALLBACK)


class TestProjectLoad:
    def test_load_existing(self, pp_ch1_txt: Path, tmp_path: Path):
        original = ingest_file(pp_ch1_txt, tmp_path)
        loaded = Project.load(original.path)
        assert loaded.metadata.id == original.metadata.id
        assert loaded.metadata.word_count == original.metadata.word_count

    def test_load_missing_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            Project.load(tmp_path / "nonexistent")
