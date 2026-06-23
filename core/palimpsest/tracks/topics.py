"""Topics track extractor: sklearn LDA → W3C TopicAnnotation JSONL + distribution signal."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

from palimpsest.annotation.bodies import topic_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector
from palimpsest.formats.signals import SignalManifest, write_signal
from palimpsest.tracks.params import InsufficientCorpusError, Param, ParameterizedTrack

N_TOPICS = 10
RANDOM_STATE = 42
MAX_ITER = 20
MIN_DF = 2
MAX_FEATURES = 10_000


class TopicsExtractor(ParameterizedTrack):
    """Per-paragraph topic modeling via LDA / NMF."""

    PARAMS = (
        Param("n_topics", int, default=N_TOPICS, min=2, max=50, help="number of topics to model"),
        Param("method", str, default="lda", choices=("lda", "nmf"), help="topic model: LDA or NMF"),
        # Declared (not hidden) algorithm constants: reported in resolved_params and written to disk,
        # locked until exposed as user knobs (G2 acceptable-default rule).
        Param("random_state", int, default=RANDOM_STATE, locked=True, help="RNG seed (reproducibility)"),
        Param("max_iter", int, default=MAX_ITER, locked=True, help="solver iteration cap"),
        Param("min_df", int, default=MIN_DF, locked=True, help="CountVectorizer min document frequency"),
        Param("max_features", int, default=MAX_FEATURES, locked=True, help="CountVectorizer vocab cap"),
    )

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
            raise InsufficientCorpusError(
                f"topic modeling needs at least 2 paragraphs, got {len(paragraphs)}"
            )

        cfg = self.resolved_params()
        method = cfg["method"]
        random_state = cfg["random_state"]
        max_iter = cfg["max_iter"]

        para_texts = [text for _, _, text in paragraphs]
        # Clamp the count knobs to corpus feasibility, then record the EFFECTIVE values (record-effective
        # policy, §2.3): disk reports what actually ran, plus a `{name}_requested` note when it differs,
        # so the clamp is transparent rather than a silent shrink of the echoed value (finding A2).
        n_topics = min(cfg["n_topics"], len(paragraphs))
        min_df = min(cfg["min_df"], len(paragraphs))

        vectorizer = CountVectorizer(
            token_pattern=r"[a-zA-Z]{3,}",
            stop_words="english",
            min_df=min_df,
            max_features=cfg["max_features"],
        )
        try:
            dtm = vectorizer.fit_transform(para_texts)
        except ValueError as exc:
            # An empty vocabulary (every token a stop-word or below min_df) is a degenerate corpus, not
            # "0 topics computed" — surface it as an honest failure with the real reason (B5/P5).
            raise InsufficientCorpusError(
                f"corpus has no usable vocabulary for topic modeling "
                f"(min_df={min_df}, alphabetic tokens of length ≥3): {exc}"
            ) from exc

        if dtm.shape[0] < n_topics:
            n_topics = max(2, dtm.shape[0])

        self.record_effective("n_topics", n_topics)
        self.record_effective("min_df", min_df)

        if method == "nmf":
            from sklearn.decomposition import NMF
            model = NMF(n_components=n_topics, random_state=random_state, max_iter=max_iter)
        else:
            model = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=random_state,
                max_iter=max_iter,
                learning_method="batch",
            )
        doc_topic_dist = model.fit_transform(dtm)

        feature_names = vectorizer.get_feature_names_out()
        topic_terms: list[list[str]] = []
        for topic_idx in range(n_topics):
            top_indices = model.components_[topic_idx].argsort()[-5:][::-1]
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
                creator=Creator(name=f"sklearn-{method}/{n_topics}topics"),
                confidence=weight,
                evidence_level="E4",
                project_id=project.metadata.id,
                track_name="topics",
            )
            annotations.append(ann)

        self._write_distribution_signal(
            project, doc_topic_dist, paragraphs,
            n_topics=n_topics, method=method, random_state=random_state, min_df=min_df,
            requested={"n_topics": cfg["n_topics"], "min_df": cfg["min_df"]},
        )
        return annotations

    def _write_distribution_signal(
        self,
        project: Any,
        dist: np.ndarray,
        paragraphs: list[tuple[int, int, str]],
        *,
        n_topics: int,
        method: str,
        random_state: int,
        min_df: int,
        requested: dict[str, int],
    ) -> None:
        """Write topics distribution as a binary signal, recording the EFFECTIVE parameters that
        produced it (the resolved/clamped values, not module constants) so disk never lies. When a
        value was clamped to corpus feasibility, the manifest also records the requested value under
        ``{name}_requested`` and lists the clamped names, so the clamp is visible to the consumer."""
        signals_dir = project.path / "signals"
        segment_offsets = [[start, end] for start, end, _ in paragraphs]

        effective = {"n_topics": n_topics, "min_df": min_df}
        metadata: dict[str, Any] = {
            "algorithm": method,
            "n_topics": n_topics,
            "random_state": random_state,
            "min_df": min_df,
            "segment_offsets": segment_offsets,
        }
        clamped = [name for name, eff in effective.items() if requested.get(name) != eff]
        for name in clamped:
            metadata[f"{name}_requested"] = requested[name]
        if clamped:
            metadata["clamped"] = clamped

        manifest = SignalManifest(
            type="distribution",
            name="topics_dist",
            source=f"sklearn-{method}/{n_topics}topics",
            reference_sha256=project.metadata.reference_sha256,
            dimensions=[dist.shape[0], dist.shape[1]],
            metadata=metadata,
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
