"""Guards for the committed OriginalDR (idx 108) v3 validation audit trail.

These tests protect the durable, git-tracked artifacts that back the reconstruction report's
headline statistics, and prove the OCR discrepancy filter is non-vacuous. They are corpus-free:
they read the committed JSON artifacts and exercise a pure helper, so they pass in CI without the
gitignored source binaries.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

VAL = Path(__file__).parent / "fixtures/gold/mask_engine/originaldr_validation"


def _load(name: str) -> dict:
    return json.loads((VAL / name).read_text())


def test_collation_artifact_present_and_clean():
    d = _load("collation-3way.json")
    agg = d["leg1_exact_madueke_sabates"]["aggregate"]
    assert agg["compared"] > 30000
    assert agg["substantive"] == 0                    # 0 substantive wording diffs A<->Sabates
    assert len(d["leg1_exact_madueke_sabates"]["per_book"]) == 73
    leg2 = d["leg2_format_fidelity_madueke_a_vs_b"]
    assert leg2["type_recall_pct"] >= 99.0            # HTML extraction faithful to the PDF edition
    for src in ("madueke_a", "sabates_a", "madueke_b"):
        assert d["sources"][src].get("digest_sha256") or d["sources"][src].get("sha256")


def test_ocr_validation_artifact_has_ci_and_no_genuine_discrepancy():
    d = _load("ocr-validation.json")
    agg = d["aggregate"]
    assert d["seed"] == 1729                          # reproducible sample
    assert agg["recall_pct"] > 80                     # independent print corroborates the wording
    lo, hi = agg["ci95"]
    assert lo <= agg["recall_pct"] <= hi              # point estimate inside its bootstrap CI
    assert agg["genuine_candidate_misses"] == 0       # 0 genuine discrepancies after 2nd-pass triage
    assert len(d["per_sample"]) >= 30
    assert set(d["per_stratum"]) >= {"OT-narrative", "NT-gospel", "apparatus-dense"}


def test_apparatus_coverage_is_near_complete():
    d = _load("apparatus-gapfill.json")
    cov = d["sabates_coverage"]
    assert cov["chapters_with_apparatus_pct"] >= 99.0
    assert d["appendix_now_two_witness"] is True      # Madueke_B corroborates the 3-book appendix


def test_apparatus_order_covers_every_section_with_evidence():
    d = _load("apparatus-order.json")
    for region in ("ot_front", "ot_back", "nt_front", "nt_back"):
        assert d[region], f"{region} empty"
        for e in d[region]:
            assert e["evidence"]["method"] in {"section-field", "ocr-offset",
                                               "manual-visual", "structural"}


def _import_ocr_sample():
    spec = importlib.util.spec_from_file_location("ocr_sample", VAL / "ocr_sample.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_genuine_candidate_filter_is_non_vacuous():
    """A discrepancy filter that can never fire proves nothing. Show it demotes a word present in
    the print but flags one that is genuinely absent."""
    O = _import_ocr_sample()
    witness = {"iesus", "christ", "heauen", "earth"}
    _, present_genuine = O.genuine_candidates(["heaven"], witness, set(witness), list(witness))
    _, absent_genuine = O.genuine_candidates(["zqxwveltfarn"], witness, set(witness), list(witness))
    assert present_genuine == []                      # "heaven" ~ "heauen" -> attested, demoted
    assert absent_genuine == ["zqxwveltfarn"]         # truly absent -> flagged (filter CAN fire)
