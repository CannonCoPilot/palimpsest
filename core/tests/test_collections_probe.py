"""Collections tier — phase C6b (probe mode R(q, Corpus) over the shared embedding space).

Unlike the C1 congruence tests (which read manifests only), the probe actually *searches* each
member's vector store — so these fixtures build real ``cache/embeddings_{label}.db`` SqliteVec DBs
with known low-dimensional vectors alongside the contract-accurate manifests. That makes ranking,
attribution, and the congruence gate all deterministic without a live embedding service. Query-text →
vector embedding (the one live-service path) is exercised only at the boundary and is not needed here:
``probe_corpus`` takes a vector, and ``query_vector_from_ref`` reuses an embedded passage.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from palimpsest import collections as cs
from palimpsest import collections_probe as probe
from palimpsest.collections_ops import MetricCongruenceError
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

_FP = "fp-shared-space"


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_member(
    workspace: Path,
    pid: str,
    vectors: list[list[float]],
    texts: list[str],
    *,
    chunk: str = "c1",
    emb_label: str = "e1",
    dim: int = 4,
    fingerprint: str = _FP,
) -> str:
    """Fabricate a member with a chunk layer, an embedding manifest, and a real vector store whose ids
    match ``EmbeddingTrack``'s ``{pid}:{label}:{index}`` scheme."""
    pdir = workspace / pid
    _write(pdir / "metadata.json",
           {"id": pid, "title": pid, "source_format": "txt", "reference_sha256": f"sha-{pid}"})
    _write(pdir / "signals" / f"chunking_{chunk}.json",
           {"metadata": {"label": chunk, "capability": {"kind": "chunk", "analyzable_digest": f"dig-{pid}"},
                         "chunk_texts": texts}})
    _write(pdir / "signals" / f"embedding_{emb_label}.json",
           {"metadata": {"label": emb_label, "capability": {
               "kind": "embedding", "chunk_layer_id": chunk, "chunk_analyzable_digest": f"dig-{pid}",
               "provider": "mlx", "model": "qwen3-4b", "dim": dim, "model_fingerprint": fingerprint}}})

    db = pdir / "cache" / f"embeddings_{emb_label}.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteVecStore(db, dim=dim)
    try:
        ids = [f"{pid}:{emb_label}:{k}" for k in range(len(vectors))]
        meta = [{"chunk_index": k} for k in range(len(vectors))]
        store.add(ids, vectors, meta)
    finally:
        store.close()
    return pid


def _corpus(workspace: Path) -> str:
    """A 2-member congruent corpus. alpha=[e0,e1], beta=[e2, e0+e1]; query e0 → alpha:0 top, beta:1 next."""
    _make_member(workspace, "alpha", [[1, 0, 0, 0], [0, 1, 0, 0]], ["alpha chunk zero", "alpha chunk one"])
    _make_member(workspace, "beta", [[0, 0, 1, 0], [1, 1, 0, 0]], ["beta chunk zero", "beta chunk one"])
    return cs.create_collection(workspace, "Probe", "probe set", ["alpha", "beta"])["id"]


# ── Happy path: ranking, attribution, snippets ────────────────────────────────────────────────────

def test_probe_ranks_and_attributes_across_members(tmp_path: Path) -> None:
    cid = _corpus(tmp_path)
    res = probe.probe_corpus(tmp_path, cid, [1.0, 0.0, 0.0, 0.0], k=3)

    assert res["members_searched"] == ["alpha", "beta"]
    assert res["dim"] == 4
    assert res["congruence_key"] == f"embedding:cosine:{_FP}"
    top = res["results"]
    assert top[0]["project_id"] == "alpha" and top[0]["chunk_index"] == 0
    assert top[0]["similarity"] == pytest.approx(1.0)
    assert top[0]["text"] == "alpha chunk zero"  # snippet resolved from the chunk layer
    # beta:1 = [1,1,0,0] has cosine ~0.7071 to the query, ahead of the two orthogonal (0.0) chunks.
    assert top[1]["project_id"] == "beta" and top[1]["chunk_index"] == 1
    assert top[1]["similarity"] == pytest.approx(0.7071, abs=1e-3)
    assert res["n_candidates"] == 4  # every member chunk was a candidate, none silently dropped


def test_probe_k_bounds_results_but_not_candidates(tmp_path: Path) -> None:
    cid = _corpus(tmp_path)
    res = probe.probe_corpus(tmp_path, cid, [1.0, 0.0, 0.0, 0.0], k=1, per_member_k=2)
    assert len(res["results"]) == 1  # k caps returned rows
    assert res["n_candidates"] == 4  # but the full candidate count is still reported


