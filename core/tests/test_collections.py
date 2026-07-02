"""Collections tier — phase C1 (object model, membership lattice, metric congruence, cross-project
operand resolution, non-destructive versioning).

The substrate is deliberately pure: object-model navigation reads loose metadata fields, congruence is
a function over capability dicts, and operand resolution reuses the Wave-0 explicit-bundle binding. So
these tests fabricate *contract-accurate* layer files (the exact JSON ``resolve_explicit_bundle`` and
``_enumerate_layers`` read) rather than running real chunking/embedding — the binding contract is what
C1 must honour, and it is exercised faithfully here.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from palimpsest import collections as cs
from palimpsest import collections_ops as ops
from palimpsest.tracks.requirements import LayerResolutionError


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_project(
    workspace: Path,
    pid: str,
    *,
    work_id: str | None = None,
    parent: str | None = None,
    chunk: str = "c1",
    mask: str = "m1",
    digest: str | None = None,
    embedding: str | None = None,
    fingerprint: str = "fp-common",
) -> str:
    """Fabricate a project with bindable chunk + repeat_mask (+ optional embedding) layers, matching
    the on-disk contract the binders read. Returns ``pid``."""
    digest = digest or f"dig-{pid}"
    pdir = workspace / pid
    meta: dict = {"id": pid, "title": pid, "source_format": "txt", "reference_sha256": f"sha-{pid}"}
    if work_id:
        meta["work_id"] = work_id
    if parent:
        meta["parent_project_id"] = parent
    _write(pdir / "metadata.json", meta)

    _write(pdir / "signals" / f"chunking_{chunk}.json",
           {"metadata": {"label": chunk, "capability": {"kind": "chunk", "analyzable_digest": digest, "size": 200}}})
    _write(pdir / "signals" / "repeats_r1.json",
           {"metadata": {"label": "r1", "capability": {"kind": "repeat-set"}, "phrases": ["the lord"]}})
    _write(pdir / "signals" / f"repeat_mask_{mask}.json",
           {"metadata": {"label": mask, "capability": {
               "kind": "repeat-mask", "chunk_layer_id": chunk,
               "chunk_analyzable_digest": digest, "repeat_layer_id": "r1"}}})
    if embedding:
        _write(pdir / "signals" / f"embedding_{embedding}.json",
               {"metadata": {"label": embedding, "capability": {
                   "kind": "embedding", "chunk_layer_id": chunk, "chunk_analyzable_digest": digest,
                   "provider": "mlx", "model": "qwen3-4b", "dim": 2560,
                   "model_fingerprint": fingerprint}}})
    return pid


# ── Collection CRUD (previously untested) ─────────────────────────────────────────────────────────

def test_collection_crud_roundtrip(tmp_path: Path) -> None:
    col = cs.create_collection(tmp_path, "Gospels", "synoptic set", ["matthew", "mark"])
    assert col["id"] == "gospels" and col["kind"] == "manual"
    assert cs.get_collection(tmp_path, "gospels")["project_ids"] == ["matthew", "mark"]

    cs.add_member(tmp_path, "gospels", "luke")
    cs.add_member(tmp_path, "gospels", "luke")  # idempotent
    assert cs.get_collection(tmp_path, "gospels")["project_ids"] == ["matthew", "mark", "luke"]

    cs.remove_member(tmp_path, "gospels", "mark")
    assert cs.collections_for_project(tmp_path, "luke") == ["gospels"]
    assert cs.collections_for_project(tmp_path, "mark") == []

    cs.update_collection(tmp_path, "gospels", description="three gospels")
    assert cs.get_collection(tmp_path, "gospels")["description"] == "three gospels"

    assert cs.delete_collection(tmp_path, "gospels") is True
    assert cs.get_collection(tmp_path, "gospels") is None
    assert cs.delete_collection(tmp_path, "gospels") is False


def test_link_derived_autocreates_subtext_collection(tmp_path: Path) -> None:
    cid = cs.link_derived(tmp_path, "octapla", "The Octapla", "octapla-col1", None)
    assert cid == "octapla--subtexts"
    col = cs.get_collection(tmp_path, cid)
    assert col["kind"] == "derived" and col["project_ids"] == ["octapla", "octapla-col1"]
    # second child joins the same auto collection
    cs.link_derived(tmp_path, "octapla", "The Octapla", "octapla-col2", None)
    assert cs.get_collection(tmp_path, cid)["project_ids"] == ["octapla", "octapla-col1", "octapla-col2"]


# ── Collection-local roles (FR-25) ────────────────────────────────────────────────────────────────

def test_member_roles(tmp_path: Path) -> None:
    cs.create_collection(tmp_path, "Bibles", "", ["kjv", "drb"])
    col = cs.get_collection(tmp_path, "bibles")
    assert cs.member_role(col, "kjv") == "member"  # default co-equal

    cs.set_member_role(tmp_path, "bibles", "kjv", "root")
    assert cs.member_role(cs.get_collection(tmp_path, "bibles"), "kjv") == "root"
    # role is collection-local, not stored on the project
    assert cs.member_role(cs.get_collection(tmp_path, "bibles"), "drb") == "member"

    cs.set_member_role(tmp_path, "bibles", "kjv", "member")  # demote → roles map pruned clean
    assert "roles" not in cs.get_collection(tmp_path, "bibles")

    with pytest.raises(ValueError):
        cs.set_member_role(tmp_path, "bibles", "kjv", "backbone")  # invalid role
    with pytest.raises(ValueError):
        cs.set_member_role(tmp_path, "bibles", "stranger", "root")  # not a member
    assert cs.set_member_role(tmp_path, "ghost", "kjv", "root") is None  # unknown collection


# ── Object model + membership lattice (FR-23, FR-24, FR-43) ───────────────────────────────────────

def test_work_tag_and_subtext_edge(tmp_path: Path) -> None:
    _make_project(tmp_path, "kjv", work_id="bible")
    _make_project(tmp_path, "drb", work_id="bible")
    _make_project(tmp_path, "iliad")
    _make_project(tmp_path, "drb-appendix", parent="drb")

    assert ops.project_work_id(tmp_path, "kjv") == "bible"
    assert ops.project_work_id(tmp_path, "iliad") is None
    ops.set_project_work_id(tmp_path, "iliad", "homer")
    assert ops.project_work_id(tmp_path, "iliad") == "homer"
    ops.set_project_work_id(tmp_path, "iliad", None)
    assert ops.project_work_id(tmp_path, "iliad") is None

    assert sorted(ops.edition_siblings(tmp_path, "kjv")) == ["drb"]
    assert ops.edition_siblings(tmp_path, "iliad") == []  # no work_id → no siblings
    assert ops.subtext_children(tmp_path, "drb") == ["drb-appendix"]
    assert ops.project_parent_id(tmp_path, "drb-appendix") == "drb"


def test_project_lattice(tmp_path: Path) -> None:
    _make_project(tmp_path, "drb", work_id="bible")
    _make_project(tmp_path, "kjv", work_id="bible")
    _make_project(tmp_path, "drb-appendix", parent="drb")
    cs.create_collection(tmp_path, "Scripture", "", ["drb", "kjv"])

    lat = ops.project_lattice(tmp_path, "drb")
    assert lat["work_id"] == "bible"
    assert lat["children"] == ["drb-appendix"]
    assert lat["siblings"] == ["kjv"]
    assert lat["collections"] == ["scripture"]
    assert lat["parent"] is None


# ── Metric-congruence contract (FR-27, FR-39) ─────────────────────────────────────────────────────

def test_congruence_key_token_vs_embedding() -> None:
    # token metrics read raw strings → congruent across any two chunked texts, no capability needed
    assert ops.congruence_key("word_overlap") == "tokens:word_overlap"
    assert ops.congruence_key("edit_distance") == "tokens:edit_distance"
    # embedding metrics fold in the model fingerprint
    cap = {"model_fingerprint": "abc123", "provider": "mlx", "model": "qwen3", "dim": 2560}
    assert ops.congruence_key("cosine", embedding_capability=cap) == "embedding:cosine:abc123"
    with pytest.raises(ops.MetricCongruenceError):
        ops.congruence_key("cosine")  # embedding metric with no capability → fail loud


def test_operands_congruent() -> None:
    a = {"model_fingerprint": "fp1"}
    b_same = {"model_fingerprint": "fp1"}
    b_diff = {"model_fingerprint": "fp2"}
    ok, reason = ops.operands_congruent("cosine", a, b_same)
    assert ok and reason is None
    ok, reason = ops.operands_congruent("cosine", a, b_diff)
    assert not ok and "Reconcile" in reason
    # token metric: congruent regardless of (ignored) capabilities
    assert ops.operands_congruent("word_overlap", None, None)[0] is True


def test_congruence_report(tmp_path: Path) -> None:
    _make_project(tmp_path, "a", embedding="e1", fingerprint="fp1")
    _make_project(tmp_path, "b", embedding="e1", fingerprint="fp1")
    _make_project(tmp_path, "c", embedding="e1", fingerprint="fp2")  # different space
    _make_project(tmp_path, "d")  # no embedding layer at all
    cs.create_collection(tmp_path, "Corpus", "", ["a", "b", "c", "d"])

    rep = ops.congruence_report(tmp_path, "corpus", "cosine")
    assert rep["needs_embedding"] is True
    assert rep["keys"]["a"] == rep["keys"]["b"]  # a,b share a space
    assert rep["keys"]["a"] != rep["keys"]["c"]
    assert rep["keys"]["d"] is None and "d" in rep["missing"]
    assert rep["all_congruent"] is False
    assert sorted(rep["groups"][rep["keys"]["a"]]) == ["a", "b"]

    # token metric: everyone congruent, nobody missing
    rep2 = ops.congruence_report(tmp_path, "corpus", "word_overlap")
    assert rep2["all_congruent"] is True and rep2["missing"] == []


# ── Cross-project operand resolution (FR-26) ──────────────────────────────────────────────────────

def test_resolve_operand_success_and_failloud(tmp_path: Path) -> None:
    _make_project(tmp_path, "matthew")
    op = ops.resolve_operand(tmp_path, "matthew", "c1", "m1")
    assert op.chunk.label == "c1" and op.repeat_mask.label == "m1"
    assert op.embedding is None and op.repeat_phrases == ["the lord"]

    with pytest.raises(LayerResolutionError):
        ops.resolve_operand(tmp_path, "matthew", "c1", "nonexistent-mask")
    with pytest.raises(FileNotFoundError):
        ops.resolve_operand(tmp_path, "ghost", "c1", "m1")


def test_resolve_comparison_cross_text_is_not_self(tmp_path: Path) -> None:
    _make_project(tmp_path, "matthew")
    _make_project(tmp_path, "mark")
    spec = ops.resolve_comparison(
        tmp_path, a_id="matthew", b_id="mark",
        chunk_label="c1", repeat_mask_label="m1", methods=["word_overlap"],
    )
    assert spec.is_self is False  # the genuine two-operand seam
    assert spec.methods == ("word_overlap",)
    assert spec.operand_a.chunk.label == "c1"


def test_resolve_comparison_embedding_congruence_gate(tmp_path: Path) -> None:
    _make_project(tmp_path, "a", embedding="e1", fingerprint="fp1")
    _make_project(tmp_path, "b", embedding="e1", fingerprint="fp1")
    _make_project(tmp_path, "c", embedding="e1", fingerprint="fp2")

    spec = ops.resolve_comparison(
        tmp_path, a_id="a", b_id="b", chunk_label="c1", repeat_mask_label="m1",
        methods=["cosine"], embedding_label="e1",
    )
    assert spec.operand_a.embedding is not None and spec.is_self is False

    with pytest.raises(ops.MetricCongruenceError):
        ops.resolve_comparison(
            tmp_path, a_id="a", b_id="c", chunk_label="c1", repeat_mask_label="m1",
            methods=["cosine"], embedding_label="e1",
        )
    with pytest.raises(ValueError):
        ops.resolve_comparison(
            tmp_path, a_id="a", b_id="b", chunk_label="c1", repeat_mask_label="m1",
            methods=["nonsense_metric"],
        )


# ── Operand identity + non-destructive versioning (FR-28, FR-41) ──────────────────────────────────

def test_operand_and_comparison_identity(tmp_path: Path) -> None:
    _make_project(tmp_path, "a", digest="dig-A")
    _make_project(tmp_path, "b", digest="dig-B")
    op_a = ops.resolve_operand(tmp_path, "a", "c1", "m1")
    op_b = ops.resolve_operand(tmp_path, "b", "c1", "m1")

    ida = ops.operand_identity(op_a)
    assert len(ida) == 32 and ida != ops.operand_identity(op_b)  # digest distinguishes operands

    spec = ops.resolve_comparison(
        tmp_path, a_id="a", b_id="b", chunk_label="c1", repeat_mask_label="m1",
        methods=["word_overlap"],
    )
    cid = ops.comparison_identity(spec)
    assert len(cid) == 32
    # identity is a pure function of the operands + methods
    spec2 = ops.resolve_comparison(
        tmp_path, a_id="a", b_id="b", chunk_label="c1", repeat_mask_label="m1",
        methods=["word_overlap"],
    )
    assert ops.comparison_identity(spec2) == cid


def test_non_destructive_versioning_and_staleness(tmp_path: Path) -> None:
    vpath = tmp_path / ".comparisons" / "a_vs_b" / "versions.json"
    assert ops.load_run_versions(vpath) == []

    v1 = ops.append_run_version(vpath, "ident-1", {"methods": ["cosine"]})
    v2 = ops.append_run_version(vpath, "ident-2", {"methods": ["cosine"], "rerun": True})
    assert v1["version_id"] == "v1" and v2["version_id"] == "v2"
    assert len(ops.load_run_versions(vpath)) == 2  # prior version kept (non-destructive)
    assert ops.latest_run_version(vpath)["identity"] == "ident-2"

    # staleness: latest identity no longer matches the current operands
    assert ops.is_stale(vpath, "ident-2") is False
    assert ops.is_stale(vpath, "ident-3") is True

    assert ops.delete_run_version(vpath, "v1") is True
    assert [v["version_id"] for v in ops.load_run_versions(vpath)] == ["v2"]
    assert ops.delete_run_version(vpath, "v1") is False


# ── HTTP + CLI parity (FR-37) ─────────────────────────────────────────────────────────────────────

def _client(workspace: Path):
    from fastapi.testclient import TestClient

    from palimpsest.server import create_app

    return TestClient(create_app(workspace))


def test_http_lattice_roles_congruence(tmp_path: Path) -> None:
    _make_project(tmp_path, "drb", work_id="bible", embedding="e1", fingerprint="fp1")
    _make_project(tmp_path, "kjv", work_id="bible", embedding="e1", fingerprint="fp1")
    _make_project(tmp_path, "drb-appendix", parent="drb")
    cs.create_collection(tmp_path, "Scripture", "", ["drb", "kjv"])
    client = _client(tmp_path)

    body = client.get("/api/projects/drb/lattice").json()
    assert body["work_id"] == "bible" and body["siblings"] == ["kjv"]
    assert body["children"] == ["drb-appendix"] and body["collections"] == ["scripture"]
    assert client.get("/api/projects/ghost/lattice").status_code == 404

    r = client.put("/api/collections/scripture/roles/drb", json={"role": "root"})
    assert r.status_code == 200 and r.json()["roles"]["drb"] == "root"
    assert client.put("/api/collections/scripture/roles/drb", json={"role": "nope"}).status_code == 400
    assert client.put("/api/collections/scripture/roles/stranger", json={"role": "root"}).status_code == 400
    assert client.put("/api/collections/ghost/roles/drb", json={"role": "root"}).status_code == 404

    c = client.get("/api/collections/scripture/congruence?metric=cosine")
    assert c.status_code == 200 and c.json()["all_congruent"] is True
    assert client.get("/api/collections/scripture/congruence?metric=bogus").status_code == 400
    assert client.get("/api/collections/ghost/congruence?metric=cosine").status_code == 404


def test_delete_project_cascades_into_collections(tmp_path: Path) -> None:
    """Deleting a project must scrub it from every collection — both the membership list
    (so counts stay accurate) and the collection-local roles map (so no stale backbone
    reference lingers for a same-slug re-import to inherit)."""
    _make_project(tmp_path, "drb")
    _make_project(tmp_path, "kjv")
    cs.create_collection(tmp_path, "Scripture", "", ["drb", "kjv"])
    cs.set_member_role(tmp_path, "scripture", "drb", "root")
    assert cs.get_collection(tmp_path, "scripture")["roles"] == {"drb": "root"}
    client = _client(tmp_path)

    assert client.delete("/api/projects/drb").status_code == 200

    col = cs.get_collection(tmp_path, "scripture")
    assert col["project_ids"] == ["kjv"]  # membership strip (count drops)
    assert "roles" not in col  # role scrubbed; empty map pruned per invariant


def test_cli_collections(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    _make_project(tmp_path, "drb", work_id="bible")
    _make_project(tmp_path, "kjv", work_id="bible")
    runner = CliRunner()

    res = runner.invoke(main, ["collections", "create", str(tmp_path), "Scripture",
                               "--project", "drb", "--project", "kjv"])
    assert res.exit_code == 0 and "scripture" in res.output

    res = runner.invoke(main, ["collections", "list", str(tmp_path)])
    assert res.exit_code == 0 and "scripture" in res.output

    res = runner.invoke(main, ["collections", "role", str(tmp_path), "scripture", "drb", "root"])
    assert res.exit_code == 0

    res = runner.invoke(main, ["collections", "lattice", str(tmp_path), "drb"])
    assert res.exit_code == 0 and '"work_id": "bible"' in res.output
