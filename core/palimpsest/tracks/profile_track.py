"""ProfileTrack — whole-document descriptive/distributional statistics (Wave-0 P4, FR-8, NFR-7).

A signal track that runs on the analysis view (masked-resolved analyzable text) and emits a single
``signals/profile.json`` manifest carrying a **report** (counts + lexical-diversity indices + Zipf/Heaps
fits + function-word profile + top n-grams) and **distribution data** (word/sentence/paragraph length
histograms) for P5/P6 to render. All compute is the deterministic, dependency-free
``palimpsest.analysis.textstats`` module.

Honesty (NFR-7): every number is descriptive *of this text* — there is no reference corpus, so the
manifest carries an explicit ``framing="descriptive"`` and caveats rather than implying norms.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from palimpsest.analysis import textstats
from palimpsest.atomic import atomic_write_text
from palimpsest.formats.signals import SignalManifest
from palimpsest.project import Project
from palimpsest.tracks.params import Param, ParameterizedTrack
from palimpsest.tracks.repeats import STOPWORDS

_CAVEATS = [
    "All statistics are descriptive of this text only; there is no reference corpus and no norm.",
    "Sentence boundaries are detected by a simple .!? splitter, so sentence-length stats are approximate.",
    "Counts are computed on the masked-resolved analyzable text (structural noise and verse numbers excised).",
]


class ProfileTrack(ParameterizedTrack):
    PARAMS = (
        Param("mattr_window", int, default=100, min=2, help="window size for moving-average TTR"),
        Param("dist_bins", int, default=30, min=1, max=200, help="histogram bin count for distributions"),
        Param("top_ngrams", int, default=25, min=1, max=200, help="how many top bigrams/trigrams to list"),
    )

    @property
    def name(self) -> str:
        return "profile"

    @property
    def output_type(self) -> str:
        return "signal"

    @property
    def depends_on(self) -> list[str]:
        # No real dependency → not a signal-consumer → runs on the analysis view (analyzable text).
        return []

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.profile"]

    @property
    def evidence_level(self) -> str:
        return "E1"

    def extract(self, project: Project) -> Path:
        p = self.resolved_params()
        bins = p["dist_bins"]

        text = project.reference_text()
        tokens = textstats.tokenize(text)

        para_word_lengths = [
            len(textstats.tokenize(t)) for _, _, t in project.paragraphs()
        ]
        para_word_lengths = [n for n in para_word_lengths if n > 0]
        word_char_lengths = [len(t) for t in tokens]
        sentence_lengths = textstats.sentence_word_lengths(text)

        report: dict[str, Any] = {
            "counts": textstats.basic_counts(tokens),
            "lexical_diversity": {
                "ttr": textstats.ttr(tokens),
                "mattr": textstats.mattr(tokens, window=p["mattr_window"]),
                "mtld": textstats.mtld(tokens),
                "yules_k": textstats.yules_k(tokens),
            },
            "zipf_slope": textstats.zipf_slope(tokens),
            "heaps": textstats.heaps_params(tokens),
            "function_words": textstats.function_word_profile(tokens, STOPWORDS),
            "top_bigrams": textstats.top_ngrams(tokens, 2, p["top_ngrams"]),
            "top_trigrams": textstats.top_ngrams(tokens, 3, p["top_ngrams"]),
        }
        distributions = {
            "word_length": textstats.histogram(word_char_lengths, bins=bins),
            "sentence_length": textstats.histogram(sentence_lengths, bins=bins),
            "paragraph_length": textstats.histogram(para_word_lengths, bins=bins),
        }

        metadata: dict[str, Any] = {
            "framing": "descriptive",
            "caveats": _CAVEATS,
            "report": report,
            "distributions": distributions,
            "params": self.parameters(),
        }

        manifest = SignalManifest(
            type="profile",
            name="profile",
            source="profile/0.1",
            reference_sha256=project.metadata.reference_sha256,
            dimensions=[report["counts"]["tokens"], report["counts"]["types"]],
            # No coordinate data — the profile is whole-document aggregate, so there is nothing for the
            # runner's signal remap to touch (segment_offsets stays empty).
            metadata=metadata,
        )

        signals_dir = project.path / "signals"
        signals_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = signals_dir / "profile.json"
        atomic_write_text(
            manifest_path, json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False)
        )
        return manifest_path

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "profile",
            "bodyType": "signal",
            "dedicatedView": "profile-panel",
            "colorScheme": {"primary": "#8B5CF6", "secondary": "#6D28D9"},
        }
