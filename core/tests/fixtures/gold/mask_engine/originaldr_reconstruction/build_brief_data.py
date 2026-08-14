#!/usr/bin/env python3
"""Materialize a small, COMMITTED brief-data.json from the gitignored basis-db.sqlite.

The academic brief (gen_originaldr_brief.py) is CI-safe: it reads only committed artifacts,
never the 94 MB basis-db.sqlite. But the genome-browser figures that need per-position,
per-source surfaces — the source-track browser, the variant pileups, the book×source
contributor matrix — cannot be computed from the existing aggregate JSONs. This script bridges
that: it reads the gitignored basis DB (the single source of truth) and writes a *small* sampled
artifact (brief-data.json) that the brief then reads. Same pattern as build_basis_db.py etc.

Everything sampled here is deterministic (fixed book/chapter selection, ORDER BY on every query,
no timestamps) so the committed artifact is byte-stable across runs on the same basis DB.

Run:  core/.venv/bin/python build_brief_data.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # R9.6: sibling import
import project_root as pr  # noqa: E402  R9.6: one derived root

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
DB = pr.BASIS_DB
OUT = HERE / "brief-data.json"

# The five substantive scripture witnesses (archive_org = placement only, madueke_b ≈ empty).
SCRIPTURE_SOURCES = ["madueke_a", "sabates_a", "ocr_consensus", "s_dismas", "odr_com"]
# Modern-surface vs archaic-surface witnesses (which column carries their reading).
SOURCE_EDITION = {"madueke_a": "modern", "sabates_a": "modern",
                  "ocr_consensus": "archaic", "s_dismas": "archaic", "odr_com": "archaic"}
# Two contrasting chapters for the source-track browser: a 5-witness clean book and a
# 3-witness ocr-only book (the archaic lineages stop at Wisdom, so the prophets lose depth).
TRACK_CHAPTERS = [("genesis", 1), ("isaie", 1)]
# Books to draw one variant-pileup locus from (the lowest-agreement verse in each).
PILEUP_BOOKS = ["genesis", "matthew", "psalms", "1-corinthians", "john", "isaie"]
SURFACE_CAP = 160  # trim raw surfaces for compact, legible pileup panels


def _clip(s: str | None) -> str:
    s = (s or "").strip()
    return s if len(s) <= SURFACE_CAP else s[:SURFACE_CAP - 1] + "…"


def _verse_no(ref: str) -> int:
    try:
        return int(ref.rsplit("/", 1)[-1])
    except ValueError:
        return 0


def _num(v: Any) -> float | None:
    try:
        return round(float(v), 3)
    except (TypeError, ValueError):
        return None


def _present_sources(cur: sqlite3.Cursor, element_id: str) -> list[str]:
    rows = cur.execute(
        "SELECT source FROM attestation WHERE element_id=? AND present=1", (element_id,)).fetchall()
    return [r[0] for r in rows if r[0] in SCRIPTURE_SOURCES]


def book_source_matrix(cur: sqlite3.Cursor) -> dict[str, Any]:
    totals = dict(cur.execute(
        "SELECT book, COUNT(*) FROM elements WHERE type='scripture-verse' GROUP BY book").fetchall())
    pairs = cur.execute(
        "SELECT e.book, a.source, COUNT(*) FROM attestation a JOIN elements e ON a.element_id=e.id "
        "WHERE e.type='scripture-verse' AND a.present=1 GROUP BY e.book, a.source").fetchall()
    by_book: dict[str, dict[str, int]] = {}
    for book, source, n in pairs:
        if source in SCRIPTURE_SOURCES:
            by_book.setdefault(book, {})[source] = n
    return {"sources": SCRIPTURE_SOURCES,
            "books": {b: {"total": totals.get(b, 0), "by_source": by_book.get(b, {})}
                      for b in sorted(totals)}}


def depth_histograms(cur: sqlite3.Cursor) -> dict[str, Any]:
    def hist(col: str) -> dict[str, int]:
        return {str(k): v for k, v in cur.execute(
            f"SELECT {col}, COUNT(*) FROM consensus GROUP BY {col} ORDER BY {col}").fetchall()}
    return {"support_depth": hist("support_depth"), "indep_depth": hist("indep_depth"),
            "note": "support_depth = attesting sources (read depth, max 5); indep_depth = "
                    "independent lineages (max 4). The gap is the non-independence correction "
                    "(madueke_a & sabates_a share the Madueke lineage)."}


def source_tracks(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    tracks = []
    for book, ch in TRACK_CHAPTERS:
        prefix = f"scripture/{book}/{ch}/"
        rows = cur.execute(
            "SELECT e.id, e.canonical_ref, c.agreement, c.support_depth, c.indep_depth, c.tier "
            "FROM elements e JOIN consensus c ON e.id=c.element_id "
            "WHERE e.type='scripture-verse' AND e.id LIKE ? ", (prefix + "%",)).fetchall()
        verses = []
        for eid, ref, agree, sup, indep, tier in sorted(rows, key=lambda r: _verse_no(r[1])):
            present = _present_sources(cur, eid)
            verses.append({"ref": ref, "verse": _verse_no(ref), "agreement": round(agree, 4),
                           "support_depth": sup, "indep_depth": indep, "tier": tier,
                           "present": {s: (s in present) for s in SCRIPTURE_SOURCES}})
        tracks.append({"book": book, "chapter": ch, "n_verses": len(verses), "verses": verses})
    return tracks


def variant_pileups(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    pileups = []
    for book in PILEUP_BOOKS:
        row = cur.execute(
            "SELECT e.id, e.canonical_ref, e.render_modern, c.agreement, c.support_depth, "
            "c.indep_depth, c.tier, c.variant_pileup FROM elements e JOIN consensus c "
            "ON e.id=c.element_id WHERE e.book=? AND e.type='scripture-verse' AND c.support_depth>=2 "
            "ORDER BY c.agreement ASC, e.id ASC LIMIT 1", (book,)).fetchone()
        if not row:
            continue
        eid, ref, called, agree, sup, indep, tier, pileup_json = row
        jac = {}
        for v in json.loads(pileup_json or "[]"):
            jac[v["source"]] = round(v.get("jaccard", 0.0), 3)
        reads = []
        for src, s_mod, s_arc, conf in cur.execute(
                "SELECT source, surface_modern, surface_archaic, confidence FROM attestation "
                "WHERE element_id=? AND present=1 ORDER BY source", (eid,)).fetchall():
            if src not in SCRIPTURE_SOURCES:
                continue
            edition = SOURCE_EDITION[src]
            surface = s_mod if edition == "modern" else s_arc
            reads.append({"source": src, "edition": edition, "surface": _clip(surface),
                          "jaccard": jac.get(src), "confidence": _num(conf)})
        pileups.append({"ref": ref, "book": book, "agreement": round(agree, 4),
                        "support_depth": sup, "indep_depth": indep, "tier": tier,
                        "called_modern": _clip(called), "reads": reads})
    return pileups


def build() -> dict[str, Any]:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = con.cursor()
    n_scripture = cur.execute(
        "SELECT COUNT(*) FROM elements WHERE type='scripture-verse'").fetchone()[0]
    data = {
        "artifact": "brief-data.json",
        "phase": "P3.2",
        "generated_by": "build_brief_data.py",
        "note": "Sampled, committed projection of the gitignored basis-db.sqlite for the genome-"
                "browser figures (source-track browser, variant pileups, book×source matrix). "
                "Deterministic: fixed selection + ORDER BY, no timestamps.",
        "source_of_truth": str(pr.BASIS_DB.relative_to(pr.REPO)) + " (regenerable)",
        "n_scripture_verses": n_scripture,
        "book_source_matrix": book_source_matrix(cur),
        "depth_histograms": depth_histograms(cur),
        "source_tracks": source_tracks(cur),
        "variant_pileups": variant_pileups(cur),
    }
    con.close()
    return data


def main() -> int:
    if not DB.exists():
        print(f"!! basis-db.sqlite not found at {DB} — regenerate via build_basis_db.py", file=sys.stderr)
        return 2
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m = data["book_source_matrix"]
    print(f"wrote {OUT.relative_to(REPO)} · {len(m['books'])} books · "
          f"{len(data['source_tracks'])} tracks · {len(data['variant_pileups'])} pileups · "
          f"{OUT.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
