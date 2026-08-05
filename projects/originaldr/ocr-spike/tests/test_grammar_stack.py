# -*- coding: utf-8 -*-
"""TDD spec for the composable block grammar, verse-number recovery, and the page-level failure alarm.

These pin the properties the 2026-07-27 visual inspection of ot2-1610 pp215-236 established:
  * the DR prints SELF-LABELLING verse markers (`N †` in Psalm 118, `N.` in the NT 1582) — a marker that
    names its own verse cannot produce an off-by-one, so it must be preferred wherever it exists;
  * a page inside a psalm's range may carry NO scripture at all (p216 is the General Annotations treatise),
    so 'no verse text here' must be a first-class detection, not a failure;
  * annotation and continuation lines are separable by GEOMETRY moving in opposite directions — a
    continuation is indented FURTHER than its opening, an annotation LESS and to the full measure;
  * a recovered number that does not fit the sequence is REFUSED, because a wrong verse number relabels a
    correct span with confidence and is worse than no number at all.
"""
from __future__ import annotations

import pytest

import block_grammar
import coverage_alarm
import verse_numbers


def _line(text, x0, x1, y0=100, y1=140, role="body"):
    return {"text": text, "role": role, "conf": 0.9, "bbox": (x0, y0, x1, y1)}


def _psalm_page():
    """A Psalm-118-shaped page: numbered openings, indented continuations, full-measure annotations."""
    L = [
        _line("105 † a Thy word is a lampe to my feete", 290, 1160, 100, 140),
        _line("and a light to my pathes.", 340, 900, 145, 185),                    # continuation: indented
        _line("a The word or law of God is the ordinarie meanes", 190, 1345, 190, 230),  # annotation
        _line("106 † I ſware and haue determined", 290, 1160, 235, 275),
        _line("of thy iuſtice.", 340, 800, 280, 320),
    ]
    return {"page_px": (2200, 3090), "r2_body": " ".join(l["text"] for l in L), "lines": L}


# --------------------------------------------------------------------------- #
# block grammar
# --------------------------------------------------------------------------- #
def test_self_labelling_opening_is_detected_and_carries_its_verse_number():
    page = _psalm_page()
    blocks = block_grammar.parse_page(page)
    opens = [b for b in blocks if b["type"] == "verse-opening"]
    assert [b["self_label"] for b in opens] == [105, 106], \
        "an `N †` opening must yield its own verse number — that is what makes the regime self-labelling"


def test_continuation_and_annotation_are_separated_by_geometry_not_by_symbol():
    """Both lack a marker, so a symbol-only rule cannot tell them apart — which is exactly how the earlier
    prototype destroyed proverbs (0.943 -> 0.337) by deleting wrapped continuations as apparatus."""
    page = _psalm_page()
    types = {b["idx"]: b["type"] for b in block_grammar.parse_page(page)}
    assert types[1] == "verse-continuation", "an indented wrap must stay with its verse"
    assert types[2] == "annotation", "a full-measure line starting left of the block is apparatus"


def test_composition_folds_a_verse_and_its_wraps_into_one_run():
    runs = block_grammar.compose(block_grammar.parse_page(_psalm_page()))
    verses = [r for r in runs if r["type"] == "verse"]
    assert verses[0]["lines"] == [0, 1], "the verse run must absorb its continuation line"
    assert verses[0]["self_label"] == 105


def test_regime_detection_prefers_the_self_labelling_grammar():
    d = block_grammar.dispatch(_psalm_page())
    assert d["regime"] == "psalm-numbered" and d["self_labelling"] is True
    assert d["schema"]["self_labelling"] is True


