#!/usr/bin/env python3
"""R14.1/R14.2 -- LECTOR, THE ADAPTIVE VISUAL AGENT: see the leaf, frame it, name what is on it.

NAMED BY SIR, 2026-08-28: **LECTOR**. In a printing house the *lector* is the reader who takes in
the whole page; this module reads the PAGE, where `recogniser.py` -- **SCRIBE** -- reads the LINE.
⚠️ The pair is deliberate and the division of labour is the architecture: LECTOR decides WHAT a
region is and WHERE it sits, SCRIBE decides what it SAYS. R14.10b is the first class LECTOR
decides with help from SCRIBE, and R14.16 is the open question of whether LECTOR should be a
model at all rather than the hand-written cascade it is today.

Masterplan §3.0 GOVERNS and states the aim in one sentence: *an agent that reproduces what a literate
human does when handed a page of this book* -- look at the leaf, recognise what KIND of page it is,
see BY VISUAL CUE where each class of text sits, bound those regions, and read each as its own kind
of thing.

⚠️ WHY THIS FILE EXISTS RATHER THAN A FIFTH SPAN RULE. R2.2o.1 measured that the two gap populations
OVERLAP -- a true region gap of 0.875 pitches against a true word space of 1.525 on the same page --
so NO CONSTANT EXISTS to be found and threshold-retuning is refuted as the repair. R14.0 then measured
that Surya's DETECTOR already localises the marginal notes as tight objects (median 0.0039 of page
area) and merely has no NAME for them: MarginNote 0/19 is a LABELLING failure on a WORKING detector.

⇒ The agent's job is exactly the missing step: take boxes that are already correctly localised and
NAME them from the page's own visual structure.

THE FOUR CUES, AND WHY EACH IS PER-PAGE (§3.0's "adaptive means per-page, from the page")
-----------------------------------------------------------------------------------------
Everything below is derived from THIS leaf's own boxes. §3.0 permits a fitted constant to INITIALISE
or CLAMP and forbids it to DECIDE, so nothing here is a corpus-fitted number:

  THE MEASURE   the body column's left and right edges, taken as the modal edges of this page's own
                LARGE boxes. This is the frame every other cue is relative to.
  OUTSIDENESS   a box whose horizontal span lies substantially OUTSIDE the measure is marginal. This
                is the cue that names a side-note, and it is the one no gap threshold could reach:
                a note is not "far from" the body, it is BESIDE it, and besideness is a fact about
                the frame, not about a distance.
  HEAD BAND     a small box sitting ABOVE the topmost large box is page furniture (running head).
  CENTREDNESS   a small box inside the measure whose centre sits in the middle half, above body ink,
                is a heading rather than a line of text.

ABSTENTION IS A FIRST-CLASS OUTPUT (§3.0 S4, Gate 9.6 / §7.8 row 10d). Where the cues conflict or the
deciding margin is thin, the agent returns `??` WITH ITS CAUSE. ⚠️ `layout.py:type_lines`'s
`return ["body"] * len(lines)  # fail-safe toward body` is the branch this retires: a leaf it cannot
read is currently emitted as entirely scripture, which is a null with no cause established in the
shipping path. An abstention silently defaulted to any class is a HARD FAILURE.

ARCHETYPE FIRST (§3.2a). Which classes a leaf CAN carry is a property of what kind of leaf it is, so
the archetype is decided before any region is named, and it FORBIDS classes as well as requiring them.
A forbidden-class emission is a hard failure (Gate 9.1 / row 10a).

    ../ocr-venv/bin/python witness/visual_agent.py            # run + score against GOLD-HEADBAND
    ../ocr-venv/bin/python witness/visual_agent.py --cache    # write the perception cache only

⚠️ THIS DISCHARGES NO GATE. Rows 10a/10b are reserved for GOLD-LAYOUT (>=125 pages, per-archetype
quota, recogniser frozen). This is 121 entries over 20 leaves of ONE witness -- the same rung-0 window
R14.0 used, chosen deliberately so the comparison against Surya-off-the-shelf is like for like.
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
import warnings
from dataclasses import dataclass, field, asdict
from pathlib import Path

warnings.filterwarnings("ignore")

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import detect as D                                       # noqa: E402
import witnesses as W                                    # noqa: E402
from score_head_regions import GOLD                      # noqa: E402

WITNESS = "OT1-1609-B"
LEAF_LO, LEAF_HI = 400, 420
CACHE = _HERE / "gold" / f"perception_{WITNESS}_{LEAF_LO}-{LEAF_HI - 1}.json"

# ---------------------------------------------------------------- pre-registered bars
# ⚠️ WRITTEN BEFORE THE FIRST RUN, and they are RUNG-0 admissibility bars, not Gate 10a/10b
# thresholds. The overall bar is set to Surya-off-the-shelf's own score deliberately: an agent that
# buys marginalia by giving back body text has not improved anything, and R2.2's four refuted span
# rules each bought ~1 MarginNote for 11-12 MainText. This bar makes that trade a FAILURE.
BAR_MN_RECALL = 0.50          # the class this edition is built around; Surya off the shelf: 0.0000
BAR_OVERALL = 0.8264          # Surya off the shelf on this exact gold: 100/121
BAR_FORBIDDEN = 0             # a class the archetype forbids must never be emitted
# Abstention is CHARACTERISED here, not bounded. Gate 9.6's rate is pre-registered FROM this run's
# characterisation (R14.2's acceptance), never asserted in advance -- §0.5 forbids a threshold not
# derived from evidence.

RH, MN, MT, CH, ABSTAIN = "RH", "MN", "MT", "CH", "??"
# 🔴 R14.10a — THE ARGUMENT, and it is a FOUNT class, not a positional one. This edition sets a
# multi-line ITALIC prose summary between the chapter head and the first verse. The agent had no
# name for it, so all ten in this window were misfiled — and MEASURED, the misfiling was decided
# ENTIRELY BY `SMALL_AREA`: the six argument boxes above 0.05 of page area became `MT`, the four
# below it became `CH`. Not one cue was reading the class; a size prior was choosing which wrong
# name it got. ⚠️ The `MT` half is the SILENT half — MainText is containment, so it scores as
# correct — which is why GOLD-FOREEDGE saw only the four `CH` cases and R14.8 recorded ×4.
AR = "AR"
# 🔴 R14.9 — FOOT FURNITURE. The agent had names for four classes on a page that prints at
# least seven. A class with no name is not skipped; it is MISFILED into the nearest name it
# does have, which is how a gathering signature became a chapter heading on leaf 409.
# ⚠️ These two are NOT in GOLD-HEADBAND (top 3 rows), so they cannot raise the score — they
# exist to stop the agent claiming something the page does not say. R14.6a already records
# both as having an ADMISSIBLE, self-verifying label source.
SIG, CAT = "SG", "CW"   # gathering signature · catchword
# 🔴 R14.10b — THE PAGE NUMBER, and it is the first class here decided by a READ. Measured over
# leaves 400-419: 16 leaves carry a detected page-number box, ALL SIXTEEN were misfiled, and 15 of
# them were named `MN` — the class this edition is built around. ⚠️ AND IT COST NOTHING ON ANY
# NUMBER EVER QUOTED, because scoring is gold-entry-driven and NO GOLD ENTRY BINDS TO ONE OF THESE
# BOXES: `MN` recall cannot fall when the agent invents notes, so the agent's `MN` PRECISION was
# unmeasured while it manufactured roughly three-quarters of a note per leaf. R14.10a's silent `MT`
# half, one class over. ⚠️ The Roadmap's positional formulation is REFUTED on this window — page
# numbers run 0.000-0.043 and 0.812-0.972 of the measure, head-band notes 0.010-0.110 and
# 0.857-1.072, so the populations OVERLAP ON BOTH SIDES and no constant separates them.
PN = "PN"

# ---------------------------------------------------------------- R16.5: THE ONTOLOGY
# 🔴 THE EYE REVIEW'S CENTRAL FINDING, AND IT IS NOT A CUE BUG. Over 208 leaves and 893 findings,
# the largest defect families are genres THIS EDITION PRINTS AND `CLASSES` HAD NO WORD FOR — E12
# ornament (51), E15 annotation (40), E10 paratext-has-no-grammar (34), E13 lost columns (15). A
# class with no name is not skipped, it is MISFILED (R14.9's rule, restated on a corpus): the
# annotation block came out `MT` on OT1-1609-B_0417, `SG` on NT-1582-B_0036 and BOTH `CH` and `MT`
# within NT-1582-B_0038 — one genre, three names, one leaf.
#
# ⚠️ EVERY NAME BELOW IS TAKEN FROM ROADMAP R12'S EIGHT-ARCHETYPE TABLE, NOT INVENTED HERE. That
# table already declares Annotation, DropCap, BookTitle/DisplayTitle and TableBlock as the required
# classes of archetypes E, C, D/G and H. Minting a second vocabulary beside it is the
# two-sources-of-truth defect this file has now paid for three times.
#
# ⚠️ AND THE ADMISSION RULE IS R12.1'S OWN: *"a class asserted but not present invites the model to
# hallucinate it"*. So a class is declared here ONLY if the eye review ATTESTS it with named
# exemplar leaves. The three that FAILED that test are recorded below the inventory, with the
# evidence that excluded them — an ontology is a claim about the book and must be refutable.
#
# ANNOTATION — the commentary block. Archetype E's class. ⚠️ It is NOT the argument: an argument is
# the italic summary BEFORE a chapter, an annotation is the smaller-type commentary AFTER the
# scripture, and E15 shows the two are confused only because neither had a home. Attested:
# OT1-1609-B_0417 (`MT`) · NT-1582-B_0036 (`SG`) · _0037 (`CH`) · _0038 (`CH` and `MT`, one leaf) ·
# _0117 (`MT`, `SG`, `SG` — three names on one leaf, E15 at its worst).
AN = "AN"
# ORNAMENT — fleuron, headpiece, tailpiece, printer's rule, divider. NON-TEXTUAL, and that is the
# point: it carried FIVE text classes across the corpus (E12). Roadmap R12 lists `Rule` and `Brace`
# as separate sorts of archetype H; they are folded in here because a rule IS an ornament at region
# grain and splitting them would declare a class the detector cannot deliver. Attested:
# NT-1582-B_0028 (`SG`) · _0034 (`CH`) · _0117 (`SG`) · OT2-1610-P_1089 (divider rule as `CH`).
ORN = "OR"
# DROP CAP — the woodcut initial. Kept SEPARATE from `OR` although both are cut in wood, because
# they differ in every respect that matters to a layout model: a drop cap sits INSIDE the measure,
# at the head of a text block, and it is part of the reading order; an ornament is not. R12 declares
# `DropCap` as archetype C's own class. Attested: NT-1582-B_0035 · _0116 · _0118 · _0119 · _0122 ·
# _0246 — named `MT`, `MN` and `CH` between them.
DROP = "DC"
# TABLE BLOCK — tabular and index matter, including the multi-column structure E13 records as lost.
# ⚠️ THIS IS THE CLASS THAT DISSOLVES THE SCOPE EXCLUSION: 15 of the 18 out-of-scope leaves were put
# out because *"table and index rows have no correct answer in CLASSES"*. Attested: NT-1582-B_0030
# (table of books) · _0313/_0314/_0317 (harmony) · _0778..._0781 (liturgical) · _0782/_0802 and
# OT2-1610-P_1112/_1113 (topical index) · _0803/_0804 (glossary, errata).
TBL = "TB"
# DISPLAY TITLE — the page's or section's own title, set in display type. R12's `BookTitle`
# (archetype D) and `DisplayTitle` (archetype G) are ONE class at region grain; which of the two a
# given line is depends on the archetype, and the archetype is already decided before naming.
# Attested: NT-1582-B_0030 box 0 (`MT`) · _0248 box 2 (`MT`) · _0313 (`MN`) · _0803 box 6 (`CW`).
DISP = "DT"
# COLOPHON — the closing formula of a text unit: `FINIS.`, `LAVS DEO`, *The end of the Prophetical
# Bookes.*, the Doway dateline, and the approbators' SUBSCRIPTIONS. ⚠️ Those subscriptions are the
# sharpest case for this class: they are signatures in the other sense of the word, and `SG` — the
# QUIRE signature — swallowed them on OT1-1609-P_0006 and OT2-1610-P_0006 for want of anywhere else
# to put them. Attested also: OT1-1609-P_0018 (dateline as `CH`) · OT2-1610-P_1085 (`FINIS.` as
# `SG`) · _0898 (`SG`) · NT-1582-B_0804 (`LAVS DEO` as `SG`).
COL = "CO"

# THE AGENT'S CLASS INVENTORY, DECLARED ONCE. ⚠️ `score_foreedge` used to keep its own copy of this
# so that "the agent has no name for this class" would be a CHECKED claim rather than a reading of
# the source — a good instinct that became a second source of truth, and R14.10a caught it doing
# exactly what a second source of truth does: the run that scored `AR` at 4/4 also printed
# `AR ⚠️ NO NAME IN THE AGENT` in the same output. One declaration; every consumer imports it.
CLASSES = frozenset({RH, MN, MT, CH, AR, PN, SIG, CAT, ABSTAIN,
                     AN, ORN, DROP, TBL, DISP, COL})

# 🔴 DECLARED AND NOT ADOPTED, WITH THE EVIDENCE THAT EXCLUDED EACH. R12.1's rule cuts both ways: a
# class present and unnamed is a misfiling, and a class named but absent is an invitation to
# hallucinate. These three were considered and REFUSED, and they are written down because a
# rejection nobody recorded is indistinguishable from a possibility nobody thought of.
#
#   ProseBlock (R12 archetype G) — REFUSED. The preface prose on OT1-1609-P_0008/_0009 already names
#     correctly as `RH`/`MT`/`MN`; `plates/scope.json` records exactly that as its reason for
#     keeping those leaves IN. Minting a class to split a class that is working buys nothing and
#     costs a confusion pair.
#   NoteRef (R12 archetype E) — REFUSED ON THE DETECTION FLOOR. Note-reference marks are single
#     sorts (`*` `†` `‡` `¶`). R14.15 records that the detector may not localise objects at this
#     grain at all, and NOT ONE of the 893 eye findings reports a misnamed note reference — because
#     no box was ever drawn on one. A class the detector cannot deliver is unfalsifiable here.
#   VerseNumber — REFUSED, same floor, same evidence: zero findings in 208 leaves.
#
# 🔑 WHICH CLASSES CAN HOLD A BLOCK OF TEXT, DECLARED RATHER THAN EMERGENT. This is the eye review's
# deepest finding made checkable. `MT` is containment — a box named MainText scores as correct
# whatever it actually holds — and the review found `SG`, `CH` and `MN` each acquiring that property
# BY ACCIDENT, wherever the frame pushed matter outside itself: E10 (*"SG and CH both act as
# containment, not only MT"*), E18 (*"MT, SG, CH and now MN have all acted as containment"*), E16.
# Four containment classes means four ways for a wrong label to score as right. Declaring the set
# lets a scorer ASK whether a furniture class is swallowing a block, instead of that being something
# only an eye on a plate can see.
CONTAINMENT = frozenset({MT, AN, TBL})               # may legitimately hold a block of running text
PAGE_FURNITURE = frozenset({RH, PN, SIG, CAT, COL})  # fixed by position on the leaf, never a block
STRUCTURAL = frozenset({CH, AR, DISP})               # heads and openings: they DELIMIT, not hold
NON_TEXT = frozenset({ORN, DROP})                    # ink that carries no reading
# ⚠️ `PAGE_FURNITURE` IS NOT `FURNITURE`. The name below, defined further down and already in use,
# holds SURYA'S OWN vocabulary (`PageHeader`/`PageFooter`) and is a cue input; this one holds THIS
# agent's classes and is a role declaration. They were one word apart and would have shadowed each
# other silently — the near-collision is recorded rather than resolved by hoping nobody re-reads it.
# ⚠️ `MN` IS DELIBERATELY IN NONE OF THESE FOUR. A marginal note is defined by BESIDENESS — a fact
# about the frame, not about what it holds — and E18 caught it acting as containment on the harmony
# pages. Forcing it into a role here would settle by declaration a question the corpus has not
# answered; it is left OPEN, and named as open, which is the honest state.
_ROLES = {"containment": CONTAINMENT, "furniture": PAGE_FURNITURE,
          "structural": STRUCTURAL, "non-text": NON_TEXT}

# THE SAME INVENTORY IN A STABLE, ROLE-GROUPED ORDER, because `CLASSES` is a frozenset and a
# frozenset has no order. ⚠️ Anything that PRESENTS the classes to a person — the review tool's
# button row — was indexing into an arbitrary iteration order, which is fine until the set changes
# and then is a silently different UI. Grouped so that adjacent buttons are classes a reviewer
# actually confuses, with the abstention LAST so it is never the accidental first choice.
CLASSES_ORDERED = [MT, AN, TBL,              # containment
                   CH, AR, DISP,             # structural
                   MN,                       # role deliberately OPEN — see above
                   RH, PN, SIG, CAT, COL,    # page furniture
                   ORN, DROP,                # non-text
                   ABSTAIN]
assert set(CLASSES_ORDERED) == set(CLASSES) and len(CLASSES_ORDERED) == len(CLASSES), (
    "CLASSES_ORDERED and CLASSES disagree — a class was added to one and not the other, which is "
    "the second-source-of-truth defect. Checked at import so it can never ship.")

# §3.2a's REQUIRES/FORBIDS contract, for the archetypes reachable in this window. The full eight
# are Roadmap R12; this file carries the ones the window can actually exhibit, and says so.
ARCHETYPES = {
    "A":  {"requires": {MT, RH}, "forbids": {MN, CH, AR, AN, TBL, DISP, DROP, COL},
           "name": "plain text page"},
    "B1": {"requires": {MT, RH, MN}, "forbids": {CH, AR, AN, TBL, DISP, DROP, COL},
           "name": "text + disjoint marginal apparatus"},
    "C":  {"requires": {MT, CH}, "forbids": {AN, TBL}, "name": "chapter opening"},
    "BC": {"requires": {MT, CH, MN}, "forbids": {AN, TBL}, "name": "chapter opening WITH apparatus"},
    # 🔴 R16.5 — THE FOUR BELOW ARE DECLARED AND UNREACHABLE, WHICH IS SAID HERE RATHER THAN LEFT TO
    # BE DISCOVERED. `classify_archetype` can emit only `A`/`B1`/`C`/`BC`; it has no cue for an
    # annotation leaf, a book opening, a prelim or a table. So these four entries are R12.2's
    # contract ("required and forbidden classes as DATA, not prose") arriving BEFORE the classifier
    # that will use it — which is the right order, because the contract is what makes the
    # classifier checkable. ⚠️ Their FORBIDS sets are therefore UNTESTED, exactly as the note below
    # says of `A`'s and `B1`'s `AR` entries. `_archetype_reachability()` prints the gap on every run
    # so it is a measured number and not a comment nobody re-reads.
    "D":  {"requires": {DISP, AR, MT}, "forbids": {TBL, MN}, "name": "book opening"},
    "E":  {"requires": {AN, RH}, "forbids": {AR, TBL, DROP}, "name": "annotation leaf"},
    # ⚠️ `G` IS THE ONE ARCHETYPE R12 STATES AS A DISJUNCTION — *"DisplayTitle **or** ProseBlock"* —
    # and a `requires` SET cannot say "or". Rather than quietly drop half the clause, the disjunct
    # is carried in its own key. ProseBlock was refused above, so today the branch that survives is
    # `DISP`; when the census (R12.1) finds a prelim leaf with neither, this key is where the
    # refutation lands.
    "G":  {"requires": {RH}, "anyof": {DISP, MT}, "forbids": {AR, CH, DROP},
           "name": "prelims (title page, approbatio, preface)"},
    "H":  {"requires": {TBL}, "forbids": {MT, AR, CH, DROP}, "name": "tabular matter"},
}
# 🔴 AND TWO OF R12'S EIGHT ARE DELIBERATELY ABSENT. `B2` (INTERLEAVED apparatus) and `F` (MIXED
# LEAF) are both defined by a BOUNDARY WITHIN the leaf, and this agent has no representation for
# one: it names whole boxes against a single page-level frame. Declaring them would create two
# archetypes that nothing can ever emit and no forbid could ever bind — the trivially-satisfied
# failure mode below, repeated on purpose instead of by accident. They stay Roadmap R12.3's work.
# ⚠️ `F` IS NOT HYPOTHETICAL HERE: leaf 417 of the scored witness IS a mixed leaf (body, then an
# ANNOTATIONS section, then a new chapter), and the eye review's E22 records the key to the marks
# sharing OT1-1609-P_0024 with the Argument of Genesis. A leaf-level scope decision cannot reach
# either, which is precisely why R12.3 exists.


def _emittable_classes() -> set[str]:
    """Which declared classes a cue can actually COMMIT, read off `_cue`'s own returns.

    🔴 THIS IS THE CHECK THAT KEEPS R16.5 HONEST. Widening `CLASSES` costs nothing and proves
    nothing: six genres now have a correct answer available, and not one of them has a cue that
    emits it. Left unstated, the wider inventory would read as six classes gained. Stated, it reads
    as what it is — the misfiling target removed, the recognition not yet built.

    ⚠️ Parsed, not listed, for the same reason as `_archetype_reachability`: a hand-kept list would
    still claim `AN` is unreachable on the day someone writes the annotation cue.
    """
    import ast
    import inspect
    import textwrap
    tree = ast.parse(textwrap.dedent(inspect.getsource(_cue)))
    names = {elt.id
             for node in ast.walk(tree) if isinstance(node, ast.Return)
             if isinstance(node.value, ast.Tuple)
             for elt in node.value.elts[:1] if isinstance(elt, ast.Name)}
    got = {globals()[n] for n in names if n in globals() and globals()[n] in CLASSES}
    if not got:
        raise RuntimeError("emittable classes could not be parsed from `_cue` — its branches no "
                           "longer `return (LABEL, conf, cause)` with LABEL a module constant. FIX "
                           "THE PARSE; an empty set would read as 'the agent names nothing'.")
    return got


def _archetype_reachability() -> tuple[set[str], set[str]]:
    """Which declared archetypes can `classify_archetype` actually EMIT, and which cannot.

    ⚠️ READ OFF `classify_archetype`'S OWN SOURCE, not restated from a second list. A hand-kept
    copy of "the four it can emit" is precisely the two-sources-of-truth defect R14.9 and R14.10a
    each paid for, and it would fail in the quietest possible way: the day someone teaches the
    classifier archetype `H`, a hardcoded set goes on reporting it unreachable and the scorer prints
    a reassuring number about a state of affairs that ended. So the archetype literals are parsed
    out of the function that assigns them, and adding a branch updates this automatically.

    ⚠️ REACHABLE IS NOT THE SAME AS OBSERVED. This answers "can the code ever say `C`", not "did it
    say `C` on this window" — `A` is reachable and never fires on leaves 400-419, which is the
    standing reason the FORBIDS contract does not yet bind.
    """
    import ast
    import inspect
    import textwrap
    tree = ast.parse(textwrap.dedent(inspect.getsource(classify_archetype)))
    reachable = {
        elt.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        # the classifier's branches all read `a, cause = "<archetype>", "<why>"`
        for tgt in node.targets if isinstance(tgt, ast.Tuple)
        and any(isinstance(e, ast.Name) and e.id == "a" for e in tgt.elts)
        if isinstance(node.value, ast.Tuple)
        for elt in node.value.elts[:1]
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
    }
    if not reachable:                      # the parse found nothing — say so, never report a clean 0
        raise RuntimeError("archetype reachability could not be parsed from classify_archetype — "
                           "its branches no longer assign `a, cause = \"X\", ...`. FIX THE PARSE; "
                           "an empty reachable set would read as 'all eight unreachable'.")
    return reachable, set(ARCHETYPES) - reachable
# ⚠️ AND THOSE TWO NEW `AR` FORBIDS ARE TRIVIALLY SATISFIED, WHICH IS SAID HERE RATHER THAN LEFT TO
# BE DISCOVERED. An argument only occurs at a chapter opening, so `classify_archetype` reads an `AR`
# cue AS evidence of one — which means a leaf carrying `AR` is typed `C` or `BC`, and `A`/`B1` can
# never be reached with an `AR` box on the page. The forbid records the edition's grammar honestly;
# it does not test the cue. Same caveat as the one already standing over `forbidden = 0`.
#
# 🔴 AND THE ALTERNATIVE WAS REJECTED ON R14.9's EVIDENCE, NOT ON TASTE. Gating `AR` on a detected
# chapter head — "an argument is the block BELOW a `CH`" — is what the Roadmap row first proposed,
# and it is CIRCULAR HERE IN THE STRONGEST FORM: on four of these ten leaves the argument box IS
# the agent's `CH` call, so the misfiled box would have become the anchor used to find itself. It is
# also the exact defect `region_head` already recorded and refuted for the row-grain rule — *"between
# the ChapterHead and the first verse would be circular; it presumes the boundary it must find, and
# is silent wherever the chapter head was missed"*. So `AR` is decided on the FOUNT, and the
# relation to the chapter head is an OUTPUT of the class, never an input to it.

# A box below this share of page area is "small" -- furniture or a note, never the measure. It is a
# SIZE PRIOR, and it initialises: it decides nothing on its own, it only routes a box to the cue set
# that applies to it. §3.0 permits exactly this use and forbids the other.
SMALL_AREA = 0.05
# How much of a box's width must fall outside the measure before "beside" is the better reading than
# "inside". A box straddling the edge is the ambiguous case and is what ABSTENTION is for.
OUTSIDE_FRAC = 0.55
# The deciding margin below which the agent declines rather than guesses. Reported, characterised.
THIN_MARGIN = 0.08
# Surya's own vocabulary, split by the question `RH vs CH` turns on: is this box PAGE FURNITURE, or
# is it CONTENT that happens to sit high on the leaf? ⚠️ Using the detector's class as ONE CUE AMONG
# CUES is legitimate and is not a fitted constant -- it is a learned visual judgement from a model
# trained on millions of pages. What would NOT be legitimate is using it as the ANSWER: R14.0
# measured that its label inventory has no name for a marginal note at all.
FURNITURE = frozenset({"PageHeader", "PageFooter"})

# ---------------------------------------------------------------- R14.10a: the fount cue's guards
# ⚠️ NONE OF THESE THREE DECIDES ANYTHING ON THIS WINDOW, and the scorer PRINTS the slack so that
# claim is checked rather than asserted. Measured over all ten adjudicated argument blocks: italic
# share 1.00 on every one, against 0.21 for the nearest non-argument box; segment count 3 at its
# lowest; measure span 0.95 at its narrowest. Each guard sits in an empty band, which is what a
# guard is for -- it excludes a shape the cue was not built for, and it does not pick a winner.
#
# "MOST OF THIS BOX'S TYPE IS ITALIC". A majority, not a fitted fraction. The gap it sits in runs
# from 0.21 to 1.00, so any value in that band gives the same answer on this window.
AR_ITALIC_MAJORITY = 0.50
# AN ARGUMENT IS MULTI-LINE BY DEFINITION -- that is what distinguishes it from an italic heading,
# and it is the edition's grammar, not a tuned number. Observed minimum is 3, so this holds a
# segment of slack.
AR_MIN_SEGMENTS = 2
# AND IT IS SET TO THE MEASURE. An italic run that does NOT reach across the body column is a
# side-note, which this edition also sets in italic -- so besideness is tested first and this is
# the second guard behind it. Observed minimum is 0.95.
AR_MEASURE_SPAN = 0.60
# The fount record is PERCEPTION, built separately (witness/build_fount_record.py). ⚠️ When it is
# absent the cue does not fire AND SAYS SO -- it never falls through silently to the size prior,
# which is the behaviour that hid this class for the whole programme. `score_argument_agent.py`
# proves that negative.
FOUNT = _HERE / "gold" / f"fount_{WITNESS}_{LEAF_LO}-{LEAF_HI - 1}.json"

# ---------------------------------------------------------------- R14.10b: the page-number cue
# ⚠️ THIS PAIR BOUNDS THE CANDIDATE SET AND DECIDES NOTHING. That distinction is the whole lesson of
# R14.10a, where `SMALL_AREA` — a constant with no opinion about arguments — silently partitioned ten
# argument blocks into two wrong names. Here the size and the position ROUTE a box to the confirming
# read, and THE READ NAMES THE CLASS. `score_pagenumber_agent.py` prints the slack in both bands so
# that claim is checked rather than asserted.
#
# "SMALL EVEN BY FURNITURE STANDARDS". Measured on this window: every page number falls in
# 0.0009-0.0012 of page area, the smallest head-band NOTE is 0.0018. The guard sits in that empty
# band. ⚠️ It admits notes as candidates when it errs, which is the safe direction — a lettered
# reading falls through to the note logic and keeps its `MN`.
PN_MAX_AREA = 0.0016
# "AT AN EXTREME OF THE MEASURE" — the same 0.20/0.80 band the running-head test uses, so a page
# number is looked for exactly where a running head is not. ⚠️ This does NOT separate page numbers
# from head-band notes and is not meant to; the two populations overlap on both sides, which is the
# measured finding that makes the read necessary rather than convenient.
PN_EDGE = 0.20
# ---------------------------------------------------------------- R14.14: the ROTATED frame
# 🔴 THE AGENT HAD NO ANGLE AT ALL, AND THAT IS WORSE THAN A WRONG ONE. Surya's boxes are
# axis-aligned, so the tilt of a page is invisible in them; the head and foot lines were horizontal
# and the measure edges vertical. Measured over leaves 400-419, real baseline tilt runs -2.39° to
# +2.75° and varies per leaf, and at +1.6° the drop across a page width is about ONE FULL LINE OF
# TYPE. Counted consequence: the horizontal head line CUT THROUGH 41 BOXES and the foot line 7.
#
# ⚠️ THE PIVOT IS THE PAGE CENTRE, AND IT IS A CHOICE THAT MUST BE STATED. Rotated y is
# `y - tan(angle) * (x - PIVOT_X)`. Any pivot gives the same ORDERING of boxes along the rotated
# axis; the pivot only fixes where rotated-y equals plain y. Taking the centre keeps the correction
# symmetric, so a leaf's head line is not displaced merely because its type sits left or right.
PIVOT_X = 0.5
# The baseline-angle record, built separately (witness/build_skew_record.py). ⚠️ When it is absent
# the frame stays UNROTATED and EVERY LEAF SAYS SO -- an unmeasured page and a square page are
# different states, and a silent zero collapses them. That collapse is exactly the defect
# `slant_mode` would have introduced had it been read as skew.
SKEW = _HERE / "gold" / f"skew_{WITNESS}_{LEAF_LO}-{LEAF_HI - 1}.json"

# The confirming read, built separately (witness/build_reading_record.py). ⚠️ When it is absent the
# cue does not fire AND SAYS SO — never a silent fall-through to the note logic, which is precisely
# how 15 page numbers spent the whole programme wearing the `MN` label without costing a point.
READING = _HERE / "gold" / f"reading_{WITNESS}_{LEAF_LO}-{LEAF_HI - 1}.json"

# ---------------------------------------------------------------- EVERY REMAINING FIXED NUMBER
# 🔴 NAMED HERE BECAUSE AN UNNAMED LITERAL CANNOT BE AUDITED. Each of the five below was previously
# spelled inline inside the cue that used it, which meant no instrument could sweep it and no reader
# could find it. §3.0 permits a fitted constant to INITIALISE or CLAMP and forbids it to DECIDE, and
# that permission is worthless if the constants are invisible. `witness/audit_fixed_measures.py`
# now sweeps every one of these and reports the SLACK around the shipped value — the band over which
# the agent's answer does not change. A constant with wide slack is a guard; a constant with ZERO
# slack is DECIDING, and a deciding constant must be derived from the page or retired.
#
# How much of the body block's width a box must share before it counts as part of the same COLUMN.
# It excludes the marginal column by construction (a side-column overlaps the body horizontally by
# almost nothing), not by a threshold on size.
COLUMN_OVERLAP = 0.50
# 🔴 R14.11 -- `CENTRED_LO, CENTRED_HI = 0.20, 0.80` STOOD HERE AND IS RETIRED, NOT RE-DERIVED.
# It was the band that tells a RUNNING HEAD (centred on the measure) from a head-band NOTE (pushed
# to a side) -- the most load-bearing cue in the head band -- and `audit_fixed_measures.py` measured
# its slack at **0.00x**: move it one sweep step either way and the label vector changes. A number
# that decides is a threshold wearing a cue's clothes, whatever the comment above it claims.
#
# ⚠️ THE ROADMAP'S OWN SUGGESTED DERIVATION WAS REJECTED, AND THE REASON MATTERS. It proposed
# judging centredness against THIS LEAF'S OWN distribution of head-band box centres. A leaf carries
# two to five head-band boxes, so that "distribution" has a sample size of three, and on a leaf
# whose head band holds only notes it would centre the band on the notes. A statistic that small is
# a fitted number wearing a derivation's clothes -- the same defect one level up.
#
# WHAT REPLACED IT CONTAINS NO NUMBER. Measure the offset of a box's centre from the measure's
# centre IN UNITS OF THE BOX'S OWN WIDTH (`centre_offset` below). Then `off <= 0.5` is not a
# threshold: it is the exact statement THE MEASURE'S CENTRE-LINE FALLS INSIDE THIS BOX, which is
# what a compositor means by setting a running head ON the measure. The measure comes from this
# leaf's body block; the width and centre come from the box; nothing is fitted.
#
# Measured over leaves 400-419, 46 head-band boxes: running heads 0.004-0.419, chapter headings
# 0.008-0.165, marginal notes 1.023-6.576, page numbers 5.738-7.740. The empty band between the
# centred classes and the notes is 0.604 wide -- 1.44x the entire running-head spread, where the
# retired constant had none. ⚠️ That measurement is the BASIS of the derivation, taken before it was
# written; it is not a range chosen after watching the answer move.
#
# The abstention tolerance, in those same box-width units: abstain when the centre-line lies within
# this fraction of a box-width of the box's edge, where "inside" and "outside" are not tellable
# apart. ⚠️ THIS IS A GUARD AND IT IS UNEXERCISED ON THIS WINDOW -- the nearest box to the boundary
# sits at 0.419 against 0.877 on the other side, so nothing is within 0.08 of it. An unexercised
# branch is UNTESTED, and saying so is the difference between a guard and a claim. It is swept by
# `audit_fixed_measures.py` so its slack is measured rather than asserted.
CENTRED_ABSTAIN = 0.04
# The same idea below the head, where a centred small box is a heading rather than a line of text.
# ⚠️ TIGHTER than the head band's, and that difference has never been justified by a measurement —
# see R14.11 in the Roadmap, which is filed to derive both from the page instead.
HEADING_LO, HEADING_HI = 0.25, 0.75
# In the foot band, which side of the measure separates a gathering signature from a catchword.
FOOT_CATCHWORD_REL = 0.60


@dataclass
class Box:
    x0: float
    y0: float
    x1: float
    y1: float
    surya: str
    label: str = ""
    conf: float = 0.0
    cause: str = ""
    # R16.20 -- THE DETECTOR'S OWN CONFIDENCE IN THIS BOX, carried at last. `see()` received it
    # and dropped it on the floor for the whole life of this agent, so no cue could weigh a
    # proposal and `frame()` could only rank boxes by AREA. That is why lowering the detection
    # floor moved the frame on 90 of 208 leaves: the column had no way to tell a confident body
    # block from a vague one. See `detect.py` and `plates/DETECT-PROBE-2026-09-03.md`.
    #
    # 🔴 THIS IS NOT `conf`, AND THE TWO MUST NEVER BE MERGED. `conf` is the CUE's confidence in
    # the LABEL IT CHOSE -- a decision this agent made. `surya_conf` is a PERCEPTION, produced
    # before any cue ran. Writing one into the other would feed a cue its own verdict as
    # evidence, which is the exact trap `leaf_from_cache` refuses below.
    #
    # ⚠️ `surya_conf_seen` is NOT `surya_conf > 0`, for the fourth time in this file and for the
    # same reason as `fount_seen` and `read_seen`: a box the detector scored near zero and a box
    # from a cache written before scores were carried are DIFFERENT STATES. Collapsing them
    # would make every box of an older cache look like a proposal the detector rejected, and
    # `frame()`'s column filter would then empty the column on every leaf.
    surya_conf: float = 0.0
    surya_conf_seen: bool = False
    # R14.10a -- the fount evidence standing under this box: how many row segments of type it
    # holds, and how many of them deslant as italic. ⚠️ `fount_seen` is NOT `fount_n > 0`: a box
    # genuinely holding no measurable type and a leaf with no fount record at all are different
    # states, and collapsing them is how an unmeasured thing gets reported as a measured zero.
    fount_n: int = 0
    fount_it: int = 0
    fount_seen: bool = False
    # R14.10b -- the confirming read standing under this box. ⚠️ `read_seen` is NOT `read_text != ""`,
    # for the reason `fount_seen` is not `fount_n > 0`: a crop the recogniser returned EMPTY on and a
    # box that was never read at all are DIFFERENT STATES, and collapsing them turns an unmeasured
    # thing into a measured negative. Five of this window's sixteen page numbers read empty, so the
    # distinction decides real boxes rather than guarding a hypothetical.
    read_text: str = ""
    read_seen: bool = False

    @property
    def italic_frac(self) -> float:
        return self.fount_it / self.fount_n if self.fount_n else 0.0

    @property
    def area(self) -> float:
        return max(0.0, self.x1 - self.x0) * max(0.0, self.y1 - self.y0)

    @property
    def cx(self) -> float:
        return 0.5 * (self.x0 + self.x1)


@dataclass
class Leaf:
    leaf: int
    # R16.2 -- WHICH WITNESS this leaf belongs to. ⚠️ A bare leaf ordinal names DIFFERENT PAGES in
    # different witnesses, so every per-witness record (fount, skew, reading) must be addressed by
    # the PAIR. Defaults to the scored witness so every existing caller keeps its current behaviour
    # exactly; only `plate_book` passes anything else.
    witness: str = WITNESS
    boxes: list[Box] = field(default_factory=list)
    measure: tuple[float, float] = (0.0, 1.0)
    head_y: float = 0.0
    foot_y: float = 1.0
    archetype: str = "?"
    arch_conf: float = 0.0
    arch_cause: str = ""
    # R14.10a. `fount_why` is empty when the fount was read; otherwise it NAMES what stopped it.
    fount_why: str = "no fount record loaded"
    # R14.10b. Same contract for the confirming read: empty when it was available, otherwise the
    # reason. ⚠️ A perception channel that is missing must say so on the LEAF as well as on the box —
    # `_cue` can only report "unreadable" per box, and "the record was never built" is a different
    # fact about the run that a per-box cause cannot carry.
    read_why: str = "no reading record loaded"
    # R16.20 -- empty when every box carried a detector confidence and the framing floor therefore
    # applied to all of them; otherwise it NAMES what bypassed it. ⚠️ Same contract as `fount_why`
    # and `read_why`, and here for the same reason: a frame taken with the floor INERT (boxes with
    # no score, e.g. an older cache) is a DIFFERENT CLAIM from the same frame taken with it live,
    # and a silent equality between the two is how a re-baselined number gets read as a repair.
    frame_why: str = "frame not yet derived"
    # R16.20 -- boxes `frame` was allowed to use but no cue was offered, because they scored below
    # `detect.CUE_MIN_CONF`. ⚠️ KEPT, NOT DROPPED: an unoffered box and a rejected box are
    # different states, and this file has already paid once for collapsing that distinction (see
    # the E2/E14 standing correction — 188 leaves abstaining WITH A CAUSE read as failure).
    withheld: list[Box] = field(default_factory=list)
    withheld_why: str = ""
    # R14.14 -- this leaf's own baseline angle, in degrees. ⚠️ `skew_seen` is NOT `skew != 0`, for
    # the third time in this file and for the same reason: an UNMEASURED leaf and a SQUARE leaf are
    # different states, and collapsing them turns "we never looked" into "it is flat".
    skew: float = 0.0
    skew_seen: bool = False
    skew_why: str = "no skew record loaded"


# ---------------------------------------------------------------- S1: SEE
def see(image, predictor) -> list[Box]:
    """S1 -- the agent looks at the LEAF, not at kraken's line objects.

    ⚠️ THIS INPUT CONSTRAINT IS LOAD-BEARING (R14 preamble, finding (c)). Kraken MERGES margin text
    into the body line object on ch3 p26 and ch6 p36 -- `"gaueſt me to be my fellow companion, gaue
    me of the tree, & I did eate. the diuel that"` is one line object spanning body and margin. No
    downstream boxer of any kind can undo a boundary destroyed upstream, so the agent must see the
    page.

    🔴 R16.20 -- THIS FUNCTION USED TO THROW THE DETECTOR'S CONFIDENCE AWAY. It built
    `Box(x0, y0, x1, y1, b.label)` and dropped `b.confidence` one line after receiving it, so no
    cue could weigh a proposal and `frame()` could rank boxes only by AREA. That single omission
    is why the detection floor could not be lowered: with no score on the box there was nothing
    to filter the framing column by, and a lower floor moved the frame on 90 of 208 leaves.

    Detection settings now come from `detect.py`, which owns them and says why. ⚠️ THIS IS
    LECTOR'S PERCEPTION PATH AND NOT EVERY CALLER SHOULD SHARE IT -- `score_surya_layout.py`,
    `surya_layout_probe.py` and `rung1_surya.py` measure SURYA OFF THE SHELF and must keep the
    shipped defaults, or the adoption bar moves with the thing measured against it.
    """
    out = [Box(x0, y0, x1, y1, label, surya_conf=score, surya_conf_seen=True)
           for x0, y0, x1, y1, label, score in D.detect(image, predictor)]
    return D.dedup(out)


# ---------------------------------------------------------------- the frame
def frame(boxes: list[Box], lf: Leaf) -> tuple[tuple[float, float], float, float]:
    """Derive THE MEASURE and the head-band floor from this page's own boxes.

    The measure is the body column. It is the frame every naming cue is relative to, and it is taken
    per leaf -- a leaf whose forme is set narrower, or which is bound with more gutter, gets its own.

    🔴 THE FIRST VERSION TOOK THE MEDIAN EDGE OF EVERY LARGE BOX AND WAS WRONG, AND THE DRAWING IS
    WHAT SHOWED IT (R14.7, leaf 412). On an apparatus leaf Surya emits the whole MARGINAL COLUMN as
    one large box -- it is tall, so it clears any area prior. Averaged into the median, that column
    dragged the measure's left edge out into the margin, and every "is this box outside the measure"
    test downstream was then asked against a frame that already contained the margin. RH fell 20/20
    -> 9/20 and MN read 3/19. ⚠️ Not one of those numbers said WHY; the picture said it immediately.

    So the measure is anchored on the SINGLE LARGEST box -- the body block, which is the largest
    object on a page of this book by a wide margin -- and then widened only by boxes that genuinely
    share its column (>=50% horizontal overlap). A marginal column overlaps the body horizontally by
    almost nothing and is therefore excluded by construction rather than by a threshold on its size.
    """
    if not boxes:
        # The agent cannot frame the page. It returns the full page; every cue downstream then reads
        # as thin-margin and abstains, which is the correct behaviour, not a fallback.
        return (0.0, 1.0), 0.0, 1.0
    # 🔴 R16.20a -- THE ANCHOR IS DRAWN FROM THE SAME CONFIDENT POPULATION AS THE COLUMN, AND
    # LEAVING IT OUT WAS A REAL DEFECT THAT THE PROBE COULD NOT SEE. R16.20 §3 reports that
    # swapping the anchor rule moves the corpus count from 90 to 89, and concludes the anchor is
    # not the mechanism. That is true of the anchor's IDENTITY and false of its POPULATION, and
    # the difference cost two leaves in the rebuild.
    #
    # The anchor does not merely get picked. `COLUMN_OVERLAP` is a fraction OF THE ANCHOR'S OWN
    # WIDTH, so the anchor sets the admission rule for every other box. On `NT-1582-B_0439` a
    # `Text` box scoring 0.137 spanning x 0.106-0.899 won `max(area)`; admission then demanded
    # 0.397 of horizontal overlap, and the real body text at x 0.395-0.774 is only 0.379 wide, so
    # it could not qualify AT ANY CONFIDENCE. The foot came from the upper half of the page and
    # the frame lost a third of its span. `OT2-1610-P_1135` failed the same way on a 0.199
    # `ListGroup` spanning almost the whole leaf.
    #
    # ⚠️ This is why one-knob-at-a-time was not enough here. Filtering the column alone looks
    # clean in aggregate because the interaction needs a low-confidence box to win max(area) AND
    # be wide enough to raise the bar past the real text. Two leaves in 208.
    #
    # 🔴 AND YET THE ANCHOR IS DELIBERATELY *NOT* FILTERED, AND THIS IS AN OPEN DEFECT RATHER THAN
    # A SETTLED RULE. Filtering it is the obvious repair and it does not survive measurement: the
    # body blocks the lowered floor recovers ARE the low-confidence ones, so an anchor floor
    # excludes the very boxes the whole change exists to reach. Swept over all 208 leaves against
    # the 26 frames the old bundle had collapsed:
    #
    #     anchor floor   0.10   0.15   0.20   0.25   0.40      (column floor held at 0.40)
    #     REPAIRED          7      5      5      3      0
    #     still collapsed  19     21     21     23     26
    #     BROKEN            2      1      1      1      1
    #
    # There is NO interior optimum. Unlike the column floor -- whose curve is U-shaped, which is
    # what licensed choosing 0.40 -- this one is monotone, and every cell that repairs also
    # breaks. Choosing a value would be fitting a constant to 26 leaves with no gold behind it,
    # which is the failure this function's own docstring warns about two paragraphs above.
    #
    # So: no new constant, the variant that repairs most, and the damage NAMED. `NT-1582-B_0439`
    # and `OT2-1610-P_1135` are broken by this line, `NT-1582-B_0804` moves for a third reason,
    # and 19 collapsed frames are still collapsed. All of them stay OPEN and block, and none is
    # traded away by a threshold picked to make the total look better.
    # 🔑 THE REAL FIX IS UPSTREAM: `COLUMN_OVERLAP` is a fraction OF THE ANCHOR'S OWN WIDTH, so a
    # spuriously wide anchor raises the admission bar for everyone. That is a redesign of the
    # admission rule and it needs GOLD REGIONS to adjudicate, which is step (2) of the order.
    body = max(boxes, key=lambda b: b.area)
    bw = max(1e-9, body.x1 - body.x0)
    # 🔴 R16.20 -- THE COLUMN IS FILTERED BY THE DETECTOR'S CONFIDENCE, AND THIS IS THE LINE THAT
    # LETS THE DETECTION FLOOR COME DOWN. The measure is the MEDIAN of these boxes' edges, so
    # every member votes on where the frame is. At the shipped floor of 0.40 the column held 2.0
    # boxes on the median leaf; at a detection floor of 0.10 it holds 5.0, and the median moves --
    # on 90 of 208 leaves, 50 of them by more than a tenth of the page, against a 6-leaf raster
    # noise floor. Filtering here takes that to 15, of which 8 are collapsed frames being REPAIRED.
    #
    # 🔑 IT IS NOT THE ANCHOR. I expected `max(area)` above to be the defect and it is not: three
    # confidence-aware anchor rules moved the count from 90 to 89. The anchor picks ONE box; the
    # column decides the EDGES, and a swollen column moves them whatever anchors it.
    #
    # ⚠️ `COLUMN_MIN_CONF` IS A MEASURED OPTIMUM, NOT A SAFETY MARGIN. The curve is U-shaped: 0.30
    # gives 34, 0.40 gives 15, 0.50 gives 44, 0.60 gives 69, because above 0.50 genuine body boxes
    # leave the column and the frame degrades from the other side. Raising it is not the safe
    # direction. `plates/DETECT-PROBE-2026-09-03.md` §4 holds the curve.
    scored = [b for b in boxes if b.surya_conf_seen]
    column = [b for b in boxes
              if b.area >= SMALL_AREA
              and (not b.surya_conf_seen or b.surya_conf >= D.COLUMN_MIN_CONF)
              and max(0.0, min(b.x1, body.x1) - max(b.x0, body.x0)) >= COLUMN_OVERLAP * bw]
    if not column:
        # ⚠️ NOT A FALLBACK THAT HIDES A GAP. Two different situations reach here and the caller is
        # told which by `lf.frame_why`: a leaf whose boxes carry NO score at all (an older cache,
        # or an off-the-shelf caller) in which case the filter above was INERT by construction and
        # this is the pre-R16.20 behaviour exactly; or a leaf where every box scored below the
        # framing floor, which is a real fact about the leaf and not a defect in the rule.
        column = [body]
    if not scored:
        lf.frame_why = ("no detector confidence on any box — the framing floor was INERT; "
                        "this frame is pre-R16.20 behaviour, not a filtered one")
    elif not any(b.surya_conf >= D.COLUMN_MIN_CONF for b in boxes):
        # Every box on the leaf scored below the framing floor, so the column fell back to the
        # anchor alone. REPORTED, because a leaf the detector was uncertain about everywhere is a
        # fact worth carrying, not a case to silently treat like a confident one.
        lf.frame_why = (f"all {len(boxes)} boxes scored below the framing floor "
                        f"{D.COLUMN_MIN_CONF:.2f} — the column is the anchor alone")
    elif len(scored) != len(boxes):
        lf.frame_why = (f"{len(boxes) - len(scored)} of {len(boxes)} boxes carry no detector "
                        f"confidence and BYPASSED the framing floor")
    else:
        lf.frame_why = ""
    left = st.median([b.x0 for b in column])
    right = st.median([b.x1 for b in column])
    # R14.14 -- the head and foot lines are the extreme ROTATED y of the column, so they are
    # lines PARALLEL TO THE TYPE rather than to the image edge.
    head_y = min(ry(b.cx, b.y0, lf) for b in column)
    # 🔴 R14.9 — THE FOOT BAND, ADDED BECAUSE THE PAGE HAS FURNITURE AT BOTH ENDS AND THE AGENT
    # ONLY KNEW ABOUT ONE. Leaf 409 prints the gathering signature `Z z` at the foot, centred; with
    # no foot band the centred-heading cue fired and the agent called it a CHAPTER HEADING, which
    # then made the whole leaf archetype BC. ⚠️ The head-band gold CANNOT SEE THIS — it labels the
    # top three rows — so the error was invisible to the score and visible in one drawing.
    foot_y = max(ry(b.cx, b.y1, lf) for b in column)
    return (left, right), head_y, foot_y


# ---------------------------------------------------------------- S1b: the FOUNT (R14.10a)
_FOUNT_CACHE: dict | None = None


def _rec_path(kind: str, wid: str):
    """Where a per-witness perception record lives.

    ⚠️ THE SCORED WITNESS KEEPS ITS EXISTING FILENAME, and that is not tidiness — `score_argument_
    agent.py` and `score_skew_frame.py` prove their pre-registered negatives by REBINDING `VA.FOUNT`
    and `VA.SKEW` to a path that does not exist. Reading the module global here, at call time, is
    what keeps those two proofs working. Resolve the path eagerly and both negatives would silently
    start passing while testing nothing.

    Every other witness is keyed by witness ALONE, with no leaf window in the name: their leaf sets
    come from the plate manifest and are not contiguous, so a `400-419` style window would be a lie
    about what the file covers.
    """
    if wid == WITNESS:
        return {"fount": FOUNT, "skew": SKEW, "reading": READING}[kind]
    return _HERE / "gold" / f"{kind}_{wid}.json"


def _fount_record(wid: str = WITNESS) -> dict | None:
    """The fount record for `wid`, or None if it has not been built. Loaded once per witness."""
    global _FOUNT_CACHE
    # ⚠️ `score_argument_agent.py` clears this by assigning None. Tolerating that here is what lets
    # the withheld-record negative keep working against a per-witness cache.
    if not isinstance(_FOUNT_CACHE, dict):
        _FOUNT_CACHE = {}
    if wid not in _FOUNT_CACHE:
        p = _rec_path("fount", wid)
        if not p.is_file():
            return None
        _FOUNT_CACHE[wid] = json.loads(p.read_text())
    return _FOUNT_CACHE[wid]


def attach_fount(lf: Leaf) -> None:
    """Hang each row segment's fount evidence on the box that holds it.

    ⚠️ ASSIGNED TO THE SMALLEST BOX CONTAINING THE SEGMENT'S CENTRE, and the reason is the nesting
    the drawing showed in R14.7: Surya's body `Text` block physically CONTAINS the chapter head and
    the argument, so "which box is this line in" has an outer answer and an inner one. The inner one
    is the only one that can distinguish them -- assigning to the container would pour the argument's
    italic into the body block and dilute it to nothing. This is `BIND_TIGHTEST`'s reasoning applied
    one step earlier, and it is stated in both places deliberately.

    ⚠️ THE PAGE'S OWN SKEW IS SUBTRACTED. `ARGUMENT_SLANT_MIN` is an ABSOLUTE threshold because
    roman is upright BY DEFINITION -- but a skewed scan shifts every row together, so the leaf's
    roman slant is the reference. Where that roman is NOT upright the whole leaf abstains rather
    than reporting its scripture as italic (`region_head.ARGUMENT_UPRIGHT_TOL`).
    """
    rec = _fount_record(lf.witness)
    if rec is None:
        lf.fount_why = (f"fount record not built for {lf.witness} — run "
                        f"witness/build_fount_record.py --build --witness {lf.witness}")
        return
    page = next((d for d in rec["leaves"] if d["leaf"] == lf.leaf), None)
    if page is None:
        lf.fount_why = f"leaf {lf.leaf} is not in the fount record"
        return
    mode = page.get("slant_mode")
    if mode is None:
        lf.fount_why = f"no roman slant reference for this leaf ({page.get('why')})"
        return
    if abs(mode) > rec["upright_tol"]:
        lf.fount_why = (f"this leaf's roman deslants at {mode:.1f}° — beyond the "
                        f"{rec['upright_tol']:.0f}° upright tolerance, so an absolute fount test "
                        f"would read its scripture as italic")
        return

    lf.fount_why = ""
    for b in lf.boxes:
        b.fount_seen = True
    for s in page["segments"]:
        cx, cy = 0.5 * (s["x0"] + s["x1"]), 0.5 * (s["y0"] + s["y1"])
        holding = [b for b in lf.boxes if b.x0 <= cx <= b.x1 and b.y0 <= cy <= b.y1]
        if not holding:
            continue
        b = min(holding, key=lambda x: x.area)
        b.fount_n += 1
        if s["slant"] - mode >= rec["slant_min"]:
            b.fount_it += 1


_SKEW_CACHE: dict | None = None


def _skew_record(wid: str = WITNESS) -> dict | None:
    global _SKEW_CACHE
    if not isinstance(_SKEW_CACHE, dict):
        _SKEW_CACHE = {}
    if wid not in _SKEW_CACHE:
        p = _rec_path("skew", wid)
        if not p.is_file():
            return None
        _SKEW_CACHE[wid] = json.loads(p.read_text())
    return _SKEW_CACHE[wid]


def attach_skew(lf: Leaf) -> None:
    """R14.14 -- hang this leaf's own baseline angle on the leaf. Runs BEFORE `frame`.

    ⚠️ ORDER MATTERS AND IS NOT INTERCHANGEABLE. `frame` derives the head and foot lines as the
    extreme rotated-y of the column boxes, so it needs the angle already attached. `attach_fount`
    and `attach_reading` run AFTER `frame` because they are expressed in the measure. Getting this
    backwards would silently frame every leaf at zero degrees and look exactly like success.
    """
    rec = _skew_record(lf.witness)
    if rec is None:
        lf.skew_why = (f"skew record not built for {lf.witness} — run "
                       f"witness/build_skew_record.py --build --witness {lf.witness}")
        return
    d = next((x for x in rec["leaves"] if x["leaf"] == lf.leaf), None)
    if d is None:
        lf.skew_why = f"leaf {lf.leaf} is not in the skew record"
        return
    if d.get("angle_deg") is None:
        lf.skew_why = f"this leaf's baseline angle could not be measured — {d.get('why')}"
        return
    lf.skew, lf.skew_seen, lf.skew_why = float(d["angle_deg"]), True, ""


def ry(x: float, y: float, lf: Leaf) -> float:
    """A point's y IN THE LEAF'S OWN ROTATED FRAME. The one place the rotation is applied.

    ⚠️ EVERY VERTICAL TEST IN THIS FILE MUST GO THROUGH HERE. A single comparison left as plain `y`
    reintroduces the horizontal cut for whichever class it decides, and it would be invisible: the
    agent would still produce a label, just the wrong one on tilted leaves. That is the shape of
    defect this project keeps paying for.
    """
    if not lf.skew_seen:
        return y
    return y - math.tan(math.radians(lf.skew)) * (x - PIVOT_X)


def box_mass_ry(b: Box, lf: Leaf) -> float:
    """The box's MASS in rotated y. ⚠️ Mass, never the last pixel -- this file's standing rule."""
    return ry(b.cx, 0.5 * (b.y0 + b.y1), lf)


def pn_candidate(b: Box, lf: Leaf) -> bool:
    """Is this box worth a confirming read? DECLARED ONCE — the agent and the record builder share it.

    ⚠️ A SECOND COPY OF THIS PREDICATE WOULD BE THE R14.10a DEFECT AGAIN. `score_foreedge` kept its
    own copy of the class inventory so that "the agent has no name for this class" would be a checked
    claim, and the run that scored `AR` at 4/4 also printed `AR ⚠️ NO NAME IN THE AGENT` in the same
    output. If the builder and the cue disagreed about what a candidate is, the record would hold
    readings for boxes the cue never asks about and be silent for boxes it does.

    ⚠️ THIS ANSWERS "SHOULD I LOOK?", NEVER "WHAT IS IT?".
    """
    (ml, mr), head_y = lf.measure, lf.head_y
    mw = max(1e-9, mr - ml)
    if b.area >= PN_MAX_AREA:
        return False
    # 🔴 NOT `mass_y <= head_y` ALONE, AND THE FOUR LEAVES THAT PROVED IT WERE FIRST REPORTED AS A
    # DETECTOR MISS BY THIS VERY PREDICATE. On leaves 401, 402, 409 and 417 the page number's mass
    # sits at 0.063-0.069 against a head line of 0.059-0.065 — BELOW IT BY ABOUT 0.005 OF A PAGE —
    # so a pure band test drops them, and all four were silently named `MT`. ⚠️ That is this file's
    # own standing rule violated one more time: NO CUE MAY TURN ON A LAST PIXEL. `head_y` is derived
    # from the topmost LARGE box, so it moves with the body block and not with the furniture.
    #
    # ⚠️ AND THE REPAIR IS THE ONE CUE 2b ALREADY MAKES AT THE OTHER END OF THE PAGE: the detector's
    # own `PageHeader`/`PageFooter` judgement is the second cue, POSITION-CLAMPED so a mislabelled
    # box low on the leaf can never be dragged into the head band. Stated in both places deliberately.
    #
    # 🔴 AND THE FALSE ABSENCE IS THE LESSON, NOT THE FIX. Bounded by the band, this predicate
    # reported "4 of 20 leaves carry no page-number box" — a DETECTION gap — and the bound was the
    # search, not the page. `audit_label_sources.py` has now recorded this shape twice (a directory,
    # then a field name) and this is the third: **a bounded search returns "not found" in exactly
    # the shape an exhaustive one does.** GOLD-FOREEDGE caught it, because that gold is not
    # band-limited and holds a `PN` entry on two of the four.
    mass_y = box_mass_ry(b, lf)
    in_head = mass_y <= head_y or (b.surya in FURNITURE and
                                   mass_y < 0.5 * (head_y + lf.foot_y))
    if not in_head:
        return False
    rel_h = (b.cx - ml) / mw
    return rel_h < PN_EDGE or rel_h > 1.0 - PN_EDGE


_READ_CACHE: dict | None = None


def _reading_record(wid: str = WITNESS) -> dict | None:
    """The reading record for `wid`, or None if it is absent or STALE. Loaded once per witness.

    ⚠️ A RECORD BUILT BY ANOTHER MODEL IS REFUSED, NOT USED. R13.1's finding was that a component
    can be pointed at and never loaded; the mirror-image defect is a cached reading that outlives the
    model that produced it and carries the selected model's authority while holding another's output.
    The stamp carries the artefact DIGEST, not just the name, because a name can be reused.
    """
    global _READ_CACHE
    if not isinstance(_READ_CACHE, dict):
        _READ_CACHE = {}
    if wid not in _READ_CACHE:
        p = _rec_path("reading", wid)
        if not p.is_file():
            return None
        d = json.loads(p.read_text())
        import recogniser as RG
        if d.get("stamp", {}).get("model_sha") != RG.provenance()["model_sha"]:
            return None
        _READ_CACHE[wid] = d
    return _READ_CACHE[wid]


def attach_reading(lf: Leaf) -> None:
    """Hang the confirming read on each candidate box. Addressed by CONTAINED CENTRE, like the fount.

    ⚠️ WHERE THE RECORD IS ABSENT EVERY CANDIDATE STAYS `read_seen = False`, and `_cue` ABSTAINS on
    it rather than falling through to the note logic. That is the pre-registered negative
    (`score_pagenumber_agent.py --withheld`): a cue whose evidence can be removed without changing
    the answer was never reading the evidence.
    """
    rec = _reading_record(lf.witness)
    if rec is None:
        lf.read_why = (f"reading record for {lf.witness} absent or built by a different model — "
                       f"run witness/build_reading_record.py --build --witness {lf.witness}")
        return
    lf.read_why = ""
    for r in rec["readings"]:
        if r["leaf"] != lf.leaf:
            continue
        cx, cy = 0.5 * (r["x0"] + r["x1"]), 0.5 * (r["y0"] + r["y1"])
        holding = [b for b in lf.boxes if b.x0 <= cx <= b.x1 and b.y0 <= cy <= b.y1]
        if not holding:
            continue
        b = min(holding, key=lambda x: x.area)
        b.read_text, b.read_seen = r["text"], True


# ---------------------------------------------------------------- S2: ARCHETYPE
def classify_archetype(lf: Leaf) -> tuple[str, float, str]:
    """S2 -- what KIND of page is this, decided from the page's own visual structure.

    ⚠️ Decided BEFORE any region is COMMITTED, because which classes a leaf CAN carry is a property
    of what kind of leaf it is (§3.2a).

    🔴 R14.9 — THE FIRST VERSION REIMPLEMENTED A SUBSET OF THE NAMING CUES, AND THAT IS WHY IT WAS
    WRONG. It detected apparatus with the BESIDENESS cue alone, while `name_regions` has TWO cues
    that can produce a MarginNote -- besideness, and head-band-off-centre. So on a leaf whose notes
    are ALL head-band notes (402, 413, 415: outside fractions 0.37 / 0.48 / 0.44, all under the
    besideness boundary) the classifier saw no apparatus, typed the page `A`, and `A` FORBIDS
    MarginNote -- so the naming step then had to abstain on a note it had correctly identified.
    Three of the six residual MN misses were this one defect.

    ⚠️ **TWO CODE PATHS ANSWERING ONE QUESTION IS THIS PROJECT'S SIGNATURE DEFECT**, and here it had
    got as far as making the agent contradict itself. The repair is structural, not a threshold
    nudge: the archetype is now derived from the SAME `_cue()` function `name_regions` uses, run
    UNCONSTRAINED over the page. §3.2a's ordering is preserved in the sense that matters -- the
    archetype is still fixed before any region is committed, and it still FORBIDS -- but it can no
    longer be blind to a cue the namer possesses.
    """
    inv: dict[str, int] = {}
    for b in lf.boxes:
        lab, _c, _why = _cue(b, lf)
        inv[lab] = inv.get(lab, 0) + 1

    # 🔴 R14.10a — AN ARGUMENT IS EVIDENCE THAT A CHAPTER OPENS HERE, and it enters the archetype
    # on that footing rather than as a class the archetype gates. The direction matters: the
    # rejected design made `AR` depend on a detected `CH`, which on four of these ten leaves would
    # have made the misfiled box the anchor for finding itself. Reading it the other way round
    # means an argument the agent CAN see rescues a chapter opening whose heading it missed —
    # `region_head`'s own objection to the positional rule, answered rather than inherited.
    n_mn, n_ch, n_ar = inv.get(MN, 0), inv.get(CH, 0), inv.get(AR, 0)
    n_open = n_ch + n_ar
    what = " AND ".join(x for x in (f"{n_ch} heading-cue box(es)" if n_ch else "",
                                    f"{n_ar} ARGUMENT box(es)" if n_ar else "") if x)
    if n_mn and n_open:
        a, cause = "BC", f"{n_mn} note-cue box(es) AND {what}"
    elif n_mn:
        a, cause = "B1", f"{n_mn} box(es) read as marginal apparatus"
    elif n_open:
        a, cause = "C", f"{what} — a chapter opens here"
    else:
        a, cause = "A", "no note cue and no chapter-opening cue fired — plain text page"

    # Confidence is the STRENGTH OF THE EVIDENCE, not a fitted score: the median confidence of the
    # cues that decided it. One box barely clearing a boundary is a weak archetype call, and the
    # abstention path below reads that.
    deciding = [c for b in lf.boxes
                for lab, c, _ in [_cue(b, lf)]
                if lab in ((MN, CH, AR) if a == "BC" else (MN,) if a == "B1"
                           else (CH, AR) if a == "C" else ())]
    conf = st.median(deciding) if deciding else 0.60
    return a, conf, cause


def centre_offset(b: Box, ml: float, mr: float) -> float:
    """R14.11 -- how far this box's centre sits from the measure's centre, IN UNITS OF ITS OWN WIDTH.

    The dimensionless quantity that replaced `CENTRED_LO/HI`. `<= 0.5` means the measure's
    centre-line falls INSIDE the box, which is what "set on the measure" means; `> 0.5` means the
    box is pushed clear of the centre. ⚠️ It is scaled by the BOX's width and not by the measure's,
    which is the whole reason it separates: a running head and a side-note may sit at similar
    fractions of the measure, but a running head STRADDLES the centre-line and a note does not.
    """
    w = max(1e-9, b.x1 - b.x0)
    return abs(b.cx - 0.5 * (ml + mr)) / w


def _outside_frac(b: Box, ml: float, mr: float) -> float:
    """What share of this box's width falls OUTSIDE the measure. The side-note cue."""
    w = max(1e-9, b.x1 - b.x0)
    inside = max(0.0, min(b.x1, mr) - max(b.x0, ml))
    return 1.0 - inside / w


