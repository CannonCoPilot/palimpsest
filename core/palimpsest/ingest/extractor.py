"""Text extraction from PDF, EPUB, HTML, Markdown, and plain text files."""

from __future__ import annotations

import re
from pathlib import Path

# Distribution watermarks injected by pirate re-hosts (e.g. OceanofPDF) that are not
# part of the work. Stripped from every extracted text so they never enter a mask.
_WATERMARK_RE = re.compile(
    r"[ \t]*(?:https?://)?(?:www\.)?OceanofPDF\.com[ \t]*\n?",
    re.IGNORECASE,
)


def _strip_watermarks(text: str) -> str:
    """Remove known distribution watermarks, collapsing the gap they leave."""
    text = _WATERMARK_RE.sub("", text)
    # avoid leaving 3+ blank lines where a standalone watermark line was removed
    return re.sub(r"\n{3,}", "\n\n", text)


def extract_text(path: Path) -> str:
    """Extract raw text from a file based on its extension."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        raw = _extract_txt(path)
    elif suffix == ".pdf":
        raw = _extract_pdf(path)
    elif suffix == ".epub":
        raw = _extract_epub(path)
    elif suffix in (".html", ".htm"):
        raw = _extract_html(path)
    elif suffix in (".md", ".markdown"):
        raw = _extract_markdown(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")
    return _strip_watermarks(raw)


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


