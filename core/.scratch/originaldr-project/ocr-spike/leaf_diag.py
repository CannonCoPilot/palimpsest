#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""leaf_diag.py — why is THIS source collapsing in THIS chapter? One screen of evidence, not a search.

A source that scores 0.90 across the book and 0.23 in one chapter has a LEAF defect, not a recognition
problem, and chapter 8 showed what those look like: a body band that is right for the witness and wrong for
one leaf, a chapter opening the model was never told about, a marginal column on a side the witness does not
normally have one. This prints the four things that distinguished them, for any (chapter, source):

  · the leaves the localizer credits, and the one CHAPTER_MODEL names as the opening leaf (they disagree)
  · each leaf's row-start and row-end distribution against the band actually in force, so a bound that cuts
    scripture or admits a margin shows up as a cluster on the wrong side of it
  · the tokens the band drops, which is the direct evidence for moving it
  · the open cells' text against the reference

Usage: ../ocr-venv/bin/python leaf_diag.py --chapter 5 --source S9 [--rows 8]
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen1_pagemodel as PM                       # noqa: E402
import gen1_pagemodel_eval as EV                  # noqa: E402
import ref_renumber as RR                         # noqa: E402

WITS = {"S1": "archive-ot1-1609", "S3": "pdf-S03a", "S6": "jp2-S06", "S9": "archive-holiebible-ot1"}


def raw_words(pd: dict) -> list[dict]:
    out: list[dict] = []
    for ln in pd.get("lines", []):
        out += ln.get("words", []) if isinstance(ln, dict) else []
    return out or pd.get("words", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--rows", type=int, default=6)
    ap.add_argument("--cells", type=int, default=4)
    a = ap.parse_args()
    ch, od = a.chapter, WITS[a.source]
    EV.BOOK, EV.CHAPTER, PM.CHAPTER = "genesis", ch, ch
    wb = PM.load("genesis", ch)
    lex = EV.book_lexicon()
    leaves = sorted(wb.get(od, {}), key=int)
    cm = PM.CHAPTER_MODEL.get((od, ch)) or {}
    print(f"=== genesis {ch} · {a.source} ({od})")
    print(f"    leaves in the word-box set: {leaves}")
    print(f"    CHAPTER_MODEL: {cm or '(none — argument and drop cap leak into verse 1)'}")

    for pi in leaves:
        pd = wb[od][pi]
        W, H = (pd.get("page_px") or [2200, 3000])[:2]
        m = {**PM.SOURCE_MODEL[od], **cm, **(PM.PAGE_OVERRIDE.get((od, int(pi))) or {})}
        lo, hi = m["body"][0] * W, m["body"][1] * W
        words = raw_words(pd)
        kept = PM.body_rows(od, int(pi), pd)
        dropped_l = [w for w in words if w.get("x0", 0) < lo]
        dropped_r = [w for w in words if (w.get("x0", 0) + w.get("x1", 0)) / 2 > hi]
        ov = PM.PAGE_OVERRIDE.get((od, int(pi)))
        print(f"\n  -- p{pi}  page {W}x{H}  band x {lo:.0f}-{hi:.0f}"
              f"{'  [PAGE_OVERRIDE]' if ov else ''}  rows kept {len(kept)}")
        print(f"     dropped LEFT of the band:  {len(dropped_l)}  " +
              " ".join(f"{w['t']}@{w.get('x0')}" for w in sorted(dropped_l, key=lambda w: -w.get("y0", 0))[:8]))
        print(f"     dropped RIGHT of the band: {len(dropped_r)}  " +
              " ".join(f"{w['t']}@{w.get('x0')}" for w in sorted(dropped_r, key=lambda w: -w.get("y0", 0))[:8]))
        for i, (ts, rr) in enumerate(PM.row_tokens(od, int(pi), pd, lex)):
            if i >= a.rows:
                break
            print(f"     {i}: x{rr[0].get('x0') if rr else '?'}-{rr[-1].get('x1') if rr else '?'}  "
                  f"{' '.join(ts)[:96]}")

    f = HERE / ".campaign" / f"matrix-genesis-{ch}.json"
    if f.exists():
        mm = json.loads(f.read_text())
        refs = RR.load_corrected("odr_com")
        opens = [c for c in mm.get("open", []) if c.get("src") == a.source]
        print(f"\n  open cells for {a.source}: {len(opens)}")
        for c in sorted(opens, key=lambda c: c["verse"])[:a.cells]:
            v = c["verse"]
            print(f"    v{v} worst={c.get('worst')} from={c.get('from')}")
            print(f"      OURS: {(c.get('text') or '(none)')[:150]}")
            print(f"      ODR : {(refs.get(f'scripture/genesis/{ch}/{v}') or '')[:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
