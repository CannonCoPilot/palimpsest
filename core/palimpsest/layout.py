"""Publication-layout sections and masking for the staged import pipeline.

A *layout section* is a typed, optionally-nested, named character range over
reference.txt (title page, chapter, endnotes, ...). Each type carries a mask flag;
masked ranges are excluded from downstream analysis.

The model is a *foundation + carve-window* stack. A small foundation layer tiles the
entire work in the fewest elements (front matter, the analyzable ``body``, back
matter, notes). Smaller, more-specific sections layer on top as subsets: structural
navigation (volume/book/part/chapter) and masked windows (the ``header`` label of a
chapter, footnotes, editorial notes). Masking resolves by the *deepest section wins*
rule — a character's effective mask comes from the most-specific (smallest-span)
section covering it — so a mask=no chapter nested in a mask=no body stays analyzable
while its mask=yes ``header`` label carves a masked window straight through it.
Uncovered text is unmasked (it belongs to the work).

Persisted per project as ``layout_sections.json``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The fixed section vocabulary, grouped by role. Custom user types may extend this
# at runtime (they are tolerated everywhere; only the default mask differs).
SECTION_TYPES: tuple[str, ...] = (
    # Foundation — these tile the whole work in the fewest elements.
    "body",
    # Structural / navigational containers nested inside the body.
    "volume", "book", "part", "chapter",
    # Masked windows carved inside the body.
    "header", "footnotes", "endnotes", "epigraph",
    # Translation of a subject text the work is written about (scripture in a study
    # bible, a quoted-source rendering, parallel-version columns).
    "translation",
    # Front-matter region + subtypes.
    "front_matter", "title_page", "copyright", "contents",
    "dedication", "foreword", "preface", "introduction",
    # Back-matter region + subtypes.
    "back_matter", "afterword", "acknowledgments", "about_author",
    "discussion", "glossary", "index", "bibliography",
    "appendix", "addendum", "insert",
)

SECTION_LABELS: dict[str, str] = {
    "body": "Body",
    "volume": "Volume", "book": "Book", "part": "Part", "chapter": "Chapter",
    "header": "Header", "footnotes": "Footnotes", "endnotes": "Endnotes",
    "epigraph": "Epigraph", "translation": "Translation",
    "front_matter": "Front Matter", "title_page": "Title Page", "copyright": "Copyright",
    "contents": "Contents", "dedication": "Dedication", "foreword": "Foreword",
    "preface": "Preface", "introduction": "Introduction",
    "back_matter": "Back Matter", "afterword": "Afterword",
    "acknowledgments": "Acknowledgments", "about_author": "About the Author",
    "discussion": "Discussion Questions", "glossary": "Glossary", "index": "Index",
    "bibliography": "Bibliography", "appendix": "Appendix", "addendum": "Addendum",
    "insert": "Insert",
}

# The analyzable work text: body and its structural nav containers are unmasked;
# everything else (matter, headers, notes) is masked by default.
_UNMASKED_TYPES = frozenset({"body", "volume", "book", "part", "chapter"})
DEFAULT_MASK_BY_TYPE: dict[str, bool] = {t: t not in _UNMASKED_TYPES for t in SECTION_TYPES}

SECTION_COLORS: dict[str, str] = {
    "body": "#98989d",
    "chapter": "#30d158", "part": "#34c759", "volume": "#5e5ce6", "book": "#0a84ff",
    "header": "#636366", "footnotes": "#ffd60a", "endnotes": "#ffd60a", "epigraph": "#ac8e68",
    "translation": "#bf5af2",
    "front_matter": "#ff453a", "title_page": "#bf5af2", "copyright": "#d6649b",
    "contents": "#ff6482", "dedication": "#ff7ab6", "foreword": "#ff9f0a",
    "preface": "#ff9f0a", "introduction": "#ffb340",
    "back_matter": "#ff453a", "afterword": "#ff9f0a", "acknowledgments": "#ffb340",
    "about_author": "#c0a0ff", "discussion": "#ff6482", "glossary": "#8e8e93",
    "index": "#8e8e93", "bibliography": "#8e8e93", "appendix": "#64d2ff",
    "addendum": "#64d2ff", "insert": "#5ac8fa",
}

# Structural nesting depth: body(0) > volume > book/part > chapter. A section of
# level L extends until the next boundary whose level is <= L, which yields containment.
_TYPE_LEVEL: dict[str, int] = {"body": 0, "volume": 1, "book": 2, "part": 2, "chapter": 3}

# Type roles for region detection.
_STRUCTURAL = frozenset({"volume", "book", "part", "chapter"})
_FRONTMATTER = frozenset({
    "front_matter", "title_page", "copyright", "contents",
    "dedication", "foreword", "preface", "introduction", "epigraph",
})
_BACKMATTER = frozenset({
    "back_matter", "afterword", "acknowledgments", "about_author", "discussion",
    "glossary", "index", "bibliography", "appendix", "addendum", "insert",
})
# Mid-body editorial matter that carves a masked window where it appears.
_EDITORIAL = frozenset({"foreword", "preface", "introduction", "afterword", "epigraph"})

# A heading label is short; cap the carved header window so a coarse boundary source
# can't mask an entire section.
_MAX_HEADER_LEN = 300

MASKED_TEXT_COLOR = "#f5f5f5"
MASKED_BG_COLOR = "#3a3a3d"


@dataclass
class LayoutSection:
    id: str
    type: str
    start: int
    end: int
    label: str = ""           # human heading text, e.g. "Chapter I.—The salutation"
    name: str = ""            # stable per-type element name, e.g. "chapter_1"
    parent_id: str | None = None
    source: str = "auto"          # "auto" (detected) or "user" (added/edited)
    masked: bool | None = None     # None = inherit mask_by_type[type]; bool = override
    # Structured heading data, e.g. a chapter's {"number": "IV", "name": "The Reckoning"}.
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "type": self.type, "start": self.start, "end": self.end,
            "label": self.label, "name": self.name, "parent_id": self.parent_id,
            "source": self.source, "masked": self.masked, "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LayoutSection:
        return cls(
            id=str(d["id"]),
            type=d.get("type", "body"),
            start=int(d["start"]),
            end=int(d["end"]),
            label=d.get("label", ""),
            name=d.get("name", ""),
            parent_id=d.get("parent_id"),
            source=d.get("source", "auto"),
            masked=d.get("masked"),
            metadata=dict(d.get("metadata") or {}),
        )


@dataclass
class LayoutConfig:
    sections: list[LayoutSection] = field(default_factory=list)
    mask_by_type: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_MASK_BY_TYPE))
    applied: bool = False
    # User-defined mask layers: [{"key", "label", "color", "default_mask"}].
    extra_types: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "mask_by_type": self.mask_by_type,
            "extra_types": self.extra_types,
            "sections": [s.to_dict() for s in self.sections],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LayoutConfig:
        mask = dict(DEFAULT_MASK_BY_TYPE)
        extra = list(d.get("extra_types", []))
        for et in extra:
            mask.setdefault(str(et["key"]), bool(et.get("default_mask", True)))
        mask.update(d.get("mask_by_type", {}))
        return cls(
            sections=[LayoutSection.from_dict(s) for s in d.get("sections", [])],
            mask_by_type=mask,
            applied=bool(d.get("applied", False)),
            extra_types=extra,
        )


def type_vocabulary(extra_types: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """The full mask-type vocabulary (builtin + custom) for the Step 2/4 UI."""
    vocab: list[dict[str, Any]] = [
        {
            "key": t,
            "label": SECTION_LABELS.get(t, t),
            "color": SECTION_COLORS.get(t, "#8e8e93"),
            "default_mask": DEFAULT_MASK_BY_TYPE.get(t, True),
            "builtin": True,
        }
        for t in SECTION_TYPES
    ]
    for et in extra_types or []:
        vocab.append({
            "key": str(et["key"]),
            "label": str(et.get("label", et["key"])),
            "color": str(et.get("color", "#8e8e93")),
            "default_mask": bool(et.get("default_mask", True)),
            "builtin": False,
        })
    return vocab


def sanitize_extra_types(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate custom mask layers: drop builtin/duplicate keys, normalize fields."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for et in raw:
        key = str(et.get("key", "")).strip()
        if not key or key in SECTION_TYPES or key in seen:
            continue
        seen.add(key)
        out.append({
            "key": key,
            "label": str(et.get("label", key)).strip()[:60] or key,
            "color": str(et.get("color", "#8e8e93")),
            "default_mask": bool(et.get("default_mask", True)),
        })
    return out


def layout_path(project_dir: Path) -> Path:
    return project_dir / "layout_sections.json"


def load_layout(project_dir: Path) -> LayoutConfig | None:
    p = layout_path(project_dir)
    if not p.exists():
        return None
    return LayoutConfig.from_dict(json.loads(p.read_text(encoding="utf-8")))


def save_layout(project_dir: Path, config: LayoutConfig) -> None:
    layout_path(project_dir).write_text(
        json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8",
    )


def effective_mask(section: LayoutSection, mask_by_type: dict[str, bool]) -> bool:
    if section.masked is not None:
        return section.masked
    return mask_by_type.get(section.type, True)


def masked_intervals(
    sections: list[LayoutSection], mask_by_type: dict[str, bool], text_len: int
) -> list[tuple[int, int]]:
    """Compute merged masked [start,end) intervals via the deepest-section-wins rule.

    For each elementary segment between section breakpoints, the most-specific
    (smallest-span) covering section decides masking. This is what makes a mask=no
    child *carve a window* through a mask=yes parent and vice versa: a mask=yes
    ``header`` nested in a mask=no ``chapter`` masks only the header's span.
    """
    valid = [s for s in sections if 0 <= s.start < s.end <= text_len]
    if not valid:
        return []

    points = sorted({0, text_len} | {s.start for s in valid} | {s.end for s in valid})
    raw: list[tuple[int, int]] = []
    for a, b in zip(points, points[1:]):
        if a >= b:
            continue
        covering = [s for s in valid if s.start <= a and s.end >= b]
        if not covering:
            continue  # uncovered text is part of the work → unmasked
        min_span = min(s.end - s.start for s in covering)
        # Most-specific section wins; ties broken by definition order (last).
        chosen = [s for s in covering if (s.end - s.start) == min_span][-1]
        if effective_mask(chosen, mask_by_type):
            raw.append((a, b))

    merged: list[tuple[int, int]] = []
    for s, e in raw:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def range_is_masked(intervals: list[tuple[int, int]], start: int, end: int) -> bool:
    """True if [start,end)'s midpoint falls inside a masked interval."""
    mid = (start + end) // 2
    for a, b in intervals:
        if a <= mid < b:
            return True
    return False


