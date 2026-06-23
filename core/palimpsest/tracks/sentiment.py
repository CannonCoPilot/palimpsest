"""Sentiment track extractor: VADER → W3C SentimentAnnotation JSONL."""

from __future__ import annotations

from typing import Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from palimpsest.annotation.bodies import sentiment_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector
from palimpsest.ingest.segmenter import Segment
from palimpsest.tracks.params import Param, ParameterizedTrack

_ANALYZER: SentimentIntensityAnalyzer | None = None


def _get_analyzer() -> SentimentIntensityAnalyzer:
    global _ANALYZER
    if _ANALYZER is None:
        _ANALYZER = SentimentIntensityAnalyzer()
    return _ANALYZER


def _sentences_from_spacy(text: str) -> list[Segment]:
    """Get sentence segments using spaCy."""
    from palimpsest.ingest.segmenter import segment_sentences

    return segment_sentences(text)


class SentimentExtractor(ParameterizedTrack):
    """Per-sentence sentiment via VADER."""

    # NOTE: `method`/`granularity` are accepted and validated but not yet consumed by extract()
    # (it always runs VADER over sentence spans). Wiring them — or restricting the choices to what
    # is implemented — is a D2 refactor; for now the contract preserves the prior accepted values.
    PARAMS = (
        Param("method", str, default="vader", choices=("vader", "hedonometer"),
              help="sentiment lexicon/model"),
        Param("granularity", str, default="sentence", choices=("sentence", "paragraph"),
              help="unit over which sentiment is scored"),
    )

    @property
    def name(self) -> str:
        return "sentiment"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return ["_spacy_parse"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.sentiment"]

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project: Any) -> list[Annotation]:
        text = project.reference_text()
        sentences = _sentences_from_spacy(text)
        analyzer = _get_analyzer()
        source_urn = f"urn:palimpsest:{project.metadata.id}"
        annotations: list[Annotation] = []

        for sent in sentences:
            scores = analyzer.polarity_scores(sent.text)
            valence = scores["compound"]
            arousal = (scores["pos"] + scores["neg"]) / 2.0
            confidence = 0.5 + abs(valence) * 0.4

            ann = Annotation(
                body=sentiment_body(valence=valence, arousal=arousal, model="vader"),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=sent.start, end=sent.end),
                ),
                creator=Creator(name="vaderSentiment/3.3"),
                confidence=confidence,
                evidence_level="E5",
                project_id=project.metadata.id,
                track_name="sentiment",
            )
            annotations.append(ann)

        return annotations

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": self.name,
            "bodyType": "palimpsest:SentimentAnnotation",
            "colorScheme": {"primary": "#2ecc71", "secondary": "#e74c3c"},
            "textViewRendering": "highlight",
            "overviewBarRendering": {"type": "density-barcode", "color": "#2ecc71"},
        }
