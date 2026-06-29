"""Wave-0 P7 commit 1 — similarity-method registry.

The registry wraps the four existing matrix builders without changing them. These tests lock the
canonical order, the embedding-requirement flags, fail-loud on unknown metrics, and that dispatching
through the registry is identical to calling a builder directly.
"""

from __future__ import annotations

import numpy as np
import pytest

from palimpsest.tracks.self_similarity import (
    METRICS,
    SimilarityMethod,
    _METHODS,
    _cosine_matrix,
    _word_overlap_matrix,
    resolve_methods,
)


def test_registry_covers_metrics_in_canonical_order() -> None:
    assert tuple(_METHODS) == METRICS
    assert list(_METHODS) == ["cosine", "jaccard", "word_overlap", "edit_distance"]


def test_requires_embedding_flags() -> None:
    assert _METHODS["cosine"].requires_embedding is True
    assert _METHODS["jaccard"].requires_embedding is True
    assert _METHODS["word_overlap"].requires_embedding is False
    assert _METHODS["edit_distance"].requires_embedding is False


def test_resolve_methods_canonical_order_regardless_of_input_order() -> None:
    out = resolve_methods(["edit_distance", "cosine", "word_overlap"])
    assert [m.name for m in out] == ["cosine", "word_overlap", "edit_distance"]
    assert all(isinstance(m, SimilarityMethod) for m in out)


def test_resolve_methods_single_metric() -> None:
    assert [m.name for m in resolve_methods(["cosine"])] == ["cosine"]


def test_resolve_methods_unknown_fails_loud() -> None:
    with pytest.raises(ValueError, match="unknown similarity metric"):
        resolve_methods(["cosine", "bogus"])


def test_text_only_build_matches_direct_builder() -> None:
    chunks = [
        {"words": ["the", "quick", "brown", "fox"], "masked": False},
        {"words": ["the", "quick", "red", "fox"], "masked": False},
        {"words": ["entirely", "different", "content", "here"], "masked": False},
    ]
    via_registry = _METHODS["word_overlap"].build(chunks, embeddings=None)
    assert np.array_equal(via_registry, _word_overlap_matrix(chunks))


def test_embedding_build_matches_direct_builder() -> None:
    rng = np.random.default_rng(0)
    emb = rng.standard_normal((5, 8)).astype(np.float32)
    via_registry = _METHODS["cosine"].build(None, embeddings=emb)
    assert np.array_equal(via_registry, _cosine_matrix(emb))
