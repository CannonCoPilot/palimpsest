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

import heapq
import json
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The fixed section vocabulary, grouped by role. Custom user types may extend this
# at runtime (they are tolerated everywhere; only the default mask differs).
SECTION_TYPES: tuple[str, ...] = (
    # Foundation — these tile the whole work in the fewest elements.
    "body",
    # Structural / navigational containers nested inside the body. `section` is a
    # per-chapter container (heading + verse content + notes) — the structural span a
    # `chapter` (verse content only, post inline-note carve) now sits inside. `verse` is
    # the finest grain: one element per verse / scripture paragraph, nested in `chapter`.
    "volume", "book", "part", "section", "chapter", "verse", "letter",
    # Verse-form authorial content (poems, songs) carried inside the body.
    "poetry",
    # Masked windows carved inside the body. `header` = a name line (book / chapter / section
    # title); `heading` = the editorial argument / summary / explanation that follows a header
    # (often numbered, so it mimics verses) — distinct from the verse/body text it precedes.
    # `chapter_heading` is the legacy combined name+argument span (kept for other works).
    "header", "heading", "chapter_heading", "footnotes", "endnotes", "epigraph",
    # Translation of a subject text the work is written about (scripture in a study
    # bible, a quoted-source rendering, parallel-version columns).
    "translation",
    # Commentary: a modern scholar's analysis/introduction of a translated source text
    # in an anthology — distinct from a front-matter introduction, analyzable by default,
    # independently toggleable against the translation it accompanies.
    "commentary",
    # Front-matter region + subtypes.
    "front_matter", "title_page", "copyright", "contents",
    "dedication", "foreword", "preface", "introduction",
    # Back-matter region + subtypes.
    "back_matter", "afterword", "acknowledgments", "about_author",
    "discussion", "glossary", "index", "bibliography",
    "appendix", "addendum", "insert",
    # Production note at the very end of a work.
    "colophon",
)

SECTION_LABELS: dict[str, str] = {
    "body": "Body",
    "volume": "Volume", "book": "Book", "part": "Part", "section": "Section",
    "chapter": "Chapter", "verse": "Verse", "letter": "Letter", "poetry": "Poetry",
    "header": "Header", "heading": "Heading", "chapter_heading": "Chapter Heading",
    "footnotes": "Footnotes", "endnotes": "Endnotes",
    "epigraph": "Epigraph", "translation": "Translation", "commentary": "Commentary",
    "front_matter": "Front Matter", "title_page": "Title Page", "copyright": "Copyright",
    "contents": "Contents", "dedication": "Dedication", "foreword": "Foreword",
    "preface": "Preface", "introduction": "Introduction",
    "back_matter": "Back Matter", "afterword": "Afterword",
    "acknowledgments": "Acknowledgments", "about_author": "About the Author",
    "discussion": "Discussion Questions", "glossary": "Glossary", "index": "Index",
    "bibliography": "Bibliography", "appendix": "Appendix", "addendum": "Addendum",
    "insert": "Insert", "colophon": "Colophon",
}

# The analyzable work text: body and its structural nav containers are unmasked, as is
# scholarly commentary (the author's own writing) and verse-form content; everything else
# (matter, headers, editorial summaries, notes, the translated source text) is masked by default.
_UNMASKED_TYPES = frozenset({
    "body", "volume", "book", "part", "section", "chapter", "verse", "letter", "commentary", "poetry",
})
DEFAULT_MASK_BY_TYPE: dict[str, bool] = {t: t not in _UNMASKED_TYPES for t in SECTION_TYPES}

# Palette by sub-group so hue signals relatedness within a Browser group. No displayed
# mask-type is grey/black — grey/black is reserved for the `sections` *analysis* track
# (frontend trackColors), distinct from the `section` mask-type here. The non-rendered
# `body` root keeps a neutral grey.
#   Structure: nesting containers + name-marker (volume→book→section, then `header`) = blue
#              family · front matter = red→pink · appendix/glossary = purple · other back
#              matter / supplementary = cyan.
#   Content:   `chapter` main text = green · editorial intros (preface/introduction) = orange ·
#              `heading` argument = gold · notes (foot/endnotes) = yellow · specialty = own hue.
SECTION_COLORS: dict[str, str] = {
    "body": "#98989d",
    # nesting containers + name-marker — blue family. `section` and `header` get two
    # distinct blues (azure / sky), sitting just below volume·book·part in the ramp.
    "volume": "#5e5ce6", "book": "#0a84ff", "part": "#409cff",
    "section": "#32ade6", "header": "#64d2ff",
    # front matter — red → pink
    "front_matter": "#ff453a", "title_page": "#ff6482", "contents": "#ff7ab6",
    "copyright": "#ff8fab", "dedication": "#ff80c0", "foreword": "#ff9f7a",
    # appendix & glossary — two purple hues (stand out from the cyan back-matter family)
    "appendix": "#bf5af2", "glossary": "#af52de",
    # other back matter / supplementary / reference — cyan
    "back_matter": "#48b0e0", "index": "#70d7ff", "bibliography": "#48b0e0",
    "addendum": "#5ac8fa", "insert": "#48b0e0", "afterword": "#48b0e0",
    "acknowledgments": "#70d7ff", "about_author": "#5ac8fa", "colophon": "#3aa0d0",
    # content main text — green; `verse` (finest grain) a lighter green tint of `chapter`;
    # verse-form specialties get their own hue
    "chapter": "#30d158", "verse": "#6fdc8c", "letter": "#40c8a0", "poetry": "#9d8df1",
    "translation": "#d68cff", "commentary": "#30b0c7",
    # editorial argument / summary — gold; epigraph brown
    "heading": "#c9a227", "chapter_heading": "#c9a227", "epigraph": "#ac8e68",
    # notes — yellow
    "footnotes": "#ffd60a", "endnotes": "#ffca28",
    # editorial intros — orange
    "preface": "#ff9f0a", "introduction": "#ffb340", "discussion": "#ff7a45",
}

# Structural nesting depth: body(0) > volume > book/part > chapter. A section of
# level L extends until the next boundary whose level is <= L, which yields containment.
_TYPE_LEVEL: dict[str, int] = {"body": 0, "volume": 1, "book": 2, "part": 2, "section": 3, "chapter": 4, "verse": 5}

# Type roles for region detection.
_STRUCTURAL = frozenset({"volume", "book", "part", "chapter"})
_FRONTMATTER = frozenset({
    "front_matter", "title_page", "copyright", "contents",
    "dedication", "foreword", "preface", "introduction", "epigraph",
})
_BACKMATTER = frozenset({
    "back_matter", "afterword", "acknowledgments", "about_author", "discussion",
    "glossary", "index", "bibliography", "appendix", "addendum", "insert", "endnotes",
})
# Mid-body editorial matter that carves a masked window where it appears.
_EDITORIAL = frozenset({"foreword", "preface", "introduction", "afterword", "epigraph"})
# Scholarly-anthology layers: a translated source text and the commentary around it. Each
# marker spans to the next marker (commentary: work header → "Translation"; translation:
# "Translation" → next work).
_SCHOLARLY = frozenset({"translation", "commentary"})

# A heading label is short; cap the carved header window so a coarse boundary source
# can't mask an entire section.
_MAX_HEADER_LEN = 300

# Back matter is a *contiguous* trailing run (glossary→index→appendix, abutting). A
# back-matter-typed boundary separated from the trailing cluster by more than this much
# text sits across a body span — e.g. a "Note on the Text" or "Illustrations" apparatus
# printed ahead of a heading-less narrative — and must not drag the region forward across
# the work. The threshold scales with length (floor for short works).
_BACKMATTER_GAP_FLOOR = 40000
_BACKMATTER_GAP_FRAC = 0.05

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
    masked: bool | None = None     # None = inherit; bool = hard override (wins over mask_as)
    # Mask this section as if it were another type, while keeping its structural `type`. Lets a
    # `chapter` of translated ancient text follow the `translation` toggle (hide/show as a
    # layer) without losing its chapter structure (number, name, nesting). None = mask by type.
    mask_as: str | None = None
    # Structured heading data, e.g. a chapter's {"number": "IV", "name": "The Reckoning"}.
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "type": self.type, "start": self.start, "end": self.end,
            "label": self.label, "name": self.name, "parent_id": self.parent_id,
            "source": self.source, "masked": self.masked, "mask_as": self.mask_as,
            "metadata": self.metadata,
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
            mask_as=d.get("mask_as"),
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
    return mask_by_type.get(section.mask_as or section.type, True)


