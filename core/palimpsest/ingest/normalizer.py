"""Text normalization: Unicode NFC, whitespace, quote standardization, SHA-256."""

from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize(text: str) -> str:
    """Normalize text to a canonical form. Idempotent."""
    text = unicodedata.normalize("NFC", text)
    text = _normalize_quotes(text)
    text = _normalize_whitespace(text)
    return text


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
