#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verse_seg.py — janvier-cut verse segmentation (VS-1..4; the §5 linchpin, 2026-07-22).

Re-cut ANY page's body text (OCR *or* Gold) to janvier's verse boundaries, so that BOTH sides of every
comparison share ONE grid and boundary-fuzz cancels. This is the fix for the "0.47 per-verse" artifact:
that number was a boundary *mismatch* (OCR cut by one versification, gold by another), never a recognition
failure — containment read 0.96 on the same pages because it is boundary-blind.

Gold-free by construction: janvier (= `reads/sabates_a.json`, USFM-ingested) covers all 76 books with a
contiguous, machine-precise \v grid, so the cut exists for ANY Douay-Rheims locus. Gold pages only VALIDATE
the engine (VS-5); they are not required to run it (Principle P1).

This is the rebuild of `align_coords.realign`, fixing its four defects:
  VS-1 body-isolate FIRST     — caller passes already-body-isolated text (layout.py runs upstream in
                                reocr_core). Marginalia/header/catchword are gone before we cut.
  VS-2 page-scope LOCALIZE     — align only the verses actually on the page, never the whole chapter.
                                (Aligning all 176 Ps-118 verses against a ~10-verse page was the 2-93x
                                drift + monotonic-clamp corruption in align_coords.)
  VS-3 janvier-PRIMARY cuts    — boundaries come from janvier (complete, machine-precise), NOT s_dismas
                                (itself a fuzzy OCR transcription — circular as a ruler; and its native
                                versification differs, e.g. odr_com Ps-118 spans 1..207 for 175 verses).
  VS-4 length-SANITY           — a produced span whose folded length deviates from janvier's verse length
                                by more than `len_k`x (either way), or that captured no anchor token, is
                                flagged OPEN — never emitted as a silently-accepted garbage span
                                (No Silent Degradation at the sub-page grain).

The output is a per-verse dict carrying the span AND its quality flags, so a caller can route OPEN verses
to escalation and can score the clean ones. Nothing here touches gold or computes an identity metric;
scoring lives in `verse_seg_eval.py` / `char_identity.evaluate_locus`.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

SPIKE = Path(__file__).resolve().parent
ROOT = SPIKE.parent                              # originaldr-project
READS = ROOT / "reconstruction" / "reads"

# Boundary authority for CUTS (VS-3) and the fallback cascade for the archaic SCORING reference.
JANVIER = "sabates_a"                             # complete, machine-precise \v grid (all 76 books)
ARCHAIC_CASCADE = ("s_dismas", "odr_com")        # archaic surface witnesses (partial coverage)
MODERN_CASCADE = ("sabates_a", "madueke_b")      # modern content references


# --------------------------------------------------------------------------- #
# reads/ loaders (skeleton_id = "scripture/{book}/{chapter}/{verse}")
# --------------------------------------------------------------------------- #
_READS_CACHE: dict[str, dict[str, str]] = {}
_SKEL_RE = re.compile(r"scripture/([^/]+)/(\d+)/(\d+)$")

# --- janvier body-grain normalization: strip inlined acrostic section-markers --------------------------- #
# sabates_a (janvier) INLINES the Hebrew-letter acrostic markers + their English gloss into the section-
# initial verse ("Nun. Everlasting. Thy word is a lamp…"), but every DR witness AND the gold body SEGREGATE
# these to apparatus (`section_marker`, hebrew_letter). For a fair body-to-body cut the janvier grid must be
# body-grain, so we strip the paratext from janvier only (a no-op on the witnesses, which lack it). The 22
# DR-transliterated Hebrew letter names form a closed set with ZERO false-strip risk. Empirically (whole
# sabates_a, 76 books): EXACTLY 22 verses match, all in Psalms 118 — this witness marks only Ps 118 with
# inline letters (Ps 111/112 use a title-gloss "Alleluia. Of the return of Aggeus…" that correctly does NOT
# match; Lamentations/Prov 31 acrostics are unmarked here). No verse is emptied and no capture exceeds ~45 chars.
_HEB = (r"Aleph|Beth|Gimel|Daleth|He|Vau|Zain|Heth|Teth|Iod|Caph|Lamed|"
        r"Mem|Nun|Samech|Ain|Phe|Sade|Coph|Res|Sin|Tau")
# optional liturgical "Alleluia." opening, then <Letter>. <gloss up to 40 non-period chars>.
_ACROSTIC_RE = re.compile(rf"^\s*(?:Alleluia\.\s+)?(?:{_HEB})\.\s+[^.]{{1,40}}?\.\s+")


