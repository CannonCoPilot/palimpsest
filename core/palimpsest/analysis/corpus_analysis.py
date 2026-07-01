"""corpus_analysis — pure numeric/graph leaves for collection-level corpus analyses (C6a).

Sibling to ``textstats`` / ``phylo`` / ``chunk_stats``: no I/O, no ``Project`` or graph import. The
caller (``corpus_graph``) reads member texts + the corpus graph, reduces them to primitive inputs
(token sets/counts, component-membership sets, the member-distance matrix), calls in here, and labels
the result.

Three families, each honest about the reference-free (undirected) corpus model:

  - **corpus IDF / BM25** — down-weight cross-member boilerplate. A term present in every member
    carries no discriminative signal; IDF is the weight, and the ubiquitous low-IDF terms are the
    reported boilerplate. BM25 ranks members for a query term set with that same down-weighting.
  - **near-duplicate / stemma clustering** — single-linkage groups over the pangenome Jaccard
    distance (the same distance ``phylo`` builds the stemma from); members that share almost all
    homology components collapse into one near-duplicate cluster.
  - **diffusion / spread** — how broadly each homology component reaches across members, and each
    member's reach across the corpus. Undirected on purpose: it measures *spread*, never
    who-copied-whom — the reference-free graph carries no arrow of influence, so any directional
    ("A influenced B") claim would be dishonest and is not offered here.
"""
from __future__ import annotations

import math


# ── corpus IDF / BM25 (boilerplate down-weighting) ────────────────────────────────────────────────

def corpus_idf(member_token_sets: list[set[str]]) -> dict[str, float]:
    """Smoothed inverse document frequency over members (document = member).

    ``idf(t) = ln((N + 1) / (df(t) + 1)) + 1`` where ``df`` is the number of members containing the
    term. Smoothing keeps every weight positive; a term in all N members gets the floor weight, a
    term in one member the ceiling. This is the down-weighting signal for cross-member boilerplate."""
    n = len(member_token_sets)
    df: dict[str, int] = {}
    for tokens in member_token_sets:
        for t in tokens:
            df[t] = df.get(t, 0) + 1
    return {t: math.log((n + 1) / (d + 1)) + 1.0 for t, d in df.items()}


def boilerplate_terms(
    member_token_sets: list[set[str]], *, min_members: int | None = None
) -> list[str]:
    """Terms shared by ``min_members`` or more members — the cross-member boilerplate to down-weight.

    Defaults to terms present in *all* members (``min_members = N``), sorted by descending document
    frequency then term for determinism."""
    n = len(member_token_sets)
    if n == 0:
        return []
    threshold = n if min_members is None else min_members
    df: dict[str, int] = {}
    for tokens in member_token_sets:
        for t in tokens:
            df[t] = df.get(t, 0) + 1
    hits = [(t, d) for t, d in df.items() if d >= threshold]
    hits.sort(key=lambda kv: (-kv[1], kv[0]))
    return [t for t, _ in hits]


def bm25_scores(
    query_tokens: list[str],
    member_token_counts: list[dict[str, int]],
    idf: dict[str, float],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """Okapi BM25 relevance of each member to ``query_tokens`` (Robertson & Spärck Jones).

    ``idf`` is supplied (typically ``corpus_idf`` above) so boilerplate query terms contribute little.
    ``member_token_counts`` is one term→count map per member. Returns one score per member, in member
    order; deterministic and dependency-free."""
    lengths = [sum(c.values()) for c in member_token_counts]
    avg_len = (sum(lengths) / len(lengths)) if lengths else 0.0
    scores: list[float] = []
    for counts, length in zip(member_token_counts, lengths):
        s = 0.0
        denom_len = (1 - b + b * (length / avg_len)) if avg_len > 0 else 1.0
        for t in query_tokens:
            f = counts.get(t, 0)
            if f == 0:
                continue
            s += idf.get(t, 0.0) * (f * (k1 + 1)) / (f + k1 * denom_len)
        scores.append(s)
    return scores


# ── near-duplicate / stemma clustering ────────────────────────────────────────────────────────────

def single_linkage_clusters(distance_matrix: list[list[float]], threshold: float) -> list[list[int]]:
    """Group indices whose pairwise distance is ``<= threshold`` under single linkage (transitive).

    Members that share nearly all homology components sit at ~0 distance and collapse together — the
    near-duplicate clusters (e.g. two editions of one translation). Returns clusters as sorted index
    lists, ordered by their smallest member for determinism. A singleton is its own cluster."""
    n = len(distance_matrix)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if distance_matrix[i][j] <= threshold:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    clusters = [sorted(g) for g in groups.values()]
    clusters.sort(key=lambda g: g[0])
    return clusters


# ── diffusion / spread (undirected — spread, not influence) ───────────────────────────────────────

def component_spread(n_members: int, comp_member_sets: list[list[int]]) -> list[float]:
    """Per-component spread fraction: distinct members reached / total members, in ``[0, 1]``.

    ``1.0`` = a core passage present in every member; ``1/N`` = a singleton. This is the honest
    breadth signal; it says nothing about direction of transmission."""
    if n_members <= 0:
        return [0.0 for _ in comp_member_sets]
    return [len(set(s)) / n_members for s in comp_member_sets]


def member_reach(n_members: int, comp_member_sets: list[list[int]]) -> list[float]:
    """Per-member reach: mean spread of the components a member participates in, in ``[0, 1]``.

    A member whose passages mostly land in widely-shared components has high reach (it holds the
    common backbone); one dominated by singletons has low reach (it is largely idiosyncratic).
    Symmetric by construction — a spread measure, not an influence/direction claim."""
    spreads = component_spread(n_members, comp_member_sets)
    sums = [0.0] * n_members
    counts = [0] * n_members
    for comp_spread, members in zip(spreads, comp_member_sets):
        for i in set(members):
            if 0 <= i < n_members:
                sums[i] += comp_spread
                counts[i] += 1
    return [sums[i] / counts[i] if counts[i] else 0.0 for i in range(n_members)]
