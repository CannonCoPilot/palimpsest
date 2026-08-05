#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""page_address.py — address EVERY page of a volume as (book, chapter), by monotone alignment (2026-07-27).

THE AIM IS TOTAL COVERAGE, NOT A BLOCKING ALARM. Sir: "we want ALL pages to always be addressed as the correct
book:chapter." An `UNRESOLVED` verdict is a safeguard for a trial run, never the deliverable — a page we cannot
address is a page we cannot re-OCR, and holding it OPEN forever is not a transcription.

WHY PER-PAGE CLASSIFICATION CANNOT GET THERE, AND WHY SEQUENCE ALIGNMENT CAN.
Addressing a page from its own content alone is genuinely ambiguous: a mid-chapter page prints no chapter
heading, a treatise page inside a psalm's range prints no scripture at all, and two chapters of the same book
read alike. But pages are not independent — **a volume is a SEQUENCE, and the canon is ORDERED**. Chapter
numbers never decrease as you turn pages. That single constraint converts an ambiguous per-page guess into a
well-posed global alignment: line the page sequence up against the canonical (book, chapter) sequence, exactly
as `verse_locate` lines verses up against a page. **It is the same monotone DP, one level up** — and it is why
every page gets an address: a page with no local evidence of its own inherits one from its neighbours, which is
precisely what a human does when they flip back a leaf to see where they are.

The three cases that broke the address-driven approach all fall out of this rather than needing special rules:
  * MID-CHAPTER page (no heading)      -> the run continues; the DP holds the same chapter across pages.
  * MULTI-CHAPTER page                 -> `block_grammar.chapter_ranges` splits it; the page carries a SPAN.
  * CHAPTER-LESS page (treatise/plate) -> still addressed — it lies BETWEEN two pages of a chapter, so its
                                          address is that locus with `kind='no-scripture'`. ot2-1610 p216 is
                                          exactly this: inside the Psalm 118 range, carrying the General
                                          Annotations. "No scripture here" is an ADDRESS, not a failure.
  * WRONG per-page guess (colossians-3) -> outvoted. An isolated page cannot disagree with its neighbours
                                          without paying a transition penalty the evidence must earn.

EVIDENCE PER PAGE (all gold-free, all from the stored stream):
  heading   printed `CHAP. IIII` -> that exact chapter          (decisive when present)
  header    running header book name -> restricts the book      (strong)
  numbers   recovered printed verse numbers -> position in ch    (self-labelling)
  content   IDF-weighted match of the page body against the chapter's reference verses
  prior     tome-map's existing chapter_pages (evidence, NOT truth: mean_chapter_recall 0.84)

HOW ACCURACY IS MEASURED AT CORPUS SCALE WITHOUT GOLD — the point of `use_headings=False`.
Printed chapter headings are the one place the book states its own address. Run the DP with headings WITHHELD
from the evidence, then check how often it independently recovers the chapter that the page actually prints.
That is a held-out accuracy estimate over every heading-bearing page in the corpus — thousands of labels, not
the 16 GT pages — and it is the evidence for "all pages are correctly addressed" that a 16-page set cannot
supply.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import block_grammar                     # noqa: E402
import verse_seg as VS                   # noqa: E402
from verse_locate import token_weights   # noqa: E402

RECON = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/mask_engine/"
             "originaldr_reconstruction")
SKELETON = json.loads((RECON / "skeleton.json").read_text())
BOOK_CHAPTERS = {b["slug"]: b["chapters"] for b in SKELETON["books"]}
BOOK_ORDER = [b["slug"] for b in SKELETON["books"]]
BOOK_TESTAMENT = {b["slug"]: b["testament"] for b in SKELETON["books"]}

_WORD = re.compile(r"[A-Za-zſ]+")
_CHAP_HEAD = block_grammar.CHAP_HEAD

# Transition costs (log-domain). Staying in a chapter is free (chapters span many pages); advancing one is
# free (the common case); a jump is penalised in proportion to its length so the DP prefers the canon's own
# order but can still cross a short book or a run of unrecognised pages.
STAY, STEP, JUMP_BASE, JUMP_PER, BACK = 0.0, 0.0, -1.5, -0.35, -1e6