def strip_acrostic_paratext(text: str) -> str:
    """Remove a leading inlined acrostic section-marker ('<Letter>. <gloss>. ') from a janvier verse so the
    reference matches body grain. No-op on the ~154/176 non-section verses and on all non-acrostic chapters."""
    return _ACROSTIC_RE.sub("", text, count=1)


def reads(name: str) -> dict[str, str]:
    """{skeleton_id -> surface} for the PRESENT entries of a reference read set (cached)."""
    if name not in _READS_CACHE:
        d = json.loads((READS / f"{name}.json").read_text())
        _READS_CACHE[name] = {e["skeleton_id"]: (e.get("surface") or "")
                              for e in d["reads"] if e.get("present")}
    return _READS_CACHE[name]


def chapter_verses(book: str, chapter: int, source: str = JANVIER,
                   strip_paratext: bool | None = None) -> dict[int, str]:
    """Ordered {verse:int -> surface} for one chapter from `source` (default janvier/sabates_a).

    janvier is the boundary authority (VS-3); the same accessor serves s_dismas/odr_com/madueke when a
    caller needs a witness's own text (e.g. to re-cut it to the janvier grid for scoring). By default the
    janvier grid is normalized to body grain (`strip_acrostic_paratext`); pass strip_paratext=False for the
    raw surface."""
    if strip_paratext is None:
        strip_paratext = (source == JANVIER)
    d = reads(source)
    out: dict[int, str] = {}
    for sid, surf in d.items():
        m = _SKEL_RE.match(sid)
        if m and m.group(1) == book and int(m.group(2)) == chapter:
            out[int(m.group(3))] = strip_acrostic_paratext(surf) if strip_paratext else surf
    return dict(sorted(out.items()))


def archaic_chapter(book: str, chapter: int) -> tuple[dict[int, str], str | None]:
    """The best archaic witness's {verse->surface} for a chapter, by cascade, plus which one (or None)."""
    for name in ARCHAIC_CASCADE:
        vs = chapter_verses(book, chapter, name)
        if vs:
            return vs, name
    return {}, None


# --------------------------------------------------------------------------- #
# folding for ALIGNMENT only (never emitted): collapse archaic<->modern spelling + glyph noise so
# s_dismas / janvier / OCR tokens of the same word match. Distinct from char_identity's scoring folds.
# --------------------------------------------------------------------------- #
def _afold(t: str) -> str:
    t = t.lower().replace("ſ", "s").replace("æ", "ae").replace("œ", "oe").replace("vv", "w")
    t = t.replace("v", "u").replace("j", "i").replace("y", "i")   # y->i bridges manie/many, waies/ways
    t = re.sub(r"[^a-z0-9]", "", t)
    t = t.replace("ff", "f")                                       # OCR ſ->f doubling leniency
    return re.sub(r"(.)\1+", r"\1", t) if t else t                 # collapse doubles (Sonne->sone, bee->be)


_WORD = re.compile(r"\S+")


def _toks(s: str) -> list[str]:
    return _WORD.findall(s or "")


def _flen(s: str) -> int:
    """folded character length — the length yardstick for VS-4 (glyph/spelling-noise-invariant)."""
    return sum(len(_afold(t)) for t in _toks(s))


