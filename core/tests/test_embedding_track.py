"""Tests for EmbeddingTrack — the embedding layer-track (Wave-0 P2, FR-3/5/6/13/14).

``embed_texts`` is monkeypatched to a deterministic fake so the track's contract (read a chunk layer,
persist vectors + manifest, cache-reuse, capability/rendering/stats backbone) is tested without a live
embedding service.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from palimpsest.project import ingest_file
from palimpsest.tracks.base import TrackExtractor
from palimpsest.tracks.chunking_track import ChunkingTrack
from palimpsest.tracks.embedding_track import EmbeddingTrack
from palimpsest.tracks.registry import TrackRegistry
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

_DIM = 8


@pytest.fixture
def pp_project(pp_ch1_txt: Path, tmp_path: Path):
    return ingest_file(pp_ch1_txt, tmp_path, title="embedding-track-test")


@pytest.fixture
def chunk_label(pp_project) -> str:
    track = ChunkingTrack()
    track.set_params({"chunk_mode": "word", "chunk_size": 7})
    path = track.extract(pp_project)
    return json.loads(path.read_text())["metadata"]["label"]


def _fake_embed_factory(counter: list[int]):
    """A deterministic stand-in for embed_texts: each text → a fixed _DIM-vector from its hash.
    Records call count so cache-reuse can be asserted."""
    def fake_embed(texts, config):
        counter.append(len(texts))
        rows = []
        for t in texts:
            seed = int.from_bytes(t.encode("utf-8")[:4].ljust(4, b"\0"), "little")
            rng = np.random.default_rng(seed)
            rows.append(rng.standard_normal(_DIM).astype(np.float32))
        return np.array(rows, dtype=np.float32)
    return fake_embed


def _run_embedding(project, chunk_label, monkeypatch, counter=None):
    counter = counter if counter is not None else []
    monkeypatch.setattr(
        "palimpsest.tracks.embedding_track.embed_texts", _fake_embed_factory(counter)
    )
    track = EmbeddingTrack()
    track.set_params({
        "chunk_label": chunk_label, "embed_provider": "mlx",
        "embed_endpoint": "http://localhost:8000", "embed_model": "test-model",
        "embed_batch_size": 4,
    })
    path = track.extract(project)
    return json.loads(path.read_text()), path, counter


class TestEmbeddingTrackProtocol:
    def test_is_track_extractor(self):
        assert isinstance(EmbeddingTrack(), TrackExtractor)

    def test_required_attributes(self):
        t = EmbeddingTrack()
        assert t.name == "embedding"
        assert t.output_type == "signal"
        assert t.depends_on == ["chunking"]  # signal-consumer: runs on full project, not remapped
        assert t.lfo_types == ["signal.embedding"]

    def test_auto_discovered(self):
        registry = TrackRegistry.discover()
        assert "embedding" in registry.names()
        assert registry.get("embedding") is EmbeddingTrack


class TestEmbeddingTrackExtract:
    def test_writes_label_keyed_layer(self, pp_project, chunk_label, monkeypatch):
        m, path, _ = _run_embedding(pp_project, chunk_label, monkeypatch)
        assert path.name.startswith("embedding_") and path.suffix == ".json"
        assert m["type"] == "embedding-layer"

    def test_persists_vectors_to_vectorstore(self, pp_project, chunk_label, monkeypatch):
        m, _, _ = _run_embedding(pp_project, chunk_label, monkeypatch)
        db = pp_project.path / m["metadata"]["vectorstore"]
        assert db.exists()
        store = SqliteVecStore.open_existing(db)
        try:
            assert store.count() == m["metadata"]["stats"]["count"]
        finally:
            store.close()

    def test_capability_descriptor(self, pp_project, chunk_label, monkeypatch):
        m, _, _ = _run_embedding(pp_project, chunk_label, monkeypatch)
        cap = m["metadata"]["capability"]
        assert cap["kind"] == "embedding"
        assert cap["chunk_layer_id"] == chunk_label
        assert cap["provider"] == "mlx"
        assert cap["dim"] == _DIM
        assert isinstance(cap["model_fingerprint"], str)

    def test_rendering_and_stats_backbone(self, pp_project, chunk_label, monkeypatch):
        m, _, _ = _run_embedding(pp_project, chunk_label, monkeypatch)
        rendering = m["metadata"]["rendering"]
        assert rendering["track_view"] == "embedding-lane"
        assert rendering["encoding"] in ("cluster", "pc1", "nn-density")
        stats = m["metadata"]["stats"]
        assert stats["count"] > 0
        assert stats["dim"] == _DIM
        assert "mean_pairwise_distance" in stats

    def test_offsets_copied_from_chunk_layer(self, pp_project, chunk_label, monkeypatch):
        chunk_manifest = json.loads(
            (pp_project.path / "signals" / f"chunking_{chunk_label}.json").read_text()
        )
        m, _, _ = _run_embedding(pp_project, chunk_label, monkeypatch)
        assert m["segment_offsets"] == chunk_manifest["segment_offsets"]

    def test_cache_reuse_skips_re_embedding(self, pp_project, chunk_label, monkeypatch):
        counter: list[int] = []
        _run_embedding(pp_project, chunk_label, monkeypatch, counter)
        calls_after_first = len(counter)
        assert calls_after_first > 0
        _run_embedding(pp_project, chunk_label, monkeypatch, counter)
        assert len(counter) == calls_after_first, "second run must reuse the cached vectors"

    def test_missing_chunk_layer_raises(self, pp_project, monkeypatch):
        monkeypatch.setattr(
            "palimpsest.tracks.embedding_track.embed_texts", _fake_embed_factory([])
        )
        track = EmbeddingTrack()
        track.set_params({
            "chunk_label": "deadbeefdeadbeef", "embed_provider": "mlx",
            "embed_endpoint": "http://localhost:8000", "embed_model": "test-model",
        })
        with pytest.raises(ValueError, match="chunk layer"):
            track.extract(pp_project)
