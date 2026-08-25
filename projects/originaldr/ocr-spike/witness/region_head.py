"""R2.1g / R2.2a -- the head-band REGION PRIMITIVE: RunningHead / MarginNote / MainText / ChapterHead.

⚠️ THIS IS NOT A PROBE LOCAL TO R2. It is the module that answers, for one leaf, *where does the
running head end and the text block begin, and which tokens belong to neither*. R2.1's head reader,
R2.2's printed page numbers, R12's layout typology and the Gate 9 region model consume THIS, so a
defect is fixed once. It is scored DIRECTLY on region assignment against a hand-labelled set
(`gold/head_regions_OT1-1609-B_400-419.json`), never only through the continuity rate it enables:
a component measured only through a downstream metric cannot be debugged when that metric moves.

════════════════════════════════════════════════════════════════════════════════════════════════
WHAT MEASUREMENT ESTABLISHED, AND WHAT IT OVERTURNED (2026-08-17, leaves 400-419, OT1-1609-B)
════════════════════════════════════════════════════════════════════════════════════════════════
The roadmap pre-registered option (1) as *"find the first baseline via the RUNNING-HEAD LEADING
GAP"*. ⚠️ **That mechanism is falsified on the first leaf of the window.** Leaf 400's running head
sits at ext=0.95 of the measure with a lead of 40.0px to the body -- EXACTLY the body pitch. There
is no gap to find. Leaf 403's running head *does* carry a 52px lead. So the leading gap is present
on some leaves and absent on others, and an instrument resting on it would fail silently on the
leaves where it is absent -- reporting a body line as the first line rather than abstaining.

Two signals do separate, and both are typographic properties of the EDITION rather than of the
error (Sir's anti-circularity ruling: an archetype must be nameable in the vocabulary of the BOOK):

  1. **The setting is justified.** Body lines are flush to a left edge AND a right edge that dozens
     of lines share. A running head is CENTRED and reaches neither. So the text block's measure is
     recoverable as the MODE of token edges, and "is this a body line" becomes "does it reach the
     measure", which is what justification means.

  2. **The head of the page is a HEADLINE BAND, not a line.** It carries the running head flanked
     by the printed side-notes -- leaf 400's row 0 is `NVMERI` with `Og Alaine. Bal-` beside it;
     leaf 410's is `NVMERE.` with `Leuites n`. So a row is NOT homogeneous and region typing here
     must be per TOKEN. A row-level separator cannot express this page at all.

⚠️ **THE 411->412 FAILURE WAS MIS-DIAGNOSED, and the correction changes what must be built.** It is
recorded as `Cades` vs `'Temporal'` = "a RUNNING HEAD". It is not. Leaf 412's body row reads
`aTemporal | Cades of the deſert Sin | To whom Moyſes anſwered` -- `Temporal` is a MARGINAL NOTE
sharing a baseline with the body line, whose true opening `Cades` is the correct answer sitting in
the very next token. And the reason it was not excluded is measurable: `collation_read.text_measure`
takes rows wider than `0.75 * max(extent)`, so a row carrying a side-note INFLATES the maximum and
drags the left edge outward. Leaves 400 and 410 measure L=215 and L=248; **leaf 412 measures L=40**.
With the measure widened the note falls inside it, `in_measure` cannot exclude it, and it is read as
the first word. The head-side defect is therefore a MEASURE-CONTAMINATION defect, and it is fixed by
estimating the measure from a statistic a side-note cannot move -- which is the mode, not the max.

════════════════════════════════════════════════════════════════════════════════════════════════
DECISION RULES -- PRE-REGISTERED, WRITTEN BEFORE THIS MODULE WAS SCORED ON ANYTHING
════════════════════════════════════════════════════════════════════════════════════════════════
R1  MEASURE. Over every token of >=3 glyph components in the band, the block's left edge `L` is the
    token-left with the most neighbours within `0.35 * pitch`; the right edge `R` likewise over
    token-rights. ⚠️ A mode, never a max or a median-of-widest: a side-note is a MINORITY of tokens
    and cannot move a mode, which is exactly the property leaf 412 needs. Fewer than 3 supporting
    tokens on either edge is an ABSTENTION, not a guess.
R2  MARGIN. A token beginning left of `L - tol`, or ending right of `R + tol`, is a MarginNote,
    where `tol = max(0.35p, 0.03 * measure)` -- ⚠️ THE SAME `tol` R3 uses. Edge-based, not
    centre-based: leaf 401's `Balaam` straddles L and a centre test misses it.
R3  BODY ROW. A row is a body row iff it holds an in-block token flush to `L` or flush to `R`,
    within `max(0.35p, 0.03 * measure)`. ⚠️ **Either edge, not both and not left alone**: leaf 415's
    body line begins at +0.049 of the measure (an indent) and would be refused by a left-only test,
    while its last token reaches +1.000. Justification is a two-edge property and the test must be.
R4  In a body row, every in-block token is MainText.
R5  In a NON-body row, an in-block token whose centre lies within the middle half of the measure
    (0.25..0.75) is a heading; any other in-block token in such a row is a MarginNote -- this is what
    catches leaf 410's `Leuites n`, a side-note set INSIDE the measure that R2's edge test cannot see.
R6  The FIRST non-body row holding a heading token gives the RunningHead; heading tokens in later
    non-body rows are ChapterHead (leaf 411's `CHAP.` / `XXVII.`).
R7  ABSTAIN, NEVER GUESS -- house rule. Every entry point returns `(value, reason)` with exactly one
    set. A reader that guesses makes a null indistinguishable from a low reading (R1.4, R2.1-CRIT).

⚠️ NOTE ON WHAT IS *NOT* CLAIMED. `first_text_token` returns the opening of the first body row. That
this is the leaf's first line of scripture is true only where the band contains the top of the type
page; the caller states its own band. This module does not decide the band, and must not, because a
fixed fraction of page height is not anchored to the type block -- which is a separate defect,
raised as R2.2b rather than papered over here.
"""

