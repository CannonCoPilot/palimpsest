"""Reference-free corpus alignment graph (collections tier C3).

The pangenome-idiom corpus model: no text is a privileged backbone. Pairwise alignments (the C2
edges) are assembled into one graph whose nodes are *passages* (maximal aligned paragraph ranges
within a member) and whose edges are cross-member correspondences. Each connected component is a
homology group; classified by how many distinct members it reaches:

    core      passage present in ALL members
    shell     present in SOME (>1, <all) members
    singleton present in exactly ONE member (a region no cross-member alignment covers)

A *root projection* is an on-demand view (not stored ground truth): given a chosen member as root,
read each component's coordinates in that member's paragraph frame.

Coordinates are 0-indexed half-open paragraph ranges ``[start, end)`` (the units of AlignmentRecord;
see alignment/smith_waterman.py). Character spans are attached from ``Project.paragraphs()`` for
downstream rendering (C4) but the graph reasons in paragraph space.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from palimpsest.alignment.records import comparison_dir, read_alignment_records
from palimpsest.collections import get_collection
from palimpsest.project import Project

CORPUS_GRAPH_FILE = "corpus_graph.json"


# ── data model ──────────────────────────────────────────────────────────────────────────────────

@dataclass
class PassageNode:
    """A maximal aligned paragraph range within one member (or an unaligned singleton gap)."""

    id: str
    member: str
    para_start: int
    para_end: int  # exclusive
    char_start: int | None = None
    char_end: int | None = None


@dataclass
class Component:
    """A homology group: passages across members judged equivalent by the alignment edges."""

    id: str
    classification: str  # "core" | "shell" | "singleton"
    members: list[str]
    node_ids: list[str]


@dataclass
class CorpusGraph:
    collection_id: str
    members: list[str]
    nodes: list[PassageNode]
    edges: list[dict[str, Any]]
    components: list[Component]
    summary: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "collection_id": self.collection_id,
            "members": self.members,
            "nodes": [asdict(n) for n in self.nodes],
            "edges": self.edges,
            "components": [asdict(c) for c in self.components],
            "summary": self.summary,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CorpusGraph:
        return cls(
            collection_id=d["collection_id"],
            members=d["members"],
            nodes=[PassageNode(**n) for n in d["nodes"]],
            edges=d.get("edges", []),
            components=[Component(**c) for c in d["components"]],
            summary=d.get("summary", {}),
            provenance=d.get("provenance", {}),
        )

    def component_for_node(self, node_id: str) -> Component | None:
        for c in self.components:
            if node_id in c.node_ids:
                return c
        return None


# ── union-find ──────────────────────────────────────────────────────────────────────────────────

class _UnionFind:
    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def add(self, x: str) -> None:
        self._parent.setdefault(x, x)

    def find(self, x: str) -> str:
        self.add(x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:  # path compression
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        self._parent[self.find(a)] = self.find(b)


# ── helpers ─────────────────────────────────────────────────────────────────────────────────────

def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping/adjacent half-open ranges into a sorted, disjoint set."""
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [list(ordered[0])]
    for s, e in ordered[1:]:
        if s <= merged[-1][1]:  # overlap or touch
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def _gaps(covered: list[tuple[int, int]], total: int) -> list[tuple[int, int]]:
    """Complement of ``covered`` (sorted, disjoint) within ``[0, total)``."""
    gaps: list[tuple[int, int]] = []
    cursor = 0
    for s, e in covered:
        if s > cursor:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < total:
        gaps.append((cursor, total))
    return gaps


def _find_comparison(workspace: Path, a: str, b: str) -> tuple[Path, str, str] | None:
    """Locate a stored pairwise comparison for the unordered pair ``{a, b}``.

    Returns ``(dir, query_id, target_id)`` so the caller knows which member owns the records'
    query vs target paragraph axis, or None if no comparison has been computed for the pair."""
    for q, t in ((a, b), (b, a)):
        d = comparison_dir(workspace, q, t)
        meta = d / "metadata.json"
        if (d / "alignment.jsonl").exists() and meta.exists():
            m = json.loads(meta.read_text(encoding="utf-8"))
            return d, m.get("query_id", q), m.get("target_id", t)
    return None


def _para_char_spans(workspace: Path, member: str) -> list[tuple[int, int]]:
    """Per-paragraph (char_start, char_end) for a member, for attaching character spans to nodes."""
    try:
        return [(s, e) for s, e, _ in Project.load(workspace / member).paragraphs()]
    except Exception:
        return []


def _reference_sha(workspace: Path, member: str) -> str | None:
    p = workspace / member / "reference.sha256"
    if p.exists():
        return p.read_text(encoding="utf-8").strip() or None
    return None


# ── build ───────────────────────────────────────────────────────────────────────────────────────

