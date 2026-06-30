"""Collections tier — phase C4 (phyletic/stemma tree leaf: pangenome distance + neighbor-joining).

``analysis.phylo`` is a pure numeric leaf — it never touches the graph or disk — so these tests drive
it with hand-built component-membership sets and distance matrices and assert the maths and topology
directly: Jaccard dissimilarity, deterministic neighbor-joining grouping, and tree orientation.
"""
from __future__ import annotations

import numpy as np
import pytest

from palimpsest.analysis import phylo


def _neighbors(edges: list[tuple[int, int, float]]) -> dict[int, set[int]]:
    adj: dict[int, set[int]] = {}
    for a, b, _ in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


def test_jaccard_distance_matrix() -> None:
    # 4 members, components: {0,1,2,3} core, {0,1} shell, {0} {1} {2} {3} singletons.
    comp_sets = [{0, 1, 2, 3}, {0, 1}, {0}, {1}, {2}, {3}]
    D = phylo.component_distance_matrix(4, comp_sets)

    assert np.allclose(np.diag(D), 0.0)
    assert np.allclose(D, D.T)
    # 0 & 1 share core+shell (both=2); participation 0→3, 1→3; union=3+3-2=4; sim .5 → dist .5
    assert D[0, 1] == 0.5
    # 0 & 2 share only core (both=1); participation 0→3, 2→2; union=3+2-1=4; sim .25 → dist .75
    assert D[0, 2] == 0.75
    # 2 & 3 share only core (both=1); participation 2→2, 3→2; union=2+2-1=3; sim 1/3 → dist 2/3
    assert D[2, 3] == pytest.approx(2 / 3)


def test_participation_counts() -> None:
    comp_sets = [{0, 1, 2}, {0, 1}, {2}]
    part = phylo.participation_counts(3, comp_sets)
    assert list(part) == [2, 2, 2]


def test_neighbor_joining_groups_close_pairs() -> None:
    # A,B close (0.1) and C,D close (0.1); cross pairs distant (0.5). NJ must pair AB and CD.
    D = np.array([
        [0.0, 0.1, 0.5, 0.5],
        [0.1, 0.0, 0.5, 0.5],
        [0.5, 0.5, 0.0, 0.1],
        [0.5, 0.5, 0.1, 0.0],
    ])
    edges, n_internal = phylo.neighbor_joining(D)
    assert n_internal == 2  # an unrooted 4-leaf tree has n-2 internal nodes

    adj = _neighbors(edges)
    internal = [u for u in adj if u >= 4]
    assert any({0, 1} <= adj[u] for u in internal), "A,B should share an internal parent"
    assert any({2, 3} <= adj[u] for u in internal), "C,D should share an internal parent"
    assert all(w >= 0.0 for _, _, w in edges)


def test_neighbor_joining_base_cases() -> None:
    assert phylo.neighbor_joining(np.zeros((1, 1))) == ([], 0)
    edges, n_internal = phylo.neighbor_joining(np.array([[0.0, 0.4], [0.4, 0.0]]))
    assert edges == [(0, 1, 0.4)] and n_internal == 0


def test_neighbor_joining_is_deterministic() -> None:
    D = np.array([
        [0.0, 0.3, 0.7, 0.6],
        [0.3, 0.0, 0.5, 0.4],
        [0.7, 0.5, 0.0, 0.2],
        [0.6, 0.4, 0.2, 0.0],
    ])
    assert phylo.neighbor_joining(D) == phylo.neighbor_joining(D)


def test_root_tree_orientation() -> None:
    # unrooted: 4—0, 4—1, 4—5, 5—2, 5—3   (two cherries joined by an internal edge)
    edges = [(4, 0, 1.0), (4, 1, 1.0), (4, 5, 0.5), (5, 2, 1.0), (5, 3, 1.0)]
    children, parent, branch = phylo.root_tree(edges, root=0)

    assert parent[0] is None and branch[0] == 0.0
    assert parent[4] == 0  # the internal node hangs below the chosen leaf root
    assert set(children[4]) == {1, 5}
    assert set(children[5]) == {2, 3}
    assert branch[4] == 1.0 and branch[5] == 0.5
