#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""layout.py — gold-free body-region typing for the reOCR ladder (Rung-1's real job).

The Douay-Rheims gold `body` field EXCLUDES the running header, marginalia, and catchword (they live in
separate json fields). A recognizer run over the whole page emits all of them, which is why R1 surface sits
near zero and apparatus-heavy pages (psalms) never improve. This module separates the main scripture BODY
from apparatus using ONLY page geometry from the segmentation — no gold, no text model — with RELATIVE
thresholds (fractions of the page's own body-column geometry) so it generalizes across the whole edition
rather than over-fitting the 13 gold pages.

Design is CONSERVATIVE: it only drops lines it is confident are apparatus (header above the body, catchword
below it, lines sitting in an outer margin). Everything else defaults to BODY — we would rather keep a
marginal line than delete scripture (precision on body-retention over recall on apparatus-removal).

Roles: 'body' (kept) · 'header' · 'catchword' · 'marginalia' (dropped from the body transcript).
"""
from __future__ import annotations
from statistics import median


def _line_geo(line):
    """(x0,x1,yc,w) from a segmentation line's baseline (fallback boundary); None if no geometry."""
    pts = getattr(line, "baseline", None) or getattr(line, "boundary", None)
    if not pts:
        return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return {"x0": min(xs), "x1": max(xs), "yc": sum(ys) / len(ys), "w": max(xs) - min(xs)}


def line_bbox(line):
    """(x0,y0,x1,y1) pixel bbox for a segmentation line. Prefers the `boundary` POLYGON (full vertical extent
    of the glyph body — what a crop needs) and falls back to the `baseline` (a near-flat box) when no polygon
    is present. None if the line carries no geometry. Used by reocr_core to attach per-line boxes so verse_geom
    can turn a flagged verse into a pixel band for R3 (§8 R3-4)."""
    pts = getattr(line, "boundary", None) or getattr(line, "baseline", None)
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def type_lines(lines, page_w, page_h, *, wide_frac=0.50, margin_frac=0.06):
    """Classify each segmentation line by geometry. Returns list[str] role, aligned to `lines`.

    Args:
      lines: segmentation lines (kraken Segmentation.lines), in reading order.
      page_w, page_h: page pixel dims.
      wide_frac: a line is a body-defining "long" line if width >= wide_frac * page_w.
      margin_frac: tolerance band (fraction of page_w) around the body column edges.
    """
    geo = [_line_geo(ln) for ln in lines]
    present = [g for g in geo if g]
    if not present:
        return ["body"] * len(lines)  # no geometry → keep everything (fail-safe toward body)

    # Body column = the x-extent of the WIDE lines (the main text column). If no wide lines (e.g. a verse
    # page with short lines), fall back to the full span of all lines so nothing is spuriously dropped.
    wide = [g for g in present if g["w"] >= wide_frac * page_w]
    ref = wide if wide else present
    bx0 = median([g["x0"] for g in ref])
    bx1 = median([g["x1"] for g in ref])
    by0 = min(g["yc"] for g in ref)   # top of the body block
    by1 = max(g["yc"] for g in ref)   # bottom of the body block
    tol = margin_frac * page_w
    long_thresh = wide_frac * page_w

    roles = []
    for g in geo:
        if g is None:
            roles.append("body"); continue
        xc = (g["x0"] + g["x1"]) / 2
        is_short = g["w"] < long_thresh
        # marginalia: sits in an outer margin (its x-centre is left of the body column or right of it)
        if xc < bx0 - tol or xc > bx1 + tol:
            roles.append("marginalia"); continue
        # header: short AND above the body block AND in the top page band
        if is_short and g["yc"] < by0 - 1 and g["yc"] < 0.15 * page_h:
            roles.append("header"); continue
        # catchword: short AND below the body block AND in the bottom page band
        if is_short and g["yc"] > by1 + 1 and g["yc"] > 0.88 * page_h:
            roles.append("catchword"); continue
        roles.append("body")
    return roles


def strip_verse_numbers(text: str) -> str:
    """Remove printed verse-number apparatus the gold body omits: standalone digit-run tokens (the DR body
    marks verses with † / ‡, never digits). Conservative — only tokens that are PURELY digits (optionally a
    trailing '.') are dropped, so real numerals inside words survive. Gold-free surface cleanup."""
    import re
    out = [t for t in text.split() if not re.fullmatch(r"\d{1,3}\.?", t)]
    return " ".join(out)


def body_text(lines, line_texts, page_w, page_h, *, drop_verse_numbers=True):
    """Assemble the body-only transcript: keep 'body' lines in reading order, optionally strip verse numbers.
    Returns (text, roles) so callers can report what was dropped (No Silent Degradation: never hide it)."""
    roles = type_lines(lines, page_w, page_h)
    kept = [line_texts[i] for i, r in enumerate(roles) if r == "body" and i < len(line_texts)]
    text = " ".join(kept)
    if drop_verse_numbers:
        text = strip_verse_numbers(text)
    return text, roles


# --------------------------------------------------------------------------------------------------
# MERGED MARGINAL PREFIX — the annotation the line builder concatenated INTO a body line
# --------------------------------------------------------------------------------------------------
def strip_margin_prefix(lines, page_w, *, gap_frac: float = 0.08, keep_slack: int = 1):
    """Return line texts with a merged marginal-column prefix removed from each body line that has one.

    MEASURED DEFECT (Genesis, all four witnesses). The Douay-Rheims sets its annotations in a column beside
    the scripture block, and the line builder merges a marginal fragment and the body text that shares its
    y-band into ONE line — so the apparatus arrives INSIDE a `role="body"` line, where no role filter can
    reach it. `archive-ot1-1609` p58 line 9 reads

        ':: Ofthis com. IL them::: Increaſe, & multiplie, and replenish the carth.'

    which is the note "Of this commandment, or ..." broken across two body lines with Genesis 9:1 running
    through it. Normalised by page width, **14.0% of S1's body lines, 12.4% of S3's and 13.6% of S9's** begin
    well left of their page's own body column; S6, set widest, is at 3.4% — and S6 has by far the fewest
    extra-token failures, which is the same fact seen from the other end.

    WHY GEOMETRY AND NOT VOCABULARY. The obvious filter — drop token runs that match no reference word — was
    tested and rejected: those runs are dominated by CORRECT ARCHAIC SPELLINGS (`sone`, `therfore`, `daies`,
    `citie`, `geue`, `betwene`, `darkenes`, `uho`) that a modern-spelling grid cannot match, so the filter
    would delete scripture to raise a score. The margin is a POSITION, not a vocabulary, and position is what
    the line box records.

    METHOD. The page's body column edge is the median body-line start (merged lines are a minority, so the
    median lands on a clean line). A line beginning more than `gap_frac` of the page width left of that edge
    carries a prefix; its width is converted to characters through the line's own mean character width and
    snapped back to a token boundary. `keep_slack` then gives back that many tokens.

    THE BIAS IS DELIBERATE AND ONE-SIDED: under-cutting leaves a few annotation tokens in the verse, which
    scores as noise; over-cutting DELETES SCRIPTURE and scores as success. Only one of those is recoverable,
    so the estimate always errs toward keeping text."""
    texts = [(l.get("text") or "") for l in lines]
    body_idx = [i for i, l in enumerate(lines) if l.get("role") == "body" and l.get("bbox")]
    if len(body_idx) < 6:
        return texts
    starts = sorted(lines[i]["bbox"][0] for i in body_idx)
    edge = median(starts)
    out = list(texts)
    for i in body_idx:
        b = lines[i]["bbox"]
        t = texts[i]
        if not t or b[0] >= edge - gap_frac * page_w:
            continue
        width = b[2] - b[0]
        if width <= 0:
            continue
        char_w = width / max(1, len(t))
        n = int(round((edge - b[0]) / char_w))
        if n <= 0 or n >= len(t):
            continue
        cut = t.rfind(" ", 0, n + 1)          # snap back to a token boundary
        if cut <= 0:
            continue
        for _ in range(keep_slack):           # ...then hand one more token back to the body
            prev = t.rfind(" ", 0, cut)
            if prev <= 0:
                break
            cut = prev
        out[i] = t[cut:].lstrip()
    return out


def drop_side_column_lines(lines, page_w, *, right_frac: float = 0.25, max_w: float = 0.35):
    """Indices of `role="body"` lines that are really a SIDE-COLUMN annotation, by position and width.

    The mirror of `strip_margin_prefix`. Where the left-hand case merges the margin INTO a body line, the
    right-hand case gives the annotation its own line — which `type_lines` then calls body, because the
    annotation column overlaps the body's right edge rather than sitting in a clean outer margin.

    MEASURED, `archive-ot1-1609` p21: body lines start at x≈2352 of a 6428-wide page; line 38 is
    `'ginninꝫ ofthe'` at x=[5455, 6360] — 905 wide, starting at 85% of the page. It is the tail of the note
    "…chapter beginning of the second…", and it lands in the verse span for Genesis 1:4 in the middle of
    "And God | ſaw the light".

    A line qualifies only if it starts well RIGHT of the body column AND is narrow. The first condition is
    what protects the legitimate short line — the last line of a paragraph is short too, but it starts at the
    body column's LEFT edge, not three-quarters of the way across the page.

    ~9–10% of body lines in all four Genesis witnesses match. Returns indices rather than mutating, so a
    caller can measure the effect before adopting it."""
    body = [i for i, l in enumerate(lines) if l.get("role") == "body" and l.get("bbox")]
    if len(body) < 8:
        return set()
    med = median(lines[i]["bbox"][0] for i in body)
    out = set()
    for i in body:
        x0, x1 = lines[i]["bbox"][0], lines[i]["bbox"][2]
        if x0 > med + right_frac * page_w and (x1 - x0) < max_w * page_w:
            out.add(i)
    return out


def _apparatus_column_left(lines, page_w, *, min_lines: int = 3):
    """Left edge of a genuine right-hand apparatus column, or None if the page does not have one.

    THIS REPLACED A GAP HEURISTIC, AND THE REPLACEMENT WAS FORCED BY A CORPUS REGRESSION. The first version
    looked for the widest gap in the line-end distribution. On a page with a separate column that finds the
    column; on a page with an ordinary RAGGED RIGHT MARGIN it finds a gap between two arbitrary line lengths
    and cuts the last word off every long line. Measured on `jp2-S06` psalms it cut **36.5% of lines**,
    truncating plain prose ("…the Hebrew ſtile and man" -> "…and"), and the corpus fell from
    pass_rate_archaic 0.6384 to 0.5602. Genesis improved throughout, which is exactly how a layout-specific
    heuristic disguises itself.

    So the column must now EVIDENCE ITSELF. `drop_side_column_lines` already finds the lines that lie wholly
    inside the apparatus column — short, and far right of the text block. If a page has at least `min_lines`
    of them it has a column, and their left edge locates it exactly; if it has none, there is nothing to
    strip and the page is left alone. No gap is guessed, and a ragged margin cannot masquerade as a column."""
    idx = drop_side_column_lines(lines, page_w)
    if len(idx) < min_lines:
        return None
    return min(lines[i]["bbox"][0] for i in idx)


def strip_margin_suffix(lines, page_w, *, over_frac: float = 0.02, edge: float | None = None):
    """Return line texts with a merged apparatus SUFFIX removed — the right-hand twin of `strip_margin_prefix`.

    MEASURED, `archive-holiebible-ot1` p31 (Genesis 1). Clean body lines end at x≈5105–5130 of a 6048-wide
    page; contaminated ones run to x≈5937–6019, and what they carry past the measure is the annotation:

        L37  'ſaw the light that it was good: & he | ſecond on Ea¬'
        L43  'one day. F God alſo ſaid: Be:: a fir. | ment is al the'
        L50  'firmament. And it was ſo done. F And | eſt part diui¬'

    `strip_margin_prefix` cannot see these because they begin at the body column like any other line; only
    their END betrays them. 27–28% of body lines overrun in S1/S3/S9 and 13% in S6 — the same ordering as
    every other apparatus measure on these volumes.

    The cut is the same arithmetic as the prefix case, from the other end, but it snaps to the NEAREST token
    boundary rather than the one that keeps more text, and that difference was measured rather than assumed.
    The prefix case can afford to under-cut because a leading annotation fragment sits OUTSIDE the verse and
    merely pads it. A trailing one does not: the next body line continues the same verse, so an un-cut suffix
    lands in the MIDDLE of the reconstructed text ("...& he | ſecond | from the darkenes"), which is exactly
    the corruption these verses are failing on. Snapping forward also loses the case where the annotation is
    glued to the last body word (`'And God ginningofthe'`), because there is no forward boundary to snap to
    and the line is skipped entirely. The character estimate is accurate to about one token, so nearest is
    the honest choice."""
    texts = [(l.get("text") or "") for l in lines]
    body_idx = [i for i, l in enumerate(lines) if l.get("role") == "body" and l.get("bbox")]
    # `edge` is passed in by the caller because the side-column lines it is derived from have, by then, been
    # DEMOTED out of `role="body"` — the evidence has to be captured before it is consumed.
    if edge is None:
        edge = _apparatus_column_left(lines, page_w)
    if edge is None:
        return texts
    out = list(texts)
    for i in body_idx:
        b = lines[i]["bbox"]
        t = texts[i]
        if not t or b[2] <= edge + over_frac * page_w:
            continue
        width = b[2] - b[0]
        if width <= 0:
            continue
        char_w = width / max(1, len(t))
        n = int(round((b[2] - edge) / char_w))          # characters sitting past the measure
        if n <= 0 or n >= len(t):
            continue
        target = len(t) - n
        fwd = t.find(" ", max(0, target))
        back = t.rfind(" ", 0, max(0, target) + 1)
        cands = [c for c in (fwd, back) if c > 0]
        if not cands:
            continue
        cut = min(cands, key=lambda c: abs(c - target))
        out[i] = t[:cut].rstrip()
    return out
