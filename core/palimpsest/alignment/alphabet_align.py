"""Narrative alphabet alignment — Foldseek-inspired fast structural comparison.

Aligns two texts by their narrative alphabet sequences (discrete state
representations from K-means clustering). Uses Smith-Waterman on character
sequences with a simple match/mismatch scoring scheme.
"""

from __future__ import annotations

import json
import logging

import numpy as np

from palimpsest.alignment.records import AlignmentRecord
from palimpsest.project import Project

logger = logging.getLogger(__name__)


def load_alphabet_sequence(project: Project) -> str:
    """Load the narrative alphabet sequence from a project's signals."""
    manifest_path = project.path / "signals" / "alphabet.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Alphabet signal not found for {project.metadata.id}. "
            "Run the alphabet track first."
        )
    manifest = json.loads(manifest_path.read_text())
    seq = manifest.get("metadata", {}).get("sequence", "")
    if not seq:
        raise ValueError(f"Empty alphabet sequence for {project.metadata.id}")
    return seq


def align_alphabets(
    project_a: Project,
    project_b: Project,
    gap_open: float = -2.0,
    gap_extend: float = -0.5,
    min_length: int = 3,
) -> list[AlignmentRecord]:
    """Align two projects by narrative alphabet sequences.

    This is the Foldseek analog — orders of magnitude faster than semantic
    alignment because it operates on short discrete-state strings rather
    than high-dimensional embedding matrices.
    """
    seq_a = load_alphabet_sequence(project_a)
    seq_b = load_alphabet_sequence(project_b)

    n = len(seq_a)
    m = len(seq_b)
    logger.info("Aligning alphabets: %d x %d characters", n, m)

    # Build similarity matrix — vectorized character match/mismatch
    arr_a = np.frombuffer(seq_a.encode('ascii'), dtype=np.uint8)
    arr_b = np.frombuffer(seq_b.encode('ascii'), dtype=np.uint8)
    sim_matrix = np.equal.outer(arr_a, arr_b).astype(np.float32)

    # Reuse Smith-Waterman with alphabet-specific scoring
    from palimpsest.alignment.smith_waterman import smith_waterman

    records = smith_waterman(
        sim_matrix,
        query_id=project_a.metadata.id,
        target_id=project_b.metadata.id,
        method="alphabet",
        gap_open=gap_open,
        gap_extend=gap_extend,
        min_length=min_length,
    )

    return records
