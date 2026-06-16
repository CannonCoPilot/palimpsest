"""Tests for the layout-section pipeline endpoints (detect / get / put / staged import)."""

from pathlib import Path

from fastapi.testclient import TestClient

from palimpsest.layout import SECTION_TYPES
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
    assert len(data["types"]) == len(SECTION_TYPES)
    chapter = next(t for t in data["types"] if t["key"] == "chapter")
    assert chapter["default_mask"] is False
    body = next(t for t in data["types"] if t["key"] == "body")
    assert body["default_mask"] is False  # the foundation body is analyzable
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


def test_apply_persists_masking_without_running_analysis(tmp_path):
    app, pid = _setup(tmp_path)
    c = TestClient(app)
    c.post(f"/api/projects/{pid}/sections/detect")
    res = c.post(f"/api/projects/{pid}/sections/apply").json()
    assert res["applied"] is True
    # Apply must persist the decision but NOT trigger analysis extractors.
    assert c.get(f"/api/projects/{pid}/sections").json()["applied"] is True
    names = {p.stem for p in (tmp_path / "ws" / pid / "tracks").glob("*.jsonl")}
    assert "entities" not in names and "sentiment" not in names


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


def test_custom_mask_type_persists_and_masks(tmp_path):
    app, pid = _setup(tmp_path)
    c = TestClient(app)
    tl = c.post(f"/api/projects/{pid}/sections/detect").json()["text_len"]
    extra = [{"key": "editorial_note", "label": "Editorial Note", "color": "#ff0000", "default_mask": True}]
    payload = {
        "sections": [
            {"id": "ls-1", "type": "body", "start": 0, "end": tl},
            {"id": "ls-2", "type": "editorial_note", "start": 10, "end": 40},
        ],
        "extra_types": extra,
        "mask_by_type": {},
    }
    data = c.put(f"/api/projects/{pid}/sections", json=payload).json()
    keys = {t["key"]: t for t in data["types"]}
    assert "editorial_note" in keys and keys["editorial_note"]["builtin"] is False
    assert keys["body"]["builtin"] is True
    # The custom layer (default_mask=True) carves a masked window through the body.
    assert [10, 40] in data["masked_intervals"]
    # Custom type survives a reload.
    assert c.get(f"/api/projects/{pid}/sections").json()["extra_types"][0]["key"] == "editorial_note"


def test_custom_type_collision_with_builtin_is_dropped(tmp_path):
    app, pid = _setup(tmp_path)
    c = TestClient(app)
    c.post(f"/api/projects/{pid}/sections/detect")
    data = c.put(f"/api/projects/{pid}/sections", json={
        "sections": [],
        "extra_types": [{"key": "chapter", "label": "X", "color": "#000", "default_mask": False}],
    }).json()
    assert data["extra_types"] == []  # a key colliding with a builtin type is rejected


def test_apply_writes_elements_track(tmp_path):
    import json as _json

    app, pid = _setup(tmp_path)
    c = TestClient(app)
    det = c.post(f"/api/projects/{pid}/sections/detect").json()
    c.put(f"/api/projects/{pid}/sections", json={"sections": det["sections"]})
    c.post(f"/api/projects/{pid}/sections/apply")
    proj_dir = tmp_path / "ws" / pid
    manifest = proj_dir / "manifests" / "elements.manifest.json"
    assert manifest.exists()
    assert _json.loads(manifest.read_text())["bodyType"] == "palimpsest:ElementAnnotation"
    track = proj_dir / "tracks" / "elements.jsonl"
    if track.exists():  # present whenever any non-body element was detected
        rec = _json.loads([ln for ln in track.read_text().splitlines() if ln.strip()][0])
        assert rec["body"]["type"] == "palimpsest:ElementAnnotation"
        assert "palimpsest:elementType" in rec["body"]
        assert "palimpsest:elementName" in rec["body"]
        assert rec["target"]["selector"]["type"] == "TextPositionSelector"