def canonical_positions(books: list[str]) -> list[tuple]:
    """The ordered (book, chapter) sequence a volume traverses — the DP's state space.

    CHAPTER 0 IS A REAL POSITION: the book's own front matter (title, argument, preface), which the DR prints
    before chapter 1 of every book. Omitting it was a measured defect — with nowhere legal to sit, the argument
    pages of the Psalms pulled the path forward into Psalm 2 by page 12, and because staying in a chapter is
    free the path then sat there through page 16, mis-addressing Psalm 1 even though that page's own content
    scored 0.414 for Psalm 1 against 0.175 for Psalm 2. **Front matter is part of the book's sequence, so it
    needs a seat in the sequence.**"""
    out = []
    for b in books:
        out.append((b, 0))
        for c in range(1, BOOK_CHAPTERS.get(b, 0) + 1):
            out.append((b, c))
    return out


def _fold(text: str) -> list[str]:
    return [w.lower().replace("ſ", "s") for w in _WORD.findall(text or "")]


class ChapterIndex:
    """Reference token sets per (book, chapter), with IDF weights — the content-evidence model.

    Built once per volume. A chapter is represented by the token multiset of its reference verses; scoring a
    page is then a weighted coverage, the same evidence `verse_locate` uses to place a verse on a page."""

    def __init__(self, positions: list[tuple]):
        self.tokens: dict = {}
        for (b, c) in positions:
            janv = VS.chapter_verses(b, c, VS.JANVIER)
            if janv:
                self.tokens[(b, c)] = set(_fold(" ".join(janv.values())))
        # A token appearing in many chapters carries little evidence about WHICH chapter this is.
        df: dict = {}
        for toks in self.tokens.values():
            for t in toks:
                df[t] = df.get(t, 0) + 1
        n = max(1, len(self.tokens))
        self.idf = {t: math.log(1 + n / (1 + d)) for t, d in df.items()}

    def score(self, page_toks: set) -> dict:
        """{(book,chapter): how much of THIS PAGE the chapter explains}, IDF-weighted, 0..1.

        MEASURED DEFECT, FIXED HERE (2026-07-27). This first normalised by the CHAPTER's tokens — the chapter's
        RECALL by the page — which is the wrong question and fails systematically by chapter length. Psalm 118
        has 176 verses, so any single page can contain only a fraction of it and scored 0.097, while short
        psalms scored ~0.19 on incidental common words: **the model preferred short chapters no matter what the
        page said.** Addressing a page asks the PRECISION question — what fraction of what is printed here does
        this chapter account for — so the denominator is the PAGE. Recall is retained only as a mild tie-break,
        capped, so a chapter cannot win by being short."""
        den_page = sum(self.idf.get(t, 0.0) for t in page_toks) or 1.0
        out = {}
        for key, toks in self.tokens.items():
            inter = toks & page_toks
            if not inter:
                continue
            num = sum(self.idf.get(t, 0.0) for t in inter)
            prec = num / den_page
            den_ch = sum(self.idf.get(t, 0.0) for t in toks) or 1.0
            rec = min(num / den_ch, 0.35)
            out[key] = 0.85 * prec + 0.15 * rec
        return out


