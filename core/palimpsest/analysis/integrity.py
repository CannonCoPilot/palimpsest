"""integrity — substrate contract integrity report (Wave-0 P4, FR-9).

A user-runnable report that makes the substrate's coordinate invariants *legible*: it runs the
**existing** contract validators — the same postcondition self-checks the producers already call — and
reports green/violation per invariant. It adds no new validation logic; it is purely a presentation
surface over functions defined elsewhere, so it can never drift from the real contract (a test injects a
violation and asserts the report catches it).

Invariants checked:
  * ``masked-partition``       — ``project._complement_spans`` turns the masked set into kept spans.
  * ``span-region-bounds``     — ``layout._validate_span_regions`` bounds/orders the masked regions.
  * ``segment-contract``       — ``segmenter._validate_segments`` anchors paragraph segments to text.
  * ``section-tree``           — ``layout.validate_section_tree`` enforces the containment forest.
  * ``offsetmap-roundtrip``    — ``derive.OffsetMap`` inverts: ``inverse_point(translate_point(x))==x``.
  * ``analyzable-bridge``      — ``analyzable_text`` agrees with its OffsetMap on length.
  * ``encoding-sanity``        — the reference text carries no U+FFFD replacement characters.

Each invariant reports ``pass``, ``violation`` (with the validator's own message), or ``na`` when its
prerequisite is absent (e.g. no layout configured), so an inapplicable check never reads as a failure.
"""

from __future__ import annotations

from typing import Any, Callable

_REPLACEMENT_CHAR = "�"


def _check(name: str, fn: Callable[[], str | None]) -> dict[str, str]:
    """Run one invariant. ``fn`` returns ``None`` (pass), a string (the ``na`` reason, prefixed
    ``na:``), or raises ``ValueError`` (violation)."""
    try:
        note = fn()
    except ValueError as exc:
        return {"name": name, "status": "violation", "detail": str(exc)}
    if isinstance(note, str) and note.startswith("na:"):
        return {"name": name, "status": "na", "detail": note[3:].strip()}
    return {"name": name, "status": "pass", "detail": note or ""}


def run_integrity_report(project: Any) -> dict[str, Any]:
    """Run every substrate validator against ``project`` and return a per-invariant pass/violation/na
    report plus a descriptive summary. Never raises — a validator's ``ValueError`` becomes a reported
    violation, which is the whole point of the surface."""
    from palimpsest.derive import OffsetMap
    from palimpsest.ingest.segmenter import _validate_segments, segment_paragraphs
    from palimpsest.layout import _validate_span_regions, load_layout, validate_section_tree
    from palimpsest.project import _complement_spans

    text = project.reference_text()
    n = len(text)
    masked = project.masked_intervals()

    def _masked_partition() -> None:
        _complement_spans(masked, n)

    def _span_bounds() -> None:
        _validate_span_regions(masked, 0, n)

    def _segments() -> None:
        segs = segment_paragraphs(text)
        _validate_segments(segs, text)

    def _section_tree() -> str | None:
        cfg = load_layout(project.path)
        if cfg is None:
            return "na: no layout configured for this project"
        validate_section_tree(cfg.sections)
        return None

    def _offsetmap_roundtrip() -> None:
        kept = _complement_spans(masked, n)
        if not kept:
            return
        omap = OffsetMap(kept, 0)
        # Sample offsets across kept spans (start + interior of each) — round-trip must be identity.
        for s, e in kept:
            for off in {s, (s + e) // 2, e - 1}:
                child = omap.translate_point(off)
                if child is None or omap.inverse_point(child) != off:
                    raise ValueError(
                        f"OffsetMap round-trip failed at original offset {off} "
                        f"(child={child}, back={omap.inverse_point(child) if child is not None else None})"
                    )

    def _analyzable_bridge() -> None:
        project.analyzable_text()  # asserts len(atext) == omap.child_len internally

    def _encoding_sanity() -> None:
        count = text.count(_REPLACEMENT_CHAR)
        if count:
            raise ValueError(f"reference text contains {count} U+FFFD replacement character(s)")

    invariants = [
        _check("masked-partition", _masked_partition),
        _check("span-region-bounds", _span_bounds),
        _check("segment-contract", _segments),
        _check("section-tree", _section_tree),
        _check("offsetmap-roundtrip", _offsetmap_roundtrip),
        _check("analyzable-bridge", _analyzable_bridge),
        _check("encoding-sanity", _encoding_sanity),
    ]

    masked_chars = sum(e - s for s, e in masked)
    summary = {
        "text_length": n,
        "masked_chars": masked_chars,
        "masked_ratio": round(masked_chars / n, 4) if n else 0.0,
        "paragraph_count": len(project.paragraphs()),
        "section_count": len(project.sections()),
    }

    return {
        "framing": "descriptive",
        "all_green": all(i["status"] != "violation" for i in invariants),
        "invariants": invariants,
        "summary": summary,
    }
