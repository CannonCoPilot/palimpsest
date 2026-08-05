#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""triage.py — is this cell failing because of GEOMETRY or because of RECOGNITION?

THE QUESTION THE CAMPAIGN NEVER ASKED. Every large win in this project has been geometry, so geometry became
the assumption: a chapter scores badly, a source is skewed, a bound moves. That assumption was right for a
long time and is now wrong for most of the remaining work. Measured over all 50 chapters at board 5733:

    RECOGNITION  172 cells (45%)   the missing words are not on the leaf at all
    GEOMETRY     125 cells (33%)   the missing words ARE on the leaf, outside the band
    unattributed  86 cells (22%)   chapter-level or r3 assembly, no single leaf to interrogate

A bound cannot recover a word the recognizer never produced, and no amount of re-cropping will. Running this
before a walk is what stops an afternoon being spent on the wrong layer.

THE TEST, AND WHY IT IS HONEST. For each open cell take the reference reading, list the words the cell is
missing, and ask whether those words exist among the leaf's word boxes OUTSIDE the current band. That is a
question about the recognizer's output, not about a score or a threshold, and it has only two answers. It
cannot tell GEOMETRY from a coincidence where the same short word (`of`, `the`) happens to sit in the margin,
so short tokens are weighted down and the examples are printed for the eye. It is a router, not a verdict.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import re
import sys

sys.path.insert(0, ".")

SRC = {"S1": "archive-ot1-1609", "S3": "pdf-S03a",
       "S9": "archive-holiebible-ot1", "S6": "jp2-S06"}
# A one- or two-letter token matching something in the margin proves nothing; `of` and `the` are everywhere.
MIN_TOKEN = 3


def norm(t: str) -> str:
    return re.sub(r"[^a-zſæœ]", "", t.lower().replace("ſ", "s"))


class Boxes:
    def __init__(self):
        self.cache: dict[tuple[str, int], dict | None] = {}
        self.files = sorted(glob.glob(".wordboxes-genesis-*.json"))

    def get(self, od: str, page: int, ch: int) -> dict | None:
        k = (od, page)
        if k in self.cache:
            return self.cache[k]
        order = [f".wordboxes-genesis-{ch}.json"] + self.files
        for f in order:
            try:
                d = json.load(open(f))
            except Exception:
                continue
            r = d.get(od, {}).get(str(page))
            if r:
                self.cache[k] = r
                return r
        self.cache[k] = None
        return None


def triage_chapter(ch: int, boxes: Boxes, show: int = 0):
    import gen1_pagemodel as PM
    m = json.load(open(f".campaign/matrix-genesis-{ch}.json"))
    refs = m.get("refs_by_verse") or {}
    out = collections.Counter()
    detail: list[tuple[str, str]] = []
    for o in m.get("open", []):
        fr = o.get("from", "")
        if not (fr.startswith("p") and fr[1:].isdigit()):
            out["unattributed"] += 1
            continue
        od, p = SRC[o["src"]], int(fr[1:])
        rec = boxes.get(od, p, ch)
        rv = refs.get(str(o["verse"]))
        ref = " ".join(v for v in rv.values() if isinstance(v, str)) if isinstance(rv, dict) else (rv or "")
        if not rec or not ref:
            out["unattributed"] += 1
            continue
        got = {norm(t) for t in o["text"].split() if norm(t)}
        missing = [t for t in (norm(x) for x in ref.split()) if t and t not in got and len(t) >= MIN_TOKEN]
        if not missing:
            out["complete-but-failing"] += 1
            continue
        W = rec["page_px"][0]
        mm = {**PM.SOURCE_MODEL[od], **PM.chapter_model(od), **PM.PAGE_OVERRIDE.get((od, p), {})}
        lo, hi = mm["body"][0] * W, mm["body"][1] * W
        outside = set()
        for L in rec["lines"]:
            for w in L["words"]:
                if w["x0"] < lo or (w["x0"] + w["x1"]) / 2 > hi:
                    n = norm(w["t"])
                    if n and len(n) >= MIN_TOKEN:
                        outside.add(n)
        hits = [t for t in missing if t in outside]
        if hits:
            out["GEOMETRY"] += 1
            detail.append((f"{o['src']} p{p} v{o['verse']}", "recoverable: " + " ".join(hits[:6])))
        else:
            out["RECOGNITION"] += 1
            detail.append((f"{o['src']} p{p} v{o['verse']}", "absent: " + " ".join(missing[:6])))
    return out, detail


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="", help="comma list; default every chapter")
    ap.add_argument("--detail", action="store_true", help="print per-cell verdicts")
    a = ap.parse_args(argv)
    chs = ([int(x) for x in a.chapters.split(",") if x.strip()] if a.chapters
           else sorted(int(re.search(r"-(\d+)\.json", f).group(1))
                       for f in glob.glob(".campaign/matrix-genesis-*.json")))
    boxes = Boxes()
    grand = collections.Counter()
    print(f"{'ch':>4} {'GEOM':>5} {'RECOG':>6} {'unattr':>7} {'done':>5}   leaves implicated (geometry)")
    for ch in chs:
        c, detail = triage_chapter(ch, boxes)
        grand.update(c)
        leaves = collections.Counter(d[0].split()[0] + " " + d[0].split()[1]
                                     for d in detail if d[1].startswith("recoverable"))
        top = " ".join(f"{k}×{v}" for k, v in leaves.most_common(5))
        print(f"{ch:>4} {c['GEOMETRY']:>5} {c['RECOGNITION']:>6} {c['unattributed']:>7} "
              f"{c['complete-but-failing']:>5}   {top}")
        if a.detail:
            for where, what in detail:
                print(f"        {where:16} {what}")
    print(f"\nTOTAL  GEOMETRY {grand['GEOMETRY']}  RECOGNITION {grand['RECOGNITION']}  "
          f"unattributed {grand['unattributed']}  complete-but-failing {grand['complete-but-failing']}")


if __name__ == "__main__":
    main()
