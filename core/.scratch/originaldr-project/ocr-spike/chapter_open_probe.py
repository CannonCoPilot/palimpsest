#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chapter_open_probe.py — where does this chapter OPEN on each witness, and what sits above it?

WHY A PROBE AND NOT A DERIVER. `chapter_model_derive.py` already derives `CHAPTER_MODEL` mechanically for all
48 un-worked chapters and is PINNED OFF: measured across the whole book it is net negative (re-verified
2026-07-31 on a board 1,100 cells better than when it was first measured — still -6, helping 4 chapters and
hurting 8). The derivation is sound; what it cannot do is tell a good cut from a bad one, and a cut that is
slightly wrong deletes scripture further down the leaf. So this prints the EVIDENCE — the printed chapter
heading, the italic argument, and the first line of verse 1, each with its y as a fraction — and the entry is
written by hand and measured. Chapter 8 was brought up that way and gained four cells; the deriver moved it
by nothing.

WHAT IT LOOKS FOR, in the order the leaf prints them:

    CHAP. XXXIX.                     <- the printed heading, in display capitals the recognizer mangles
    Ioſeph being in great credite    <- the italic ARGUMENT, which carries verse numbers and must be cut
    with his maiſter ... priſoners.
    THERFORE Ioſeph was brought      <- verse 1, located by janvier's own wording, never by spelling

`chapter_open_y` belongs BETWEEN the last argument line and the first verse line, and the probe prints that
window explicitly so the choice is a reading rather than a guess.

AND IT FINDS THE MIXED LEAF, which is the defect worth the most. `_is_annotation_leaf` excludes a whole leaf
whose head declares ANNOTATIONS, and that is right for a pure commentary leaf. But `pdf-S03a` p145 carries
chapter 38's annotations at the top and chapter 39's OPENING at the bottom — so the whole-leaf rule threw away
genesis 39:1-8 on two witnesses at once, and they were scored as cells with no text at all. A `CHAPTER_MODEL`
entry fixes it without touching that rule, because the y-cut is applied to the WORDS before the rows are
grouped: cut the annotations away and the leaf no longer declares itself an annotation leaf.

Usage:
  ../ocr-venv/bin/python chapter_open_probe.py --chapters 39
  ../ocr-venv/bin/python chapter_open_probe.py --chapters 2-50 --brief
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen1_pagemodel as PM                       # noqa: E402
import gen1_pagemodel_eval as EV                  # noqa: E402
import verse_seg as VS                            # noqa: E402

WITS = {"S1": "archive-ot1-1609", "S3": "pdf-S03a", "S6": "jp2-S06", "S9": "archive-holiebible-ot1"}
_ROMAN = "IVXL"
LINE_H = 40


def _fold(w: str) -> str:
    return re.sub(r"[^a-z]", "", w.lower().replace("ſ", "s").replace("v", "u").replace("j", "i"))


