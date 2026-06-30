"""phylo — reference-free distance + neighbor-joining tree for the corpus overview (C4, FR-38).

A pure numeric leaf, like the sibling analysis modules: it takes the raw component-membership sets
behind a pangenome graph and returns a distance matrix and a neighbor-joining tree topology. No I/O,
no graph/``Project`` import — the caller (``corpus_graph.phyletic_tree``) reads the corpus graph, maps
member ids to integer indices, calls in here, and labels the result.

Distance is **pangenome Jaccard dissimilarity**: members that co-occur in many homology components are
close; members sharing few are distant (``1.0`` when two members never share a component). The tree is
built by **neighbor-joining** (Saitou & Nei 1987), the additive-distance standard. Rooting is a
separate, user-overridable choice — the "map everything onto text X" lens — defaulting to the most
component-complete member (FR-38: manual-first, distance-driven later, auto-root suggestion).

Member indices, not ids, cross this boundary; tie-breaking is deterministic (lowest index) so the same
distances always yield the same tree.
"""
from __future__ import annotations

from collections import deque

import numpy as np


def participation_counts(n: int, comp_member_sets: list[set[int]]) -> np.ndarray:
    """How many components each member appears in (the root-completeness signal)."""
    counts = np.zeros(n)
    for s in comp_member_sets:
        for i in s:
            counts[i] += 1
    return counts


def component_distance_matrix(n: int, comp_member_sets: list[set[int]]) -> np.ndarray:
    """Jaccard dissimilarity ``D[i,j] = 1 - |comps with both i,j| / |comps with i or j|``.

    Zero on the diagonal; ``1.0`` when two members never co-occur in any component."""
    both = np.zeros((n, n))
    for s in comp_member_sets:
        members = sorted(s)
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                i, j = members[a], members[b]
                both[i, j] += 1
                both[j, i] += 1
    part = participation_counts(n, comp_member_sets)
    D = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            union = part[i] + part[j] - both[i, j]
            d = 1.0 - both[i, j] / union if union > 0 else 1.0
            D[i, j] = D[j, i] = d
    return D


def neighbor_joining(D: np.ndarray) -> tuple[list[tuple[int, int, float]], int]:
    """Saitou-Nei neighbor-joining. Leaves are ``0..n-1``; internal nodes get ids ``n, n+1, …``.

    Returns ``(edges, n_internal)`` where each edge is ``(node_a, node_b, branch_length)`` with the
    length clamped to ``>= 0`` (NJ can yield small negative lengths, a display artifact). Pair
    selection breaks ties by lowest index so the topology is deterministic for a given matrix."""
    n = D.shape[0]
    if n <= 1:
        return [], 0
    if n == 2:
        return [(0, 1, max(0.0, float(D[0, 1])))], 0

    active = list(range(n))
    dist: dict[tuple[int, int], float] = {}
    for a in range(n):
        for b in range(n):
            dist[(a, b)] = float(D[a, b])
    edges: list[tuple[int, int, float]] = []
    next_id = n

    while len(active) > 2:
        m = len(active)
        r = {a: sum(dist[(a, b)] for b in active if b != a) for a in active}
        best: tuple[int, int] | None = None
        best_q = None
        for ia in range(m):
            for ib in range(ia + 1, m):
                a, b = active[ia], active[ib]
                q = (m - 2) * dist[(a, b)] - r[a] - r[b]
                if best_q is None or q < best_q - 1e-12:
                    best_q, best = q, (a, b)
        assert best is not None
        a, b = best
        u = next_id
        next_id += 1
        dab = dist[(a, b)]
        da = 0.5 * dab + (r[a] - r[b]) / (2 * (m - 2))
        db = dab - da
        edges.append((u, a, max(0.0, da)))
        edges.append((u, b, max(0.0, db)))
        for c in active:
            if c in (a, b):
                continue
            duc = 0.5 * (dist[(a, c)] + dist[(b, c)] - dab)
            dist[(u, c)] = dist[(c, u)] = duc
        active = [x for x in active if x not in (a, b)] + [u]

    a, b = active
    edges.append((a, b, max(0.0, dist[(a, b)])))
    return edges, next_id - n


def root_tree(
    edges: list[tuple[int, int, float]], root: int
) -> tuple[dict[int, list[int]], dict[int, int | None], dict[int, float]]:
    """Orient the unrooted ``edges`` as a tree rooted at node ``root``.

    Returns ``(children, parent, branch_length)``: ``children[node]`` lists child nodes in BFS order,
    ``parent[node]`` is the node above (``None`` at the root), ``branch_length[node]`` is the length of
    the edge to that parent (``0.0`` at the root)."""
    adj: dict[int, list[int]] = {}
    elen: dict[tuple[int, int], float] = {}
    for a, b, w in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
        elen[(a, b)] = elen[(b, a)] = w

    children: dict[int, list[int]] = {}
    parent: dict[int, int | None] = {root: None}
    branch: dict[int, float] = {root: 0.0}
    seen = {root}
    queue = deque([root])
    while queue:
        node = queue.popleft()
        for nb in adj.get(node, []):
            if nb not in seen:
                seen.add(nb)
                parent[nb] = node
                branch[nb] = elen[(node, nb)]
                children.setdefault(node, []).append(nb)
                queue.append(nb)
    return children, parent, branch
