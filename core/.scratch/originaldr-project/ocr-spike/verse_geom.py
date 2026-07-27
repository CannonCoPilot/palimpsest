#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verse_geom.py — verse -> pixel-band crop geometry (§8 R3-4; the bridge that makes R3 targetable).

THE problem this solves: the cross-source gate (`xsrc_gate`) flags WHICH janvier verses diverge, but it works
on the JOINED body-text string — the mapping from a flagged verse back to PIXELS is lost in the join. And
olmOCR (the R3 local backend) only beats R2 on CROPS; it repetition-loops on a full dense page. So R3 is only
useful if we can turn a flagged verse into the precise pixel band to re-read.

The map is reconstructed from a `reocr_core.reocr_page` result (no re-segmentation of the image — reocr_page
already carries per-line text + role + bbox):

    verse  --verse_seg.segment(tok_lo,tok_hi)-->  raw-token range in the body text
           --build_body_tokmap(token->line)  -->  the body-line indices carrying those tokens
           --line bboxes (reocr_page)         -->  union pixel box  --> fractional crop (0..1) for reocr_r3

GOLD-FREE (janvier grid + the page's own geometry; no ground-truth). NO SILENT DEGRADATION: the reconstructed
body text is checked against the page's stored `r2_body`; on any drift it RAISES rather than emit a crop keyed
to the wrong pixels, and a verse that localizes but has no line geometry is returned as an explicit OPEN
(`crop=None, reason='no-geometry'`) for the caller to fall back on, never silently dropped.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import verse_seg  # noqa: E402  (path-inserted, like every module in this spike)

_VNUM = re.compile(r"\d{1,3}\.?")     # == layout.strip_verse_numbers' pure verse-number token


def build_body_tokmap(page_lines) -> tuple[str, list[int]]:
    """Reproduce `reocr_core`'s r2_body construction while recording each raw token's source line index.

    reocr_core builds `r2_body = strip_verse_numbers(norm(" ".join(body line texts)))`. Tokenizing each body
    line with str.split(), dropping the same pure verse-number tokens, and joining with single spaces yields
    the IDENTICAL token sequence (str.split collapses whitespace exactly as norm does). Returns
    (body_text, tok_line) where body_text == the page's r2_body and tok_line[j] is the index into page_lines
    of the body line that emitted raw token j."""
    toks: list[str] = []
    tok_line: list[int] = []
    for li, l in enumerate(page_lines):
        if l.get("role") != "body":
            continue
        for t in (l.get("text") or "").split():
            if _VNUM.fullmatch(t):        # strip_verse_numbers: the DR body marks verses with † / ‡, not digits
                continue
            toks.append(t)
            tok_line.append(li)
    return " ".join(toks), tok_line


def _union_frac(boxes_px, page_px, pad_frac: float, min_h_frac: float):
    """Union pixel boxes -> a padded fractional (0..1) crop (x0,y0,x1,y1), floored to min_h_frac tall so a
    near-flat baseline-only box still gives the vision model a readable strip."""
    W, H = page_px
    x0 = min(b[0] for b in boxes_px); y0 = min(b[1] for b in boxes_px)
    x1 = max(b[2] for b in boxes_px); y1 = max(b[3] for b in boxes_px)
    px, py = pad_frac * W, pad_frac * H

    def cl(v):
        return max(0.0, min(1.0, v))

    fx0, fy0, fx1, fy1 = cl((x0 - px) / W), cl((y0 - py) / H), cl((x1 + px) / W), cl((y1 + py) / H)
    if (fy1 - fy0) < min_h_frac:                        # baseline-only near-flat box -> grow around its centre
        c = (fy0 + fy1) / 2
        fy0, fy1 = max(0.0, c - min_h_frac / 2), min(1.0, c + min_h_frac / 2)
    if fx1 <= fx0:                                       # degenerate x (single-point geometry) -> full width
        fx0, fx1 = 0.0, 1.0
    return (fx0, fy0, fx1, fy1)


def verse_crops(page_result: dict, book: str, chapter: int, *, pad_frac: float = 0.02,
                min_h_frac: float = 0.012, seg_kwargs: dict | None = None,
                spans: dict[int, dict] | None = None) -> dict[int, dict]:
    """Map every janvier verse localized on this page to its pixel-band crop.

    page_result: a `reocr_core.reocr_page` dict — needs `page_px`, `r2_body`, and `lines` (each with
                 `text`, `role`, and `bbox`=(x0,y0,x1,y1) px or None).
    Returns {verse:int -> {crop:(x0,y0,x1,y1) frac | None, lines:[idx], open:bool, reason:str, ref:str,
             text:str}}. `crop` is ready for `reocr_r3.r3_transcribe(..., crop=crop)`.

    Aligns to the gate by re-segmenting the SAME r2_body the gate scored. Defaults to the gate's
    `drop_apparatus=True` (xsrc_gate.cross_source_verse_scores) so the localized verse set and OPEN flags match
    what the gate flagged — the crop BOX itself is invariant to drop_apparatus (that flag only changes the
    emitted verse text, never the tok_lo/tok_hi boundary extents). RAISES ValueError if the reconstructed body
    disagrees with the stored r2_body.

    `spans`: a PRE-COMPUTED segmentation ({verse -> {tok_lo, tok_hi, text, open, reason, ...}}, e.g. from
    `verse_locate.best_spans`) used instead of re-segmenting here. The gate and the geometry MUST agree on
    where each verse sits — if the gate scores an ALIGN span while the crop is cut from a WALK span, the verse
    that was flagged is not the verse that gets re-read. Threading ONE spans dict through both makes that
    structurally impossible rather than merely intended. Extents are RAW body-token indices either way (both
    segmenters publish that same coordinate system)."""
    page_lines = page_result["lines"]
    page_px = tuple(page_result["page_px"])
    body_text, tok_line = build_body_tokmap(page_lines)
    stored = page_result.get("r2_body")
    if stored is not None and body_text != stored:
        raise ValueError(
            "verse_geom: reconstructed body text disagrees with the stored r2_body (the line set or "
            "verse-number stripping drifted) — refusing to emit geometry keyed to the wrong pixels "
            "(No Silent Degradation).")

    if spans is not None:
        segs = spans
    else:
        kw = seg_kwargs if seg_kwargs is not None else {"drop_apparatus": True}   # match the gate's segmentation
        segs = verse_seg.segment_book_chapter(body_text, book, chapter, **kw)
    n_tok = len(tok_line)
    out: dict[int, dict] = {}
    for v, s in segs.items():
        if s.get("tok_lo") is None:      # a hybrid span the walk placed nowhere -> explicit OPEN, never dropped
            out[v] = {"crop": None, "lines": [], "open": True, "text": s.get("text", ""),
                      "ref": s.get("ref", ""),
                      "reason": (s.get("reason", "") + ",no-extent").lstrip(",")}
            continue
        lo, hi = s["tok_lo"], min(s["tok_hi"], n_tok)
        lines = sorted({tok_line[j] for j in range(lo, hi)})
        boxes = [page_lines[li].get("bbox") for li in lines if page_lines[li].get("bbox")]
        common = {"lines": lines, "open": bool(s.get("open")), "reason": s.get("reason", ""),
                  "ref": s.get("ref", ""), "text": s.get("text", "")}
        if not boxes:                                   # localized to tokens but no line geometry -> OPEN
            out[v] = {"crop": None, **{**common, "open": True,
                                       "reason": (common["reason"] + ",no-geometry").lstrip(",")}}
            continue
        out[v] = {"crop": _union_frac(boxes, page_px, pad_frac, min_h_frac), **common}
    return out


def _quantile(vals, q: float) -> float:
    """Linear-interpolated quantile (numpy's default method) over a small sample — kept local so verse_geom
    stays dependency-free."""
    xs = sorted(vals)
    if len(xs) == 1:
        return float(xs[0])
    pos = q * (len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return float(xs[lo] + (xs[hi] - xs[lo]) * (pos - lo))


def body_column(page_result: dict, *, q: float = 0.50, wide_frac: float = 0.50,
                default=(0.0, 1.0)) -> tuple[float, float]:
    """Fractional (x0, x1) of the main body text column, from the page's FULL-MEASURE body lines: x0 = the
    (1-q) quantile of their left edges, x1 = the q quantile of their right edges (q=0.50 => the median).
    Region crops are x-clipped to this so a stray wide line — a swallowed margin note — can't drag the crop
    into the outer margin (the genesis-24 e2e). Falls back to the full width if there is no body geometry.

    FULL-MEASURE, not all-lines (fix for the psalms R3 hard-zero, 2026-07-25): the DR psalms pages set short
    italic gloss fragments flush-right INSIDE the text block, and on a gloss-heavy page those fragments are the
    majority of the line count. Taking the median over every body line therefore lands the left edge inside the
    scripture column and clips the opening of each full line (psalms-001: median-over-all x0 = 0.310 vs the
    true column edge 0.161, i.e. 15% of page width of scripture silently cut off). Only lines at least
    `wide_frac` of the page wide actually define a column margin — the same population `layout.type_lines`
    uses. Measured effect: identical to 3 decimals on every 1-column prose gold page, materially wider on every
    psalms page, and it lifted containment of the flagged regions' own body lines from 0.456 to 0.675.

    WHY q STAYS AT THE MEDIAN — a MEASURED negative result, do not "fix" this again (2026-07-25). Raising q to
    0.90 widens the column to a near-full envelope and lifts that containment to 0.949, and the argument for it
    is seductive: clipped scripture is unrecoverable, whereas over-inclusion should be recoverable because the
    P5 janvier-cut discards unaligned material. THE MEASUREMENT REFUTES THAT ARGUMENT. On the 46 known-bad gold
    verses, scored as the mean over 4 crop variants (the low-variance estimator — a single run cannot resolve
    this, see r3_variance.py), q=0.90 scored WORSE than q=0.50: 0.6875 -> 0.6631, 18 verses worsened vs 5
    improved, Wilcoxon signed-rank p=0.018. The extra material admitted on psalms pages is the interleaved
    annotation apparatus, and the janvier-cut does NOT reliably discard it. Containment is therefore NOT a
    valid proxy for transcript quality; the honest fix for the apparatus is to identify and remove it (the
    †/annotation-aware segmentation lever), not to crop more generously around it.

    FULL-MEASURE, not all-lines (fix for the psalms R3 hard-zero, 2026-07-25): the DR psalms pages set short
    italic gloss fragments flush-right INSIDE the text block, and on a gloss-heavy page those fragments are the
    majority of the line count. Taking the median over every body line therefore lands the left edge inside the
    scripture column and clips the opening of each full line — olmOCR then re-reads a headless verse and the
    janvier-cut span scores ~0 (psalms-001: median-over-all x0 = 0.310 vs the true column edge 0.161, i.e. 15%
    of page width of scripture silently cut off; 13 of the 13 worst R3 regressions were this exact 0.000).
    Only lines at least `wide_frac` of the page wide actually define a column margin, which is the same
    population `layout.type_lines` uses to locate the body column. Measured effect: identical to 3 decimals on
    every 1-column prose gold page (genesis/matthew/2esdras/abdias), materially wider on every psalms page.

    STILL SINGLE-COLUMN (see region_crops): this returns ONE column for the page. A genuinely 2-column page
    yields a blended estimate; such verses stay OPEN (never a false accept)."""
    W = page_result["page_px"][0]
    boxes = [l["bbox"] for l in page_result["lines"] if l.get("role") == "body" and l.get("bbox")]
    if not boxes:
        return default
    wide = [b for b in boxes if (b[2] - b[0]) >= wide_frac * W]
    ref = wide or boxes                      # no full-measure population (poetic short-line page) -> use all
    return (_quantile([b[0] for b in ref], 1.0 - q) / W, _quantile([b[2] for b in ref], q) / W)


def group_contiguous(verses, *, max_gap: int = 1) -> list[list[int]]:
    """Group sorted verse numbers into runs where each consecutive pair differs by <= max_gap. Contiguous
    flagged verses become ONE region crop — olmOCR is clean + janvier cuts are sharpest on a multi-verse region
    with full context (vs a per-verse crop that clips boundaries)."""
    out: list[list[int]] = []
    cur: list[int] = []
    for v in sorted(verses):
        if cur and v - cur[-1] <= max_gap:
            cur.append(v)
        else:
            if cur:
                out.append(cur)
            cur = [v]
    if cur:
        out.append(cur)
    return out


def region_crops(page_result: dict, book: str, chapter: int, verses, *, pad_frac: float = 0.012,
                 max_gap: int = 1, clip_body_col: bool = True, seg_kwargs: dict | None = None,
                 spans: dict[int, dict] | None = None) -> dict:
    """Group `verses` (e.g. the gate's flagged set) into contiguous REGIONS and return one body-column-clipped
    crop per region. Returns {"regions": [{crop, verses, lines}], "no_geometry": [v,...]}. This is the
    production R3 targeting unit (one olmOCR pass per region, then janvier-cut the region output).

    SINGLE-COLUMN ASSUMPTION (code-review MEDIUM-5): `body_column` is ONE page-wide median x-extent applied to
    every region, correct for 1-column prose (validated on genesis) but a blended/wrong estimate on a 2-column
    page (psalms apparatus). A verse living in one column then gets an over-wide crop. This is not silent — such
    verses simply stay OPEN (a wrong-reason OPEN, never a false accept) — and the per-mode column-band fix is the
    named §8 R3-4 next lever; `r3_stats.py` already measures the exact metric to prove it. Do not read the
    genesis validation as covering multi-column layout."""
    vc = verse_crops(page_result, book, chapter, seg_kwargs=seg_kwargs, spans=spans)
    H = page_result["page_px"][1]
    bx0, bx1 = body_column(page_result) if clip_body_col else (0.0, 1.0)
    present = [v for v in verses if v in vc and vc[v]["crop"] is not None]
    no_geometry = [v for v in verses if v not in vc or vc[v]["crop"] is None]

    def cl(x):
        return max(0.0, min(1.0, x))

    regions = []
    for grp in group_contiguous(present, max_gap=max_gap):
        line_ids = sorted({li for v in grp for li in vc[v]["lines"]})
        boxes = [page_result["lines"][li]["bbox"] for li in line_ids if page_result["lines"][li].get("bbox")]
        if not boxes:
            no_geometry.extend(grp)
            continue
        y0 = min(b[1] for b in boxes) / H
        y1 = max(b[3] for b in boxes) / H
        crop = (cl(bx0 - pad_frac), cl(y0 - pad_frac), cl(bx1 + pad_frac), cl(y1 + pad_frac))
        regions.append({"crop": crop, "verses": grp, "lines": line_ids})
    return {"regions": regions, "no_geometry": sorted(set(no_geometry))}


# --------------------------------------------------------------------------- #
# self-check: a synthetic one-verse-per-line page must map each verse to its own band, ordered & in-unit
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    cv = verse_seg.chapter_verses("psalms", 118, verse_seg.JANVIER)
    vv = list(range(9, 17))
    W, H = 1000, 2000
    lines = [{"text": cv[v], "role": "body", "conf": 0.9,
              "bbox": (100, 100 + i * 100, 900, 100 + i * 100 + 80)} for i, v in enumerate(vv)]
    import layout
    r2_body = layout.strip_verse_numbers(re.sub(r"\s+", " ", " ".join(l["text"] for l in lines)).strip())
    page = {"page_px": (W, H), "r2_body": r2_body, "lines": lines}
    crops = verse_crops(page, "psalms", 118)
    ok = set(crops) == set(vv)
    prev = -1.0
    for i, v in enumerate(vv):
        x0, y0, x1, y1 = crops[v]["crop"]
        in_unit = 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
        covers = y0 <= (100 + i * 100) / H and y1 >= (100 + i * 100 + 80) / H
        ordered = y0 > prev
        prev = y0
        ok = ok and in_unit and covers and ordered and crops[v]["lines"] == [i]
        print(f"  v{v:>3} crop=({x0:.3f},{y0:.3f},{x1:.3f},{y1:.3f}) lines={crops[v]['lines']} "
              f"{'OK' if in_unit and covers and ordered else 'BAD'}")
    print("\nSELF-CHECK:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
