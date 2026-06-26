"""Unit tests for self-similarity pipeline — chunk positions, scoring, calibration, alignment."""

from __future__ import annotations

import numpy as np
import pytest

from palimpsest.tracks.self_similarity import (
    LASTZ_SMALL_SAMPLE_THRESHOLD,
    LOCKED_CONSTANTS,
    METRICS,
    SelfSimilarityTrack,
    _build_word_positions,
    _chunk_text,
    _char_identity,
    _banded_lcs_identity,
    _calibrate_threshold,
    _content_tokens,
    _embed_cache_label,
    _edit_distance_tokens,
    _edit_distance_matrix,
    _find_exact_repeats,
    _find_local_optima,
    _extend_alignment,
    _mask_repeats,
    _word_overlap_matrix,
    _lastz_align,
    _sliding_window_refine,
)


class TestBuildWordPositions:
    def test_basic(self):
        words, positions = _build_word_positions("the quick brown fox")
        assert words == ["the", "quick", "brown", "fox"]
        assert positions[0] == (0, 3)
        assert positions[1] == (4, 9)
        assert positions[3] == (16, 19)

    def test_extra_whitespace(self):
        words, positions = _build_word_positions("  hello   world  ")
        assert words == ["hello", "world"]
        assert positions[0] == (2, 7)
        assert positions[1] == (10, 15)

    def test_empty(self):
        words, positions = _build_word_positions("")
        assert words == []
        assert positions == []


class TestChunkText:
    def test_round_trip(self):
        text = "the quick brown fox jumps over the lazy dog and the cat sat on the mat"
        chunks = _chunk_text(text, 5)
        for c in chunks:
            assert text[c["start"]:c["end"]] == c["text"], f"Chunk {c['index']} position mismatch"

    def test_repeated_words(self):
        text = "the fox and the cat and the dog and the bird"
        chunks = _chunk_text(text, 5)
        for c in chunks:
            assert text[c["start"]:c["end"]] == c["text"], (
                f"Chunk {c['index']}: positions [{c['start']}:{c['end']}] give "
                f"'{text[c['start']:c['end']]}' but expected '{c['text']}'"
            )

    def test_short_tail_is_kept(self):
        # No silent tail drop: a text shorter than the window is one chunk covering all words.
        text = "one two three four"
        chunks = _chunk_text(text, 5)
        assert len(chunks) == 1
        assert chunks[0]["words"] == ["one", "two", "three", "four"]

    def test_chunk_count(self):
        words = ["w"] * 50
        text = " ".join(words)
        chunks = _chunk_text(text, 10)
        assert len(chunks) == 5


class TestCharIdentity:
    def test_identical(self):
        assert _char_identity("hello world", "hello world") == pytest.approx(1.0)

    def test_empty(self):
        assert _char_identity("", "hello") == 0.0
        assert _char_identity("hello", "") == 0.0

    def test_completely_different(self):
        score = _char_identity("aaaa", "bbbb")
        assert score == 0.0

    def test_partial_match(self):
        score = _char_identity("abcdef", "abcxyz")
        assert 0.0 < score < 1.0

    def test_symmetric(self):
        a, b = "the quick brown fox", "the slow brown cat"
        assert _char_identity(a, b) == pytest.approx(_char_identity(b, a))


class TestBandedLcsIdentity:
    def test_consistent_with_char_identity_on_short_strings(self):
        a = "the quick brown fox"
        b = "the quick brown cat"
        full = _char_identity(a, b)
        banded = _banded_lcs_identity(a, b, bandwidth=200)
        assert banded == pytest.approx(full, abs=0.001)

    def test_long_strings(self):
        a = "word " * 200
        b = "word " * 200
        score = _banded_lcs_identity(a, b, bandwidth=200)
        assert score > 0.9


class TestCalibrateThreshold:
    def test_returns_positive(self):
        chunks = [{"words": ["the", "quick", "brown", "fox", "jumps"]} for _ in range(20)]
        threshold = _calibrate_threshold(chunks, n_samples=100)
        assert threshold > 0.0

    def test_small_input_fallback(self):
        chunks = [{"words": ["a"]}] * 5
        threshold = _calibrate_threshold(chunks)
        # the small-sample fallback is the declared LOCKED_CONSTANT, not a magic literal
        assert threshold == LASTZ_SMALL_SAMPLE_THRESHOLD

    def test_deterministic(self):
        chunks = [{"words": ["word", str(i), "test", "the", "and"]} for i in range(50)]
        t1 = _calibrate_threshold(chunks, n_samples=200)
        t2 = _calibrate_threshold(chunks, n_samples=200)
        assert t1 == t2


