"""candidate_gen — the recall dial (C6c, FR-35): candidate-set generation for an O(N×M) sweep.

Pure numeric leaf (sibling to ``textstats`` / ``phylo`` / ``chunk_stats`` / ``corpus_analysis``): no
I/O, no ``Project``/graph import. The caller reduces members to primitive inputs (embedding vectors, or
token-shingle sets), calls in here, and labels the result.

The dial trades recall for cost on the **expensive** per-pair step (exact alignment + Gumbel
significance): cheap candidate generation proposes which ``(i, j)`` chunk pairs are worth scoring
exactly; everything else is pruned. Every result reports ``n_total / n_candidates / n_pruned`` and an
**empirical** estimated recall measured on a sample — never a silent cap, never a theoretical
hand-wave. A forced-exhaustive escape overrides the dial at any size, and small sweeps
(``<= dense_threshold`` pairs) default to exhaustive since there is no signal to miss where it is cheap.

Two generators, one per metric family (chosen by the caller):

  * **embeddings → ANN over-fetch.** Each row's top-``depth`` nearest by cosine, unioned across rows;
    ``depth`` is the recall knob. A larger depth recovers more true-near pairs at more candidates.
  * **tokens / alignment → MinHash-LSH.** Banded LSH over shingle sets; the band count is the recall
    knob (more bands → looser buckets → higher recall, more candidates). This is the family that runs on
    a word-method corpus with no embeddings.

A true ANN *index* (HNSW ``efSearch`` / IVF ``nprobe``) is the scale path when even the O(N×M) cosine
matmul is too large; the numpy over-fetch here gives the dial *semantics* without a new index
dependency, matching C6c's lightweight-now / full-later discipline.
"""
from __future__ import annotations

import numpy as np

RECALL_MODES = ("exhaustive", "high-recall", "fast")
DENSE_PAIR_THRESHOLD = 10_000  # ≤ this many pairs → exhaustive by default (cheap, no missed signal)

# Over-fetch depth (embeddings) / band count (tokens) per mode. Higher = more recall, more candidates.
_MODE_DEPTH = {"high-recall": 20, "fast": 5}
_MODE_BANDS = {"high-recall": 32, "fast": 8}
_MERSENNE = (1 << 61) - 1  # a large prime for universal hashing


def plan_sweep(
    n_a: int,
    n_b: int,
    mode: str = "exhaustive",
    *,
    force_exhaustive: bool = False,
    dense_threshold: int = DENSE_PAIR_THRESHOLD,
) -> dict:
    """Decide how to sweep an ``n_a × n_b`` pair space. Returns the resolved plan.

    ``force_exhaustive`` or ``mode == "exhaustive"`` or a small space (``<= dense_threshold``) resolves
    to a dense/exhaustive sweep (``estimated_recall`` will be 1.0). ``auto_dense`` flags when the dial
    *asked* for candidate generation but the space was small enough to stay exhaustive — reported so the
    user is never surprised that pruning "did nothing"."""
    if mode not in RECALL_MODES:
        raise ValueError(f"mode must be one of {RECALL_MODES}, got {mode!r}")
    total = int(n_a) * int(n_b)
    small = total <= dense_threshold
    dense = force_exhaustive or mode == "exhaustive" or small
    return {
        "mode": "exhaustive" if dense else mode,
        "requested_mode": mode,
        "n_pairs_total": total,
        "dense": dense,
        "forced_exhaustive": force_exhaustive,
        "auto_dense": bool(small and mode != "exhaustive" and not force_exhaustive),
        "depth": None if dense else _MODE_DEPTH[mode],
        "bands": None if dense else _MODE_BANDS[mode],
        "dense_threshold": dense_threshold,
    }


def exhaustive_pairs(n_a: int, n_b: int) -> list[tuple[int, int]]:
    """Every ``(i, j)`` pair — the dense sweep, recall 1.0 by construction."""
    return [(i, j) for i in range(n_a) for j in range(n_b)]


