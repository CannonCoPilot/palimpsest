"""Text extraction from PDF, EPUB, HTML, Markdown, and plain text files."""

from __future__ import annotations

from pathlib import Path


def extract_text(path: Path) -> str:
    """Extract raw text from a file based on its extension."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _extract_txt(path)
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".epub":
        return _extract_epub(path)
    if suffix in (".html", ".htm"):
        return _extract_html(path)
    if suffix in (".md", ".markdown"):
        return _extract_markdown(path)
    raise ValueError(f"Unsupported file format: {suffix}")


def _extract_txt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def _extract_pdf(path: Path) -> str:
    import pymupdf

    doc = pymupdf.open(str(path))
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages)


def _extract_html(path: Path) -> str:
    from bs4 import BeautifulSoup

    raw = _extract_txt(path)
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n\n")


def _extract_markdown(path: Path) -> str:
    import re

    text = _extract_txt(path)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    return text


def _extract_epub(path: Path) -> str:
    from palimpsest.ingest.epub_parser import parse_epub

    result = parse_epub(path)
    return result.text


