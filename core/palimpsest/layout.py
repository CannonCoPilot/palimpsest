"""Publication-layout sections and masking for the staged import pipeline.

A *layout section* is a typed, optionally-nested character range over reference.txt
(title page, chapter, endnotes, ...). Each type carries a mask flag; masked ranges
are excluded from downstream analysis. Masking resolves by the *deepest section wins*
rule: a character's effective mask is taken from the most-specific (smallest-span)
section covering it, so a chapter (mask=no) nested inside a book (mask=yes) keeps its
prose analyzable while the book's own front matter stays masked. Uncovered text is
unmasked.

Persisted per project as ``layout_sections.json``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The fixed, user-facing section vocabulary (Step 3 "add new section" menu).
SECTION_TYPES: tuple[str, ...] = (
    "title_page", "front_matter", "contents", "index",
    "foreword", "afterword", "chapter", "volume", "book",
    "header", "footnotes", "endnotes",
)

SECTION_LABELS: dict[str, str] = {
    "title_page": "Title Page", "front_matter": "Front Matter", "contents": "Contents",
    "index": "Index", "foreword": "Foreword", "afterword": "Afterword",
    "chapter": "Chapter", "volume": "Volume", "book": "Book",
    "header": "Header", "footnotes": "Footnotes", "endnotes": "Endnotes",
}

# Default mask=yes for everything except chapter text (the analyzable core).
DEFAULT_MASK_BY_TYPE: dict[str, bool] = {t: True for t in SECTION_TYPES}
DEFAULT_MASK_BY_TYPE["chapter"] = False

SECTION_COLORS: dict[str, str] = {
    "chapter": "#30d158", "volume": "#5e5ce6", "book": "#0a84ff",
    "title_page": "#bf5af2", "front_matter": "#ff453a", "contents": "#ff6482",
    "index": "#8e8e93", "foreword": "#ff9f0a", "afterword": "#ff9f0a",
    "header": "#636366", "footnotes": "#ffd60a", "endnotes": "#ffd60a",
}

# Structural nesting depth: work(0) > volume > book > chapter. A section of level L
# extends until the next boundary whose level is <= L, which yields containment.
_TYPE_LEVEL: dict[str, int] = {"volume": 1, "book": 2, "chapter": 3}

MASKED_TEXT_COLOR = "#f5f5f5"
MASKED_BG_COLOR = "#3a3a3d"


@dataclass
class LayoutSection:
    id: str
    type: str
    start: int
    end: int
    label: str = ""
    parent_id: str | None = None
    source: str = "auto"          # "auto" (detected) or "user" (added/edited)
    masked: bool | None = None     # None = inherit mask_by_type[type]; bool = override

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "type": self.type, "start": self.start, "end": self.end,
            "label": self.label, "parent_id": self.parent_id,
            "source": self.source, "masked": self.masked,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LayoutSection:
        return cls(
            id=str(d["id"]),
            type=d.get("type", "chapter"),
            start=int(d["start"]),
            end=int(d["end"]),
            label=d.get("label", ""),
            parent_id=d.get("parent_id"),
            source=d.get("source", "auto"),
            masked=d.get("masked"),
        )


@dataclass
class LayoutConfig:
    sections: list[LayoutSection] = field(default_factory=list)
    mask_by_type: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_MASK_BY_TYPE))
    applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "mask_by_type": self.mask_by_type,
            "sections": [s.to_dict() for s in self.sections],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LayoutConfig:
        mask = dict(DEFAULT_MASK_BY_TYPE)
        mask.update(d.get("mask_by_type", {}))
        return cls(
            sections=[LayoutSection.from_dict(s) for s in d.get("sections", [])],
            mask_by_type=mask,
            applied=bool(d.get("applied", False)),
        )


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
    """Compute merged masked [start,end) intervals via the deepest-section-wins rule."""
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


# ── Auto-detection (Step 2: "pre-process Formatting") ──────────────────────────

# Headings come space-inconsistent across producers: "Chapter1", "Chapter 1",
# "CHAPTER I", bare "1"/"IV". Match an optional space then a roman/arabic numeral.
_CHAPTER_RE = re.compile(r"^(chapter\s*[ivxlcdm\d]|chap\.\s*\d|[ivxlcdm]+\.?$|\d+\.?$)", re.IGNORECASE)
_VOLUME_RE = re.compile(r"^(volume|vol\.|part)\s*[ivxlcdm\d]", re.IGNORECASE)
_BOOK_RE = re.compile(r"^book\s*[ivxlcdm\d]", re.IGNORECASE)
_CONTENTS_RE = re.compile(r"contents", re.IGNORECASE)
_INDEX_RE = re.compile(r"^index\b", re.IGNORECASE)
_FOREWORD_RE = re.compile(r"fore-?word|preface|introduction|prologue", re.IGNORECASE)
_AFTERWORD_RE = re.compile(r"after-?word|epilogue|conclusion|postscript|afterword", re.IGNORECASE)


def _classify_heading(heading: str) -> str | None:
    """Map a heading to a section type, or None if it isn't a recognizable boundary."""
    h = heading.strip()
    if not h:
        return None
    if _VOLUME_RE.search(h):
        return "volume"
    if _BOOK_RE.search(h):
        return "book"
    if _CONTENTS_RE.search(h):
        return "contents"
    if _INDEX_RE.search(h):
        return "index"
    if _AFTERWORD_RE.search(h):
        return "afterword"
    if _FOREWORD_RE.search(h):
        return "foreword"
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