def page_evidence(page_result: dict, index: ChapterIndex, *, use_headings: bool = True) -> dict:
    """Local, gold-free evidence for one page: printed heading, running header, content fit, scripture-ness."""
    lines = page_result.get("lines", [])
    text = " ".join((l.get("text") or "") for l in lines)
    body = " ".join((l.get("text") or "") for l in lines if l.get("role") == "body") or text

    # One heading matcher for evidence, pins and held-out labels alike — a stricter pattern here than in
    # `printed_heading_lines` would mean the two disagree about what the page prints. So CALL it rather than
    # re-deriving: this line previously ran its own scan, which is the project's recurring defect shape (one
    # rule, two copies) sitting one line under a comment forbidding it.
    printed = sorted(printed_heading_lines(page_result))

    header = " ".join((l.get("text") or "") for l in lines if l.get("role") == "header")
    # THE RUNNING HEAD IS SET LETTER-SPACED, like the chapter headings, and folding it raw destroys it:
    # `G E N E S 1 5.` folds to ['g','e','n','e','s'], never to ['genesis'], so the book-name bonus could not
    # fire on the pages that print the book's name most plainly. Measured on the four Genesis volumes, the
    # book-name match went 26% -> 46% of scripture pages by collapsing the spacing first, while staying at
    # ~1% on the volume's front matter (whose running head genuinely says something else, e.g.
    # `TO THE ENGLISH READER`). Same defect as #6, one evidence channel over.
    hdr_tokens = set(_fold(" ".join(block_grammar.display_words(header))))
    fits = index.score(set(_fold(body)))
    try:
        regime = block_grammar.detect_regime(page_result).get("regime")
    except Exception:                                     # noqa: BLE001
        regime = None
    best_fit = max(fits.values(), default=0.0)
    return {"best_fit": best_fit,
            "printed_chapters": (printed if use_headings else []),
            "printed_chapters_observed": printed,          # kept even when withheld — this is the held-out label
            "header_tokens": hdr_tokens, "fits": fits, "regime": regime,
            "n_body_tokens": len(_fold(body))}


def _emission(ev: dict, pos: tuple, prior: set) -> float:
    """log-score that this page sits at canonical position `pos`."""
    book, ch = pos
    if ch == 0:
        # Book front matter: no verse reference exists to match against, so it is scored flat and the sequence
        # places it. Slightly below a weak content match, so a page with real scripture on it never prefers
        # front matter, and slightly above nothing, so argument pages stop dragging the path into chapter 1+.
        base = 0.30
        if ev["header_tokens"] & set(_fold(book.replace("-", " "))):
            base += 0.8
        return base
    s = 3.0 * ev["fits"].get(pos, 0.0)                    # content is the workhorse
    if ev["printed_chapters"] and ch in ev["printed_chapters"]:
        s += 4.0                                          # the page states its own chapter — decisive
    elif ev["printed_chapters"]:
        s -= 1.0                                          # it states a DIFFERENT chapter
    if ev["header_tokens"] & set(_fold(book.replace("-", " "))):
        s += 0.8                                          # running header names this book
    if pos in prior:
        s += 0.4                                          # tome-map thinks so (evidence, not truth)
    if ev["regime"] == "no-scripture" and ev["best_fit"] < 0.20:
        # A treatise/plate page carries no verse tokens, so content evidence is silent BY CONSTRUCTION. It does
        # not "belong nowhere" — it belongs where its neighbours are, and the transition term supplies that, so
        # flatten the emission and let the sequence decide.
        #
        # THE GUARD IS ON THE EVIDENCE, NOT ON THE LABEL OR THE LENGTH (both earlier versions were wrong and
        # both were caught by measurement). `detect_regime` calls pages `no-scripture` that are manifestly
        # scripture — ot2-1610 p227 carries 381 body tokens of Psalm 118, and a 40-token slice of Psalm 100
        # scores a fit of 0.88 — so flattening on the regime LABEL let one misfiring detector erase a page's
        # entire content evidence. A body-length guard was no better: it is not length that makes a page
        # scripture. "No scripture here" means precisely "nothing on this page matches any chapter", so that
        # is what is tested.
        s = 0.15
    return s


