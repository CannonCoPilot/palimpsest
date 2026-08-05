#!/usr/bin/env python3
"""Splice ONLY genesis + psalms reads (from the rewritten drop-cap-anchored
detect_s_dismas) into the existing s_dismas.json reference, leaving the other 74
books' reads byte-identical. Recomputes coverage. Verifies invariants BEFORE
writing; refuses to write if a non-pilot book's read set changed."""
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
PILOT = ("genesis", "psalms")

ref = json.loads(REF.read_text())
old_reads = ref["reads"]

# fresh reads for the two pilot OT books from the rewritten detector
pairs = dict(D.book_files())
fresh = {b: D.detect_book(b, pairs[b])[0] for b in PILOT}
for b in PILOT:
    print(f"fresh {b}: {len(fresh[b])} reads")


def book_of(r: dict) -> str | None:
    p = r["skeleton_id"].split("/")
    return p[1] if len(p) >= 2 and p[0] == "scripture" else None


# rebuild in place: substitute each pilot book's contiguous run at its position
new_reads: list[dict] = []
emitted = set()
for r in old_reads:
    b = book_of(r)
    if b in PILOT:
        if b not in emitted:
            new_reads.extend(fresh[b])
            emitted.add(b)
        continue                      # drop old pilot-book read (replaced)
    new_reads.append(r)
for b in PILOT:                       # safety: append if book absent from ref
    if b not in emitted:
        new_reads.extend(fresh[b])
        emitted.add(b)

# ---- INVARIANT CHECK: non-pilot books untouched ----
def by_book(reads):
    d = defaultdict(list)
    for r in reads:
        b = book_of(r)
        if b:
            d[b].append(r)
    return d

old_bb, new_bb = by_book(old_reads), by_book(new_reads)
changed_nonpilot = []
for b in old_bb:
    if b in PILOT:
        continue
    if old_bb[b] != new_bb.get(b):
        changed_nonpilot.append(b)
if changed_nonpilot:
    print(f"ABORT: non-pilot books changed: {changed_nonpilot}")
    sys.exit(1)
print(f"OK: all {len(old_bb) - len(PILOT)} non-pilot books byte-identical")

# ---- recompute coverage ----
cov = D.coverage(new_reads)
missing = {}
got = defaultdict(set)
for r in new_reads:
    p = r["skeleton_id"].split("/")
    if len(p) == 4 and p[0] == "scripture":
        got[p[1]].add(int(p[2]))
for b, mx in D._BOOK_CH.items():
    if mx > 1 and b in got:
        miss = [c for c in range(1, mx + 1) if c not in got[b]]
        if miss:
            missing[b] = miss
cov["missing_chapters"] = missing

ref["reads"] = new_reads
ref["count"] = len(new_reads)
ref["coverage"] = cov

print(f"\ntotal reads: {len(old_reads)} -> {len(new_reads)} (delta {len(new_reads)-len(old_reads):+d})")
print(f"genesis chapters: {sorted(got['genesis'])[-3:]} count={len(got['genesis'])}")
print(f"psalms  chapters: count={len(got['psalms'])}")
print(f"missing_chapters (pilot): genesis={missing.get('genesis','-')} psalms={missing.get('psalms','-')}")
print(f"missing_chapters (all): {missing}")

if "--write" in sys.argv:
    REF.write_text(json.dumps(ref, ensure_ascii=False))
    print(f"\nWROTE {REF}")
else:
    print("\n(dry run — pass --write to persist)")
