#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""layout_profile.py — GOLD-FREE per-page layout fingerprint: which schema should this page be read with?

THE PROPOSAL THIS TESTS (Sir, 2026-07-27): each book of the DR prints its own layout and its own symbol
conventions, so instead of one segmenter for the whole corpus we should DETECT the regime and dispatch to a
schema fitted to it. The prerequisite for that is a detector that can tell the regimes apart WITHOUT gold —
because at production time gold is exactly what we do not have.

This module computes signals that are all available at runtime from the recognizer's own output (line text +
bounding boxes), and nothing else:

    dagger_frac     fraction of body lines carrying † / ‡        — OT verse-marking regime
    numeral_frac    fraction carrying a printed "N." verse number — NT 1582 regime (SELF-LABELLING)
    star_frac       fraction carrying * or ‖                      — annotation-reference density
    short_frac      fraction of lines much shorter than the median — verse-per-line / poetic setting
    indent_var      spread of line left edges (fraction of width) — flush-left prose vs indented verse
    right_ragged    spread of line right edges                    — justified prose vs ragged verse
    lines_per_verse body lines / janvier verses on the page       — paragraph vs verse-per-line density

The question this file answers is narrow and empirical: DO THESE SIGNALS SEPARATE THE REGIMES WE ALREADY KNOW
ARE DIFFERENT? If they do not, book-specific dispatch cannot be built on them and a different signal is needed
(that would be a useful negative result). If they do, the dispatcher is a lookup away.

Usage: ../ocr-venv/bin/python layout_profile.py        # profile every cached gold page
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import verse_seg as VS  # noqa: E402

DAGGER = re.compile(r"[†‡]")
NUMERAL = re.compile(r"(?:(?<=\s)|^)(\d{1,3})\.(?=\s|$)")
STAR = re.compile(r"[*‖″]")


def _spread(vals: list[float]) -> float:
    """Robust spread: inter-decile range. Resistant to one stray line, unlike min/max."""
    if len(vals) < 3:
        return 0.0
    v = sorted(vals)
    lo = v[max(0, int(0.10 * (len(v) - 1)))]
    hi = v[min(len(v) - 1, int(0.90 * (len(v) - 1)))]
    return hi - lo


def profile(page_result: dict, book: str | None = None, chapter: int | None = None) -> dict:
    """Gold-free layout fingerprint of one page. `book`/`chapter` are optional and only used for the
    lines-per-verse density (janvier tells us how many verses the page's chapter holds)."""
    lines = [l for l in page_result.get("lines", []) if l.get("role") == "body" and (l.get("text") or "").strip()]
    if not lines:
        return {"n_body": 0}
    W = float(page_result.get("page_px", (1, 1))[0]) or 1.0
    texts = [l["text"] for l in lines]
    n = len(lines)
    lens = [len(t) for t in texts]
    med = median(lens) or 1

    boxes = [l.get("bbox") for l in lines if l.get("bbox")]
    x0s = [b[0] / W for b in boxes]
    x1s = [b[2] / W for b in boxes]

    prof = {
        "n_body": n,
        "dagger_frac": round(sum(1 for t in texts if DAGGER.search(t)) / n, 3),
        "numeral_frac": round(sum(1 for t in texts if NUMERAL.search(t)) / n, 3),
        "star_frac": round(sum(1 for t in texts if STAR.search(t)) / n, 3),
        "short_frac": round(sum(1 for L in lens if L < 0.6 * med) / n, 3),
        "indent_var": round(_spread(x0s), 3),
        "right_ragged": round(_spread(x1s), 3),
    }
    if book and chapter:
        janv = VS.chapter_verses(book, chapter, VS.JANVIER)
        on_page = max(1, len(janv))
        prof["lines_per_verse"] = round(n / on_page, 3)
    return prof


def classify(prof: dict) -> dict:
    """Dispatch a page to a reading schema from its fingerprint alone.

    The thresholds are read off the measured gold-page profiles (see __main__) and are deliberately coarse —
    the point is to show the regimes are SEPARABLE, not to over-fit 14 pages. Returns {schema, why}.
    """
    if prof.get("n_body", 0) == 0:
        return {"schema": "unknown", "why": "no body lines"}
    if prof.get("numeral_frac", 0) >= 0.25:
        return {"schema": "nt-numeral",
                "why": f"printed verse numerals on {prof['numeral_frac']:.0%} of body lines — "
                       "self-labelling boundaries, the strongest regime"}
    if prof.get("dagger_frac", 0) >= 0.25:
        return {"schema": "ot-dagger-verse-per-line" if prof.get("short_frac", 0) >= 0.25
                else "ot-dagger-paragraph",
                "why": f"† on {prof['dagger_frac']:.0%} of lines; short-line fraction "
                       f"{prof.get('short_frac', 0):.0%} distinguishes verse-per-line from paragraph setting"}
    if prof.get("dagger_frac", 0) > 0:
        return {"schema": "ot-under-marked",
                "why": f"† present but sparse ({prof['dagger_frac']:.0%}) — markers alone cannot cut every "
                       "verse; boundaries must be completed from the reference text"}
    return {"schema": "unmarked",
            "why": "no printed verse markers — fall back to text-anchored localization"}


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    from gate_calibrate import LOCI, gold_by_chapter, cached_page

    GT = HERE / "ground-truth"
    print(f"{'slug':<27} {'book':<9} {'†frac':>6} {'Nfrac':>6} {'*frac':>6} {'short':>6} "
          f"{'indent':>7} {'ragged':>7} {'l/v':>5}  schema")
    for slug in sorted(LOCI):
        gt = json.loads((GT / f"{slug}.json").read_text())
        book = LOCI[slug]
        r = cached_page(slug, gt.get("ocr_dir"), gt.get("page_index"))
        chs = sorted(gold_by_chapter(gt))
        p = profile(r, book, chs[0] if chs else None)
        c = classify(p)
        print(f"{slug:<27} {book:<9} {p['dagger_frac']:>6} {p['numeral_frac']:>6} {p['star_frac']:>6} "
              f"{p['short_frac']:>6} {p['indent_var']:>7} {p['right_ragged']:>7} "
              f"{p.get('lines_per_verse', 0):>5}  {c['schema']}")