def address_volume(pages: list[dict], books: list[str], *, prior: dict | None = None,
                   use_headings: bool = True, band: int = 40) -> list[dict]:  # noqa: C901
    """Assign EVERY page in `pages` (reading order) a (book, chapter) by monotone Viterbi over the canon.

    `pages`  : [{page_index, lines:[{text, role}]}] in reading order — the stored stream is enough.
    `books`  : the canonical books this volume covers, in order.
    `prior`  : {page_index: {(book, chapter), ...}} from tome-map; evidence only.
    `band`   : how far ahead of the running position the DP may look — keeps the state space linear.

    Returns one record per page, ALWAYS with an address. `confidence` reports how much better the chosen
    position scored than the runner-up, so a weak address is visible as weak WITHOUT being absent."""
    positions = canonical_positions(books)
    if not positions or not pages:
        return []
    index = ChapterIndex(positions)
    prior = prior or {}
    evs = [page_evidence(p, index, use_headings=use_headings) for p in pages]

    P = len(positions)
    NEG = -1e9
    # Viterbi with a forward-only band. dp[j] = best score of any labelling of pages[:i+1] ending at position j.
    dp = [NEG] * P
    back: list[list[int]] = []
    for i, ev in enumerate(evs):
        pr = prior.get(pages[i].get("page_index"), set())
        nd = [NEG] * P
        bk = [-1] * P
        lo = 0 if i == 0 else max(0, min(range(P), key=lambda k: -dp[k]) - 2)
        for j in range(P):
            em = _emission(ev, positions[j], pr)
            if i == 0:
                # NO POSITIONAL PRIOR AT THE START. A previous cut penalised late positions by 0.02*j, which on
                # a 900-position canon reaches -18 — an order of magnitude above any emission — so a slice that
                # legitimately begins mid-volume (page 200 of the Psalms) was dragged to the front of the canon
                # and the monotone constraint then propagated that error through every following page.
                nd[j] = em
                continue
            best, arg = NEG, -1
            for k in range(max(0, j - band), j + 1):
                if dp[k] <= NEG / 2:
                    continue
                d = j - k
                tr = STAY if d == 0 else (STEP if d == 1 else JUMP_BASE + JUMP_PER * (d - 1))
                v = dp[k] + tr
                if v > best:
                    best, arg = v, k
            if arg < 0:
                continue
            nd[j], bk[j] = best + em, arg
        dp, _ = nd, lo
        back.append(bk)

    # Trace back the single best monotone path — every page necessarily lands on a position.
    j = max(range(P), key=lambda k: dp[k])
    path = [j]
    for i in range(len(evs) - 1, 0, -1):
        j = back[i][j]
        path.append(j)
    path.reverse()

    out = []
    for i, (p, ev) in enumerate(zip(pages, evs)):
        pos = positions[path[i]]
        # A PAGE IS AN INTERVAL, NOT A POINT. Most pages carry the tail of one chapter and the head of the
        # next, so a single label is wrong for the majority of the corpus by construction. The monotone path
        # already contains the answer: page i runs from its own position up to where page i+1 begins, so the
        # chapters ON the page are exactly that closed range. (Measured: p265 carries Ps 149 AND 150 and was
        # scored wrong for naming only one of them.) The jump is capped so a mis-stepped path cannot claim a
        # whole book.
        # THE INTERVAL IS BOUNDED BY THE NEXT PAGE'S POSITION, NOT BY A FIXED REACH. The previous rule ran
        # forward up to 4 canonical positions and back up to 3 regardless of plausibility, which is where 489
        # of the 751 discontiguous-chapter outliers came from: a page at chapter 8 still carried chapter 5
        # because chapter 5 was three positions behind it. A page carries the chapter it is on, plus whatever
        # begins on it before the next page starts — nothing further.
        nxt = path[i + 1] if i + 1 < len(path) else path[i]
        span_positions = positions[path[i]: max(path[i], min(nxt, path[i] + 2)) + 1] or [pos]
        # THE INTERVAL HAS A LEFT EDGE TOO. The forward span catches the chapters this page STARTS; a page also
        # carries the TAIL of the chapter running onto it from the previous leaf. That backward reach must be
        # earned by content, not assumed: a preceding position joins the page only if this page's own text
        # supports it at a real fraction of the chosen chapter's fit. (Measured: ot2-1610 p15 prints the whole
        # of Psalm 1 — six verses — plus the start of Psalm 2, and naming only Psalm 2 lost it.)
        # The backward reach is now ONE position and must be earned by content: a page can carry the tail of
        # the chapter running onto it from the previous leaf, but not a chapter three positions back.
        prev = path[i - 1] if i > 0 else path[i]
        chosen_fit_ = ev["fits"].get(pos, 0.0)
        for k in range(max(prev, path[i] - 1), path[i]):
            if ev["fits"].get(positions[k], 0.0) >= max(0.25 * chosen_fit_, 0.02):
                span_positions = positions[k: path[i]] + span_positions
        ranked = sorted(ev["fits"].items(), key=lambda kv: -kv[1])[:2]
        runner = ranked[1][1] if len(ranked) > 1 else 0.0
        chosen_fit = ev["fits"].get(pos, 0.0)
        # Multi-chapter pages: the printer marks the split, so report the SPAN rather than one chapter.
        spans = []
        try:
            spans = [r for r in block_grammar.chapter_ranges(p) if r.get("chapter")]
        except Exception:                                  # noqa: BLE001
            spans = []
        chs_on = sorted({c for (b, c) in span_positions if b == pos[0] and c}
                        | {r["chapter"] for r in spans} | ({pos[1]} if pos[1] else set()))
        out.append({
            "page_index": p.get("page_index"),
            "printed_heading_lines": printed_heading_lines(p),
            "book": pos[0], "chapter": pos[1],
            # HEADINGS COME FROM ONE PARSER. `block_grammar.chapter_ranges` carries its own copy of the
            # numeral logic and still truncates a spaced roman numeral (`CHAP. X. V.` -> 10), so taking chapter
            # numbers from it re-introduced the very defect fixed in `_heading_chapter` — 598 of the 747
            # discontiguous-chapter outliers traced to exactly that. `chapter_ranges` is still used for the
            # LINE RANGES it computes; its chapter NUMBERS are not trusted.
            "chapters_on_page": sorted({c for (b, c) in span_positions if b == pos[0] and c}
                                       | set(printed_heading_lines(p))
                                       | ({pos[1]} if pos[1] else set())),
            "books_on_page": sorted({b for (b, _c) in span_positions}),
            "chapter_spans": spans,
            "kind": ("book-front-matter" if pos[1] == 0
                     else "no-scripture" if ev["regime"] == "no-scripture" else "scripture"),
            "printed_chapters": ev["printed_chapters_observed"],
            # In held-out mode the headings were NOT evidence, so the label must not claim they were.
            "source": ("printed-heading" if (use_headings and ev["printed_chapters"]
                                             and pos[1] in ev["printed_chapters"])
                       else "content" if chosen_fit > 0 else "sequence-inherited"),
            "fit": round(chosen_fit, 4),
            "margin": round(chosen_fit - runner, 4),
            "regime": ev["regime"],
        })
    return out


