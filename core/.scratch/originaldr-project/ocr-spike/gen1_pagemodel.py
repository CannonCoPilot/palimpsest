# -*- coding: utf-8 -*-
"""PER-SOURCE PAGE MODEL FOR GENESIS 1 — read off the actual page images, not inferred from coordinates.

WHY THIS EXISTS AND WHY IT IS DELIBERATELY OVERFITTED (Sir, 2026-07-29). Every generic attempt to separate the
Douay-Rheims's apparatus from its scripture failed, and the last one failed even with per-character geometry in
hand. Rendering the pages and looking at them explains why in one glance: **the four witnesses do not share a
layout, and two of them are mirror images of each other.**

    S9 / S1 / S3  — first edition (1609)          S6 — second edition (1635)
    ┌────┬─┬──────────────────┬─────────┐         ┌─┬──────────┬────────────────┬────┐
    │ x-refs │ v │   BODY      │ ANNOT.  │        │ │  ANNOT.  │      BODY      │refs│
    │  left  │ n │             │  right  │        │ │   left   │                │right│
    └────┴─┴──────────────────┴─────────┘         └─┴──────────┴────────────────┴────┘
     .05 .12  .15      .16-.80    .81-.99          .09      .215   .22-.82    .83-.88

On the first edition the main annotation column is on the RIGHT, a narrow cross-reference column sits on the
far LEFT, and the verse numbers have a column of their own. On the second edition the main annotation column is
on the LEFT, the right margin carries only sparse cross-references, and **the verse numbers are inline in the
body**. A single x threshold cannot serve both, which is exactly why the word-level threshold test scored
42-46% recall for 17-19% of scripture lost: it was asked to catch a left column and a right column at once.

THE OTHER THING THE IMAGES SETTLED. The first edition opens the book with a full title block — ornamental band,
"THE BOOKE OF / GENESIS, IN HEBREW / BERESITH.", "CHAP. I.", and an italic chapter argument — and an ornamental
DROP CAPITAL that the body indents around for five lines. None of that is scripture, and none of it is
distinguishable from scripture by vocabulary: the argument is a summary of the chapter and shares its words.
It is separable by POSITION IN THE PAGE, which is what this model encodes.

These bands are per-source constants measured off the rendered pages. That is the point — they are not meant to
generalize, they are meant to be right for these four witnesses in Genesis, and the next book gets its own.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

WB = HERE / ".gen1-wordboxes.json"

# (body_x0, body_x1) as fractions of page width, plus the y below which the page is title/argument matter on
# the leaf that OPENS the chapter. `chapter_open_y` is applied only to the opening leaf of each witness.
SOURCE_MODEL = {
    # first edition: annotation right, cross-refs far left, verse numbers in their own narrow column
    "archive-ot1-1609":       {"body": (0.140, 0.815), "edition": 1, "open_page": 21, "chapter_open_y": 0.38, "head_frac": 0.055},
    "pdf-S03a":               {"body": (0.140, 0.815), "edition": 1, "open_page": 25, "chapter_open_y": 0.38, "head_frac": 0.055},
    "archive-holiebible-ot1": {"body": (0.140, 0.815), "edition": 1, "open_page": 31, "chapter_open_y": 0.38, "head_frac": 0.055},
    # second edition: annotation LEFT, body shifted right, only sparse cross-refs on the right
    # `chapter_open_y` is 0 here and that is a MEASURED no-op, not an omission: S6's opening leaf carries a
    # title block and argument like the 1609 leaves do, but cutting them by y changes nothing (0.548 and 0.0
    # score identically, 59/62). They never win a span because the argument does not anchor to janvier. The
    # leaf still needs `open_page` set, for the drop-cap rules — see DROP_CAP and PAGE_OVERRIDE.
    # S6's LEFT BOUND IS SWEPT, NOT GUESSED (2026-07-29). Word-start histogram over 21 S6 leaves shows two
    # clusters: the LEFT ANNOTATION column starting at 0.16-0.17 and the BODY at 0.23-0.24. A bound of 0.215
    # admits the annotation tail, which is why S6 is the worst source in every chapter measured — all ten open
    # cells of genesis 12 were S6 carrying intruders (`and trie`, `borne of`, `dicated on`, `pron bencfits.`).
    # ODR_S6_LEFT overrides it for the sweep; the adopted value is whatever the sweep measured best without
    # regressing chapters 1 and 16.
    "jp2-S06":                {"body": (float(os.environ.get("ODR_S6_LEFT", "0.215")), 0.825),
                               "edition": 2, "head_frac": 0.075},
}

# THE CHAPTER-SPECIFIC PART, KEYED (ocr_dir, chapter). `SOURCE_MODEL` above holds what is true of a WITNESS
# throughout — its column bands, its edition, where its running head sits. What belongs to a CHAPTER is only
# which leaf opens it and what that leaf shows: an engraved initial, a title block, an argument. Separating the
# two is what lets a new chapter be brought up without touching anything Genesis 1 established.
#
#   open_page       the leaf that opens this chapter in this witness (None if it opens mid-leaf with no display)
#   chapter_open_y  fraction of page height above which the opening leaf is title/argument matter, not scripture
#   drop_cap        (glued token, restored display line) for an engraved initial the recognizer cannot see
CHAPTER_MODEL: dict[tuple[str, int], dict] = {
    ("archive-ot1-1609", 1):       {"open_page": 21, "chapter_open_y": 0.38,
                                    "drop_cap": ("NTHEbeginning", "IN THE beginning")},
    ("pdf-S03a", 1):               {"open_page": 25, "chapter_open_y": 0.38,
                                    "drop_cap": ("NTHEbeginning", "IN THE beginning")},
    ("archive-holiebible-ot1", 1): {"open_page": 31, "chapter_open_y": 0.38,
                                    "drop_cap": ("NTHEbeginning", "IN THE beginning")},
    ("jp2-S06", 1):                {"open_page": 18, "chapter_open_y": 0.0,
                                    "drop_cap": ("Nthe", "IN the")},
    # GENESIS 16. Read off the leaves the same way, and the same three facts recur with different values:
    # `jp2-S06` p76 carries `CHAP. XVI.` at y 413, an italic argument at y 517-622 (`giueth her handemaid Agar
    # as a wife to Abram...`), and an engraved S opening `ARAI therfore the wife of Abram` — i.e. SARAI.
    ("jp2-S06", 16):               {"open_page": 76, "chapter_open_y": 0.263,
                                    "drop_cap": ("ARAI", "SARAI")},
    # The 1609 witnesses open Genesis 16 partway down a leaf that also carries the end of Genesis 15:
    # `CHAP. XVI.` at y~0.29, the italic argument at y~0.35, then `SARAI therfore, the wife of Abram` at
    # y~0.43. `chapter_open_y` cuts the chapter-15 text and the argument together.
    #
    # On `archive-ot1-1609` alone the engraved S is recognized but MERGED with the argument's last word, so the
    # display line arrives as `ſmaelSARAI` (Iſmael + SARAI). S3 and S9 return a clean `SARAI` and need no
    # drop-cap entry — the same edition, but three different scans, so the glue is a scanning accident rather
    # than a property of the setting.
    ("archive-ot1-1609", 16):      {"open_page": 81, "chapter_open_y": 0.390,
                                    "drop_cap": ("ſmaelSARAI", "SARAI")},
    ("pdf-S03a", 16):              {"open_page": 85, "chapter_open_y": 0.400},
    ("archive-holiebible-ot1", 16): {"open_page": 91, "chapter_open_y": 0.400},
    # GENESIS 8, read off the leaves (2026-07-31). Chapter 8 had NO entry, so it ran with `open_page=None` and
    # every source leaked its argument and engraved initial into verse 1 — exactly the failure the derived-table
    # comment below describes. The three sources that open the chapter mid-leaf show the same three facts:
    #
    #   S1 `archive-ot1-1609` p56 (h 3090): argument y 379-521, body opens y 629 `part ND God remembred Noc`
    #   S3 `pdf-S03a`         p60 (h 3030): argument y 345-473, body opens y 596 `part Np God remembred Noe`
    #   S6 `jp2-S06`          p50 (h 2847): argument y 2026-2127, body opens y 2283 `ND God remembred Noe`
    #
    # `part` is the tail of the right-hand side-note (`The third part of this booke`) merged into the body row
    # by the row reader; the drop-cap rule deletes everything before the display line, which removes it.
    # The engraved A is invisible to the recognizer, so `AND` arrives as `ND` (S1, S6) or `Np` (S3).
    #
    # WHY THIS MATTERS MORE THAN IT LOOKS: with no entry, S3's verse 1 was taken from the CHAPTER STREAM
    # instead of the leaf, because the leaf candidate opened with `part Np` and lost the janvier-fit contest.
    # The chapter stream's copy is missing `remembred` altogether — so the selector preferred a reading with a
    # word MISSING over one with two junk tokens in front. Leaf 0.9133 vs chapter-stream 0.8733.
    ("archive-ot1-1609", 8):       {"open_page": 56, "chapter_open_y": 0.185,
                                    "drop_cap": ("ND", "AND")},
    ("pdf-S03a", 8):               {"open_page": 60, "chapter_open_y": 0.180,
                                    "drop_cap": ("Np", "AND")},
    ("jp2-S06", 8):                {"open_page": 50, "chapter_open_y": 0.775,
                                    "drop_cap": ("ND", "AND")},
    # GENESIS 39, located with `chapter_open_probe.py` and confirmed line by line (2026-07-31). Two of these
    # four are MIXED LEAVES — chapter 38's ANNOTATIONS at the top, chapter 39's opening below — and
    # `_is_annotation_leaf` excludes such a leaf WHOLE. That rule is right for a pure commentary leaf and
    # catastrophic here: genesis 39:1-8 was thrown away on S3 and S9 at once and scored as sixteen cells with
    # NO TEXT AT ALL, which is why this chapter was the worst in the book at 0.554.
    #
    # No change to that rule is needed. `chapter_open_y` filters WORDS before the rows are grouped, so cutting
    # the annotations away leaves a leaf that no longer declares itself an annotation leaf.
    #
    #   S3 p145  `CHAP. XXXVIII` annotations y 320 · `CHAP. XXXIX` y 920 · argument to y 1280 · v1 y 1400
    #   S9 p153  `CHAP. XXXVIII.` y 360 · `CHAP. XXXIX.` y 960 · argument to y 1240 · v1 y 1360
    #   S1 p141  heading y 1000 · v1 y 1640          S6 p130  heading y 480 · v1 y 1040
    #
    # Verse 1 on all four is `THERFORE Ioſeph was brought into Egypt`. The cut sits just above it: everything
    # over verse 1 — running head, annotations, chapter heading, italic argument — is matter, not scripture.
    ("archive-ot1-1609", 39):      {"open_page": 141, "chapter_open_y": 0.524},
    ("pdf-S03a", 39):              {"open_page": 145, "chapter_open_y": 0.455},
    ("jp2-S06", 39):               {"open_page": 130, "chapter_open_y": 0.358},
    ("archive-holiebible-ot1", 39): {"open_page": 153, "chapter_open_y": 0.441},
    # GENESIS 15, located with `chapter_open_probe.py` and read off the leaves (2026-07-31). Chapter 15 had NO
    # model on ANY witness — `chapter_model()` returned `{}` for all four — so the title block, the italic
    # argument and the engraved initial all leaked into verse 1 on every source at once.
    #
    #   S1 `archive-ot1-1609` p79 (h 3090): `CHAP. XV.` y 1480 · argument y 1600-1800 · v1 y 1920
    #   S6 `jp2-S06`          p74 (h 2847): `CHAP. XV.` y  600 · argument y  680- 920 · v1 y  960
    #   S9 `archive-holiebible-ot1` p89 (h 2988): `CHAP. XV.` y 1440 · argument y 1560-1760 · v1 y 1840
    #
    # S6's p74 IS A MIXED LEAF of the genesis-39 kind, and it is the reason this chapter sat at S6 0.38-0.59:
    # its top four rows are the TAIL OF CHAPTER 14'S ANNOTATIONS (`that Chriſts Prieſthood is greatter then the
    # Leuitical`, `ot tithes by Abraham heweth the antiquitie of this :radition`), which the localizer credits
    # to chapter 15 and whose prose then competes for chapter 15's verse spans. `_is_annotation_leaf` cannot
    # see it — the leaf carries no ANNOTATIONS heading, only a continuation — but no change to that rule is
    # needed here either: `chapter_open_y` filters WORDS before the rows are grouped, so the annotation tail is
    # gone before anything can match against it.
    #
    # The cut sits just above verse 1 on each witness. Everything over it — running head, the previous
    # chapter's annotation tail, the chapter heading, the italic argument, and the two short marginal notes S6
    # sets between the argument and the body (`kinds of beaſts` y 880, `& two of birds` y 920) — is matter,
    # not scripture.
    ("archive-ot1-1609", 15):      {"open_page": 79, "chapter_open_y": 0.610},
    ("jp2-S06", 15):               {"open_page": 74, "chapter_open_y": 0.330},
    ("archive-holiebible-ot1", 15): {"open_page": 89, "chapter_open_y": 0.605},
    # `pdf-S03a` is deliberately absent: the probe does NOT locate chapter 15's opening on any of its credited
    # leaves ['82','83','84','85']. An open_page guessed rather than read is the one thing this table may not
    # carry, so S3 stays unconfigured until its leaf is found. (Its own diagnosis is a separate item.)
    #
    # GENESIS 3 and GENESIS 6 (2026-07-31). Both were carried as "S6-interleave" chapters needing per-leaf
    # bounds; `gutter_probe.py` says otherwise — see the note under PAGE_OVERRIDE — and what they ACTUALLY
    # lacked, on every witness, was a chapter model at all. Located with `chapter_open_probe.py`; the cut sits
    # just above verse 1 in each case, and the argument it removes is the long one these chapters both carry
    # (`By the craft of the Diuel ſpeaking in a ſerpent, our firſt parents tranſgreſſed...`, eight display
    # lines on the 1609 witnesses).
    ("archive-ot1-1609", 3):       {"open_page": 29, "chapter_open_y": 0.810},
    ("pdf-S03a", 3):               {"open_page": 33, "chapter_open_y": 0.812},
    ("jp2-S06", 3):                {"open_page": 26, "chapter_open_y": 0.260},
    ("archive-holiebible-ot1", 3): {"open_page": 39, "chapter_open_y": 0.806},
    ("archive-ot1-1609", 6):       {"open_page": 40, "chapter_open_y": 0.770},
    ("jp2-S06", 6):                {"open_page": 36, "chapter_open_y": 0.275},
    ("archive-holiebible-ot1", 6): {"open_page": 50, "chapter_open_y": 0.778},
    # ("pdf-S03a", 6): {"open_page": 44, "chapter_open_y": 0.785}  — MEASURED AND REJECTED (2026-07-31).
    #
    # NEGATIVE RESULT, PINNED. Naming S3's opening leaf for chapter 6 costs exactly one cell: ch6 goes 69/88 ->
    # 68/88 and S3 0.8636 -> 0.8182, with S1, S6 and S9 unmoved. The cell it loses is VERSE 1 — the very verse
    # the entry exists to repair — and the mechanism is the GENESIS 8 finding running in reverse.
    #
    # With no `open_page`, S3's verse 1 is taken from the CHAPTER STREAM and clears the bar. Naming the leaf
    # makes the leaf authoritative, and this leaf's verse 1 is doubly damaged:
    #
    #     leaf   : `afterthat men began to be multiplied vpon Nearth, & had procreation of daughters:`  0.862
    #     ODR    : `AND after that men began to be multiplied vpon the earth, & had procreation of daughters:`
    #
    # the opening `AND` is missing (engraved A, and the recognizer's `N` is not where a drop-cap rule can take
    # it) AND that same `N` has been glued onto the following word — `vpon Nearth` for `vpon the earth`. A
    # `drop_cap` cannot fix the second fault, and fixing only the first still leaves the cell short.
    #
    # THE GENERAL POINT, worth more than the cell: `open_page` is not free. It does not merely ADD the leaf as
    # a candidate, it PREFERS it, so on a leaf whose verse 1 is worse than the chapter stream's the entry is a
    # regression. Genesis 8 recorded the case where the leaf was better and the stream had a word missing; this
    # is the same selector seen from the other side. Measure before adding one, per witness — the other three
    # witnesses of this same chapter take the entry harmlessly.
}

# The chapter the model is currently reading. Set by the entry points (`--chapter`); the opening-leaf and
# drop-cap rules key off it. Everything else in this module is chapter-agnostic.
CHAPTER = 1


# DERIVED ENTRIES (`chapter_model_derive.py`) sit UNDER the hand-set table above. `CHAPTER_MODEL` was hand-set
# for chapters 1 and 16 and for no others, so every other chapter ran with `open_page=None` and leaked its title
# block, italic argument and engraved initial into verse 1 — `ch38 S1 v1` arrived as
# `and Zara. HIſame time Iudas going downe from his brethren`. The derived table fixes that mechanically for all
# 48 remaining chapters; it is a JSON side file so any single entry can be audited or removed without a code
# change, and a hand-set entry ALWAYS wins.
_DERIVED_PATH = HERE / ".chapter-model-derived.json"
_DERIVED_CACHE: dict | None = None


def _derived() -> dict:
    global _DERIVED_CACHE
    # MEASURED AND REJECTED — DEFAULT OFF (2026-07-30). Deriving `CHAPTER_MODEL` for all 48 un-worked chapters
    # looked like the campaign's central lever: the table existed only for chapters 1 and 16, so every other
    # chapter leaked its title block, italic argument and engraved initial into verse 1 (`ch42 v3` returned the
    # chapter ARGUMENT in all four witnesses). The derivation is real and it does fix that. It is still net
    # NEGATIVE, measured per chapter across all 49:
    #
    #     derived ON  3,827 passing cells      HELPS 4 chapters (7, 21, 28, 29; +5 cells)
    #     derived OFF 3,834 passing cells      HURTS 7 chapters (2, 14, 27, 32, 33, 36, 49; -12 cells)
    #
    # The gain on verse 1 is smaller than the damage an imperfect opening-leaf cut does elsewhere on the leaf.
    # Kept wired-but-off with the table and the tool, as with every other pinned negative here, because the
    # DERIVATION is sound and a better opening-leaf rule should start from it rather than rebuild it. Per-chapter
    # cherry-picking was rejected too: the differences are 1-3 cells, which is noise to fit.
    if os.environ.get("ODR_DERIVED_CM", "0") == "0":
        return {}
    if _DERIVED_CACHE is None:
        try:
            _DERIVED_CACHE = json.loads(_DERIVED_PATH.read_text())
        except Exception:                                        # noqa: BLE001
            _DERIVED_CACHE = {}
    return _DERIVED_CACHE


_PROBE_PATH = HERE / ".chapter-open-probe.json"
_PROBE_CACHE: dict | None = None


def _probed() -> dict:
    """Openings located by `chapter_open_probe.py`: the leaf and the y JUST ABOVE VERSE 1.

    DISTINCT FROM THE PINNED DERIVER, and in the one way that matters. Both fill the same gap — `CHAPTER_MODEL`
    was hand-set for three chapters and every other chapter leaked its title block, italic argument and
    engraved initial into verse 1. The deriver is net NEGATIVE (re-verified 2026-07-31: -6 cells, helping 4
    chapters and hurting 8) because its cut was chosen some other way and took scripture with it further down
    the leaf. This table's cut has no judgement left in it: verse 1 is located by JANVIER'S OWN WORDING, and
    everything above verse 1 — running head, a previous chapter's annotations, the heading, the argument — is
    matter by definition. Where the probe cannot locate verse 1 it emits nothing rather than guessing.

    It also reaches a defect the deriver could not. `_is_annotation_leaf` excludes a whole leaf whose head
    declares ANNOTATIONS; on a MIXED leaf — chapter 38's annotations above, chapter 39's opening below — that
    threw away genesis 39:1-8 on two witnesses at once, sixteen cells with no text at all, and made 39 the
    worst chapter in the book. Because `chapter_open_y` filters WORDS before the rows are grouped, cutting the
    annotations away leaves a leaf that no longer declares itself an annotation leaf. 16 such leaves exist.

    ODR_PROBE_CM=0 ablates it."""
    global _PROBE_CACHE
    if os.environ.get("ODR_PROBE_CM", "1") == "0":
        return {}
    if _PROBE_CACHE is None:
        try:
            _PROBE_CACHE = json.loads(_PROBE_PATH.read_text())
        except Exception:                                        # noqa: BLE001
            _PROBE_CACHE = {}
    return _PROBE_CACHE


def chapter_model(ocr_dir: str, chapter: int | None = None) -> dict:
    ch = chapter if chapter is not None else CHAPTER
    hand = CHAPTER_MODEL.get((ocr_dir, ch))
    if hand is not None:
        return hand
    pr = _probed().get(f"{ocr_dir}|{ch}")
    if pr:
        return {"open_page": pr["open_page"], "chapter_open_y": pr["chapter_open_y"], "probed": True}
    d = _derived().get(f"{ocr_dir}|{ch}")
    if not d or d.get("suspect"):
        # A SUSPECT derivation is not applied. Cutting most of a leaf on a bad verse-1 match would delete
        # scripture to tidy a number, and a chapter that keeps its argument text merely fails visibly.
        return {}
    out = {"open_page": d["open_page"], "chapter_open_y": d["chapter_open_y"], "derived": True}
    if d.get("drop_cap_applied"):
        out["drop_cap"] = tuple(d["drop_cap_applied"])
    return out

# PER-LEAF OVERRIDES. A witness's band is one constant for its ORDINARY leaves, and the leaf that opens a
# chapter is not an ordinary leaf — it carries a title block, an argument and an engraved initial, and on the
# second edition it is set to a DIFFERENT MEASURE entirely. `jp2-S06` p18 makes the point: its scripture runs
# x 848-1670 with a right cross-reference column beginning at x 1692, while its ordinary leaves (p19) run the
# body out to x 1789. A single right bound cannot serve both — 0.825 admits the whole margin column on p18,
# and anything tight enough to exclude it truncates every line on p19.
#
# This is the same conclusion M33 reached about the two editions, applied one level further down: the unit that
# owns a layout is the LEAF, not the witness. S6's opening leaf was left unconfigured (`open_page: None`) and
# that alone accounted for ten of Genesis 1's open cells — the title block, the italic argument and the entire
# right column were all being read as scripture.
# S6 p18 IS A THREE-COLUMN LEAF: left cross-references at x 229-320 (`Ad. I,` `Pial. 32,` `Eccl. 10,` `Tob.`),
# the body, and a CONTINUOUS PROSE annotation down the right margin from x 1692 (`The firma-` / `ment is al
# the` / `ſpace from the` / `lhigheſt ſtar-` / `res: the loweſt`). The body's own left edge changes down the
# leaf — x 852 for the eleven lines set beside the argument, then x 385 once past it — but the RIGHT edge is
# what matters, and it is the one the witness constant gets wrong.
#
# Swept over the archaic references (62 cells, S6 alone). The right bound carries essentially all of it:
#
#     hi=0.740  54/62 (0.941)   hi=0.765  59/62 (0.949)   hi=0.790  51/62 (0.934)   hi=0.825  44/62 (0.909)
#
# and the left bound is nearly inert (0.140 and 0.165 tie exactly) because the left cross-references do not
# anchor to janvier and never win a span. 0.165 is used anyway: it is the gutter the leaf actually shows,
# between the reference column ending near x 330 and the body beginning at x 383, so it is right for the
# reason it is right rather than by coincidence. Note S6's ORDINARY leaves genuinely need the wider bound —
# p19's body runs out to x 1775 (0.807) — which is the whole justification for overriding per leaf.
PAGE_OVERRIDE: dict[tuple[str, int], dict] = {
    ("jp2-S06", 18): {"body": (0.165, 0.765)},
    # GENESIS 8 ON S6, and the SAME argument one leaf apart — which is why this is a per-leaf table and not a
    # per-witness one. Chapter 8 opens at the foot of p50 and runs down p51, and the two leaves want opposite
    # things:
    #
    #   p50 carries the right-hand side-note column. Its chapter-8 body rows end at x<=1638 and the note begins
    #       at x>=1677 (`The third`, `of ths beo`, `Of the new`, `tiplication`, `vord.` — the running note `The
    #       third part of this booke. Of the new increaſe & multiplication of the world`). Bound 1660/2200.
    #   p51 has NO right column at all: its body genuinely runs to x 1784, and `the`(x7), `of`(x3), `which`,
    #       `were`(x3), `ſeauen`(x2) all start beyond 1660. The p50 bound applied here would delete scripture
    #       from thirty-nine tokens of ordinary text.
    #
    # p51's own defect is at the TOP instead: the running head arrives as `GENES I Noe.` — the head SPLIT into
    # two tokens, so `_PROSE_HEADS` (which matches whole capitalised words) cannot see it, plus the marginal
    # `Noe.`. It sits at y 251 of 2847 = 0.088, just under S6's witness head band of 0.075. Widening the band
    # for this leaf alone drops the whole row and takes the marginal with it.
    # ...and p50's body has TWO left edges, the same shape p18 already documents. The rows set beside the
    # engraved ornamental `A` begin at x 610-628; the first full-measure line below it begins at x 353, and
    # S6's swept left bound of 0.215 (x 473) cuts it. That line carries `ſtayd.` — the last word of verse 2 —
    # and it was the only real word below the bound in the whole chapter-8 body (the one other token, a
    # zero-width `M` at x 433, is a fragment of the ornament and is removed as a lone capital anyway).
    # Everything above `chapter_open_y` is already excluded, so lowering the bound here cannot readmit the
    # previous chapter's annotation column.
    ("jp2-S06", 50): {"body": (0.15, 0.754)},
    ("jp2-S06", 51): {"head_frac": 0.10},
    # ---- TWO-AXIS BOUNDS FOR `jp2-S06`, from `s6_bounds_probe.py` (ch39 walk, 2026-08-02) ----------------
    # This edition ALTERNATES its margin by leaf parity, and the entries above were each produced by a hunt
    # for one defect that varied the axis it was hunting and left the other at its default: p74/p128/p150/
    # p156 carried four-decimal RIGHT bounds beside an untouched default left, p90/p92 a tuned LEFT beside
    # an untouched default right. Both halves were real; each entry was half-done. Measured across every
    # wordbox cache, 62 of 127 leaves differ from the model and EVERY ONE IS EVEN: even leaves set their
    # glosses in a RIGHT column at 0.745-0.765 and run their body left to 0.13-0.16; odd leaves set them on
    # the LEFT at 0.10-0.21 and run the body right to 0.825. The left bound comes from `left_strip_probe`'s
    # line-membership test (a histogram cannot tell a clipped body from a full-width note block -- see p89);
    # the right from the dip-then-spike in the leaf's own token histogram.
    ('jp2-S06', 22): {"body": (0.14, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 24): {"body": (0.13, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 26): {"body": (0.14, 0.745)},   # was (0.215, 0.825)
    ('jp2-S06', 28): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 30): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 32): {"body": (0.215, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 34): {"body": (0.215, 0.765)},   # was (0.215, 0.825)   # was (0.215, 0.825)
    ('jp2-S06', 36): {"body": (0.15, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 38): {"body": (0.15, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 42): {"body": (0.1, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 44): {"body": (0.17, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 52): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 54): {"body": (0.215, 0.745)},   # was (0.215, 0.825)
    ('jp2-S06', 58): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 60): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 66): {"body": (0.15, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 68): {"body": (0.17, 0.755)},   # was (0.215, 0.825)

    # SEVEN HOLES IN THE PARITY SWEEP (ch10 walk, 2026-08-03). Every other EVEN leaf from 22 to 158 carries a
    # right bound at 0.745-0.765 — the gloss column this edition puts on the recto side of an even leaf. These
    # seven were skipped and sat on the SOURCE default 0.825, which reaches into the column. Rule C in its
    # purest form: the axis was not measured and found correct, it was never varied. RIGHT ONLY here; the left
    # bound is a separate axis and is tested separately (bounds_probe declines p56's left at 61 cont / 21 note).
    ('jp2-S06', 20): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 40): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 46): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 48): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 56): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 62): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 64): {"body": (0.215, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 70): {"body": (0.15, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 72): {"body": (0.14, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 74): {"body": (0.15, 0.746)},   # was (0.215, 0.746)
    ('jp2-S06', 76): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 78): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 80): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 82): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 84): {"body": (0.12, 0.735)},   # was (0.215, 0.825)
    ('jp2-S06', 86): {"body": (0.14, 0.745)},   # was (0.215, 0.825)
    ('jp2-S06', 88): {"body": (0.12, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 90): {"body": (0.14, 0.745)},   # was (0.14, 0.825)
    ('jp2-S06', 92): {"body": (0.14, 0.755)},   # was (0.14, 0.825)
    ('jp2-S06', 94): {"body": (0.14, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 96): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 98): {"body": (0.14, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 100): {"body": (0.15, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 102): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 104): {"body": (0.15, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 106): {"body": (0.15, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 108): {"body": (0.16, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 110): {"body": (0.15, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 112): {"body": (0.15, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 114): {"body": (0.15, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 116): {"body": (0.14, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 118): {"body": (0.16, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 120): {"body": (0.14, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 122): {"body": (0.15, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 124): {"body": (0.14, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 126): {"body": (0.16, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 128): {"body": (0.16, 0.7544)},   # was (0.215, 0.7544)
    ('jp2-S06', 130): {"body": (0.15, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 132): {"body": (0.13, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 134): {"body": (0.15, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 136): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 138): {"body": (0.15, 0.765)},   # was (0.215, 0.825)
    ('jp2-S06', 140): {"body": (0.14, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 142): {"body": (0.15, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 144): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 146): {"body": (0.16, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 148): {"body": (0.15, 0.745)},   # was (0.215, 0.825)
    ('jp2-S06', 150): {"body": (0.13, 0.745)},   # was (0.215, 0.746)
    ('jp2-S06', 152): {"body": (0.13, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 154): {"body": (0.15, 0.755)},   # was (0.215, 0.825)
    ('jp2-S06', 156): {"body": (0.14, 0.7497)},   # was (0.215, 0.7497)
    ('jp2-S06', 158): {"body": (0.215, 0.765)},   # was (0.215, 0.825)
    # HAND-VERIFIED, WHERE THE PROBE DECLINES. p35 is an ODD leaf, so nothing corroborates its histogram,
    # and its spike of 12 is the same height as p79's -- where the eye finds body (`derogateth Baptiſme`),
    # not apparatus. Here the eye finds an unmistakable citation column, `Gen. S.Chriſ. Theod. Moral.
    # Exech. Heb. lib.`, running 0.82-0.87 with the body ending at 0.80. The probe stays conservative and
    # the exception is recorded with its reason, rather than a constant tuned until it admits its example.
    ("jp2-S06", 35): {"body": (0.215, 0.815)},
    # S3 p60 — the same lesson on the LEFT, and on a witness whose bound is right for its other leaves.
    # `pdf-S03a`'s body starts at 0.14 (x 308), and on its ANNOTATION leaves that is correct: p59 and p61 have
    # 27 of 41 and 31 of 42 rows genuinely starting at x 309-331. On the SCRIPTURE leaves the body starts at
    # x 410-427 and everything to the left of it is a marginal column. Every token this bound drops on p60 was
    # checked one by one, and all nine are intruders:
    #
    #   x347 `of`   x320 `not`  x337 `He`   x329 `go-`  x362 `v-`  x313 `mo-`  x347 `ſo`  x326 `and`  x336 `12.`
    #
    # Two of them were doing visible damage inside verse 13: `ſo` sits between the halves of a word broken at
    # the measure, so `mo-`/`neth` came out as `mo ſo neth` instead of rejoining to `moneth`, and `and` turned
    # `the roofe of the arke` into `of and arke`. The bound is 0.17 (x 374) — above the highest intruder (362)
    # and below the lowest real body row (402).
    # ...and its RIGHT bound was two pixels too tight. The band test admits a word whose CENTRE is inside the
    # measure, and on this leaf the body legitimately overhangs: `arke.` centres at 1795 against a bound of
    # 1793 and was dropped, taking the last word of genesis 8:10 with it. Measured over every word below the
    # argument, the two columns do not overlap at all —
    #     body     x0 1741-1807, centres up to 1845   (`him.`, `ſea-`, `arke.`, `di-`, `mo`, `an`)
    #     VERSE NUMBERS  x0 1888-1915, centres from 1901   (`2`, `3`, `14`, `15`)
    # — so any bound between them is right by the layout rather than by tuning. 0.851 (x 1872) sits in the
    # middle of a 56px gutter. This recovered `him.` to verse 12, `arke.` to verse 10, and the `ſea-` that
    # rejoins `uen` into `ſeauen`.
    # GENESIS 15 ON S6 p74 — a THIRD instance of "the unit that owns a layout is the LEAF", and the one that
    # finally separates an annotation column geometrically. Four earlier apparatus splits are pinned dead
    # (§13 Q50) because they sought ONE threshold across a ragged edge; this is a per-leaf bound on a leaf whose
    # two columns genuinely do not overlap, measured word by word below the chapter cut:
    #
    #     body   — every line's rightmost word ENDS at x1 <= 1647 (`hin:` 1647, `(c)as` 1643, `ſerue,` 1641)
    #     margin — every annotation line STARTS at x0 >= 1673 (`ſignifie` 1673, `Iſraelites` 1680, `(b` 1678)
    #
    # so there is a real gutter at x 1647-1673 and the witness bound (0.825 = x1815) sits INSIDE the margin
    # column. That is what put `ſignifie`, `Iſraelites`, `should be three`, `generations in` into verses 1-4 —
    # the continuous side-note glossing 15:13 (`Abraham & his ſeed were in a ſtrange land ... 400 yeares`).
    #
    # SWEPT, not guessed (ch15 cells, baseline 64/84):
    #     0.825 -> 64   0.780 -> 65   0.765 -> 66   0.755 -> 66   0.746 -> 66   0.740 -> 66   0.735 -> 65   0.730 -> 65
    #
    # The plateau is 0.740-0.765 and 0.746 is taken because it is the MIDPOINT OF THE MEASURED GUTTER
    # (1642/2200) — right for the reason it is right, not by tying on the scoreboard. Below 0.740 the bound
    # starts eating the body's own line ends; above 0.780 it re-admits the note.
    #
    # PER-LEAF AND NOT PER-WITNESS, for the p50/p51 reason exactly: p75 has NO right column (its body runs out
    # to x1803) and this bound applied there would delete scripture from every line.
    # THREE MORE ANNOTATION COLUMNS, found by sweeping `gutter_probe.py` over all 914 credited leaves and kept
    # only where the removed tokens are apparatus (2026-07-31). PAGE_OVERRIDE is keyed by LEAF, so each entry
    # serves every chapter that leaf carries — which is why two of the three pay off in a pair of chapters.
    #
    #   p128 (ch37, ch38)  removes 30 tokens: the note on Iudas and Thamar's genealogy (`Moyſes ... ſerteth of
    #                      this gencalogie`, `Mat.`, `mariage`).           ch38 100/120 -> 101/120
    #   p156 (ch49, ch50)  removes 20: `(4) Iacob ... hertofore mentioned`, `Aug. Gen.`       score-neutral
    #   p150 (ch47, ch48)  removes 19: `The Septuagint ... contrarie ... Hebre[w] Latin text`, `Adoration`
    #                                                                                        score-neutral
    #
    # The two neutral bounds are KEPT because they are correct about the page and remove only apparatus — but
    # they are recorded as NEUTRAL, not as wins (CHAPTER-WORKFLOW Phase 4: a correct rule that changes no score
    # is not a win). A fourth candidate, p138 (ch42), was REJECTED: it changes 0 tokens of 0, i.e. that leaf
    # contributes nothing to the body at all, so a bound there is an unevidenced entry and was removed.
    ("pdf-S03a", 60): {"body": (0.17, 0.851)},
    # ── THE SAME LEFT-BOUND DEFECT ON THE 1635 WITNESS (ch23, 2026-08-02) ────────────────────────────────
    #
    # `jp2-S06` carries its ANNOTATION COLUMN ON THE LEFT (0.09-0.215) where the 1609 witnesses put theirs on
    # the right, so its body bound is 0.215. On p90 and p92 that column IS NOT THERE and the bound eats
    # scripture: ch23 S6 scored **0.25**, 15 of its 20 open cells on p90 alone, every row starting mid-phrase
    # — `right ot a ſepulchre with vou` (no `Giue me the`), `children of Heth auſwered` (no `The`), `a Prince
    # of God amons vs` (no `thou art`).
    #
    # THE FOUR LEAVES OF ONE CHAPTER GIVE TWO OPPOSITE ANSWERS, which is the whole case for keying by LEAF:
    #
    #   p89  0 continuation / 88 note    p91  0 / 43     -> a REAL note column, left alone
    #   p90 58 continuation /  1 note    p92 77 /  2     -> body, clipped
    #
    # The token histogram says the same thing without the classifier. p89/p91 are dense from 0.11 to 0.21 and
    # plainly apparatus (`Chriſoſt.`, `Gen.`, `S. 48.`, `ho.`, `Amb.`, `li.`); p90/p92 hold **nothing at all
    # below 0.15** and their body starts at 0.155. 0.14 is taken because it is clear of the body start on both
    # leaves and there is no column on them for it to re-admit — not because it tied on the scoreboard.
    #
    # This was invisible until `left_strip_probe.py` was generalized off the hardcoded 1609 bound. A probe that
    # can only see one edition's layout reports "no defect" on the other and is believed.
    # ── GENESIS 41's MARGIN COLUMN, ON THE THREE 1609 WITNESSES (2026-08-01). CANDIDATE — see the delta note. ──
    #
    # ch41 was carried as "S1 is a recognizer problem" (S1 0.5439, the worst source on the worst chapter). It is
    # not. S1's open cells are DROPPED AND INTRUDED WORDS, not mis-read glyphs — `vpon banke of the riuer`,
    # `Behold there ſbal ſeuen yeares`, `Landof` twice — and the leaf dump shows why: the patristic margin is
    # merged into the body rows (`...he ſent to al | e ben ad`, `...and they | II. S Gieg. I.`).
    #
    # `gutter_probe.py` says OVERLAP on every one of these leaves, and it is right AT ROW GRANULARITY: a merged
    # row's centre lies in the margin, so no row-level bound is safe. But the word filter in `_page_words` has
    # always cut PER WORD, so the row verdict never settled the question. Measured per word instead:
    #
    #   body words end   x1 <= 1735       margin words begin x0 >= 1775        (S1 p145, 35 rows in band)
    #
    # an empty column strip, found by x-coverage profile rather than by the largest intra-line gap — the biggest
    # gap on those rows is MID-BODY (67px at x=1003) and smaller than the column break, so gap-ranking picks the
    # wrong seam. Column separation here is an absolute-x fact, not a relative-spacing one.
    #
    # REFUSAL CRITERION, and it is not a knob: a cut counts only where it separates something — rows lying WHOLLY
    # right of it (a column exists) AND rows CROSSING it (the merge to repair). That test rejects every jp2-S06
    # leaf of this chapter and p144/146/148/150/152/158/160 outright, where the minimum-coverage search merely
    # finds the page's right-hand whitespace (rows_cut=0, margin_only=0).
    #
    # The tokens the column holds are apparatus without exception — `S. Greg. li.`, `9. de Gen. ad lit.` (S1's
    # clipped `Aug1` + `e ben ad` are fragments of that same Augustine note), `the 70. & Philo`, `the Chaldey
    # paraphraſis`, `and Ioſephus`. Three INDEPENDENT witnesses of the same opening (S1 p143 / S3 p147 / S9 p155)
    # derived cuts separately from their own pixels — 1749 / 1753 / 1733 — and remove the SAME three fragments
    # (`: Death`, `the croſſe was`, `moſt cruel, &`). Independent derivation converging on identical content is
    # not a fit to noise.
    #
    # THE DELTA IS THE ONLY THING THAT COUNTS, and it is small. Against the base bound already in force (0.815 =
    # x1793, tested on the word CENTRE) these bounds newly remove just 18 tokens across the eight leaves; the
    # first audit credited work the base bound was already doing. Of those 18, six are plainly apparatus (`::`,
    # `ro.`, `lit.`, `9.`, `11.`, `c.`) and the rest are ORDINARY WORDS — `the`, `him`, `came`, `moſt`, `gift` —
    # which is exactly the population the PINNED NEGATIVE below (word boxes crossing the gutter) warns about.
    # Read back against the note text they are note-INITIAL words (`the croſſe was`, `moſt cruel, &`, `came ro
    # paſſe`, `gift to inter-`), and the re-measure confirms it: nothing was amputated.
    #
    # MEASURED (all 50 chapters, before/after): ch41 158/228 -> 159/228, and NO other chapter moves in either
    # direction — board 5224 -> 5225 of 6116 achievable. The single cell is S3's (0.6667 -> 0.6842). KEPT on the p156 /
    # p150 precedent: correct about the page, removes only apparatus, recorded as very nearly NEUTRAL and NOT as
    # a win.
    #
    # WHAT THIS RULES OUT, which is worth more than the cell. S1 DID NOT MOVE — 0.5439 before and after — so the
    # margin merge is NOT what holds ch41's worst source down. S1's residue is genuine recognizer damage on
    # these particular scans: `Seuon cares` (eares), `blaſled vith adulon` (blaſted with aduſtion), `tlare
    # ſprang alto orher eates` (there ſprang alſo other eares), `thu:ne` (thinne), `wimn` (wiſe men), `Egp`
    # (Ægypt). Those are mis-read glyphs, not misplaced words, and no bound of any kind reaches them. ch41/S1 is
    # therefore a RECOGNIZER problem after all — but for a reason now established by elimination rather than
    # assumed, and with the marginalia defect that was masking the diagnosis removed.
    # ── AND THE SAME LEAVES' LEFT EDGE, WHICH THE ELIMINATION ABOVE NEVER VARIED (2026-08-01). ──
    #
    # THE CONCLUSION ABOVE — "ch41/S1 is therefore a RECOGNIZER problem after all, established by elimination" —
    # IS WRONG, AND THE WAY IT WENT WRONG IS THE REUSABLE PART. It varied the RIGHT bound, saw S1 unmoved, and
    # attributed the whole residue to the recognizer. The LEFT bound was never varied: every 1609 entry in this
    # table carries a right bound tuned to four decimals beside the untouched default 0.140, which is the
    # fingerprint of `gutter_probe.py` — a tool that sweeps the GUTTER and has no opinion about the fore-edge.
    #
    # The very tokens quoted there as proof of misread glyphs are tokens this bound was DROPPING. On S1 p145 the
    # word boxes hold, at x0/W 0.118-0.136 and so outside the band, exactly:
    #
    #     [Seuon] + `cares of corne grew forth vpon one ſtalke ful and`      (v5, scored 0.000)
    #     [faire:] + `tlare ſprang alto orher eates a many`                  (v6, scored 0.000)
    #     [blaſled] + `vith adulon, deuou ng al the beaue of the`            (v7)
    #     [morning] + `was come, being fighted with feare`                   (v8)
    #
    # `Seuon` IS a misread of `Seuen`, and it is ALSO clipped. Both causes are live at one site, and v5 scores
    # 0.000 because its head is ABSENT, not because one glyph is wrong — a single bad glyph costs hundredths.
    # An elimination that varies one bound can only ever return the cause it did not test.
    #
    # THE SPLITTING TEST IS `left_strip_probe.py`, and it needs no classifier. Word boxes carry line membership:
    # a strip token whose LINE also has >=2 tokens inside the band is a body line with its head cut off; a strip
    # token whose line lies wholly in the strip is a marginal note. On this chapter it separates the two cleanly
    # on the SAME page set — p145/p143 and S03a p149/p147 are pure continuation (39/0, 23/1, 39/0, 31/0), while
    # p144, S03a p148 and holiebible p156 are notes (2/9, 3/7, 5/8) and are left alone.
    #
    # THE STRIP IS MIXED ACROSS THE BOOK, SO THE DEFAULT MUST NOT MOVE. Book-wide the band 0.109 <= x0/W < 0.140
    # holds ~8,200 tokens on 404 leaves: 194 leaves are continuation, 167 are genuine note columns
    # (`1.Idals. called idols.`) and 29 are mixed. Lowering `SOURCE_MODEL` would pull apparatus into scripture on
    # a third of them. Per-leaf, on the probe's verdict, or not at all.
    #
    # Only the five leaves the probe calls MOVE are changed here. The four it calls `mixed` (S03a p151/p150/p152,
    # holiebible p159/p160) are DELIBERATELY LEFT AT 0.140 pending an eye — kraken merges a note into a body
    # line's own line object often enough (the ch3/ch6 overlap) that a straddling line is not by itself proof.
    # ---- RIGHT BOUNDS FOR THE THREE 1609 WITNESSES, WIDENING ONLY (`bounds_probe.py --right-only`)
    # Their LEFT bound was measured book-wide by `left_strip_probe --emit` and adopted at +57 cells; their
    # RIGHT bound is the axis nobody ever varied for them, and ch41 was losing whole words off the ends of
    # body lines to it: `He ſaid [ther]fore`, `a dreame [per]teining`, `shal not be [con]ſumed`.
    #
    # WIDENING ONLY, AND THE RESTRICTION WAS LEARNED THE HARD WAY. Applied in both directions this emit
    # cost ch41 eleven cells: it reset p146 to 0.705 -- a proposal already refused by the eye (it cuts `the
    # dreame came vp after ... Which shal come`) and by measurement -- and reverted p144 to the clipping
    # default. An estimate does not overturn a measurement on this axis either. Every gain here came from
    # widening; the parity runs OPPOSITE to `jp2-S06`, the ODD leaves carrying the right column and already
    # tuned tight, correctly, since widening those costs -7 in ch41 alone.
    ('archive-ot1-1609', 28): {"body": (0.14, 0.905)},
    ('archive-ot1-1609', 32): {"body": (0.109, 0.895)},
    ('archive-ot1-1609', 36): {"body": (0.14, 0.905)},
    ('archive-ot1-1609', 37): {"body": (0.109, 0.825)},
    ('archive-ot1-1609', 38): {"body": (0.14, 0.855)},
    ('archive-ot1-1609', 40): {"body": (0.14, 0.895)},
    ('archive-ot1-1609', 42): {"body": (0.109, 0.895)},
    ('archive-ot1-1609', 46): {"body": (0.14, 0.865)},
    ('archive-ot1-1609', 48): {"body": (0.14, 0.905)},
    ('archive-ot1-1609', 58): {"body": (0.14, 0.845)},
    ('archive-ot1-1609', 60): {"body": (0.109, 0.905)},
    ('archive-ot1-1609', 62): {"body": (0.14, 0.885)},
    ('archive-ot1-1609', 66): {"body": (0.14, 0.895)},
    ('archive-ot1-1609', 72): {"body": (0.14, 0.905)},
    ('archive-ot1-1609', 74): {"body": (0.14, 0.845)},
    ('archive-ot1-1609', 80): {"body": (0.14, 0.895)},
    ('archive-ot1-1609', 82): {"body": (0.14, 0.895)},
    ('archive-ot1-1609', 84): {"body": (0.14, 0.855)},
    ('archive-ot1-1609', 88): {"body": (0.109, 0.855)},
    ('archive-ot1-1609', 90): {"body": (0.14, 0.855)},
    ('archive-ot1-1609', 94): {"body": (0.14, 0.855)},
    ('archive-ot1-1609', 96): {"body": (0.14, 0.895)},
    ('archive-ot1-1609', 98): {"body": (0.14, 0.855)},
    ('archive-ot1-1609', 106): {"body": (0.14, 0.875)},
    ('archive-ot1-1609', 110): {"body": (0.14, 0.875)},
    ('archive-ot1-1609', 112): {"body": (0.14, 0.905)},
    ('archive-ot1-1609', 116): {"body": (0.14, 0.865)},
    ('archive-ot1-1609', 118): {"body": (0.14, 0.845)},
    ('archive-ot1-1609', 122): {"body": (0.14, 0.865)},
    ('archive-ot1-1609', 124): {"body": (0.14, 0.875)},
    ('archive-ot1-1609', 126): {"body": (0.109, 0.905)},
    ('archive-ot1-1609', 128): {"body": (0.14, 0.875)},
    ('archive-ot1-1609', 130): {"body": (0.14, 0.865)},
    ('archive-ot1-1609', 134): {"body": (0.14, 0.875)},
    ('archive-ot1-1609', 138): {"body": (0.14, 0.905)},
    ('archive-ot1-1609', 140): {"body": (0.14, 0.865)},
    ('archive-ot1-1609', 142): {"body": (0.14, 0.875)},
    ('archive-ot1-1609', 151): {"body": (0.109, 0.845)},
    ('archive-ot1-1609', 154): {"body": (0.14, 0.855)},
    ('archive-ot1-1609', 156): {"body": (0.14, 0.835)},
    ('archive-ot1-1609', 166): {"body": (0.109, 0.905)},
    ('pdf-S03a', 32): {"body": (0.14, 0.915)},
    ('pdf-S03a', 34): {"body": (0.14, 0.855)},
    ('pdf-S03a', 36): {"body": (0.14, 0.895)},
    ('pdf-S03a', 38): {"body": (0.14, 0.855)},
    ('pdf-S03a', 40): {"body": (0.14, 0.905)},
    ('pdf-S03a', 41): {"body": (0.109, 0.825)},
    ('pdf-S03a', 42): {"body": (0.14, 0.855)},
    ('pdf-S03a', 44): {"body": (0.14, 0.905)},
    ('pdf-S03a', 46): {"body": (0.109, 0.905)},
    ('pdf-S03a', 52): {"body": (0.14, 0.905)},
    ('pdf-S03a', 62): {"body": (0.14, 0.845)},
    ('pdf-S03a', 64): {"body": (0.14, 0.915)},
    ('pdf-S03a', 66): {"body": (0.14, 0.885)},
    ('pdf-S03a', 68): {"body": (0.14, 0.855)},
    ('pdf-S03a', 70): {"body": (0.14, 0.905)},
    ('pdf-S03a', 76): {"body": (0.14, 0.845)},
    ('pdf-S03a', 78): {"body": (0.14, 0.855)},
    ('pdf-S03a', 80): {"body": (0.14, 0.915)},
    ('pdf-S03a', 84): {"body": (0.14, 0.855)},
    ('pdf-S03a', 86): {"body": (0.14, 0.865)},
    ('pdf-S03a', 88): {"body": (0.14, 0.865)},
    ('pdf-S03a', 94): {"body": (0.14, 0.855)},
    ('pdf-S03a', 98): {"body": (0.14, 0.855)},
    ('pdf-S03a', 102): {"body": (0.14, 0.875)},
    ('pdf-S03a', 104): {"body": (0.14, 0.885)},
    ('pdf-S03a', 108): {"body": (0.14, 0.835)},
    ('pdf-S03a', 110): {"body": (0.14, 0.875)},
    ('pdf-S03a', 114): {"body": (0.14, 0.875)},
    ('pdf-S03a', 116): {"body": (0.14, 0.905)},
    ('pdf-S03a', 120): {"body": (0.14, 0.875)},
    ('pdf-S03a', 122): {"body": (0.14, 0.855)},
    ('pdf-S03a', 124): {"body": (0.14, 0.865)},
    ('pdf-S03a', 126): {"body": (0.14, 0.875)},
    ('pdf-S03a', 130): {"body": (0.109, 0.905)},
    ('pdf-S03a', 132): {"body": (0.14, 0.875)},
    ('pdf-S03a', 134): {"body": (0.14, 0.865)},
    ('pdf-S03a', 138): {"body": (0.14, 0.865)},
    ('pdf-S03a', 142): {"body": (0.14, 0.905)},
    ('pdf-S03a', 144): {"body": (0.14, 0.875)},
    ('pdf-S03a', 146): {"body": (0.14, 0.865)},
    ('pdf-S03a', 158): {"body": (0.14, 0.845)},
    ('pdf-S03a', 160): {"body": (0.14, 0.855)},
    ('pdf-S03a', 166): {"body": (0.14, 0.835)},
    ('pdf-S03a', 170): {"body": (0.109, 0.905)},
    ('pdf-S03a', 174): {"body": (0.14, 0.905)},
    ('pdf-S03a', 176): {"body": (0.109, 0.865)},
    ('archive-holiebible-ot1', 36): {"body": (0.14, 0.895)},
    ('archive-holiebible-ot1', 38): {"body": (0.14, 0.915)},
    ('archive-holiebible-ot1', 42): {"body": (0.14, 0.885)},
    ('archive-holiebible-ot1', 43): {"body": (0.109, 0.835)},
    ('archive-holiebible-ot1', 46): {"body": (0.14, 0.885)},
    ('archive-holiebible-ot1', 48): {"body": (0.205, 0.845)},
    ('archive-holiebible-ot1', 50): {"body": (0.14, 0.875)},
    ('archive-holiebible-ot1', 52): {"body": (0.109, 0.885)},
    ('archive-holiebible-ot1', 58): {"body": (0.14, 0.875)},
    ('archive-holiebible-ot1', 70): {"body": (0.109, 0.885)},
    ('archive-holiebible-ot1', 72): {"body": (0.14, 0.875)},
    ('archive-holiebible-ot1', 76): {"body": (0.14, 0.865)},
    ('archive-holiebible-ot1', 90): {"body": (0.14, 0.835)},
    ('archive-holiebible-ot1', 91): {"body": (0.109, 0.835)},
    ('archive-holiebible-ot1', 92): {"body": (0.14, 0.875)},
    ('archive-holiebible-ot1', 94): {"body": (0.14, 0.835)},
    ('archive-holiebible-ot1', 100): {"body": (0.14, 0.855)},
    ('archive-holiebible-ot1', 102): {"body": (0.14, 0.835)},
    ('archive-holiebible-ot1', 104): {"body": (0.14, 0.895)},
    ('archive-holiebible-ot1', 118): {"body": (0.14, 0.835)},
    ('archive-holiebible-ot1', 120): {"body": (0.14, 0.825)},
    ('archive-holiebible-ot1', 122): {"body": (0.14, 0.875)},
    ('archive-holiebible-ot1', 128): {"body": (0.14, 0.855)},
    ('archive-holiebible-ot1', 130): {"body": (0.14, 0.845)},
    ('archive-holiebible-ot1', 132): {"body": (0.14, 0.845)},
    ('archive-holiebible-ot1', 146): {"body": (0.14, 0.845)},
    ('archive-holiebible-ot1', 150): {"body": (0.14, 0.885)},
    ('archive-holiebible-ot1', 152): {"body": (0.14, 0.845)},
    ('archive-holiebible-ot1', 154): {"body": (0.14, 0.845)},
    ('archive-holiebible-ot1', 164): {"body": (0.14, 0.855)},
    ('archive-holiebible-ot1', 166): {"body": (0.14, 0.835)},
    ('archive-holiebible-ot1', 178): {"body": (0.14, 0.875)},
    ('archive-holiebible-ot1', 182): {"body": (0.14, 0.885)},
    ('archive-holiebible-ot1', 184): {"body": (0.14, 0.835)},
    ("archive-ot1-1609", 143): {"body": (0.109, 0.7950)},
    ("archive-ot1-1609", 145): {"body": (0.109, 0.7995)},
    ("archive-ot1-1609", 147): {"body": (0.109, 0.8032)},
    ("archive-ot1-1609", 146): {"body": (0.14, 0.86)},
    ("pdf-S03a", 150): {"body": (0.14, 0.885)},
    ("archive-holiebible-ot1", 159): {"body": (0.14, 0.795)},
    ("archive-ot1-1609", 144): {"body": (0.14, 0.86)},
    ("archive-ot1-1609", 148): {"body": (0.14, 0.86)},
    ("pdf-S03a", 147): {"body": (0.109, 0.7968)},
    ("pdf-S03a", 149): {"body": (0.109, 0.8018)},
    ("pdf-S03a", 151): {"body": (0.140, 0.8041)},
    ("archive-holiebible-ot1", 155): {"body": (0.140, 0.7877)},
    ("archive-holiebible-ot1", 157): {"body": (0.140, 0.7941)},
    # ══ THE LEFT BOUND, APPLIED BOOK-WIDE BY PROBE VERDICT (2026-08-01) ══════════════════════════════
    # Generated by `left_strip_probe.py --emit`; regenerate, never hand-edit. The defect and the splitting
    # test are documented at the ch41 block above -- these are the same finding at book scale.
    #
    # WHY NOT LOWER `SOURCE_MODEL` INSTEAD, which would be one line. The strip 0.109 <= x0/W < 0.140 holds
    # ~8,200 tokens on 404 leaves and it is MIXED: 194 leaves are clipped body, 167 are genuine note columns
    # (`1.Idals. called idols.`), 29 are mixed. A default change would pull apparatus into scripture on a
    # third of them -- the contamination this table's nine pinned negatives exist to prevent.
    #
    # THE EMIT RULE IS DELIBERATELY CONSERVATIVE, and it is why 194 candidate leaves became 162 entries. A
    # leaf is carried by several chapters and each chapter's word-box cache holds its OWN recognition of it;
    # the emitter takes the worst-case note count and requires continuation >= 3x notes in EVERY cache. A
    # leaf any cache reads as a note column is left alone.
    #
    # NOT INCLUDED, and left at 0.140 on purpose: the 29 `mixed` leaves. kraken merges a marginal note into a
    # body line's own line object often enough (the ch3/ch6 overlap, which no x-threshold ever fixed) that a
    # straddling line is not by itself proof of a clipped head. Those need an eye, not a threshold.
    #
    # RESIDUAL, recorded rather than hidden: the strip's floor is 0.109, so body text starting left of that is
    # still clipped and this probe cannot see it. Nothing measures that today.
    ('archive-holiebible-ot1', 35): {"body": (0.109, 0.815)},   # +47 body, 1 note
    ('archive-holiebible-ot1', 37): {"body": (0.109, 0.815)},   # +7 body, 2 note
    ('archive-holiebible-ot1', 39): {"body": (0.109, 0.815)},   # +37 body, 0 note
    ('archive-holiebible-ot1', 41): {"body": (0.109, 0.815)},   # +20 body, 0 note
    ('archive-holiebible-ot1', 45): {"body": (0.109, 0.815)},   # +46 body, 1 note
    ('archive-holiebible-ot1', 47): {"body": (0.109, 0.815)},   # +33 body, 0 note
    ('archive-holiebible-ot1', 49): {"body": (0.109, 0.815)},   # +43 body, 0 note
    ('archive-holiebible-ot1', 51): {"body": (0.109, 0.815)},   # +4 body, 0 note
    ('archive-holiebible-ot1', 53): {"body": (0.109, 0.815)},   # +49 body, 0 note
    ('archive-holiebible-ot1', 55): {"body": (0.109, 0.815)},   # +49 body, 1 note
    ('archive-holiebible-ot1', 57): {"body": (0.109, 0.815)},   # +6 body, 1 note
    ('archive-holiebible-ot1', 65): {"body": (0.109, 0.815)},   # +19 body, 0 note
    ('archive-holiebible-ot1', 67): {"body": (0.109, 0.815)},   # +25 body, 0 note
    ('archive-holiebible-ot1', 69): {"body": (0.109, 0.815)},   # +11 body, 0 note
    ('archive-holiebible-ot1', 71): {"body": (0.109, 0.815)},   # +6 body, 0 note
    ('archive-holiebible-ot1', 73): {"body": (0.109, 0.815)},   # +28 body, 0 note
    ('archive-holiebible-ot1', 75): {"body": (0.109, 0.815)},   # +32 body, 0 note
    ('archive-holiebible-ot1', 81): {"body": (0.109, 0.815)},   # +5 body, 0 note
    ('archive-holiebible-ot1', 85): {"body": (0.109, 0.815)},   # +9 body, 0 note
    ('archive-holiebible-ot1', 89): {"body": (0.109, 0.815)},   # +28 body, 1 note
    ('archive-holiebible-ot1', 93): {"body": (0.109, 0.815)},   # +21 body, 0 note
    ('archive-holiebible-ot1', 95): {"body": (0.109, 0.815)},   # +42 body, 1 note
    ('archive-holiebible-ot1', 96): {"body": (0.109, 0.815)},   # +7 body, 0 note
    ('archive-holiebible-ot1', 99): {"body": (0.109, 0.815)},   # +11 body, 0 note
    ('archive-holiebible-ot1', 101): {"body": (0.109, 0.815)},   # +3 body, 0 note
    ('archive-holiebible-ot1', 113): {"body": (0.109, 0.815)},   # +3 body, 0 note
    ('archive-holiebible-ot1', 115): {"body": (0.109, 0.815)},   # +28 body, 0 note
    ('archive-holiebible-ot1', 121): {"body": (0.109, 0.815)},   # +40 body, 0 note
    ('archive-holiebible-ot1', 125): {"body": (0.109, 0.815)},   # +21 body, 0 note
    ('archive-holiebible-ot1', 127): {"body": (0.109, 0.815)},   # +3 body, 1 note
    ('archive-holiebible-ot1', 133): {"body": (0.109, 0.815)},   # +20 body, 0 note
    ('archive-holiebible-ot1', 136): {"body": (0.109, 0.815)},   # +7 body, 1 note
    ('archive-holiebible-ot1', 138): {"body": (0.109, 0.815)},   # +6 body, 1 note
    ('archive-holiebible-ot1', 143): {"body": (0.109, 0.815)},   # +3 body, 1 note
    ('archive-holiebible-ot1', 145): {"body": (0.109, 0.815)},   # +3 body, 0 note
    ('archive-holiebible-ot1', 147): {"body": (0.109, 0.815)},   # +32 body, 1 note
    ('archive-holiebible-ot1', 151): {"body": (0.109, 0.815)},   # +6 body, 0 note
    ('archive-holiebible-ot1', 153): {"body": (0.109, 0.815)},   # +8 body, 0 note
    ('archive-holiebible-ot1', 163): {"body": (0.109, 0.815)},   # +35 body, 2 note
    ('archive-holiebible-ot1', 171): {"body": (0.109, 0.815)},   # +8 body, 0 note
    ('archive-holiebible-ot1', 175): {"body": (0.109, 0.815)},   # +17 body, 0 note
    ('archive-holiebible-ot1', 179): {"body": (0.109, 0.815)},   # +26 body, 1 note
    ('archive-holiebible-ot1', 181): {"body": (0.109, 0.815)},   # +17 body, 0 note
    ('archive-holiebible-ot1', 183): {"body": (0.109, 0.815)},   # +7 body, 0 note
    ('archive-holiebible-ot1', 185): {"body": (0.109, 0.815)},   # +3 body, 0 note
    ('archive-ot1-1609', 25): {"body": (0.109, 0.815)},   # +15 body, 1 note
    ('archive-ot1-1609', 27): {"body": (0.109, 0.815)},   # +10 body, 1 note
    ('archive-ot1-1609', 29): {"body": (0.109, 0.815)},   # +17 body, 0 note
    ('archive-ot1-1609', 31): {"body": (0.109, 0.815)},   # +19 body, 0 note
    ('archive-ot1-1609', 33): {"body": (0.109, 0.815)},   # +5 body, 0 note
    ('archive-ot1-1609', 35): {"body": (0.109, 0.815)},   # +27 body, 1 note
    ('archive-ot1-1609', 39): {"body": (0.109, 0.815)},   # +18 body, 0 note
    ('archive-ot1-1609', 41): {"body": (0.109, 0.815)},   # +4 body, 0 note
    ('archive-ot1-1609', 43): {"body": (0.109, 0.815)},   # +28 body, 0 note
    ('archive-ot1-1609', 45): {"body": (0.109, 0.815)},   # +10 body, 1 note
    ('archive-ot1-1609', 47): {"body": (0.109, 0.815)},   # +9 body, 1 note
    ('archive-ot1-1609', 55): {"body": (0.109, 0.815)},   # +34 body, 0 note
    ('archive-ot1-1609', 57): {"body": (0.109, 0.815)},   # +7 body, 1 note
    ('archive-ot1-1609', 59): {"body": (0.109, 0.815)},   # +8 body, 0 note
    ('archive-ot1-1609', 61): {"body": (0.109, 0.815)},   # +3 body, 0 note
    ('archive-ot1-1609', 63): {"body": (0.109, 0.815)},   # +32 body, 0 note
    ('archive-ot1-1609', 65): {"body": (0.109, 0.815)},   # +27 body, 0 note
    ('archive-ot1-1609', 71): {"body": (0.109, 0.815)},   # +5 body, 1 note
    ('archive-ot1-1609', 75): {"body": (0.109, 0.815)},   # +6 body, 0 note
    ('archive-ot1-1609', 79): {"body": (0.109, 0.815)},   # +15 body, 1 note
    ('archive-ot1-1609', 81): {"body": (0.109, 0.815)},   # +6 body, 2 note
    ('archive-ot1-1609', 83): {"body": (0.109, 0.815)},   # +12 body, 0 note
    ('archive-ot1-1609', 85): {"body": (0.109, 0.815)},   # +13 body, 1 note
    ('archive-ot1-1609', 86): {"body": (0.109, 0.815)},   # +6 body, 1 note
    ('archive-ot1-1609', 95): {"body": (0.109, 0.815)},   # +4 body, 1 note
    ('archive-ot1-1609', 105): {"body": (0.109, 0.815)},   # +21 body, 2 note
    ('archive-ot1-1609', 107): {"body": (0.109, 0.815)},   # +3 body, 1 note
    ('archive-ot1-1609', 111): {"body": (0.109, 0.815)},   # +27 body, 0 note
    ('archive-ot1-1609', 113): {"body": (0.109, 0.815)},   # +18 body, 0 note
    ('archive-ot1-1609', 115): {"body": (0.109, 0.815)},   # +13 body, 2 note
    ('archive-ot1-1609', 117): {"body": (0.109, 0.815)},   # +11 body, 3 note
    ('archive-ot1-1609', 123): {"body": (0.109, 0.815)},   # +26 body, 0 note
    ('archive-ot1-1609', 127): {"body": (0.109, 0.815)},   # +7 body, 1 note
    ('archive-ot1-1609', 131): {"body": (0.109, 0.815)},   # +38 body, 0 note
    ('archive-ot1-1609', 132): {"body": (0.109, 0.815)},   # +6 body, 2 note
    ('archive-ot1-1609', 135): {"body": (0.109, 0.815)},   # +10 body, 0 note
    ('archive-ot1-1609', 137): {"body": (0.109, 0.815)},   # +36 body, 1 note
    ('archive-ot1-1609', 139): {"body": (0.109, 0.815)},   # +21 body, 0 note
    ('archive-ot1-1609', 141): {"body": (0.109, 0.815)},   # +7 body, 0 note
    ('archive-ot1-1609', 163): {"body": (0.109, 0.815)},   # +33 body, 0 note
    ('archive-ot1-1609', 167): {"body": (0.109, 0.815)},   # +28 body, 0 note
    ('archive-ot1-1609', 169): {"body": (0.109, 0.815)},   # +16 body, 0 note
    ('archive-ot1-1609', 171): {"body": (0.109, 0.815)},   # +5 body, 1 note
    ('archive-ot1-1609', 172): {"body": (0.109, 0.815)},   # +6 body, 2 note
    ('archive-ot1-1609', 173): {"body": (0.109, 0.815)},   # +3 body, 0 note
    ('pdf-S03a', 29): {"body": (0.109, 0.815)},   # +22 body, 0 note
    ('pdf-S03a', 33): {"body": (0.109, 0.815)},   # +17 body, 1 note
    ('pdf-S03a', 35): {"body": (0.109, 0.815)},   # +16 body, 0 note
    ('pdf-S03a', 37): {"body": (0.109, 0.815)},   # +6 body, 1 note
    ('pdf-S03a', 39): {"body": (0.109, 0.815)},   # +20 body, 0 note
    ('pdf-S03a', 43): {"body": (0.109, 0.815)},   # +19 body, 0 note
    ('pdf-S03a', 45): {"body": (0.109, 0.815)},   # +5 body, 0 note
    ('pdf-S03a', 47): {"body": (0.109, 0.815)},   # +28 body, 0 note
    ('pdf-S03a', 49): {"body": (0.109, 0.815)},   # +12 body, 0 note
    ('pdf-S03a', 51): {"body": (0.109, 0.815)},   # +8 body, 0 note
    ('pdf-S03a', 53): {"body": (0.109, 0.815)},   # +9 body, 0 note
    ('pdf-S03a', 55): {"body": (0.109, 0.815)},   # +16 body, 0 note
    ('pdf-S03a', 59): {"body": (0.109, 0.815)},   # +25 body, 0 note
    ('pdf-S03a', 61): {"body": (0.109, 0.815)},   # +7 body, 0 note
    ('pdf-S03a', 63): {"body": (0.109, 0.815)},   # +4 body, 0 note
    ('pdf-S03a', 65): {"body": (0.109, 0.815)},   # +5 body, 0 note
    ('pdf-S03a', 67): {"body": (0.109, 0.815)},   # +32 body, 0 note
    ('pdf-S03a', 69): {"body": (0.109, 0.815)},   # +15 body, 0 note
    ('pdf-S03a', 77): {"body": (0.109, 0.815)},   # +12 body, 0 note
    ('pdf-S03a', 79): {"body": (0.109, 0.815)},   # +6 body, 0 note
    ('pdf-S03a', 83): {"body": (0.109, 0.815)},   # +16 body, 0 note
    ('pdf-S03a', 85): {"body": (0.109, 0.815)},   # +6 body, 2 note
    ('pdf-S03a', 87): {"body": (0.109, 0.815)},   # +11 body, 1 note
    ('pdf-S03a', 89): {"body": (0.109, 0.815)},   # +18 body, 1 note
    ('pdf-S03a', 90): {"body": (0.109, 0.815)},   # +4 body, 0 note
    ('pdf-S03a', 95): {"body": (0.109, 0.815)},   # +3 body, 1 note
    ('pdf-S03a', 99): {"body": (0.109, 0.815)},   # +4 body, 0 note
    ('pdf-S03a', 103): {"body": (0.109, 0.815)},   # +13 body, 0 note
    ('pdf-S03a', 105): {"body": (0.109, 0.815)},   # +3 body, 0 note
    ('pdf-S03a', 109): {"body": (0.109, 0.815)},   # +23 body, 1 note
    ('pdf-S03a', 115): {"body": (0.109, 0.815)},   # +17 body, 0 note
    ('pdf-S03a', 117): {"body": (0.109, 0.815)},   # +29 body, 0 note
    ('pdf-S03a', 119): {"body": (0.109, 0.815)},   # +17 body, 2 note
    ('pdf-S03a', 121): {"body": (0.109, 0.815)},   # +7 body, 2 note
    ('pdf-S03a', 127): {"body": (0.109, 0.815)},   # +26 body, 0 note
    ('pdf-S03a', 131): {"body": (0.109, 0.815)},   # +10 body, 0 note
    ('pdf-S03a', 135): {"body": (0.109, 0.815)},   # +38 body, 0 note
    ('pdf-S03a', 139): {"body": (0.109, 0.815)},   # +15 body, 0 note
    ('pdf-S03a', 141): {"body": (0.109, 0.815)},   # +37 body, 0 note
    ('pdf-S03a', 143): {"body": (0.109, 0.815)},   # +30 body, 0 note
    ('pdf-S03a', 145): {"body": (0.109, 0.815)},   # +6 body, 0 note
    ('pdf-S03a', 154): {"body": (0.109, 0.815)},   # +3 body, 0 note
    ('pdf-S03a', 155): {"body": (0.109, 0.815)},   # +28 body, 1 note
    ('pdf-S03a', 163): {"body": (0.109, 0.815)},   # +3 body, 0 note
    ('pdf-S03a', 165): {"body": (0.109, 0.815)},   # +6 body, 2 note
    ('pdf-S03a', 167): {"body": (0.109, 0.815)},   # +32 body, 0 note
    ('pdf-S03a', 171): {"body": (0.109, 0.815)},   # +29 body, 0 note
    ('pdf-S03a', 173): {"body": (0.109, 0.815)},   # +18 body, 0 note
    ('pdf-S03a', 175): {"body": (0.109, 0.815)},   # +5 body, 0 note
    ('pdf-S03a', 177): {"body": (0.109, 0.815)},   # +3 body, 0 note

}


# ROW GROUPING — the two parameters that turned out to matter most in the whole page model.
#
# `ROW_TOL` is the step tolerance: how far a word's vertical centre may sit from the word LAST added to the
# open row, in median word heights. `ROW_MAX_DRIFT` bounds how far that running reference may wander from the
# row's FIRST word, which is what stops a sloping line's tolerance from chaining across two printed lines.
#
# Swept together over the archaic references (248 cells, all four witnesses), passing cells at >=0.90:
#
#     drift ->      0.8        1.2        1.8        3.0
#     tol 0.5   245/248    195/248    193/248    191/248
#     tol 0.6   243/248    173/248    169/248    171/248
#     tol 0.8   237/248     49/248     47/248     43/248
#     tol 1.0   237/248      8/248      4/248      0/248
#
# Read the columns, not the rows: the drift bound is the dominant term and it must be TIGHT. Loosen it and the
# running reference walks from one printed line onto the next, the merged row is sorted by x across both, and
# the text becomes word salad — 0/248 at the extreme. Held tight, the running reference tracks a skewed line
# perfectly. This single pair took S9 from 24/62 to 62/62.
ROW_TOL_DEFAULT = 0.5
ROW_TOL: dict[str, float] = {}
ROW_MAX_DRIFT = 0.8

# The engraved initial indents this many body lines on the chapter-opening leaf (measured: five on the 1609
# leaves). A leading token separated from the rest of its row by more than `DROP_CAP_ORPHAN_GAP` times that
# row's typical inter-word gap, within that block, is the engraving and not a word.
DROP_CAP_ROWS = 6
DROP_CAP_ORPHAN_GAP = 4.0
# The same gap evidence applied to EVERY row, for the left-column intruders that dominate the un-worked
# chapters' residual. Wired via `MARGIN_ORPHANS` so the effect is measured before it is trusted.
MARGIN_ORPHAN_GAP = 4.0
MARGIN_ORPHANS = os.environ.get("ODR_MARGIN_ORPHANS", "0") != "0"


def _row_interrupt_on() -> bool:
    return os.environ.get("ODR_ROW_INTERRUPT", "0") != "0"

# Per-leaf body left edge — see `_trim_left_margin`. The tolerance is a fraction of page width, wide enough
# to absorb a justified line's own variation and the indent of a paragraph opening.
LEFT_EDGE_MIN_ROWS = 6
LEFT_EDGE_TOL = 0.02

# How many leading rows to search for an ANNOTATIONS heading — see `_is_annotation_leaf`.
ANNOT_LEAF_ROWS = 3

# Running-head shape test — see `_is_running_head`.
HEAD_MAX_TOKENS = 2
HEAD_UPPER_FRAC = 0.6

# Catchword / signature mark at the foot of a leaf — see `_is_foot_line`. `FOOT_MIN_FRAC` is how far across
# the measure the row must begin before it counts as set apart from the text rather than continuing it.
FOOT_MAX_TOKENS = 2
FOOT_MIN_FRAC = 0.55
# A binder's SIGNATURE mark, which shares the foot row with the catchword and is set to the LEFT of it:
# `H2`, `C2`, `Aa3`, or the letter and its number recognised as two tokens (`H` + `2`). See `_is_foot_line`.
_SIGNATURE_RE = re.compile(r"^(?:[A-Z][a-z]?\d?|\d{1,2})$")
# A bare folio number in the head zone — too few letters for `_is_running_head` to judge. See `body_rows`.
_VNUM_ONLY = re.compile(r"^\d{1,4}[.,]?$")


_DESKEW_CACHE: dict[tuple[str, int, int], dict] = {}


def _DESKEW_MODE() -> str:
    """`off` | `untuned` (default) | `all`.

    MEASURED, AND THE DEFAULT IS THE RESULT. Straightening every leaf costs 5 cells book-wide and deriving
    bounds fresh on straightened leaves costs 25, even though the deskew demonstrably works (S9's line-start
    spread falls 0.0157 -> 0.0043, and all four witnesses converge on the same ~0.004 floor of hand-set
    type). Both facts are true because THE HAND-TUNED BOUNDS WERE FITTED IN THE SKEWED FRAME: rotating the
    page upright moves it out from under its own tuning. So the two changes are each right and mutually
    destructive, and the gate follows from that — straighten the leaves that carry no measured override, and
    leave every hand-fitted leaf in the frame it was fitted in. A leaf earns its way out of the deskew by
    having been measured, not by being straight.
    """
    # DEFAULT `off`, AND THAT IS A MEASURED RESULT, NOT A PREFERENCE. Book-wide, against a 5733 baseline:
    #     off 5733  ·  untuned 5724 (-9)  ·  all 5728 (-5)  ·  all + bounds re-derived on deskewed 5708 (-25)
    # The deskew itself is sound — S9's line-start spread falls 0.0157 -> 0.0043 and all four witnesses
    # converge on the same ~0.004 floor of hand-set type. It loses cells anyway because EVERY calibrated
    # constant in this stack was fitted in the skewed frame: not only the 364 per-leaf overrides but the
    # SOURCE defaults (chosen "generous enough for every leaf" across skewed leaves), R3's 6% crop margin,
    # and the head/foot tests. Rotating the page upright moves it out from under all of them at once, which
    # is why even gating to untuned leaves still loses. Deskew cannot be retrofitted incrementally; it is
    # adoptable only together with a re-derivation of the whole geometry, and a re-derivation must beat 364
    # hand-measurements — which the heuristic probe does not (-25). That is the argument for replacing the
    # fractional-bound model with a trained region segmenter rather than adding constants to it.
    return os.environ.get("ODR_DESKEW", "off")


def _deskewed(ocr_dir: str, page_index: int, page: dict) -> dict:
    """This leaf's boxes, rotated upright. Cached — the estimator sweeps 100 angles over every word."""
    key = (ocr_dir, page_index, len(page.get("lines") or ()))
    hit = _DESKEW_CACHE.get(key)
    if hit is None:
        import deskew as _dk
        hit = _DESKEW_CACHE[key] = _dk.deskew(page)
    return hit


