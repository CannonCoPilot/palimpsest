"""Explicit layer-bundle binding (Wave-0 P7).

``self_similarity`` is a fail-loud *consumer*: the user names exactly which chunk / repeat_mask /
embedding layers to analyse (one bundle per chunk size), and this module binds those named layers by
path and validates they are mutually coherent — built on the same chunk layer and the same analyzable
view — before any analysis runs.

This is deliberately *not* :func:`palimpsest.tracks.requirements.resolve_layers`. That resolver
*discovers* a compatible layer from capability predicates and breaks ambiguity with newest-wins; here
the user is choosing specific reproducible artifacts by label, so binding is by explicit path (the
:meth:`EmbeddingTrack.extract` pattern) and the work is *coherence checking*, not discovery. A missing
or mis-paired layer raises :class:`LayerResolutionError`, which the run handlers already surface through
the same failed-job path as every other bad-input error.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from palimpsest.tracks.requirements import BoundLayer, LayerResolutionError


@dataclass(frozen=True)
class LayerBundle:
    """A coherent set of layers for one chunk size: the chunk layer, its required repeat_mask layer,
    optionally an embedding layer, and the repeat phrases reached through the mask's repeat layer
    (the source of ``exact_repeats`` in the consumer model)."""

    chunk: BoundLayer
    repeat_mask: BoundLayer
    embedding: BoundLayer | None
    repeat_phrases: list[str]

    @property
    def chunk_size(self) -> Any:
        return self.chunk.capability.get("size")


# A LayerBundle IS one operand of a comparison — one text's bound layers. The alias makes the
# two-operand generalization (cross-text, P10/FR-21) legible: today every comparison is A=A, so the
# same bundle is both operands.
Operand = LayerBundle


@dataclass(frozen=True)
class ComparisonSpec:
    """One resemblance comparison: two operands and the methods to run over them (P9/FR-18).

    Self-similarity is the degenerate ``A = B`` case — :meth:`self_` builds a spec whose two operands
    are the *same* object, so :attr:`is_self` is ``True``. A genuine two-operand (cross-text) spec,
    where ``operand_a`` and ``operand_b`` are different texts coordinate-mapped onto a root backbone, is
    the deferred P10/FR-21 extension this pre-stage is shaped to make additive. Today only the self case
    is constructed and executed."""

    operand_a: Operand
    operand_b: Operand
    methods: tuple[str, ...]

    @classmethod
    def self_(cls, operand: Operand, methods: tuple[str, ...]) -> "ComparisonSpec":
        """The ``A = B`` self-comparison: the same operand on both axes (``operand_a is operand_b``)."""
        return cls(operand, operand, methods)

    @property
    def is_self(self) -> bool:
        """``True`` when both operands are the same object — the only mode built today."""
        return self.operand_a is self.operand_b


def _load_layer(project: Any, prefix: str, label: str, kind: str) -> BoundLayer:
    """Load a persisted layer by explicit label (``signals/{prefix}{label}.json``), fail loud if
    absent. Mirrors ``EmbeddingTrack.extract``'s direct-path load."""
    path = Path(project.path) / "signals" / f"{prefix}{label}.json"
    if not path.exists():
        raise LayerResolutionError(
            f"{kind} layer '{prefix}{label}' not found at {path} — run the {kind} track first, or "
            "pass the label of an existing layer"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data.get("metadata", {})
    return BoundLayer(kind, meta.get("label", label), path, meta.get("capability", {}), data)


def coherence_reason(
    capability: dict[str, Any], kind: str, label: str, chunk_label: str, chunk_digest: Any
) -> str | None:
    """Why a repeat_mask/embedding layer is *not* bindable against a given chunk layer, or ``None``
    if it is coherent. A dependent layer must declare the chunk layer it was built on and the same
    analyzable digest, so it can never be paired against a different chunking or a different masking
    of the document.

    This is the single coherence predicate shared by run-time binding (:func:`_assert_coherent`,
    which raises on a truthy return) and display-time discovery (the ``self_similarity/inputs``
    endpoint, which routes a truthy return into its ``incompatible[]`` list). One predicate, two
    callers — discovery and binding can never disagree."""
    bound_chunk = capability.get("chunk_layer_id")
    if bound_chunk != chunk_label:
        return (
            f"{kind} layer '{label}' was built on chunk layer '{bound_chunk}', not '{chunk_label}' — "
            f"select a {kind} layer produced for this chunk layer"
        )
    bound_digest = capability.get("chunk_analyzable_digest")
    if chunk_digest is not None and bound_digest != chunk_digest:
        return (
            f"{kind} layer '{label}' has a different analyzable digest than chunk layer "
            f"'{chunk_label}' (a different masking of the document) — re-run it on the same view"
        )
    return None


def _assert_coherent(
    layer: BoundLayer, kind: str, label: str, chunk_label: str, chunk_digest: Any
) -> None:
    """Raise :class:`LayerResolutionError` if ``layer`` is not coherent with the chunk layer."""
    reason = coherence_reason(layer.capability, kind, label, chunk_label, chunk_digest)
    if reason:
        raise LayerResolutionError(reason)


def resolve_explicit_bundle(
    project: Any,
    chunk_label: str,
    repeat_mask_label: str,
    *,
    need_embedding: bool,
    embedding_label: str | None = None,
) -> LayerBundle:
    """Bind one chunk size's layers by explicit label and validate coherence, fail-loud.

    ``repeat_mask`` is REQUIRED (the consumer never masks inline). ``embedding`` is required only when
    an embedding-based metric is selected (``need_embedding``); ``embedding_label`` then names it.
    ``repeat_phrases`` are read from the repeats layer the mask was derived from (its
    ``capability.repeat_layer_id``) — the source of the manifest's ``exact_repeats`` in P7.
    """
    chunk = _load_layer(project, "chunking_", chunk_label, "chunk")
    chunk_digest = chunk.capability.get("analyzable_digest")

    repeat_mask = _load_layer(project, "repeat_mask_", repeat_mask_label, "repeat-mask")
    _assert_coherent(repeat_mask, "repeat-mask", repeat_mask_label, chunk_label, chunk_digest)

    embedding: BoundLayer | None = None
    if need_embedding:
        if not embedding_label:
            raise LayerResolutionError(
                "an embedding-based metric (cosine/jaccard) was requested but no embedding_label was "
                f"given for chunk layer '{chunk_label}'"
            )
        embedding = _load_layer(project, "embedding_", embedding_label, "embedding")
        _assert_coherent(embedding, "embedding", embedding_label, chunk_label, chunk_digest)

    repeat_label = repeat_mask.capability.get("repeat_layer_id")
    repeat_phrases: list[str] = []
    if repeat_label:
        repeats = _load_layer(project, "repeats_", repeat_label, "repeat-set")
        repeat_phrases = list(repeats.manifest.get("metadata", {}).get("phrases", []))

    return LayerBundle(chunk, repeat_mask, embedding, repeat_phrases)
