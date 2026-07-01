"""Tests for RepeatTrack — the chunk-independent repeat-detection layer-track (Wave-0 P8, FR-15).

Run directly on an ingested project (no masking view), so repeat ``segment_offsets`` stay in original
coordinates and must anchor to the reference text. The masked-run + remap path is shared with
ChunkingTrack (covered by the runner/CLI parity tests); here the focus is detection correctness, the
capability/rendering/stats manifest backbone, and the ``self_similarity`` byte-identity guard.
"""

import copy
import json
from pathlib import Path

import pytest

from palimpsest.project import ingest_file
from palimpsest.tracks.base import TrackExtractor
from palimpsest.tracks.registry import TrackRegistry
from palimpsest.tracks.repeat_track import RepeatTrack
from palimpsest.tracks.repeats import (
    MASK_COVERAGE_THRESHOLD,
    _count_repeats,
    detect_repeats,
    find_exact_repeats,
    mask_repeats,
)

# A passage with one planted refrain ("ancient mariner sailed onward", all content words) recurring
# three times among otherwise-unique filler — so detection is deterministic at the default params
# (min_words=3, min_occurrences=3) and absent at min_occurrences=4.
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
    return ingest_file(src, tmp_path / "proj", title="repeat-track-test")


def _run(project, **params) -> dict:
    track = RepeatTrack()
    track.set_params(params)
    manifest_path = track.extract(project)
    return json.loads(manifest_path.read_text())


class TestRepeatTrackProtocol:
    def test_is_track_extractor(self):
        assert isinstance(RepeatTrack(), TrackExtractor)

    def test_required_attributes(self):
        t = RepeatTrack()
        assert t.name == "repeats"
        assert t.output_type == "signal"
        assert isinstance(t.depends_on, list) and t.depends_on == []
        assert t.lfo_types == ["signal.repeats"]
        assert t.evidence_level in ("E1", "E2", "E3", "E4", "E5")

    def test_auto_discovered(self):
        registry = TrackRegistry.discover()
        assert "repeats" in registry.names()
        assert registry.get("repeats") is RepeatTrack


class TestRepeatTrackExtract:
    def test_writes_label_keyed_layer(self, planted_project):
        track = RepeatTrack()
        track.set_params({})
        path = track.extract(planted_project)
        assert path.exists()
        assert path.name.startswith("repeats_") and path.suffix == ".json"
        assert path.parent == planted_project.path / "signals"

    def test_manifest_core_fields(self, planted_project):
        m = _run(planted_project)
        assert m["type"] == "repeat-layer"
        assert m["name"].startswith("repeats_")
        assert m["segment_offsets"], "repeat intervals must be emitted as segment_offsets (remap-handled)"
        assert m["dimensions"] == [len(m["segment_offsets"])]

    def test_detects_planted_refrain(self, planted_project):
        m = _run(planted_project)
        phrases = m["metadata"]["phrases"]
        # the planted 4-word refrain (and its constituent 3-grams) must be found
        assert "ancient mariner sailed onward" in phrases
        # three well-separated occurrences -> three disjoint intervals
        assert m["metadata"]["stats"]["interval_count"] == 3

    def test_intervals_anchor_to_text(self, planted_project):
        # Run directly (no masking view) so intervals are original coordinates; each must be in-bounds,
        # and the merged interval list must be ordered + strictly disjoint.
        m = _run(planted_project)
        text = planted_project.reference_text()
        offsets = m["segment_offsets"]
        for start, end in offsets:
            assert 0 <= start < end <= len(text)
            assert "ancient mariner sailed onward" in text[start:end].lower()
        for (s0, e0), (s1, e1) in zip(offsets, offsets[1:]):
            assert e0 <= s1, "intervals must be ordered and disjoint (merged spans)"

    def test_capability_descriptor(self, planted_project):
        m = _run(planted_project)
        cap = m["metadata"]["capability"]
        assert cap["kind"] == "repeat-set"
        assert cap["min_words"] == 3
        assert cap["min_occurrences"] == 3
        assert cap["max_phrase_len"] == 7
        assert isinstance(cap["analyzable_digest"], str) and len(cap["analyzable_digest"]) == 64

    def test_rendering_backbone(self, planted_project):
        m = _run(planted_project)
        rendering = m["metadata"]["rendering"]
        assert rendering["track_view"] == "repeat-band"
        assert rendering["overviewBarRendering"]["type"] == "repeat-band"

    def test_stats_backbone(self, planted_project):
        m = _run(planted_project)
        stats = m["metadata"]["stats"]
        assert stats["phrase_count"] >= 1
        assert stats["interval_count"] == len(m["segment_offsets"])
        assert 0.0 < stats["coverage_pct"] <= 100.0

    def test_open_param_changes_result_and_is_reported(self, planted_project):
        # min_occurrences=4 must drop the thrice-occurring refrain (open param changes the result), and
        # the chosen value is echoed in provenance (G2 — never silently defaulted).
        m = _run(planted_project, min_occurrences=4)
        assert "ancient mariner sailed onward" not in m["metadata"]["phrases"]
        assert m["metadata"]["capability"]["min_occurrences"] == 4
        assert m["metadata"]["params"]["repeats.min_occurrences"] == 4


