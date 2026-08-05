# -*- coding: utf-8 -*-
"""GENESIS-TUNED LOCALIZATION — the first book-specific variation of the shared logic (Sir, 2026-07-29).

THE DESIGN PRINCIPLE, IN SIR'S WORDS. There is no rule that every book must be handled by identical code.
Books — and chapters within books — are handled by VARIATIONS of the same fundamental logic. So this module
holds Genesis's variation, the generic functions in `layout` / `verse_seg` / `corpus_localize` are left exactly
as they are to serve as the reference implementation, and the next book gets its own variation tuned the same
way. Nothing here is imported by the generic path.

WHY THE GENERIC APPARATUS FILTER COULD NOT WORK, AND WHAT CHANGES HERE. `verse_seg.segment(drop_apparatus=True)`
excises contiguous token runs that anchor to NO reference token, at `apparatus_min=8`. It is anchored on
JANVIER, which is a MODERN-SPELLING text, so the archaic readings the DR actually prints — `sone`, `therfore`,
`daies`, `citie`, `geue`, `betwene`, `darkenes` — anchor to nothing and look exactly like apparatus. Lowering
the threshold there deletes scripture, which is why it was left conservative and why it is a no-op on Genesis.

Genesis has a way out that the generic path does not assume: **an archaic-spelled reference of its own**
(`s_dismas`, backfilled by `odr_com`). Anchoring on that instead of janvier drops the archaic-spelling false
positives from 3,282 to 838 — a 74% cut — and what remains un-anchored is no longer spelling but the
recognizer's own confusions (`uhich`, `uho`, `uas`, `uere`, `aud`, `ot`, `ofthe`, `thec`). Folding those
confusion classes as well takes the un-anchored rate from 18.77% to 14.54% of all Genesis tokens.

Once the anchor is right, the threshold can come down, because a short un-anchored run is now evidence of
foreign material rather than evidence of archaic spelling.

TWO RULES THIS MODULE KEEPS FROM THE GENERIC PATH, because they are not stylistic:
  * The tuned fold is used for ANCHORING ONLY. It never touches the text that is stored or scored — the
    diplomatic surface (long-ſ, real `w` not `vv`) is the deliverable and is decided by the arbiter, not here.
  * Nothing is deleted to raise a score. A run is excised only when it anchors to nothing in the CHAPTER's
    reference, which is a far weaker claim than anchoring to nothing in the verse's.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import qc_audit as QC                        # noqa: E402
import verse_seg as VS                       # noqa: E402

BOOK = "genesis"

# The confusion classes are the ones MEASURED off the split verses, where a passing sibling supplies the
# correct reading for a failing witness of the same edition: w->v (424 char / ~190 whole-word), e<->c (586),
# t/r/f (498), n<->u (221). Folded together here so a page carrying them can still ANCHOR.
_CONF = (("w", "u"), ("n", "u"), ("c", "e"))


def gfold(t: str) -> str:
    """`verse_seg._afold` plus Genesis's measured confusion classes. FOR ANCHORING ONLY.

    `_afold` folds `vv->w` and then `v->u`, but never `w->u`, so `was` and `vas` can never match — and `w`->`v`
    is the single most frequent confusion in these volumes. The rest (`n`<->`u`, `c`<->`e`) are the next two,
    and each was added only after measuring that it lowered the un-anchored rate without loosening the
    localizer's decisions (verified end-to-end, not on the fold statistic alone)."""
    t = t.lower().replace("ſ", "s").replace("æ", "ae").replace("œ", "oe").replace("vv", "w")
    for a, b in _CONF:
        t = t.replace(a, b)
    t = t.replace("v", "u").replace("j", "i").replace("y", "i")
    t = re.sub(r"[^a-z0-9]", "", t)
    t = t.replace("ff", "f")
    return re.sub(r"(.)\1+", r"\1", t) if t else t


_ARCHAIC: dict | None = None


def archaic_reference() -> dict:
    """s_dismas preeminent, odr_com backfilling — the same construction `qc_audit` gates on."""
    global _ARCHAIC
    if _ARCHAIC is None:
        oc, sd = QC.load_reads_verse("odr_com"), QC.load_reads_verse("s_dismas")
        a = dict(oc)
        a.update(sd)
        _ARCHAIC = a
    return _ARCHAIC


def chapter_anchor_set(chapter: int) -> set[str]:
    """Every folded token of the CHAPTER, from the archaic reference AND janvier.

    Chapter grain, not verse grain, and deliberately so: a verse-grain anchor set would excise the tokens of a
    neighbouring verse whenever a span's boundary is slightly off, which turns a boundary error into deleted
    scripture. At chapter grain a mis-bounded span still anchors, and only material foreign to the whole
    chapter can be dropped. Janvier is unioned in because a few loci have no archaic entry at all."""
    a = archaic_reference()
    toks: set[str] = set()
    janv = VS.chapter_verses(BOOK, chapter, VS.JANVIER) or {}
    for v in janv:
        for src in (a.get(f"scripture/{BOOK}/{chapter}/{v}"), janv.get(v)):
            if src:
                toks |= {gfold(t) for t in VS._toks(src)}
    toks.discard("")
    return toks


MIN_RUN = int(os.environ.get("ODR_GEN_MINRUN", "3"))


def strip_apparatus(text: str, anchors: set[str], *, min_run: int | None = None) -> str:
    """Drop contiguous runs of >= `min_run` tokens that anchor to nothing in the chapter — Genesis's filter.

    `min_run=2` where the generic filter uses 8. The threshold can come down because the anchor is now the
    ARCHAIC reference with the confusion classes folded, so a token failing to anchor is no longer evidence
    that the DR simply spelled it differently.

    A run of ONE is always kept: a single un-anchored token is usually a misrecognition inside a real word,
    and deleting it would remove scripture and flatter the score. Two or more in a row is the signature of
    intruding apparatus, which is exactly what the y-band line merge produces."""
    min_run = MIN_RUN if min_run is None else min_run
    toks = VS._toks(text)
    if not toks:
        return text
    foreign = [gfold(t) not in anchors for t in toks]
    out, i = [], 0
    while i < len(toks):
        if not foreign[i]:
            out.append(toks[i])
            i += 1
            continue
        j = i
        while j < len(toks) and foreign[j]:
            j += 1
        if (j - i) < min_run:
            out.extend(toks[i:j])                       # too short to be apparatus — keep it
        i = j
    return " ".join(out)


def clean_page_lines(lines: list[dict], chapter: int) -> list[str]:
    """Per-line apparatus removal for a Genesis page, returning replacement line texts.

    Line grain rather than whole-page grain on purpose: an apparatus run that straddles the join between two
    body lines would otherwise be invisible to a run-length test, and — more importantly — a run confined to
    one line cannot swallow the start of the next verse."""
    anchors = chapter_anchor_set(chapter)
    out = []
    for l in lines:
        t = l.get("text") or ""
        out.append(strip_apparatus(t, anchors) if l.get("role") == "body" else t)
    return out
