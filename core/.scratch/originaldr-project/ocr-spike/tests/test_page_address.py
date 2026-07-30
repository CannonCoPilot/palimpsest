# -*- coding: utf-8 -*-
"""Regression spec for `page_address` — pins the TEN measured defects so they cannot silently return.

Each of these was found by measurement on the real corpus, and each was silently corrupting addressing before
it was found. A comment cannot stop a later session from "simplifying" one back in; a test can.
"""
from __future__ import annotations

import page_address as PA


def _page(texts, roles=None, pi=0):
    roles = roles or ["body"] * len(texts)
    return {"page_index": pi,
            "lines": [{"text": t, "role": r, "bbox": (0, 10 * i, 100, 10 * i + 8)}
                      for i, (t, r) in enumerate(zip(texts, roles))]}


# ---------------------------------------------------------------- DEFECT 1: fit normalised by the chapter

def test_content_fit_does_not_prefer_short_chapters():
    """It normalised by the CHAPTER's tokens (the chapter's recall), so a long chapter could never score well
    on any single page: Psalm 118 (176 verses) scored 0.097 on its own page while short psalms scored ~0.19 on
    incidental words. Addressing is a PRECISION question — what fraction of THIS PAGE the chapter explains."""
    idx = PA.ChapterIndex([("psalms", 118), ("psalms", 122)])
    import verse_seg as VS
    long_ch = " ".join(VS.chapter_verses("psalms", 118, VS.JANVIER).values())
    page_toks = set(PA._fold(" ".join(long_ch.split()[:120])))     # a page-sized slice OF Psalm 118
    fits = idx.score(page_toks)
    assert fits[("psalms", 118)] > fits.get(("psalms", 122), 0.0), \
        "a page taken from Psalm 118 must score Psalm 118 above a short unrelated psalm"


# ---------------------------------------------------------------- DEFECT 2: start-position prior

def test_no_positional_prior_drags_a_mid_volume_slice_to_the_front():
    """A `-0.02*j` start prior reached -18 on a 900-position canon — an order of magnitude above any emission —
    so a slice legitimately beginning mid-volume was pulled to the front of the canon and the monotone
    constraint propagated that error through every page after it."""
    import verse_seg as VS
    janv = VS.chapter_verses("psalms", 100, VS.JANVIER)
    text = " ".join(janv.values())
    pages = [_page(text.split()[i * 40:(i + 1) * 40] or ["x"], pi=i) for i in range(3)]
    recs = PA.address_volume(pages, ["psalms"], use_headings=False)
    assert all(r["chapter"] > 50 for r in recs), \
        f"a slice of Psalm 100 must not be addressed to the front of the book: {[r['chapter'] for r in recs]}"


# ---------------------------------------------------------------- DEFECT 3: book front matter has no seat

def test_book_front_matter_is_a_real_position():
    """The DR prints a title/argument before chapter 1 of every book. With nowhere legal to sit, those pages
    pulled the path forward into chapter 2 and — staying in a chapter being free — it sat there, mis-addressing
    chapter 1 even where that page's own content scored it more than twice as high."""
    assert ("genesis", 0) in PA.canonical_positions(["genesis"])
    assert PA.canonical_positions(["genesis"])[0] == ("genesis", 0)


def test_front_matter_pages_are_addressed_not_dropped():
    pages = [_page(["THE ARGVMENT OF THIS BOOKE"], pi=0), _page(["THE ARGVMENT continued"], pi=1)]
    recs = PA.address_volume(pages, ["abdias"], use_headings=False)
    assert len(recs) == 2
    assert all(r["chapter"] is not None and r["book"] for r in recs), "every page must carry an address"


# ---------------------------------------------------------------- DEFECT 4: state space from a coverage claim