# ── Auto-detection (Step 2: "Detect") ─────────────────────────────────────────

# Headings come space-inconsistent across producers: "Chapter1", "Chapter 1",
# "CHAPTER I", bare "1"/"IV". Match an optional space then a roman/arabic numeral.
_CHAPTER_RE = re.compile(r"^(chapter\s*[ivxlcdm\d]|chap\.\s*\d|[ivxlcdm]+\.?$|\d+\.?$)", re.IGNORECASE)
_VOLUME_RE = re.compile(r"^(volume|vol\.)\s*[ivxlcdm\d]", re.IGNORECASE)
_PART_RE = re.compile(r"^part\s*[ivxlcdm\d]", re.IGNORECASE)
_BOOK_RE = re.compile(r"^book\s*[ivxlcdm\d]", re.IGNORECASE)

_TITLE_PAGE_RE = re.compile(r"title\s*page", re.IGNORECASE)
_COPYRIGHT_RE = re.compile(r"copyright|all rights reserved", re.IGNORECASE)
_CONTENTS_RE = re.compile(r"contents|sommaire|table des mati|índice|inhalt|indice", re.IGNORECASE)
_DEDICATION_RE = re.compile(r"dedicat", re.IGNORECASE)
_EPIGRAPH_RE = re.compile(r"epigraph", re.IGNORECASE)
_PREFACE_RE = re.compile(r"preface|préface|avant-propos", re.IGNORECASE)
_FOREWORD_RE = re.compile(r"fore-?word", re.IGNORECASE)
_INTRO_RE = re.compile(r"introduction|introductory|prologue", re.IGNORECASE)