import sys
from pathlib import Path as _P

_HERE = _P(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import numpy as np
import collation_read as CR

RUNNING_HEAD = "RH"
MARGIN_NOTE = "MN"
MAIN_TEXT = "MT"
CHAPTER_HEAD = "CH"
ARGUMENT = "AR"

# ══════════════════════════════════════════════════════════════════════════════════════════════
# R2.2d -- R3b, THE ARGUMENT RULE. DEFAULT OFF until it clears D1-D4 (pre-registered in the roadmap).
# ══════════════════════════════════════════════════════════════════════════════════════════════
# THE DEFECT, measured 2026-08-18 while scoring R2.2b/A1. Between `CHAP. XXVII.` and the first verse
# this edition sets a multi-line ITALIC ARGUMENT -- 4 detected rows on leaf 403, ELEVEN on leaf 411.
# It is justified to the full measure, so R3's body-row test passes on it and R4 labels every token
# in it MainText. ⇒ ON A CHAPTER-OPENING LEAF THE HEAD READER RETURNS THE ARGUMENT'S OPENING WORDS
# AS THE LEAF'S FIRST LINE OF SCRIPTURE. Ninth instance of this project's signature defect.
#
# ⚠️ THE RULE IS A FOUNT TEST, NOT A POSITION TEST. "Between the ChapterHead and the first verse"
# would be circular -- it presumes the boundary it must find, and is silent wherever the chapter head
# was missed. `CR.row_slant` measures what the BOOK distinguishes: italic against roman.
#
# ⚠️ THE THRESHOLD IS ABSOLUTE, AND THAT IS AN ASSUMPTION WITH A GUARD. Roman is upright BY
# DEFINITION, so 0 is not a fitted value; but a skewed scan shifts every row together. The consumer
# therefore checks `CR.page_slant_mode` against `ARGUMENT_UPRIGHT_TOL` and ABSTAINS on a leaf whose
# roman is not upright, rather than labelling its scripture italic. A page-RELATIVE threshold was
# rejected on measurement: leaf 411's head band is 11 argument rows of 17, so a band-local reference
# is itself italic and the rule would invert.
ARGUMENT_RULE = False           # ⚠️ OFF. Turning it on silently would restate R2.1g's numbers under
                                # a rule that has not passed its own acceptance.
ARGUMENT_SLANT_MIN = 8.0        # degrees. Midway between upright roman and this edition's italic.
ARGUMENT_MIN_COMPONENTS = 8     # a row too small to support a slant estimate does not get a fount
ARGUMENT_UPRIGHT_TOL = 3.0      # the leaf's roman must be within this of upright, or the consumer
                                # abstains -- see `CR.page_slant_mode`

MIN_GLYPHS = 3          # a token below this is a speck or a fragment; it does not vote on geometry

# R2.1k CANDIDATE, DEFAULT "tokens" (unchanged behaviour). How R3 measures a row's extent.
#   "tokens"  -- tokens surviving MIN_GLYPHS. The shipped rule, and the one leaf 414 exposed.
#   "ink"     -- the row's raw ink extent. 🔴 REFUTED, see `classify`.
#   "segment" -- the row's LONGEST REGION SEGMENT (R2.1h `region_segments`).
SPAN_MODE = "tokens"

# R2.2e CANDIDATE, DEFAULT OFF. A TOKEN MAY NEVER SPAN A REGION GAP.
# 🔴 THE DEFECT IT ADDRESSES, measured 2026-08-19 with `ARGUMENT_RULE` off, i.e. in the SHIPPING
# pipeline: the splitter sometimes emits ONE token covering an entire printed line -- leaf 412 r33
# is 63 glyphs spanning l=56..r=1215, 90% of the row. R2 below tests `l < L` or `r > R`, so a token
# that spans the measure NECESSARILY fails it and is labelled MARGIN_NOTE. **49 rows over the 20
# leaves are typed as marginalia that way, and 44 of them are ordinary scripture** -- `† And Moyses
# referred their people`, `the familie of the Noemanites. † The`, and 42 more.
# ⚠️ `region_segments` SPLITS THOSE SAME ROWS CORRECTLY (leaf 412 r33 -> a roman side-note at 1 deg
# plus the italic argument at 11 deg). Two splitters disagree about one row and THE COARSER ONE
# DECIDES THE LABEL: the signature defect again, this time in the splitter/label handoff.
# ⚠️ THE RULE IS THE BOOK'S, NOT THE ERROR'S (Sir's anti-circularity ruling): a gap wider than the
# line pitch is not a word space, it is a run out to another region -- `CR.REGION_GAP_P`, already
# relied on by `region_segments` and `band_word_gap`. This is a POST-CONDITION on whatever
# `split_fn` returns, not a second splitter: it can only CUT, never merge, and a token already
# inside one segment is returned untouched. Placed in `tokens` so that EVERY splitter inherits it --
# a post-condition applied at one call site is how the splitter under test and the splitter in
# production drift apart.
# ⚠️ Turning this on silently would restate R2.1g's headline numbers under a rule that has not
# passed its pre-registered acceptance (E1-E4, OCR-ROADMAP.md). It stays OFF until it does.
REGION_GAP_TOKENS = False

# R2.2e-b CANDIDATE, DEFAULT OFF. A TOKEN THAT SPANS THE MEASURE IS IN THE BLOCK.
# 🔴 THE DEFECT, measured 2026-08-20 after the first candidate was REFUTED: of the 43 body rows typed
# MarginNote, **41 are pure OVERSHOOT and 0 are merges**. Leaf 400 r46's 46-glyph token spans
# l=238..r=1174 against a modal R=1132 and a 27px tolerance -- it ends 42px past the edge, so R2
# types a full line of scripture as a marginal note. Their median share of the measure is 0.90 and
# many EXCEED 1.00: the token is longer than the block.
# ⚠️ R2 is a pure EDGE test with NO SIZE QUALIFICATION, and the modal edge is a MODE over many lines
# -- an individual justified line exceeding it is ORDINARY, not anomalous. Same family as R2.1k: a
# threshold answering a question it was not built for.
# ⚠️ THE RULE IS THE BOOK'S (anti-circularity): marginalia in this edition is set in a NARROW COLUMN
# BESIDE the measure, so a run of type that SPANS the measure is a line of the text block. The
# constant is R3's existing BODY_SPAN_M, not a new one -- it is the same idea ("a justified line is
# FULL"), and this module's header records what two tolerances for one edge already cost once.
# ⚠️ INTERACTS WITH `REGION_GAP_TOKENS` AND THE INTERACTION IS THE POINT: a token merged across a
# region gap (body + marginal note) ALSO spans the measure, so this qualifier ALONE would call the
# merge in-block and MASK it. The region-gap cut is the precondition; F4 measures both.
BLOCK_SPAN_QUALIFIES = False

# R2.2f CANDIDATE, DEFAULT OFF. R4 LABELS PER REGION SEGMENT, NOT PER ROW.
# 🔴 THE DEFECT, measured 2026-08-20 by R2.2e-b: leaf 412 r2's marginal note `pinces are` is 142px
# against a 1110px measure and sits INSIDE the block bounds -- on that leaf the marginal column and
# the measure are contiguous, so the modal L=48 falls LEFT of the note. It scored MarginNote only
# because its ROW was broken; repair the row and R4 below sweeps every in-block token on that
# baseline into MainText, the note with them. ⚠️ THE GOLD'S MN 0.8947 WAS RESTING ON THAT: two
# errors cancelled, and the first genuine repair exposed the second.
# ⚠️ This is this module's FOUNDING observation on a THIRD axis. A row is not homogeneous in REGION
# (which is why labels are per token) and not in FOUNT (R2.2d, measured) -- and R4's own row-to-token
# inheritance is the one place the module still assumes it is.
# ⚠️ THE RULE IS THE BOOK'S (anti-circularity): marginalia is set in a NARROW COLUMN BESIDE the
# measure, separated from the block by a run wider than the line pitch. `CR.region_segments` is that
# primitive, already relied on by R2.1h, R2.2d and `band_word_gap`; a body SEGMENT is one meeting
# R3's OWN test, the same two clauses and the same constants. No threshold is minted here.
# ⚠️ IT MAY ONLY DEMOTE. A row where NO segment qualifies keeps today's behaviour -- a row can pass
# R3 on its token-union span while no single segment does, and stripping MainText from such a row
# would be this rule answering a question it was not asked. `r4_seg` records which of the three
# fates each token took so the rule's REACH is measurable and the fallback is counted, not silent.
R4_PER_SEGMENT = False

# R2.2g CANDIDATE, DEFAULT "both" (unchanged behaviour). HOW R3 TESTS FLUSHNESS AT AN EDGE.
# 🔴 THE DEFECT, measured 2026-08-20 by R2.2f: R3 asks `abs(a - L) <= tol or abs(b - R) <= tol`, a
# SYMMETRIC WINDOW -- so it refuses a line for having too MUCH ink at the edge exactly as readily as
# too little. Leaf 412 r2's body segment spans 931px against an 832px bar (FULL) and misses flush by
# ending 45px past the modal R against a 33px tolerance. 20 of the 43 swallowed body rows hang on
# this test, and R2.2f cannot identify a body segment it refuses -- which is why R2.2f's own
# acceptance failed on a row it should have repaired.
# ⚠️ THE RULE IS THE BOOK'S (anti-circularity): justification is the compositor setting each line OUT
# TO the measure. Falling SHORT of it is unjustified; running PAST it by a hair of bearing, a hyphen
# or a swash is not. The modal edge is a MODE OVER MANY LINES and binds no individual line.
#   "both"        -- symmetric window at both edges. What ships, and what R2.2f measured against.
#   "reach"       -- one-sided at BOTH edges: flush iff `a <= L + tol` or `b >= R - tol`.
#   "reach_right" -- one-sided at R only; the left edge keeps the symmetric test.
# ⚠️ THE LEFT EDGE IS THE DANGEROUS HALF, hence three settings rather than one. `a <= L + tol` holds
# for ANY row whose leftmost ink is in the left margin -- i.e. every row carrying a marginal note --
# and R3's span clause could then promote it to a body row. This module has already lost RunningHead
# recall 1.0000 -> 0.7500 once to a promoted row (`SPAN_MODE = "ink"`, below), and H3 exists to catch
# a second time. Pre-registered as H1-H5 in OCR-ROADMAP.md.
FLUSH_MODE = "both"

# R2.2h CANDIDATE, DEFAULT OFF. THE EDGE ESTIMATOR AND THE EDGE TEST USE ONE TOLERANCE.
# 🔴 THE DEFECT, measured 2026-08-20 by R2.2g: `block_measure` finds the modal edge with
# `EDGE_TOL_P * p` = 13px at pitch 38, and `classify` then tests in-block with
# `max(0.35p, 0.03 * measure)` = 27px. The estimator's window is HALF the test's, the real scatter of
# justified line-starts in this edition is a smear ~80px wide, and so the mode lands in one bin of it:
# on leaf 403, 17 rows start LEFT of the modal L against 17 within tolerance; on 411, 20 rows end
# RIGHT of R. Three of R2.2g's 6 surviving rows have NO in-block solid token at all.
# ⚠️ TWO TOLERANCES FOR ONE EDGE -- the defect this module's header records having ALREADY paid for
# once (`edge_tol`/`flush_tol` unified in `classify`, continuity 0.312 -> 0.176 before the fix). The
# R2.1 fix never reached the estimator that PRODUCES the edge. Twelfth instance of the signature
# defect, and the reason it hid this long is that a rule and its input were fixed in different places.
EDGE_FIXED_POINT = False
EDGE_FIXED_POINT_MAX = 8        # iterations before ABSTAINING -- an oscillating fit is refuted, R7

EDGE_TOL_P = 0.35       # margin test, in pitches
FLUSH_TOL_P = 0.35      # justification test, in pitches
FLUSH_TOL_M = 0.03      # justification test, in fractions of the measure -- whichever is larger
BODY_SPAN_M = 0.75      # a justified line is FULL as well as flush; see R3
HEAD_MID = (0.25, 0.75)  # a heading is set into the middle half of the measure
MIN_EDGE_SUPPORT = 3    # tokens that must agree on an edge before it is an edge


def _modal_edge(values, tol):
    """The value with the most neighbours within `tol`, and its support count.

    A MODE, not a max and not a median-of-the-widest. The whole point is that a side-note is a
    minority of tokens: it can move a maximum by its own width, but it cannot move a mode at all.
    """
    if not values:
        return None, 0
    best, best_n = None, 0
    for v in values:
        near = [u for u in values if abs(u - v) <= tol]
        if len(near) > best_n:
            best, best_n = float(np.median(near)), len(near)
    return best, best_n


def _flush(a, b, L, R, tol):
    """R2.2g -- is a run of ink from `a` to `b` flush to the block at either edge?

    ONE definition read by BOTH call sites (R3's body-row test and R2.2f's body-segment test). They
    were written separately and asked the same question two ways for one day; a rule with two
    implementations is this project's signature defect, and R2.2f's refutation was legible only
    because both sites happened to agree. They agree BY CONSTRUCTION now.
    """
    if FLUSH_MODE == "reach":
        return a <= L + tol or b >= R - tol
    if FLUSH_MODE == "reach_right":
        return abs(a - L) <= tol or b >= R - tol
    return abs(a - L) <= tol or abs(b - R) <= tol


def _cut_at_region_gaps(spans, row, p):
    """R2.2e -- cut every span at the REGION GAPS inside it. Can only cut, never merge.

    A span is kept as-is unless the glyph boxes it covers contain a gap wider than the line pitch;
    then it is replaced by one span per `region_segments` group, each tightened to that group's own
    ink. A span covering no glyph box is passed through untouched rather than dropped -- this is a
    post-condition, and a post-condition that can DELETE evidence is not one.

    ⚠️ A DECODED span (`[l, r, read, conf]`) that gets cut LOSES its reading, deliberately: the text
    belonged to the whole crop, and re-attributing it to one of the pieces would be inventing a
    reading nobody made. `region_segments`' own docstring records what happens when a recogniser is
    handed a crop spanning two regions -- it fails at the boundary -- so a decoded span that needed
    cutting is exactly the case whose reading should not be trusted to either half.
    """
    out = []
    for sp in spans:
        l, rr = float(sp[0]), float(sp[1])
        inside = [g for g in row if g[2] >= l - 1 and g[3] <= rr + 1]
        if len(inside) < 2:
            out.append(sp)
            continue
        segs = CR.region_segments(inside, p)
        if len(segs) == 1:
            out.append(sp)
            continue
        for seg in segs:
            out.append([float(min(g[2] for g in seg)), float(max(g[3] for g in seg))])
    return out


def tokens(band, pitch, nrows=None, gap_fn=None, split_fn=None):
    """-> (list of token dicts, reason). Every token of the band, ungrouped and unclassified.

    Deliberately does NOT call `collation_read.in_measure`: this module's job is to decide what
    is inside the measure, so it must see what lies outside it.

    ⚠️ `split_fn(row, p) -> [[l, r], ...]` IS THE INJECTION POINT (R2.1h redesign). `gap_fn` is
    kept, and is now expressed THROUGH `split_fn` rather than beside it, because R2.1h's redesign
    takes the split from the recogniser's decoded spaces and a recogniser split is not a threshold
    at all. Folding the threshold rules into the general shape keeps ONE path through this
    function; a second branch here is how the splitter under test and the splitter in production
    drift apart. Passing both is an error rather than a precedence rule -- a silent precedence is
    exactly how a measurement ends up reporting an instrument that was not the one running.
    """
    if gap_fn is not None and split_fn is not None:
        raise ValueError("pass gap_fn or split_fn, not both -- see the docstring")
    if split_fn is None:
        split_fn = CR.gap_split(gap_fn)
    p = float(pitch)
    rows = CR._rows_and_lines(CR.glyph_boxes(band, 0, p), p)
    if not rows:
        return [], "no line of type in the band"
    # ⚠️ THE DEFAULT SPLITTER IS STILL THE PER-ROW 2-MEANS, and R2.1h's QUANTILE splitter is still
    # NOT adopted: it FAILED its pre-registered acceptance (exact 0.2500 against a 0.75 bar) even
    # though it improves MAE 3.50 -> 1.44 and removes the blob failure outright. A change that fails
    # its own bar is not adopted -- the same rule that keeps `chapter_model_derive` pinned OFF at
    # net -6. What changed at R2.1h's redesign is that a splitter can now be EVALUATED here at all:
    # wiring the quantile splitter in once collapsed the R2.1g region score from MN recall 0.8947 to
    # 0.5263 with the unlabelled count going 80 -> 212 and NOTHING about the regions changed, because
    # the gold was keyed by TOKEN ORDINAL and any change to the splitter silently renumbered every
    # key. R2.1i re-keyed the gold by band-pixel SPAN, so a splitter change now reads as what it is.
    # ⚠️ A row the splitter returns NO spans for contributes no tokens and is therefore invisible to
    # the measure. That is deliberate -- see `CR.make_recogniser_split` on why no gap fallback fires.
    out = []
    for j, r in enumerate(rows if nrows is None else rows[:nrows]):
        base = float(np.median([g[1] for g in r]))
        spans = split_fn(r, p)
        if REGION_GAP_TOKENS:
            spans = _cut_at_region_gaps(spans, r, p)
        for t, sp in enumerate(spans):
            l, rr = sp[0], sp[1]
            n = sum(1 for g in r if g[2] >= l and g[3] <= rr)
            # `row_l`/`row_r` are the ROW's ink extent, kept because `classify` pops `_row` and a
            # consumer that needs "how much of its line does this token span" must not re-derive the
            # row a second way to find out. `audit_prefix_rule` tests exactly that ratio.
            # R2.2j -- the token's OWN vertical extent, over the glyph boxes it covers. Kept because
            # a gold entry names a RECTANGLE of ink and an address needs both axes; `base` is a
            # single median and cannot say whether two runs of ink share a printed line. Falls back
            # to the row's extent when the span covers no glyph box, so the field is always present.
            inside = [g for g in r if g[2] >= l and g[3] <= rr]
            src = inside or r
            d = {"row": j, "tok": t, "l": float(l), "r": float(rr),
                 "y0": float(min(g[0] for g in src)), "y1": float(max(g[1] for g in src)),
                 "row_l": float(min(g[2] for g in r)), "row_r": float(max(g[3] for g in r)),
                 "base": base, "n_glyphs": n, "_row": r}
            # A splitter that DECODED the token carries its text and confidence with the span. A
            # consumer that re-reads a padded crop instead can disagree with the split it was given.
            if len(sp) >= 4:
                d["read"], d["conf"] = sp[2], sp[3]
            out.append(d)
    return out, None


def block_measure(toks, pitch):
    """-> ((L, R), reason). The text block's justified edges, by R1.

    ⚠️ ONLY THE FIRST AND LAST TOKEN OF EACH ROW VOTE. First written with every token voting, and
    leaf 412's measure collapsed to a sliver -- x_centre came out at +4.3 and +5.5 -- because the
    interior word-starts of a dozen justified lines are scattered, and a chance cluster among them
    outvoted the block edge. Justification is a statement about where a LINE begins and ends, not
    about where its words do, so the statistic has to be taken over line edges to mean anything.
    """
    p = float(pitch)
    solid = [t for t in toks if t["n_glyphs"] >= MIN_GLYPHS]
    if not solid:
        return None, f"no token carries {MIN_GLYPHS}+ glyph components"
    rows = {}
    for t in solid:
        a, b = rows.get(t["row"], (t["l"], t["r"]))
        rows[t["row"]] = (min(a, t["l"]), max(b, t["r"]))
    lefts = [a for a, _ in rows.values()]
    rights = [b for _, b in rows.values()]
    L, nL = _modal_edge(lefts, EDGE_TOL_P * p)
    R, nR = _modal_edge(rights, EDGE_TOL_P * p)
    if L is None or R is None:
        return None, "no modal edge could be taken"
    # R2.2h -- ONE TOLERANCE FOR ONE EDGE, reached by a FIXED POINT. The mode above is taken with
    # `EDGE_TOL_P * p` (13px at this edition's pitch) while `classify` decides in-block with
    # `max(0.35p, 0.03 * measure)` (27px): the ESTIMATOR'S WINDOW IS HALF THE TEST'S, so the mode
    # lands in one bin of an ~80px smear of true line-starts and whole body lines fall outside the
    # block -- leaf 403 has 17 rows starting left of L against 17 within it. The test's tolerance
    # depends on the measure the estimator produces, so the two are brought together by iterating to
    # a fixed point rather than by widening either one.
    # ⚠️ ABSTAIN, NEVER GUESS (R7): an iteration that does not settle returns a reason, and a
    # candidate that oscillates is refuted rather than damped. Pre-registered as J1-J7.
    if EDGE_FIXED_POINT:
        for _ in range(EDGE_FIXED_POINT_MAX):
            tol = max(EDGE_TOL_P * p, FLUSH_TOL_M * (R - L))
            L2, nL2 = _modal_edge(lefts, tol)
            R2, nR2 = _modal_edge(rights, tol)
            if L2 is None or R2 is None:
                return None, "no modal edge could be taken at the widened tolerance"
            settled = abs(L2 - L) < 0.5 and abs(R2 - R) < 0.5
            L, R, nL, nR = L2, R2, nL2, nR2
            if settled:
                break
        else:
            return None, (f"the edge fixed point did not settle in {EDGE_FIXED_POINT_MAX} "
                          f"iterations -- refusing to guess an edge")
    if nL < MIN_EDGE_SUPPORT or nR < MIN_EDGE_SUPPORT:
        return None, (f"edge support too thin: {nL} token(s) agree on the left edge and {nR} on the "
                      f"right, against a minimum of {MIN_EDGE_SUPPORT} -- refusing to call this a "
                      f"justified block")
    if R - L <= 0:
        return None, "modal edges are degenerate (R <= L)"
    return (L, R), None


def classify(band, pitch, nrows=None, gap_fn=None, split_fn=None):
    """-> (list of token dicts each carrying `label`, reason). Rules R1-R6, in order.

    ⚠️ THE MEASURE IS TAKEN OVER THE WHOLE BAND, THE LABELS ONLY OVER `nrows`. First written the
    other way and every one of the 20 leaves abstained: with three rows in view there are only two
    or three body lines, so at most two tokens can agree on an edge and R1's support minimum is
    never met. The measure is a property of the LEAF, not of the rows a caller happens to want, and
    estimating it from the caller's window makes a page-level constant depend on the question asked.
    """
    p = float(pitch)
    allt, why = tokens(band, p, nrows=None, gap_fn=gap_fn, split_fn=split_fn)
    if not allt:
        return None, why
    LR, why = block_measure(allt, p)
    if LR is None:
        return None, why
    toks = allt if nrows is None else [t for t in allt if t["row"] < nrows]
    L, R = LR
    measure = R - L
    # ⚠️ ONE TOLERANCE FOR ONE EDGE. These were two -- `0.35p` for the margin test and
    # `max(0.35p, 0.03*measure)` for the flush test -- and a body line beginning a little left of
    # the modal L came out FLUSH by one and OUTSIDE THE BLOCK by the other. Its opening token was
    # then labelled MarginNote, `first_text_token` fell through to an interior word, and the
    # continuity rate went DOWN, from 0.312 to 0.176. Found by the consumer, not by the region
    # score, which is the sixth time in this project a rule was only tested once something read it.
    edge_tol = flush_tol = max(FLUSH_TOL_P * p, FLUSH_TOL_M * measure)

    # R2 -- margin by EDGE, so a note that straddles L is still caught.
    # ⚠️ R2.2e-b: the edge test alone types a FULL LINE OF SCRIPTURE as a marginal note when its ink
    # runs past the modal edge -- 41 rows over 20 leaves, median share of the measure 0.90, many
    # above 1.00. A thing that spans the measure cannot be a note set beside it, so spanning the
    # measure QUALIFIES a token as in-block whatever it does at the edges. DEFAULT OFF.
    for t in toks:
        t["in_block"] = not (t["l"] < L - edge_tol or t["r"] > R + edge_tol)
        if BLOCK_SPAN_QUALIFIES and not t["in_block"]:
            t["in_block"] = (t["r"] - t["l"]) >= BODY_SPAN_M * measure
        t["x_centre"] = ((t["l"] + t["r"]) / 2.0 - L) / measure

    # R3 -- a body row reaches the measure at EITHER edge AND spans most of it.
    # ⚠️ The span clause is not decoration. Without it, leaf 406's headline row was promoted to a
    # body row by a 3-glyph UNREAD speck sitting at the left margin -- one speck at the right x is
    # enough to satisfy "flush", and the running head was then labelled MainText. A justified line
    # is flush AND full; testing only flushness tests half the property.
    # 🔴 R2.1k, MEASURED 2026-08-17 by RENDERING leaf 414 and seeing a whole body row typed
    # MarginNote. `MIN_GLYPHS` is a SPECK FILTER -- "does this token get a vote on geometry" -- and it
    # is being used here as a SPAN ESTIMATOR, which is a different question. A two-component word like
    # 'of' is not a speck. The finer the splitter, the more real ink the filter discards, so the
    # measured span SHRINKS while `block_measure`'s R moves right and the 0.75 x measure requirement
    # GROWS. On leaf 414 row 1: under the blob splitter one 37-component token spans 851px against a
    # 677px requirement; under the recogniser splitter 5 in-block words drop out (rightmost at
    # r=1086), the span collapses to 696px, and the requirement rises to 708px. The row fails BY 12
    # PIXELS and every word in it is relabelled. Nothing about the page changed.
    # ⚠️ The row's extent is a property of its INK, which no splitter can alter -- the same invariance
    # argument that made R2.1j's ink binding work. `SPAN_FROM_INK` is the candidate and is DEFAULT OFF
    # until it has passed its own pre-registered acceptance; turning it on silently would restate
    # R2.1g's headline number under a rule that has not been accepted.
    span = {}
    if SPAN_MODE == "ink":
        # 🔴 REFUTED, MEASURED, kept because the refutation is the finding. Raw ink extent makes
        # every RUNNING HEAD look like a full justified line: leaf 414's head row is
        # `382 ... NVMERI. ... Sacrifices for`, three separate elements whose COMBINED extent spans
        # nearly the measure though no single element approaches it. RunningHead recall fell
        # 1.0000 -> 0.7500 under EVERY splitter, while MainText rose -- it trades R3's original
        # failure for the one the span clause was added to prevent.
        for t in toks:
            if not t["in_block"]:
                continue
            row = t.get("_row") or []
            if row:
                span[t["row"]] = (min(g[2] for g in row), max(g[3] for g in row))
    elif SPAN_MODE == "segment":
        # A justified body line is CONTINUOUS across the measure; a headline band is SPARSE ISLANDS.
        # Extent cannot tell them apart, so take the longest run that is continuous at the setting's
        # own scale -- `region_segments`, the rule R2.1h already justified (a gap wider than the line
        # pitch is a run to another region, not a word space). Computed on GLYPH BOXES, so no
        # splitter can move it.
        for t in toks:
            if not t["in_block"]:
                continue
            row = t.get("_row") or []
            if not row:
                continue
            segs = CR.region_segments(row, p)
            a, b = max(((min(g[2] for g in sg), max(g[3] for g in sg)) for sg in segs),
                       key=lambda ab: ab[1] - ab[0])
            span[t["row"]] = (a, b)
    else:
        for t in toks:
            if not t["in_block"] or t["n_glyphs"] < MIN_GLYPHS:
                continue
            a, b = span.get(t["row"], (t["l"], t["r"]))
            span[t["row"]] = (min(a, t["l"]), max(b, t["r"]))
    body_rows = {j for j, (a, b) in span.items()
                 if (b - a) >= BODY_SPAN_M * measure
                 and _flush(a, b, L, R, flush_tol)}                  # R2.2g

    # R3b -- ARGUMENT. A body row set in a DIFFERENT FOUNT is not scripture (R2.2d).
    # ⚠️ Placed HERE, after body rows are found and before R4 labels them, because the argument is
    # justified to the measure and therefore IS a body row by R3. The fount is what separates it, and
    # nothing earlier in the chain looks at fount at all. Rows are read off `_row`, the ink each token
    # already carries, so this does not re-derive a second description of a row -- the drift
    # `head_tokens` exists to prevent, and which R2.1g and R2.1i each paid for once.
    # ⚠️ THE FOUNT TEST IS PER SEGMENT, NOT PER ROW, AND THE ROW-LEVEL VERSION WAS MEASURED AND
    # REFUTED. A row-level slant is an AVERAGE over everything sharing that baseline, and this
    # edition sets its side-notes in ITALIC beside roman scripture: leaf 405's `† How beautiful are
    # thy tabernacles o Iacob` shares its line with the note `Manie do prophecie, and cast out
    # diuels`, and the row averages to slant 8 -- firing the rule on a verse. Leaves 403, 406 and 412
    # fail the same way. This is `region_head`'s FOUNDING observation returning on a new axis: a row
    # is not homogeneous in REGION (which is why labels are per token) and it is not homogeneous in
    # FOUNT either. `region_segments` -- the R2.1h primitive that cuts a row where a gap exceeds the
    # line pitch, i.e. a run out to another region -- is exactly the grain the fount question needs.
    arg_segs = {}
    if ARGUMENT_RULE:
        ink = CR._ink(band)
        # ⚠️ OVER EVERY ROW, NOT ONLY BODY ROWS, and that was measured. Gating the fount test on
        # `body_rows` reached only 9 of 24 gold argument rows: an argument's short last line
        # (`Collection.`, `and the people.`) and its indented lines fail R3's span/flush test, so
        # they never reached the test at all. A FOUNT IS A PROPERTY OF THE SETTING, not of whether a
        # line happens to be justified -- conditioning it on justification imports R3's question into
        # a rule that is not asking it.
        seen = {}
        for t in toks:
            if t["row"] not in seen and t.get("_row"):
                seen[t["row"]] = t["_row"]
        for j, row in seen.items():
            spans = []
            for seg in CR.region_segments(row, p):
                if len(seg) < ARGUMENT_MIN_COMPONENTS:
                    continue
                s = CR.row_slant(ink, seg)
                if s is not None and s >= ARGUMENT_SLANT_MIN:
                    spans.append((min(g[2] for g in seg), max(g[3] for g in seg)))
            if spans:
                arg_segs[j] = spans

    # R4 PER SEGMENT -- R2.2f. A body row's MainText is its BODY SEGMENT, not its whole baseline.
    # Qualification is R3's test verbatim (span >= BODY_SPAN_M x measure AND flush at L or at R),
    # applied to `region_segments` instead of to the row's token union. Rows with no qualifying
    # segment keep today's labels; `fallback_rows` counts them so the reach stays knowable.
    body_segs, fallback_rows = {}, set()
    if R4_PER_SEGMENT:
        rows_of = {}
        for t in toks:
            if t["row"] in body_rows and t["row"] not in rows_of and t.get("_row"):
                rows_of[t["row"]] = t["_row"]
        for j, row in rows_of.items():
            qual = []
            for seg in CR.region_segments(row, p):
                a, b = min(g[2] for g in seg), max(g[3] for g in seg)
                if (b - a) >= BODY_SPAN_M * measure and _flush(a, b, L, R, flush_tol):
                    qual.append((a, b))
            if qual:
                body_segs[j] = qual
            else:
                fallback_rows.add(j)

    def _in_body_seg(t):
        if not R4_PER_SEGMENT or t["row"] not in body_segs:
            return True
        c = (t["l"] + t["r"]) / 2.0
        return any(a <= c <= b for a, b in body_segs[t["row"]])

    def _in_arg(t):
        c = (t["l"] + t["r"]) / 2.0
        return any(a <= c <= b for a, b in arg_segs.get(t["row"], ()))

    # R6 -- the first NON-body row carrying a heading token is the running head; later ones are
    # chapter heads. Resolved before labelling so the decision is one statement, not a running flag.
    head_rows = sorted({t["row"] for t in toks
                        if t["row"] not in body_rows and t["in_block"]
                        and t["n_glyphs"] >= MIN_GLYPHS
                        and HEAD_MID[0] <= t["x_centre"] <= HEAD_MID[1]})
    rh_row = head_rows[0] if head_rows else None

    for t in toks:
        if not t["in_block"]:
            t["label"] = MARGIN_NOTE                                    # R2
        elif _in_arg(t):
            t["label"] = ARGUMENT                                       # R3b
        elif t["row"] in body_rows and _in_body_seg(t):
            t["label"] = MAIN_TEXT                                      # R4
        elif HEAD_MID[0] <= t["x_centre"] <= HEAD_MID[1]:               # R5 / R6
            t["label"] = RUNNING_HEAD if t["row"] == rh_row else CHAPTER_HEAD
        else:
            t["label"] = MARGIN_NOTE                                    # R5
        # R2.2f G5 -- which fate this token took, so the rule's reach is read off the classification
        # rather than re-derived by a scorer holding a second description of the same rows.
        if R4_PER_SEGMENT and t["row"] in body_rows and t["in_block"]:
            t["r4_seg"] = ("fallback" if t["row"] in fallback_rows
                           else "kept" if _in_body_seg(t) else "demoted")
        t.pop("_row", None)
    return toks, None


def first_text_token(band, pitch):
    """-> (token dict, reason). The opening token of the first body row.

    This is what R2.1's head side needs, and it is a CONSUMER of the classification rather than a
    parallel path -- so a head-side failure is attributable to a region label, which can be scored,
    instead of to an opaque crop.
    """
    toks, why = classify(band, pitch)
    if toks is None:
        return None, why
    body = [t for t in toks if t["label"] == MAIN_TEXT]
    if not body:
        return None, "no MainText token in the band"
    row = min(t["row"] for t in body)
    line = sorted([t for t in body if t["row"] == row], key=lambda t: t["l"])
    return line[0], None
