#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apparatus_geom.py — separate VERSE lines from ANNOTATION lines by GEOMETRY, conditioned on the page regime.

WHY GEOMETRY AND NOT SYMBOLS. The earlier symbol-only prototype (drop lines with no †) gave psalms-115-116
ch116 0.500 → 0.985 but destroyed proverbs (0.943 → 0.337), because a verse WRAPS onto continuation lines that
carry no marker of their own. A rule that reads only the symbol cannot tell a continuation line from an
annotation line — they both lack a †. Geometry can, and the visual inspection of the Psalm 118 pages
(ot2-1610 pp215-235, 2026-07-27) shows exactly how the printer distinguishes them:

    VERSE opening line     inset from the measure, opens with `N †` (self-labelling!) or `†`
    VERSE continuation     inset FURTHER still — a hanging indent, narrower than the measure
    ANNOTATION             starts LEFT of the verse block and runs the FULL measure, keyed by an italic letter
    STANZA HEADING         short, centred, isolated ("Gimel.  Fulnes.")
    MARGINAL NOTE          outside the text block entirely, either side

So the discriminating signal is the pair (left edge, right edge) relative to the VERSE BLOCK, not the presence
of a symbol. A continuation line is indented MORE than its verse opening; an annotation is indented LESS and
extends further right. Those two move in opposite directions, which is what makes them separable at all.

This module implements several variants of that idea and `apparatus_eval.py` measures them end to end. They
are variants rather than one rule because which signal survives depends on the regime: a page whose verse
block is unstable (short poetic lines, psalms) gives a noisy left edge, while a justified prose page gives a
noisy right edge instead — so the dispatcher picks the rule whose evidence the page actually supports.

GOLD-FREE: every signal is a line bbox or the line's own text. No gold, no reference text.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

MARKER = re.compile(r"[†‡]")
# A SELF-LABELLING verse opening: an arabic number immediately followed by the dagger — "14 † I am delighted".
# Seen throughout Psalm 118 (ot2-1610 p219). `layout.strip_verse_numbers` currently deletes these numbers on
# the documented assumption that "the DR body marks verses with † / ‡, never digits", which the page
# disproves: the number IS the verse label, and dropping it throws away the strongest boundary signal we have.
NUM_MARKER = re.compile(r"^\s*(\d{1,3})\s*[†‡]")
ANNOT_KEY = re.compile(r"^\s*[a-z]\s+\S")     # annotation lines open with an italic key letter: "a O Lord ..."


def _q(vals, p):
    if not vals:
        return 0.0
    v = sorted(vals)
    return v[max(0, min(len(v) - 1, int(p * (len(v) - 1))))]


def block_geometry(lines) -> dict:
    """Estimate the VERSE BLOCK's left and right edges from the lines that certainly open a verse.

    Anchoring on marker-bearing lines is what makes this robust: those lines are verse openings by
    construction, so their left edge IS the block's left edge, with no circularity and no gold."""
    body = [l for l in lines if l.get("role") == "body" and l.get("bbox")]
    if not body:
        return {}
    opens = [l for l in body if MARKER.search(l.get("text") or "")]
    x0_all = [l["bbox"][0] for l in body]
    x1_all = [l["bbox"][2] for l in body]
    x0_open = [l["bbox"][0] for l in opens] or x0_all
    return {
        "verse_left": _q(x0_open, 0.5),          # median left edge of marker-bearing (verse-opening) lines
        "verse_right": _q([l["bbox"][2] for l in opens] or x1_all, 0.5),
        "page_left": _q(x0_all, 0.05),
        "page_right": _q(x1_all, 0.95),
        "n_open": len(opens),
        "n_body": len(body),
    }


def classify_lines(lines, variant: str = "v6", tol_frac: float = 0.02, page_w: float = 1.0) -> list[dict]:
    """Label each body line 'verse' | 'continuation' | 'apparatus'. Returns one dict per body line.

    Variants (all gold-free; measured against each other in apparatus_eval.py):
      v1  left-edge only        — apparatus iff it starts left of the verse block
      v2  right-edge only       — apparatus iff it runs past the verse block's right edge (full measure)
      v3  BOTH (AND)            — conservative: must be both further left AND further right
      v4  EITHER (OR)           — aggressive
      v5  marker-anchored left  — v1, but the block edge comes only from marker-bearing lines
      v6  v5 + CONTINUATION PROTECTION — never drop a line indented at or right of the verse block. This is
          the rule the wrapped-continuation failure demands: a continuation is indented MORE than its opening,
          an annotation LESS, so protecting the indented side cannot cost a verse line.
    """
    g = block_geometry(lines)
    if not g:
        return []
    tol = tol_frac * (page_w or 1.0)
    out = []
    for i, l in enumerate(lines):
        if l.get("role") != "body" or not l.get("bbox"):
            continue
        x0, x1 = l["bbox"][0], l["bbox"][2]
        txt = l.get("text") or ""
        has_marker = bool(MARKER.search(txt)) or bool(NUM_MARKER.match(txt))
        left_of = x0 < g["verse_left"] - tol
        right_of = x1 > g["verse_right"] + tol
        if variant == "v1":
            appar = left_of
        elif variant == "v2":
            appar = right_of
        elif variant == "v3":
            appar = left_of and right_of
        elif variant == "v4":
            appar = left_of or right_of
        elif variant == "v5":
            appar = left_of
        else:                                    # v6
            appar = (left_of and not has_marker)
            if x0 >= g["verse_left"] - tol:      # indented at/inside the block -> verse or continuation, never
                appar = False                    # apparatus. Protects the wrapped-continuation case.
        kind = "apparatus" if appar else ("verse" if has_marker else "continuation")
        out.append({"idx": i, "kind": kind, "x0": x0, "x1": x1, "text": txt,
                    "annot_key": bool(ANNOT_KEY.match(txt))})
    return out


def body_without_apparatus(lines, variant: str = "v6", page_w: float = 1.0) -> str:
    """Rebuild the page's body text keeping only verse + continuation lines (apparatus excluded)."""
    import layout
    keep = [c for c in classify_lines(lines, variant=variant, page_w=page_w) if c["kind"] != "apparatus"]
    return layout.strip_verse_numbers(" ".join(c["text"] for c in keep))
