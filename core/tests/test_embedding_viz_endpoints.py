"""P3 embedding-visualization endpoint tests (FR-3/6/13/14, NFR-4).

Builds a real chunk + embedding layer with a deterministic fake embedder (no embedding service), then
exercises the six on-read endpoints through the FastAPI app: the binary fetch contract
(little-endian Float32Array), JSON histogram/cluster shapes, the pre-run cost estimate, the filtered
embedding, and the loud failures (bad method/kind/encoding/label).
"""

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from palimpsest.project import ingest_file
from palimpsest.server import create_app
from palimpsest.tracks.chunking_track import ChunkingTrack
from palimpsest.tracks.embedding_track import EmbeddingTrack

_DIM = 8


def _fake_embed(texts, config):
    """Deterministic stand-in for embed_texts: each text → a fixed _DIM-vector seeded by its bytes."""
    rows = []
    for t in texts:
        seed = int.from_bytes(t.encode("utf-8")[:4].ljust(4, b"\0"), "little")
        rows.append(np.random.default_rng(seed).standard_normal(_DIM).astype(np.float32))
    return np.array(rows, dtype=np.float32)


def _f32(content: bytes) -> np.ndarray:
    return np.frombuffer(content, dtype="<f4")


def _build_embedding(workspace: Path, src: Path, monkeypatch, embed_filter: str | None = None):
    monkeypatch.setattr("palimpsest.tracks.embedding_track.embed_texts", _fake_embed)
    project = ingest_file(src, workspace, title="P3 Viz Test")
    ct = ChunkingTrack()
    ct.set_params({"chunk_mode": "word", "chunk_size": 7})
    chunk_label = json.loads(ct.extract(project).read_text())["metadata"]["label"]
    et = EmbeddingTrack()
    params = {
        "chunk_label": chunk_label, "embed_provider": "mlx",
        "embed_endpoint": "http://localhost:8000", "embed_model": "test-model",
    }
    if embed_filter is not None:
        params["embed_filter"] = embed_filter
    et.set_params(params)
    manifest = json.loads(et.extract(project).read_text())
    return project, chunk_label, manifest


