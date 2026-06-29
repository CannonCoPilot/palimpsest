"""Exact-repeat phrase detection and chunk masking — shared substrate for the repeat analyses that
keep formulaic, frequently-repeated passages from dominating a result.

This logic was born inside ``self_similarity`` (where repeated scripture/legal boilerplate would
otherwise inflate the similarity matrix). It is extracted here so the P8 repeat tracks share one
definition: the ``repeats`` detection track calls :func:`detect_repeats` (text-level) and the
``repeat_mask`` track calls :func:`mask_repeats`; both route through the same :func:`_count_repeats`
tally, so they can never drift. ``self_similarity`` (now a layer consumer) imports only
:data:`STOPWORDS` from here for its content-token filter — it no longer detects or masks repeats inline.

A "repeat" is a contiguous word-sequence (n-gram) that recurs at least ``min_occurrences`` times across
the whole document; a chunk is "masked" when more than ``MASK_COVERAGE_THRESHOLD`` of its content words
are covered by such repeats. Masking only sets a boolean flag on each chunk dict — what a consumer does
with that flag (skip in a matrix, shade a lane, …) is the consumer's policy, not this module's.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Masking knobs (design §6 / audit A3): they change which text is excluded from analysis. They are the
# single source of the defaults for the now user-tunable Params on the P8 repeats / repeat_mask tracks,
# kept as named constants so a positional mask_repeats(chunks, repeats) call stays byte-identical to the
# pre-P8 behaviour.
EXACT_REPEAT_MIN_WORDS = 3             # shortest repeated phrase considered for masking
EXACT_REPEAT_MIN_OCCURRENCES = 3       # times a phrase must recur to count as a repeat
MASK_COVERAGE_THRESHOLD = 0.5          # fraction of a chunk's content covered by repeats to mask it

# Only reached if a non-empty chunk list has an empty first chunk — effectively unreachable (an empty
# document returns early), but kept so the n-gram ceiling has a defined value in every branch.
_DEFAULT_CHUNK_SIZE = 7

# Default n-gram ceiling for the text-level detection path (the ``repeats`` track), used in place of the
# chunk-size-derived ceiling the chunk-based path takes. Mirrors self_similarity's DEFAULT_CHUNK_SIZE so
# default-param detection considers the same phrase lengths.
DEFAULT_MAX_PHRASE_LEN = 7

# Whitespace-delimited token spans: the text-level path maps a repeated phrase back to character
# intervals, which ``text.split()`` cannot do (it loses positions).
_WORD_RE = re.compile(r"\S+")

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "nor", "not", "no", "so", "as",
    "at", "by", "for", "from", "in", "into", "of", "on", "to", "up", "with",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "shall", "would", "should", "may", "might", "can", "could", "must",
    "he", "she", "it", "i", "me", "my", "we", "us", "our", "you", "your",
    "they", "them", "their", "him", "his", "her", "its",
    "this", "that", "these", "those", "which", "who", "whom", "whose",
    "what", "when", "where", "how", "why", "if", "then", "than", "else",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "also", "just", "very", "too",
    "ye", "thee", "thou", "thy", "thine", "unto", "upon", "hath", "doth",
    "thereof", "therein", "hereby", "thereby", "wherefore",
    "saith", "cometh", "goeth",
})


def _normalise(words: list[str]) -> list[str]:
    """Lowercase + strip non-letter/apostrophe characters — the single normalisation both the
    chunk-based and text-level paths apply before counting, so they can never diverge."""
    return [re.sub(r"[^a-z']", "", w.lower()) for w in words]


def _count_repeats(
    normalised: list[str], min_words: int, min_occurrences: int, max_ngram: int
) -> set[str]:
    """The shared n-gram tally: every contiguous word sequence of length ``min_words..max_ngram`` that
    occurs at least ``min_occurrences`` times across ``normalised``, skipping all-stopword grams. Both
    :func:`find_exact_repeats` (chunk-based) and :func:`detect_repeats` (text-level) call this, so the
    detection logic has one definition — the text-level path can never drift from what ``self_similarity``
    finds inline."""
    phrase_counts: dict[str, int] = {}
    for n in range(min_words, max_ngram + 1):
        for start in range(len(normalised) - n + 1):
            gram = normalised[start:start + n]
            # Skip n-grams that are entirely stopwords
            if all(w in STOPWORDS or not w for w in gram):
                continue
            key = " ".join(gram)
            if not key.strip():
                continue
            phrase_counts[key] = phrase_counts.get(key, 0) + 1

    return {phrase for phrase, count in phrase_counts.items() if count >= min_occurrences}


def find_exact_repeats(
    chunks: list[dict[str, Any]],
    min_words: int = EXACT_REPEAT_MIN_WORDS,
    min_occurrences: int = EXACT_REPEAT_MIN_OCCURRENCES,
) -> set[str]:
    """Chunk-based exact-repeat detection: build a phrase-occurrence index over the concatenated word
    list of ``chunks`` and return every contiguous word sequence (length ``min_words`` to the chunk
    size) that recurs at least ``min_occurrences`` times across the whole document.

    The index is built once over the concatenated word list (not per-chunk), so phrase counts reflect
    the whole document. This is the reference path the equivalence tests check the text-level
    :func:`detect_repeats` against; the tracks themselves use the text-level path.
    """
    all_words: list[str] = []
    for chunk in chunks:
        all_words.extend(chunk["words"])

    if len(all_words) < min_words:
        return set()

    chunk_size = len(chunks[0]["words"]) if chunks else _DEFAULT_CHUNK_SIZE
    max_ngram = min(chunk_size, len(all_words) // 2)

    repeats = _count_repeats(_normalise(all_words), min_words, min_occurrences, max_ngram)
    logger.info(
        "Exact-repeat detection: found %d phrases with >= %d occurrences",
        len(repeats), min_occurrences,
    )
    return repeats


def detect_repeats(
    text: str,
    *,
    min_words: int = EXACT_REPEAT_MIN_WORDS,
    min_occurrences: int = EXACT_REPEAT_MIN_OCCURRENCES,
    max_phrase_len: int = DEFAULT_MAX_PHRASE_LEN,
) -> tuple[set[str], list[tuple[int, int]]]:
    """Detect exact repeats directly from text — the chunk-independent entry point used by the
    ``repeats`` track (FR-15). Tokenises ``text`` on whitespace (so detection does not depend on any
    chunking), counts n-grams up to ``max_phrase_len`` with the same shared tally the chunk-based path
    uses, and maps every occurrence of a repeated phrase back to its character interval in ``text``.

    Returns ``(phrases, intervals)`` where ``phrases`` is the normalised repeated-phrase set and
    ``intervals`` is the merged, ordered, disjoint list of ``(start, end)`` character spans covered by
    those phrases — ready to become a signal layer's ``segment_offsets`` (analyzable coordinates,
    remapped to original by the runner).

    The ``min(max_phrase_len, token_count // 2)`` ceiling preserves the chunk-based path's cap, so at the
    default ``max_phrase_len`` the considered phrase lengths match what ``self_similarity`` considers."""
    tokens = list(_WORD_RE.finditer(text))
    words = [t.group() for t in tokens]
    if len(words) < min_words:
        return set(), []

    max_ngram = min(max_phrase_len, len(words) // 2)
    normalised = _normalise(words)
    phrases = _count_repeats(normalised, min_words, min_occurrences, max_ngram)
    logger.info(
        "Repeat detection: found %d phrases with >= %d occurrences",
        len(phrases), min_occurrences,
    )
    if not phrases:
        return phrases, []

    # Map each phrase occurrence to the character span from its first token's start to its last token's
    # end, then merge into ordered disjoint intervals.
    phrase_token_lists = [p.split() for p in phrases]
    spans: list[tuple[int, int]] = []
    for phrase_tokens in phrase_token_lists:
        plen = len(phrase_tokens)
        for start in range(len(normalised) - plen + 1):
            if normalised[start:start + plen] == phrase_tokens:
                spans.append((tokens[start].start(), tokens[start + plen - 1].end()))
    return phrases, _merge_spans(spans)


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping/adjacent character spans into an ordered, disjoint interval list (the
    partition shape ``_complement_spans`` and ``OffsetMap`` consume for excision/remap)."""
    if not spans:
        return []
    ordered = sorted(spans)
    merged: list[tuple[int, int]] = [ordered[0]]
    for s, e in ordered[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    return merged


def mask_repeats(
    chunks: list[dict[str, Any]],
    repeats: set[str],
    coverage_threshold: float = MASK_COVERAGE_THRESHOLD,
) -> list[dict[str, Any]]:
    """Mark chunks where more than ``coverage_threshold`` of content words are covered by a repeated
    phrase.

    A content word is 'covered' if it belongs to any repeated n-gram that
    appears somewhere within the chunk's content-token sequence.  The function
    adds a ``masked`` key (True/False) to each chunk dict in-place and also
    returns the list for convenience. ``coverage_threshold`` defaults to the module constant so a
    positional ``mask_repeats(chunks, repeats)`` call (``self_similarity``) is byte-identical; the
    ``repeat_mask`` track passes the user-tunable value.
    """
    if not repeats:
        for chunk in chunks:
            chunk["masked"] = False
        return chunks

    # Pre-split repeated phrases into token lists for fast membership testing
    repeat_token_lists: list[list[str]] = [p.split() for p in repeats]

    for chunk in chunks:
        tokens = [re.sub(r"[^a-z']", "", w.lower()) for w in chunk["words"]]
        content_tokens = [t for t in tokens if t and t not in STOPWORDS and len(t) > 1]
        if not content_tokens:
            chunk["masked"] = False
            continue

        # Mark which token positions are covered by any repeated phrase
        covered = [False] * len(tokens)
        for phrase_tokens in repeat_token_lists:
            plen = len(phrase_tokens)
            for start in range(len(tokens) - plen + 1):
                if tokens[start:start + plen] == phrase_tokens:
                    for k in range(start, start + plen):
                        covered[k] = True

        # Count covered content tokens
        covered_content = sum(
            1 for t, cov in zip(tokens, covered)
            if cov and t and t not in STOPWORDS and len(t) > 1
        )
        chunk["masked"] = covered_content / len(content_tokens) > coverage_threshold

    masked_count = sum(1 for c in chunks if c.get("masked"))
    if masked_count:
        logger.info("Repeat masking: %d / %d chunks masked", masked_count, len(chunks))
    return chunks
