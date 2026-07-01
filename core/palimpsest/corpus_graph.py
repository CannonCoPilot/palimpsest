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
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from palimpsest.alignment.records import comparison_dir, read_alignment_records
from palimpsest.collections import get_collection
from palimpsest.formats.signals import read_signal
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


def _trim_to_high_sim(
    matrix: Any, qs: int, qe: int, ts: int, te: int, trim: float
) -> tuple[int, int, int, int]:
    """Shrink a record's ``[qs,qe) x [ts,te)`` block inward past low-similarity boundary cells.

    Anchor honesty (C6a): a Smith-Waterman block always starts and ends on a diagonal (match)
    cell, but a *trailing/leading mismatch* — a shared passage extended by one weakly-overlapping
    paragraph — inflates the anchor and can pull a genuinely disjoint passage into a ``core``/``shell``
    homology component. Trimming boundary cells whose cross-similarity is ``< trim`` keeps only the
    high-similarity core. The trim walks the diagonal correspondence in lockstep (valid at the block
    endpoints, which are diagonal by construction). Returns the trimmed range; may be empty."""
    rows, cols = matrix.shape
    while qe > qs and te > ts and qe - 1 < rows and te - 1 < cols and float(matrix[qe - 1, te - 1]) < trim:
        qe -= 1
        te -= 1
    while qs < qe and ts < te and qs < rows and ts < cols and float(matrix[qs, ts]) < trim:
        qs += 1
        ts += 1
    return qs, qe, ts, te


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

def build_corpus_graph(
    workspace: Path, collection_id: str, *, anchor_trim: float = 0.0,
    edge_min_identity: float = 0.0,
) -> CorpusGraph:
    """Assemble the reference-free corpus graph for a collection from its computed pairwise edges.

    Pairs without a stored comparison contribute no edges (reported under ``summary.pairs_missing``);
    the graph still builds from whatever correspondences exist.

    ``anchor_trim`` (C6a anchor honesty): when ``> 0``, each record's aligned block is trimmed inward
    past boundary cells whose cross-similarity is below the threshold before it becomes an anchor, so
    a shared passage extended by a weakly-overlapping (trailing/leading) paragraph no longer absorbs a
    disjoint passage into a ``core``/``shell`` homology component. ``0.0`` (default) keeps the raw
    record ranges (prior behavior). The trimmed span is reported under ``summary.anchor_trim``.

    ``edge_min_identity``: an alignment record whose scale-free block identity (mean per-cell
    similarity, ``AlignmentRecord.identity``) is below this threshold is still recorded as an edge but
    flagged ``weak`` and does NOT union its endpoints — so a weak cross-member correspondence cannot
    fuse two otherwise-disjoint passages into one homology component. ``0.0`` (default) unions every
    edge (prior behavior). Reported under ``summary.edge_min_identity``."""
    collection = get_collection(workspace, collection_id)
    if collection is None:
        raise ValueError(f"Collection not found: {collection_id}")
    members: list[str] = list(collection.get("project_ids", []))
    if len(members) < 2:
        raise ValueError("A corpus graph needs at least 2 members")

    # 1. Gather aligned intervals per member + the raw records (with their owning members) per pair.
    member_intervals: dict[str, list[tuple[int, int]]] = {m: [] for m in members}
    raw_edges: list[tuple[str, tuple[int, int], str, tuple[int, int], float, float, str]] = []
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
            matrix = None
            if anchor_trim > 0.0:
                try:
                    _, matrix = read_signal(comp_dir, "cross_similarity")
                except Exception:
                    matrix = None  # no stored matrix → fall back to untrimmed ranges (reported)
            pairs_with_edges.append([a, b])
            for r in records:
                qs, qe, ts, te = r.query_start, r.query_end, r.target_start, r.target_end
                if matrix is not None:
                    qs, qe, ts, te = _trim_to_high_sim(matrix, qs, qe, ts, te, anchor_trim)
                    if qe <= qs or te <= ts:
                        continue  # whole block was low-similarity boundary → drop, don't anchor
                q_iv = (qs, qe)
                t_iv = (ts, te)
                member_intervals[q_id].append(q_iv)
                member_intervals[t_id].append(t_iv)
                raw_edges.append(
                    (q_id, q_iv, t_id, t_iv, float(r.score), float(r.identity), comp_dir.name)
                )

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
    for q_id, q_iv, t_id, t_iv, score, identity, comp_name in raw_edges:
        na, nb = _anchor_of(q_id, q_iv), _anchor_of(t_id, t_iv)
        if na is None or nb is None:
            continue
        weak = identity < edge_min_identity
        if not weak:  # weak edges are recorded but never fuse homology components
            uf.union(na, nb)
        edges.append({"a": na, "b": nb, "comparison": comp_name,
                      "score": score, "identity": identity, "weak": weak})

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
        "anchor_trim": anchor_trim,
        "edge_min_identity": edge_min_identity,
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