_AFTERWORD_RE = re.compile(r"after-?word|epilogue|conclusion|postscript|elucidation", re.IGNORECASE)
_ACK_RE = re.compile(r"acknowledge?ment", re.IGNORECASE)
_ABOUT_AUTHOR_RE = re.compile(r"about the author|about the translator", re.IGNORECASE)
_DISCUSSION_RE = re.compile(r"discussion question|reading group|book club", re.IGNORECASE)
_GLOSSARY_RE = re.compile(r"glossary", re.IGNORECASE)
_INDEX_RE = re.compile(r"^index\b|^indices\b|^indexes\b", re.IGNORECASE)
_BIBLIO_RE = re.compile(r"bibliograph|works cited|references$", re.IGNORECASE)
_APPENDIX_RE = re.compile(r"appendix|appendices", re.IGNORECASE)
_ADDENDUM_RE = re.compile(r"addend", re.IGNORECASE)
_INSERT_RE = re.compile(r"^insert\b|illustrations?$|^plates?\b", re.IGNORECASE)


# A chapter heading carries a numeral and often a title: "Chapter IV.—The Reckoning",
# "Chapter 5: The Reckoning", "Chapter X - The Reckoning". Peel off the keyword, then
# the leading roman/arabic numeral (word-bounded so it can't bite into a title word),
# then a separator, leaving the title.
_HEAD_KEYWORD_RE = re.compile(r"^\s*(?:chapter|chap\.?|part|book|volume|vol\.?)\s*", re.IGNORECASE)
_LEADING_NUM_RE = re.compile(r"^\s*(\d+|[ivxlcdm]+)\b\.?", re.IGNORECASE)
_HEAD_SEP_RE = re.compile(r"^\s*[.\-—–:)]+\s*")
# "<Book> Chapter <N>" — scripture-style headings that name the book before the
# chapter (e.g. "Genesis Chapter 14", "1 Kings Chapter 5", "Psalms Chapter 119").
# End-anchored + a required trailing numeral so it can't fire on prose or on bare
# "Chapter N" / "The Final Chapter" literary headings.
_BOOK_CHAPTER_RE = re.compile(r"^(?P<book>.+?)\s+chapter\s+(?P<num>[ivxlcdm\d]+)\.?\s*$", re.IGNORECASE)


