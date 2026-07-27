# -*- coding: utf-8 -*-
"""TDD spec for verse_locate — the anchor-walk verse localizer.

The premise: janvier tells us WHAT each verse says (near enough) but not how THIS edition sets it, so we use
the known text to find WHERE each verse sits on the page, then read the page there. These tests pin the
properties that make that safe, on synthetic pages carrying real janvier text at known token positions —
hermetic, no kraken, no model, instant.

The invariants under test are the ones whose violation we have actually measured:
  * MONOTONE, NON-OVERLAPPING spans — the structural fix for a verse absorbing the rest of the page;
  * ABSENCE IS FIRST-CLASS — an off-page verse is reported not-located, never given a plausible span;
  * the unmatched text is GIVEN BACK — a verse's span must include this edition's divergent wording, which by
    definition did not match janvier (trimming to the matched core cost 0.10 mean identity);
  * apparatus is the RESIDUE — whatever no verse claims is returned as apparatus rather than absorbed;
  * IDF weighting — on a repetitive list page the distinctive tokens, not the boilerplate, place the verse.
"""
from __future__ import annotations

import re

import pytest

import layout
import verse_geom
import verse_locate
import verse_seg


def _page(line_texts, page_px=(1000, 4000), lh=40):
    """A synthetic reocr_page-shaped dict: one body line per string, stacked top to bottom."""
    lines = [{"text": t, "role": "body", "conf": 0.9,
              "bbox": (100, 100 + i * lh, 900, 100 + i * lh + lh - 5)} for i, t in enumerate(line_texts)]
    body = layout.strip_verse_numbers(re.sub(r"\s+", " ", " ".join(line_texts)).strip())
    return {"page_px": page_px, "r2_body": body, "lines": lines}


def _janv(book, ch):
    return verse_seg.chapter_verses(book, ch, verse_seg.JANVIER)


# --------------------------------------------------------------------------- #
# core walk properties
# --------------------------------------------------------------------------- #
def test_locates_a_run_of_verses_in_order_and_monotonically():
    cv = _janv("psalms", 118)
    vv = list(range(9, 17))
    page = _page([cv[v] for v in vv])
    got = verse_locate.locate(page, "psalms", 118)["verses"]
    placed = [(v, got[v]["tok_lo"], got[v]["tok_hi"]) for v in vv if got[v]["tok_lo"] is not None]
    assert len(placed) >= 7, f"only {len(placed)}/8 verses located on a clean synthetic page"
    for (_v1, _lo1, hi1), (_v2, lo2, _hi2) in zip(placed, placed[1:]):
        assert lo2 >= hi1, "spans must be monotone and non-overlapping"


def test_no_span_runs_away_when_neighbours_are_absent():
    """The failure this module exists to prevent: on the real corpus a verse whose neighbours failed to anchor
    took 53 lines / 74% of the page. Here only ONE verse of the chapter is present, followed by a long stretch
    of unrelated material; its span must stay near its own length instead of swallowing the remainder."""
    cv = _janv("psalms", 118)
    filler = ["quite unrelated printed matter about other things entirely"] * 12
    page = _page([cv[9]] + filler)
    got = verse_locate.locate(page, "psalms", 118)["verses"][9]
    assert got["tok_lo"] is not None, "the one present verse should still be located"
    ref_len = len(verse_seg._toks(cv[9]))
    assert (got["tok_hi"] - got["tok_lo"]) <= 3 * ref_len, \
        f"span of {got['tok_hi'] - got['tok_lo']} tokens ran away from a {ref_len}-token verse"


def test_absent_verses_are_reported_not_located_never_given_a_span():
    """Page-boundary chapters are the common case in this corpus: most of a chapter is NOT on the page. A
    verse that is absent must say so — handing it a plausible-looking span is the silent degradation."""
    cv = _janv("psalms", 118)
    page = _page([cv[v] for v in (9, 10, 11)])
    got = verse_locate.locate(page, "psalms", 118)["verses"]
    far = [v for v in range(100, 120) if v in got]
    assert far, "expected the chapter to carry verses far from the page's range"
    for v in far:
        assert got[v]["tok_lo"] is None and got[v]["open"] and got[v]["reason"] == "not-located", \
            f"v{v} is not on this page but was given a span: {got[v]}"


