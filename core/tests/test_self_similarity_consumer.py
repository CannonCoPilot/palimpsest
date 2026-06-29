"""Wave-0 P7 commit 3 — self_similarity as a fail-loud layer CONSUMER.

The track no longer chunks/embeds/masks: it binds explicit chunk + repeat_mask (+ embedding) layers and
reproduces the dotplot output contract from layer data. These tests plant layers on disk (computed with
the real chunker / masker so they are faithful) and cover: the equivalence guard (layer-sourced matrices
== legacy inline matrices), the manifest contract DotplotView depends on, multi-size, the embedding
path, fail-loud binding, param validation, transactional output, and the refinement label.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from palimpsest.project import ingest_file
from palimpsest.tracks.bundles import resolve_explicit_bundle
from palimpsest.tracks.chunking import ChunkingConfig, chunk_text
from palimpsest.tracks.repeats import find_exact_repeats, mask_repeats
from palimpsest.tracks.requirements import LayerResolutionError
from palimpsest.tracks.self_similarity import (
    SelfSimilarityTrack,
    _cosine_matrix,
    _edit_distance_matrix,
    _word_overlap_matrix,
    load_embeddings,
    reconstruct_chunks,
)
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

# A repeat-rich text. `_REFRAIN` recurs verbatim (a content n-gram occurring >= the 3-occurrence
# threshold, so `mask_repeats` flags the chunks it dominates), while two near-identical bag passages
# (block / swapped, adjacent words transposed) seed off-diagonal LASTZ alignments WITHOUT recurring
# verbatim — so they stay unmasked.
_BLOCK = (
    "lighthouse compass mariner tempest beacon anchor harbor voyage lantern rudder seagull "
    "driftwood meridian sextant fathom keel mast galleon cargo wharf pelican estuary saltmarsh "
    "cormorant barnacle schooner ballast hull tiller jib spinnaker capstan grommet halyard topsail"
).split()
_SWAPPED = _BLOCK[:]
for _i in range(0, len(_SWAPPED) - 1, 2):
    _SWAPPED[_i], _SWAPPED[_i + 1] = _SWAPPED[_i + 1], _SWAPPED[_i]
_FILLER = (
    "quarterly throughput logistics monsoon warehouse distribution overnight compliance auditor "
    "inventory shipment freight tariff customs broker pallet forklift loading dock manifest"
)
# Seven non-stopword content words, none shared with the block/swapped/filler vocab, repeated five
# times back-to-back so an interior word-7 chunk is fully covered by the repeat → masked above 0.5.
_REFRAIN = "formulaic refrain echoes thrice cascading persistent cadence"
_REPEATS = " ".join([_REFRAIN] * 5)
_TEXT = f"{' '.join(_BLOCK)}. {_FILLER}. {_REPEATS}. {' '.join(_SWAPPED)}."


def _project(tmp_path: Path):
    src = tmp_path / "src.txt"
    src.write_text(_TEXT, encoding="utf-8")
    return ingest_file(src, tmp_path, title="Consumer")


def _write_layer(signals: Path, name: str, capability: dict, *, label: str,
                 segment_offsets: list | None = None, extra_meta: dict | None = None) -> None:
    meta: dict[str, Any] = {"label": label, "capability": capability}
    if extra_meta:
        meta.update(extra_meta)
    (signals / f"{name}.json").write_text(
        json.dumps({"metadata": meta, "segment_offsets": segment_offsets or []}), encoding="utf-8"
    )


def _plant(project, *, mode: str = "word", size: int = 7, chunk_label: str = "ck",
           repeat_label: str = "rp", with_embedding: bool = False, embed_dim: int = 6) -> dict:
    """Chunk the project's text with the real chunker, mask it inline (the reference behaviour), and
    persist the result as chunk + repeats + repeat_mask (+ optional embedding) layers, returning the
    explicit input bundle and the masked reference chunks (for the equivalence guard)."""
    signals = project.path / "signals"
    signals.mkdir(parents=True, exist_ok=True)
    text = project.reference_text()
    chunks = chunk_text(text, ChunkingConfig(mode=mode, size=size))
    phrases = find_exact_repeats(chunks)
    mask_repeats(chunks, phrases)  # in-place; sets each chunk["masked"]

    digest = hashlib.sha256(f"{chunk_label}".encode()).hexdigest()
    offsets = [[c["start"], c["end"]] for c in chunks]
    _write_layer(signals, f"chunking_{chunk_label}",
                 {"kind": "chunk", "mode": mode, "size": size, "unit": "word",
                  "analyzable_digest": digest},
                 label=chunk_label, segment_offsets=offsets,
                 extra_meta={"chunk_texts": [c["text"] for c in chunks]})
    _write_layer(signals, f"repeats_{repeat_label}",
                 {"kind": "repeat-set", "analyzable_digest": digest},
                 label=repeat_label, extra_meta={"phrases": sorted(phrases)})
    rm_label = f"{chunk_label}_{repeat_label}"
    _write_layer(signals, f"repeat_mask_{rm_label}",
                 {"kind": "repeat-mask", "chunk_layer_id": chunk_label, "repeat_layer_id": repeat_label,
                  "coverage_threshold": 0.5, "chunk_analyzable_digest": digest},
                 label=rm_label, segment_offsets=offsets,
                 extra_meta={"masked": [bool(c.get("masked")) for c in chunks]})

    bundle: dict[str, str] = {"chunk_label": chunk_label, "repeat_mask_label": rm_label}
    if with_embedding:
        emb_label = f"em_{chunk_label}"
        rng = np.random.default_rng(abs(hash(chunk_label)) % (2**32))
        vectors = rng.standard_normal((len(chunks), embed_dim)).astype(np.float32)
        db = project.path / "cache" / f"embeddings_{emb_label}.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        store = SqliteVecStore(db, dim=embed_dim)
        store.add([f"i{k}" for k in range(len(vectors))], vectors.tolist(),
                  [{"chunk_index": k} for k in range(len(vectors))])
        store.close()
        _write_layer(signals, f"embedding_{emb_label}",
                     {"kind": "embedding", "chunk_layer_id": chunk_label,
                      "chunk_analyzable_digest": digest, "provider": "mlx", "model": "qwen",
                      "dim": embed_dim, "model_fingerprint": "fp0"},
                     label=emb_label, segment_offsets=offsets,
                     extra_meta={"vectorstore": f"cache/embeddings_{emb_label}.db"})
        bundle["embedding_label"] = emb_label
        return {"input": bundle, "chunks": chunks, "vectors": vectors}
    return {"input": bundle, "chunks": chunks}


def _run(project, inputs: list[dict], metrics: list[str]) -> dict:
    track = SelfSimilarityTrack()
    track.set_params({"inputs": inputs, "metrics": metrics})
    track.extract(project)
    return json.loads((project.path / "signals" / "self_similarity.json").read_text())


# --------------------------------------------------------------------------- equivalence guard

class TestEquivalenceGuard:
    """The crux of P7: layer-sourced chunks (texts + words=split + masked flag from layers) yield the
    SAME lexical matrices as the legacy inline path. No embedding service needed."""

    def test_word_overlap_and_edit_distance_match_inline(self, tmp_path):
        project = _project(tmp_path)
        planted = _plant(project)
        ref_chunks = planted["chunks"]  # already masked inline by _plant
        ref_wo = _word_overlap_matrix(ref_chunks)
        ref_ed = _edit_distance_matrix(ref_chunks)

        bundle = resolve_explicit_bundle(
            project, planted["input"]["chunk_label"], planted["input"]["repeat_mask_label"],
            need_embedding=False,
        )
        recon = reconstruct_chunks(bundle)
        assert np.array_equal(_word_overlap_matrix(recon), ref_wo)
        assert np.array_equal(_edit_distance_matrix(recon), ref_ed)

    def test_reconstructed_masked_flags_come_from_layer(self, tmp_path):
        project = _project(tmp_path)
        planted = _plant(project)
        bundle = resolve_explicit_bundle(
            project, planted["input"]["chunk_label"], planted["input"]["repeat_mask_label"],
            need_embedding=False,
        )
        recon = reconstruct_chunks(bundle)
        assert [c["masked"] for c in recon] == [bool(c.get("masked")) for c in planted["chunks"]]
        # at least one chunk is masked (the recurring phrase) — proves flags are non-trivial
        assert any(c["masked"] for c in recon)


# --------------------------------------------------------------------------- manifest contract

class TestManifestContract:
    def test_manifest_carries_frozen_fields_and_bins(self, tmp_path):
        project = _project(tmp_path)
        planted = _plant(project, size=7)
        manifest = _run(project, [planted["input"]], ["word_overlap", "edit_distance"])
        meta = manifest["metadata"]

        for field in ("available_metrics", "metric_info", "available_chunk_sizes",
                      "exact_repeats", "formulaic_patterns", "locked_constants", "layer_inputs"):
            assert field in meta, f"manifest missing {field}"
        assert manifest["dimensions"][0] == manifest["dimensions"][1] > 0
        assert manifest["segment_offsets"]
        assert set(meta["available_metrics"]) == {"word_overlap", "edit_distance"}
        assert meta["available_chunk_sizes"] == [7]
        n = manifest["dimensions"][0]
        assert meta["metric_info"]["word_overlap"]["dimensions"] == [n, n]

        signals = project.path / "signals"
        for metric in ("word_overlap", "edit_distance"):
            assert (signals / "self_similarity_cs7" / f"{metric}.bin").exists()
            assert (signals / f"self_similarity_{metric}.bin").exists()
        # exact_repeats sourced from the repeats layer (decision 3)
        assert meta["layer_inputs"][0]["repeat_mask_label"] == planted["input"]["repeat_mask_label"]

    def test_no_partial_files_after_success(self, tmp_path):
        project = _project(tmp_path)
        planted = _plant(project)
        _run(project, [planted["input"]], ["word_overlap"])
        assert list((project.path / "signals").rglob("*.partial")) == []


# --------------------------------------------------------------------------- multi-size

class TestMultiSize:
    def test_two_sizes_produce_both_dirs_and_sizes(self, tmp_path):
        project = _project(tmp_path)
        a = _plant(project, size=7, chunk_label="cka")
        b = _plant(project, size=13, chunk_label="ckb")
        manifest = _run(project, [a["input"], b["input"]], ["word_overlap"])
        meta = manifest["metadata"]
        assert meta["available_chunk_sizes"] == [7, 13]
        signals = project.path / "signals"
        assert (signals / "self_similarity_cs7" / "word_overlap.bin").exists()
        assert (signals / "self_similarity_cs13" / "word_overlap.bin").exists()
        # headline fields come from the PRIMARY (first) bundle = size 7
        assert meta["chunk_size"] == 7
        assert len(meta["layer_inputs"]) == 2


# --------------------------------------------------------------------------- embedding path

class TestEmbeddingConsumer:
    def test_cosine_matrix_matches_layer_vectors(self, tmp_path):
        project = _project(tmp_path)
        planted = _plant(project, with_embedding=True)
        manifest = _run(project, [planted["input"]], ["cosine"])
        n = manifest["dimensions"][0]

        buf = (project.path / "signals" / "self_similarity_cs7" / "cosine.bin").read_bytes()
        got = np.frombuffer(buf, dtype=np.float32).reshape(n, n)
        expected = _cosine_matrix(planted["vectors"])
        np.fill_diagonal(expected, 1.0)
        assert np.allclose(got, expected, atol=1e-5)
        assert manifest["metadata"]["embedding"]["model"] == "qwen"

    def test_load_embeddings_count_check(self, tmp_path):
        project = _project(tmp_path)
        planted = _plant(project, with_embedding=True)
        bundle = resolve_explicit_bundle(
            project, planted["input"]["chunk_label"], planted["input"]["repeat_mask_label"],
            need_embedding=True, embedding_label=planted["input"]["embedding_label"],
        )
        vecs = load_embeddings(project, bundle)
        assert vecs.shape == (len(planted["chunks"]), 6)


# --------------------------------------------------------------------------- fail-loud

class TestFailLoud:
    def test_missing_repeat_mask_raises(self, tmp_path):
        project = _project(tmp_path)
        _plant(project)
        track = SelfSimilarityTrack()
        track.set_params({"inputs": [{"chunk_label": "ck", "repeat_mask_label": "ck_nope"}],
                          "metrics": ["word_overlap"]})
        with pytest.raises(LayerResolutionError, match="repeat_mask_ck_nope"):
            track.extract(project)

    def test_cosine_without_embedding_label_raises(self, tmp_path):
        project = _project(tmp_path)
        planted = _plant(project)  # no embedding layer planted
        track = SelfSimilarityTrack()
        track.set_params({"inputs": [planted["input"]], "metrics": ["cosine"]})
        with pytest.raises(LayerResolutionError, match="no embedding_label"):
            track.extract(project)


# --------------------------------------------------------------------------- param validation

class TestParamValidation:
    def test_missing_inputs_rejected(self):
        track = SelfSimilarityTrack()
        track.set_params({"metrics": ["cosine"]})
        with pytest.raises(ValueError, match="'inputs' is required"):
            track.validate_params()

    def test_unknown_metric_rejected_synchronously(self):
        track = SelfSimilarityTrack()
        track.set_params({"inputs": [{"chunk_label": "a", "repeat_mask_label": "a_b"}],
                          "metrics": ["bogus"]})
        with pytest.raises(ValueError, match="unknown similarity metric"):
            track.validate_params()

    def test_inputs_json_string_parsed(self):
        track = SelfSimilarityTrack()
        track.set_params({"inputs": '[{"chunk_label":"a","repeat_mask_label":"a_b"}]'})
        resolved = track.resolved_params()
        assert resolved["inputs"] == [{"chunk_label": "a", "repeat_mask_label": "a_b"}]

    def test_malformed_input_object_rejected(self):
        track = SelfSimilarityTrack()
        track.set_params({"inputs": [{"chunk_label": "a"}]})  # missing repeat_mask_label
        with pytest.raises(ValueError, match="requires 'chunk_label' and 'repeat_mask_label'"):
            track.resolved_params()


# --------------------------------------------------------------------------- transactional output

class TestTransactional:
    def test_mid_run_failure_promotes_nothing(self, tmp_path, monkeypatch):
        import palimpsest.tracks.self_similarity as ss

        project = _project(tmp_path)
        planted = _plant(project)
        track = SelfSimilarityTrack()
        # Canonical order (word_overlap before edit_distance): word_overlap stages first, then
        # edit_distance raises — the run dies after one metric is staged but before commit.
        track.set_params({"inputs": [planted["input"]], "metrics": ["word_overlap", "edit_distance"]})
        monkeypatch.setattr(ss, "_edit_distance_matrix",
                            lambda chunks: (_ for _ in ()).throw(RuntimeError("boom")))
        with pytest.raises(RuntimeError, match="boom"):
            track.extract(project)
        signals = project.path / "signals"
        assert not (signals / "self_similarity.json").exists()
        assert not (signals / "self_similarity_word_overlap.bin").exists()
        assert not (signals / "self_similarity_cs7" / "word_overlap.bin").exists()
        assert list(signals.rglob("*.partial")) == []


# --------------------------------------------------------------------------- refinement label

class TestRefinementLabel:
    @pytest.mark.parametrize("mode, expected", [("word", "exact"), ("slide", "approximate")])
    def test_refinement_from_chunk_capability(self, tmp_path, mode, expected):
        project = _project(tmp_path)
        planted = _plant(project, mode=mode, size=10)
        manifest = _run(project, [planted["input"]], ["word_overlap", "edit_distance"])
        for info in manifest["metadata"]["metric_info"].values():
            assert info["alignment_refinement"] == expected
