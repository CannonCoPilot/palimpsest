"""Dialogue track extractor: regex quote detection → W3C DialogueAnnotation JSONL."""

from __future__ import annotations

import re
from typing import Any

from palimpsest.annotation.bodies import dialogue_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector
from palimpsest.tracks.params import Param, ParameterizedTrack

# Quote regexes paired with the keys of the locked confidence params that score each pattern. The
# defaults live on the Params below; this table only owns the patterns (structural) so the two cannot
# drift \u2014 extract() zips these with the resolved confidences.
_QUOTE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile("\u201c(.{1,500}?)\u201d"), "confidence_curly"),
    (re.compile(r'"(.{1,500}?)"'), "confidence_straight"),
    (re.compile(r"'(.{1,500}?)'"), "confidence_single"),
    (re.compile("\u2014([^.\\n]{5,200}?)(?=[,.:\u201c\u201d\"\\n]|$)"), "confidence_dash"),
]

_ATTRIBUTION_RE = re.compile(
    r"(said|asked|replied|cried|exclaimed|answered|whispered|murmured|called|shouted)"
    r"\s+(\w+(?:\s+\w+){0,3}?)(?=[,.\s;])",
)

MAX_ATTRIBUTION_WINDOW = 100


class DialogueExtractor(ParameterizedTrack):
    """Detect quoted speech via regex with speaker attribution."""

    PARAMS = (
        Param("max_attribution_window", int, default=MAX_ATTRIBUTION_WINDOW, min=10, max=1000,
              help="characters scanned before/after a quote when searching for the speaker"),
        # Per-pattern detection confidences are locked analytical constants (reported, not yet
        # user-tunable). Each scores one regex in _QUOTE_PATTERNS, weakest quote style lowest.
        Param("confidence_curly", float, default=0.92, locked=True,
              help="confidence for typographic “curly” double quotes"),
        Param("confidence_straight", float, default=0.85, locked=True,
              help="confidence for straight double quotes"),
        Param("confidence_single", float, default=0.60, locked=True,
              help="confidence for single quotes (ambiguous with apostrophes)"),
        Param("confidence_dash", float, default=0.70, locked=True,
              help="confidence for em-dash dialogue"),
    )

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
        cfg = self.resolved_params()
        attribution_window = cfg["max_attribution_window"]
        text = project.reference_text()
        source_urn = f"urn:palimpsest:{project.metadata.id}"
        seen: set[tuple[int, int]] = set()
        annotations: list[Annotation] = []

        for pattern, confidence_key in _QUOTE_PATTERNS:
            pattern_confidence = cfg[confidence_key]
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
                speaker, verb = self._find_attribution(
                    text, span_start, span_end, attribution_window
                )

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

    def _find_attribution(
        self, text: str, quote_start: int, quote_end: int, window: int
    ) -> tuple[str, str]:
        """Look for attribution verb + speaker name before or after quote."""
        after = text[quote_end : quote_end + window]
        m = _ATTRIBUTION_RE.search(after)
        if m:
            return m.group(2), m.group(1).lower()
        before_start = max(0, quote_start - window)
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
