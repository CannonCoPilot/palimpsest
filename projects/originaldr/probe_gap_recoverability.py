#!/usr/bin/env python3
"""Probe: are the 199 coverage-gap verses recoverable from the archive.org djvu OCR?
For a sample, take the verse's MODERN text, fold it, and best-window-match against each djvu witness.
A high match ⇒ the archaic print reading exists in the (independent) archive.org OCR ⇒ recoverable.
A low match ⇒ the OCR family dropped it too ⇒ genuine gap, modern-fallback is the honest disposition."""
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path("/Users/nathanielcannon/Claude/Projects/palimpsest")
AO = REPO / "projects/originaldr/sources/archive-org"
DB = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/projects/originaldr/reconstruction/basis-db.sqlite")

print("djvu files present:", sorted(p.name for p in AO.glob("*_djvu.txt")) if AO.exists() else "AO MISSING")

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def toks(s):
    return [w.lower() for w in WORD.findall(s or "")]


# load djvu witnesses as token streams
djvu = {}
for p in sorted(AO.glob("*_djvu.txt")):
    djvu[p.stem.replace("_djvu", "")] = toks(p.read_text(encoding="utf-8", errors="ignore"))
print("djvu witnesses:", {k: len(v) for k, v in djvu.items()})


def best_window_overlap(probe_tokens, hay_tokens):
    """Max token-set overlap fraction of `probe` found in any window of `hay` the probe's length."""
    P = set(probe_tokens)
    if not P or not hay_tokens:
        return 0.0
    n = len(probe_tokens)
    best = 0
    # slide a coarse window (step n//2) for speed
    step = max(1, n // 2)
    for i in range(0, max(1, len(hay_tokens) - n + 1), step):
        w = set(hay_tokens[i:i + n])
        ov = len(P & w)
        if ov > best:
            best = ov
    return best / len(P)


con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()
gaps = [e for (e,) in cur.execute(
    "SELECT id FROM elements WHERE type='scripture-verse' "
    "AND render_modern IS NOT NULL AND TRIM(render_modern)<>'' "
    "AND (render_archaic IS NULL OR TRIM(render_archaic)='') ORDER BY id").fetchall()]

# sample across the main gap books
import itertools
by_book = {}
for e in gaps:
    by_book.setdefault(e.split("/")[1], []).append(e)
sample = []
for bk in ("ecclesiasticus", "isaie", "4-esdras", "zacharias", "proverbs", "ezechiel", "jeremie", "osee"):
    sample += by_book.get(bk, [])[:2]

print(f"\nprobing {len(sample)} sample gap verses vs {len(djvu)} djvu witnesses:")
for eid in sample:
    rm = cur.execute("SELECT render_modern FROM elements WHERE id=?", (eid,)).fetchone()[0]
    pt = toks(rm)
    scores = {name: round(best_window_overlap(pt, hay), 2) for name, hay in djvu.items()}
    best = max(scores.values()) if scores else 0.0
    print(f"  {eid:26s} ntok={len(pt):3d} best={best:.2f}  {scores}")
    print(f"       MOD: {rm[:90]}")
con.close()
