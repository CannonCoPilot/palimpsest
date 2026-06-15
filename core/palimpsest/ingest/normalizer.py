"""Text normalization: Unicode NFC, whitespace, quote standardization, SHA-256."""

from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize(text: str, strip_paratextual: bool = True) -> str:
    """Normalize text to a canonical form. Idempotent."""
    text = unicodedata.normalize("NFC", text)
    if strip_paratextual:
        text = strip_gutenberg_boilerplate(text)
    text = _normalize_quotes(text)
    text = _normalize_whitespace(text)
    return text


_GUTENBERG_START = re.compile(
    r"^\*{3}\s*START OF (?:THE |THIS )?PROJECT GUTENBERG.*$",
    re.MULTILINE | re.IGNORECASE,
)
_GUTENBERG_END = re.compile(
    r"^\*{3}\s*END OF (?:THE |THIS )?PROJECT GUTENBERG.*$",
    re.MULTILINE | re.IGNORECASE,
)
_SE_COLOPHON = re.compile(
    r"(?:^|\n)(?:This ebook is the product of|Uncopyright|Standard Ebooks|"
    r"This particular edition|The cover page is adapted).*",
    re.IGNORECASE | re.DOTALL,
)


def strip_gutenberg_boilerplate(text: str) -> str:
    """Remove Project Gutenberg / Standard Ebooks headers, footers, and colophons."""
    start_match = _GUTENBERG_START.search(text)
    if start_match:
        text = text[start_match.end():]

    end_match = _GUTENBERG_END.search(text)
    if end_match:
        text = text[:end_match.start()]

    # Standard Ebooks colophon (typically at end)
    se_match = _SE_COLOPHON.search(text, pos=max(0, len(text) - 3000))
    if se_match:
        text = text[:se_match.start()]

    return text.strip()


def _normalize_quotes(text: str) -> str:
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("«", '"').replace("»", '"')
    return text


def _normalize_whitespace(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        cleaned.append(re.sub(r"[ \t]+", " ", line).strip())
    result = "\n".join(cleaned)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def compute_sha256(text: str) -> str:
    """Compute SHA-256 hex digest of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_words(text: str) -> int:
    """Count whitespace-delimited tokens."""
    return len(text.split())


def count_characters(text: str) -> int:
    """Count Unicode characters."""
    return len(text)
