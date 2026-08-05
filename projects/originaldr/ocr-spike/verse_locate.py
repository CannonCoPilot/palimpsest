#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verse_locate.py — ANCHOR-WALK verse localization: find each janvier verse ON THE PAGE, then read it there.

THE IDEA (Sir, 2026-07-26). We already know, almost exactly, WHAT the page says: janvier carries a complete
machine-precise verse grid for all 76 books. What we do not know is this edition's word-choice, spelling and
typesetting. So do not ask the recognizer "what is on this page?" — ask "WHERE on this page is Psalms 118:5?"
Having just found 118:4 at a known token/pixel position, search FORWARD from there for the next verse, match
the known janvier surface against the raw OCR stream, and reverse-look-up the geometry of whatever matched.
That yields a bounding box for 118:5, which can then be re-OCR'd and re-checked against janvier. Anything the
verse walk does not claim is, by construction, apparatus — locatable the same way from the apparatus witnesses,
and whatever is still unclaimed can be chunked and read as residual.

HOW THIS DIFFERS FROM `verse_seg.segment` (which it is designed to replace, not duplicate). That function runs
ONE GLOBAL `difflib.SequenceMatcher` over the whole chapter's token stream against the page, then places
boundaries from the resulting blocks. Global matching has three failure modes we have measured:
  * a verse absorbs the rest of the page when its neighbours fail to anchor (psalms-150-p265 ch150 v1 took
    53 lines / 74% of the page; ch116 v1 took 47; ch74 v1 took 39) — there is nothing to STOP a span;
  * interleaved apparatus breaks blocks into fragments, so localization evidence collapses exactly where the
    page is hardest (the psalms pages);
  * every verse of the chapter competes for every page position, so an off-page verse can steal an anchor.

The anchor-walk fixes all three structurally rather than by tuning:
  * MONOTONE BY CONSTRUCTION — verse i+1 may only start at or after verse i ends, so no span can run away;
  * LOCAL EVIDENCE — each verse is scored only against the window where it could plausibly sit, so garble in
    verse 7 cannot move verse 3;
  * ABSENCE IS FIRST-CLASS — a verse that is genuinely not on the page (page boundaries, the commonest case
    in this corpus) is *chosen* to be absent by the optimizer rather than forced to take tokens.

The placement is a DP over (verse x candidate window), maximizing total match evidence subject to
monotonicity — the exact optimum of "walk forward finding each next verse", not a greedy approximation of it.