def masked_intervals(
    sections: list[LayoutSection],
    mask_by_type: dict[str, bool],
    text_len: int,
    extra_masked: list[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """Compute merged masked [start,end) intervals via the deepest-section-wins rule,
    then union in any active *interval mask-layers* (``extra_masked``).

    For each elementary segment between section breakpoints, the most-specific
    (smallest-span) covering section decides masking. This is what makes a mask=no
    child *carve a window* through a mask=yes parent and vice versa: a mask=yes
    ``header`` nested in a mask=no ``chapter`` masks only the header's span.

    ``extra_masked`` is the union of any enabled interval mask-layers — flat, disjoint
    spans masked *categorically* rather than structurally (e.g. the verse-number layer:
    every "C:V." token). They are unioned in directly, so a dense layer (tens of thousands
    of verse-number tokens) never enters the O(n·breakpoints) deepest-wins sweep and the
    cost stays bounded. With ``extra_masked=None`` the result is byte-identical to the
    pure structural masking.

    ``verse`` elements (the verse *text*, if any were ever passed as sections) are skipped:
    they are unmasked and nested inside the (also unmasked) ``chapter`` content, so they can
    never change the masked set.
    """
    valid = [s for s in sections if s.type != "verse" and 0 <= s.start < s.end <= text_len]
    raw: list[tuple[int, int]] = []
    if valid:
        # Sweep the breakpoints left→right, keeping a heap of sections that have opened but
        # not yet closed. For each elementary segment [a,b) the covering section that decides
        # masking is the deepest (smallest span); ties go to the last-defined (highest index
        # in `valid`) — so the heap is keyed (span, -index) and already-closed entries are
        # lazily discarded from the top. This is O(N log N) vs. the prior O(N²) per-segment
        # rescan, and is byte-identical to it.
        starts_at: dict[int, list[int]] = defaultdict(list)
        for i, s in enumerate(valid):
            starts_at[s.start].append(i)
        points = sorted({0, text_len} | {s.start for s in valid} | {s.end for s in valid})
        heap: list[tuple[int, int, int, int]] = []  # (span, -index, end, index)
        for a, b in zip(points, points[1:]):
            for i in starts_at.get(a, ()):
                s = valid[i]
                heapq.heappush(heap, (s.end - s.start, -i, s.end, i))
            while heap and heap[0][2] <= a:  # section closed at/before a → no longer covering
                heapq.heappop(heap)
            if heap and effective_mask(valid[heap[0][3]], mask_by_type):
                raw.append((a, b))

    if extra_masked:
        raw.extend((a, b) for (a, b) in extra_masked if 0 <= a < b <= text_len)
    raw.sort()

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
_CHAPTER_RE = re.compile(
    r"^(chapter\s*[ivxlcdm\d]|chap\.\s*\d|cap[ií]tulo\b|[ivxlcdm]+\.?$|\d+\.?$)", re.IGNORECASE
)
# An explicit "Chapter <N>" / "Chap. <N>" keyword PREFIX (the numbered form, not a bare
# numeral) is an unambiguous chapter opening even when its title carries a matter word
# ("Chapter XXV — Conclusion", "Chapter 8. Appendix"): the keyword+number wins over the
# matter-type regexes, which would otherwise mis-type it from the trailing word.
_EXPLICIT_CHAPTER_RE = re.compile(r"^\s*(?:chapter|chap\.)\s*[ivxlcdm\d]", re.IGNORECASE)
# A bare Roman-numeral heading ("I", "XIV"). A real one stands alone on its line; when the
# same letters are really the capital first letter of a word the EPUB nav split mid-token
# ("I"+"lustración", "XV"+"III tomó"), so a bare-Roman chapter whose boundary cuts a word is
# a mis-split, not a division.
_BARE_ROMAN_RE = re.compile(r"^[ivxlcdm]+\.?$", re.IGNORECASE)
_VOLUME_RE = re.compile(r"^(volume|volumen|vol\.|tomo)\s*[ivxlcdm\d]", re.IGNORECASE)
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
_INDEX_RE = re.compile(
    r"^index\b|^indices\b|^indexes\b"
    # A manuscript catalogue/list is an index-type back-matter apparatus (e.g. the Dead
    # Sea Scrolls' "List of the Manuscripts from Qumran").
    r"|^(?:list|catalogue|catalog|index) of (?:the )?(?:manuscripts|mss)\b",
    re.IGNORECASE,
)
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

# Translated-source anthology template (e.g. NT Apocrypha): each ancient work opens with a
# scholar's work header ("A new translation and introduction") that begins the commentary,
# then a bare "Translation" heading that begins the rendered subject text, running to the
# next work. The opener is matched EXACTLY so a pericope title like "The martyrdom and
# translation of Barnabas" can't be mistaken for one.
_TRANSLATION_HEAD_RE = re.compile(r"^translations?$", re.IGNORECASE)
_WORK_HEADER_RE = re.compile(
    r"^(?:(?:a\s+)?(?:new\s+)?translation\s+and\s+introduction"
    r"|introduction\s+and\s+translation)$",
    re.IGNORECASE,
)
_MIN_SCHOLARLY_WORKS = 3  # this many "Translation" headings ⇒ a repeating anthology template

# Line-anchored variants for a heading-INDEPENDENT text scan. Some EPUBs flatten the
# per-work headers into inline body text with no structural heading track (e.g. MNTA
# Vol. 3), so the structural pass finds zero markers and the whole anthology collapses
# into one body blob. Recover the same template directly from the text. A standalone
# "Translation" line and a "(A new) translation and introduction[ by …]" line are
# template-specific enough not to fire in running prose, and the repetition gate
# (_MIN_SCHOLARLY_WORKS of each) blocks stray matches.
_TRANSLATION_HEAD_LINE_RE = re.compile(r"(?m)^[ \t]*translations?[ \t]*$", re.IGNORECASE)
_WORK_HEADER_LINE_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:a\s+)?(?:new\s+)?translation\s+and\s+introduction"
    r"|introduction\s+and\s+translation)(?:\s+by\b[^\n]*)?[ \t]*$",
    re.IGNORECASE,
)

# Attribution-delimited translation anthology (e.g. the Nag Hammadi Library): scholarly
# front matter is followed by many translated ancient works, each opening with a
# "Translated by <Name>" attribution line and NO per-work commentary. A run of these
# (>= _MIN_ATTRIB_WORKS) marks a translation anthology; each attribution begins a
# translation region running to the next. A translated novel's lone title-page credit
# stays below the gate, so it cannot fire on ordinary prose.
_TRANSLATED_BY_LINE_RE = re.compile(r"(?im)^[ \t]*translated by\s+\w[^\n]*$")
_MIN_ATTRIB_WORKS = 8

# Siglum-delimited translation corpus (e.g. the Dead Sea Scrolls): the translated texts
# carry no verse numbers and no per-work attribution, but each scroll opens with a Qumran
# siglum header (cave number + Q + designation: 1QS, 4Q521, 11QTa). Dense runs of these
# mark the translated corpus, distinct from the sparse siglum mentions in the scholarly
# introduction and from the very dense manuscript catalog/index (excluded by a density cap).
_QUMRAN_SIGLUM_RE = re.compile(r"(?im)^[ \t]*(?:[1-9]|1[01])Q[A-Za-z0-9]+\b")
_SIGLUM_RUN_MIN = 5           # clustered sigla ⇒ a scroll corpus, not a stray ref
_SIGLUM_RUN_GAP = 12000       # a gap larger than this (chars) ends a corpus run
_SIGLUM_MAX_DENSITY = 1.5     # sigla/1000c above which a run is a catalog, not prose

