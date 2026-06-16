"""Tests for EPUB text assembly — drop-cap handling and inline concatenation (B3).

No EPUB fixture is committed; a minimal EPUB is built in-memory with ebooklib so
the end-to-end assertion exercises the real spine-walk in ``_assemble_text``.
"""

from pathlib import Path

from palimpsest.ingest.epub_parser import (
    _clean_assembled_text,
    _needs_separating_space,
    _read_epub,
    _sections_from_text_headings,
    parse_epub,
)


def test_needs_space_joins_separate_inline_fragments():
    # Two real words split across a flattened inline element get a separating space.
    assert _needs_separating_space("end of", "sentence") is True
    assert _needs_separating_space("word", "next") is True


def test_needs_space_suppresses_dropcap_initial():
    # A lone uppercase initial glued to a lowercase continuation is one word.
    assert _needs_separating_space("T", "he morning was clear") is False
    assert _needs_separating_space("I", "t was a truth") is False
    assert _needs_separating_space("W", "hen in doubt") is False


def test_needs_space_respects_existing_whitespace():
    assert _needs_separating_space("done. ", "Next") is False   # prev ends in space
    assert _needs_separating_space("word", " spaced") is False  # nxt starts with space


def test_needs_space_ignores_non_alpha_and_empty():
    assert _needs_separating_space("word", "123") is False
    assert _needs_separating_space("", "word") is False
    assert _needs_separating_space("word", "") is False


def test_needs_space_keeps_space_for_multichar_fragment():
    # Not a drop cap: a multi-letter fragment is treated as a real word boundary.
    assert _needs_separating_space("US", "navy") is True


_DROPCAP_BODY = (
    "<html><body><h1>Chapter 1</h1>"
    '<p><span class="dropcap">T</span>he quick brown fox jumped over it. '
    '<span class="dropcap">I</span>t was a fine day.</p>'
    "</body></html>"
)


def _build_dropcap_epub(path: Path) -> Path:
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("dropcap-test")
    book.set_title("Drop Cap Test")
    book.set_language("en")
    book.add_author("Test Author")
    chapter = epub.EpubHtml(title="Chapter 1", file_name="chap_01.xhtml", lang="en")
    chapter.content = _DROPCAP_BODY
    book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.toc = (chapter,)
    book.spine = ["nav", chapter]
    epub.write_epub(str(path), book)
    return path


def test_parse_epub_preserves_dropcap_words(tmp_path: Path):
    result = parse_epub(_build_dropcap_epub(tmp_path / "dropcap.epub"))
    assert "The quick brown fox" in result.text
    assert "It was a fine day" in result.text
    assert "T he" not in result.text
    assert "I t was" not in result.text


_COMMENT_BODY = (
    "<html><body><h1>Chapter 1</h1>"
    '<p>Visit <!--<a href="http://example.com">link</a>-->our site for more.</p>'
    "</body></html>"
)


def _build_comment_epub(path: Path) -> Path:
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("comment-test")
    book.set_title("Comment Test")
    book.set_language("en")
    book.add_author("Test Author")
    chapter = epub.EpubHtml(title="Chapter 1", file_name="chap_01.xhtml", lang="en")
    chapter.content = _COMMENT_BODY
    book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.toc = (chapter,)
    book.spine = ["nav", chapter]
    epub.write_epub(str(path), book)
    return path


def test_parse_epub_skips_commented_markup(tmp_path: Path):
    # bs4 Comment is a NavigableString subclass; commented HTML must not leak as text.
    result = parse_epub(_build_comment_epub(tmp_path / "comment.epub"))
    assert "href" not in result.text
    assert "<a" not in result.text
    assert "example.com" not in result.text
    assert "Visit" in result.text and "our site" in result.text


# ---------------------------------------------------------------------------
# OceanofPDF watermark stripping (C2)
# ---------------------------------------------------------------------------

def test_clean_strips_oceanofpdf_watermark_lines():
    raw = (
        "Real sentence one.\n\nOceanofPDF.com\n\nReal sentence two.\n\n"
        "oceanofpdf.com\n\nEnd."
    )
    cleaned = _clean_assembled_text(raw)
    assert "oceanofpdf" not in cleaned.lower()
    for keep in ("Real sentence one.", "Real sentence two.", "End."):
        assert keep in cleaned


def test_clean_keeps_watermark_url_inside_prose():
    # Only a standalone watermark line is removed; a URL mid-sentence is left alone.
    raw = "She visited OceanofPDF.com to download the book."
    assert "OceanofPDF.com" in _clean_assembled_text(raw)


# ---------------------------------------------------------------------------
# Text-pattern heading fallback (C3)
# ---------------------------------------------------------------------------

def test_text_heading_fallback_detects_structural_lines():
    text = (
        "Front matter blah.\n\nCHAPTER I\n\nIt began.\n\nCHAPTER II\n\nIt continued.\n\n"
        "Part II\n\nLetter 1\n\nDear friend."
    )
    secs = _sections_from_text_headings(text)
    headings = [s.heading_text for s in secs]
    assert "CHAPTER I" in headings
    assert "CHAPTER II" in headings
    assert "Letter 1" in headings
    assert any(h.startswith("Part II") for h in headings)
    # Offsets are at the keyword and in document order.
    assert [s.offset for s in secs] == sorted(s.offset for s in secs)
    levels = {s.heading_text: s.heading_level for s in secs}
    assert levels["CHAPTER I"] == 3       # chapter/letter are leaf-level
    assert levels["Letter 1"] == 3
    assert levels[next(h for h in headings if h.startswith("Part II"))] == 2


def test_text_heading_fallback_ignores_inline_mentions():
    # Keywords mid-line (not starting a line) are not headings.
    text = "As discussed in chapter 3 the hero returns. Book sales rose sharply."
    assert _sections_from_text_headings(text) == []


# ---------------------------------------------------------------------------
# Resilient read against ebooklib nav-doc crashes (C4)
# ---------------------------------------------------------------------------

def test_read_epub_happy_path(tmp_path: Path):
    assert _read_epub(_build_dropcap_epub(tmp_path / "ok.epub")) is not None


def test_read_epub_defuses_nav_crash_and_restores(monkeypatch, tmp_path: Path):
    # Simulate the Book-of-Mormon case: both ordinary read attempts crash in
    # nav parsing; the guarded third attempt must succeed and restore the patch.
    from ebooklib import epub

    target = _build_dropcap_epub(tmp_path / "flaky.epub")
    original_parse_nav = epub.EpubReader._parse_nav
    real_read = epub.read_epub
    calls = {"n": 0}

    def flaky_read(path, options=None):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise IndexError("simulated nav crash")
        return real_read(path, options=options)

    monkeypatch.setattr(epub, "read_epub", flaky_read)
    book = _read_epub(target)

    assert book is not None
    assert calls["n"] == 3  # two failures, then one guarded success
    assert epub.EpubReader._parse_nav is original_parse_nav  # restored
