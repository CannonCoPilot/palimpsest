"""Tests for the substrate integrity report (Wave-0 P4, FR-9).

The load-bearing test injects a real coordinate violation and asserts the report catches it — proving
the report runs the actual validators (no drift), not a re-implementation.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from palimpsest.analysis.integrity import run_integrity_report
from palimpsest.project import ingest_file
from palimpsest.server import create_app

_INVARIANTS = {
    "masked-partition", "span-region-bounds", "segment-contract",
    "section-tree", "offsetmap-roundtrip", "analyzable-bridge", "encoding-sanity",
}


@pytest.fixture
def project(pp_ch1_txt: Path, tmp_path: Path):
    return ingest_file(pp_ch1_txt, tmp_path, title="integrity-test")


def _by_name(report: dict, name: str) -> dict:
    return next(i for i in report["invariants"] if i["name"] == name)


class TestCleanProject:
    def test_all_invariants_present(self, project):
        report = run_integrity_report(project)
        assert {i["name"] for i in report["invariants"]} == _INVARIANTS

    def test_clean_project_is_green(self, project):
        report = run_integrity_report(project)
        assert report["all_green"] is True
        assert all(i["status"] in ("pass", "na") for i in report["invariants"])

    def test_summary_fields(self, project):
        s = run_integrity_report(project)["summary"]
        assert s["text_length"] > 0
        assert s["paragraph_count"] > 0
        assert 0.0 <= s["masked_ratio"] <= 1.0


class TestInjectedViolation:
    def test_overlapping_mask_is_caught(self, project):
        # Inject an out-of-order/overlapping masked set: _complement_spans must raise, and the report
        # must surface it as a violation rather than passing — this is what guarantees no drift.
        project.masked_intervals = lambda *a, **k: [(50, 10)]
        report = run_integrity_report(project)
        assert report["all_green"] is False
        assert _by_name(report, "masked-partition")["status"] == "violation"

    def test_replacement_char_flagged(self, project):
        original = project.reference_text()
        project.reference_text = lambda *a, **k: original + "��"
        report = run_integrity_report(project)
        enc = _by_name(report, "encoding-sanity")
        assert enc["status"] == "violation"
        assert "U+FFFD" in enc["detail"]


class TestEndpoint:
    def test_integrity_endpoint(self, pp_ch1_txt, tmp_path):
        workspace = tmp_path / "ws"
        workspace.mkdir()
        project = ingest_file(pp_ch1_txt, workspace, title="integrity-ep")
        client = TestClient(create_app(workspace))
        r = client.get(f"/api/projects/{project.metadata.id}/integrity")
        assert r.status_code == 200
        body = r.json()
        assert body["all_green"] is True
        assert {i["name"] for i in body["invariants"]} == _INVARIANTS