class TestRepeatTrackPlurality:
    def test_distinct_params_distinct_layer(self, planted_project):
        a = _run(planted_project, min_occurrences=3)
        b = _run(planted_project, min_occurrences=2)
        assert a["name"] != b["name"], "different detection params must produce different layers"
        both = list((planted_project.path / "signals").glob("repeats_*.json"))
        assert len(both) == 2, "plural repeat layers must coexist without collision"

    def test_label_is_deterministic(self, planted_project):
        first = _run(planted_project)["name"]
        second = _run(planted_project)["name"]
        assert first == second


class TestByteIdentityGuard:
    """The new text-level path must not change what the chunk-based path (self_similarity's) finds, and
    opening coverage_threshold must not change the default masking decision."""

    def test_text_path_agrees_with_chunk_path(self):
        # Feed the same word list to both paths with a matched n-gram ceiling: identical phrase set.
        words = PLANTED_TEXT.split()
        chunks = [{
            "index": 0, "start": 0, "end": len(PLANTED_TEXT),
            "text": PLANTED_TEXT, "words": words,
        }]
        chunk_phrases = find_exact_repeats(chunks)
        text_phrases, _intervals = detect_repeats(PLANTED_TEXT, max_phrase_len=len(words) // 2)
        assert text_phrases == chunk_phrases
        assert "ancient mariner sailed onward" in text_phrases

    def test_mask_repeats_default_threshold_matches_explicit(self):
        words = PLANTED_TEXT.split()
        chunks = [
            {"index": i, "words": words[i * 5:(i + 1) * 5]}
            for i in range(len(words) // 5)
        ]
        repeats = find_exact_repeats([{"words": words}])
        default = mask_repeats(copy.deepcopy(chunks), repeats)
        explicit = mask_repeats(copy.deepcopy(chunks), repeats, MASK_COVERAGE_THRESHOLD)
        assert [c["masked"] for c in default] == [c["masked"] for c in explicit]


class TestEmptyTokenBoundary:
    """An empty token in the normalised stream marks a text boundary (a pilcrow/paragraph split).
    An n-gram straddling one is not a contiguous phrase and must be skipped, rather than joined into
    a space-padded key that pollutes — or even reaches the threshold of — the phrase tally."""

    def test_grams_spanning_empty_boundary_are_dropped(self):
        # "a|b a|b" across two boundaries: the only recurring bigrams straddle empty tokens, so a
        # correct tally finds nothing. The old all-stopword-only guard admitted "a "/" b" keys that
        # each reached occurrence 2 — phantom phrases from the boundary.
        result = _count_repeats(["a", "", "b", "a", "", "b"], min_words=2, min_occurrences=2, max_ngram=2)
        assert result == set()

    def test_empty_token_is_a_hard_separator(self):
        # "alpha beta" recurs contiguously twice; the boundary between the copies must not let the
        # tally merge "beta … alpha" into a phantom phrase, and no key carries a space artifact.
        result = _count_repeats(["alpha", "beta", "", "alpha", "beta"], min_words=2, min_occurrences=2, max_ngram=3)
        assert result == {"alpha beta"}
        assert all(k == k.strip() and "  " not in k for k in result)
