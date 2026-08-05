#!/usr/bin/env python3
"""Explore the 55 archaic-only coords: surface, attestation, and shift-signal vs neighbours."""
import re
import sqlite3
from pathlib import Path

DB = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/projects/originaldr/reconstruction/basis-db.sqlite")
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def toks(s):
    return set(w.lower() for w in WORD.findall(s or "") if len(w) >= 3)


def jac(a, b):
    A, B = toks(a), toks(b)
    return len(A & B) / len(A | B) if (A or B) else 0.0


# archaic-only = render_archaic present, render_modern null/empty
rows = cur.execute(
    "SELECT id, render_archaic FROM elements WHERE type='scripture-verse' "
    "AND render_archaic IS NOT NULL AND TRIM(render_archaic)<>'' "
    "AND (render_modern IS NULL OR TRIM(render_modern)='') ORDER BY id").fetchall()
print(f"total archaic-only: {len(rows)}")

from collections import Counter
bybook = Counter(r[0].split("/")[1] for r in rows)
print("by book:", dict(bybook))
print()

for eid, ra in rows:
    _, book, ch, v = eid.split("/")
    v = int(v)
    srcs = [s for (s,) in cur.execute(
        "SELECT source FROM attestation WHERE element_id=? AND present=1 ORDER BY source", (eid,)).fetchall()]
    cons = cur.execute("SELECT indep_depth, tier, support_depth FROM consensus WHERE element_id=?", (eid,)).fetchone()
    indep, tier, sup = cons if cons else (None, None, None)
    # neighbours: modern surfaces of same-chapter verses v-2..v+1
    neigh = {}
    for nv in (v - 2, v - 1, v, v + 1):
        nid = f"scripture/{book}/{ch}/{nv}"
        rm = cur.execute("SELECT render_modern FROM elements WHERE id=?", (nid,)).fetchone()
        if rm and rm[0] and rm[0].strip():
            neigh[nv] = rm[0]
    # best jaccard vs a neighbour's MODERN surface (shift signal)
    best = max(((nv, jac(ra, txt)) for nv, txt in neigh.items()), key=lambda x: x[1], default=(None, 0.0))
    # is this the last verse of the chapter in the modern skeleton?
    maxmodv = cur.execute(
        "SELECT MAX(CAST(SUBSTR(id, LENGTH(?)+1) AS INTEGER)) FROM elements "
        "WHERE type='scripture-verse' AND id LIKE ? AND render_modern IS NOT NULL AND TRIM(render_modern)<>''",
        (f"scripture/{book}/{ch}/", f"scripture/{book}/{ch}/%")).fetchone()[0]
    beyond = (maxmodv is not None and v > maxmodv)
    print(f"{eid:28s} d={indep}/{sup} {str(tier):8s} src={','.join(srcs):30s} "
          f"beyondCh(max{maxmodv})={beyond} bestNeighJac=v{best[0]}:{best[1]:.2f}")
    print(f"    ARC: {ra[:110]}")
    if best[0] is not None and best[1] >= 0.4:
        print(f"    ~v{best[0]} MOD: {neigh[best[0]][:110]}")
con.close()
