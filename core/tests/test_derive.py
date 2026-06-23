"""Unit tests for the subtext-derivation offset map and layer remapping (palimpsest.derive)."""
from palimpsest.derive import (
    OffsetMap,
    assemble_text,
    compute_kept_spans,
    remap_layout,
    remap_track_annotations,
    remap_verses,
)
from palimpsest.layout import LayoutSection


def _sec(id, type, start, end, parent_id=None, masked=None):
    return LayoutSection(id=id, type=type, start=start, end=end, parent_id=parent_id, masked=masked)


# A synthetic parent: body+book span the whole work; two chapters with a header and front
# matter that sit OUTSIDE the chapter spans. Extracting 'chapter' should keep only the two
# chapter spans and carry body/book (clipped), dropping header + front_matter.
PARENT = [
    _sec("body", "body", 0, 100),
    _sec("fm", "front_matter", 0, 10),
    _sec("book", "book", 10, 100, parent_id="body"),
    _sec("h1", "header", 10, 20, parent_id="book"),
    _sec("c1", "chapter", 20, 40, parent_id="book"),
    _sec("h2", "header", 40, 50, parent_id="book"),
    _sec("c2", "chapter", 50, 70, parent_id="book"),
]
TEXT = "".join(chr(ord("a") + (i % 26)) for i in range(100))


def test_compute_kept_spans_merges_and_excludes():
    spans = compute_kept_spans(PARENT, {"chapter"}, set())
    assert spans == [(20, 40), (50, 70)]
    # Excluding c2 drops the second span.
    assert compute_kept_spans(PARENT, {"chapter"}, {"c2"}) == [(20, 40)]


def test_offset_map_translate_and_assemble():
    spans = [(20, 40), (50, 70)]
    omap = OffsetMap(spans, len("\n\n"))
    # span0 → child [0,20]; separator (2) ; span1 → child [22,42]
    assert omap.translate_point(20) == 0
    assert omap.translate_point(39) == 19
    assert omap.translate_point(50) == 22
    assert omap.translate_point(45) is None  # in the dropped gap
    assert omap.child_len == 20 + 2 + 20
    child = assemble_text(TEXT, spans)
    assert child == TEXT[20:40] + "\n\n" + TEXT[50:70]
    assert len(child) == omap.child_len


def test_remap_layout_clips_containers_and_drops_nonoverlap():
    spans = compute_kept_spans(PARENT, {"chapter"}, set())
    omap = OffsetMap(spans, 2)
    cfg = remap_layout(PARENT, {"chapter": False, "body": False, "book": False}, [], omap)
    by_id = {s.id: s for s in cfg.sections}
    # header + front_matter dropped (no overlap with the chapter spans).
    assert "h1" not in by_id and "h2" not in by_id and "fm" not in by_id
    # body/book clipped to the kept region and span the whole child (incl. the separator gap).
    assert (by_id["body"].start, by_id["body"].end) == (0, 42)
    assert (by_id["book"].start, by_id["book"].end) == (0, 42)
    # chapters become the two child segments.
    assert (by_id["c1"].start, by_id["c1"].end) == (0, 20)
    assert (by_id["c2"].start, by_id["c2"].end) == (22, 42)
    # parent_id to a dropped element (book is kept, body is kept) stays; chapters keep book.
    assert by_id["c1"].parent_id == "book"
    assert cfg.applied is True


def test_remap_layout_clears_dangling_parent_id():
    # If the parent container is dropped, the child's parent_id is cleared.
    secs = [_sec("only", "chapter", 50, 70, parent_id="gone")]
    omap = OffsetMap([(50, 70)], 2)
    cfg = remap_layout(secs, {"chapter": False}, [], omap)
    assert cfg.sections[0].parent_id is None


def test_remap_verses_preserves_metadata_and_masks():
    # A verse inside chapter c1 (parent 20..40): num token [22,27), prose [27,40).
    recs = [{"b": "Genesis", "c": 1, "v": 1, "ns": 22, "s": 27, "e": 40}]
    omap = OffsetMap([(20, 40), (50, 70)], 2)
    out = remap_verses(recs, omap)
    assert out == [{"b": "Genesis", "c": 1, "v": 1, "ns": 2, "s": 7, "e": 20}]
    # A verse in the dropped gap is removed.
    assert remap_verses([{"b": "X", "c": 1, "v": 1, "ns": 44, "s": 45, "e": 48}], omap) == []


def test_remap_track_drops_gap_crossing_annotations():
    omap = OffsetMap([(20, 40), (50, 70)], 2)
    inside = {"target": {"selector": {"start": 22, "end": 30}}, "body": {"value": "x"}}
    crossing = {"target": {"selector": {"start": 38, "end": 52}}, "body": {"value": "y"}}
    out = remap_track_annotations([inside, crossing], omap)
    assert len(out) == 1
    assert out[0]["target"]["selector"] == {"start": 2, "end": 10}