def test_probe_snippet_chars_zero_skips_text(tmp_path: Path) -> None:
    cid = _corpus(tmp_path)
    res = probe.probe_corpus(tmp_path, cid, [1.0, 0.0, 0.0, 0.0], k=2, snippet_chars=0)
    assert all(r["text"] is None for r in res["results"])


# ── Service-free ref-mode query ───────────────────────────────────────────────────────────────────

def test_probe_ref_mode_finds_self_first(tmp_path: Path) -> None:
    cid = _corpus(tmp_path)
    qvec = probe.query_vector_from_ref(tmp_path, "alpha", 0)
    assert qvec == [1.0, 0.0, 0.0, 0.0]
    res = probe.probe_corpus(tmp_path, cid, qvec, k=1)
    assert res["results"][0]["project_id"] == "alpha" and res["results"][0]["chunk_index"] == 0


def test_probe_ref_out_of_range(tmp_path: Path) -> None:
    _corpus(tmp_path)
    with pytest.raises(ValueError, match="out of range"):
        probe.query_vector_from_ref(tmp_path, "alpha", 99)


# ── The congruence gate: fail-loud, never a silent partial/mixed-space probe ───────────────────────

def test_probe_fails_loud_on_member_missing_embedding(tmp_path: Path) -> None:
    _make_member(tmp_path, "alpha", [[1, 0, 0, 0]], ["a"])
    # gamma has a chunk layer but no embedding layer at all.
    gdir = tmp_path / "gamma"
    _write(gdir / "metadata.json", {"id": "gamma", "title": "g", "source_format": "txt", "reference_sha256": "s"})
    _write(gdir / "signals" / "chunking_c1.json",
           {"metadata": {"label": "c1", "capability": {"kind": "chunk", "analyzable_digest": "d"}}})
    cid = cs.create_collection(tmp_path, "Mixed", "", ["alpha", "gamma"])["id"]
    with pytest.raises(MetricCongruenceError, match="gamma"):
        probe.probe_corpus(tmp_path, cid, [1.0, 0.0, 0.0, 0.0])


def test_probe_fails_loud_on_incongruent_members(tmp_path: Path) -> None:
    _make_member(tmp_path, "alpha", [[1, 0, 0, 0]], ["a"], fingerprint="fp-A")
    _make_member(tmp_path, "beta", [[0, 1, 0, 0]], ["b"], fingerprint="fp-B")  # different space
    cid = cs.create_collection(tmp_path, "Split", "", ["alpha", "beta"])["id"]
    with pytest.raises(MetricCongruenceError, match="not congruent"):
        probe.probe_corpus(tmp_path, cid, [1.0, 0.0, 0.0, 0.0])


def test_probe_rejects_query_from_a_different_space(tmp_path: Path) -> None:
    cid = _corpus(tmp_path)
    with pytest.raises(MetricCongruenceError, match="different space"):
        probe.probe_corpus(tmp_path, cid, [1.0, 0.0, 0.0, 0.0], query_fingerprint="fp-wrong")


def test_probe_rejects_wrong_dimension_query(tmp_path: Path) -> None:
    cid = _corpus(tmp_path)
    with pytest.raises(MetricCongruenceError, match="dimension"):
        probe.probe_corpus(tmp_path, cid, [1.0, 0.0, 0.0])  # dim 3 vs corpus dim 4


def test_probe_rejects_token_metric(tmp_path: Path) -> None:
    cid = _corpus(tmp_path)
    with pytest.raises(ValueError, match="token metric"):
        probe.probe_corpus(tmp_path, cid, [1.0, 0.0, 0.0, 0.0], metric="word_overlap")


def test_probe_unknown_collection(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        probe.probe_corpus(tmp_path, "no-such-collection", [1.0, 0.0, 0.0, 0.0])


# ── CLI parity (service-free ref mode) ────────────────────────────────────────────────────────────

def test_probe_cli_ref_mode(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    cid = _corpus(tmp_path)
    result = CliRunner().invoke(
        main, ["collections", "probe", str(tmp_path), cid, "--ref-project", "alpha", "--ref-chunk", "0", "-k", "2"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["results"][0]["project_id"] == "alpha"
    assert payload["congruence_key"] == f"embedding:cosine:{_FP}"


def test_probe_cli_requires_one_query_source(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    cid = _corpus(tmp_path)
    result = CliRunner().invoke(main, ["collections", "probe", str(tmp_path), cid])  # neither source
    assert result.exit_code == 1
    assert "exactly one query source" in result.output
