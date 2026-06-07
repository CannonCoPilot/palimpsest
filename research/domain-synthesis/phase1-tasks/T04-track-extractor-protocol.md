# T04: TrackExtractor Protocol + TrackRegistry

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 3 hours (unchanged)
**Dependencies**: T03
**Outputs**: `python/palimpsest/tracks/base.py`, `python/palimpsest/tracks/registry.py`, `python/palimpsest/tracks/__init__.py`, `python/tests/test_registry.py`

---

## v4.0 Critical Review

**The TrackExtractor protocol is architecturally sound and is one of the elements explicitly preserved in v4.0. However, it has two integration problems with the new architecture that must be corrected.**

1. **`extract()` returns `list[Annotation] | Path`. The `list[Annotation]` path is wrong for the v4.0 pipeline.** In v3.0, the CLI calls `extract()`, gets `list[Annotation]`, calls `write_track()`, and the browser fetches the resulting JSONL. In v4.0, the CLI is a Rust binary that spawns Python extractors as subprocesses. The extractor cannot return Python objects to Rust — it must write JSONL to stdout (or to a file), and Rust reads it. The `extract()` return type is therefore only meaningful within a Python-only test context. For production use, extractors must implement `extract_to_stdout()` or write JSONL directly to a file path passed via argument.

2. **`TrackRegistry.discover()` uses `__subclasses__()`.** This is fine for an in-process Python pipeline, but in v4.0 the Rust pipeline manager needs to know which Python extractors are available before spawning them. The discovery mechanism must be expressible as a JSON manifest that Rust can read without running Python. Add `TrackRegistry.write_manifest(path)` that outputs a JSON file listing track names, output types, dependencies, and evidence levels.

3. **The `manifest()` method returns browser rendering config.** In v4.0, the browser's rendering is done by the `CanvasAnnotationOverlay` (a canvas element, not DOM spans) and WebGPU shaders. The `manifest()` method's `textViewRendering` and `overviewBarRendering` fields still apply — they drive the canvas renderer's color and style choices. No change needed, but the downstream consumer changes from DOM span injection to canvas draw calls.

4. **`depends_on` is a list of track names.** The Rust pipeline manager needs to resolve this dependency graph without running Python. The manifest JSON written by `TrackRegistry.write_manifest()` must include `depends_on` for Rust to compute execution order.

**What must change:**
- Add `extract_to_file(project, output_path)` as the production method (called by Rust via subprocess)
- Add `TrackRegistry.write_manifest(path)` for Rust pipeline manager discovery
- All other protocol details (properties, `manifest()`, registry mechanics) are unchanged
- Path changes: `core/palimpsest/tracks/` → `python/palimpsest/tracks/`

---

## v4.0 Rewrite

### `python/palimpsest/tracks/base.py`

