"""Tests for P4 positional/lexical endpoints — KWIC, collocations, duplicates, dispersion (FR-10).

Uses a crafted text with a known exact repeat and a known search term so occurrence counts, repeat
detection, and original-coordinate remapping are all assertable.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from palimpsest.project import ingest_file
from palimpsest.server import create_app

_REPEAT = "The wandering scholar paused at the silent gate."
_TEXT = (
    _REPEAT + "\n\n"
    "A quite different paragraph follows here with other words entirely.\n\n"
    + _REPEAT + "\n\n"
    "Yet another distinct passage, mentioning the scholar once more in passing.\n\n"
    + _REPEAT + "\n"
)


@pytest.fixture
def client_and_project(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    src = tmp_path / "crafted.txt"
    src.write_text(_TEXT, encoding="utf-8")
    project = ingest_file(src, workspace, title="lexical-test")
    return TestClient(create_app(workspace)), project


def _pid(project) -> str:
    return project.metadata.id


class TestKWIC:
    def test_finds_term_with_context(self, client_and_project):
        client, project = client_and_project
        r = client.get(f"/api/projects/{_pid(project)}/kwic", params={"term": "scholar", "window": 15})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 4  # 3 in the repeats + 1 in the distinct passage
        for row in body["rows"]:
            assert row["keyword"].lower() == "scholar"
            assert "start" in row and "end" in row

    def test_original_coords_anchor_to_term(self, client_and_project):
        client, project = client_and_project
        r = client.get(f"/api/projects/{_pid(project)}/kwic", params={"term": "scholar"})
        original = project.reference_text()
        for row in r.json()["rows"]:
            assert original[row["start"]:row["end"]].lower() == "scholar"

    def test_missing_term_422(self, client_and_project):
        client, project = client_and_project
        # term is required (min_length=1) → FastAPI validation 422
        assert client.get(f"/api/projects/{_pid(project)}/kwic").status_code == 422


class TestCollocations:
    def test_returns_scored_bigrams(self, client_and_project):
        client, project = client_and_project
        r = client.get(
            f"/api/projects/{_pid(project)}/collocations", params={"window": 2, "min_count": 2}
        )
        assert r.status_code == 200
        cols = r.json()["collocations"]
        assert all(len(row) == 5 for row in cols)
        assert all(row[4] >= 2 for row in cols)


class TestDuplicates:
    def test_detects_exact_repeat(self, client_and_project):
        client, project = client_and_project
        r = client.get(
            f"/api/projects/{_pid(project)}/duplicates",
            params={"min_words": 5, "min_occurrences": 2},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["phrase_count"] > 0
        assert len(body["spans"]) > 0
        # repeated spans must land on the repeated sentence in the original text
        original = project.reference_text()
        assert any("scholar" in original[s:e].lower() for s, e in body["spans"])


class TestDispersion:
    def test_counts_and_original_spans(self, client_and_project):
        client, project = client_and_project
        r = client.get(f"/api/projects/{_pid(project)}/dispersion", params={"term": "scholar"})
        assert r.status_code == 200
        body = r.json()
        assert body["count"] >= 4
        assert body["doc_length"] == len(project.reference_text())
        original = project.reference_text()
        for s, e in body["spans"]:
            assert original[s:e].lower() == "scholar"

    def test_absent_term_is_empty_not_error(self, client_and_project):
        client, project = client_and_project
        r = client.get(
            f"/api/projects/{_pid(project)}/dispersion", params={"term": "zzzunfindable"}
        )
        assert r.status_code == 200
        assert r.json()["count"] == 0 and r.json()["spans"] == []