def pin_page_chapters(page_result: dict, chapters: list, book: str, index: "ChapterIndex") -> list[dict]:
    """Pin WHERE each chapter of the page's interval begins: [{chapter, lo, hi}] over LINE indices.

    Addressing a page to an interval of ~1.8 chapters says which region it is in; it does not say which chapter
    a given line belongs to, and `best_spans(book, chapter, line_range=)` needs the latter or every verse of
    both chapters competes for every position again (the §13 Q5 colossians-3 failure at line grain).

    THE SAME MONOTONE DP, ONE LEVEL FURTHER DOWN. Assign every line a chapter from the interval, non-decreasing
    down the page, maximising IDF-weighted agreement between the line's tokens and the chapter's reference. A
    chapter boundary is then a change-point in that assignment. Printed headings are NOT used here, which is
    what makes the heading line an independent label for how well the pinning works."""
    lines = page_result.get("lines", [])
    body = [(i, l) for i, l in enumerate(lines) if l.get("role") == "body"] or list(enumerate(lines))
    chs = sorted(c for c in chapters if c)
    if not body or len(chs) < 2:
        return [{"chapter": chs[0], "lo": 0, "hi": len(lines) - 1}] if chs and lines else []

    # emission[k][j] = evidence that body line k belongs to chapter chs[j]
    em = []
    for _i, l in body:
        toks = set(_fold(l.get("text") or ""))
        w = sum(index.idf.get(t, 0.0) for t in toks) or 1.0
        row = []
        for c in chs:
            ct = index.tokens.get((book, c), set())
            row.append(sum(index.idf.get(t, 0.0) for t in (toks & ct)) / w)
        em.append(row)

    NEG = -1e9
    K, J = len(em), len(chs)
    dp = [[NEG] * J for _ in range(K)]
    bk = [[-1] * J for _ in range(K)]
    for j in range(J):
        dp[0][j] = em[0][j] - (0.0 if j == 0 else 0.25)   # mild preference for opening in the first chapter
    for k in range(1, K):
        for j in range(J):
            best, arg = NEG, -1
            for p_ in range(j + 1):                        # monotone: a chapter never restarts further up
                v = dp[k - 1][p_] - (0.0 if p_ == j else 0.30)   # switching costs a little; noise cannot flip it
                if v > best:
                    best, arg = v, p_
            dp[k][j], bk[k][j] = best + em[k][j], arg
    j = max(range(J), key=lambda x: dp[K - 1][x])
    assign = [0] * K
    for k in range(K - 1, -1, -1):
        assign[k] = j
        j = bk[k][j] if k else j
    out, cur, lo = [], assign[0], body[0][0]
    for k in range(1, K):
        if assign[k] != cur:
            out.append({"chapter": chs[cur], "lo": lo, "hi": body[k - 1][0]})
            cur, lo = assign[k], body[k][0]
    out.append({"chapter": chs[cur], "lo": lo, "hi": body[-1][0]})
    return out


