"""AlignmentRecord — data model for pairwise text alignment results."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class AlignmentRecord:
    """A single aligned region between two texts."""

    query_id: str
    query_start: int
    query_end: int
    target_id: str
    target_start: int
    target_end: int
    score: float
    p_value: float = 1.0
    method: str = "semantic"
    strand: str = "+"
    identity: float = 0.0
    cigar: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AlignmentRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def write_alignment_records(path: Path, records: list[AlignmentRecord]) -> None:
    """Write alignment records as JSON Lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.to_dict()) + "\n")


def read_alignment_records(path: Path) -> list[AlignmentRecord]:
    """Read alignment records from JSON Lines."""
    records: list[AlignmentRecord] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(AlignmentRecord.from_dict(json.loads(line)))
    return records