# Canonical scripture book names (Protestant 66 + Catholic deuterocanon + KJV/Douay
# spelling variants). Bare book-name headings ("GENESIS", "1 Corinthians") aren't
# structural by the generic regexes, so we match them against this lexicon — but only
# promote to 'book' when many appear together (a canon), never a lone novel chapter.
_BIBLE_BOOK_NAMES = frozenset({
    "genesis", "exodus", "leviticus", "numbers", "deuteronomy",
    "joshua", "josue", "judges", "ruth", "samuel", "kings", "chronicles", "paralipomenon",
    "ezra", "esdras", "nehemiah", "tobit", "tobias", "judith", "esther", "maccabees", "machabees",
    "job", "psalms", "psalm", "proverbs", "ecclesiastes", "canticle of canticles",
    "song of solomon", "song of songs", "wisdom", "sirach", "ecclesiasticus",
    "isaiah", "isaias", "jeremiah", "jeremias", "lamentations", "baruch", "ezekiel", "ezechiel",
    "daniel", "hosea", "osee", "joel", "amos", "obadiah", "abdias", "jonah", "jonas",
    "micah", "micheas", "nahum", "habakkuk", "habacuc", "zephaniah", "sophonias",
    "haggai", "aggeus", "zechariah", "zacharias", "malachi", "malachias",
    "matthew", "mark", "luke", "john", "acts", "romans", "corinthians", "galatians",
    "ephesians", "philippians", "colossians", "thessalonians", "timothy", "titus",
    "philemon", "hebrews", "james", "peter", "jude", "revelation", "apocalypse",
})
_BOOK_PREFIX_RE = re.compile(
    r"^(?:the\s+)?(?:book\s+of\s+|gospel\s+(?:according\s+to\s+)?(?:st\.?\s+)?|"
    r"epistle\s+(?:of\s+(?:st\.?\s+)?paul\s+)?to\s+the\s+|acts\s+of\s+the\s+|"
    r"prophe(?:cy|t)\s+of\s+)",
    re.IGNORECASE,
)
_BOOK_ORDINAL_RE = re.compile(r"^(?:(first|second|third|1st|2nd|3rd|iii|ii|i|[123])\s+)?(.+)$", re.IGNORECASE)
_ORDINAL_NUM = {"first": "1", "second": "2", "third": "3", "1st": "1", "2nd": "2",
                "3rd": "3", "i": "1", "ii": "2", "iii": "3", "1": "1", "2": "2", "3": "3"}
