"""Layer dependency-check resolver — Wave-0 P2, FR-7 (the load-bearing reuse mechanism).

A downstream track declares what layers it needs as ``layer_requirements`` (a list of
:class:`LayerRequirement`) instead of triggering hidden chunk/embed invocation. :func:`resolve_layers`
binds each requirement to a persisted layer whose capability descriptor satisfies it, or **fails loud**
(:class:`LayerResolutionError`) — no silent consumption of an incompatible layer, no silent
auto-production. This is the compatibility check that makes layer reuse safe rather than
silently-wrong; it composes with (does not replace) the registry's name-based ``depends_on``
topological ordering.

``layer_requirements`` is an *optional* attribute read via ``getattr``; tracks without it behave
exactly as before, so this is fully back-compatible and never affects ``TrackExtractor`` protocol
conformance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

LayerKind = Literal["chunk", "embedding"]

# On-disk layer file prefix and the capability-descriptor field naming each layer's analyzable digest.
_KIND_PREFIX: dict[str, str] = {"chunk": "chunking_", "embedding": "embedding_"}
_KIND_DIGEST_FIELD: dict[str, str] = {
    "chunk": "analyzable_digest",
    "embedding": "chunk_analyzable_digest",
}


class LayerResolutionError(ValueError):
    """No persisted layer satisfies a :class:`LayerRequirement`. Subclasses :class:`ValueError` (like
    ``UnmappedCoordinateError``) so the run handlers surface it through the same failed-job path as
    every other bad-input error, carrying the requirement and what was available to the user."""


@dataclass(frozen=True)
class LayerRequirement:
    """A declared dependency on a layer of ``kind`` whose capability descriptor satisfies every
    ``constraints`` predicate (descriptor-field == value). ``digest_match`` additionally requires the
    layer to have been computed on the same analyzable text as the project view it is resolved
    against, so a layer can never be matched against a different masking of the document."""

    kind: LayerKind
    constraints: dict[str, Any] = field(default_factory=dict)
    digest_match: bool = True


@dataclass(frozen=True)
class BoundLayer:
    """A layer bound to a requirement: its label, manifest path/contents, and capability descriptor."""

    kind: str
    label: str
    manifest_path: Path
    capability: dict[str, Any]
    manifest: dict[str, Any]

    @property
    def vectorstore_path(self) -> str | None:
        """Relative path to the embedding layer's SQLite-vec DB, if this is an embedding layer."""
        return self.manifest.get("metadata", {}).get("vectorstore")


def project_analyzable_digest(project: Any, sep: str = "") -> str:
    """The sha256 of the project's analyzable text for ``sep`` — the same digest the chunk layer
    records (``capability.analyzable_digest``), so ``digest_match`` compares like with like."""
    atext, _omap = project.analyzable_text(sep)
    return hashlib.sha256(atext.encode("utf-8")).hexdigest()


def _enumerate_layers(project: Any, kind: LayerKind) -> list[BoundLayer]:
    """All persisted layers of ``kind`` for ``project``, in stable (path-sorted) order."""
    signals = Path(project.path) / "signals"
    if not signals.is_dir():
        return []
    out: list[BoundLayer] = []
    for path in sorted(signals.glob(f"{_KIND_PREFIX[kind]}*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        cap = data.get("metadata", {}).get("capability", {})
        if cap.get("kind") != kind:
            continue
        label = data.get("metadata", {}).get("label", path.stem[len(_KIND_PREFIX[kind]):])
        out.append(BoundLayer(kind, label, path, cap, data))
    return out


def _satisfies(capability: dict[str, Any], constraints: dict[str, Any]) -> bool:
    return all(capability.get(k) == v for k, v in constraints.items())


def resolve_layers(
    project: Any,
    requirements: list[LayerRequirement],
    *,
    analyzable_digest: str | None = None,
    sep: str = "",
) -> dict[str, BoundLayer]:
    """Bind each requirement to a compatible persisted layer, keyed by ``kind``.

    For each requirement: enumerate persisted layers of its kind, keep those whose capability
    descriptor satisfies every constraint and (when ``digest_match``) whose recorded analyzable digest
    equals the project view's. Bind the sole survivor; if several survive, bind the most recently
    written (file mtime) — a deterministic "newest wins" that callers can record in provenance; if none
    survive, raise :class:`LayerResolutionError` naming the requirement and listing what was available.

    ``analyzable_digest`` is computed from the project for ``sep`` when not supplied, so callers that
    already have it (the run lifecycle) avoid recomputing.
    """
    bound: dict[str, BoundLayer] = {}
    digest = analyzable_digest
    for req in requirements:
        candidates = _enumerate_layers(project, req.kind)
        survivors = [c for c in candidates if _satisfies(c.capability, req.constraints)]
        if req.digest_match:
            if digest is None:
                digest = project_analyzable_digest(project, sep)
            field_name = _KIND_DIGEST_FIELD[req.kind]
            survivors = [c for c in survivors if c.capability.get(field_name) == digest]

        if not survivors:
            available = ", ".join(
                f"{c.label}({_describe(c.capability)})" for c in candidates
            ) or "(none)"
            raise LayerResolutionError(
                f"no {req.kind} layer satisfies {req.constraints!r}"
                + (" with matching analyzable digest" if req.digest_match else "")
                + f"; available {req.kind} layers: {available}. Run the layer first or adjust the "
                "requirement."
            )
        chosen = survivors[0] if len(survivors) == 1 else max(
            survivors, key=lambda c: c.manifest_path.stat().st_mtime
        )
        bound[req.kind] = chosen
    return bound


def _describe(capability: dict[str, Any]) -> str:
    """Compact one-line descriptor summary for an error message."""
    keys = ("mode", "overlapping", "size", "provider", "model", "dim")
    return ", ".join(f"{k}={capability[k]}" for k in keys if k in capability)
