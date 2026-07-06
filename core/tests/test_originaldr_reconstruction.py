"""Guards for the committed OriginalDR (idx 108) Phase-1 reconstruction artifacts.

Corpus-free: these read the committed JSON artifacts (layout-map, apparatus-attestation,
basis-db snapshot, re-detection report) and assert the Phase-1 invariants, so they pass in CI
without the gitignored source corpora or the 89 MB basis-db.sqlite. They protect the P1.4-P1.7
outputs and the Gate P1 result.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

REC = Path(__file__).parent / "fixtures/gold/mask_engine/originaldr_reconstruction"


def _load(name: str) -> dict:
    return json.loads((REC / name).read_text())


def _load_module(name: str) -> ModuleType:
    """Load a recon-dir module by path (corpus-free: these modules import only stdlib)."""
    spec = importlib.util.spec_from_file_location(name, REC / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def test_p2_spelling_glyph_model_fold_matches_worked_examples():
    """§6.1 (plan §6.1): the documented archaic↔modern fold reduces every worked example's modern AND
    archaic surface to one identical skeleton, and the stored fold arrays match the live algorithm —
    so the spec cannot silently drift from spelling_glyph_model.fold_diplomatic."""
    sgm = _load_module("spelling_glyph_model")
    model = _load("spelling-glyph-model.json")
    examples = model["worked_examples"]
    assert len(examples) >= 3
    for ex in examples:
        fm, fa = sgm.fold_tokens(ex["modern"]), sgm.fold_tokens(ex["archaic"])
        # modern and archaic fold identically (the whole point) AND match the documented fold
        assert fm == fa == ex["fold"], f"fold drift for {ex['modern']!r}/{ex['archaic']!r}: {fm} vs {fa} vs {ex['fold']}"
    # the reversible glyph pairs are exactly the type-level round-trip correspondences
    assert model["reversible_round_trip"] == [["ſ", "s"], ["æ", "ae"], ["œ", "oe"], ["vv", "w"], ["&", "and"]]
    # the OCR-tolerance symmetric f<->s of ocr_sample.skel is DELIBERATELY excluded so §6.2 SEES the ſ→f defect
    assert "f<->s" in model["fold"]["excludes"] and "SYMMETRIC" in model["fold"]["excludes"].upper()
    # a genuine long-ſ folds to s (type-agnostic), but a fresh-OCR ſ→f misread stays distinct — NOT masked
    assert sgm.fold_diplomatic("Bleſſed") == sgm.fold_diplomatic("Blessed")
    assert sgm.fold_diplomatic("vifion") != sgm.fold_diplomatic("vision")


def test_p2_archaic_fidelity_validation_is_tiered_and_honest():
    """§6.2 (plan §6.2): the post-fold word-correspondence validation is non-vacuous, its buckets
    partition the compared verses, fidelity is tiered by archaic-witness coverage (well-attested
    books fold far tighter than the ocr-only books), and the severe tail is the well-attested
    versification-divergence set — not an OCR artifact."""
    d = _load("archaic-fidelity-validation.json")
    agg = d["aggregate"]
    n = agg["verses_compared"]
    assert n == 36931
    # buckets partition the compared verses exactly (non-vacuity + completeness)
    assert sum(agg["distribution"].values()) == n
    assert 0.75 <= agg["mean_jaccard"] <= 0.77
    # tiered finding: both well-attested tiers fold far tighter than the ocr-only tier
    bt = d["by_witness_tier"]
    clean, mixed, ocr = bt["clean-diplomatic"], bt["mixed"], bt["ocr-only-noisy"]
    assert (clean["n_archaic_witnesses"], mixed["n_archaic_witnesses"], ocr["n_archaic_witnesses"]) == (3, 2, 1)
    assert clean["mean_jaccard"] > 0.80 and mixed["mean_jaccard"] > 0.80
    assert ocr["mean_jaccard"] < 0.55
    assert min(clean["mean_jaccard"], mixed["mean_jaccard"]) - ocr["mean_jaccard"] > 0.25
    # the ocr-only tier is exactly the single-witness books absent from s-dismas (Gen→Wisdom) + odr-com
    assert set(ocr["books"]) == {
        "3-esdras", "4-esdras", "abdias", "aggeus", "amos", "ecclesiasticus", "ezechiel", "habacuc",
        "isaie", "jeremie", "joel", "malachie", "micheas", "nahum", "osee", "prayer-of-manasses", "zacharias"}
    # every book is accounted for, each with a valid mean in [0, 1]
    assert len(d["per_book"]) == 76
    assert all(0.0 <= b["mean_jaccard"] <= 1.0 for b in d["per_book"].values())
    # severe tail is dominated by the WELL-ATTESTED books (versification off-by-one), not OCR noise
    st = d["severe_tail"]
    sev = st["by_witness_tier"]
    assert sev["ocr-only-noisy"] <= 5
    assert sev["clean-diplomatic"] + sev["mixed"] >= 0.95 * st["count"]
    # Psalms tops the tail — the Vulgate convention of numbering the psalm title as verse 1
    assert next(iter(st["by_book_top"])) == "psalms"


def test_p2_archaic_print_validation_bootstrap_cis_are_reproducible_and_honest():
    """§6.3 (plan §6.3): the independent-print bootstrap-CI validation is seeded/reproducible, both
    editions clear a high recall bar against the third-party archive.org print OCR with no genuine
    content-word discrepancies, CIs are well-formed, and recall is reported per genre stratum and per
    archaic-witness tier (with the ocr-only tier flagged partially self-referential)."""
    d = _load("archaic-print-validation.json")
    assert d["idx"] == 109 and d["seed"] == 1729 and d["n_bootstrap"] == 10000
    # reuses the symmetric long-ſ/f PRINT fold (opposite of §6.2's fold_diplomatic, which keeps f≠s)
    assert "skel" in d["fold"] and "symmetric" in d["fold"].lower()
    assert "self-referential" in d["independence_note"].lower()
    # six pinned djvu print witnesses, each with a sha256
    assert len(d["sources"]) == 6
    assert all(len(v["sha256"]) == 64 for v in d["sources"].values())

    def _ci_ok(block: dict) -> bool:
        lo, hi = block["ci95"]
        return 0.0 <= lo <= block["recall_pct"] <= hi <= 100.0

    agg = d["aggregate"]
    # both editions strongly corroborated by the independent print; CIs well-formed
    assert _ci_ok(agg["archaic"]) and _ci_ok(agg["modern"])
    assert 80.0 <= agg["archaic"]["recall_pct"] <= 92.0
    assert 85.0 <= agg["modern"]["recall_pct"] <= 95.0
    # the genuine-discrepancy signal: zero distinctive content words absent from the independent print
    assert agg["archaic_genuine_candidate_misses"] == 0
    assert agg["archaic_genuine_candidate_words"] == []
    # reported across all five genre strata and all three archaic-witness tiers, each with paired CIs
    assert set(d["per_stratum"]) == {"OT-narrative", "OT-poetry", "OT-prophets", "NT-gospel", "NT-epistle"}
    assert list(d["per_witness_tier"]) == ["clean-diplomatic", "mixed", "ocr-only-noisy"]
    for tier in d["per_witness_tier"].values():
        assert tier["archaic"]["n_chapters"] >= 1
        assert _ci_ok(tier["archaic"]) and _ci_ok(tier["modern"])
    # every sample carries a paired archaic + modern measurement
    assert d["per_sample"] and all("archaic" in s and "modern" in s for s in d["per_sample"])


def test_p3_academic_brief_regenerates_and_traces_to_artifacts():
    """P3.1 (plan §7): the academic brief regenerates deterministically from the committed artifacts
    (no basis-db needed), carries the full section structure + genome-browser figures with balanced
    SVG, every headline number traces to its source JSON, and the committed HTML is in sync."""
    gen = _load_module("gen_originaldr_brief")
    A, paths = gen.load_artifacts()
    out = gen.build_html(A, paths)
    # full academic structure + balanced, data-driven figures
    for anchor in ("abstract", "intro", "sources", "methods", "results",
                   "discussion", "limitations", "repro", "refs"):
        assert f'id="{anchor}"' in out
    assert out.count("<svg") == out.count("</svg>") >= 4
    assert out.count("<rect") > 200 and out.count("<title>") > 100  # data-driven bars + tooltips
    # traceability: headline numbers equal their source-artifact values
    assert f'{A["basis"]["element_counts"]["scripture-verse"]:,}' in out
    assert f'{A["fidelity"]["aggregate"]["mean_jaccard"]:.3f}' in out
    assert str(A["print_archaic"]["aggregate"]["archaic"]["recall_pct"]) in out
    assert str(A["print_archaic"]["aggregate"]["modern"]["recall_pct"]) in out
    assert ("PASS" if A["redetection"]["gate_p1_pass"] else "FAIL") in out
    # audit trail lists the backing artifacts (sample a few)
    for key in ("basis", "fidelity", "print_archaic"):
        assert str(paths[key].relative_to(gen.REPO)) in out
    # the committed brief is not stale w.r.t. the generator + artifacts
    assert gen.OUT.read_text(encoding="utf-8") == out


def test_p3_2_brief_data_is_consistent_and_powers_genome_browser_figures():
    """P3.2 (plan §7.2): the committed brief-data.json — the sampled projection of the gitignored
    basis DB that feeds the source-track browser, coverage histograms and variant pileups — is
    internally consistent, reconciles with the basis-db snapshot, and renders those three figures in
    the brief. Keeps the genome-browser figures CI-safe (no basis-db.sqlite at test time)."""
    bd = _load("brief-data.json")
    basis = _load("basis-db.json")
    n = basis["element_counts"]["scripture-verse"]
    assert bd["n_scripture_verses"] == n

    # coverage histograms reconcile with the basis-db snapshot and partition all verses
    dh = bd["depth_histograms"]
    assert {int(k): v for k, v in dh["indep_depth"].items()} == \
        {int(k): v for k, v in basis["scripture"]["indep_depth"].items()}
    assert sum(dh["support_depth"].values()) == sum(dh["indep_depth"].values()) == n
    # read depth reaches five sources; independent depth caps at four lineages (non-independence correction)
    assert max(int(k) for k in dh["support_depth"]) == 5
    assert max(int(k) for k in dh["indep_depth"]) == 4

    # book×source matrix: 76 books, five scripture witnesses, per-source counts bounded by the book total
    m = bd["book_source_matrix"]
    assert len(m["books"]) == 76
    assert m["sources"] == ["madueke_a", "sabates_a", "ocr_consensus", "s_dismas", "odr_com"]
    assert sum(b["total"] for b in m["books"].values()) == n
    assert all(0 <= c <= b["total"] for b in m["books"].values() for c in b["by_source"].values())

    # source tracks: the ocr-only contrast — genesis carries all five witnesses, isaie only its three
    tracks = {t["book"]: t for t in bd["source_tracks"]}
    assert set(tracks) == {"genesis", "isaie"}
    assert max(sum(v["present"].values()) for v in tracks["genesis"]["verses"]) == 5
    isaie_present = {s for v in tracks["isaie"]["verses"] for s, p in v["present"].items() if p}
    assert isaie_present == {"madueke_a", "sabates_a", "ocr_consensus"}

    # variant pileups: each is a genuine disagreement (agreement < 1) with a called consensus + witness reads
    assert len(bd["variant_pileups"]) >= 5
    for p in bd["variant_pileups"]:
        assert 0.0 <= p["agreement"] < 1.0 and p["called_modern"]
        assert p["reads"] and all(r["surface"] and r["edition"] in ("modern", "archaic") for r in p["reads"])
    # at least one pileup shows the versification-offset signature: a near-zero-Jaccard witness
    # (reading the neighbouring verse) beside high-Jaccard witnesses at the same coordinate
    assert any(
        any(r["jaccard"] is not None and r["jaccard"] < 0.1 for r in p["reads"])
        and any(r["jaccard"] is not None and r["jaccard"] >= 0.6 for r in p["reads"])
        for p in bd["variant_pileups"])

    # the brief renders the three P3.2 figures from this artifact and lists it in the audit trail
    gen = _load_module("gen_originaldr_brief")
    A, paths = gen.load_artifacts()
    out = gen.build_html(A, paths)
    for label in ("Source-track browser", "Coverage depth", "Variant pileups"):
        assert label in out
    assert str(paths["brief_data"].relative_to(gen.REPO)) in out
    assert out.count("<svg") == out.count("</svg>") >= 7
