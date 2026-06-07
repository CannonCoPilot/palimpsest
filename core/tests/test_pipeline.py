"""Integration tests for the full pipeline (annotation + signal tracks)."""

from pathlib import Path

import pytest

from palimpsest.annotation.serializer import read_track, validate_annotation
from palimpsest.project import ingest_file
from palimpsest.tracks.registry import TrackRegistry


@pytest.fixture
def analyzed_project(pp_ch1_txt: Path, tmp_path: Path):
    """A project that has been fully ingested and analyzed.

    Signal tracks that require external services (embeddings, Ollama)
    are skipped gracefully, matching CLI behavior.
    """
    project = ingest_file(pp_ch1_txt, tmp_path, title="Pipeline Test")
    registry = TrackRegistry.discover()
    ordered = registry.dependency_order()

    for cls in ordered:
        ext = cls()
        try:
            result = ext.extract(project)
        except (FileNotFoundError, ValueError, RuntimeError):
            continue
        if ext.output_type == "annotation" and isinstance(result, list):
            from palimpsest.annotation.serializer import write_track

            track_path = project.path / "tracks" / f"{ext.name}.jsonl"
            write_track(track_path, result)

    return project


class TestFullPipeline:
    def test_all_tracks_written(self, analyzed_project):
        tracks_dir = analyzed_project.path / "tracks"
        expected = ["segments.jsonl", "entities.jsonl", "sentiment.jsonl",
                     "lexical.jsonl", "dialogue.jsonl", "topics.jsonl"]
        for name in expected:
            path = tracks_dir / name
            assert path.exists(), f"Missing track: {name}"
            assert path.stat().st_size > 0, f"Empty track: {name}"

    def test_all_annotations_valid_w3c(self, analyzed_project):
        tracks_dir = analyzed_project.path / "tracks"
        for jsonl_file in sorted(tracks_dir.glob("*.jsonl")):
            anns = read_track(jsonl_file)
            assert len(anns) > 0, f"No annotations in {jsonl_file.name}"
            for ann in anns[:10]:
                jld = ann.to_jsonld()
                errors = validate_annotation(jld)
                assert errors == [], f"{jsonl_file.name}: {errors}"

    def test_annotation_offsets_within_bounds(self, analyzed_project):
        text = analyzed_project.reference_text()
        text_len = len(text)
        tracks_dir = analyzed_project.path / "tracks"
        for jsonl_file in sorted(tracks_dir.glob("*.jsonl")):
            anns = read_track(jsonl_file)
            for ann in anns:
                sel = ann.target.selector
                assert 0 <= sel.start < sel.end <= text_len, (
                    f"{jsonl_file.name}: offset [{sel.start}, {sel.end}) "
                    f"out of bounds for text length {text_len}"
                )

    def test_topics_signal_valid(self, analyzed_project):
        import numpy as np

        from palimpsest.formats.signals import read_signal

        m, data = read_signal(analyzed_project.path / "signals", "topics_dist")
        assert data.shape[1] == 10
        assert data.shape[0] > 0
        row_sums = data.sum(axis=1)
        assert np.allclose(row_sums, 1.0, atol=0.01)

    def test_registry_discovers_all_tracks(self):
        reg = TrackRegistry.discover()
        names = reg.names()
        # 5 annotation tracks
        assert "entities" in names
        assert "sentiment" in names
        assert "lexical" in names
        assert "dialogue" in names
        assert "topics" in names
        # 4 signal tracks
        assert "narrative_arc" in names
        assert "rqa" in names
        assert "alphabet" in names
        assert "self_similarity" in names
        # 1 optional annotation track (coreference — BookNLP)
        assert "coreference" in names

    def test_dependency_order_valid(self):
        reg = TrackRegistry.discover()
        ordered = reg.dependency_order()
        names = [cls().name for cls in ordered]
        # 6 annotation tracks + 4 signal tracks = 10 total
        assert len(names) >= 10
        for cls in ordered:
            ext = cls()
            for dep in ext.depends_on:
                if dep.startswith("_"):
                    continue
                if dep not in names:
                    continue
                assert names.index(dep) < names.index(ext.name)
