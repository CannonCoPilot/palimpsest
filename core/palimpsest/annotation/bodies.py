"""Palimpsest-specific W3C annotation body type constructors.

Each function creates a Body with the correct type, purpose, lfo_type,
and Palimpsest-namespaced extra properties for its track type.
"""

from __future__ import annotations

from typing import Any

from palimpsest.annotation.model import Body


def entity_body(
    entity_type: str,
    name: str = "",
    mention_type: str = "name",
    lfo_type: str = "entity.character",
    canonical_name: str = "",
) -> Body:
    extra: dict[str, Any] = {
        "palimpsest:entityType": entity_type,
        "palimpsest:mentionType": mention_type,
    }
    if canonical_name:
        extra["palimpsest:canonicalName"] = canonical_name
    return Body(
        type="palimpsest:EntityAnnotation",
        purpose="classifying",
        value=name,
        lfo_type=lfo_type,
        extra=extra,
    )


def sentiment_body(
    valence: float,
    arousal: float = 0.0,
    model: str = "vader",
) -> Body:
    return Body(
        type="palimpsest:SentimentAnnotation",
        purpose="describing",
        lfo_type="signal.sentiment",
        extra={
            "palimpsest:valence": round(valence, 4),
            "palimpsest:arousal": round(arousal, 4),
            "palimpsest:model": model,
        },
    )


def lexical_body(
    ttr: float,
    hapax_count: int,
    mean_word_length: float,
    yules_k: float,
) -> Body:
    return Body(
        type="palimpsest:LexicalAnnotation",
        purpose="describing",
        lfo_type="signal.lexical_density",
        extra={
            "palimpsest:ttr": round(ttr, 4),
            "palimpsest:hapaxCount": hapax_count,
            "palimpsest:meanWordLength": round(mean_word_length, 4),
            "palimpsest:yulesK": round(yules_k, 4),
        },
    )


def dialogue_body(
    text: str = "",
    quote_type: str = "direct",
    speaker: str = "",
    verb: str = "",
) -> Body:
    extra: dict[str, Any] = {"palimpsest:quoteType": quote_type}
    if speaker:
        extra["palimpsest:speaker"] = speaker
    if verb:
        extra["palimpsest:verb"] = verb
    return Body(
        type="palimpsest:DialogueAnnotation",
        purpose="tagging",
        value=text[:200] if text else "",
        lfo_type="structural.dialogue.quote",
        extra=extra,
    )


def topic_body(
    topic_id: int,
    topic_weight: float,
    topic_terms: list[str] | None = None,
) -> Body:
    extra: dict[str, Any] = {
        "palimpsest:topicId": topic_id,
        "palimpsest:topicWeight": round(topic_weight, 4),
    }
    if topic_terms:
        extra["palimpsest:topicTerms"] = topic_terms
    return Body(
        type="palimpsest:TopicAnnotation",
        purpose="classifying",
        lfo_type="signal.topic_assignment",
        extra=extra,
    )


def coreference_body(
    chain_id: str,
    referent_id: str = "",
    mention_type: str = "name",
) -> Body:
    return Body(
        type="palimpsest:CoreferenceAnnotation",
        purpose="linking",
        lfo_type="entity.coreference_link",
        extra={
            "palimpsest:chainId": chain_id,
            "palimpsest:referentId": referent_id,
            "palimpsest:mentionType": mention_type,
        },
    )


def segment_body(
    segment_type: str,
    segment_index: int,
) -> Body:
    return Body(
        type="palimpsest:SegmentAnnotation",
        purpose="describing",
        lfo_type=f"structural.{segment_type}",
        extra={
            "palimpsest:segmentType": segment_type,
            "palimpsest:segmentIndex": segment_index,
        },
    )