# ---------------------------------------------------------------- S3/S4: NAME + BOUND
def _cue(b: Box, lf: Leaf) -> tuple[str, float, str]:
    """THE cue set, unconstrained by archetype -> (label, confidence, cause).

    🔴 R14.9 MADE THIS ONE FUNCTION. It is called by `classify_archetype` (to see what the page
    contains) and by `name_regions` (to commit a label, after the archetype's FORBIDS is applied).
    ⚠️ It must never be reimplemented at either call site: the defect R14.9 fixed was precisely a
    second, poorer copy of these cues inside the archetype classifier, which made the agent
    contradict itself on three leaves.

    ⚠️ EVERY BRANCH RECORDS ITS CAUSE. §3.0 S4's abstention clause is only worth anything if the
    abstention says WHY; an untyped region with no cause is the same null the fail-safe-to-body
    branch produces, wearing a better name.
    """
    (ml, mr), head_y = lf.measure, lf.head_y
    mw = max(1e-9, mr - ml)
    out = _outside_frac(b, ml, mr)


    # CUE 0 -- THE FOUNT. R14.10a. ⚠️ IT RUNS BEFORE THE SIZE PRIOR BECAUSE THE SIZE PRIOR IS THE
    # DEFECT: measured over ten adjudicated argument blocks, `SMALL_AREA` alone decided whether the
    # class came out as `MT` (six boxes above 0.05) or `CH` (four below it). A cue that reads what
    # the BOOK distinguishes has to be asked before a constant that reads nothing.
    #
    # ⚠️ BUT BESIDENESS STILL OUTRANKS IT, and that is not a preference either — THIS EDITION SETS
    # ITS SIDE-NOTES IN ITALIC TOO (`region_head`, measured: leaf 405's note beside a verse). So
    # italic ALONE cannot name an argument; italic ON THE MEASURE can. The `out < OUTSIDE_FRAC`
    # guard is what makes the fount test safe to ask this early, and removing it would hand every
    # italic side-note the `AR` label.
    if out < OUTSIDE_FRAC and b.fount_seen:
        span = (min(b.x1, mr) - max(b.x0, ml)) / mw
        frac, n = b.italic_frac, b.fount_n
        if n >= AR_MIN_SEGMENTS and span >= AR_MEASURE_SPAN:
            if frac >= AR_ITALIC_MAJORITY:
                return (AR, min(0.99, 0.55 + (frac - AR_ITALIC_MAJORITY)),
                        f"{b.fount_it} of its {n} lines of type deslant as ITALIC "
                        f"({frac:.0%}) and it is set to {span:.0%} of the measure — this is the "
                        f"chapter's ARGUMENT, not scripture and not a heading")
            # ⚠️ THE ABSTENTION IS THE POINT OF THE CLAUSE, not an afterthought. R14.10's
            # pre-registered rule requires a new class to be ABSTAINABLE — adding a name must not
            # add a confident wrong answer — and a block of MIXED fount is exactly where a
            # confident answer would be wrong. It declines and names the mixture.
            if frac >= AR_ITALIC_MAJORITY - THIN_MARGIN:
                return (ABSTAIN, 1.0 - (AR_ITALIC_MAJORITY - frac) / THIN_MARGIN,
                        f"set to {span:.0%} of the measure with {b.fount_it} of {n} lines italic "
                        f"({frac:.0%}) — too near the majority to call argument against scripture")

    # 🔴 SIZE IS NOT THE CUE, AND THE DRAWING IS WHERE THAT WAS LEARNED (R14.7, leaf 412). Reading
    # `area >= SMALL_AREA` as "this is the body block" made the whole MARGINAL COLUMN body text -- a
    # tall box is large, and this edition sets its notes in a column running the height of the page.
    # ⚠️ BESIDENESS OUTRANKS SIZE: a big box beside the measure is a marginal COLUMN, a big box on
    # the measure is the body. Same cue, applied first.
    if b.area >= SMALL_AREA:
        if out >= OUTSIDE_FRAC:
            return (MN, min(1.0, 0.5 + (out - OUTSIDE_FRAC)),
                    f"a LARGE box with {out:.0%} of its width outside the measure — "
                    f"this is the marginal column, not the body")
        return (MT, 0.90, "spans the measure — this is the body block")

    # CUE 0b -- THE PAGE NUMBER. R14.10b, and it is the first cue in this agent DECIDED BY A READ.
    #
    # ⚠️ IT RUNS BEFORE BESIDENESS, WHICH IS A REVERSAL AND IS DELIBERATE. A page number sits out at
    # the fore-edge, so `out >= OUTSIDE_FRAC` fires on it and CUE 1 would name it `MN` — which is
    # exactly what the agent did to 15 of them. Besideness outranks the FOUNT because this edition
    # sets side-notes in italic too; it does NOT outrank the read, because "it is beside the body"
    # and "it says 380" are not competing readings of one piece of evidence — the second is simply
    # decisive and the first is not. ⚠️ The precedence is safe ONLY because `pn_candidate` is narrow:
    # a box must be small even by furniture standards AND at an extreme of the measure AND in the
    # head band before the read is ever consulted.
    #
    # 🔴 AND POSITION CANNOT DECIDE THIS CLASS — MEASURED, NOT ASSUMED, AND THE ROADMAP'S OWN
    # FORMULATION IS REFUTED BY IT. The row filed `PN` as "a head-band box at the extreme fore-edge,
    # BEYOND where a note sits". On this window page numbers run 0.000-0.043 and 0.812-0.972 of the
    # measure and head-band notes run 0.010-0.110 and 0.857-1.072: the two populations OVERLAP ON
    # BOTH SIDES, so no constant separates them — the R2.2o.1 shape, one class over. What separates
    # them is that one says `380` and the other says `Sacrifices for`.
    if pn_candidate(b, lf):
        txt = b.read_text.strip()
        rel_p = (b.cx - ml) / mw
        if not b.read_seen:
            # The record was never built, or was built by another model and REFUSED as stale. ⚠️ THE
            # ABSTENTION IS THE POINT: falling through here would restore the exact behaviour that
            # hid this class — a confident `MN` on page furniture, costing nothing.
            return (ABSTAIN, 0.0,
                    f"small ({b.area:.4f} of the page) and out at {rel_p:.2f} of the measure — a "
                    f"page number or a short side-note, and only a read can tell them apart. "
                    f"{lf.read_why or 'no reading for this box'}")
        if txt.isdigit():
            return (PN, 0.95,
                    f"in the head band, out at {rel_p:.2f} of the measure, and the confirming "
                    f"read returns {txt!r} — all digits. This is the PAGE NUMBER")
        if not txt:
            # ⚠️ THIS BRANCH DECIDES REAL BOXES — a third of them. An empty reading is NOT evidence
            # of "not a numeral", it is the ABSENCE of evidence, and the two are the same only to a
            # scorer that never had to be right.
            return (ABSTAIN, 0.5,
                    f"small and out at {rel_p:.2f} of the measure, but the confirming read came "
                    f"back EMPTY — no evidence either way, and a page number and a short side-note "
                    f"are indistinguishable here without it")
        # A LETTERED READING IS A NEGATIVE WITH CONTENT: this is not a page number, and the cues
        # below are the right answer for it. ⚠️ The cue must never REMOVE a correct `MN`; it exists
        # to stop one being invented.

    # CUE 1 -- BESIDE the measure. The marginal note, and the cue R2.2's four span rules could not
    # reach: a note is not FAR from the body, it is BESIDE it.
    if out >= OUTSIDE_FRAC:
        margin = out - OUTSIDE_FRAC
        if margin < THIN_MARGIN:
            return (ABSTAIN, 1.0 - margin / THIN_MARGIN,
                    f"straddles the measure edge ({out:.2f} outside, boundary {OUTSIDE_FRAC:.2f}) "
                    f"— beside or inside cannot be told apart here")
        return (MN, min(1.0, 0.5 + margin),
                f"{out:.0%} of its width lies outside the measure — it sits BESIDE the body")

    # CUE 2 -- the HEAD BAND. Judged on the box's MASS, never its last pixel: `y1 <= head_y` failed
    # by 0.0015 of a page on leaf 400 and killed 11 of 20 running heads. A cue that turns on a last
    # pixel is a threshold wearing a cue's clothes.
    if box_mass_ry(b, lf) <= head_y:
        # 🔴 THE HEAD BAND HOLDS TWO DIFFERENT THINGS, and calling both `RH` cost 14 of the 19
        # marginal notes. This edition sets head-band notes at the SAME HEIGHT as the running head,
        # out at the fore-edge, so height cannot separate them and besideness does not fire (they
        # straddle the edge). ⚠️ The cue that DOES separate them is the reader's: A RUNNING HEAD IS
        # CENTRED ON THE MEASURE; A HEAD-BAND NOTE IS PUSHED TO A SIDE -- read off this leaf's own
        # measure, not from a fitted position.
        # R14.11 -- the test is now the GEOMETRIC FACT and not a band: does the measure's
        # centre-line fall inside this box? `rel_h` survives for the CAUSE only, because "pushed out
        # to 0.98 of the measure" is what a reader can check against the page, while an offset in
        # box-widths is what the agent decides on. ⚠️ Both are printed, and the deciding one is
        # named as such -- a cause that quotes a quantity the cue did not use is a cause that
        # cannot be audited.
        rel_h = (b.cx - ml) / mw
        off = centre_offset(b, ml, ml + mw)
        d = abs(off - 0.5)
        if off <= 0.5:
            # 🔴 R14.9 -- AND A CENTRED HEAD-BAND BOX IS STILL TWO THINGS. On leaf 411 the chapter
            # heading sits directly under the running head, both centred, so position cannot split
            # them either. ⚠️ Surya's OWN CLASS is the cue here, and it is a legitimate one: its
            # vocabulary separates PAGE FURNITURE (PageHeader / PageFooter) from CONTENT (Text /
            # SectionHeader), which is exactly the question running-head-versus-heading turns on,
            # and it is a learned visual judgement rather than a constant we fitted.
            if b.surya in FURNITURE:
                return (RH, min(0.99, 0.60 + d),
                        f"in the head band, CENTRED on the measure (at {rel_h:.2f}), and the "
                        f"detector calls it page furniture ({b.surya}) — the running head")
            return (CH, 0.65,
                    f"in the head band and centred (at {rel_h:.2f}) but the detector calls it "
                    f"CONTENT ({b.surya}), not furniture — a heading, not the running head")
        if d < CENTRED_ABSTAIN:
            return (ABSTAIN, 1.0 - d / CENTRED_ABSTAIN,
                    f"in the head band with the measure's centre-line sitting within "
                    f"{d:.3f} of a box-width of this box's edge (offset {off:.3f}) — on the "
                    f"measure or clear of it cannot be told apart here")
        return (MN, min(1.0, 0.55 + d),
                f"in the head band and its centre sits {off:.2f} of its OWN WIDTH clear of the "
                f"measure's centre-line, so the centre-line misses it entirely (it lies at "
                f"{rel_h:.2f} of the measure) — a head-band side-note, not the running head")

    # CUE 2b -- the FOOT BAND. Page furniture again, and position alone is decisive: this box's mass
    # sits BELOW the bottom of the body block, where scripture does not go. ⚠️ Without this cue the
    # centred-heading test below fires on a gathering signature (leaf 409's `Z z`) and invents a
    # chapter opening, which then propagates into the ARCHETYPE. A missing class is never a skipped
    # box -- it is a box misfiled into the nearest class the agent does have.
    #
    # 🔴 AND THE FOOT BAND HAS THE HEAD BAND'S NESTING PROBLEM, ONE END DOWN. On leaf 409 the body
    # `Text` box runs to 0.906 and the signature sits at 0.885-0.904 — INSIDE it — so a pure
    # position test never fires. ⚠️ The detector's own class is the second cue and it is decisive
    # here for the same reason it is for the running head: `PageFooter` IS the "this is page
    # furniture" judgement, made by a model trained on millions of pages. The position test is kept
    # as a CLAMP so a mislabelled box high on the leaf cannot be dragged into the foot band.
    mass_y = box_mass_ry(b, lf)
    if mass_y >= lf.foot_y or (b.surya in FURNITURE and mass_y > 0.5 * (lf.head_y + lf.foot_y)):
        rel_f = (b.cx - ml) / mw
        if rel_f >= FOOT_CATCHWORD_REL:
            return (CAT, 0.70,
                    f"below the body block and out at {rel_f:.2f} of the measure — a catchword")
        return (SIG, 0.70,
                f"below the body block at {rel_f:.2f} of the measure — a gathering signature")

    # CUE 3 -- CENTRED inside the measure, below the head. A heading, not a line of text.
    rel = (b.cx - ml) / mw
    if (HEADING_LO <= rel <= HEADING_HI
            and ry(b.cx, b.y0, lf) > head_y and ry(b.cx, b.y1, lf) <= lf.foot_y):
        return (CH, 0.70,
                f"small, centred in the measure (at {rel:.2f}) and below the head — a heading")

    # No cue fired decisively.
    return (MT, 0.55,
            "small, inside the measure, not centred and not above the body — read as body")


