"""Tests for the FastAPI server."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from palimpsest.annotation.serializer import write_track
from palimpsest.project import ingest_file
from palimpsest.server import create_app
from palimpsest.tracks.entities import EntityExtractor


@pytest.fixture
def workspace_with_project(pp_ch1_txt: Path, tmp_path: Path):
    """Create a workspace with one ingested + analyzed project."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    project = ingest_file(pp_ch1_txt, workspace, title="PP Server Test")
    anns = EntityExtractor().extract(project)
    write_track(project.path / "tracks" / "entities.jsonl", anns)
    return workspace


@pytest.fixture
def client(workspace_with_project):
    app = create_app(workspace_with_project)
    return TestClient(app)


class TestProjectsAPI:
    def test_list_projects(self, client):
        response = client.get("/api/projects")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) >= 1
        assert projects[0]["title"] == "PP Server Test"

    def test_list_projects_has_word_count(self, client):
        projects = client.get("/api/projects").json()
        assert projects[0]["word_count"] > 0

    def test_list_tracks(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/api/projects/{project_id}/tracks")
        assert response.status_code == 200
        tracks = response.json()
        assert isinstance(tracks, list)
        assert "segments" in tracks
        assert "entities" in tracks


class TestSummarizeAPI:
    # Calls Ollama for a real summary when the service is up (cold model load can
    # take ~30s); returns ollama_available=False and stays fast when it is down.
    @pytest.mark.external
    def test_summarize_valid_request(self, client):
        passage = (
            "It is a truth universally acknowledged, that a single man "
            "in possession of a good fortune, must be in want of a wife."
        )
        response = client.post("/api/summarize", json={
            "passage": passage,
            "model": "qwen3:8b",
        })
        assert response.status_code == 200
        data = response.json()
        assert "ollama_available" in data
        assert "model" in data
        assert data["model"] == "qwen3:8b"
        if data["ollama_available"]:
            assert data["summary"] is not None
        else:
            assert data["summary"] is None

    def test_summarize_invalid_model_rejected(self, client):
        response = client.post("/api/summarize", json={
            "passage": "Some valid passage text that is long enough.",
            "model": "../../etc/passwd",
        })
        assert response.status_code == 422

    def test_summarize_passage_too_short(self, client):
        response = client.post("/api/summarize", json={
            "passage": "Short",
            "model": "qwen3:8b",
        })
        assert response.status_code == 422


class TestSearchAPI:
    def test_search_no_embeddings(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/api/search?project={project_id}&query=wife")
        assert response.status_code == 200
        data = response.json()
        assert data["embedding_available"] is False
        assert data["results"] == []

    def test_search_invalid_project(self, client):
        response = client.get("/api/search?project=nonexistent&query=test")
        assert response.status_code == 200
        data = response.json()
        assert data["embedding_available"] is False


class TestStaticServing:
    def test_serve_reference_txt(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/data/{project_id}/reference.txt")
        assert response.status_code == 200
        assert "Mr. Bennet" in response.text

    def test_serve_metadata_json(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/data/{project_id}/metadata.json")
        assert response.status_code == 200
        meta = response.json()
        assert meta["title"] == "PP Server Test"

    def test_serve_entities_jsonl(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/data/{project_id}/tracks/entities.jsonl")
        assert response.status_code == 200
        lines = response.text.strip().split("\n")
        assert len(lines) > 0
        first = json.loads(lines[0])
        assert first["type"] == "Annotation"

    def test_path_traversal_blocked(self, client):
        response = client.get("/data/../../../etc/passwd")
        assert response.status_code in (400, 404)

    def test_nonexistent_file_404(self, client):
        projects = client.get("/api/projects").json()
        project_id = projects[0]["id"]
        response = client.get(f"/data/{project_id}/nonexistent.txt")
        assert response.status_code == 404


class TestSelfSimilarityEndpoints:
    """Coverage for the self-similarity cs/* endpoints (audit E-NEW4) including
    the route-ordering regression and W7 metric-allowlist validation."""

    def _pid(self, client):
        return client.get("/api/projects").json()[0]["id"]

    def test_alignments_route_not_shadowed_by_metric_route(self, client):
        # Regression: the generic /cs/{cs}/{metric} route must be declared AFTER
        # the literal /cs/{cs}/alignments route, else "alignments" is treated as a
        # metric and rejected by W7 validation (400) instead of returning records.
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/alignments")
        assert r.status_code == 200
        assert r.json() == []

    def test_per_metric_alignments_valid_metric(self, client):
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/alignments/cosine")
        assert r.status_code == 200
        assert r.json() == []

    def test_per_metric_alignments_invalid_metric_rejected(self, client):
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/alignments/bogus")
        assert r.status_code == 400

    def test_chunk_data_invalid_metric_rejected(self, client):
        # W7: unknown metric must be rejected, not used to build a file path.
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/bogus")
        assert r.status_code == 400

    def test_chunk_data_valid_metric_missing_file_404(self, client):
        # A valid metric passes W7 validation but 404s when no data exists.
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/cs/17/cosine")
        assert r.status_code == 404

    def test_chunk_sizes_empty_for_fresh_project(self, client):
        pid = self._pid(client)
        r = client.get(f"/api/projects/{pid}/self_similarity/chunk_sizes")
        assert r.status_code == 200
        assert r.json()["chunk_sizes"] == []

    def test_auto_run_without_embeddings(self, client):
        pid = self._pid(client)
        r = client.post(f"/api/projects/{pid}/analyze/self_similarity/auto_run")
        assert r.status_code == 200
        assert r.json()["status"] == "no_embeddings"

    def test_run_analysis_declares_per_metric_chunk_size(self, client):
        # E-NEW1: chunk_size_cosine must be a *declared* int query param. A non-int
        # value triggers FastAPI 422; an undeclared param would be silently ignored.
        pid = self._pid(client)
        r = client.post(f"/api/projects/{pid}/analyze/self_similarity?chunk_size_cosine=notanint")
        assert r.status_code == 422
