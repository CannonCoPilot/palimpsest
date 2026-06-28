"""Char-level analyzable-text resolver: complement spans and OffsetMap inverse translation."""
from pathlib import Path

import pytest

from palimpsest.derive import OffsetMap
from palimpsest.project import _complement_spans


def test_complement_spans():
    assert _complement_spans([(2, 5)], 10) == [(0, 2), (5, 10)]
    assert _complement_spans([], 10) == [(0, 10)]               # nothing masked → whole doc
    assert _complement_spans([(0, 10)], 10) == []               # fully masked → nothing kept
    assert _complement_spans([(0, 3), (3, 6)], 10) == [(6, 10)]  # adjacent masked spans
    assert _complement_spans([(0, 2), (8, 10)], 10) == [(2, 8)]  # masked at both ends


def test_offsetmap_inverse_round_trips_translate():
    # child = parent[0:5] + "··" + parent[10:15]; sep_len 2.
    omap = OffsetMap([(0, 5), (10, 15)], sep_len=2)
    assert omap.child_len == 12
    # forward then inverse returns the original parent offset for every kept point
    for p in (0, 1, 4, 5, 10, 13, 15):
        c = omap.translate_point(p)
        assert c is not None
        assert omap.inverse_point(c) == p


def test_offsetmap_inverse_point_separator_has_no_preimage():
    omap = OffsetMap([(0, 5), (10, 15)], sep_len=2)
    # child offsets 5..6 are the separator between the two kept spans → no parent pre-image
    assert omap.inverse_point(6) is None
    assert omap.inverse_point(0) == 0
    assert omap.inverse_point(7) == 10   # first char after the separator maps to span-2 start


def test_offsetmap_inverse_element_within_and_across_spans():
    omap = OffsetMap([(0, 5), (10, 15)], sep_len=2)
    assert omap.inverse_element(2, 4) == (2, 4)        # wholly inside span 1
    assert omap.inverse_element(8, 12) == (11, 15)     # wholly inside span 2
    assert omap.inverse_element(4, 8) is None          # straddles the dropped gap → dropped


def test_offsetmap_inverse_span_keeps_gap_spanning():
    # sep_len 0 = pure excision: child is parent[0:5] + parent[10:15], child_len 10.
    omap = OffsetMap([(0, 5), (10, 15)], sep_len=0)
    assert omap.child_len == 10
    assert omap.inverse_span(1, 4) == (1, 4)        # wholly inside span 1 → exact
    assert omap.inverse_span(6, 9) == (11, 14)      # wholly inside span 2 → exact
    # child [4,7) = parent[4] + parent[10] + parent[11]; the original range includes the excised
    # gap (5..10) "as if it weren't there" — first char parent[4] to last char parent[11], +1.
    assert omap.inverse_span(4, 7) == (4, 12)


def _masked_project(tmp_path: Path):
    """A small ingested project whose front matter ("CONTENTS …") is masked by an applied layout."""
    from palimpsest.layout import (
        DEFAULT_MASK_BY_TYPE,
        LayoutConfig,
        detect_layout_sections,
        save_layout,
    )
    from palimpsest.project import ingest_file

    body = "The quick brown fox jumps over the lazy dog. " * 60
    text = "CONTENTS\n\nChapter one .... 1\nChapter two .... 9\n\n" + body
    src = tmp_path / "src.txt"
    src.write_text(text, encoding="utf-8")
    project = ingest_file(src, tmp_path, title="Mask Test")
    full = project.reference_text()
    contents_at = full.index("CONTENTS")
    body_at = full.index("The quick brown fox")
    sections = detect_layout_sections(
        [(contents_at, contents_at + 8, "Contents"), (body_at, body_at + 1, "Chapter 1")],
        text_len=len(full),
    )
    save_layout(project.path, LayoutConfig(sections=sections, mask_by_type=dict(DEFAULT_MASK_BY_TYPE), applied=True))
    return project, full


def test_analysis_view_text_is_unmasked_chars_only(tmp_path: Path):
    project, full = _masked_project(tmp_path)
    masked = project.masked_intervals()
    assert masked, "expected the front matter to be masked"

    def in_masked(p: int) -> bool:
        return any(a <= p < b for a, b in masked)

    view, omap = project.analysis_view()
    atext = view.reference_text()
    assert len(atext) < len(full)                       # masked front matter dropped
    # every analyzable character maps back to an UNMASKED original char, with fidelity
    for c in range(len(atext)):
        p = omap.inverse_point(c)
        if p is not None:
            assert not in_masked(p)
            assert atext[c] == full[p]


