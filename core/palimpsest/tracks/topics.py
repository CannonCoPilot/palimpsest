"""Topics track extractor: sklearn LDA → W3C TopicAnnotation JSONL + distribution signal."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

from palimpsest.annotation.bodies import topic_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector
from palimpsest.formats.signals import SignalManifest, write_signal

N_TOPICS = 10
RANDOM_STATE = 42
MAX_ITER = 20
MIN_DF = 2
MAX_FEATURES = 10_000


class TopicsExtractor:
    """Per-paragraph topic modeling via LDA."""

    @property
    def name(self) -> str:
        return "topics"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return []

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.topic_assignment"]

    @property
    def evidence_level(self) -> str:
        return "E4"

    def extract(self, project: Any) -> list[Annotation]:
        source_urn = f"urn:palimpsest:{project.metadata.id}"
        paragraphs = project.paragraphs()

        if len(paragraphs) < 2:
            return []

        para_texts = [text for _, _, text in paragraphs]
        n_topics = min(N_TOPICS, len(paragraphs))

        vectorizer = CountVectorizer(
            token_pattern=r"[a-zA-Z]{3,}",
            stop_words="english",
            min_df=min(MIN_DF, len(paragraphs)),
            max_features=MAX_FEATURES,
        )
        try:
            dtm = vectorizer.fit_transform(para_texts)
        except ValueError:
            return []

        if dtm.shape[0] < n_topics:
            n_topics = max(2, dtm.shape[0])

        lda = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=RANDOM_STATE,
            max_iter=MAX_ITER,
            learning_method="batch",
        )
        doc_topic_dist = lda.fit_transform(dtm)

        feature_names = vectorizer.get_feature_names_out()
        topic_terms: list[list[str]] = []
        for topic_idx in range(n_topics):
            top_indices = lda.components_[topic_idx].argsort()[-5:][::-1]
            topic_terms.append([feature_names[i] for i in top_indices])

        annotations: list[Annotation] = []
        for i, (start, end, _text) in enumerate(paragraphs):
            dist = doc_topic_dist[i]
            dominant_topic = int(np.argmax(dist))
            weight = float(dist[dominant_topic])

            ann = Annotation(
                body=topic_body(
                    topic_id=dominant_topic,
                    topic_weight=weight,
                    topic_terms=topic_terms[dominant_topic],
                ),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=start, end=end),
                ),
                creator=Creator(name=f"sklearn-lda/{N_TOPICS}topics"),
                confidence=weight,
                evidence_level="E4",
                project_id=project.metadata.id,
                track_name="topics",
            )
            annotations.append(ann)

        self._write_distribution_signal(project, doc_topic_dist, paragraphs)
        return annotations

    def _write_distribution_signal(
        self,
        project: Any,
        dist: np.ndarray,
        paragraphs: list[tuple[int, int, str]],
    ) -> None:
        """Write topics distribution as binary signal."""
        signals_dir = project.path / "signals"
        segment_offsets = [[start, end] for start, end, _ in paragraphs]

        manifest = SignalManifest(
            type="distribution",
            name="topics_dist",
            source=f"sklearn-lda/{N_TOPICS}topics",
            reference_sha256=project.metadata.reference_sha256,
            dimensions=[dist.shape[0], dist.shape[1]],
            metadata={
                "algorithm": "lda",
                "n_topics": N_TOPICS,
                "random_state": RANDOM_STATE,
                "min_df": MIN_DF,
                "segment_offsets": segment_offsets,
            },
        )
        write_signal(signals_dir, dist.astype(np.float32), manifest)

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": self.name,
            "bodyType": "palimpsest:TopicAnnotation",
            "colorScheme": {"primary": "#e74c3c", "secondary": "#f1948a"},
            "textViewRendering": "margin-marker",
            "overviewBarRendering": {"type": "density-barcode", "color": "#e74c3c"},
            "dedicatedView": "topics-stacked-bar",
        }

    def parameters(self) -> dict[str, Any]:
        return {
            "topics.n_topics": N_TOPICS,
            "topics.random_state": RANDOM_STATE,
            "topics.max_iter": MAX_ITER,
            "topics.min_df": MIN_DF,
        }
