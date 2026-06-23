"""Runtime chunking strategies for analysis over the continuous analyzable stream.

Every chunker returns the canonical chunk-record list ``[{index, start, end, text, words}]`` with
character offsets into the *analyzable* text — the masked-resolved, verse-number-excised stream the
analysis view exposes. The caller remaps those offsets back to original document coordinates, so
chunkers never deal with masking or original positions.

Design principle (enforced): **every parameter is user-defined at runtime.** There are no hidden
defaults, no silent clamps/coercion, and no silently-ignored settings. :class:`ChunkingConfig`
validates that exactly the parameters relevant to the chosen mode are supplied — a missing required
parameter or an extraneous one for the mode raises ``ValueError`` rather than being defaulted or
ignored. A unit-based mode whose unit spans are unavailable raises rather than falling back.

Modes:
  - ``word``        non-overlapping fixed-width word windows of ``size`` words.
  - ``slide``       overlapping word windows of ``size`` words at stride ``size // 2``; ``size`` must
                    be even and at least :data:`MIN_SLIDE_SIZE`.
  - ``punctuation`` clause-level: each run between any of the user-supplied ``delimiters`` is a chunk.
  - ``verse``       one chunk per verse; boundaries supplied as analyzable-coordinate spans.
  - ``smart``       target ``size`` words, grown per syntactic ``smart_unit`` (verse | paragraph |
                    sentence) per ``grow_factor`` / ``remainder_ratio`` so no tiny remainder dangles.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

CHUNK_MODES = ("word", "slide", "punctuation", "verse", "smart")
SMART_UNITS = ("verse", "paragraph", "sentence")

# The smallest legal slide window. A hard validation bound (a user-stated rule: "N must be even and
# >= 10"), NOT a default — values below it are rejected, never silently raised.
MIN_SLIDE_SIZE = 10

Span = tuple[int, int]
Chunk = dict[str, Any]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChunkingConfig:
    """Fully explicit chunking parameters for one run.

    Only the fields relevant to ``mode`` may be set; the rest must be ``None``. Validation rejects
    both missing-required and extraneous-for-the-mode parameters so nothing is defaulted or ignored.
    """

    mode: str
    size: int | None = None
    smart_unit: str | None = None
    delimiters: tuple[str, ...] | None = None
    grow_factor: float | None = None
    remainder_ratio: float | None = None

    def __post_init__(self) -> None:
        if self.mode not in CHUNK_MODES:
            raise ValueError(f"chunk mode must be one of {CHUNK_MODES}, got {self.mode!r}")
        # Which fields are meaningful for this mode; every other field must be left unset.
        relevant: set[str] = {
            "word": {"size"},
            "slide": {"size"},
            "punctuation": {"delimiters"},
            "verse": set(),
            "smart": {"size", "smart_unit", "grow_factor", "remainder_ratio"},
        }[self.mode]
        for field in ("size", "smart_unit", "delimiters", "grow_factor", "remainder_ratio"):
            value = getattr(self, field)
            if field in relevant:
                if value is None:
                    raise ValueError(f"chunk mode {self.mode!r} requires '{field}'")
            elif value is not None:
                raise ValueError(f"chunk mode {self.mode!r} does not accept '{field}'")

        if self.size is not None:
            if self.size < 1:
                raise ValueError(f"chunk size must be >= 1, got {self.size}")
            if self.mode == "slide":
                if self.size < MIN_SLIDE_SIZE:
                    raise ValueError(f"slide size must be >= {MIN_SLIDE_SIZE}, got {self.size}")
                if self.size % 2 != 0:
                    raise ValueError(f"slide size must be even, got {self.size}")
        if self.smart_unit is not None and self.smart_unit not in SMART_UNITS:
            raise ValueError(f"smart_unit must be one of {SMART_UNITS}, got {self.smart_unit!r}")
        if self.delimiters is not None and (not self.delimiters or not all(self.delimiters)):
            raise ValueError("delimiters must be a non-empty tuple of non-empty strings")
        if self.grow_factor is not None and self.grow_factor < 1:
            raise ValueError(f"grow_factor must be >= 1, got {self.grow_factor}")
        if self.remainder_ratio is not None and not (0 < self.remainder_ratio <= 1):
            raise ValueError(f"remainder_ratio must be in (0, 1], got {self.remainder_ratio}")


# ---------------------------------------------------------------------------
# Word tokenisation
# ---------------------------------------------------------------------------

def build_word_positions(text: str) -> tuple[list[str], list[Span]]:
    """Build the word list and each word's ``(start, end)`` char span (whitespace-delimited)."""
    words: list[str] = []
    positions: list[Span] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        start = i
        while i < n and not text[i].isspace():
            i += 1
        words.append(text[start:i])
        positions.append((start, i))
    return words, positions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trim(text: str, s: int, e: int) -> Span:
    """Shrink ``[s, e)`` past leading/trailing whitespace so the span snaps to content."""
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    return s, e


