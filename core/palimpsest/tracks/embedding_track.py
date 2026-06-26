"""EmbeddingTrack — embedding promoted from a ``self_similarity`` local into a first-class layer-track.

Reads a persisted chunk layer (``signals/chunking_{chunk_label}.json``), embeds its chunk texts with a
user-chosen provider/model, and persists the result as a reusable embedding layer: vectors go to
``cache/embeddings_{label}.db`` (SQLite-vec) and a manifest to ``signals/embedding_{label}.json``. Like
the chunk layer it is *plural* and content-addressed — distinct chunk texts or a distinct model yield a
distinct ``label`` and file (FR-5).

This track is a *signal consumer* (it ``depends_on`` the chunk layer), so ``runner.extract_masked``
runs it on the full project and does not remap it: the chunk layer it reads already carries
original-coordinate ``segment_offsets`` (remapped when the chunk layer was produced), which this track
copies through unchanged so the embedding lane renders against the original document.

The embedding label deliberately matches ``self_similarity``'s content-addressing scheme
(``sha256(provider+endpoint+model+chunk_texts)``) so the same chunk texts + model reuse one vector
cache rather than re-embedding.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from palimpsest.atomic import atomic_write_text
from palimpsest.formats.signals import SignalManifest
from palimpsest.project import Project
from palimpsest.tracks.embedding import EMBEDDING_PROVIDERS, EmbeddingConfig, embed_texts
from palimpsest.tracks.params import Param, ParameterizedTrack
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

# Above this chunk count, the O(n^2) mean-pairwise-distance summary is skipped rather than computed —
# it is a cheap geometry hint, not a load-bearing statistic. Heavier distributions are computed
# on-read in P6.
_PAIRWISE_CAP = 800


def _mean_pairwise_cosine_distance(vectors: np.ndarray) -> float | None:
    """Mean cosine distance over all chunk pairs, or ``None`` when there are too many chunks (the
    summary is a cheap hint, not exact analysis — P6 computes full distributions on demand)."""
    n = vectors.shape[0]
    if n < 2 or n > _PAIRWISE_CAP:
        return None
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    safe = np.where(norms == 0, 1.0, norms)
    unit = vectors / safe
    sims = unit @ unit.T
    iu = np.triu_indices(n, k=1)
    return round(float(np.mean(1.0 - sims[iu])), 6)


class EmbeddingTrack(ParameterizedTrack):
    # Label-keyed layer track (see ChunkingTrack.layer_keyed): writes signals/embedding_{label}.json,
    # gets per-label provenance, and is enumerated as plural layers in /analysis/status.
    layer_keyed = True

    # Param names mirror the self_similarity embed vocabulary (embed_provider/embed_endpoint/embed_model/
    # embed_batch_size) the shared HTTP run handler already forwards; chunk_label selects which persisted
    # chunk layer to embed and is forwarded to the handler for this track (FR-4).
    PARAMS = (
        Param("chunk_label", str, required=True,
              help="label of the chunk layer to embed (the {label} in chunking_{label}.json)"),
        Param("embed_provider", str, required=True, choices=EMBEDDING_PROVIDERS,
              help="embedding provider (mlx or ollama)"),
        Param("embed_endpoint", str, required=True, help="embedding service base URL"),
        Param("embed_model", str, required=True, help="embedding model name or server alias"),
        Param("embed_batch_size", int, default=32, min=1, help="texts per embedding request"),
    )

    @property
    def name(self) -> str:
        return "embedding"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        # Depends on the chunk layer: this makes it a signal-consumer (runs on the full project,
        # inheriting masking through the already-remapped chunk layer it reads) and orders it after
        # chunking. The specific chunk *layer* is bound by the chunk_label param (and, in P2's
        # resolver, by capability) — depends_on names the producing track, not the label.
        return ["chunking"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.embedding"]

    @property
    def evidence_level(self) -> str:
        return "E2"

    def _config(self) -> EmbeddingConfig:
        p = self.resolved_params()
        return EmbeddingConfig(
            provider=p["embed_provider"], endpoint=p["embed_endpoint"],
            model=p["embed_model"], batch_size=p["embed_batch_size"],
        )

    def _label(self, config: EmbeddingConfig, chunk_texts: list[str]) -> str:
        """Content-addressed embedding-layer id: changes whenever the embedded texts or the embedding
        identity (provider/endpoint/model) change. batch_size is excluded — it changes how vectors are
        requested, not their values."""
        h = hashlib.sha256()
        h.update(f"{config.provider}\x00{config.endpoint}\x00{config.model}\x00".encode())
        for t in chunk_texts:
            h.update(t.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()[:16]

    def _embed(
        self, project: Project, texts: list[str], label: str, config: EmbeddingConfig
    ) -> np.ndarray:
        """Embed ``texts``, caching vectors in ``cache/embeddings_{label}.db``. Reuses a present,
        count-matching cache; otherwise rebuilds. Raises on any embedding failure — never returns a
        partial or ``None`` result (mirrors self_similarity._embed_chunks)."""
        cache_dir = project.path / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        chunk_db = cache_dir / f"embeddings_{label}.db"

        if chunk_db.exists():
            store = SqliteVecStore.open_existing(chunk_db)
            try:
                cached = store.get_all_vectors()
                if len(cached) == len(texts):
                    return np.array(cached, dtype=np.float32)
            finally:
                store.close()
            chunk_db.unlink()  # present but stale (count changed) — rebuild

        vectors = embed_texts(texts, config)  # raises on any provider/HTTP/shape error
        store = SqliteVecStore(chunk_db, dim=int(vectors.shape[1]))
        slug = project.metadata.id
        try:
            ids = [f"{slug}:{label}:{k}" for k in range(len(texts))]
            meta = [{"chunk_index": k} for k in range(len(texts))]
            store.add(ids, vectors.tolist(), meta)
        finally:
            store.close()
        return vectors

    def extract(self, project: Project) -> Path:
        p = self.resolved_params()
        chunk_label = p["chunk_label"]
        chunk_path = project.path / "signals" / f"chunking_{chunk_label}.json"
        if not chunk_path.exists():
            raise ValueError(
                f"embedding: chunk layer 'chunking_{chunk_label}' not found at {chunk_path} — run the "
                "chunking track first, or pass the label of an existing chunk layer"
            )
        chunk_manifest = json.loads(chunk_path.read_text())
        chunk_texts: list[str] = chunk_manifest["metadata"]["chunk_texts"]
        if not chunk_texts:
            raise ValueError(f"embedding: chunk layer 'chunking_{chunk_label}' has no chunks to embed")
        segment_offsets = chunk_manifest.get("segment_offsets", [])
        chunk_digest = chunk_manifest["metadata"]["capability"].get("analyzable_digest")

        config = self._config()
        label = self._label(config, chunk_texts)
        vectors = self._embed(project, chunk_texts, label, config)
        dim = int(vectors.shape[1])

        model_fingerprint = hashlib.sha256(
            f"{config.provider}:{config.endpoint}:{config.model}:{dim}".encode()
        ).hexdigest()[:16]

        capability = {
            "kind": "embedding",
            "chunk_layer_id": chunk_label,
            "chunk_analyzable_digest": chunk_digest,
            "provider": config.provider,
            "model": config.model,
            "dim": dim,
            "model_fingerprint": model_fingerprint,
        }
        rendering = {
            "track_view": "embedding-lane",
            "encoding": "nn-density",
            "projection_ref": None,  # 2-D scatter projection is produced in P3
        }
        stats = {
            "count": len(chunk_texts),
            "dim": dim,
            "model_fingerprint": model_fingerprint,
            "mean_pairwise_distance": _mean_pairwise_cosine_distance(vectors),
        }

        metadata: dict[str, Any] = {
            "label": label,
            "capability": capability,
            "rendering": rendering,
            "stats": stats,
            "vectorstore": f"cache/embeddings_{label}.db",
            "params": self.parameters(),
        }

        manifest = SignalManifest(
            type="embedding-layer",
            name=f"embedding_{label}",
            source="embedding/0.1",
            reference_sha256=project.metadata.reference_sha256,
            dimensions=[len(chunk_texts), dim],
            # Copied through from the chunk layer (already original coordinates); this track is a
            # signal-consumer and is not remapped, so it must not introduce analyzable coordinates.
            segment_offsets=segment_offsets,
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
            "trackName": "embedding",
            "bodyType": "signal",
            "dedicatedView": "embedding-lane",
            "colorScheme": {"primary": "#0EA5E9", "secondary": "#0284C7"},
        }
