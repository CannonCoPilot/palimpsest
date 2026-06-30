"""chunk_stats — deterministic per-chunk-layer distributions (Wave-0 P6, FR-14).

The distribution data behind a chunk layer's stats panel: length histograms (words & chars),
ECDF arrays, by-element-type length groups (for violins), and the chunk-boundary-vs-structural
alignment breakdown.

A true leaf, like ``textstats``: pure numpy over plain lists, no I/O, no ``Project``/``OffsetMap``/
track import. The caller (the server endpoint) does the I/O and coordinate remap — it loads the
chunk layer's ``segment_offsets`` (analyzable coords), slices the analyzable text to count words,
assigns each chunk an element type from ``layout_sections.json``, and remaps chunk starts to
*original* coordinates so they share a coordinate system with the structural boundaries before
calling in here. That keeps boundary-alignment a same-space comparison rather than a silent
cross-coordinate bug.

Distinct from ``textstats``/ProfileTrack, which describe the whole text: these describe a *chunk
layer* (over its ``segment_offsets``). Tokenization is shared, endpoints are not.
"""

from __future__ import annotations

import numpy as np

from palimpsest.analysis import textstats


def ecdf(values: list[float] | list[int]) -> dict[str, list[float]]:
    """Empirical CDF as parallel ``x``/``y`` arrays: ``x`` the sorted distinct values, ``y`` the
    fraction of observations ``<= x`` (so ``y`` ends at 1.0). Empty input → empty arrays."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return {"x": [], "y": []}
    xs = np.unique(arr)  # sorted, distinct
    # fraction of observations <= each distinct x
    ys = np.searchsorted(np.sort(arr), xs, side="right") / arr.size
    return {"x": xs.tolist(), "y": [round(float(y), 6) for y in ys]}


def _quantile_summary(values: list[float] | list[int]) -> dict[str, float]:
    """Five-number summary + mean + count for a box/violin overlay. Empty → well-defined zeros."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return {"n": 0, "min": 0.0, "q1": 0.0, "median": 0.0, "q3": 0.0, "max": 0.0, "mean": 0.0}
    q1, med, q3 = (round(float(q), 4) for q in np.quantile(arr, [0.25, 0.5, 0.75]))
    return {
        "n": int(arr.size),
        "min": round(float(arr.min()), 4),
        "q1": q1,
        "median": med,
        "q3": q3,
        "max": round(float(arr.max()), 4),
        "mean": round(float(arr.mean()), 4),
    }


def _stride_sample(values: list[int], cap: int) -> tuple[list[int], bool, int]:
    """Even-strided downsample to at most ``cap`` items (deterministic). Returns the (possibly
    sampled) list, a ``sampled`` flag, and the original count — so a cap is reported, never silent."""
    n = len(values)
    if n <= cap:
        return values, False, n
    idx = np.linspace(0, n - 1, cap).round().astype(int)
    return [values[i] for i in idx], True, n


def compute_chunk_layer_stats(
    *,
    char_lengths: list[int],
    word_counts: list[int],
    element_types: list[str],
    chunk_starts: list[int],
    structural_boundaries: list[int],
    bins: int = 30,
    tolerance: int = 0,
    max_violin: int = 2000,
) -> dict[str, object]:
    """Per-chunk-layer distribution payload. All per-chunk lists are parallel and index-aligned
    (``len == n_chunks``). ``chunk_starts`` and ``structural_boundaries`` must already be in the
    *same* coordinate system (the caller remaps).

    - length: word & char histograms (``textstats.histogram``) + ECDFs.
    - by_element_type: word-count groups per element type (raw values for violins, capped with a
      reported sample size, + a five-number summary).
    - boundary_alignment: fraction of chunk starts that coincide (within ``tolerance``) with a
      structural boundary, the converse structural-coverage fraction, and a per-element-type
      breakdown. All fractions are guaranteed in ``[0, 1]``.
    """
    n = len(char_lengths)
    if not (len(word_counts) == len(element_types) == len(chunk_starts) == n):
        raise ValueError("char_lengths, word_counts, element_types, chunk_starts must be parallel")

    length = {
        "words": {"histogram": textstats.histogram(word_counts, bins=bins), "ecdf": ecdf(word_counts)},
        "chars": {"histogram": textstats.histogram(char_lengths, bins=bins), "ecdf": ecdf(char_lengths)},
    }

    # By-element-type word-count groups, ordered by descending group size (stable).
    groups_by_type: dict[str, list[int]] = {}
    for wc, etype in zip(word_counts, element_types):
        groups_by_type.setdefault(etype, []).append(wc)
    groups = []
    for etype, vals in sorted(groups_by_type.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        sampled_vals, sampled, original_n = _stride_sample(vals, max_violin)
        groups.append({
            "type": etype,
            "values": sampled_vals,
            "sampled": sampled,
            "sample_size": len(sampled_vals),
            "original_n": original_n,
            "summary": _quantile_summary(vals),
        })

    # Boundary alignment in shared coordinates.
    bset = np.asarray(sorted(set(structural_boundaries)), dtype=np.int64)
    starts = np.asarray(chunk_starts, dtype=np.int64)

    def _within_tol(points: np.ndarray, targets: np.ndarray) -> np.ndarray:
        """Boolean mask: each point is within ``tolerance`` of some target (nearest-by-insertion)."""
        if points.size == 0 or targets.size == 0:
            return np.zeros(points.shape, dtype=bool)
        pos = np.searchsorted(targets, points)
        left = np.clip(pos - 1, 0, targets.size - 1)
        right = np.clip(pos, 0, targets.size - 1)
        nearest = np.minimum(np.abs(points - targets[left]), np.abs(points - targets[right]))
        return nearest <= tolerance

    chunk_aligned = _within_tol(starts, bset)
    structural_hit = _within_tol(bset, starts)

    # Per-element-type chunk-alignment breakdown.
    by_type_align = []
    type_to_aligned: dict[str, list[bool]] = {}
    for etype, hit in zip(element_types, chunk_aligned.tolist()):
        type_to_aligned.setdefault(etype, []).append(hit)
    for etype, hits in sorted(type_to_aligned.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        total = len(hits)
        aligned = int(sum(hits))
        by_type_align.append({
            "type": etype,
            "n": total,
            "aligned": aligned,
            "fraction": round(aligned / total, 6) if total else 0.0,
        })

    n_aligned = int(chunk_aligned.sum())
    n_struct_hit = int(structural_hit.sum())
    boundary_alignment = {
        "tolerance": tolerance,
        "n_chunk_boundaries": int(starts.size),
        "n_aligned": n_aligned,
        "fraction_aligned": round(n_aligned / starts.size, 6) if starts.size else 0.0,
        "n_structural_boundaries": int(bset.size),
        "n_structural_hit": n_struct_hit,
        "fraction_structural_hit": round(n_struct_hit / bset.size, 6) if bset.size else 0.0,
        "by_type": by_type_align,
    }

    return {
        "n_chunks": n,
        "length": length,
        "by_element_type": {"metric": "words", "groups": groups},
        "boundary_alignment": boundary_alignment,
    }
