"""W3C Web Annotation Data Model for Palimpsest.

Core dataclasses that represent W3C Web Annotations with Palimpsest-specific
extensions (evidence levels, custom body types, namespaced properties).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

W3C_CONTEXT = "http://www.w3.org/ns/anno.jsonld"
PALIMPSEST_NS = "https://palimpsest.dev/ns/"
EVIDENCE_LEVELS = frozenset({"E1", "E2", "E3", "E4", "E5"})

DEFAULT_CONTEXT: list[Any] = [
    W3C_CONTEXT,
    {"palimpsest": PALIMPSEST_NS},
]


@dataclass
class TextPositionSelector:
    start: int
    end: int

    def to_jsonld(self) -> dict[str, Any]:
        return {
            "type": "TextPositionSelector",
            "start": self.start,
            "end": self.end,
        }

    @classmethod
    def from_jsonld(cls, data: dict[str, Any]) -> TextPositionSelector:
        return cls(start=int(data["start"]), end=int(data["end"]))


@dataclass
class TextQuoteSelector:
    exact: str
    prefix: str = ""
    suffix: str = ""

    def to_jsonld(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": "TextQuoteSelector", "exact": self.exact}
        if self.prefix:
            d["prefix"] = self.prefix
        if self.suffix:
            d["suffix"] = self.suffix
        return d

    @classmethod
    def from_jsonld(cls, data: dict[str, Any]) -> TextQuoteSelector:
        return cls(
            exact=data["exact"],
            prefix=data.get("prefix", ""),
            suffix=data.get("suffix", ""),
        )


Selector = TextPositionSelector | TextQuoteSelector


def selector_from_jsonld(data: dict[str, Any]) -> Selector:
    t = data.get("type", "")
    if t == "TextPositionSelector":
        return TextPositionSelector.from_jsonld(data)
    if t == "TextQuoteSelector":
        return TextQuoteSelector.from_jsonld(data)
    raise ValueError(f"Unknown selector type: {t}")


@dataclass
class Target:
    source: str
    selector: Selector

    def to_jsonld(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "selector": self.selector.to_jsonld(),
        }

    @classmethod
    def from_jsonld(cls, data: dict[str, Any]) -> Target:
        return cls(
            source=data["source"],
            selector=selector_from_jsonld(data["selector"]),
        )


@dataclass
class Creator:
    name: str
    type: str = "Software"

    def to_jsonld(self) -> dict[str, Any]:
        return {"type": self.type, "name": self.name}

    @classmethod
    def from_jsonld(cls, data: dict[str, Any]) -> Creator:
        return cls(name=data["name"], type=data.get("type", "Software"))


_BODY_BASE_KEYS = frozenset({"type", "purpose", "value", "palimpsest:lfoType"})


@dataclass
class Body:
    """W3C annotation body with Palimpsest extensions.

    The `type` field holds the Palimpsest body type name
    (e.g., "palimpsest:EntityAnnotation"). Additional properties
    are stored in `extra` as a flat dict of key-value pairs.
    """

    type: str
    purpose: str = ""
    value: str = ""
    lfo_type: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        collisions = set(self.extra.keys()) & _BODY_BASE_KEYS
        if collisions:
            raise ValueError(
                f"Body 'extra' dict contains reserved keys: {collisions}. "
                f"Use the dedicated fields instead."
            )

    def to_jsonld(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        d.update(self.extra)
        d["type"] = self.type
        if self.purpose:
            d["purpose"] = self.purpose
        if self.value:
            d["value"] = self.value
        if self.lfo_type:
            d["palimpsest:lfoType"] = self.lfo_type
        return d

    @classmethod
    def from_jsonld(cls, data: dict[str, Any]) -> Body:
        return cls(
            type=data.get("type", ""),
            purpose=data.get("purpose", ""),
            value=data.get("value", ""),
            lfo_type=data.get("palimpsest:lfoType", ""),
            extra={k: v for k, v in data.items() if k not in _BODY_BASE_KEYS},
        )


@dataclass
class Annotation:
    """A W3C Web Annotation with Palimpsest extensions."""

    body: Body
    target: Target
    creator: Creator
    confidence: float = 0.0
    evidence_level: str = "E4"
    id: str = ""
    project_id: str = ""
    track_name: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be in [0.0, 1.0], got {self.confidence}"
            )
        if self.evidence_level not in EVIDENCE_LEVELS:
            raise ValueError(
                f"Invalid evidence level: {self.evidence_level!r}. "
                f"Must be one of {sorted(EVIDENCE_LEVELS)}"
            )
        if not self.id:
            suffix = uuid.uuid4().hex[:8]
            if self.project_id and self.track_name:
                self.id = f"urn:palimpsest:{self.project_id}:{self.track_name}:{suffix}"
            else:
                self.id = f"urn:palimpsest:{suffix}"

    def to_jsonld(self) -> dict[str, Any]:
        return {
            "@context": list(DEFAULT_CONTEXT),
            "type": "Annotation",
            "id": self.id,
            "body": self.body.to_jsonld(),
            "target": self.target.to_jsonld(),
            "creator": self.creator.to_jsonld(),
            "palimpsest:confidence": self.confidence,
            "palimpsest:evidenceLevel": self.evidence_level,
        }

    @classmethod
    def from_jsonld(cls, data: dict[str, Any]) -> Annotation:
        if "creator" not in data:
            raise ValueError("Annotation missing required field 'creator'")
        if "body" not in data:
            raise ValueError("Annotation missing required field 'body'")
        if "target" not in data:
            raise ValueError("Annotation missing required field 'target'")

        ann_id = data.get("id", "")
        project_id = ""
        track_name = ""
        if ann_id.startswith("urn:palimpsest:"):
            parts = ann_id.split(":")
            if len(parts) >= 5:
                project_id = parts[2]
                track_name = parts[3]

        return cls(
            id=ann_id,
            body=Body.from_jsonld(data["body"]),
            target=Target.from_jsonld(data["target"]),
            creator=Creator.from_jsonld(data["creator"]),
            confidence=float(data.get("palimpsest:confidence", 0.0)),
            evidence_level=str(data.get("palimpsest:evidenceLevel", "E4")),
            project_id=project_id,
            track_name=track_name,
        )
