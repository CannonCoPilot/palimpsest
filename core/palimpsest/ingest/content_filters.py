"""Content filters for epub parsing — strip annotative markup from Bible and reference texts."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ElementSelector:
    """Matches HTML elements for filtering."""
    tag: str | None = None
    classes: frozenset[str] = field(default_factory=frozenset)
    id_pattern: re.Pattern[str] | None = None
    text_pattern: re.Pattern[str] | None = None


@dataclass
class ContentProfile:
    """Configuration for content-type-specific epub filtering."""
    name: str
    strip_selectors: list[ElementSelector] = field(default_factory=list)
    promote_selectors: list[ElementSelector] = field(default_factory=list)
    skip_file_patterns: list[str] = field(default_factory=list)
    text_cleaners: list[Callable[[str], str]] = field(default_factory=list)


PROFILE_LITERARY = ContentProfile(name="literary")

PROFILE_KJV = ContentProfile(
    name="bible-kjv",
    strip_selectors=[
        ElementSelector(tag="span", classes=frozenset({"verses"})),
    ],
)

PROFILE_TYNDALE = ContentProfile(
    name="bible-tyndale",
    strip_selectors=[
        ElementSelector(tag="span", classes=frozenset({"versejump"})),
        ElementSelector(tag="span", classes=frozenset({"displayReference"})),
        ElementSelector(tag="a", classes=frozenset({"verse"})),
    ],
)

PROFILE_GENEVA = ContentProfile(
    name="bible-geneva",
    strip_selectors=[
        ElementSelector(tag="a", id_pattern=re.compile(r"FOOTNOTE")),
        ElementSelector(tag="a", id_pattern=re.compile(r"MIDDLENOTE")),
        # Verse numbers inside calibre5 sups: <sup class="calibre5"><span class="bold1">1</span></sup>
        ElementSelector(tag="sup", classes=frozenset({"calibre5"}), text_pattern=re.compile(r"^\s*[\d,\s]+$")),
    ],
    skip_file_patterns=["split_003"],
)

PROFILE_DOUAY_RHEIMS = ContentProfile(
    name="bible-douay-rheims",
    promote_selectors=[
        ElementSelector(tag="div", classes=frozenset({"wQnqgsgYTu_NfSPYRkhxPg466"})),
    ],
    text_cleaners=[
        lambda text: re.sub(r"(?m)^\d+:\d+\.\s*", "", text),
    ],
)

_PROFILES: dict[str, ContentProfile] = {
    "literary": PROFILE_LITERARY,
    "bible-kjv": PROFILE_KJV,
    "bible-tyndale": PROFILE_TYNDALE,
    "bible-geneva": PROFILE_GENEVA,
    "bible-douay-rheims": PROFILE_DOUAY_RHEIMS,
}


def get_profile(name: str) -> ContentProfile:
    """Get a named content profile."""
    if name not in _PROFILES:
        raise ValueError(f"Unknown content profile: {name!r}. Available: {sorted(_PROFILES)}")
    return _PROFILES[name]


def detect_content_profile(book: Any) -> ContentProfile:
    """Auto-detect the content profile for an epub based on metadata and HTML structure."""
    # Check metadata for Bible keywords
    meta_text = _collect_metadata_text(book)
    is_bible_meta = any(
        kw in meta_text for kw in ("bible", "scripture", "testament", "gospel")
    )

    # Sample HTML from first few spine items
    sample_html = _get_sample_html(book)

    if not is_bible_meta and not _has_bible_markers(sample_html):
        return PROFILE_LITERARY

    # Detect specific Bible format by class/structure patterns
    if "verses" in sample_html and ("red" in sample_html or "chp_" in sample_html):
        return PROFILE_KJV
    if "versejump" in sample_html:
        return PROFILE_TYNDALE
    if "chapter-verse" in sample_html or "MIDDLENOTE" in sample_html:
        return PROFILE_GENEVA
    if "wQnqgsgYTu" in sample_html:
        return PROFILE_DOUAY_RHEIMS

    # Generic Bible: at minimum strip superscript-only verse numbers
    logger.info("Detected Bible-like content but no specific profile match; using literary")
    return PROFILE_LITERARY


def _collect_metadata_text(book: Any) -> str:
    parts = []
    for ns in ("DC",):
        for f in ("title", "subject", "description", "creator"):
            vals = book.get_metadata(ns, f)
            for v in vals:
                parts.append(str(v[0] if isinstance(v, tuple) else v).lower())
    return " ".join(parts)


def _get_sample_html(book: Any) -> str:
    import ebooklib
    count = 0
    parts = []
    for item_id, _ in book.spine:
        item = book.get_item_with_id(item_id)
        if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content().decode("utf-8", errors="replace")
            parts.append(content[:3000])
            count += 1
            if count >= 3:
                break
    return " ".join(parts)


def _has_bible_markers(html: str) -> bool:
    return any(marker in html for marker in (
        'class="verses"', 'class="versejump"', 'class="chapter-verse"',
        "FOOTNOTE", "MIDDLENOTE", 'class="verse"',
    ))


def apply_content_filters(soup: Any, profile: ContentProfile) -> None:
    """Modify soup in-place: decompose elements matching strip_selectors, promote elements matching promote_selectors."""
    from bs4 import Tag

    for selector in profile.strip_selectors:
        for elem in _find_matching(soup, selector):
            elem.decompose()

    for selector in profile.promote_selectors:
        for elem in _find_matching(soup, selector):
            if isinstance(elem, Tag):
                elem.name = "h2"


def _find_matching(soup: Any, sel: ElementSelector) -> list[Any]:
    from bs4 import Tag

    if sel.tag:
        candidates = soup.find_all(sel.tag)
    else:
        candidates = soup.find_all(True)

    results = []
    for elem in candidates:
        if not isinstance(elem, Tag):
            continue
        if sel.classes:
            elem_classes = set(elem.get("class", []))
            if not sel.classes.issubset(elem_classes):
                continue
        if sel.id_pattern:
            elem_id = elem.get("id") or ""
            if not sel.id_pattern.search(elem_id):
                continue
        if sel.text_pattern:
            text = elem.get_text(strip=True)
            if not sel.text_pattern.match(text):
                continue
        results.append(elem)
    return results


def should_skip_spine_item(item: Any, profile: ContentProfile) -> bool:
    """Check if a spine item should be skipped based on filename patterns."""
    if not profile.skip_file_patterns:
        return False
    name = getattr(item, "file_name", "") or getattr(item, "get_name", lambda: "")()
    return any(pat in name for pat in profile.skip_file_patterns)
