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
    workspace: Path, q: str, t: str, pairs: list[tuple[int, int, int, int]],
    score: float = 30.0, identity: float = 0.0,
) -> Path:
    """Write a pairwise comparison exactly as the alignment run does: alignment.jsonl + metadata.json.

    ``pairs`` are (query_start, query_end, target_start, target_end) half-open paragraph ranges.
    ``identity`` is the block identity stamped on every record (0.0 = the AlignmentRecord default)."""
    records = [
        AlignmentRecord(query_id=q, query_start=qs, query_end=qe, target_id=t,
                        target_start=ts, target_end=te, score=score, identity=identity)
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


# ── phyletic / stemma tree (C4, FR-38) ─────────────────────────────────────────────────────────────

def test_phyletic_tree_distances_and_root(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    graph = cg.build_corpus_graph(workspace, cid)
    tree = cg.phyletic_tree(graph)

    members = tree["members"]
    di = {m: i for i, m in enumerate(members)}
    D = tree["distances"]
    # alpha & beta share core + shell; alpha/beta & gamma share only core → alpha,beta are closer.
    assert D[di["alpha"]][di["beta"]] == 0.5
    assert D[di["alpha"]][di["gamma"]] == 0.75
    assert D[di["beta"]][di["gamma"]] == 0.75

    # alpha and beta participate in 3 components, gamma in 2 → alpha (lowest index) is the backbone.
    assert tree["participation"] == {"alpha": 3, "beta": 3, "gamma": 2}
    assert tree["suggested_root"] == "alpha" and tree["root"] == "alpha"

    # every member is a leaf; the root has no parent.
    leaves = {n["member"] for n in tree["tree"] if n["is_leaf"]}
    assert leaves == {"alpha", "beta", "gamma"}
    root_node = next(n for n in tree["tree"] if n["id"] == "alpha")
    assert root_node["parent"] is None


def test_phyletic_tree_reroot_and_guard(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    graph = cg.build_corpus_graph(workspace, cid)

    tree = cg.phyletic_tree(graph, root="beta")
    assert tree["root"] == "beta" and tree["suggested_root"] == "alpha"
    assert next(n for n in tree["tree"] if n["id"] == "beta")["parent"] is None

    with pytest.raises(ValueError, match="not a member"):
        cg.phyletic_tree(graph, root="delta")


# ── over-merge guards (audit 2026-07-01: corpus-graph over-merge cluster) ────────────────────────────

def test_edge_min_identity_gates_union(tmp_path: Path) -> None:
    """A cross-member edge below ``edge_min_identity`` is recorded (flagged ``weak``) but does NOT fuse
    its two passages into one homology component — so weak cross-book noise cannot over-merge."""
    a = _member(tmp_path, "alpha", [
        "Strong shared core passage about the beginning of all things.",
        "Alpha gap padding present only in alpha here.",
        "Weak noisy passage that only faintly overlaps.",
    ])
    b = _member(tmp_path, "beta", [
        "Strong shared core passage about the beginning of all things.",
        "Beta gap padding present only in beta here.",
        "Weak noisy passage that only faintly overlaps.",
    ])
    # One comparison, two records at different block identities: para 0 is a true correspondence
    # (high identity), para 2 is faint noise (low identity).
    d = comparison_dir(tmp_path, a, b)
    d.mkdir(parents=True, exist_ok=True)
    write_alignment_records(d / "alignment.jsonl", [
        AlignmentRecord(query_id=a, query_start=0, query_end=1, target_id=b,
                        target_start=0, target_end=1, score=40.0, identity=0.9),
        AlignmentRecord(query_id=a, query_start=2, query_end=3, target_id=b,
                        target_start=2, target_end=3, score=12.0, identity=0.2),
    ])
    (d / "metadata.json").write_text(json.dumps({"query_id": a, "target_id": b}), encoding="utf-8")
    cid = cs.create_collection(tmp_path, "Pair", "two-text", [a, b])["id"]

    # Default (0.0): both edges union → both shared passages become 2-member "core" components.
    loose = cg.build_corpus_graph(tmp_path, cid)
    assert all(not e["weak"] for e in loose.edges)
    assert sum(1 for c in loose.components if c.classification == "core") == 2

    # Gate at 0.5: the strong edge still unions, the weak edge is recorded-not-unioned.
    gated = cg.build_corpus_graph(tmp_path, cid, edge_min_identity=0.5)
    weak = [e for e in gated.edges if e["weak"]]
    strong = [e for e in gated.edges if not e["weak"]]
    assert len(weak) == 1 and weak[0]["identity"] == 0.2
    assert len(strong) == 1 and strong[0]["identity"] == 0.9
    # Only the true correspondence remains a core component; the noisy passages split apart.
    assert sum(1 for c in gated.components if c.classification == "core") == 1
    assert gated.summary["edge_min_identity"] == 0.5


def test_edge_min_score_gates_union_where_identity_cannot(tmp_path: Path) -> None:
    """The score gate separates *shared-source* from *shared-content* correspondences where identity
    cannot. Both cross-member edges carry the SAME block identity — a synoptic-parallel fragment can be
    locally as identical as a genuine translation match — but the whole-text correspondence scores far
    higher because score is length/coverage-proportional. No ``edge_min_identity`` threshold keeps the
    first and drops the second (they share identity); ``edge_min_score`` does."""
    a = _member(tmp_path, "alpha", [
        "A long collinear passage that aligns end to end like a faithful translation of one source.",
        "Alpha gap padding present only in alpha here.",
        "A brief shared phrase.",
    ])
    b = _member(tmp_path, "beta", [
        "A long collinear passage that aligns end to end like a faithful translation of one source.",
        "Beta gap padding present only in beta here.",
        "A brief shared phrase.",
    ])
    # Same identity on both records; only the score differs — a long collinear correspondence (high
    # score) vs a short shared fragment (low score). Identity alone cannot tell them apart.
    d = comparison_dir(tmp_path, a, b)
    d.mkdir(parents=True, exist_ok=True)
    write_alignment_records(d / "alignment.jsonl", [
        AlignmentRecord(query_id=a, query_start=0, query_end=1, target_id=b,
                        target_start=0, target_end=1, score=40.0, identity=0.85),
        AlignmentRecord(query_id=a, query_start=2, query_end=3, target_id=b,
                        target_start=2, target_end=3, score=8.0, identity=0.85),
    ])
    (d / "metadata.json").write_text(json.dumps({"query_id": a, "target_id": b}), encoding="utf-8")
    cid = cs.create_collection(tmp_path, "Pair", "two-text", [a, b])["id"]

    # Default (no gate): both edges union → both shared passages become 2-member core components.
    loose = cg.build_corpus_graph(tmp_path, cid)
    assert all(not e["weak"] for e in loose.edges)
    assert sum(1 for c in loose.components if c.classification == "core") == 2

    # Identity gate is powerless here: identical identities mean every threshold treats both edges
    # alike. Below 0.85 both union (2 core); above 0.85 neither unions (0 core). It never yields 1.
    assert sum(1 for c in cg.build_corpus_graph(tmp_path, cid, edge_min_identity=0.5).components
               if c.classification == "core") == 2
    assert sum(1 for c in cg.build_corpus_graph(tmp_path, cid, edge_min_identity=0.9).components
               if c.classification == "core") == 0

    # Score gate separates them: the long correspondence unions, the short fragment is recorded-weak.
    gated = cg.build_corpus_graph(tmp_path, cid, edge_min_score=20.0)
    weak = [e for e in gated.edges if e["weak"]]
    strong = [e for e in gated.edges if not e["weak"]]
    assert len(weak) == 1 and weak[0]["score"] == 8.0
    assert len(strong) == 1 and strong[0]["score"] == 40.0
    assert sum(1 for c in gated.components if c.classification == "core") == 1
    assert gated.summary["edge_min_score"] == 20.0


def test_suggested_root_excludes_singletons(tmp_path: Path) -> None:
    """The suggested root counts only SHARED (multi-member) components: a fragmented member whose many
    unique gaps inflate its total participation must not out-rank the true shared backbone."""
    aaa = _member(tmp_path, "aaa", [
        "core beginning passage about all things",
        "shell passage shared with bbb only",
        "shell passage shared with zzz only",
    ])
    bbb = _member(tmp_path, "bbb", [
        "core beginning passage about all things",
        "shell passage shared with aaa only",
    ])
    zzz = _member(tmp_path, "zzz", [
        "core beginning passage about all things",
        "gap one unique to zzz alone",
        "shell passage shared with aaa only",
        "gap two unique to zzz alone",
    ])
    _comparison(tmp_path, aaa, bbb, [(0, 1, 0, 1), (1, 2, 1, 2)])
    _comparison(tmp_path, aaa, zzz, [(0, 1, 0, 1), (2, 3, 2, 3)])
    _comparison(tmp_path, bbb, zzz, [(0, 1, 0, 1)])
    cid = cs.create_collection(tmp_path, "Frag", "fragmented outgroup", [aaa, bbb, zzz])["id"]

    graph = cg.build_corpus_graph(tmp_path, cid)
    tree = cg.phyletic_tree(graph)
    # Full participation (still reported) would nominate zzz — its 2 singleton gaps inflate it.
    assert tree["participation"]["zzz"] > tree["participation"]["aaa"]
    # Shared-only participation correctly nominates the backbone aaa.
    assert tree["suggested_root"] == "aaa"


def test_phyletic_distance_uses_alignment_identity(tmp_path: Path) -> None:
    """The phyletic distance reflects alignment IDENTITY, not just shared-component membership: two
    near-identical members land closer than two distant ones, even when Jaccard cannot tell them apart
    (all three share only the core component, so Jaccard makes every pair equidistant)."""
    a = _member(tmp_path, "aaa", ["core beginning passage about all things", "aaa unique tail gap"])
    b = _member(tmp_path, "bbb", ["core beginning passage about all things", "bbb unique tail gap"])
    c = _member(tmp_path, "ccc", ["core beginning passage about all things", "ccc unique tail gap"])
    _comparison(tmp_path, a, b, [(0, 1, 0, 1)], identity=0.95)  # near-identical
    _comparison(tmp_path, a, c, [(0, 1, 0, 1)], identity=0.30)  # distant
    _comparison(tmp_path, b, c, [(0, 1, 0, 1)], identity=0.30)  # distant
    cid = cs.create_collection(tmp_path, "Ident", "identity distance", [a, b, c])["id"]
    graph = cg.build_corpus_graph(tmp_path, cid)
    ii = {m: i for i, m in enumerate(graph.members)}

    # Jaccard flattens all three pairs to one distance (each shares exactly the core).
    Dj = cg.phyletic_tree(graph, distance="jaccard")["distances"]
    assert Dj[ii["aaa"]][ii["bbb"]] == Dj[ii["aaa"]][ii["ccc"]] == Dj[ii["bbb"]][ii["ccc"]]

    # auto selects alignment identity (informative edges present) and separates the close pair.
    tree = cg.phyletic_tree(graph)
    assert tree["distance_basis"] == "alignment_identity"
    D = tree["distances"]
    assert D[ii["aaa"]][ii["bbb"]] == 0.05  # 1 - 0.95
    assert D[ii["aaa"]][ii["bbb"]] < D[ii["aaa"]][ii["ccc"]]
    assert D[ii["aaa"]][ii["bbb"]] < D[ii["bbb"]][ii["ccc"]]
    # only the core is shared across all 3 members → the coarse-structure warning is honest.
    assert tree["distance_warning"] is not None


def test_spread_histogram_shell_not_mislabeled_singleton() -> None:
    """A low-``N`` shell component (2/6 = 0.333) must bin as shell, not singleton: ``narrow + broad``
    always equals the shell-component count and ``singleton`` counts only true 1-member components."""
    hist = cg._spread_histogram([1 / 6, 2 / 6, 6 / 6], 6)
    assert hist["singleton"] == 1  # only the genuine 1-member component
    assert hist["core"] == 1
    assert hist["narrow"] + hist["broad"] == 1  # the 2-member shell, not a singleton


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

    tree = client.get(f"/api/collections/{cid}/phyletic-tree")
    assert tree.status_code == 200 and tree.json()["suggested_root"] == "alpha"
    rerooted = client.get(f"/api/collections/{cid}/phyletic-tree?root=beta")
    assert rerooted.status_code == 200 and rerooted.json()["root"] == "beta"
    assert client.get(f"/api/collections/{cid}/phyletic-tree?root=delta").status_code == 400

    # a <2-member collection cannot form a graph → 400.
    cs.create_collection(workspace, "Solo", "", ["alpha"])
    assert client.post("/api/collections/solo/corpus-graph").status_code == 400
    # phyletic tree 404s until the graph is built.
    assert client.get("/api/collections/solo/phyletic-tree").status_code == 404


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

    res = runner.invoke(main, ["collections", "phyletic-tree", str(workspace), cid])
    assert res.exit_code == 0 and '"suggested_root": "alpha"' in res.output


# ── C6a: anchor honesty (trim) + corpus analyses ────────────────────────────────────────────────

def _comparison_with_matrix(
    workspace: Path, q: str, t: str, pairs: list[tuple[int, int, int, int]], matrix
) -> Path:
    """Like _comparison but also writes the cross_similarity signal the anchor trim reads."""
    import numpy as np

    from palimpsest.formats.signals import SignalManifest, write_signal

    d = _comparison(workspace, q, t, pairs)
    arr = np.asarray(matrix, dtype=np.float32)
    manifest = SignalManifest(
        type="cross_similarity", name="cross_similarity", source=f"{q}->{t}",
        reference_sha256="", dimensions=list(arr.shape),
    )
    write_signal(d, arr, manifest)
    return d


def test_anchor_trim_prevents_trailing_mismatch_absorption(tmp_path: Path) -> None:
    """A shared block extended by a trailing mismatch would pull each member's unique final paragraph
    into a core component; anchor_trim shrinks the block to the high-similarity core so those unique
    paragraphs fall out as singletons."""
    a = _member(tmp_path, "alpha", ["shared one", "shared two", "alpha only unique tail"])
    b = _member(tmp_path, "beta", ["shared one", "shared two", "beta only unique tail"])
    # one record spanning all 3 paragraphs; matrix says para2<->para2 is a weak (trailing) match.
    matrix = [[0.9, 0.1, 0.1], [0.1, 0.9, 0.1], [0.1, 0.1, 0.2]]
    _comparison_with_matrix(tmp_path, a, b, [(0, 3, 0, 3)], matrix)
    col = cs.create_collection(tmp_path, "MM", "", [a, b])

    untrimmed = cg.build_corpus_graph(tmp_path, col["id"])  # trim off (default)
    assert untrimmed.summary["core"] == 1 and untrimmed.summary["singleton"] == 0

    trimmed = cg.build_corpus_graph(tmp_path, col["id"], anchor_trim=0.5)
    assert trimmed.summary["anchor_trim"] == 0.5
    # the shared [0,2) stays core; each member's trailing unique paragraph is now its own singleton.
    assert trimmed.summary["core"] == 1
    assert trimmed.summary["singleton"] == 2


def test_corpus_analyses_report(corpus: tuple[Path, str]) -> None:
    workspace, cid = corpus
    graph = cg.build_corpus_graph(workspace, cid)
    rep = cg.corpus_analyses(workspace, graph, duplicate_threshold=0.6)

    # words in every member's shared opening are boilerplate; a member-unique word is discriminative.
    assert "core" in rep["boilerplate"]["shared_by_all"]
    disc_terms = {d["term"] for d in rep["boilerplate"]["most_discriminative"]}
    assert "singleton" in disc_terms  # only gamma's unique paragraph has this word

    # alpha & beta are within 0.6 pangenome distance → clustered; gamma stays apart.
    clusters = [set(c["members"]) for c in rep["near_duplicate_clusters"]]
    assert {"alpha", "beta"} in clusters

    # diffusion is symmetric spread, present for every member, with the non-directionality note.
    assert set(rep["diffusion"]["member_reach"]) == {"alpha", "beta", "gamma"}
    assert "not a directional" in rep["diffusion"]["non_directional_note"]
    # 1 core component out of 5 total (1 core + 1 shell + 3 singletons).
    assert rep["diffusion"]["core_fraction"] == 0.2


def test_http_and_cli_corpus_analyses(corpus: tuple[Path, str]) -> None:
    from click.testing import CliRunner

    from palimpsest.cli import main

    workspace, cid = corpus
    client = _client(workspace)

    assert client.get(f"/api/collections/{cid}/corpus-analyses").status_code == 404  # not built
    client.post(f"/api/collections/{cid}/corpus-graph")
    rep = client.get(f"/api/collections/{cid}/corpus-analyses?duplicate_threshold=0.6")
    assert rep.status_code == 200
    assert {"alpha", "beta"} in [set(c["members"]) for c in rep.json()["near_duplicate_clusters"]]

    res = CliRunner().invoke(
        main, ["collections", "corpus-analyses", str(workspace), cid, "--duplicate-threshold", "0.6"]
    )
    assert res.exit_code == 0 and '"member_reach"' in res.output
