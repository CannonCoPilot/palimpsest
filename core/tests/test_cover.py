"""Tests for EPUB cover extraction, persistence, and serving.

No EPUB fixture is committed; minimal EPUBs are built in-memory with ebooklib so
the test is self-contained and exercises the full chain: parse -> ingest ->
/api/projects URL -> /data serving.
"""

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from palimpsest.ingest.epub_parser import cover_extension, parse_epub
from palimpsest.project import ingest_file
from palimpsest.server import create_app

# A valid 1x1 PNG.
_PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4"
    "2mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

_BODY = "<html><body><h1>Chapter 1</h1><p>" + ("Lorem ipsum dolor sit amet. " * 60) + "</p></body></html>"


def _build_epub(path: Path, *, with_cover: bool) -> Path:
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("cover-test" if with_cover else "nocover-test")
    book.set_title("Cover Test Book" if with_cover else "No Cover Book")
    book.set_language("en")
    book.add_author("Test Author")
    if with_cover:
        book.set_cover("cover.png", _PNG_1x1)
    chapter = epub.EpubHtml(title="Chapter 1", file_name="chap_01.xhtml", lang="en")
    chapter.content = _BODY
    book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.toc = (chapter,)
    book.spine = ["nav", chapter]
    epub.write_epub(str(path), book)
    return path


def _build_epub_titlepage_image(path: Path) -> Path:
    """An EPUB with NO declared cover, but a titlepage that embeds an image via
    an SVG <image> (the 1599 Geneva Bible shape). The image name has no "cover"
    substring, so only the front-matter fallback — not the name heuristic — finds it.
    """
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("titlepage-image-test")
    book.set_title("Titlepage Image Book")
    book.set_language("en")
    book.add_author("Test Author")

    img = epub.EpubItem(uid="img0", file_name="images/00004.png",
                        media_type="image/png", content=_PNG_1x1)
    book.add_item(img)
    titlepage = epub.EpubHtml(title="Title", file_name="titlepage.xhtml", lang="en")
    titlepage.content = (
        '<html xmlns="http://www.w3.org/1999/xhtml"><body><div>'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1 1">'
        '<image xlink:href="images/00004.png"/></svg></div></body></html>'
    )
    book.add_item(titlepage)
    chapter = epub.EpubHtml(title="Chapter 1", file_name="chap_01.xhtml", lang="en")
    chapter.content = _BODY
    book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.toc = (chapter,)
    book.spine = [titlepage, chapter]
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def epub_with_cover(tmp_path: Path) -> Path:
    return _build_epub(tmp_path / "with-cover.epub", with_cover=True)


@pytest.fixture
def epub_without_cover(tmp_path: Path) -> Path:
    return _build_epub(tmp_path / "no-cover.epub", with_cover=False)


@pytest.fixture
def epub_titlepage_image(tmp_path: Path) -> Path:
    return _build_epub_titlepage_image(tmp_path / "titlepage-image.epub")


def test_cover_extension_mapping():
    assert cover_extension("image/jpeg") == ".jpg"
    assert cover_extension("image/png") == ".png"
    assert cover_extension("image/webp") == ".webp"
    assert cover_extension("", "art.PNG") == ".png"
    assert cover_extension("", "frontcover.jpeg") == ".jpg"
    assert cover_extension("", "mystery") == ".jpg"


def test_parse_epub_extracts_cover(epub_with_cover):
    result = parse_epub(epub_with_cover)
    assert result.cover_image is not None
    assert len(result.cover_image) > 0


def test_parse_epub_without_cover_is_none(epub_without_cover):
    result = parse_epub(epub_without_cover)
    assert result.cover_image is None
    assert result.cover_media_type == ""


def test_parse_epub_extracts_titlepage_image(epub_titlepage_image):
    # No declared cover: the fallback pulls the image out of the titlepage.
    result = parse_epub(epub_titlepage_image)
    assert result.cover_image == _PNG_1x1
    assert result.cover_media_type == "image/png"


def test_ingest_persists_titlepage_cover(epub_titlepage_image, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    project = ingest_file(epub_titlepage_image, workspace)
    meta = json.loads((project.path / "metadata.json").read_text())
    assert meta.get("cover") == "cover.png"
    assert (project.path / "cover.png").is_file()


def test_ingest_persists_cover_file_and_metadata(epub_with_cover, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    project = ingest_file(epub_with_cover, workspace)
    meta = json.loads((project.path / "metadata.json").read_text())
    assert meta.get("cover")
    assert (project.path / meta["cover"]).is_file()


def test_ingest_without_cover_omits_field(epub_without_cover, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    project = ingest_file(epub_without_cover, workspace)
    meta = json.loads((project.path / "metadata.json").read_text())
    assert "cover" not in meta
    assert not list(project.path.glob("cover.*"))


def test_api_exposes_and_serves_cover(epub_with_cover, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    project = ingest_file(epub_with_cover, workspace)
    client = TestClient(create_app(workspace))

    entry = next(p for p in client.get("/api/projects").json() if p["id"] == project.metadata.id)
    assert entry["cover"], "cover URL should be present"
    assert entry["cover"].startswith(f"/data/{project.metadata.id}/")

    served = client.get(entry["cover"])
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/")


def test_api_cover_is_none_without_cover(epub_without_cover, tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    project = ingest_file(epub_without_cover, workspace)
    client = TestClient(create_app(workspace))
    entry = next(p for p in client.get("/api/projects").json() if p["id"] == project.metadata.id)
    assert entry["cover"] is None
