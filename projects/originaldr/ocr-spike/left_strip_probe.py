#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""left_strip_probe.py — is the strip left of the body bound TEXT or NOTES, per leaf?

THE DEFECT THIS SIZES. Every PAGE_OVERRIDE for a 1609 source carries a RIGHT bound tuned
to four decimals and a LEFT bound that is the untouched default 0.14 -- the fingerprint of
`gutter_probe.py`, which only ever swept the gutter. On ch41 `archive-ot1-1609` p145 that
bound cuts THROUGH the body column: `there`, `The`, `faire.`, `leanenes` sit at x0/W
0.118-0.136 and are dropped, and the verses that lost them fail (v5 and v6 score 0.000).
Book-wide the strip 0.109 <= x0/W < 0.14 holds ~8,200 tokens over 404 leaves.

WHY THIS IS NOT A DEFAULT CHANGE. The strip is MIXED across the book. On p145 it is body;
on `archive-holiebible-ot1` p35 it is `1.Idals. called idols.` -- a note column. Moving the
default would drag apparatus into the body text on every leaf of the second kind, which is
the contamination this project has spent nine pinned negatives learning to avoid.

THE SPLITTING TEST, and it needs no classifier. Word boxes carry LINE membership. A strip
token is a BODY CONTINUATION if the line it sits on also has substantial tokens INSIDE the
band -- the bound clipped the head off a body line. It is a NOTE if its line lies wholly in
the strip -- a short marginal line of its own. Reported per leaf, never aggregated, because
`PAGE_OVERRIDE` is keyed by LEAF and one leaf's answer is not another's.

CAVEAT, MEASURED ELSEWHERE AND LOAD-BEARING HERE: kraken sometimes merges a marginal note
INTO a body line's own line object (this is why no x-threshold fixed ch3/ch6). Where that
happens a line looks straddling and this probe will call the note a continuation. So the
`--verify` mode prints the reconstructed head text for an eye BEFORE any bound moves.

Usage:
  ../ocr-venv/bin/python left_strip_probe.py --chapter 41
  ../ocr-venv/bin/python left_strip_probe.py --chapter 41 --verify
  ../ocr-venv/bin/python left_strip_probe.py --all          # every cached chapter
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
S1609 = ("archive-ot1-1609", "pdf-S03a", "archive-holiebible-ot1")
STRIP_LO, DEFAULT_BOUND = 0.109, 0.14

# GENERALIZED 2026-08-02 (ch23). The first version hardcoded the three 1609 witnesses and their 0.14 bound,
# which made it blind to `jp2-S06` — whose body starts at 0.215 because that edition carries its ANNOTATION
# COLUMN ON THE LEFT, where the 1609 witnesses put theirs on the right. A probe that can only see one edition's
# layout will report "no defect" on the other and be believed, which is the same shape of error as sweeping one
# bound and concluding "recognizer".
#
# THE FLOOR IS NOT A CONSTANT ANY MORE EITHER. 0.109 was the empty gap in the 1609 token histogram; it means
# nothing on S6. The strip is now simply "left of this leaf's own body bound", and the LINE-MEMBERSHIP TEST
# does all the discriminating — which is what it was for. A whole marginal column reads as lines lying wholly
# in the strip and is correctly refused; a clipped body head reads as a line straddling the bound.
ALL_SOURCES = S1609 + ("jp2-S06",)
EDGE_FLOOR = 0.02      # below this is page edge / bleed, never a column


def source_bound(od: str, page: int) -> float:
    """This LEAF's body left bound, from the page model — never assumed."""
    import gen1_pagemodel as PM
    ov = PM.PAGE_OVERRIDE.get((od, page), {})
    return (ov.get("body") or PM.SOURCE_MODEL[od]["body"])[0]
# A line counts as a BODY line if it has at least this many tokens inside the band. Two is
# deliberately low: the point is to separate "a line that lives in the band" from "a line
# that lives in the strip", not to judge how long a body line ought to be.
BAND_MIN = 2