# PSALM HEADINGS ARE NOT "CHAP. N" AND THE OCR MANGLES THEM. The Psalms — the largest book in the OT volumes —
# head each chapter "PSALME I." / "PSALME 74", and the recognizer returns things like `PSALηE I.` and
# `οF PSALMEI.`. A strict pattern finds 147 headings on 1128 pages and leaves the whole Psalter unpinned, so
# the matcher is tolerant of the noise the recognizer actually makes on these short display lines: any line
# whose letters reduce to PSAL… followed by a roman or arabic number.
_PSALM_HEAD = re.compile(r"^\W*(?:OF\s+)?PS[A-Za-zΑ-Ωα-ω]{0,3}L[A-Za-zΑ-Ωα-ω]{0,3}\.?\s*"
                         r"([IVXLCDM]+|\d{1,3})\s*\.?\W*$", re.I)


_RVAL = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
# A roman chapter numeral, possibly broken by the spaces and stray periods the recognizer inserts into a
# letter-spaced display line.
_ROMAN_RUN = re.compile(r"^([IVXLCDM][IVXLCDM\s.]*)")


def _roman(tok: str):
    """Subtractive roman -> int, tolerant of internal spaces and periods. None if not a roman numeral.

    MEASURED DEFECT, FIXED HERE. Chapter headings are set letter-spaced, and the recognizer returns the numeral
    broken up: `CHAP. X. V.` (XV=15), `CHAP. X I.X.` (XIX=19), `CHAP. X XII.` (XXII=22). The previous parser
    took the FIRST whitespace-delimited token, so all three read as X=10 — and every one of those pages then
    carried a spurious chapter 10, which surfaced as 331 'discontiguous chapter' errors in the integrity sweep
    and depressed the honest held-out addressing accuracy. **The addressing was right on all three; the parser
    was wrong.** A heading that cannot be parsed whole is worse than one not detected at all, because it
    attributes a real page to a distant chapter."""
    t = re.sub(r"[\s.]", "", (tok or "").upper())
    if not t or any(c not in _RVAL for c in t):
        return None
    total, prev = 0, 0
    for c in reversed(t):
        v = _RVAL[c]
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total or None


