# -*- coding: utf-8 -*-
"""RUNG 3 ON THE GENESIS 1 RESIDUAL — re-read the open cells with the vision model, adopt only what improves.

WHY R3 AND NOT MORE GEOMETRY. The page model closed 485 of the 496 Genesis 1 cells, and the 11 that remain are
not layout defects. Three classes, each diagnosed:

    S1 v13, S3 v13   0.852   both witnesses genuinely drop `was` from `And there was euening`   RECOGNITION
    S9 v15/v18/v21   0.881   margin words (`first`, `of`, `di`, `for`) interleaved into rows     SEGMENTATION
    S6 v8            0.895   `firmameut` `euenins` `mornins` (n/u, g/s) + the `(b)` marker       RECOGNITION

No band, threshold or row rule reaches any of them — the words are either absent from the recognizer's output
or merged into it by a segmentation that cannot be un-merged downstream. That is exactly the residual the
ladder's third rung exists for: re-read the PIXELS of the verse with a different model.

THE BACKEND IS LOCAL (olmOCR-2 via MLX, §8 R3-1). No paid API is called. olmOCR MODERNIZES ſ->s on crops —
its OCR fine-tuning ignores diplomatic prompts — so it is a CONTENT rung and nothing more. That is sound here
because the governing gate is `archaic_id`, whose `fold_archaic` treats ſ and s as the same letter (a measured
finding: ſ->s scores 1.000, invisible to the content gate). The ſ-faithful SURFACE is the s_arbiter's job and
is not touched by this module. **A ſ must never be faked to raise a score.**

NO SILENT DEGRADATION, MECHANICALLY. A re-read is adopted only if it beats the incumbent on the governing arm
AND clears the bar. Anything else leaves the cell exactly as it was and OPEN — including a re-read that is
better but still short, which is recorded as a partial and still blocks. The module cannot mark a cell closed
by any path other than actually clearing it.

Usage:  ../ocr-venv/bin/python gen1_r3.py [--bar 0.90] [--cells S9:15,S6:8] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen1_matrix as MX                       # noqa: E402
import gen1_pagemodel as PM                    # noqa: E402
import gen1_pagemodel_eval as EV               # noqa: E402
import ref_renumber as RR                      # noqa: E402
import s_arbiter
import s_lexicon                               # noqa: E402

# §13 Q40. Attested-lexicon ſ closure, ON by default because it is measured at 1.0000 on held-out human GT and
# refuses three quarters of what it is asked; ODR_S_LEXICON=0 ablates it.
S_LEXICON = os.environ.get("ODR_S_LEXICON", "1") != "0"
_S_LEX_TABLE = {}
_EDITION_OF = dict(s_lexicon.EDITION)


def _s_lex_table() -> dict:
    global _S_LEX_TABLE
    if not _S_LEX_TABLE:
        try:
            _S_LEX_TABLE = __import__("json").loads((HERE / ".s-lexicon.json").read_text())
        except Exception:                                        # noqa: BLE001
            _S_LEX_TABLE = {"table": {}}
    return _S_LEX_TABLE
import verse_geom                              # noqa: E402
import verse_locate                            # noqa: E402
import verse_seg as VS                         # noqa: E402
from char_identity import evaluate_locus        # noqa: E402

REFS = EV.REFS
ARM = MX.ARM
ARCHAIC = EV.ARCHAIC
def residual_path() -> Path:
    """Chapter-keyed. It was NOT, and the Genesis 1 verification run silently overwrote the Genesis 16 report —
    a later diagnostic then compared Genesis 1 texts against Genesis 16 references and produced nonsense
    (verses 20-31 in a 16-verse chapter). Any per-chapter artifact must be keyed by chapter."""
    return (HERE / "gen1-r3-residual.json") if (EV.BOOK, EV.CHAPTER) == ("genesis", 1) \
        else HERE / f"r3-residual-{EV.BOOK}-{EV.CHAPTER}.json"
# The ADOPTED re-reads, keyed `SRC:verse`. `gen1_matrix.py` overlays this file and labels those cells `r3` in
# its provenance column — an R3 rescue must be VISIBLE in the matrix, never blended in as though the page model
# had produced it. Delete the file and the matrix returns to the pure page-model result.


# IN-SESSION VISUAL READINGS — the ſ-arbiter's closure path, `SRC:verse` -> {token index: ſ-faithful spelling}.
# `s_arbiter.transfer` can only adopt a ſ that R2 actually observed. Where R3 CORRECTED R2 the surface is
# unattested, and `long_s_rule.restore_long_s` must not be used to fill it (measured ~90.4% on this project's
# own gold — publishing it would present about 1 invented glyph in 10 as the printed surface). The only
# admissible closure is OBSERVATION, so the crop is rendered and read.
#
# Each entry records what the image shows, so the reading can be re-checked against the same pixels.
# Keyed by the TOKEN AS R3 RETURNED IT, not by its index. `s_arbiter.arbitrate` wants indices, and an earlier
# draft stored them — but an index shifts whenever the localizer trims a word, so the entry silently starts
# pointing at a different token. A reading is an observation about a WORD on a leaf; storing it that way makes
# it re-checkable and stable. Indices are resolved at apply time.
VISUAL_READINGS_BY_TOKEN: dict[str, dict[str, str]] = {
    # --- archive-ot1-1609 (S1) p82, read 2026-07-29 ---
    # The leaf shows `shalt bring forth a ſonne`, `his hand shal be againſt al men`, `And she called the name
    # of our Lord`, `ſpake vnto her`, `haſt ſene me`, `For she ſaid : verily here haue I ſene`. So in this font
    # initial s before h is ROUND (`shal`, `she`) while initial s elsewhere is LONG (`ſonne`, `ſpake`, `ſaid`).
    # Recorded as the readings they are, not as the rule they suggest.
    "S1:12": {"shal": "shal"},
    "S1:13": {"she": "she", "said:": "ſaid:"},
    "S3:12": {"shal": "shal"},
    "S3:13": {"she": "she", "said:": "ſaid:", "fene": "ſene"},

    # --- jp2-S06 (S6) p76, read 2026-07-29 — AND IT SETS ſhe/ſhal WITH LONG-ſ, unlike the 1609 leaves above.
    # `3. ſhe toke Agar the Ægyptian`, `but ſhe (a) perceiuing that ſhe was with child, deſpiſed her miſtreſſe`,
    # `Thou doeſt vniuſtly againſt me`, `making anſwer`, `as it pleaſeth thee`, `who anſwered : From the face of
    # Sarai my miſtreſſe doe I flye`, `it ſhal not be numbred`, `bring forth a ſonne`, `And ſhe called`,
    # `Eightie and ſixe yeares old`. That the two editions differ here is exactly why this is observed per
    # witness and never derived from a positional rule.
    # p76 band at y 0.375-0.520 reads `3. ſhe toke Agar the Ægyptian her handmaid`. R2 observed `ſhe`; R3
    # returned `She` — modernized AND capitalized, so the ſ-fold did not match it against R2's token and the
    # modernized form won, dropping an observed ſ (3 -> 2) and tripping the arbiter's ALERT. That ALERT was
    # right: the fix is the reading, not a looser fold.
    "S6:3":  {"after": "after", "wife.": "wife."},
    "S6:4":  {"mistresse.": "miſtreſſe."},
    "S6:5":  {"doest": "doeſt", "ſelf": "ſelf"},
    "S6:6":  {"pleaseth": "pleaſeth", "therfore": "therfore"},
    "S6:7":  {"found": "found"},               # genuine f
    "S6:8":  {"answered:": "anſwered:", "miftresse": "miſtreſſe", "flye.": "flye.",
              "said": "ſaid", "mistresse": "miſtreſſe"},
    "S6:10": {"for": "for"},                   # genuine f
    "S6:11": {"sonne;": "ſonne;", "shalt": "ſhalt"},   # p76: `thou ſhalt bring forth a ſonne`
    "S6:13": {"she": "ſhe", "Therfore": "Therfore"},
    # p76 at y 0.855-0.885 reads `Cadeſſe and Barad. 15. And Agar brought forth a ſonne`, and at y~0.87
    # `liueth and ſeeth me`. R3 returns the ſſ ligature as `ff` and ſ as f.
    "S6:14": {"feeth": "ſeeth", "Cadeffe": "Cadeſſe"},
    "S6:15": {"forth": "forth"},               # genuine f

    # --- archive-holiebible-ot1 (S9) p91, read 2026-07-29 ---
    # `And Sarai ſaid to Abram : Thou doeſt vniuſtly againſt me`, `making anſwere`, `as it pleaſeth thee`,
    # `When Sarai therfore did afflict her`.
    "S9:6":  {"answere:": "anſwere:"},

    # `ſixe` — long-ſ in BOTH editions. `archive-ot1-1609` p82 reads `Eightie and ſixe yeares old was Abram`;
    # `jp2-S06` p76 reads the same. R3 returns `fixe`, a ſ->f misread, so the ſ has to be restored by reading.
    "S1:16": {"fixe": "ſixe"},
    "S3:16": {"fixe": "ſixe"},
    "S6:16": {"fixe": "ſixe"},
    # These two become surface questions only AFTER the content correction above rewrites the token, so the
    # reading confirms what the leaf shows for the corrected form: `her ſelf` (long-ſ) and `therfore` (true f).
}


def _assert_no_duplicate_readings() -> None:
    """A DICT LITERAL SILENTLY DROPS A DUPLICATE KEY, and that cost real observations. A later edit appended a
    second `"S6:5"` entry below the first; Python kept only the last, so the `doest -> doeſt` reading I had read
    off the leaf vanished and the cell stayed OPEN for a token I had already resolved. Source text is checked
    directly because by the time the dict exists the evidence is gone."""
    import collections
    import re as _re
    src = Path(__file__).read_text()
    for table in ("VISUAL_READINGS_BY_TOKEN", "VISUAL_CONTENT_BY_TOKEN"):
        i = src.index(table + ":")
        body = src[i:src.index("\n}", i)]
        keys = _re.findall(r'^\s*"([A-Z0-9]+:\d+)":', body, _re.M)
        dupes = [k for k, c in collections.Counter(keys).items() if c > 1]
        if dupes:
            raise AssertionError(f"{table} has duplicate keys (later ones silently win): {dupes}")


_assert_no_duplicate_readings()

VISUAL_READINGS: dict[str, dict[int, str]] = {
    # jp2-S06 p18, the line at y 0.788-0.818, read 2026-07-29. `firmament` contains no s at all, so the `f`
    # that made the token an open ſ-decision (`decision_positions` treats f as a possible misread ſ) is a true
    # `f`. Confirming that with the same content skeleton is what closes the surface honestly — the n->m
    # correction is a CONTENT matter and goes through VISUAL_CONTENT below, which the arbiter's guard rightly
    # refuses to accept here. The spelling matches the token AFTER VISUAL_CONTENT is applied, so the arbiter
    # sees an unchanged content skeleton and is asked only the question it exists to answer: is that f a ſ?
    "S6:8": {4: "firmament,"},
}

# IN-SESSION VISUAL CONTENT CORRECTIONS — `SRC:verse` -> {token index: reading}. SEPARATE from the ſ-arbiter on
# purpose. `s_arbiter.arbitrate` raises if a reading changes the content skeleton, and that guard is correct:
# a content change must be visible as a content change and be re-scored, not slipped in as a surface adoption.
# (It fired on this very entry — `sirmanent,` -> `sirmament,` — which is how the two got separated.)
#
# Admissible ONLY from direct observation of the page image, with what the image shows recorded, and only when
# it raises the governing score. This is the top of the ladder: neither recognizer read the word correctly, so
# no amount of re-running them would have fixed it.
# Content corrections keyed by TOKEN, same reasoning as VISUAL_READINGS_BY_TOKEN. Applied BEFORE the surface
# arbitration, so the arbiter then sees an unchanged content skeleton and is asked only its own question.
#
# READ OFF THE LEAVES, 2026-07-29. Genesis 16 needed these because R3 modernizes more than the ſ: it returns
# `therefore` where all four witnesses print `therfore`, `afflicte` for `afflict`, `selfe` for `ſelf`, and
# `vnjustly` for `vniuſtly` (j for i). Those are spelling, not recognition — a diplomatic transcription must
# keep what the leaf shows.
VISUAL_CONTENT_BY_TOKEN: dict[str, dict[str, str]] = {
    "S1:1":  {"therefore,": "therfore,"},      # archive-ot1-1609 p81: `SARAI therfore, the wife of Abram`
    "S3:1":  {"therefore,": "therfore,"},
    "S9:1":  {"therefore,": "therfore,"},
    "S6:5":  {"selfe": "ſelf", "vnjustly": "vniuſtly"},
    "S9:5":  {"vnjustly": "vniuſtly"},
    "S6:6":  {"therefore": "therfore"},
    "S9:6":  {"therefore": "therfore", "afflicte": "afflict"},
    # archive-ot1-1609 p82 at y 0.288-0.318 reads `him that liueth and ſeeth me. The ſame is betwen Cadeſſe,`.
    # The merge's conflict block was `berwen Cadeſſe, | betwen Cadelle,` — R3 right on the first token, R2 right
    # on the second — so R3's `Cadelle,` has to be corrected from the leaf.
    "S1:14": {"Cadelle,": "Cadeſſe,"},
    # The stray " is a marginal quotation mark, not type. `She` -> `ſhe` is here rather than in the readings
    # table because `s_arbiter` classifies it as CONTENT, not surface: its fold is ſ-only and case-sensitive, so
    # `ſhe` and `She` are not fold-equal and no ſ decision is ever opened. p76 prints `3. ſhe toke Agar`.
    "S6:3":  {'husband"': "huſband", "She": "ſhe"},
}

VISUAL_CONTENT: dict[str, dict[int, str]] = {
    # jp2-S06 p18 at y 0.788-0.818 reads, plainly:
    #     `firmament. And it was ſo done. 8. And God called the firmament,`
    # R2 read `firmameut`, R3 read `firmanent`; the printed word is `firmament` in both places on the line.
    "S6:8": {4: "firmament,"},
}


_LOC_CACHE: dict[str, dict] = {}


def _localizer_leaf(ocr_dir: str, verse: int) -> int | None:
    """The leaf the corpus localizer found this verse on — evidence, not a search over candidates."""
    if ocr_dir not in _LOC_CACHE:
        f = HERE / f".corpus-localize-{ocr_dir}.json"
        _LOC_CACHE[ocr_dir] = json.loads(f.read_text()).get("verses", {}) if f.exists() else {}
    rec = _LOC_CACHE[ocr_dir].get(f"{EV.BOOK}/{EV.CHAPTER}/{verse}")
    return rec.get("page") if isinstance(rec, dict) else None


def _chapter_leaves(ocr_dir: str) -> set[int]:
    """Every leaf the corpus localizer credits with a verse of THIS chapter, for this witness."""
    _localizer_leaf(ocr_dir, 1)                      # prime the cache
    return {rec["page"] for k, rec in _LOC_CACHE.get(ocr_dir, {}).items()
            if k.startswith(f"{EV.BOOK}/{EV.CHAPTER}/") and isinstance(rec, dict) and rec.get("page")}


def widen_to_measure(box, ocr_dir: str, page_index: int, margin: float = 0.06):
    """Widen a verse crop horizontally to the LEAF'S WHOLE MEASURE, keeping its vertical extent.

    THE BUG THIS FIXES, AND IT WAS SYSTEMIC. `verse_geom.verse_crops` unions the bboxes of the verse's own
    lines and pads by 2%. On a leaf whose body left edge varies down the page — `jp2-S06` p76 is indented to
    x~0.38 beside its argument and runs out to x~0.19 below it — that union starts at this verse's own leftmost
    glyph, and 2% does not clear the scan's skew. The crop then GUILLOTINES WORD BEGINNINGS, and the vision
    model faithfully transcribes the fragment it was shown. Measured on genesis 16:3, one crop, three x0 values:

        x0 = 0.2186 (as computed)   `...they first ed in the land`        <- `dwelled` beheaded
        x0 = 0.1886 (-3%)           `...they first velled in the land`    <- still cut
        x0 = 0.1386 (-8%)           `...they first dwelled in the land`   <- correct

    The same fault explains `ke parts` for `backe parts` and `I hold` for `Behold`. It is not a recognition
    failure at all, and no amount of merging two beheaded transcripts would recover the missing letters.

    A verse is a BAND OF LINES; the lines span the measure. So the crop is tight in y — which is what selects
    the verse — and full-width in x, which is what makes the words whole.

    `margin` is 0.06, not the 0.03 first tried: at 0.03 `Behold` still came back as `hold,` on `jp2-S06` p76,
    whose body reaches further left than its witness-level band constant admits. The margin costs nothing —
    a little apparatus in the crop is transcribed and then discarded by localization — while a margin that is
    too small costs letters that cannot be recovered downstream."""
    m = {**PM.SOURCE_MODEL[ocr_dir], **PM.chapter_model(ocr_dir),
         **PM.PAGE_OVERRIDE.get((ocr_dir, page_index), {})}
    lo, hi = m["body"]
    x0, y0, x1, y1 = box
    return (max(0.0, min(x0, lo - margin)), y0, min(1.0, max(x1, hi + margin)), y1)


LEAF_FIT_FLOOR = 0.55


def span_fit(span: str, janvier_verse: str) -> float:
    """How much of THIS SPAN is janvier's verse — a coverage measure that survives a partial span.

    `verse_locate.janvier_fit` cannot be used to choose a leaf, and finding out why explains two earlier
    failures. It delegates to `evaluate_locus`, which compares a WHOLE verse to its reference, so it returns
    **0.000 for any partial span**:

        identical                                     1.000
        the whole verse in archaic spelling            0.959   <- spelling is NOT the problem
        `and humble thyself under her hand.` (tail)    0.000
        `And the Angel of our Lord said to her:` (head) 0.000

    A verse that straddles two leaves appears on each leaf ONLY as a partial — which is precisely the case leaf
    selection exists for. So every candidate scored 0, `max()` picked arbitrarily, and the crop came back
    reading Genesis 15. Adding a floor did not help because nothing ever cleared it.

    This measures the fraction of the span's own tokens that occur, in order, in the janvier verse. A correct
    partial scores high (all its words are in the verse); a span from the wrong leaf scores low (few are). It is
    deliberately PRECISION-like, not recall-like: a partial should not be penalised for the part it lacks."""
    import difflib
    a = [PM._bare(t) for t in (span or "").split()]
    b = [PM._bare(t) for t in (janvier_verse or "").split()]
    a = [t for t in a if t]
    b = [t for t in b if t]
    if not a or not b:
        return 0.0
    m = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    return sum(bl.size for bl in m.get_matching_blocks()) / len(a)


def _leaf_span(ocr_dir: str, page: int, verse: int, lex, wb):
    """(janvier fit, span) for `verse` on `page`, or (0, {}) if the leaf is not cached."""
    pd = (wb.get(ocr_dir) or {}).get(str(page))
    if not pd:
        return 0.0, {}, 0
    pr = _page_result(ocr_dir, page, pd, lex)
    if not pr["lines"]:
        return 0.0, {}, 0
    sp = (verse_locate.best_spans(pr, EV.BOOK, EV.CHAPTER) or {}).get(verse) or {}
    grid = VS.chapter_verses(EV.BOOK, EV.CHAPTER, VS.JANVIER) or {}
    fit = span_fit(sp.get("text") or "", grid.get(verse))
    return fit, sp, len(pr["lines"])


def _straddle_leaves(ocr_dir: str, verse: int, anchor: int, lex, wb) -> list[int]:
    """The leaf this verse is printed on, plus a neighbour only if its span RUNS OFF that leaf's edge.

    THE ANCHOR IS A HYPOTHESIS, NOT A FACT. `.corpus-localize-*.json` is the best available statement of where
    a verse sits, and for genesis 16:9 it is simply WRONG on two of three witnesses: it names `pdf-S03a` p84,
    whose span for that verse reads `And the foules lighted vpon the carcaſſes` (Genesis 15:11), and
    `archive-holiebible-ot1` p90, which gives `a shee goat of three yeares` (Genesis 15:9). It is right on
    `archive-ot1-1609`. So the localizer's page attribution is unreliable at chapter boundaries.

    Neither pure source works alone — picking by best fit chose Genesis 15 leaves twice, and trusting the
    localizer chose them here. So the anchor is TESTED: it is accepted only if the verse's span there clears
    `LEAF_FIT_FLOOR` against janvier, and otherwise the chapter's other leaves are tried and must clear the
    same floor. The floor is the positive evidence the earlier attempts had no way to demand; the localizer's
    claim still wins any tie, because it was made with the whole book in view."""
    own = _chapter_leaves(ocr_dir)
    fit, sp, n = _leaf_span(ocr_dir, anchor, verse, lex, wb)
    if fit < LEAF_FIT_FLOOR:
        cands = [(f, p2, s2, m) for p2 in sorted(own) if p2 != anchor
                 for f, s2, m in [_leaf_span(ocr_dir, p2, verse, lex, wb)] if f >= LEAF_FIT_FLOOR]
        if cands:
            fit, anchor, sp, n = max(cands)[0], max(cands)[1], max(cands)[2], max(cands)[3]
    out = [anchor]
    lines = sp.get("lines") or []
    if not lines or n == 0:
        return out
    if min(lines) <= 0 and (anchor - 1) in own:
        out.insert(0, anchor - 1)               # the verse begins before this leaf
    if max(lines) >= n - 1 and (anchor + 1) in own:
        out.append(anchor + 1)                  # the verse continues onto the next
    return out


def _page_result(ocr_dir: str, page_index: int, pd: dict, lex) -> dict:
    lines = EV.page_lines(ocr_dir, page_index, pd, lex)
    return {"page_px": tuple(pd["page_px"]), "lines": lines, "page_index": page_index,
            "n_body": len(lines), "n_lines": len(lines),
            "r2_body": " ".join(l["text"] for l in lines)}


def localize_in_crop(text: str, verse: int, neighbours: set[int] | None = None) -> str:
    """Cut verse `verse` out of a crop transcript before scoring it.

    A VERSE CROP IS NOT A VERSE. `verse_geom.verse_crops` returns the band of LINES the verse occupies, and
    those lines carry their neighbours: the crop for gen 1:13 begins mid-way through 1:12, so R3 returns
    `...according to his kinde. And God saw that it was good. † And there was euening & morning that made the
    third day.` Scored whole against an 11-token reference that returns **0.000** — which on the first run made
    six perfectly good re-reads look like total failures. (Same trap as the kraken probe: a dead metric reads
    as a verdict.)

    So the R3 text is localized the way R2 output is — segmented against the JANVIER grid, which is the
    project's gold-free localization reference, and only then scored against s_dismas/odr_com. Janvier decides
    WHERE the verse is; the archaic references decide how well it was read. Using the scoring reference to find
    the span would be circular; using janvier is the same separation the live pipeline relies on.

    AND THE GRID MUST BE RESTRICTED TO THE VERSES THE CROP CONTAINS. Segmenting a two- or three-verse crop
    against the whole 31-verse chapter is under-constrained, and it mis-assigns: asked for gen 1:15 in a crop
    holding 14 and 15, it returned 14's text (`divide the day & the night ... for signes & seasons`) and scored
    0.000. `neighbours` is derived from the page's OWN geometry — the verses whose lines overlap the cropped
    band — so it is a fact about which pixels were sent, not a hint about the answer.

    NEITHER GRID IS RIGHT ON ITS OWN, SO BOTH ARE TRIED. The restricted grid fixes the mis-assignment above,
    and breaks gen 1:13: that crop ends just after v14's first word, too little of v14 for the segmenter to
    claim it, so `Againe` stays attached to v13 and the score falls 1.000 -> 0.883. The full grid keeps
    `Againe` (v14's janvier text anchors it) and mis-assigns v15. Each grid wins on a different crop, so both
    are segmented and the span with the better JANVIER fit is kept — the same gold-free selection
    `verse_locate.best_spans` already uses to choose between its two segmenters, applied one level down."""
    if not text.strip():
        return ""
    full = VS.chapter_verses(EV.BOOK, EV.CHAPTER, VS.JANVIER) or {}
    grids = [full]
    if neighbours:
        grids.append({v: t for v, t in full.items() if v in neighbours})
    cands: list[str] = []
    for grid in grids:
        if verse not in grid:
            continue
        try:
            spans = VS.segment(text, grid) or {}
        except Exception:                                       # noqa: BLE001
            continue
        cands.append(((spans.get(verse) or {}).get("text") or "").strip())
    # And the HYBRID localizer as a third candidate. `verse_seg.segment` is one segmenter; `best_spans` runs
    # the global alignment and the anchor-walk and picks per verse. On gen 1:13 only its walk arm trims the
    # trailing `Againe` (v14's first word), which is worth 0.883 -> 1.000 — so leaving it out of the candidate
    # set loses a cell that the incumbent pipeline would have localized correctly.
    page = {"page_px": (1000, 1000), "page_index": 0, "n_body": 1, "n_lines": 1,
            "r2_body": text, "lines": [{"text": text, "conf": 1.0, "role": "body",
                                        "bbox": (0, 0, 1000, 1000)}]}
    try:
        cands.append((((verse_locate.best_spans(page, EV.BOOK, EV.CHAPTER) or {}).get(verse) or {})
                      .get("text") or "").strip())
    except Exception:                                           # noqa: BLE001
        pass
    best, best_fit = "", -1.0
    for cand in cands:
        if not cand:
            continue
        fit = verse_locate.janvier_fit(cand, full.get(verse))
        if fit > best_fit:
            best, best_fit = cand, fit
    return best


def merge_arms(r2: str, r3: str) -> tuple[str, list[str]]:
    """Compose one transcript from R2 and R3 using only what the two recognizers themselves establish.

    WHY A MERGE AT ALL. On `jp2-S06` p76 gen 16:16 the two arms are each missing a different word:

        R2  `Eightie and ſixe yeares old was Abram      Agar brought him forth Iſmael.`
        R3  `        and fixe yeares old was Abram when Agar brought him forth Iſmael.`

    Neither clears the bar; between them they hold the whole verse. But the diagnosis that produced this module
    also bounds it: R3 out-reads R2 on almost every verse, and the union beats the better single arm by only
    ONE OR TWO tokens on half the open verses. This is a small, last-mile lever, not the main event — the main
    event was the crop geometry (see `widen_to_measure`), worth 0.09-0.16 per verse.

    WHAT IT MAY AND MAY NOT USE. It aligns the two ARMS against each other, never against a reference:

      * both arms agree           -> take it (two independent observations)
      * one arm has tokens where the other has NONE  -> take them. A dropout is not a reading; the arm that
        saw nothing is not testifying against the arm that saw something.
      * the arms DISAGREE         -> a genuine conflict. Report it, take R3 (the measurably stronger arm), and
        let the ſ-arbiter and a visual read settle it.

    Choosing tokens by which one matches the scoring reference would manufacture a transcript neither
    recognizer produced, guided by the answer. That is the line this function does not cross — which is also
    why it cannot close a cell on its own, only hand a better candidate to the same gates as before."""
    import difflib
    A, B = r2.split(), r3.split()
    fa = [PM._bare(t) for t in A]
    fb = [PM._bare(t) for t in B]
    out: list[str] = []
    conflicts: list[str] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=fa, b=fb, autojunk=False).get_opcodes():
        if tag == "equal":
            out += B[j1:j2]                      # agreed; keep R3's surface (it may carry the better glyphs)
        elif tag == "delete":                    # R2 has tokens, R3 dropped them
            out += A[i1:i2]
        elif tag == "insert":                    # R3 has tokens, R2 dropped them
            out += B[j1:j2]
        else:
            # A REAL DISAGREEMENT. Pair the tokens positionally: where the two differ ONLY by the ſ-fold, keep
            # R2's — it is the ſ-faithful recognizer, so its glyph is an observation and R3's is a
            # modernization. Where they differ in content, keep R3's, which measures stronger.
            #
            # This does not resolve every conflict, and it must not pretend to. On `archive-ot1-1609` gen 16:14
            # the block is `berwen Cadeſſe, | betwen Cadelle,`: R3 is right about the first token and R2 about
            # the second, and neither is a pure ſ difference. The ſ-arbiter returns ALERT there — correctly —
            # and the leaf has to be read. Choosing by which token matched the reference is the one thing this
            # may never do.
            conflicts.append(f"{' '.join(A[i1:i2])} | {' '.join(B[j1:j2])}")
            ra, rb = A[i1:i2], B[j1:j2]
            for k in range(max(len(ra), len(rb))):
                ta = ra[k] if k < len(ra) else None
                tb = rb[k] if k < len(rb) else None
                if ta is not None and tb is not None and PM._bare(ta) == PM._bare(tb):
                    out.append(ta if ta.count("ſ") >= tb.count("ſ") else tb)
                elif tb is not None:
                    out.append(tb)
                elif ta is not None:
                    out.append(ta)
    return " ".join(out), conflicts


def _stitch(chunks: list[str], max_overlap: int = 12) -> str:
    """Join per-leaf crop transcripts, collapsing the repeated n-gram at each junction.

    Adjacent leaves' crops both catch the text either side of the break, so a naive join DUPLICATES it:
    genesis 16:9 came out `...ſaid to her: Returne to thy TO THY mistresse, and humble...`. A duplicated phrase
    costs the verse as surely as a missing one. The longest suffix of what we have that is also a prefix of the
    next chunk is the overlap; it is dropped from the incoming chunk, never from the text already accepted."""
    out: list[str] = []
    for c in (x.strip() for x in chunks):
        if not c:
            continue
        toks = c.split()
        if out:
            fa = [PM._bare(t) for t in out]
            fb = [PM._bare(t) for t in toks]
            k = 0
            for n in range(min(max_overlap, len(fa), len(fb)), 0, -1):
                if fa[-n:] == fb[:n]:
                    k = n
                    break
            toks = toks[k:]
        out += toks
    return " ".join(out)


def _stitch(chunks: list[str], max_overlap: int = 12) -> str:
    """Join per-leaf crop transcripts, collapsing the repeated n-gram at each junction.

    Adjacent leaves' crops both catch the text either side of the break, so a naive join DUPLICATES it:
    genesis 16:9 came out `...ſaid to her: Returne to thy TO THY mistresse, and humble...`. A duplicated phrase
    costs the verse as surely as a missing one. The longest suffix of what we have that is also a prefix of the
    next chunk is the overlap; it is dropped from the incoming chunk, never from the text already accepted."""
    out: list[str] = []
    for c in (x.strip() for x in chunks):
        if not c:
            continue
        toks = c.split()
        if out:
            fa = [PM._bare(t) for t in out]
            fb = [PM._bare(t) for t in toks]
            k = 0
            for n in range(min(max_overlap, len(fa), len(fb)), 0, -1):
                if fa[-n:] == fb[:n]:
                    k = n
                    break
            toks = toks[k:]
        out += toks
    return " ".join(out)


def trim_span_edges(text: str, verse: int) -> str:
    """Drop leading/trailing tokens that belong to the NEIGHBOURING verse, judged on janvier only.

    A crop holds two or three verses, and the localizer's cut can land a word late or early. `jp2-S06` 16:15
    came back as `...who called his name Iſmael. Eightie` — `Eightie` opens verse 16. One stray token costs a
    short verse ~0.05, which is the difference between clearing the bar and not.

    The test is comparative and gold-free: a boundary token is dropped only if it matches the NEIGHBOUR's
    janvier text and does NOT appear in this verse's own. Tokens this verse genuinely contains are never
    touched, so a verse that legitimately repeats a neighbour's wording is safe."""
    # THE COMPARISON MUST FOLD ARCHAIC/MODERN SPELLING. janvier is modern, so a plain fold left `Eightie`
    # attached to genesis 16:15 because janvier verse 16 spells it `Eighty` — the token was in the next verse
    # and the test could not see it. This is the same fold `ref_alignment_audit` needed for the same reason.
    import ref_alignment_audit as RA
    def f1(t):
        n = RA._norm(t)
        return n[0] if n else ""
    def fset(txt):
        return set(RA._norm(txt or ""))
    grid = VS.chapter_verses(EV.BOOK, EV.CHAPTER, VS.JANVIER) or {}
    mine = fset(grid.get(verse))
    prv = fset(grid.get(verse - 1)) - mine
    nxt = fset(grid.get(verse + 1)) - mine
    toks = text.split()
    while toks and f1(toks[0]) in prv:
        toks.pop(0)
    while toks and f1(toks[-1]) in nxt:
        toks.pop()
    return " ".join(toks)


def _score(text: str, refs: dict, verse: int) -> dict[str, float | None]:
    out = {}
    for r in REFS:
        ref = refs[r].get(f"scripture/{EV.BOOK}/{EV.CHAPTER}/{verse}")
        out[r] = round(evaluate_locus(text, ref, ref)[ARM[r]], 3) if (text and ref) else None
    return out


def _governing(sc: dict) -> float:
    """The archaic arm governs (QC §1.4). A cell is judged on the WORSE archaic reference, not the kinder one."""
    vals = [sc[r] for r in ARCHAIC if sc.get(r) is not None]
    return min(vals) if vals else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bar", type=float, default=0.90)
    ap.add_argument("--book", default="genesis")
    ap.add_argument("--chapter", type=int, default=1)
    ap.add_argument("--improve-below", type=float, default=None, metavar="X",
                    help="ALSO re-read cells that already clear the bar but score under X, to push the best "
                         "toward 1.000. Adoption still requires beating the incumbent AND clearing the bar, so "
                         "this can only improve the deliverable. Genesis 1: 64 of 124 groups sit under 0.95.")
    ap.add_argument("--cells", default=None, help="restrict to e.g. S9:15,S6:8")
    ap.add_argument("--dry-run", action="store_true", help="report the crops and skip the vision calls")
    ap.add_argument("--max-tokens", type=int, default=700)
    a = ap.parse_args()

    EV.set_locus(a.book, a.chapter)
    ADOPTED = MX.r3_store()
    import reocr_r3

    wb = PM.load(EV.BOOK, EV.CHAPTER)
    lex = EV.book_lexicon()
    refs = {n: RR.load_corrected(n, trim=(EV.BOOK, EV.CHAPTER)) for n in REFS}
    janv = VS.chapter_verses(EV.BOOK, EV.CHAPTER, VS.JANVIER) or {}

    # The open set is recomputed here rather than read from the matrix json, so this module can never act on a
    # stale worklist — a cell the page model has since fixed must not be "rescued".
    todo: list[dict] = []
    for s, od in EV.WITS.items():
        got = EV.witness_spans(od, wb.get(od, {}), lex)
        for v in sorted(janv):
            sp = got.get(v) or {}
            sc = _score(sp.get("text", ""), refs, v)
            worst = min([x for x in sc.values() if x is not None] or [0.0])
            # THE WORKLIST MUST NOT STOP AT THE BAR when a better reading is already known. S6 v8 cleared 0.90
            # the moment the apparatus filter dropped its `(b)`, which took it OFF the R3 list and silently kept
            # `firmameut ... euenins mornins` in place of the `firmament ... euening morning` a visual read had
            # already established. A passing score is not a reason to keep a worse transcript.
            threshold = max(a.bar, a.improve_below or 0.0)
            known_better = f"{s}:{v}" in VISUAL_CONTENT or f"{s}:{v}" in VISUAL_READINGS
            if worst >= threshold and not known_better:
                continue
            todo.append({"src": s, "ocr_dir": od, "verse": v, "from": sp.get("from"),
                         "old_text": sp.get("text", ""), "old": sc})
    if a.cells:
        want = {tuple(c.split(":")) for c in a.cells.split(",")}
        todo = [t for t in todo if (t["src"], str(t["verse"])) in want]

    print(f"=== RUNG 3 ON THE RESIDUAL — {len(todo)} open cell-groups (bar {a.bar}, governing arm = archaic) ===\n")
    results = []
    for t in todo:
        od, v = t["ocr_dir"], t["verse"]
        # The crop must come from the leaf the incumbent span came from, and from the SAME spans dict that
        # produced it — otherwise the verse we judged bad is not the verse we re-read.
        page_key = (t["from"] or "").lstrip("p")
        janv_all = VS.chapter_verses(EV.BOOK, EV.CHAPTER, VS.JANVIER) or {}
        if page_key.isdigit():
            leaves = [int(page_key)]
        else:
            # A CHAPTER-STREAM SPAN HAS NO SINGLE LEAF, and skipping it is a silent coverage hole (it dropped
            # S1 v9 and S3 v9 on Genesis 16 unexamined). But the leaf must be ASKED FOR, not searched for.
            #
            # A first attempt localized this verse on EVERY cached leaf and took the best janvier fit. That is
            # unsound and it fired immediately: for S1 v9 it chose p80 — a GENESIS 15 leaf — because forcing a
            # chapter-16 grid onto chapter-15 text still yields a span, and a spurious span can out-fit a real
            # one. The crop came back reading `the birdes he diuided not ... a deepe sleepe fel vpon Abram`,
            # which is Genesis 15:10-12. A fit score cannot tell "this verse is here" from "something matched".
            #
            # `.corpus-localize-<ocr_dir>.json` already records the leaf each verse was found on, from a run
            # that had the whole book in view. That is evidence about this verse's location rather than a guess
            # derived from the chapter under test, so it is what decides.
            # For a straddling verse the localizer names ONE leaf, but the verse's pixels are on two.
            #
            # DO NOT WIDEN AND THEN PICK BY FIT. That was tried twice and failed twice: first over all cached
            # leaves (it chose a Genesis 15 leaf for 16:9 and transcribed `the birdes he diuided not`), then
            # over the chapter's own leaves ±1 — which chose `pdf-S03a` p84, still Genesis 15, because a
            # spurious span on the wrong leaf can out-fit a truncated real one. A fit score cannot distinguish
            # "the verse is here" from "something matched".
            #
            # The ANCHOR is the localizer's leaf for this verse, full stop. A second leaf is added only on
            # TRUNCATION EVIDENCE: the verse's span on the anchor touches the anchor's first or last body row,
            # which is what a verse continuing off the leaf actually looks like. Direction follows the edge it
            # touches, so the join order is the reading order.
            loc = _localizer_leaf(od, v)
            leaves = _straddle_leaves(od, v, loc, lex, wb) if loc is not None else []
        # A VERSE CAN STRADDLE TWO LEAVES, and then no single crop holds it. Genesis 16:9 begins `And the
        # angel of our Lord said to her: Returne` on p81 and finishes `to thy miſtreſſe, and humble thy ſelfe`
        # on p82; the single-leaf crop returned only the tail, so S1/S3 v9 could not be rescued at all. Each
        # contributing leaf is therefore cropped and transcribed separately and the transcripts are joined in
        # leaf order before localization — the same insight the chapter stream applied to the page model,
        # applied to the pixels.
        parts: list[tuple[int, tuple]] = []
        best_leaf, box, pi, crops = -1.0, None, None, {}
        for cand_pi in leaves:
            pr = _page_result(od, cand_pi, wb[od][str(cand_pi)], lex)
            if not pr["lines"]:
                continue
            spans = verse_locate.best_spans(pr, EV.BOOK, EV.CHAPTER) or {}
            sp2 = spans.get(v) or {}
            if not (sp2.get("text") or "").strip():
                continue
            fit = verse_locate.janvier_fit(sp2["text"], janv_all.get(v))
            cc = verse_geom.verse_crops(pr, EV.BOOK, EV.CHAPTER, spans=spans)
            cb = (cc.get(v) or {}).get("crop")
            if not cb:
                continue
            cb = widen_to_measure(cb, ocr_dir=od, page_index=cand_pi)
            parts.append((cand_pi, cb))
            if fit > best_leaf:
                best_leaf, box, pi, crops = fit, cb, cand_pi, cc
        # Which verses share the cropped band — a fact about the pixels sent, read off the same spans dict.
        own = set((crops.get(v) or {}).get("lines") or [])
        t["neighbours"] = sorted({v} | {w for w, c in crops.items()
                                        if own & set(c.get("lines") or [])})
        if not box:
            t["skip"] = f"no crop geometry; leaves tried: {leaves or 'none (localizer has no leaf for it)'}"
            print(f"  {t['src']} v{v}: SKIP ({t['skip']})")
            results.append(t)
            continue
        t["crop"] = [round(x, 4) for x in box]
        t["crop_page"] = pi
        print(f"  {t['src']} v{v}  p{pi}  crop {t['crop']}  incumbent gov {_governing(t['old']):.3f}")
        if a.dry_run:
            results.append(t)
            continue
        try:
            chunks = []
            for lp, lb in parts:
                chunks.append(reocr_r3.r3_transcribe(od, lp, backend="mlx", crop=lb,
                                                     max_tokens=a.max_tokens) or "")
            new = _stitch(chunks)
            if len(parts) > 1:
                t["crop_leaves"] = [lp for lp, _ in parts]
        except Exception as e:                                  # noqa: BLE001
            t["r3_error"] = f"{type(e).__name__}: {e}"
            print(f"      R3 ERROR {t['r3_error']} — cell stays OPEN")
            results.append(t)
            continue
        t["r3_raw"] = (new or "").strip()
        # THE R3 TEXT GOES THROUGH THE SAME TOKEN FILTER AS THE PAGE MODEL. It did not, and a printed verse
        # number `9.` reached the deliverable on S6 v8 — the overlay bypassed `PM.clean_tokens` entirely. Any
        # path that produces deliverable text has to pass the one filter, or the exceptions accumulate silently.
        t["r3_verse"] = trim_span_edges(" ".join(PM.clean_tokens(
            localize_in_crop(t["r3_raw"], v, set(t["neighbours"])).split())), v)
        # THE ſ SURFACE IS RESTORED BY OBSERVATION, NOT BY RULE. olmOCR modernizes ſ->s, so adopting its text
        # raw would trade the diplomatic surface — the whole point of the project — for a content score the
        # gate cannot even see (fold_archaic folds ſ/s). `s_arbiter.transfer` takes R3's CONTENT and R2's
        # OBSERVED spelling wherever the two agree modulo the ſ-fold: R2 (kraken + reichenau_lat) is itself a
        # ſ-faithful visual recognizer, so those glyphs are attested, not invented. Tokens where R3 genuinely
        # CORRECTED R2 have no attested ſ and are itemised as `unresolved` for a visual read — never guessed.
        content = dict(VISUAL_CONTENT.get(f"{t['src']}:{v}") or {})
        by_tok_c = VISUAL_CONTENT_BY_TOKEN.get(f"{t['src']}:{v}") or {}
        if by_tok_c:
            for i, tok in enumerate(t["r3_verse"].split()):
                if tok in by_tok_c:
                    content[i] = by_tok_c[tok]
        if content:
            toks = t["r3_verse"].split()
            for i, word in content.items():
                if 0 <= i < len(toks):
                    toks[i] = word
            t["visual_content"] = {str(k): x for k, x in content.items()}
            t["r3_verse"] = " ".join(toks)
        # The merged arm is offered ALONGSIDE the plain R3 arm, and whichever scores better on the governing
        # references is the candidate. The merge can only help where an arm dropped tokens; where it would hurt
        # (a conflict resolved the wrong way) the plain arm still wins on its own merits.
        merged, t["arm_conflicts"] = merge_arms(t["old_text"], t["r3_verse"])
        if _governing(_score(merged, refs, v)) > _governing(_score(t["r3_verse"], refs, v)):
            t["used_merge"] = True
            t["r3_verse"] = merged
        arb = s_arbiter.transfer(t["old_text"], t["r3_verse"])
        readings = dict(VISUAL_READINGS.get(f"{t['src']}:{v}") or {})
        lex_ix: set[int] = set()
        by_tok = VISUAL_READINGS_BY_TOKEN.get(f"{t['src']}:{v}") or {}
        if by_tok:
            for i, tok in enumerate(t["r3_verse"].split()):
                if tok in by_tok:
                    readings[i] = by_tok[tok]
        # Only tokens the arbiter actually holds OPEN can be arbitrated — it raises on anything else, and
        # rightly: a reading offered for an already-attested token would be overriding an observation with
        # another observation, silently. `transfer` may resolve a token this table also covers.
        unres_ix = {u["i"] for u in (arb.get("unresolved") or []) if isinstance(u, dict) and "i" in u}
        # ATTESTED-LEXICON CLOSURE (§13 Q40, 2026-07-29). Where R2 dropped or badly misread a word, R3's token
        # has no observation to inherit and the cell stayed OPEN — on genesis 2 that held 19 of 25 verses with
        # debts like `2 unresolved: therefore, seventh`. `s_lexicon` answers such a token from the HUMAN ground
        # truth of the same EDITION (2,611 hand-transcribed lines), and only where those transcriptions are
        # overwhelmingly consistent: measured 403/403 = 1.0000 on held-out GT files while REFUSING 75% of tokens.
        # It is not `long_s_rule.restore_long_s` (a positional guess, ~0.904 — one invented glyph in ten): it
        # refuses display capitals outright (there is no capital ſ) and refuses the `sh` cluster, which the
        # guidelines state is set both ways within one page. Provenance is recorded separately from
        # `R2-observed` so every lexicon closure is auditable and can be ablated with ODR_S_LEXICON=0.
        if S_LEXICON:
            ed = _EDITION_OF.get(t.get("ocr_dir") or "")
            if ed:
                lex_hits = {}
                for i, tok in enumerate(t["r3_verse"].split()):
                    if i in readings or i not in unres_ix:
                        continue
                    core = tok.strip(" \t.,;:·†‡*()[]?!")
                    if not core or ("s" not in core.lower() and "ſ" not in core):
                        continue
                    form, _ev = s_lexicon.decide(_s_lex_table(), ed, core)
                    if form and form != core:
                        lex_hits[i] = tok.replace(core, form)
                if lex_hits:
                    readings.update(lex_hits)
                    lex_ix |= set(lex_hits)
                    t["lexicon_readings"] = {str(k): x for k, x in lex_hits.items()}
        # The fallback below is for HAND-SET readings only, whose indices are absolute. It must NOT widen the
        # window for lexicon hits: `arbitrate` raises on a token that is not open, and with the fallback in place
        # a verse with NOTHING unresolved accepted lexicon readings and aborted the whole chapter's R3 with
        # `KeyError: token 1 is not unresolved` (genesis 33, rc=1 — every adoption in that run lost).
        wide = unres_ix or set(range(len(arb.get("text", "").split())))
        readings = {i: w for i, w in readings.items()
                    if i in (unres_ix if i in lex_ix else wide)}
        if readings:
            arb = s_arbiter.arbitrate(arb, readings)
            t["visual_readings"] = {str(k): x for k, x in readings.items()}
        t["new_text"] = arb["text"]
        t["s_unresolved"] = [u.get("token") if isinstance(u, dict) else u
                             for u in (arb.get("unresolved") or [])]
        t["s_verdict"] = s_arbiter.verdict(arb, t["old_text"]).get("state")
        t["new"] = _score(t["new_text"], refs, v)
        og, ng = _governing(t["old"]), _governing(t["new"])
        # ADOPTION REQUIRES THE ſ SURFACE, NOT JUST THE CONTENT. Genesis 1 hid this: all six of its rescues
        # closed their surface, so content-only adoption looked sufficient. Genesis 16 adopted 12 cells of which
        # ELEVEN carried surface debt (`shal`, `she`, `mistresse.`, `doest`, `vnjustly`, ...) and the matrix
        # still reported them as passing. A diplomatic transcription with an unattested surface is not a passing
        # cell — it is a cell with a debt, and the debt has to block. So a cell now clears only when the content
        # beats the incumbent AND clears the bar AND `s_arbiter` closes the surface with nothing unresolved.
        content_ok = bool(ng >= a.bar and ng > og)
        surface_ok = t.get("s_verdict") == "CLOSED" and not t.get("s_unresolved")
        t["adopt"] = bool(content_ok and surface_ok)
        t["verdict"] = ("ADOPT" if t["adopt"] else
                        f"CONTENT OK, ſ-SURFACE {t.get('s_verdict')} — read the crop (stays OPEN)"
                        if content_ok else
                        "BETTER-BUT-SHORT (stays OPEN)" if ng > og else "NO-GAIN (stays OPEN)")
        print(f"      R3 gov {ng:.3f} vs {og:.3f}  -> {t['verdict']}")
        print(f"      R3 verse: {t['new_text'][:130]}")
        print(f"      ſ-surface: {t['s_verdict']}  ({t['new_text'].count(chr(0x17F))} ſ kept, "
              f"{len(t['s_unresolved'])} unresolved{': ' + ', '.join(map(str, t['s_unresolved'][:6])) if t['s_unresolved'] else ''})")
        print(f"      incumbent: {t['old_text'][:130]}")
        results.append(t)

    residual_path().write_text(json.dumps(results, ensure_ascii=False, indent=1))
    if not a.dry_run:
        store = json.loads(ADOPTED.read_text()) if ADOPTED.exists() else {}
        for r in results:
            if r.get("adopt"):
                store[f"{r['src']}:{r['verse']}"] = {
                    "text": r["new_text"], "backend": "mlx/olmOCR-2", "crop": r.get("crop"),
                    "page": r.get("from"), "gov_before": _governing(r["old"]), "gov_after": _governing(r["new"]),
                    "s_verdict": r.get("s_verdict"), "s_unresolved": r.get("s_unresolved")}
        ADOPTED.write_text(json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True))
        print(f"\nadopted store -> {ADOPTED.name} ({len(store)} cells)")
    if not a.dry_run:
        adopted = [r for r in results if r.get("adopt")]
        partial = [r for r in results if r.get("new") and not r.get("adopt")
                   and _governing(r["new"]) > _governing(r["old"])]
        print(f"\n=== {len(adopted)} cleared · {len(partial)} improved but still short · "
              f"{len(results) - len(adopted)} STILL OPEN and blocking ===")
        for r in results:
            if not r.get("adopt"):
                print(f"  OPEN  {r['src']} v{r['verse']}  gov {_governing(r['old']):.3f}"
                      + (f" -> {_governing(r['new']):.3f}" if r.get("new") else "")
                      + (f"  [{r.get('skip') or r.get('r3_error') or ''}]" if r.get("skip") or r.get("r3_error") else ""))
    reocr_r3.shutdown_mlx()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
