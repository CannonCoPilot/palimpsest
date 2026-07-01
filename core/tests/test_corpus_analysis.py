"""Collections tier C6a — pure corpus-analysis leaf (IDF/BM25, near-duplicate clustering, spread).

These test the dependency-free numeric leaf in isolation (no graph, no I/O); the assembler that reads
member texts + the corpus graph and calls in here is covered in test_corpus_graph.py."""
from __future__ import annotations

from palimpsest.analysis import corpus_analysis as ca


def test_corpus_idf_downweights_ubiquitous_terms() -> None:
    sets = [{"the", "jesus", "saith"}, {"the", "jesus", "said"}, {"the", "christ"}]
    idf = ca.corpus_idf(sets)
    # in all 3 → floor; in 2 → higher; in 1 → highest.
    assert idf["the"] < idf["jesus"] < idf["christ"]
    assert idf["the"] == 1.0  # ln((3+1)/(3+1)) + 1


def test_boilerplate_terms_are_the_shared_by_all() -> None:
    sets = [{"the", "a", "x"}, {"the", "a", "y"}, {"the", "z"}]
    assert ca.boilerplate_terms(sets) == ["the"]  # only "the" is in every member
    # min_members=2 widens to terms in >=2 members (df desc, then alpha).
    assert ca.boilerplate_terms(sets, min_members=2) == ["the", "a"]
    assert ca.boilerplate_terms([]) == []


def test_bm25_rewards_rare_query_terms() -> None:
    sets = [{"the", "jesus"}, {"the", "jesus"}, {"the", "christ"}]
    idf = ca.corpus_idf(sets)
    counts = [{"the": 5, "jesus": 1}, {"the": 4, "jesus": 1}, {"the": 2, "christ": 3}]
    # querying a discriminative term ranks its member top; the boilerplate term barely moves scores.
    disc = ca.bm25_scores(["christ"], counts, idf)
    assert disc[2] > disc[0] and disc[2] > disc[1]
    boiler = ca.bm25_scores(["the"], counts, idf)
    assert max(boiler) < disc[2]


def test_single_linkage_clusters_group_near_duplicates() -> None:
    # 0 and 1 are near (0.05); 2 is far. Transitive linkage.
    D = [[0.0, 0.05, 0.9], [0.05, 0.0, 0.85], [0.9, 0.85, 0.0]]
    assert ca.single_linkage_clusters(D, 0.1) == [[0, 1], [2]]
    # a tighter threshold separates everyone.
    assert ca.single_linkage_clusters(D, 0.01) == [[0], [1], [2]]
    # a loose threshold merges all.
    assert ca.single_linkage_clusters(D, 0.95) == [[0, 1, 2]]


def test_component_spread_and_member_reach() -> None:
    # core (all 3), a singleton of member 0, a shell of members 1&2.
    comps = [[0, 1, 2], [0], [1, 2]]
    assert ca.component_spread(3, comps) == [1.0, 1 / 3, 2 / 3]
    reach = ca.member_reach(3, comps)
    # member 0: mean(core=1, singleton=1/3) = 2/3; members 1,2: mean(core=1, shell=2/3) = 5/6.
    assert abs(reach[0] - 2 / 3) < 1e-9
    assert abs(reach[1] - 5 / 6) < 1e-9 and abs(reach[2] - 5 / 6) < 1e-9


def test_spread_reach_handle_empty() -> None:
    assert ca.component_spread(0, []) == []
    assert ca.member_reach(2, []) == [0.0, 0.0]