def _alignment_distance(
    graph: CorpusGraph, idx: dict[str, int], n: int, fallback: np.ndarray
) -> tuple[np.ndarray, bool]:
    """Member-pair distance ``1 − mean edge identity``, with per-pair fallback to ``fallback`` (Jaccard).

    Aggregates ``identity`` over the graph's cross-member edges (populated by Smith-Waterman; see
    ``AlignmentRecord.identity``). A pair with no edges, or edges whose identity is uninformative
    (summing to 0 — e.g. unpopulated legacy records), keeps its ``fallback`` distance. Returns the
    distance matrix and whether ANY pair had informative identity (so the caller can auto-select)."""
    node_member = {nd.id: nd.member for nd in graph.nodes}
    id_sum = np.zeros((n, n))
    id_cnt = np.zeros((n, n))
    for e in graph.edges:
        ma, mb = node_member.get(e["a"]), node_member.get(e["b"])
        if ma is None or mb is None or ma == mb:
            continue
        i, j = idx[ma], idx[mb]
        ident = float(e.get("identity", 0.0))
        id_sum[i, j] += ident
        id_sum[j, i] += ident
        id_cnt[i, j] += 1
        id_cnt[j, i] += 1

    dist = fallback.copy()
    informative = False
    for i in range(n):
        for j in range(i + 1, n):
            if id_cnt[i, j] > 0 and id_sum[i, j] > 0.0:
                d = float(np.clip(1.0 - id_sum[i, j] / id_cnt[i, j], 0.0, 1.0))
                dist[i, j] = dist[j, i] = d
                informative = True
    return dist, informative


def phyletic_tree(
    graph: CorpusGraph, root: str | None = None, *, distance: str = "auto"
) -> dict[str, Any]:
    """Derive the phyletic/stemma tree from the corpus graph's distance structure (FR-38).

    The tree is neighbor-joining; the suggested root is the most SHARED-component-complete member (the
    natural backbone for a "map everything onto X" lens), which the caller may override via ``root``.
    The tree is a *reading* of the reference-free graph, not a stored ground truth.

    ``distance`` selects the inter-text metric:

      - ``"alignment_identity"`` — ``1 − mean alignment identity`` of the edges between each member
        pair (falling back to Jaccard for a pair whose edges carry no informative identity). Pangenome
        Jaccard alone counts *which* components two members share but is blind to alignment QUALITY, so
        two near-identical translations and two distant paraphrases that merely co-occur in the core
        land at the same distance — the tree then contradicts ground truth. Identity restores the
        gradient.
      - ``"jaccard"`` — pangenome Jaccard dissimilarity over shared homology components (prior behavior).
      - ``"auto"`` (default) — alignment identity when any member pair has informative edge identity,
        else Jaccard.

    ``summary.distance_basis`` reports which metric produced the returned ``distances``; a
    ``distance_warning`` is set when there are too few shared components to resolve the tree stably."""
    from palimpsest.analysis import phylo

    members = graph.members
    idx = {m: i for i, m in enumerate(members)}
    n = len(members)
    comp_sets = [{idx[m] for m in c.members} for c in graph.components]

    jaccard = phylo.component_distance_matrix(n, comp_sets)
    align, informative = _alignment_distance(graph, idx, n, jaccard)
    use_align = informative if distance == "auto" else distance in ("alignment", "alignment_identity")
    distances = align if use_align else jaccard
    distance_basis = "alignment_identity" if use_align else "jaccard"

    n_shared = sum(1 for c in graph.components if len(c.members) > 1)
    distance_warning = None
    if n_shared < n - 1:
        distance_warning = (
            f"only {n_shared} shared (multi-member) component(s) across {n} members — the distance "
            "structure is coarse and the tree may be unstable"
        )

    participation = phylo.participation_counts(n, comp_sets)
    # Root = most component-complete member, but count only SHARED (multi-member) components: a
    # heavily-fragmented outgroup accrues many singleton components from its own gaps, which would
    # otherwise inflate its participation and wrongly nominate it as the backbone.
    shared_sets = [s for s in comp_sets if len(s) > 1]
    root_participation = phylo.participation_counts(n, shared_sets)
    suggested = members[max(range(n), key=lambda i: (root_participation[i], -i))]

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
        "distance_basis": distance_basis,
        "distance_warning": distance_warning,
        "participation": {members[i]: int(participation[i]) for i in range(n)},
        "suggested_root": suggested,
        "root": chosen,
        "tree": tree,
    }