GOLD-FREE: janvier + the page's own OCR and geometry. No ground truth anywhere.
NO SILENT DEGRADATION: every verse carries its own match score and an explicit `open`/`reason`; a verse that
cannot be located is returned ABSENT with a reason, never given a plausible-looking span.
"""
from __future__ import annotations

import difflib
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import verse_seg  # noqa: E402
import verse_geom  # noqa: E402

_VNUM = re.compile(r"\d{1,3}\.?")

# §13 Q30/Q36. DEFAULT OFF — built, wired and measurable, not yet validated against all-pass 799 /
# pass_rate_archaic 0.6381 / verse_cover_rate 0.8627.
#
# TWO SITES, SEPARATELY SWITCHED, because the first A/B showed they do not behave alike. `ODR_PARTIAL_FIT`
# accepts a comma list of site names, or `1`/`all` for both:
#
#   spans  — `best_spans`'s arm selection (the 33.7% silent coin flip)
#   better — `corpus_localize._better`'s cross-page arbitration (the 7.8% decided by the length proxy)
#
# WHY THEY HAD TO BE SPLIT. On `archive-ot1-1609` the both-sites arm moved 37 verses, and while several are
# plainly better (`genesis/11/6` and `18/2` change from a neighbouring verse's text to the right one), it also
# moved `genesis/1/1` to page 4 — the volume's FRONT MATTER (`in banisliment. The Slauonians and Gothes`). That
# is precisely the failure `_better`'s length-sanity rule exists to prevent, and F1 can lose to it because a
# SHORT front-matter fragment can out-score a long, badly-garbled reading of the real page. So the cross-page
# site needs a recall/length guard of its own, and it must not be adopted on the intra-page site's evidence.
# Read at call time, not import time, so one process can measure several arms.
_PARTIAL_SITES = ("spans", "better")


def _rescue_partial(site: str = "spans") -> bool:
    import os
    v = os.environ.get("ODR_PARTIAL_FIT", "0")
    if v in ("0", "", "off"):
        return False
    if v in ("1", "all"):
        return True
    return site in {s.strip() for s in v.split(",")}


# --------------------------------------------------------------------------- #
# token stream with geometry
# --------------------------------------------------------------------------- #
def page_tokens(page_result: dict) -> tuple[list[str], list[int], list[str], list[int]]:
    """(folded tokens, line index per folded token, RAW tokens, raw index per folded token).

    Reuses `verse_geom.build_body_tokmap` so this stream is token-for-token the same one the crop geometry is
    keyed to — a verse's token span therefore maps straight back to line indices and pixels with no second
    tokenization to drift out of sync.

    TWO STREAMS, DELIBERATELY. The walk MATCHES on the folded stream (`_afold` collapses archaic↔modern
    spelling so janvier's "many" can find the page's "manie"), but it must EMIT the raw one: `_afold` is
    documented in verse_seg as "for ALIGNMENT only (never emitted)" — it lowercases, folds ſ→s, v→u, j→i,
    y→i and collapses doubled letters, i.e. it destroys precisely the diplomatic surface this project exists
    to preserve. `raw_idx` is the bridge: raw_idx[k] is the index in `raw` of the k-th folded token, so a
    folded span [lo,hi) recovers its verbatim page text and its RAW token extent (the coordinate system
    `verse_seg.segment` and `verse_geom` already speak)."""
    body_text, tok_line = verse_geom.build_body_tokmap(page_result["lines"])
    raw = body_text.split()
    folded, lines, raw_idx = [], [], []
    for j, (t, li) in enumerate(zip(raw, tok_line)):
        ft = verse_seg._afold(t)
        if ft:                       # drop pure punctuation/markers, exactly as verse_seg does
            folded.append(ft)
            lines.append(li)
            raw_idx.append(j)
    return folded, lines, raw, raw_idx


# --------------------------------------------------------------------------- #
# candidate windows for one verse
# --------------------------------------------------------------------------- #
def token_weights(toks: list[str]) -> dict[str, float]:
    """IDF-style weight per page token: rare tokens carry the locating evidence, common ones carry none.

    THIS IS LOAD-BEARING, not a refinement. 2-Esdras 7 is the census list — every verse reads "the children of
    <name>". Unweighted matching lets the repeated "the children of" align across verse boundaries, so a
    verse's span starts inside its predecessor and both score 0 (measured: v53 lost its position to v54
    entirely). Weighting by 1/df collapses that scaffolding to near-zero and lets the proper names — the only
    tokens that actually distinguish one verse of a list from the next — decide where a verse sits. The same
    effect protects any repetitive passage: genealogies, litanies, the psalms' formulaic parallelism."""
    df: dict[str, int] = defaultdict(int)
    for t in toks:
        df[t] += 1
    n = max(1, len(toks))
    return {t: math.log(1.0 + n / c) for t, c in df.items()}


def _match_score(ref: list[str], win: list[str], w: dict[str, float]) -> tuple[float, list]:
    """(IDF-weighted coverage, matching blocks) for janvier tokens `ref` against a page-token window.

    coverage = weight of matched janvier tokens / total weight of the verse — i.e. "how much of this verse's
    DISTINCTIVE content can I see here?". Deliberately NOT symmetric: the window may legitimately contain
    extra material (apparatus, a neighbour's tail), and penalising that would push the optimizer toward
    truncating real verses. Unseen tokens get the maximum weight — a janvier word absent from the page is
    maximally informative about the verse, and must not be silently free."""
    if not ref or not win:
        return 0.0, []
    dflt = max(w.values()) if w else 1.0
    total = sum(w.get(t, dflt) for t in ref) or 1.0
    sm = difflib.SequenceMatcher(a=ref, b=win, autojunk=False)
    blocks = [(a, b, n) for a, b, n in sm.get_matching_blocks() if n > 0]
    got = sum(w.get(ref[a + k], dflt) for a, _b, n in blocks for k in range(n))
    return got / total, blocks


def _seed_positions(ref: list[str], index: dict[str, list[int]], page_df: dict[str, int],
                    max_seeds: int = 6) -> list[int]:
    """Page positions worth testing for this verse, seeded from its RAREST tokens.

    Rare tokens are the informative ones: "Lord"/"the"/"of" occur everywhere on a scripture page and would
    nominate every position, whereas a distinctive token nominates the few places the verse could actually be.
    This is the cheap 'find some signal' step — it keeps the DP to a handful of candidates per verse instead of
    a scan over every token offset."""
    # TOTAL ORDER, deliberately. Sorting a SET of tokens by df alone leaves ties broken by set-iteration
    # order, which Python randomizes per process (PEP 456 string hash seeding) — so which rare tokens seeded
    # the search, and therefore where verses landed, varied run to run on the same input (measured on
    # psalms-118: walk mean 0.811 vs 0.747 across two identical sweeps). Tie-breaking on the token itself
    # makes the walk reproducible. Fixing PYTHONHASHSEED would have hidden the variation, not removed it.
    rare = sorted({t for t in ref if t in index}, key=lambda t: (page_df.get(t, 0), t))[:max_seeds]
    pos: set[int] = set()
    for t in rare:
        for p in index[t]:
            pos.add(p)
    return sorted(pos)


