#!/usr/bin/env python3
"""Phase 1 · P1.6 — basis database emission.

Emit the core basis database — the single source of truth for both renderings (plan §4.6). It
JOINS the three Phase-1 products into one relational store:

  * scripture verses (37,185 elements) from the P1.3 consensus files — each already carries full
    per-source attestation, the consensus call, and the resolved modern/archaic render surfaces;
  * apparatus items from the P1.5 apparatus-attestation (26 reference docs + 76 book arguments),
    with per-source presence + the scan-grounded placement + the include/exclude decision;
  * structural nodes — the 6 scan-grounded scripture sections + 76 book nodes from the P1.4
    layout-map scripture_order — carrying the tome/part placement the verses inherit.

Tables (plan §4.6):
  elements(id, type, canonical_ref, book, section_id, render_modern, render_archaic, meta)
  attestation(element_id, source, present, surface_modern, surface_archaic, locus, method,
              confidence, evidence)
  consensus(element_id, lemma, agreement, support_depth, indep_depth, tier, variant_pileup)
  placement(element_id, tome_position, page, crop, identifying_text, ocr_offset, sha256)

The `.sqlite` is written to the gitignored scratch tree (it derives from — and is comparable in
size to — the 95 MB consensus corpus, which is likewise regenerable scratch). What is COMMITTED
is this builder + `basis-db.json`: a diff-reviewable, CI-safe snapshot (schema, table row counts,
per-book verse + confidence-tier/independent-depth distributions, the full small apparatus /
structural / placement records, and the built DB's sha256 + size). A 95 MB dump cannot be
diff-reviewed; these counts and distributions can, and the artifact tests assert against them.

Run:  core/.venv/bin/python build_basis_db.py
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
CONS = REPO / "core/.scratch/originaldr-project/reconstruction/consensus"
SKELETON = HERE / "skeleton.json"
LAYOUT_MAP = HERE / "layout-map.json"
ATTEST = HERE / "apparatus-attestation.json"
OUT_DB = REPO / "core/.scratch/originaldr-project/reconstruction/basis-db.sqlite"
OUT_JSON = HERE / "basis-db.json"

SCHEMA = """
CREATE TABLE elements(
  id TEXT PRIMARY KEY, type TEXT NOT NULL, canonical_ref TEXT, book TEXT, section_id TEXT,
  render_modern TEXT, render_archaic TEXT, meta TEXT);
CREATE TABLE attestation(
  element_id TEXT NOT NULL, source TEXT NOT NULL, present INTEGER, surface_modern TEXT,
  surface_archaic TEXT, locus TEXT, method TEXT, confidence REAL, evidence TEXT);
CREATE TABLE consensus(
  element_id TEXT PRIMARY KEY, lemma TEXT, agreement REAL, support_depth INTEGER,
  indep_depth INTEGER, tier TEXT, variant_pileup TEXT);
CREATE TABLE placement(
  element_id TEXT PRIMARY KEY, tome_position TEXT, page INTEGER, crop TEXT, identifying_text TEXT,
  ocr_offset INTEGER, sha256 TEXT);
