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
    """Extract coreference chains via BookNLP with spaCy NER fallback.

    If BookNLP is not installed, falls back to spaCy-based name repetition
    chains (lower quality but always available).
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
            return self._spacy_fallback(project)


        import os
        import warnings

        # Use cached HF models — don't hit the network on every run
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

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

        entities_file = cache_dir / f"{project.metadata.id}.entities"
        tokens_file = cache_dir / f"{project.metadata.id}.tokens"
        if not entities_file.exists() or not tokens_file.exists():
            raise FileNotFoundError(
                f"BookNLP output not found at {cache_dir}"
            )

        # Build token_id → byte offset mapping from .tokens file
        token_offsets: dict[int, tuple[int, int]] = {}
        with tokens_file.open() as f:
            header = f.readline().strip().split("\t")
            tid_idx = header.index("token_ID_within_document")
            onset_idx = header.index("byte_onset")
            offset_idx = header.index("byte_offset")
            for line in f:
                fields = line.strip().split("\t")
                tid = int(fields[tid_idx])
                token_offsets[tid] = (int(fields[onset_idx]), int(fields[offset_idx]))

        # Read coreference chains from .entities file
        chains: dict[int, list[dict[str, Any]]] = {}
        with entities_file.open() as f:
            f.readline()  # skip header: COREF start_token end_token prop cat text
            for line in f:
                fields = line.strip().split("\t")
                if len(fields) < 6:
                    continue
                chain_id = int(fields[0])
                start_tok = int(fields[1])
                end_tok = int(fields[2])
                mention_type = fields[3].lower()  # PROP/NOM/PRON
                text = fields[5]

                if start_tok not in token_offsets or end_tok not in token_offsets:
                    continue
                byte_start = token_offsets[start_tok][0]
                byte_end = token_offsets[end_tok][1]

                if chain_id not in chains:
                    chains[chain_id] = []
                chains[chain_id].append({
                    "start": byte_start,
                    "end": byte_end,
                    "text": text,
                    "mention_type": mention_type,
                })

        annotations: list[Annotation] = []
        source_urn = f"urn:palimpsest:{project.metadata.id}"

        for chain_id, mentions in chains.items():
            if len(mentions) < 2:
                continue
            referent = mentions[0]["text"]
            for mention in mentions:
                ann = Annotation(
                    body=coreference_body(
                        chain_id=str(chain_id),
                        referent_id=referent,
                        mention_type=mention["mention_type"],
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

    def _spacy_fallback(self, project: Project) -> list[Annotation]:
        """Basic coreference via spaCy NER: link repeated entity mentions into chains."""
        import spacy

        try:
            nlp = spacy.load("en_core_web_lg")
        except OSError:
            nlp = spacy.load("en_core_web_sm")

        text = project.reference_text()
        nlp.max_length = len(text) + 1000
        doc = nlp(text)

        name_chains: dict[str, list[tuple[int, int, str]]] = {}
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "GPE", "LOC", "ORG"):
                key = ent.text.strip().lower()
                if key not in name_chains:
                    name_chains[key] = []
                name_chains[key].append((ent.start_char, ent.end_char, ent.text))

        annotations: list[Annotation] = []
        source_urn = f"urn:palimpsest:{project.metadata.id}"
        chain_id = 0

        for _key, mentions in name_chains.items():
            if len(mentions) < 2:
                continue
            referent = max(mentions, key=lambda m: len(m[2]))[2]
            for start, end, mention_text in mentions:
                ann = Annotation(
                    body=coreference_body(
                        chain_id=str(chain_id),
                        referent_id=referent,
                        mention_type="name",
                    ),
                    target=Target(
                        source=source_urn,
                        selector=TextPositionSelector(start=start, end=end),
                    ),
                    creator=Creator(name="spacy-coref-fallback/0.1"),
                    confidence=0.60,
                    evidence_level="E4",
                    project_id=project.metadata.id,
                    track_name="coreference",
                )
                annotations.append(ann)
            chain_id += 1

        return annotations

    def parameters(self) -> dict[str, Any]:
        return {
            "coreference.model": "booknlp/big" if BOOKNLP_AVAILABLE else "spacy-fallback",
            "coreference.available": True,
            "coreference.booknlp_available": BOOKNLP_AVAILABLE,
        }