def build_corpus_graph(workspace: Path, collection_id: str) -> CorpusGraph:
    """Assemble the reference-free corpus graph for a collection from its computed pairwise edges.

    Pairs without a stored comparison contribute no edges (reported under ``summary.pairs_missing``);
    the graph still builds from whatever correspondences exist."""
    collection = get_collection(workspace, collection_id)
    if collection is None:
        raise ValueError(f"Collection not found: {collection_id}")
    members: list[str] = list(collection.get("project_ids", []))
    if len(members) < 2:
        raise ValueError("A corpus graph needs at least 2 members")

    # 1. Gather aligned intervals per member + the raw records (with their owning members) per pair.
    member_intervals: dict[str, list[tuple[int, int]]] = {m: [] for m in members}
    raw_edges: list[tuple[str, tuple[int, int], str, tuple[int, int], float, str]] = []
    pairs_with_edges: list[list[str]] = []
    pairs_missing: list[list[str]] = []

    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            a, b = members[i], members[j]
            found = _find_comparison(workspace, a, b)
            if found is None:
                pairs_missing.append([a, b])
                continue
            comp_dir, q_id, t_id = found
            records = read_alignment_records(comp_dir / "alignment.jsonl")
            if not records:
                pairs_missing.append([a, b])
                continue
            pairs_with_edges.append([a, b])
            for r in records:
                q_iv = (r.query_start, r.query_end)
                t_iv = (r.target_start, r.target_end)
                member_intervals[q_id].append(q_iv)
                member_intervals[t_id].append(t_iv)
                raw_edges.append((q_id, q_iv, t_id, t_iv, float(r.score), comp_dir.name))

    # 2. Merge each member's intervals into anchor nodes; index by (member, start) for lookup.
    nodes: list[PassageNode] = []
    anchor_index: dict[str, list[tuple[int, int, str]]] = {}  # member -> [(start, end, node_id)]
    node_counter = 0
    char_spans_cache: dict[str, list[tuple[int, int]]] = {}

    for member in members:
        char_spans = char_spans_cache.setdefault(member, _para_char_spans(workspace, member))
        anchors = _merge_intervals(member_intervals[member])
        anchor_index[member] = []
        for s, e in anchors:
            nid = f"n{node_counter}"
            node_counter += 1
            cs = char_spans[s][0] if s < len(char_spans) else None
            ce = char_spans[e - 1][1] if 0 < e <= len(char_spans) else None
            nodes.append(PassageNode(nid, member, s, e, cs, ce))
            anchor_index[member].append((s, e, nid))

    def _anchor_of(member: str, iv: tuple[int, int]) -> str | None:
        for s, e, nid in anchor_index.get(member, []):
            if s <= iv[0] and iv[1] <= e:  # fully contained (anchors are merges of all intervals)
                return nid
        return None

    # 3. Union anchors linked by an edge; record edges between node ids.
    uf = _UnionFind()
    for n in nodes:
        uf.add(n.id)
    edges: list[dict[str, Any]] = []
    for q_id, q_iv, t_id, t_iv, score, comp_name in raw_edges:
        na, nb = _anchor_of(q_id, q_iv), _anchor_of(t_id, t_iv)
        if na is None or nb is None:
            continue
        uf.union(na, nb)
        edges.append({"a": na, "b": nb, "comparison": comp_name, "score": score})

    # 4. Add unaligned regions as singleton nodes (each its own component later).
    for member in members:
        char_spans = char_spans_cache[member]
        total = len(char_spans)
        covered = _merge_intervals(member_intervals[member])
        for s, e in _gaps(covered, total):
            nid = f"n{node_counter}"
            node_counter += 1
            cs = char_spans[s][0] if s < len(char_spans) else None
            ce = char_spans[e - 1][1] if 0 < e <= len(char_spans) else None
            nodes.append(PassageNode(nid, member, s, e, cs, ce))
            uf.add(nid)  # isolated → its own component

    # 5. Group nodes into components and classify by distinct-member reach.
    groups: dict[str, list[str]] = {}
    for n in nodes:
        groups.setdefault(uf.find(n.id), []).append(n.id)

    node_by_id = {n.id: n for n in nodes}
    n_members = len(members)
    components: list[Component] = []
    counts = {"core": 0, "shell": 0, "singleton": 0}
    for idx, (_root, node_ids) in enumerate(sorted(groups.items())):
        comp_members = sorted({node_by_id[nid].member for nid in node_ids})
        if len(comp_members) == n_members:
            kind = "core"
        elif len(comp_members) == 1:
            kind = "singleton"
        else:
            kind = "shell"
        counts[kind] += 1
        components.append(Component(f"c{idx}", kind, comp_members, sorted(node_ids)))

    summary = {
        "n_members": n_members,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_components": len(components),
        "core": counts["core"],
        "shell": counts["shell"],
        "singleton": counts["singleton"],
        "pairs_with_edges": pairs_with_edges,
        "pairs_missing": pairs_missing,
    }
    provenance = {
        "member_sha256": {m: _reference_sha(workspace, m) for m in members},
        "edge_comparisons": sorted({e["comparison"] for e in edges}),
    }
    return CorpusGraph(collection_id, members, nodes, edges, components, summary, provenance)