def test_divergent_wording_inside_a_verse_is_kept_not_trimmed_away():
    """The whole point is to read THIS edition's wording, which by construction does not match janvier.
    Trimming each span to its matched core dropped exactly that text (measured cost ~0.03 mean identity on
    the gold pages), so variant wording BETWEEN a verse's anchors must survive into the span."""
    cv = _janv("psalms", 118)
    toks = cv[9].split()
    variant = " ".join(toks[:4] + ["ſundrie", "ſtraunge", "wordes"] + toks[4:])
    page = _page([variant, cv[10], cv[11]])
    got = verse_locate.locate(page, "psalms", 118)["verses"][9]
    assert "ſtraunge" in got["text"] or "straunge" in got["text"], \
        f"the edition's own divergent wording was trimmed away: {got['text']!r}"


def test_trailing_material_beyond_the_janvier_budget_is_not_reclaimed():
    """MEASURED PARAMETER CHOICE, pinned (2026-07-26). A verse reclaims unclaimed neighbouring tokens only up
    to the number of its OWN janvier tokens still unmatched. It is tempting to also allow a flat expansion
    budget proportional to verse length, since an edition can add words janvier lacks. Measured on the 177
    gold verses, that allowance degrades mean identity MONOTONICALLY — 0.0 -> 0.860, 0.10 -> 0.809,
    0.15 -> 0.782, 0.25 -> 0.700, 0.40 -> 0.654 — because on these pages the material sitting in the gap is
    APPARATUS. A verse whose janvier text matched in full therefore reclaims nothing."""
    cv = _janv("psalms", 118)
    page = _page([cv[9] + " an interleaved annotation gloſſe of other matter", cv[10]])
    r = verse_locate.locate(page, "psalms", 118)
    got = r["verses"][9]
    assert "annotation" not in got["text"], \
        f"apparatus was swallowed into the verse: {got['text']!r}"
    assert r["apparatus"], "the annotation must be reported as apparatus instead"


def test_unclaimed_material_is_returned_as_apparatus():
    cv = _janv("psalms", 118)
    page = _page([cv[9], "an interleaved annotation gloſſe of quite other matter", cv[10]])
    r = verse_locate.locate(page, "psalms", 118)
    assert r["apparatus"], "the interleaved annotation must surface as apparatus, not vanish"
    covered = {t for a in r["apparatus"] for t in range(a["tok_lo"], a["tok_hi"])}
    claimed = {t for d in r["verses"].values() if d["tok_lo"] is not None
               for t in range(d["tok_lo"], d["tok_hi"])}
    assert not (covered & claimed), "apparatus and verse spans must not overlap"


def test_spans_map_back_to_line_geometry():
    """The span is only useful if it reverse-looks-up to pixels — that is the 'find, then bound, then re-read'
    step. Each located verse must carry the line indices its tokens came from."""
    cv = _janv("psalms", 118)
    vv = [9, 10, 11]
    page = _page([cv[v] for v in vv])
    got = verse_locate.locate(page, "psalms", 118)["verses"]
    for i, v in enumerate(vv):
        if got[v]["tok_lo"] is None:
            continue
        assert i in got[v]["lines"], f"v{v} lives on line {i} but mapped to {got[v]['lines']}"


# --------------------------------------------------------------------------- #
# IDF weighting — the repetitive-list case
# --------------------------------------------------------------------------- #
def test_token_weights_rank_distinctive_tokens_above_boilerplate():
    toks = "the children of ater the children of telmon the children of accub".split()
    w = verse_locate.token_weights(toks)
    assert w["ater"] > w["the"] and w["telmon"] > w["children"] and w["accub"] > w["of"], \
        "proper names must outweigh the repeated scaffolding that makes list verses indistinguishable"


