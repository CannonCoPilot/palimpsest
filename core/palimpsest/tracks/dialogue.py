"""Dialogue track extractor: regex quote detection → W3C DialogueAnnotation JSONL."""

from __future__ import annotations

import re
from typing import Any

from palimpsest.annotation.bodies import dialogue_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector

_QUOTE_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    (re.compile("\u201c(.{1,500}?)\u201d"), 0.92),
    (re.compile(r'"(.{1,500}?)"'), 0.85),
    (re.compile(r"'(.{1,500}?)'"), 0.60),
    (re.compile("\u2014([^.\\n]{5,200}?)(?=[,.:\u201c\u201d\"\\n]|$)"), 0.70),
]

_ATTRIBUTION_RE = re.compile(
    r"(said|asked|replied|cried|exclaimed|answered|whispered|murmured|called|shouted)"
    r"\s+(\w+(?:\s+\w+){0,3}?)(?=[,.\s;])",
)

MAX_ATTRIBUTION_WINDOW = 100


class DialogueExtractor:
    """Detect quoted speech via regex with speaker attribution."""

    @property
    def name(self) -> str:
        return "dialogue"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return []

    @property
    def lfo_types(self) -> list[str]:
        return ["structural.dialogue.quote"]

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project: Any) -> list[Annotation]:
        text = project.reference_text()
        source_urn = f"urn:palimpsest:{project.metadata.id}"
        seen: set[tuple[int, int]] = set()
        annotations: list[Annotation] = []

        for pattern, pattern_confidence in _QUOTE_PATTERNS:
            for m in pattern.finditer(text):
                if m.lastindex:
                    span_start = m.start(1)
                    span_end = m.end(1)
                    quote_text = m.group(1)
                else:
                    span_start = m.start()
                    span_end = m.end()
                    quote_text = m.group(0)
                key = (span_start, span_end)
                if key in seen:
                    continue
                seen.add(key)
                speaker, verb = self._find_attribution(text, span_start, span_end)

                ann = Annotation(
                    body=dialogue_body(
                        text=quote_text,
                        quote_type="direct",
                        speaker=speaker,
                        verb=verb,
                    ),
                    target=Target(
                        source=source_urn,
                        selector=TextPositionSelector(start=span_start, end=span_end),
                    ),
                    creator=Creator(name="palimpsest-dialogue/0.1"),
                    confidence=pattern_confidence,
                    evidence_level="E5",
                    project_id=project.metadata.id,
                    track_name="dialogue",
                )
                annotations.append(ann)

        return annotations

    def _find_attribution(self, text: str, quote_start: int, quote_end: int) -> tuple[str, str]:
        """Look for attribution verb + speaker name before or after quote."""
        after = text[quote_end : quote_end + MAX_ATTRIBUTION_WINDOW]
        m = _ATTRIBUTION_RE.search(after)
        if m:
            return m.group(2), m.group(1).lower()
        before_start = max(0, quote_start - MAX_ATTRIBUTION_WINDOW)
        before = text[before_start:quote_start]
        m = _ATTRIBUTION_RE.search(before)
        if m:
            return m.group(2), m.group(1).lower()
        return "", ""

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": self.name,
            "bodyType": "palimpsest:DialogueAnnotation",
            "colorScheme": {"primary": "#e67e22", "secondary": "#f5cba7"},
            "textViewRendering": "underline",
            "overviewBarRendering": {"type": "density-barcode", "color": "#e67e22"},
        }

    def parameters(self) -> dict[str, Any]:
        return {"dialogue.max_attribution_window": MAX_ATTRIBUTION_WINDOW}
