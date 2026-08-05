"""Sizing query for B7 rung 2 (acquire a 1635 reference).

Dumps EVERY cell's per-reference scores -- passing cells included, which the
matrix artifacts discard -- and partitions them by worst-score band and by
arm gap  min(MODERN) - min(ARCHAIC).  S6 is the 1635 second edition; S1/S3/S9
are 1609 and act as the control that subtracts out the metric artifact.

Read-only.  Writes one JSON dump; changes no campaign state.
"""
import json, sys, statistics, collections

# run from ocr-spike/ with ../ocr-venv/bin/python

import gen1_matrix as MX
import gen1_pagemodel_eval as EV

ARCHAIC = ["s_dismas", "odr_com"]
MODERN = ["sabates_a", "madueke_b"]
OUT = ".campaign/band-cells.json"

rows = []
for ch in range(1, 51):
    EV.set_locus("genesis", ch)
    board = MX.build(use_r3=True)
    cells, verses = board["cells"], board["verses"]
    for v in verses:
        for s in MX.WITS:
            sc = (cells.get((s, v)) or {}).get("score") or {}
            vals = {r: sc.get(r) for r in MX.REFS if sc.get(r) is not None}
            if len(vals) < len(MX.REFS):
                continue                      # incomplete coverage: not comparable
            arc = min(vals[r] for r in ARCHAIC)
            mod = min(vals[r] for r in MODERN)
            rows.append({"ch": ch, "src": s, "verse": v,
                         "worst": min(vals.values()),
                         "archaic": arc, "modern": mod, "gap": mod - arc,
                         "scores": vals})
    print(f"ch{ch:>2} done  ({len(rows)} cells)", file=sys.stderr, flush=True)

json.dump(rows, open(OUT, "w"))

# ---- report ---------------------------------------------------------------
BANDS = [("[0.876,0.90)", 0.876, 0.90), ("[0.90,0.999)", 0.90, 0.999),
         ("[0.876,0.999) TOTAL", 0.876, 0.999),
         ("below 0.876", 0.0, 0.876), ("[0.999,1.0]", 0.999, 1.01)]

by_src = collections.defaultdict(list)
for r in rows:
    by_src[r["src"]].append(r)

print(f"\nTOTAL CELLS SCORED (all 4 refs present): {len(rows)}\n")
print(f"{'band':<22}" + "".join(f"{s:>9}" for s in sorted(by_src)))
for name, lo, hi in BANDS:
    line = f"{name:<22}"
    for s in sorted(by_src):
        line += f"{sum(1 for r in by_src[s] if lo <= r['worst'] < hi):>9}"
    print(line)

print("\nARM GAP  min(MODERN) - min(ARCHAIC)   [positive = archaic refs penalise this source]")
print(f"{'source':<10}{'n':>7}{'median':>10}{'mean':>10}{'p90':>10}{'>+0.024':>10}")
for s in sorted(by_src):
    g = sorted(r["gap"] for r in by_src[s])
    print(f"{s:<10}{len(g):>7}{statistics.median(g):>10.4f}{statistics.mean(g):>10.4f}"
          f"{g[int(0.9 * len(g))]:>10.4f}{sum(1 for x in g if x > 0.024):>10}")

# The decisive number: cells in band whose gap exceeds the shift a correct
# 1635 reference could plausibly supply, i.e. cells an edition fix could move.
print("\nCELLS IN [0.876,0.999) REACHABLE BY AN EDITION FIX")
print("   (worst score is set by an ARCHAIC ref, and gap > threshold)")
print(f"{'source':<10}{'gap>0':>9}{'gap>0.024':>12}{'gap>0.05':>10}{'gap>0.10':>10}")
for s in sorted(by_src):
    b = [r for r in by_src[s] if 0.876 <= r["worst"] < 0.999 and r["archaic"] < r["modern"]]
    print(f"{s:<10}{len(b):>9}"
          f"{sum(1 for r in b if r['gap'] > 0.024):>12}"
          f"{sum(1 for r in b if r['gap'] > 0.05):>10}"
          f"{sum(1 for r in b if r['gap'] > 0.10):>10}")

print("\nSUB-BAR HALF ONLY  [0.876,0.90)  -- these are the cells that move the BOARD")
for s in sorted(by_src):
    b = [r for r in by_src[s] if 0.876 <= r["worst"] < 0.90]
    reach = [r for r in b if r["archaic"] < r["modern"]]
    print(f"  {s}: {len(b)} in band, {len(reach)} archaic-limited, "
          f"{sum(1 for r in reach if r['gap'] > 0.024)} with gap > +0.024")