def test_analyzable_text_length_matches_offset_map(tmp_path: Path):
    # Bridge invariant: the assembled analyzable text and its OffsetMap agree on length, and the
    # analysis view exposes that same text already pre-masked (its own masked set is empty).
    project, _full = _masked_project(tmp_path)
    atext, omap = project.analyzable_text()
    assert len(atext) == omap.child_len
    view, view_omap = project.analysis_view()
    assert len(view.reference_text()) == view_omap.child_len
    assert view.masked_intervals() == []


def test_extract_masked_keeps_annotations_out_of_masked_regions(tmp_path: Path):
    from palimpsest.runner import extract_masked as _extract_masked
    from palimpsest.tracks.lexical import LexicalExtractor

    project, full = _masked_project(tmp_path)
    masked = project.masked_intervals()
    anns = _extract_masked(project, LexicalExtractor())
    assert isinstance(anns, list) and anns, "lexical should produce annotations on the body"
    for a in anns:
        s, e = a.target.selector.start, a.target.selector.end
        assert 0 <= s < e <= len(full)
        for ms, me in masked:                            # no annotation overlaps a masked span
            assert not (s < me and e > ms), f"annotation [{s},{e}) overlaps masked [{ms},{me})"


def test_self_similarity_signal_excludes_masked_and_maps_to_original(tmp_path: Path):
    import json

    from palimpsest.runner import extract_masked as _extract_masked
    from palimpsest.tracks.self_similarity import SelfSimilarityTrack

    project, full = _masked_project(tmp_path)
    masked = project.masked_intervals()
    track = SelfSimilarityTrack()
    # Non-embedding metrics exercise the chunking → signal → remap path without an embedding service;
    # all chunking+embedding params are explicit (the stage has no defaults).
    track.set_params({
        "chunk_mode": "word",
        "chunk_size": 7,
        "metrics": ["word_overlap", "edit_distance"],
    })
    _extract_masked(project, track)
    manifest = json.loads((project.path / "signals" / "self_similarity.json").read_text())
    offsets = manifest["segment_offsets"]
    assert offsets, "self_similarity should chunk the body"
    for s, e in offsets:
        assert 0 <= s < e <= len(full)                   # remapped to original coordinates
        for ms, me in masked:                            # masked content is excised, never chunked
            assert not (s >= ms and e <= me), f"chunk [{s},{e}) lies inside masked [{ms},{me})"


def test_analysis_view_threads_separator(tmp_path: Path, monkeypatch):
    # R2: the analyzable-stream separator threads through analysis_view → analyzable_text (it is no
    # longer a hidden "" default) and stays coordinate-safe — separator characters have no original
    # preimage, while every kept character still round-trips to its unmasked original.
    from palimpsest.project import ingest_file

    src = tmp_path / "sep.txt"
    src.write_text("AAAA BBBB CCCC DDDD EEEE", encoding="utf-8")
    project = ingest_file(src, tmp_path, title="Sep")
    full = project.reference_text()
    b = full.index("BBBB")
    # Mask an interior word so two kept spans flank it and a separator is actually inserted.
    monkeypatch.setattr(project, "masked_intervals", lambda extra_masked=None: [(b, b + 4)])

    empty = project.analysis_view("")[0].reference_text()
    spaced_view, omap = project.analysis_view(" | ")
    spaced = spaced_view.reference_text()

    # The separator lands exactly at the excised gap — the spaced stream is the pure-excision stream
    # with " | " inserted at the join (the first kept span ends at original offset b).
    assert spaced == empty[:b] + " | " + empty[b:]
    # Coordinate-safe: every kept (non-separator) character still round-trips to its unmasked original.
    sep_region = range(b, b + len(" | "))
    for c in range(len(spaced)):
        if c in sep_region:
            continue
        p = omap.inverse_point(c)
        if p is not None:
            assert spaced[c] == full[p]


def _verse_project(tmp_path: Path):
    from palimpsest.project import ingest_file

    text = (
        "1:1. In the beginning God created the heaven and the earth.\n"
        "1:2. And the earth was without form, and void.\n"
        "1:3. And God said, Let there be light: and there was light.\n"
    )
    src = tmp_path / "verses.txt"
    src.write_text(text, encoding="utf-8")
    return ingest_file(src, tmp_path, title="Verses")