def name_regions(lf: Leaf) -> None:
    """S3/S4 -- COMMIT a label per box, applying the archetype's FORBIDS contract."""
    forbid = ARCHETYPES.get(lf.archetype, {}).get("forbids", set())
    for b in lf.boxes:
        b.label, b.conf, b.cause = _cue(b, lf)
        # §3.2a's FORBIDS contract, enforced rather than described. A class the archetype forbids is
        # NEVER silently relabelled to a permitted one -- that would launder a wrong archetype into a
        # confident region call. It becomes an ABSTENTION naming the contradiction.
        if b.label in forbid:
            b.cause = (f"cue says {b.label}, but archetype {lf.archetype} "
                       f"({ARCHETYPES[lf.archetype]['name']}) FORBIDS it — contradiction, not a guess")
            b.label, b.conf = ABSTAIN, 0.0

def settle(lf: Leaf) -> Leaf:
    """S1b -> S2 -> S3/S4. ONE definition of the order the agent works in.

    ⚠️ THIS EXISTS BECAUSE THE SEQUENCE HAD TWO CALL SITES AND R14.10a WOULD HAVE MADE IT THREE.
    `read_leaf` and `leaf_from_cache` each spelled out frame / archetype / name for themselves, so
    every new perception step had to be remembered twice. That is the same shape as the defect R14.9
    repaired one level down — two code paths answering one question — caught here before it could
    cost anything, which is the only cheap time to catch it.
    """
    attach_skew(lf)          # R14.14 -- BEFORE `frame`; the frame is expressed in rotated y
    lf.measure, lf.head_y, lf.foot_y = frame(lf.boxes, lf)
    # 🔴 R16.20 -- THE CUE FLOOR, AND ITS POSITION IN THIS SEQUENCE IS THE WHOLE DESIGN.
    # It runs AFTER `frame` and BEFORE everything that names, because the two steps want
    # OPPOSITE things from a low-confidence box:
    #   * `frame` NEEDS them. The body blocks the lowered detection floor recovers ARE the
    #     low-confidence ones, and 7 of the 26 collapsed frames are repaired by an anchor that
    #     scores below 0.40. Filtering before `frame` returns all 7 repairs to collapsed.
    #   * every CUE is harmed by them, costing 6 MarginNote entries (117/121 -> 111/121).
    # Filtering in one place at one time cannot serve both, so the split is by STAGE.
    #
    # ⚠️ WITHHELD, NOT DISCARDED, AND THE DIFFERENCE IS THE ONE E2/E14 ALREADY TAUGHT THIS FILE.
    # A box that was never offered to a cue and a box a cue rejected are different states. These
    # are kept on the leaf, written to the bundle, and counted in `withheld_why`, so "the agent
    # did not name this" stays distinguishable from "the agent did not see this" — and so R16.6
    # can lower this floor without re-detecting anything.
    keep, held = [], []
    for b in lf.boxes:
        (held if b.surya_conf_seen and b.surya_conf < D.CUE_MIN_CONF else keep).append(b)
    lf.boxes, lf.withheld = keep, held
    lf.withheld_why = (f"{len(held)} of {len(held) + len(keep)} boxes scored below the cue floor "
                       f"{D.CUE_MIN_CONF:.2f} — offered to `frame`, withheld from every cue"
                       if held else "")
    attach_fount(lf)
    # ⚠️ AFTER `frame`, NECESSARILY — `pn_candidate` is expressed in the measure, and the measure is
    # what `frame` derives. A perception step that ran first would have to invent its own frame,
    # which is the second-source-of-truth defect this file has now paid for twice.
    attach_reading(lf)
    lf.archetype, lf.arch_conf, lf.arch_cause = classify_archetype(lf)
    name_regions(lf)
    return lf


