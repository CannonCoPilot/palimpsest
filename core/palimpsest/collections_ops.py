"""Collections operations — the cross-text analytical substrate (Collections tier, phase C1).

Wave 0 made a *single* text's layers first-class. This module is the *multi-text* foundation the
Collections tier builds on (see ``docs/development/design/collections-tier-{vision,plan}.md``). It is
pure substrate — object-model navigation, the metric-congruence contract, cross-project operand
resolution, and non-destructive run versioning — with no visualization or analysis of its own. The
pairwise engine (C2) and corpus graph (C3) consume what is defined here.

Design decisions encoded here (collections-tier-plan §0; OQ-1…7 ratified 2026-06-30):

* **Lightweight object model (OQ-2, FR-23/43).** A *Work* is a user-asserted ``work_id`` tag carried
  in project metadata, not a heavy entity; the subtext edge is ``parent_project_id`` (FR-43). Both are
  read as *loose* metadata fields, mirroring how ``parent_project_id`` is already persisted, so the
  :class:`palimpsest.project.ProjectMetadata` dataclass and its serialization contract are untouched.

* **Metric congruence (FR-27) is a cross-project comparability test, distinct from intra-project
  coherence.** ``tracks.bundles.coherence_reason`` (FR-7) already checks, *within one project*, that an
  embedding/mask layer was built on its chunk layer and the same analyzable digest. Congruence is the
  orthogonal *cross-project* question: are two operands comparable on metric X? For embedding metrics
  that means the *same embedding space* (``model_fingerprint`` = provider+endpoint+model+dim); for
  token metrics (edit_distance/word_overlap) that read raw chunk strings, any two chunked texts are
  congruent. The per-text analyzable digest is deliberately **not** part of this key: two distinct
  texts always have distinct digests, so folding it in would make cross-text comparison impossible by
  construction. (The vision lists the digest in the congruence key; that is the intra-project coherence
  field, enforced separately — see the FR-7 note above.)

* **Non-destructive run versioning (FR-41) + identity-based staleness (FR-28).** Re-running a
  comparison *appends* a version, never overwrites; a result is content-addressed by operand identity,
  so a changed operand (e.g. a ground-truth-masking re-run) surfaces as a new identity and the prior
  result as *stale*, never a silent overwrite.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from palimpsest import collections as col_store
from palimpsest.tracks.bundles import ComparisonSpec, Operand, resolve_explicit_bundle
from palimpsest.tracks.requirements import _enumerate_layers

_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")


class MetricCongruenceError(ValueError):
    """Two operands are not comparable on a metric (FR-27). Subclasses :class:`ValueError` (like
    :class:`LayerResolutionError`) so run handlers surface it through the same failed-job path, and
    carries the reconcile hint (re-embed into a common space)."""


def _safe_id(project_id: str) -> str:
    if not _ID_RE.match(project_id):
        raise ValueError(f"invalid project id {project_id!r}")
    return project_id


def _project_ref(workspace: Path, project_id: str) -> SimpleNamespace:
    """A lightweight stand-in carrying ``.path`` for the layer-binding helpers (which only read
    ``signals/`` by path). Avoids the cost of a full :meth:`Project.load` while still asserting the
    project exists (fail-loud on an unknown id)."""
    _safe_id(project_id)
    pdir = workspace / project_id
    if not (pdir / "metadata.json").exists():
        raise FileNotFoundError(f"project {project_id!r} not found under {workspace}")
    return SimpleNamespace(path=pdir)


def _read_metadata(workspace: Path, project_id: str) -> dict[str, Any]:
    _safe_id(project_id)
    p = workspace / project_id / "metadata.json"
    if not p.exists():
        raise FileNotFoundError(f"project {project_id!r} not found under {workspace}")
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Object model: Work tag + subtext edge (loose metadata fields, FR-23/43) ──────────────────────

def project_work_id(workspace: Path, project_id: str) -> str | None:
    """The project's user-asserted ``work_id`` tag, or ``None`` (OQ-2). Read loosely so the
    ProjectMetadata serialization contract is untouched."""
    try:
        return _read_metadata(workspace, project_id).get("work_id")
    except FileNotFoundError:
        return None


def set_project_work_id(workspace: Path, project_id: str, work_id: str | None) -> None:
    """Set (or clear, with ``None``) the project's ``work_id``, preserving every other metadata key."""
    meta = _read_metadata(workspace, project_id)
    if work_id:
        meta["work_id"] = work_id
    else:
        meta.pop("work_id", None)
    _write_json(workspace / project_id / "metadata.json", meta)


