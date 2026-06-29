"""textstats — deterministic descriptive/distributional text statistics (Wave-0 P4, FR-8/FR-10).

Pure functions over token lists or raw text: counts, lexical-diversity indices, length distributions,
Zipf/Heaps fits, n-gram tables, and window collocations. No randomness, no I/O, no track/server import
(a true leaf): function-word sets are injected by the caller rather than imported, so this module never
depends on ``tracks``. Everything is descriptive-of-this-text — there is no reference corpus and no
inferential claim (NFR-7); callers surface that framing in the report.

The tokenizer mirrors ``tracks.lexical._TOKEN_RE`` (``[A-Za-z']+``, lowercased) so the per-paragraph
lexical track and the whole-document profile agree on what a "word" is.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

TOKEN_RE = re.compile(r"[A-Za-z']+")
# Sentence splitter: a run of non-terminator characters ended by . ! ? (or end of text). Deliberately
# simple and dependency-free — used only for an approximate sentence-length distribution, flagged as
# such in the report; it is not a linguistic sentence segmenter.
_SENT_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)", re.S)


def tokenize(text: str) -> list[str]:
    """Lowercased word tokens (``[A-Za-z']+``), in order. Deterministic."""
    return [t.lower() for t in TOKEN_RE.findall(text)]


def basic_counts(tokens: list[str]) -> dict[str, float]:
    """Token/type/hapax counts and mean token length."""
    n = len(tokens)
    if n == 0:
        return {"tokens": 0, "types": 0, "hapax": 0, "hapax_ratio": 0.0, "mean_token_length": 0.0}
    freq = Counter(tokens)
    hapax = sum(1 for c in freq.values() if c == 1)
    return {
        "tokens": n,
        "types": len(freq),
        "hapax": hapax,
        "hapax_ratio": round(hapax / len(freq), 4),
        "mean_token_length": round(sum(len(t) for t in tokens) / n, 4),
    }


def ttr(tokens: list[str]) -> float:
    """Type-token ratio. Length-sensitive — reported alongside length-robust MATTR/MTLD/Yule's K."""
    return round(len(set(tokens)) / len(tokens), 4) if tokens else 0.0


def mattr(tokens: list[str], window: int = 100) -> float:
    """Moving-average TTR over a sliding window (length-robust). For texts shorter than one window the
    single-window TTR is returned (and the report notes the short-text case)."""
    n = len(tokens)
    if n == 0:
        return 0.0
    if n <= window:
        return ttr(tokens)
    ratios = [len(set(tokens[i:i + window])) / window for i in range(n - window + 1)]
    return round(float(np.mean(ratios)), 4)


def _mtld_pass(tokens: list[str], threshold: float) -> float:
    factors = 0.0
    types: set[str] = set()
    count = 0
    for t in tokens:
        count += 1
        types.add(t)
        if (len(types) / count) <= threshold:
            factors += 1
            types, count = set(), 0
    if count > 0:
        partial = (1.0 - (len(types) / count)) / (1.0 - threshold)
        factors += partial
    return len(tokens) / factors if factors > 0 else float(len(tokens))


def mtld(tokens: list[str], threshold: float = 0.72) -> float:
    """Measure of Textual Lexical Diversity (bidirectional mean). Length-robust diversity index."""
    if len(tokens) < 2:
        return 0.0
    fwd = _mtld_pass(tokens, threshold)
    bwd = _mtld_pass(list(reversed(tokens)), threshold)
    return round((fwd + bwd) / 2.0, 4)


def yules_k(tokens: list[str]) -> float:
    """Yule's K characteristic (length-independent richness). Mirrors ``tracks.lexical._yules_k``."""
    n = len(tokens)
    if n == 0:
        return 0.0
    freq = Counter(tokens)
    spectrum = Counter(freq.values())
    m2 = sum(m * m * vm for m, vm in spectrum.items())
    return round(10_000 * (m2 - n) / (n * n), 4)


def zipf_slope(tokens: list[str]) -> float:
    """Slope of the log-rank/log-frequency fit (Zipf's law → ≈ -1 for natural text). Descriptive of
    this text's frequency distribution; not a goodness-of-fit claim."""
    if len(tokens) < 2:
        return 0.0
    freqs = sorted(Counter(tokens).values(), reverse=True)
    if len(freqs) < 2:
        return 0.0
    ranks = np.arange(1, len(freqs) + 1)
    slope = np.polyfit(np.log(ranks), np.log(freqs), 1)[0]
    return round(float(slope), 4)


def heaps_params(tokens: list[str], points: int = 30) -> dict[str, float]:
    """Heaps' law fit ``V ≈ K · N^beta`` over growing prefixes → ``{K, beta}``. Describes how this
    text's vocabulary grows with length."""
    n = len(tokens)
    if n < 2:
        return {"K": 0.0, "beta": 0.0}
    seen: set[str] = set()
    cum = np.empty(n, dtype=np.int64)
    for i, t in enumerate(tokens):
        seen.add(t)
        cum[i] = len(seen)
    ns = np.unique(np.linspace(1, n, min(points, n)).astype(int))
    vs = cum[ns - 1]
    beta, log_k = np.polyfit(np.log(ns), np.log(vs), 1)
    return {"K": round(float(np.exp(log_k)), 4), "beta": round(float(beta), 4)}


def histogram(values: list[float] | list[int], bins: int = 30) -> dict[str, object]:
    """Histogram + summary of a numeric distribution → ``{edges, counts, n, mean, median, min, max}``.
    Empty input yields a well-defined empty result rather than a NaN range."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return {"edges": [], "counts": [], "n": 0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
    counts, edges = np.histogram(arr, bins=bins)
    return {
        "edges": edges.tolist(),
        "counts": counts.astype(np.int64).tolist(),
        "n": int(arr.size),
        "mean": round(float(arr.mean()), 4),
        "median": round(float(np.median(arr)), 4),
        "min": round(float(arr.min()), 4),
        "max": round(float(arr.max()), 4),
    }


def sentence_word_lengths(text: str) -> list[int]:
    """Word count per (approximate) sentence — for the sentence-length distribution."""
    out: list[int] = []
    for m in _SENT_RE.finditer(text):
        chunk = m.group().strip()
        if chunk:
            wc = len(TOKEN_RE.findall(chunk))
            if wc:
                out.append(wc)
    return out


def top_ngrams(tokens: list[str], n: int, k: int = 25) -> list[list[object]]:
    """Top ``k`` contiguous ``n``-grams by frequency → ``[[ "a b", count ], …]`` (ties broken by the
    n-gram text, so the ordering is deterministic)."""
    if n < 1 or len(tokens) < n:
        return []
    grams = Counter(" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1))
    ranked = sorted(grams.items(), key=lambda kv: (-kv[1], kv[0]))
    return [[g, c] for g, c in ranked[:k]]


def function_word_profile(
    tokens: list[str], function_words: frozenset[str], top: int = 25
) -> list[list[object]]:
    """Most frequent function words (from the injected ``function_words`` set) with relative frequency
    → ``[[ word, count, ratio ], …]``. The set is injected so this module stays a leaf; callers pass
    ``tracks.repeats.STOPWORDS`` to reuse the one shared definition."""
    n = len(tokens)
    if n == 0:
        return []
    freq = Counter(t for t in tokens if t in function_words)
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return [[w, c, round(c / n, 5)] for w, c in ranked[:top]]


def _log_likelihood(c12: int, c1: int, c2: int, n: int) -> float:
    """Dunning's G² for a bigram's association (2×2 contingency). Higher = more surprising than chance."""
    def _ll(k: float, total: float, p: float) -> float:
        if k <= 0 or p <= 0 or p >= 1:
            return 0.0
        return k * math.log(p) + (total - k) * math.log(1 - p)

    if n <= 0 or c1 <= 0 or c2 <= 0:
        return 0.0
    p = c2 / n
    p1 = c12 / c1 if c1 else 0.0
    p2 = (c2 - c12) / (n - c1) if (n - c1) else 0.0
    ll = _ll(c12, c1, p) + _ll(c2 - c12, n - c1, p) - _ll(c12, c1, p1) - _ll(c2 - c12, n - c1, p2)
    return round(-2.0 * ll, 4)


def collocations(
    tokens: list[str], window: int = 2, min_count: int = 3, top: int = 50
) -> list[list[object]]:
    """Within-window ordered bigram associations → ``[[a, b, pmi, log_likelihood, count], …]``.

    For each token, pairs it with the next ``window`` tokens. PMI and Dunning's G² are computed against
    unigram frequencies over the whole token stream. Pairs below ``min_count`` are dropped; results are
    ranked by count then alphabetically (deterministic)."""
    n = len(tokens)
    if n < 2:
        return []
    unigram = Counter(tokens)
    pairs: Counter[tuple[str, str]] = Counter()
    for i in range(n):
        for j in range(i + 1, min(i + 1 + window, n)):
            pairs[(tokens[i], tokens[j])] += 1
    out: list[list[object]] = []
    for (a, b), c in pairs.items():
        if c < min_count:
            continue
        pmi = math.log2((c * n) / (unigram[a] * unigram[b]))
        out.append([a, b, round(pmi, 4), _log_likelihood(c, unigram[a], unigram[b], n), c])
    out.sort(key=lambda r: (-r[4], r[0], r[1]))
    return out[:top]
