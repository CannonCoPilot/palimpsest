"""Tests for ChunkingTrack.hide_repeats — pre-chunk excision of a repeat layer (Wave-0 P8, FR-16).

These exercise the full masked-run path (``runner.extract_masked``), because the excision rides the
``view_mask_intervals`` hook the runner invokes before building the analysis view. The key contracts:
the repeats-hidden chunk layer's texts contain none of the repeated phrases; it content-addresses
distinctly from the un-hidden chunking and the two coexist; and its offsets stay in original bounds
(reusing the masking excise/remap substrate, no new coordinate math).
"""

import json
from pathlib import Path

import pytest

from palimpsest.project import ingest_file
from palimpsest.runner import extract_masked
from palimpsest.tracks.chunking_track import ChunkingTrack
from palimpsest.tracks.repeat_track import RepeatTrack

REFRAIN = "ancient mariner sailed onward"
PLANTED_TEXT = (
    "Filler one introduces the opening scene with assorted singular vocabulary here.\n"
    "Ancient mariner sailed onward through the gathering tempest.\n"
    "More entirely distinct narration follows across this particular middle passage now.\n"
    "Ancient mariner sailed onward beneath a pale clouded moon.\n"
    "Yet another stretch of wholly individual wording surfaces at precisely this juncture.\n"
    "Ancient mariner sailed onward across the immense churning deep.\n"
    "A final unrelated closing remark quietly concludes the brief sample excerpt.\n"
)


@pytest.fixture
def planted_project(tmp_path: Path):
    src = tmp_path / "planted.txt"
    src.write_text(PLANTED_TEXT, encoding="utf-8")
    return ingest_file(src, tmp_path / "proj", title="hide-repeats-test")


def _repeat_label(project) -> str:
    track = RepeatTrack()
    track.set_params({})
    path = extract_masked(project, track)
    return json.loads(Path(path).read_text())["metadata"]["label"]


def _chunk_layer(project, **params) -> dict:
    track = ChunkingTrack()
    track.set_params(params)
    path = extract_masked(project, track)
    return json.loads(Path(path).read_text())


class TestHideRepeats:
    def test_hidden_layer_excludes_repeats(self, planted_project):
        label = _repeat_label(planted_project)
        hidden = _chunk_layer(planted_project, chunk_mode="word", chunk_size=5, hide_repeats=label)
        joined = " ".join(hidden["metadata"]["chunk_texts"]).lower()
        assert REFRAIN not in joined, "repeats-hidden chunking must not contain the repeated phrase"
        assert "tempest" in joined, "non-repeat content must survive excision"

    def test_unhidden_layer_contains_repeats(self, planted_project):
        plain = _chunk_layer(planted_project, chunk_mode="word", chunk_size=5)
        joined = " ".join(plain["metadata"]["chunk_texts"]).lower()
        assert REFRAIN in joined, "ordinary chunking (no hide_repeats) keeps the repeated phrase"

    def test_hidden_label_distinct_and_coexists(self, planted_project):
        label = _repeat_label(planted_project)
        plain = _chunk_layer(planted_project, chunk_mode="word", chunk_size=5)
        hidden = _chunk_layer(planted_project, chunk_mode="word", chunk_size=5, hide_repeats=label)
        assert plain["name"] != hidden["name"], (
            "the excised-view digest must give the hidden layer a distinct content-addressed label"
        )
        chunk_files = list((planted_project.path / "signals").glob("chunking_*.json"))
        assert len(chunk_files) == 2, "hidden and un-hidden chunk layers must coexist"

    def test_hidden_offsets_round_trip_to_original(self, planted_project):
        # The chunk offsets are remapped analyzable->original via the same OffsetMap content masking
        # uses (G4): every span must lie within the ORIGINAL text bounds and stay ordered by start.
        label = _repeat_label(planted_project)
        hidden = _chunk_layer(planted_project, chunk_mode="word", chunk_size=5, hide_repeats=label)
        text_len = len(planted_project.reference_text())
        offsets = hidden["segment_offsets"]
        assert offsets
        for start, end in offsets:
            assert 0 <= start < end <= text_len
        for (s0, _e0), (s1, _e1) in zip(offsets, offsets[1:]):
            assert s0 <= s1

    def test_missing_repeat_layer_fails_loud(self, planted_project):
        track = ChunkingTrack()
        track.set_params({"chunk_mode": "word", "chunk_size": 5, "hide_repeats": "deadbeefdeadbeef"})
        with pytest.raises(ValueError, match="not found"):
            extract_masked(planted_project, track)
