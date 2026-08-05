#!/usr/bin/env python3
"""Explore (a) the 199 coverage-gap coords' archaic attestation, (b) apparatus archaic surfaces."""
import sqlite3
from collections import Counter
from pathlib import Path

DB = Path("/Users/nathanielcannon/Claude/Projects/palimpsest/projects/originaldr/reconstruction/basis-db.sqlite")
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = con.cursor()

ARCHAIC_SRCS = {"ocr_consensus", "s_dismas", "odr_com"}

print("=== (A) 199 COVERAGE-GAP coords: any archaic attestation at all? ===")
gaps = cur.execute(
    "SELECT id FROM elements WHERE type='scripture-verse' "
    "AND render_modern IS NOT NULL AND TRIM(render_modern)<>'' "
    "AND (render_archaic IS NULL OR TRIM(render_archaic)='') ORDER BY id").fetchall()
print(f"total coverage-gap: {len(gaps)}")
# for each gap, do ANY archaic source have a present attestation with a surface_archaic?
has_any_archaic_att = 0
has_archaic_surface = 0
by_book_recoverable = Counter()
by_book_total = Counter()
examples = []
for (eid,) in gaps:
    book = eid.split("/")[1]
    by_book_total[book] += 1
    rows = cur.execute(
        "SELECT source, present, surface_archaic FROM attestation WHERE element_id=? AND source IN (?,?,?)",
        (eid, *ARCHAIC_SRCS)).fetchall()
    any_present = any(p for _, p, _ in rows)
    any_surface = any((sa and sa.strip()) for _, p, sa in rows if p)
    if any_present:
        has_any_archaic_att += 1
    if any_surface:
        has_archaic_surface += 1
        by_book_recoverable[book] += 1
        if len(examples) < 12:
            src_surf = [(s, (sa or '')[:60]) for s, p, sa in rows if p and sa and sa.strip()]
            examples.append((eid, src_surf))
print(f"  gaps with ANY present archaic attestation: {has_any_archaic_att}")
print(f"  gaps with a non-empty archaic SURFACE (recoverable-in-principle): {has_archaic_surface}")
print(f"  recoverable by book: {dict(by_book_recoverable)}")
print(f"  total gaps by book: {dict(by_book_total)}")
print("  examples of gaps WITH an archaic surface (why not consensus-called?):")
for eid, ss in examples:
    print(f"    {eid}")
    for s, surf in ss:
        print(f"       {s}: {surf}")

print("\n=== (B) APPARATUS elements: archaic surfaces available? ===")
apps = cur.execute("SELECT id FROM elements WHERE type='apparatus-item' ORDER BY id").fetchall()
print(f"total apparatus-item elements: {len(apps)}")
# which sources attest apparatus items, with modern vs archaic surfaces?
src_mod = Counter()
src_arc = Counter()
for (eid,) in apps:
    for s, p, sm, sa in cur.execute(
            "SELECT source, present, surface_modern, surface_archaic FROM attestation WHERE element_id=? AND present=1",
            (eid,)).fetchall():
        if sm and sm.strip():
            src_mod[s] += 1
        if sa and sa.strip():
            src_arc[s] += 1
print(f"  apparatus MODERN-surface counts by source: {dict(src_mod)}")
print(f"  apparatus ARCHAIC-surface counts by source: {dict(src_arc)}")
# sample an apparatus item's attestations
sample = apps[0][0] if apps else None
if sample:
    print(f"  sample apparatus item {sample}:")
    for s, p, sm, sa in cur.execute(
            "SELECT source, present, surface_modern, surface_archaic FROM attestation WHERE element_id=? AND present=1",
            (sample,)).fetchall():
        print(f"     {s}: mod={(sm or '')[:40]!r} arc={(sa or '')[:40]!r}")
con.close()
