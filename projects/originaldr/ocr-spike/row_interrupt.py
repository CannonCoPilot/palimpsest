#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""row_interrupt.py — separate interleaved apparatus by CONTENT AND SEQUENCE, not geometry (2026-07-29).

SEVEN GEOMETRIC ATTEMPTS HAVE NOW FAILED at this, and the residual they leave is the campaign's largest OCR
class. All ten open cells of genesis 12 are `jp2-S06` carrying left-column annotation words merged into body
rows:

    `and out of thy kindred`     arrives as  `and trie and out of thy kindred`
    `therfore went out as ...`   arrives as  `borne of therfore went out as ...`
    `And from thence to a ...`   arrives as  `And dicated on from thence to a ...`
    `and Abram deſcended into`   arrives as  `and Abtam deſcen- pron bencfits. Egypt`

Why geometry cannot do it, measured tonight: S6's word-start histogram over 21 leaves has the annotation column
at 0.16-0.17 and the body at 0.23-0.24, but a swept left bound HURTS (0.228 costs chapter 1 four cells and halves
chapter 12's S6 rate) because the annotation's LONG lines run right past the body's left edge, so their tails sit
inside the band and kraken merges them into the body row's y-band. The intruder is not at an edge; it is
INTERLEAVED.

THE SIGNATURE THAT DOES SEPARATE THEM. Scripture in a row is a run of tokens that appears IN ORDER in the
chapter's own reference. An interleaved intruder interrupts such a run: remove it and the two fragments either
side become CONTIGUOUS in the reference. A real archaic word never has that property — removing it leaves a gap
where it belongs, so the fragments stay non-adjacent.

    row      `and trie and out of thy kindred`
    ref      `... and out of thy kindred ...`
    `and` matches ref[i], `out of thy kindred` matches ref[i+1..], so `trie` sits between two
    reference-ADJACENT positions -> it interrupts -> apparatus.

WHAT KEEPS THIS OFF THE SCRIPTURE. Three constraints, each answering a way the previous attempts went wrong:
  * The anchor is the ARCHAIC reference (`genesis_tuned.chapter_anchor_set`), not modern janvier. That choice is
    already validated: it cuts archaic-spelling false positives 3,282 -> 838. Anchoring on janvier is what made
    every earlier content filter delete `sone`, `therfore`, `daies`, `citie`.
  * A token is removed ONLY on the interruption test above. Being un-anchored is not sufficient — that is the
    rejected run-length rule, which deleted the hyphen-split `a fir. ment` out of *firmament*.
  * At most `MAX_PER_ROW` tokens leave a row, and never the row's whole content. A row needing more than that is
    reported, not silently emptied.

MEASURED AND REJECTED — DEFAULT OFF, AND IT MUST STAY OFF (2026-07-29). It deletes scripture:

    chapter    1     16    12     2     38    17
    OFF      124/124 64/64 43/80 84/100 84/120 88/108
    ON       107/124 60/64 35/80 76/100 62/120 68/108

WHY IT FAILS, which is the part worth keeping. The criterion "the remainder matches a reference n-gram" is
satisfied by shifting PAST A MISREAD WORD: where the row's first token is an OCR error, k=0 finds no n-gram and
k=1 does, so the filter deletes the error — and with it real scripture — instead of keeping it. A diplomatic
transcription must preserve a misread for a later rung to correct; a filter that tidies it away is worse than the
misread.

AND A LESSON ABOUT HOW IT WAS ALMOST ADOPTED. Its three hand-checked examples all worked, and all three were
drawn from FAILING cells — precisely the rows where stripping helps. Examples chosen from the residual will
always flatter a fix aimed at the residual. The verdict came only from measuring the whole population, chapters
1 and 16 included, where the cost is visible.

Kept in the tree, wired but off, because the ANCHOR insight underneath it is still sound (archaic reference, not
janvier) and a later attempt should start from the negative result rather than rediscover it. This is the EIGHTH
failed attempt to separate this apparatus — seven geometric, this one on content — and the honest current answer
is that the interleaved left column is fixed by R3 re-reading the printed crop, not by filtering the row.
"""
from __future__ import annotations

import difflib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ENABLED = os.environ.get("ODR_ROW_INTERRUPT", "0") != "0"
MAX_PER_ROW = 3
_CACHE: dict[tuple[str, int], list[str]] = {}


def _fold(t: str) -> str:
    import genesis_tuned as GT
    return GT.gfold(t)


def reference_stream(book: str, chapter: int) -> list[str]:
    """The chapter's ARCHAIC reference as one folded token sequence — the order scripture must appear in."""
    key = (book, chapter)
    if key in _CACHE:
        return _CACHE[key]
    import genesis_tuned as GT
    ref = GT.archaic_reference()
    toks: list[str] = []
    for v in range(1, 200):
        t = ref.get(f"scripture/{book}/{chapter}/{v}")
        if t:
            toks += [_fold(x) for x in t.split() if _fold(x)]
    _CACHE[key] = toks
    return toks


def _bigrams(ref: list[str]) -> set[tuple[str, str]]:
    return {(ref[i], ref[i + 1]) for i in range(len(ref) - 1)}


def _trigrams(ref: list[str]) -> set[tuple[str, str, str]]:
    return {(ref[i], ref[i + 1], ref[i + 2]) for i in range(len(ref) - 2)}


_NG: dict[tuple[str, int], tuple[set, set, set]] = {}


def _ngrams(book: str, chapter: int):
    key = (book, chapter)
    if key not in _NG:
        ref = reference_stream(book, chapter)
        _NG[key] = (set(ref), _bigrams(ref), _trigrams(ref))
    return _NG[key]


def interrupters(row_tokens: list[str], book: str, chapter: int,
                 *, max_per_row: int = MAX_PER_ROW) -> list[int]:
    """Indices of row tokens that INTERRUPT a reference-contiguous run — i.e. interleaved apparatus.

    THE TEST IS LOCAL, NOT A GLOBAL ALIGNMENT, and that is a measured correction. A `difflib` alignment of the
    row against the 528-token chapter stream anchored `and trie and out of thy kindred`'s FIRST `and` to a
    distant `and` (ref[0]) rather than the adjacent one (ref[11]), so the two anchors were 11 apart and the
    interruption was invisible. Global alignment has no reason to prefer the near occurrence; a local n-gram
    test does not need it to.

    A token is apparatus only when ALL of these hold — each one closing a way an earlier filter went wrong:
      1. it is ABSENT from the chapter's entire reference vocabulary. A word the chapter uses anywhere is never
         deleted, which is what keeps archaic forms (`ſone`, `therfore`, `daies`) and real scripture safe.
      2. its NEIGHBOURS form a bigram that the reference actually contains — so removing it joins text the
         chapter really does set contiguously.
      3. the TRIGRAM including it does not appear in the reference — if the chapter sets those three words in
         that order, this token belongs here whatever (1) suggested.
      4. at most `max_per_row` tokens leave a row, and never all of them."""
    if len(row_tokens) < 3:
        return []
    vocab, bigrams, trigrams = _ngrams(book, chapter)
    if not vocab:
        return []
    a = [_fold(t) for t in row_tokens]
    out: list[int] = []
    for i in range(1, len(a) - 1):
        if not a[i] or a[i] in vocab:
            continue
        prev, nxt = a[i - 1], a[i + 1]
        if not prev or not nxt:
            continue
        if (prev, nxt) not in bigrams:
            continue
        if (prev, a[i], nxt) in trigrams:
            continue
        out.append(i)
    if len(out) > max_per_row or len(out) >= len(row_tokens):
        return []
    return out


def leading_intruders(row_tokens: list[str], book: str, chapter: int,
                      *, max_lead: int = MAX_PER_ROW, window: int = 4) -> int:
    """How many tokens at the START of the row are apparatus — the dominant real case.

    ROWS ARE ORDERED BY x, and on `jp2-S06` the annotation column is to the LEFT of the body, so an annotation
    word merged into a body row arrives at the row's HEAD. That is why the single-token interruption test above
    found nothing on the real examples: `and trie and out of thy kindred` has TWO leading intruders (`and trie`),
    and its first `and` is the annotation's own word, so the neighbours of `trie` are `and`/`and` — a bigram the
    reference never sets.

    The test: find the smallest k for which the row's next `window` tokens from k appear as a CONTIGUOUS n-gram in
    the chapter's archaic reference. Real scripture gives k=0, so nothing is stripped from a clean row. A leading
    intruder run gives k>0 and only then are those tokens dropped — the criterion is that what REMAINS matches
    text the chapter actually sets in that order, which is a far stronger claim than "these tokens are
    un-anchored" (the rejected run-length rule)."""
    if len(row_tokens) < window + 1:
        return 0
    _vocab, _bg, _tg = _ngrams(book, chapter)
    ref = reference_stream(book, chapter)
    if len(ref) < window:
        return 0
    grams = {tuple(ref[i:i + window]) for i in range(len(ref) - window + 1)}
    a = [_fold(t) for t in row_tokens]
    for k in range(0, min(max_lead, len(a) - window) + 1):
        if tuple(a[k:k + window]) in grams:
            return k
    return 0


def strip_row(row_tokens: list[str], book: str, chapter: int) -> tuple[list[str], list[str]]:
    """(kept tokens, removed tokens) for one row."""
    ix = set(interrupters(row_tokens, book, chapter))
    k = leading_intruders(row_tokens, book, chapter)
    ix |= set(range(k))
    if not ix:
        return row_tokens, []
    return ([t for i, t in enumerate(row_tokens) if i not in ix],
            [t for i, t in enumerate(row_tokens) if i in ix])