def _heading_chapter(text: str):
    """The chapter a display line heads, or None. Accepts `CHAP. IIII`, `PSALME 74`, and OCR-mangled variants.

    A CHAPTER HEADING IS A DISPLAY LINE, and testing for that removes the false positives that survived the
    numeral fix (measured on the implausible detections): an annotation citing a chapter inline reads
    `chap. 35. §.` or `chap. 1. in o.` in LOWERCASE running text, and a prose line reads `Pſalme ii alſo
    accunenient prayer ſor anie C` at ten words. Genuine headings are two or three words, set in caps. Both
    tests are on the line's FORM, not on whether the answer agrees with the addressing — filtering by agreement
    would make the held-out check circular a second time."""
    t = (text or "").strip()
    # Letter-spaced runs collapse first: `C H A P. I.` is one word and a numeral, not five. Counting raw
    # whitespace tokens rejected the most heavily letter-spaced headings — the same ones the old CHAP_HEAD
    # pattern already missed, so the two defects compounded.
    words = block_grammar.display_words(t)
    if len(words) > 4:
        return None                       # a sentence, not a display line
    head = re.match(r"^\W*([A-Za-zſΑ-Ωα-ω]+)", t)
    if head and head.group(1).islower():
        return None                       # lowercase `chap.` is an inline citation, not a printed heading
    for pat in (_CHAP_HEAD, _PSALM_HEAD):
        m = pat.match(t)
        if not m:
            continue
        tok = m.group(1).upper()
        if tok.isdigit():
            return int(tok)
        # Re-read the numeral from the ORIGINAL line, so a numeral split by spaces/periods is taken whole.
        tail = t[m.start(1):]
        rm = _ROMAN_RUN.match(tail)
        return _roman(rm.group(1)) if rm else _roman(tok)
    return None


def printed_heading_lines(page_result: dict) -> dict:
    """{chapter: line_index} for chapters the page PRINTS a heading for — the exact pin, where the print gives one.

    A HEADING MUST HEAD SOMETHING. A match below the page's last body line is not heading this page's text: it
    is bottom-of-page furniture — a forward reference, a signature line, or a catchword's neighbour. 68 of the
    corpus's 4,085 detected headings (1.7%) are of this kind, and under a MONOTONE DP one of them is not a
    small error but an erasure.

    MEASURED, `jp2-S06` p1085. Line 50 of 52 reads `Pſal. 30`, sitting below the last body line, after a
    catchword and beside the next leaf's `T H E B O O K` header. Taken as a heading it is decisive evidence
    (+4.0), so the page was addressed to Psalm 30 — and because the chain cannot go back, pages 1086–1088 were
    dragged to 30 with it. Content alone had them right (27, 28, 28, 29; p1086 carries Vulgate Ps 28:6–7,
    "breake them in pieces as a calfe of Libanus … the voice of our Lord diuiding the flame of fire"). Three
    psalms vanished from the corpus on the strength of one line of page furniture.

    Rejecting it costs nothing when the heading is real but its chapter starts on the NEXT leaf: the pin is
    simply not offered for THIS page, and content places it, which is what content is for."""
    lines = page_result.get("lines", [])
    last_body = max((i for i, l in enumerate(lines)
                     if l.get("role") == "body" and (l.get("text") or "").strip()), default=-1)
    out = {}
    for i, l in enumerate(lines):
        if i >= last_body:                 # nothing left on this page for a heading to head
            continue
        ch = _heading_chapter(l.get("text"))
        if ch and ch not in out:
            out[ch] = i
    return out