# ── root projection (a view, not stored) ─────────────────────────────────────────────────────────

def project_to_root(graph: CorpusGraph, root_id: str) -> dict[str, Any]:
    """Project the graph onto a chosen root member's paragraph frame.

    Each component reports its coordinate range in the root (the root's anchor for that passage) or
    ``null`` when the passage is absent from the root. This is the synteny lens — derived on demand,
    never the canonical model."""
    if root_id not in graph.members:
        raise ValueError(f"Root {root_id!r} is not a member of collection {graph.collection_id}")
    node_by_id = {n.id: n for n in graph.nodes}
    rows: list[dict[str, Any]] = []
    for comp in graph.components:
        root_node = next(
            (node_by_id[nid] for nid in comp.node_ids if node_by_id[nid].member == root_id), None
        )
        rows.append({
            "component": comp.id,
            "classification": comp.classification,
            "members": comp.members,
            "in_root": root_node is not None,
            "root_span": None if root_node is None
            else {
                "para_start": root_node.para_start, "para_end": root_node.para_end,
                "char_start": root_node.char_start, "char_end": root_node.char_end,
            },
            "member_spans": {
                node_by_id[nid].member: {
                    "para_start": node_by_id[nid].para_start, "para_end": node_by_id[nid].para_end,
                }
                for nid in comp.node_ids
            },
        })
    rows.sort(key=lambda r: (
        r["root_span"]["para_start"] if r["root_span"] else 1 << 30, r["component"]))
    return {
        "collection_id": graph.collection_id,
        "root": root_id,
        "components": rows,
        "in_root_count": sum(1 for r in rows if r["in_root"]),
    }


# ── phyletic / stemma tree (a view over the graph's distance structure, C4 / FR-38) ───────────────

def phyletic_tree(graph: CorpusGraph, root: str | None = None) -> dict[str, Any]:
    """Derive the phyletic/stemma tree from the corpus graph's distance structure (FR-38).

    Inter-text distance is pangenome Jaccard dissimilarity over shared homology components; the tree is
    neighbor-joining; the suggested root is the most component-complete member (the natural backbone for
    a "map everything onto X" lens), which the caller may override via ``root``. The tree is a *reading*
    of the reference-free graph, not a stored ground truth."""
    from palimpsest.analysis import phylo

    members = graph.members
    idx = {m: i for i, m in enumerate(members)}
    n = len(members)
    comp_sets = [{idx[m] for m in c.members} for c in graph.components]

    distances = phylo.component_distance_matrix(n, comp_sets)
    participation = phylo.participation_counts(n, comp_sets)
    suggested = members[max(range(n), key=lambda i: (participation[i], -i))]

    chosen = suggested if root is None else root
    if chosen not in idx:
        raise ValueError(f"Root {chosen!r} is not a member of collection {graph.collection_id}")

    edges, _ = phylo.neighbor_joining(distances)
    children, parent, branch = phylo.root_tree(edges, idx[chosen])

    def label(node: int) -> str:
        return members[node] if node < n else f"node{node - n}"

    all_nodes = sorted(set(parent) | set(children))
    tree = [
        {
            "id": label(node),
            "is_leaf": node < n,
            "member": members[node] if node < n else None,
            "parent": None if parent.get(node) is None else label(parent[node]),
            "branch_length": round(branch.get(node, 0.0), 6),
            "children": [label(c) for c in children.get(node, [])],
        }
        for node in all_nodes
    ]
    return {
        "collection_id": graph.collection_id,
        "members": members,
        "distances": [[round(float(distances[i][j]), 6) for j in range(n)] for i in range(n)],
        "participation": {members[i]: int(participation[i]) for i in range(n)},
        "suggested_root": suggested,
        "root": chosen,
        "tree": tree,
    }


# ── persistence (collections/{id}/, OQ-6 / FR-32) ────────────────────────────────────────────────

def corpus_graph_dir(workspace: Path, collection_id: str) -> Path:
    return Path(workspace) / "collections" / collection_id


def write_corpus_graph(workspace: Path, collection_id: str, graph: CorpusGraph) -> Path:
    d = corpus_graph_dir(workspace, collection_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / CORPUS_GRAPH_FILE
    path.write_text(json.dumps(graph.to_dict(), indent=2), encoding="utf-8")
    return path


def read_corpus_graph(workspace: Path, collection_id: str) -> CorpusGraph | None:
    path = corpus_graph_dir(workspace, collection_id) / CORPUS_GRAPH_FILE
    if not path.exists():
        return None
    return CorpusGraph.from_dict(json.loads(path.read_text(encoding="utf-8")))