def project_parent_id(workspace: Path, project_id: str) -> str | None:
    """The id of the parent project this project was derived from (subtext edge, FR-43), or ``None``."""
    try:
        return _read_metadata(workspace, project_id).get("parent_project_id")
    except FileNotFoundError:
        return None


# ── Membership lattice + inverse navigation (FR-24) ───────────────────────────────────────────────

def all_project_ids(workspace: Path) -> list[str]:
    """Every project id in the workspace (a directory holding ``metadata.json``), sorted. Dot-prefixed
    bookkeeping dirs (``.comparisons``, ``.analysis``) are skipped."""
    if not workspace.is_dir():
        return []
    out = []
    for child in sorted(workspace.iterdir()):
        if child.name.startswith(".") or not child.is_dir():
            continue
        if (child / "metadata.json").exists():
            out.append(child.name)
    return out


def edition_siblings(workspace: Path, project_id: str) -> list[str]:
    """Other projects sharing this project's ``work_id`` — the edition-sibling navigation (FR-24).
    Empty when the project has no ``work_id``."""
    work = project_work_id(workspace, project_id)
    if not work:
        return []
    return [
        pid for pid in all_project_ids(workspace)
        if pid != project_id and project_work_id(workspace, pid) == work
    ]


def subtext_children(workspace: Path, project_id: str) -> list[str]:
    """Projects derived from this one by subtext extraction (their ``parent_project_id`` is this id;
    FR-43/FR-24)."""
    return [
        pid for pid in all_project_ids(workspace)
        if project_parent_id(workspace, pid) == project_id
    ]


def project_lattice(workspace: Path, project_id: str) -> dict[str, Any]:
    """The full inverse-navigation view for a project (FR-24): its Work tag, parent + derived
    children (subtext edge), edition siblings (shared Work), and the collections it belongs to."""
    _project_ref(workspace, project_id)  # fail-loud on an unknown project id
    return {
        "project_id": project_id,
        "work_id": project_work_id(workspace, project_id),
        "parent": project_parent_id(workspace, project_id),
        "children": subtext_children(workspace, project_id),
        "siblings": edition_siblings(workspace, project_id),
        "collections": col_store.collections_for_project(workspace, project_id),
    }


# ── Metric-congruence contract (FR-27) ────────────────────────────────────────────────────────────

def metric_needs_embedding(metric: str) -> bool:
    """Whether ``metric`` compares embedding vectors (cosine/jaccard) vs raw chunk strings
    (edit_distance/word_overlap). Reuses the canonical :data:`SimilarityMethod` registry (fail-loud on
    an unknown metric name) so this never drifts from what the analysis engine actually runs."""
    from palimpsest.tracks.self_similarity import resolve_methods

    return resolve_methods([metric])[0].requires_embedding


def congruence_key(metric: str, *, embedding_capability: dict[str, Any] | None = None) -> str:
    """The cross-text comparability key for ``metric`` (FR-27). Two operands are comparable on the
    metric iff their keys are equal.

    Token metrics read raw chunk strings → congruent across any two chunked texts: the key is
    metric-only. Embedding metrics require the *same* vector space → the key folds in the embedding
    layer's ``model_fingerprint`` (a digest of provider+endpoint+model+dim), falling back to
    ``provider:model:dim`` when no fingerprint was recorded."""
    if not metric_needs_embedding(metric):
        return f"tokens:{metric}"
    if embedding_capability is None:
        raise MetricCongruenceError(
            f"metric {metric!r} is embedding-based but no embedding capability was provided"
        )
    fp = embedding_capability.get("model_fingerprint")
    if fp:
        return f"embedding:{metric}:{fp}"
    prov = embedding_capability.get("provider")
    model = embedding_capability.get("model")
    dim = embedding_capability.get("dim")
    return f"embedding:{metric}:{prov}:{model}:{dim}"


