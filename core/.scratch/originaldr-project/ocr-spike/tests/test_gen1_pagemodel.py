# -*- coding: utf-8 -*-
"""Spec for the Genesis 1 per-source page model — the rules read off the rendered leaves.

WHY THESE ARE PINNED. Every rule here was arrived at by rendering the actual page and looking at it, and each
one replaces something that fails: a running head that no `head_frac` can cut, an engraved initial the
recognizer emits as a stray digit, a band edge that admitted a margin word. They are cheap to re-derive
wrongly and expensive to re-derive rightly, so the properties are stated on synthetic pages with the same
geometry as the leaves they came from — hermetic, no kraken, no word-box file, instant.

The last test is the important one: it pins a rule that was measured and REJECTED, so a later session cannot
quietly wire it back in. Negative results are only cheap once.
"""
from __future__ import annotations

import gen1_pagemodel as PM

OD = "archive-ot1-1609"        # first edition: body band (0.140, 0.815), opening leaf p21
W, H = 2200, 3090


def _w(t, x0, x1, y0, y1=None):
    return {"t": t, "x0": x0, "x1": x1, "y0": y0, "y1": y1 if y1 is not None else y0 + 70}


def _page(rows):
    """One synthetic leaf. Each row is a list of words; kraken's own line grouping is irrelevant here because
    the model regroups by y, so everything is handed over as a single line."""
    return {"page_px": (W, H), "lines": [{"words": [w for r in rows for w in r]}]}


def _text(page, page_index, lex=None):
    return PM.body_text(OD, page_index, page, lex)


# --- the running head -------------------------------------------------------------------------------------

def test_running_head_is_cut_by_shape_not_by_y():
    """`GENESIs.` is dropped because it is a short all-capital topmost row, not because it is high.

    y cannot do this job: on `archive-holiebible-ot1` the running head of p33 ends BELOW the first real body
    line of p32, so any `head_frac` that cuts the one eats the other."""
    page = _page([[_w("GENESIs.", 958, 1333, 104, 187)],
                  [_w("grene", 408, 515, 161), _w("herbe,", 552, 697, 161)]])
    assert _text(page, 22) == "grene herbe,"


def test_a_head_shaped_row_below_the_top_is_kept():
    """Only the TOPMOST row is eligible. A capitalised short row inside the text block is scripture (`And God
    ſaid`, a divine name, an abbreviated reference set in caps) and must survive."""
    page = _page([[_w("grene", 408, 515, 161), _w("herbe,", 552, 697, 161)],
                  [_w("GOD", 408, 520, 240)]])
    assert _text(page, 22) == "grene herbe, GOD"


def test_a_long_capitalised_row_is_not_a_head():
    page = _page([[_w("AND", 400, 470, 104), _w("GOD", 490, 560, 104),
                   _w("SAID", 580, 650, 104), _w("LET", 670, 730, 104)]])
    assert "AND" in _text(page, 22)


# --- the engraved drop capital ----------------------------------------------------------------------------

def test_drop_cap_orphan_is_discarded():
    """The recognizer's reading of the ornamental initial is identified by WHERE it is, not what it says.

    Geometry taken from `archive-holiebible-ot1` p31 row 1, where the engraving comes back as `2` at x=348
    while that row's first real word begins at x=908. Left in, it also breaks the line-break rejoin: `hea-`
    glues to `2` and strands `uen`."""
    page = _page([[_w("hea-", 1668, 1748, 1120)],
                  [_w("2", 348, 348, 1188), _w("uen", 908, 961, 1188), _w("and", 1029, 1087, 1188)]])
    assert _text(page, 21) == "heauen and"


def test_a_normally_spaced_leading_word_is_not_an_orphan():
    page = _page([[_w("hea-", 1668, 1748, 1120)],
                  [_w("uen", 908, 961, 1188), _w("and", 1029, 1087, 1188)]])
    assert _text(page, 21) == "heauen and"