```python
"""TrackExtractor protocol — the interface every track must satisfy."""
from __future__ import annotations
import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from palimpsest.annotation.model import Annotation
    from palimpsest.project import Project


@runtime_checkable
class TrackExtractor(Protocol):
    """
    Protocol for Palimpsest track extractors. Mirrors JBrowse 2's TrackAdapter pattern.

    In v4.0, extractors are invoked as Python subprocesses by the Rust pipeline manager.
    The primary production interface is `extract_to_file()`. `extract()` is retained
    for Python-only testing contexts.

    Evidence levels per §2.4:
      E1 — direct text extraction (segmentation)
      E4 — ML model prediction (NER, LDA, BookNLP)
      E5 — rule-based / statistical computation (VADER, lexical stats)
    """

    @property
    def name(self) -> str:
        """Short identifier: 'entities', 'sentiment', etc. Used as JSONL filename stem."""
        ...

    @property
    def output_type(self) -> Literal["annotation", "signal"]:
        """
        'annotation' — track writes JSONL to tracks/{name}.jsonl.
        'signal'     — track writes binary + manifest to signals/{name}.bin + .json.
        """
        ...

    @property
    def depends_on(self) -> list[str]:
        """
        Names of other tracks this extractor depends on.
        Used by TrackRegistry.dependency_order() and exported to JSON manifest for Rust.
        Empty list means no dependencies.
        """
        ...

    @property
    def lfo_types(self) -> list[str]:
        """
        Literary Feature Ontology types produced by this track.
        E.g., ['entity.character', 'entity.place', 'entity.organization'].
        """
        ...

    @property
    def evidence_level(self) -> str:
        """Evidence level for all annotations produced: 'E1'-'E5'."""
        ...

    def extract(self, project: "Project") -> "list[Annotation] | Path":
        """
        Run extraction on the project.

        For 'annotation' tracks: returns list[Annotation] objects.
        For 'signal' tracks: writes binary + manifest internally, returns Path to manifest.

        Note: In production (Rust pipeline manager), use extract_to_file() instead.
        This method is used in Python-only tests and during development.
        """
        ...

    def extract_to_file(self, project: "Project", output_path: Path) -> None:
        """
        Run extraction and write output directly to output_path.

        For 'annotation' tracks: writes JSONL to output_path.
        For 'signal' tracks: writes binary to output_path.bin, manifest to output_path.json.

        This is the production interface called by the Rust pipeline manager via subprocess.
        Output must be written atomically (write to temp, then rename) to avoid partial reads.

        Default implementation calls extract() and serializes the result. Override for
        streaming behavior (large texts that cannot hold all annotations in memory).
        """
        from palimpsest.annotation.serializer import write_track
        result = self.extract(project)
        if self.output_type == "annotation":
            assert isinstance(result, list)
            write_track(output_path, result)
        # Signal tracks write their own files; output_path is ignored for them.

    def manifest(self) -> dict:
        """
        Track rendering manifest for the canvas renderer and WebGPU shaders.

        Required keys: trackName, bodyType, colorScheme, textViewRendering, overviewBarRendering.
        In v4.0, textViewRendering drives the CanvasAnnotationOverlay draw style,
        not DOM span injection.

        Example:
            {
              "trackName": "entities",
              "bodyType": "palimpsest:EntityAnnotation",
              "colorScheme": {"primary": "#e63946", "secondary": "#457b9d"},
              "textViewRendering": "highlight",
              "overviewBarRendering": {"type": "density-barcode", "color": "#e63946"},
            }
        """
        ...
```

### `python/palimpsest/tracks/registry.py`

Adds `write_manifest()` to the existing registry. All other methods are preserved from v3.0:

