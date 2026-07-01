"""Liftover — project features across an A↔B alignment into the other text's coordinate frame.

Genomic ``liftOver`` takes an interval on one assembly and re-expresses it on another via a chain of
aligned blocks. C5 does the same for texts: given a stored pairwise alignment (paragraph-indexed
correspondence blocks) and each member's per-paragraph character spans, an :class:`AlignmentMap`
projects a source-frame character interval onto the destination frame — so a mask, annotation, or
score-track computed on A can be re-anchored on B as a new *additive* version (FR-42, principles §4.1).

**Why not reuse ``OffsetMap``.** ``OffsetMap`` (derive.py) models the *excision of one text* — a child
assembled from kept spans of a single parent. An alignment is a *correspondence between two independent
texts*; the destination is not a subset of the source. Forcing one text's excision map onto a
cross-text projection would be a leaky abstraction, so this is a purpose-built map. It obeys the same
principle §4 discipline (offsets are remapped operand→operand explicitly, out-of-block content is
reported, never silently passed through) — one additional remap target, as the design doc directs.

**Granularity is honest.** Alignment records correspond *paragraph blocks*, not characters — the
character-level correspondence inside a block is unknown. So a source interval is projected to the
*corresponding destination block(s)* it overlaps, not to an interpolated sub-span. Mapping to the
corresponding paragraph region is correct at the alignment's actual granularity; linear interpolation
within a block would smuggle in an unstated uniform-char-rate assumption.
"""

from __future__ import annotations

from dataclasses import dataclass

from .records import AlignmentRecord

Span = tuple[int, int]


def _merge_spans(spans: list[Span]) -> list[Span]:
    """Sort and union overlapping/adjacent half-open spans."""
    ordered = sorted(s for s in spans if s[1] > s[0])
    if not ordered:
        return []
    merged: list[Span] = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _block_char_span(para_spans: list[Span], p_start: int, p_end: int) -> Span | None:
    """Character span covering paragraphs ``[p_start, p_end)`` (exclusive end), or None if out of range.

    Clamps the exclusive end to the paragraph count so a record running one past the last paragraph
    still yields its covered region rather than being dropped."""
    n = len(para_spans)
    if n == 0 or p_start < 0 or p_start >= n or p_end <= p_start:
        return None
    last = min(p_end, n) - 1
    return (para_spans[p_start][0], para_spans[last][1])


@dataclass(frozen=True)
class Block:
    """One aligned correspondence block, in character coordinates on each side."""

    src_start: int
    src_end: int
    dst_start: int
    dst_end: int


class AlignmentMap:
    """A piecewise character-coordinate correspondence between a source and destination text.

    Built from paragraph-indexed :class:`AlignmentRecord` blocks plus each side's per-paragraph
    character spans. Direction is chosen at construction (``source="query"`` maps the record's query
    text onto its target text; ``"target"`` the reverse), so the caller lifts *from* whichever member
    owns the features *onto* the other.
    """

    def __init__(self, blocks: list[Block]) -> None:
        # Sorted by source start so projection can scan and so ``src_covered`` is well defined.
        self.blocks: list[Block] = sorted(blocks, key=lambda b: (b.src_start, b.src_end))

    @classmethod
    def from_records(
        cls,
        records: list[AlignmentRecord],
        src_para_spans: list[Span],
        dst_para_spans: list[Span],
        *,
        source: str = "query",
    ) -> "AlignmentMap":
        """Assemble a map from alignment records and the two texts' per-paragraph char spans.

        ``source`` selects which record axis is the source frame: ``"query"`` lifts query→target,
        ``"target"`` lifts target→query. Records whose paragraph ranges fall outside either text's
        paragraph count are skipped (malformed/stale), not silently mis-projected."""
        if source not in ("query", "target"):
            raise ValueError(f"source must be 'query' or 'target', got {source!r}")
        blocks: list[Block] = []
        for r in records:
            if source == "query":
                s = _block_char_span(src_para_spans, r.query_start, r.query_end)
                d = _block_char_span(dst_para_spans, r.target_start, r.target_end)
            else:
                s = _block_char_span(src_para_spans, r.target_start, r.target_end)
                d = _block_char_span(dst_para_spans, r.query_start, r.query_end)
            if s is None or d is None:
                continue
            blocks.append(Block(s[0], s[1], d[0], d[1]))
        return cls(blocks)

    def project_span(self, start: int, end: int) -> list[Span]:
        """Destination char spans corresponding to source ``[start, end)`` — the blocks it overlaps.

        Block-granular and honest: a source interval overlapping an aligned block yields that block's
        whole destination span (character-level position inside a block is not known). Overlapping
        destination spans are merged. Empty if the interval lands entirely in unaligned gaps."""
        if end <= start:
            return []
        hits: list[Span] = [
            (b.dst_start, b.dst_end)
            for b in self.blocks
            if b.src_start < end and start < b.src_end
        ]
        return _merge_spans(hits)

    def lift_intervals(self, intervals: list[Span]) -> tuple[list[Span], list[Span]]:
        """Project a set of source intervals to the destination frame.

        Returns ``(lifted, dropped)``: ``lifted`` is the merged destination spans; ``dropped`` is the
        merged source intervals that touched no aligned block (reported, never silent — principles §4)."""
        lifted: list[Span] = []
        dropped: list[Span] = []
        for start, end in intervals:
            if end <= start:
                continue
            projected = self.project_span(start, end)
            if projected:
                lifted.extend(projected)
            else:
                dropped.append((start, end))
        return _merge_spans(lifted), _merge_spans(dropped)

    @property
    def src_covered(self) -> list[Span]:
        """Merged source-frame spans that participate in some alignment block (liftable region)."""
        return _merge_spans([(b.src_start, b.src_end) for b in self.blocks])

    @property
    def dst_covered(self) -> list[Span]:
        """Merged destination-frame spans reachable by liftover."""
        return _merge_spans([(b.dst_start, b.dst_end) for b in self.blocks])
