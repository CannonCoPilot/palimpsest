#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chapter_model_derive.py — derive `CHAPTER_MODEL` per (witness, chapter) from the leaves (2026-07-29).

WHY THIS IS THE CAMPAIGN'S CENTRAL LEVER. `CHAPTER_MODEL` carries the three facts about a chapter's OPENING LEAF
that no generalizable rule can supply — which leaf opens the chapter, how far down the page the title block and
italic argument run, and what the engraved initial glued to the first word. It was hand-set for chapters 1 and 16
and **for no other chapter**, so every one of the other 48 runs with `open_page=None`: the title, the argument and
the drop capital all leak into verse 1. That is exactly what the cold matrices show —

    ch2  S1 v1  `ribbe of HEheauens therfore & the earth were fully finiſhed`
    ch38 S1 v1  `and Zara. HIſame time Iudas going downe from his brethren`
    ch14 S9 v1  `and it came to paſſe in that time, that. Amraphel the and Xking of Sennaar`

— verse 1 failing in most witnesses of most chapters, from one missing table. Deriving it mechanically lifts all
48 chapters at once, which is worth far more than hand-working chapters one at a time.

HOW EACH FACT IS DERIVED, and what it is derived FROM (never from the reference's spelling):

  open_page       the leaf the localizer credits with this chapter's verse 1, confirmed by finding a printed
                  `CHAP.`-shaped row on it. The heading is the page's own statement about itself.
  chapter_open_y  the y of the first body row that matches janvier verse 1's opening tokens, minus a small
                  margin. Everything above it on the opening leaf is title/argument. Janvier is used only to
                  say WHERE verse 1 starts — a content anchor, exactly as `verse_locate` uses it — never to
                  supply a spelling.
  drop_cap        PROPOSED ONLY, never auto-applied. An engraved initial makes verse 1's first token arrive
                  short or glued (`ARAI` for SARAI, `NTHEbeginning` for IN THE beginning). The deriver reports
                  the candidate and its evidence; a human/agent eye confirms it against the rendered leaf before
                  it is encoded, because inventing a letter is exactly the corruption this project forbids.

OUTPUT: `.chapter-model-derived.json`, a side table keyed `"<ocr_dir>|<chapter>"`. `gen1_pagemodel.chapter_model`
merges it UNDER the hand-set entries, so chapters 1 and 16 are untouched and every derived value is auditable and
reversible by deleting one line of JSON.

Usage: ../ocr-venv/bin/python chapter_model_derive.py --chapters 2-50 [--apply] [--verbose]
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen1_pagemodel as PM                              # noqa: E402
import verse_seg as VS                                   # noqa: E402

DERIVED = HERE / ".chapter-model-derived.json"
CHAP_RE = re.compile(r"^C\s*H\s*A\s*P", re.I)
OPEN_MARGIN = 0.012        # cut this fraction of page height ABOVE verse 1's first row
MATCH_MIN = 0.55           # janvier-v1 token overlap needed to call a row "verse 1 starts here"


def _fold(t: str) -> str:
    return t.strip(" \t.,;:·†‡*()[]").lower().replace("ſ", "s").replace("v", "u").replace("j", "i")


def raw_rows(od: str, page: int, pd: dict) -> list[list[dict]]:
    """Rows of the leaf with NO chapter-model cut applied — the state the deriver has to reason about."""
    saved = PM.CHAPTER_MODEL.pop((od, PM.CHAPTER), None)
    try:
        return PM.body_rows(od, page, pd)
    finally:
        if saved is not None:
            PM.CHAPTER_MODEL[(od, PM.CHAPTER)] = saved


def derive_one(od: str, chapter: int, wb: dict, janv: dict, verbose: bool = False) -> dict | None:
    pages = sorted((wb.get(od) or {}), key=int)
    if not pages:
        return None
    v1 = janv.get(1) or ""
    v1_toks = [_fold(t) for t in v1.split()[:8] if _fold(t)]
    if not v1_toks:
        return None
    best = None
    for pi in pages:
        pd = wb[od][str(pi)] if str(pi) in wb[od] else wb[od][pi]
        H = pd["page_px"][1]
        rows = raw_rows(od, int(pi), pd)
        if not rows:
            continue
        has_chap = any(CHAP_RE.match("".join(w["t"] for w in r[:3])) for r in rows[:14])
        for ri, r in enumerate(rows):
            toks = [_fold(w["t"]) for w in r]
            toks = [t for t in toks if t]
            if not toks:
                continue
            sm = difflib.SequenceMatcher(a=toks, b=v1_toks, autojunk=False)
            hit = sum(bl.size for bl in sm.get_matching_blocks()) / max(1, len(v1_toks))
            if hit < MATCH_MIN:
                continue
            y0 = min(w["y0"] for w in r)
            cand = {"open_page": int(pi), "chapter_open_y": round(max(0.0, y0 / H - OPEN_MARGIN), 4),
                    "row_index": ri, "has_chap_heading": has_chap,
                    "v1_hit": round(hit, 3), "first_token": r[0]["t"],
                    "rows_above": ri, "y0_px": y0, "page_h": H}
            # PREFER the leaf that also shows a printed CHAP. heading, then the strongest v1 match. A chapter's
            # text recurs in annotations and in the next chapter's argument, so the heading is the tie-breaker
            # that keeps the deriver off a leaf that merely QUOTES verse 1.
            key = (has_chap, hit, -ri)
            if best is None or key > best[0]:
                best = (key, cand)
            break
    if best is None:
        return None
    c = best[1]
    # DROP-CAP CANDIDATE — proposed, never applied. Evidence: verse 1's first printed token differs from
    # janvier's first word by a MISSING HEAD (the engraved initial), or carries the argument's tail glued on.
    j1 = _fold(v1.split()[0]) if v1.split() else ""
    ft = c["first_token"]
    f_ft = _fold(ft)
    prop = None
    if j1 and f_ft and f_ft != j1:
        if j1.endswith(f_ft) and len(f_ft) < len(j1):
            prop = {"glued": ft, "why": f"missing head: janvier v1 opens {v1.split()[0]!r}"}
        elif f_ft.endswith(j1) and len(f_ft) > len(j1):
            prop = {"glued": ft, "why": f"argument tail glued before {v1.split()[0]!r}"}
        elif len(f_ft) > 6 and j1 in f_ft:
            prop = {"glued": ft, "why": f"display line run together around {v1.split()[0]!r}"}
    c["drop_cap_candidate"] = prop
    # SANITY GUARD. A chapter_open_y that cuts most of a leaf is almost certainly a verse-1 match against an
    # ANNOTATION quoting the verse rather than the verse itself. Flagged, not silently applied — `jp2-S06` ch2
    # derives 0.793 with 42 rows above and no printed heading, which is exactly that shape.
    # SUSPECT MEANS "THE VERSE-1 MATCH IS PROBABLY WRONG", NOT "THE CUT IS DEEP" (recalibrated 2026-07-30).
    # Genesis's chapters run CONTINUOUSLY, so a chapter opening three quarters of the way down a leaf is the
    # ordinary case and a deep `chapter_open_y` is correct — the leaf above it belongs to the PREVIOUS chapter and
    # must be cut. The first threshold (>0.60 of the leaf) assumed chapter 1's layout, where the chapter opens
    # near the top after a title block, and it withheld 64 of 162 derivations for doing exactly the right thing.
    #
    # The real risk is a verse-1 match against an ANNOTATION quoting the verse. That is what is tested now: a
    # derivation is suspect when the leaf shows no printed `CHAP.` heading AND the verse-1 token overlap is weak.
    # The rows_above cap stays, far looser, purely as a backstop against a match near a leaf's very bottom.
    c["suspect"] = bool((not c["has_chap_heading"] and c["v1_hit"] < 0.70) or c["rows_above"] > 45)
    if verbose:
        print(f"    {od:<24} p{c['open_page']:<5} open_y={c['chapter_open_y']:.4f} "
              f"rows_above={c['rows_above']:<3} chap_heading={c['has_chap_heading']} "
              f"v1_hit={c['v1_hit']} first={ft!r} drop_cap={prop['glued'] if prop else '-'}")
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="2-50")
    ap.add_argument("--apply", action="store_true", help="write .chapter-model-derived.json")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    from chapter_campaign import parse_chapters
    chs = parse_chapters(a.chapters)
    table = json.loads(DERIVED.read_text()) if DERIVED.exists() else {}
    n_new = n_skip = 0
    for ch in chs:
        wb = PM.load("genesis", ch)
        if not wb:
            continue
        PM.CHAPTER = ch
        janv = VS.chapter_verses("genesis", ch, VS.JANVIER) or {}
        if not janv:
            continue
        print(f"ch {ch}:")
        for od in sorted(wb):
            if (od, ch) in PM.CHAPTER_MODEL:
                print(f"    {od:<24} HAND-SET — left alone")
                n_skip += 1
                continue
            c = derive_one(od, ch, wb, janv, verbose=True)
            if c is None:
                print(f"    {od:<24} no verse-1 row found (chapter may open mid-leaf with no display)")
                continue
            table[f"{od}|{ch}"] = c
            n_new += 1
            if c["suspect"]:
                print(f"    {od:<24} ^^ SUSPECT: would cut {c['chapter_open_y']:.0%} of the leaf "
                      f"({c['rows_above']} rows above) — needs an eye before it is trusted")
    print(f"\nderived {n_new} entries ({n_skip} hand-set entries left untouched)")
    if a.apply:
        DERIVED.write_text(json.dumps(table, ensure_ascii=False, indent=1))
        print(f"[wrote] {DERIVED.name}")
    else:
        print("(dry run — pass --apply to write the table)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