_MIN_BIBLE_BOOKS = 8  # gate: this many book-name matches ⇒ treat them as 'book' divisions


def _match_bible_book(heading: str) -> str | None:
    """Canonical display name if the heading is a scripture book, else None.

    Handles ordinals ("1 Corinthians", "Second Kings") and wrappers ("The Gospel
    According to St. Matthew", "The Book of Genesis").
    """
    core = re.sub(r"[.,:;]+$", "", heading.strip()).strip()
    core = _BOOK_PREFIX_RE.sub("", core)
    m = _BOOK_ORDINAL_RE.match(core.lower())
    if not m:
        return None
    ordinal, base = m.group(1), re.sub(r"\s+", " ", m.group(2).strip())
    if base not in _BIBLE_BOOK_NAMES:
        return None
    num = _ORDINAL_NUM.get(ordinal or "", "")
    name = base.title()
    return f"{num} {name}" if num else name


def _parse_chapter_heading(label: str) -> dict[str, str]:
    """Split a chapter heading into {book?, number?, name?}; all keys optional."""
    s = label.strip()
    bc = _BOOK_CHAPTER_RE.match(s)
    if bc:
        meta: dict[str, str] = {"number": bc.group("num")}
        book = bc.group("book").strip(" .—–-:")
        if book and book.lower() not in ("chapter", "chap", "chap."):
            meta["book"] = book
        return meta
    rest = _HEAD_KEYWORD_RE.sub("", s, count=1)
    meta = {}
    m = _LEADING_NUM_RE.match(rest)
    if m:
        meta["number"] = m.group(1)
        rest = _HEAD_SEP_RE.sub("", rest[m.end():], count=1)
    name = rest.strip(" .—–-:)")
    if name:
        meta["name"] = name
    return meta


def _chapter_label(meta: dict[str, str], fallback: str) -> str:
    """Display label for a heading-stripped chapter: book+num, title, "Chapter N", raw."""
    if meta.get("book") and meta.get("number"):
        return f"{meta['book']} {meta['number']}"
    if meta.get("name"):
        return meta["name"]
    if meta.get("number"):
        return f"Chapter {meta['number']}"
    return fallback or "Chapter"


