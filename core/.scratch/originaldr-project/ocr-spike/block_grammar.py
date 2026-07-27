#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""block_grammar.py — a COMPOSABLE grammar of page blocks, and the regime detector that dispatches on it.

THE ARGUMENT AGAINST PER-BOOK MODELS. Visual inspection of ot2-1610 pp215-236 (2026-07-27) shows the variation
between books is not a variation in KIND. One page (p234) composes six block types in sequence — section
heading, treatise, psalm heading, italic argument, rubric, drop-cap verse, annotations — and another page
INSIDE the same psalm (p216) carries no scripture at all, being wholly the "General Annotations" treatise. The
inventory of blocks is small and shared across the corpus; what changes per book, and per SECTION of a book,
is which blocks appear, in what order, and with what parameters.

So the schema is not "the Psalms model" versus "the Matthew model". It is:

    BLOCK VOCABULARY  (shared)      running-head · psalm/chapter heading · argument (italic) · rubric ·
                                    verse-opening · verse-continuation · annotation · stanza-heading ·
                                    marginal-note · catchword · signature · treatise
    MARKER GRAMMAR    (per regime)  `N †` inline · `†` with the number in the right margin · `N.` inline (NT
                                    1582) · drop-cap opening · none
    GEOMETRY RULES    (per regime)  verse block inset; continuations indented FURTHER (hanging indent);
                                    annotations start LEFT of the block and run the FULL measure; marginalia
                                    outside the block on either side

Book identity is a PRIOR, never a key. A page that prints numerals is read with the numeral grammar whether or
not this book has been seen before — which is how one regime extends across a testament for free, and how a
treatise page is recognised as carrying no scripture instead of having verses forced onto it.

WHY THIS SHAPE RESISTS OVER-FITTING. With 14 gold pages across 7 books, a per-book model would be fitted on
1–2 pages each and would generalize badly. Detecting the REGIME from page evidence keeps the fitted quantity
small (a handful of thresholds shared by all pages in a regime) and makes coverage measurable: an unseen book
either matches a known regime or is reported as unmatched, which is a signal rather than a silent failure.

GOLD-FREE throughout: every signal is a line's own text or bbox.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

MARKER = re.compile(r"[†‡]")
NUM_MARKER = re.compile(r"^\s*(\d{1,3})\s*[†‡]")          # `14 †` — SELF-LABELLING (Psalm 118)
NT_NUMERAL = re.compile(r"(?:(?<=\s)|^)(\d{1,3})\.(?=\s|$)")  # `2.` — SELF-LABELLING (NT 1582)
ANNOT_KEY = re.compile(r"^\s*[a-z]\s+\S")                 # annotation opens with an italic key letter
STANZA = re.compile(r"^\s*(Aleph|Beth|Gimel|Daleth|He|Vau|Zain|Heth|Teth|Iod|Caph|Lamed|Mem|Nun|Samech|"
                    r"Ain|Phe|Sade|Coph|Res|Sin|Shin|Thau|Tau)\b", re.I)
HEADING = re.compile(r"^\s*(PSALME|PSALM|CHAP|THE\s+BOOKE|A\s+BRIEFE|GENERAL\s+ANNOTATIONS)", re.I)

BLOCK_TYPES = ("running-head", "heading", "argument", "rubric", "verse-opening", "verse-continuation",
               "annotation", "stanza-heading", "marginal-note", "catchword", "signature", "treatise")


def _q(vals, p):
    if not vals:
        return 0.0
    v = sorted(vals)
    return v[max(0, min(len(v) - 1, int(p * (len(v) - 1))))]


def page_frame(lines) -> dict:
    """Left/right edges of the VERSE BLOCK and of the page measure, from marker-bearing lines where possible.

    Anchoring the block on lines that certainly open a verse (they carry a marker) avoids circularity: those
    lines define the block, and everything else is then described relative to it."""
    body = [l for l in lines if l.get("role") == "body" and l.get("bbox")]
    if not body:
        return {}
    opens = [l for l in body if MARKER.search(l.get("text") or "")]
    ref = opens or body
    return {
        "block_left": _q([l["bbox"][0] for l in ref], 0.5),
        "block_right": _q([l["bbox"][2] for l in ref], 0.5),
        "measure_left": _q([l["bbox"][0] for l in body], 0.05),
        "measure_right": _q([l["bbox"][2] for l in body], 0.95),
        "median_len": median([len(l.get("text") or "") for l in body]) or 1,
        "n_open": len(opens),
        "n_body": len(body),
    }