# Inline chapter recovery: some EPUBs expose only work-level headings (or none) and carry
# their chapter divisions as plain line-anchored body text ("Chapter I.—Exhortation to the
# Heathen", "CHAPTER XV"). When the structural track is sparse but such lines repeat, recover
# them as the chapter track so the work segments instead of collapsing into one body blob.
# The "Chapter"/"Chap." keyword plus a roman/arabic number is required, so a prose mention of
# the word "chapter" (never line-anchored before a numeral) cannot fire. An optional wrapping
# "[" is allowed so a bracketed heading style ("[Chapter 18]", used by some multi-book scripture
# volumes for one book's chapters) is recovered alongside the bare form.
_CHAPTER_LINE_RE = re.compile(r"(?im)^[ \t]*\[?(?:chapter|chap\.)[ \t]+(?:[ivxlcdm]+|\d+)\b[^\n]*$")
_MIN_CHAPTER_RECOVERY = 5  # this many inline ^Chapter lines ⇒ recover them as the chapter track

# Numbered+named scripture divisions named in English with the original name parenthesised on
# the FOLLOWING line ("2. The Cow\n\n( Al-Baqarah)") — the Quran's surahs. The next-line paren
# distinguishes a real division opening from an inline table-of-contents entry (paren on the
# SAME line) and from a numbered verse or note (no parenthetical at all), so the divisions
# segment but the TOC and verses do not. Gated on a Quran-scale count.
_DIVISION_HEAD_RE = re.compile(
    r"(?m)^[^\w\n]{0,8}\d{1,3}\.[ \t]+[A-Z][^\n(]{1,40}?[ \t]*\n+\([ \t]*[A-Z]"
)
_MIN_NAMED_DIVISIONS = 20  # this many numbered+named divisions ⇒ a structured scripture (Quran)

# Ordinal-worded scripture divisions: some editions head each division with an English
# ordinal WORD instead of a digit ("THE FIRST SŪRAH", "THE SECOND SŪRAH", … — Asad's
# Qur'an), with the division's name on the following line. The ordinal carries no numeral
# so the digit-based chapter pass can't see them; the divisions appear in order, so the
# sequence position is the number. The line must END right after the keyword, which keeps
# the page-numbered contents listing ("THE FIRST SŪRAH 1") out.
_ORDINAL_DIVISION_RE = re.compile(
    r"(?m)^[ \t]*THE[ \t]+[A-Z][A-Z \t\-]{2,40}?[ \t]+S[UŪ]RAH[ \t\r]*$"
)

# Versed scripture printed as "chapter. verse." on a chapter's opening line ("1.   1. The
# words…" — R.H. Charles' Book of Enoch). Only the first verse of each chapter is line-
# anchored (later verses run inline), so each line-anchored chapter.verse pair opens a new
# chapter; the chapter number is the first group. The REQUIRED inner verse number is what
# separates a chapter opening from an editorial numbered note ("1. His desire…").
_VERSED_CHAPTER_RE = re.compile(r"(?m)^[ \t]*(\d{1,3})\.[ \t ]+\d{1,3}\.(?=[ \t ])")
_MIN_VERSED_CHAPTERS = 20  # this many chapter.verse openings ⇒ versed scripture, not stray lists

# A scripture verse marker opening a section: a "chapter:verse" reference ("13:51") or the
# bare verse number that opens the verse body ("54 then the priest…"), as in Friedman's
# Commentary on the Torah. Some EPUB nav anchors land one digit into such a marker and expose
# only a 1-char heading window, so the carved boundary splits the number mid-token. Used to
# find the whole marker straddling a boundary so the header can be snapped to span it.
_VERSE_NUM_HEAD_RE = re.compile(r"\d{1,3}(?::\d{1,3})?")

# Inline scripture-book recovery: some EPUBs (the Book of Mormon) expose no book-level
# heading track and carry their books as upper-case line-anchored "THE [ordinal] BOOK OF
# <NAME>" headings, across which chapter numbering restarts ("CHAPTER I" recurs once per
# book). When several repeat, recover them as the book track so each per-book chapter run
# nests under a disambiguating book. Upper-case (no re.I) plus the "BOOK OF" anchor keeps
# ordinary prose mentions and a modern intro's title ("The Meaning of the Book of Mormon
# Today") out; the leading "THE" is optional because some books print bare ("BOOK OF ETHER").
_BOOK_HEAD_RE = re.compile(
    r"(?m)^[ \t]*(?:THE[ \t]+)?(?:(?:FIRST|SECOND|THIRD|FOURTH)[ \t]+)?BOOK[ \t]+OF[ \t]+[A-Z]"
)
_MIN_BOOK_RECOVERY = 8  # this many upper-case "BOOK OF <Name>" lines ⇒ recover a book track

# Trailing numbered endnote/footnote list: an annotated edition prints its notes as a run of
# bare numerals each alone on a line, incrementing 1, 2, 3, … with the note text between them
# (Robinson Crusoe's glossary, Infinite Jest's endnotes). A lone such numeral in a sparse
# heading track is otherwise mis-read as a body "chapter" — and, sitting at the tail, drags the
# whole work into front matter. The bare-numeral-ALONE line (no following text on the line)
# distinguishes it from a verse ("1 In the beginning") or a "Chapter 1" heading.
_ENDNOTE_NUM_LINE_RE = re.compile(r"(?m)^[ \t]*(\d{1,4})[ \t]*$")
_MIN_ENDNOTE_RUN = 8       # this many incrementing bare numerals ⇒ a notes list
_ENDNOTE_RUN_GAP = 6000    # chars; a larger gap between consecutive numbers ends the run

# Table-of-contents cross-reference recovery: an edition whose chapters carry descriptive,
# non-"Chapter N" titles ("I Go to Sea", "The Journal" — Robinson Crusoe) exposes no chapter
# heading track and matches no chapter regex. But its leading contents block lists those titles,
# and each reappears verbatim as a body heading. Matching the two — a title listed in the
# contents AND repeating as its own line later — recovers the sections that no local rule could.
_TOC_ENTRY_LINE_RE = re.compile(r"(?m)^[ \t]*(\S[^\n]*?)[ \t]*$")
_TOC_LINE_MAX = 80      # a contents entry is a short line; longer ⇒ body prose ends the block
_MIN_TOC_HEADINGS = 5   # matched contents→body headings ⇒ recover them as the section track
_TOC_SCAN_LIMIT = 20000  # chars; the contents block sits near the head — bound the scan


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
# A "Scripture Index" / "Index of Ancient Sources" lists each book name followed by a dense
# run of verse:page citations ("Genesis 1 127, 301, 386 1:1 127, 128 …"). Those book-name
# headings match the canon lexicon but open an INDEX, not the book itself; their content is
# dominated by reference digits where real scripture prose is not.
_INDEX_DIGIT_FRACTION = 0.15  # book-name entry whose content is ≥15% digits ⇒ a citation index
_MIN_INDEX_SHARE = 0.6        # this share of book-hits index-like ⇒ the run is a scripture index
_INDEX_TRAILING_START = 0.80  # the index run begins this far into the document (back matter)
_INDEX_MAX_SPAN_FRAC = 0.15   # and is compact — a real canon's books span the whole work


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