def detect_layout_sections(
    boundaries: list[tuple[int, int, str]],
    text_len: int,
    endnote_separator: int = -1,
) -> list[LayoutSection]:
    """Classify raw section boundaries into typed, nested layout sections.

    ``boundaries`` is a sorted list of (start, end, heading) from the EPUB section
    track or the segmenter. Structural sections (volume/book/chapter) extend until the
    next boundary of equal-or-higher level, giving containment; matter before the first
    structural section becomes front matter, and text past ``endnote_separator`` becomes
    endnotes.
    """
    bounds = sorted(boundaries, key=lambda b: b[0])
    sections: list[LayoutSection] = []
    next_id = 0

    def new_id() -> str:
        nonlocal next_id
        next_id += 1
        return f"ls-{next_id}"

    # Classify each boundary's type + structural level.
    typed: list[tuple[int, str, int, str]] = []  # (start, type, level, heading)
    for start, _end, heading in bounds:
        t = _classify_heading(heading)
        if t is None:
            continue
        typed.append((start, t, _TYPE_LEVEL.get(t, 99), heading))

    first_struct_start = next(
        (s for s, t, lvl, _ in typed if t in ("chapter", "book", "volume")), text_len
    )

    # Front matter: everything before the first structural boundary.
    if first_struct_start > 0:
        sections.append(LayoutSection(
            id=new_id(), type="front_matter", start=0, end=first_struct_start,
            label="Front Matter", source="auto",
        ))

    body_end = endnote_separator if endnote_separator > 0 else text_len

    # Each structural/leading boundary spans until the next boundary of <= level.
    for i, (start, t, level, heading) in enumerate(typed):
        if start >= body_end:
            continue
        end = body_end
        for nstart, _nt, nlevel, _nh in typed[i + 1:]:
            if nlevel <= level and nstart > start:
                end = min(nstart, body_end)
                break
            if nstart >= body_end:
                break
        if end <= start:
            continue
        sections.append(LayoutSection(
            id=new_id(), type=t, start=start, end=end,
            label=" ".join(heading.split())[:120], source="auto",
        ))

    # Endnotes: from the separator to the end.
    if endnote_separator > 0 and endnote_separator < text_len:
        sections.append(LayoutSection(
            id=new_id(), type="endnotes", start=endnote_separator, end=text_len,
            label="Endnotes", source="auto",
        ))

    sections.sort(key=lambda s: (s.start, -(s.end - s.start)))
    _compute_parents(sections)
    return sections
