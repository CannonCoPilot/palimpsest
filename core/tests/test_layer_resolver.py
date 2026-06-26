"""Tests for the layer dependency-check resolver (Wave-0 P2, FR-7).

Builds real chunk layers with ChunkingTrack (direct extract → analyzable == original on an unmasked
project) and exercises resolve_layers: constraint filtering, digest matching, ambiguity tiebreak, and
fail-loud on no match.
"""

import json
import os
from pathlib import Path

import pytest

from palimpsest.project import ingest_file
from palimpsest.tracks.chunking_track import ChunkingTrack
from palimpsest.tracks.requirements import (
    LayerRequirement,
    LayerResolutionError,
    project_analyzable_digest,
    resolve_layers,
)
from palimpsest.tracks.registry import TrackRegistry


@pytest.fixture
def pp_project(pp_ch1_txt: Path, tmp_path: Path):
    return ingest_file(pp_ch1_txt, tmp_path, title="resolver-test")


def _chunk(project, **params) -> Path:
    track = ChunkingTrack()
    track.set_params(params)
    return track.extract(project)


def test_resolver_module_does_not_register_a_track():
    # The dataclasses in requirements.py must not be mistaken for track extractors by discovery.
    names = TrackRegistry.discover().names()
    assert "requirements" not in names
    assert {"chunking", "embedding"} <= set(names)


class TestResolveLayers:
    def test_binds_sole_survivor_by_constraint(self, pp_project):
        _chunk(pp_project, chunk_mode="word", chunk_size=5)
        _chunk(pp_project, chunk_mode="slide", chunk_size=10)
        bound = resolve_layers(
            pp_project, [LayerRequirement("chunk", {"overlapping": False})]
        )
        assert bound["chunk"].capability["mode"] == "word"
        assert bound["chunk"].capability["overlapping"] is False

    def test_constraint_selects_overlapping_layer(self, pp_project):
        _chunk(pp_project, chunk_mode="word", chunk_size=5)
        _chunk(pp_project, chunk_mode="slide", chunk_size=10)
        bound = resolve_layers(
            pp_project, [LayerRequirement("chunk", {"overlapping": True})]
        )
        assert bound["chunk"].capability["mode"] == "slide"

    def test_digest_match_filters_wrong_text(self, pp_project):
        _chunk(pp_project, chunk_mode="word", chunk_size=5)
        with pytest.raises(LayerResolutionError, match="analyzable digest"):
            resolve_layers(
                pp_project,
                [LayerRequirement("chunk", {"overlapping": False})],
                analyzable_digest="0" * 64,
            )

    def test_digest_match_passes_for_current_text(self, pp_project):
        _chunk(pp_project, chunk_mode="word", chunk_size=5)
        digest = project_analyzable_digest(pp_project, "")
        bound = resolve_layers(
            pp_project, [LayerRequirement("chunk", {})], analyzable_digest=digest
        )
        assert bound["chunk"].capability["analyzable_digest"] == digest

    def test_no_match_raises_listing_available(self, pp_project):
        _chunk(pp_project, chunk_mode="word", chunk_size=5)
        with pytest.raises(LayerResolutionError, match="no chunk layer satisfies"):
            resolve_layers(
                pp_project, [LayerRequirement("chunk", {"mode": "verse"}, digest_match=False)]
            )

    def test_ambiguity_binds_newest_by_mtime(self, pp_project):
        older = _chunk(pp_project, chunk_mode="word", chunk_size=5)
        newer = _chunk(pp_project, chunk_mode="word", chunk_size=9)
        # Both are non-overlapping word layers → two survivors; make mtimes unambiguous.
        os.utime(older, (1_000_000, 1_000_000))
        os.utime(newer, (2_000_000, 2_000_000))
        newer_label = json.loads(newer.read_text())["metadata"]["label"]
        bound = resolve_layers(
            pp_project,
            [LayerRequirement("chunk", {"overlapping": False}, digest_match=False)],
        )
        assert bound["chunk"].label == newer_label