def _book_hits_are_scripture_index(
    items: list[tuple[int, int, str | None, str]],
    book_hits: list[int],
    text: str,
    body_end: int,
    text_len: int,
) -> bool:
    """True when book-name boundaries open a scripture INDEX, not a canon of books.

    A scripture index ("Index of Ancient Sources") is a compact run of book-name
    entries in the back matter, each followed by dense verse:page citations
    ("Genesis 1 127, 301 1:1 128 …"). Three signals together separate it from a real
    canon (whose books span the whole work) and from a head nav/TOC cluster (whose
    book names sit at the front, often with chapter-number strips that are also
    digit-dense): the run begins deep in the document, spans only a small fraction of
    it, and a majority of its entries are citation-dense.
    """
    first = items[book_hits[0]][0]
    last = items[book_hits[-1]][0]
    if first < _INDEX_TRAILING_START * text_len:
        return False
    if (last - first) > _INDEX_MAX_SPAN_FRAC * text_len:
        return False
    starts = sorted(it[0] for it in items)
    index_like = 0
    for i in book_hits:
        s = items[i][0]
        nxt = [x for x in starts if x > s]
        end = min(nxt) if nxt else body_end
        seg = text[s:min(end, s + 2000)]  # judge by the entry head — cheap and stable
        if seg and sum(c.isdigit() for c in seg) / len(seg) >= _INDEX_DIGIT_FRACTION:
            index_like += 1
    return index_like >= _MIN_INDEX_SHARE * len(book_hits)


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
    had_keyword = rest != s
    meta = {}
    m = _LEADING_NUM_RE.match(rest)
    if m:
        after = rest[m.end():]
        # Accept the leading numeral as the chapter number only when a keyword introduced it
        # ("Chapter IV"), a separator delimits it (the match itself ate a trailing dot — "1." —
        # or a separator follows — "IV—Title", "1)"), or it stands alone ("I"). A bare numeral
        # running straight into title words ("I Go to Sea" — the narrator pronoun) is part of
        # the descriptive title, not a number.
        if (had_keyword or not after.strip() or m.group(0).rstrip().endswith(".")
                or _HEAD_SEP_RE.match(after)):
            meta["number"] = m.group(1)
            rest = _HEAD_SEP_RE.sub("", after, count=1)
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
    # An explicit "Chapter <N>" keyword prefix wins over the matter types below, so a
    # chapter whose title happens to contain a matter word ("Chapter XXV — Conclusion")
    # stays a chapter rather than being mis-typed afterword/appendix/introduction.
    if _EXPLICIT_CHAPTER_RE.match(h):
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


def _suppress_misanchored_head_toc(
    items: list[tuple[int, int, str | None, str]],
    text_len: int,
) -> list[tuple[int, int, str | None, str]]:
    """Demote a misanchored front contents cluster that lacks a 'Contents' heading.

    Some EPUBs (Nyland's Complete Books of Enoch) anchor every chapter nav link to one front
    contents fragment instead of the body, so a compact run of 'chapter' boundaries with
    JUMBLED numbers (8, 9, 1) sits at the document head and drags the body start into the TOC.
    A genuine opening run is monotonic (1, 2, 3) and spread far apart, so the gate is narrow: a
    compact head run (each within _TOC_ENTRY_GAP) of >= _MIN_TOC_RUN chapters whose Arabic
    numbers are not strictly increasing. The real divisions recur at their body offsets (here
    recovered by the inline chapter scan), so dropping the duplicated TOC links is safe. This is
    the no-'Contents'-heading counterpart to _suppress_toc_entries.
    """
    out = list(items)
    first = next((i for i, it in enumerate(out) if it[2] in _STRUCTURAL), None)
    if first is None or out[first][0] > text_len * 0.05:
        return out
    run = [first]
    j = first + 1
    while j < len(out):
        nxt = out[j]
        if nxt[2] not in _STRUCTURAL or nxt[0] - out[run[-1]][0] > _TOC_ENTRY_GAP:
            break
        run.append(j)
        j += 1
    if len(run) < _MIN_TOC_RUN or any(out[k][2] != "chapter" for k in run):
        return out
    nums: list[int] = []
    for k in run:
        num = _parse_chapter_heading(out[k][3]).get("number")
        if num is None or not num.isdigit():
            return out
        nums.append(int(num))
    if all(a < b for a, b in zip(nums, nums[1:])):  # strictly increasing = a real opening run
        return out
    for k in run:
        s, he, _, lbl = out[k]
        out[k] = (s, he, None, lbl)
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


# A scripture verse line looks like "1 In the beginning…": a 1–3 digit verse number
# (Psalm 119, the longest chapter, has 176 verses) then whitespace then verse prose.
# A colon ("8:1." study note) or period ("1." outline entry) right after the digits
# breaks the match, and a book name ("1 Samuel") is too short to anchor a run — so
# only genuine verse lines qualify. (A period form is deliberately NOT matched: it is
# indistinguishable from numbered editorial notes — "1. His desire…" — which would then
# false-mask as translation, e.g. Pilgrim's Progress annotations and endnotes.)
_VERSE_LINE_RE = re.compile(r"(?m)^(\d{1,3})[ \t]+[\"'(A-Za-z]")
_VERSE_RUN_MIN = 4        # verse lines needed before a cluster counts as scripture
_VERSE_RUN_GAP = 1600     # verse starts farther apart than this belong to separate runs
_MIN_VERSE_LINE_LEN = 22  # shorter "<num> Word" lines are book names / chapter nav, not verses
_VERSE_SEQ_MIN = 0.5      # fraction of steps that must increment (or reset a chapter)
_VERSE_BODY_MAX_FRACTION = 0.85  # above this share of the body, the work is all scripture
_VERSE_BODY_MIN_FRACTION = 0.05  # below this share, verse-numbered lines are incidental
                                 # (editorial endnotes, ordered lists), not scripture


def detect_verse_regions(text: str, lo: int = 0, hi: int | None = None) -> list[tuple[int, int]]:
    """Find contiguous runs of scripture verses in ``text[lo:hi]`` as (start, end) spans.

    Locates the verse-dense passages of an annotated scripture work — a study bible's
    biblical text as distinct from its surrounding commentary — by clustering
    verse-numbered lines. Detection is purely content-based, so it is independent of
    the work's heading structure (robust even when headings are mislocated) and finds
    nothing in ordinary prose, which has no verse-numbered lines. Two guards keep
    non-scripture out: a length floor drops digit-prefixed book names ("1 Samuel") and
    chapter-nav entries that cluster inside a table of contents, and a sequence check
    requires the verse numbers to mostly count up (or reset for a new chapter), which
    rejects apparatus tables of arbitrary numbers (weights and measures, genealogies).
    """
    hi = len(text) if hi is None else hi
    marks: list[tuple[int, int]] = []  # (line start, verse number)
    for m in _VERSE_LINE_RE.finditer(text):
        s = m.start()
        if not (lo <= s < hi):
            continue
        eol = text.find("\n", s)
        if (hi if eol < 0 else eol) - s >= _MIN_VERSE_LINE_LEN:
            marks.append((s, int(m.group(1))))
    regions: list[tuple[int, int]] = []

    def flush(run: list[tuple[int, int]]) -> None:
        if len(run) < _VERSE_RUN_MIN:
            return
        nums = [n for _, n in run]
        # A scripture-like step counts up by one, or is a genuine chapter reset (a real
        # verse number dropping back to a chapter's first verse). Arbitrary number
        # tables (weights, genealogies) satisfy neither and fail the threshold.
        ok = sum(b == a + 1 or (a >= 5 and b <= 2) for a, b in zip(nums, nums[1:]))
        if ok / (len(nums) - 1) < _VERSE_SEQ_MIN:
            return
        end = text.find("\n\n", run[-1][0])
        regions.append((run[0][0], hi if end < 0 else min(end, hi)))

    run: list[tuple[int, int]] = []
    for mk in marks:
        if run and mk[0] - run[-1][0] > _VERSE_RUN_GAP:
            flush(run)
            run = []
        run.append(mk)
    flush(run)
    return regions


def detect_scholarly_markers(
    text: str, lo: int, hi: int
) -> list[tuple[int, int, str, str]]:
    """Find inline anthology markers in ``text[lo:hi]`` as body-item tuples.

    Content-based counterpart to the structural anthology pass: locates the
    line-anchored work-header ("A new translation and introduction") and bare
    "Translation" lines that some EPUBs carry as plain body text rather than as
    headings. Returns (start, line_end, type, label) tuples — type 'commentary' for
    a work header, 'translation' for a Translation line — sorted by position, so the
    body loop can carve the alternating layers exactly as it does for real headings.
    """
    marks: list[tuple[int, int, str, str]] = []
    for m in _WORK_HEADER_LINE_RE.finditer(text):
        if lo <= m.start() < hi:
            marks.append((m.start(), m.end(), "commentary", " ".join(m.group().split())[:120]))
    for m in _TRANSLATION_HEAD_LINE_RE.finditer(text):
        if lo <= m.start() < hi:
            marks.append((m.start(), m.end(), "translation", "Translation"))
    marks.sort(key=lambda x: x[0])
    return marks


def _line_before(text: str, pos: int) -> tuple[int, int, str] | None:
    """The non-empty line immediately preceding ``pos`` as (start, end, stripped_text)."""
    end = pos
    while end > 0 and text[end - 1] in "\r\n":
        end -= 1
    if end <= 0:
        return None
    start = text.rfind("\n", 0, end) + 1
    line = text[start:end].strip()
    return (start, end, line) if line else None