def _classify_heading(heading: str) -> str | None:
    """Map a heading to a section type, or None if it isn't a recognizable boundary.

    Specific matter types are tested before the generic structural patterns so that,
    e.g., "Introduction" wins over the bare-numeral chapter fallback.
    """
    h = heading.strip()
    if not h:
        return None
    # "<Book> Chapter <N>" is unambiguously a scripture chapter — test first so a book
    # name can't be mistaken for a matter type.
    if _BOOK_CHAPTER_RE.match(h):
        return "chapter"
    # Front matter (specific first).
    if _TITLE_PAGE_RE.search(h):
        return "title_page"
    if _COPYRIGHT_RE.search(h):
        return "copyright"
    if _DEDICATION_RE.search(h):
        return "dedication"
    if _EPIGRAPH_RE.search(h):
        return "epigraph"
    if _CONTENTS_RE.search(h):
        return "contents"
    if _PREFACE_RE.search(h):
        return "preface"
    if _FOREWORD_RE.search(h):
        return "foreword"
    if _INTRO_RE.search(h):
        return "introduction"
    # Back matter.
    if _ACK_RE.search(h):
        return "acknowledgments"
    if _ABOUT_AUTHOR_RE.search(h):
        return "about_author"
    if _DISCUSSION_RE.search(h):
        return "discussion"
    if _GLOSSARY_RE.search(h):
        return "glossary"
    if _BIBLIO_RE.search(h):
        return "bibliography"
    if _INDEX_RE.search(h):
        return "index"
    if _APPENDIX_RE.search(h):
        return "appendix"
    if _ADDENDUM_RE.search(h):
        return "addendum"
    if _INSERT_RE.search(h):
        return "insert"
    if _AFTERWORD_RE.search(h):
        return "afterword"
    # Structural (generic).
    if _VOLUME_RE.search(h):
        return "volume"
    if _PART_RE.search(h):
        return "part"
    if _BOOK_RE.search(h):
        return "book"
    if _CHAPTER_RE.search(h):
        return "chapter"
    return None


def _compute_parents(sections: list[LayoutSection]) -> None:
    """Set parent_id to the smallest strictly-containing section (in place)."""
    for s in sections:
        best: LayoutSection | None = None
        for t in sections:
            if t is s:
                continue
            if t.start <= s.start and t.end >= s.end and (t.end - t.start) > (s.end - s.start):
                if best is None or (t.end - t.start) < (best.end - best.start):
                    best = t
        s.parent_id = best.id if best else None


def _assign_names(sections: list[LayoutSection]) -> None:
    """Give every element a stable per-type name (chapter_1, contents_1, ...)."""
    counters: dict[str, int] = {}
    for s in sorted(sections, key=lambda x: (x.start, x.end)):
        counters[s.type] = counters.get(s.type, 0) + 1
        s.name = f"{s.type}_{counters[s.type]}"


_TOC_ENTRY_GAP = 240  # chars; a real division is far larger than a TOC line
_MIN_TOC_RUN = 3


def _suppress_toc_entries(
    items: list[tuple[int, int, str | None, str]],
    text_len: int,
) -> list[tuple[int, int, str | None, str]]:
    """Demote chapter-like boundaries that are really table-of-contents links (#6).

    Some EPUBs inline their TOC as one boundary per entry; each entry's heading
    ("Chapter 1", "Part II"…) would classify as a structural division, fragmenting
    the front matter and dragging the body start into the TOC. When a 'contents'
    boundary exists, a tightly-packed run of structural boundaries following it —
    each only a heading apart, and compact relative to the whole text — is treated
    as TOC links and demoted to type=None. The compactness gate keeps genuine
    micro-chapter books (whose short chapters span the whole work) untouched.
    """
    if not any(it[2] == "contents" for it in items):
        return items
    out = list(items)
    n = len(out)
    # A real TOC is a small fraction of the whole text; a genuine micro-chapter
    # book's run spans most of it. Gate on the RATIO, not an absolute ceiling —
    # otherwise a dense TOC in a long novel (large absolute span) escapes.
    span_cap = int(text_len * 0.12)
    for ci in range(n):
        if out[ci][2] != "contents":
            continue
        i = ci + 1
        if i >= n or out[i][2] not in _STRUCTURAL:
            continue
        # Build the cluster by spacing from the previous *cluster member* so the last
        # TOC link is captured even though the first real division sits far after it.
        run = [i]
        i += 1
        while i < n and out[i][2] in _STRUCTURAL and out[i][0] - out[run[-1]][0] <= _TOC_ENTRY_GAP:
            run.append(i)
            i += 1
        if len(run) >= _MIN_TOC_RUN and out[run[-1]][0] - out[run[0]][0] <= span_cap:
            for j in run:
                s, he, _, lbl = out[j]
                out[j] = (s, he, None, lbl)
    return out


