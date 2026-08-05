#!/usr/bin/env python3
"""NON-DESTRUCTIVE diagnostic: run the CURRENT detect_s_dismas parser over every
book and compare chapter/verse coverage against the on-disk reference reads AND
the expected skeleton chapter counts. Never writes reads/s_dismas.json. Read-only.
Reveals the net effect of a regeneration: chapters recovered, chapters lost,
whether each book now hits its expected chapter count, and verse-count drift."""
from __future__ import annotations
import json
import sys
from collections import defaultdict
from pathlib import Path

FIX = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/"
           "gold/mask_engine/originaldr_reconstruction")
sys.path.insert(0, str(FIX))
import detect_s_dismas as D  # noqa: E402

REF = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/.scratch/"
           "originaldr-project/reconstruction/reads/s_dismas.json")
PILOT = {"genesis", "psalms", "matthew", "apocalypse"}

ref = json.loads(REF.read_text())
ref_ch: dict[str, set] = defaultdict(set)
ref_vc: dict[str, int] = defaultdict(int)
for r in ref["reads"]:
    p = r["skeleton_id"].split("/")
    if len(p) == 4 and p[0] == "scripture":
        ref_ch[p[1]].add(int(p[2]))
        ref_vc[p[1]] += 1

pairs = D.book_files()
print(f"{'book':22s} {'exp':>3s} {'refC':>4s} {'newC':>4s} {'=exp?':>5s} "
      f"{'refV':>6s} {'newV':>6s} {'dV':>5s}  notes")
print("-" * 92)
recovered, lost_ch, now_complete, still_short, big_vloss = [], [], [], [], []
for slug, pdf in pairs:
    exp = D._BOOK_CH.get(slug, 0)
    reads, warn = D.detect_book(slug, pdf)
    new_ch = {int(r["skeleton_id"].split("/")[2]) for r in reads}
    new_v = len(reads)
    rc, rv = ref_ch.get(slug, set()), ref_vc.get(slug, 0)
    gained = sorted(new_ch - rc)
    lost = sorted(rc - new_ch)
    hits_exp = (len(new_ch) == exp)
    note = ""
    if gained:
        note += f" +ch{gained}"; recovered.append((slug, gained))
    if lost:
        note += f" -ch{lost}"; lost_ch.append((slug, lost))
    dv = new_v - rv
    if hits_exp and len(rc) != exp:
        note += " ->COMPLETE"; now_complete.append(slug)
    if not hits_exp:
        miss = sorted(set(range(1, exp + 1)) - new_ch)
        note += f" [short {miss[:6]}]"; still_short.append((slug, miss))
    if dv <= -10:
        big_vloss.append((slug, dv))
    tag = "*" if slug in PILOT else " "
    print(f"{tag}{slug:21s} {exp:3d} {len(rc):4d} {len(new_ch):4d} "
          f"{('YES' if hits_exp else 'no'):>5s} {rv:6d} {new_v:6d} {dv:+5d}  {note}")

print("\n=== SUMMARY ===")
print(f"chapters RECOVERED: {[(s,g) for s,g in recovered]}")
print(f"chapters LOST:      {[(s,l) for s,l in lost_ch] or 'NONE'}")
print(f"books now COMPLETE (=expected): {now_complete}")
print(f"books STILL short of expected:  {[(s,m) for s,m in still_short]}")
print(f"books with verse loss <=-10:    {big_vloss}")
print(f"\nPILOT books status:")
for slug, pdf in pairs:
    if slug not in PILOT:
        continue
    exp = D._BOOK_CH.get(slug, 0)
    reads, _ = D.detect_book(slug, pdf)
    new_ch = {int(r["skeleton_id"].split("/")[2]) for r in reads}
    miss = sorted(set(range(1, exp + 1)) - new_ch)
    print(f"  {slug}: {len(new_ch)}/{exp} chapters {'COMPLETE' if not miss else f'MISSING {miss}'}")
