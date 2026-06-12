"""Self-similarity matrix track — pairwise cosine similarity over paragraph embeddings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from palimpsest.formats.signals import SignalManifest, write_signal
from palimpsest.project import Project
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

logger = logging.getLogger(__name__)


class SelfSimilarityTrack:
    def __init__(self) -> None:
        self._metric = "cosine"

    def set_params(self, params: dict[str, Any]) -> None:
        if "metric" in params and params["metric"] in ("cosine", "jaccard", "word_overlap", "edit_distance"):
            self._metric = params["metric"]

    @property
    def name(self) -> str:
        return "self_similarity"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        return ["_embeddings"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.self_similarity"]

    @property
    def evidence_level(self) -> str:
        return "E4"

    def extract(self, project: Project) -> Path:
        embeddings_db = project.path / "cache" / "embeddings.db"
        if not embeddings_db.exists():
            raise FileNotFoundError(
                f"Embeddings not found at {embeddings_db}. "
                "Run `palimpsest analyze` with Ollama available first."
            )

        store = SqliteVecStore.open_existing(embeddings_db)
        all_vectors = store.get_all_vectors()
        store.close()

        if not all_vectors:
            raise ValueError("No embeddings found in database")

        n = len(all_vectors)
        dim = len(all_vectors[0])
        embeddings = np.array(all_vectors, dtype=np.float32)

        # L2-normalize rows
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms > 1e-8, norms, 1.0)
        normed = embeddings / norms

        # Cosine similarity matrix
        matrix = normed @ normed.T
        np.clip(matrix, -1.0, 1.0, out=matrix)
        np.fill_diagonal(matrix, 1.0)

        paras = project.paragraphs()
        sha = project.metadata.reference_sha256

        manifest = SignalManifest(
            type="matrix",
            name="self_similarity",
            source="embedding_cosine/0.1",
            reference_sha256=sha,
            dimensions=[n, n],
            data_file="self_similarity.bin",
            segment_offsets=[[s, e] for s, e, _ in paras],
            metadata={
                "similarity_metric": self._metric,
                "paragraph_count": n,
                "embedding_dim": dim,
            },
        )

        signals_dir = project.path / "signals"
        write_signal(signals_dir, matrix, manifest)
        return signals_dir / "self_similarity.json"

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "self_similarity",
            "bodyType": "signal",
            "colorScheme": {
                "primary": "#3B82F6",
                "secondary": "#1E40AF",
                "scale": ["#EFF6FF", "#3B82F6", "#1E3A8A"],
            },
            "dedicatedView": "dotplot",
        }

    def parameters(self) -> dict[str, Any]:
        return {
            "self_similarity.metric": "cosine",
            "self_similarity.source": "paragraph_embeddings",
        }
