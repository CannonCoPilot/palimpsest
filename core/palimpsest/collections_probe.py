"""collections_probe — R(q, Corpus) retrieval over a collection's shared embedding space (C6b).

Sibling to ``collections_ops`` (substrate) and ``collections_masking`` (C5): the probe assembler. A
query vector is ranked against every member's chunk embeddings and the corpus-wide top-k is returned
with member + chunk attribution.

The honesty guarantee is the C1 metric-congruence contract (FR-27/39), applied twice:

  * **Members** — every member must resolve one embedding layer *and* share a single congruence key
    (same ``model_fingerprint`` = provider+endpoint+model+dim). A member missing the layer, or sitting
    in a different embedding space, raises :class:`MetricCongruenceError` — never a silent probe over a
    partial or mixed-space corpus.
  * **Query** — the query vector must have the corpus dimension; and when a fingerprint is supplied
    (the HTTP/CLI text path re-derives it from the caller's provider/endpoint/model), it must equal the
    corpus key's fingerprint. A query embedded in a different space is rejected before any search.

Query *text* → vector is deliberately not the core's job: that is embedding-service I/O (MLX/Ollama),
done at the boundary by :func:`embed_probe_query`. The core :func:`probe_corpus` takes a vector, so it
is deterministic and unit-testable without a live service. A service-free query is also available via
:func:`query_vector_from_ref` (reuse a passage already embedded in the corpus).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from palimpsest import collections as col_store
from palimpsest.collections_ops import (
    MetricCongruenceError,
    congruence_key,
    member_embedding_layer,
    metric_needs_embedding,
)
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore


def _embeddings_db(workspace: Path, project_id: str, label: str) -> Path:
    """The vector store for a member's embedding layer (``EmbeddingTrack`` writes here)."""
    return workspace / project_id / "cache" / f"embeddings_{label}.db"


def _fingerprint(provider: str, endpoint: str, model: str, dim: int) -> str:
    """Re-derive an embedding ``model_fingerprint`` exactly as ``EmbeddingTrack.extract`` does, so a
    query embedded at the boundary can be checked against the corpus's congruence key."""
    return hashlib.sha256(f"{provider}:{endpoint}:{model}:{dim}".encode()).hexdigest()[:16]


class _MemberLayer:
    """A resolved member embedding layer: project id, layer label, its vector DB, and capability."""

    __slots__ = ("project_id", "label", "db_path", "capability", "key")

    def __init__(self, project_id: str, label: str, db_path: Path, capability: dict[str, Any], key: str):
        self.project_id = project_id
        self.label = label
        self.db_path = db_path
        self.capability = capability
        self.key = key


def _gate_congruent_cohort(
    workspace: Path, collection_id: str, metric: str, embedding_label: str | None
) -> tuple[list[_MemberLayer], str, int]:
    """Resolve every member's embedding layer and fail loud unless they share one congruence key.

    Returns ``(members, shared_key, dim)``. Raises :class:`MetricCongruenceError` naming the members
    missing an embedding layer and/or the divergent congruence keys — the same honest picture the
    compatibility badge shows (FR-39), never a silent partial/mixed-space probe."""
    if not metric_needs_embedding(metric):
        raise ValueError(
            f"probe requires an embedding metric (a vector space to search); {metric!r} is a token "
            "metric with no embedding space"
        )
    col = col_store.get_collection(workspace, collection_id)
    if col is None:
        raise KeyError(collection_id)
    member_ids: list[str] = col.get("project_ids", [])
    if not member_ids:
        raise ValueError(f"collection {collection_id!r} has no members to probe")

    resolved: list[_MemberLayer] = []
    missing: list[str] = []
    for pid in member_ids:
        layer = member_embedding_layer(workspace, pid, embedding_label)
        if layer is None:
            missing.append(pid)
            continue
        key = congruence_key(metric, embedding_capability=layer.capability)
        resolved.append(
            _MemberLayer(pid, layer.label, _embeddings_db(workspace, pid, layer.label), layer.capability, key)
        )
    if missing:
        raise MetricCongruenceError(
            f"cannot probe collection {collection_id!r} on metric {metric!r}: members {missing} have no "
            f"matching embedding layer. Reconcile by embedding them into the corpus's space."
        )
    distinct = sorted({m.key for m in resolved})
    if len(distinct) > 1:
        cohorts = {key: [m.project_id for m in resolved if m.key == key] for key in distinct}
        raise MetricCongruenceError(
            f"members are not congruent on metric {metric!r}: {cohorts}. Reconcile by re-embedding all "
            "members into a common space (same model + params + dimensionality)."
        )
    shared_key = distinct[0]
    dims = {int(m.capability.get("dim", 0)) for m in resolved}
    if len(dims) > 1:  # fingerprints agreed but dims disagree — corrupt capability, refuse to guess
        raise MetricCongruenceError(
            f"members share a congruence key but report different dimensions {sorted(dims)} — refusing "
            "to probe an inconsistent corpus"
        )
    return resolved, shared_key, dims.pop()


def _member_chunk_texts(workspace: Path, member: _MemberLayer) -> list[str]:
    """The chunk texts backing a member's embedding layer (for result snippets), or ``[]`` if the
    source chunk layer is gone. Read once per member; embedding row *i* is chunk *i*."""
    chunk_label = member.capability.get("chunk_layer_id")
    if not chunk_label:
        return []
    path = workspace / member.project_id / "signals" / f"chunking_{chunk_label}.json"
    if not path.exists():
        return []
    manifest = json.loads(path.read_text(encoding="utf-8"))
    texts = manifest.get("metadata", {}).get("chunk_texts")
    return texts if isinstance(texts, list) else []