def test_repetitive_list_verses_are_placed_by_their_names():
    """2-Esdras 7 is the census list — every verse is 'the children of <name>'. Unweighted matching let the
    repeated scaffolding align across verse boundaries and a verse's span began inside its predecessor."""
    cv = _janv("2-esdras", 7)
    vv = [v for v in (52, 53, 54, 55) if cv.get(v)]
    if len(vv) < 3:
        pytest.skip("janvier text for the census verses unavailable")
    page = _page([cv[v] for v in vv])
    got = verse_locate.locate(page, "2-esdras", 7)["verses"]
    for i, v in enumerate(vv):
        if got[v]["tok_lo"] is None:
            continue
        assert i in got[v]["lines"], \
            f"census v{v} is set on line {i} but was placed on {got[v]['lines']} (scaffolding stole the anchor)"


# --------------------------------------------------------------------------- #
# the hybrid selector
# --------------------------------------------------------------------------- #
def test_best_spans_records_which_engine_produced_each_span():
    cv = _janv("psalms", 118)
    page = _page([cv[v] for v in (9, 10, 11)])
    got = verse_locate.best_spans(page, "psalms", 118)
    assert got, "the hybrid must return spans"
    for v, d in got.items():
        assert d.get("source") in ("walk", "align"), f"v{v} has no engine provenance: {d}"
        assert "fit" in d and "alt_fit" in d, "both engines' gold-free fits must be recorded, not just the winner's"


def test_best_spans_picks_the_better_janvier_fit():
    cv = _janv("psalms", 118)
    page = _page([cv[v] for v in (9, 10, 11)])
    got = verse_locate.best_spans(page, "psalms", 118)
    for v, d in got.items():
        assert d["fit"] >= d["alt_fit"], f"v{v} selected the worse-fitting engine ({d['fit']} < {d['alt_fit']})"


def test_janvier_fit_is_gold_free_and_detects_a_misplaced_span():
    """The selector signal: a span pointed at the WRONG PLACE diverges from janvier far more than any of this
    edition's spelling variation does, which is exactly the failure the hybrid needs to catch."""
    cv = _janv("psalms", 118)
    right = verse_locate.janvier_fit(cv[9], cv[9])
    wrong = verse_locate.janvier_fit(cv[40], cv[9])
    assert right > wrong + 0.3, f"janvier fit cannot separate a correct span ({right}) from a misplaced one ({wrong})"
    assert verse_locate.janvier_fit("", cv[9]) == 0.0


# --------------------------------------------------------------------------- #
# emission contract: verbatim surface + one shared coordinate system (2026-07-27, wiring prerequisites)
# --------------------------------------------------------------------------- #
def test_located_text_is_the_verbatim_page_surface_not_the_alignment_fold():
    """`verse_seg._afold` is documented 'for ALIGNMENT only (never emitted)': it lowercases and folds
    ſ→s, v→u, j→i, y→i and collapses doubled letters. The walk MATCHES on that fold but must EMIT the raw
    page text — emitting the fold would hand the diplomatic pipeline a modernized, case-flattened reading,
    i.e. destroy the very surface this project exists to preserve."""
    line = "Bleſſed are the vndefiled in the way: who walke in the law of the Lord."
    page = _page([line])
    got = verse_locate.locate(page, "psalms", 118)["verses"]
    spans = [d["text"] for d in got.values() if d["tok_lo"] is not None]
    assert spans, "the verse must localize on its own text"
    joined = " ".join(spans)
    assert "ſ" in joined, f"long-s was folded out of the emitted span: {joined!r}"
    assert "Bleſſed" in joined, f"case and doubled letters were folded out: {joined!r}"


