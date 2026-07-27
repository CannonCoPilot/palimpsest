#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verse_numbers.py — recover the PRINTED VERSE NUMBERS the pipeline currently throws away.

THE PROBLEM (visual inspection of ot2-1610 pp215-236, 2026-07-27). The DR body DOES number its verses:
Psalm 118 prints the number inline immediately before the dagger — `14 † I am delighted...` — and Psalm 119
prints it in the right margin. That number is a SELF-LABELLING marker, the strongest class we have: unlike a
bare †, it cannot produce an off-by-one, because it says which verse it opens.

We lose it twice over:
  1. `layout.strip_verse_numbers` deletes digit-only tokens, documented on the claim that the DR body marks
     verses "with † / ‡, never digits". The page disproves that claim.
  2. Worse, and upstream: kraken's line polygons usually START AT THE DAGGER, so the number sits outside the
     recognized line and never reaches the text at all. Surveying the 14 cached gold pages, an `N †` opening
     survives in the OCR exactly ONCE. It is not being stripped — it is never being read.

So recovery is an IMAGE-level operation: crop the sliver immediately left of each verse-opening line and read
it. The crops are tiny and there is one per verse opening, so this is cheap next to any re-OCR of the page.

The geometry and parsing here are pure functions over a `reocr_page` dict and are unit-tested hermetically;
the reader is INJECTED (`transcribe`), so the module can be tested with no model at all and driven by olmOCR
in production.

NO SILENT DEGRADATION: a number that is read but does not fit the expected monotone sequence is reported as
`suspect` rather than used. A wrong verse number is worse than no verse number — it would relabel a correct
span with confidence.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

MARKER = re.compile(r"[†‡]")
NUM = re.compile(r"\d{1,3}")


def _q(vals, p):
    if not vals:
        return 0.0
    v = sorted(vals)
    return v[max(0, min(len(v) - 1, int(p * (len(v) - 1))))]


def verse_opening_lines(page_result: dict) -> list[int]:
    """Indices of body lines that open a verse — i.e. carry a verse marker. These are the only lines whose
    left gutter can hold a verse number, so they are the only ones worth cropping."""
    return [i for i, l in enumerate(page_result.get("lines", []))
            if l.get("role") == "body" and l.get("bbox") and MARKER.search(l.get("text") or "")]


def gutter_crops(page_result: dict, *, width_frac: float = 0.06, context_frac: float = 0.30,
                 pad_frac: float = 0.006, min_h_frac: float = 0.010) -> dict[int, tuple]:
    """{body line index -> fractional crop of the sliver LEFT of that line} for every verse opening.

    The strip starts `width_frac` of the page width left of the line's own edge and — CRUCIALLY — extends
    `context_frac` INTO the line. A bare sliver holding only the digits was measured to recover NOTHING from
    olmOCR on all 7 openings of the psalms-118 page: a vision model given two glyphs and no context returns
    nothing usable. The same crops widened to include the opening words returned "105 † a Thy word is a lampe"
    and read the number correctly. The number is cheap to isolate afterwards (it precedes the dagger); the
    context is what makes it readable at all.

    Pure geometry — no image is touched here."""
    W, H = page_result["page_px"]
    out: dict[int, tuple] = {}
    for i in verse_opening_lines(page_result):
        x0, y0, x1, y1 = page_result["lines"][i]["bbox"]
        cx0 = max(0.0, (x0 - width_frac * W) / W)
        cx1 = max(cx0 + 1e-3, min(1.0, (x0 + context_frac * W) / W))
        cy0 = max(0.0, (y0 - pad_frac * H) / H)
        cy1 = min(1.0, (y1 + pad_frac * H) / H)
        if cy1 - cy0 < min_h_frac:                      # a very flat box gives the reader nothing to work on
            c = (cy0 + cy1) / 2
            cy0, cy1 = max(0.0, c - min_h_frac / 2), min(1.0, c + min_h_frac / 2)
        out[i] = (cx0, cy0, cx1, cy1)
    return out