def test_state_space_comes_from_the_canon_not_a_coverage_claim():
    """tome-map claims archive-nt-1582 holds only matthew, mark and john — for a 765-page New Testament. Seeding
    the state space from that left 2john and colossians with NO legal position, so addressing scored 0/2 there:
    it could not represent the right answer. This is the same defect that mis-addressed colossians-3."""
    import page_address_eval as EV
    books = EV.volume_books("archive-nt-1582")
    for b in ("2-john", "colossians", "luke", "apocalypse"):
        assert b in books, f"{b} must have a legal position in an NT volume's state space"


# ---------------------------------------------------------------- coverage + pinning contracts

def test_every_page_gets_an_address():
    """The aim is total coverage: a page that cannot be addressed cannot be re-OCR'd."""
    pages = [_page(["some text that matches nothing at all"], pi=i) for i in range(4)]
    recs = PA.address_volume(pages, ["abdias"], use_headings=False)
    assert len(recs) == len(pages)
    assert all(r["book"] and r["chapter"] is not None for r in recs)


def test_psalm_headings_are_detected_despite_ocr_noise():
    """The Psalter heads chapters `PSALME I.`, not `CHAP. I`, and the recognizer mangles the display line
    (`PSALηE I.`). A strict CHAP-only matcher left the largest book in the OT volumes entirely unpinned."""
    assert PA._heading_chapter("PSALME I.") == 1
    assert PA._heading_chapter("PSALηE I.") == 1
    assert PA._heading_chapter("CHAP. IIII") == 4
    assert PA._heading_chapter("and he was bleſſed") is None


def test_pins_are_line_ranges_anchored_on_the_printed_heading():
    pages = [_page(["carry over text", "CHAP. II", "new chapter text"], pi=0)]
    recs = PA.pin_carry_chain(PA.address_volume(pages, ["abdias"], use_headings=True), pages)
    pins = recs[0]["pins"]
    assert any(s["source"] == "printed-heading" and s["lo"] == 1 for s in pins), pins


# ------------------------------------ DEFECT 6: the heading pattern did not match how the DR prints headings

def test_chapter_headings_are_detected_in_the_forms_the_dr_actually_prints():
    """MEASURED: the old pattern saw 2,372 of the corpus's 4,640 heading-bearing pages — 51%.

    Three print/recognition facts defeated it: headings are set LETTER-SPACED (`C H A P. I.`); the 1582/1610
    New Testaments abbreviate to `CHA.`, not `CHAP.`; and display capitals are misrecognised in a small stable
    set (`Cη`/`CN`/`CИ` for CH, `O`/`G`/`0` for C). `archive-nt-1582` therefore yielded SIX readable headings
    in 762 pages, and its Matthew was addressed from chapter 2 with chapter 1 never used at all.

    This matters twice over, because printed headings are BOTH the DP's pin evidence AND the held-out
    validation label — and the miss fell on exactly the letter-spaced and degraded pages, so the honest
    accuracy figure was computed on an easy-biased half of the evidence."""
    for text, expected in [("C H A. I.", 1),        # letter-spaced, NT `CHA.` abbreviation
                           ("CHA. XI.", 11),
                           ("O H A. I.", 1),        # C misread as O
                           ("CηA. XII.", 12),       # CH misread as Cη
                           ("C H A P. I.", 1),
                           ("CH A P. II.", 2),
                           ("C N A P. I.", 1),
                           ("GHAP. I.", 1),
                           ("CHAP. XXII.", 22),     # above XX — the old block_grammar lookup capped there
                           ("CHAPTER V.", 5),
                           ("CHAP. 14", 14)]:
        assert PA._heading_chapter(text) == expected, f"{text!r} -> {PA._heading_chapter(text)!r}"