# ── corpus analyses (C6a — leaves over the graph + member texts, FR-31) ────────────────────────────

_CORPUS_WORD_RE = re.compile(r"\w+")


def _member_tokens(workspace: Path, member: str) -> list[str]:
    """Lowercased word tokens of a member's analyzable (masked-resolved) text."""
    try:
        text, _ = Project.load(workspace / member).analyzable_text(sep=" ")
    except Exception:
        return []
    return _CORPUS_WORD_RE.findall(text.lower())


def corpus_analyses(
    workspace: Path,
    graph: CorpusGraph,
    *,
    duplicate_threshold: float = 0.15,
    top_terms: int = 25,
) -> dict[str, Any]:
    """Collection-level corpus analyses over the C3 graph + member texts (C6a, FR-31).

    Reads member texts and the corpus graph, reduces them to primitive inputs, and calls the pure
    ``analysis.corpus_analysis`` leaf. Three honest families:

      - **boilerplate / IDF** — terms shared by every member (lowest IDF) are the cross-member
        boilerplate to down-weight; ``top_terms`` highest-IDF terms are the most discriminative.
      - **near-duplicate clusters** — single-linkage groups over the pangenome Jaccard distance
        (``duplicate_threshold``); members sharing almost all homology collapse together.
      - **diffusion / spread** — per-component breadth and per-member reach across the corpus.
        Undirected by construction: spread, never who-influenced-whom (the reference-free graph
        carries no arrow of transmission — stated, not implied)."""
    from palimpsest.analysis import corpus_analysis as ca

    members = graph.members
    idx = {m: i for i, m in enumerate(members)}
    n = len(members)

    token_lists = [_member_tokens(workspace, m) for m in members]
    token_sets = [set(t) for t in token_lists]

    idf = ca.corpus_idf(token_sets)
    boilerplate = ca.boilerplate_terms(token_sets)
    discriminative = sorted(idf.items(), key=lambda kv: (-kv[1], kv[0]))[:top_terms]

    comp_sets_int = [[idx[m] for m in c.members] for c in graph.components]
    comp_sets_set = [set(s) for s in comp_sets_int]
    distances = phylo_distance_rows(n, comp_sets_set)
    clusters = ca.single_linkage_clusters(distances, duplicate_threshold)

    spreads = ca.component_spread(n, comp_sets_int)
    reach = ca.member_reach(n, comp_sets_int)

    return {
        "collection_id": graph.collection_id,
        "members": members,
        "boilerplate": {
            "shared_by_all": boilerplate[:top_terms],
            "n_shared_by_all": len(boilerplate),
            "most_discriminative": [{"term": t, "idf": round(v, 4)} for t, v in discriminative],
            "vocab_size": len(idf),
        },
        "near_duplicate_clusters": [
            {"members": [members[i] for i in cl], "size": len(cl)} for cl in clusters if len(cl) > 1
        ],
        "diffusion": {
            "non_directional_note": (
                "reference-free graph: this is passage spread across members, not a directional "
                "influence/derivation claim"
            ),
            "member_reach": {members[i]: round(reach[i], 4) for i in range(n)},
            "component_spread_histogram": _spread_histogram(spreads, n),
            "core_fraction": round(sum(1 for s in spreads if s >= 1.0) / len(spreads), 4)
            if spreads else 0.0,
        },
    }


def phylo_distance_rows(n: int, comp_member_sets: list[set[int]]) -> list[list[float]]:
    """Pangenome Jaccard distance as plain nested lists (the leaf's single-linkage input)."""
    from palimpsest.analysis import phylo

    D = phylo.component_distance_matrix(n, comp_member_sets)
    return [[float(D[i][j]) for j in range(n)] for i in range(n)]


def _spread_histogram(spreads: list[float], n_members: int) -> dict[str, int]:
    """Bucket component spread fractions into coarse breadth bands for a compact readout.

    ``singleton`` and ``core`` key on distinct-member COUNT (exactly one member / all members) to match
    the graph's own classification, so a low-``N`` shell component (e.g. 2/6 = 0.333) is never
    mis-binned as a singleton; ``narrow``/``broad`` sub-divide the remaining shell band by breadth.
    Consequently ``narrow + broad`` always equals the shell-component count."""
    bins = {"singleton": 0, "narrow": 0, "broad": 0, "core": 0}
    for s in spreads:
        k = round(s * n_members)  # distinct members reached
        if n_members > 0 and k >= n_members:
            bins["core"] += 1
        elif k <= 1:
            bins["singleton"] += 1
        elif s >= 0.66:
            bins["broad"] += 1
        else:
            bins["narrow"] += 1
    return bins


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