def leaf_lines(pd: dict) -> list[tuple[int, str]]:
    words = []
    for ln in pd.get("lines", []):
        words += ln.get("words", []) if isinstance(ln, dict) else []
    words = words or pd.get("words", [])
    by = collections.defaultdict(list)
    for w in words:
        by[w.get("y0", 0) // LINE_H].append(w)
    return [(k * LINE_H, " ".join(w["t"] for w in sorted(by[k], key=lambda w: w.get("x0", 0))))
            for k in sorted(by)]


EMIT: dict[str, dict] = {}


def probe(ch: int, brief: bool) -> None:
    EV.BOOK, EV.CHAPTER, PM.CHAPTER = "genesis", ch, ch
    wb = PM.load("genesis", ch)
    janv1 = (VS.chapter_verses("genesis", ch, VS.JANVIER) or {}).get(1, "")
    anchor = [t for t in (_fold(x) for x in janv1.split()[:5]) if t]
    print(f"\n===== GENESIS {ch}   janvier v1: {janv1[:70]!r}")
    for src, od in WITS.items():
        if od not in wb:
            print(f"  {src}: no word boxes")
            continue
        hand = PM.CHAPTER_MODEL.get((od, ch))
        best = None
        for pg in sorted(wb[od], key=int):
            pd = wb[od][pg]
            H = (pd.get("page_px") or [2200, 3000])[1]
            lines = leaf_lines(pd)
            head_y = next((y for y, s in lines
                           if re.search(r"CHAP", s.upper().replace(" ", "")) and
                           re.search(rf"[{_ROMAN}]{{2,8}}", s.upper().replace(" ", ""))), None)
            v1_y, v1_txt = None, ""
            for y, s in lines:
                # A LOOSE ANCHOR CUTS SCRIPTURE. Accepting any 2-3 of five tokens matched `God : who heard me
                # in the day of my tribulation` — genesis 35 VERSE 3 — as verse 1 on all four witnesses, and
                # the cut then deleted verses 1 and 2 (ch35 -3 cells, ch33 -4, ch23 -3). The tokens that made
                # it match were `god`, `in`, `the`: the commonest words in the book.
                # So the match must be CONSECUTIVE and must begin where the verse begins — within the first
                # few tokens of the line — which is what distinguishes the opening of a verse from a later
                # line that happens to reuse its vocabulary.
                fold = [_fold(x) for x in s.split()]
                if not anchor or len(fold) < 2:
                    continue
                best_hit, best_at = 0.0, None
                for i in range(min(4, max(1, len(fold) - 1))):
                    hit = sum(1 for a, b in zip(fold[i:i + len(anchor)], anchor) if a == b) / len(anchor)
                    if hit > best_hit:
                        best_hit, best_at = hit, i
                if best_hit >= 0.6 and best_at is not None:
                    v1_y, v1_txt = y, s
                    break
            if head_y is not None and v1_y is not None and v1_y > head_y:
                best = (pg, H, head_y, v1_y, v1_txt, lines)
                break
        if not best:
            print(f"  {src}: chapter opening NOT located on {sorted(wb[od], key=int)}"
                  f"{'   [hand entry exists: ' + str(hand) + ']' if hand else ''}")
            continue
        pg, H, hy, vy, vtxt, lines = best
        mid = (hy + vy) / 2
        note = ""
        head_txt = " ".join(s for y, s in lines[:4])
        if "NNOTATION" in head_txt.upper().replace(" ", ""):
            note = "  *** MIXED LEAF: annotations above, this chapter's opening below — dropped WHOLE today"
        print(f"  {src} p{pg}: heading y={hy} ({hy/H:.3f})  verse1 y={vy} ({vy/H:.3f})  "
              f"-> chapter_open_y in ({hy/H:.3f}, {vy/H:.3f}), midpoint {mid/H:.3f}{note}")
        # THE CUT IS ALWAYS JUST ABOVE VERSE 1. Everything over it — running head, a previous chapter's
        # annotations, the chapter heading, the italic argument — is matter and never scripture, so there is
        # no judgement left in choosing the y once verse 1 is located. That is the difference from the pinned
        # deriver, whose cut was chosen some other way and deleted text further down the leaf.
        if not hand:
            EMIT[f"{od}|{ch}"] = {"open_page": int(pg), "chapter_open_y": round((vy - LINE_H / 2) / H, 4),
                                  "v1": vtxt[:70], "mixed_leaf": bool(note)}
        if hand:
            print(f"       hand entry already set: {hand}")
        if not brief:
            print(f"       v1 reads: {vtxt[:88]}")
            for y, s in lines:
                if hy <= y <= vy:
                    print(f"         y={y:>5} ({y/H:.3f}): {s[:84]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="1-50")
    ap.add_argument("--brief", action="store_true")
    ap.add_argument("--emit", help="write located openings to this JSON side-table")
    a = ap.parse_args()
    chs: list[int] = []
    for part in a.chapters.split(","):
        if "-" in part:
            x, y = part.split("-")
            chs += list(range(int(x), int(y) + 1))
        else:
            chs.append(int(part))
    for ch in chs:
        probe(ch, a.brief)
    if a.emit:
        import json
        Path(a.emit).write_text(json.dumps(EMIT, ensure_ascii=False, indent=1))
        print(f"\n[emit] {len(EMIT)} openings -> {a.emit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
