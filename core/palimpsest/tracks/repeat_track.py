"""RepeatTrack — exact-repeat detection promoted from a ``self_similarity`` local into a first-class,
chunk-independent layer-track (Wave-0 P8, FR-15).

Detection is deliberately decoupled from chunking: this track tokenises the project's analyzable text
directly (``repeats.detect_repeats``) and persists the repeated-phrase intervals as a reusable signal
layer (``signals/repeats_{label}.json``), with ``depends_on=[]`` so it runs before *or* after any
chunking. The layer is *plural* and content-addressed — distinct detection params or distinct analyzable
text yield a distinct ``label`` and file (FR-5) — and is consumed two ways downstream: a chunk layer can
hide its intervals before chunking (``ChunkingTrack.hide_repeats``, FR-16), and the ``repeat_mask`` track
flags repeat-dominated chunks after (FR-17).

Coordinate contract: like ``ChunkingTrack``, it runs against the masked analysis view (via
``runner.extract_masked``) and emits repeat spans in analyzable coordinates as the manifest's top-level
``segment_offsets``; the runner remaps those to original coordinates after extract (G4). ``metadata``
holds only phrases/counts/descriptors — no raw offsets — so the G4 coordinate check passes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from palimpsest.atomic import atomic_write_text
from palimpsest.formats.signals import SignalManifest
from palimpsest.project import Project
from palimpsest.tracks.params import Param, ParameterizedTrack
from palimpsest.tracks.repeats import (
    DEFAULT_MAX_PHRASE_LEN,
    EXACT_REPEAT_MIN_OCCURRENCES,
    EXACT_REPEAT_MIN_WORDS,
    detect_repeats,
)


class RepeatTrack(ParameterizedTrack):
    # Label-keyed layer track (see ChunkingTrack.layer_keyed): writes signals/repeats_{label}.json, gets
    # per-label provenance, and is enumerated as plural layers in /analysis/status.
    layer_keyed = True

    # The three masking constants, promoted from LOCKED module constants (repeats.py) to user-tunable
    # Params (G2). Defaults are exactly the prior LOCKED values, so default-param detection considers the
    # same phrases self_similarity finds inline; coverage_threshold is a *mask* knob and lives on the
    # repeat_mask track, not here (detection produces the repeat set; masking is a downstream policy).
    PARAMS = (
        Param("min_words", int, default=EXACT_REPEAT_MIN_WORDS, min=1,
              help="shortest repeated phrase, in words, considered a repeat"),
        Param("min_occurrences", int, default=EXACT_REPEAT_MIN_OCCURRENCES, min=2,
              help="times a phrase must recur across the text to count as a repeat"),
        Param("max_phrase_len", int, default=DEFAULT_MAX_PHRASE_LEN, min=1,
              help="longest repeated phrase, in words, considered"),
    )

    @property
    def name(self) -> str:
        return "repeats"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        # No upstream track: detection is text-level and order-independent of chunking. An empty list
        # keeps it a non-signal-consumer (runner.extract_masked masks + remaps it), which is what we
        # want — repeat spans are produced from the text and must be remapped analyzable->original.
        return []

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.repeats"]

    @property
    def evidence_level(self) -> str:
        # Exact repeats are a deterministic function of the text and chosen params — directly observed,
        # not inferred — so the strongest evidence level.
        return "E1"

    def _label(self, params: dict[str, Any], analyzable_digest: str) -> str:
        """Content-addressed layer id: distinct detection params or distinct analyzable text -> distinct
        label -> distinct path (FR-5), mirroring ChunkingTrack._label."""
        h = hashlib.sha256()
        h.update(repr((
            params["min_words"], params["min_occurrences"], params["max_phrase_len"],
        )).encode("utf-8"))
        h.update(b"\x00")
        h.update(analyzable_digest.encode("utf-8"))
        return h.hexdigest()[:16]

    def extract(self, project: Project) -> Path:
        # On an analysis view, reference_text() is the masked-resolved analyzable stream; repeat spans
        # are in its coordinates and remapped to original by runner.extract_masked after this returns.
        text = project.reference_text()
        p = self.resolved_params()
        phrases, intervals = detect_repeats(
            text,
            min_words=p["min_words"],
            min_occurrences=p["min_occurrences"],
            max_phrase_len=p["max_phrase_len"],
        )

        analyzable_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        label = self._label(p, analyzable_digest)

        covered = sum(e - s for s, e in intervals)
        coverage_pct = round(100.0 * covered / len(text), 4) if text else 0.0

        # FR-6 capability descriptor: the checkable facts a downstream dependency (hide_repeats,
        # repeat_mask) declares against. analyzable_digest binds the layer to the exact text detected on.
        capability = {
            "kind": "repeat-set",
            "min_words": p["min_words"],
            "min_occurrences": p["min_occurrences"],
            "max_phrase_len": p["max_phrase_len"],
            "analyzable_digest": analyzable_digest,
        }
        # FR-13 rendering backbone: drawn by rendering.track_view, so the repeat layer renders with zero
        # per-layer code (its repeated stretches shaded over the text).
        rendering = {
            "track_view": "repeat-band",
            "overviewBarRendering": {"type": "repeat-band", "color": "#F59E0B"},
        }
        # FR-14 stats backbone: precomputed once so the stats UI shows numbers with no recompute.
        stats = {
            "phrase_count": len(phrases),
            "interval_count": len(intervals),
            "coverage_pct": coverage_pct,
        }

        metadata: dict[str, Any] = {
            "label": label,
            "capability": capability,
            "rendering": rendering,
            "stats": stats,
            # The detected repeated phrases (normalised), sorted for a stable manifest. Strings, not
            # offsets, so they are invariant under the analyzable->original remap (G4).
            "phrases": sorted(phrases),
            "params": self.parameters(),
        }

        manifest = SignalManifest(
            type="repeat-layer",
            name=f"repeats_{label}",
            source="repeats/0.1",
            reference_sha256=project.metadata.reference_sha256,
            dimensions=[len(intervals)],
            segment_offsets=[[s, e] for s, e in intervals],
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
            "trackName": "repeats",
            "bodyType": "signal",
            "dedicatedView": "repeat-band",
            "colorScheme": {"primary": "#F59E0B", "secondary": "#D97706"},
        }
