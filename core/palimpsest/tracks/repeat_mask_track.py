"""RepeatMaskTrack — post-chunk repeat masking as a flag-only layer (Wave-0 P8, FR-17).

Binds a persisted chunk layer and a persisted repeat layer (via the dependency resolver, FR-7), flags
each chunk whose content is dominated by repeated phrases (``repeats.mask_repeats`` at a user-tunable
``coverage_threshold``), and persists the per-chunk boolean flags as a reusable signal layer
(``signals/repeat_mask_{chunk_label}_{repeat_label}.json``). It is *flag-only*: it records which chunks
are repeat-dominated and never mutates the chunk or embedding layers — a consumer (the P7
``self_similarity`` redesign) decides what to do with the flags.

This is the first track to drive ``resolve_layers``: it declares ``layer_requirements`` and **fails
loud** (``LayerResolutionError``) if no compatible chunk + repeat layers exist, rather than silently
producing nothing. It is a *signal consumer* (it ``depends_on`` both producing tracks), so
``runner.extract_masked`` runs it on the full project and does not remap it — it reads, and copies
through, the chunk layer's already-original ``segment_offsets`` so the flag lane renders against the
original document, index-aligned to the chunks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from palimpsest.atomic import atomic_write_text
from palimpsest.formats.signals import SignalManifest
from palimpsest.project import Project
from palimpsest.tracks.params import Param, ParameterizedTrack
from palimpsest.tracks.repeats import MASK_COVERAGE_THRESHOLD, mask_repeats
from palimpsest.tracks.requirements import LayerRequirement, resolve_layers


class RepeatMaskTrack(ParameterizedTrack):
    # Label-keyed layer track: writes signals/repeat_mask_{chunk_label}_{repeat_label}.json, gets
    # per-binding provenance, and is enumerated as plural layers in /analysis/status.
    layer_keyed = True

    # Resolved against persisted layers (FR-7) rather than triggering hidden production: a chunk layer
    # and a repeat layer computed on the same analyzable view (digest_match defaults on). Read by the
    # resolver, not part of the TrackExtractor protocol.
    layer_requirements = [
        LayerRequirement(kind="chunk"),
        LayerRequirement(kind="repeat-set"),
    ]

    # coverage_threshold is the one masking knob, promoted from the LOCKED module constant to a tunable
    # Param (G2). Its default is exactly the prior LOCKED value, so the default masking decision matches
    # self_similarity's inline pass.
    PARAMS = (
        Param("coverage_threshold", float, default=MASK_COVERAGE_THRESHOLD, min=0.0, max=1.0,
              help="fraction of a chunk's content words covered by repeats to flag it (0, 1]"),
    )

    @property
    def name(self) -> str:
        return "repeat_mask"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        # Depends on both producing tracks: this makes it a signal-consumer (runs on the full project,
        # no remap — it reads already-original layer coordinates) and orders it after both. The specific
        # layers are bound by the resolver via layer_requirements, not by these names.
        return ["chunking", "repeats"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.repeat_mask"]

    @property
    def evidence_level(self) -> str:
        return "E1"

    def extract(self, project: Project) -> Path:
        p = self.resolved_params()
        # Fail-loud binding: raises LayerResolutionError if no compatible chunk/repeat layer exists.
        bound = resolve_layers(project, self.layer_requirements)
        chunk = bound["chunk"]
        repeat = bound["repeat-set"]

        chunk_texts: list[str] = chunk.manifest["metadata"]["chunk_texts"]
        phrases = set(repeat.manifest["metadata"].get("phrases", []))

        # Reconstruct the chunk dicts mask_repeats consumes. The chunk layer stored chunk_texts (the
        # ground truth of what was chunked); words = text.split() reproduces the original chunk["words"]
        # (chunk_text builds words the same way), so masking is identical to the inline pass.
        chunks: list[dict[str, Any]] = [{"words": t.split()} for t in chunk_texts]
        mask_repeats(chunks, phrases, p["coverage_threshold"])
        masked = [bool(c["masked"]) for c in chunks]
        masked_count = sum(masked)

        label = f"{chunk.label}_{repeat.label}"
        capability = {
            "kind": "repeat-mask",
            "chunk_layer_id": chunk.label,
            "repeat_layer_id": repeat.label,
            "coverage_threshold": p["coverage_threshold"],
            "chunk_analyzable_digest": chunk.capability.get("analyzable_digest"),
        }
        # FR-13 rendering backbone: a chunk-band lane with the repeat-dominated chunks shaded.
        rendering = {
            "track_view": "chunk-band",
            "shade": "masked",
            "overviewBarRendering": {"type": "chunk-band", "color": "#EF4444"},
        }
        # FR-14 stats backbone.
        stats = {
            "chunk_count": len(chunks),
            "masked_count": masked_count,
            "masked_ratio": round(masked_count / len(chunks), 4) if chunks else 0.0,
            "phrase_count": len(phrases),
        }

        metadata: dict[str, Any] = {
            "label": label,
            "capability": capability,
            "rendering": rendering,
            "stats": stats,
            # Per-chunk repeat-dominated flags, index-aligned to the bound chunk layer's chunks.
            "masked": masked,
            "params": self.parameters(),
        }

        manifest = SignalManifest(
            type="repeat-mask-layer",
            name=f"repeat_mask_{label}",
            source="repeat_mask/0.1",
            reference_sha256=project.metadata.reference_sha256,
            dimensions=[len(chunks)],
            # Copied through from the bound chunk layer (already original coordinates); this track is a
            # signal-consumer and is not remapped, so it must not introduce analyzable coordinates.
            segment_offsets=chunk.manifest.get("segment_offsets", []),
            metadata=metadata,
        )

        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = signals_dir / f"{manifest.name}.json"
        atomic_write_text(
            manifest_path,
            json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        )
        return manifest_path

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "repeat_mask",
            "bodyType": "signal",
            "dedicatedView": "chunk-band",
            "colorScheme": {"primary": "#EF4444", "secondary": "#DC2626"},
        }