def read_leaf(image, leaf_no: int, predictor) -> Leaf:
    """S1 -> S2 -> S3/S4 for one leaf. The whole agent, in the order §3.0 states it."""
    return settle(Leaf(leaf=leaf_no, boxes=see(image, predictor)))


def leaf_from_cache(d: dict, witness: str = WITNESS) -> Leaf:
    """Rebuild a Leaf from cached PERCEPTION (boxes only) and re-run the naming.

    ⚠️ THE CACHE HOLDS S1's OUTPUT ONLY -- the boxes Surya emitted -- and never a label. Caching a
    DECISION would mean a cue change silently scored against stale calls, which is the shape of every
    defect this project keeps finding. S2-S4 re-run on every invocation.

    ⚠️ `witness` IS PART OF THE ADDRESS, NOT DECORATION (R16.2). A bare leaf ordinal names different
    pages in different witnesses, and every perception record is looked up by the pair. Defaulting to
    the scored witness keeps the cache path byte-identical for existing callers.

    ⚠️ ONLY THE PERCEPTION KEYS ARE READ BACK. A plate record also carries `label`, `conf` and
    `cause`; taking those would feed the agent its own previous DECISION and score a cue against
    itself. The keys are listed explicitly here so that widening the source cannot widen the read.

    🔑 R16.20 -- `surya_conf` JOINS THAT LIST, AND THE DISTINCTION IS THE WHOLE REASON IT MAY.
    It is the DETECTOR's score, produced before any cue ran, which makes it perception in exactly
    the sense `x0` is. `conf` beside it is the CUE's confidence in a label this agent chose, and
    that one still stays out. Same file, adjacent fields, opposite status.

    ⚠️ A RECORD WRITTEN BEFORE R16.20 HAS NO SCORE, and that is read as UNSEEN rather than as zero.
    `frame()`'s framing floor then goes inert for that leaf and says so in `lf.frame_why`, which is
    the honest answer: an old cache cannot be filtered by a number it never stored, and pretending
    its boxes all scored 0.0 would empty the column on every leaf of it.
    """
    return settle(Leaf(leaf=d["leaf"], witness=witness,
                       boxes=[Box(**{k: b[k] for k in ("x0", "y0", "x1", "y1", "surya")},
                                  surya_conf=b.get("surya_conf", 0.0),
                                  surya_conf_seen="surya_conf" in b)
                              for b in d["boxes"]]))


