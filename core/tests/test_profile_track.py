"""Tests for ProfileTrack — whole-document descriptive statistics (Wave-0 P4, FR-8, NFR-7)."""

import json
from pathlib import Path

import pytest

from palimpsest.project import ingest_file
from palimpsest.runner import extract_masked, persist_track_outputs
from palimpsest.tracks.base import TrackExtractor
from palimpsest.tracks.profile_track import ProfileTrack
from palimpsest.tracks.registry import TrackRegistry


@pytest.fixture
def project(pp_ch1_txt: Path, tmp_path: Path):
    return ingest_file(pp_ch1_txt, tmp_path, title="profile-test")


@pytest.fixture
def profile_manifest(project) -> dict:
    track = ProfileTrack()
    result = extract_masked(project, track, "")
    persist_track_outputs(project.path, track, result)
    return json.loads((project.path / "signals" / "profile.json").read_text())


class TestProtocol:
    def test_is_track_extractor(self):
        assert isinstance(ProfileTrack(), TrackExtractor)

    def test_required_attributes(self):
        t = ProfileTrack()
        assert t.name == "profile"
        assert t.output_type == "signal"
        assert t.depends_on == []  # not a signal-consumer → runs on the analysis view

    def test_auto_discovered(self):
        assert TrackRegistry.discover().get("profile") is ProfileTrack


class TestExtract:
    def test_emits_profile_signal(self, profile_manifest):
        assert profile_manifest["type"] == "profile"

    def test_report_has_counts_and_diversity(self, profile_manifest):
        report = profile_manifest["metadata"]["report"]
        assert report["counts"]["tokens"] > 0
        assert report["counts"]["types"] > 0
        div = report["lexical_diversity"]
        assert set(div) == {"ttr", "mattr", "mtld", "yules_k"}
        assert 0.0 < div["ttr"] <= 1.0

    def test_distributions_present(self, profile_manifest):
        dists = profile_manifest["metadata"]["distributions"]
        assert set(dists) == {"word_length", "sentence_length", "paragraph_length"}
        assert dists["word_length"]["n"] > 0
        assert sum(dists["word_length"]["counts"]) == dists["word_length"]["n"]

    def test_descriptive_framing_nfr7(self, profile_manifest):
        # NFR-7: descriptive-not-inferential — the manifest must say so and carry caveats.
        md = profile_manifest["metadata"]
        assert md["framing"] == "descriptive"
        assert any("reference corpus" in c for c in md["caveats"])

    def test_top_ngrams_and_function_words(self, profile_manifest):
        report = profile_manifest["metadata"]["report"]
        assert len(report["top_bigrams"]) > 0
        assert all(len(row) == 2 for row in report["top_bigrams"])
        assert all(len(row) == 3 for row in report["function_words"])

    def test_deterministic(self, project):
        track = ProfileTrack()
        a = json.loads(extract_masked(project, track, "").read_text())
        b = json.loads(extract_masked(project, track, "").read_text())
        assert a["metadata"]["report"] == b["metadata"]["report"]