# Digit shapes this typeface's OCR confuses. Applied ONLY to the token immediately before a dagger, where
# position already guarantees the token IS a verse number — "III †" for 111 and "1c9 †" for 109 both occur on
# the psalms-118 page. Applying these substitutions to free text would corrupt words; applying them to a slot
# known to hold a number is just reading the glyph correctly.
_DIGITISE = str.maketrans({"I": "1", "l": "1", "i": "1", "O": "0", "o": "0", "c": "0", "S": "5", "|": "1"})
_BEFORE_MARKER = re.compile(r"(\S+)\s*[†‡]")


def parse_number(text: str) -> int | None:
    """The verse number in a gutter reading, or None.

    Prefers the token immediately BEFORE the dagger — position identifies it as the verse number regardless of
    how well the glyphs were read — and only then falls back to the last plain number in the strip. The strip
    deliberately includes context, so it may also clip a marginal key or the previous line's tail; taking the
    marker-adjacent token avoids mistaking those for the verse."""
    if not text:
        return None
    for tok in _BEFORE_MARKER.findall(text):
        cand = tok.translate(_DIGITISE)
        if cand.isdigit() and 1 <= int(cand) <= 200:
            return int(cand)
    nums = NUM.findall(text)
    if not nums:
        return None
    v = int(nums[-1])
    return v if 1 <= v <= 200 else None


def vet_sequence(found: dict[int, int], expected: list[int] | None = None) -> dict[int, dict]:
    """Accept only numbers that fit a MONOTONE reading-order sequence; mark the rest suspect.

    A misread gutter ("18" read as "8", a marginal key mistaken for a number) would relabel a correct span
    with false confidence — strictly worse than recovering nothing. Reading order down the page must give
    non-decreasing verse numbers, which is a cheap and strong check; `expected` (the chapter's janvier verse
    list) additionally rejects a number that is not a verse of this chapter at all."""
    out: dict[int, dict] = {}
    prev = None
    exp = set(expected or [])
    for idx in sorted(found):
        v = found[idx]
        reasons = []
        if prev is not None and v < prev:
            reasons.append(f"out-of-order (after {prev})")
        if exp and v not in exp:
            reasons.append("not a verse of this chapter")
        ok = not reasons
        out[idx] = {"verse": v, "ok": ok, "reason": ",".join(reasons)}
        if ok:
            prev = v
    return out


def recover(page_result: dict, ocr_dir: str, page_index: int, *, transcribe=None,
            expected: list[int] | None = None, **crop_kw) -> dict:
    """Read the verse number in each verse opening's left gutter.

    `transcribe(ocr_dir, page_index, crop=..., verse=None) -> str` is injected (default: olmOCR via reocr_r3),
    so this is testable with no model. Returns {"numbers": {line_idx -> {verse, ok, reason}}, "n_read",
    "n_accepted", "notes"}.
    """
    if transcribe is None:
        import reocr_r3

        def transcribe(od, pi, *, crop=None, verse=None):
            return reocr_r3.r3_transcribe(od, pi, crop=crop)

    crops = gutter_crops(page_result, **crop_kw)
    raw: dict[int, int] = {}
    notes: list[str] = []
    for idx, crop in crops.items():
        try:
            txt = transcribe(ocr_dir, page_index, crop=crop, verse=None)
        except Exception as e:                          # a failed strip is an absence, never a guess
            notes.append(f"line {idx}: gutter read failed ({type(e).__name__})")
            continue
        v = parse_number(txt)
        if v is not None:
            raw[idx] = v
    vetted = vet_sequence(raw, expected)
    n_ok = sum(1 for d in vetted.values() if d["ok"])
    if len(crops) and not n_ok:
        notes.append(f"no verse number recovered from {len(crops)} gutter strips — this page either does not "
                     "print them or prints them somewhere else (e.g. the right margin, as Psalm 119 does)")
    return {"numbers": vetted, "n_crops": len(crops), "n_read": len(raw), "n_accepted": n_ok, "notes": notes}


def anchors(page_result: dict, recovered: dict) -> dict[int, int]:
    """{verse number -> body line index} for the accepted numbers — SELF-LABELLING localization anchors.

    This is the payload the segmenters want: it fixes not just where a verse boundary is but WHICH verse it
    is, which is exactly the information the anchor-walk and the labelling DP otherwise have to infer."""
    return {d["verse"]: idx for idx, d in recovered.get("numbers", {}).items() if d["ok"]}
