# -*- coding: utf-8 -*-
"""TDD spec for r3_variance — the crop-variance experiment harness.

The experiment's whole validity rests on one property: the crop variants must be LABEL-PRESERVING. Each
variant may only GROW the region box, never shrink it, so every variant still contains all of the region's
verse text. If a variant could clip content, a lower score would be explained by lost text rather than by the
model's sensitivity, and the measured "chaos term" would be an artefact of the harness instead of a property
of olmOCR. These tests pin exactly that, plus the aggregation contract (a gold-free selector may only accept
what its OWN gold-free score clears — the selector must never be allowed to peek at gold).
"""
from __future__ import annotations

import pytest

import r3_variance


def test_variant_zero_is_the_production_crop():
    c = (0.2, 0.3, 0.8, 0.6)
    assert r3_variance.crop_variants(c, 4)[0] == c, "variant 0 must be the unperturbed production crop"


def test_variants_only_grow_the_box_never_clip_content():
    c = (0.2, 0.3, 0.8, 0.6)
    for i, v in enumerate(r3_variance.crop_variants(c, 5)):
        assert v[0] <= c[0] and v[1] <= c[1], f"variant {i} shrank the top-left corner: {v}"
        assert v[2] >= c[2] and v[3] >= c[3], f"variant {i} shrank the bottom-right corner: {v}"


def test_variants_are_distinct_and_monotonically_larger():
    vs = r3_variance.crop_variants((0.2, 0.3, 0.8, 0.6), 5)
    assert len(set(vs)) == len(vs), "duplicate variants would waste an olmOCR call and bias the spread"
    widths = [v[2] - v[0] for v in vs]
    assert widths == sorted(widths), "variants must grow monotonically so the sweep is interpretable"


def test_variants_are_clamped_into_the_unit_square():
    for v in r3_variance.crop_variants((0.005, 0.002, 0.995, 0.998), 5):
        assert all(0.0 <= q <= 1.0 for q in v), f"crop escaped the unit square: {v}"
        assert v[0] < v[2] and v[1] < v[3], f"degenerate crop: {v}"


def test_n_variants_is_respected():
    for n in (1, 2, 3, 4, 5):
        assert len(r3_variance.crop_variants((0.2, 0.3, 0.8, 0.6), n)) == n


def _rec(v, taux, r2_gold, samples):
    return {"slug": "s", "book": "psalms", "ch": 1, "v": v, "taux": taux, "r2_xsrc": 0.5,
            "r2_gold_aid": r2_gold, "known_bad_gold": True, "has_gold": True, "samples": samples}


def _write(tmp_path, monkeypatch, recs):
    monkeypatch.setattr(r3_variance, "OUT", tmp_path)
    import json
    (tmp_path / "page.json").write_text(json.dumps(recs))
    return r3_variance.aggregate()


def test_selector_may_not_accept_what_its_own_gold_free_score_fails(tmp_path, monkeypatch):
    """NO SILENT DEGRADATION / no gold peeking: a variant that is excellent vs GOLD but whose witness score is
    below taux must NOT count as a selected pass — production cannot see gold, so neither may the measurement.
    Here the argmax-by-xsrc variant has xsrc 0.80 < taux 0.90, so the selected pass-rate is 0 even though the
    oracle (gold) ceiling is 1.0."""
    s = _write(tmp_path, monkeypatch, [_rec(1, 0.90, 0.5, [
        {"i": 0, "xsrc": 0.80, "gold": 0.99}, {"i": 1, "xsrc": 0.70, "gold": 1.00}])])
    assert s["pass_rate_ge_0.90_vs_gold"]["oracle_best_by_gold"] == 1.0
    assert s["pass_rate_ge_0.90_vs_gold"]["selected_gold_free"] == 0.0


def test_selected_uses_argmax_of_the_witness_not_of_gold(tmp_path, monkeypatch):
    """The selected score must come from the variant with the best WITNESS score, even when another variant is
    better vs gold — otherwise the experiment would report an unreachable number as if production could hit it."""
    s = _write(tmp_path, monkeypatch, [_rec(1, 0.90, 0.5, [
        {"i": 0, "xsrc": 0.95, "gold": 0.92},     # witness-best, gold 0.92  -> what production gets
        {"i": 1, "xsrc": 0.60, "gold": 1.00}])])  # gold-best but witness-poor -> oracle only
    assert s["mean_gold"]["selected_gold_free_argmax_xsrc"] == pytest.approx(0.92)
    assert s["mean_gold"]["oracle_best_by_gold"] == pytest.approx(1.00)
    assert s["pass_rate_ge_0.90_vs_gold"]["selected_gold_free"] == 1.0


def test_spread_is_the_gold_range_across_variants(tmp_path, monkeypatch):
    s = _write(tmp_path, monkeypatch, [_rec(1, 0.90, 0.5, [
        {"i": 0, "xsrc": 0.9, "gold": 0.20}, {"i": 1, "xsrc": 0.8, "gold": 0.95}])])
    assert s["gold_spread_across_variants"]["mean"] == pytest.approx(0.75)
    assert s["gold_spread_across_variants"]["n_spread_gt_0.3"] == 1


def test_failed_variants_are_missing_samples_not_zero_scores(tmp_path, monkeypatch):
    """A transcribe failure must be recorded as an ABSENT sample (xsrc/gold None) and skipped, never folded in
    as a 0.0 — a harness that scored errors as zero would manufacture chaos that olmOCR did not produce."""
    s = _write(tmp_path, monkeypatch, [_rec(1, 0.90, 0.5, [
        {"i": 0, "xsrc": 0.95, "gold": 0.96},
        {"i": 1, "error": "TimeoutError: x", "xsrc": None, "gold": None}])])
    assert s["gold_spread_across_variants"]["mean"] == pytest.approx(0.0), "the errored variant must not count"
    assert s["mean_gold"]["selected_gold_free_argmax_xsrc"] == pytest.approx(0.96)


def test_verse_with_no_usable_samples_is_dropped_not_scored_zero(tmp_path, monkeypatch):
    """Every variant failing means we learned NOTHING about that verse; it must leave the sample set entirely
    rather than enter it as a zero and drag the reported means down."""
    s = _write(tmp_path, monkeypatch, [
        _rec(1, 0.90, 0.5, [{"i": 0, "xsrc": 0.95, "gold": 0.96}]),
        _rec(2, 0.90, 0.5, [{"i": 0, "error": "E", "xsrc": None, "gold": None}])])
    assert s["n_known_bad_with_samples"] == 1
    assert s["mean_gold"]["single_run_variant0"] == pytest.approx(0.96)
