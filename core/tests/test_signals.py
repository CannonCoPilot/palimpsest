"""Tests for signal tracks — narrative arc, RQA, alphabet, self-similarity."""

import json

import numpy as np
import pytest

from palimpsest.formats.signals import SignalManifest, read_signal, write_signal
from palimpsest.project import Project


@pytest.fixture
def small_project(tmp_path):
    """Create a minimal project for signal track testing."""
    project_dir = tmp_path / "test-project"
    for d in ["tracks", "signals", "manifests", "cache"]:
        (project_dir / d).mkdir(parents=True)

    text = (
        "It is a truth universally acknowledged, that a single man in possession "
        "of a good fortune, must be in want of a wife.\n\n"
        "However little known the feelings or views of such a man may be on his "
        "first entering a neighbourhood, this truth is so well fixed in the minds "
        "of the surrounding families, that he is considered as the rightful property "
        "of some one or other of their daughters.\n\n"
        "My dear Mr. Bennet, said his lady to him one day, have you heard that "
        "Netherfield Park is let at last?\n\n"
        "Mr. Bennet replied that he had not.\n\n"
        "But it is, returned she; for Mrs. Long has just been here, and she told "
        "me all about it."
    )
    (project_dir / "reference.txt").write_text(text)
    (project_dir / "reference.sha256").write_text("abc123")

    metadata = {
        "id": "test-project",
        "title": "Test",
        "language": "en",
        "source_format": "txt",
        "source_file": "test.txt",
        "ingest_date": "2026-06-07",
        "palimpsest_version": "0.1.0",
        "reference_sha256": "abc123",
        "word_count": len(text.split()),
        "paragraph_count": 5,
        "section_count": 1,
        "sentence_count": 5,
        "character_count": len(text),
    }
    (project_dir / "metadata.json").write_text(json.dumps(metadata))

    # Write minimal track files for alphabet track dependency
    for track in ["sentiment", "lexical", "dialogue", "topics"]:
        (project_dir / "tracks" / f"{track}.jsonl").write_text("")

    return Project.load(project_dir)


class TestNarrativeArc:
    def test_produces_signal(self, small_project):
        from palimpsest.tracks.narrative_arc import NarrativeArcTrack

        track = NarrativeArcTrack()
        result = track.extract(small_project)
        assert result.exists()
        assert result.name == "narrative_arc.json"

    def test_binary_size(self, small_project):
        from palimpsest.tracks.narrative_arc import NarrativeArcTrack

        NarrativeArcTrack().extract(small_project)
        bin_path = small_project.path / "signals" / "narrative_arc.bin"
        assert bin_path.exists()
        assert bin_path.stat().st_size == 60  # 5 segments * 3 dims * 4 bytes

    def test_values_in_range(self, small_project):
        from palimpsest.tracks.narrative_arc import NarrativeArcTrack

        NarrativeArcTrack().extract(small_project)
        _, data = read_signal(small_project.path / "signals", "narrative_arc")
        assert data.shape == (5, 3)
        assert np.all(data >= 0.0)
        assert np.all(data <= 1.0)

    def test_deterministic(self, small_project):
        from palimpsest.tracks.narrative_arc import NarrativeArcTrack

        track = NarrativeArcTrack()
        track.extract(small_project)
        _, data1 = read_signal(small_project.path / "signals", "narrative_arc")
        track.extract(small_project)
        _, data2 = read_signal(small_project.path / "signals", "narrative_arc")
        np.testing.assert_array_equal(data1, data2)

    def test_manifest_content(self, small_project):
        from palimpsest.tracks.narrative_arc import NarrativeArcTrack

        track = NarrativeArcTrack()
        m = track.manifest()
        assert m["trackName"] == "narrative_arc"
        assert "dedicatedView" in m

    def test_properties(self):
        from palimpsest.tracks.narrative_arc import NarrativeArcTrack

        track = NarrativeArcTrack()
        assert track.name == "narrative_arc"
        assert track.output_type == "signal"
        assert track.evidence_level == "E5"
        assert track.depends_on == []