class TestLockedConstants:
    """The LASTZ calibration + repeat-masking cutoffs are declared and reported, not hidden function
    defaults (audit A3 / design §6 — locked ≠ hidden)."""

    def test_parameters_report_locked_constants(self):
        params = SelfSimilarityTrack().parameters()
        assert params["self_similarity.locked_constants"] == LOCKED_CONSTANTS
        # the cutoffs that decide the alignment threshold and what text is masked are visible
        assert LOCKED_CONSTANTS["calibration"]["percentile"] == 0.95
        assert LOCKED_CONSTANTS["masking"]["coverage_threshold"] == 0.5

    def test_provenance_exposes_constants_bare(self):
        from palimpsest.tracks.params import track_provenance

        # track_provenance runs post-run via validate_params(); give it a valid embedding-free config
        # (word_overlap + edit_distance need no embeddings) so validation passes as it would after a run.
        track = SelfSimilarityTrack()
        track.set_params({
            "metrics": ["word_overlap", "edit_distance"],
            "chunk_mode": "word",
            "chunk_size": 7,
        })
        prov = track_provenance(track)
        # prefix stripped — the run record reconstructs the cutoffs that produced the matrix (P3)
        assert prov["locked_constants"] == LOCKED_CONSTANTS


class TestEditDistanceTokens:
    def test_identical(self):
        assert _edit_distance_tokens(["a", "b"], ["a", "b"]) == 0

    def test_completely_different(self):
        assert _edit_distance_tokens(["a"], ["b"]) == 1

    def test_empty(self):
        assert _edit_distance_tokens([], ["a", "b"]) == 2
        assert _edit_distance_tokens(["a"], []) == 1


class TestFindLocalOptima:
    def test_finds_known_optima(self):
        matrix = np.zeros((10, 10), dtype=np.float32)
        matrix[2, 7] = 0.9
        matrix[7, 2] = 0.9
        optima = _find_local_optima(matrix, k=2, min_gap=1)
        assert len(optima) >= 1
        assert optima[0][2] == pytest.approx(0.9)

    def test_excludes_diagonal(self):
        matrix = np.eye(10, dtype=np.float32)
        optima = _find_local_optima(matrix, k=5, min_gap=3)
        assert len(optima) == 0


class TestWordOverlapMatrix:
    def test_self_similarity_is_one(self):
        chunks = [
            {"words": ["the", "quick", "brown", "fox"]},
            {"words": ["the", "quick", "brown", "fox"]},
        ]
        matrix = _word_overlap_matrix(chunks)
        assert matrix[0, 0] == pytest.approx(1.0)
        assert matrix[0, 1] == pytest.approx(1.0)

    def test_no_overlap(self):
        chunks = [
            {"words": ["alpha", "beta"]},
            {"words": ["gamma", "delta"]},
        ]
        matrix = _word_overlap_matrix(chunks)
        assert matrix[0, 1] == pytest.approx(0.0)


class TestExtendAlignment:
    def test_finds_planted_repeat(self):
        repeated = "alpha beta gamma delta epsilon"
        different = "one two three four five"
        text = f"{repeated} {different} {repeated} {different}"
        chunks = _chunk_text(text, 5)
        assert len(chunks) >= 4
        result = _extend_alignment(text, chunks, 0, 2, threshold=0.3, chunk_size=5)
        if result is not None:
            assert result["identity"] > 0.3


class TestSlidingWindowRefine:
    def test_refines_boundaries(self):
        text = "AAA BBB CCC DDD EEE FFF GGG HHH III JJJ"
        words, positions = _build_word_positions(text)
        refined = _sliding_window_refine(
            text, words, positions,
            coarse_start_a=0, coarse_end_a=11,
            coarse_start_b=20, coarse_end_b=31,
            chunk_size=3, threshold=0.0,
        )
        assert len(refined) == 4
        assert refined[0] >= 0
        assert refined[1] <= len(text)


