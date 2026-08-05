# -*- coding: utf-8 -*-
"""The `Annotations2` truncation, pinned (§13 Q48).

THE DEFECT. `originaldouayrheims.com` marks the start of a chapter's apparatus with `<span id="Annotations">`,
and `scrape_odr_com.parse_chapter` correctly cuts the scripture stream there. But the id was matched with

    id\\s*=\\s*['\"]?Annotations['\"]?[^>]*>

whose optional closing quote also matches the PREFIX of `id="Annotations2"` — `[^>]*` then swallows the
trailing `2">`. And `Annotations2` is not apparatus: on this site it is a STYLE, whose meaning is positional.
After the ANNOTATIONS. header it wraps annotation prose; before it, it wraps plain scripture — genesis 4
carries verses 8-15 and 16-26 in two such spans, genesis 13 verses 5-9 and 10-18.

So every chapter using that style was cut at its first occurrence: genesis 4, 6 and 9 at verse 7, genesis 11 at
9, genesis 13 at 4, genesis 49 at 2. 149 verses of Genesis and 47 of Exodus, silently absent from the witness,
which is why 9 Genesis chapters were classified REF-GAP and 596 cells were unreachable.

IT WAS DETECTED AT ACQUISITION AND NOT READ. The scrape manifest recorded `verse_count_match: 37/50` for
genesis and a chapter-bag agreement (0.8559) well below the per-verse agreement (0.9292) — the manifest's own
documentation says that gap "isolates verse-boundary differences from TEXT LOSS". The measurement was right
there; nothing consumed it.

Two tests, one per half of the fix: the header must not match the styled span, and the styled span must keep
its scripture. They run on synthetic HTML in the site's shape — no network, no cache.
"""
from __future__ import annotations

import sys
from pathlib import Path

# The scraper lives with the tracked acquisition code, not in the spike. Imported HARD, not via
# `importorskip`: a skip on a wrong path is a silent pass, and this file exists to stop a silent loss.
_ACQ = (Path(__file__).resolve().parents[4]
        / "tests/fixtures/gold/mask_engine/originaldr_reconstruction/acquisition")
assert _ACQ.is_dir(), f"acquisition dir not found at {_ACQ}"
if str(_ACQ) not in sys.path:
    sys.path.insert(0, str(_ACQ))

import scrape_odr_com as S  # noqa: E402


_SCRIPTURE_IN_ANNOT2 = """
<span id="Chapter"> </span> <br>
<b>1. </b>And Adam knewe Eue his wife.
<b>2. </b>And she againe brought forth his brother Abel.
<span id="Annotations2">
 <b>3. </b>And it came to passe after manie dayes.
 <b>4. </b>Abel also offered of the firstlings of his flocke.
</span>
"""

_REAL_APPARATUS = """
<b>1. </b>In the beginning God created heauen and earth.
<b>2. </b>And the earth was voide and vacant.
<span id="Annotations">
  ANNOTATIONS. </span>
<span id="Annotations2">
1. <i>In the beginning.</i>] The Church had only Traditions and no Scripture.
</span>
"""


def test_a_styled_span_does_not_truncate_the_chapter():
    """`Annotations2` before the header holds scripture; the chapter must not stop at it."""
    verses, _notes = S.parse_chapter(_SCRIPTURE_IN_ANNOT2, 4)
    assert sorted(int(k) for k in verses) == [1, 2, 3, 4]
    assert "firstlings" in verses["4"]


def test_the_real_annotations_header_still_ends_the_scripture():
    """The fix must not cost the cut it was protecting: apparatus stays out of the verses."""
    verses, notes = S.parse_chapter(_REAL_APPARATUS, 1)
    assert sorted(int(k) for k in verses) == [1, 2]
    assert "Traditions" not in " ".join(verses.values()), "annotation prose leaked into scripture"
    assert any("Traditions" in n for n in notes), "the annotation was not captured as a note"


def test_the_header_pattern_rejects_the_numbered_variant():
    """The regex itself, at the level the bug lived on."""
    assert S._ANNOT_HDR_MARK.search('<span id="Annotations">')
    assert S._ANNOT_HDR_MARK.search("<span id='Annotations'>")
    assert not S._ANNOT_HDR_MARK.search('<span id="Annotations2">')
    assert not S._ANNOT_HDR_MARK.search('<span id="AnnotationsNum">')
