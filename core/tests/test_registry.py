"""Tests for TrackExtractor protocol and TrackRegistry."""

from pathlib import Path

import pytest

from palimpsest.tracks.base import TrackExtractor
from palimpsest.tracks.registry import TrackRegistry


class _DummyTrackA:
    @property
    def name(self) -> str:
        return "track_a"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return []

    @property
    def lfo_types(self) -> list[str]:
        return []

    @property
    def evidence_level(self) -> str:
        return "E4"

    def extract(self, project):
        return []

    def manifest(self) -> dict:
        return {"trackName": self.name, "colorScheme": {"primary": "#888"}}

    def parameters(self) -> dict:
        return {}


class _DummyTrackB:
    @property
    def name(self) -> str:
        return "track_b"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return ["track_a"]

    @property
    def lfo_types(self) -> list[str]:
        return []

    @property
    def evidence_level(self) -> str:
        return "E4"

    def extract(self, project):
        return []

    def manifest(self) -> dict:
        return {"trackName": self.name, "colorScheme": {"primary": "#888"}}

    def parameters(self) -> dict:
        return {}


class _DummyTrackC:
    @property
    def name(self) -> str:
        return "track_c"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        return ["track_b", "_embeddings"]

    @property
    def lfo_types(self) -> list[str]:
        return []

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project):
        return Path("/dev/null")

    def manifest(self) -> dict:
        return {"trackName": self.name, "colorScheme": {"primary": "#888"}}

    def parameters(self) -> dict:
        return {}


class TestTrackProtocol:
    def test_dummy_satisfies_protocol(self):
        assert isinstance(_DummyTrackA(), TrackExtractor)
        assert isinstance(_DummyTrackB(), TrackExtractor)
        assert isinstance(_DummyTrackC(), TrackExtractor)

    def test_protocol_rejects_incomplete_class(self):
        class _Incomplete:
            @property
            def name(self) -> str:
                return "bad"

        assert not isinstance(_Incomplete(), TrackExtractor)


class TestTrackRegistry:
    def test_register_and_get(self):
        reg = TrackRegistry()
        reg.register(_DummyTrackA)
        assert reg.get("track_a") is _DummyTrackA

    def test_get_unknown_raises(self):
        reg = TrackRegistry()
        with pytest.raises(KeyError, match="Unknown track"):
            reg.get("nonexistent")

    def test_duplicate_name_raises(self):
        reg = TrackRegistry()
        reg.register(_DummyTrackA)
        with pytest.raises(ValueError, match="Duplicate track name"):
            reg.register(_DummyTrackA)

    def test_all_returns_registered(self):
        reg = TrackRegistry()
        reg.register(_DummyTrackA)
        reg.register(_DummyTrackB)
        assert len(reg.all()) == 2

    def test_names_sorted(self):
        reg = TrackRegistry()
        reg.register(_DummyTrackB)
        reg.register(_DummyTrackA)
        assert reg.names() == ["track_a", "track_b"]

    def test_dependency_order_respects_deps(self):
        reg = TrackRegistry()
        reg.register(_DummyTrackB)
        reg.register(_DummyTrackA)
        ordered = reg.dependency_order()
        names = [cls().name for cls in ordered]
        assert names.index("track_a") < names.index("track_b")

    def test_dependency_order_ignores_virtual_deps(self):
        reg = TrackRegistry()
        reg.register(_DummyTrackA)
        reg.register(_DummyTrackB)
        reg.register(_DummyTrackC)
        ordered = reg.dependency_order()
        names = [cls().name for cls in ordered]
        assert names.index("track_a") < names.index("track_b")
        assert names.index("track_b") < names.index("track_c")

    def test_dependency_cycle_raises(self):
        class _CycleA:
            name = "cycle_a"
            output_type = "annotation"
            depends_on = ["cycle_b"]
            lfo_types = []
            evidence_level = "E4"
            def extract(self, project): return []
            def manifest(self): return {}
            def parameters(self): return {}

        class _CycleB:
            name = "cycle_b"
            output_type = "annotation"
            depends_on = ["cycle_a"]
            lfo_types = []
            evidence_level = "E4"
            def extract(self, project): return []
            def manifest(self): return {}
            def parameters(self): return {}

        reg = TrackRegistry()
        reg.register(_CycleA)
        reg.register(_CycleB)
        with pytest.raises(ValueError, match="cycle"):
            reg.dependency_order()

    def test_discover_finds_entities(self):
        reg = TrackRegistry.discover()
        assert isinstance(reg, TrackRegistry)
        assert "entities" in reg.names()
