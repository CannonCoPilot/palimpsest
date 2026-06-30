"""AlignmentRecord — data model for pairwise text alignment results."""

from __future__ import annotations

import json
import math
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


def _mapq_from_pvalue(p_value: float) -> int:
    """Phred-scaled mapping quality from a p-value, capped to PAF's 0–255 range."""
    p = min(max(p_value, 1e-9), 1.0)
    return max(0, min(255, int(round(-10.0 * math.log10(p)))))


def records_to_paf(
    records: list[AlignmentRecord], query_len: int, target_len: int
) -> list[str]:
    """Render alignment records as minimap2 PAF lines (FR-36): 12 mandatory tab-separated columns
    plus optional tags.

    Our records carry character spans but no per-residue CIGAR, so the residue-match count (col 10) is
    approximated from ``identity × block_len`` (block_len = the longer of the two spans), and mapping
    quality (col 12) is the Phred-scaled p-value. Score, p-value, identity and method travel as PAF
    optional tags so nothing is lost: ``AS:i`` (score), ``pv:f`` (p-value), ``id:f`` (identity),
    ``mt:Z`` (method)."""
    lines: list[str] = []
    for r in records:
        q_span = max(0, r.query_end - r.query_start)
        t_span = max(0, r.target_end - r.target_start)
        block = max(q_span, t_span, 1)
        matches = int(round(r.identity * block)) if r.identity > 0 else block
        matches = min(matches, block)
        cols = [
            r.query_id, str(query_len), str(r.query_start), str(r.query_end),
            r.strand or "+",
            r.target_id, str(target_len), str(r.target_start), str(r.target_end),
            str(matches), str(block), str(_mapq_from_pvalue(r.p_value)),
            f"AS:i:{int(round(r.score))}",
            f"pv:f:{r.p_value:.6g}",
            f"id:f:{r.identity:.6g}",
            f"mt:Z:{r.method}",
        ]
        lines.append("\t".join(cols))
    return lines


def write_paf(
    path: Path, records: list[AlignmentRecord], *, query_len: int, target_len: int
) -> None:
    """Write alignment records in minimap2 PAF format (FR-36)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(records_to_paf(records, query_len, target_len))
    path.write_text(body + ("\n" if records else ""), encoding="utf-8")
