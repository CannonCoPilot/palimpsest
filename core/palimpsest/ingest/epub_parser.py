"""EPUB structural parser — extracts text, sections, and endnotes with offset mapping.

Preserves structural metadata that the simple ebooklib extraction discards:
section boundaries from heading elements, endnote pairs with bidirectional
call-site/note-text links, and OPF publication metadata.
"""

from __future__ import annotations

import logging
import posixpath
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EpubMetadata:
    title: str = ""
    author: str = ""
    publisher: str = ""
    date: str = ""
    isbn: str = ""
    language: str = "en"
    uuid: str = ""
    source_format: str = "epub"


@dataclass
class SectionBoundary:
    offset: int
    heading_text: str
    heading_level: int
    section_index: int


@dataclass
class EndnoteRecord:
    note_number: int
    call_site_start: int
    call_site_end: int
    note_text_start: int
    note_text_end: int
    note_text: str


@dataclass
class EpubParseResult:
    text: str
    metadata: EpubMetadata
    sections: list[SectionBoundary] = field(default_factory=list)
    endnotes: list[EndnoteRecord] = field(default_factory=list)
    endnote_separator_offset: int = -1
    cover_image: bytes | None = None
    cover_media_type: str = ""


def _read_epub(path: Path) -> Any:
    """Read an EPUB, tolerating producers whose nav/NCX crashes ebooklib.

    Falls back through three levels: (1) honor the NCX, (2) ignore it, and
    finally (3) defuse ebooklib's nav parser, which raises IndexError on EPUB3
    nav documents that declare no ``<nav epub:type="toc">`` (e.g. the Penguin
    Book of Mormon). Levels 1-2 don't help there because the crash is in nav
    parsing regardless of the NCX option, so without level 3 the book cannot be
    imported at all.
    """
    from ebooklib import epub

    for opts in ({"ignore_ncx": False}, {"ignore_ncx": True}):
        try:
            return epub.read_epub(str(path), options=opts)
        except Exception:
            continue

    reader_cls = getattr(epub, "EpubReader", None)
    original = getattr(reader_cls, "_parse_nav", None)
    if reader_cls is None or original is None:
        # Internals not as expected — surface the genuine error instead of a
        # confusing AttributeError from the patch path.
        return epub.read_epub(str(path), options={"ignore_ncx": True})

    def _safe_parse_nav(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return original(self, *args, **kwargs)
        except Exception:
            logger.warning("Defused ebooklib nav-parse failure for %s", path.name)
            return None

    reader_cls._parse_nav = _safe_parse_nav
    try:
        return epub.read_epub(str(path), options={"ignore_ncx": True})
    finally:
        reader_cls._parse_nav = original


def parse_epub(path: Path, content_profile: Any = None) -> EpubParseResult:
    """Parse an EPUB file, extracting text with structural metadata."""
    from palimpsest.ingest.content_filters import detect_content_profile

    book = _read_epub(path)

    # Auto-detect profile if not provided
    if content_profile is None:
        content_profile = detect_content_profile(book)

    metadata = _extract_metadata(book)
    text, sections, endnote_anchors, endnote_defs, spine_fractions = _assemble_text(
        book, content_profile
    )

    if not sections:
        sections = _sections_from_toc(book, text, spine_fractions)
    if not sections:
        sections = _sections_from_text_headings(text)

    endnotes, sep_offset = _resolve_endnotes(text, endnote_anchors, endnote_defs)
    cover_image, cover_media_type = _extract_cover(book)

    return EpubParseResult(
        text=text,
        metadata=metadata,
        sections=sections,
        endnotes=endnotes,
        endnote_separator_offset=sep_offset,
        cover_image=cover_image,
        cover_media_type=cover_media_type,
    )


_COVER_EXT_BY_MEDIA = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def cover_extension(media_type: str, name: str = "") -> str:
    """Map an image media type (falling back to a filename) to a file extension."""
    ext = _COVER_EXT_BY_MEDIA.get(media_type.lower().strip())
    if ext:
        return ext
    suffix = Path(name).suffix.lower()
    if suffix in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"):
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def _extract_cover(book: Any) -> tuple[bytes | None, str]:
    """Return (cover_bytes, media_type) for the book's cover, or (None, "").

    EPUB cover declaration is inconsistent across producers, so try, in order:
    1. an explicit cover item (EPUB3 properties="cover-image" / guide reference,
       which ebooklib surfaces as ITEM_COVER),
    2. the EPUB2 OPF <meta name="cover" content="ITEM_ID"> pointer,
    3. any manifest image whose name looks like a cover (the only strategy that
       matches many real-world files — verified empirically),
    4. the image embedded in a title/cover front-matter page (many scans, e.g.
       the 1599 Geneva Bible, ship the cover only as a titlepage <image>).
    """
    import ebooklib

    for item in book.get_items_of_type(ebooklib.ITEM_COVER):
        content = item.get_content()
        if content:
            return content, getattr(item, "media_type", "") or ""

    cover_id = None
    try:
        meta = book.get_metadata("OPF", "cover")
        if meta:
            cover_id = meta[0][1].get("content")
    except Exception:
        cover_id = None
    if cover_id:
        item = book.get_item_with_id(cover_id)
        if item is not None:
            content = item.get_content()
            if content:
                return content, getattr(item, "media_type", "") or ""

    candidates = [
        it for it in book.get_items_of_type(ebooklib.ITEM_IMAGE)
        if "cover" in it.get_name().lower()
    ]
    if candidates:
        # Prefer the most cover-like basename: 'cover.jpg' over 'frontcover-thumb.png'.
        candidates.sort(key=lambda it: (
            not Path(it.get_name()).stem.lower().startswith("cover"),
            len(it.get_name()),
        ))
        item = candidates[0]
        content = item.get_content()
        if content:
            return content, getattr(item, "media_type", "") or ""

    return _frontmatter_cover(book)


def _frontmatter_cover(book: Any) -> tuple[bytes | None, str]:
    """Return the image embedded in a title/cover front-matter page, or (None, "").

    Fallback for EPUBs that declare no cover but render one as a titlepage image
    (SVG <image> or <img>). Only front-matter spine docs whose name/id reads as a
    cover/title page are scanned, so a decorative body image is never mistaken for
    the cover. The referenced href is resolved against the manifest images.
    """
    import ebooklib

    images = {it.get_name(): it for it in book.get_items_of_type(ebooklib.ITEM_IMAGE)}
    if not images:
        return None, ""
    ref_re = re.compile(r'(?:src|xlink:href)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    front_keys = ("cover", "title", "front", "halftitle")
    for spine_id, _ in getattr(book, "spine", []):
        doc = book.get_item_with_id(spine_id)
        if doc is None:
            continue
        name = doc.get_name().lower()
        if not any(k in name or k in str(spine_id).lower() for k in front_keys):
            continue
        try:
            html = doc.get_content().decode("utf-8", "replace")
        except Exception:
            continue
        base = posixpath.dirname(doc.get_name())
        for ref in ref_re.findall(html):
            ref = ref.split("#")[0].strip()
            if not ref:
                continue
            resolved = posixpath.normpath(posixpath.join(base, ref)) if base else ref
            item = images.get(resolved) or images.get(ref) or next(
                (im for nm, im in images.items()
                 if posixpath.basename(nm) == posixpath.basename(resolved)), None)
            if item is None:
                continue
            content = item.get_content()
            if content:
                return content, getattr(item, "media_type", "") or ""
    return None, ""


def _extract_metadata(book: Any) -> EpubMetadata:
    """Extract publication metadata from OPF."""
    def _get(ns: str, key: str) -> str:
        vals = book.get_metadata(ns, key)
        if vals:
            v = vals[0]
            return v[0] if isinstance(v, tuple) else str(v)
        return ""

    identifiers = book.get_metadata("DC", "identifier")
    isbn = ""
    epub_uuid = ""
    for val, attrs in identifiers:
        val_str = str(val).strip()
        if "isbn" in str(attrs).lower() or re.match(r"^97[89]\d{10}$", val_str.replace("-", "")):
            isbn = val_str
        elif val_str.startswith("urn:uuid:") or re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            val_str, re.IGNORECASE,
        ):
            epub_uuid = val_str

    return EpubMetadata(
        title=_get("DC", "title"),
        author=_get("DC", "creator"),
        publisher=_get("DC", "publisher"),
        date=_get("DC", "date"),
        isbn=isbn,
        language=_get("DC", "language") or "en",
        uuid=epub_uuid,
    )


_HEADING_RE = re.compile(r"^h([1-6])$", re.IGNORECASE)
_ENDNOTE_ANC_RE = re.compile(r"sdendnote(\d+)anc")
_ENDNOTE_SYM_RE = re.compile(r"sdendnote(\d+)sym")
_BLOCK_TAGS = frozenset({
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "li", "tr", "section", "article", "aside",
})


def _needs_separating_space(prev: str, nxt: str) -> bool:
    """Whether to insert a space between two text fragments made adjacent when an
    inline element was flattened.

    Inserts a space only when ``prev`` ends in a non-space and ``nxt`` begins with
    a letter (the anti-concatenation rule). Crucially, it does NOT split a drop-cap
    initial: a lone uppercase letter glued to a lowercase continuation is one word
    (``<span class="dropcap">T</span>he`` -> ``The``, never ``T he``). A real
    single-letter word ("I", "A") never reaches this guard because its trailing
    space lives in the source text node, so ``prev`` already ends in whitespace.
    """
    if not prev or not nxt:
        return False
    if prev[-1].isspace() or not nxt[0].isalpha():
        return False
    prev_token = prev.strip()
    if len(prev_token) == 1 and prev_token.isupper() and nxt[0].islower():
        return False
    return True


def _sections_from_toc(
    book: Any, assembled_text: str, spine_fractions: dict[str, float] | None = None
) -> list[SectionBoundary]:
    """Extract section boundaries from the NCX/navigation table of contents.

    Fallback when HTML heading elements aren't present (common in Calibre
    conversions and older EPUB2 files that use CSS-styled chapter titles).

    Each entry is anchored via its spine ``href`` rather than a naive global text
    search. The href names the reading-order document the entry points at; that
    document's fractional position (``spine_fractions``) gives an expected offset,
    and the title is matched at the occurrence nearest it. This sidesteps the
    TOC-relocation misfire: a global ``find`` would anchor every entry to its own
    link inside an inlined TOC at the front of the book instead of the real
    division. Without spine data the search degrades to the legacy first match.
    """
    toc = book.toc
    if not toc:
        return []

    spine_fractions = spine_fractions or {}
    doc_len = len(assembled_text)
    sections: list[SectionBoundary] = []
    section_index = 0

    def _expected_offset(href: str) -> int | None:
        """Expected assembled-text offset of the document a TOC href points at."""
        file = href.split("#", 1)[0]
        if not file:
            return None
        frac = spine_fractions.get(file)
        if frac is None:  # hrefs may be path-qualified; fall back to basename match
            base = file.rsplit("/", 1)[-1]
            frac = next(
                (f for name, f in spine_fractions.items() if name.rsplit("/", 1)[-1] == base),
                None,
            )
        return int(frac * doc_len) if frac is not None else None

    def _find_near(needle: str, expected: int | None) -> int:
        """First match if no hint; else the occurrence nearest the expected offset."""
        if expected is None:
            return assembled_text.find(needle)
        best = -1
        pos = assembled_text.find(needle)
        while pos != -1:
            if best == -1 or abs(pos - expected) < abs(best - expected):
                best = pos
            if pos >= expected:
                break
            pos = assembled_text.find(needle, pos + 1)
        return best

    def _process_toc_item(item: Any, level: int) -> None:
        nonlocal section_index
        if hasattr(item, "title") and hasattr(item, "href"):
            title = str(item.title).strip()
            if not title or len(title) > 500:
                return
            title_normalized = " ".join(title.split())
            expected = _expected_offset(str(getattr(item, "href", "") or ""))
            pos = -1
            if len(title_normalized) <= 4 and title_normalized.isdigit():
                chapter_variants = [
                    f"Chapter {title_normalized}\n",
                    f"CHAPTER {title_normalized}\n",
                    f"\n{title_normalized}\n",
                ]
                for variant in chapter_variants:
                    idx = _find_near(variant, expected)
                    if idx >= 0:
                        pos = idx + 1 if variant.startswith("\n") else idx
                        title_normalized = variant.strip()
                        break
            else:
                pos = _find_near(title_normalized, expected)
                if pos < 0:
                    words = title_normalized.split()
                    if len(words) >= 2:
                        search_prefix = " ".join(words[:3]) if len(words) >= 3 else title_normalized
                        pos = _find_near(search_prefix, expected)
                        if pos >= 0:
                            context = assembled_text[pos:pos + len(title_normalized) + 50]
                            if words[-1] not in context:
                                pos = -1
            if pos >= 0:
                sections.append(SectionBoundary(
                    offset=pos,
                    heading_text=title_normalized,
                    heading_level=min(level, 6),
                    section_index=section_index,
                ))
                section_index += 1
        elif isinstance(item, tuple) and len(item) == 2:
            section, children = item
            _process_toc_item(section, level)
            for child in children:
                _process_toc_item(child, level + 1)

    for item in toc:
        _process_toc_item(item, 1)

    sections.sort(key=lambda s: s.offset)
    for i, s in enumerate(sections):
        s.section_index = i

    return sections


# Heading keywords that introduce a structural division when they begin a line
# and are followed by a roman/arabic numeral. Used only as a last-resort fallback.
_TEXT_HEADING_RE = re.compile(
    r"(?im)^[ \t]*"
    r"(chapter|chap\.|part|book|volume|vol\.|canto|letter|section)"
    r"\s+([ivxlcdm]+|\d{1,3})"
    r"\b[ \t]*(.*)$"
)
_HEADING_KEYWORD_LEVEL = {
    "part": 2, "book": 2, "volume": 2, "vol.": 2,
    "chapter": 3, "chap.": 3, "canto": 3, "letter": 3, "section": 3,
}


def _sections_from_text_headings(text: str) -> list[SectionBoundary]:
    """Last-resort fallback: detect headings from the assembled text itself.

    Some EPUBs put chapter titles in styled inline spans (no ``<hN>``) and ship
    a TOC with no chapter entries — leaving zero detectable structure (e.g. Jane
    Eyre, Frankenstein). Such headings still land on their own line in the
    assembled text because block breaks surround them, so we match
    ``CHAPTER I`` / ``Letter 1`` / ``Part II`` at line starts. Only invoked when
    HTML headings and the TOC both yielded nothing, and the user can still
    refine the result in the import wizard.
    """
    sections: list[SectionBoundary] = []
    for m in _TEXT_HEADING_RE.finditer(text):
        keyword = m.group(1).lower()
        level = _HEADING_KEYWORD_LEVEL.get(keyword, 3)
        heading = " ".join(m.group(0).split())[:120]
        sections.append(SectionBoundary(
            offset=m.start(1),
            heading_text=heading,
            heading_level=level,
            section_index=len(sections),
        ))
    return sections


def _assemble_text(book: Any, profile: Any = None) -> tuple[
    str,
    list[SectionBoundary],
    dict[int, tuple[int, int]],
    dict[int, tuple[int, str]],
    dict[str, float],
]:
    """Walk spine items in order, assembling clean text with structural markers.

    Also returns ``spine_fractions``: each included document's start position as a
    fraction of the assembled length, keyed by item name. TOC entries are anchored
    via these fractions (see ``_sections_from_toc``) so they land in reading order
    rather than at a duplicate title inside an inlined TOC. Fractions are taken
    pre-clean, which is invariant to the small, scattered removals cleaning makes.
    """
    import ebooklib
    from bs4 import BeautifulSoup, Comment, NavigableString, Tag

    from palimpsest.ingest.content_filters import apply_content_filters, should_skip_spine_item

    parts: list[str] = []
    sections: list[SectionBoundary] = []
    section_index = 0
    spine_offsets: dict[str, int] = {}
    _parts_len: int = 0  # running total of len(parts) — avoids O(n²) sum() in loops

    spine_items = []
    for item_id, _ in book.spine:
        item = book.get_item_with_id(item_id)
        if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
            spine_items.append(item)

    if not spine_items:
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            spine_items.append(item)

    for item in spine_items:
        if profile and should_skip_spine_item(item, profile):
            continue

        spine_offsets[item.get_name()] = _parts_len
        html_content = item.get_content()
        soup = BeautifulSoup(html_content, "html.parser")

        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        # Apply content-type-specific filters (e.g., strip verse numbers from Bible text)
        if profile and profile.name != "literary":
            apply_content_filters(soup, profile)

        body = soup.find("body") or soup

        for elem in body.descendants:
            if isinstance(elem, NavigableString):
                # bs4 Comment is a NavigableString subclass; commented-out markup
                # must not leak into the text (e.g. KJV Study Bible <!--<a ...>-->).
                if isinstance(elem, Comment):
                    continue
                parent = elem.parent
                if parent and parent.name in ("script", "style"):
                    continue

                text_content = str(elem)
                if not text_content.strip():
                    continue

                # Prevent word concatenation when inline elements are stripped,
                # but keep drop-cap initials intact (see _needs_separating_space).
                if parts and _needs_separating_space(parts[-1], text_content):
                    parts.append(" ")
                    _parts_len += 1

                parts.append(text_content)
                _parts_len += len(text_content)

            elif isinstance(elem, Tag):
                heading_match = _HEADING_RE.match(elem.name)
                if heading_match:
                    heading_level = int(heading_match.group(1))
                    heading_text = " ".join(elem.get_text(strip=True).split())
                    if heading_text and len(heading_text) < 500:
                        if parts and not parts[-1].endswith("\n\n"):
                            parts.append("\n\n")
                            _parts_len += 2
                        sections.append(SectionBoundary(
                            offset=_parts_len,
                            heading_text=heading_text,
                            heading_level=heading_level,
                            section_index=section_index,
                        ))
                        section_index += 1

                elif elem.name in _BLOCK_TAGS:
                    if parts and parts[-1] and not parts[-1].endswith("\n\n"):
                        if parts[-1].endswith("\n"):
                            parts.append("\n")
                            _parts_len += 1
                        else:
                            parts.append("\n\n")
                            _parts_len += 2

    raw = "".join(parts)

    pre_clean_len = len(raw)
    spine_fractions = {
        name: (off / pre_clean_len if pre_clean_len else 0.0)
        for name, off in spine_offsets.items()
    }

    raw = _clean_assembled_text(raw)

    if profile and profile.text_cleaners:
        for cleaner in profile.text_cleaners:
            raw = cleaner(raw)

    endnote_anchors, endnote_defs = _extract_endnote_data(book, spine_items, raw)

    final_sections: list[SectionBoundary] = []
    for sec in sections:
        search_start = max(0, sec.offset - 500)
        search_end = min(len(raw), sec.offset + 500)
        search_region = raw[search_start:search_end]
        words = sec.heading_text.split()
        if words:
            search_str = " ".join(words[:3]) if len(words) >= 3 else sec.heading_text
            idx_in_region = search_region.find(search_str)
            if idx_in_region >= 0:
                final_sections.append(SectionBoundary(
                    offset=search_start + idx_in_region,
                    heading_text=sec.heading_text,
                    heading_level=sec.heading_level,
                    section_index=sec.section_index,
                ))
            else:
                final_sections.append(sec)
        else:
            final_sections.append(sec)

    return raw, final_sections, endnote_anchors, endnote_defs, spine_fractions


def _extract_endnote_data(
    book: Any,
    spine_items: list[Any],
    assembled_text: str,
) -> tuple[dict[int, tuple[int, int]], dict[int, tuple[int, str]]]:
    """Extract endnote anchor and definition positions from the assembled text."""
    from bs4 import BeautifulSoup

    anchors: dict[int, tuple[int, int]] = {}
    defs: dict[int, tuple[int, str]] = {}

    for item in spine_items:
        soup = BeautifulSoup(item.get_content(), "html.parser")

        for link in soup.find_all("a"):
            elem_id = link.get("id") or link.get("name") or ""
            anc_match = _ENDNOTE_ANC_RE.search(str(elem_id))
            if anc_match:
                note_num = int(anc_match.group(1))
                link_text = link.get_text(strip=True)
                if link_text:
                    pos = _find_endnote_anchor_position(assembled_text, note_num, link)
                    if pos >= 0:
                        anchors[note_num] = (pos, pos + len(link_text))

            sym_match = _ENDNOTE_SYM_RE.search(str(elem_id))
            if sym_match:
                note_num = int(sym_match.group(1))
                note_text = _collect_endnote_text(link)
                if note_text:
                    note_text = _clean_endnote_text(note_text, note_num)
                    pos = assembled_text.find(note_text[:60].strip())
                    if pos >= 0:
                        defs[note_num] = (pos, note_text)
                    else:
                        defs[note_num] = (-1, note_text)

    return anchors, defs


def _find_endnote_anchor_position(text: str, _note_num: int, link_elem: Any) -> int:
    """Find the character position of an endnote anchor in the assembled text."""
    parent = link_elem.parent
    if parent:
        context = parent.get_text()
        if context and len(context) < 500:
            pos = text.find(context)
            if pos >= 0:
                link_text = link_elem.get_text(strip=True)
                sub_pos = context.find(link_text)
                if sub_pos >= 0:
                    return pos + sub_pos
    return -1


def _collect_endnote_text(sym_element: Any) -> str:
    """Collect the full text of an endnote, including multi-paragraph notes."""
    parent_p = sym_element.find_parent("p")
    if not parent_p:
        return sym_element.get_text(strip=True)

    parts = [parent_p.get_text()]

    sibling = parent_p.find_next_sibling()
    while sibling:
        for link in sibling.find_all("a"):
            link_id = link.get("id") or link.get("name") or ""
            if _ENDNOTE_SYM_RE.search(str(link_id)):
                return "\n".join(parts).strip()
        parts.append(sibling.get_text())
        sibling = sibling.find_next_sibling()

    return "\n".join(parts).strip()


def _clean_endnote_text(text: str, note_num: int) -> str:
    """Clean endnote text: remove the leading number and whitespace artifacts."""
    text = text.strip()
    prefix = f"{note_num}"
    if text.startswith(prefix):
        text = text[len(prefix):].lstrip()
    prefix2 = f"{note_num}."
    if text.startswith(prefix2):
        text = text[len(prefix2):].lstrip()
    prefix3 = f"{note_num}  {note_num}."
    if text.startswith(prefix3):
        text = text[len(prefix3):].lstrip()
    return text.strip()


_WATERMARK_RE = re.compile(r"(?im)^[ \t]*OceanofPDF\.com[ \t]*$")


def _clean_assembled_text(text: str) -> str:
    """Normalize assembled text: collapse whitespace, fix paragraph breaks."""
    # Strip the 'OceanofPDF.com' watermark that pirated EPUBs inject as its own
    # centered line on nearly every page (≈175× in one sample). Done before the
    # whitespace collapse so the resulting blank line folds away cleanly.
    text = _WATERMARK_RE.sub("", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *\n *(\n *)*", "\n\n", text)
    text = re.sub(r"^\s+", "", text)
    text = re.sub(r"\s+$", "\n", text)
    return text


def _resolve_endnotes(
    text: str,
    anchors: dict[int, tuple[int, int]],
    defs: dict[int, tuple[int, str]],
) -> tuple[list[EndnoteRecord], int]:
    """Resolve endnote anchors and definitions into EndnoteRecords."""
    endnotes: list[EndnoteRecord] = []
    sep_offset = -1

    all_note_nums = sorted(set(anchors.keys()) | set(defs.keys()))
    if not all_note_nums:
        return endnotes, sep_offset

    if defs:
        positive_offsets = [off for off, _ in defs.values() if off >= 0]
        if positive_offsets:
            sep_offset = min(positive_offsets)

    for num in all_note_nums:
        anc = anchors.get(num)
        defn = defs.get(num)

        call_start = anc[0] if anc else -1
        call_end = anc[1] if anc else -1
        note_start = defn[0] if defn else -1
        note_text = defn[1] if defn else ""
        note_end = note_start + len(note_text) if note_start >= 0 and note_text else -1

        endnotes.append(EndnoteRecord(
            note_number=num,
            call_site_start=call_start,
            call_site_end=call_end,
            note_text_start=note_start,
            note_text_end=note_end,
            note_text=note_text,
        ))

    return endnotes, sep_offset
