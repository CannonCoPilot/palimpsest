#!/usr/bin/env python3
"""Classify the 55 archaic-only coords using the documented spelling fold (so modern↔archaic
orthography doesn't mask a content match) + chapter-overflow + witness-depth signals."""
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REC = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/core/tests/fixtures/gold/mask_engine/originaldr_reconstruction")
sys.path.insert(0, str(REC))
import spelling_glyph_model as sgm  # type: ignore

DB = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/projects/originaldr/reconstruction/basis-db.sqlite")
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()


def foldset(s):
    return set(sgm.fold_tokens(s or "", min_len=2))


def jac(a, b):
    A, B = foldset(a), foldset(b)
    return len(A & B) / len(A | B) if (A or B) else 0.0


rows = cur.execute(
    "SELECT id, render_archaic FROM elements WHERE type='scripture-verse' "
    "AND render_archaic IS NOT NULL AND TRIM(render_archaic)<>'' "
    "AND (render_modern IS NULL OR TRIM(render_modern)='') ORDER BY id").fetchall()

SHIFT = 0.6
cls = Counter()
out = []
for eid, ra in rows:
    _, book, ch, v = eid.split("/")
    v = int(v)
    srcs = [s for (s,) in cur.execute(
        "SELECT source FROM attestation WHERE element_id=? AND present=1 ORDER BY source", (eid,)).fetchall()]
    cons = cur.execute("SELECT indep_depth, tier FROM consensus WHERE element_id=?", (eid,)).fetchone()
    indep, tier = cons if cons else (None, None)
    # fold-aware similarity to EVERY modern verse in the same chapter (duplicate-in-chapter signal:
    # an OCR verse-number misparse can duplicate a FAR verse, not just the neighbour)
    chapter = cur.execute(
        "SELECT id, render_modern FROM elements WHERE type='scripture-verse' AND id LIKE ? "
        "AND render_modern IS NOT NULL AND TRIM(render_modern)<>''",
        (f"scripture/{book}/{ch}/%",)).fetchall()
    best = (None, 0.0)
    for mid, rm in chapter:
        mv = int(mid.split("/")[-1])
        j = jac(ra, rm)
        if j > best[1]:
            best = (mv, j)
    if best[1] >= SHIFT:
        c = "shifted-duplicate"       # content already present at another modern coord in the chapter
    elif (indep or 1) >= 2:
        c = "genuine-split"           # multi-witness archaic content with no modern coordinate
    else:
        c = "single-witness-unresolved"
    cls[c] += 1
    out.append((eid, c, indep, tier, ",".join(srcs), best[0], round(best[1], 2)))

print("=== classification summary ===")
for k, n in cls.most_common():
    print(f"  {k:26s} {n}")
print(f"  TOTAL {sum(cls.values())}")
print("\n=== by book × class ===")
bookcls = Counter((e.split('/')[1], c) for e, c, *_ in out)
for (bk, c), n in sorted(bookcls.items()):
    print(f"  {bk:16s} {c:26s} {n}")
print("\n=== genuine-split detail (the real versification divergences) ===")
for eid, c, indep, tier, srcs, nv, j in out:
    if c == "genuine-split":
        print(f"  {eid:26s} d={indep} {tier:8s} {srcs:20s} bestPrevJac=v{nv}:{j}")
print("\n=== single-witness-unresolved detail ===")
for eid, c, indep, tier, srcs, nv, j in out:
    if c == "single-witness-unresolved":
        print(f"  {eid:26s} {srcs:12s} bestPrevJac=v{nv}:{j}")
con.close()