def test_widened_heading_pattern_still_rejects_inline_citations_and_prose():
    """The widening must not buy recall with precision. `Cη. Ad` is the load-bearing case: with `re.I` on the
    NUMERAL it parsed as roman D = chapter 500, so the numeral is deliberately case-sensitive while the stem
    is not. Headings are set in caps; inline citations are not."""
    for text in ["Cη. Ad",                                            # marginal note, not a heading
                 "chap. 35. §.",                                      # lowercase inline citation
                 "and he came to the chap. 3 of",                     # citation in running prose
                 "Pſalme ii alſo accunenient prayer ſor anie C",      # ten words of prose
                 "THE GOSPEL ACCORDING TO S. MATTHEW"]:               # a running head, no numeral
        assert PA._heading_chapter(text) is None, f"{text!r} -> {PA._heading_chapter(text)!r}"


def test_one_roman_parser_not_two():
    """Defect shape #5/#6: `block_grammar._ROMAN` was a hand-typed lookup capped at XX while `page_address`
    used a correct subtractive parser, so the same heading read differently through the two call paths. The
    lookup is deleted, not extended — extending it only moves the cap."""
    import block_grammar as BG
    assert not hasattr(BG, "_ROMAN"), "the hand-typed roman lookup is back; it will diverge again"
    assert BG.roman("XXII") == 22 and BG.roman("CXI") == 111
    assert BG.roman("Ad") is None


def test_letter_spaced_display_lines_are_one_word_not_five():
    """The `len(text.split()) > 4` display-line test rejected `C H A P. I.` as 'a sentence'. It compounded
    with the pattern defect: both failed on precisely the most letter-spaced pages."""
    import block_grammar as BG
    # The roman `I.` is itself a single-character token, so it collapses into the same display run — which is
    # fine and is the point: what the guard needs is the WORD COUNT, and a fully letter-spaced heading is one.
    assert len(BG.display_words("C H A P. I.")) <= 4
    assert len(BG.display_words("C H A P. XXII.")) <= 4          # a multi-char numeral stays its own word
    assert len(BG.display_words("and he came to the chap. 3 of")) > 4


# --------------------------- DEFECT 7: the persisted accuracy field measured a set the label helped build

def test_heldout_accuracy_does_not_consult_a_set_the_heading_helped_build():
    """CIRCULAR VALIDATION, SECOND OCCURRENCE. The old check asked whether the printed chapter was in
    `chapters_on_page` — but `address_volume` unions `printed_heading_lines(p)` into `chapters_on_page`
    unconditionally, held-out mode included. It returned exactly 1.0 on all eleven volumes in BOTH modes, and
    it was the figure written to the artifact while the honest one went only to stdout.

    The honest predicate is the one the heading cannot influence: printed chapter vs the DP's OWN chapter
    (allowing dp+1). On `jp2-S06` the two read 50.67% and 1.0 — the corpus's worst volume, fully masked."""
    recs = [  # a page whose heading says 9 while the DP placed it at 2: honestly wrong, circularly "right"
        {"printed_chapters": [9], "chapters_on_page": [2, 9], "carry_disagrees_with_dp": True},
        {"printed_chapters": [3], "chapters_on_page": [3], "carry_disagrees_with_dp": False},
    ]
    ho = PA.heldout_heading_accuracy(recs)
    assert ho["accuracy"] == 0.5, "the honest measure must count the disagreeing page as wrong"
    assert ho["circular_accuracy_do_not_quote"] == 1.0, \
        "the old measure scores this 100% — kept visible so the artifact shows why it is not the measure"


# ------------------- DEFECT 8: the chapter's line range took only the first printed-heading pin