def test_verse_number_masking_defaults_on(tmp_path: Path):
    # R10: with no override the verse-number markers stay masked — the long-standing default that
    # keeps "C:V." structural noise out of analysis. (Three markers in the fixture: "1:1. " etc.)
    project = _verse_project(tmp_path)
    masked = project.masked_intervals()
    assert len(masked) == 3, "verse-number markers should be masked by default"


def test_verse_number_masking_toggle_off_yields_fully_unmasked(tmp_path: Path):
    # R10: the verse-number layer is now a runtime toggle. With structural masking off AND
    # mask_verse_numbers off, nothing remains masked — a fully unmasked run, previously impossible
    # because the verse layer was unconditionally unioned in.
    project = _verse_project(tmp_path)
    project.set_mask_override({"enabled": False, "mask_verse_numbers": False})
    assert project.masked_intervals() == [], "toggling both off should leave nothing masked"


def test_verse_number_masking_independent_of_structural_toggle(tmp_path: Path):
    # R10: the verse toggle is orthogonal to the structural `enabled` toggle — turning structural
    # masking off keeps verse-number masking on unless verse masking is also explicitly disabled.
    project = _verse_project(tmp_path)
    project.set_mask_override({"enabled": False, "mask_verse_numbers": True})
    assert len(project.masked_intervals()) == 3, "verse layer survives structural-off when left on"


# ── Masking-pipeline contract (Wave-0 substrate hardening) ──────────────────────
# The masking pipeline is the substrate spine: masked_intervals -> _complement_spans -> analyzable
# text + OffsetMap. These lock the invariants every downstream analysis silently relies on, so a
# future change to the masking core cannot quietly corrupt the analyzable coordinate space.


def test_complement_spans_rejects_malformed_masked_set():
    # Update 1: the partition pivot fails loud on a precondition violation instead of emitting
    # silently-wrong kept spans (which would mis-anchor every analysis).
    with pytest.raises(ValueError, match="out of bounds"):
        _complement_spans([(5, 20)], 10)            # end past text length
    with pytest.raises(ValueError, match="out of bounds"):
        _complement_spans([(-1, 3)], 10)            # negative start
    with pytest.raises(ValueError, match="sorted and disjoint"):
        _complement_spans([(0, 6), (3, 8)], 10)     # overlapping
    with pytest.raises(ValueError, match="sorted and disjoint"):
        _complement_spans([(5, 8), (0, 3)], 10)     # out of order


def _assert_masking_contract(project) -> None:
    """Assert the universal masking invariants (I1-I6) for a project's current mask state."""
    full = project.reference_text()
    n = len(full)
    masked = project.masked_intervals()

    # I3 idempotence: recomputation is identical.
    assert project.masked_intervals() == masked

    # I1/I2: sorted, mutually disjoint (strictly separated after merge), in-bounds.
    prev_end = -1
    for a, b in masked:
        assert 0 <= a < b <= n, f"interval ({a}, {b}) out of bounds for length {n}"
        assert a > prev_end, f"interval ({a}, {b}) not sorted/disjoint after end {prev_end}"
        prev_end = b

    # I4 partition: masked ∪ kept tiles [0, n) exactly — no gap, no overlap.
    kept = _complement_spans(masked, n)
    cur = 0
    for a, b in sorted(masked + kept):
        assert a == cur, f"partition break at {a}, expected {cur}"
        cur = b
    assert cur == n, f"partition did not reach text end ({cur} != {n})"

    # I5/I6: pure-excision analyzable text contains only kept chars, each mapping back to its
    # original character via the OffsetMap.
    atext, omap = project.analyzable_text(sep="")
    assert len(atext) == sum(e - s for s, e in kept)        # I6: only kept chars survive
    for c in range(len(atext)):                              # I5: round-trip to the right char
        p = omap.inverse_point(c)
        assert p is not None and atext[c] == full[p], f"analyzable char {c} did not round-trip"


def test_masking_contract_holds_for_structural_masking(tmp_path: Path):
    project, _ = _masked_project(tmp_path)
    assert project.masked_intervals(), "fixture should mask its front matter"
    _assert_masking_contract(project)


def test_masking_contract_holds_across_verse_and_override_configs(tmp_path: Path):
    project = _verse_project(tmp_path)
    _assert_masking_contract(project)                                    # verse-number layer (default on)
    project.set_mask_override({"enabled": False, "mask_verse_numbers": True})
    _assert_masking_contract(project)                                    # verse-only (structural off)
    project.set_mask_override({"enabled": False, "mask_verse_numbers": False})
    assert project.masked_intervals() == []                             # fully unmasked
    _assert_masking_contract(project)
