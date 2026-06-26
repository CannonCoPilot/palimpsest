"""ChunkingTrack — chunking promoted from a ``self_similarity`` local into a first-class layer-track.

Running this track chunks the project's analyzable text under a user-chosen mode/params and persists
the result as a reusable signal layer (``signals/chunking_{label}.json``). The layer is *plural*: a
different mode/size yields a different content-addressed ``label`` and therefore a distinct file, so
many chunk layers coexist for the same project without collision (FR-5). Downstream analyses declare a
dependency on a chunk layer (checked by the resolver, FR-7) instead of re-chunking inline.

Coordinate contract: the track runs against the masked *analysis view* (via ``runner.extract_masked``)
and emits chunk spans in analyzable coordinates as the manifest's top-level ``segment_offsets``; the
runner remaps those to original coordinates after extract (G4). Everything in ``metadata`` is
content/length data (chunk texts, distributions) that is invariant under that remap — no raw offsets
live there, so the G4 ``_assert_coordinates_blessed`` check passes.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

from palimpsest.atomic import atomic_write_text
from palimpsest.formats.signals import SignalManifest
from palimpsest.project import Project
from palimpsest.tracks.chunking import CHUNK_MODES, ChunkingConfig, chunk_text
from palimpsest.tracks.params import Param, ParameterizedTrack

Span = tuple[int, int]

# The chunking unit each mode operates over, for the capability descriptor (FR-6). word/slide/smart
# count word windows; verse aligns to verse bodies; punctuation splits on delimiters.
_MODE_UNIT = {"word": "word", "slide": "word", "smart": "unit", "verse": "verse", "punctuation": "delimiter"}


def _to_str_tuple(value: Any) -> tuple[str, ...]:
    """Coerce a user-supplied delimiters value to a tuple of strings (a lone string is one delimiter,
    not split into characters). ``ChunkingConfig`` does the real validation."""
    if isinstance(value, str):
        return (value,)
    return tuple(str(x) for x in value)


def _union_length(spans: list[Span]) -> int:
    """Total number of characters covered by ``spans``, counting overlaps once (merged intervals)."""
    if not spans:
        return 0
    ordered = sorted(spans)
    total = 0
    cur_start, cur_end = ordered[0]
    for s, e in ordered[1:]:
        if s > cur_end:
            total += cur_end - cur_start
            cur_start, cur_end = s, e
        else:
            cur_end = max(cur_end, e)
    total += cur_end - cur_start
    return total


def _dist(values: list[int]) -> dict[str, float]:
    """Summary distribution (mean/median/min/max) of ``values``; all-zero for an empty list."""
    if not values:
        return {"mean": 0.0, "median": 0.0, "min": 0, "max": 0}
    return {
        "mean": round(statistics.fmean(values), 4),
        "median": float(statistics.median(values)),
        "min": min(values),
        "max": max(values),
    }


class ChunkingTrack(ParameterizedTrack):
    # Marks this as a *label-keyed layer* track: it writes signals/{name}_{label}.json (plural, one per
    # param set), so the run handler stamps per-label provenance (manifests/{name}_{label}.run.json) and
    # /analysis/status enumerates the layers instead of looking for a single signals/{name}.json. Read
    # via getattr, so non-layer tracks are unaffected.
    layer_keyed = True

    # chunk_mode is the one required choice; the rest are mode-relevant and validated (presence + range
    # + cross-field exclusivity) by ChunkingConfig, the single source of truth for chunk-param validity.
    # They are declared here only so they are reported in provenance (G2), never silently defaulted.
    # The param names mirror the established self_similarity chunk vocabulary (chunk_mode/chunk_size/…)
    # that the shared HTTP run handler already forwards, so the track is produced through the same
    # surface as every other track (one vocabulary, routed by track_name) rather than a side door.
    PARAMS = (
        Param("chunk_mode", str, required=True, choices=CHUNK_MODES,
              help="chunking mode (word, slide, punctuation, verse, smart)"),
        Param("chunk_size", int, default=None, min=1, help="window size in words (word/slide/smart)"),
        Param("smart_unit", str, default=None, help="smart-mode growth unit (verse/paragraph/sentence)"),
        Param("delimiters", _to_str_tuple, default=None, help="punctuation-mode split delimiters"),
        Param("grow_factor", float, default=None, min=1, help="smart-mode growth factor (>= 1)"),
        Param("remainder_ratio", float, default=None, help="smart-mode remainder merge ratio (0, 1]"),
    )

    @property
    def name(self) -> str:
        return "chunking"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        # No upstream track: chunking is the first substrate-boundary layer. An empty list keeps it a
        # non-signal-consumer (runner.extract_masked masks + remaps it), which is what we want — chunk
        # spans are produced from the text and must be remapped analyzable->original.
        return []

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.chunking"]

    @property
    def evidence_level(self) -> str:
        # Chunking is a deterministic function of the text and chosen params — directly observed, not
        # inferred — so it carries the strongest evidence level.
        return "E1"

    def _config(self) -> ChunkingConfig:
        """Build the validated ChunkingConfig from resolved params. ChunkingConfig rejects any field
        not relevant to the mode and any missing required field, so a bad combination fails loud."""
        p = self.resolved_params()
        return ChunkingConfig(
            mode=p["chunk_mode"], size=p["chunk_size"], smart_unit=p["smart_unit"],
            delimiters=p["delimiters"], grow_factor=p["grow_factor"],
            remainder_ratio=p["remainder_ratio"],
        )

    def _unit_spans(
        self, project: Project, cfg: ChunkingConfig, text: str
    ) -> tuple[list[Span] | None, list[Span] | None, list[Span] | None]:
        """Resolve the verse/paragraph/sentence spans a unit-based mode needs (analyzable coords),
        mirroring self_similarity. A unit-based mode whose spans are unavailable raises in chunk_text
        rather than silently falling back."""
        verse = paragraph = sentence = None
        if cfg.mode == "verse" or (cfg.mode == "smart" and cfg.smart_unit == "verse"):
            verse = project.analyzable_verse_spans() or None
        elif cfg.mode == "smart" and cfg.smart_unit == "paragraph":
            paragraph = [(s, e) for s, e, _ in project.paragraphs()]
        elif cfg.mode == "smart" and cfg.smart_unit == "sentence":
            from palimpsest.ingest.segmenter import segment_sentences
            sentence = [(seg.start, seg.end) for seg in segment_sentences(text)]
        return verse, paragraph, sentence

    def _label(self, cfg: ChunkingConfig, analyzable_digest: str) -> str:
        """Content-addressed layer id: distinct mode/params or distinct analyzable text -> distinct
        label -> distinct path (FR-5). The digest binds the layer to the exact text it was computed on,
        so a descriptor can never be matched against a different masking of the document."""
        h = hashlib.sha256()
        h.update(repr((
            cfg.mode, cfg.size, cfg.smart_unit, cfg.delimiters, cfg.grow_factor, cfg.remainder_ratio,
        )).encode("utf-8"))
        h.update(b"\x00")
        h.update(analyzable_digest.encode("utf-8"))
        return h.hexdigest()[:16]

    def extract(self, project: Project) -> Path:
        # On an analysis view, reference_text() is the masked-resolved analyzable stream; chunk spans
        # are in its coordinates and remapped to original by runner.extract_masked after this returns.
        text = project.reference_text()
        cfg = self._config()
        verse_spans, paragraph_spans, sentence_spans = self._unit_spans(project, cfg, text)
        chunks = chunk_text(
            text, cfg, verse_spans=verse_spans,
            paragraph_spans=paragraph_spans, sentence_spans=sentence_spans,
        )

        analyzable_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        label = self._label(cfg, analyzable_digest)

        char_lens = [c["end"] - c["start"] for c in chunks]
        word_lens = [len(c["words"]) for c in chunks]
        covered = _union_length([(c["start"], c["end"]) for c in chunks])
        coverage_pct = round(100.0 * covered / len(text), 4) if text else 0.0
        overlaps = sum(1 for a, b in zip(chunks, chunks[1:]) if b["start"] < a["end"])
        overlap_ratio = round(overlaps / (len(chunks) - 1), 4) if len(chunks) > 1 else 0.0

        # FR-6 capability descriptor: the checkable facts a downstream dependency declares against.
        capability = {
            "kind": "chunk",
            "mode": cfg.mode,
            "overlapping": cfg.mode == "slide",
            "covers_full_text": coverage_pct >= 100.0,
            "unit": cfg.smart_unit if cfg.mode == "smart" else _MODE_UNIT[cfg.mode],
            "size": cfg.size,
            "analyzable_digest": analyzable_digest,
        }
        # FR-13 rendering backbone: the frontend draws any layer by rendering.track_view, so plural
        # chunk layers render with zero per-layer code.
        rendering = {
            "track_view": "chunk-band",
            "overviewBarRendering": {"type": "chunk-band", "color": "#6366F1"},
        }
        # FR-14 stats backbone: precomputed once (O(chunks)) so the stats UI shows numbers with no
        # recompute. boundary_alignment is intentionally deferred to P6, where coordinate-correct unit
        # spans (sentence/paragraph/verse/element) are wired for the stats surface.
        stats = {
            "count": len(chunks),
            "coverage_pct": coverage_pct,
            "overlap_ratio": overlap_ratio,
            "len_words": _dist(word_lens),
            "len_chars": _dist(char_lens),
        }

        metadata: dict[str, Any] = {
            "label": label,
            "capability": capability,
            "rendering": rendering,
            "stats": stats,
            # Analyzable chunk texts, in order — what an EmbeddingTrack (or any consumer) embeds. Stored
            # here (not reconstructed from offsets) because masking makes the analyzable text a non-
            # contiguous projection of the original; the texts are the ground truth of what was chunked.
            "chunk_texts": [c["text"] for c in chunks],
            "params": self.parameters(),
        }

        manifest = SignalManifest(
            type="chunk-layer",
            name=f"chunking_{label}",
            source="chunking/0.1",
            reference_sha256=project.metadata.reference_sha256,
            dimensions=[len(chunks)],
            segment_offsets=[[c["start"], c["end"]] for c in chunks],
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
            "trackName": "chunking",
            "bodyType": "signal",
            "dedicatedView": "chunk-band",
            "colorScheme": {"primary": "#6366F1", "secondary": "#4F46E5"},
        }
