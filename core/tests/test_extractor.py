"""Tests for text extraction format dispatch (txt, html, markdown, errors)."""

from __future__ import annotations

import pytest

from palimpsest.ingest.extractor import extract_text


def test_extract_txt(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("Hello world.", encoding="utf-8")
    assert extract_text(p) == "Hello world."


def test_extract_txt_latin1_fallback(tmp_path):
    p = tmp_path / "a.txt"
    # 0xE9 is 'é' in latin-1 but invalid as standalone UTF-8 → triggers fallback.
    p.write_bytes(b"caf\xe9")
    assert extract_text(p) == "café"


def test_extract_html_strips_script_and_style(tmp_path):
    p = tmp_path / "a.html"
    p.write_text(
        "<html><head><style>body{}</style></head>"
        "<body><p>Real text</p><script>evil()</script></body></html>",
        encoding="utf-8",
    )
    out = extract_text(p)
    assert "Real text" in out
    assert "evil()" not in out
    assert "body{}" not in out


def test_extract_htm_extension(tmp_path):
    p = tmp_path / "a.htm"
    p.write_text("<p>Hi</p>", encoding="utf-8")
    assert "Hi" in extract_text(p)


def test_extract_markdown_strips_formatting(tmp_path):
    p = tmp_path / "a.md"
    p.write_text(
        "# Heading\n\n"
        "Some **bold** and *italic* and `code` and a [link](http://x).\n"
        "- bullet item\n"
        "1. numbered item\n",
        encoding="utf-8",
    )
    out = extract_text(p)
    assert "Heading" in out and "#" not in out
    assert "bold" in out and "**" not in out
    assert "italic" in out
    assert "code" in out and "`" not in out
    assert "link" in out and "http://x" not in out
    assert "bullet item" in out
    assert "numbered item" in out


def test_unsupported_format_raises(tmp_path):
    p = tmp_path / "a.xyz"
    p.write_text("data", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file format"):
        extract_text(p)
