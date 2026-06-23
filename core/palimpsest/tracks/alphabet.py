"""Alphabet track — K-means narrative state encoding, complementary to LitHMM."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from palimpsest.atomic import atomic_write_text
from palimpsest.formats.signals import SignalManifest
from palimpsest.project import Project
from palimpsest.tracks.params import Param, ParameterizedTrack

logger = logging.getLogger(__name__)

N_CLUSTERS = 16
RANDOM_STATE = 42
N_INIT = 10
LETTERS = "ABCDEFGHIJKLMNOP"


class AlphabetTrack(ParameterizedTrack):
    # n_clusters is an analytical knob whose max is the LETTERS alphabet size (16) — a hard
    # label-index bound, not a tuning preference. random_state/n_init are declared-but-locked
    # algorithm constants (reported in provenance, not yet user-settable) per the G2 default rule.
    PARAMS = (
        Param("n_clusters", int, default=N_CLUSTERS, min=2, max=N_CLUSTERS,
              help="K-means narrative-state count (2..16; capped at the 16-letter alphabet)"),
        Param("random_state", int, default=RANDOM_STATE, locked=True,
              help="RNG seed (reproducibility)"),
        Param("n_init", int, default=N_INIT, locked=True, help="K-means restarts"),
    )

    @property
    def name(self) -> str:
        return "alphabet"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        return ["sentiment", "lexical", "dialogue", "topics"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.narrative_alphabet"]

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project: Project) -> Path:
        """Build feature matrix from track outputs, cluster into alphabet."""
        from palimpsest.annotation.serializer import read_track

        paras = project.paragraphs()
        n_paras = len(paras)

        features = np.zeros((n_paras, 4), dtype=np.float32)

        sent_path = project.path / "tracks" / "sentiment.jsonl"
        if sent_path.exists():
            sent_anns = read_track(sent_path)
            sent_accum: dict[int, list[float]] = {}
            for ann in sent_anns:
                i = project.find_paragraph(ann.target.selector.start)
                if 0 <= i < n_paras:
                    val = ann.body.extra.get("palimpsest:valence", 0)
                    sent_accum.setdefault(i, []).append(float(val) if val else 0.0)
            for i, vals in sent_accum.items():
                features[i, 0] = sum(vals) / len(vals)

        lex_path = project.path / "tracks" / "lexical.jsonl"
        if lex_path.exists():
            lex_anns = read_track(lex_path)
            for ann in lex_anns:
                i = project.find_paragraph(ann.target.selector.start)
                if 0 <= i < n_paras:
                    ttr = ann.body.extra.get("palimpsest:ttr", 0)
                    features[i, 1] = float(ttr) if ttr else 0.0

        dial_path = project.path / "tracks" / "dialogue.jsonl"
        if dial_path.exists():
            dial_anns = read_track(dial_path)
            for ann in dial_anns:
                i = project.find_paragraph(ann.target.selector.start)
                if 0 <= i < n_paras:
                    features[i, 2] = 1.0

        topics_path = project.path / "tracks" / "topics.jsonl"
        if topics_path.exists():
            topics_anns = read_track(topics_path)
            for ann in topics_anns:
                i = project.find_paragraph(ann.target.selector.start)
                if 0 <= i < n_paras:
                    weight = ann.body.extra.get("palimpsest:topicWeight", 0)
                    features[i, 3] = float(weight) if weight else 0.0

        # Standardize and cluster
        scaler = StandardScaler()
        if n_paras > 1:
            features_scaled = scaler.fit_transform(features)
        else:
            features_scaled = features

        cfg = self.resolved_params()
        random_state = cfg["random_state"]
        n_init = cfg["n_init"]
        # Clamp the requested cluster count to feasibility (a corpus of N paragraphs yields at most N
        # clusters; a 1-paragraph corpus collapses to a single state), then record the EFFECTIVE value
        # (record-effective policy, §2.3). parameters()/provenance/the manifest now report what actually
        # ran plus `n_clusters_requested` when it differs — the old parameters() returned the constant
        # 16 and lied whenever this clamp fired (findings A2/A1).
        n_clusters = min(cfg["n_clusters"], n_paras)
        if n_clusters < 2:
            sequence = LETTERS[0] * n_paras
            effective_clusters = 1
        else:
            kmeans = KMeans(
                n_clusters=n_clusters,
                random_state=random_state,
                n_init=n_init,
            )
            labels = kmeans.fit_predict(features_scaled)
            sequence = "".join(LETTERS[label] for label in labels)
            effective_clusters = n_clusters
        self.record_effective("n_clusters", effective_clusters)

        sha = project.metadata.reference_sha256
        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)

        metadata: dict[str, Any] = {
            "n_clusters": effective_clusters,
            "random_state": random_state,
            "n_init": n_init,
            "features": [
                "sentiment_valence", "lexical_ttr",
                "dialogue_presence", "topic_weight",
            ],
            "sequence": sequence,
            "note": "K-means structural encoding, complementary to LitHMM passage states",
        }
        if cfg["n_clusters"] != effective_clusters:
            metadata["n_clusters_requested"] = cfg["n_clusters"]
            metadata["clamped"] = ["n_clusters"]

        manifest = SignalManifest(
            type="sequence",
            name="alphabet",
            source="kmeans_narrative_state/0.1",
            reference_sha256=sha,
            dimensions=[n_paras],
            metadata=metadata,
        )

        manifest_path = signals_dir / "alphabet.json"
        atomic_write_text(
            manifest_path,
            json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        )

        return manifest_path

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "alphabet",
            "bodyType": "signal",
            "colorScheme": {
                "primary": "#EC4899",
                "secondary": "#DB2777",
                "scale": [f"hsl({i * 360 // N_CLUSTERS}, 70%, 60%)" for i in range(N_CLUSTERS)],
            },
            "dedicatedView": "barcode",
        }