def classify_block(line: dict, frame: dict, page_px, *, tol_frac: float = 0.02) -> dict:
    """Assign ONE line a block type from its own text and geometry. Returns {type, why, self_label}.

    `self_label` carries the verse number when the line's marker names it — the property that makes the
    numeral regimes stronger than the bare dagger."""
    txt = (line.get("text") or "").strip()
    role = line.get("role")
    if role in ("header", "running-head"):
        return {"type": "running-head", "why": "layout role", "self_label": None}
    if role == "catchword":
        return {"type": "catchword", "why": "layout role", "self_label": None}
    if role == "marginalia":
        return {"type": "marginal-note", "why": "layout role", "self_label": None}
    if not txt:
        return {"type": "treatise", "why": "empty", "self_label": None}

    W = page_px[0] or 1
    tol = tol_frac * W
    bbox = line.get("bbox")
    x0 = bbox[0] if bbox else frame.get("block_left", 0)
    x1 = bbox[2] if bbox else frame.get("block_right", W)

    m = NUM_MARKER.match(txt)
    if m:
        return {"type": "verse-opening", "why": "`N †` — self-labelling marker", "self_label": int(m.group(1))}
    n = NT_NUMERAL.search(txt[:6])
    if n:
        return {"type": "verse-opening", "why": "`N.` numeral — self-labelling marker",
                "self_label": int(n.group(1))}
    if HEADING.match(txt):
        return {"type": "heading", "why": "heading keyword", "self_label": None}
    if STANZA.match(txt) and len(txt) < 0.5 * frame.get("median_len", 60):
        return {"type": "stanza-heading", "why": "Hebrew letter name, short line", "self_label": None}
    if MARKER.search(txt):
        return {"type": "verse-opening", "why": "† marker (positional, not self-labelling)", "self_label": None}
    # no marker: geometry decides. An ANNOTATION starts left of the verse block and runs the full measure;
    # a CONTINUATION is indented at or inside the block. They move in opposite directions, which is the whole
    # reason the wrapped-continuation case is separable at all.
    left_of = x0 < frame.get("block_left", 0) - tol
    full_measure = x1 > frame.get("block_right", W) + tol
    if left_of and (full_measure or ANNOT_KEY.match(txt)):
        return {"type": "annotation", "why": "starts left of the verse block and runs the full measure",
                "self_label": None}
    if left_of:
        return {"type": "annotation", "why": "starts left of the verse block", "self_label": None}
    return {"type": "verse-continuation", "why": "indented at or inside the verse block", "self_label": None}


def parse_page(page_result: dict, *, tol_frac: float = 0.02) -> list[dict]:
    """The page as a sequence of typed blocks — one entry per line, in reading order."""
    lines = page_result.get("lines", [])
    frame = page_frame(lines)
    px = page_result.get("page_px", (1, 1))
    out = []
    for i, l in enumerate(lines):
        c = classify_block(l, frame, px, tol_frac=tol_frac)
        out.append({"idx": i, "text": l.get("text", ""), "role": l.get("role"), **c})
    return out


def compose(blocks: list[dict]) -> list[dict]:
    """Fold the per-line types into contiguous RUNS — the composition step.

    A verse is an opening followed by its continuations; an annotation run is one apparatus unit. Composition
    is what turns a line classifier into a grammar: it is the run structure, not the individual line, that a
    segmenter or a crop router consumes."""
    runs: list[dict] = []
    for b in blocks:
        t = b["type"]
        if t == "verse-continuation" and runs and runs[-1]["type"] == "verse":
            runs[-1]["lines"].append(b["idx"])
            continue
        if t == "verse-opening":
            runs.append({"type": "verse", "lines": [b["idx"]], "self_label": b["self_label"]})
            continue
        if runs and runs[-1]["type"] == t:
            runs[-1]["lines"].append(b["idx"])
            continue
        runs.append({"type": t, "lines": [b["idx"]], "self_label": None})
    return runs