def leaf_report(rec: dict, bound: float = DEFAULT_BOUND, floor: float = STRIP_LO) -> dict:
    W = rec["page_px"][0]
    cont, note, heads = [], [], []
    for L in rec["lines"]:
        ws = L["words"]
        strip = [w for w in ws if floor <= w["x0"] / W < bound]
        if not strip:
            continue
        inband = [w for w in ws if w["x0"] / W >= bound]
        if len(inband) >= BAND_MIN:
            cont += strip
            heads.append((" ".join(w["t"] for w in strip),
                          " ".join(w["t"] for w in inband)[:58]))
        else:
            note += strip
    return {"W": W, "continuation": cont, "note": note, "heads": heads}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--min", type=int, default=8, help="only report leaves with >= this many strip tokens")
    ap.add_argument("--source", default="", help="one ocr_dir; default every witness")
    ap.add_argument("--emit", action="store_true",
                    help="print PAGE_OVERRIDE entries for MOVE leaves only, preserving any tuned right bound")
    a = ap.parse_args(argv)

    if a.emit:
        import gen1_pagemodel as PM
        seen: dict[tuple[str, int], tuple[int, int]] = {}
        for f in sorted(glob.glob(str(HERE / ".wordboxes-genesis-*.json"))):
            d = json.load(open(f))
            for od in S1609:
                for p, rec in d.get(od, {}).items():
                    r = leaf_report(rec, source_bound(od, int(p)), EDGE_FLOOR)
                    nc, nn = len(r["continuation"]), len(r["note"])
                    # A leaf is carried by MANY chapters and each chapter's cache holds its own recognition of
                    # it. Take the WORST-CASE note count and best-case continuation across caches, so a leaf is
                    # only moved if no cache calls it a note column.
                    k = (od, int(p))
                    if k in seen:
                        nc, nn = max(nc, seen[k][0]), max(nn, seen[k][1])
                    seen[k] = (nc, nn)
        moved = 0
        for (od, p), (nc, nn) in sorted(seen.items()):
            if not (nc >= 3 * max(nn, 1) and nc >= 3):
                continue
            cur = PM.PAGE_OVERRIDE.get((od, p), {})
            right = cur.get("body", PM.SOURCE_MODEL[od]["body"])[1]
            extra = {k: v for k, v in cur.items() if k != "body"}
            tail = ("".join(f", {k!r}: {v!r}" for k, v in extra.items())) if extra else ""
            print(f'    ({od!r}, {p}): {{"body": ({STRIP_LO}, {right}){tail}}},   # +{nc} body, {nn} note')
            moved += 1
        print(f"    # {moved} leaves emitted")
        return

    files = (sorted(glob.glob(str(HERE / ".wordboxes-genesis-*.json"))) if a.all
             else [str(HERE / f".wordboxes-genesis-{a.chapter}.json")])

    tot_c = tot_n = 0
    rows = []
    for f in files:
        d = json.load(open(f))
        for od in (a.source and [a.source] or list(ALL_SOURCES)):
            for p, rec in d.get(od, {}).items():
                r = leaf_report(rec, source_bound(od, int(p)), EDGE_FLOOR)
                nc, nn = len(r["continuation"]), len(r["note"])
                if nc + nn < a.min:
                    continue
                tot_c += nc
                tot_n += nn
                rows.append((od, int(p), nc, nn, r))

    rows.sort(key=lambda x: -x[2])
    print(f"{'source':<24}{'leaf':>6}{'CONT':>7}{'note':>7}   verdict")
    for od, p, nc, nn, r in rows:
        v = "MOVE THE LEFT BOUND" if nc >= 3 * max(nn, 1) else ("mixed — eye needed" if nc > nn else "notes; leave it")
        print(f"  {od:<22}{p:>6}{nc:>7}{nn:>7}   {v}")
        if a.verify and nc:
            for head, rest in r["heads"][:6]:
                print(f"        [{head}] + {rest}")
    print(f"\ntotals: {tot_c} continuation, {tot_n} note, over {len(rows)} leaves")


if __name__ == "__main__":
    main()