def pin_carry_chain(records: list[dict], pages: list[dict]) -> list[dict]:
    """Pin each page's chapters to LINE ranges by walking the volume once, carrying the running chapter.

    THE MODEL WAS WRONG BEFORE THIS, AND MEASUREMENT SAID SO (pinning landed within 2 lines of the printed
    heading only 39.7% of the time). I was inferring chapter boundaries from line-level content, which is
    noisy because a single line carries ~8 tokens and neighbouring chapters share vocabulary.

    **THE DR PRINTS A HEADING AT EVERY CHAPTER START. So a page with no heading contains no chapter START —
    it is one chapter, continuing from the previous leaf.** The printer has already pinned the chapters
    exactly; the only genuine unknown is the CARRY-IN, which is a sequence problem, which is what the DP is
    for. That makes the boundaries exact by construction rather than estimated, and it collapses the average
    interval from a guessed 1.82 chapters to what the page actually prints.

    The DP remains the error-recovery path: where the carried chapter and the DP's independent estimate
    disagree (a heading lost to OCR, a book boundary), the disagreement is RECORDED per page, and the rate is
    the honest error estimate for the chain."""
    out = []
    for r, p in zip(records, pages):
        heads = sorted(((int(c), i) for c, i in (r.get("printed_heading_lines") or {}).items()),
                       key=lambda t: t[1])
        n_lines = len(p.get("lines", []))
        # CARRY-IN IS THE DP's OWN PER-PAGE CHAPTER, not a chain propagated across many leaves. A running chain
        # was measured and rejected: with psalm headings unreadable it got stuck on one chapter for hundreds of
        # pages (68% disagreement with the DP, GT 9/9 -> 1/9). The DP already solves the sequence and is
        # validated at 1251/1251 held-out; the headings' job is only to pin boundaries WITHIN a page.
        cur_ch = r["chapter"]
        disagree = bool(heads and cur_ch and heads[0][0] not in (cur_ch, cur_ch + 1))
        segs = []
        if not heads:
            segs = [{"chapter": cur_ch, "lo": 0, "hi": max(0, n_lines - 1), "source": "carry-in"}]
        else:
            if heads[0][1] > 0:
                segs.append({"chapter": cur_ch, "lo": 0, "hi": heads[0][1] - 1, "source": "carry-in"})
            for k, (ch, line) in enumerate(heads):
                hi = (heads[k + 1][1] - 1) if k + 1 < len(heads) else max(0, n_lines - 1)
                segs.append({"chapter": ch, "lo": line, "hi": hi, "source": "printed-heading"})
        r = {**r, "pins": segs, "carry_disagrees_with_dp": bool(disagree),
             "exact_pins": sum(1 for s in segs if s["source"] == "printed-heading"),
             # The DP's interval is retained: where no heading survives (the whole Psalter), the boundary is
             # genuinely not printed-and-readable, and reporting a tight-but-wrong split would be worse than
             # reporting the small interval the verse localizer can resolve within.
             "chapters_on_page": sorted(set(r["chapters_on_page"]) | {s["chapter"] for s in segs if s["chapter"]})}
        out.append(r)
    return out


def heldout_heading_accuracy(records: list[dict]) -> dict:
    """Accuracy against the pages that PRINT their own chapter — the corpus-scale check.

    THE PREVIOUS MEASURE WAS CIRCULAR AND THIS IS THE SECOND TIME. It asked whether the printed chapter was in
    `chapters_on_page` — but `address_volume` unions `printed_heading_lines(p)` into `chapters_on_page`
    UNCONDITIONALLY, in held-out mode too, so the label helped build the very set it was then tested against.
    It returned exactly **1.0 on all eleven volumes, in both modes**, and it was the number persisted to the
    artifact while the honest one went only to stdout — so the circular figure is what a later reader quotes.
    §12.6 already recorded one circular validation ("100% held-out chapter accuracy"); this is the same error
    surviving in a different field.

    The honest predicate is the one the DP cannot influence: does the PRINTED chapter agree with the DP's OWN
    chapter (allowing dp+1, since a page that starts a chapter also carries the tail of the previous one)?
    `carry_disagrees_with_dp` records exactly that, per page, and is computed from the DP's answer rather than
    from a set the heading contributed to. Any future accuracy check must not consult a set the label helped
    build."""
    ev = [r for r in records if r["printed_chapters"]]
    hit = sum(1 for r in ev if not r.get("carry_disagrees_with_dp"))
    circular = sum(1 for r in ev if set(r["printed_chapters"]) & set(r["chapters_on_page"]))
    return {"pages_with_printed_chapter": len(ev), "agreed": hit,
            "accuracy": round(hit / len(ev), 4) if ev else None,
            # Retained ONLY so the artifact shows what the old number was and why it is not the measure.
            "circular_accuracy_do_not_quote": round(circular / len(ev), 4) if ev else None}