def test_opening_display_line_is_restored():
    """`NTHEbeginning` is one token because the display capitals are kerned tight and the initial is engraved;
    the restored reading is a datum about the leaf, keyed by the glued token so it cannot fire elsewhere."""
    page = _page([[_w("NTHEbeginning", 915, 1333, 1157), _w("created", 1481, 1624, 1157)]])
    assert _text(page, 21) == "IN THE beginning created"


def test_display_line_restoration_does_not_fire_off_the_opening_leaf():
    page = _page([[_w("NTHEbeginning", 915, 1333, 300)]])
    assert _text(page, 22) == "NTHEbeginning"


# --- the band edges ---------------------------------------------------------------------------------------

def test_left_edge_is_tested_on_the_word_start_and_right_edge_on_its_centre():
    """The two edges are different kinds of edge. `birdes` (x 257-364, centre 310) is a margin word that a
    centre test admits against a left bound of 308; `tree` (x 1752-1821) is body that a strict test would
    reject against a right bound of 1793, because words legitimately overhang the measure."""
    page = _page([[_w("birdes", 257, 364, 161), _w("grene", 408, 515, 161), _w("tree", 1752, 1821, 161)]])
    assert _text(page, 22) == "grene tree"


# --- words broken at the measure --------------------------------------------------------------------------

def test_hyphenated_break_is_rejoined_across_the_row():
    page = _page([[_w("wa-", 1679, 1746, 1423)], [_w("ters.", 904, 993, 1479)]])
    assert _text(page, 22) == "waters."


def test_lost_hyphen_is_rejoined_only_on_lexicon_evidence():
    """`pdf-S03a` prints the same break as `hea` + `uen` with no mark at all. Joining needs evidence that a
    break happened — neither fragment is a word of the book and their concatenation is — because joining every
    row boundary would glue `was` to `voide`."""
    lex = {"heauen", "was", "voide"}
    broken = _page([[_w("hea", 1696, 1754, 1157)], [_w("uen", 900, 959, 1239)]])
    assert _text(broken, 22, lex) == "heauen"
    assert _text(broken, 22, None) == "hea uen"        # without the lexicon the rule cannot fire

    whole = _page([[_w("was", 1715, 1791, 1157)], [_w("voide", 902, 1009, 1239)]])
    assert _text(whole, 22, lex) == "was voide"        # both are words: never joined


# --- a rule that was measured and rejected ------------------------------------------------------------------

def test_margin_orphan_gap_test_stays_default_off():
    """PINNED NEGATIVE RESULT — the SIXTH geometric attempt at apparatus separation, and it fails the same way.

    The left cross-reference column of `archive-holiebible-ot1` p36 (genesis 2) sits inside the witness's body
    band, so its words join body rows: `I and al the furniture of them.`, `kind 4 de ſeuenth day`,
    `li, lit. bleſſed the ſeuenth day`, `ſoule † Theſe are the generations`. The idea was to reuse the evidence
    `_drop_cap_orphans` already trusts — a leading token separated from its row by a gap many times the typical
    word gap — on every row rather than the first six of an opening leaf.

    MEASURED ON THE ACTUAL ROWS, and the evidence is simply not there:

        row2 `I and al …`            lead/typical 1.73   <- intruder
        row3 `of God ended his …`    lead/typical 1.62   <- REAL BODY TEXT
        row4 `kind 4 de ſeuenth …`   lead/typical -1.17  <- intruder, boxes OVERLAP
        row7 `ſoule † Theſe are …`   lead/typical 2.45   <- intruder

    A multiplier low enough to catch `kind` deletes `of God ended`, and x cannot separate them either (an
    intruder at 0.153 of page width against real body text at 0.162). At the default 4.0 the rule fires NOWHERE:
    chapters 1, 16, 2, 14 and 38 all score identically with `ODR_MARGIN_ORPHANS` on and off.

    The remedy the evidence points to is CONTENT AND SEQUENCE — a monotone alignment over the token stream, the
    way `verse_locate` anchors verses — not another geometric threshold. Kept wired-but-off with its numbers so a
    later session does not spend the same day rediscovering that geometry cannot do this."""
    assert PM.MARGIN_ORPHANS is False, "the margin-orphan strip must not be on by default"
    W = 2200
    # the measured shape: a real first word one word-space from its neighbour is NEVER stripped
    real = [[_w("of", 357, 400, 100), _w("God", 440, 520, 100), _w("ended", 560, 700, 100)]]
    assert PM._strip_margin_orphans([list(r) for r in real], W)[0][0]["t"] == "of"


