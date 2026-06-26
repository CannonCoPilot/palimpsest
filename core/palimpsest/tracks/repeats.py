"""Exact-repeat phrase detection and chunk masking — shared substrate for analyses that must not let
formulaic, frequently-repeated passages dominate a result.

This logic was born inside ``self_similarity`` (where repeated scripture/legal boilerplate would
otherwise inflate the similarity matrix). It is extracted here so it is reusable by any track that
embeds or compares chunks — notably the Wave-0 ``EmbeddingTrack`` — instead of living only inside one
consumer. ``self_similarity`` imports these names back, so there is a single definition (no drift).

A "repeat" is a contiguous word-sequence (n-gram) that recurs at least ``min_occurrences`` times across
the whole document; a chunk is "masked" when more than ``MASK_COVERAGE_THRESHOLD`` of its content words
are covered by such repeats. Masking only sets a boolean flag on each chunk dict — what a consumer does
with that flag (skip in a matrix, exclude from embedding, …) is the consumer's policy, not this
module's.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Masking knobs (locked analytical constants, design §6 / audit A3): they change which text is excluded
# from analysis, so they are declared here and re-exported into self_similarity's LOCKED_CONSTANTS for
# provenance. Not yet user-tunable.
EXACT_REPEAT_MIN_WORDS = 3             # shortest repeated phrase considered for masking
EXACT_REPEAT_MIN_OCCURRENCES = 3       # times a phrase must recur to count as a repeat
MASK_COVERAGE_THRESHOLD = 0.5          # fraction of a chunk's content covered by repeats to mask it

# Only reached if a non-empty chunk list has an empty first chunk — effectively unreachable (an empty
# document returns early), but kept so the n-gram ceiling has a defined value in every branch.
_DEFAULT_CHUNK_SIZE = 7

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


def find_exact_repeats(
    text: str,
    chunks: list[dict[str, Any]],
    min_words: int = EXACT_REPEAT_MIN_WORDS,
    min_occurrences: int = EXACT_REPEAT_MIN_OCCURRENCES,
) -> set[str]:
    """Build a phrase-occurrence index from all chunks and return the set of
    contiguous word sequences (of length min_words to chunk_size) that appear
    at least min_occurrences times across the full text.

    The index is built once over the concatenated word list (not per-chunk),
    so phrase counts reflect the whole document.
    """
    # Collect all words from the full text in document order
    all_words: list[str] = []
    for chunk in chunks:
        all_words.extend(chunk["words"])

    if len(all_words) < min_words:
        return set()

    chunk_size = len(chunks[0]["words"]) if chunks else _DEFAULT_CHUNK_SIZE
    max_ngram = min(chunk_size, len(all_words) // 2)

    # Normalise words for comparison (lowercase, strip punctuation)
    normalised = [re.sub(r"[^a-z']", "", w.lower()) for w in all_words]

    # Count every n-gram of each length
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

    repeats = {phrase for phrase, count in phrase_counts.items()
               if count >= min_occurrences}
    logger.info(
        "Repeat masking: found %d phrases with >= %d occurrences",
        len(repeats), min_occurrences,
    )
    return repeats


def mask_repeats(
    chunks: list[dict[str, Any]],
    repeats: set[str],
) -> list[dict[str, Any]]:
    """Mark chunks where >50% of content words are covered by a repeated phrase.

    A content word is 'covered' if it belongs to any repeated n-gram that
    appears somewhere within the chunk's content-token sequence.  The function
    adds a ``masked`` key (True/False) to each chunk dict in-place and also
    returns the list for convenience.
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
        chunk["masked"] = covered_content / len(content_tokens) > MASK_COVERAGE_THRESHOLD

    masked_count = sum(1 for c in chunks if c.get("masked"))
    if masked_count:
        logger.info("Repeat masking: %d / %d chunks masked", masked_count, len(chunks))
    return chunks