class TestRepeatMasking:
    """Covers the repeat-masking subsystem (previously untested — audit E-NEW2)."""

    def _repeat_text(self) -> str:
        phrase = "alpha beta gamma delta epsilon"
        fillers = ["one two three four five", "six seven eight nine ten",
                   "red green blue cyan gold", "north south east west center"]
        parts = []
        for f in fillers:
            parts.append(phrase)
            parts.append(f)
        return " ".join(parts)

    def test_find_exact_repeats_detects_phrase(self):
        text = self._repeat_text()
        chunks = _chunk_text(text, 5)
        repeats = _find_exact_repeats(text, chunks, min_words=3, min_occurrences=3)
        assert "alpha beta gamma delta epsilon" in repeats

    def test_find_exact_repeats_ignores_unique_phrases(self):
        text = "alpha beta gamma one two three four five six seven eight nine ten"
        chunks = _chunk_text(text, 5)
        repeats = _find_exact_repeats(text, chunks, min_words=3, min_occurrences=3)
        assert repeats == set()

    def test_mask_repeats_marks_dominated_chunks(self):
        text = self._repeat_text()
        chunks = _chunk_text(text, 5)
        repeats = _find_exact_repeats(text, chunks, min_words=3, min_occurrences=3)
        _mask_repeats(chunks, repeats)
        # The phrase-only chunks (every other chunk) must be masked.
        masked_texts = {c["text"] for c in chunks if c.get("masked")}
        assert any("alpha beta gamma delta epsilon" in t for t in masked_texts)
        # At least one filler chunk must remain unmasked.
        assert any(not c.get("masked") for c in chunks)

    def test_mask_repeats_empty_set_unmasks_all(self):
        chunks = _chunk_text("one two three four five six seven eight nine ten", 5)
        _mask_repeats(chunks, set())
        assert all(c["masked"] is False for c in chunks)

    def test_matrix_builders_skip_masked_chunks(self):
        """E3 contract: masked chunks must produce zero matrix cells. The extract
        loop relies on this holding for every metric, not just the first."""
        chunks = [
            {"words": ["alpha", "beta", "gamma", "delta"], "masked": True},
            {"words": ["alpha", "beta", "gamma", "delta"], "masked": False},
            {"words": ["alpha", "beta", "gamma", "delta"], "masked": False},
        ]
        for builder in (_word_overlap_matrix, _edit_distance_matrix):
            matrix = builder(chunks)
            # Row/col 0 is masked → all its cells stay 0 (including the diagonal).
            assert np.all(matrix[0, :] == 0.0)
            assert np.all(matrix[:, 0] == 0.0)
            # The two unmasked identical chunks still score high.
            assert matrix[1, 2] > 0.0

    def test_lastz_copy_preserves_shared_mask(self):
        """E3 regression: building an unmasked LASTZ view must not clear masks on
        the shared per-chunk-size cache that later metrics reuse."""
        cached_chunks = [
            {"words": ["alpha", "beta"], "masked": True},
            {"words": ["one", "two"], "masked": False},
        ]
        lastz_chunks = [{**c, "masked": False} for c in cached_chunks]
        assert all(c["masked"] is False for c in lastz_chunks)
        # The shared cache is untouched — metric #2 will still see the mask.
        assert cached_chunks[0]["masked"] is True


class TestMetricSelection:
    """Covers E1 subset-compute: per-metric checkboxes drive which metrics run."""

    def test_default_selects_all_metrics(self):
        track = SelfSimilarityTrack()
        assert track._selected_metrics == list(METRICS)

    def test_set_params_narrows_selection(self):
        track = SelfSimilarityTrack()
        track.set_params({"metrics": ["cosine", "edit_distance"]})
        assert track._selected_metrics == ["cosine", "edit_distance"]

    def test_invalid_metric_stored_raw_then_rejected(self):
        # R6: set_params no longer silently filters — the value is stored verbatim and
        # validate_params rejects the unknown metric (instead of quietly dropping it).
        track = SelfSimilarityTrack()
        track.set_params({"metrics": ["bogus", "jaccard"], "chunk_mode": "word", "chunk_size": 7})
        assert track._selected_metrics == ["bogus", "jaccard"]
        with pytest.raises(ValueError, match="unknown self_similarity metric"):
            track.validate_params()

    def test_all_invalid_metrics_rejected_not_silently_kept(self):
        # R6: previously an all-invalid selection silently fell back to running *all* metrics; now it
        # is rejected.
        track = SelfSimilarityTrack()
        track.set_params({"metrics": ["nonsense"], "chunk_mode": "word", "chunk_size": 7})
        with pytest.raises(ValueError, match="unknown self_similarity metric"):
            track.validate_params()


