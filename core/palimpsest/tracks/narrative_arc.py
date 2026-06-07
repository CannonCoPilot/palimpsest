"""Narrative arc track — Boyd function-word structural arc (5 segments x 3 dims)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

from palimpsest.formats.signals import SignalManifest, write_signal
from palimpsest.project import Project

STAGING_WORDS: frozenset[str] = frozenset({
    "a", "an", "the",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "about",
    "one", "two", "three", "several", "many", "few", "some", "each", "all",
    "this", "that", "these", "those", "which", "what", "who",
    "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "they", "their", "them", "there", "here",
})

PROGRESSION_WORDS: frozenset[str] = frozenset({
    "then", "after", "before", "when", "while", "until", "since", "during",
    "because", "therefore", "so", "thus", "finally", "suddenly",
    "next", "already", "still", "yet", "now", "soon",
    "first", "second", "last", "again", "once",
})

TENSION_WORDS: frozenset[str] = frozenset({
    "think", "know", "feel", "want", "need", "believe", "understand", "wonder",
    "not", "never", "no", "nothing", "without", "cannot", "could", "would",
    "should", "might", "must", "but", "however", "although", "though",
    "if", "whether", "perhaps", "maybe", "seem", "appear",
})


class NarrativeArcTrack:
    @property
    def name(self) -> str:
        return "narrative_arc"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        return []

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.narrative_arc"]

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project: Project) -> Path:
        text = project.reference_text()
        all_tokens = re.findall(r"[a-z']+", text.lower())
        n_words = len(all_tokens)

        if n_words == 0:
            arc = np.zeros((5, 3), dtype=np.float32)
        else:
            segment_size = n_words // 5
            arc = np.zeros((5, 3), dtype=np.float32)

            for seg_idx in range(5):
                seg_start = seg_idx * segment_size
                seg_end = seg_start + segment_size if seg_idx < 4 else n_words
                seg_tokens = all_tokens[seg_start:seg_end]
                seg_count = len(seg_tokens)
                if seg_count == 0:
                    continue
                arc[seg_idx, 0] = sum(1 for t in seg_tokens if t in STAGING_WORDS) / seg_count
                arc[seg_idx, 1] = sum(1 for t in seg_tokens if t in PROGRESSION_WORDS) / seg_count
                arc[seg_idx, 2] = sum(1 for t in seg_tokens if t in TENSION_WORDS) / seg_count

        sha = project.metadata.reference_sha256
        manifest = SignalManifest(
            type="vector",
            name="narrative_arc",
            source="boyd_function_words/0.1",
            reference_sha256=sha,
            dimensions=[5, 3],
            data_file="narrative_arc.bin",
            metadata={
                "dimensions_label": ["staging", "progression", "tension"],
                "segments": 5,
                "word_count": n_words,
            },
        )

        signals_dir = project.path / "signals"
        write_signal(signals_dir, arc, manifest)
        return signals_dir / "narrative_arc.json"

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "narrative_arc",
            "bodyType": "signal",
            "colorScheme": {
                "primary": "#8B5CF6",
                "secondary": "#6D28D9",
                "scale": ["#EDE9FE", "#8B5CF6", "#4C1D95"],
            },
            "dedicatedView": "sparkline",
        }

    def parameters(self) -> dict[str, Any]:
        return {
            "narrative_arc.model": "boyd_function_words",
            "narrative_arc.segments": 5,
            "narrative_arc.dimensions": 3,
        }
