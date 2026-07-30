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
    "jp2-S06":                {"body": (0.215, 0.825), "edition": 2, "head_frac": 0.075},
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
    if _DERIVED_CACHE is None:
        try:
            _DERIVED_CACHE = json.loads(_DERIVED_PATH.read_text())
        except Exception:                                        # noqa: BLE001
            _DERIVED_CACHE = {}
    return _DERIVED_CACHE


def chapter_model(ocr_dir: str, chapter: int | None = None) -> dict:
    ch = chapter if chapter is not None else CHAPTER
    hand = CHAPTER_MODEL.get((ocr_dir, ch))
    if hand is not None:
        return hand
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


def body_rows(ocr_dir: str, page_index: int, page: dict) -> list[list[dict]]:
    """The words of one page that lie inside this SOURCE's body column, in reading order.

    Reading order is rebuilt from the boxes rather than taken from kraken's line order, because the recognizer
    interleaves the columns: on `archive-holiebible-ot1` p31 the annotation lines at y=4713 and y=4862 are
    emitted BETWEEN the body lines at y=4694 and y=4877. Sorting the surviving body words by (y-band, x) puts
    the scripture back in the order it is printed."""
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
    return len(row) == 2 and all(w["t"][:1].isupper() and w["t"].endswith(".") for w in row)


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
    return bool(_LONE_LETTER.fullmatch(t)) and t not in _REAL_ONE_LETTER


# Running heads and section headings as they appear in PROSE (an R3 crop transcript, where there are no rows to
# test the shape of). A multi-leaf crop join walks straight over a leaf's top, so `GENESIS.` lands mid-verse.
_PROSE_HEADS = {"genesis", "creation", "annotations", "annotation"}


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