def test_line_range_is_the_union_of_every_pin_naming_the_chapter():
    """MEASURED: taking only the FIRST `printed-heading` pin was wrong in BOTH directions, and only became
    visible once the heading parser could actually read the headings (defect #6).

    TRUNCATION — 3,006 pages, 67,284 body lines discarded. A chapter occupies TWO pin segments whenever its
    heading falls mid-page (second column, or a chapter reopening): a `carry-in` run before the heading and a
    `printed-heading` run after it. `jp2-S04` p680 is Apocalypse 1 across all 83 lines with `CHA P. I.` at
    line 44, so the old code returned (44, 82) and discarded lines 0-43 — taking Apoc 1:11-15 (janvier fit
    0.79-0.98) out of scope. That, not over-claim removal, is where 659 scan-verses went.

    OVER-CLAIM — 275 pages. A chapter with only a `carry-in` pin returned None, so the whole page was offered:
    the exact runaway this function exists to prevent, on the pages that straddle a chapter boundary."""
    import corpus_localize as CL
    same_chapter_twice = {"pins": [{"chapter": 1, "lo": 0, "hi": 43, "source": "carry-in"},
                                   {"chapter": 1, "lo": 44, "hi": 82, "source": "printed-heading"}]}
    assert CL._line_range(same_chapter_twice, 1) == (0, 82), "the chapter owns both of its segments"

    straddling = {"pins": [{"chapter": 5, "lo": 0, "hi": 20, "source": "carry-in"},
                           {"chapter": 6, "lo": 21, "hi": 60, "source": "printed-heading"}]}
    assert CL._line_range(straddling, 5) == (0, 20), "a carry-in-only chapter must NOT get the whole page"
    assert CL._line_range(straddling, 6) == (21, 60)
    assert CL._line_range(straddling, 9) is None, "a chapter with no pin has no honest range"


# --------------------------------- DEFECT 9: page furniture accepted as a chapter heading

def test_a_heading_below_the_last_body_line_is_furniture_not_a_heading():
    """A HEADING MUST HEAD SOMETHING. 68 of the corpus's 4,085 detected headings (1.7%) sit below the page's
    last body line — forward references, signature lines, catchword neighbours. Under a MONOTONE DP one of
    those is not a small error, it is an erasure.

    MEASURED, `jp2-S06` p1085: line 50 of 52 reads `Pſal. 30`, below the last body line, after a catchword and
    beside the next leaf's `T H E B O O K` header. Read as a heading it is decisive (+4.0), so the page went to
    Psalm 30 — and since the chain cannot go back, p1086-1088 were dragged to 30 with it. Content alone had
    them right (27, 28, 28, 29); p1086 carries Vulgate Ps 28:6-7, "breake them in pieces as a calfe of Libanus
    … the voice of our Lord diuiding the flame of fire". Three psalms vanished on one line of furniture, and
    it cost 11 verse loci of corpus coverage."""
    def page(rows):
        return {"lines": [{"role": r, "text": t} for r, t in rows]}

    furniture = page([("body", "8. Our Lord is the ſtrength of his people"),
                      ("catchword", "(h) God"),
                      ("body", "Pſal. 30"),          # <- the killer: heads nothing on this page
                      ("header", "T H E B O O K")])
    assert PA.printed_heading_lines(furniture) == {}, "furniture below the last body line is not a heading"

    real = page([("header", "OF PSALMES"), ("body", "PSALME XXX."),
                 ("body", "In thee o Lord haue I hoped")])
    assert PA.printed_heading_lines(real) == {30: 1}, "a heading with text under it must still be taken"


def test_evidence_and_pins_never_disagree_about_what_the_page_prints():
    """`page_evidence` used to run its OWN heading scan one line below a comment saying it must not — the
    project's recurring defect shape (one rule, two copies) in its purest form. It now calls
    `printed_heading_lines`, so a guard added to one is a guard on both."""
    furniture = {"lines": [{"role": "body", "text": "8. Our Lord is the ſtrength"},
                           {"role": "body", "text": "Pſal. 30"}]}
    ev = PA.page_evidence(furniture, PA.ChapterIndex([("psalms", 30)]))
    assert ev["printed_chapters"] == [], "evidence must not see a heading the pinner rejects"
    assert ev["printed_chapters_observed"] == [], "nor may the held-out LABEL be built from furniture"


# ------------------- DEFECT 10: marginal apparatus merged INTO a body line by the line builder