def test_row_interrupt_filter_stays_default_off():
    """PINNED NEGATIVE RESULT — the EIGHTH failed attempt at this apparatus, and the first on the content axis.

    `row_interrupt` drops a leading run of row tokens when what REMAINS matches an n-gram of the chapter's
    ARCHAIC reference. On hand-picked failing rows it looks excellent (`and trie and out of thy kindred` ->
    `and out of thy kindred`). On the whole population it DELETES SCRIPTURE:

        chapter    1     16    12     2     38    17
        OFF      124/124 64/64 43/80 84/100 84/120 88/108
        ON       107/124 60/64 35/80 76/100 62/120 68/108

    Cause: the criterion is satisfied by shifting past a MISREAD word — k=0 finds no n-gram because the first
    token is an OCR error, k=1 does, so the error is deleted along with real text. A diplomatic transcription
    must keep a misread for a later rung to correct.

    Method note worth as much as the result: its three passing examples were all drawn from failing cells, i.e.
    exactly where stripping helps. Chapters 1 and 16 are sentinels on every measurement for this reason."""
    import row_interrupt as RI
    assert RI.ENABLED is False
    assert PM._row_interrupt_on() is False, "the content filter must not be on by default"


def test_split_glued_stays_default_off():
    """PINNED NEGATIVE RESULT — and the one whose METRIC lesson matters most.

    `split_glued` is the mirror of the accepted hyphen JOIN: split `oflife` into `of life` when the glued form is
    absent from the book's lexicon and both fragments are present. On the scoreboard it was the session's only
    systemic win — 50 chapters, HELPS 8, HURTS 1, net +8 cells, sentinels unmoved.

    Counting the TEXT it changes rather than the verdicts it flips: **1,356 tokens split across Genesis**, the
    commonest being real words torn into morphemes — `lawful` -> `law ful` (28x), `earthlie` -> `earth lie` (18x),
    `prayeth` -> `pray eth` (17x), `faithful` -> `faith ful` (14x). A +8 net concealed 1,356 corruptions, nearly
    all invisible because score-neutral or inside cells that already failed.

    Edit distance cannot separate the classes either: at 2 edits the garble `hofore` is correctly refused, but so
    are `oflife` and `pleasantto`, which is the only thing the rule existed to do."""
    assert PM.os.environ.get("ODR_SPLIT_GLUED", "0") == "0", "the glued-token split must stay off by default"
    lex = {"law", "ful", "of", "life"}
    assert PM.split_glued(["lawful"], lex) == ["law", "ful"], \
        "documenting the defect: a real word IS torn apart, which is why this stays off"


