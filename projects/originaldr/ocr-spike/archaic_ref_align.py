#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""archaic_ref_align.py — realign the ARCHAIC reference to janvier's verse numbering (2026-07-27).

THE SYSTEMIC DEFECT, DIAGNOSED FROM THE TEXT ITSELF (Sir's THIRD). At the 517 loci where the OCR agrees with
janvier above 0.9 while the archaic reference agrees with janvier at 0.017, the archaic entry is not missing
and not corrupt — **it is the NEIGHBOURING VERSE**:

    psalms/1/5   s_dismas: "The impious not ſo: but as duſt…"        = Ps 1:4   janvier: Ps 1:5
    psalms/3/1   s_dismas: "Lord why are they multiplied…"           = Ps 3:2   janvier: the SUPERSCRIPTION
    psalms/4/1   s_dismas: "VVhen I inuocated…"                      = Ps 4:2   janvier: the SUPERSCRIPTION

**s_dismas does not count the Psalm superscription ("The Psalm of David, when he fled from Absalom") as verse
1; janvier does.** Every verse in such a psalm is therefore shifted by exactly one, which is a known
Vulgate/DR numbering divergence and not an error in either witness. 306 of the 467 mismatched loci are psalms,
and 29 of 45 "overlong" entries are psalms too — a merge that is what a one-verse shift looks like at a
chapter boundary.

WHY REALIGN RATHER THAN DISCOUNT. The day-1 rule (archaic governs where it has text of its own, else modern)
would hand these 1535 records to janvier — correct, but it throws away a real archaic witness that IS present,
merely indexed differently. Recovering the alignment keeps the diplomatic reference for those verses, which is
the reference this project actually needs.

METHOD — the same monotone-offset technique that resolved the tome-map join, one level down. Per (book,
chapter), score every small shift by mean `floor_modern` (archaic-vs-modern agreement, NO OCR involved, so
this cannot be tuned to flatter the OCR) and adopt a shift only when it beats zero-offset by a clear margin.
A chapter with a genuine textual divergence stays low at EVERY offset and is left alone — the same signature
that distinguished a shifted tome-map index from a wrong one.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import char_identity as CI          # noqa: E402

OFFSETS = (-2, -1, 0, 1, 2)
MIN_VERSES = 4          # a chapter needs enough overlap for a shift to be evidence rather than coincidence
MIN_GAIN = 0.15         # the shift must beat offset 0 by this much in mean floor_modern
MIN_ABS = 0.60          # ...and reach this, or the chapter is genuinely divergent, not merely shifted
_LOCUS = re.compile(r"^scripture/([^/]+)/(\d+)/(\d+)$")


def _key(book, ch, v):
    return f"scripture/{book}/{ch}/{v}"


def detect(archaic: dict, modern: dict) -> dict:
    """{(book, chapter): {offset, gain, base, best, n}} for chapters whose archaic reference is SHIFTED."""
    by_ch = defaultdict(list)
    for locus in archaic:
        m = _LOCUS.match(locus)
        if m and locus in modern:
            by_ch[(m.group(1), int(m.group(2)))].append(int(m.group(3)))
    out = {}
    for (book, ch), verses in by_ch.items():
        if len(verses) < MIN_VERSES:
            continue
        scores = {}
        for off in OFFSETS:
            vals = []
            for v in verses:
                a = archaic.get(_key(book, ch, v + off))
                mo = modern.get(_key(book, ch, v))
                if a and mo:
                    f = CI.floor_modern(a, mo)
                    if f is not None:
                        vals.append(f)
            if len(vals) >= MIN_VERSES:
                scores[off] = mean(vals)
        if not scores or 0 not in scores:
            continue
        best = max(scores, key=lambda o: scores[o])
        if best != 0 and scores[best] - scores[0] >= MIN_GAIN and scores[best] >= MIN_ABS:
            out[(book, ch)] = {"offset": best, "base": round(scores[0], 4), "best": round(scores[best], 4),
                               "gain": round(scores[best] - scores[0], 4), "n": len(verses),
                               "profile": {str(o): round(s, 4) for o, s in sorted(scores.items())}}
    return out


def apply(archaic: dict, archaic_src: dict, shifts: dict) -> tuple[dict, dict]:
    """Return a realigned archaic reference: verse v takes the entry indexed v+offset for shifted chapters.

    The provenance is amended too — a realigned entry is still s_dismas/odr_com text, but the reader must be
    able to see that its INDEX was corrected, so it is never mistaken for an untouched reading."""
    out, src = dict(archaic), dict(archaic_src)
    for (book, ch), info in shifts.items():
        off = info["offset"]
        moved = {}
        for locus in list(archaic):
            m = _LOCUS.match(locus)
            if not m or m.group(1) != book or int(m.group(2)) != ch:
                continue
            v = int(m.group(3))
            srcloc = _key(book, ch, v + off)
            if srcloc in archaic:
                moved[locus] = archaic[srcloc]
        for locus, text in moved.items():
            out[locus] = text
            src[locus] = (archaic_src.get(locus, "?") or "?") + f"+realigned{off:+d}"
        for locus in list(out):
            m = _LOCUS.match(locus)
            if m and m.group(1) == book and int(m.group(2)) == ch and locus not in moved:
                # no source verse at v+offset -> this locus has no archaic text of its own any more.
                out.pop(locus, None)
                src.pop(locus, None)
    return out, src


# --------------------------------------------------------------------------------------------------
# PIECEWISE ALIGNMENT — the shift that starts MID-CHAPTER
# --------------------------------------------------------------------------------------------------
SWITCH_COST = 0.55      # cost of changing offset mid-chapter: a shift is rare, so make the DP pay for one
PIECE_MIN_GAIN = 0.12   # piecewise must beat the best UNIFORM offset by this much in mean floor_modern
PIECE_MIN_RUN = 3       # a segment shorter than this is noise, not a shift


def detect_piecewise(archaic: dict, modern: dict) -> dict:
    """{(book, chapter): {v -> offset}} for chapters whose archaic reference shifts PART-WAY THROUGH.

    WHY `detect` MISSES THESE, AND IT IS NOT A THRESHOLD PROBLEM. `detect` fits ONE offset per chapter and
    scores it over every verse, so a tail shift is averaged against the aligned head and can never clear
    MIN_GAIN. Genesis 1 is the clean case: verses 1–25 are aligned and 26–31 are shifted by one, so at
    offset −1 the 25 correct verses drag the mean below offset 0 and the chapter is declared sound. Those six
    verses are then scored against the wrong reference, which is why **Genesis 1 is the worst chapter in the
    book for all four witnesses at once** — the signature of a vertical defect. Genesis 26 is worse: 29 verses
    shifted, and the offset itself grows from −1 to −2 part-way down.

    METHOD — the same monotone DP used for page addressing, one level down. State is the offset; emission is
    `floor_modern` (archaic vs MODERN, so no OCR is involved and this cannot be tuned to flatter the
    recognizer); changing offset costs `SWITCH_COST`, so the solver prefers one segment and buys a second only
    when the text pays for it. Adopted only when it beats the best UNIFORM offset by `PIECE_MIN_GAIN` — a
    chapter that is genuinely divergent scores low at every offset and in every segmentation, and is left
    alone."""
    by_ch = defaultdict(list)
    for locus in archaic:
        m = _LOCUS.match(locus)
        if m and locus in modern:
            by_ch[(m.group(1), int(m.group(2)))].append(int(m.group(3)))
    out = {}
    for (book, ch), verses in by_ch.items():
        vs = sorted(verses)
        if len(vs) < MIN_VERSES:
            continue
        sc = {}
        for v in vs:
            mo = modern.get(_key(book, ch, v))
            for off in OFFSETS:
                a = archaic.get(_key(book, ch, v + off))
                f = CI.floor_modern(a, mo) if (a and mo) else None
                sc[(v, off)] = f if f is not None else 0.0
        uniform = {off: mean([sc[(v, off)] for v in vs]) for off in OFFSETS}
        best_uniform = max(uniform.values())
        # Viterbi over offsets
        prev = {off: (sc[(vs[0], off)], [off]) for off in OFFSETS}
        for v in vs[1:]:
            cur = {}
            for off in OFFSETS:
                cand = max(((prev[p][0] - (0.0 if p == off else SWITCH_COST), p) for p in OFFSETS),
                           key=lambda t: t[0])
                cur[off] = (cand[0] + sc[(v, off)], prev[cand[1]][1] + [off])
            prev = cur
        score, path = max(prev.values(), key=lambda t: t[0])
        piece = mean([sc[(v, o)] for v, o in zip(vs, path)])
        if len(set(path)) == 1 or piece - best_uniform < PIECE_MIN_GAIN or piece < MIN_ABS:
            continue
        # drop runs too short to be evidence
        runs, i = [], 0
        while i < len(path):
            j = i
            while j + 1 < len(path) and path[j + 1] == path[i]:
                j += 1
            runs.append((i, j, path[i]))
            i = j + 1
        keep = {}
        for i, j, off in runs:
            if off != 0 and (j - i + 1) >= PIECE_MIN_RUN:
                for k in range(i, j + 1):
                    keep[vs[k]] = off
        if keep:
            out[(book, ch)] = {"offsets": keep, "uniform_best": round(best_uniform, 4),
                               "piecewise": round(piece, 4), "gain": round(piece - best_uniform, 4)}
    return out


def apply_piecewise(archaic: dict, archaic_src: dict, pieces: dict) -> tuple[dict, dict]:
    """Per-VERSE realignment. Same provenance rule as `apply`: a corrected index must be visible as one."""
    out, src = dict(archaic), dict(archaic_src)
    for (book, ch), info in pieces.items():
        moved = {}
        for v, off in info["offsets"].items():
            srcloc = _key(book, ch, int(v) + off)
            if srcloc in archaic:
                moved[_key(book, ch, int(v))] = (archaic[srcloc], off)
        for locus, (text, off) in moved.items():
            out[locus] = text
            src[locus] = (archaic_src.get(locus, "?") or "?") + f"+realigned{off:+d}"
    return out, src


if __name__ == "__main__":
    import qc_audit as QA
    archaic, modern, asrc, _msrc = QA.build_refs()
    shifts = detect(archaic, modern)
    print(f"chapters with a SHIFTED archaic reference: {len(shifts)}")
    byb = defaultdict(int)
    for (b, _c) in shifts:
        byb[b] += 1
    print("  by book: " + " · ".join(f"{b}={n}" for b, n in sorted(byb.items())))
    for (b, c), i in sorted(shifts.items())[:8]:
        print(f"    {b}/{c:<4} offset {i['offset']:+d}  floor_modern {i['base']} -> {i['best']}  "
              f"(n={i['n']})  profile={i['profile']}")
    new_arc, new_src = apply(archaic, asrc, shifts)

    def coverage(a):
        vals = [CI.floor_modern(a[k], modern[k]) for k in a if k in modern]
        vals = [v for v in vals if v is not None]
        return len(vals), mean(vals), sum(1 for v in vals if v >= 0.90) / len(vals)
    n0, m0, p0 = coverage(archaic)
    n1, m1, p1 = coverage(new_arc)
    print(f"\narchaic-vs-modern agreement over all loci with both refs:")
    print(f"  before  n={n0}  mean floor_modern {m0:.4f}  >=0.90 on {100*p0:.1f}%")
    print(f"  after   n={n1}  mean floor_modern {m1:.4f}  >=0.90 on {100*p1:.1f}%")
    (HERE / "archaic-realignment.json").write_text(json.dumps(
        {"n_chapters_shifted": len(shifts),
         "shifts": {f"{b}/{c}": i for (b, c), i in sorted(shifts.items())},
         "before": {"n": n0, "mean_floor_modern": round(m0, 4), "frac_ge_090": round(p0, 4)},
         "after": {"n": n1, "mean_floor_modern": round(m1, 4), "frac_ge_090": round(p1, 4)}},
        ensure_ascii=False, indent=1))
    print("-> wrote archaic-realignment.json")