def test_a_page_with_no_verse_markers_is_no_scripture_not_a_failure():
    """ot2-1610 p216 sits INSIDE the Psalm 118 range and is wholly the General Annotations treatise. Forcing
    verse localization onto such a page and then reporting failure would be the pipeline refusing to believe
    its own detector."""
    L = [_line("As this Pſalme is the longeſt in the whole Pſalter, ſo it ſemeth", 300, 1300),
         _line("to the ancient Fathers moſt profound in ſenſe.", 300, 1200, 145, 185)]
    page = {"page_px": (2200, 3090), "r2_body": " ".join(l["text"] for l in L), "lines": L}
    d = block_grammar.dispatch(page)
    assert d["regime"] == "no-scripture"
    assert d["schema"]["segmenter"] is None, "no verse localization should be attempted on such a page"


def test_an_unfamiliar_marker_pattern_is_reported_not_forced():
    """Coverage question: an unseen book must either match a regime or be REPORTED unmatched. Silently
    forcing it into the nearest regime is how a book-specific model fails invisibly."""
    assert "unmatched" in block_grammar.SCHEMA
    assert block_grammar.SCHEMA["unmatched"]["self_labelling"] is False


# --------------------------------------------------------------------------- #
# verse-number recovery
# --------------------------------------------------------------------------- #
def test_gutter_crop_includes_context_not_just_the_digits():
    """MEASURED (2026-07-27): bare digit slivers recovered NOTHING from olmOCR on all 7 openings of the
    psalms-118 page; the same crops widened to include the opening words read the numbers correctly."""
    page = _psalm_page()
    crops = verse_numbers.gutter_crops(page)
    assert crops, "verse openings must yield gutter crops"
    for (cx0, _cy0, cx1, _cy1) in crops.values():
        assert cx1 - cx0 > 0.20, "the crop must carry textual context, not only the number"


def test_number_is_read_from_the_token_before_the_marker_despite_glyph_confusion():
    """Position identifies the token as a verse number, so 'III †' (111) and '1c9 †' (109) are read as
    numbers. The same substitutions applied to free text would corrupt words."""
    assert verse_numbers.parse_number("III † For inheritance I haue purchaſed") == 111
    assert verse_numbers.parse_number("1c9 † My ſoule is in my handes") == 109
    assert verse_numbers.parse_number("105 † a Thy word is a lampe") == 105
    assert verse_numbers.parse_number("no number at all here") is None


def test_out_of_order_numbers_are_refused_not_used():
    """A wrong verse number relabels a correct span WITH CONFIDENCE — strictly worse than no number."""
    vetted = verse_numbers.vet_sequence({1: 105, 2: 110, 3: 2, 4: 111})
    assert vetted[3]["ok"] is False and "out-of-order" in vetted[3]["reason"]
    assert vetted[1]["ok"] and vetted[2]["ok"]


def test_numbers_outside_the_chapter_are_refused():
    vetted = verse_numbers.vet_sequence({1: 5, 2: 900}, expected=[5, 6, 7])
    assert vetted[1]["ok"] is True
    assert vetted[2]["ok"] is False


def test_recover_never_guesses_when_the_reader_fails():
    page = _psalm_page()

    def broken(_od, _pi, *, crop=None, verse=None):
        raise RuntimeError("reader down")

    out = verse_numbers.recover(page, "d", 0, transcribe=broken)
    assert out["n_accepted"] == 0 and out["notes"], "a failed read must be an absence with a note, not a guess"


def test_anchors_expose_verse_to_line_mapping():
    page = _psalm_page()

    def reader(_od, _pi, *, crop=None, verse=None):
        return "105 † a Thy word is a lampe"

    out = verse_numbers.recover(page, "d", 0, transcribe=reader)
    a = verse_numbers.anchors(page, out)
    assert a and all(isinstance(k, int) for k in a), "anchors map verse number -> line index"


