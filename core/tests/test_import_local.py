"""Tests for the imports/ drop-folder endpoints: GET /api/imports + POST /api/import/local.

Only the new surface — directory listing and path-traversal safety — is exercised
here; the heavy ingest+track compute path is covered via ingest_file in test_cover.py.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from palimpsest.server import create_app


def _make_app(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    imports = tmp_path / "imports"
    (imports / "Jane Austen" / "Emma").mkdir(parents=True)
    (imports / "Jane Austen" / "Emma" / "emma.txt").write_text("Emma. " * 80, encoding="utf-8")
    (imports / "notes.md").write_text("# notes", encoding="utf-8")
    (imports / "ignore.bin").write_text("nope", encoding="utf-8")
    return create_app(workspace, imports_dir=imports)


def test_list_imports_lists_supported_files(tmp_path):
    client = TestClient(_make_app(tmp_path))
    data = client.get("/api/imports").json()
    assert data["available"] is True
    paths = {f["path"] for f in data["files"]}
    assert "Jane Austen/Emma/emma.txt" in paths
    assert "notes.md" in paths
    assert "ignore.bin" not in paths  # unsupported suffix is filtered
    emma = next(f for f in data["files"] if f["name"] == "emma.txt")
    assert emma["folder"] == "Jane Austen/Emma"
    assert emma["format"] == "txt"


def test_list_imports_unavailable_when_dir_missing(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    client = TestClient(create_app(workspace, imports_dir=tmp_path / "nope"))
    data = client.get("/api/imports").json()
    assert data["available"] is False
    assert data["files"] == []


def test_import_local_rejects_traversal(tmp_path):
    client = TestClient(_make_app(tmp_path))
    res = client.post("/api/import/local", json={"path": "../secret.txt"})
    assert res.status_code == 400


def test_import_local_missing_file_404(tmp_path):
    client = TestClient(_make_app(tmp_path))
    res = client.post("/api/import/local", json={"path": "Nope/missing.txt"})
    assert res.status_code == 404
