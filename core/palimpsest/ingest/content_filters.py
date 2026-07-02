"""Content filters for epub parsing — strip annotative markup from Bible and reference texts."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Block-level tags whose boundaries the epub parser turns into paragraph breaks. Mirrors
# ``epub_parser._BLOCK_TAGS`` (kept local to avoid a circular import); a split_before element is
# lifted into a new tag of its enclosing block's kind so it begins a fresh paragraph.
_BLOCK_TAGS = frozenset({
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "li", "tr", "section", "article", "aside",
})


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
    # Elements before which the enclosing <p> is split, so the element begins a new paragraph.
    split_before_selectors: list[ElementSelector] = field(default_factory=list)
    skip_file_patterns: list[str] = field(default_factory=list)
    text_cleaners: list[Callable[[str], str]] = field(default_factory=list)


PROFILE_LITERARY = ContentProfile(name="literary")

# The KJV epub packs a whole chapter into one <p> with inline <span class="verses">N</span> verse
# markers. Formerly this profile *stripped* those spans, deleting the verse numbers and leaving the
# chapter as a single paragraph — which both lost the canonical references and made verse-vs-verse
# alignment degenerate. Instead: PRESERVE each verse span and split the chapter <p> so every verse
# becomes its own paragraph (soup equivalent of the fixture's _patch_epub), then strip only the
# TOC/index anchors (a.index book links + a.index2a per-book chapter links, which live on the index
# pages and carry no verse text). Mirrors the gold-verified _kjv_profile in validation-mm/build.py.
PROFILE_KJV = ContentProfile(
    name="bible-kjv",
    strip_selectors=[
        ElementSelector(tag="a", classes=frozenset({"index"})),
        ElementSelector(tag="a", classes=frozenset({"index2a"})),
    ],
    split_before_selectors=[
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

# Geneva footnote/cross-reference paragraph classes. ``second_scripture``/``fn-sub``/``fn_line``
# are footnote-only paragraphs; ``midtx``/``midtx1``/``midtx2`` are marginal cross-references
# ("a Luke 3:23"). Stripping these leaves the chapter-verse (verse text) and chapter (argument)
# paragraphs — the analyzable frame — matching the Douay-Rheims clean-text standard.
_GENEVA_NOTE_CLASSES = ("second_scripture", "fn-sub", "fn_line", "midtx", "midtx1", "midtx2")

PROFILE_GENEVA = ContentProfile(
    name="bible-geneva",
    strip_selectors=[
        ElementSelector(tag="a", id_pattern=re.compile(r"FOOTNOTE")),
        ElementSelector(tag="a", id_pattern=re.compile(r"MIDDLENOTE")),
        # Verse numbers inside calibre5 sups: <sup class="calibre5"><span class="bold1">1</span></sup>
        ElementSelector(tag="sup", classes=frozenset({"calibre5"}), text_pattern=re.compile(r"^\s*[\d,\s]+$")),
        *(ElementSelector(tag="p", classes=frozenset({c})) for c in _GENEVA_NOTE_CLASSES),
    ],
    # Keep every spine file: the old skip_file_patterns=["split_003"] dropped a file that also
    # holds tail-chapter verse text (Matthew 27-28), truncating the Gospels. The footnote content
    # that motivated the skip is removed above by paragraph-class stripping instead.
    skip_file_patterns=[],
)

PROFILE_DOUAY_RHEIMS = ContentProfile(
    name="bible-douay-rheims",
    promote_selectors=[
        ElementSelector(tag="div", classes=frozenset({"wQnqgsgYTu_NfSPYRkhxPg466"})),
    ],
    # Verse-number prefixes ("1:1. ") are intentionally PRESERVED in the text: they carry the
    # canonical verse reference and delimit verses exactly. The masking layer marks each number
    # token as masked (so it is excluded from analysis) while the verse text stays analyzable.
    text_cleaners=[],
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

    # Detect specific Bible format by distinctive class/structure markers.
    # Order matters: check the most specific markers first so a format whose
    # markup happens to contain a generic token (e.g. Tyndale also has verse
    # spans) isn't captured by an earlier, looser rule.
    if "versejump" in sample_html:
        return PROFILE_TYNDALE
    if "chapter-verse" in sample_html or "MIDDLENOTE" in sample_html:
        return PROFILE_GENEVA
    if "wQnqgsgYTu" in sample_html:
        return PROFILE_DOUAY_RHEIMS
    # KJV last: anchor to the class attribute so the bare substring "verses"
    # (and the formerly-used "red", a substring of countless words) can't
    # mis-trigger on unrelated markup.
    if 'class="verses"' in sample_html:
        return PROFILE_KJV

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


def _get_sample_html(book: Any, max_items: int = 12, per_item: int = 6000) -> str:
    """Sample HTML spread across the whole spine.

    Sampling only the first few spine items misses formats whose distinctive
    markup lives past the front matter — e.g. the 1599 Geneva Bible keeps all
    its ``chapter-verse``/``MIDDLENOTE`` markup in content files that come after
    ~15 front-matter items, so a head-only sample detected it as literary.
    Evenly-spaced picks across the spine guarantee we look at real content.
    """
    import ebooklib

    docs = []
    for item_id, _ in book.spine:
        item = book.get_item_with_id(item_id)
        if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
            docs.append(item)
    if not docs:
        docs = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    if not docs:
        return ""

    if len(docs) > max_items:
        # Endpoint-inclusive spread: always sample the first and last document
        # items plus evenly-spaced picks between, so a marker in the final
        # content file is never skipped.
        last = len(docs) - 1
        seen: set[int] = set()
        picks = []
        for i in range(max_items):
            idx = round(i * last / (max_items - 1))
            if idx not in seen:
                seen.add(idx)
                picks.append(docs[idx])
    else:
        picks = docs

    parts = []
    for item in picks:
        content = item.get_content().decode("utf-8", errors="replace")
        parts.append(content[:per_item])
    return " ".join(parts)


def _has_bible_markers(html: str) -> bool:
    return any(marker in html for marker in (
        'class="verses"', 'class="versejump"', 'class="chapter-verse"',
        "FOOTNOTE", "MIDDLENOTE", 'class="verse"',
    ))


def apply_content_filters(soup: Any, profile: ContentProfile) -> None:
    """Modify soup in-place: split enclosing blocks before split_before_selectors, decompose
    elements matching strip_selectors, promote elements matching promote_selectors."""
    from bs4 import Tag

    # Split first so verse-span boundaries define paragraph structure before anything is removed.
    for selector in profile.split_before_selectors:
        _split_block_before(soup, selector)

    for selector in profile.strip_selectors:
        for elem in _find_matching(soup, selector):
            elem.decompose()

    for selector in profile.promote_selectors:
        for elem in _find_matching(soup, selector):
            if isinstance(elem, Tag):
                elem.name = "h2"


def _enclosing_block(elem: Any) -> Any:
    """The nearest block-level ancestor of ``elem`` (inclusive), or None if none exists."""
    node = elem
    while node is not None:
        name = getattr(node, "name", None)
        if name in _BLOCK_TAGS:
            return node
        node = node.parent
    return None


def _split_block_before(soup: Any, selector: ElementSelector) -> None:
    """Split each matching element's enclosing block so the element begins a new paragraph.

    Soup equivalent of the fixture's raw-HTML patch (``<span class="verses">`` ->
    ``</p><p><span class="verses">``): a chapter ``<p>`` packed with several inline verse spans is
    partitioned into one ``<p>`` per verse. For each enclosing block, every matching top-level child
    (and its following siblings up to the next match) is lifted into a fresh sibling block, so each
    verse span opens its own paragraph while its number and text are preserved verbatim.
    """
    # Group matches by enclosing block in document order; ascend each match to the block's direct
    # child so the split point is always a top-level sibling we can partition on.
    order: list[int] = []
    grouped: dict[int, tuple[Any, list[Any]]] = {}
    for elem in _find_matching(soup, selector):
        block = _enclosing_block(elem)
        if block is None:
            continue
        node = elem
        while node.parent is not block:
            node = node.parent
            if node is None:
                break
        if node is None:
            continue
        key = id(block)
        if key not in grouped:
            grouped[key] = (block, [])
            order.append(key)
        grouped[key][1].append(node)

    for key in order:
        block, points = grouped[key]
        # Extract from last point to first so earlier siblings stay put; each insert_after(block)
        # lands immediately after the block, so processing in reverse yields correct final order.
        for point in reversed(points):
            new_block = soup.new_tag(block.name)
            for sibling in _self_and_following(point):
                new_block.append(sibling.extract())
            block.insert_after(new_block)


def _self_and_following(node: Any) -> list[Any]:
    """``node`` plus all of its following siblings, captured before any are moved."""
    collected = []
    sib = node
    while sib is not None:
        collected.append(sib)
        sib = sib.next_sibling
    return collected


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