def build_cache() -> list[Leaf]:
    from PIL import Image

    vol, sig = [k for k in W.WITNESSES if W.wid(*k) == WITNESS][0]
    leaves = W.leaves(vol, sig)
    # R16.20 -- the cap-lifted predictor, from the module that owns the detection constants.
    pred = D.predictor()
    out = []
    for i in range(LEAF_LO, LEAF_HI):
        im = Image.open(str(leaves[i])).convert("RGB")
        boxes = see(im, pred)
        out.append({"leaf": i, "w": im.size[0], "h": im.size[1],
                    "boxes": [{"x0": b.x0, "y0": b.y0, "x1": b.x1, "y1": b.y1,
                               "surya": b.surya, "surya_conf": b.surya_conf}
                              for b in boxes]})
        print(f"  leaf {i}: {len(boxes)} boxes", flush=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"witness": WITNESS, "leaves": out}, indent=1))
    print(f"\nperception cached -> {CACHE.relative_to(_HERE.parent)}")
    return [leaf_from_cache(d) for d in out]


def load_leaves() -> list[Leaf]:
    if CACHE.is_file():
        return [leaf_from_cache(d) for d in json.loads(CACHE.read_text())["leaves"]]
    print("no perception cache — running Surya once (this is the slow part)\n")
    return build_cache()