def _record(index: int, start: int, end: int, text: str) -> Chunk:
    seg = text[start:end]
    return {"index": index, "start": start, "end": end, "text": seg, "words": seg.split()}


# ---------------------------------------------------------------------------
# Word / slide modes
# ---------------------------------------------------------------------------

def chunk_words(text: str, size: int) -> list[Chunk]:
    """Non-overlapping word windows of ``size`` words. Every word is covered; the final window is
    kept even if shorter than ``size`` (no silent tail drop)."""
    words, positions = build_word_positions(text)
    n = len(words)
    out: list[Chunk] = []
    i = 0
    while i < n:
        end_i = min(i + size, n)
        out.append(_record(len(out), positions[i][0], positions[end_i - 1][1], text))
        i += size
    return out


def chunk_slide(text: str, size: int) -> list[Chunk]:
    """Overlapping word windows of ``size`` words at stride ``size // 2`` (``size`` validated even
    and >= MIN_SLIDE_SIZE by :class:`ChunkingConfig`). The final window is kept even if shorter."""
    stride = size // 2
    words, positions = build_word_positions(text)
    n = len(words)
    out: list[Chunk] = []
    i = 0
    while i < n:
        end_i = min(i + size, n)
        out.append(_record(len(out), positions[i][0], positions[end_i - 1][1], text))
        if end_i >= n:
            break
        i += stride
    return out


# ---------------------------------------------------------------------------
# Punctuation mode
# ---------------------------------------------------------------------------

def chunk_punctuation(text: str, delimiters: tuple[str, ...]) -> list[Chunk]:
    """Split into clause-level chunks at any of ``delimiters``. The delimiter terminates the chunk
    it closes; whitespace-only runs between adjacent delimiters are skipped."""
    pattern = re.compile("|".join(re.escape(d) for d in delimiters))
    out: list[Chunk] = []
    prev = 0

    def _maybe_emit(lo: int, hi: int) -> None:
        s, e = _trim(text, lo, hi)
        if e > s and text[s:e].strip():
            out.append(_record(len(out), s, e, text))

    for m in pattern.finditer(text):
        _maybe_emit(prev, m.end())
        prev = m.end()
    _maybe_emit(prev, len(text))
    return out


# ---------------------------------------------------------------------------
# Verse mode
# ---------------------------------------------------------------------------

def chunk_verse(text: str, verse_spans: list[Span]) -> list[Chunk]:
    """One chunk per verse. ``verse_spans`` are verse-prose ``[start, end)`` spans already in the
    analyzable coordinate system (translated from the verse index by the caller)."""
    out: list[Chunk] = []
    for s, e in verse_spans:
        s, e = _trim(text, s, e)
        if e > s and text[s:e].strip():
            out.append(_record(len(out), s, e, text))
    return out