# --------------------------------------------------------------------------- #
# the segmenter (VS-2 + VS-3 + VS-4)
# --------------------------------------------------------------------------- #
def segment(text: str, cverses: dict[int, str], *, len_k: float = 2.5,
            min_anchor: int = 2, block_min: int = 3, drop_apparatus: bool = False,
            apparatus_min: int = 8) -> dict[int, dict]:
    """Cut `text` (one chapter's body text from a single page) to janvier verse boundaries.

    Args:
      text: body-isolated page text for ONE chapter (verse numbers already stripped; VS-1 done upstream).
      cverses: ordered {verse:int -> janvier surface} for the WHOLE chapter (the grid + length reference).
      len_k: a span is length-OPEN if got/expected folded-length is outside [1/len_k, len_k].
      min_anchor: a verse counts as "on this page" only with >= this many matched tokens FROM CONTIGUOUS
                  blocks (VS-2 outlier rejection — scattered high-frequency function words must not localize).
      block_min: minimum length of a difflib matching block to count toward localization evidence. Single-token
                  matches (n==1) of common words ("the"/"of"/"God") are excluded so unrelated same-vocabulary
                  prose cannot spuriously localize (they still serve as boundary anchors, just not as evidence
                  that a verse is present on the page).
      drop_apparatus: janvier-as-apparatus-filter. A CONTIGUOUS RUN of >= apparatus_min page tokens that
                  anchor to NO janvier token is non-verse material (an interleaved footnote/annotation) and is
                  excluded from the verse spans. This lets the janvier grid itself separate body from
                  central-column apparatus that pure-geometry body-isolation (layout.py) cannot — no Surya/
                  geometry needed. Short un-anchored gaps (OCR noise inside a verse) are kept.
      apparatus_min: minimum un-anchored run length to treat as apparatus (conservative: clean prose has only
                  short un-anchored gaps, so this is a no-op on well-recognized body pages like genesis).

    Returns {verse:int -> {text, ref, present, open, reason, len_ratio, anchor, exp_len, got_len}} for the
    verses LOCALIZED to this page. Empty dict if the text matches no verse of this chapter (a no-locate OPEN
    the caller must surface).

    CONTRACT: `text` must be ONE chapter's body text. On a page that straddles chapters, split the body by
    chapter first and call once per chapter. If foreign-chapter text bleeds in, a LARGE bleed is caught by the
    len-sanity flag (the edge verse goes OPEN(len-long)) and by `drop_apparatus`; only a small (<apparatus_min)
    trailing/leading leak can slip into the first/last verse — a documented edge residual, not a silent
    mid-page truncation (interior boundaries are anchored locally and never encroach past a real anchor)."""
    verses = sorted(cverses.items())                     # reading order = verse number (don't trust dict order)
    if not verses or not (text or "").strip():
        return {}

    # ref token stream: folded tokens of the whole chapter, tagged with their verse index + first-index map
    ref_tok: list[str] = []
    ref_vi: list[int] = []
    first: dict[int, int] = {}
    exp_len: dict[int, int] = {}
    for vi, (v, surf) in enumerate(verses):
        exp_len[vi] = _flen(surf)
        for t in _toks(surf):
            ft = _afold(t)
            if ft:
                first.setdefault(vi, len(ref_tok))
                ref_tok.append(ft)
                ref_vi.append(vi)

    raw = _toks(text)
    in_all = [_afold(t) for t in raw]
    keep = [i for i, ft in enumerate(in_all) if ft]     # drop pure-punctuation/marker tokens
    in_f = [in_all[i] for i in keep]
    if not ref_tok or not in_f:
        return {}

    sm = difflib.SequenceMatcher(a=ref_tok, b=in_f, autojunk=False)
    ref2in: dict[int, int] = {}
    block_hits: dict[int, int] = {}                      # per-verse tokens in blocks >= block_min (localize)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            ref2in[a + k] = b + k
        if n >= block_min:                               # scattered common-word (n==1) matches don't localize
            for k in range(n):
                block_hits[ref_vi[a + k]] = block_hits.get(ref_vi[a + k], 0) + 1

    # ---- janvier-as-apparatus-filter: contiguous runs of >= apparatus_min page tokens anchoring to NO
    #      janvier token are interleaved non-verse material (footnotes/annotations) -> drop from spans ----
    apparatus_idx: set[int] = set()
    if drop_apparatus:
        anchored = set(ref2in.values())
        j = 0
        while j < len(in_f):
            if j in anchored:
                j += 1; continue
            k = j
            while k < len(in_f) and k not in anchored:
                k += 1
            if k - j >= apparatus_min:
                apparatus_idx.update(range(j, k))
            j = k

    # ---- VS-2: localize using CONTIGUOUS-block evidence (>= block_min consecutive matched tokens), NOT
    #      scattered high-frequency function words ("the"/"of"/"God"), which can localize unrelated prose ----
    strong = [vi for vi, c in block_hits.items() if c >= min_anchor]
    if not strong:                                       # nothing anchors -> no-locate (caller surfaces OPEN)
        return {}
    lo, hi = min(strong), max(strong)
    n_in = len(in_f)

    # per-verse FIRST/LAST matched input position (from all matches), for local-evidence boundary placement.
    def _verse_ref_span(vi: int) -> tuple[int, int]:
        s = first.get(vi)
        if s is None:
            return (0, 0)
        e = len(ref_tok)
        for j in range(vi + 1, len(verses)):
            if j in first:
                e = first[j]
                break
        return (s, e)

    anchor_first: dict[int, int | None] = {}
    anchor_last: dict[int, int | None] = {}
    anchor_hits: dict[int, int] = {}
    for vi in range(lo, hi + 1):
        s, e = _verse_ref_span(vi)
        js = [ref2in[i] for i in range(s, e) if i in ref2in]
        anchor_hits[vi] = len(js)
        anchor_first[vi] = min(js) if js else None
        anchor_last[vi] = max(js) if js else None

    # ---- boundary placement (local-evidence): an anchored verse starts at its own first anchor; an
    #      un-anchored verse is interpolated LOCALLY within the gap (predecessor's last anchor, successor's
    #      first anchor) so it can NEVER encroach past a real anchor on either side. This is the No Silent
    #      Degradation fix: a well-recognized verse never silently loses its tail to a fabricated neighbor. ----
    starts: dict[int, int] = {}
    for vi in range(lo, hi + 1):
        af_vi = anchor_first[vi]
        if af_vi is not None:
            starts[vi] = af_vi
    starts[lo] = 0                                        # page opens mid-chapter -> lead tokens belong to `lo`
    vi = lo + 1
    while vi <= hi:
        if vi in starts:                                 # anchored -> already placed
            vi += 1; continue
        run_lo = vi                                       # a maximal run of consecutive un-anchored verses
        while vi <= hi and anchor_first[vi] is None:
            vi += 1
        run_hi = vi - 1
        pred, succ = run_lo - 1, run_hi + 1               # both are anchored (lo & hi are in `strong`)
        al = anchor_last.get(pred)
        af = anchor_first.get(succ)
        lo_bound = (al + 1) if al is not None else starts.get(pred, 0)
        hi_bound = af if (succ <= hi and af is not None) else n_in
        lo_bound = min(lo_bound, n_in)
        hi_bound = max(hi_bound, lo_bound)
        weights = [max(1, exp_len.get(k, 1)) for k in range(run_lo, run_hi + 1)]
        totw = sum(weights)
        acc = 0
        for k, w in zip(range(run_lo, run_hi + 1), weights):
            starts[k] = int(round(lo_bound + (hi_bound - lo_bound) * (acc / totw))) if totw else lo_bound
            acc += w
    # enforce monotonic non-decreasing, clamp to [0, n_in]
    last = 0
    for vi in range(lo, hi + 1):
        s = min(max(starts.get(vi, last), last), n_in)
        starts[vi] = s
        last = s

    # ---- emit spans + VS-4 length-sanity ----
    out: dict[int, dict] = {}
    for vi in range(lo, hi + 1):
        v = verses[vi][0]
        s_in = starts[vi]
        e_in = starts[vi + 1] if vi + 1 <= hi else n_in
        # raw-token extent [raw_lo, raw_hi) this verse spans in the INPUT tokens (emitted as tok_lo/tok_hi).
        # verse_geom maps this range -> page-line indices -> pixel bands so R3 crops target the flagged verse.
        # Equals the emitted `text` verbatim on a CLEAN cut; on an apparatus-filtered cut `text` drops interior
        # apparatus tokens while [tok_lo, tok_hi) stays the COARSE extent (a crop legitimately covers those
        # lines). Consecutive verses tile it (raw_hi[v] == raw_lo[v+1]) because e_in[v] == s_in[v+1].
        raw_lo = keep[s_in] if s_in < len(keep) else len(raw)
        raw_hi = keep[e_in] if e_in < len(keep) else len(raw)
        if apparatus_idx:                                    # filter interleaved apparatus token-by-token
            span = " ".join(raw[keep[j]] for j in range(s_in, e_in)
                            if j < len(keep) and j not in apparatus_idx).strip()
        else:
            span = " ".join(raw[raw_lo:raw_hi]).strip()
        got = _flen(span)
        exp = exp_len.get(vi, 0)
        ratio = (got / exp) if exp else (0.0 if got == 0 else float("inf"))
        reasons = []
        if anchor_hits.get(vi, 0) == 0:
            reasons.append("no-anchor")
        if exp and not (1.0 / len_k <= ratio <= len_k):
            reasons.append(f"len-{'long' if ratio > 1 else 'short'}({ratio:.2f}x)")
        if not span:
            reasons.append("empty")
        out[v] = {
            "text": span,
            "ref": verses[vi][1],
            "present": True,
            "open": bool(reasons),
            "reason": ",".join(reasons),
            "len_ratio": round(ratio, 3) if ratio != float("inf") else None,
            "anchor": anchor_hits.get(vi, 0),
            "exp_len": exp,
            "got_len": got,
            "tok_lo": raw_lo,
            "tok_hi": raw_hi,
        }
    return out