# ---------------------------------------------------------------- scoring
MIN_BIND_FRAC = 0.50   # R2.1i: a binding must be SUBSTANTIAL, never merely non-zero


def _ov(a, b):
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


# ⚠️ TWO DECLARED ADDRESSING RULES, BOTH REPORTED — the same discipline R14.0 applied to its two
# label maps, and for the same reason: a rule chosen after seeing the numbers is the rule that
# flatters. Surya's boxes NEST — its body `Text` block physically contains the running head and the
# chapter head — so "which box does this gold entry belong to" has two defensible answers:
#
#   BIND_OVERLAP  the box covering most of the entry's area. R14.0's rule, kept verbatim so the
#                 agent's numbers are like-for-like comparable with Surya off the shelf. ⚠️ Under
#                 nesting it prefers the OUTER box, because a container covers the entry completely.
#   BIND_TIGHTEST the SMALLEST box that substantially contains the entry. The right answer for
#                 nested layout objects: a running head inside a page-sized block is addressed by
#                 the running-head box, not by the block. ⚠️ This rule was NOT invented to raise a
#                 score — it is written here because the drawing showed the nesting, and it is
#                 reported alongside, never instead.
BIND_OVERLAP, BIND_TIGHTEST = "BIND_OVERLAP", "BIND_TIGHTEST"