def _trim(ref: list[str], blocks: list, start: int, end: int, w: dict[str, float],
          rare_q: float = 1.0) -> tuple[int, int, int, int]:
    """Tighten a generous search window to the matched core: returns (page_lo, page_hi, ref_lo, ref_hi), where
    the ref_* pair records WHICH janvier tokens matched — the budget for giving unmatched text back later.

    MUST happen before the walk, not after (this was a real bug): the search window is deliberately `slack` x
    the verse's length so it can absorb this edition's expansions, but if the DP enforces monotonicity on that
    padded extent then every verse's slack tail blocks its own successor, and the second half of the chapter
    goes 'not-located'. Monotonicity has to be judged on where the verse REALLY is.

    Only blocks carrying a DISTINCTIVE token define the extent (same reason as token_weights): on a
    repetitive list page a stray "the children of" block sitting in the neighbouring verse would otherwise
    stretch this verse's extent over its predecessor. Falls back to all blocks when nothing rare matched."""
    if not blocks:
        return start, end, 0, len(ref)
    ws = sorted(w.values())
    cut = ws[int(rare_q * (len(ws) - 1))] if ws else 0.0
    strong = blocks if rare_q >= 1.0 else (
        [(a, b, n) for a, b, n in blocks
         if any(w.get(ref[a + k], cut) >= cut for k in range(n))] or blocks)
    return (start + min(b for _a, b, _n in strong), start + max(b + n for _a, b, n in strong),
            min(a for a, _b, _n in strong), max(a + n for a, _b, n in strong))