@pytest.fixture
def viz(pp_ch1_txt: Path, tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project, chunk_label, manifest = _build_embedding(workspace, pp_ch1_txt, monkeypatch)
    return {
        "client": TestClient(create_app(workspace)),
        "pid": project.metadata.id,
        "chunk_label": chunk_label,
        "label": manifest["metadata"]["label"],
        "n": manifest["metadata"]["stats"]["count"],
    }


def _url(viz, suffix: str) -> str:
    return f"/api/projects/{viz['pid']}/embedding/{viz['label']}/{suffix}"


class TestProjection:
    def test_returns_n_by_2_float32(self, viz):
        r = viz["client"].get(_url(viz, "projection"))
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/octet-stream"
        arr = _f32(r.content)
        assert arr.size == viz["n"] * 2
        assert arr.reshape(-1, 2).shape == (viz["n"], 2)

    def test_deterministic(self, viz):
        a = viz["client"].get(_url(viz, "projection")).content
        b = viz["client"].get(_url(viz, "projection")).content
        assert a == b

    def test_umap_rejected_loudly(self, viz):
        r = viz["client"].get(_url(viz, "projection"), params={"method": "umap"})
        assert r.status_code == 400
        assert "OQ#4" in r.json()["detail"]


class TestDistances:
    def test_nn_histogram(self, viz):
        r = viz["client"].get(_url(viz, "distances"), params={"kind": "nn"})
        assert r.status_code == 200
        body = r.json()
        assert body["kind"] == "nn"
        assert body["count"] == viz["n"]
        assert sum(body["counts"]) == viz["n"]
        assert body["edges"][0] == 0.0 and body["edges"][-1] == 2.0

    def test_pairwise_histogram_reports_pairs(self, viz):
        r = viz["client"].get(_url(viz, "distances"), params={"kind": "pairwise"})
        body = r.json()
        total = viz["n"] * (viz["n"] - 1) // 2
        assert body["total_pairs"] == total
        assert body["sampled_pairs"] == total  # small fixture → no sampling
        assert sum(body["counts"]) == total

    def test_bad_kind_400(self, viz):
        assert viz["client"].get(_url(viz, "distances"), params={"kind": "cosine"}).status_code == 400


class TestHeatmap:
    def test_chunk_order_matrix(self, viz):
        r = viz["client"].get(_url(viz, "heatmap"))
        assert r.status_code == 200
        n = viz["n"]
        assert int(r.headers["X-Matrix-N"]) == n
        assert r.headers["X-Matrix-Reduced"] == "0"
        m = _f32(r.content).reshape(n, n)
        assert np.allclose(np.diag(m), 1.0, atol=1e-4)

    def test_cluster_order_exposes_permutation(self, viz):
        r = viz["client"].get(_url(viz, "heatmap"), params={"order": "cluster", "k": 3})
        assert r.status_code == 200
        order = r.headers["X-Matrix-Order"].split(",")
        assert len(order) == viz["n"]
        assert sorted(map(int, order)) == list(range(viz["n"]))  # a true permutation

    def test_bad_order_400(self, viz):
        assert viz["client"].get(_url(viz, "heatmap"), params={"order": "x"}).status_code == 400


class TestClusters:
    def test_labels_and_sizes(self, viz):
        r = viz["client"].get(_url(viz, "clusters"), params={"k": 4, "seed": 0})
        assert r.status_code == 200
        body = r.json()
        assert len(body["labels"]) == viz["n"]
        assert sum(body["sizes"]) == viz["n"]
        assert body["requested_k"] == 4
        assert body["effective_k"] == len(body["sizes"])

    def test_deterministic_seed(self, viz):
        a = viz["client"].get(_url(viz, "clusters"), params={"seed": 0}).json()["labels"]
        b = viz["client"].get(_url(viz, "clusters"), params={"seed": 0}).json()["labels"]
        assert a == b


class TestLane:
    @pytest.mark.parametrize("encoding", ["pc1", "cluster", "nn-density"])
    def test_one_scalar_per_chunk(self, viz, encoding):
        r = viz["client"].get(_url(viz, "lane"), params={"encoding": encoding})
        assert r.status_code == 200
        assert _f32(r.content).size == viz["n"]

    def test_pc1_lane_matches_projection(self, viz):
        lane = _f32(viz["client"].get(_url(viz, "lane"), params={"encoding": "pc1"}).content)
        proj = _f32(viz["client"].get(_url(viz, "projection")).content).reshape(-1, 2)
        assert np.allclose(lane, proj[:, 0])

    def test_bad_encoding_400(self, viz):
        assert viz["client"].get(_url(viz, "lane"), params={"encoding": "tsne"}).status_code == 400


class TestEstimate:
    def test_precedes_run_from_chunk_layer(self, viz):
        r = viz["client"].get(
            f"/api/projects/{viz['pid']}/embedding/estimate",
            params={"chunk_label": viz["chunk_label"]},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["chunk_count"] == viz["n"]
        assert body["vector_count"] == viz["n"]
        assert body["estimated_seconds"] >= 0
        assert "note" in body  # honest framing: rough, provider-dependent

    def test_missing_chunk_layer_404(self, viz):
        r = viz["client"].get(
            f"/api/projects/{viz['pid']}/embedding/estimate",
            params={"chunk_label": "deadbeefdeadbeef"},
        )
        assert r.status_code == 404


class TestLabelValidation:
    def test_non_hex_label_400(self, viz):
        assert viz["client"].get(
            f"/api/projects/{viz['pid']}/embedding/not-a-hex-label/projection"
        ).status_code == 400

    def test_unknown_label_404(self, viz):
        assert viz["client"].get(
            f"/api/projects/{viz['pid']}/embedding/deadbeefdeadbeef/projection"
        ).status_code == 404


class TestFilteredEmbedding:
    def test_filter_embeds_subset_with_provenance(self, pp_ch1_txt, tmp_path, monkeypatch):
        ws_full = tmp_path / "full"
        ws_full.mkdir()
        _, _, full = _build_embedding(ws_full, pp_ch1_txt, monkeypatch)

        ws_filt = tmp_path / "filt"
        ws_filt.mkdir()
        _, _, filtered = _build_embedding(ws_filt, pp_ch1_txt, monkeypatch, embed_filter="the")

        assert filtered["metadata"]["stats"]["count"] < full["metadata"]["stats"]["count"]
        assert filtered["metadata"]["label"] != full["metadata"]["label"]  # distinct, content-addressed
        cap = filtered["metadata"]["capability"]
        assert cap["filter"] == "the"
        assert cap["source_chunk_count"] == full["metadata"]["stats"]["count"]

    def test_filter_matching_nothing_fails_loud(self, pp_ch1_txt, tmp_path, monkeypatch):
        ws = tmp_path / "none"
        ws.mkdir()
        with pytest.raises(ValueError, match="matched no chunks"):
            _build_embedding(ws, pp_ch1_txt, monkeypatch, embed_filter="zzzznonexistentzzz")