def _bind(e, boxes, rule=BIND_OVERLAP):
    ea = max(1e-9, (e["xrf"] - e["xlf"]) * (e["y1f"] - e["y0f"]))
    cands = []
    for b in boxes:
        a = _ov((e["xlf"], e["xrf"]), (b.x0, b.x1)) * _ov((e["y0f"], e["y1f"]), (b.y0, b.y1))
        if a >= MIN_BIND_FRAC * ea:
            cands.append((b, a))
    if not cands:
        return None, 0.0
    if rule == BIND_TIGHTEST:
        b, a = min(cands, key=lambda ba: ba[0].area)
    else:
        b, a = max(cands, key=lambda ba: ba[1])
    return b, a


def headband_score(leaves=None, rule=BIND_OVERLAP):
    """GOLD-HEADBAND scored, as (total_ok, total, {class: [ok, n]}). THE ONE PLACE IT IS COMPUTED.

    🔴 R14.11, 2026-08-28 — EXTRACTED BECAUSE TWO SCORERS HELD RESTATED COPIES AND BOTH WENT STALE
    THE MOMENT THE AGENT IMPROVED. `score_foreedge.py` carried `HEADBAND_MN = 16 / 19` as a literal
    and `score_skew_frame.py` carried the whole vector as `S2_EXPECT`; when this step moved the
    agent 115/121 -> 117/121, one silently compared the fore-edge against a figure the head band no
    longer scored, and the other reported a FALSE FAIL against the rotation. ⚠️ This is the SAME
    defect the fore-edge scorer's own docstring already records one level up, where its restated
    copy of `CLASSES` scored `AR 4/4` while printing "NO NAME IN THE AGENT" about those four boxes.
    A measured figure restated in a second file is a figure that will drift, and it drifts SILENTLY
    because both copies keep printing.
    """
    if leaves is None:
        leaves = load_leaves()
    lm = {lf.leaf: lf for lf in leaves}
    gold = json.loads(GOLD.read_text())
    per: dict[str, list[int]] = {}
    tot_ok = tot = 0
    for e in gold["labels"]:
        if "xlf" not in e:
            continue
        lf = lm.get(e["leaf"])
        if lf is None:
            continue
        b, _ = _bind(e, lf.boxes, rule)
        if b is None:
            continue
        g = e["label"]
        per.setdefault(g, [0, 0])
        per[g][1] += 1
        tot += 1
        if b.label == g:
            per[g][0] += 1
            tot_ok += 1
    return tot_ok, tot, per