# ---------------------------------------------------------------------------
# Smart mode
# ---------------------------------------------------------------------------

def smart_unit_sizes(
    unit_words: int,
    target: int,
    grow_factor: float,
    remainder_ratio: float,
) -> list[int]:
    """Word-counts for splitting a unit of ``unit_words`` words at target chunk size ``target``.

    Grows the chunk size from ``target`` up to ``floor(grow_factor × target)`` looking for one whose
    remainder is 0 or at least ``remainder_ratio`` of the chunk (a respectable final chunk). If the
    remainder is still small at the cap, it is merged into the preceding chunk so nothing tiny
    dangles. A unit no larger than ``target`` is a single chunk.
    """
    if unit_words <= 0:
        return []
    if unit_words <= target:
        return [unit_words]

    chosen = target
    cap = max(target, int(math.floor(target * grow_factor)))
    size = target
    while size <= cap:
        r = unit_words % size
        if r == 0 or r >= math.ceil(size * remainder_ratio):
            chosen = size
            break
        size += 1
    else:
        chosen = target

    count = unit_words // chosen
    remainder = unit_words % chosen
    sizes = [chosen] * count
    if remainder:
        if sizes and remainder < math.ceil(chosen * remainder_ratio):
            sizes[-1] += remainder
        else:
            sizes.append(remainder)
    return sizes


def chunk_smart(
    text: str,
    size: int,
    unit_spans: list[Span],
    grow_factor: float,
    remainder_ratio: float,
) -> list[Chunk]:
    """Target ``size`` words per chunk, never crossing a unit boundary, growing the size within each
    unit (via :func:`smart_unit_sizes`) so no tiny remainder chunk is left behind. ``unit_spans`` are
    the chosen syntactic units in analyzable coordinates, in document order."""
    words, positions = build_word_positions(text)
    n = len(words)
    out: list[Chunk] = []
    wi = 0
    for s, e in unit_spans:
        while wi < n and positions[wi][0] < s:
            wi += 1
        lo = wi
        j = lo
        while j < n and positions[j][1] <= e:
            j += 1
        unit_words = j - lo
        cur = lo
        for sz in smart_unit_sizes(unit_words, size, grow_factor, remainder_ratio):
            out.append(_record(len(out), positions[cur][0], positions[cur + sz - 1][1], text))
            cur += sz
        wi = j
    return out


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    config: ChunkingConfig,
    *,
    verse_spans: list[Span] | None = None,
    paragraph_spans: list[Span] | None = None,
    sentence_spans: list[Span] | None = None,
) -> list[Chunk]:
    """Chunk ``text`` per ``config``. Unit spans for verse/smart modes are supplied by the caller
    (already in analyzable coordinates); a unit-based mode whose spans are ``None`` raises rather
    than falling back to another mode."""
    mode = config.mode
    if mode == "word":
        return chunk_words(text, config.size)  # type: ignore[arg-type]
    if mode == "slide":
        return chunk_slide(text, config.size)  # type: ignore[arg-type]
    if mode == "punctuation":
        return chunk_punctuation(text, config.delimiters)  # type: ignore[arg-type]
    if mode == "verse":
        if verse_spans is None:
            raise ValueError("verse chunking requires verse_spans (verse index unavailable)")
        return chunk_verse(text, verse_spans)
    if mode == "smart":
        unit = config.smart_unit
        assert unit is not None  # ChunkingConfig guarantees this for smart mode
        units = {
            "verse": verse_spans,
            "paragraph": paragraph_spans,
            "sentence": sentence_spans,
        }[unit]
        if units is None:
            raise ValueError(f"smart chunking by {unit!r} requires {unit}_spans")
        return chunk_smart(
            text, config.size, units, config.grow_factor, config.remainder_ratio,  # type: ignore[arg-type]
        )
    raise ValueError(f"unknown chunk mode: {mode!r}")  # unreachable: ChunkingConfig validates