def _parse_chunk_index(vector_id: str, member_id: str, label: str) -> int | None:
    """Recover the chunk index from an embedding id ``{project}:{label}:{index}`` (project ids and
    labels are colon-free), or ``None`` if it does not parse to this member/label."""
    prefix = f"{member_id}:{label}:"
    if vector_id.startswith(prefix):
        tail = vector_id[len(prefix):]
        if tail.isdigit():
            return int(tail)
    return None


def probe_corpus(
    workspace: Path,
    collection_id: str,
    query_vector: list[float],
    *,
    metric: str = "cosine",
    embedding_label: str | None = None,
    k: int = 10,
    per_member_k: int | None = None,
    snippet_chars: int = 200,
    query_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Rank corpus chunks against ``query_vector`` over the shared embedding space (C6b, FR-31).

    Gated by the C1 metric-congruence contract: fail-loud on any member missing the layer or in a
    different space, and — when ``query_fingerprint`` is given — on a query embedded in a different
    space. Searches each member's store for its top ``per_member_k`` (default ``k``), merges to a
    corpus-wide top ``k`` with ``(project_id, chunk_index, text, similarity)`` attribution. Every search
    is reported (``members_searched``, ``n_candidates``) so nothing is silently dropped."""
    members, shared_key, dim = _gate_congruent_cohort(workspace, collection_id, metric, embedding_label)

    qdim = len(query_vector)
    if qdim != dim:
        raise MetricCongruenceError(
            f"query vector has dimension {qdim} but the corpus embedding space is {dim}-dimensional — "
            "the query is not in the members' space"
        )
    if query_fingerprint is not None:
        # shared_key == f"embedding:{metric}:{fingerprint}" — the query must carry the same fingerprint.
        corpus_fp = shared_key.split(":", 2)[2]
        if query_fingerprint != corpus_fp:
            raise MetricCongruenceError(
                f"query was embedded in a different space (fingerprint {query_fingerprint}) than the "
                f"corpus ({corpus_fp}) — re-embed the query with the members' provider/endpoint/model"
            )

    depth = per_member_k if per_member_k is not None else k
    candidates: list[dict[str, Any]] = []
    for member in members:
        if not member.db_path.exists():
            raise FileNotFoundError(
                f"embedding store missing for member {member.project_id!r} (layer {member.label}) at "
                f"{member.db_path} — the manifest exists but its vectors do not"
            )
        store = SqliteVecStore.open_existing(member.db_path)
        try:
            hits = store.search(query_vector, k=depth)
        finally:
            store.close()
        texts = _member_chunk_texts(workspace, member) if snippet_chars > 0 else []
        for vector_id, similarity in hits:
            idx = _parse_chunk_index(vector_id, member.project_id, member.label)
            snippet = None
            if snippet_chars > 0 and idx is not None and 0 <= idx < len(texts):
                snippet = texts[idx][:snippet_chars]
            candidates.append({
                "project_id": member.project_id,
                "label": member.label,
                "chunk_index": idx,
                "similarity": round(float(similarity), 6),
                "text": snippet,
            })

    candidates.sort(key=lambda c: (-c["similarity"], c["project_id"], c["chunk_index"] if c["chunk_index"] is not None else -1))
    return {
        "collection_id": collection_id,
        "metric": metric,
        "congruence_key": shared_key,
        "dim": dim,
        "k": k,
        "per_member_k": depth,
        "members_searched": [m.project_id for m in members],
        "n_candidates": len(candidates),
        "results": candidates[:k],
    }


def query_vector_from_ref(
    workspace: Path,
    project_id: str,
    chunk_index: int,
    *,
    embedding_label: str | None = None,
) -> list[float]:
    """A service-free query: the embedding vector of an existing corpus passage (member ``project_id``,
    chunk ``chunk_index``). Lets a probe run with no live embedding service — 'find passages like this
    one'. Fail-loud if the member has no embedding layer or the index is out of range."""
    layer = member_embedding_layer(workspace, project_id, embedding_label)
    if layer is None:
        raise ValueError(f"member {project_id!r} has no embedding layer to draw a query from")
    db_path = _embeddings_db(workspace, project_id, layer.label)
    if not db_path.exists():
        raise FileNotFoundError(f"embedding store missing at {db_path}")
    store = SqliteVecStore.open_existing(db_path)
    try:
        vectors = store.get_all_vectors()
    finally:
        store.close()
    if not 0 <= chunk_index < len(vectors):
        raise ValueError(
            f"chunk_index {chunk_index} out of range for member {project_id!r} "
            f"({len(vectors)} chunks embedded)"
        )
    return vectors[chunk_index]


def embed_probe_query(
    text: str, *, provider: str, endpoint: str, model: str
) -> tuple[list[float], str]:
    """Boundary I/O: embed a query string, returning ``(vector, model_fingerprint)``.

    Lives here (not in the pure core) because it calls the live embedding service. The fingerprint is
    re-derived exactly as ``EmbeddingTrack`` does so :func:`probe_corpus` can reject a query embedded in
    a space that differs from the corpus's. Raises (never returns a partial result) on any service
    error — an unreachable embedder is an error, not a reason to guess."""
    from palimpsest.tracks.embedding import EmbeddingConfig, embed_texts

    if not text or not text.strip():
        raise ValueError("probe query text is empty")
    config = EmbeddingConfig(provider=provider, endpoint=endpoint, model=model, batch_size=1)
    matrix = embed_texts([text], config)
    vector = [float(x) for x in matrix[0].tolist()]
    return vector, _fingerprint(provider, endpoint, model, len(vector))
