"""Alphabet track — K-means narrative state encoding, complementary to LitHMM."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from palimpsest.formats.signals import SignalManifest
from palimpsest.project import Project

logger = logging.getLogger(__name__)

N_CLUSTERS = 16
RANDOM_STATE = 42
LETTERS = "ABCDEFGHIJKLMNOP"


class AlphabetTrack:
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

        n_clusters = min(N_CLUSTERS, n_paras)
        if n_clusters < 2:
            sequence = LETTERS[0] * n_paras
        else:
            kmeans = KMeans(
                n_clusters=n_clusters,
                random_state=RANDOM_STATE,
                n_init=10,
            )
            labels = kmeans.fit_predict(features_scaled)
            sequence = "".join(LETTERS[label] for label in labels)

        sha = project.metadata.reference_sha256
        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)

        manifest = SignalManifest(
            type="sequence",
            name="alphabet",
            source="kmeans_narrative_state/0.1",
            reference_sha256=sha,
            dimensions=[n_paras],
            metadata={
                "n_clusters": n_clusters if n_paras >= 2 else 1,
                "random_state": RANDOM_STATE,
                "features": [
                    "sentiment_valence", "lexical_ttr",
                    "dialogue_presence", "topic_weight",
                ],
                "sequence": sequence,
                "note": "K-means structural encoding, complementary to LitHMM passage states",
            },
        )

        manifest_path = signals_dir / "alphabet.json"
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
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

    def parameters(self) -> dict[str, Any]:
        return {
            "alphabet.n_clusters": N_CLUSTERS,
            "alphabet.random_state": RANDOM_STATE,
        }