def body_rows(ocr_dir: str, page_index: int, page: dict) -> list[list[dict]]:
    """The words of one page that lie inside this SOURCE's body column, in reading order.

    Reading order is rebuilt from the boxes rather than taken from kraken's line order, because the recognizer
    interleaves the columns: on `archive-holiebible-ot1` p31 the annotation lines at y=4713 and y=4862 are
    emitted BETWEEN the body lines at y=4694 and y=4877. Sorting the surviving body words by (y-band, x) puts
    the scripture back in the order it is printed."""
    # DESKEW FIRST, BECAUSE A FRACTIONAL BOUND ONLY MEANS ANYTHING ON A LEAF WHOSE COLUMNS ARE VERTICAL.
    # `archive-holiebible-ot1` p48 leans -0.03: its body's left edge migrates 0.212 -> 0.226 down the leaf
    # while the note column's right edge falls 0.210 -> 0.192, so at the head of that page the channel between
    # apparatus and scripture is four pixels wide and no single fraction can sit in it. The transform is on
    # COORDINATES only — x' = x + theta*(y - y_centre), y untouched — so every row-grouping and line-splitting
    # decision downstream is bit-identical and any change in the board is attributable to the bounds alone.
    # See `deskew.py` for the estimator and why the median line slope is not it.
    _dm = _DESKEW_MODE()
    if _dm != "off" and not (_dm == "untuned" and "body" in PAGE_OVERRIDE.get((ocr_dir, page_index), {})):
        page = _deskewed(ocr_dir, page_index, page)
    cm = chapter_model(ocr_dir)
    m = {**SOURCE_MODEL[ocr_dir], **cm, **PAGE_OVERRIDE.get((ocr_dir, page_index), {})}
    W, H = page["page_px"]
    lo, hi = m["body"][0] * W, m["body"][1] * W
    is_open = page_index == m.get("open_page")
    y_min = m.get("chapter_open_y", 0.0) * H if is_open else 0.0
    # THE RUNNING HEAD IS NOT CUT BY y ANY MORE (§13 Q34, 2026-07-29). `head_frac` used to delete every word
    # above it, and on `pdf-S03a` p86 that deleted A BODY ROW: the head `62 GENESIS.` sits at y=30 and the first
    # body line — `to thy miſtreſſe, and humble thy ſelfe vnder her hand.` — at y=97, while the cut fell at
    # 0.055·H = 167. That row is the continuation of genesis 16:9 from the previous leaf, so the verse lost its
    # own text; it was the LAST cell open in Genesis 16, and with the catchword defect (`_is_foot_line`) it made
    # ONE junction fail in two independent ways. This is the same lesson the module already records twice: the
    # head cannot be cut by `head_frac` at ANY value, because the leaves are scanned at different offsets (S9's
    # p33 head ends BELOW p32's first body line). `head_frac` now only bounds WHERE a head may be looked for;
    # what removes it is `_is_running_head`'s SHAPE test, applied per row below.
    head_y = max(y_min, m["head_frac"] * H)
    ws = []
    for l in page["lines"]:
        for w in l["words"]:
            # THE TWO EDGES ARE NOT THE SAME KIND OF EDGE, so they are not tested the same way. The LEFT bound
            # is a real gutter between the body and a margin column, and nothing in the body crosses it — so a
            # word must begin inside it. The RIGHT bound is the measure, which body words legitimately overhang
            # by a few glyphs (`tree@1752-1821` against a bound of 1793 on `archive-ot1-1609` p22), so there
            # the word's centre is what counts. Testing both edges by centre let the margin word `birdes`
            # (x 257-364, centre 310, bound 308) into gen 1:12 in every 1609 witness.
            if w["x0"] < lo or (w["x0"] + w["x1"]) / 2 > hi:
                continue                       # a margin column — cross-references or annotation
            if _MARGIN_MARK_RE.search(w["t"]) and w["x0"] < 0.14 * W and ocr_dir == "archive-ot1-1609":
                continue                       # the copy's own marginal mark — see _MARGIN_MARK_RE
            if w["y1"] <= y_min:
                continue    # title block / ornament / chapter argument on the OPENING leaf — genuinely a y fact
            ws.append(w)
    if not ws:
        return []
    # group into visual lines by y-overlap, then order within a line by x
    ws.sort(key=lambda w: (w["y0"] + w["y1"]) / 2)
    med_h = sorted(w["y1"] - w["y0"] for w in ws)[len(ws) // 2] or 1
    tol = ROW_TOL.get(ocr_dir, ROW_TOL_DEFAULT) * med_h
    # THE ROW REFERENCE HAS TO FOLLOW THE LINE'S SLOPE. These leaves are photographed off bound volumes and
    # the lines are not level: on `archive-holiebible-ot1` p32 a single printed line runs from y=1157 at
    # x=336 to y=1122 at x=999 — a 35px rise across the measure, against a tolerance of ~30px. Compared
    # against the row's FIRST word, the far end of every line falls out of tolerance, starts a spurious row,
    # and then collects the neighbouring line's words; sorted by x, the two printed lines interleave. That is
    # the whole of why S9 gen 1:21-29 read as scrambled word salad (0.646-0.826) while S1 and S3, from flatter
    # scans of the same edition, read the same verses at 0.92-0.98.
    #
    # So membership is tested against the word LAST added to the row — a running reference that tracks the
    # slope, since the step between adjacent words is small however far the line rises overall. `max_drift`
    # keeps that from chaining indefinitely across genuinely different lines.
    rows: list[list[dict]] = [[ws[0]]]
    for w in ws[1:]:
        c = (w["y0"] + w["y1"]) / 2
        last = (rows[-1][-1]["y0"] + rows[-1][-1]["y1"]) / 2
        first = (rows[-1][0]["y0"] + rows[-1][0]["y1"]) / 2
        if abs(c - last) <= tol and abs(c - first) <= ROW_MAX_DRIFT * med_h:
            rows[-1].append(w)
        else:
            rows.append([w])
    rows = [sorted(r, key=lambda w: w["x0"]) for r in rows]
    if rows and _is_annotation_leaf(rows):
        return []
    # ONE ROW, ONE PRINTED LINE. The grouping above is on vertical overlap, and on a leaf scanned askew two
    # consecutive printed lines overlap in y while their BASELINES stay ~35px apart — so they merge, and the
    # x-sort then interleaves them word by word into something that reads exactly like two columns. Applied
    # AFTER `_is_annotation_leaf` on purpose: that test reads the leading rows, and it must go on seeing the
    # same rows it was calibrated against. See `line_split.py` for the measurement that showed this is skew
    # and not columns — a recursive XY-cut of the same leaf finds no gutter, because there is none.
    if os.environ.get("ODR_LINE_SPLIT", "1") != "0":
        import line_split
        rows = line_split.split_rows(rows)
    # ORPHAN REMOVAL IS A DROP-CAP REMEDY, so it fires only where a drop cap is ATTESTED (2026-07-29). Setting
    # `open_page` from a DERIVED chapter model used to switch it on wholesale, and on a leaf whose opening rows
    # are not indented around an engraving it deletes real words: `genesis 2` S9 v8 lost `God` from
    # `And our Lord God` and fell to 0.000, S3 v9 to 0.871. A hand-set entry keeps the old behaviour (chapters 1
    # and 16 were verified by eye, including the witnesses whose entry carries no `drop_cap`); a derived entry
    # must earn it by having a confirmed `drop_cap`.
    orphan_ok = is_open and (not cm.get("derived") or cm.get("drop_cap"))
    if orphan_ok:
        rows = _drop_cap_orphans(rows, W)
    elif is_open:
        # a derived opening leaf with no attested drop cap: still strip furniture as on an ordinary leaf
        while rows and _is_running_head(rows[0]):
            rows = rows[1:]
    else:
        # Drop leading rows that lie in the head zone AND look like furniture. Two shapes qualify, and nothing
        # else does: a running head (`62 GENESIS.`, `GENESIS. Creation.`) and a BARE FOLIO NUMBER, which
        # `_is_running_head` cannot judge because it has fewer than three letters. A leading row in the head
        # zone that is neither is KEPT — that is the whole point of the change, and it is what returns
        # `pdf-S03a` p86's first body line. A head BELOW the zone is still caught by the shape test alone,
        # which is why the second clause has no y condition.
        while rows and _is_running_head(rows[0]):
            rows = rows[1:]
        while rows and max(w["y1"] for w in rows[0]) <= head_y and \
                all(is_apparatus_mark(w["t"]) or _VNUM_ONLY.match(w["t"]) for w in rows[0]):
            rows = rows[1:]
        while rows and _is_running_head(rows[0]):
            rows = rows[1:]
    if len(rows) > 2 and _is_foot_line(rows[-1], W, lo, hi):
        rows = rows[:-1]
    if MARGIN_ORPHANS:
        rows = _strip_margin_orphans(rows, W)
    return rows


def _is_foot_line(row: list[dict], W: float, lo: float, hi: float) -> bool:
    """Is the last row a CATCHWORD or a SIGNATURE mark rather than the end of the text?

    Early-modern printing sets, at the foot of each leaf, the first word of the NEXT leaf — the catchword, a
    binder's aid — and often a signature mark (`C2`) beside it. Both are set apart from the text block and
    pushed to the right of the measure.

    They matter because of the chapter stream: read leaf by leaf a catchword is one stray token, but
    concatenate the leaves and it lands immediately before the word it duplicates, so gen 1:12 arrives as
    `grene grene herbe` in all three 1609 witnesses (`grene` at x 1639 alone on the last row of
    `archive-ot1-1609` p21, then `grene` again as the first word of p22). The verse cannot reach the bar while
    carrying a duplicate its printed page does not have.

    Identified by position, not by content: last row of the leaf, one or two tokens, beginning beyond the
    middle of the measure. A real final line of text is either long or begins at the left margin.

    THE SIGNATURE SITS ON THE SAME ROW AND AT THE LEFT (§13 Q34, fixed 2026-07-29). The two tests above are
    both defeated by the row `H3 to thy` (`pdf-S03a` p85): the signature makes it THREE tokens, and `row[0]` is
    the signature at the left of the measure, not the catchword. So the foot row was kept, and concatenating the
    leaves put the catchword immediately before the words it duplicates —

        p85 ends `... ſaid to her : Rerurne` / `H3 to thy`   p86 opens `to thy miſtreſſe, and humble ...`

    which is how genesis 16:9 arrived as `Returne to thy TO THY mistresse` and why it was the LAST verse of
    Genesis 16 still open. It was never an R3 fault; the page model produced the duplicate. The same row shape
    occurs on `archive-holiebible-ot1` (`H to thy`, `H 2 † Abram` — the signature letter and its number
    recognised as separate tokens) and on `pdf-S03a` p83 (`H2 † Abram`, whose leading signature ALSO pulled
    `row[0]["x0"]` to 0.499 of the page, just under the 0.511 threshold — so it failed both tests at once).

    Remedy: strip a leading run of SIGNATURE-shaped tokens (a capital, optionally with a following digit, or a
    bare one-or-two-digit number) before applying either test, and test the position of the first REMAINING
    token. Measured on the Genesis 16 leaves this converts exactly the four catchword rows above and leaves
    every other short final row as body — including `archive-ot1-1609`'s `com` / `m` / `amomn com`, which sit
    at 0.17-0.28 of the measure and are garbled text, not catchwords. Never strip the whole row: a row that is
    ALL signature-shaped tokens keeps its last token, so the position test still has something to judge."""
    k = 0
    while k < len(row) - 1 and _SIGNATURE_RE.match(row[k]["t"]):
        k += 1
    rest = row[k:]
    if len(rest) > FOOT_MAX_TOKENS:
        return False
    return rest[0]["x0"] > lo + FOOT_MIN_FRAC * (hi - lo)


# THE archive-ot1-1609 COPY'S OWN MARGINAL MARK, and it is a PHYSICAL fact about that one scan, not a class of
# text. Something is written or stamped down the fore-edge margin of this witness and the recognizer renders it
# as a stable family of nonsense: `fatimamovement` x9, `atmamom` x6, `fatimamovemant` x4, and 14 further
# variants — 63 occurrences, ALL of them on `archive-ot1-1609`. No other witness shows a single one, which is
# what makes it a property of the copy rather than of the printing.
#
# 45 of the 63 lie in the left strip and are what this filter removes. THE OTHER 18 ALREADY SIT INSIDE THE BODY
# BAND and are LEFT ALONE ON PURPOSE: they are a pre-existing contamination that predates the left bound and
# owes nothing to it, so removing them is a separate change that must carry its own before/after measurement.
# Folding it in here would let this fix take credit for work it did not do — the error the ch41 right-margin
# audit above made and had to correct.
#
# The stem was checked against every token in every 1609 cache: it matches 63 tokens and all 63 are the mark.
# No scripture word in Genesis contains any of these stems.
#
# IT SURFACED AS THE ONE REGRESSION OF THE LEFT-BOUND FIX, and that is the only reason it is filtered here. On
# ch50 S1 v11 admitting `amammcm` pushed the verse tail out: `...was called, The mourning of Egypt.` became
# `...was called, The amammcm The mourning of` — 0.954 -> 0.898, the single cell lost against +56 gained.
#
# WHY A PATTERN AND NOT A LEAF EXCLUSION. The mark sits on leaves that are otherwise the fix's best earners
# (p143 recovers `wrath`, `rers,`, `of`, `was`), so refusing those leaves would cost far more than the mark
# does. It is matched on its stem rather than by listing all 17 spellings because the spellings are recognizer
# noise on ONE underlying mark and the list is not closed — a new chapter's cache will render an 18th.
#
# SCOPE IS DELIBERATELY NARROW ON ALL THREE AXES: this witness, inside the left strip, stem match. A body word
# would have to be on `archive-ot1-1609`, begin left of 0.14W, and contain one of these stems to be lost.
_MARGIN_MARK_RE = re.compile(r"(mamo|amamm|imamo|movem|mamoc|mamom)")


def _trim_left_margin(rows: list[list[dict]], W: float) -> list[list[dict]]:
    """MEASURED AND REJECTED — NOT WIRED IN. Kept as the pinned record of a negative result.

    THE IDEA. The per-source `body` band is one constant for a whole witness, generous enough for every leaf,
    so on any particular leaf it sits left of where the body actually starts — and margin words wide enough to
    reach across the gutter survive it. `in` (x0 335) got into gen 1:12 in all three 1609 witnesses against a
    band beginning at 308, on a leaf whose real body lines begin at 400. Since the body is justified, the leaf
    should be able to state its own left edge: the median row start, less a tolerance.

    WHY IT FAILS. The left edge of these scans is not that tight. At `LEFT_EDGE_TOL` = 0.02 the rule removes
    the 7 genuine intruders on `archive-ot1-1609` p22 and ALSO strips the first real word off some forty rows
    across the four witnesses — `And it was ſo done` -> `ſo done`, `And S. Paul willed` -> `S. Paul willed`,
    `made a firmament` -> `a firmament`. Measured against the archaic references that is a clear loss:

        odr_com mean 0.928 -> 0.907 · s_dismas 0.747 -> 0.725 · verses at 4/4 support 15 -> 11

    Widening the tolerance keeps the intruders; narrowing it eats more scripture. This is the same shape as
    every geometric apparatus filter this project has tried: **one threshold cannot serve a ragged edge.** The
    intruders are annotation words that kraken interleaved into the body's reading order, so they are a
    segmentation problem (§13 Q18), not a margin problem, and a margin rule will not reach them.
    """
    starts = sorted(r[0]["x0"] for r in rows if r)
    if len(starts) < LEFT_EDGE_MIN_ROWS:
        return rows
    left = starts[len(starts) // 2] - LEFT_EDGE_TOL * W
    out = []
    for r in rows:
        while len(r) > 1 and r[0]["x0"] < left:
            r = r[1:]
        out.append(r)
    return out


def _is_annotation_leaf(rows: list[list[dict]]) -> bool:
    """Is this whole leaf the chapter's ANNOTATIONS rather than its scripture?

    The second edition prints each chapter's commentary on its own leaf, headed `GENESIS ... ANNOTATIONS.` —
    `jp2-S06` p77 for Genesis 16 is entirely notes on the Manichees, Luther and Chrysostom, with not one verse
    of scripture on it. The localizer credits such a leaf to the chapter (its words do belong to that chapter),
    so it lands in the word-box set and its prose then competes for verse spans. Whole-leaf exclusion is the
    right grain: nothing on the leaf is wanted.

    Detected by the printed heading, which is what the page itself declares — not by guessing from content.
    The match is on `NNOTATION`, not `ANNOTATION`, because the heading is set in display capitals that the
    recognizer runs together and mangles: p77's came back as `o GENESI AbtamNNOTATIONS.`, losing the leading A
    into the previous word. The distinctive core survives; the first letter does not."""
    head = " ".join(w["t"] for r in rows[:ANNOT_LEAF_ROWS] for w in r).upper().replace(" ", "")
    return "NNOTATION" in head


def _is_running_head(row: list[dict]) -> bool:
    """Is this the page's running head (`GENESIS.` / `Creation.` / the folio) rather than scripture?

    The head cannot be cut by y. `head_frac` was raised to try, and it cannot work: on
    `archive-holiebible-ot1` the running head of p33 ends at y=165 while the first real BODY line of p32
    begins at y=118 — the head of one leaf sits lower than the text of the next, because the leaves are
    scanned at different offsets. The head is identifiable by its SHAPE instead: it is the topmost row, it is
    one or two tokens, and it is set in capitals. That holds for `GENESIs.`, the misrecognized `GEMESIs.`, and
    `GENESIS.` alike, and no scripture row on any of these leaves is one short all-capital token."""
    if len(row) > HEAD_MAX_TOKENS:
        return False
    letters = [c for w in row for c in w["t"] if c.isalpha()]
    if len(letters) < 3:
        return False
    if sum(c.isupper() for c in letters) / len(letters) >= HEAD_UPPER_FRAC:
        return True
    # The second edition sets a TWO-PART head — the book on the verso, the subject on the recto,
    # `GENESIS. Creation.` — which is only 53% capitals and slips through a pure ratio test, carrying
    # `genesis` and `creation` into gen 1:11 on S6.
    #
    # The extra signature has to be narrow. "Initial capital" alone is far too loose: a body row opening
    # `And God` is two initial-capital tokens and was duly deleted when that was tried. What distinguishes a
    # head is that it is PUNCTUATED AS A LABEL — every token capitalised AND full-stopped, which a line of
    # running prose at the top of a leaf is not.
    if len(row) == 2 and all(w["t"][:1].isupper() and w["t"].endswith(".") for w in row):
        return True
    # ...AND THE SAME TWO-PART HEAD WITH THE STOP IN THE WRONG PLACE (ch23, 2026-08-02). On `jp2-S06` p90 the
    # head recognises as `Abraham. G.ENESI` — the subject full-stopped, the book with its period slid inward.
    # 13 letters, 7 capitals = 53%, under the ratio test; and `G.ENESI` does not END in a stop, so the label
    # test above misses it too. It slipped into gen 23:4 mid-verse: `...pilgrime among you giue Abraham.
    # G.ENESI me the right ot a ſepulchre...`.
    #
    # It was NOT reachable before the left bound on that leaf moved to 0.14 — with the body starting at 0.215
    # the fragment was outside the band and the row was a single token. **A fix that widens what the page model
    # sees can BREAK a filter that was passing only because it never saw the token.** Check the head after
    # every bound change.
    #
    # The extra signature stays narrow for the reason the comment above gives: one token punctuated as a label,
    # the OTHER an unbroken run of >=4 capital letters once punctuation is stripped. A body row opening
    # `And God` fails it — `God` is three letters and not all-caps — which is the case that killed the loose
    # "initial capital" version.
    if len(row) == 2:
        lab = [w for w in row if w["t"][:1].isupper() and w["t"].endswith(".")]
        caps = [w for w in row if (lambda x: len(x) >= 4 and x.isupper())("".join(c for c in w["t"] if c.isalpha()))]
        if len(lab) >= 1 and len(caps) >= 1 and lab[0] is not caps[0]:
            return True
    return False


def _drop_cap_orphans(rows: list[list[dict]], W: float) -> list[list[dict]]:
    """Discard the recognizer's attempts to read the ORNAMENTAL DROP CAPITAL as type.

    The chapter-opening leaf indents its first five body lines around an engraved initial. kraken has no way to
    know the block is an engraving, so it emits a token for it — on `archive-holiebible-ot1` p31 the initial
    comes back as `2` at x=348 while that row's actual first word starts at x=908. The token is not identified
    by WHAT it says (it says different things in different witnesses) but by WHERE it is: alone in the indent,
    separated from its row by a gap many times any gap between words.

    Left in, it corrupts the line-break rejoin — `hea-` + `2` glued to `hea2`, stranding `uen` — so this runs
    before any joining."""
    for i, r in enumerate(rows[:DROP_CAP_ROWS]):
        while len(r) >= 2:
            gaps = [b["x0"] - a["x1"] for a, b in zip(r, r[1:])]
            lead = gaps[0]
            rest = sorted(g for g in gaps[1:] if g > 0)
            typical = rest[len(rest) // 2] if rest else 0.0
            if lead > max(DROP_CAP_ORPHAN_GAP * typical, 0.08 * W):
                r = r[1:]
                continue
            break
        rows[i] = r
    return [r for r in rows if r]


def _strip_margin_orphans(rows: list[list[dict]], W: float, gap_mult: float = MARGIN_ORPHAN_GAP
                          ) -> list[list[dict]]:
    """Drop a LEADING token that is separated from its row by a gap many times the row's typical word gap.

    THE DEFECT THIS ADDRESSES is the dominant residual across the un-worked chapters. On
    `archive-holiebible-ot1` p36 (genesis 2) the left cross-reference column sits just inside the witness's body
    band, so its words join body rows:

        `I and al the furniture of them.`      `kind 4 de ſeuenth day, from al woorke`
        `li, lit. bleſſed the ſeuenth day`     `by cod heauen, and the earth.`
        `ſub- fore it ſhot vp in the earth`    `extant became a liuing ſoule.`

    WHY THIS IS NOT THE REJECTED `_trim_left_margin`. That rule derived ONE per-leaf left edge from the median row
    start and stripped anything left of it, which cost 40 real first words across the four witnesses (odr_com
    0.928 -> 0.907) — a single threshold against a ragged edge, the failure this project has now met five times.
    This test is RELATIVE TO THE ROW'S OWN TYPOGRAPHY: a body row's first word sits one word-space from its
    second, while a margin intruder is separated by a chasm. It is the SAME evidence `_drop_cap_orphans` already
    uses and trusts for the engraved initial — applied to every row rather than only the first six of an opening
    leaf, which is the only reason it was not already doing this work.

    A capped loop, not a while-True: at most two leading tokens can go, because a third would mean the row is
    something other than body text and deleting scripture to tidy a number is the one thing forbidden here."""
    out = []
    for r in rows:
        for _ in range(2):
            if len(r) < 3:
                break
            gaps = [b["x0"] - a["x1"] for a, b in zip(r, r[1:])]
            rest = sorted(g for g in gaps[1:] if g > 0)
            if not rest:
                break
            typical = rest[len(rest) // 2]
            if typical <= 0:
                break
            if gaps[0] > max(gap_mult * typical, 0.045 * W):
                r = r[1:]
                continue
            break
        out.append(r)
    return [r for r in out if r]


def body_words(ocr_dir: str, page_index: int, page: dict) -> list[dict]:
    """`body_rows` flattened into a single reading-order word sequence."""
    return [w for r in body_rows(ocr_dir, page_index, page) for w in r]


# THE OPENING DISPLAY LINE. Genesis 1 begins with an engraved drop capital followed by the rest of the first
# two words set in display capitals; the capitals are kerned tight enough that kraken returns the whole run as
# ONE token, `NTHEbeginning`, and the engraving not at all. Neither half is recoverable by recognizer tuning:
# the initial is not type, and the run has no spaces to find. What the line SAYS is a fixed property of the
# printed leaf — the same in every copy of the edition and legible in the rendered image — so it is recorded
# here as the page datum it is, keyed by the glued token so it cannot fire on a page that does not show it.
# (The old module-level DROP_CAP table is superseded by CHAPTER_MODEL[...]['drop_cap'] above — a
# drop cap belongs to the chapter's opening LEAF, not to the witness as a whole.)


def _join_hyphens(toks: list[str]) -> list[str]:
    """Rejoin a word the compositor broke across a line: `hea-` + `uen` -> `heauen`.

    The DR hyphenates freely at the measure, and every broken word costs the identity score twice — once for
    the fragment that is not a word and once for the one that follows it. The recognizer returns the hyphen
    (as `-` or `¬`), so this is a join of things already marked as joined, not an inference."""
    out: list[str] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if i + 1 < len(toks) and len(t) > 1 and t[-1] in "-¬":
            out.append(t[:-1] + toks[i + 1])
            i += 2
            continue
        out.append(t)
        i += 1
    return out


_re = __import__("re")
_VNUM = _re.compile(r"^\d{1,3}[.,]?$")
# The SECOND edition sets its verse numbers INLINE, and kraken glues them to the word that follows: `16.And`,
# `2.And`. A bare-token test cannot see those, so they are stripped by prefix — digits, an optional stop, then
# a capital. Requiring the capital is what keeps it off real words (no DR word begins with digits, but the
# capital also rules out a mangled numeral+fragment).
_VNUM_GLUED = _re.compile(r"^\d{1,3}[.,]?(?=[A-Z])")
# APPARATUS MARKS THAT ARE NOT SCRIPTURE, and that none of the four references carries:
#   `(b)` `(d)` `(e)` — the second edition's inline footnote reference letters, keyed to its annotation column
#   `S.` `I.`         — abbreviated marginal cross-references (`S. Aug`, `I.`) interleaved into a body row
#   a bare `c`        — a footnote letter left standing where its word was
# The one-letter test excludes `a`, `A`, `O`, `o` and `I`, which are real words; every other single letter,
# and every single letter followed by a stop, is apparatus in this text.
_PAREN_LETTER = _re.compile(r"^\(\s*[A-Za-z]\s*\)[.,;:]?$")
_ABBREV_LETTER = _re.compile(r"^[A-Za-z]\.$")
_LONE_LETTER = _re.compile(r"^[A-Za-z]$")
_REAL_ONE_LETTER = {"a", "A", "O", "o", "I"}
# A token made only of reference marks. MEASURED before adoption (2026-07-31, all 50 chapters, 406,116 tokens
# surviving the existing filter): 7,414 hits, of which 7,406 are `†` — and reading them in context shows what
# it is. The dagger falls at VERSE BOUNDARIES and nowhere else (`and earth. † And the earth was`,
# `darkenes. † And he called`), in three sources at once: it is the printed verse marker that the recognizer
# could not resolve into a digit. None of the four references carries it.
# SCORE EFFECT: NONE — `char_identity` already strips punctuation, so all 7,406 are score-neutral. This is
# adopted for the TEXT, not the number: Phase 7's exit criterion 3 is "no apparatus tokens in any verse text",
# and 7,406 of them were sitting in the deliverable.
_MARK_ONLY = _re.compile(r"^[†‡*¶§·•]+$")
# A roman numeral used as a marginal cross-reference (`ii:` in `In ii: the ſecond moneth`, from an R3 crop).
# LOWERCASE and at least two characters, deliberately: the corpus probe found `I,` twelve times and it is the
# PRONOUN — `I, euen I wil bring` — so a pattern admitting a single character or an uppercase one would delete
# real scripture. `il,` (8x, a misreading of `it,`) is excluded by requiring the trailing mark to be `.` or `:`.
# The uppercase class (`XXI.`, `XLV.`, ~400 tokens, chapter headings and citation numerals) is NOT included
# here — it is a larger population and belongs in its own attributed step, not smuggled in with this one.
_ROMAN_REF = _re.compile(r"^[ivxl]{2,6}[.:]$")

# ── PINNED NEGATIVE (2026-07-31): SPLITTING A WORD BOX THAT CROSSES THE GUTTER. NOT WIRED. ──────────────
# Genesis 8:13 on `pdf-S03a` p60 loses the word `Therfore` in a way no bound can fix: the recognizer merged the
# marginal note's last word with the body's first into ONE box, `theTherfore` spanning x 274-660 across a
# gutter at 374. Dropping the margin therefore drops a word of scripture, and the obvious remedy — split a
# box that begins outside the body and ends inside it, keep the body part — looked narrow and geometric.
#
# MEASURED FIRST, and it is neither. Across all 50 chapters and 931 leaves, **12,859 boxes cross the left
# gutter**, and the commonest are ordinary words: `the` 350, `and` 200, `of` 173, `that` 99, `was` 80. A rule
# firing on twelve thousand boxes and splitting them on a proportional character estimate is `split_glued`
# again — the rule this project already pinned for trading 1,356 real corruptions (`lawful` -> `law ful`) for
# a net +8 cells. The gutter crossing is not the rare signal it appears to be from one example.
#
# `Therfore` is therefore left LOST in the page-model text and recovered, correctly, by the rung that exists
# for exactly this (R3 re-read the crop and returned it). One example is not a population, and the measurement
# is what said so — before the rule was written rather than after it was adopted.
# ────────────────────────────────────────────────────────────────────────────────────────────────────────


def _near_a_word(low: str, lex: set[str], max_edits: int = 1) -> bool:
    """Is this token within `max_edits` of a single lexicon word — i.e. a GARBLE rather than a glue?

    Only same-length substitutions and single insert/delete are tested, and only against words of comparable
    length, which keeps it cheap over a 3,421-word lexicon."""
    n = len(low)
    for w in lex:
        if abs(len(w) - n) > max_edits or not (n - 2 <= len(w) <= n + 2):
            continue
        if len(w) == n:
            if sum(1 for a, b in zip(w, low) if a != b) <= max_edits:
                return True
        else:
            short, long = (w, low) if len(w) < len(low) else (low, w)
            i = j = 0
            skips = 0
            while i < len(short) and j < len(long):
                if short[i] == long[j]:
                    i += 1
                    j += 1
                else:
                    skips += 1
                    j += 1
                    if skips > max_edits:
                        break
            if skips <= max_edits and i >= len(short) - max_edits:
                return True
    return False


def split_glued(toks: list[str], lex: set[str] | None) -> list[str]:
    """Split a token the recognizer ran together, on the SAME lexicon evidence the hyphen JOIN already uses.

    THE MIRROR OF `rejoin_break`. That rule joins `hea` + `uen` when neither fragment is a word of the book and
    their concatenation is; this one splits `oflife` into `of life` when the GLUED FORM is not a word of the book
    and both fragments are. Measured across the campaign's open cells: **67 cells carry such a token** —
    `oflife` for `of life` (genesis 2 S1 v7), `pleasantto` for `pleasant to` (2 S1/S9 v9), `to thee` (31),
    `weeping and` (50), `be mindful` (50).

    THE GUARD IS THE GLUED FORM'S OWN ABSENCE, and it is doing real work: `indeed` splits into `in` + `deed`,
    both of which are words, so a rule without that guard would break a legitimate token in half. It only fires
    where the book itself never uses the joined form — the same asymmetry that lets the join rule refuse to glue
    `was` to `voide`.

    MEASURED AND REJECTED — DEFAULT OFF, AND THE NUMBERS ARE WHY IT MUST STAY OFF.

    On the campaign scoreboard it looked like the one systemic win of the session:

        50 chapters: HELPS 8, HURTS 1, net +8 cells. Chapters 1 and 16 unmoved.

    Then I counted what it actually CHANGES rather than what it scores: **1,356 tokens split across Genesis**, and
    the commonest are REAL WORDS torn into morphemes that happen to be lexicon entries —

        lawful -> law ful (28x)      earthlie -> earth lie (18x)    prayeth -> pray eth (17x)
        faithful -> faith ful (14x)  delight -> de light (13x)      offereth -> offer eth (15x)

    The guard on the glued form's own absence cannot save it: `lawful` is not in the lexicon (the book sets
    `lawfull`), while `law` and `ful` both are. Nor can edit distance separate the classes — at max_edits=2
    `hofore` (garbled `before`) is correctly refused but `oflife` and `pleasantto` are refused too, so the rule
    stops doing the only thing it was for.

    **THE LESSON IS ABOUT THE METRIC, NOT THE RULE.** A +8 net on the scoreboard concealed 1,356 alterations to the
    transcription, nearly all invisible because they were score-neutral or fell in cells that already failed. A
    rule is not measured by the verdicts it flips; it is measured by the TEXT it changes. I nearly adopted this on
    the strength of "HELPS 8 HURTS 1".

    Kept wired-but-off with its figures, like every other pinned negative here."""
    if not lex:
        return toks
    out: list[str] = []
    for t in toks:
        core = t.strip(_STRIP)
        low = core.lower()
        if len(low) < 6 or low in lex or not low.isalpha():
            out.append(t)
            continue
        # DISPLAY CAPITALS ARE SET AS A UNIT, never glued words: `SHALBEBLESSED` on `pdf-S03a` p100 is a display
        # line, and splitting it invents word boundaries the printer did not set.
        if not any(c.islower() for c in core):
            out.append(t)
            continue
        # A GARBLE IS ONE EDIT FROM A REAL WORD; A GLUE IS FAR FROM EVERY WORD. This is what separates `oflife`
        # (no single word resembles it) from `thinas`/`hegotten`/`vpeuen` — garbled `things`, `begotten`, `vp
        # euen` that happen to split into two lexicon words and cost genesis 23 a cell. Without this test the
        # rule tidies away recognizer errors, which a diplomatic transcription must preserve for a later rung.
        if _near_a_word(low, lex):
            out.append(t)
            continue
        cut = None
        for i in range(2, len(low) - 1):
            a, b = low[:i], low[i:]
            if a in lex and b in lex:
                cut = i
                break
        if cut is None:
            out.append(t)
            continue
        # preserve the token's own case and any trailing punctuation the strip removed
        head, tail = core[:cut], core[cut:]
        suffix = t[t.index(core) + len(core):] if core in t else ""
        prefix = t[:t.index(core)] if core in t else ""
        out += [prefix + head, tail + suffix]
    return out


def is_apparatus_mark(t: str) -> bool:
    """A token that is an apparatus marker rather than a word of the text.

    These survived every geometric filter because they are set INSIDE the measure — the second edition prints
    its footnote letters inline in the body, and kraken merges a marginal `S.` into the body row beside it. They
    cost score in every reference at once (none of the four carries them) and they are trivially identifiable by
    shape, which is why they are removed here rather than chased through the geometry."""
    if _PAREN_LETTER.fullmatch(t):
        return True
    if _ABBREV_LETTER.fullmatch(t):
        return True
    if _MARK_ONLY.fullmatch(t):
        return True
    if _ROMAN_REF.fullmatch(t):
        return True
    return bool(_LONE_LETTER.fullmatch(t)) and t not in _REAL_ONE_LETTER


# Running heads and section headings as they appear in PROSE (an R3 crop transcript, where there are no rows to
# test the shape of). A multi-leaf crop join walks straight over a leaf's top, so `GENESIS.` lands mid-verse.
_PROSE_HEADS = {"genesis", "creation", "annotations", "annotation",
                # THE HEAD IS NOT ALWAYS ONE TOKEN. `jp2-S06` p51 returns it as `GENES I` — split in two, so a
                # whole-word test cannot see either half, and `GENES I Noe.` walked into genesis 8:3. Counted
                # over all 50 chapters: `GENES` 35, `GENESI` 34, `ENESIS` 1, and not one of the 70 is a word.
                # The `isupper()` guard in `clean_tokens` still applies, so ordinary prose is untouched.
                "genes", "genesi", "enesis"}


def clean_tokens(toks: list[str]) -> list[str]:
    """Drop verse numbers (standalone and glued) and apparatus marks. The ONE place that decision is made, so
    the Rung-3 overlay goes through it too — a `9.` reached the deliverable when R3 text bypassed this."""
    out = []
    for t in toks:
        t = _VNUM_GLUED.sub("", t)
        if not t or _VNUM.fullmatch(t) or is_apparatus_mark(t):
            continue
        # A RUNNING HEAD SURVIVES A LEAF JUNCTION. `_is_running_head` works on rows and cannot help here: when
        # two leaves' crops are joined for a straddling verse, the second leaf's head arrives inside the prose
        # (`...ſaid to her: Returne GENESIS. to thy miſtreſſe...` on genesis 16:9). Dropped only when the token
        # is set in capitals AND is one of the known heading words — never on the ordinary word `genesis`.
        bare = t.strip(_STRIP).lower()
        if bare in _PROSE_HEADS and t.strip(_STRIP).isupper():
            continue
        out.append(t)
    return out
_STRIP = " \t.,;:·†‡*()[]"


def _bare(t: str) -> str:
    return t.strip(_STRIP).lower().replace("ſ", "s")


def rejoin_break(rows: list[list[str]], lex: set[str] | None) -> list[list[str]]:
    """Rejoin a word the compositor broke at the measure, across the row boundary, in place on the first row.

    Two cases, and they need different evidence:

    * **The hyphen survived.** `hea-` + `uen` -> `heauen`. The recognizer marked the break itself (as `-` or
      `¬`), so joining is transcription, not inference.
    * **The hyphen was lost.** On `pdf-S03a` the same break comes back as `hea` + `uen` with no mark at all —
      the rule that reads the hyphen simply misses it, and the verse pays twice for one break. Joining every
      row boundary is not an option (`...and earth was` / `voide...` would glue to `wasvoide`), so the join
      needs independent evidence that a break happened: **neither fragment is a word of this book's archaic
      reference, and their concatenation is.** That is a lexicon test, not an answer key — the lexicon is the
      book's vocabulary, it says nothing about which words belong in which verse, and it can only ever join
      two things that are both already non-words.

    Without a lexicon only the first case fires, so the caller decides how much evidence it is willing to use.
    """
    for i in range(len(rows) - 1):
        if not rows[i] or not rows[i + 1]:
            continue
        last, nxt = rows[i][-1], rows[i + 1][0]
        if len(last) > 1 and last[-1] in "-¬":
            rows[i][-1] = last[:-1] + rows[i + 1].pop(0)
        elif lex and _bare(last) and _bare(nxt) and _bare(last) not in lex \
                and _bare(nxt) not in lex and _bare(last + nxt) in lex:
            rows[i][-1] = last + rows[i + 1].pop(0)
    return rows


def row_tokens(ocr_dir: str, page_index: int, page: dict,
               lex: set[str] | None = None) -> list[tuple[list[str], list[dict]]]:
    """The single assembly path: column-filtered rows -> broken words rejoined -> display line restored ->
    verse numbers dropped. Returns (tokens, source words) per surviving row so a caller can keep the geometry.

    Everything that consumes the page model goes through here, so `body_text` and the scoring harness cannot
    drift apart — the earlier split between them is why the flat-token hyphen rule and the row-boundary rule
    disagreed about `hea-`/`uen`."""
    rows = body_rows(ocr_dir, page_index, page)
    toks = rejoin_break([[w["t"] for w in r] for r in rows], lex)
    cm = chapter_model(ocr_dir)
    if page_index == cm.get("open_page") and cm.get("drop_cap"):
        glued, display = cm["drop_cap"]
        # Scan the OPENING ROWS' tokens, not just the first token of the first row. On `archive-ot1-1609` p81
        # the display line arrives as `and ſmaelSARAI` — the engraved S is glued to the argument's last word AND
        # preceded by a stray `and`, so a first-token test never fired and gen 16:1 kept `and ſmaelSARAI`.
        for r in toks[:DROP_CAP_ROWS]:
            hit = next((i for i, t in enumerate(r) if t == glued), None)
            if hit is not None:
                r[hit] = display
                del r[:hit]                    # anything before the display line is not scripture
                break
    out = []
    for ts, r in zip(toks, rows):
        ts = clean_tokens(ts)
        # CONTENT-AND-SEQUENCE APPARATUS STRIP (§13 Q43, default OFF under ODR_ROW_INTERRUPT). Seven geometric
        # attempts have failed to separate the left annotation column from the body once kraken has merged both
        # into one y-band row; `row_interrupt` does it on the chapter's ARCHAIC reference instead — a leading run
        # is dropped only when what REMAINS matches an n-gram the chapter actually sets.
        if ts and os.environ.get("ODR_SPLIT_GLUED", "0") != "0":
            ts = split_glued(ts, lex)
        if ts and _row_interrupt_on():
            import row_interrupt as RI
            ts2, removed = RI.strip_row(ts, "genesis", CHAPTER)
            if removed:
                ts = ts2
        if ts and r:
            out.append((ts, r))
    return out


def body_text(ocr_dir: str, page_index: int, page: dict, lex: set[str] | None = None) -> str:
    """Body text for one page: column-filtered, reading-order restored, hyphens rejoined, verse numbers out.

    The printed verse NUMBERS are dropped here rather than kept: on the first edition they are a column of
    their own and on the second they are inline, so leaving them in would mean the two editions' spans differ
    by material that is not text. `verse_seg` cuts on the janvier grid, not on printed numbers, so nothing
    downstream needs them."""
    return " ".join(" ".join(ts) for ts, _ in row_tokens(ocr_dir, page_index, page, lex))


def load(book: str = "genesis", chapter: int | None = None) -> dict:
    """The word-box cache for one chapter. Genesis 1 keeps its historical filename."""
    ch = CHAPTER if chapter is None else chapter
    p = WB if (book, ch) == ("genesis", 1) else HERE / f".wordboxes-{book}-{ch}.json"
    return json.loads(p.read_text()) if p.exists() else {}


if __name__ == "__main__":
    wb = load()
    for od, pages in wb.items():
        for pi, pd in sorted(pages.items(), key=lambda kv: int(kv[0])):
            t = body_text(od, int(pi), pd)
            allw = sum(len(l["words"]) for l in pd["lines"])
            print(f"{od:24s} p{pi:>3}  {len(t.split()):>4}/{allw:<4} words kept   {t[:88]}")
