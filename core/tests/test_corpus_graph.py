"""Collections tier — phase C3 (reference-free corpus graph, pangenome classification, root projection).

The graph is *assembled correspondences*, not a new alignment algorithm: nodes are merged paragraph
anchors per member, edges are the C2 pairwise alignment records, union-find groups anchors into
homology components, and each component is classified core / shell / singleton by its distinct-member
reach. These tests fabricate a contract-accurate 3-member collection — real ``reference.txt``
paragraphs (so ``Project.paragraphs()`` yields true char spans) plus pairwise comparison dirs written
exactly as ``POST /api/alignment/run`` writes them (``alignment.jsonl`` + ``metadata.json``) — and
exercise classification, the never-singleton-when-aligned invariant, root-projection coordinates,
missing-pair reporting, and persistence.

Fixture topology (paragraph index in brackets):

    A: [0] core   [1] gap   [2] shell-with-B
    B: [0] core   [1] gap   [2] shell-with-A
    C: [0] core   [1] unique

    edges  A↔B: (0,0) core, (2,2) shell    A↔C: (0,0) core    B↔C: (0,0) core

The gap paragraph between each member's core and shell passages is load-bearing: ``_merge_intervals``
fuses adjacent ranges, so core[0] and shell[2] would collapse into one anchor without an unaligned
[1] between them. That gap also supplies the singletons. Expected classification: 1 core {A,B,C},
1 shell {A,B}, 3 singletons (each member's unaligned region).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from palimpsest import collections as cs
from palimpsest import corpus_graph as cg
from palimpsest.alignment.records import AlignmentRecord, comparison_dir, write_alignment_records
from palimpsest.project import Project


def _member(workspace: Path, pid: str, paragraphs: list[str]) -> str:
    pdir = workspace / pid
    pdir.mkdir(parents=True, exist_ok=True)
    text = "\n\n".join(paragraphs) + "\n"
    (pdir / "metadata.json").write_text(
        json.dumps({
            "id": pid, "title": pid, "language": "en", "source_format": "txt",
            "source_file": f"{pid}.txt", "ingest_date": "2026-06-30", "palimpsest_version": "0",
            "reference_sha256": f"sha-{pid}", "word_count": len(text.split()),
            "paragraph_count": len(paragraphs), "section_count": 0,
            "sentence_count": len(paragraphs), "character_count": len(text),
        }),
        encoding="utf-8",
    )
    (pdir / "reference.txt").write_text(text, encoding="utf-8")
    (pdir / "reference.sha256").write_text(f"sha-{pid}", encoding="utf-8")
    return pid


def _comparison(
    workspace: Path, q: str, t: str, pairs: list[tuple[int, int, int, int]], score: float = 30.0
) -> Path:
    """Write a pairwise comparison exactly as the alignment run does: alignment.jsonl + metadata.json.

    ``pairs`` are (query_start, query_end, target_start, target_end) half-open paragraph ranges."""
    records = [
        AlignmentRecord(query_id=q, query_start=qs, query_end=qe,
                        target_id=t, target_start=ts, target_end=te, score=score)
        for qs, qe, ts, te in pairs
    ]
    d = comparison_dir(workspace, q, t)
    d.mkdir(parents=True, exist_ok=True)
    write_alignment_records(d / "alignment.jsonl", records)
    (d / "metadata.json").write_text(json.dumps({"query_id": q, "target_id": t}), encoding="utf-8")
    return d


@pytest.fixture
def corpus(tmp_path: Path) -> tuple[Path, str]:
    """A 3-member collection with the topology documented in the module docstring. Returns
    (workspace, collection_id)."""
    a = _member(tmp_path, "alpha", [
        "Alpha zero core passage about the beginning of things.",
        "Alpha one gap passage present only in alpha here.",
        "Alpha two shell passage shared with beta alone.",
    ])
    b = _member(tmp_path, "beta", [
        "Beta zero core passage about the beginning of things.",
        "Beta one gap passage present only in beta here.",
        "Beta two shell passage shared with alpha alone.",
    ])
    c = _member(tmp_path, "gamma", [
        "Gamma zero core passage about the beginning of things.",
        "Gamma one singleton passage unique to gamma.",
    ])
    _comparison(tmp_path, a, b, [(0, 1, 0, 1), (2, 3, 2, 3)])  # core + shell
    _comparison(tmp_path, a, c, [(0, 1, 0, 1)])               # core
    _comparison(tmp_path, b, c, [(0, 1, 0, 1)])               # core
    col = cs.create_collection(tmp_path, "Corpus", "three-text corpus", [a, b, c])
    return tmp_path, col["id"]


def _by_class(graph: cg.CorpusGraph, kind: str) -> list[cg.Component]:
    return [c for c in graph.components if c.classification == kind]


def test_pangenome_classification(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    graph = cg.build_corpus_graph(workspace, cid)

    assert graph.summary["core"] == 1
    assert graph.summary["shell"] == 1
    assert graph.summary["singleton"] == 3

    (core,) = _by_class(graph, "core")
    assert core.members == ["alpha", "beta", "gamma"]

    (shell,) = _by_class(graph, "shell")
    assert shell.members == ["alpha", "beta"]

    singletons = _by_class(graph, "singleton")
    assert {m for s in singletons for m in s.members} == {"alpha", "beta", "gamma"}
    assert all(len(s.members) == 1 for s in singletons)


def test_aligned_components_are_never_singletons(corpus: tuple[Path, str]) -> None:
    """The formalized C3 invariant: every alignment edge crosses members (a query member links to a
    *different* target member), so every edge-touched component reaches >=2 members and is core or
    shell. Singletons arise only from unaligned gaps — no edge touches them."""
    workspace, cid = corpus
    graph = cg.build_corpus_graph(workspace, cid)

    edge_nodes = {e["a"] for e in graph.edges} | {e["b"] for e in graph.edges}
    assert edge_nodes, "fixture must produce edges"

    for comp in graph.components:
        touched = [nid for nid in comp.node_ids if nid in edge_nodes]
        if comp.classification == "singleton":
            assert touched == [], f"singleton {comp.id} should not be touched by any edge"
            assert len(comp.members) == 1
        if touched:
            assert len(comp.members) >= 2, f"edge-touched {comp.id} must span >=2 members"


def test_root_projection_coordinates(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    graph = cg.build_corpus_graph(workspace, cid)
    proj = cg.project_to_root(graph, "alpha")

    assert proj["root"] == "alpha"
    rows = {r["component"]: r for r in proj["components"]}

    paras = Project.load(workspace / "alpha").paragraphs()

    (core,) = _by_class(graph, "core")
    core_row = rows[core.id]
    assert core_row["in_root"] is True
    assert core_row["root_span"]["para_start"] == 0 and core_row["root_span"]["para_end"] == 1
    assert core_row["root_span"]["char_start"] == paras[0][0]
    assert core_row["root_span"]["char_end"] == paras[0][1]

    (shell,) = _by_class(graph, "shell")
    shell_row = rows[shell.id]
    assert shell_row["in_root"] is True
    assert shell_row["root_span"]["para_start"] == 2 and shell_row["root_span"]["para_end"] == 3
    assert shell_row["root_span"]["char_start"] == paras[2][0]
    assert shell_row["root_span"]["char_end"] == paras[2][1]

    # gamma's unique passage is absent from the alpha root frame.
    gamma_only = next(s for s in _by_class(graph, "singleton") if s.members == ["gamma"])
    assert rows[gamma_only.id]["in_root"] is False
    assert rows[gamma_only.id]["root_span"] is None

    # alpha contributes core + shell + its own gap singleton = 3 components present in the root.
    assert proj["in_root_count"] == 3


def test_missing_pair_is_reported_and_graph_still_builds(tmp_path: Path) -> None:
    """A pair without a stored comparison contributes no edges but is reported, and the graph still
    assembles from the correspondences that do exist."""
    a = _member(tmp_path, "alpha", ["shared opening passage", "alpha tail"])
    b = _member(tmp_path, "beta", ["shared opening passage", "beta tail"])
    c = _member(tmp_path, "gamma", ["shared opening passage", "gamma tail"])
    _comparison(tmp_path, a, b, [(0, 1, 0, 1)])
    _comparison(tmp_path, a, c, [(0, 1, 0, 1)])
    # deliberately omit beta↔gamma
    col = cs.create_collection(tmp_path, "Corpus", "", [a, b, c])

    graph = cg.build_corpus_graph(tmp_path, col["id"])
    assert ["beta", "gamma"] in graph.summary["pairs_missing"]
    assert sorted(graph.summary["pairs_with_edges"]) == [["alpha", "beta"], ["alpha", "gamma"]]
    # alpha bridges beta and gamma transitively → still one core component over all three members.
    (core,) = _by_class(graph, "core")
    assert core.members == ["alpha", "beta", "gamma"]


def test_persistence_roundtrip(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    graph = cg.build_corpus_graph(workspace, cid)
    path = cg.write_corpus_graph(workspace, cid, graph)

    assert path == workspace / "collections" / cid / "corpus_graph.json"
    reloaded = cg.read_corpus_graph(workspace, cid)
    assert reloaded is not None
    assert reloaded.to_dict() == graph.to_dict()


def test_build_guards(tmp_path: Path) -> None:
    cs.create_collection(tmp_path, "Solo", "", ["only"])
    with pytest.raises(ValueError, match="at least 2 members"):
        cg.build_corpus_graph(tmp_path, "solo")

    with pytest.raises(ValueError, match="not found"):
        cg.build_corpus_graph(tmp_path, "does-not-exist")


def test_project_to_root_rejects_non_member(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    graph = cg.build_corpus_graph(workspace, cid)
    with pytest.raises(ValueError, match="not a member"):
        cg.project_to_root(graph, "delta")


# ── HTTP + CLI parity (FR-37) ─────────────────────────────────────────────────────────────────────

def _client(workspace: Path):
    from fastapi.testclient import TestClient

    from palimpsest.server import create_app

    return TestClient(create_app(workspace))


def test_http_corpus_graph(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    client = _client(workspace)

    # not built yet → 404 on read + projection.
    assert client.get(f"/api/collections/{cid}/corpus-graph").status_code == 404
    assert client.get(f"/api/collections/{cid}/corpus-graph/projection?root=alpha").status_code == 404

    built = client.post(f"/api/collections/{cid}/corpus-graph")
    assert built.status_code == 200
    summary = built.json()["summary"]
    assert (summary["core"], summary["shell"], summary["singleton"]) == (1, 1, 3)

    graph = client.get(f"/api/collections/{cid}/corpus-graph").json()
    assert len(graph["components"]) == summary["n_components"]

    proj = client.get(f"/api/collections/{cid}/corpus-graph/projection?root=alpha")
    assert proj.status_code == 200 and proj.json()["in_root_count"] == 3
    assert client.get(f"/api/collections/{cid}/corpus-graph/projection?root=delta").status_code == 400

    # a <2-member collection cannot form a graph → 400.
    cs.create_collection(workspace, "Solo", "", ["alpha"])
    assert client.post("/api/collections/solo/corpus-graph").status_code == 400


def test_cli_corpus_graph(corpus: tuple[Path, str]) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    workspace, cid = corpus
    runner = CliRunner()

    res = runner.invoke(main, ["collections", "corpus-graph-build", str(workspace), cid])
    assert res.exit_code == 0 and "1 core" in res.output and "1 shell" in res.output

    res = runner.invoke(main, ["collections", "corpus-graph-show", str(workspace), cid])
    assert res.exit_code == 0 and '"classification": "core"' in res.output

    res = runner.invoke(
        main, ["collections", "corpus-graph-project", str(workspace), cid, "--root", "alpha"]
    )
    assert res.exit_code == 0 and '"root": "alpha"' in res.output
