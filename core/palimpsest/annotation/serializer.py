"""JSONL serializer for W3C Web Annotations.

Reads and writes JSONL files where each line is a complete W3C annotation.
Lines are ordered by target.selector.start for efficient sequential access.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from palimpsest.annotation.model import (
    DEFAULT_CONTEXT,
    EVIDENCE_LEVELS,
    Annotation,
    TextPositionSelector,
)


def write_track(path: Path, annotations: list[Annotation]) -> None:
    """Write annotations to a JSONL file, sorted by start offset.

    All annotations must use TextPositionSelector for deterministic ordering.
    """

    def sort_key(a: Annotation) -> int:
        sel = a.target.selector
        if not isinstance(sel, TextPositionSelector):
            raise TypeError(
                f"write_track requires TextPositionSelector, got {type(sel).__name__}"
            )
        return sel.start

    sorted_anns = sorted(annotations, key=sort_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ann in sorted_anns:
            f.write(json.dumps(ann.to_jsonld(), ensure_ascii=False) + "\n")


def read_track(path: Path) -> list[Annotation]:
    """Read annotations from a JSONL file."""
    annotations: list[Annotation] = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                annotations.append(Annotation.from_jsonld(data))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise ValueError(f"Invalid annotation at line {line_num} in {path}: {e}") from e
    return annotations


def validate_annotation(data: dict[str, Any]) -> list[str]:
    """Validate a JSON-LD annotation dict, returning a list of error messages."""
    errors: list[str] = []

    ctx = data.get("@context")
    if ctx is None:
        errors.append("Missing '@context'")
    elif ctx != DEFAULT_CONTEXT:
        errors.append(
            f"Invalid '@context': expected {DEFAULT_CONTEXT!r}, got {ctx!r}"
        )

    if "id" not in data:
        errors.append("Missing 'id'")

    if data.get("type") != "Annotation":
        errors.append(f"Expected type 'Annotation', got {data.get('type')!r}")

    if "body" not in data:
        errors.append("Missing 'body'")
    elif not isinstance(data["body"], dict):
        errors.append("'body' must be a dict")
    elif "type" not in data["body"]:
        errors.append("body missing 'type'")

    if "target" not in data:
        errors.append("Missing 'target'")
    elif not isinstance(data["target"], dict):
        errors.append("'target' must be a dict")
    else:
        if "source" not in data["target"]:
            errors.append("target missing 'source'")
        if "selector" not in data["target"]:
            errors.append("target missing 'selector'")
        else:
            sel = data["target"]["selector"]
            if isinstance(sel, dict) and sel.get("type") == "TextPositionSelector":
                start = sel.get("start")
                end = sel.get("end")
                if start is not None and end is not None:
                    if not isinstance(start, int) or not isinstance(end, int):
                        errors.append("Selector start/end must be integers")
                    elif start > end:
                        errors.append(f"Selector start ({start}) > end ({end})")
                    elif start < 0:
                        errors.append(f"Selector start must be non-negative, got {start}")

    if "creator" not in data:
        errors.append("Missing 'creator'")

    if "palimpsest:evidenceLevel" not in data:
        errors.append("Missing 'palimpsest:evidenceLevel'")
    else:
        ev = data["palimpsest:evidenceLevel"]
        if ev not in EVIDENCE_LEVELS:
            errors.append(f"Invalid evidence level: {ev!r}")

    if "palimpsest:confidence" not in data:
        errors.append("Missing 'palimpsest:confidence'")
    else:
        conf = data["palimpsest:confidence"]
        if not isinstance(conf, (int, float)):
            errors.append(f"Confidence must be numeric, got {type(conf).__name__}")
        elif not 0.0 <= float(conf) <= 1.0:
            errors.append(f"Confidence out of range [0, 1]: {conf}")

    return errors
