"""Syntactic complexity track: dependency depth, subordination ratio → W3C SyntaxAnnotation JSONL."""

from __future__ import annotations

from typing import Any

import spacy

from palimpsest.annotation.bodies import syntax_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector

DEFAULT_SPACY_MODEL = "en_core_web_lg"
_NLP_CACHE: dict[str, Any] = {}

SUBORDINATE_DEPS = frozenset({
    "advcl", "relcl", "acl", "csubj", "ccomp", "xcomp",
})


def _get_nlp(model: str = DEFAULT_SPACY_MODEL) -> Any:
    if model not in _NLP_CACHE:
        try:
            _NLP_CACHE[model] = spacy.load(model)
        except OSError:
            _NLP_CACHE[model] = spacy.load("en_core_web_sm")
    return _NLP_CACHE[model]


def _tree_depth(token: Any, _depth: int = 0) -> int:
    if _depth > 100:
        return _depth
    children = list(token.children)
    if not children:
        return 0
    return 1 + max(_tree_depth(c, _depth + 1) for c in children)


class SyntaxExtractor:
    """Per-paragraph syntactic complexity features."""

    @property
    def name(self) -> str:
        return "syntax"

    @property
    def output_type(self) -> str:
        return "annotation"

    @property
    def depends_on(self) -> list[str]:
        return ["_spacy_parse"]

    @property
    def lfo_types(self) -> list[str]:
        return ["signal.syntactic_complexity"]

    @property
    def evidence_level(self) -> str:
        return "E5"

    def extract(self, project: Any) -> list[Annotation]:
        doc = project.spacy_doc(DEFAULT_SPACY_MODEL)

        paragraphs = project.paragraphs()
        source_urn = f"urn:palimpsest:{project.metadata.id}"
        annotations: list[Annotation] = []

        for para_start, para_end, _para_text in paragraphs:
            para_span = doc.char_span(para_start, para_end)
            if para_span is None:
                continue

            sents = list(para_span.sents)
            if not sents:
                continue

            depths: list[int] = []
            sub_counts: list[int] = []
            sent_lengths: list[int] = []

            for sent in sents:
                root = None
                for token in sent:
                    if token.dep_ == "ROOT":
                        root = token
                        break
                if root is not None:
                    depths.append(_tree_depth(root))

                sub_count = sum(1 for t in sent if t.dep_ in SUBORDINATE_DEPS)
                sub_counts.append(sub_count)
                sent_lengths.append(len(sent))

            if not depths:
                continue

            mean_depth = sum(depths) / len(depths)
            total_tokens = sum(sent_lengths)
            sub_ratio = sum(sub_counts) / max(total_tokens, 1)
            mean_sent_len = total_tokens / len(sents)

            ann = Annotation(
                body=syntax_body(
                    mean_tree_depth=mean_depth,
                    subordination_ratio=sub_ratio,
                    mean_sentence_length=mean_sent_len,
                ),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=para_start, end=para_end),
                ),
                creator=Creator(name=f"spacy/{DEFAULT_SPACY_MODEL}"),
                confidence=0.90,
                evidence_level="E5",
                project_id=project.metadata.id,
                track_name="syntax",
            )
            annotations.append(ann)

        return annotations

    def manifest(self) -> dict[str, Any]:
        return {
            "trackName": self.name,
            "bodyType": "palimpsest:SyntaxAnnotation",
            "colorScheme": {"primary": "#e67e22", "secondary": "#f0b27a"},
            "textViewRendering": "margin-marker",
            "overviewBarRendering": {"type": "density-barcode", "color": "#e67e22"},
        }

    def parameters(self) -> dict[str, Any]:
        return {"syntax.spacy_model": DEFAULT_SPACY_MODEL}
