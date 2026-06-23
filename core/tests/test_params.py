"""Unit tests for the declarative parameter contract (tracks/params.py — guard-rails G1+G2)."""

from __future__ import annotations

import pytest

from palimpsest.tracks.params import (
    Param,
    ParameterizedTrack,
    resolve_params,
    track_provenance,
)


class _Track(ParameterizedTrack):
    PARAMS = (
        Param("n", int, default=5, min=2, max=10),
        Param("method", str, default="a", choices=("a", "b")),
        Param("seed", int, default=42, locked=True),
    )

    @property
    def name(self) -> str:
        return "demo"


def test_defaults_resolve_when_unset():
    assert _Track().resolved_params() == {"n": 5, "method": "a", "seed": 42}


def test_user_value_overrides_default():
    t = _Track()
    t.set_params({"n": 8, "method": "b"})
    assert t.resolved_params() == {"n": 8, "method": "b", "seed": 42}


def test_range_rejected():
    t = _Track()
    t.set_params({"n": 99})
    with pytest.raises(ValueError, match="'n'.*<= 10"):
        t.resolved_params()


def test_choice_rejected():
    t = _Track()
    t.set_params({"method": "z"})
    with pytest.raises(ValueError, match="'method'.*one of"):
        t.resolved_params()


def test_unknown_rejected_with_valid_list():
    t = _Track()
    t.set_params({"nope": 1})
    with pytest.raises(ValueError, match="unknown parameter.*'nope'"):
        t.resolved_params()


def test_locked_rejects_write_but_is_reported():
    t = _Track()
    assert t.resolved_params()["seed"] == 42  # reported
    t.set_params({"seed": 7})
    with pytest.raises(ValueError, match="locked"):
        t.resolved_params()  # not settable


def test_bad_coercion_is_valueerror():
    t = _Track()
    t.set_params({"n": "x"})
    with pytest.raises(ValueError, match="'n'.*int"):
        t.resolved_params()


def test_required_missing_rejected():
    params = (Param("k", int, required=True),)
    with pytest.raises(ValueError, match="'k' is required"):
        resolve_params(params, {}, track="demo")


def test_structural_param_may_not_be_locked():
    with pytest.raises(ValueError, match="structural.*cannot be locked"):
        Param("sep", str, kind="structural", locked=True)


def test_reserved_force_ignored():
    assert resolve_params((Param("n", int, default=1),), {"force": True}, track="demo") == {"n": 1}


def test_track_provenance_prefers_resolved_params_bare_keys():
    # A ParameterizedTrack exposes resolved_params() (bare keys) — used directly for the run record.
    assert track_provenance(_Track()) == {"n": 5, "method": "a", "seed": 42}


def test_track_provenance_strips_namespace_prefix():
    """G3/C1: a track whose only provenance is a namespaced ``parameters()`` (like self_similarity)
    is normalized to bare keys, so the on-disk run record reads the same regardless of source."""

    class _NamespacedOnly:
        name = "ss"

        def parameters(self):
            return {"ss.metric": "cosine", "ss.chunk_size": 7}

    assert track_provenance(_NamespacedOnly()) == {"metric": "cosine", "chunk_size": 7}
