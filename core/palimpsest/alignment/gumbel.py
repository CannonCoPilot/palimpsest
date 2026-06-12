"""Gumbel extreme-value significance testing for alignment scores.

Fits alignment scores from random shuffles to a Gumbel distribution,
then computes p-values for observed alignment scores. This follows
the GNAT methodology (Pial & Skiena 2023).
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def calibrate_gumbel(
    similarity_matrix: np.ndarray,
    n_shuffles: int = 100,
    gap_open: float = -2.0,
    gap_extend: float = -0.5,
) -> tuple[float, float]:
    """Fit Gumbel parameters from shuffled alignment scores.

    Shuffles one dimension of the similarity matrix n_shuffles times,
    computes the optimal local alignment score for each shuffle,
    and fits Gumbel(mu, beta) to the resulting score distribution.

    Returns (mu, beta) — the location and scale parameters.
    """
    n, m = similarity_matrix.shape
    if n < 3 or m < 3:
        return (0.0, 1.0)

    rng = np.random.default_rng(42)
    scores: list[float] = []

    for _ in range(n_shuffles):
        perm = rng.permutation(n)
        shuffled = similarity_matrix[perm, :]
        max_score = _quick_sw_max_score(shuffled, gap_open, gap_extend)
        scores.append(max_score)

    scores_arr = np.array(scores)

    if scores_arr.std() < 1e-10:
        return (float(scores_arr.mean()), 1.0)

    # Method of moments for Gumbel distribution
    beta = scores_arr.std() * np.sqrt(6) / np.pi
    mu = float(scores_arr.mean()) - 0.5772 * beta

    logger.info("Gumbel fit: mu=%.3f, beta=%.3f (from %d shuffles)", mu, beta, n_shuffles)
    return (float(mu), float(beta))


def p_value(score: float, mu: float, beta: float) -> float:
    """Compute Gumbel p-value for an alignment score.

    Returns P(X >= score) under the fitted Gumbel distribution.
    Lower p-values indicate more significant alignments.
    """
    if beta <= 0:
        return 1.0
    z = (score - mu) / beta
    # Clamp to avoid overflow
    z = min(z, 700)
    return float(1.0 - np.exp(-np.exp(-z)))


def _quick_sw_max_score(
    matrix: np.ndarray,
    gap_open: float,
    gap_extend: float,
) -> float:
    """Fast Smith-Waterman that only returns the max score (no traceback).

    Optimized for the calibration loop — skips traceback and record extraction.
    """
    n, m = matrix.shape
    H_prev = np.zeros(m + 1, dtype=np.float64)
    E_prev = np.full(m + 1, -np.inf, dtype=np.float64)
    max_score = 0.0

    for i in range(1, n + 1):
        H_curr = np.zeros(m + 1, dtype=np.float64)
        E_curr = np.full(m + 1, -np.inf, dtype=np.float64)
        F_val = -np.inf

        for j in range(1, m + 1):
            sim = float(matrix[i - 1, j - 1])
            score = sim * 2.0 - 1.0

            E_curr[j] = max(H_curr[j - 1] + gap_open, E_curr[j - 1] + gap_extend)
            F_val = max(H_prev[j] + gap_open, F_val + gap_extend)

            best = max(0.0, H_prev[j - 1] + score, E_curr[j], F_val)
            H_curr[j] = best
            if best > max_score:
                max_score = best

        H_prev = H_curr
        E_prev = E_curr

    return max_score
