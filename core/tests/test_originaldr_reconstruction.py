"""Guards for the committed OriginalDR (idx 108) Phase-1 reconstruction artifacts.

Corpus-free: these read the committed JSON artifacts (layout-map, apparatus-attestation,
basis-db snapshot, re-detection report) and assert the Phase-1 invariants, so they pass in CI
without the gitignored source corpora or the 89 MB basis-db.sqlite. They protect the P1.4-P1.7
outputs and the Gate P1 result.
"""
from __future__ import annotations

import json
from pathlib import Path

REC = Path(__file__).parent / "fixtures/gold/mask_engine/originaldr_reconstruction"


def _load(name: str) -> dict:
    return json.loads((REC / name).read_text())


def test_scripture_order_partitions_all_76_books_into_grounded_sections():
    so = _load("layout-map.json")["scripture_order"]
    assert so["book_total"] == 76 and so["section_total"] == 6
    # every ordinal 1..76 assigned exactly once, each tagged tome/part/section
    ordinals = [b["ordinal"] for b in so["canonical_order"]]
    assert ordinals == list(range(1, 77))
    assert all(b.get("tome") and b.get("part") and b.get("section_id") for b in so["canonical_order"])
    section_of = {b["ordinal"]: b["section_id"] for b in so["canonical_order"]}
    # the scan-grounded tome split: Iob (20) closes the First Tome, Psalmes (21) opens the Second
    assert section_of[20] == "ot-tome1-historical"
    assert section_of[21] == "ot-tome2-sapiential"
    # the two internal tome/part boundaries carry a rendered, OCR-located crop
    crops = {s["section_id"]: s.get("boundary_leaf", {}).get("crop_image")
             for s in so["sections"] if "boundary_leaf" in s}
    assert crops.get("ot-tome1-historical", "").endswith("first-tome-end.png")
    assert crops.get("ot-tome2-sapiential", "").endswith("sapiential-divider.png")


def test_apparatus_attestation_matrix_is_complete_with_honest_decisions():
    d = _load("apparatus-attestation.json")
    assert len(d["reference_docs"]) == 26
    assert len(d["book_channels"]) == 76
    inc = [r for r in d["reference_docs"] if r["decision"]["include"]]
    exc = [r for r in d["reference_docs"] if not r["decision"]["include"]]
    assert len(inc) == 25 and len(exc) == 1
    # the single exclusion is the OT epistles-table (over-enumerated NT apparatus, unlocatable in OT)
    assert exc[0]["slot_id"] == "apparatus/ot-back/epistles-table"
    assert exc[0]["placement"]["status"] == "unlocatable"
    # all five contributing sources are declared
    assert {s["id"] for s in d["sources"]} == {
        "sabates_a", "odr_com", "s_dismas", "madueke_b", "archive_org"}
    # Sabates is the backbone: it attests every reference doc
    assert all(r["attestation"]["sabates_a"]["present"] for r in inc)


def test_basis_db_snapshot_is_internally_consistent():
    d = _load("basis-db.json")
    ec = d["element_counts"]
    assert ec["scripture-verse"] == 37185
    assert ec["apparatus-item"] == 102          # 26 reference docs + 76 book arguments
    assert ec["structural-node"] == 82          # 6 sections + 76 books
    rc = d["sqlite"]["row_counts"]
    assert rc["consensus"] == 37185
    assert rc["elements"] == sum(ec.values())
    sc = d["scripture"]
    assert sum(sc["tiers"].values()) == 37185
    # consensus distribution matches the P1.3 summary (regression guard on the assembled basis)
    assert sc["tiers"] == {"high": 30522, "low": 239, "moderate": 6424}
    assert sc["indep_depth"] == {"1": 239, "2": 8680, "3": 15472, "4": 12794}
    assert 0.80 <= sc["mean_agreement"] <= 0.82


def test_redetection_gate_p1_passes_all_checks():
    d = _load("redetection-report.json")
    assert d["gate_p1_pass"] is True
    checks = d["checks"]
    assert set(checks) == {
        "G1_coordinate_roundtrip", "G2_referential_integrity", "G3_attestation_consensus",
        "G4_placement_grounding", "G5_source_validity"}
    assert all(c["pass"] for c in checks.values())
    g1 = checks["G1_coordinate_roundtrip"]
    assert g1["failure_count"] == 0
    assert g1["round_tripped"] == g1["elements"]        # 100% round-trip
    assert all(v == 0 for v in checks["G2_referential_integrity"]["orphans"].values())


def test_p2a_modern_render_is_a_pure_basis_db_projection():
    """P2a (plan §5.2): idx 108 is emitted as a projection of the basis DB — every modern verse
    body sourced from a consensus render_modern surface, no render-time fallbacks — and the projected
    reference text is byte-identical to the committed idx 108 gold map."""
    r = _load("render-modern-report.json")
    assert r["idx"] == 108 and r["artifact"] == "render-modern"
    sp = r["scripture_projection"]
    # the modern edition + the archaic-only coordinates partition the basis-db scripture set
    assert sp["modern_surface_verses"] + sp["archaic_only_coordinates"] == sp["basis_db_verses"] == 37185
    # every modern verse body came from the basis DB — a pure projection, zero render-time fallbacks
    assert sp["verse_bodies_from_basis_db"] == sp["modern_surface_verses"] == 37130
    assert sp["render_time_fallbacks"] == 0 and sp["pure_basis_db_projection"] is True
    # the rendered verses' confidence tiers account for the whole modern edition
    assert sum(sp["rendered_confidence_tiers"].values()) == sp["verse_bodies_from_basis_db"]
    # the projected reference sha ties to the committed idx 108 gold map (identical text)
    assert r["reference"]["matches_pinned_reference_sha"] is True
    work108 = json.loads((REC.parent.parent / "maps" / "work-108.map.json").read_text())
    assert work108["idx"] == 108
    assert work108["reference_sha256"] == r["reference"]["sha256"]
