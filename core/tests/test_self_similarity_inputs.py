"""Wave-0 P7 (C5) — the self_similarity input-discovery endpoint.

``GET /api/projects/{id}/self_similarity/inputs`` is the read-side of the dependency system: it
enumerates the layers bindable into a self_similarity run, chunk-rooted, with each chunk layer's
*coherent* repeat_mask/embedding layers nested, plus the method registry and an ``incompatible`` list
for layers that bind to no present chunk layer. Coherence is computed with the same predicate
(``bundles.coherence_reason``) that run-time binding uses, so discovery and binding cannot disagree.

These tests plant minimal layer manifests on disk (only the fields the endpoint reads) and hit the
route through ``TestClient``; no ingest or analysis run is needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from palimpsest.server import create_app

DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64


def _plant(signals: Path, name: str, capability: dict, *, label: str,
           stats: dict | None = None, rendering: dict | None = None) -> None:
    meta: dict = {"label": label, "capability": capability}
    if stats is not None:
        meta["stats"] = stats
    if rendering is not None:
        meta["rendering"] = rendering
    (signals / f"{name}.json").write_text(
        json.dumps({"metadata": meta, "segment_offsets": []}), encoding="utf-8"
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / "proj" / "signals").mkdir(parents=True)
    return ws


@pytest.fixture
def signals(workspace: Path) -> Path:
    return workspace / "proj" / "signals"


@pytest.fixture
def client(workspace: Path) -> TestClient:
    return TestClient(create_app(workspace))


def _get(client: TestClient) -> dict:
    resp = client.get("/api/projects/proj/self_similarity/inputs")
    assert resp.status_code == 200
    return resp.json()


def test_happy_path_groups_coherent_deps_under_chunk(signals, client):
    _plant(signals, "chunking_ck", {
        "kind": "chunk", "mode": "word", "size": 256, "analyzable_digest": DIGEST,
    }, label="ck", stats={"count": 10, "coverage_pct": 98.0})
    _plant(signals, "repeats_rp", {"kind": "repeat-set", "analyzable_digest": DIGEST}, label="rp")
    _plant(signals, "repeat_mask_ck_rp", {
        "kind": "repeat-mask", "chunk_layer_id": "ck", "repeat_layer_id": "rp",
        "chunk_analyzable_digest": DIGEST,
    }, label="ck_rp", stats={"masked_count": 2})
    _plant(signals, "embedding_em", {
        "kind": "embedding", "chunk_layer_id": "ck", "chunk_analyzable_digest": DIGEST,
        "provider": "mlx", "model": "qwen", "dim": 8,
    }, label="em", stats={"dim": 8})

    data = _get(client)
    assert data["consumer"] == "self_similarity"
    assert data["incompatible"] == []
    assert len(data["chunk_layers"]) == 1
    cl = data["chunk_layers"][0]
    assert cl["label"] == "ck"
    assert cl["size"] == 256
    assert cl["bundle_ready"] is True
    # richness: capability + stats surfaced inline (serves FR-14, no extra round-trip)
    assert cl["capability"]["mode"] == "word"
    assert cl["stats"]["coverage_pct"] == 98.0
    assert [m["label"] for m in cl["repeat_masks"]] == ["ck_rp"]
    assert cl["repeat_masks"][0]["stats"] == {"masked_count": 2}
    assert [e["label"] for e in cl["embeddings"]] == ["em"]


def test_methods_registry_with_embedding_flags(client):
    data = _get(client)
    methods = {m["name"]: m["requires_embedding"] for m in data["methods"]}
    assert methods == {
        "cosine": True, "jaccard": True, "word_overlap": False, "edit_distance": False,
    }


def test_bundle_ready_false_without_repeat_mask(signals, client):
    # A chunk layer with no coherent repeat_mask cannot form a bundle (mask is mandatory).
    _plant(signals, "chunking_ck", {
        "kind": "chunk", "mode": "word", "size": 256, "analyzable_digest": DIGEST,
    }, label="ck")
    data = _get(client)
    cl = data["chunk_layers"][0]
    assert cl["bundle_ready"] is False
    assert cl["repeat_masks"] == []


def test_multi_size_chunk_layers_are_distinct_rows(signals, client):
    for label, size in (("c256", 256), ("c512", 512)):
        _plant(signals, f"chunking_{label}", {
            "kind": "chunk", "mode": "slide", "size": size, "analyzable_digest": DIGEST,
        }, label=label)
        _plant(signals, f"repeat_mask_{label}_rp", {
            "kind": "repeat-mask", "chunk_layer_id": label, "repeat_layer_id": "rp",
            "chunk_analyzable_digest": DIGEST,
        }, label=f"{label}_rp")
    data = _get(client)
    by_size = {cl["size"]: cl for cl in data["chunk_layers"]}
    assert set(by_size) == {256, 512}
    assert all(cl["bundle_ready"] for cl in data["chunk_layers"])


def test_orphan_dependency_surfaced_in_incompatible(signals, client):
    # An embedding whose chunk_layer_id names a chunk that isn't present is reported, not dropped.
    _plant(signals, "embedding_ghost", {
        "kind": "embedding", "chunk_layer_id": "ghost", "chunk_analyzable_digest": DIGEST,
        "provider": "mlx", "model": "qwen", "dim": 8,
    }, label="ghost")
    data = _get(client)
    assert data["chunk_layers"] == []
    assert len(data["incompatible"]) == 1
    inc = data["incompatible"][0]
    assert inc["kind"] == "embedding"
    assert inc["label"] == "ghost"
    assert "not present" in inc["reason"]


def test_digest_mismatch_dep_is_incompatible_not_nested(signals, client):
    # repeat_mask points at the right chunk label but a different analyzable view → incompatible.
    _plant(signals, "chunking_ck", {
        "kind": "chunk", "mode": "word", "size": 256, "analyzable_digest": DIGEST,
    }, label="ck")
    _plant(signals, "repeat_mask_ck_rp", {
        "kind": "repeat-mask", "chunk_layer_id": "ck", "repeat_layer_id": "rp",
        "chunk_analyzable_digest": OTHER_DIGEST,
    }, label="ck_rp")
    data = _get(client)
    cl = data["chunk_layers"][0]
    assert cl["repeat_masks"] == []
    assert cl["bundle_ready"] is False
    assert len(data["incompatible"]) == 1
    assert "different analyzable digest" in data["incompatible"][0]["reason"]


def test_empty_project_is_200_not_error(client):
    data = _get(client)
    assert data["chunk_layers"] == []
    assert data["incompatible"] == []
    assert len(data["methods"]) == 4


def test_unknown_project_is_404(client):
    resp = client.get("/api/projects/nope/self_similarity/inputs")
    assert resp.status_code == 404