def main() -> int:
    if "--cache" in sys.argv:
        build_cache()
        return 0

    leaves = {lf.leaf: lf for lf in load_leaves()}
    gold = json.loads(GOLD.read_text())
    by_leaf: dict[int, list] = {}
    for e in gold["labels"]:
        if "xlf" in e:
            by_leaf.setdefault(e["leaf"], []).append(e)

    print("R14.1/R14.2 — THE ADAPTIVE VISUAL AGENT vs GOLD-HEADBAND")
    print(f"{WITNESS} leaves {LEAF_LO}-{LEAF_HI - 1}; page-fraction addressing (R2.2c); "
          f"MIN_BIND_FRAC={MIN_BIND_FRAC}; TWO declared addressing rules, both reported\n")

    arche: dict[str, int] = {}
    for i in sorted(by_leaf):
        lf = leaves.get(i)
        if lf is not None:
            arche[lf.archetype] = arche.get(lf.archetype, 0) + 1
    print("S2 — ARCHETYPES SEEN (decided before any region was named):")
    for a, n in sorted(arche.items(), key=lambda kv: -kv[1]):
        print(f"    {a:3s} {ARCHETYPES[a]['name']:38s} {n:2d} leaf/leaves")

    # 🔴 R16.5 — THE ONTOLOGY'S OWN GAP, PRINTED. Three numbers that were previously only knowable
    # by reading the source, and each of them is a limit on what any score below can mean.
    reach, unreach = _archetype_reachability()
    print("\nS2b — THE ONTOLOGY, AND WHAT IT CANNOT YET DO (R16.5):")
    print(f"    classes declared      : {len(CLASSES) - 1} + abstention")
    print(f"    classes a cue can emit: {len(_emittable_classes())}  "
          f"— NO CUE FOR: {' '.join(sorted(CLASSES - _emittable_classes() - {ABSTAIN})) or 'none'}")
    print(f"    archetypes declared   : {len(ARCHETYPES)}  ({' '.join(sorted(ARCHETYPES))})")
    print(f"    archetypes reachable  : {len(reach)}  ({' '.join(sorted(reach))})"
          f"  — UNREACHABLE: {' '.join(sorted(unreach)) or 'none'}")
    print("    ⚠️ A DECLARED CLASS WITH NO CUE CANNOT BE SCORED AND CANNOT BE WRONG. Naming the")
    print("    genre is the FIRST half of R16.5 — it gives the eye review's 893 findings somewhere")
    print("    correct to point, and it removes 'no correct answer exists' as a reason to put a")
    print("    leaf out of scope. The cues are the second half and are NOT done here.")

    scored = {}
    for rule in (BIND_OVERLAP, BIND_TIGHTEST):
        per: dict[str, list[int]] = {}
        conf_m: dict[tuple, int] = {}
        orphans, abstained, forbidden_hits = [], [], []
        for i in sorted(by_leaf):
            lf = leaves.get(i)
            if lf is None:
                continue
            for e in by_leaf[i]:
                b, _ = _bind(e, lf.boxes, rule)
                if b is None:
                    orphans.append(e)
                    continue
                gl = e["label"]
                per.setdefault(gl, [0, 0])
                per[gl][1] += 1
                if b.label == gl:
                    per[gl][0] += 1
                if b.label == ABSTAIN:
                    abstained.append((i, gl, b.cause))
                conf_m[(gl, b.label)] = conf_m.get((gl, b.label), 0) + 1
            forb = ARCHETYPES.get(lf.archetype, {}).get("forbids", set())
            for b in lf.boxes:
                if b.label in forb:
                    forbidden_hits.append((i, lf.archetype, b.label))
        scored[rule] = (per, conf_m, orphans, abstained, forbidden_hits)

        hit = sum(v[0] for v in per.values())
        tot = sum(v[1] for v in per.values())
        print(f"\n{rule}: bound-entry accuracy {hit}/{tot} = {hit / tot if tot else 0:.4f}   "
              f"ORPHANS {len(orphans)} (reported, never folded into accuracy)")
        for lab in (RH, MN, MT, CH, AR):
            if lab in per:
                c, n = per[lab]
                print(f"    {lab} recall {c}/{n} = {c / n:.4f}")
        print("    confusion (gold -> agent):")
        for (gl, al), n in sorted(conf_m.items(), key=lambda kv: -kv[1]):
            if gl != al:
                print(f"     🔴 {gl} -> {al:3s} {n}")

    # ⚠️ THE HEADLINE IS THE WORSE OF THE TWO RULES, NOT THE BETTER. Reporting both and then
    # judging on the flattering one would be the map-chosen-after-the-numbers defect with an extra
    # step. The bars below are applied to whichever rule scores lower.
    per, conf_m, orphans, abstained, forbidden_hits = min(
        scored.values(), key=lambda v: sum(x[0] for x in v[0].values()) / max(1, sum(x[1] for x in v[0].values())))
    hit = sum(v[0] for v in per.values())
    tot = sum(v[1] for v in per.values())
    acc = hit / tot if tot else 0.0
    mn = per.get(MN, [0, 0])
    mn_r = mn[0] / mn[1] if mn[1] else 0.0
    print(f"\n⚠️ THE BARS ARE APPLIED TO THE WORSE RULE: {hit}/{tot} = {acc:.4f}")

    ab_rate = len(abstained) / tot if tot else 0.0
    print(f"\nS4 — ABSTENTION, characterised (Gate 9.6 / §7.8 row 10d's rate is pre-registered FROM")
    print(f"     this run, never asserted in advance): {len(abstained)}/{tot} = {ab_rate:.4f}")
    for i, gl, cause in abstained[:6]:
        print(f"    leaf {i} gold {gl}: {cause}")
    print(f"\n  forbidden-class emissions (Gate 9.1 clause 2): {len(forbidden_hits)}")

    print("\n📌 THE COMPARISON THAT MATTERS — same gold, same window, same binding rule:")
    print(f"    {'':22s} {'overall':>9s} {'MN':>9s} {'RH':>9s} {'MT':>9s}")
    print(f"    {'Surya off the shelf':22s} {'100/121':>9s} {'0/19':>9s} {'20/20':>9s} {'80/80':>9s}")
    print(f"    {'geometric region_head':22s} {'—':>9s} {'17/19':>9s} {'20/20':>9s} {'67/80':>9s}")
    agent_cells = {lab: f"{per[lab][0]}/{per[lab][1]}" if lab in per else "—" for lab in (MN, RH, MT)}
    print(f"    {'THE AGENT':22s} {f'{hit}/{tot}':>9s} {agent_cells[MN]:>9s} "
          f"{agent_cells[RH]:>9s} {agent_cells[MT]:>9s}")

    print("\nRUNG-0 BARS, pre-registered in this file before the first run:")
    ok_mn = mn_r >= BAR_MN_RECALL
    ok_ov = acc >= BAR_OVERALL
    ok_fb = len(forbidden_hits) <= BAR_FORBIDDEN
    print(f"  MN recall     >= {BAR_MN_RECALL:.4f} : {mn_r:.4f} {'PASS' if ok_mn else '🔴 FAIL'}")
    print(f"  overall       >= {BAR_OVERALL:.4f} : {acc:.4f} {'PASS' if ok_ov else '🔴 FAIL'}"
          f"   (the bar IS Surya's own score — buying MN with MT is a FAILURE)")
    print(f"  forbidden emis <= {BAR_FORBIDDEN}      : {len(forbidden_hits)} "
          f"{'PASS' if ok_fb else '🔴 FAIL'}")

    print("\n⚠️ THIS DISCHARGES NO GATE. Rows 10a/10b are reserved for GOLD-LAYOUT (>=125 pages,")
    print("   per-archetype quota, recogniser frozen — Roadmap R16.1). 121 entries, 20 leaves, ONE")
    print("   witness, head band only, so every MN here is a HEAD-BAND note: that the agent names")
    print("   notes running down the OUTER MARGIN beside the measure is NOT shown by this run.")
    print("   ⚠️ And MainText remains CONTAINMENT — the body block is one large box, and Gate 10b's")
    print("   boundary error is what separates containment from boundary quality. Not measured here.")

    if ok_mn and ok_ov and ok_fb:
        print("\n✅ ALL RUNG-0 BARS PASS. The naming step is admissible; R14.2 proceeds.")
        return 0
    print("\n🔴 A BAR FAILED. The step stays OPEN and BLOCKS — it is never closed by lowering a bar.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
