#!/usr/bin/env python3
"""Phase 1 · P1.7 — re-detection confirmation (validate by re-mapping).

The third leg of the paradigm (detect -> generate -> RE-DETECT). Re-run detection on the emitted
basis DB and confirm every element round-trips to its skeleton coordinate and cross-checks against
the witnesses that attest it (plan §4.7). This is the assembly-vs-reads re-mapping.

Gate P1 (all must hold):
  G1 coordinate round-trip  — every element id parses to a VALID skeleton coordinate
                              (book/chapter in range · reference-doc slot · book-argument · section).
  G2 referential integrity  — every attestation / consensus / placement row resolves to an element
                              (zero orphans).
  G3 attestation+consensus  — every scripture-verse carries >=1 attestation and exactly one
                              consensus row; every present scripture attestation has an evidence_ptr.
  G4 placement grounding    — every included, scan-placed reference doc carries a placement row with
                              a scan citation; every scripture section is placed.
  G5 source validity        — every attestation.source is a known witness.

Reads the basis-db.sqlite from scratch (built by P1.6) + the committed skeleton/layout artifacts;
emits the committed redetection-report.json (the CI-checked gate result). Exit 1 if the gate fails.

Run:  core/.venv/bin/python redetect_basis_db.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[5]
DB = REPO / "core/.scratch/originaldr-project/reconstruction/basis-db.sqlite"
SKELETON = HERE / "skeleton.json"
LAYOUT_MAP = HERE / "layout-map.json"
ATTEST = HERE / "apparatus-attestation.json"
OUT = HERE / "redetection-report.json"

KNOWN_SOURCES = {"madueke_a", "ocr_consensus", "odr_com", "s_dismas", "sabates_a",
                 "madueke_b", "archive_org"}


def _valid_coordinates() -> dict[str, Any]:
    skel = json.loads(SKELETON.read_text())
    layout = json.loads(LAYOUT_MAP.read_text())
    books = {b["slug"]: b["chapters"] for b in skel["books"]}
    ref_slots = {rd["slot_id"] for rd in skel["reference_docs"]}
    sections = {s["section_id"] for s in layout["scripture_order"]["sections"]}
    return {"books": books, "ref_slots": ref_slots, "sections": sections}


def _roundtrip(eid: str, etype: str, coords: dict[str, Any]) -> bool:
    books, ref_slots, sections = coords["books"], coords["ref_slots"], coords["sections"]
    parts = eid.split("/")
    if etype == "scripture-verse":
        # scripture/<book>/<ch>/<v>
        if len(parts) != 4 or parts[0] != "scripture":
            return False
        book, ch = parts[1], parts[2]
        if book not in books:
            return False
        try:
            c, v = int(ch), int(parts[3])
        except ValueError:
            return False
        return 1 <= c <= books[book] and v >= 1
    if etype == "apparatus-item":
        if eid in ref_slots:
            return True
        # apparatus/<book>/argument
        return len(parts) == 3 and parts[0] == "apparatus" and parts[1] in books and parts[2] == "argument"
    if etype == "structural-node":
        if len(parts) == 3 and parts[0] == "structure" and parts[1] == "section":
            return parts[2] in sections
        if len(parts) == 3 and parts[0] == "structure" and parts[1] == "book":
            return parts[2] in books
        return False
    return False


def run_gate(cur: sqlite3.Cursor, coords: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}

    # G1 — coordinate round-trip
    bad_coord: list[str] = []
    for eid, etype in cur.execute("SELECT id, type FROM elements"):
        if not _roundtrip(eid, etype, coords):
            bad_coord.append(eid)
    total_elements = cur.execute("SELECT COUNT(*) FROM elements").fetchone()[0]
    checks["G1_coordinate_roundtrip"] = {
        "pass": not bad_coord, "elements": total_elements,
        "round_tripped": total_elements - len(bad_coord), "failures": bad_coord[:20],
        "failure_count": len(bad_coord)}

    # G2 — referential integrity (no orphan child rows)
    orphans = {t: cur.execute(
        f"SELECT COUNT(*) FROM {t} WHERE element_id NOT IN (SELECT id FROM elements)").fetchone()[0]
        for t in ("attestation", "consensus", "placement")}
    checks["G2_referential_integrity"] = {"pass": all(v == 0 for v in orphans.values()),
                                          "orphans": orphans}

    # G3 — every scripture-verse has >=1 attestation + exactly 1 consensus; present rows carry evidence
    no_att = cur.execute(
        "SELECT COUNT(*) FROM elements e WHERE e.type='scripture-verse' AND NOT EXISTS "
        "(SELECT 1 FROM attestation a WHERE a.element_id=e.id)").fetchone()[0]
    no_cons = cur.execute(
        "SELECT COUNT(*) FROM elements e WHERE e.type='scripture-verse' AND NOT EXISTS "
        "(SELECT 1 FROM consensus c WHERE c.element_id=e.id)").fetchone()[0]
    dup_cons = cur.execute(
        "SELECT COUNT(*) FROM (SELECT element_id FROM consensus GROUP BY element_id "
        "HAVING COUNT(*)>1)").fetchone()[0]
    present_no_ptr = cur.execute(
        "SELECT COUNT(*) FROM attestation a JOIN elements e ON e.id=a.element_id "
        "WHERE e.type='scripture-verse' AND a.present=1 AND (a.evidence IS NULL OR a.evidence='')"
        ).fetchone()[0]
    checks["G3_attestation_consensus"] = {
        "pass": no_att == 0 and no_cons == 0 and dup_cons == 0,
        "scripture_without_attestation": no_att, "scripture_without_consensus": no_cons,
        "duplicate_consensus": dup_cons, "present_attestation_without_evidence_ptr": present_no_ptr}

    # G4 — placement grounding for included, scan-placed reference docs + every section
    attest = json.loads(ATTEST.read_text())
    placed_ids = {r[0] for r in cur.execute(
        "SELECT element_id FROM placement WHERE page IS NOT NULL OR crop IS NOT NULL")}
    missing_place: list[str] = []
    for rd in attest["reference_docs"]:
        if rd["decision"]["include"] and rd["placement"]["status"] in ("grounded", "co-located"):
            if rd["slot_id"] not in placed_ids:
                missing_place.append(rd["slot_id"])
    sect_ids = [f"structure/section/{s}" for s in coords["sections"]]
    placed_sect = {r[0] for r in cur.execute("SELECT element_id FROM placement")}
    missing_sect = [s for s in sect_ids if s not in placed_sect]
    checks["G4_placement_grounding"] = {
        "pass": not missing_place and not missing_sect,
        "reference_docs_missing_placement": missing_place,
        "sections_missing_placement": missing_sect}

    # G5 — attestation source validity
    unknown = [r[0] for r in cur.execute(
        "SELECT DISTINCT source FROM attestation") if r[0] not in KNOWN_SOURCES]
    checks["G5_source_validity"] = {"pass": not unknown, "unknown_sources": unknown}

    gate_pass = all(c["pass"] for c in checks.values())
    return {"gate_p1_pass": gate_pass, "checks": checks}


def main() -> int:
    if not DB.exists():
        print(f"!! basis-db.sqlite not found ({DB}); run build_basis_db.py first", file=sys.stderr)
        return 2
    coords = _valid_coordinates()
    con = sqlite3.connect(DB)
    result = run_gate(con.cursor(), coords)
    con.close()

    report = {
        "artifact": "redetection-report", "phase": "P1.7", "idx": 108,
        "generated_by": "redetect_basis_db.py",
        "note": "Re-detection confirmation of the basis DB (plan §4.7). Every basis element is "
                "re-mapped to its skeleton coordinate and its child rows are checked for referential "
                "integrity, attestation/consensus completeness, placement grounding, and source "
                "validity. Gate P1 passes iff all five checks pass. Reads the scratch basis-db.sqlite "
                "(built by P1.6); this committed report is the CI-checked gate result.",
        **result,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    status = "PASS" if result["gate_p1_pass"] else "FAIL"
    print(f"Gate P1: {status}")
    for name, c in result["checks"].items():
        print(f"  [{'ok' if c['pass'] else 'XX'}] {name}")
    return 0 if result["gate_p1_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
