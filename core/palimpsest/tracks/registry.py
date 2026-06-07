"""TrackRegistry — auto-discovery and dependency-ordered execution of track extractors.

Imports all modules in the tracks package, then checks each class against
the TrackExtractor protocol via isinstance(). Virtual dependencies
(prefixed with '_') are treated as pre-satisfied and excluded from topological sort.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from collections import deque

from palimpsest.tracks.base import TrackExtractor

logger = logging.getLogger(__name__)


class TrackRegistry:
    """Registry of all available track extractors."""

    def __init__(self) -> None:
        self._extractors: dict[str, type] = {}
        self._instances: dict[str, TrackExtractor] = {}
        self._names: dict[type, str] = {}

    def register(self, extractor_cls: type) -> None:
        instance = extractor_cls()
        name = instance.name
        if name in self._extractors:
            raise ValueError(
                f"Duplicate track name: {name!r} "
                f"(from {extractor_cls.__name__} and {self._extractors[name].__name__})"
            )
        self._extractors[name] = extractor_cls
        self._instances[name] = instance
        self._names[extractor_cls] = name

    def get(self, name: str) -> type:
        if name not in self._extractors:
            available = ", ".join(sorted(self._extractors.keys()))
            raise KeyError(f"Unknown track: {name!r}. Available: {available}")
        return self._extractors[name]

    def all(self) -> list[type]:
        return list(self._extractors.values())

    def names(self) -> list[str]:
        return sorted(self._extractors.keys())

    def dependency_order(self) -> list[type]:
        """Return extractors in topological order (Kahn's algorithm).

        Virtual dependencies (prefixed with '_') are excluded from the graph.
        """
        real_deps: dict[str, list[str]] = {}
        in_degree: dict[str, int] = {}

        for name in self._extractors:
            deps = [
                d
                for d in self._instances[name].depends_on
                if not d.startswith("_") and d in self._extractors
            ]
            real_deps[name] = deps
            in_degree[name] = len(deps)

        queue: deque[str] = deque(n for n, deg in in_degree.items() if deg == 0)
        result: list[str] = []

        while queue:
            name = queue.popleft()
            result.append(name)
            for other_name, deps in real_deps.items():
                if name in deps:
                    in_degree[other_name] -= 1
                    if in_degree[other_name] == 0:
                        queue.append(other_name)

        if len(result) != len(self._extractors):
            missing = set(self._extractors.keys()) - set(result)
            raise ValueError(f"Dependency cycle detected among tracks: {missing}")

        return [self._extractors[n] for n in result]

    @classmethod
    def discover(cls) -> TrackRegistry:
        """Auto-discover all TrackExtractor-conforming classes in the tracks package."""
        import palimpsest.tracks as tracks_pkg

        for _importer, modname, _ispkg in pkgutil.iter_modules(
            tracks_pkg.__path__, prefix="palimpsest.tracks."
        ):
            if modname.endswith(".base") or modname.endswith(".registry"):
                continue
            try:
                importlib.import_module(modname)
            except ImportError as e:
                logger.warning("Skipping track module %s: %s", modname, e)

        registry = cls()

        for _importer, modname, _ispkg in pkgutil.iter_modules(
            tracks_pkg.__path__, prefix="palimpsest.tracks."
        ):
            if modname.endswith(".base") or modname.endswith(".registry"):
                continue
            try:
                mod = importlib.import_module(modname)
            except ImportError:
                continue
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name)
                if not isinstance(obj, type):
                    continue
                if obj is TrackExtractor:
                    continue
                if not obj.__module__.startswith("palimpsest.tracks."):
                    continue
                try:
                    instance = obj()
                except TypeError:
                    continue
                if isinstance(instance, TrackExtractor) and obj not in registry._names:
                    registry.register(obj)

        return registry