def operands_congruent(
    metric: str, cap_a: dict[str, Any] | None, cap_b: dict[str, Any] | None
) -> tuple[bool, str | None]:
    """Whether two operands are comparable on ``metric``. Returns ``(ok, reason)``; on mismatch the
    reason names the divergence and the reconcile action. ``cap_*`` are the operands' embedding
    capabilities (ignored for token metrics)."""
    try:
        ka = congruence_key(metric, embedding_capability=cap_a)
        kb = congruence_key(metric, embedding_capability=cap_b)
    except MetricCongruenceError as exc:
        return False, str(exc)
    if ka == kb:
        return True, None
    return False, (
        f"operands are not congruent on metric {metric!r}: {ka} vs {kb}. Reconcile by re-embedding "
        "both operands into a common space (same model + params + dimensionality)."
    )


def member_embedding_layer(
    workspace: Path, project_id: str, embedding_label: str | None = None
) -> Any | None:
    """The member's chosen embedding :class:`BoundLayer` (newest-wins, or the named label), or ``None``
    if it has no matching embedding layer. Returns the whole layer — carrying ``label`` (→ its
    ``cache/embeddings_{label}.db``) and ``capability`` — so the probe (C6b) can both congruence-gate on
    the capability and locate the vector store from one newest-wins resolution."""
    ref = _project_ref(workspace, project_id)
    layers = _enumerate_layers(ref, "embedding")
    if embedding_label is not None:
        layers = [layer for layer in layers if layer.label == embedding_label]
    if not layers:
        return None
    return max(layers, key=lambda layer: layer.manifest_path.stat().st_mtime)


def member_embedding_capability(
    workspace: Path, project_id: str, embedding_label: str | None = None
) -> dict[str, Any] | None:
    """The embedding-layer capability for a member (newest-wins, or the named label), or ``None`` if
    the member has no matching embedding layer."""
    layer = member_embedding_layer(workspace, project_id, embedding_label)
    return layer.capability if layer else None


def congruence_report(
    workspace: Path, collection_id: str, metric: str, embedding_label: str | None = None
) -> dict[str, Any]:
    """Per-metric congruence across a collection's members — the data behind the compatibility badge
    (FR-39). Reports each member's congruence key, the congruent cohorts (key → members), members
    missing the required layer, and whether the whole collection is congruent on the metric."""
    col = col_store.get_collection(workspace, collection_id)
    if col is None:
        raise KeyError(collection_id)
    members: list[str] = col.get("project_ids", [])
    needs_embed = metric_needs_embedding(metric)
    keys: dict[str, str | None] = {}
    missing: list[str] = []
    for pid in members:
        if needs_embed:
            cap = member_embedding_capability(workspace, pid, embedding_label)
            if cap is None:
                keys[pid] = None
                missing.append(pid)
                continue
            keys[pid] = congruence_key(metric, embedding_capability=cap)
        else:
            keys[pid] = congruence_key(metric)
    groups: dict[str, list[str]] = {}
    for pid, key in keys.items():
        if key is not None:
            groups.setdefault(key, []).append(pid)
    distinct = {key for key in keys.values() if key is not None}
    all_congruent = len(distinct) <= 1 and not missing
    return {
        "collection_id": collection_id,
        "metric": metric,
        "needs_embedding": needs_embed,
        "members": members,
        "keys": keys,
        "groups": groups,
        "missing": missing,
        "all_congruent": all_congruent,
        "reconcile_hint": None if all_congruent else (
            "re-embed members into a common space (same model + params + dim) to compare on this metric"
        ),
    }


# ── Cross-project operand resolution (FR-26) ──────────────────────────────────────────────────────

def resolve_operand(
    workspace: Path,
    project_id: str,
    chunk_label: str,
    repeat_mask_label: str,
    *,
    need_embedding: bool = False,
    embedding_label: str | None = None,
) -> Operand:
    """Bind a member project's named layers into an :class:`Operand`, fail-loud (FR-26). Reuses the
    Wave-0 explicit-bundle binding (``resolve_explicit_bundle``, FR-7) across projects — the only new
    thing is resolving the project *by id within the workspace*."""
    ref = _project_ref(workspace, project_id)
    return resolve_explicit_bundle(
        ref, chunk_label, repeat_mask_label,
        need_embedding=need_embedding, embedding_label=embedding_label,
    )


