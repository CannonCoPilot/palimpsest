"""Text segmentation: sentences, paragraphs, and sections.

Uses spaCy for sentence boundaries. Paragraph boundaries are double-newline
delimited. Section boundaries detected by ALL-CAPS or "Chapter" headings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Cache loaded spaCy pipelines keyed on (model, excluded components). Loading
# en_core_web_lg costs ~0.5 GB and several seconds; segment_sentences is called
# once per ingest, so without this cache a multi-file ingest (or a test suite
# that ingests per test) reloads the model every time. Mirrors tracks/syntax.py.
_NLP_CACHE: dict[tuple[str, frozenset[str]], Any] = {}


def _get_segmenter_nlp(model: str, exclude: tuple[str, ...]) -> Any:
    import spacy

    key = (model, frozenset(exclude))
    if key not in _NLP_CACHE:
        try:
            _NLP_CACHE[key] = spacy.load(model, exclude=list(exclude))
        except OSError:
            _NLP_CACHE[key] = spacy.load("en_core_web_sm", exclude=list(exclude))
    return _NLP_CACHE[key]


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
        r"^(?:(?i:chapter)\s+[\divxlc]+\.?|[A-Z][A-Z ]{5,}|[IVXLC]+\.\s)",
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
    """Split text into sentences using spaCy, one paragraph at a time.

    Running spaCy on a whole book-length document builds a single Doc holding
    per-token annotations for the entire text and gets OOM-killed (a ~10M-char
    study bible was unanalyzable). Sentences never cross a blank-line paragraph
    boundary, so we parse each paragraph independently via ``nlp.pipe`` — the
    boundaries are identical, but peak memory is bounded by the largest single
    paragraph rather than the whole work — and shift each sentence's character
    offsets back into the global text.
    """
    nlp = _get_segmenter_nlp(model, ("ner",))

    paragraphs = segment_paragraphs(text)
    if not paragraphs:
        return []

    # Paragraphs are short, but a degenerate block with no blank lines could be
    # large; size the guard to the biggest chunk so spaCy never rejects one.
    chunks = [text[p.start:p.end] for p in paragraphs]
    nlp.max_length = max(len(c) for c in chunks) + 1000

    segments: list[Segment] = []
    idx = 0
    for para, doc in zip(paragraphs, nlp.pipe(chunks, batch_size=64)):
        for sent in doc.sents:
            segments.append(
                Segment(
                    segment_type="sentence",
                    index=idx,
                    start=para.start + sent.start_char,
                    end=para.start + sent.end_char,
                    text=sent.text.strip(),
                )
            )
            idx += 1
    return segments