class TestPerMetricChunkSize:
    """Covers E-NEW1 consumer side: per-metric chunk sizes resolve correctly."""

    def test_shared_chunk_size_applies_to_all(self):
        track = SelfSimilarityTrack()
        track.set_params({"chunk_size": 12})
        assert track._chunk_size_for("cosine") == 12
        assert track._chunk_size_for("jaccard") == 12

    def test_per_metric_override_takes_precedence(self):
        track = SelfSimilarityTrack()
        track.set_params({"chunk_size": 12, "chunk_size_cosine": 20})
        assert track._chunk_size_for("cosine") == 20
        assert track._chunk_size_for("jaccard") == 12

    def test_chunk_size_not_clamped(self):
        # Stage parameters are stored verbatim — no silent clamping. Out-of-range values are
        # rejected later by ChunkingConfig / the API, never quietly rewritten here.
        track = SelfSimilarityTrack()
        track.set_params({"chunk_size_cosine": 999})
        assert track._chunk_size_for("cosine") == 999


class TestEmbedCacheLabel:
    """R5: the embedding cache key hashes the actual content + embedding identity, so no two runs
    that would produce different vectors can ever share a cache file (the prior label encoded only
    mode+size+sanitized-model and silently collided)."""

    @staticmethod
    def _cfg(**kw):
        from palimpsest.tracks.embedding import EmbeddingConfig
        base = dict(provider="mlx", endpoint="http://x", model="m", batch_size=8)
        base.update(kw)
        return EmbeddingConfig(**base)

    def test_differs_when_chunk_text_differs(self):
        # Different chunk boundaries (e.g. different smart params / separator) → different texts.
        cfg = self._cfg()
        a = _embed_cache_label("smart_cs7", [{"text": "alpha"}, {"text": "beta"}], cfg)
        b = _embed_cache_label("smart_cs7", [{"text": "alpha"}, {"text": "gamma"}], cfg)
        assert a != b

    def test_same_when_only_batch_size_differs(self):
        # batch_size changes how vectors are requested, not their values → cache is reused.
        chunks = [{"text": "alpha"}, {"text": "beta"}]
        assert _embed_cache_label("word_cs7", chunks, self._cfg(batch_size=8)) == \
               _embed_cache_label("word_cs7", chunks, self._cfg(batch_size=64))

    def test_differs_on_model_provider_endpoint(self):
        chunks = [{"text": "alpha"}]
        base = _embed_cache_label("word_cs7", chunks, self._cfg())
        assert _embed_cache_label("word_cs7", chunks, self._cfg(model="m2")) != base
        assert _embed_cache_label("word_cs7", chunks, self._cfg(provider="ollama")) != base
        assert _embed_cache_label("word_cs7", chunks, self._cfg(endpoint="http://y")) != base

    def test_sanitization_collision_regression(self):
        # "a:b" and "a/b" both sanitized to "a_b" in the old label → stale-cache collision. The hash
        # of the raw model name keeps them distinct.
        chunks = [{"text": "alpha"}]
        assert _embed_cache_label("word_cs7", chunks, self._cfg(model="a:b")) != \
               _embed_cache_label("word_cs7", chunks, self._cfg(model="a/b"))

    def test_label_is_filesystem_safe(self):
        import re
        label = _embed_cache_label("smart_cs7", [{"text": "a:b/c d"}], self._cfg(model="x/y:z"))
        assert re.fullmatch(r"[A-Za-z0-9._-]+", label)