def test_left_margin_trim_stays_unwired():
    """PINNED NEGATIVE RESULT — do not wire `_trim_left_margin` into `body_rows`.

    Deriving a per-leaf body left edge from the median row start removes the genuine margin intruders on
    `archive-ot1-1609` p22 and ALSO strips the first real word off some forty rows across the four witnesses
    (`And it was ſo done` -> `ſo done`). Measured: odr_com mean 0.928 -> 0.907, s_dismas 0.747 -> 0.725,
    verses at 4/4 support 15 -> 11. One threshold cannot serve a ragged left edge — the same shape as every
    geometric apparatus filter this project has tried. The intruders are a segmentation problem (§13 Q18).

    This test asserts the rule is NOT in the pipeline, and demonstrates on the measured geometry what it does
    when it is."""
    # A leaf whose left edge rags the way the real ones do: five rows on the modal edge near x=403, and one
    # scripture row outdented to x=320 — inside the body band, but the pattern behind `And God made a
    # firmament` losing its `And` on `jp2-S06` p18. The derived edge (median 403, less 0.02*W = 44) is 359.
    rows = [[_w("And", 320, 394, 100), _w("God", 430, 500, 100)],
            [_w("made", 400, 484, 170), _w("a", 520, 540, 170)],
            [_w("firmament,", 405, 560, 240), _w("and", 590, 650, 240)],
            [_w("diuided", 400, 530, 310), _w("the", 560, 610, 310)],
            [_w("waters", 403, 520, 380), _w("that", 550, 620, 380)],
            [_w("were", 402, 490, 450), _w("vnder", 520, 630, 450)]]
    trimmed = PM._trim_left_margin([list(r) for r in rows], W)
    assert [w["t"] for w in trimmed[0]] == ["God"], "the rejected rule eats the real leading word `And`"

    page = _page(rows)
    assert _text(page, 22).startswith("And God"), "body_rows must NOT apply the rejected trim"


# --- the foot of the leaf -----------------------------------------------------------------------------------

def test_catchword_at_the_foot_is_dropped():
    """The first word of the NEXT leaf, printed at the foot of this one as a binder's aid.

    Geometry from `archive-ot1-1609` p21, whose last row is `grene` alone at x 1639. Read leaf by leaf it is
    one stray token; read as a chapter stream it lands immediately before the word it duplicates, and gen 1:12
    arrives as `grene grene herbe` in all three 1609 witnesses."""
    page = _page([[_w("earth.", 368, 495, 100), _w("And", 528, 603, 100)],
                  [_w("after", 366, 460, 170), _w("his", 501, 553, 170)],
                  [_w("kinde,", 400, 500, 240), _w("ſuch", 530, 600, 240)],
                  [_w("grene", 1639, 1756, 320)]])
    assert _text(page, 22) == "earth. And after his kinde, ſuch"


def test_a_short_final_line_at_the_left_margin_is_kept():
    """A real last line of text is either long or begins at the left margin — the foot rule must not eat it."""
    page = _page([[_w("earth.", 368, 495, 100), _w("And", 528, 603, 100)],
                  [_w("after", 366, 460, 170), _w("his", 501, 553, 170)],
                  [_w("kinde,", 400, 500, 240), _w("ſuch", 530, 600, 240)],
                  [_w("done.", 366, 470, 320)]])
    assert _text(page, 22).endswith("done.")


def test_signature_mark_does_not_shield_the_catchword():
    """§13 Q34. The SIGNATURE shares the foot row with the catchword and is set to its LEFT, which defeated both
    halves of the foot test at once: `H3 to thy` (`pdf-S03a` p85) is THREE tokens, and `row[0]` is the signature
    near the middle of the page rather than the catchword out at 0.75 of the measure. The row was kept, the
    chapter stream put it immediately before the text it duplicates, and genesis 16:9 read `Returne to thy TO
    THY mistresse` — the last cell open in Genesis 16, and never an R3 fault."""
    page = _page([[_w("earth.", 368, 495, 100), _w("And", 528, 603, 100)],
                  [_w("after", 366, 460, 170), _w("his", 501, 553, 170)],
                  [_w("kinde,", 400, 500, 240), _w("ſuch", 530, 600, 240)],
                  [_w("H3", 1100, 1160, 320), _w("to", 1656, 1700, 320), _w("thy", 1720, 1790, 320)]])
    assert _text(page, 22) == "earth. And after his kinde, ſuch"
    # the letter and its number are often recognised as two tokens (`H 2 † Abram`, archive-holiebible-ot1 p89)
    page2 = _page([[_w("earth.", 368, 495, 100), _w("And", 528, 603, 100)],
                   [_w("after", 366, 460, 170), _w("his", 501, 553, 170)],
                   [_w("kinde,", 400, 500, 240), _w("ſuch", 530, 600, 240)],
                   [_w("H", 1050, 1090, 320), _w("2", 1110, 1140, 320),
                    _w("†", 1482, 1500, 320), _w("Abram", 1530, 1700, 320)]])
    assert _text(page2, 22) == "earth. And after his kinde, ſuch"


