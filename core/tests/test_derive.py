"""Unit tests for the subtext-derivation offset map and layer remapping (palimpsest.derive)."""
import pytest

from palimpsest.derive import (
    OffsetMap,
    UnmappedCoordinateError,
    assemble_text,
    compute_kept_spans,
    remap_layout,
    remap_signal_data,
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


# Two adjacent containers: a "main" book [0,40] and an "appendix" [40,80], each with two chapters.
SCOPED = [
    _sec("main", "book", 0, 40),
    _sec("m1", "chapter", 0, 20, parent_id="main"),
    _sec("m2", "chapter", 20, 40, parent_id="main"),
    _sec("apx", "appendix", 40, 80),
    _sec("a1", "chapter", 40, 60, parent_id="apx"),
    _sec("a2", "chapter", 60, 80, parent_id="apx"),
]


def test_compute_kept_spans_container_scope_restricts_to_appendix():
    # No scope (None or empty) keeps every chapter (all four merge into one span).
    assert compute_kept_spans(SCOPED, {"chapter"}, set()) == [(0, 80)]
    assert compute_kept_spans(SCOPED, {"chapter"}, set(), []) == [(0, 80)]
    # Scoped to the appendix container span: only its two chapters survive.
    assert compute_kept_spans(SCOPED, {"chapter"}, set(), [(40, 80)]) == [(40, 80)]


def test_compute_kept_spans_container_scope_honors_exclusions_and_partial_overlap():
    # Per-element exclusion still applies within a container scope.
    assert compute_kept_spans(SCOPED, {"chapter"}, {"a2"}, [(40, 80)]) == [(40, 60)]
    # An element only partially inside the container is NOT included (full containment required).
    spill = SCOPED + [_sec("x", "chapter", 70, 95)]
    assert compute_kept_spans(spill, {"chapter"}, set(), [(40, 80)]) == [(40, 80)]


def test_derive_subtext_scoped_to_container(tmp_path):
    from palimpsest.derive import derive_subtext
    from palimpsest.layout import LayoutConfig, save_layout
    from palimpsest.project import Project, ingest_file

    text = "MAINBODYAAAAAAAAAA" + "APPENDIXBBBBBBBBBB"  # 18 + 18, contiguous
    src = tmp_path / "src.txt"
    src.write_text(text, encoding="utf-8")
    project = ingest_file(src, tmp_path, title="Scope Test")
    full = project.reference_text()
    m0, a0 = full.index("MAINBODY"), full.index("APPENDIX")
    end = a0 + len("APPENDIXBBBBBBBBBB")
    sections = [
        _sec("mainbook", "book", m0, a0),
        _sec("mc1", "chapter", m0, m0 + 9, parent_id="mainbook"),
        _sec("mc2", "chapter", m0 + 9, a0, parent_id="mainbook"),
        _sec("apx", "appendix", a0, end),
        _sec("ac1", "chapter", a0, a0 + 9, parent_id="apx"),
        _sec("ac2", "chapter", a0 + 9, end, parent_id="apx"),
    ]
    save_layout(project.path, LayoutConfig(sections=sections, applied=True, parents_computed=True))
    parent = Project.load(project.path)

    child, _cfg, summary = derive_subtext(
        parent, tmp_path, extraction_types=["chapter"], include_container_ids=["apx"], title="Apx only",
    )
    child_text = child.reference_text()
    assert "APPENDIX" in child_text and "MAINBODY" not in child_text
    assert summary["container_ids"] == ["apx"]

    # Unknown container id fails loud (no silent empty subtext).
    with pytest.raises(ValueError, match="Unknown or empty container"):
        derive_subtext(parent, tmp_path, extraction_types=["chapter"], include_container_ids=["nope"])


def test_derive_reuses_parent_segmentation_and_stays_offset_aligned(tmp_path, monkeypatch):
    """Regression for the slow + mis-aligned subtext derive (fixed 2026-06-23).

    Two root causes are locked here: (1) derivation re-ran the spaCy segmenter on the assembled
    child (the dominant cost, scaling with child size); it must instead remap the parent's existing
    segments. (2) ``ingest_file`` re-normalized the child, re-collapsing whitespace at the separator
    junctions, so ``reference.txt`` drifted from the offset map and pushed segments out of bounds;
    derivation now passes ``pre_normalized=True``.
    """
    import json as _json

    from palimpsest.derive import derive_subtext
    from palimpsest.layout import LayoutConfig, save_layout
    from palimpsest.project import Project, ingest_file
    import palimpsest.project as project_mod

    raw = (
        "Front matter to drop.\n\n"
        "Alpha chapter sentence one. Alpha chapter sentence two.\n\n"
        "Header to drop.\n\n"
        "Beta chapter sentence one. Beta chapter sentence two."
    )
    src = tmp_path / "src.txt"
    src.write_text(raw, encoding="utf-8")
    project = ingest_file(src, tmp_path, title="Seg Reuse")
    full = project.reference_text()
    c1s = full.index("Alpha")
    c1e = c1s + len("Alpha chapter sentence one. Alpha chapter sentence two.")
    c2s = full.index("Beta")
    sections = [
        _sec("body", "body", 0, len(full)),
        _sec("fm", "front_matter", 0, c1s),
        _sec("c1", "chapter", c1s, c1e, parent_id="body"),
        _sec("hdr", "header", c1e, c2s),
        _sec("c2", "chapter", c2s, len(full), parent_id="body"),
    ]
    save_layout(project.path, LayoutConfig(sections=sections, applied=True, parents_computed=True))
    parent = Project.load(project.path)

    # Trap the slow path: the derive must reuse the parent's segmentation, so any call into the spaCy
    # segmenters during derivation is a regression to the pre-fix behavior — fail it loudly.
    def _boom(*_a, **_k):
        raise AssertionError("subtext derivation must reuse parent segmentation, not re-segment")

    monkeypatch.setattr(project_mod, "segment_sentences", _boom)
    monkeypatch.setattr(project_mod, "segment_paragraphs", _boom)
    monkeypatch.setattr(project_mod, "segment_sections", _boom)

    child, _cfg, summary = derive_subtext(parent, tmp_path, extraction_types=["chapter"], title="Chapters")

    child_text = child.reference_text()
    # pre_normalized alignment: reference.txt length is EXACTLY the offset map's child length — no
    # whitespace re-collapse drift at the separator junctions.
    assert len(child_text) == summary["char_count"]
    assert "Alpha" in child_text and "Beta" in child_text and "Front matter" not in child_text

    segs = [
        _json.loads(line)
        for line in (child.path / "tracks" / "segments.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert segs, "derived child should carry remapped segments"
    # Every remapped segment stays in bounds (the drift bug had pushed sentences past the end).
    for rec in segs:
        sel = rec["target"]["selector"]
        assert 0 <= sel["start"] <= sel["end"] <= len(child_text)
    # Only the two chapter paragraphs survive; the dropped front-matter/header paragraphs do not.
    para_count = sum(
        1 for r in segs if (r.get("body") or {}).get("palimpsest:segmentType") == "paragraph"
    )
    assert para_count == 2


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


class TestRemapSignalContract:
    """G4/C4: signal coordinates are remapped analyzable→original through a single enforced contract.
    A recognized shape is remapped; a coordinate-free shape passes through; an offset-bearing field in
    a position the remap can't handle is a hard error (``UnmappedCoordinateError``), never a silent
    passthrough that mislabels analyzable coordinates as original."""

    def _omap(self):
        # span0 → child [0,20); separator(2); span1 → child [22,42). Child→parent: +20 in span0.
        return OffsetMap([(20, 40), (50, 70)], 2)

    def test_segment_offsets_remapped(self):
        data = {"type": "matrix", "segment_offsets": [[0, 5], [6, 10]]}
        assert remap_signal_data(data, self._omap()) is True
        assert data["segment_offsets"] == [[20, 25], [26, 30]]

    def test_alignment_list_char_keys_remapped_chunk_indices_untouched(self):
        data = [{"char_start_a": 0, "char_end_a": 5, "char_start_b": 6, "char_end_b": 10,
                 "chunk_a": 3, "metric": "cosine"}]
        assert remap_signal_data(data, self._omap()) is True
        rec = data[0]
        assert (rec["char_start_a"], rec["char_end_a"]) == (20, 25)
        assert (rec["char_start_b"], rec["char_end_b"]) == (26, 30)
        assert rec["chunk_a"] == 3  # coordinate-free matrix index, untouched

    def test_nested_segment_offsets_is_hard_error(self):
        # The exact C4 landmine: offsets nested under metadata would silently pass through today.
        data = {"type": "x", "metadata": {"segment_offsets": [[0, 5]]}}
        with pytest.raises(UnmappedCoordinateError, match="segment_offsets"):
            remap_signal_data(data, self._omap())

    def test_misplaced_char_key_is_hard_error(self):
        data = {"foo": {"char_start_a": 0, "char_end_a": 5}}
        with pytest.raises(UnmappedCoordinateError, match="char_start_a"):
            remap_signal_data(data, self._omap())

    def test_declared_span_list_field_remapped(self):
        # The declaration hook: a novel output names its coordinate field and it is remapped + blessed.
        data = {"type": "graph", "node_spans": [[0, 5], [6, 10]],
                "analyzable_coordinate_fields": ["node_spans"]}
        assert remap_signal_data(data, self._omap()) is True
        assert data["node_spans"] == [[20, 25], [26, 30]]

    def test_declared_pair_field_remapped(self):
        data = {"span": [0, 5], "analyzable_coordinate_fields": ["span"]}
        assert remap_signal_data(data, self._omap()) is True
        assert data["span"] == [20, 25]

    def test_coordinate_free_signal_passes_through(self):
        data = {"type": "scalar", "metadata": {"count": 5}, "values": [1, 2, 3]}
        assert remap_signal_data(data, self._omap()) is False
        assert data == {"type": "scalar", "metadata": {"count": 5}, "values": [1, 2, 3]}