def detect_regime(page_result: dict, anchors: dict | None = None) -> dict:
    """Which marker grammar does this page print? Returns {regime, self_labelling, confidence, why, evidence}.

    Regimes:
      'nt-numeral'      `N.` inline (NT 1582)            SELF-LABELLING
      'psalm-numbered'  `N †` inline (Psalm 118 etc.)    SELF-LABELLING
      'ot-dagger'       bare † (most of the OT)          positional only
      'no-scripture'    no verse markers and no verse-shaped blocks — a treatise/annotation page (p216)
      'unmatched'       markers present but no grammar fits — REPORTED, never forced into a regime
    """
    blocks = parse_page(page_result)
    body = [b for b in blocks if b["role"] == "body"]
    # Numbers RECOVERED from the page (verse_numbers) count as printed evidence, because they ARE printed —
    # they were simply outside kraken's line polygons. Without this, psalms-118 detects as `ot-dagger` and the
    # pipeline reads it in the weaker positional regime while the stronger self-labelling one sits recovered
    # and unused.
    if anchors:
        return {"regime": "psalm-numbered", "self_labelling": True,
                "confidence": round(min(1.0, len(anchors) / max(1, sum(
                    1 for b in body if b["type"] == "verse-opening"))), 3),
                "why": f"{len(anchors)} printed verse number(s) recovered from the page gutter",
                "evidence": {"recovered_numbers": len(anchors), "n_body": len(body)}}
    if not body:
        return {"regime": "no-scripture", "self_labelling": False, "confidence": 1.0,
                "why": "no body lines", "evidence": {}}
    n = len(body)
    n_numeral = sum(1 for b in body if b["type"] == "verse-opening" and "N." in b["why"])
    n_psalmnum = sum(1 for b in body if b["type"] == "verse-opening" and "N †" in b["why"])
    n_dagger = sum(1 for b in body if b["type"] == "verse-opening" and b["why"].startswith("†"))
    n_open = n_numeral + n_psalmnum + n_dagger
    ev = {"n_body": n, "numeral": n_numeral, "psalm_numbered": n_psalmnum, "dagger": n_dagger,
          "open_frac": round(n_open / n, 3)}
    if n_open == 0:
        return {"regime": "no-scripture", "self_labelling": False, "confidence": round(1 - 0.0, 3),
                "why": "no verse markers anywhere on the page — a treatise or annotation page, not scripture",
                "evidence": ev}
    if n_numeral >= max(2, 0.5 * n_open):
        return {"regime": "nt-numeral", "self_labelling": True, "confidence": round(n_numeral / n_open, 3),
                "why": "inline `N.` verse numerals dominate", "evidence": ev}
    if n_psalmnum >= max(2, 0.5 * n_open):
        return {"regime": "psalm-numbered", "self_labelling": True,
                "confidence": round(n_psalmnum / n_open, 3),
                "why": "inline `N †` openings — the number names its own verse", "evidence": ev}
    if n_dagger >= max(2, 0.5 * n_open):
        return {"regime": "ot-dagger", "self_labelling": False, "confidence": round(n_dagger / n_open, 3),
                "why": "bare † openings — boundaries are marked but not labelled", "evidence": ev}
    return {"regime": "unmatched", "self_labelling": False, "confidence": 0.0,
            "why": "markers present but no grammar accounts for them — reported, not forced", "evidence": ev}


_ROMAN = {"I": 1, "II": 2, "III": 3, "IIII": 4, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9,
          "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17,
          "XVIII": 18, "XIX": 19, "XX": 20}
CHAP_HEAD = re.compile(r"^\s*(?:CHAP(?:TER)?\.?|PSALME?\.?)\s*([IVXLC]+|\d{1,3})\b", re.I)


def chapter_ranges(page_result: dict) -> list[dict]:
    """Line ranges belonging to each chapter printed on the page: [{chapter, lo, hi}], reading order.

    WHY THIS IS NEEDED (§13 Q5, colossians-3). `verse_seg.segment`'s documented contract is that `text` must be
    ONE chapter's body — "on a page that straddles chapters, split the body by chapter first and call once per
    chapter". No caller did. On a multi-chapter page every verse of BOTH chapters then competes for every
    position, which is exactly the failure mode the anchor-walk was built to remove, reintroduced at the page
    level. The printer marks the split with a chapter heading, so the grammar can supply it.

    A page with no chapter heading returns a single open range — the common case, and correct: the page
    continues the chapter that began earlier."""
    lines = page_result.get("lines", [])
    heads: list[tuple[int, int | None]] = []
    for i, l in enumerate(lines):
        m = CHAP_HEAD.match((l.get("text") or "").strip())
        if not m:
            continue
        tok = m.group(1).upper()
        ch = _ROMAN.get(tok) if not tok.isdigit() else int(tok)
        heads.append((i, ch))
    if not heads:
        return [{"chapter": None, "lo": 0, "hi": len(lines)}]
    out = []
    if heads[0][0] > 0:
        out.append({"chapter": None, "lo": 0, "hi": heads[0][0]})   # tail of the previous chapter
    for k, (i, ch) in enumerate(heads):
        hi = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        out.append({"chapter": ch, "lo": i, "hi": hi})
    return out


SCHEMA = {
    # regime -> how to read a page in it. Small, shared per regime — NOT per book.
    "nt-numeral":     {"marker": r"N\.", "self_labelling": True, "segmenter": "hybrid",
                       "boundaries": "printed numerals (verse number read off the marker)"},
    "psalm-numbered": {"marker": r"N †", "self_labelling": True, "segmenter": "hybrid",
                       "boundaries": "printed number+dagger (verse number read off the marker)"},
    "ot-dagger":      {"marker": r"†", "self_labelling": False, "segmenter": "hybrid",
                       "boundaries": "printed daggers, labels inferred by monotone assignment"},
    "no-scripture":   {"marker": None, "self_labelling": False, "segmenter": None,
                       "boundaries": "none — page carries no verse text; do not attempt verse localization"},
    "unmatched":      {"marker": None, "self_labelling": False, "segmenter": "hybrid",
                       "boundaries": "unknown — fall back to text-anchored localization and FLAG the page"},
}


def dispatch(page_result: dict, anchors: dict | None = None) -> dict:
    """Regime + the schema to read the page with. The single entry point for the composable grammar."""
    d = detect_regime(page_result, anchors=anchors)
    return {**d, "schema": SCHEMA[d["regime"]]}