def _candidates(ref: list[str], toks: list[str], index, page_df, w, *, slack: float,
                max_cand: int, min_cov: float) -> list[tuple[int, int, float, int, int]]:
    """Candidate (start, end, coverage) placements for one verse, best-first, already TRIMMED to the matched
    extent so the walk's monotonicity test sees the verse's real span.

    A search window is `slack` x the verse's own janvier length — long enough to absorb this edition's
    expansions and interleaved apparatus, short enough that the verse cannot swallow its neighbours. It is
    anchored so the seed token sits inside it rather than at its head, since a seed is usually mid-verse."""
    m = len(ref)
    if m == 0:
        return []
    span = max(4, int(m * slack))
    out: list[tuple[int, int, float, int, int]] = []
    seen: set[tuple[int, int]] = set()
    for p in _seed_positions(ref, index, page_df):
        start = max(0, p - m // 2)                 # seed sits mid-verse, so back off half a verse
        end = min(len(toks), start + span)
        cov, blocks = _match_score(ref, toks[start:end], w)
        if cov < min_cov:
            continue
        lo, hi, rlo, rhi = _trim(ref, blocks, start, end, w)
        if (lo, hi) in seen:
            continue
        seen.add((lo, hi))
        out.append((lo, hi, cov, rlo, rhi))
    out.sort(key=lambda c: (-c[2], c[0], c[1]))     # total order: equal-coverage candidates rank by position
    return out[:max_cand]


# --------------------------------------------------------------------------- #
# the walk (monotone DP)
# --------------------------------------------------------------------------- #
def _walk(verses: list[int], cands: dict[int, list[tuple[int, int, float, int, int]]]):
    """Choose at most one candidate per verse, in verse order, with non-overlapping monotone spans, maximizing
    total coverage. Absence costs nothing, so a verse only takes a span when the evidence is positive — which
    is what makes page-boundary chapters (most of this corpus) behave.

    DP over (verse index, chosen end position). States stay tiny (<= max_cand per verse), so this is exact."""
    # state: dict end_pos -> (total_score, backpointer chain)
    best: dict[int, tuple[float, tuple]] = {0: (0.0, ())}
    for v in verses:
        nxt = dict(best)                                    # option: verse absent (carry every state forward)
        for (s, e, cov, rlo, rhi) in cands.get(v, []):
            for end_prev, (sc, chain) in best.items():
                if s < end_prev:                            # monotonicity: cannot start before the previous end
                    continue
                tot = sc + cov
                cur = nxt.get(e)
                if cur is None or tot > cur[0]:
                    nxt[e] = (tot, chain + ((v, s, e, cov, rlo, rhi),))
        # prune: keep only the best chain per end position, and cap the frontier
        best = dict(sorted(nxt.items(), key=lambda kv: -kv[1][0])[:64])
    if not best:
        return ()
    return max(best.values(), key=lambda x: x[0])[1]


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def locate(page_result: dict, book: str, chapter: int, *, slack: float = 2.2, max_cand: int = 6,
           min_cov: float = 0.25, expand_k: float = 1.6, expand_pad: float = 0.0) -> dict:
    """Locate each janvier verse of (book, chapter) on this page.

    Returns {"verses": {v -> {tok_lo, tok_hi, lines, coverage, text, open, reason}},
             "apparatus": [{tok_lo, tok_hi, text, lines}],   # contiguous unclaimed token runs
             "n_tokens": int}
    `tok_lo`/`tok_hi` are RAW body-token indices — the same coordinate system `verse_seg.segment` emits and
    `verse_geom` maps to pixels — so a span from either segmenter is interchangeable downstream. `text` is
    the VERBATIM page text of that span (never the alignment fold; see `page_tokens`).
    `text` is the page's OWN reading of that verse (the edition's spelling/typesetting), which is the whole
    point: janvier says WHERE and roughly WHAT; the page says exactly HOW it is set here.

    A verse absent from the walk is reported with `open=True, reason='not-located'` — never given a span.
    """
    toks, tok_line, raw, raw_idx = page_tokens(page_result)
    cv = verse_seg.chapter_verses(book, chapter, verse_seg.JANVIER)
    if not cv or not toks:
        return {"verses": {}, "apparatus": [], "n_tokens": len(toks)}

    def _raw_span(lo: int, hi: int) -> tuple[int, int]:
        """folded [lo,hi) -> RAW [lo,hi). Tiles like verse_seg: a span ends where the next kept token starts,
        so consecutive verses hand off with no raw token falling between them."""
        r_lo = raw_idx[lo] if lo < len(raw_idx) else len(raw)
        r_hi = raw_idx[hi] if hi < len(raw_idx) else len(raw)
        return r_lo, max(r_lo, r_hi)

    index: dict[str, list[int]] = defaultdict(list)
    for i, t in enumerate(toks):
        index[t].append(i)
    page_df = {t: len(ps) for t, ps in index.items()}

    refs = {v: [verse_seg._afold(t) for t in verse_seg._toks(s) if verse_seg._afold(t)]
            for v, s in cv.items()}
    w = token_weights(toks)
    cands = {v: _candidates(refs[v], toks, index, page_df, w, slack=slack, max_cand=max_cand, min_cov=min_cov)
             for v in sorted(cv)}
    chain = _walk(sorted(cv), cands)

    placed = {v: (s, e, cov, rlo, rhi) for (v, s, e, cov, rlo, rhi) in chain}

    # ---- GIVE THE UNMATCHED TEXT BACK (the point of the whole exercise) --------------------------------- #
    # The walk anchors on tokens that MATCH janvier, but what we actually want to read is this edition's own
    # wording — which by definition is the text that did NOT match. Anchoring to the matched core and stopping
    # there returns a verse stripped of exactly its divergent parts (measured: mean identity 0.824 vs the
    # incumbent's 0.921). So each verse is expanded outward into the unclaimed gap around it, BUDGETED by how
    # many of its own janvier tokens are still unaccounted for: a verse whose match ran to its last janvier
    # token has no tail owing and claims nothing, while one that matched only its first half may claim a tail
    # about as long as the half it is missing. Whatever neither neighbour can claim is apparatus — which is
    # how interleaved annotation stays OUT of the verses instead of being swallowed by a greedy fill.
    ordered = [v for v in sorted(cv) if v in placed]
    for i, v in enumerate(ordered):
        lo, hi, cov, rlo, rhi = placed[v]
        m = len(refs[v]) or 1
        # budget = the janvier tokens still owing, x expand_k. `expand_pad` would additionally let a verse
        # reclaim text proportional to its own length, on the theory that an edition can ADD words janvier
        # lacks (expansions, doublets) which no unmatched-janvier token pays for. MEASURED AND REJECTED: on
        # the 177 gold verses the mean identity falls monotonically with it — 0.0 -> 0.860, 0.10 -> 0.809,
        # 0.15 -> 0.782, 0.25 -> 0.700, 0.40 -> 0.654. On these pages the material sitting in the gap is
        # APPARATUS, not verse expansion, so a verse that matched its janvier text in full should reclaim
        # nothing. Kept as a parameter (default 0.0) so the result stays reproducible.
        head_budget = int(rlo * expand_k + expand_pad * m)
        tail_budget = int((m - rhi) * expand_k + expand_pad * m)
        prev_end = placed[ordered[i - 1]][1] if i else 0
        next_start = placed[ordered[i + 1]][0] if i + 1 < len(ordered) else len(toks)
        # claim backward into the gap after the previous verse, and forward into the gap before the next one
        new_lo = max(prev_end, lo - head_budget)
        new_hi = min(next_start, hi + tail_budget)
        placed[v] = (new_lo, new_hi, cov, rlo, rhi)
    # resolve any residual overlap created by two neighbours claiming the same gap: split it at the midpoint
    for i in range(1, len(ordered)):
        a, b = ordered[i - 1], ordered[i]
        if placed[a][1] > placed[b][0]:
            mid = (placed[a][1] + placed[b][0]) // 2
            placed[a] = (placed[a][0], mid, *placed[a][2:])
            placed[b] = (mid, *placed[b][1:])

    out: dict[int, dict] = {}
    for v in sorted(cv):
        if v not in placed:
            out[v] = {"tok_lo": None, "tok_hi": None, "lines": [], "coverage": 0.0, "text": "",
                      "open": True, "reason": "not-located"}
            continue
        lo, hi, cov, _rlo, _rhi = placed[v]
        lines = sorted({tok_line[j] for j in range(lo, min(hi, len(tok_line)))})
        r_lo, r_hi = _raw_span(lo, hi)
        out[v] = {"tok_lo": r_lo, "tok_hi": r_hi, "lines": lines, "coverage": round(cov, 4),
                  "text": " ".join(raw[r_lo:r_hi]), "open": cov < 0.5,
                  "reason": "" if cov >= 0.5 else f"low-coverage {cov:.2f}"}

    claimed = set()
    for v in ordered:
        lo, hi, *_ = placed[v]
        claimed.update(range(lo, hi))
    apparatus, j = [], 0
    while j < len(toks):
        if j in claimed:
            j += 1
            continue
        k = j
        while k < len(toks) and k not in claimed:
            k += 1
        r_lo, r_hi = _raw_span(j, k)
        apparatus.append({"tok_lo": r_lo, "tok_hi": r_hi,
                          "text": " ".join(raw[r_lo:r_hi]),
                          "lines": sorted({tok_line[t] for t in range(j, min(k, len(tok_line)))})})
        j = k
    return {"verses": out, "apparatus": apparatus, "n_tokens": len(toks)}


def janvier_fit(span: str, janvier_verse: str) -> float:
    """GOLD-FREE quality of a produced span: its identity against the janvier verse it claims to be.

    This is the selector signal, and it is legitimate in production because janvier is a reference witness,
    not ground truth — the same standing `xsrc_gate` already relies on. It cannot certify that a span is a
    faithful diplomatic reading (this edition's spelling deliberately differs from janvier), but it is a
    strong detector of the failure we actually care about here: a span pointed at the WRONG PLACE, which
    diverges from janvier far more than any spelling variation does."""
    if not span or not janvier_verse:
        return 0.0
    from char_identity import evaluate_locus
    return evaluate_locus(span, janvier_verse, janvier_verse)["archaic_id"]


_FIT_STRIP = " \t.,;:·†‡*()[]"


def _fit_tokens(text: str) -> list[str]:
    """Bare lowercase word tokens for the partial-tolerant fits below.

    This duplicates `gen1_pagemodel._bare` rather than importing it, deliberately: the page model is STANDALONE
    (the live corpus pipeline does not import it, which is what lets two chapters be tuned aggressively without
    touching production), and `verse_locate` IS in the live path. A four-line fold is a smaller price than that
    coupling. Kept character-identical to `_bare` so a span scored here and a span scored there agree."""
    return [t for t in ((w or "").strip(_FIT_STRIP).lower().replace("ſ", "s") for w in (text or "").split()) if t]


def partial_fit(span: str, janvier_verse: str) -> tuple[float, float, float]:
    """(precision, recall, F1) of a span against the janvier verse it claims to be — PARTIAL-TOLERANT.

    WHY THIS EXISTS (§13 Q30, measured 2026-07-29). `janvier_fit` returns **0.000 for any partial span**
    because it delegates to `evaluate_locus`, which compares a WHOLE verse to its reference. Measured on the
    live localize loop (`selector_corpus_probe.py`, archive-ot1-1609, psalms/genesis/matthew/john/apocalypse):

        arms DIFFER (the selector actually decides)     91.1% of verse-spans
        selector DEAD (both arms janvier_fit 0.000)     42.5%
        DEAD *and* the arms differ — a SILENT COIN FLIP 42.1%   (46% of all real decisions)

    On every one of those the comparison is `0.0 > 0.0`, so `best_spans` takes the aligner arm without
    recording that nothing was compared. That is not a scoring nicety: `fit` is carried downstream as evidence
    (`corpus_localize._better`, `xsrc_gate`), and a constant 0.0 is evidence of nothing.

    `precision` is `gen1_r3.span_fit` — the fraction of the SPAN's tokens appearing in order in the verse. It
    is what a partial needs, and alone it is NOT safe: a ONE-TOKEN span scores 1.000, and in cross-page
    arbitration that pathology fired for real (`genesis/3/13`: a 1-token span at precision 1.00 beating a
    12-token one at 0.58). `recall` is the mirror — the fraction of the VERSE's tokens the span covers — which
    is what `janvier_fit`'s length-awareness was providing. F1 keeps both, so a partial is not penalised for
    the part it lacks any more than a fragment is rewarded for it.

    UNWIRED ON PURPOSE. Nothing in production calls this yet; adoption is gated on the corpus measurement
    (all-pass 799 / pass_rate_archaic 0.6381 / verse_cover_rate 0.8627, report v045)."""
    a, b = _fit_tokens(span), _fit_tokens(janvier_verse)
    if not a or not b:
        return 0.0, 0.0, 0.0
    m = sum(bl.size for bl in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks())
    p, r = m / len(a), m / len(b)
    return p, r, (0.0 if p + r == 0 else 2 * p * r / (p + r))


def anchored_spans(page_result: dict, book: str, chapter: int, anchors: dict[int, int]) -> dict[int, dict]:
    """Spans derived DIRECTLY from recovered printed verse numbers — the self-labelling path.

    `anchors` maps verse -> the body-line index whose printed number opens it (verse_numbers.anchors). Because
    the number NAMES its verse, this needs no text matching at all: verse v runs from the first token of its
    anchor line to the first token of the next anchored verse's line. Everything the walk and the aligner have
    to infer — where a verse starts, and which verse it is — the printer already recorded.

    Only verses between the first and last anchor are emitted; the page's edges are left to the text-anchored
    arms, since an anchor cannot say where an un-anchored neighbour ends."""
    body_text, tok_line = verse_geom.build_body_tokmap(page_result["lines"])
    raw = body_text.split()
    if not raw or not anchors:
        return {}
    first_tok: dict[int, int] = {}
    for j, li in enumerate(tok_line):
        first_tok.setdefault(li, j)
    ordered = [v for v in sorted(anchors) if anchors[v] in first_tok]
    out: dict[int, dict] = {}
    for i, v in enumerate(ordered):
        lo = first_tok[anchors[v]]
        # END AT THE NEXT ANCHOR ONLY IF IT IS THE VERY NEXT VERSE. Anchors are sparse (45 accepted across 145
        # openings), so running a span to the next ANCHORED verse would swallow every un-anchored verse
        # between them — the runaway span the walk was built to make impossible, reintroduced by the anchor.
        # A lone anchor is trustworthy about where its verse BEGINS and says nothing about where it ends.
        nxt = ordered[i + 1] if i + 1 < len(ordered) else None
        if nxt is not None and nxt == v + 1:
            hi = first_tok[anchors[nxt]]
        else:
            hi = None                      # caller keeps the inferred end; the anchor fixes the start only
        if hi is not None and hi <= lo:
            continue
        if hi is None:
            out[v] = {"tok_lo": lo, "tok_hi": None, "lines": [], "text": "", "open": False,
                      "reason": "start-only", "source": "anchor"}
            continue
        lines = sorted({tok_line[j] for j in range(lo, min(hi, len(tok_line)))})
        out[v] = {"tok_lo": lo, "tok_hi": hi, "lines": lines, "text": " ".join(raw[lo:hi]),
                  "open": False, "reason": "", "source": "anchor"}
    return out


def best_spans(page_result: dict, book: str, chapter: int, *, switch_margin: float = 0.0,
               anchors: dict[int, int] | None = None, line_range: tuple[int, int] | None = None,
               **kw) -> dict[int, dict]:
    """Per verse, take whichever of the two segmenters fits janvier better — the production entry point.

    WHY A HYBRID RATHER THAN A REPLACEMENT (measured on the 13 gold pages, 177 verses):

        incumbent (global align)   mean 0.9215   pass 131/177 = 0.740
        anchor-walk                mean 0.8557   pass 127/177 = 0.718
        HYBRID (this function)     mean 0.9488   pass 143/177 = 0.808   Wilcoxon p=0.004
        oracle (chosen with gold)  mean 0.9553   pass 150/177 = 0.847

    The two methods fail in DIFFERENT places, which is why picking between them beats either. Global
    alignment is better on clean continuous prose, where its long matching blocks are unambiguous. The
    anchor-walk is better exactly where global alignment degenerates — page-boundary chapters and interleaved
    apparatus (psalms-074 ch74: 0.000 -> 0.943; psalms-150-p265 ch149: 0/8 -> 5/8 passing) — because
    monotonicity structurally forbids a runaway span. Selecting per verse on the gold-free janvier fit
    captures 80% of the oracle's available gain, so the selector is nearly as good as knowing the answer.

    Returns {verse -> {text, tok_lo, tok_hi, lines, source, fit, alt_fit, open, reason, ...}} where `source`
    is 'walk' or 'align' — always recorded, so a downstream consumer can see which engine produced a span
    rather than inheriting an anonymous string.

    GEOMETRY IS RESOLVED FROM THE WINNER'S OWN SPAN. Both engines now report `tok_lo/tok_hi` in RAW body-token
    space, so `lines` is derived here from the selected span's extent through the single `build_body_tokmap`
    token→line map. (An earlier draft copied the WALK's line list onto align-sourced verses — `verse_seg` emits
    no `lines` of its own, so the fallback fired on every align verse — which would have handed a downstream
    crop the losing engine's pixels. Nothing consumed it yet; the tests below pin it shut.)
    """
    if line_range is not None:
        # §13 Q5: restrict the page to ONE chapter's lines before segmenting. verse_seg's contract requires it
        # ("split the body by chapter first and call once per chapter") and no caller honoured it, so on a
        # straddling page the verses of both chapters competed for every position.
        lo_l, hi_l = line_range
        page_result = {**page_result,
                       "lines": [l for i, l in enumerate(page_result["lines"]) if lo_l <= i < hi_l]}
        page_result["r2_body"] = verse_geom.build_body_tokmap(page_result["lines"])[0]
    body_text, tok_line = verse_geom.build_body_tokmap(page_result["lines"])
    raw_toks = body_text.split()
    stored = page_result.get("r2_body")
    if stored is not None and body_text != stored:
        # The walk indexes the body reconstructed from `lines`; the aligner is handed the stored `r2_body`.
        # They are the same string by construction — if they ever diverge, the two arms are talking about
        # different token streams and every span mixes two coordinate systems. Fail loudly rather than emit
        # geometry keyed to the wrong pixels (the guard verse_geom.verse_crops already applies).
        raise ValueError("verse_locate.best_spans: body text reconstructed from `lines` disagrees with the "
                         "stored r2_body — refusing to mix two token streams (No Silent Degradation).")
    walk = locate(page_result, book, chapter, **kw)["verses"]
    align = verse_seg.segment_book_chapter(body_text, book, chapter, drop_apparatus=True)
    cv = verse_seg.chapter_verses(book, chapter, verse_seg.JANVIER)
    out: dict[int, dict] = {}
    for v in sorted(set(walk) | set(align)):
        # `locate` reports EVERY janvier verse of the chapter, including the ones it chose to call absent
        # (that is its absence-is-first-class contract). The hybrid's consumers — the gate, the crop router —
        # ask "which verses are ON this page?", so a verse neither engine localized is not emitted at all
        # rather than emitted as an empty span that would read as a catastrophically bad verse and flood the
        # flagged set. `locate(...)['verses']` remains available for the not-located reasons.
        if v not in align and (walk.get(v) or {}).get("tok_lo") is None:
            continue
        jv = cv.get(v)
        wtxt = (walk.get(v) or {}).get("text", "")
        atxt = (align.get(v) or {}).get("text", "")
        wf, af = janvier_fit(wtxt, jv), janvier_fit(atxt, jv)
        # §13 Q30 RESCUE (2026-07-29, DEFAULT OFF pending the corpus A/B). Where BOTH arms are partial, both
        # `janvier_fit`s are 0.000, the comparison below is `0.0 > 0.0`, and the aligner wins by default without
        # anything having been compared — measured over 11 witnesses / 2,767 pages / 36,833 verse-spans
        # (`selector_corpus_probe.py`) at **33.7% of live verse-spans**, i.e. 40.7% of every decision where the
        # arms actually differ. `partial_fit` separates 84.7% of those pairs and prefers the WALK on ~4,470 of
        # them, so this null is not a cosmetic tie.
        #
        # NOTE ON `switch_margin`: it is compared against whichever score decided, and the two are not on the
        # same scale (a janvier_fit and an F1). Production passes 0.0 at every call site, so this is inert today;
        # a future sweep must calibrate the margin per selector rather than assume one number serves both.
        #
        # It rescues ONLY the dead rows. Replacing the selector outright was measured on the 14 gold pages and
        # is NET NEGATIVE — `span_fit` alone changed 18 verses and lost all 18; `partial_fit` alone changed 16
        # and lost 16. The incumbent is right wherever it can see; it is blind, not wrong.
        selector = "janvier_fit"
        if _rescue_partial() and wf <= 1e-9 and af <= 1e-9:
            pw, pa = partial_fit(wtxt, jv)[2], partial_fit(atxt, jv)[2]
            if pw > pa + 1e-9 or pa > pw + 1e-9:
                # Decide on the partial-tolerant score, but do NOT overwrite `fit`: downstream consumers
                # (`corpus_localize._better`, `xsrc_gate`) compare `fit` values across pages and mixing two
                # metrics into one field would make those comparisons meaningless. The partial scores are
                # published alongside, under their own names, so the substitution stays auditable.
                wf_eff, af_eff = pw, pa
                selector = "partial_fit-rescue"
            else:
                wf_eff, af_eff = wf, af
            pfit_w, pfit_a = pw, pa
        else:
            wf_eff, af_eff = wf, af
            pfit_w = pfit_a = None
        # `switch_margin` makes the incumbent aligner the DEFAULT and requires the walk to beat it by a margin
        # before the span is switched — the obvious remedy for the selector's honest cost (verses the aligner
        # already read near-perfectly that a marginally-better janvier fit moved). Whether it helps is an
        # empirical question, answered by the sweep in verse_locate_eval (see the pinned result in the tests).
        if wf_eff > af_eff + switch_margin:
            d = dict(walk.get(v) or {})
            d.update(source="walk", fit=round(wf, 4), alt_fit=round(af, 4))
        else:
            d = dict(align.get(v) or {})
            d.update(source="align", fit=round(af, 4), alt_fit=round(wf, 4))
        d["selector"] = selector
        if pfit_w is not None and pfit_a is not None:
            d["pfit"], d["alt_pfit"] = (round(pfit_w, 4), round(pfit_a, 4)) if d["source"] == "walk" \
                else (round(pfit_a, 4), round(pfit_w, 4))
        lo, hi = d.get("tok_lo"), d.get("tok_hi")
        if lo is None or hi is None:
            d["lines"] = []
        else:
            d["lines"] = sorted({tok_line[j] for j in range(lo, min(hi, len(tok_line)))})
        out[v] = d

    # SELF-LABELLING ANCHORS WIN. A recovered printed number does not merely suggest where a verse starts —
    # it states which verse starts there, which is the one thing neither text-anchored arm can know rather
    # than infer. Where an anchor exists it therefore replaces the inferred span outright, and the displaced
    # arm's fit is retained so the substitution stays auditable. (Anchors are vetted upstream for monotonicity
    # and chapter membership; an anchor that failed vetting never reaches here.)
    if anchors:
        anc = anchored_spans(page_result, book, chapter, anchors)
        for v, d in anc.items():
            prev = out.get(v) or {}
            if d.get("tok_hi") is None:
                # START-ONLY anchor: trim the inferred span to begin where the printer says the verse does,
                # keeping the inferred end. This is the common case (anchors are sparse) and it is strictly
                # a correction — the anchor can only move the start, never invent an extent.
                if prev.get("tok_lo") is None or prev.get("tok_hi") is None:
                    continue
                lo, hi = d["tok_lo"], prev["tok_hi"]
                if hi <= lo:
                    continue
                text = " ".join(raw_toks[lo:hi])
                nd = {**prev, "tok_lo": lo, "tok_hi": hi, "text": text,
                      "lines": sorted({tok_line[j] for j in range(lo, min(hi, len(tok_line)))}),
                      "source": prev.get("source"), "anchored": True}
                nd["fit"] = round(janvier_fit(text, cv.get(v)), 4)
                nd["alt_fit"] = prev.get("fit")
                out[v] = nd
                continue
            d["fit"] = round(janvier_fit(d.get("text", ""), cv.get(v)), 4)
            d["alt_fit"] = prev.get("fit")
            d["displaced"] = prev.get("source")
            d["anchored"] = True
            out[v] = d
    return out


if __name__ == "__main__":
    import json
    slug = sys.argv[1] if len(sys.argv) > 1 else "scripture-psalms-150-p265"
    ch = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    from gate_calibrate import LOCI
    d = json.loads((HERE / ".page-cache" / f"{slug}.json").read_text())
    pr = {"page_px": tuple(d["page_px"]), "r2_body": d["r2_body"], "lines": d["lines"]}
    r = locate(pr, LOCI[slug], ch)
    for v, x in r["verses"].items():
        print(f"  v{v:>4} cov={x['coverage']:.2f} lines={len(x['lines']):>3} {x['reason']:<20} {x['text'][:70]!r}")
    print(f"  apparatus runs: {[(a['tok_lo'], a['tok_hi']) for a in r['apparatus']]}")
