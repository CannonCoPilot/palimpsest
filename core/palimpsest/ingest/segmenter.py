"""Text segmentation: sentences, paragraphs, and sections.

Uses spaCy for sentence boundaries. Paragraph boundaries are double-newline
delimited. Section boundaries detected by ALL-CAPS or "Chapter" headings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Segment:
    """A text segment with character offsets."""

    segment_type: str
    index: int
    start: int
    end: int
    text: str


def segment_paragraphs(text: str) -> list[Segment]:
    """Split text into paragraphs at double-newline boundaries.

    Tracks exact character offsets in the original text (E-C3 fix).
    """
    segments: list[Segment] = []
    idx = 0
    for m in re.finditer(r"[^\n](?:[^\n]|\n(?!\n))*", text):
        block = m.group().strip()
        if block:
            segments.append(
                Segment(
                    segment_type="paragraph",
                    index=idx,
                    start=m.start(),
                    end=m.end(),
                    text=block,
                )
            )
            idx += 1
    return segments


def segment_sections(text: str) -> list[Segment]:
    """Detect section/chapter boundaries.

    Heuristics:
    - Lines matching 'Chapter N' or 'CHAPTER N'
    - ALL-CAPS lines of 3+ words
    - Lines starting with a Roman numeral followed by a period
    """
    section_pattern = re.compile(
        r"^(?:(?i:chapter)\s+[\divxlc]+\.?|[A-Z][A-Z\s]{5,}|[IVXLC]+\.\s)",
        re.MULTILINE,
    )
    segments: list[Segment] = []
    idx = 0
    for m in section_pattern.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        if line_end == -1:
            line_end = len(text)
        heading = text[line_start:line_end].strip()
        segments.append(
            Segment(
                segment_type="section",
                index=idx,
                start=line_start,
                end=line_end,
                text=heading,
            )
        )
        idx += 1
    return segments


def segment_sentences(text: str, model: str = "en_core_web_lg") -> list[Segment]:
    """Split text into sentences using spaCy."""
    import spacy

    try:
        nlp = spacy.load(model, exclude=["ner"])
    except OSError:
        nlp = spacy.load("en_core_web_sm", exclude=["ner"])
    nlp.max_length = len(text) + 1000
    doc = nlp(text)
    segments: list[Segment] = []
    for idx, sent in enumerate(doc.sents):
        segments.append(
            Segment(
                segment_type="sentence",
                index=idx,
                start=sent.start_char,
                end=sent.end_char,
                text=sent.text.strip(),
            )
        )
    return segments
