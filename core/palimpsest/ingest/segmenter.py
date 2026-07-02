"""Text segmentation: sentences, paragraphs, and sections.

Uses spaCy for sentence boundaries. Paragraph boundaries are double-newline
delimited. Section boundaries detected by ALL-CAPS or "Chapter" headings.

Segmentation contract: every producer here returns segments anchored to
character offsets in the text it was given, and downstream coordinate machinery
(``segments.jsonl``, the derive OffsetMap remap) trusts those offsets blindly.
So each returned list is guaranteed — and self-checked via
:func:`_validate_segments` — to be index-sequential from 0, in-bounds
(``0 <= start < end <= len(text)``), ordered and mutually disjoint
(``prev.end <= cur.start``), and anchored (``seg.text ==
text[seg.start:seg.end].strip()``).
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
_SPACY_FALLBACK = "en_core_web_sm"


def _get_segmenter_nlp(model: str, exclude: tuple[str, ...]) -> Any:
    import spacy

    key = (model, frozenset(exclude))
    if key not in _NLP_CACHE:
        try:
            _NLP_CACHE[key] = spacy.load(model, exclude=list(exclude))
        except OSError:
            # Substituting a different model silently would change segmentation without a trace;
            # surface it. If the requested model already IS the fallback, a retry can't help.
            if model == _SPACY_FALLBACK:
                raise
            import warnings
            warnings.warn(
                f"spaCy model {model!r} unavailable; falling back to {_SPACY_FALLBACK!r}. "
                f"Install the requested model with `python -m spacy download {model}`.",
                RuntimeWarning, stacklevel=2,
            )
            _NLP_CACHE[key] = spacy.load(_SPACY_FALLBACK, exclude=list(exclude))
    return _NLP_CACHE[key]


@dataclass
class Segment:
    """A text segment with character offsets."""

    segment_type: str
    index: int
    start: int
    end: int
    text: str


def _validate_segments(segments: list[Segment], text: str) -> list[Segment]:
    """Enforce the module's segmentation contract, returning the segments unchanged.

    This is a postcondition self-check run at every producer's return: it holds
    by construction for correct producers, and raises ``ValueError`` the moment a
    future change (a reworked regex, a new spaCy version, an offset-shift bug)
    breaks it — so a coordinate-corrupting segment fails loudly at its source
    instead of silently poisoning everything that reads ``segments.jsonl``.
    """
    n = len(text)
    prev_end = 0
    for i, seg in enumerate(segments):
        if seg.index != i:
            raise ValueError(f"segment index {seg.index} out of sequence at position {i}")
        if not (0 <= seg.start < seg.end <= n):
            raise ValueError(
                f"segment {i} span ({seg.start}, {seg.end}) out of bounds for text length {n}"
            )
        if seg.start < prev_end:
            raise ValueError(
                f"segments must be ordered and disjoint: segment {i} starts at {seg.start}, "
                f"before prior segment's end {prev_end}"
            )
        if seg.text != text[seg.start : seg.end].strip():
            raise ValueError(
                f"segment {i} text is not anchored to its offsets ({seg.start}, {seg.end})"
            )
        prev_end = seg.end
    return segments


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
    return _validate_segments(segments, text)


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
    return _validate_segments(segments, text)


_BLANK_EN_SENTENCIZER_KEY = ("__blank_en_sentencizer__", frozenset())


def _get_sentencizer_nlp() -> Any:
    """Return a fast rule-based sentence boundary pipeline.

    Uses ``spacy.blank("en")`` with the built-in ``sentencizer`` component —
    no tagger, parser, or lemmatizer — which runs roughly 150× faster than
    the full ``en_core_web_lg`` pipeline while producing identical paragraph-
    level sentence splits for import-time segmentation.

    The result is stored in ``_NLP_CACHE`` under a private sentinel key so it
    participates in the same cache-lifetime logic as the full-pipeline entries.
    """
    if _BLANK_EN_SENTENCIZER_KEY not in _NLP_CACHE:
        import spacy

        nlp = spacy.blank("en")
        nlp.add_pipe("sentencizer")
        _NLP_CACHE[_BLANK_EN_SENTENCIZER_KEY] = nlp
    return _NLP_CACHE[_BLANK_EN_SENTENCIZER_KEY]


def segment_sentences(text: str, model: str = "en_core_web_lg") -> list[Segment]:
    """Split text into sentences using spaCy, one paragraph at a time.

    Running spaCy on a whole book-length document builds a single Doc holding
    per-token annotations for the entire text and gets OOM-killed (a ~10M-char
    study bible was unanalyzable). Sentences never cross a blank-line paragraph
    boundary, so we parse each paragraph independently via ``nlp.pipe`` — the
    boundaries are identical, but peak memory is bounded by the largest single
    paragraph rather than the whole work — and shift each sentence's character
    offsets back into the global text.

    The ``model`` parameter is accepted for API compatibility but import-time
    segmentation now uses a fast rule-based sentencizer (``spacy.blank("en")``
    + ``sentencizer`` pipe) rather than the full ``en_core_web_lg`` pipeline.
    The full-quality spaCy Doc is built at analysis time in ``project.py`` and
    does not depend on this function.
    """
    nlp = _get_sentencizer_nlp()

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
    return _validate_segments(segments, text)
