"""Recall dial — the pure candidate-generation leaf (C6c, FR-35).

These exercise the dial arithmetic directly: exhaustive vs candidate-generated planning, the two
generators (embedding over-fetch ANN, token MinHash-LSH), their recall oracles, and the honest
summary (never a silent cap). All deterministic — no I/O, no service.
"""
from __future__ import annotations

import numpy as np
import pytest

from palimpsest.analysis import candidate_gen as cg


# ── plan_sweep: the dial + escape hatch ───────────────────────────────────────────────────────────

def test_plan_small_space_is_auto_dense() -> None:
    plan = cg.plan_sweep(10, 10, "high-recall", dense_threshold=1000)
    assert plan["dense"] and plan["mode"] == "exhaustive"
    assert plan["auto_dense"] is True  # dial asked to prune, but the space was small — reported, not silent


def test_plan_large_space_prunes() -> None:
    plan = cg.plan_sweep(500, 500, "high-recall", dense_threshold=1000)
    assert not plan["dense"] and plan["mode"] == "high-recall"
    assert plan["depth"] == 20 and plan["bands"] == 32


def test_force_exhaustive_overrides_mode_and_size() -> None:
    plan = cg.plan_sweep(500, 500, "fast", force_exhaustive=True, dense_threshold=1)
    assert plan["dense"] and plan["mode"] == "exhaustive" and plan["forced_exhaustive"] is True


def test_plan_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="mode must be"):
        cg.plan_sweep(10, 10, "turbo")


def test_exhaustive_pairs_is_full_product() -> None:
    assert len(cg.exhaustive_pairs(3, 4)) == 12


# ── embedding generator: over-fetch ANN ───────────────────────────────────────────────────────────

def _vecs(rows: list[list[float]]) -> np.ndarray:
    return np.array(rows, dtype=np.float32)


def test_ann_recovers_nearest_and_is_deterministic() -> None:
    a = _vecs([[1, 0, 0], [0, 1, 0]])
    b = _vecs([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    pairs = cg.ann_candidate_pairs(a, b, depth=1)
    assert pairs == cg.ann_candidate_pairs(a, b, depth=1)  # deterministic
    assert (0, 0) in pairs and (1, 1) in pairs  # each row's true nearest is present


def test_ann_depth_ge_nb_is_exhaustive() -> None:
    a = _vecs([[1, 0], [0, 1]])
    b = _vecs([[1, 0], [0, 1], [1, 1]])
    assert len(cg.ann_candidate_pairs(a, b, depth=3)) == 6  # depth >= n_b → all pairs


# ── token generator: MinHash-LSH ──────────────────────────────────────────────────────────────────

def test_lsh_identical_shingles_collide() -> None:
    shingles = [{1, 2, 3}, {1, 2, 3}, {90, 91, 92}]
    sigs = cg.minhash_signatures(shingles, num_perm=32)
    assert np.array_equal(sigs, cg.minhash_signatures(shingles, num_perm=32))  # deterministic
    pairs = cg.lsh_candidate_pairs(sigs, sigs, bands=16)
    assert (0, 1) in pairs and (1, 0) in pairs  # the identical pair collides
    assert (0, 2) not in pairs  # the disjoint one does not


def test_lsh_more_bands_more_candidates() -> None:
    # Overlapping-but-not-identical sets: looser (more) bands should recover at least as many pairs.
    a = [{1, 2, 3, 4}, {5, 6, 7, 8}]
    b = [{1, 2, 3, 9}, {5, 6, 10, 11}]
    sa, sb = cg.minhash_signatures(a, 64), cg.minhash_signatures(b, 64)
    loose = len(cg.lsh_candidate_pairs(sa, sb, bands=32))
    tight = len(cg.lsh_candidate_pairs(sa, sb, bands=4))
    assert loose >= tight


# ── recall oracles + honest summary ───────────────────────────────────────────────────────────────

def test_cosine_oracle_picks_true_nearest() -> None:
    a = _vecs([[1, 0, 0]])
    b = _vecs([[1, 0, 0], [0, 1, 0]])
    oracle = cg.exact_top_pairs_cosine(a, b, sample_stride=1, top_n=1)
    assert oracle == {(0, 0)}


def test_summary_dense_is_full_recall_no_prune() -> None:
    s = cg.summarize_candidates(4, 4, [], None, dense=True)
    assert s["estimated_recall"] == 1.0 and s["n_pruned"] == 0 and s["n_candidates"] == 16


def test_summary_reports_prune_and_measured_recall() -> None:
    # candidates cover the oracle fully → recall 1.0, but pruning is still reported (never silent).
    oracle = {(0, 0), (1, 1)}
    cands = [(0, 0), (1, 1), (0, 1)]
    s = cg.summarize_candidates(3, 3, cands, oracle, dense=False)
    assert s["n_pruned"] == 9 - 3 and s["estimated_recall"] == 1.0 and s["recall_sample_size"] == 2


def test_summary_partial_recall_is_measured_not_guessed() -> None:
    oracle = {(0, 0), (1, 1)}
    cands = [(0, 0)]  # misses (1, 1)
    s = cg.summarize_candidates(3, 3, cands, oracle, dense=False)
    assert s["estimated_recall"] == 0.5


def test_summary_no_oracle_is_null_recall_not_fabricated() -> None:
    s = cg.summarize_candidates(2, 2, [], set(), dense=False)
    assert s["estimated_recall"] is None  # honest: no sample → no number, not a fake 1.0