def test_margin_prefix_is_stripped_by_position_not_by_vocabulary():
    """MEASURED: the DR sets annotations in a column beside the text, and the line builder merges a marginal
    fragment with the body text sharing its y-band into ONE line — so apparatus arrives inside a
    `role="body"` line, past every role filter downstream. `archive-ot1-1609` p58 line 9 is the note
    "Of this commandment, or …" with Genesis 9:1 running through it.

    Normalised by page width, 14.0% of S1's body lines, 12.4% of S3's and 13.6% of S9's begin well left of
    their page's body column; S6, set widest, is at 3.4%. Stripping by position moved the corpus
    pass_rate_archaic 0.5919 -> 0.6300 and verse coverage 0.8187 -> 0.8535, and on Genesis it gained
    S1 +6.1, S3 +6.3, S9 +7.0 and S6 only +0.4 points — the gain tracks the defect's own distribution, which
    is what distinguishes a mechanism from a coincidence.

    IT MUST BE POSITION, NOT VOCABULARY. Dropping token runs that match no reference word was tested and
    rejected: those runs are dominated by CORRECT ARCHAIC SPELLINGS (`sone`, `therfore`, `daies`, `citie`,
    `geue`, `betwene`, `darkenes`, `uho`) that a modern-spelling grid cannot match, so the filter would delete
    scripture to raise a score."""
    import layout
    W = 6574
    lines = ([{"role": "body", "text": "clean scripture line of about this many characters here",
               "bbox": (1634, 100 * i, 5783, 100 * i + 60)} for i in range(6)]
             + [{"role": "body", "text": ":: Ofthis com. IL them::: Increaſe, & multiplie, and replenish the carth.",
                 "bbox": (281, 900, 5632, 960)}])
    out = layout.strip_margin_prefix(lines, W, keep_slack=0)
    assert out[:6] == [l["text"] for l in lines[:6]], "a line starting at the body column must be untouched"
    assert "Increaſe" in out[6] and "replenish the carth." in out[6], "scripture must survive the strip"
    assert "Ofthis" not in out[6], "the marginal fragment must not"


def test_margin_strip_errs_toward_keeping_text():
    """The bias is one-sided ON PURPOSE. Under-cutting leaves a few annotation tokens in the verse, which
    scores as noise and stays visible; over-cutting DELETES SCRIPTURE and scores as an improvement. Only one
    of those is recoverable, so a page whose body lines all start together must never be cut at all."""
    import layout
    lines = [{"role": "body", "text": f"line {i} of ordinary body text set flush to the column",
              "bbox": (400, 100 * i, 3000, 100 * i + 60)} for i in range(8)]
    assert layout.strip_margin_prefix(lines, 3200) == [l["text"] for l in lines]


def test_side_column_annotation_is_demoted_not_read_as_body():
    """The mirror of the merged-margin case. Where the LEFT-hand apparatus is concatenated into a body line,
    the RIGHT-hand apparatus gets its own line — which `type_lines` calls body, because the annotation column
    overlaps the text block's right edge instead of sitting in a clean outer margin.

    MEASURED, `archive-ot1-1609` p21: body lines start at x≈2352 of a 6428-wide page; line 38 is
    'ginninꝫ ofthe' at x=[5455, 6360], and it lands inside Genesis 1:4's span between "And God" and
    "ſaw the light". ~9-10% of body lines in all four Genesis witnesses match. Corpus effect:
    pass_rate_archaic 0.6300 -> 0.6387, verse coverage 0.8535 -> 0.8626.

    The 'starts well right of the body column' test is what protects the legitimate short line: the last line
    of a paragraph is short too, but it starts at the body column's LEFT edge."""
    import layout
    W = 6428
    lines = [{"role": "body", "text": f"ordinary body line number {i} running the full measure",
              "bbox": (2352, 100 * i, 6360, 100 * i + 60)} for i in range(9)]
    lines.append({"role": "body", "text": "and a short last line of the paragraph",
                  "bbox": (2352, 1000, 3600, 1060)})                    # short but LEFT-aligned -> keep
    lines.append({"role": "body", "text": "ginninꝫ ofthe",
                  "bbox": (5455, 1100, 6360, 1160)})                    # short and FAR RIGHT -> annotation
    drop = layout.drop_side_column_lines(lines, W)
    assert drop == {10}, f"only the far-right narrow line is a side column, got {drop}"