# --------------------------------------------------------------------------- #
# the page-level catastrophic-failure alarm
# --------------------------------------------------------------------------- #
def test_alarm_consults_every_reference_and_keeps_the_best():
    """s_dismas gives 2-Esdras 7 seventy verses where sabates_a gives seventy-three, so a single-source alarm
    scored a correctly-read page at 0.06 and would have sent it to an expensive rung that cannot help it."""
    import verse_seg as VS
    janv = VS.chapter_verses("2-esdras", 7, VS.JANVIER)
    spans = {v: {"text": t} for v, t in list(janv.items())[:8]}
    cov = coverage_alarm.page_coverage(spans, "2-esdras", 7)
    assert cov["fidelity"] > 0.8, f"perfect text scored {cov['fidelity']} — the reference cascade is broken"
    assert len(cov["per_ref"]) > 1, "every covering reference must be reported, not just the winner"


def test_alarm_fires_when_no_reference_recognises_the_page():
    spans = {v: {"text": "xqz mmm lll ttt zzz qqq vbn plmk foo bar baz"} for v in range(1, 8)}
    cov = coverage_alarm.page_coverage(spans, "genesis", 24)
    assert cov["alarm"] is True and any("fidelity" in r for r in cov["reasons"])


def test_alarm_does_not_fire_on_a_page_boundary_fragment():
    """A chapter with two verses on the page cannot distinguish 'grammar misfired' from 'that verse is a
    fragment'. An alarm that fires on every page boundary is one that gets ignored."""
    spans = {1: {"text": "garbled"}, 2: {"text": "also garbled"}}
    cov = coverage_alarm.page_coverage(spans, "genesis", 24)
    assert cov["alarm"] is False and cov["low_evidence"] is True


# --------------------------------------------------------------------------- #
# ALARM 5 — the structural alarm the four content alarms cannot raise
# --------------------------------------------------------------------------- #
def test_alarm5_fires_when_a_span_contradicts_its_printed_number():
    """psalms-118 118:109 scored 0.0 vs gold while cross-source identity was 0.985 and confidence 0.973 —
    every CONTENT alarm saw a clean verse, because the text was clean; it belonged to a different verse.
    A printed number is about IDENTITY, not quality, which is why it catches what the others cannot."""
    import xsrc_gate
    spans = {109: {"text": "text of some other verse", "lines": [20, 21]},
             110: {"text": "sinners laid a snare", "lines": [30]}}
    bad = xsrc_gate.anchor_disagreement(spans, {109: 34, 110: 30})
    assert 109 in bad and "disagree" in bad[109]
    assert 110 not in bad, "a span that covers its own printed number must NOT fire"


def test_alarm5_fires_when_a_printed_verse_was_never_localized():
    import xsrc_gate
    bad = xsrc_gate.anchor_disagreement({110: {"text": "x", "lines": [30]}}, {109: 34, 110: 30})
    assert 109 in bad and "did not localize" in bad[109]


def test_alarm5_catches_a_span_that_absorbed_a_neighbours_opening():
    """The same fault from the other side: the mislabelled verse may not be anchored itself, so the check
    must also fire on the span that swallowed someone else's printed opening."""
    import xsrc_gate
    spans = {105: {"text": "a very long run", "lines": [9, 10, 30]}}
    bad = xsrc_gate.anchor_disagreement(spans, {110: 30})
    assert 105 in bad and "absorbed" in bad[105]


def test_alarm5_escalates_through_the_gate():
    import xsrc_gate
    import verse_seg as VS
    janv = VS.chapter_verses("genesis", 24, VS.JANVIER)
    body = " ".join(janv[v] for v in sorted(janv))
    spans = VS.segment(body, janv)
    for d in spans.values():
        d["lines"] = [0]
    clean = xsrc_gate.cross_source_verse_scores(body, "genesis", 24, spans=spans)
    v = sorted(clean)[3]
    assert clean[v]["escalate"] is False, "a clean verse should not escalate before alarm-5 is given anchors"
    with_anchor = xsrc_gate.cross_source_verse_scores(body, "genesis", 24, spans=spans, anchors={v: 99})
    assert with_anchor[v]["escalate"] is True and with_anchor[v]["anchor_mismatch"], \
        "a verse whose span does not cover its printed number must escalate"
