"""Tests for the layout-section pipeline endpoints (detect / get / put / staged import)."""

from pathlib import Path

from fastapi.testclient import TestClient

from palimpsest.project import ingest_file
from palimpsest.server import create_app


def _setup(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    src = tmp_path / "book.txt"
    src.write_text(
        "Chapter 1\n\n" + ("The hero walked the long road. " * 40)
        + "\n\nChapter 2\n\n" + ("Then came the cold night. " * 40),
        encoding="utf-8",
    )
    project = ingest_file(src, workspace, title="Section Test")
    return create_app(workspace), project.metadata.id


def test_get_sections_empty_default_exposes_type_vocabulary(tmp_path):
    app, pid = _setup(tmp_path)
    c = TestClient(app)
    data = c.get(f"/api/projects/{pid}/sections").json()
    assert data["sections"] == []
    assert data["applied"] is False
    assert len(data["types"]) == 12
    chapter = next(t for t in data["types"] if t["key"] == "chapter")
    assert chapter["default_mask"] is False
    endnotes = next(t for t in data["types"] if t["key"] == "endnotes")
    assert endnotes["default_mask"] is True


def test_detect_then_get_roundtrips(tmp_path):
    app, pid = _setup(tmp_path)
    c = TestClient(app)
    det = c.post(f"/api/projects/{pid}/sections/detect").json()
    assert "chapter" in {s["type"] for s in det["sections"]}
    again = c.get(f"/api/projects/{pid}/sections").json()
    assert len(again["sections"]) == len(det["sections"])


def test_put_sections_persists_and_computes_masks(tmp_path):
    app, pid = _setup(tmp_path)
    c = TestClient(app)
    payload = {
        "sections": [
            {"id": "s1", "type": "front_matter", "start": 0, "end": 50},
            {"id": "s2", "type": "chapter", "start": 50, "end": 400},
        ],
        "mask_by_type": {"front_matter": True, "chapter": False},
    }
    data = c.put(f"/api/projects/{pid}/sections", json=payload).json()
    assert data["masked_intervals"] == [[0, 50]]
    assert data["applied"] is False


def test_put_invalid_project_404(tmp_path):
    app, _ = _setup(tmp_path)
    c = TestClient(app)
    assert c.put("/api/projects/nope/sections", json={"sections": []}).status_code == 404


def test_staged_local_import_defers_analysis(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    imports = tmp_path / "imports"
    imports.mkdir()
    (imports / "b.txt").write_text(
        "Chapter 1\n\n" + ("words on the page here. " * 50), encoding="utf-8",
    )
    c = TestClient(create_app(workspace, imports_dir=imports))
    data = c.post("/api/import/local", json={"path": "b.txt", "process": False}).json()
    assert data["staged"] is True
    project_dir = workspace / data["project_id"]
    assert (project_dir / "reference.txt").exists()
    # No analysis tracks (entities/sentiment/...) — only structural segments from ingest.
    track_names = {p.stem for p in (project_dir / "tracks").glob("*.jsonl")}
    assert "entities" not in track_names