def test_a_short_final_line_beginning_with_a_capital_word_is_still_kept():
    """The bound on the rule above: stripping a leading signature must not turn a real short final line into a
    catchword. `In` is signature-shaped by pattern, so what saves this row is POSITION — the remaining tokens
    still begin at the left margin, where no catchword ever sits."""
    page = _page([[_w("earth.", 368, 495, 100), _w("And", 528, 603, 100)],
                  [_w("after", 366, 460, 170), _w("his", 501, 553, 170)],
                  [_w("In", 366, 420, 240), _w("deede.", 440, 560, 240)]])
    assert _text(page, 22).endswith("In deede.")


def test_a_body_row_in_the_head_zone_is_kept():
    """§13 Q34, the second half of the same junction. `head_frac` used to delete every word above it, and on
    `pdf-S03a` p86 the head `62 GENESIS.` sits at y=30 while the first BODY line — the continuation of genesis
    16:9 from the previous leaf — sits at y=97, under a cut at 0.055·H = 167. So the verse lost its own text
    even after the catchword was fixed. The head zone now only BOUNDS where a head is looked for; the shape test
    removes it, and a row in the zone that is not furniture survives."""
    head_y = PM.SOURCE_MODEL[OD]["head_frac"] * H
    assert head_y > 120, "fixture assumes the head zone reaches past the rows below"
    page = _page([[_w("62", 424, 470, 30, 90), _w("GENESIS.", 520, 900, 30, 90)],
                  [_w("to", 421, 460, 97, 160), _w("thy", 480, 540, 97, 160),
                   _w("miſtreſſe,", 560, 780, 97, 160)],
                  [_w("and", 424, 490, 171), _w("humble", 510, 690, 171)]])
    got = _text(page, 22)
    assert got == "to thy miſtreſſe, and humble", got


def test_a_bare_folio_number_in_the_head_zone_is_still_dropped():
    """The one furniture shape `_is_running_head` cannot judge — fewer than three letters — so it is named
    explicitly rather than left to survive as a body token."""
    page = _page([[_w("62", 424, 470, 30, 90)],
                  [_w("to", 421, 460, 97, 160), _w("thy", 480, 540, 97, 160)]])
    assert _text(page, 22) == "to thy"


def test_two_part_running_head_needs_label_punctuation():
    """`GENESIS. Creation.` is a head; `And God` opening a body line is not.

    The second edition's head is only 53% capitals, so the ratio test misses it. The extra signature must stay
    narrow: keyed on initial-capital alone, this rule deleted body rows beginning `And God`."""
    head = _page([[_w("GENESIS.", 904, 1200, 104, 187)],
                  [_w("ſeed,", 494, 600, 292), _w("fruit", 630, 700, 292)]])
    assert _text(head, 22) == "ſeed, fruit"

    two = _page([[_w("GENESIS.", 904, 1100, 104, 187), _w("Creation.", 1130, 1400, 104, 187)],
                 [_w("ſeed,", 494, 600, 292), _w("fruit", 630, 700, 292)]])
    assert _text(two, 22) == "ſeed, fruit"

    body = _page([[_w("And", 400, 470, 104), _w("God", 490, 560, 104)],
                  [_w("ſeed,", 494, 600, 292), _w("fruit", 630, 700, 292)]])
    assert _text(body, 22).startswith("And God"), "a body line of two capitals is not a running head"