def segment_book_chapter(text: str, book: str, chapter: int, **kw) -> dict[int, dict]:
    """Convenience: pull janvier's chapter grid and segment. Empty dict if janvier lacks the chapter."""
    cv = chapter_verses(book, chapter, JANVIER)
    return segment(text, cv, **kw) if cv else {}


# --------------------------------------------------------------------------- #
# self-check: localize a mid-chapter slice; verify clean 1-verse spans + OPEN flagging
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    ok = True
    cv = chapter_verses("psalms", 118, JANVIER)
    assert len(cv) == 176, f"expected 176 janvier verses in Ps 118, got {len(cv)}"

    # Build a synthetic "page" = the exact janvier text of verses 9..16 concatenated (no verse numbers),
    # as if a recognizer had read that slice perfectly. A correct segmenter must (a) localize to 9..16,
    # (b) cut each verse cleanly (len_ratio ~ 1, no OPEN), (c) reproduce each verse's content.
    lo, hi = 9, 16
    page = " ".join(cv[v] for v in range(lo, hi + 1))
    seg = segment(page, cv)
    got_range = (min(seg), max(seg)) if seg else (None, None)
    print(f"[localize] page = janvier vv{lo}-{hi}; segmenter localized to {got_range}  (expect ({lo}, {hi}))")
    ok = ok and got_range == (lo, hi)

    from char_identity import fold_modern, edit_ratio
    worst = 1.0
    n_open = 0
    for v in range(lo, hi + 1):
        r = seg.get(v, {})
        cid = edit_ratio(fold_modern(r.get("text", "")), fold_modern(cv[v]))
        worst = min(worst, cid)
        n_open += int(r.get("open", True))
        flag = "  OPEN:" + r.get("reason", "") if r.get("open") else ""
        print(f"  v{v:>3} id={cid:.3f} len_ratio={r.get('len_ratio')} anchor={r.get('anchor')}{flag}")
    print(f"[clean-cut] worst per-verse content-id={worst:.3f} (expect >= 0.95);  OPEN verses={n_open} (expect 0)")
    ok = ok and worst >= 0.95 and n_open == 0

    # off-page rejection: a page of Ps 118 vv9-16 must NOT localize into a far verse (e.g. 120)
    ok = ok and 120 not in seg and 1 not in seg

    # no-locate: unrelated text over this chapter grid -> empty dict (a no-locate OPEN the caller surfaces)
    empty = segment("xqz mmm lll ttt zzz qqq vbn plmk foo bar baz", cv)
    print(f"[no-locate] unrelated text -> {len(empty)} verses (expect 0)")
    ok = ok and empty == {}

    # apparatus filter: interleave a 10-token "footnote" run between vv12 and vv13; drop_apparatus must
    # excise it (janvier-as-apparatus-filter) and restore clean per-verse content the plain cut pollutes.
    foot = "this is an interleaved footnote annotation gloss commentary paratext insertion here"  # 12 toks
    poll = " ".join([cv[9], cv[10], cv[11], cv[12], foot, cv[13], cv[14], cv[15], cv[16]])
    seg_off = segment(poll, cv)                                  # trim-and-join absorbs the footnote
    seg_on = segment(poll, cv, drop_apparatus=True)             # filter should excise it
    off12 = edit_ratio(fold_modern(seg_off.get(12, {}).get("text", "")), fold_modern(cv[12]))
    on12 = edit_ratio(fold_modern(seg_on.get(12, {}).get("text", "")), fold_modern(cv[12]))
    print(f"[apparatus] v12 content: no-drop={off12:.3f}  drop={on12:.3f}  (expect drop >> no-drop, drop ~1.0)")
    ok = ok and on12 >= 0.98 and (on12 - off12) >= 0.2

    # regression (review #1, No Silent Degradation): an un-anchored junk verse next to a good one must NOT
    # steal the good verse's tail. page = janvier vv48,49, JUNK(for v50), 51,52 — v49 must keep full content.
    pg = " ".join([cv[48], cv[49], "xxq yyw zzr aab bbc", cv[51], cv[52]])
    s2 = segment(pg, cv)
    v49id = edit_ratio(fold_modern(s2.get(49, {}).get("text", "")), fold_modern(cv[49]))
    print(f"[review#1 no-steal] v49 content-id={v49id:.3f} len_ratio={s2.get(49, {}).get('len_ratio')}  "
          f"(expect ~1.0; pre-fix truncated to 0.536)")
    ok = ok and v49id >= 0.95

    # regression (review #2): unrelated same-vocabulary prose (Genesis 24:1-5) must NOT localize onto the
    # Psalms 118 grid via scattered common words ("the"/"of"/"and").
    gen = chapter_verses("genesis", 24, JANVIER)
    foreign = " ".join(gen[v] for v in list(gen)[:5])
    s3 = segment(foreign, cv)
    print(f"[review#2 no-mislocalize] Gen24 text vs Ps118 grid -> {len(s3)} verses (expect <=2; pre-fix 32)")
    ok = ok and len(s3) <= 2

    print("\nSELF-CHECK:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