def resolve_comparison(
    workspace: Path,
    *,
    a_id: str,
    b_id: str,
    chunk_label: str,
    repeat_mask_label: str,
    methods: list[str] | tuple[str, ...],
    embedding_label: str | None = None,
    b_chunk_label: str | None = None,
    b_repeat_mask_label: str | None = None,
    b_embedding_label: str | None = None,
) -> ComparisonSpec:
    """Resolve a genuine two-operand (cross-text) :class:`ComparisonSpec`, gated by metric congruence
    (FR-26 + FR-27). Raises :class:`MetricCongruenceError` if any embedding metric's operands are not
    in the same space — never a silent cross-space comparison. The resulting spec has
    ``operand_a is not operand_b`` (``is_self`` is ``False``), the P10 seam P9 was shaped for."""
    methods = tuple(methods)
    if not methods:
        raise ValueError("at least one method is required")
    need = any(metric_needs_embedding(m) for m in methods)  # also validates metric names, fail-loud
    op_a = resolve_operand(
        workspace, a_id, chunk_label, repeat_mask_label,
        need_embedding=need, embedding_label=embedding_label,
    )
    op_b = resolve_operand(
        workspace, b_id, b_chunk_label or chunk_label, b_repeat_mask_label or repeat_mask_label,
        need_embedding=need, embedding_label=b_embedding_label or embedding_label,
    )
    for m in methods:
        if metric_needs_embedding(m):
            cap_a = op_a.embedding.capability if op_a.embedding else None
            cap_b = op_b.embedding.capability if op_b.embedding else None
            ok, reason = operands_congruent(m, cap_a, cap_b)
            if not ok:
                raise MetricCongruenceError(reason)
    return ComparisonSpec(op_a, op_b, methods)


# ── Operand identity + non-destructive run versioning (FR-28, FR-41) ──────────────────────────────

def operand_identity(operand: Operand) -> str:
    """A content-address for an operand: its chunk layer (label + analyzable digest), repeat-mask
    label, and — when present — its embedding space + chunk digest. Because the chunk's analyzable
    digest encodes the text *and its ground-truth masking*, a ground-truth-masking re-run changes the
    operand identity, which is exactly what drives FR-28 staleness."""
    parts = [
        str(operand.chunk.capability.get("analyzable_digest", "")),
        operand.chunk.label,
        operand.repeat_mask.label,
    ]
    if operand.embedding is not None:
        parts.append(str(operand.embedding.capability.get(
            "model_fingerprint", operand.embedding.label)))
        parts.append(str(operand.embedding.capability.get("chunk_analyzable_digest", "")))
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]


def comparison_identity(spec: ComparisonSpec) -> str:
    """A content-address for a comparison result: both operand identities (ordered — the stored
    artifact is directional, query→target) and the method set."""
    payload = "|".join([
        operand_identity(spec.operand_a),
        operand_identity(spec.operand_b),
        ",".join(spec.methods),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def load_run_versions(versions_path: Path) -> list[dict[str, Any]]:
    """All recorded versions for a result (newest last), or ``[]``."""
    if not versions_path.exists():
        return []
    data = json.loads(versions_path.read_text(encoding="utf-8"))
    versions = data.get("versions", []) if isinstance(data, dict) else []
    return versions if isinstance(versions, list) else []


def append_run_version(
    versions_path: Path, identity: str, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Append a result version *non-destructively* (FR-41) — prior versions are kept. Returns the new
    version record. Version ids are a monotonic ``v{N}`` index (deterministic, no wall-clock)."""
    versions = load_run_versions(versions_path)
    version = {
        "version_id": f"v{len(versions) + 1}",
        "identity": identity,
        "metadata": metadata or {},
    }
    versions.append(version)
    _write_json(versions_path, {"versions": versions})
    return version


def latest_run_version(versions_path: Path) -> dict[str, Any] | None:
    versions = load_run_versions(versions_path)
    return versions[-1] if versions else None


def delete_run_version(versions_path: Path, version_id: str) -> bool:
    """Delete one version (user-deletable, FR-41). Returns ``True`` if a version was removed."""
    versions = load_run_versions(versions_path)
    kept = [v for v in versions if v.get("version_id") != version_id]
    if len(kept) == len(versions):
        return False
    _write_json(versions_path, {"versions": kept})
    return True


def is_stale(versions_path: Path, current_identity: str) -> bool:
    """Whether the latest recorded result is stale: its operand-comparison identity no longer matches
    the current operands (e.g. a ground-truth-masking re-run changed an operand). FR-28."""
    latest = latest_run_version(versions_path)
    return latest is not None and latest.get("identity") != current_identity
