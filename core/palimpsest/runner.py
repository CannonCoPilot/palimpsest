"""Shared track-run helpers: masked extraction + analyzable→original remap.

These run a single extractor under character-level masking and remap its outputs back to
original document coordinates. They live here — not in ``server.py`` — so the HTTP server
and the CLI ``analyze`` command share one masked-run code path (the CLI previously called
``extractor.extract(project)`` directly, with no masking or remap, producing wrong
coordinates for any masked project). This module has no web-framework dependency, so the
CLI can import it without loading FastAPI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _is_signal_consumer(extractor: Any) -> bool:
    """True for extractors whose output positions derive from an upstream track/signal (already in
    original coordinates) rather than from the text — so they run on the full project and are not
    remapped; the masking is inherited through their (already-masked) upstream. ``coreference`` is
    excluded: it derives positions from the text via BookNLP despite depending on ``entities``."""
    if getattr(extractor, "name", "") == "coreference":
        return False
    return any(not d.startswith("_") for d in extractor.depends_on)


def _remap_signal_dir(signals_dir: Path, omap: Any, prefix: str | None = None) -> None:
    """Remap signal outputs analyzable→original: manifest ``segment_offsets`` and alignment-record
    ``char_*`` spans. When ``prefix`` is given, only files belonging to that signal are touched."""
    from palimpsest.atomic import atomic_write_text
    from palimpsest.derive import remap_signal_data
    if not signals_dir.is_dir():
        return
    for jp in signals_dir.rglob("*.json"):
        if prefix is not None and prefix not in jp.name and prefix not in jp.parent.name:
            continue
        data = json.loads(jp.read_text(encoding="utf-8"))
        # remap_signal_data raises UnmappedCoordinateError on an offset-bearing shape it can't handle
        # (G4): a new output that forgot to declare/remap its coordinates fails loudly here rather than
        # writing analyzable coordinates mislabeled as original.
        if remap_signal_data(data, omap):
            atomic_write_text(jp, json.dumps(data, indent=2, ensure_ascii=False))


def extract_masked(project: Any, extractor: Any, sep: str = "") -> Any:
    """Run a single extractor under character-level masking.

    Text-deriving extractors run against the project's analysis view — the masked-resolved
    analyzable stream (masked spans and verse-number tokens excised) that they chunk at their own
    runtime — and their outputs are remapped back to original coordinates (annotation results
    in-place; any signal files they wrote by name). Signal-consumer extractors run on the full
    project, inheriting masking through their already-masked, already-original upstream.

    ``sep`` is the analyzable-stream separator inserted between kept (unmasked) spans; the caller
    resolves it from a runtime parameter (default "" — pure excision) so it is never a hidden
    default. It is coordinate-safe: the OffsetMap is built from ``len(sep)``, so remapping back to
    original coordinates accounts for it."""
    if _is_signal_consumer(extractor):
        return extractor.extract(project)
    from palimpsest.derive import remap_result_annotations

    # Optional per-run pre-chunk masking: a track may declare additional original-coordinate intervals
    # to hide before the analysis view is built, so the excised text drives extraction and the outputs
    # remap around the gaps (e.g. ChunkingTrack.hide_repeats excises a repeat layer, FR-16). Generic
    # tracks have no such hook and are unaffected. The view's analyzable_digest reflects the hidden
    # spans, so a repeats-hidden layer is content-addressed distinctly with no special-casing.
    extra_masked = None
    hook = getattr(extractor, "view_mask_intervals", None)
    if callable(hook):
        extra_masked = hook(project) or None

    view, omap = project.analysis_view(sep, extra_masked=extra_masked)
    try:
        result = extractor.extract(view)
    finally:
        view.close_analysis_view()
    if extractor.output_type == "annotation" and isinstance(result, list):
        result = remap_result_annotations(result, omap)
    # Remap any signal files this extractor wrote (its own signal, or a signal side-effect).
    _remap_signal_dir(project.path / "signals", omap, prefix=extractor.name)
    return result


def provenance_name(track_name: str, extractor: Any, result: Any) -> str:
    """The name a finished run's provenance record is keyed by.

    Layer-keyed tracks (chunking/embedding) return the produced manifest's ``Path``; their provenance
    is keyed by that path's stem (``{name}_{label}``) so a second run with different params writes a
    *separate* record instead of overwriting the first layer's (FR-4). Every other track keeps the bare
    ``track_name`` (one ``{name}.run.json``)."""
    if getattr(extractor, "layer_keyed", False) and isinstance(result, Path):
        return result.stem
    return track_name


def persist_track_outputs(project_dir: Path, extractor: Any, result: Any) -> str:
    """Persist a finished extractor run the one way both the HTTP server and the CLI use, so a track
    produced from either entry point leaves identical on-disk artifacts (annotation tracks coexist;
    content-addressed layer signals accumulate). Writes:

      - an annotation ``result`` -> ``tracks/{name}.jsonl`` (signal results were already written to
        ``signals/`` by ``extract`` itself, layer signals as ``{name}_{label}.json``);
      - ``manifests/{name}.manifest.json`` (the static track manifest);
      - ``manifests/{provenance_name}.run.json`` (resolved params; per-label for layer-keyed tracks).

    Returns the provenance name (``{name}_{label}`` for a layer, else ``{name}``)."""
    from palimpsest.atomic import atomic_write_text, write_run_provenance
    from palimpsest.tracks.params import track_clamps, track_provenance

    name = extractor.name
    if extractor.output_type == "annotation" and isinstance(result, list):
        from palimpsest.annotation.serializer import write_track
        write_track(project_dir / "tracks" / f"{name}.jsonl", result)

    manifest_dir = project_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        manifest_dir / f"{name}.manifest.json",
        json.dumps(extractor.manifest(), indent=2),
    )
    pname = provenance_name(name, extractor, result)
    clamped = track_clamps(extractor)
    write_run_provenance(
        manifest_dir, pname, track_provenance(extractor),
        extra={"clamped": clamped} if clamped else None,
    )
    return pname
