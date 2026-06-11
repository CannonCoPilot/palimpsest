"""Lexical track extractor: TTR, hapax, Yule's K → W3C LexicalAnnotation JSONL."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from palimpsest.annotation.bodies import lexical_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector

_TOKEN_RE = re.compile(r"[A-Za-z']+")
MIN_TOKENS = 5


def _yules_k(tokens: list[str]) -> float:
    """Compute Yule's K characteristic (length-independent vocabulary richness)."""
    n = len(tokens)
    if n == 0:
        return 0.0
    freq = Counter(tokens)
    freq_spectrum = Counter(freq.values())
    m2_sum = sum(m * m * vm for m, vm in freq_spectrum.items())
    return 10_000 * (m2_sum - n) / (n * n)


class LexicalExtractor:
    """Per-paragraph vocabulary statistics."""

    @property
    def name(self) -> str:
        return "lexical"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return []

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.lexical_density"]

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project: Any) -> list[Annotation]:
        source_urn = f"urn:palimpsest:{project.metadata.id}"
        paragraphs = project.paragraphs()
        annotations: list[Annotation] = []

        for start, end, text in paragraphs:
            tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
            if len(tokens) < MIN_TOKENS:
                continue

            types = set(tokens)
            ttr = len(types) / len(tokens)
            hapax = sum(1 for t in Counter(tokens).values() if t == 1)
            mean_len = sum(len(t) for t in tokens) / len(tokens)
            yules_k_val = _yules_k(tokens)

            ann = Annotation(
                body=lexical_body(
                    ttr=ttr,
                    hapax_count=hapax,
                    mean_word_length=mean_len,
                    yules_k=yules_k_val,
                ),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=start, end=end),
                ),
                creator=Creator(name="palimpsest-lexical/0.1"),
                confidence=0.99,
                evidence_level="E5",
                project_id=project.metadata.id,
                track_name="lexical",
            )
            annotations.append(ann)

        return annotations

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": self.name,
            "bodyType": "palimpsest:LexicalAnnotation",
            "colorScheme": {"primary": "#9b59b6", "secondary": "#d2b4de"},
            "textViewRendering": "margin-marker",
            "overviewBarRendering": {"type": "density-barcode", "color": "#9b59b6"},
        }

    def parameters(self) -> dict[str, Any]:
        return {"lexical.min_tokens": MIN_TOKENS}
