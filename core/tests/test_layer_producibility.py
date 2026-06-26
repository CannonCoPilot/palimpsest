"""FR-4 producibility + status for label-keyed layer tracks (Wave-0 P2).

Layer tracks (chunking/embedding) must be runnable through the normal run flow with their params, write
per-label provenance (so plural runs don't overwrite each other), and surface their plural layers in
``/analysis/status``. The async background job cannot advance under ``TestClient`` (the anyio portal
only runs the loop during a request), so producibility is tested via (1) the *synchronous*
``validate_params`` echo the POST returns in-request, and (2) the pure status/provenance helpers driven
by layers produced directly on disk.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from palimpsest.project import Project, ingest_file
from palimpsest.server import _layer_status_entries, _provenance_name, create_app
from palimpsest.tracks.chunking_track import ChunkingTrack


@pytest.fixture
def workspace(pp_ch1_txt: Path, tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    ingest_file(pp_ch1_txt, ws, title="FR4 Layer Test")
    return ws


@pytest.fixture
def project_dir(workspace: Path) -> Path:
    return next(p for p in workspace.iterdir() if p.is_dir())


@pytest.fixture
def client(workspace: Path) -> TestClient:
    return TestClient(create_app(workspace))


def _make_chunk_layer(project_dir: Path, **params) -> str:
    """Produce a chunk layer directly (synchronous, no embedding service) and return its label."""
    track = ChunkingTrack()
    track.set_params(params)
    manifest_path = track.extract(Project.load(project_dir))
    return json.loads(manifest_path.read_text())["metadata"]["label"]


class TestProvenanceName:
    def test_layer_keyed_track_keyed_by_manifest_stem(self):
        # A layer track returns the produced manifest Path; provenance is keyed by its stem so two
        # different-param runs do not overwrite one another's record.
        name = _provenance_name("chunking", ChunkingTrack(), Path("/x/signals/chunking_abc123.json"))
        assert name == "chunking_abc123"

    def test_non_layer_track_keyed_by_track_name(self):
        # A non-layer extractor returns a list (annotations); provenance stays the bare track name.
        assert _provenance_name("entities", object(), ["ann"]) == "entities"

    def test_layer_track_without_path_falls_back_to_track_name(self):
        # Defensive: a layer track that somehow didn't return a Path keeps the bare name (no crash).
        assert _provenance_name("chunking", ChunkingTrack(), None) == "chunking"


class TestLayerStatusEntries:
    def test_empty_when_no_layers(self, project_dir):
        assert _layer_status_entries(project_dir, "chunking") == []

    def test_enumerates_plural_layers_with_descriptors(self, project_dir):
        label5 = _make_chunk_layer(project_dir, chunk_mode="word", chunk_size=5)
        label9 = _make_chunk_layer(project_dir, chunk_mode="word", chunk_size=9)
        entries = _layer_status_entries(project_dir, "chunking")
        assert len(entries) == 2
        assert {e["label"] for e in entries} == {label5, label9}
        for e in entries:
            assert e["status"] == "computed"
            assert e["capability"]["kind"] == "chunk"
            assert "count" in e["stats"]
            assert e["rendering"]["track_view"] == "chunk-band"

    def test_skips_unparseable_manifest(self, project_dir):
        _make_chunk_layer(project_dir, chunk_mode="word", chunk_size=5)
        (project_dir / "signals" / "chunking_deadbeefdeadbeef.json").write_text("{not json")
        entries = _layer_status_entries(project_dir, "chunking")
        # the good layer is enumerated; the corrupt file is skipped, not faked
        assert len(entries) == 1
        assert entries[0]["capability"]["kind"] == "chunk"


class TestStatusEndpointLayers:
    def _pid(self, client) -> str:
        return client.get("/api/projects").json()[0]["id"]

    def test_chunking_row_carries_plural_layers(self, client, project_dir):
        _make_chunk_layer(project_dir, chunk_mode="word", chunk_size=5)
        _make_chunk_layer(project_dir, chunk_mode="word", chunk_size=9)
        rows = client.get(f"/api/projects/{self._pid(client)}/analysis/status").json()
        chunking = next(r for r in rows if r["name"] == "chunking")
        assert chunking["status"] == "computed"
        assert len(chunking["layers"]) == 2
        for layer in chunking["layers"]:
            assert layer["capability"]["kind"] == "chunk"
            assert "stats" in layer

    def test_chunking_row_pending_with_zero_layers(self, client):
        rows = client.get(f"/api/projects/{self._pid(client)}/analysis/status").json()
        chunking = next(r for r in rows if r["name"] == "chunking")
        assert chunking["status"] == "pending"
        assert chunking["layers"] == []


class TestRunFlowProducibility:
    """The POST validates params synchronously (returns ``resolved_params`` / 400 in-request) before the
    async job — so param producibility is testable even though the job itself can't advance here."""

    def _pid(self, client) -> str:
        return client.get("/api/projects").json()[0]["id"]

    def test_chunking_runnable_with_chunk_vocab(self, client):
        r = client.post(f"/api/projects/{self._pid(client)}/analyze/chunking?chunk_mode=word&chunk_size=7")
        assert r.status_code == 200
        resolved = r.json()["resolved_params"]
        assert resolved["chunk_mode"] == "word"
        assert resolved["chunk_size"] == 7

    def test_embedding_runnable_with_chunk_label_and_embed_vocab(self, client):
        r = client.post(
            f"/api/projects/{self._pid(client)}/analyze/embedding"
            "?chunk_label=abc123&embed_provider=mlx"
            "&embed_endpoint=http://localhost:8000&embed_model=test-model"
        )
        assert r.status_code == 200
        resolved = r.json()["resolved_params"]
        assert resolved["chunk_label"] == "abc123"
        assert resolved["embed_provider"] == "mlx"

    def test_embedding_requires_chunk_label(self, client):
        r = client.post(
            f"/api/projects/{self._pid(client)}/analyze/embedding"
            "?embed_provider=mlx&embed_endpoint=http://localhost:8000&embed_model=test-model"
        )
        assert r.status_code == 400
        assert "chunk_label" in r.json()["detail"]