# ----------- DEFECT 11: the span selector had no tie-break, so a one-token span held a whole verse

def test_equal_fit_ties_are_broken_by_span_length_sanity():
    """MEASURED, `archive-holiebible-ot1` genesis 1. Pages 30 (front matter) and 31 (the real text) both carry
    chapter 1 in their interval, so both are offered. For verses 4, 5, 6, 9 and 11, page 30 produced a
    ONE-TOKEN span and page 31 an 18-, 13-, 19-, 20- and 26-token one — and BOTH scored `janvier_fit` 0.0,
    because the real text is present but too corrupt to match. The test was a strict `fit > incumbent`, so the
    tie went to whichever page was visited first, which is the front matter.

    Comparing Genesis 1 verses that ≥3 witnesses pass against those ≤2 pass, 11 of 18 low-support verses carry
    a span under half or over 1.5x the reference length and 0 of 13 high-support verses do — but the MEAN
    ratio does not separate them (1.07 vs 1.01). Only the extremes carry the signal, which is why this is a
    tie-break and not a scoring term.

    NOTHING IS DROPPED AND NO SCORE CHANGES. A verse that is genuinely unreadable still fails; it now fails
    holding its own text instead of one token of somebody else's, which is also what the R3 re-OCR crop needs
    to point at the right region."""
    import corpus_localize as CL
    ref_len = 17
    one_token = {"text": "though", "fit": 0.0}
    assert CL._better(0.0, "And God ſaw the light that it was good and he diuided the light from darkenes",
                      one_token, ref_len), "at equal fit the sane-length span must win"
    real = {"text": "And God ſaw the light that it was good and he diuided the light from darkenes", "fit": 0.0}
    assert not CL._better(0.0, "though", real, ref_len), "...and must not be displaced by a one-token span"


def test_fit_still_decides_whenever_it_can():
    """The tie-break must never override the selector. A better-fitting span wins even if its length is less
    tidy, and a worse-fitting one loses even if its length is perfect — otherwise length would quietly become
    the scoring criterion."""
    import corpus_localize as CL
    incumbent = {"text": "a b c d e f g h i j", "fit": 0.50}
    assert CL._better(0.80, "a b c", incumbent, 10), "higher fit wins regardless of length"
    assert not CL._better(0.20, "a b c d e f g h i j", incumbent, 10), "lower fit loses regardless of length"


def test_partial_fit_arbitration_cannot_promote_a_fragment_over_a_verse_length_span(monkeypatch):
    """§13 Q36. `partial_fit` is the honest measure of a fit-0 contest — the length ratio kept `matthew/19/9`'s
    38-token span at F1 0.20 over a 23-token one at 0.51 — but used ALONE here it re-opens the very defect the
    test above pins. MEASURED on `archive-ot1-1609`: F1 alone moved `genesis/1/1` to page 4, the volume's FRONT
    MATTER (`in banisliment. The Slauonians and Gothes`), because a short fragment can out-score a long,
    badly-garbled reading of the real page. So the length BAND is the first key and F1 decides only among
    candidates that are plausibly the whole verse."""
    import corpus_localize as CL
    monkeypatch.setenv("ODR_PARTIAL_FIT", "better")
    ref = "And God ſaw the light that it was good and he diuided the light from the darkenes"
    rl = len(ref.split())
    garbled_real = {"text": "And God ſavv the ligllt tllat it vvas goode and lle diuided tlle liglit from tlle "
                            "darkenes vvhich", "fit": 0.0}
    assert not CL._better(0.0, "in banisliment. The Slauonians and Gothes", garbled_real, rl, ref), \
        "a short front-matter fragment must never displace a verse-length span, whatever its F1"
    # ...and within the band, F1 is allowed to decide.
    worse = {"text": "And God ſaw the light that it was xxx yyy zzz qqq www eee rrr ttt", "fit": 0.0}
    better = "And God ſaw the light that it was good and he diuided the light from the darkenes"
    assert CL._better(0.0, better, worse, rl, ref), "among in-band candidates the better F1 must win"


