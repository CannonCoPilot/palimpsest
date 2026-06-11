"""EPUB structural parser — extracts text, sections, and endnotes with offset mapping.

Preserves structural metadata that the simple ebooklib extraction discards:
section boundaries from heading elements, endnote pairs with bidirectional
call-site/note-text links, and OPF publication metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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


def parse_epub(path: Path) -> EpubParseResult:
    """Parse an EPUB file, extracting text with structural metadata."""
    import ebooklib
    from ebooklib import epub

    book = epub.read_epub(str(path), options={"ignore_ncx": False})

    metadata = _extract_metadata(book)
    text, sections, endnote_anchors, endnote_defs = _assemble_text(book)

    if not sections:
        sections = _sections_from_toc(book, text)

    endnotes, sep_offset = _resolve_endnotes(text, endnote_anchors, endnote_defs)

    return EpubParseResult(
        text=text,
        metadata=metadata,
        sections=sections,
        endnotes=endnotes,
        endnote_separator_offset=sep_offset,
    )


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


def _sections_from_toc(book: Any, assembled_text: str) -> list[SectionBoundary]:
    """Extract section boundaries from the NCX/navigation table of contents.

    Fallback when HTML heading elements aren't present (common in Calibre
    conversions and older EPUB2 files that use CSS-styled chapter titles).
    """
    toc = book.toc
    if not toc:
        return []

    sections: list[SectionBoundary] = []
    section_index = 0

    def _process_toc_item(item: Any, level: int) -> None:
        nonlocal section_index
        if hasattr(item, "title") and hasattr(item, "href"):
            title = str(item.title).strip()
            if not title or len(title) > 500:
                return
            title_normalized = " ".join(title.split())
            pos = -1
            if len(title_normalized) <= 4 and title_normalized.isdigit():
                chapter_variants = [
                    f"Chapter {title_normalized}\n",
                    f"CHAPTER {title_normalized}\n",
                    f"\n{title_normalized}\n",
                ]
                for variant in chapter_variants:
                    idx = assembled_text.find(variant)
                    if idx >= 0:
                        pos = idx + 1 if variant.startswith("\n") else idx
                        title_normalized = variant.strip()
                        break
            else:
                pos = assembled_text.find(title_normalized)
                if pos < 0:
                    words = title_normalized.split()
                    if len(words) >= 2:
                        search_prefix = " ".join(words[:3]) if len(words) >= 3 else title_normalized
                        pos = assembled_text.find(search_prefix)
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


def _assemble_text(book: Any) -> tuple[
    str,
    list[SectionBoundary],
    dict[int, tuple[int, int]],
    dict[int, tuple[int, str]],
]:
    """Walk spine items in order, assembling clean text with structural markers."""
    import ebooklib
    from bs4 import BeautifulSoup, NavigableString, Tag

    parts: list[str] = []
    sections: list[SectionBoundary] = []
    section_index = 0

    spine_items = []
    for item_id, _ in book.spine:
        item = book.get_item_with_id(item_id)
        if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
            spine_items.append(item)

    if not spine_items:
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            spine_items.append(item)

    for item in spine_items:
        html_content = item.get_content()
        soup = BeautifulSoup(html_content, "html.parser")

        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        body = soup.find("body") or soup

        for elem in body.descendants:
            if isinstance(elem, NavigableString):
                parent = elem.parent
                if parent and parent.name in ("script", "style"):
                    continue

                text_content = str(elem)
                if not text_content.strip():
                    continue

                parts.append(text_content)

            elif isinstance(elem, Tag):
                heading_match = _HEADING_RE.match(elem.name)
                if heading_match:
                    heading_level = int(heading_match.group(1))
                    heading_text = " ".join(elem.get_text(strip=True).split())
                    if heading_text and len(heading_text) < 500:
                        if parts and not parts[-1].endswith("\n\n"):
                            parts.append("\n\n")
                        offset = sum(len(p) for p in parts)
                        sections.append(SectionBoundary(
                            offset=offset,
                            heading_text=heading_text,
                            heading_level=heading_level,
                            section_index=section_index,
                        ))
                        section_index += 1

                elif elem.name in _BLOCK_TAGS:
                    if parts and parts[-1] and not parts[-1].endswith("\n\n"):
                        if parts[-1].endswith("\n"):
                            parts.append("\n")
                        else:
                            parts.append("\n\n")

    raw = "".join(parts)

    raw = _clean_assembled_text(raw)

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

    return raw, final_sections, endnote_anchors, endnote_defs


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


def _clean_assembled_text(text: str) -> str:
    """Normalize assembled text: collapse whitespace, fix paragraph breaks."""
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