# ── embedding candidate generator: over-fetch ANN ─────────────────────────────────────────────────

def _unit_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1.0, norms)


def ann_candidate_pairs(
    vectors_a: np.ndarray, vectors_b: np.ndarray, depth: int
) -> list[tuple[int, int]]:
    """For each row *i* of A, its ``depth`` nearest rows *j* of B by cosine similarity; unioned over *i*.

    Deterministic (``argpartition`` + stable sort). Returns sorted unique pairs. ``depth >= n_b`` yields
    the full space (every j per i) — i.e. exhaustive, so the dial degrades gracefully."""
    if vectors_a.size == 0 or vectors_b.size == 0:
        return []
    ua, ub = _unit_rows(vectors_a), _unit_rows(vectors_b)
    sims = ua @ ub.T  # (n_a, n_b) cosine similarities
    n_b = sims.shape[1]
    d = min(depth, n_b)
    # top-d columns per row (unordered by argpartition, fine — we only need the SET)
    top = np.argpartition(-sims, d - 1, axis=1)[:, :d]
    pairs = {(int(i), int(j)) for i, row in enumerate(top) for j in row}
    return sorted(pairs)


# ── token candidate generator: MinHash-LSH over shingle sets ──────────────────────────────────────

def minhash_signatures(shingle_sets: list[set[int]], num_perm: int, seed: int = 0) -> np.ndarray:
    """MinHash signatures ``(n, num_perm)`` for integer shingle sets under seeded universal hashing.

    Deterministic in ``seed`` (a fixed seed is *passed in*, never drawn — this leaf has no hidden RNG
    state). An empty shingle set gets a max-value signature so it collides with nothing."""
    rng = np.random.default_rng(seed)
    a = rng.integers(1, _MERSENNE, size=num_perm, dtype=np.uint64)
    b = rng.integers(0, _MERSENNE, size=num_perm, dtype=np.uint64)
    sigs = np.full((len(shingle_sets), num_perm), np.iinfo(np.uint64).max, dtype=np.uint64)
    for i, shingles in enumerate(shingle_sets):
        if not shingles:
            continue
        x = np.fromiter((s % _MERSENNE for s in shingles), dtype=np.uint64)
        hashed = (a[None, :] * x[:, None] + b[None, :]) % _MERSENNE  # (|shingles|, num_perm)
        sigs[i] = hashed.min(axis=0)
    return sigs


def lsh_candidate_pairs(
    sig_a: np.ndarray, sig_b: np.ndarray, bands: int
) -> list[tuple[int, int]]:
    """Candidate ``(i, j)`` pairs whose MinHash signatures collide in at least one LSH band.

    The signature is split into ``bands`` bands of ``num_perm // bands`` rows; A-items and B-items whose
    band sub-signatures are identical bucket together. More bands → looser buckets → higher recall (and
    more candidates): the recall knob. Deterministic."""
    if sig_a.size == 0 or sig_b.size == 0:
        return []
    num_perm = sig_a.shape[1]
    bands = max(1, min(bands, num_perm))
    rows = num_perm // bands
    pairs: set[tuple[int, int]] = set()
    for band in range(bands):
        lo = band * rows
        hi = lo + rows
        buckets: dict[bytes, list[int]] = {}
        for i in range(sig_a.shape[0]):
            buckets.setdefault(sig_a[i, lo:hi].tobytes(), []).append(i)
        for j in range(sig_b.shape[0]):
            key = sig_b[j, lo:hi].tobytes()
            for i in buckets.get(key, ()):
                pairs.add((i, j))
    return sorted(pairs)


# ── honest empirical recall on a sample ───────────────────────────────────────────────────────────

def _sample_rows(n: int, stride: int) -> list[int]:
    stride = max(1, stride)
    return list(range(0, n, stride))


