"""Tests for ChunkingTrack — the chunking layer-track (Wave-0 P2, FR-2/5/6/13/14).

These run the track directly on an ingested project (no masking view), so chunk ``segment_offsets``
stay in original coordinates and must anchor to the reference text. The masked-run + remap path is
covered by the runner/CLI parity tests; here the focus is the track's own output contract and the
capability/rendering/stats manifest backbone P5/P6 consume.
"""

import json
from pathlib import Path

import pytest

from palimpsest.project import ingest_file
from palimpsest.tracks.base import TrackExtractor
from palimpsest.tracks.chunking_track import ChunkingTrack
from palimpsest.tracks.registry import TrackRegistry


@pytest.fixture
def pp_project(pp_ch1_txt: Path, tmp_path: Path):
    return ingest_file(pp_ch1_txt, tmp_path, title="chunking-track-test")


def _run(project, **params) -> dict:
    track = ChunkingTrack()
    track.set_params(params)
    manifest_path = track.extract(project)
    return json.loads(manifest_path.read_text())


class TestChunkingTrackProtocol:
    def test_is_track_extractor(self):
        assert isinstance(ChunkingTrack(), TrackExtractor)

    def test_required_attributes(self):
        t = ChunkingTrack()
        assert t.name == "chunking"
        assert t.output_type == "signal"
        assert isinstance(t.depends_on, list) and t.depends_on == []
        assert t.lfo_types == ["signal.chunking"]
        assert t.evidence_level in ("E1", "E2", "E3", "E4", "E5")

    def test_auto_discovered(self):
        registry = TrackRegistry.discover()
        assert "chunking" in registry.names()
        assert registry.get("chunking") is ChunkingTrack


class TestChunkingTrackExtract:
    def test_writes_label_keyed_layer(self, pp_project):
        track = ChunkingTrack()
        track.set_params({"mode": "word", "size": 5})
        path = track.extract(pp_project)
        assert path.exists()
        assert path.name.startswith("chunking_") and path.suffix == ".json"
        assert path.parent == pp_project.path / "signals"

    def test_manifest_core_fields(self, pp_project):
        m = _run(pp_project, mode="word", size=5)
        assert m["type"] == "chunk-layer"
        assert m["name"].startswith("chunking_")
        assert m["segment_offsets"], "chunk spans must be emitted as segment_offsets (remap-handled)"
        assert m["dimensions"] == [len(m["segment_offsets"])]
        assert len(m["metadata"]["chunk_texts"]) == len(m["segment_offsets"])

    def test_offsets_anchor_to_text(self, pp_project):
        # Run directly (no masking view) so offsets are original coordinates: each chunk text must
        # equal reference_text()[start:end] — the same anchored contract _validate_chunks enforces.
        m = _run(pp_project, mode="word", size=7)
        text = pp_project.reference_text()
        offsets = m["segment_offsets"]
        texts = m["metadata"]["chunk_texts"]
        for (start, end), chunk_text in zip(offsets, texts):
            assert text[start:end] == chunk_text

    def test_capability_descriptor(self, pp_project):
        m = _run(pp_project, mode="word", size=5)
        cap = m["metadata"]["capability"]
        assert cap["kind"] == "chunk"
        assert cap["mode"] == "word"
        assert cap["overlapping"] is False
        assert cap["unit"] == "word"
        assert cap["size"] == 5
        assert isinstance(cap["analyzable_digest"], str) and len(cap["analyzable_digest"]) == 64

    def test_rendering_backbone(self, pp_project):
        m = _run(pp_project, mode="word", size=5)
        rendering = m["metadata"]["rendering"]
        assert rendering["track_view"] == "chunk-band"
        assert rendering["overviewBarRendering"]["type"] == "chunk-band"

    def test_stats_backbone(self, pp_project):
        m = _run(pp_project, mode="word", size=5)
        stats = m["metadata"]["stats"]
        assert stats["count"] == len(m["segment_offsets"])
        assert 0.0 <= stats["coverage_pct"] <= 100.0
        assert stats["overlap_ratio"] == 0.0  # word mode is disjoint, never overlapping
        for block in ("len_words", "len_chars"):
            for key in ("mean", "median", "min", "max"):
                assert key in stats[block]

    def test_slide_mode_reports_overlap(self, pp_project):
        # slide requires an even window >= MIN_SLIDE_SIZE (10); ChunkingConfig enforces this.
        m = _run(pp_project, mode="slide", size=10)
        assert m["metadata"]["capability"]["overlapping"] is True
        assert m["metadata"]["stats"]["overlap_ratio"] > 0.0


class TestChunkingTrackPlurality:
    def test_distinct_params_distinct_layer(self, pp_project):
        m5 = _run(pp_project, mode="word", size=5)
        m9 = _run(pp_project, mode="word", size=9)
        assert m5["name"] != m9["name"], "different sizes must produce different label-keyed layers"
        both = list((pp_project.path / "signals").glob("chunking_*.json"))
        assert len(both) == 2, "plural chunk layers must coexist without collision"

    def test_label_is_deterministic(self, pp_project):
        first = _run(pp_project, mode="word", size=5)["name"]
        second = _run(pp_project, mode="word", size=5)["name"]
        assert first == second