```python
"""TrackRegistry — auto-discovery and dependency ordering of track extractors."""
from __future__ import annotations
import importlib
import json
import pkgutil
from collections import defaultdict
from pathlib import Path
from palimpsest.tracks.base import TrackExtractor


class TrackRegistry:
    """
    Discovers and manages all TrackExtractor implementations.

    New in v4.0: write_manifest() exports track metadata to JSON so the Rust
    pipeline manager can discover and order tracks without running Python.
    """

    def __init__(self) -> None:
        self._extractors: dict[str, type[TrackExtractor]] = {}

    def register(self, extractor_cls: type[TrackExtractor]) -> None:
        """Explicitly register a TrackExtractor class by its name property."""
        instance = extractor_cls()
        name = instance.name
        if name in self._extractors:
            raise ValueError(
                f"Duplicate track name {name!r}: already registered as "
                f"{self._extractors[name].__qualname__}"
            )
        self._extractors[name] = extractor_cls

    @classmethod
    def discover(cls, package: str = "palimpsest.tracks") -> "TrackRegistry":
        """Auto-discover all TrackExtractor implementations in a package."""
        registry = cls()
        try:
            pkg = importlib.import_module(package)
            pkg_path = getattr(pkg, "__path__", [])
            for _, module_name, _ in pkgutil.walk_packages(pkg_path, prefix=package + "."):
                try:
                    importlib.import_module(module_name)
                except ImportError:
                    pass
        except ImportError:
            pass

        def collect_subclasses(cls_: type) -> list[type]:
            result = []
            for sub in cls_.__subclasses__():
                result.append(sub)
                result.extend(collect_subclasses(sub))
            return result

        for sub in collect_subclasses(object):
            if sub is TrackExtractor:
                continue
            try:
                instance = sub()
                if isinstance(instance, TrackExtractor):
                    name = instance.name
                    if name not in registry._extractors:
                        registry._extractors[name] = sub
            except Exception:
                pass

        return registry

    def get(self, name: str) -> type[TrackExtractor]:
        if name not in self._extractors:
            raise KeyError(f"Unknown track: {name!r}. Available: {list(self._extractors)}")
        return self._extractors[name]

    def all(self) -> list[type[TrackExtractor]]:
        return list(self._extractors.values())

    def dependency_order(self) -> list[type[TrackExtractor]]:
        """Return extractors in topological dependency order (Kahn's algorithm)."""
        deps: dict[str, list[str]] = {}
        for name, cls_ in self._extractors.items():
            instance = cls_()
            deps[name] = list(instance.depends_on)

        in_degree: dict[str, int] = defaultdict(int)
        dependents: dict[str, list[str]] = defaultdict(list)

        for name, dep_list in deps.items():
            in_degree.setdefault(name, 0)
            for dep in dep_list:
                in_degree[name] += 1
                dependents[dep].append(name)

        queue = [name for name, deg in in_degree.items() if deg == 0]
        order: list[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self._extractors):
            cycle_nodes = set(self._extractors) - set(order)
            raise ValueError(f"Dependency cycle detected among tracks: {cycle_nodes}")

        return [self._extractors[name] for name in order]

    def write_manifest(self, output_path: Path) -> None:
        """
        Write a JSON manifest listing all registered tracks and their metadata.

        This manifest is read by the Rust pipeline manager (src-tauri/src/commands/pipeline.rs)
        to discover tracks without spawning a Python process for introspection.

        Format:
        {
          "tracks": [
            {
              "name": "entities",
              "output_type": "annotation",
              "depends_on": [],
              "lfo_types": ["entity.character", ...],
              "evidence_level": "E4",
              "manifest": { ...rendering config... }
            },
            ...
          ],
          "execution_order": ["entities", "sentiment", ...]
        }
        """
        tracks = []
        for name, cls_ in self._extractors.items():
            instance = cls_()
            tracks.append({
                "name": name,
                "output_type": instance.output_type,
                "depends_on": instance.depends_on,
                "lfo_types": instance.lfo_types,
                "evidence_level": instance.evidence_level,
                "manifest": instance.manifest(),
            })

        try:
            ordered = self.dependency_order()
            execution_order = [cls_().name for cls_ in ordered]
        except ValueError:
            execution_order = list(self._extractors.keys())  # fallback if cycle

        manifest_data = {
            "tracks": tracks,
            "execution_order": execution_order,
        }

        output_path.write_text(
            json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def names(self) -> list[str]:
        return list(self._extractors.keys())

    def __len__(self) -> int:
        return len(self._extractors)

    def __repr__(self) -> str:
        return f"TrackRegistry({list(self._extractors.keys())})"
```

### `python/tests/test_registry.py`

All v3.0 tests are preserved. Two new tests are added for v4.0:

