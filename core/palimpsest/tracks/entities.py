"""Entity track extractor: spaCy NER → W3C EntityAnnotation JSONL."""

from __future__ import annotations

from typing import Any

import spacy

from palimpsest.annotation.bodies import entity_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector

_ENTITY_TYPE_MAP = {
    "PERSON": "PER",
    "GPE": "LOC",
    "LOC": "LOC",
    "ORG": "ORG",
    "WORK_OF_ART": "WORK",
    "FAC": "LOC",
}

_LFO_MAP = {
    "PER": "entity.character",
    "LOC": "entity.place",
    "ORG": "entity.organization",
    "WORK": "entity.work",
}

DEFAULT_SPACY_MODEL = "en_core_web_lg"
DEFAULT_CONFIDENCE = 0.85

_NLP_CACHE: dict[str, Any] = {}


def _get_nlp(model: str = DEFAULT_SPACY_MODEL) -> Any:
    if model not in _NLP_CACHE:
        try:
            _NLP_CACHE[model] = spacy.load(model)
        except OSError:
            _NLP_CACHE[model] = spacy.load("en_core_web_sm")
    return _NLP_CACHE[model]


class EntityExtractor:
    """Extract named entities using spaCy NER."""

    @property
    def name(self) -> str:
        return "entities"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return ["_spacy_parse"]

    @property
    def lfo_types(self) -> list[str]:
        return ["entity.character", "entity.place", "entity.organization", "entity.work"]

    @property
    def evidence_level(self) -> str:
        return "E4"

    def extract(self, project: Any) -> list[Annotation]:
        text = project.reference_text()
        nlp = _get_nlp(DEFAULT_SPACY_MODEL)
        nlp.max_length = len(text) + 1000
        doc = nlp(text)

        source_urn = f"urn:palimpsest:{project.metadata.id}"
        annotations: list[Annotation] = []

        for ent in doc.ents:
            mapped = _ENTITY_TYPE_MAP.get(ent.label_)
            if not mapped:
                continue
            lfo = _LFO_MAP.get(mapped, "entity.character")
            ann = Annotation(
                body=entity_body(
                    entity_type=mapped,
                    name=ent.text,
                    lfo_type=lfo,
                ),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=ent.start_char, end=ent.end_char),
                ),
                creator=Creator(name=f"spacy/{DEFAULT_SPACY_MODEL}"),
                confidence=DEFAULT_CONFIDENCE,
                evidence_level="E4",
                project_id=project.metadata.id,
                track_name="entities",
            )
            annotations.append(ann)

        return annotations

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": self.name,
            "bodyType": "palimpsest:EntityAnnotation",
            "colorScheme": {
                "primary": "#3498db",
                "secondary": "#85c1e9",
                "scale": {
                    "PER": "#3498db",
                    "LOC": "#2ecc71",
                    "ORG": "#e74c3c",
                    "WORK": "#9b59b6",
                },
            },
            "textViewRendering": "highlight",
            "overviewBarRendering": {"type": "density-barcode", "color": "#3498db"},
        }

    def parameters(self) -> dict[str, Any]:
        return {"entities.spacy_model": DEFAULT_SPACY_MODEL}
