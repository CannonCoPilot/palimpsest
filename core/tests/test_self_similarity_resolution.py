"""Wave-0 P7 commit 2 — explicit layer-bundle binding.

Binds chunk + repeat_mask (+ embedding) layers by explicit label and validates coherence. These tests
plant minimal layer manifests on disk (only the fields the binder reads) and exercise the happy path
plus every fail-loud branch. A lightweight stub stands in for Project — the binder only touches
``project.path``.
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from palimpsest.tracks.bundles import LayerBundle, resolve_explicit_bundle
from palimpsest.tracks.requirements import LayerResolutionError

DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64


def _write(signals: Path, name: str, capability: dict, *, label: str, extra_meta: dict | None = None):
    meta: dict = {"label": label, "capability": capability}
    if extra_meta:
        meta.update(extra_meta)
    (signals / f"{name}.json").write_text(
        json.dumps({"metadata": meta, "segment_offsets": []}), encoding="utf-8"
    )


@pytest.fixture
def project(tmp_path: Path):
    signals = tmp_path / "signals"
    signals.mkdir()
    _write(signals, "chunking_ck", {
        "kind": "chunk", "size": 17, "mode": "word", "analyzable_digest": DIGEST,
    }, label="ck")
    _write(signals, "repeats_rp", {
        "kind": "repeat-set", "analyzable_digest": DIGEST,
    }, label="rp", extra_meta={"phrases": ["lorem ipsum dolor", "sit amet"]})
    _write(signals, "repeat_mask_ck_rp", {
        "kind": "repeat-mask", "chunk_layer_id": "ck", "repeat_layer_id": "rp",
        "chunk_analyzable_digest": DIGEST,
    }, label="ck_rp", extra_meta={"masked": [False, True]})
    _write(signals, "embedding_em", {
        "kind": "embedding", "chunk_layer_id": "ck", "chunk_analyzable_digest": DIGEST,
        "provider": "mlx", "model": "qwen", "dim": 8,
    }, label="em")
    return types.SimpleNamespace(path=tmp_path)


def test_happy_path_binds_all_three_and_reaches_phrases(project):
    bundle = resolve_explicit_bundle(
        project, "ck", "ck_rp", need_embedding=True, embedding_label="em"
    )
    assert isinstance(bundle, LayerBundle)
    assert bundle.chunk.label == "ck"
    assert bundle.repeat_mask.label == "ck_rp"
    assert bundle.embedding is not None and bundle.embedding.label == "em"
    assert bundle.chunk_size == 17
    assert bundle.repeat_phrases == ["lorem ipsum dolor", "sit amet"]


def test_text_only_skips_embedding(project):
    bundle = resolve_explicit_bundle(project, "ck", "ck_rp", need_embedding=False)
    assert bundle.embedding is None
    assert bundle.repeat_phrases  # still reached through the mask's repeat layer


def test_missing_chunk_layer_fails_loud(project):
    with pytest.raises(LayerResolutionError, match="chunk layer 'chunking_nope' not found"):
        resolve_explicit_bundle(project, "nope", "ck_rp", need_embedding=False)


def test_missing_repeat_mask_fails_loud(project):
    with pytest.raises(LayerResolutionError, match="repeat-mask layer 'repeat_mask_ck_xx' not found"):
        resolve_explicit_bundle(project, "ck", "ck_xx", need_embedding=False)


def test_repeat_mask_for_other_chunk_fails_loud(project, tmp_path):
    _write(tmp_path / "signals", "repeat_mask_other_rp", {
        "kind": "repeat-mask", "chunk_layer_id": "other", "repeat_layer_id": "rp",
        "chunk_analyzable_digest": DIGEST,
    }, label="other_rp", extra_meta={"masked": [False]})
    with pytest.raises(LayerResolutionError, match="built on chunk layer 'other', not 'ck'"):
        resolve_explicit_bundle(project, "ck", "other_rp", need_embedding=False)


def test_need_embedding_without_label_fails_loud(project):
    with pytest.raises(LayerResolutionError, match="no embedding_label was given"):
        resolve_explicit_bundle(project, "ck", "ck_rp", need_embedding=True)


def test_embedding_digest_mismatch_fails_loud(project, tmp_path):
    _write(tmp_path / "signals", "embedding_stale", {
        "kind": "embedding", "chunk_layer_id": "ck", "chunk_analyzable_digest": OTHER_DIGEST,
        "provider": "mlx", "model": "qwen", "dim": 8,
    }, label="stale")
    with pytest.raises(LayerResolutionError, match="different analyzable digest"):
        resolve_explicit_bundle(project, "ck", "ck_rp", need_embedding=True, embedding_label="stale")
