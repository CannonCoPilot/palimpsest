#!/usr/bin/env python3
"""
Stage 2: Text Cleaner — normalize extracted text for analysis.

Handles: encoding artifacts, ligatures, smart quotes, hyphenation rejoining,
page header/footer stripping, whitespace normalization, boilerplate removal.

Input: JSON from text_extractor (stdin or file)
Output: JSON with cleaned text chunks

Usage:
    python text_extractor.py book.pdf | python text_cleaner.py [-o cleaned.json]
    python text_cleaner.py extracted.json -o cleaned.json
"""

import argparse
import json
import re
import sys
import unicodedata
from typing import Optional

LIGATURE_MAP = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st",
    "Œ": "OE", "œ": "oe",
    "Æ": "AE", "æ": "ae",
}

SMART_QUOTE_MAP = {
    "‘": "'", "’": "'",
    "“": '"', "”": '"',
    "–": "-", "—": "--",
    "…": "...",
}

HEADER_FOOTER_PATTERNS = [
    re.compile(r"^\s*\d+\s*$", re.MULTILINE),
    re.compile(r"^\s*(?:chapter|page)\s+\w+\s*$", re.MULTILINE | re.IGNORECASE),
]

BOILERPLATE_PATTERNS = [
    re.compile(r"(?:project\s+gutenberg|distributed\s+proofreaders)", re.IGNORECASE),
    re.compile(r"(?:copyright|©)\s*\d{4}", re.IGNORECASE),
    re.compile(r"(?:all\s+rights\s+reserved)", re.IGNORECASE),
    re.compile(r"(?:isbn|issn)\s*[:=]?\s*[\d-]+", re.IGNORECASE),
]


def replace_ligatures(text: str) -> str:
    for lig, replacement in LIGATURE_MAP.items():
        text = text.replace(lig, replacement)
    return text


def normalize_quotes(text: str) -> str:
    for smart, plain in SMART_QUOTE_MAP.items():
        text = text.replace(smart, plain)
    return text


def rejoin_hyphenated_words(text: str) -> str:
    return re.sub(r"(\w)-\n\s*(\w)", r"\1\2", text)


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_page_artifacts(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d{1,4}$", stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def remove_control_chars(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)


def detect_boilerplate_lines(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        is_boilerplate = any(pat.search(line) for pat in BOILERPLATE_PATTERNS)
        if not is_boilerplate:
            cleaned.append(line)
    return "\n".join(cleaned)


def clean_text(text: str, strip_boilerplate: bool = True) -> str:
    text = normalize_unicode(text)
    text = remove_control_chars(text)
    text = replace_ligatures(text)
    text = normalize_quotes(text)
    text = rejoin_hyphenated_words(text)
    text = strip_page_artifacts(text)
    if strip_boilerplate:
        text = detect_boilerplate_lines(text)
    text = normalize_whitespace(text)
    return text


def clean_extraction(data: dict, strip_boilerplate: bool = True) -> dict:
    if "files" in data:
        for file_entry in data["files"]:
            for chunk in file_entry.get("chunks", []):
                original_len = chunk["char_count"]
                chunk["text"] = clean_text(chunk["text"], strip_boilerplate)
                chunk["char_count"] = len(chunk["text"])
                chunk["chars_removed"] = original_len - chunk["char_count"]
            file_entry["total_chars"] = sum(c["char_count"] for c in file_entry["chunks"])
    elif "chunks" in data:
        for chunk in data["chunks"]:
            original_len = chunk["char_count"]
            chunk["text"] = clean_text(chunk["text"], strip_boilerplate)
            chunk["char_count"] = len(chunk["text"])
            chunk["chars_removed"] = original_len - chunk["char_count"]
        data["total_chars"] = sum(c["char_count"] for c in data["chunks"])

    data["pipeline_stage"] = "cleaned"
    return data


def main():
    parser = argparse.ArgumentParser(description="Clean and normalize extracted text")
    parser.add_argument("input", nargs="?", help="Input JSON (default: stdin)")
    parser.add_argument("-o", "--output", help="Output JSON path (default: stdout)")
    parser.add_argument("--keep-boilerplate", action="store_true",
                        help="Don't strip boilerplate lines")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    result = clean_extraction(data, strip_boilerplate=not args.keep_boilerplate)

    indent = None if args.compact else 2
    json_str = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
