"""Smith-Waterman local alignment on pre-computed similarity matrices.

Implements the GNAT methodology (Pial & Skiena 2023): local alignment with
affine gap penalties on semantic similarity scores. Produces AlignmentRecord
objects for each significant local alignment found.
"""

from __future__ import annotations

import logging

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
    max_alignments: int | None = None,
) -> list[AlignmentRecord]:
    """Smith-Waterman local alignment on a pre-computed NxM similarity matrix.

    Uses affine gap penalties. Returns non-overlapping local alignments above
    ``score_threshold``, sorted by score descending. "Non-overlapping" is enforced
    in cell space (Waterman-Eggert style): each accepted alignment consumes its
    traceback path, and a later candidate that overlaps an accepted alignment on
    *both* the query and target axes (a shifted diagonal or trailing-mismatch
    extension of the same block) is rejected rather than re-reported. A genuine
    repeat — one query range aligning to several target ranges — overlaps on only
    one axis and survives.

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
        max_alignments: Optional ceiling on the number of alignments returned.
            ``None`` (default) extracts exhaustively until no cell scores above
            threshold — no silent cap. If a positive limit is hit while signal
            remains above threshold, the truncation is logged at WARNING (never
            silent); raise the limit for exhaustive extraction.
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

    # Extract non-overlapping local alignments by repeated traceback from the highest-scoring
    # cell. Each accepted alignment consumes its traceback path (used[i,j]); traceback also stops
    # at any already-consumed cell, so accepted alignments never share cells. A candidate whose
    # paragraph ranges overlap an accepted alignment on BOTH axes (a shifted-diagonal duplicate or
    # a trailing-mismatch extension of the same block) is rejected — the previous silent
    # ``min(100, n*m)`` cap masked exactly this by hiding the flood of near-duplicates.
    records: list[AlignmentRecord] = []
    used = np.zeros((n + 1, m + 1), dtype=bool)
    overlap_tol = 0.5  # reject if overlap exceeds this fraction on BOTH axes vs. an accepted record

    def _is_duplicate(qs: int, qe: int, ts: int, te: int) -> bool:
        for r in records:
            q_ov = max(0, min(qe, r.query_end) - max(qs, r.query_start))
            t_ov = max(0, min(te, r.target_end) - max(ts, r.target_start))
            if q_ov <= 0 or t_ov <= 0:
                continue  # disjoint on an axis → distinct block (e.g. a repeat) → keep
            q_frac = q_ov / max(1, min(qe - qs, r.query_end - r.query_start))
            t_frac = t_ov / max(1, min(te - ts, r.target_end - r.target_start))
            if q_frac > overlap_tol and t_frac > overlap_tol:
                return True
        return False

    # Candidate endpoint cells, highest H first. H is fixed after the DP fill, so the above-threshold
    # cells are sorted ONCE and walked in order, skipping any consumed by an earlier traceback — far
    # cheaper than re-scanning the whole matrix for the argmax on every extraction. Ties break by
    # ascending flat index (stable sort) so the result is deterministic.
    flat = H.ravel()
    cand = np.where(flat > score_threshold)[0]
    cand = cand[np.argsort(-flat[cand], kind="stable")]
    width = m + 1

    truncated = False
    for flat_idx in cand:
        if max_alignments is not None and len(records) >= max_alignments:
            truncated = True  # candidate cells above threshold remain unexamined
            break

        i = int(flat_idx) // width
        j = int(flat_idx) % width
        if used[i, j]:
            continue

        max_score = float(H[i, j])
        query_end = i
        target_end = j
        aligned_pairs: list[tuple[int, int]] = []

        # Traceback; stop at cells already consumed so accepted alignments stay cell-disjoint.
        while i > 0 and j > 0 and H[i, j] > 0 and trace[i, j] != 0 and not used[i, j]:
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

        # Half-open paragraph ranges are [start, end); reject shifted/trailing duplicates.
        if _is_duplicate(query_start, query_end, target_start, target_end):
            continue

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
    if truncated:
        logger.warning(
            "smith_waterman: stopped at max_alignments=%d with signal still above "
            "threshold=%.3f — raise max_alignments for exhaustive extraction (not a silent cap)",
            max_alignments, score_threshold,
        )
    logger.info("Found %d alignments (threshold=%.2f)", len(records), score_threshold)
    return records