def test_token_extents_are_raw_body_token_indices_shared_with_verse_seg():
    """Both segmenters must speak ONE coordinate system, or a downstream crop reads the wrong pixels.
    `verse_seg.segment` indexes RAW body tokens (its `keep[]` map); the walk drops punctuation-only tokens
    when folding, so its internal indices are a SUBSEQUENCE. The published `tok_lo/tok_hi` are raw."""
    cv = _janv("psalms", 118)
    page = _page([cv[v] for v in (9, 10, 11)])
    raw = page["r2_body"].split()
    got = verse_locate.locate(page, "psalms", 118)["verses"]
    for v, d in got.items():
        if d["tok_lo"] is None:
            continue
        assert d["tok_hi"] <= len(raw), f"v{v} extent {d['tok_hi']} exceeds the {len(raw)}-token raw body"
        assert d["text"] == " ".join(raw[d["tok_lo"]:d["tok_hi"]]), \
            f"v{v} text does not match its own raw extent — the two coordinate systems have drifted"


def test_best_spans_geometry_comes_from_the_SELECTED_engine():
    """Regression (found while wiring, 2026-07-27): `verse_seg` emits no `lines`, so a fallback that copied
    the WALK's line list onto align-sourced verses fired on EVERY align verse — a crop keyed to the losing
    engine's pixels while the text came from the winner. Lines must follow the selected span's own extent."""
    cv = _janv("psalms", 118)
    # an interleaved annotation on its own line makes the two engines DISAGREE geometrically: the walk leaves
    # the gloss unclaimed (v9 -> line 0) while global alignment absorbs it (v9 -> lines 0,1). Without that
    # disagreement the bug is invisible, which is why a clean page is not enough to pin it.
    page = _page([cv[9], "an interleaved annotation gloſſe of quite other matter here indeed", cv[10], cv[11]])
    _body, tok_line = verse_geom.build_body_tokmap(page["lines"])
    walk = verse_locate.locate(page, "psalms", 118)["verses"]
    got = verse_locate.best_spans(page, "psalms", 118)
    assert any(d["source"] == "align" for d in got.values()), \
        "this page must select at least one align span for the regression to bite"
    assert any(d["source"] == "align" and d.get("tok_lo") is not None
               and d["lines"] != (walk.get(v) or {}).get("lines", [])
               for v, d in got.items()), \
        "the two engines agree on every span here — the test can no longer detect the mix-up"
    for v, d in got.items():
        if d.get("tok_lo") is None:
            continue
        expect = sorted({tok_line[j] for j in range(d["tok_lo"], min(d["tok_hi"], len(tok_line)))})
        assert d["lines"] == expect, f"v{v} ({d['source']}) carries geometry from the other engine's span"


def test_seed_selection_is_reproducible_not_hash_order_dependent():
    """REGRESSION (2026-07-27). `_seed_positions` ranked candidate tokens with `sorted(SET, key=df)`: set-of-
    strings iteration is randomized per process (PEP 456), and a df-only key leaves ties broken by exactly
    that randomness — so which tokens seeded the search, and where verses landed, changed between identical
    runs (psalms-118 walk mean 0.811 vs 0.747 on two sweeps of the same cache). A result that will not
    reproduce cannot be measured against a threshold, so the ordering must be TOTAL."""
    ref = "ater telmon accub hatita sobai children".split()
    index = {t: [i] for i, t in enumerate(ref)}
    df = dict.fromkeys(ref, 3)                        # ALL TIED: only the tie-break can order these
    first = verse_locate._seed_positions(ref, index, df, max_seeds=3)
    for perm in (list(reversed(ref)), ref[2:] + ref[:2]):
        idx2 = {t: index[t] for t in perm}            # same mapping, different insertion order
        assert verse_locate._seed_positions(perm, idx2, df, max_seeds=3) == first, \
            "seed choice depends on token iteration order — the walk is not reproducible"


def test_best_spans_refuses_a_page_whose_body_and_lines_disagree():
    """The walk indexes the body reconstructed from `lines`; the aligner is handed the stored `r2_body`. They
    are the same string by construction, so divergence means the two arms are indexing different token streams
    and every emitted span mixes coordinate systems. That must raise, not silently produce spans."""
    cv = _janv("psalms", 118)
    page = _page([cv[9], cv[10]])
    page["r2_body"] = page["r2_body"] + " an extra tampered tail"
    with pytest.raises(ValueError, match="No Silent Degradation"):
        verse_locate.best_spans(page, "psalms", 118)