class TestRQA:
    def test_produces_signal(self, small_project):
        from palimpsest.tracks.rqa import RQATrack

        track = RQATrack()
        result = track.extract(small_project)
        assert result.exists()
        assert result.name == "rqa.json"

    def test_values_in_range(self, small_project):
        from palimpsest.tracks.rqa import RQATrack

        RQATrack().extract(small_project)
        _, data = read_signal(small_project.path / "signals", "rqa")
        assert data.ndim == 2
        assert data.shape[1] == 3
        assert np.all(data >= 0.0)
        assert np.all(data <= 1.0)

    def test_tfidf_fallback(self, small_project):
        from palimpsest.tracks.rqa import RQATrack

        # No embeddings.db, should fall back to TF-IDF
        RQATrack().extract(small_project)
        manifest_path = small_project.path / "signals" / "rqa.json"
        manifest = json.loads(manifest_path.read_text())
        assert manifest["metadata"]["state_vector_source"] == "tfidf"

    def test_properties(self):
        from palimpsest.tracks.rqa import RQATrack

        track = RQATrack()
        assert track.name == "rqa"
        assert track.output_type == "signal"
        assert track.evidence_level == "E5"

    def test_extract_windows(self):
        from palimpsest.tracks.rqa import _extract_windows

        paras = [
            (0, 100, "word " * 20),
            (100, 200, "word " * 20),
            (200, 300, "word " * 20),
            (300, 400, "word " * 20),
            (400, 500, "word " * 20),
        ]
        windows = _extract_windows(paras, window_words=40, overlap_words=20)
        assert len(windows) > 0
        for w in windows:
            assert len(w) > 0


class TestAlphabet:
    def test_produces_manifest(self, small_project):
        from palimpsest.tracks.alphabet import AlphabetTrack

        track = AlphabetTrack()
        result = track.extract(small_project)
        assert result.exists()
        assert result.name == "alphabet.json"

    def test_sequence_length_matches_paragraphs(self, small_project):
        from palimpsest.tracks.alphabet import AlphabetTrack

        AlphabetTrack().extract(small_project)
        manifest_path = small_project.path / "signals" / "alphabet.json"
        manifest = json.loads(manifest_path.read_text())
        seq = manifest["metadata"]["sequence"]
        assert len(seq) == small_project.metadata.paragraph_count

    def test_no_binary_file(self, small_project):
        from palimpsest.tracks.alphabet import AlphabetTrack

        AlphabetTrack().extract(small_project)
        assert not (small_project.path / "signals" / "alphabet.bin").exists()

    def test_deterministic(self, small_project):
        from palimpsest.tracks.alphabet import AlphabetTrack

        track = AlphabetTrack()
        track.extract(small_project)
        m1 = json.loads((small_project.path / "signals" / "alphabet.json").read_text())
        track.extract(small_project)
        m2 = json.loads((small_project.path / "signals" / "alphabet.json").read_text())
        assert m1["metadata"]["sequence"] == m2["metadata"]["sequence"]

    def test_properties(self):
        from palimpsest.tracks.alphabet import AlphabetTrack

        track = AlphabetTrack()
        assert track.name == "alphabet"
        assert track.output_type == "signal"
        assert track.evidence_level == "E5"
        assert "sentiment" in track.depends_on


class TestCoreference:
    def test_properties(self):
        from palimpsest.tracks.coreference import CoreferenceExtractor

        track = CoreferenceExtractor()
        assert track.name == "coreference"
        assert track.output_type == "annotation"
        assert track.evidence_level == "E4"
        assert "entities" in track.depends_on

    def test_graceful_fallback_without_booknlp(self, small_project):
        from palimpsest.tracks.coreference import BOOKNLP_AVAILABLE, CoreferenceExtractor

        track = CoreferenceExtractor()
        if not BOOKNLP_AVAILABLE:
            with pytest.raises(FileNotFoundError, match="BookNLP not installed"):
                track.extract(small_project)
        else:
            # BookNLP installed but may fail at runtime (model/version issues)
            with pytest.raises((FileNotFoundError, RuntimeError)):
                track.extract(small_project)

    def test_manifest(self):
        from palimpsest.tracks.coreference import CoreferenceExtractor

        m = CoreferenceExtractor().manifest()
        assert m["trackName"] == "coreference"
        assert "colorScheme" in m

    def test_parameters_report_availability(self):
        from palimpsest.tracks.coreference import BOOKNLP_AVAILABLE, CoreferenceExtractor

        p = CoreferenceExtractor().parameters()
        assert "coreference.available" in p
        assert p["coreference.available"] is BOOKNLP_AVAILABLE


class TestSignalIO:
    def test_write_read_roundtrip(self, tmp_path):
        data = np.array([[1.0, 0.5], [0.5, 1.0]], dtype=np.float32)
        manifest = SignalManifest(
            type="matrix",
            name="test_matrix",
            source="test/0.1",
            reference_sha256="abc",
            dimensions=[2, 2],
        )
        write_signal(tmp_path, data, manifest)
        loaded_manifest, loaded_data = read_signal(tmp_path, "test_matrix")
        assert loaded_manifest.name == "test_matrix"
        np.testing.assert_array_almost_equal(loaded_data, data)

    def test_vector_signal(self, tmp_path):
        data = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
        manifest = SignalManifest(
            type="vector",
            name="test_vec",
            source="test/0.1",
            reference_sha256="abc",
            dimensions=[5],
        )
        write_signal(tmp_path, data, manifest)
        _, loaded = read_signal(tmp_path, "test_vec")
        assert loaded.shape == (5,)
        np.testing.assert_array_almost_equal(loaded, data)