class TestMetricValidation:
    """R6: an unknown or empty metric selection is rejected, not silently dropped (the old code kept
    only recognized metrics and, if none survived, silently ran all of them)."""

    def test_empty_metric_selection_rejected(self):
        track = SelfSimilarityTrack()
        track.set_params({"metrics": [], "chunk_mode": "word", "chunk_size": 7})
        with pytest.raises(ValueError, match="at least one metric"):
            track.validate_params()

    def test_unknown_singular_metric_rejected(self):
        track = SelfSimilarityTrack()
        track.set_params({
            "metric": "cosin", "metrics": ["word_overlap"],
            "chunk_mode": "word", "chunk_size": 7,
        })
        with pytest.raises(ValueError, match="unknown self_similarity metric"):
            track.validate_params()

    def test_valid_metrics_pass(self):
        track = SelfSimilarityTrack()
        track.set_params({
            "metrics": ["word_overlap", "edit_distance"],
            "chunk_mode": "word", "chunk_size": 7,
        })
        # No embedding needed for these lexical metrics; valid selection returns the echo-back dict.
        assert isinstance(track.validate_params(), dict)

    def test_unknown_param_rejected(self):
        """G1/A4: self-similarity rejects an undeclared parameter instead of silently ignoring it."""
        track = SelfSimilarityTrack()
        track.set_params({
            "metrics": ["word_overlap"], "chunk_mode": "word", "chunk_size": 7,
            "bogus_param": 1,
        })
        with pytest.raises(ValueError, match="unknown parameter.*bogus_param"):
            track.validate_params()

    def test_non_numeric_chunk_size_raises_valueerror_not_silent(self):
        """G5/A5: self-similarity coerces numerics inside set_params (``int(chunk_size)``). A
        non-numeric value must raise ``ValueError`` — the server wraps this call and returns a 400
        instead of the uncaught 500 the bare ``int(...)`` produced before. (The typed FastAPI query
        param shields the HTTP path today, so the guarantee is asserted at the track level.)"""
        track = SelfSimilarityTrack()
        with pytest.raises(ValueError):
            track.set_params({"chunk_size": "not-a-number"})


class TestSizelessModeRejection:
    """R7: verse/punctuation are size-less chunking modes the self-similarity refinement can't yet
    consume (its alignment internals key on an integer word-window). They are refused with a clear
    message that names the mode and the reason — never silently run or coerced into a window size.
    Wiring them through is the deferred self-similarity redesign; the chunking *stage* already
    supports them (see test_chunking)."""

    @pytest.mark.parametrize("mode", ["verse", "punctuation"])
    def test_validate_params_rejects_sizeless_mode(self, mode):
        track = SelfSimilarityTrack()
        track.set_params({"metrics": ["word_overlap"], "chunk_mode": mode})
        with pytest.raises(ValueError, match=f"does not yet support {mode!r}"):
            track.validate_params()