def test_partial_fit_arbitration_is_off_by_default(monkeypatch):
    """PINNED: not adopted. Without the flag, `_better` must behave exactly as the two tests above specify."""
    import corpus_localize as CL
    monkeypatch.delenv("ODR_PARTIAL_FIT", raising=False)
    ref = "And God ſaw the light that it was good and he diuided the light from the darkenes"
    one_token = {"text": "though", "fit": 0.0}
    assert CL._better(0.0, ref, one_token, len(ref.split()), ref)
    assert not CL._better(0.0, "though", {"text": ref, "fit": 0.0}, len(ref.split()), ref)


# ------- DEFECT 12: the apparatus-removal stages ran in an order that made the first one delete scripture

def test_side_column_demotion_must_run_before_the_margin_strips():
    """THE ORDER IS LOAD-BEARING. Both strips locate the text block by the median body-line x0. While the
    right-hand apparatus lines are still typed `body`, their x0 (≈5150 of a 6048-wide page) drags that median
    from ≈1075 to ≈2400 — so every legitimate line looks like it begins in the margin and the PREFIX strip
    cuts real scripture out of it.

    MEASURED, `archive-holiebible-ot1` p31: with the strips run first it removed "5 diuided the light" from
    L38, "light, Day, and the" from L39 and "mament made amidſt the" from L44 — deleting the text the strip
    exists to protect, and taking Genesis 1:5 with it. Demote first and the median lands on the text block.

    This is the failure the one-sided under-cut bias was supposed to make impossible, and it was not enough:
    a bias only helps once the ESTIMATE is anchored on the right thing."""
    import layout
    W = 6048
    # Proportions taken from the real page: 34 genuine body lines and 19 right-column apparatus lines, all
    # typed `body` on arrival. That mass is what moves the median x0 from 1075 to 2603.
    lines = [{"role": "body", "text": "ordinary body line running the full measure of the page",
              "bbox": (1075, 100 * i, 5124, 100 * i + 60)} for i in range(19)]
    # the chapter opening indents around the drop capital, which is the second legitimate x0 cluster
    lines += [{"role": "body", "text": "indented opening line beside the drop capital",
               "bbox": (2603, 2000 + 60 * j, 6005, 2060 + 60 * j)} for j in range(9)]
    hanging = len(lines)
    lines.append({"role": "body", "text": "5 diuided the light from the darkenes. And he called the",
                  "bbox": (947, 4000, 5124, 4060)})                     # verse-number hanging indent
    lines += [{"role": "body", "text": "ſter Eue be¬", "bbox": (5172, 5000 + 60 * j, 5875, 5060 + 60 * j)}
              for j in range(19)]                                       # the right-hand apparatus column
    bad = layout.strip_margin_prefix([dict(l) for l in lines], W, keep_slack=0)
    demoted = [dict(l) for l in lines]
    for i in layout.drop_side_column_lines(demoted, W):
        demoted[i]["role"] = "marginalia"
    good = layout.strip_margin_prefix(demoted, W, keep_slack=0)
    assert len(bad[hanging]) < len(lines[hanging]["text"]), \
        "this test is only meaningful if the wrong order actually truncates the line"
    assert good[hanging] == lines[hanging]["text"], \
        f"the verse-number hanging indent is scripture and must survive: {good[hanging]!r}"