def test_sloping_line_stays_one_row():
    """A printed line rising 35px across the measure must not split and interleave with its neighbour.

    Geometry from `archive-holiebible-ot1` p32, the defect that made S9 gen 1:21-29 read as word salad: the
    row reference follows the LAST word added, not the first, so the step stays small however far the line
    rises overall."""
    page = _page([[_w("4.", 336, 360, 1157, 1207), _w("ouer", 421, 514, 1145, 1195),
                   _w("the", 546, 596, 1133, 1183), _w("earth", 633, 721, 1129, 1179),
                   _w("vnder", 768, 879, 1129, 1179), _w("firmament", 999, 1226, 1122, 1172)]])
    assert _text(page, 22) == "ouer the earth vnder firmament"


# --- Rung-3 residual discipline ------------------------------------------------------------------------------

def test_r3_crop_transcript_is_localized_before_scoring():
    """A VERSE CROP IS NOT A VERSE, and scoring one whole is the trap that made six good re-reads read as 0.000.

    `verse_geom.verse_crops` returns the band of LINES a verse occupies, so the crop carries its neighbours.
    The R3 text must be cut down to the verse — on the janvier grid, never on the scoring reference — before it
    is compared to s_dismas/odr_com."""
    import gen1_r3

    whole = ("that beareth fruite, hauing ſeede eche one according to his kinde. And God ſaw that it was good. "
             "† And there was euening & morning that made the third day. † Againe God")
    got = gen1_r3.localize_in_crop(whole, 13, {12, 13, 14})
    assert "euening" in got and "morning" in got
    assert "beareth" not in got, "verse 12's text must not be scored as verse 13"
    assert "Againe" not in got, "verse 14's first word must not be scored as verse 13"


def test_r3_localization_needs_all_three_candidates():
    """The candidate set is not redundant. `verse_seg.segment` on the restricted grid leaves gen 1:13's trailing
    `Againe` attached (too little of v14 in the crop to anchor it, 1.000 -> 0.883); only the hybrid
    `best_spans` walk arm trims it. Selection between them is on the gold-free JANVIER fit."""
    import gen1_r3
    import verse_seg as VS

    text = "† And there was euening & morning that made the third day. † Againe God"
    grid = {v: t for v, t in (VS.chapter_verses("genesis", 1, VS.JANVIER) or {}).items() if v in (13, 14)}
    restricted = ((VS.segment(text, grid) or {}).get(13) or {}).get("text") or ""
    chosen = gen1_r3.localize_in_crop(text, 13, {13, 14})
    assert len(chosen.split()) <= len(restricted.split()), \
        "the selector must not be worse than the restricted grid alone"


def test_visual_content_and_surface_are_separate_paths():
    """`s_arbiter.arbitrate` must refuse a reading that changes CONTENT, and that guard must stay load-bearing.

    Reading `firmanent` -> `firmament` off the page is a content correction; routing it through the ſ-arbiter
    would let a content change enter as a surface adoption, unscored. The arbiter raised on exactly this, which
    is why `gen1_r3` keeps VISUAL_CONTENT and VISUAL_READINGS apart."""
    import pytest
    import s_arbiter

    # R3 CORRECTED R2 at token 4, so its ſ surface is unattested and the token is `unresolved` — the only
    # state in which `arbitrate` accepts a reading at all.
    res = s_arbiter.transfer("And God called the firmameut,", "And God called the firmanent,")
    assert 4 in {u["i"] if isinstance(u, dict) and "i" in u else u for u in (res.get("unresolved") or [])} \
        or res.get("unresolved"), "token 4 must be unresolved for this guard to be reachable"
    with pytest.raises(ValueError, match="changed content"):
        s_arbiter.arbitrate(res, {4: "firmament,"})