def detect_anthology_title_works(
    text: str, lo: int, hi: int
) -> list[tuple[int, int, str, str]]:
    """Commentary/translation layers for an anthology with no "Translation" divider.

    Some scholarly anthologies (the Eerdmans *Old Testament Pseudepigrapha*) lay each
    work out as ``<Title>`` / "A new translation and introduction by <Name>" / intro /
    Bibliography / ``<Title>`` (repeated) / the translation — there is no bare
    "Translation" heading, so :func:`detect_scholarly_markers` finds only the work
    headers. The work title recurs as a standalone line after the bibliography to open
    the rendered text, so the commentary runs from the title to that recurrence and the
    translation from the recurrence to the next work. Returns (start, end, type, label)
    markers; only emitted when the repeated-title template holds for enough works.
    """
    headers = [m.start() for m in _WORK_HEADER_LINE_RE.finditer(text) if lo <= m.start() < hi]
    if len(headers) < _MIN_SCHOLARLY_WORKS:
        return []
    bounds = headers + [hi]
    marks: list[tuple[int, int, str, str]] = []
    for k, h in enumerate(headers):
        nxt = bounds[k + 1]
        tb = _line_before(text, h)
        if tb is None:
            continue
        tstart, tend, title = tb
        if not (4 <= len(title) <= 80):
            continue
        marks.append((tstart, tend, "commentary", title[:_MAX_HEADER_LEN]))
        # The translation opens where the title recurs as its own line after the intro.
        # Search past a small offset so the work's own Contents listing isn't mistaken
        # for it, and take the last such recurrence (the rendered text follows the
        # apparatus, which the title never re-heads).
        pat = re.compile(r"(?m)^[ \t]*" + re.escape(title) + r"[ \t]*$")
        rec_start = -1
        rec_end = -1
        for rm in pat.finditer(text, tend + 200, nxt):
            rec_start, rec_end = rm.start(), rm.end()
        if rec_start >= 0:
            marks.append((rec_start, rec_end, "translation", "Translation"))
    marks.sort(key=lambda x: x[0])
    return marks


def detect_chapter_markers(
    text: str, lo: int, hi: int
) -> list[tuple[int, int, str, str]]:
    """Find inline chapter headings in ``text[lo:hi]`` as body-item tuples.

    Content-based counterpart to the structural chapter pass: some EPUBs expose only
    work-level headings (or none) and carry their chapter divisions as line-anchored
    body text ("Chapter I.—Exhortation to the Heathen"). Returns (start, line_end,
    'chapter', label) tuples so the body loop carves each into a masked header window
    and a numbered chapter exactly as it does for real heading-track chapters.
    """
    marks: list[tuple[int, int, str, str]] = []
    for m in _CHAPTER_LINE_RE.finditer(text):
        if lo <= m.start() < hi:
            label = " ".join(m.group().split())[:_MAX_HEADER_LEN]
            if label.startswith("["):
                # Drop the wrapping brackets ("[Chapter 18]") so the keyword/number parse.
                label = label[1:].replace("]", "", 1)
            marks.append((m.start(), m.end(), "chapter", label))
    return marks


def detect_division_markers(
    text: str, lo: int, hi: int
) -> list[tuple[int, int, str, str]]:
    """Find Quran-style numbered+named scripture divisions as body-item tuples.

    A surah opens with its number and English name, then its transliterated name in
    parentheses on the next line ("2. The Cow\\n\\n( Al-Baqarah)"). Returns (start,
    line_end, 'chapter', label) tuples — label is the "N. Name" heading line — so the
    body loop carves each division into a masked header and a numbered chapter. The
    next-line parenthetical keeps the inline contents listing and plain verses out.
    """
    marks: list[tuple[int, int, str, str]] = []
    for m in _DIVISION_HEAD_RE.finditer(text):
        if lo <= m.start() < hi:
            eol = text.find("\n", m.start())
            head_end = eol if eol > m.start() else m.end()
            label = " ".join(text[m.start():head_end].split())[:_MAX_HEADER_LEN]
            marks.append((m.start(), head_end, "chapter", label))
    return marks


def detect_ordinal_division_markers(
    text: str, lo: int, hi: int
) -> list[tuple[int, int, str, str]]:
    """Find ordinal-worded scripture divisions (Asad's Qur'an surahs) as body items.

    Each surah is headed by an English ordinal word ("THE FIRST SŪRAH") with its name on
    the following line ("Al-Fātiḥah(The Opening)"). The ordinal carries no numeral, so the
    structural chapter pass can't see it; the divisions appear in order, so the sequence
    position supplies the number and the name line supplies the title. Returns (start,
    line_end, 'chapter', "N. Name") tuples so the body loop carves a header + numbered
    chapter exactly as for a digit-headed division.
    """
    marks: list[tuple[int, int, str, str]] = []
    n = 0
    for m in _ORDINAL_DIVISION_RE.finditer(text):
        if not (lo <= m.start() < hi):
            continue
        n += 1
        eol = text.find("\n", m.start())
        head_end = eol if eol > m.start() else m.end()
        # The surah name is the next non-empty line; the "<...> Period" line that may
        # follow the name is editorial, not the title, so it is not used as the name.
        j = head_end
        while j < len(text) and text[j] in "\r\n":
            j += 1
        keol = text.find("\n", j)
        if keol < 0:
            keol = len(text)
        cand = " ".join(text[j:keol].split())
        name = cand if cand and not cand.lower().endswith("period") else ""
        label = f"{n}. {name}".strip() if name else f"{n}."
        marks.append((m.start(), head_end, "chapter", label[:_MAX_HEADER_LEN]))
    return marks


def detect_versed_chapter_markers(
    text: str, lo: int, hi: int
) -> list[tuple[int, int, str, str]]:
    """Find chapter openings in versed scripture printed as "chapter. verse." as body items.

    Content-based counterpart to the chapter pass for an edition (R.H. Charles' Book of
    Enoch) whose EPUB exposes no chapter headings and prints each chapter's opening as
    "<chapter>. <verse>. <text>" with only the first verse line-anchored. The chapter
    number is the first group; the header window is just the "N." chapter-number prefix so
    the verse text stays in the analyzable chapter body. The required inner verse number
    keeps an editorial numbered note ("1. His desire…") from being read as a chapter.
    """
    marks: list[tuple[int, int, str, str]] = []
    for m in _VERSED_CHAPTER_RE.finditer(text):
        if not (lo <= m.start() < hi):
            continue
        num = m.group(1)
        head_end = m.end(1) + 1  # through the chapter number's trailing dot
        marks.append((m.start(1), head_end, "chapter", f"Chapter {num}"))
    return marks


def detect_book_markers(
    text: str, lo: int, hi: int
) -> list[tuple[int, int, str, str]]:
    """Find inline scripture-book headings in ``text[lo:hi]`` as body-item 'book' tuples.

    Content-based counterpart to the chapter pass for an edition (the Book of Mormon) whose
    EPUB exposes no book-level heading track: its 15 books — across which chapter numbering
    restarts, so "CHAPTER I" recurs once per book — sit inline as upper-case "THE [ordinal]
    BOOK OF <NAME>" lines. Returns (start, line_end, 'book', label) tuples so the body loop
    nests each per-book chapter run under a disambiguating book exactly as for a heading-track
    book. The upper-case, line-anchored ``BOOK OF`` form keeps prose mentions and a modern
    introduction's title out.
    """
    marks: list[tuple[int, int, str, str]] = []
    for m in _BOOK_HEAD_RE.finditer(text):
        if lo <= m.start() < hi:
            eol = text.find("\n", m.start())
            head_end = eol if eol > m.start() else m.end()
            label = " ".join(text[m.start():head_end].split())[:_MAX_HEADER_LEN]
            marks.append((m.start(), head_end, "book", label))
    return marks


