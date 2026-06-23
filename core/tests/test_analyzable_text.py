"""Char-level analyzable-text resolver: complement spans and OffsetMap inverse translation."""
from pathlib import Path

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


def test_extract_masked_keeps_annotations_out_of_masked_regions(tmp_path: Path):
    from palimpsest.server import _extract_masked
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
