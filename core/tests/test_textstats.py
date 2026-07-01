"""Unit tests for palimpsest.analysis.textstats — P4 deterministic descriptive statistics (FR-8/10)."""

import math

import pytest

from palimpsest.analysis import textstats as T

_TEXT = ("The quick brown fox jumps over the lazy dog. " * 20) + "A singular rare phrase appears once."


@pytest.fixture
def tokens() -> list[str]:
    return T.tokenize(_TEXT)


class TestTokenize:
    def test_lowercased_words(self):
        assert T.tokenize("The QUICK fox's tail.") == ["the", "quick", "fox's", "tail"]

    def test_empty(self):
        assert T.tokenize("") == []


class TestCounts:
    def test_basic_counts(self, tokens):
        c = T.basic_counts(tokens)
        assert c["tokens"] == len(tokens)
        assert c["types"] <= c["tokens"]
        assert 0.0 <= c["hapax_ratio"] <= 1.0

    def test_empty_is_zeroed(self):
        c = T.basic_counts([])
        assert c["tokens"] == 0 and c["types"] == 0 and c["hapax"] == 0


class TestDiversity:
    def test_ttr_range(self, tokens):
        assert 0.0 < T.ttr(tokens) <= 1.0

    def test_mattr_short_text_falls_back_to_ttr(self):
        toks = ["a", "b", "c"]
        assert T.mattr(toks, window=100) == T.ttr(toks)

    def test_mtld_positive(self, tokens):
        assert T.mtld(tokens) > 0

    def test_yules_k_matches_lexical_definition(self, tokens):
        from palimpsest.tracks.lexical import _yules_k
        # textstats.yules_k mirrors lexical._yules_k (rounded) — they must not drift.
        assert T.yules_k(tokens) == pytest.approx(_yules_k(tokens), abs=1e-3)

    def test_deterministic(self, tokens):
        assert T.mtld(tokens) == T.mtld(tokens)
        assert T.yules_k(tokens) == T.yules_k(tokens)


class TestFits:
    def test_zipf_slope_negative_for_natural_text(self, tokens):
        # A repeated function word dominates → frequency falls with rank → negative slope.
        assert T.zipf_slope(tokens) < 0

    def test_heaps_beta_between_zero_and_one(self, tokens):
        h = T.heaps_params(tokens)
        assert 0.0 <= h["beta"] <= 1.0 and h["K"] > 0

    def test_degenerate_inputs(self):
        assert T.zipf_slope([]) == 0.0
        assert T.heaps_params(["a"]) == {"K": 0.0, "beta": 0.0}


class TestHistogram:
    def test_summary_and_shape(self):
        h = T.histogram([1, 2, 3, 4, 5], bins=5)
        assert h["n"] == 5 and h["min"] == 1.0 and h["max"] == 5.0
        assert len(h["edges"]) == 6 and len(h["counts"]) == 5
        assert sum(h["counts"]) == 5

    def test_empty_is_well_defined(self):
        h = T.histogram([])
        assert h["n"] == 0 and h["edges"] == [] and h["counts"] == []


class TestNgramsAndCollocations:
    def test_top_ngrams_ordered(self, tokens):
        bigrams = T.top_ngrams(tokens, 2, 3)
        counts = [c for _, c in bigrams]
        assert counts == sorted(counts, reverse=True)

    def test_ngram_too_long_is_empty(self):
        assert T.top_ngrams(["a", "b"], 5) == []

    def test_function_word_profile_injected_set(self, tokens):
        prof = T.function_word_profile(tokens, frozenset({"the", "over", "a"}), top=10)
        words = {row[0] for row in prof}
        assert words <= {"the", "over", "a"}  # only injected function words reported

    def test_collocations_shape_and_threshold(self, tokens):
        cols = T.collocations(tokens, window=2, min_count=3, top=10)
        assert all(len(row) == 5 for row in cols)
        assert all(row[4] >= 3 for row in cols)  # min_count honored

    def test_collocations_deterministic(self, tokens):
        assert T.collocations(tokens, 2, 3, 10) == T.collocations(tokens, 2, 3, 10)

    def test_collocations_pmi_normalized_by_windowed_pair_total(self):
        # "a b a b" with window=1 → pairs {(a,b):2, (b,a):1}; total_pairs=3, n=4, ua=ub=2.
        # Correct PMI(a,b) = log2( P(a,b) / (P(a)·P(b)) ) with P(a,b)=c/total_pairs, P(x)=ux/n
        #                  = log2( c·n·n / (total_pairs·ua·ub) ) = log2(32/12) ≈ 1.415.
        # The prior bug normalized the joint by the token count n (one-pair-per-token) → log2(8/4)=1.0.
        cols = T.collocations(["a", "b", "a", "b"], window=1, min_count=2, top=10)
        assert len(cols) == 1
        a, b, pmi, _g2, count = cols[0]
        assert (a, b, count) == ("a", "b", 2)
        assert pmi == round(math.log2((2 * 4 * 4) / (3 * 2 * 2)), 4) == 1.415
        assert pmi != 1.0  # the old token-count-normalized value

    def test_log_likelihood_zero_cell_keeps_surviving_term(self):
        # c12 == c2 (the bigram accounts for every occurrence of the second word) → the "second word
        # without the first" cell is empty. 0·log0 = 0 must zero only that term; the paired
        # (total-k)·log(1-p) term is still valid. The old guard discarded the whole term at k=0,
        # understating G². New: 6.189; old (whole-term-dropped): 3.065.
        g2 = T._log_likelihood(c12=2, c1=3, c2=2, n=10)
        assert g2 == 6.189
        assert g2 != 3.065