def test_r3_adoption_requires_clearing_the_bar():
    """No Silent Degradation, mechanically: a re-read that improves but stays short must NOT be adopted."""
    import gen1_r3

    better_but_short = {"s_dismas": 0.88, "odr_com": 0.88}
    incumbent = {"s_dismas": 0.85, "odr_com": 0.85}
    assert gen1_r3._governing(better_but_short) > gen1_r3._governing(incumbent)
    assert gen1_r3._governing(better_but_short) < 0.90, "so the ADOPT test below must fail it"


# --- GENESIS 15 / 3 / 6: the chapter models added 2026-07-31, and the one that was rejected ------------------

def test_genesis_15_s6_leaf_bound_is_the_swept_value():
    """`jp2-S06` p74 is the first leaf on which an annotation column was separated GEOMETRICALLY, and it is
    per-leaf for the p50/p51 reason: p75 has no right column and its body runs out to x1803.

    Swept over ch15's cells (baseline 64/84): 0.825->64, 0.780->65, 0.765->66, 0.755->66, 0.746->66,
    0.740->66, 0.735->65, 0.730->65. The plateau is 0.740-0.765 and 0.746 is the MEASURED GUTTER MIDPOINT
    (body line-ends x1<=1647, margin column x0>=1673), so the bound is right for the reason it is right."""
    ov = PM.PAGE_OVERRIDE.get(("jp2-S06", 74))
    assert ov is not None, "the ch15 p74 bound must stay wired"
    lo, hi = ov["body"]
    assert 0.740 <= hi <= 0.765, "the right bound must stay inside the swept plateau"
    assert ("jp2-S06", 75) not in PM.PAGE_OVERRIDE, \
        "p75 must NOT inherit p74's bound — it has no right column and would lose scripture"


def test_genesis_15_opens_on_a_mixed_leaf_on_three_witnesses():
    """p74 carries the TAIL OF CHAPTER 14'S ANNOTATIONS above `CHAP. XV.` — a continuation leaf with no
    ANNOTATIONS heading, so `_is_annotation_leaf` cannot see it. `chapter_open_y` filters words before the rows
    are grouped, which removes it without touching that rule. Verified by reading the removed tokens: 636
    across the three witnesses, all annotation or argument, no scripture, and one word RESTORED (`excee-` +
    `ding` -> `exceeding`, which the intruding margin had been splitting)."""
    for od, page in [("archive-ot1-1609", 79), ("jp2-S06", 74), ("archive-holiebible-ot1", 89)]:
        cm = PM.CHAPTER_MODEL[(od, 15)]
        assert cm["open_page"] == page
        assert 0.0 < cm["chapter_open_y"] < 1.0
    assert ("pdf-S03a", 15) not in PM.CHAPTER_MODEL, \
        "S3's chapter-15 leaf is NOT located by the probe; a guessed open_page may not be encoded"


def test_genesis_6_s3_chapter_model_stays_rejected():
    """PINNED NEGATIVE RESULT (2026-07-31). Naming S3's opening leaf for genesis 6 costs one cell —
    ch6 69/88 -> 68/88, S3 0.8636 -> 0.8182, S1/S6/S9 unmoved — and the cell it loses is VERSE 1 itself.

    `open_page` does not merely ADD the leaf as a candidate, it PREFERS it over the chapter stream. This
    leaf's verse 1 reads `afterthat men began to be multiplied vpon Nearth` (0.862) against the stream's
    passing copy: the opening `AND` is gone AND the engraved initial is glued to the next word, so no
    `drop_cap` can recover it. Genesis 8 recorded the same selector from the other side, where the leaf was
    better and the stream had a word missing. Measure per witness before adding an entry."""
    assert ("pdf-S03a", 6) not in PM.CHAPTER_MODEL, \
        "the genesis-6 S3 entry is a measured regression and must stay out"
    for od in ("archive-ot1-1609", "jp2-S06", "archive-holiebible-ot1"):
        assert (od, 6) in PM.CHAPTER_MODEL, "the other three witnesses take the entry harmlessly"