CREATE INDEX ix_att_element ON attestation(element_id);
CREATE INDEX ix_att_source ON attestation(source);
CREATE INDEX ix_el_type ON elements(type);
CREATE INDEX ix_el_book ON elements(book);
CREATE INDEX ix_cons_tier ON consensus(tier);
"""


def _surfaces(spelling: Optional[str], surface: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if spelling == "modern":
        return surface, None
    if spelling == "archaic":
        return None, surface
    return None, None                                  # unknown spelling axis


def ingest_scripture(cur: sqlite3.Cursor, section_of_book: dict[str, str]) -> dict[str, Any]:
    """Load every consensus book; return per-book + aggregate stats for the snapshot."""
    per_book: dict[str, Any] = {}
    tier_tot: Counter[str] = Counter()
    depth_tot: Counter[int] = Counter()
    n_el = n_att = 0
    agree_sum = 0.0
    for path in sorted(CONS.glob("*.json")):
        book = path.stem
        doc = json.loads(path.read_text())
        els = doc.get("elements") or []
        tiers: Counter[str] = Counter()
        depths: Counter[int] = Counter()
        for e in els:
            eid = e["id"]
            con = e.get("consensus") or {}
            cur.execute(
                "INSERT INTO elements(id,type,canonical_ref,book,section_id,render_modern,"
                "render_archaic,meta) VALUES(?,?,?,?,?,?,?,?)",
                (eid, e.get("type", "scripture-verse"), eid.replace("scripture/", "", 1), book,
                 section_of_book.get(book), (e.get("render") or {}).get("modern_form"),
                 (e.get("render") or {}).get("archaic_form"), None))
            for a in e.get("attestation") or []:
                sm, sa = _surfaces(a.get("spelling"), a.get("surface"))
                cur.execute(
                    "INSERT INTO attestation(element_id,source,present,surface_modern,"
                    "surface_archaic,locus,method,confidence,evidence) VALUES(?,?,?,?,?,?,?,?,?)",
                    (eid, a.get("source"), 1 if a.get("present") else 0, sm, sa, a.get("locus"),
                     a.get("method"), a.get("local_confidence"), a.get("evidence_ptr")))
                n_att += 1
            cur.execute(
                "INSERT INTO consensus(element_id,lemma,agreement,support_depth,indep_depth,tier,"
                "variant_pileup) VALUES(?,?,?,?,?,?,?)",
                (eid, con.get("lemma_neutral"), con.get("agreement"), con.get("support_depth"),
                 con.get("independent_depth"), con.get("confidence_tier"),
                 json.dumps(con.get("variant_pileup") or [], ensure_ascii=False)))
            t = con.get("confidence_tier")
            if t:
                tiers[t] += 1
            d = con.get("independent_depth")
            if isinstance(d, int):
                depths[d] += 1
            if isinstance(con.get("agreement"), (int, float)):
                agree_sum += float(con["agreement"])
            n_el += 1
        tier_tot.update(tiers)
        depth_tot.update(depths)
        per_book[book] = {"elements": len(els), "tiers": dict(sorted(tiers.items())),
                          "indep_depth": {str(k): v for k, v in sorted(depths.items())}}
    return {"elements": n_el, "attestation_rows": n_att, "per_book": per_book,
            "tiers": dict(sorted(tier_tot.items())),
            "indep_depth": {str(k): v for k, v in sorted(depth_tot.items())},
            "mean_agreement": round(agree_sum / n_el, 4) if n_el else 0.0}


def ingest_structural(cur: sqlite3.Cursor, scripture_order: dict) -> tuple[dict[str, str], list[dict]]:
    """Section + book structural nodes; returns book->section map and the section records."""
    section_of_book: dict[str, str] = {}
    section_records: list[dict] = []
    for sec in scripture_order["sections"]:
        sid = f"structure/section/{sec['section_id']}"
        tome_position = f"{sec['tome']} · {sec['part']}"
        cur.execute("INSERT INTO elements(id,type,canonical_ref,book,section_id,render_modern,"
                    "render_archaic,meta) VALUES(?,?,?,?,?,?,?,?)",
                    (sid, "structural-node", sec["section_id"], None, sec["section_id"], None, None,
                     json.dumps({"tome": sec["tome"], "part": sec["part"],
                                 "ordinal_span": sec["ordinal_span"]}, ensure_ascii=False)))
        bl = sec.get("boundary_leaf") or {}
        lf = sec.get("layout_leaf_ref") or {}
        cur.execute("INSERT INTO placement(element_id,tome_position,page,crop,identifying_text,"
                    "ocr_offset,sha256) VALUES(?,?,?,?,?,?,?)",
                    (sid, tome_position, bl.get("page") or lf.get("page"),
                     bl.get("crop_image") or lf.get("crop_image"), bl.get("identifying_text"),
                     None, bl.get("sha256")))
        for b in sec["books"]:
            section_of_book[b["slug"]] = sec["section_id"]
        section_records.append({"section_id": sec["section_id"], "tome_position": tome_position,
                                "books": sec["book_count"]})
    for b in json.loads(SKELETON.read_text())["books"]:
        bid = f"structure/book/{b['slug']}"
        cur.execute("INSERT INTO elements(id,type,canonical_ref,book,section_id,render_modern,"
                    "render_archaic,meta) VALUES(?,?,?,?,?,?,?,?)",
                    (bid, "structural-node", b["slug"], b["slug"],
                     section_of_book.get(b["slug"]), None, None,
                     json.dumps({"ordinal": b["ordinal"], "testament": b["testament"],
                                 "chapters": b["chapters"]}, ensure_ascii=False)))
    return section_of_book, section_records


def ingest_apparatus(cur: sqlite3.Cursor, attest: dict) -> dict[str, Any]:
    """Reference-doc + book-argument apparatus elements with attestation + placement + decision.

    Placement is read from each reference doc's own `placement` block (copied from the layout-map
    into apparatus-attestation at P1.5), so the layout-map is not re-joined here.
    """
    n_ref = n_bookarg = n_att = 0
    for rd in attest["reference_docs"]:
        eid = rd["slot_id"]
        sab = rd["attestation"].get("sabates_a") or {}
        title = ((sab.get("evidence") or {}).get("title")) if sab.get("present") else None
        cur.execute("INSERT INTO elements(id,type,canonical_ref,book,section_id,render_modern,"
                    "render_archaic,meta) VALUES(?,?,?,?,?,?,?,?)",
                    (eid, "apparatus-item", eid.replace("apparatus/", "", 1), None, None, title, None,
                     json.dumps({"apparatus_class": "reference-doc", "section": rd["section"],
                                 "testament": rd["testament"], "decision": rd["decision"]},
                                ensure_ascii=False)))
        for src, rec in rd["attestation"].items():
            present = rec.get("present")
            cur.execute("INSERT INTO attestation(element_id,source,present,surface_modern,"
                        "surface_archaic,locus,method,confidence,evidence) VALUES(?,?,?,?,?,?,?,?,?)",
                        (eid, src, None if present is None else (1 if present else 0), None, None,
                         rec.get("status") or rec.get("granularity"), rec.get("granularity"), None,
                         json.dumps(rec, ensure_ascii=False)))
            n_att += 1
        pl = rd["placement"]
        cur.execute("INSERT INTO placement(element_id,tome_position,page,crop,identifying_text,"
                    "ocr_offset,sha256) VALUES(?,?,?,?,?,?,?)",
                    (eid, f"{rd['section']} · {rd['testament']}", pl.get("page"),
                     pl.get("crop_image"), pl.get("identifying_text"), None, None))
        n_ref += 1
    for bc in attest["book_channels"]:
        ba = bc["per_channel"]["book_argument"]
        present = (ba.get("sabates_a") or {}).get("present")
        eid = f"apparatus/{bc['slug']}/argument"
        cur.execute("INSERT INTO elements(id,type,canonical_ref,book,section_id,render_modern,"
                    "render_archaic,meta) VALUES(?,?,?,?,?,?,?,?)",
                    (eid, "apparatus-item", eid.replace("apparatus/", "", 1), bc["slug"], None,
                     None, None, json.dumps({"apparatus_class": "book-argument",
                                             "present": bool(present)}, ensure_ascii=False)))
        for src, rec in ba.items():
            cur.execute("INSERT INTO attestation(element_id,source,present,surface_modern,"
                        "surface_archaic,locus,method,confidence,evidence) VALUES(?,?,?,?,?,?,?,?,?)",
                        (eid, src, 1 if rec.get("present") else 0, None, None, None,
                         rec.get("granularity"), None, json.dumps(rec, ensure_ascii=False)))
            n_att += 1
        n_bookarg += 1
    return {"reference_docs": n_ref, "book_arguments": n_bookarg, "attestation_rows": n_att}


def main() -> int:
    for p in (CONS, SKELETON, LAYOUT_MAP, ATTEST):
        if not p.exists():
            print(f"!! missing input: {p}", file=sys.stderr)
            return 2
    layout = json.loads(LAYOUT_MAP.read_text())
    attest = json.loads(ATTEST.read_text())

    OUT_DB.parent.mkdir(parents=True, exist_ok=True)
    if OUT_DB.exists():
        OUT_DB.unlink()
    con = sqlite3.connect(OUT_DB)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    section_of_book, section_records = ingest_structural(cur, layout["scripture_order"])
    scripture = ingest_scripture(cur, section_of_book)
    apparatus = ingest_apparatus(cur, attest)
    con.commit()

    counts = {t: cur.execute("SELECT COUNT(*) FROM elements WHERE type=?", (t,)).fetchone()[0]
              for t in ("scripture-verse", "apparatus-item", "structural-node")}
    row_counts = {tbl: cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                  for tbl in ("elements", "attestation", "consensus", "placement")}
    src_counts = dict(sorted(cur.execute(
        "SELECT source, COUNT(*) FROM attestation GROUP BY source").fetchall()))
    cur.execute("VACUUM")
    con.commit()
    con.close()

    sha = hashlib.sha256(OUT_DB.read_bytes()).hexdigest()
    snapshot = {
        "artifact": "basis-db", "phase": "P1.6", "idx": 108, "generated_by": "build_basis_db.py",
        "note": "Committed snapshot of the basis database. The queryable basis-db.sqlite is written "
                "to the gitignored scratch tree (regenerable from the consensus corpus it derives "
                "from, and comparable in size); this JSON carries the schema, table row counts, "
                "per-book verse + confidence distributions, and the full apparatus/structural/"
                "placement records — the diff-reviewable, CI-safe view. Scripture render surfaces "
                "are materialized in the DB (needed for P2a/P2b); chapter-level apparatus text is "
                "coverage-tracked (P1.5) and sourced at render time from the pinned witnesses.",
        "sqlite": {"path": str(OUT_DB.relative_to(REPO)), "sha256": sha,
                   "size_bytes": OUT_DB.stat().st_size, "row_counts": row_counts},
        "schema": [s.strip() for s in SCHEMA.strip().split(";\n") if s.strip()],
        "element_counts": counts,
        "attestation_by_source": src_counts,
        "scripture": {"elements": scripture["elements"], "tiers": scripture["tiers"],
                      "indep_depth": scripture["indep_depth"],
                      "mean_agreement": scripture["mean_agreement"],
                      "per_book": scripture["per_book"]},
        "apparatus": apparatus,
        "structural": {"sections": section_records, "books": counts["structural-node"] - len(section_records)},
        "reference_doc_decisions": [{"slot_id": rd["slot_id"], "include": rd["decision"]["include"]}
                                    for rd in attest["reference_docs"]],
    }
    OUT_JSON.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    print(f"basis-db.sqlite  ·  {row_counts}  ·  elements {counts}  ·  "
          f"{OUT_DB.stat().st_size // (1024*1024)} MB  ·  snapshot -> {OUT_JSON.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