def detect_endnote_list(text: str, lo: int, hi: int) -> int:
    """Start offset of a trailing numbered endnote/footnote list in ``text[lo:hi]``, else -1.

    A run of bare-numeral lines incrementing 1, 2, 3, … (the note text on the lines between)
    in the trailing portion of the work is its endnotes/notes glossary. Returned so the caller
    can bound it as back matter — keeping a lone such numeral in a sparse heading track from
    being mis-read as a body chapter (and, at the tail, dragging the whole work into front
    matter). Gated on a low start (the list begins near note 1), a dense incrementing run, and
    a trailing position, so an in-body numbered list cannot trip it.
    """
    span = hi - lo
    if span <= 0:
        return -1
    marks = [(m.start(), int(m.group(1)))
             for m in _ENDNOTE_NUM_LINE_RE.finditer(text) if lo <= m.start() < hi]
    i = 0
    while i < len(marks):
        j = i
        while (j + 1 < len(marks) and marks[j + 1][1] == marks[j][1] + 1
               and marks[j + 1][0] - marks[j][0] <= _ENDNOTE_RUN_GAP):
            j += 1
        if (j - i + 1 >= _MIN_ENDNOTE_RUN and marks[i][1] <= 3
                and marks[i][0] - lo > span * 0.5):
            return marks[i][0]
        i = j + 1
    return -1


def detect_toc_headings(text: str, body_end: int) -> list[tuple[int, int, str, str]]:
    """Recover sections by matching a leading contents block to repeated body headings.

    Some editions title their chapters descriptively ("I Go to Sea", "The Journal") rather than
    "Chapter N", so no regex recognizes them and the EPUB exposes no heading track. Their leading
    table of contents, however, lists each title, and each reappears verbatim as a standalone
    body line. This finds the contents block (a leading run of short lines), then for each entry
    locates its later line-anchored occurrence — typing it via ``_classify_heading`` (so a listed
    "Introduction"/"Afterword" lands as front/back matter) and defaulting an unrecognized repeated
    title to ``chapter``. Returns (start, head_end, type, label) markers, or [] below the gate.
    """
    head = text[:min(max(1, body_end), _TOC_SCAN_LIMIT)]
    toc: list[str] = []
    toc_end = 0
    for m in _TOC_ENTRY_LINE_RE.finditer(head):
        line = m.group(1).strip()
        if not line:
            continue
        if len(line) <= _TOC_LINE_MAX:
            toc.append(line)
            toc_end = m.end()
        elif len(toc) >= _MIN_TOC_HEADINGS:
            break  # the contents block ends where body prose begins
        else:
            toc = []  # the short run before this long line wasn't the contents
            toc_end = m.end()
    if len(toc) < _MIN_TOC_HEADINGS:
        return []

    marks: list[tuple[int, int, str, str]] = []
    seen: set[str] = set()
    for title in toc:
        if title in seen:
            continue
        seen.add(title)
        typ = _classify_heading(title)
        # A listed chapter title is a substantial multi-word phrase; skip tiny fragments
        # so an opening run of short narrative lines isn't mistaken for a contents block.
        # Recognized matter headings (Introduction, Afterword) are kept regardless.
        if typ is None and (len(title) < 8 or " " not in title):
            continue
        pos = text.find("\n" + title + "\n", toc_end)
        if pos < 0 or pos + 1 >= body_end:
            continue
        start = pos + 1
        marks.append((start, start + len(title), typ or "chapter", title))
    marks.sort(key=lambda x: x[0])
    # Require enough chapter-typed matches so a couple of stray repeated lines can't trip it.
    if sum(1 for m in marks if m[2] == "chapter") < _MIN_TOC_HEADINGS:
        return []
    return marks


def _drop_toc_chapter_runs(
    marks: list[tuple[int, int, str, str]], text_len: int
) -> list[tuple[int, int, str, str]]:
    """Drop inlined table-of-contents runs from recovered chapter markers.

    A compact run of >= ``_MIN_TOC_RUN`` markers each within ``_TOC_ENTRY_GAP`` of the
    previous is a bare "Chapter I. / Chapter II. …" contents listing, not body chapters
    (which are separated by their body text). The span cap (a TOC is a small fraction of
    the work) keeps a genuine micro-chapter book, whose short chapters span the whole
    text, from being mistaken for a TOC. Counterpart to ``_suppress_toc_entries`` for
    markers recovered by content scan, which carry no adjacent 'contents' boundary.
    """
    span_cap = int(text_len * 0.12)
    keep = [True] * len(marks)
    i = 0
    while i < len(marks):
        j = i
        while j + 1 < len(marks) and marks[j + 1][0] - marks[j][0] <= _TOC_ENTRY_GAP:
            j += 1
        if j - i + 1 >= _MIN_TOC_RUN and marks[j][0] - marks[i][0] <= span_cap:
            for k in range(i, j + 1):
                keep[k] = False
        i = j + 1
    return [m for m, k in zip(marks, keep) if k]