class TestAlignmentRefinementHonesty:
    """R9: LASTZ seed-and-extend + sliding-window refinement assume uniform, non-overlapping word
    windows. ``word`` mode satisfies that, but ``slide`` (overlapping) and ``smart`` (variable-size)
    do not — the similarity matrices stay exact while the refined alignment *boundaries* become
    approximate. Rather than reject those modes or silently degrade, extract() records the honest
    label ``alignment_refinement: "exact"|"approximate"`` per metric in the manifest so a downstream
    consumer can see what the boundaries mean."""

    @pytest.mark.parametrize(
        "mode, size, expected",
        [("word", 7, "exact"), ("slide", 10, "approximate")],
    )
    def test_manifest_records_refinement_label(self, tmp_path, mode, size, expected):
        import json
        from pathlib import Path

        from palimpsest.project import ingest_file
        from palimpsest.runner import extract_masked as _extract_masked

        # Non-embedding metrics exercise chunking → matrix → LASTZ without an embedding service.
        # To get alignments we need two passages similar enough to seed an off-diagonal optimum that
        # also survive repeat-masking (_mask_repeats), which suppresses any phrase recurring
        # >= EXACT_REPEAT_MIN_OCCURRENCES (3) times. A verbatim copy would be masked — and slide mode
        # masks *doubly* hard because _find_exact_repeats concatenates the 50%-overlapping windows,
        # counting every phrase ~2x. So the second passage shares the first's exact bag-of-words (high
        # word_overlap / edit_distance similarity) while breaking every 3-gram via an adjacent-word
        # swap: identical multiset, no recurring phrase, no masking — alignments survive in both modes.
        block = (
            "lighthouse compass mariner tempest beacon anchor harbor voyage lantern rudder seagull "
            "driftwood meridian sextant fathom keel mast galleon cargo wharf pelican estuary saltmarsh "
            "cormorant barnacle schooner ballast hull tiller jib spinnaker capstan grommet halyard topsail"
        ).split()
        swapped = block[:]
        for i in range(0, len(swapped) - 1, 2):
            swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
        filler = (
            "quarterly throughput logistics monsoon warehouse distribution overnight compliance auditor "
            "inventory shipment freight tariff customs broker pallet forklift loading dock manifest "
            "invoice receipt ledger surcharge embargo quota consignment depot"
        )
        text = f"{' '.join(block)}. {filler}. {' '.join(swapped)}."

        src: Path = tmp_path / "src.txt"
        src.write_text(text, encoding="utf-8")
        project = ingest_file(src, tmp_path, title="Refinement")

        track = SelfSimilarityTrack()
        track.set_params({
            "chunk_mode": mode,
            "chunk_size": size,
            "metrics": ["word_overlap", "edit_distance"],
        })
        _extract_masked(project, track)

        manifest = json.loads((project.path / "signals" / "self_similarity.json").read_text())
        metric_info = manifest["metadata"]["metric_info"]
        assert metric_info, "expected per-metric records in the manifest"
        for metric, info in metric_info.items():
            assert info["alignment_refinement"] == expected, (
                f"{mode} mode metric {metric!r} should report {expected!r} refinement"
            )

        # B3: the label travels on each individual alignment record too (not only the manifest's
        # metric_info), so the dotplot can mark a single alignment exact vs approximate. The two
        # bag-identical passages guarantee LASTZ hits, so the combined file exists and is non-empty.
        combined = project.path / "signals" / "self_similarity_alignments.json"
        records = json.loads(combined.read_text())
        assert records, "bag-identical passages should yield alignments"
        for rec in records:
            assert rec["refinement"] == expected


class TestTransactionalOutputs:
    """G3/C3: per-metric matrices, alignment files, and the master manifest are staged to invisible
    ".partial" siblings and committed together with atomic renames only after the whole run succeeds.
    A mid-run failure promotes nothing — so no orphan ``.bin`` is left for the chunk-size scanners
    (``_discover_chunk_sizes``, the chunk_sizes endpoint) to surface as a valid result — and a
    successful run leaves no ".partial" staging files behind."""

    def _project(self, tmp_path):
        from palimpsest.project import ingest_file

        src = tmp_path / "src.txt"
        src.write_text("The quick brown fox jumps over the lazy dog. " * 60, encoding="utf-8")
        return ingest_file(src, tmp_path, title="Transactional")

    def test_successful_run_leaves_no_partial_files(self, tmp_path):
        project = self._project(tmp_path)
        track = SelfSimilarityTrack()
        track.set_params({"chunk_mode": "word", "chunk_size": 7, "metrics": ["word_overlap"]})
        track.extract(project)
        signals = project.path / "signals"
        assert (signals / "self_similarity.json").exists()
        assert (signals / "self_similarity_word_overlap.bin").exists()
        assert list(signals.rglob("*.partial")) == []

    def test_mid_run_failure_promotes_no_orphan_bin_or_manifest(self, tmp_path, monkeypatch):
        import palimpsest.tracks.self_similarity as ss

        project = self._project(tmp_path)
        track = SelfSimilarityTrack()
        # Canonical order is (cosine, jaccard, word_overlap, edit_distance): word_overlap is computed
        # and STAGED first, then edit_distance raises — so the run dies after one metric is staged but
        # before commit. The transactional guarantee is that nothing was promoted.
        track.set_params({
            "chunk_mode": "word", "chunk_size": 7,
            "metrics": ["word_overlap", "edit_distance"],
        })

        def boom(chunks):
            raise RuntimeError("metric blew up mid-run")

        monkeypatch.setattr(ss, "_edit_distance_matrix", boom)
        with pytest.raises(RuntimeError, match="blew up"):
            track.extract(project)

        signals = project.path / "signals"
        assert not (signals / "self_similarity_word_overlap.bin").exists()
        assert not (signals / "self_similarity_cs7" / "word_overlap.bin").exists()
        assert not (signals / "self_similarity.json").exists()


