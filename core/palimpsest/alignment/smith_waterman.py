"""Smith-Waterman local alignment on pre-computed similarity matrices.

Implements the GNAT methodology (Pial & Skiena 2023): local alignment with
affine gap penalties on semantic similarity scores. Produces AlignmentRecord
objects for each significant local alignment found.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from palimpsest.alignment.records import AlignmentRecord

logger = logging.getLogger(__name__)


def smith_waterman(
    similarity_matrix: np.ndarray,
    query_id: str,
    target_id: str,
    method: str = "semantic",
    gap_open: float = -2.0,
    gap_extend: float = -0.5,
    score_threshold: float = 0.0,
    min_length: int = 2,
) -> list[AlignmentRecord]:
    """Smith-Waterman local alignment on a pre-computed NxM similarity matrix.

    Uses affine gap penalties. Returns all non-overlapping local alignments
    above score_threshold, sorted by score descending.

    Args:
        similarity_matrix: NxM matrix where [i,j] = similarity between
            paragraph i of query and paragraph j of target.
        query_id: Project ID of the query (rows).
        target_id: Project ID of the target (columns).
        method: Alignment method name for records.
        gap_open: Penalty for opening a gap (negative).
        gap_extend: Penalty for extending a gap (negative).
        score_threshold: Minimum alignment score to report.
        min_length: Minimum alignment length (in paragraphs).
    """
    n, m = similarity_matrix.shape
    if n == 0 or m == 0:
        return []

    # DP matrices: H = match/mismatch, E = gap in query (horizontal), F = gap in target (vertical)
    H = np.zeros((n + 1, m + 1), dtype=np.float64)
    E = np.full((n + 1, m + 1), -np.inf, dtype=np.float64)
    F = np.full((n + 1, m + 1), -np.inf, dtype=np.float64)

    # Traceback direction: 0=stop, 1=diagonal, 2=left(E), 3=up(F)
    trace = np.zeros((n + 1, m + 1), dtype=np.int8)

    # Fill DP
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            # Score for aligning paragraph i-1 with j-1
            sim = float(similarity_matrix[i - 1, j - 1])
            score = sim * 2.0 - 1.0  # Map [0,1] similarity to [-1,1] score range

            E[i, j] = max(H[i, j - 1] + gap_open, E[i, j - 1] + gap_extend)
            F[i, j] = max(H[i - 1, j] + gap_open, F[i - 1, j] + gap_extend)

            diag = H[i - 1, j - 1] + score
            best = max(0.0, diag, E[i, j], F[i, j])
            H[i, j] = best

            if best == 0.0:
                trace[i, j] = 0
            elif best == diag:
                trace[i, j] = 1
            elif best == E[i, j]:
                trace[i, j] = 2
            else:
                trace[i, j] = 3

    # Extract all local alignments by repeated traceback from highest scoring cells
    records: list[AlignmentRecord] = []
    used = np.zeros((n + 1, m + 1), dtype=bool)

    for _ in range(min(100, n * m)):
        # Find highest unused cell
        masked_H = np.where(used, 0.0, H)
        max_score = float(masked_H.max())
        if max_score <= score_threshold:
            break

        max_pos = np.unravel_index(masked_H.argmax(), H.shape)
        i, j = int(max_pos[0]), int(max_pos[1])

        # Traceback
        query_end = i
        target_end = j
        aligned_pairs: list[tuple[int, int]] = []

        while i > 0 and j > 0 and H[i, j] > 0 and trace[i, j] != 0:
            used[i, j] = True
            if trace[i, j] == 1:  # diagonal
                aligned_pairs.append((i - 1, j - 1))
                i -= 1
                j -= 1
            elif trace[i, j] == 2:  # left (gap in query)
                j -= 1
            else:  # up (gap in target)
                i -= 1

        if len(aligned_pairs) < min_length:
            continue

        aligned_pairs.reverse()  # traceback produces end-to-start; reverse for start-to-end

        query_start = aligned_pairs[0][0]
        target_start = aligned_pairs[0][1]

        # Compute average identity within aligned block
        sims = [float(similarity_matrix[qi, tj]) for qi, tj in aligned_pairs]
        avg_identity = sum(sims) / len(sims) if sims else 0.0

        # Detect strand: forward if target indices increase with query indices
        is_forward = all(
            aligned_pairs[k + 1][1] >= aligned_pairs[k][1]
            for k in range(len(aligned_pairs) - 1)
        )

        records.append(AlignmentRecord(
            query_id=query_id,
            query_start=query_start,
            query_end=query_end,
            target_id=target_id,
            target_start=target_start,
            target_end=target_end,
            score=max_score,
            method=method,
            strand="+" if is_forward else "-",
            identity=avg_identity,
        ))

    records.sort(key=lambda r: r.score, reverse=True)
    logger.info("Found %d alignments (threshold=%.2f)", len(records), score_threshold)
    return records
