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


def test_list_projects_includes_source_file(tmp_path):
    client = TestClient(_make_app(tmp_path))
    client.post(
        "/api/import/local",
        json={"path": "Jane Austen/Emma/emma.txt", "process": False},
    )
    proj = client.get("/api/projects").json()[0]
    assert proj["source_file"] == "emma.txt"


def test_delete_project_removes_it(tmp_path):
    client = TestClient(_make_app(tmp_path))
    res = client.post(
        "/api/import/local",
        json={"path": "Jane Austen/Emma/emma.txt", "process": False},
    )
    assert res.status_code == 200
    pid = res.json()["project_id"]
    assert any(p["id"] == pid for p in client.get("/api/projects").json())

    deleted = client.delete(f"/api/projects/{pid}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "ok"
    assert all(p["id"] != pid for p in client.get("/api/projects").json())
    # already gone → 404 on a second delete
    assert client.delete(f"/api/projects/{pid}").status_code == 404


def test_reimport_requires_overwrite(tmp_path):
    client = TestClient(_make_app(tmp_path))
    body = {"path": "Jane Austen/Emma/emma.txt", "process": False}
    assert client.post("/api/import/local", json=body).status_code == 200
    # same source again without overwrite collides
    assert client.post("/api/import/local", json=body).status_code == 409
    # overwrite replaces in place — still exactly one project
    ov = client.post("/api/import/local", json={**body, "overwrite": True})
    assert ov.status_code == 200
    assert len(client.get("/api/projects").json()) == 1


def test_import_status_flags_imported_and_versions(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    imports = tmp_path / "imports"
    imports.mkdir()
    f_main = "Ante-Nicene Fathers Volume 1 - Enhanced -- Philip Schaff -- 2009 -- CCEL -- aaa -- Anna's Archive.txt"
    f_edition = "Ante-Nicene Fathers, Vol. I -- Roberts, Donaldson -- 2023 -- Global Grey -- bbb -- Anna's Archive.txt"
    f_other = "Some Unrelated Book -- Nobody -- 2000 -- Pub -- ccc -- Anna's Archive.txt"
    for fn in (f_main, f_edition, f_other):
        (imports / fn).write_text("Chapter 1\n\n" + ("words here. " * 50), encoding="utf-8")
    client = TestClient(create_app(workspace, imports_dir=imports))
    # Import the main edition; its title drives the cross-edition signature match.
    client.post("/api/import/local", json={
        "path": f_main, "title": "Ante-Nicene Fathers Volume 1", "process": False,
    })
    files = {f["name"]: f for f in client.get("/api/imports").json()["files"]}
    assert files[f_main]["status"] == "imported"
    # "Vol. I" is recognized as another version of "Volume 1".
    assert files[f_edition]["status"] == "version"
    assert files[f_edition]["matched_project_id"] == files[f_main]["matched_project_id"]
    assert files[f_other]["status"] == "new"
    # parsed metadata is surfaced for the UI's search/filter + grouping.
    assert files[f_edition]["author"] == "Roberts, Donaldson"