def _sublabel_frontmatter(
    text: str,
    body_start: int,
    has_type: set[str],
    leading_claimed: bool,
    add: Callable[[str, int, int, str], None],
) -> None:
    """Sub-label headingless front matter (copyright / title page) by content (#7).

    EPUBs often render the copyright and title pages with no heading, so they land
    in the undifferentiated front-matter run. A light content scan over [0,
    body_start) recovers them: the paragraph block containing a copyright marker
    becomes a 'copyright' element, and a short leading block becomes 'title_page'.
    ``leading_claimed`` is True when a detected subtype already starts at offset 0
    (e.g. a foreword), in which case the title-page guess is suppressed so it can't
    mask the opening of that section.
    """
    if body_start <= 0:
        return
    region = text[:body_start]
    if "copyright" not in has_type:
        m = _COPYRIGHT_RE.search(region)
        if m:
            lo = region.rfind("\n\n", 0, m.start())
            lo = 0 if lo < 0 else lo + 2
            hi = region.find("\n\n", m.end())
            hi = body_start if hi < 0 else hi
            add("copyright", lo, min(hi, body_start), "Copyright")
    if "title_page" not in has_type and not leading_claimed:
        hi = region.find("\n\n")
        hi = body_start if hi < 0 else hi
        if 0 < hi <= 600:
            add("title_page", 0, hi, "Title Page")


