"""AlignmentRecord — data model for pairwise text alignment results."""

from __future__ import annotations

import json
from dataclasses import dataclass
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
        return {
            "queryId": self.query_id,
            "queryStart": self.query_start,
            "queryEnd": self.query_end,
            "targetId": self.target_id,
            "targetStart": self.target_start,
            "targetEnd": self.target_end,
            "score": self.score,
            "pValue": self.p_value,
            "method": self.method,
            "strand": self.strand,
            "identity": self.identity,
            "cigar": self.cigar,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AlignmentRecord:
        return cls(
            query_id=d.get("query_id", d.get("queryId", "")),
            query_start=d.get("query_start", d.get("queryStart", 0)),
            query_end=d.get("query_end", d.get("queryEnd", 0)),
            target_id=d.get("target_id", d.get("targetId", "")),
            target_start=d.get("target_start", d.get("targetStart", 0)),
            target_end=d.get("target_end", d.get("targetEnd", 0)),
            score=d.get("score", 0.0),
            p_value=d.get("p_value", d.get("pValue", 1.0)),
            method=d.get("method", "semantic"),
            strand=d.get("strand", "+"),
            identity=d.get("identity", 0.0),
            cigar=d.get("cigar", ""),
        )


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
