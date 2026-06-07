#!/usr/bin/env python3
"""
Stage 1: Text Extractor — parse PDF/EPUB/TXT/HTML into clean plaintext.

Supports: .pdf (via PyMuPDF), .epub (via ebooklib+BeautifulSoup),
          .txt/.md (direct read), .html (BeautifulSoup).

Output: JSON with extracted text, source metadata, and per-page/chapter structure.

Usage:
    python text_extractor.py input.pdf [-o output.json]
    python text_extractor.py /path/to/directory/ --recursive
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".txt", ".md", ".html", ".htm"}


@dataclass
class ExtractedChunk:
    index: int
    label: str
    text: str
    char_count: int


@dataclass
class ExtractionResult:
    source_path: str
    format: str
    title: Optional[str]
    chunks: list
    total_chars: int
    total_chunks: int


def extract_pdf(path: str) -> ExtractionResult:
    import fitz
    doc = fitz.open(path)
    chunks = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        chunks.append(ExtractedChunk(
            index=i,
            label=f"page_{i+1}",
            text=text,
            char_count=len(text),
        ))
    title = doc.metadata.get("title") or Path(path).stem
    doc.close()
    total = sum(c.char_count for c in chunks)
    return ExtractionResult(
        source_path=str(path),
        format="pdf",
        title=title,
        chunks=[asdict(c) for c in chunks],
        total_chars=total,
        total_chunks=len(chunks),
    )


def extract_epub(path: str) -> ExtractionResult:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(path, options={"ignore_ncx": True})
    title = book.get_metadata("DC", "title")
    title = title[0][0] if title else Path(path).stem

    chunks = []
    idx = 0
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        if not text.strip():
            continue
        label = item.get_name() or f"section_{idx}"
        chunks.append(ExtractedChunk(
            index=idx,
            label=label,
            text=text,
            char_count=len(text),
        ))
        idx += 1

    total = sum(c.char_count for c in chunks)
    return ExtractionResult(
        source_path=str(path),
        format="epub",
        title=title,
        chunks=[asdict(c) for c in chunks],
        total_chars=total,
        total_chunks=len(chunks),
    )


def extract_html(path: str) -> ExtractionResult:
    from bs4 import BeautifulSoup

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else Path(path).stem
    text = soup.get_text(separator="\n", strip=True)

    chunks = [asdict(ExtractedChunk(index=0, label="body", text=text, char_count=len(text)))]
    return ExtractionResult(
        source_path=str(path),
        format="html",
        title=title,
        chunks=chunks,
        total_chars=len(text),
        total_chunks=1,
    )


def extract_plaintext(path: str) -> ExtractionResult:
    import chardet

    with open(path, "rb") as f:
        raw = f.read()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8") or "utf-8"

    text = raw.decode(encoding, errors="replace")
    fmt = "markdown" if path.endswith(".md") else "plaintext"
    chunks = [asdict(ExtractedChunk(index=0, label="full_text", text=text, char_count=len(text)))]
    return ExtractionResult(
        source_path=str(path),
        format=fmt,
        title=Path(path).stem,
        chunks=chunks,
        total_chars=len(text),
        total_chunks=1,
    )


def extract_file(path: str) -> ExtractionResult:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_pdf(path)
    elif ext == ".epub":
        return extract_epub(path)
    elif ext in (".html", ".htm"):
        return extract_html(path)
    elif ext in (".txt", ".md"):
        return extract_plaintext(path)
    else:
        raise ValueError(f"Unsupported format: {ext}")


def find_files(directory: str, recursive: bool = False) -> list:
    results = []
    if recursive:
        for root, _, files in os.walk(directory):
            for f in files:
                if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS:
                    results.append(os.path.join(root, f))
    else:
        for f in os.listdir(directory):
            if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS:
                results.append(os.path.join(directory, f))
    return sorted(results)


def main():
    parser = argparse.ArgumentParser(description="Extract text from PDF/EPUB/TXT/HTML")
    parser.add_argument("input", help="File or directory path")
    parser.add_argument("-o", "--output", help="Output JSON path (default: stdout)")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="Recursively process directories")
    parser.add_argument("--compact", action="store_true",
                        help="Compact JSON output (no indentation)")
    args = parser.parse_args()

    input_path = args.input

    if os.path.isdir(input_path):
        files = find_files(input_path, recursive=args.recursive)
        if not files:
            print(f"No supported files found in {input_path}", file=sys.stderr)
            return 1
        results = []
        for fp in files:
            try:
                results.append(asdict(extract_file(fp)))
                print(f"  extracted: {fp}", file=sys.stderr)
            except Exception as e:
                print(f"  FAILED: {fp} — {e}", file=sys.stderr)
        output = {"files": results, "total_files": len(results)}
    else:
        result = extract_file(input_path)
        output = asdict(result)

    indent = None if args.compact else 2
    json_str = json.dumps(output, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