def exact_top_pairs_cosine(
    vectors_a: np.ndarray, vectors_b: np.ndarray, *, sample_stride: int, top_n: int
) -> set[tuple[int, int]]:
    """The true top-``top_n`` B-neighbors (by cosine) of a strided sample of A-rows — the recall oracle
    for :func:`ann_candidate_pairs`."""
    if vectors_a.size == 0 or vectors_b.size == 0:
        return set()
    ua, ub = _unit_rows(vectors_a), _unit_rows(vectors_b)
    out: set[tuple[int, int]] = set()
    n_b = ub.shape[0]
    t = min(top_n, n_b)
    for i in _sample_rows(ua.shape[0], sample_stride):
        sims = ua[i] @ ub.T
        for j in np.argpartition(-sims, t - 1)[:t]:
            out.add((i, int(j)))
    return out


def exact_top_pairs_jaccard(
    shingle_a: list[set[int]], shingle_b: list[set[int]], *, sample_stride: int, top_n: int
) -> set[tuple[int, int]]:
    """The true top-``top_n`` B-neighbors (by Jaccard) of a strided sample of A-rows — the recall oracle
    for :func:`lsh_candidate_pairs`."""
    out: set[tuple[int, int]] = set()
    for i in _sample_rows(len(shingle_a), sample_stride):
        sa = shingle_a[i]
        scored = []
        for j, sb in enumerate(shingle_b):
            union = len(sa | sb)
            scored.append((len(sa & sb) / union if union else 0.0, j))
        scored.sort(key=lambda kv: (-kv[0], kv[1]))
        for _, j in scored[:top_n]:
            out.add((i, j))
    return out


def summarize_candidates(
    n_a: int,
    n_b: int,
    candidate_pairs: list[tuple[int, int]],
    oracle_pairs: set[tuple[int, int]] | None,
    *,
    dense: bool,
    recall_exact_by_construction: bool = False,
) -> dict:
    """The honest sweep report: totals, prune counts, and an empirical estimated recall.

    ``estimated_recall`` is ``|oracle ∩ candidates| / |oracle|`` on the sampled oracle — a measured
    fraction, reported with its sample size. A dense sweep is 1.0 by construction. ``n_pruned`` is what
    the dial removed from the exhaustive space — reported so a cap is never silent.

    ``recall_basis`` qualifies what that number is worth, because not every 1.0 is earned:
      - ``dense``               — no pruning, recall is 1.0 trivially.
      - ``exact_by_construction`` — candidate-gen and the oracle rank by the *same* metric with
        over-fetch depth ≥ the oracle's top-N (the embedding/ANN family). The candidates then contain
        the oracle by construction, so recall is forced to 1.0 and measures nothing. Pass
        ``recall_exact_by_construction=True`` for these so a reader never mistakes the tautology for
        evidence the ANN dial is safe.
      - ``measured``            — candidate-gen approximates a *different* oracle (token MinHash-LSH vs
        exact Jaccard); the fraction is a genuine empirical recall.
      - ``unmeasured``          — no oracle sample was drawn (e.g. empty operands)."""
    total = int(n_a) * int(n_b)
    n_cand = total if dense else len(candidate_pairs)
    if dense:
        recall: float | None = 1.0
        oracle_size = 0
        recall_basis = "dense"
    elif oracle_pairs:
        cand_set = set(candidate_pairs)
        recovered = sum(1 for p in oracle_pairs if p in cand_set)
        recall = round(recovered / len(oracle_pairs), 4)
        oracle_size = len(oracle_pairs)
        recall_basis = "exact_by_construction" if recall_exact_by_construction else "measured"
    else:
        recall = None  # no oracle sample (e.g. empty operands) — honest null, not a fabricated 1.0
        oracle_size = 0
        recall_basis = "unmeasured"
    return {
        "n_pairs_total": total,
        "n_candidates": n_cand,
        "n_pruned": total - n_cand,
        "prune_fraction": round((total - n_cand) / total, 4) if total else 0.0,
        "estimated_recall": recall,
        "recall_sample_size": oracle_size,
        "recall_basis": recall_basis,
        "dense": dense,
    }