def detect_siglum_regions(text: str, lo: int, hi: int) -> list[tuple[int, int]]:
    """Find runs of Qumran-siglum-headed scrolls in ``text[lo:hi]`` as (start, end) spans.

    Content-based counterpart to ``detect_verse_regions`` for a translated manuscript
    corpus (the Dead Sea Scrolls) whose works are headed by sigla (1QS, 4Q521, 11QTa)
    rather than verses or attributions. Sigla are clustered into runs; a run shorter than
    ``_SIGLUM_RUN_MIN`` is a stray reference (the scholarly introduction mentions a few),
    and a run denser than ``_SIGLUM_MAX_DENSITY`` is a manuscript catalog/index rather than
    translated prose — both are rejected, leaving the translated scrolls.
    """
    marks = [m.start() for m in _QUMRAN_SIGLUM_RE.finditer(text) if lo <= m.start() < hi]
    # Cluster sigla into runs; a gap larger than the threshold ends a run.
    runs: list[list[int]] = []
    run: list[int] = []
    for p in marks:
        if run and p - run[-1] > _SIGLUM_RUN_GAP:
            runs.append(run)
            run = []
        run.append(p)
    if run:
        runs.append(run)

    # Keep substantial runs (drop short stray-reference clusters like the few sigla the
    # scholarly introduction cites).
    runs_info: list[tuple[int, int, float]] = []  # (start, end, density)
    for r in runs:
        if len(r) < _SIGLUM_RUN_MIN:
            continue
        end = text.find("\n\n", r[-1])
        end = hi if end < 0 else min(end, hi)
        runs_info.append((r[0], end, len(r) / max(1, (end - r[0]) / 1000)))
    if not runs_info:
        return []
    # The translated scrolls run contiguously: inter-run gaps are long single scrolls, and
    # some genres (parallel liturgical manuscripts) cite sigla densely mid-corpus, so mask
    # one span from the first corpus siglum onward. A very dense *trailing* run still inside
    # the range is an un-stripped manuscript catalog — end the span at its start; otherwise
    # the corpus runs contiguously to the back matter, so extend to the range end (covering
    # a final scroll like the Copper Scroll that drops its sigla for column markers).
    last = runs_info[-1]
    end = last[0] if (len(runs_info) > 1 and last[2] > _SIGLUM_MAX_DENSITY) else hi
    return [(runs_info[0][0], end)]


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
    items = _suppress_misanchored_head_toc(items, text_len)  # drop a misanchored front TOC cluster

    # Mis-split Roman headings: some EPUB nav entries land inside a word, so the capital
    # first letter of a token ("Ilustración", "siglo XVIII", "Christ-cross-row") is exposed
    # as a bare-Roman "chapter". A real Roman heading (including a treatise's numbered
    # fragment run "I", "II", "III") abuts whitespace; demote only one whose boundary (start
    # or label end) falls between two alphanumerics — it split a word, so it is not a heading.
    if text is not None:
        n_text = len(text)

        def _splits_word(s: int, he: int) -> bool:
            start_mid = 0 < s < n_text and text[s - 1].isalnum() and text[s].isalnum()
            end_mid = 0 < he < n_text and text[he - 1].isalnum() and text[he].isalnum()
            return start_mid or end_mid

        # Versed-scripture nav anchors: some EPUB section breaks land *inside* a verse marker —
        # a "chapter:verse" reference ("13:52") or the bare verse number opening the verse body
        # ("54 then…") — and expose a 1-char heading window, so the carved boundary splits the
        # number mid-token ("1"|"3:52", "5"|"4"). When a chapter boundary that splits a word sits
        # within such a marker, snap it to span the whole marker: the header becomes the clean
        # verse marker and the previous chapter ends — and this one's body begins — on the
        # marker's word edges. Gated on an actual split, so clean anchors stay put.
        def _verse_marker_around(s: int) -> tuple[int, int] | None:
            for m in _VERSE_NUM_HEAD_RE.finditer(text, max(0, s - 6), min(s + 8, body_end)):
                if m.start() <= s <= m.end():
                    return (m.start(), m.end())
            return None

        snapped: list[tuple[int, int, str | None, str]] = []
        for s, he, t, lbl in items:
            if t == "chapter" and _splits_word(s, he):
                ref = _verse_marker_around(s)
                if ref is not None and not _splits_word(*ref):
                    s, he = ref
            snapped.append((s, he, t, lbl))
        items = snapped

        items = [
            (s, he, None, lbl)
            if t == "chapter" and _BARE_ROMAN_RE.match(lbl.strip()) and _splits_word(s, he)
            else (s, he, t, lbl)
            for (s, he, t, lbl) in items
        ]

    # Scripture book divisions: bare book-name headings ("GENESIS", "1 Corinthians")
    # match no structural regex. When a canon's worth of them appears, promote the
    # unclassified ones to 'book'. The count gate keeps a lone novel chapter named
    # after a book (e.g. "Genesis") from being misread as a structural division.
    book_hits = [i for i, it in enumerate(items) if it[2] is None and _match_bible_book(it[3])]
    if len(book_hits) >= _MIN_BIBLE_BOOKS:
        if text is not None and _book_hits_are_scripture_index(
            items, book_hits, text, body_end, text_len
        ):
            # A trailing scripture index (book name + citations), not a canon: type the run's
            # first entry as a single back-matter `index` spanning the rest, and drop the other
            # book-name boundaries so the index neither anchors the body nor offers the body_start
            # fallback a landing spot inside itself.
            first = book_hits[0]
            s, he, _, lbl = items[first]
            items[first] = (s, he, "index", lbl)
            drop = set(book_hits[1:])
            items = [it for j, it in enumerate(items) if j not in drop]
        else:
            for i in book_hits:
                s, he, _, lbl = items[i]
                items[i] = (s, he, "book", lbl)

    # Heading-independent chapter recovery: when the EPUB exposes (almost) no chapter-level
    # structure but the body carries a dense run of line-anchored "Chapter N" headings as
    # plain text (e.g. the Global Grey / Schaff Ante-Nicene editions), recover them as chapter
    # items BEFORE body_start is derived, so the body begins at the first recovered chapter
    # instead of collapsing the early works into front matter. Runs after book promotion so a
    # Bible's books count toward the gate; gated on a sparse structural track (standard
    # chaptered works and scripture keep their existing structure untouched) and a repeating
    # run; _drop_toc_chapter_runs strips any inlined "Chapter I. / II. …" contents listing.
    anthology_body_start: int | None = None  # set when a title-template anthology is recovered
    if text is not None:
        n_struct = sum(1 for it in items if it[2] in _STRUCTURAL)
        if n_struct < _MIN_CHAPTER_RECOVERY:
            recovered: list[tuple[int, int, str, str]] = []
            # Versed scripture ("<chapter>. <verse>. …") is a stronger, more specific
            # signal than a loose "Chapter N" scan: when a chapter.verse run is present it
            # is the chapter track, and the loose scan — which would also catch stray prose
            # mentions of chapter numbers (an intro discussing "Chapter 108") — is skipped
            # so those mentions don't become spurious chapters.
            vcmarks = detect_versed_chapter_markers(text, 0, body_end)
            if len(vcmarks) >= _MIN_VERSED_CHAPTERS:
                recovered += vcmarks
            else:
                cmarks_raw = detect_chapter_markers(text, 0, body_end)
                bmarks_raw = detect_book_markers(text, 0, body_end)
                if len(bmarks_raw) >= _MIN_BOOK_RECOVERY:
                    # A contents listing interleaves each book with its chapter entries,
                    # so the book markers alone aren't adjacent; drop inlined-TOC runs over
                    # the merged book+chapter stream so the whole listing drops as one
                    # compact run, leaving the real body divisions (separated by their text).
                    merged = _drop_toc_chapter_runs(
                        sorted(cmarks_raw + bmarks_raw, key=lambda m: m[0]), text_len
                    )
                    bmarks = [m for m in merged if m[2] == "book"]
                    cmarks = [m for m in merged if m[2] == "chapter"]
                    if len(bmarks) >= _MIN_BOOK_RECOVERY:
                        recovered += bmarks
                else:
                    cmarks = _drop_toc_chapter_runs(cmarks_raw, text_len)
                if len(cmarks) >= _MIN_CHAPTER_RECOVERY:
                    recovered += cmarks
            smarks = detect_division_markers(text, 0, body_end)
            if len(smarks) >= _MIN_NAMED_DIVISIONS:
                recovered += smarks
            omarks = detect_ordinal_division_markers(text, 0, body_end)
            if len(omarks) >= _MIN_NAMED_DIVISIONS:
                recovered += omarks
            # Last resort when no numbered/keyworded structure was found: an edition whose
            # chapters carry descriptive titles, recovered by matching the leading contents
            # block to the titles' repeated body occurrences. Skipped for a scholarly
            # translation anthology (handled as commentary/translation layers), so its work
            # titles aren't also recovered as a competing chapter track.
            if not recovered:
                smk = detect_scholarly_markers(text, 0, body_end)
                n_comm = sum(1 for m in smk if m[2] == "commentary")
                n_tran = sum(1 for m in smk if m[2] == "translation")
                is_scholarly = n_comm >= _MIN_SCHOLARLY_WORKS and n_tran >= _MIN_SCHOLARLY_WORKS
                if not is_scholarly and n_comm >= _MIN_SCHOLARLY_WORKS:
                    # Work headers but no "Translation" dividers (Eerdmans OT Pseudepigrapha):
                    # recover the missing translation boundary of each work from the repeated
                    # work title; the work headers themselves become the commentary layer via
                    # the body-loop reclassify pass. The first work anchors the body (the
                    # apparatus is body, not front matter), and a few stray chapter headings
                    # from one constituent work must neither drag body_start ahead of the
                    # anthology nor punch unmasked holes in a translation, so demote them.
                    tmarks = [m for m in detect_anthology_title_works(text, 0, body_end)
                              if m[2] == "translation"]
                    if len(tmarks) >= _MIN_SCHOLARLY_WORKS:
                        recovered += tmarks
                        items = [(s, he, None, lbl) if t == "chapter" else (s, he, t, lbl)
                                 for (s, he, t, lbl) in items]
                        anthology_body_start = min(m[0] for m in smk if m[2] == "commentary")
                        is_scholarly = True
                if not is_scholarly:
                    recovered += detect_toc_headings(text, body_end)
            if recovered:
                items.extend(recovered)
                items.sort(key=lambda x: x[0])

        # A trailing numbered endnote/notes list is back matter, not body chapters. Retype any
        # structural boundary inside it (a bare-numeral "chapter" that is really a note number)
        # so it neither anchors the body nor masks as a chapter, and add a marker bounding the
        # region when the track exposes none — so the notes stay out of the analyzable body.
        en_start = detect_endnote_list(text, 0, body_end)
        if 0 <= en_start < body_end:
            items = [(s, he, "endnotes" if (s >= en_start and t in _STRUCTURAL) else t, lbl)
                     for (s, he, t, lbl) in items]
            if not any(s == en_start for s, _, _, _ in items):
                items.append((en_start, en_start, "endnotes", "Endnotes"))
            items.sort(key=lambda x: x[0])

    classified = [it for it in items if it[2] is not None]

    # Body begins at the first structural division if the work has any; otherwise
    # after the leading run of front-matter boundaries (so a chapterless epistolary
    # work still gets an analyzable body instead of being masked end to end).
    structural_starts = [it[0] for it in items if it[2] in _STRUCTURAL]
    if anthology_body_start is not None:
        # A title-template anthology: the body is the run of constituent works, beginning
        # at the first work (its scholarly apparatus is the body, not front matter).
        body_start = anthology_body_start
    elif structural_starts:
        body_start = min(structural_starts)
    else:
        # Heading-less work: the body is the large unbroken text span. Apparatus
        # boundaries (title, contents, intro sub-heads, note-on-text) cluster closely
        # at the head, so the narrative begins at the first body-scale gap between
        # boundaries — placing body_start there keeps the leading apparatus masked as
        # front matter instead of analyzing it as body. When no such gap exists (a
        # short heading-less work, e.g. an epistolary novel), fall back to the first
        # non-front-matter boundary so the body stays analyzable end to end.
        large_gap = max(_BACKMATTER_GAP_FLOOR, int(text_len * _BACKMATTER_GAP_FRAC))
        gap_starts = [it[0] for it in items] + [body_end]
        body_start = -1
        for a, b in zip(gap_starts, gap_starts[1:]):
            if b - a >= large_gap:
                body_start = a
                break
        if body_start < 0:
            # The body begins at the first non-matter boundary. Trailing back-matter
            # boundaries (e.g. a tail endnote list) must be skipped too, so a work whose
            # only boundary is a trailing notes glossary keeps its narrative in the body
            # rather than collapsing it into front matter.
            body_start = 0
            for it in items:
                if it[2] in _FRONTMATTER or it[2] in _BACKMATTER:
                    continue
                body_start = it[0]
                break
            else:
                # Only matter boundaries exist → body is the span after the leading
                # front-matter run (a trailing back-matter run bounds it on the right).
                leading_fm = [it for it in items if it[2] in _FRONTMATTER]
                body_start = leading_fm[-1][1] if leading_fm else 0

    # Back-matter region: the maximal *contiguous* trailing run of classified
    # back-matter boundaries. Unrecognized boundaries (in-world documents inside the
    # work) are ignored here so they cannot swallow the body. Contiguity is enforced —
    # a back-matter boundary separated from the trailing cluster by a body-scale gap
    # (apparatus printed ahead of a heading-less narrative) ends the run.
    bm_max_gap = max(_BACKMATTER_GAP_FLOOR, int(text_len * _BACKMATTER_GAP_FRAC))
    backmatter_start = body_end
    for start, _, t, _ in reversed(classified):
        if t not in _BACKMATTER or start <= body_start:
            break
        if backmatter_start != body_end and backmatter_start - start > bm_max_gap:
            break
        backmatter_start = start

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

    # Translated-source anthology pass: when the "Translation"/work-header template repeats
    # (a real anthology, not a stray heading), reclassify those markers so the body loop
    # carves alternating commentary + translation layers. Work headers are otherwise caught
    # by the generic introduction regex; this overrides them. Gated on repetition so a lone
    # "Translation" heading can't mask everything after it.
    scholarly = (
        sum(_TRANSLATION_HEAD_RE.match(it[3].strip()) is not None for it in body_items)
        >= _MIN_SCHOLARLY_WORKS
    )
    if scholarly:
        for i, it in enumerate(body_items):
            lbl = it[3].strip()
            if _TRANSLATION_HEAD_RE.match(lbl):
                body_items[i] = (it[0], it[1], "translation", it[3])
            elif _WORK_HEADER_RE.match(lbl):
                body_items[i] = (it[0], it[1], "commentary", it[3])
    elif text is not None:
        # Heading-independent recovery: the EPUB lost its per-work heading track and
        # carries the template as inline body text. Require the full repeating template
        # (both marker kinds ≥ the gate) so a stray inline "Translation" can't trip it.
        tmarks = detect_scholarly_markers(text, body_start, backmatter_start)
        n_work = sum(1 for m in tmarks if m[2] == "commentary")
        n_trans = sum(1 for m in tmarks if m[2] == "translation")
        if n_work >= _MIN_SCHOLARLY_WORKS and n_trans >= _MIN_SCHOLARLY_WORKS:
            scholarly = True
            body_items.extend(tmarks)
            body_items.sort(key=lambda x: x[0])

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
        elif t in _SCHOLARLY:
            # Anthology layer: commentary (work header → next marker) or translation
            # ("Translation" → next marker). Each spans to the next scholarly marker, so a
            # work's commentary runs up to its "Translation" heading and the translation
            # runs up to the next work.
            end = backmatter_start
            for nstart, _, nt, _ in body_items[i + 1:]:
                if nstart > start and nt in _SCHOLARLY:
                    end = min(nstart, backmatter_start)
                    break
            add(t, start, end, "Translation" if t == "translation" else lbl)

    # Content-scan overlay: runs of scripture verses inside the body become
    # 'translation' windows (the biblical text of an annotated/study edition, as
    # distinct from the surrounding commentary). Heading-independent, so it works
    # even when the work's structural headings are absent or mislocated. The overlay
    # is meaningful only as a contrast: a work that is almost entirely verses is
    # mono-scriptural (a plain Bible), so the body itself is the scripture and an
    # overlay would just shadow the whole thing — suppress it there.
    if text is not None and not scholarly:
        vregions = detect_verse_regions(text, body_start, backmatter_start)
        body_span = max(1, backmatter_start - body_start)
        vfrac = sum(e - s for s, e in vregions) / body_span
        # The overlay marks scripture as distinct from surrounding commentary, so it is
        # meaningful only as a contrast. Suppress it when verse runs are a negligible
        # share of the work (incidental numbered lines — editorial endnotes, ordered
        # lists — that aren't scripture) or when they are nearly the whole body (a plain
        # mono-scriptural Bible, where the body already *is* the scripture).
        if _VERSE_BODY_MIN_FRACTION <= vfrac <= _VERSE_BODY_MAX_FRACTION:
            for vstart, vend in vregions:
                add("translation", vstart, vend, "Scripture")

    # Content-scan overlay #2: an attribution-delimited translation anthology whose works
    # carry no verse density and no per-work heading track (e.g. the Nag Hammadi Library),
    # only a "Translated by <Name>" line per work. When many appear, each attribution opens
    # a translation region running to the next (the last to the back matter), masking the
    # translated ancient texts while the scholarly front matter stays analyzable. Scans the
    # whole text, not just the body, because such editions misplace body_start (tractates
    # begin before the first structural division). Suppressed for verse/heading anthologies,
    # which are already carved above.
    if text is not None and not scholarly:
        attribs = [m.start() for m in _TRANSLATED_BY_LINE_RE.finditer(text)
                   if m.start() < backmatter_start]
        if len(attribs) >= _MIN_ATTRIB_WORKS:
            edges = attribs + [backmatter_start]
            for a, b in zip(edges, edges[1:]):
                add("translation", a, min(b, backmatter_start), "Translation")

    # Content-scan overlay #3: a Qumran-siglum-delimited translation corpus (the Dead Sea
    # Scrolls), whose translated scrolls have neither verse numbers nor attribution lines.
    # Dense runs of scroll sigla become translation regions; the sparse scholarly intro and
    # the dense manuscript catalog are rejected inside detect_siglum_regions.
    if text is not None and not scholarly:
        for sstart, send in detect_siglum_regions(text, body_start, backmatter_start):
            add("translation", sstart, send, "Translation")

    # Structural translation edition (Fix B): in a scholarly edition of translated ancient
    # works, the ancient text — carried by the chapter structure — is masked as `translation`
    # so an analyst can hide or show it as a layer, while each chapter keeps its structure
    # (number, name, nesting) and the modern apparatus stays analyzable. Realized via `mask_as`
    # so it composes with deepest-section-wins: the chapter both nests and masks. Gated on
    # unambiguous patristic signposts — an existing per-work "Translation" attribution, or a run
    # of "Elucidation" editorial afterwords — so it never fires on a novel or a study Bible
    # (whose scripture overlay is labelled "Scripture", not "Translation").
    if text is not None and not scholarly:
        has_attribution = any(
            s.type == "translation" and s.label == "Translation" for s in sections
        )
        elucidations = sum(
            1 for s in sections
            if s.type == "afterword" and "elucidation" in s.label.lower()
        )
        if has_attribution or elucidations >= 3:
            for sec in sections:
                if sec.type == "chapter" and body_start <= sec.start < backmatter_start:
                    sec.mask_as = "translation"

    sections.sort(key=lambda s: (s.start, -(s.end - s.start)))
    _compute_parents(sections)
    _assign_names(sections)
    return sections
