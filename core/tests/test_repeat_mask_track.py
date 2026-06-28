"""Tests for RepeatMaskTrack — the post-chunk, flag-only repeat-mask layer (Wave-0 P8, FR-17).

The track binds a chunk layer + a repeat layer through the resolver (FR-7) and flags repeat-dominated
chunks. The contracts under test: it fails loud when a required layer is absent; its flags are
index-aligned to the bound chunk layer; and — the load-bearing equivalence — it flags exactly the
chunks ``self_similarity``'s inline pass flags at the default threshold.
"""

import json
from pathlib import Path

import pytest

from palimpsest.project import ingest_file
from palimpsest.runner import extract_masked
from palimpsest.tracks.chunking import ChunkingConfig, chunk_text
from palimpsest.tracks.chunking_track import ChunkingTrack
from palimpsest.tracks.repeat_mask_track import RepeatMaskTrack
from palimpsest.tracks.repeat_track import RepeatTrack
from palimpsest.tracks.repeats import find_exact_repeats, mask_repeats
from palimpsest.tracks.requirements import LayerResolutionError

CHUNK_SIZE = 7
PLANTED_TEXT = (
    "Filler one introduces the opening scene with assorted singular vocabulary here.\n"
    "Ancient mariner sailed onward through the gathering tempest of dusk.\n"
    "More entirely distinct narration follows across this particular middle passage now.\n"
    "Ancient mariner sailed onward beneath a pale and clouded waning moon.\n"
    "Yet another stretch of wholly individual wording surfaces at precisely this juncture.\n"
    "Ancient mariner sailed onward across the immense and churning open deep.\n"
    "A final unrelated closing remark quietly concludes the brief little sample excerpt.\n"
)


@pytest.fixture
def planted_project(tmp_path: Path):
    src = tmp_path / "planted.txt"
    src.write_text(PLANTED_TEXT, encoding="utf-8")
    return ingest_file(src, tmp_path / "proj", title="repeat-mask-test")


def _chunk_layer(project, chunk_size=CHUNK_SIZE) -> str:
    track = ChunkingTrack()
    track.set_params({"chunk_mode": "word", "chunk_size": chunk_size})
    path = extract_masked(project, track)
    return json.loads(Path(path).read_text())["metadata"]["label"]


def _repeat_layer(project) -> str:
    track = RepeatTrack()
    track.set_params({})
    path = extract_masked(project, track)
    return json.loads(Path(path).read_text())["metadata"]["label"]


def _run_mask(project, **params) -> dict:
    track = RepeatMaskTrack()
    track.set_params(params)
    path = extract_masked(project, track)
    return json.loads(Path(path).read_text())


def _inline_expected(project, threshold=None) -> list[bool]:
    """What self_similarity's inline repeat pass flags for word/size-7 chunks at the given threshold."""
    ref = project.reference_text()
    cfg = ChunkingConfig(
        mode="word", size=CHUNK_SIZE, smart_unit=None, delimiters=None,
        grow_factor=None, remainder_ratio=None,
    )
    chunks = chunk_text(ref, cfg)
    repeats = find_exact_repeats(ref, chunks)
    if threshold is None:
        mask_repeats(chunks, repeats)
    else:
        mask_repeats(chunks, repeats, threshold)
    return [bool(c["masked"]) for c in chunks]


class TestRepeatMaskTrackProtocol:
    def test_required_attributes(self):
        t = RepeatMaskTrack()
        assert t.name == "repeat_mask"
        assert t.output_type == "signal"
        assert t.depends_on == ["chunking", "repeats"]


class TestRepeatMaskExtract:
    def test_persists_named_layer(self, planted_project):
        clabel = _chunk_layer(planted_project)
        rlabel = _repeat_layer(planted_project)
        m = _run_mask(planted_project)
        assert m["name"] == f"repeat_mask_{clabel}_{rlabel}"
        assert m["type"] == "repeat-mask-layer"
        cap = m["metadata"]["capability"]
        assert cap["kind"] == "repeat-mask"
        assert cap["chunk_layer_id"] == clabel
        assert cap["repeat_layer_id"] == rlabel

    def test_index_aligned_to_chunk_layer(self, planted_project):
        clabel = _chunk_layer(planted_project)
        _repeat_layer(planted_project)
        chunk_manifest = json.loads(
            (planted_project.path / "signals" / f"chunking_{clabel}.json").read_text()
        )
        n_chunks = len(chunk_manifest["metadata"]["chunk_texts"])
        m = _run_mask(planted_project)
        masked = m["metadata"]["masked"]
        assert len(masked) == n_chunks
        assert len(m["segment_offsets"]) == n_chunks
        assert m["metadata"]["stats"]["chunk_count"] == n_chunks

    def test_matches_self_similarity_inline_at_default(self, planted_project):
        _chunk_layer(planted_project)
        _repeat_layer(planted_project)
        m = _run_mask(planted_project)
        assert m["metadata"]["masked"] == _inline_expected(planted_project)

    def test_threshold_is_open_and_reported(self, planted_project):
        _chunk_layer(planted_project)
        _repeat_layer(planted_project)
        # threshold 0.0: any chunk with any repeat-covered content is flagged — strictly more (or equal)
        # masking than the default, and at least one chunk (the refrain-bearing ones) is flagged.
        m0 = _run_mask(planted_project, coverage_threshold=0.0)
        assert m0["metadata"]["capability"]["coverage_threshold"] == 0.0
        assert m0["metadata"]["stats"]["masked_count"] > 0
        assert m0["metadata"]["masked"] == _inline_expected(planted_project, threshold=0.0)


class TestRepeatMaskFailLoud:
    def test_missing_repeat_layer_raises(self, planted_project):
        _chunk_layer(planted_project)  # chunk layer only — no repeat layer
        track = RepeatMaskTrack()
        track.set_params({})
        with pytest.raises(LayerResolutionError):
            extract_masked(planted_project, track)

    def test_missing_chunk_layer_raises(self, planted_project):
        _repeat_layer(planted_project)  # repeat layer only — no chunk layer
        track = RepeatMaskTrack()
        track.set_params({})
        with pytest.raises(LayerResolutionError):
            extract_masked(planted_project, track)
