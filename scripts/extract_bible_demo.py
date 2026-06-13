#!/usr/bin/env python3
"""Extract Gospel texts from Bible epubs into Palimpsest demo projects.

Extracts 5 texts:
  1. matthew-kjv       — Gospel of Matthew from KJV
  2. mark-kjv          — Gospel of Mark from KJV
  3. matthew-geneva     — Gospel of Matthew from 1599 Geneva Bible
  4. matthew-tyndale    — Gospel of Matthew from Tyndale Bible
  5. matthew-douay-rheims — Gospel of Matthew from Douay-Rheims

Usage:
    python scripts/extract_bible_demo.py [--workspace .scratch/demo]
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


BIBDIR = Path(__file__).parent.parent.parent / "Project_Aion" / "projects" / "annas_archive" / "library" / "Bibles"

EPUB_FILES = {
    "kjv": "The Holy Bible -- King James Version",
    "tyndale": "Tyndale Bible",
    "geneva": "1599 Geneva Bible",
    "rheims": "Douay-Rheims Bible",
}


def find_epub(prefix: str) -> Path:
    for f in BIBDIR.iterdir():
        if f.name.startswith(prefix) and f.suffix == ".epub":
            return f
    raise FileNotFoundError(f"No epub starting with {prefix!r} in {BIBDIR}")


def extract_html_from_zip(epub_path: Path, internal_paths: list[str]) -> list[str]:
    with zipfile.ZipFile(epub_path) as zf:
        results = []
        for p in internal_paths:
            results.append(zf.read(p).decode("utf-8", errors="replace"))
        return results


def strip_tags_and_filter(html: str, profile_name: str) -> str:
    from palimpsest.ingest.content_filters import apply_content_filters, get_profile

    profile = get_profile(profile_name)
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    if profile.name != "literary":
        apply_content_filters(soup, profile)

    body = soup.find("body") or soup
    blocks: list[str] = []
    _walk_for_text(body, blocks)

    text = "".join(blocks)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *\n *(\n *)*", "\n\n", text)
    text = text.strip()

    for cleaner in profile.text_cleaners:
        text = cleaner(text)

    return text


_BLOCK_TAGS = frozenset({
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "li", "tr", "section", "article", "aside",
})

_HEADING_RE = re.compile(r"^h([1-6])$", re.IGNORECASE)


def _walk_for_text(element: Any, parts: list[str]) -> None:
    from bs4 import NavigableString, Tag

    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if text.strip():
                parts.append(text)
        elif isinstance(child, Tag):
            if child.name in ("script", "style"):
                continue
            if child.name in _BLOCK_TAGS or _HEADING_RE.match(child.name):
                if parts and parts[-1] and not parts[-1].endswith("\n\n"):
                    parts.append("\n\n")
            _walk_for_text(child, parts)
            if child.name in _BLOCK_TAGS or _HEADING_RE.match(child.name):
                if parts and not parts[-1].endswith("\n\n"):
                    parts.append("\n\n")


# ── Per-epub extraction functions ──


def extract_kjv_book(epub_path: Path, book_file: str, book_title: str) -> str:
    """Extract a single book from the KJV epub (one file per book)."""
    [html] = extract_html_from_zip(epub_path, [f"OEBPS/{book_file}"])

    soup = BeautifulSoup(html, "html.parser")

    # Remove the navigation links at top (TOC links)
    for a in soup.find_all("a", class_="index"):
        a.decompose()
    for a in soup.find_all("a", class_="index2a"):
        a.decompose()

    # Convert chapter headings: <h2 id="chp_NNN">Matthew 1 [TOC]</h2> → clean heading
    for h2 in soup.find_all("h2"):
        h2_text = h2.get_text(strip=True)
        # Strip [TOC] suffix
        h2_text = re.sub(r"\s*\[TOC\]\s*$", "", h2_text)
        h2.string = h2_text

    text = strip_tags_and_filter(str(soup), "bible-kjv")

    # Remove the book-level heading (redundant with title)
    text = re.sub(rf"^{re.escape(book_title)}\s*\n\n", "", text)

    return text.strip()


def extract_tyndale_book(epub_path: Path, book_prefix: str) -> str:
    """Extract a book from the Tyndale epub (one file per chapter)."""
    with zipfile.ZipFile(epub_path) as zf:
        # Find chapter files: Matt-1.xml through Matt-28.xml
        chapter_files = sorted(
            [f for f in zf.namelist()
             if f.startswith(f"OPS/{book_prefix}-") and f.endswith(".xml")],
            key=lambda f: int(re.search(r"-(\d+)\.xml$", f).group(1))
        )

    if not chapter_files:
        raise ValueError(f"No chapter files found for {book_prefix}")

    html_parts = extract_html_from_zip(epub_path, chapter_files)
    texts: list[str] = []

    for i, html in enumerate(html_parts):
        chapter_num = int(re.search(r"-(\d+)\.xml$", chapter_files[i]).group(1))
        chapter_text = strip_tags_and_filter(html, "bible-tyndale")
        chapter_text = chapter_text.strip()
        if chapter_text:
            texts.append(f"Chapter {chapter_num}\n\n{chapter_text}")

    return "\n\n".join(texts)


def extract_geneva_matthew(epub_path: Path) -> str:
    """Extract Matthew from the Geneva epub (3 text files + skip footnotes file)."""
    text_files = [
        "text/part0055_split_000.html",
        "text/part0055_split_001.html",
        "text/part0055_split_002.html",
    ]
    html_parts = extract_html_from_zip(epub_path, text_files)
    texts: list[str] = []

    for html in html_parts:
        text = strip_tags_and_filter(html, "bible-geneva")
        text = text.strip()
        if text:
            texts.append(text)

    combined = "\n\n".join(texts)

    # The Geneva has chapter markers like "1 1 That Jesus is..." (chapter summary)
    # and verse content with IDs. Clean up any remaining artifacts.
    # Remove lines that are just numbers (orphaned verse/chapter numbers)
    combined = re.sub(r"(?m)^\d+$\n?", "", combined)

    return combined.strip()


def extract_rheims_matthew(epub_path: Path) -> str:
    """Extract Matthew from the Douay-Rheims epub (3 files)."""
    text_files = [
        "OEBPS/part0120.xhtml",
        "OEBPS/part0121.xhtml",
        "OEBPS/part0122.xhtml",
    ]
    html_parts = extract_html_from_zip(epub_path, text_files)
    texts: list[str] = []

    for html in html_parts:
        text = strip_tags_and_filter(html, "bible-douay-rheims")

        # Remove chapter summary paragraphs (they appear between heading and first verse)
        # Summary div class is wQnqgsgYTu_NfSPYRkhxPg468 — these were not decomposed,
        # just left as text. We can identify them: they don't start with verse text
        # and appear right after chapter headings.

        text = text.strip()
        if text:
            texts.append(text)

    return "\n\n".join(texts).strip()


def ingest_text(
    text: str,
    workspace: Path,
    slug: str,
    title: str,
    author: str,
    year: int,
) -> None:
    """Write extracted text to a temp file and ingest it as a Palimpsest project."""
    from palimpsest.project import ingest_file

    project_dir = workspace / slug
    if project_dir.exists():
        print(f"  Skipping {slug} — already exists")
        return

    tmp = workspace / f".tmp-{slug}.txt"
    tmp.write_text(text, encoding="utf-8")

    try:
        project = ingest_file(
            source_path=tmp,
            workspace=workspace,
            title=title,
            author=author,
            year=year,
        )
        meta = project.metadata
        print(f"  {slug}: {meta.word_count:,} words, {meta.paragraph_count} paragraphs, {meta.section_count} sections")
    finally:
        tmp.unlink(missing_ok=True)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Extract Gospel demo texts from Bible epubs")
    parser.add_argument("--workspace", type=Path, default=Path(".scratch/demo"))
    parser.add_argument("--bibdir", type=Path, default=None)
    args = parser.parse_args()

    workspace = args.workspace
    workspace.mkdir(parents=True, exist_ok=True)

    global BIBDIR
    if args.bibdir:
        BIBDIR = args.bibdir

    print("Finding epub files...")
    epubs = {}
    for key, prefix in EPUB_FILES.items():
        try:
            epubs[key] = find_epub(prefix)
            print(f"  {key}: {epubs[key].name[:60]}...")
        except FileNotFoundError as e:
            print(f"  {key}: NOT FOUND — {e}")

    targets = [
        ("matthew-kjv", "kjv", lambda p: extract_kjv_book(p, "chapter_44.xhtml", "Matthew"),
         "Gospel of Matthew (KJV)", "King James Version", 1611),
        ("mark-kjv", "kjv", lambda p: extract_kjv_book(p, "chapter_45.xhtml", "Mark"),
         "Gospel of Mark (KJV)", "King James Version", 1611),
        ("matthew-tyndale", "tyndale", lambda p: extract_tyndale_book(p, "Matt"),
         "Gospel of Matthew (Tyndale)", "William Tyndale", 1526),
        ("matthew-geneva", "geneva", lambda p: extract_geneva_matthew(p),
         "Gospel of Matthew (Geneva 1599)", "Geneva Bible", 1599),
        ("matthew-douay-rheims", "rheims", lambda p: extract_rheims_matthew(p),
         "Gospel of Matthew (Douay-Rheims)", "Douay-Rheims Version", 1582),
    ]

    print(f"\nExtracting {len(targets)} texts to {workspace}/...")
    for slug, epub_key, extractor, title, author, year in targets:
        if epub_key not in epubs:
            print(f"\n{slug}: SKIPPED (epub not found)")
            continue

        print(f"\n{slug}:")
        try:
            text = extractor(epubs[epub_key])
            print(f"  Extracted {len(text):,} chars")

            first_line = text.split("\n")[0][:80]
            print(f"  First line: {first_line}")

            ingest_text(text, workspace, slug, title, author, year)
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
