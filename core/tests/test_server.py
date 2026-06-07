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
