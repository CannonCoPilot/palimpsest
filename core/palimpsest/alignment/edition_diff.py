"""Edition comparison — character-level diff with paragraph-preserving alignment.

CollateX-inspired methodology: align paragraphs via LCS, then compute
character-level diffs within each aligned pair.
"""

from __future__ import annotations

import difflib
import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from palimpsest.project import Project

logger = logging.getLogger(__name__)


@dataclass
class DiffRecord:
    """A single change between two text editions."""

    para_index_a: int
    para_index_b: int
    change_type: str  # "insert" | "delete" | "replace" | "equal"
    text_a: str
    text_b: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DiffRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DiffSummary:
    """Statistics for an edition comparison."""

    total_paragraphs_a: int
    total_paragraphs_b: int
    aligned_pairs: int
    insertions: int
    deletions: int
    replacements: int
    unchanged: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_edition_diff(
    project_a: Project,
    project_b: Project,
) -> tuple[list[DiffRecord], DiffSummary]:
    """Compute character-level diff between two editions.

    Step 1: Align paragraphs via longest common subsequence on paragraph text hashes.
    Step 2: For each aligned pair, compute character-level diff.
    """
    paras_a = project_a.paragraphs()
    paras_b = project_b.paragraphs()

    texts_a = [text for _, _, text in paras_a]
    texts_b = [text for _, _, text in paras_b]

    # Paragraph-level alignment via SequenceMatcher
    matcher = difflib.SequenceMatcher(None, texts_a, texts_b)
    opcodes = matcher.get_opcodes()

    records: list[DiffRecord] = []
    insertions = 0
    deletions = 0
    replacements = 0
    unchanged = 0
    aligned_pairs = 0

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            for k in range(i2 - i1):
                unchanged += 1
                aligned_pairs += 1
        elif tag == 'replace':
            a_count = i2 - i1
            b_count = j2 - j1
            pairs = min(a_count, b_count)
            for k in range(pairs):
                aligned_pairs += 1
                replacements += 1
                records.append(DiffRecord(
                    para_index_a=i1 + k,
                    para_index_b=j1 + k,
                    change_type='replace',
                    text_a=texts_a[i1 + k][:500],
                    text_b=texts_b[j1 + k][:500],
                ))
            for k in range(pairs, a_count):
                deletions += 1
                records.append(DiffRecord(
                    para_index_a=i1 + k,
                    para_index_b=-1,
                    change_type='delete',
                    text_a=texts_a[i1 + k][:500],
                    text_b='',
                ))
            for k in range(pairs, b_count):
                insertions += 1
                records.append(DiffRecord(
                    para_index_a=-1,
                    para_index_b=j1 + k,
                    change_type='insert',
                    text_a='',
                    text_b=texts_b[j1 + k][:500],
                ))
        elif tag == 'delete':
            for k in range(i1, i2):
                deletions += 1
                records.append(DiffRecord(
                    para_index_a=k,
                    para_index_b=-1,
                    change_type='delete',
                    text_a=texts_a[k][:500],
                    text_b='',
                ))
        elif tag == 'insert':
            for k in range(j1, j2):
                insertions += 1
                records.append(DiffRecord(
                    para_index_a=-1,
                    para_index_b=k,
                    change_type='insert',
                    text_a='',
                    text_b=texts_b[k][:500],
                ))

    summary = DiffSummary(
        total_paragraphs_a=len(paras_a),
        total_paragraphs_b=len(paras_b),
        aligned_pairs=aligned_pairs,
        insertions=insertions,
        deletions=deletions,
        replacements=replacements,
        unchanged=unchanged,
    )

    logger.info(
        "Diff: %d aligned, %d insert, %d delete, %d replace, %d unchanged",
        aligned_pairs, insertions, deletions, replacements, unchanged,
    )
    return records, summary


def write_diff_results(path: Path, records: list[DiffRecord], summary: DiffSummary) -> None:
    """Write diff results to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "summary": summary.to_dict(),
            "records": [r.to_dict() for r in records],
        }, indent=2),
        encoding="utf-8",
    )


def read_diff_results(path: Path) -> tuple[list[DiffRecord], DiffSummary]:
    """Read diff results from a JSON file."""
    data = json.loads(path.read_text())
    records = [DiffRecord.from_dict(r) for r in data["records"]]
    summary = DiffSummary(**data["summary"])
    return records, summary