def detect_layout_sections(
    boundaries: list[tuple[int, int, str]],
    text_len: int,
    endnote_separator: int = -1,
    text: str | None = None,
) -> list[LayoutSection]:
    """Classify raw section boundaries into typed, nested, named layout sections.

    ``boundaries`` is a list of (start, head_end, heading) from the EPUB section
    track or the segmenter, where ``head_end`` bounds the heading-label text. The
    text is tiled into a front-matter run, an analyzable ``body`` foundation, and a
    back-matter run; structural sections nest inside the body and each one's heading
    label is carved out as a masked ``header`` window.
    """
    bounds = sorted(boundaries, key=lambda b: b[0])
    body_end = endnote_separator if 0 < endnote_separator < text_len else text_len

    # Classify every in-range boundary, keeping unrecognized ones (type=None) because
    # they still mark where a region ends even though they create no section.
    items: list[tuple[int, int, str | None, str]] = []  # (start, head_end, type, label)
    for start, end, heading in bounds:
        if start < 0 or start >= body_end:
            continue
        t = _classify_heading(heading)
        head_end = max(start, min(int(end), body_end))
        items.append((int(start), head_end, t, " ".join(heading.split())[:120]))
    items.sort(key=lambda x: x[0])
    items = _suppress_toc_entries(items, text_len)  # #6 — drop inlined TOC links

    # Scripture book divisions: bare book-name headings ("GENESIS", "1 Corinthians")
    # match no structural regex. When a canon's worth of them appears, promote the
    # unclassified ones to 'book'. The count gate keeps a lone novel chapter named
    # after a book (e.g. "Genesis") from being misread as a structural division.
    book_hits = [i for i, it in enumerate(items) if it[2] is None and _match_bible_book(it[3])]
    if len(book_hits) >= _MIN_BIBLE_BOOKS:
        for i in book_hits:
            s, he, _, lbl = items[i]
            items[i] = (s, he, "book", lbl)

    classified = [it for it in items if it[2] is not None]

    # Body begins at the first structural division if the work has any; otherwise
    # after the leading run of front-matter boundaries (so a chapterless epistolary
    # work still gets an analyzable body instead of being masked end to end).
    structural_starts = [it[0] for it in items if it[2] in _STRUCTURAL]
    if structural_starts:
        body_start = min(structural_starts)
    else:
        body_start = 0
        for it in items:
            if it[2] in _FRONTMATTER:
                continue
            body_start = it[0]
            break
        else:
            # Every boundary was front matter → body begins after the last one.
            body_start = items[-1][0] if items else 0

    # Back-matter region: the maximal trailing run of *classified* boundaries that are
    # all back-matter. Unrecognized boundaries (in-world documents inside the work) are
    # ignored here so they cannot swallow the body.
    backmatter_start = body_end
    for start, _, t, _ in reversed(classified):
        if t in _BACKMATTER and start > body_start:
            backmatter_start = start
        else:
            break

    sections: list[LayoutSection] = []
    next_id = 0

    def add(
        type_: str, start: int, end: int, label: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        nonlocal next_id
        if end <= start:
            return
        next_id += 1
        sections.append(LayoutSection(
            id=f"ls-{next_id}", type=type_, start=start, end=end,
            label=label or SECTION_LABELS.get(type_, type_), source="auto",
            metadata=dict(metadata or {}),
        ))

    # ── Foundation layer: front matter, body, back matter. ──
    add("front_matter", 0, body_start, "Front Matter")
    add("body", body_start, backmatter_start, "Body")
    add("back_matter", backmatter_start, body_end, "Back Matter")
    if 0 < endnote_separator < text_len:
        add("endnotes", endnote_separator, text_len, "Endnotes")

    # ── Front-matter subtypes (each spans heading → next boundary, clipped). ──
    fm = [it for it in items if it[0] < body_start]
    for i, (start, _, t, lbl) in enumerate(fm):
        if t is None:
            continue
        end = body_start
        for nstart, _, _, _ in fm[i + 1:]:
            if nstart > start:
                end = min(nstart, body_start)
                break
        add(t, start, end, lbl)

    # #7 — recover headingless copyright / title pages by content scan.
    if text is not None:
        fm_types = {s.type for s in sections if s.start < body_start}
        leading_claimed = any(
            s.start == 0 and s.type not in ("front_matter", "body") for s in sections
        )
        _sublabel_frontmatter(text, body_start, fm_types, leading_claimed, add)

    # ── Back-matter subtypes. ──
    bm = [it for it in items if it[0] >= backmatter_start]
    for i, (start, _, t, lbl) in enumerate(bm):
        if t is None:
            continue
        end = body_end
        for nstart, _, _, _ in bm[i + 1:]:
            if nstart > start:
                end = min(nstart, body_end)
                break
        add(t, start, end, lbl)

    # ── Inside the body: structural nav (mask=no) + carved windows. ──
    body_items = [it for it in items if body_start <= it[0] < backmatter_start]
    for i, (start, head_end, t, lbl) in enumerate(body_items):
        if t is None:
            continue
        if t in _STRUCTURAL:
            level = _TYPE_LEVEL.get(t, 3)
            end = backmatter_start
            for nstart, _, nt, _ in body_items[i + 1:]:
                if nstart <= start:
                    continue
                nlevel = _TYPE_LEVEL.get(nt, 99) if nt in _STRUCTURAL else 99
                if nt in _STRUCTURAL and nlevel <= level:
                    end = min(nstart, backmatter_start)
                    break
            # Carve the heading label out of the structural body as a masked window.
            # Cap the span so a segmenter fallback (whose boundary end is a section
            # end, not a heading end) can't mask an entire chapter as a "header".
            carve = start < head_end <= start + _MAX_HEADER_LEN and head_end <= end
            meta: dict[str, str] | None = None
            if t == "chapter":
                meta = _parse_chapter_heading(lbl)
            elif t == "book":
                bk = _match_bible_book(lbl)
                meta = {"book": bk} if bk else None
            if t == "chapter" and carve and head_end < end:
                # The heading line ("Chapter IV.—The Reckoning") becomes its own masked
                # header; the chapter element starts after it and stores number/title.
                add("chapter", head_end, end, _chapter_label(meta or {}, lbl), metadata=meta)
                add("header", start, head_end, lbl)
            else:
                add(t, start, end, lbl, metadata=meta)
                if carve:
                    add("header", start, head_end, lbl)
        elif t in _EDITORIAL:
            # Mid-body editorial matter (introductory notes, elucidations) → masked
            # window spanning to the next body boundary.
            end = backmatter_start
            for nstart, _, _, _ in body_items[i + 1:]:
                if nstart > start:
                    end = min(nstart, backmatter_start)
                    break
            add(t, start, end, lbl)

    sections.sort(key=lambda s: (s.start, -(s.end - s.start)))
    _compute_parents(sections)
    _assign_names(sections)
    return sections