```python
# --- v4.0 additions ---

def test_write_manifest(tmp_path: Path) -> None:
    """write_manifest() produces valid JSON readable by Rust pipeline manager."""
    reg = TrackRegistry()
    reg.register(AlphaTrack)
    reg.register(BetaTrack)
    reg.register(GammaTrack)

    manifest_path = tmp_path / "track_registry.json"
    reg.write_manifest(manifest_path)

    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())

    assert "tracks" in data
    assert "execution_order" in data
    assert len(data["tracks"]) == 3

    track_names = {t["name"] for t in data["tracks"]}
    assert track_names == {"alpha", "beta", "gamma"}

    # Execution order must respect dependencies
    order = data["execution_order"]
    assert order.index("alpha") < order.index("beta")
    assert order.index("beta") < order.index("gamma")

    # Each track entry has required fields
    for track in data["tracks"]:
        for field in ("name", "output_type", "depends_on", "lfo_types", "evidence_level", "manifest"):
            assert field in track, f"Missing field {field!r} in track {track['name']!r}"


def test_extract_to_file_writes_jsonl(tmp_path: Path) -> None:
    """extract_to_file() writes JSONL that can be loaded into Rust arena."""
    # Use a minimal in-memory extractor for testing
    class MinimalExtractor:
        @property
        def name(self) -> str: return "minimal"
        @property
        def output_type(self): return "annotation"
        @property
        def depends_on(self) -> list: return []
        @property
        def lfo_types(self) -> list: return ["test.minimal"]
        @property
        def evidence_level(self) -> str: return "E4"
        def extract(self, project):
            from palimpsest.annotation.model import (
                Annotation, Body, Target, TextPositionSelector, Creator
            )
            return [
                Annotation(
                    body=Body(type="palimpsest:EntityAnnotation", purpose="classifying",
                              extra={"palimpsest:entityType": "PER"}),
                    target=Target(
                        source="urn:palimpsest:test",
                        selector=TextPositionSelector(start=0, end=10),
                    ),
                    creator=Creator(name="test/0.1"),
                    confidence=0.9,
                    evidence_level="E4",
                )
            ]
        def manifest(self) -> dict: return {}

    ext = MinimalExtractor()
    output = tmp_path / "minimal.jsonl"

    class FakeProject:
        source_urn = "urn:palimpsest:test"
        reference_text = "Hello world"
        class metadata:
            id = "test"

    ext.extract_to_file(FakeProject(), output)
    assert output.exists()
    lines = [l for l in output.read_text().strip().split("\n") if l.strip()]
    assert len(lines) == 1
    ann_data = json.loads(lines[0])
    assert ann_data["type"] == "Annotation"
    assert ann_data["palimpsest:evidenceLevel"] == "E4"
```

## Acceptance Criteria

- `pytest python/tests/test_registry.py` passes all tests (original 10 + 2 new)
- `mypy --strict python/palimpsest/tracks/` exits 0
- `AlphaTrack`, `BetaTrack`, `GammaTrack` stubs satisfy `isinstance(instance, TrackExtractor)`
- `TrackRegistry.write_manifest()` produces valid JSON with `tracks` and `execution_order` arrays
- `execution_order` in manifest respects topological dependencies (alpha before beta before gamma)
- Each track entry in manifest contains: `name`, `output_type`, `depends_on`, `lfo_types`, `evidence_level`, `manifest`
- `extract_to_file()` default implementation writes valid JSONL readable by the Python `read_track()` function
- `TrackRegistry.dependency_order()` raises `ValueError` containing "cycle" on circular dependencies
- `TrackRegistry.get("nonexistent")` raises `KeyError`

## Design Decisions

- **`extract_to_file()` has a default implementation**: The default calls `extract()` and writes the result, which is correct for all Phase 1 tracks. Phase 2 tracks processing 500K-word novels may need streaming implementations that override this method and yield annotations without holding all in memory.

- **`write_manifest()` is separate from `manifest()`**: The per-track `manifest()` returns rendering configuration. The registry-level `write_manifest()` exports discovery metadata for Rust. These are different consumers (TypeScript canvas renderer vs. Rust subprocess manager) and different formats.

- **Rust reads the manifest file, not the Python registry**: The Rust pipeline manager reads `track_registry.json` at startup and uses `execution_order` to determine which Python subprocess to spawn and in what sequence. This avoids the latency and complexity of Rust interrogating a Python process for introspection — the manifest is a cache of the registry state.

---

## Original Content (v3.0, preserved for reference)

The v3.0 T04 specified the `TrackExtractor` Protocol and `TrackRegistry` with `__subclasses__()` discovery and Kahn's algorithm for dependency ordering. All of that is preserved. The additions in v4.0 are: `extract_to_file()` method on the protocol, and `write_manifest()` on the registry. Path changes from `core/palimpsest/tracks/` to `python/palimpsest/tracks/`.
