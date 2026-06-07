"""Coreference track — BookNLP coreference chains (optional, graceful fallback)."""

from __future__ import annotations

import logging
from typing import Any

from palimpsest.annotation.bodies import coreference_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector
from palimpsest.project import Project

logger = logging.getLogger(__name__)

BOOKNLP_AVAILABLE = False
try:
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        warnings.filterwarnings("ignore", category=UserWarning, message="pkg_resources")
        import booknlp  # noqa: F401

    BOOKNLP_AVAILABLE = True
except ImportError:
    pass


class CoreferenceExtractor:
    """Extract coreference chains via BookNLP.

    If BookNLP is not installed, extract() raises FileNotFoundError
    which the pipeline gracefully skips.
    """

    @property
    def name(self) -> str:
        return "coreference"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return ["entities"]

    @property
    def lfo_types(self) -> list[str]:
        return ["entity.coreference_link"]

    @property
    def evidence_level(self) -> str:
        return "E4"

    def extract(self, project: Project) -> list[Annotation]:
        if not BOOKNLP_AVAILABLE:
            raise FileNotFoundError(
                "BookNLP not installed. Install with: pip install booknlp\n"
                "Also requires Java 11+. Coreference track will be skipped."
            )

        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=SyntaxWarning)
            warnings.filterwarnings("ignore", category=UserWarning, message="pkg_resources")
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from booknlp.booknlp import BookNLP  # type: ignore[import-untyped]

        cache_dir = project.path / "cache" / "booknlp"
        cache_dir.mkdir(parents=True, exist_ok=True)

        model_params = {
            "pipeline": "entity,quote,supersense,event,coref",
            "model": "big",
        }

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=SyntaxWarning)
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            booknlp_model = BookNLP("en", model_params)

            input_file = project.path / "reference.txt"
            booknlp_model.process(
                str(input_file),
                str(cache_dir),
                project.metadata.id,
            )

        tokens_file = cache_dir / f"{project.metadata.id}.tokens"
        if not tokens_file.exists():
            raise FileNotFoundError(
                f"BookNLP output not found at {tokens_file}"
            )

        annotations: list[Annotation] = []
        source_urn = f"urn:palimpsest:{project.metadata.id}"

        chains: dict[int, list[dict[str, Any]]] = {}
        with tokens_file.open() as f:
            header = f.readline().strip().split("\t")
            coref_idx = header.index("coref") if "coref" in header else -1
            start_idx = header.index("byte_onset") if "byte_onset" in header else -1
            end_idx = header.index("byte_offset") if "byte_offset" in header else -1
            word_idx = header.index("word") if "word" in header else -1

            if coref_idx < 0 or start_idx < 0 or end_idx < 0:
                return []

            for line in f:
                fields = line.strip().split("\t")
                if len(fields) <= max(coref_idx, start_idx, end_idx):
                    continue
                chain_id_str = fields[coref_idx]
                if chain_id_str == "-1" or chain_id_str == "":
                    continue
                chain_id = int(chain_id_str)
                if chain_id not in chains:
                    chains[chain_id] = []
                chains[chain_id].append({
                    "start": int(fields[start_idx]),
                    "end": int(fields[end_idx]),
                    "word": fields[word_idx] if word_idx >= 0 else "",
                })

        for chain_id, mentions in chains.items():
            if len(mentions) < 2:
                continue
            referent = mentions[0]["word"]
            for mention in mentions:
                ann = Annotation(
                    body=coreference_body(
                        chain_id=str(chain_id),
                        referent_id=referent,
                        mention_type="name",
                    ),
                    target=Target(
                        source=source_urn,
                        selector=TextPositionSelector(
                            start=mention["start"],
                            end=mention["end"],
                        ),
                    ),
                    creator=Creator(name="booknlp/2.0"),
                    confidence=0.75,
                    evidence_level="E4",
                    project_id=project.metadata.id,
                    track_name="coreference",
                )
                annotations.append(ann)

        return annotations

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": "coreference",
            "bodyType": "palimpsest:CoreferenceAnnotation",
            "colorScheme": {
                "primary": "#14B8A6",
                "secondary": "#0D9488",
            },
            "textViewRendering": "underline",
            "overviewBarRendering": {"type": "density-barcode", "color": "#14B8A6"},
        }

    def parameters(self) -> dict[str, Any]:
        return {
            "coreference.model": "booknlp/big" if BOOKNLP_AVAILABLE else "unavailable",
            "coreference.available": BOOKNLP_AVAILABLE,
        }
