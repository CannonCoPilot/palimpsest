"""Tests for W3C annotation model, body types, and JSONL serializer."""

import json

import pytest

from palimpsest.annotation.bodies import (
    coreference_body,
    dialogue_body,
    entity_body,
    lexical_body,
    segment_body,
    sentiment_body,
    topic_body,
)
from palimpsest.annotation.model import (
    DEFAULT_CONTEXT,
    Annotation,
    Body,
    Creator,
    Target,
    TextPositionSelector,
    TextQuoteSelector,
)
from palimpsest.annotation.serializer import read_track, validate_annotation, write_track


def _make_annotation(**overrides):
    defaults = dict(
        body=entity_body("PER", name="Mr. Bennet", lfo_type="entity.character"),
        target=Target(
            source="urn:palimpsest:pride-and-prejudice",
            selector=TextPositionSelector(start=14, end=23),
        ),
        creator=Creator(name="spacy/en_core_web_lg/3.7"),
        confidence=0.95,
        evidence_level="E4",
        project_id="pride-and-prejudice",
        track_name="entities",
    )
    defaults.update(overrides)
    return Annotation(**defaults)


class TestAnnotationRoundTrip:
    def test_to_jsonld_and_back(self):
        ann = _make_annotation()
        jld = ann.to_jsonld()
        restored = Annotation.from_jsonld(jld)
        assert restored.body.type == "palimpsest:EntityAnnotation"
        assert restored.target.source == "urn:palimpsest:pride-and-prejudice"
        assert restored.confidence == 0.95
        assert restored.evidence_level == "E4"

    def test_json_serialize_deserialize(self):
        ann = _make_annotation()
        json_str = json.dumps(ann.to_jsonld())
        data = json.loads(json_str)
        restored = Annotation.from_jsonld(data)
        assert restored.body.value == "Mr. Bennet"

    def test_context_correct_structure(self):
        ann = _make_annotation()
        jld = ann.to_jsonld()
        assert jld["@context"] == DEFAULT_CONTEXT
        assert isinstance(jld["@context"], list)
        assert jld["@context"][0] == "http://www.w3.org/ns/anno.jsonld"
        assert jld["@context"][1] == {"palimpsest": "https://palimpsest.dev/ns/"}

    def test_id_format_with_project_and_track(self):
        ann = _make_annotation()
        assert ann.id.startswith("urn:palimpsest:pride-and-prejudice:entities:")
        parts = ann.id.split(":")
        assert len(parts) == 5

    def test_id_format_without_project(self):
        ann = Annotation(
            body=entity_body("PER", name="test"),
            target=Target(source="urn:test", selector=TextPositionSelector(start=0, end=4)),
            creator=Creator(name="test"),
            confidence=0.5,
            evidence_level="E4",
        )
        assert ann.id.startswith("urn:palimpsest:")

    def test_custom_id_preserved(self):
        ann = _make_annotation(id="urn:palimpsest:test:entities:e001")
        assert ann.id == "urn:palimpsest:test:entities:e001"
        jld = ann.to_jsonld()
        assert jld["id"] == "urn:palimpsest:test:entities:e001"

    def test_invalid_evidence_level_raises(self):
        with pytest.raises(ValueError, match="Invalid evidence level"):
            _make_annotation(evidence_level="E99")

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError, match="Confidence must be"):
            _make_annotation(confidence=1.5)

    def test_confidence_negative_raises(self):
        with pytest.raises(ValueError, match="Confidence must be"):
            _make_annotation(confidence=-0.1)

    def test_text_position_selector_roundtrip(self):
        sel = TextPositionSelector(start=10, end=20)
        jld = sel.to_jsonld()
        restored = TextPositionSelector.from_jsonld(jld)
        assert restored.start == 10
        assert restored.end == 20

    def test_text_quote_selector_roundtrip(self):
        sel = TextQuoteSelector(exact="hello world", prefix="say ", suffix=" now")
        jld = sel.to_jsonld()
        restored = TextQuoteSelector.from_jsonld(jld)
        assert restored.exact == "hello world"
        assert restored.prefix == "say "

    def test_from_jsonld_missing_creator_raises(self):
        data = {
            "type": "Annotation",
            "body": {"type": "test"},
            "target": {
                "source": "x",
                "selector": {"type": "TextPositionSelector", "start": 0, "end": 1},
            },
        }
        with pytest.raises(ValueError, match="creator"):
            Annotation.from_jsonld(data)


class TestBodyTypes:
    def test_entity_body(self):
        b = entity_body("PER", name="Ishmael")
        assert b.type == "palimpsest:EntityAnnotation"
        assert b.purpose == "classifying"
        assert b.extra["palimpsest:entityType"] == "PER"

    def test_entity_body_canonical_name(self):
        b = entity_body("PER", name="Mr. B", canonical_name="Mr. Bennet")
        assert b.extra["palimpsest:canonicalName"] == "Mr. Bennet"

    def test_sentiment_body(self):
        b = sentiment_body(valence=0.75, arousal=0.3)
        assert b.type == "palimpsest:SentimentAnnotation"
        assert b.extra["palimpsest:valence"] == 0.75
        assert b.extra["palimpsest:model"] == "vader"

    def test_lexical_body(self):
        b = lexical_body(ttr=0.65, hapax_count=42, mean_word_length=4.8, yules_k=12.3)
        assert b.type == "palimpsest:LexicalAnnotation"
        assert b.extra["palimpsest:hapaxCount"] == 42

    def test_dialogue_body(self):
        b = dialogue_body(text="Hello there", quote_type="direct", speaker="Obi-Wan")
        assert b.type == "palimpsest:DialogueAnnotation"
        assert b.extra["palimpsest:speaker"] == "Obi-Wan"

    def test_dialogue_body_truncates_long_text(self):
        long_text = "x" * 300
        b = dialogue_body(text=long_text)
        assert len(b.value) == 200

    def test_topic_body(self):
        b = topic_body(topic_id=3, topic_weight=0.42, topic_terms=["love", "marriage", "family"])
        assert b.type == "palimpsest:TopicAnnotation"
        assert b.extra["palimpsest:topicTerms"] == ["love", "marriage", "family"]

    def test_coreference_body(self):
        b = coreference_body(chain_id="chain-1", referent_id="e001")
        assert b.type == "palimpsest:CoreferenceAnnotation"
        assert b.extra["palimpsest:chainId"] == "chain-1"

    def test_segment_body(self):
        b = segment_body(segment_type="paragraph", segment_index=5)
        assert b.type == "palimpsest:SegmentAnnotation"
        assert b.lfo_type == "structural.paragraph"

    def test_body_extra_key_collision_raises(self):
        with pytest.raises(ValueError, match="reserved keys"):
            Body(type="test", extra={"type": "OVERWRITE"})


class TestSerializer:
    def test_write_and_read_roundtrip(self, tmp_path):
        anns = [
            _make_annotation(
                body=entity_body("PER", name="Mr. Bennet"),
                target=Target(
                    source="urn:palimpsest:pp",
                    selector=TextPositionSelector(start=14, end=23),
                ),
            ),
            _make_annotation(
                body=entity_body("LOC", name="Hertfordshire", lfo_type="entity.place"),
                target=Target(
                    source="urn:palimpsest:pp",
                    selector=TextPositionSelector(start=100, end=113),
                ),
            ),
        ]
        path = tmp_path / "entities.jsonl"
        write_track(path, anns)

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2

        for line in lines:
            data = json.loads(line)
            assert data["type"] == "Annotation"

        restored = read_track(path)
        assert len(restored) == 2
        assert restored[0].body.value == "Mr. Bennet"
        assert restored[1].body.value == "Hertfordshire"

    def test_write_sorts_by_offset(self, tmp_path):
        ann_late = _make_annotation(
            target=Target(source="urn:test", selector=TextPositionSelector(start=100, end=110))
        )
        ann_early = _make_annotation(
            target=Target(source="urn:test", selector=TextPositionSelector(start=10, end=20))
        )
        path = tmp_path / "test.jsonl"
        write_track(path, [ann_late, ann_early])

        restored = read_track(path)
        assert restored[0].target.selector.start == 10
        assert restored[1].target.selector.start == 100

    def test_write_creates_parent_dir(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "test.jsonl"
        write_track(path, [_make_annotation()])
        assert path.exists()

    def test_read_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        assert read_track(path) == []

    def test_read_malformed_line_raises(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text("not valid json\n")
        with pytest.raises(ValueError, match="Invalid annotation at line 1"):
            read_track(path)

    def test_write_rejects_text_quote_selector(self, tmp_path):
        ann = _make_annotation(
            target=Target(source="urn:test", selector=TextQuoteSelector(exact="hello")),
        )
        path = tmp_path / "test.jsonl"
        with pytest.raises(TypeError, match="TextPositionSelector"):
            write_track(path, [ann])


class TestValidation:
    def test_valid_annotation_no_errors(self):
        ann = _make_annotation()
        errors = validate_annotation(ann.to_jsonld())
        assert errors == []

    def test_missing_context(self):
        ann = _make_annotation()
        jld = ann.to_jsonld()
        del jld["@context"]
        errors = validate_annotation(jld)
        assert any("context" in e.lower() for e in errors)

    def test_missing_id(self):
        ann = _make_annotation()
        jld = ann.to_jsonld()
        del jld["id"]
        errors = validate_annotation(jld)
        assert any("id" in e.lower() for e in errors)

    def test_missing_body(self):
        data = {
            "@context": DEFAULT_CONTEXT,
            "type": "Annotation",
            "id": "x",
            "target": {"source": "x", "selector": {}},
            "creator": {"name": "x"},
            "palimpsest:evidenceLevel": "E4",
            "palimpsest:confidence": 0.5,
        }
        errors = validate_annotation(data)
        assert any("body" in e.lower() for e in errors)

    def test_missing_evidence_level(self):
        ann = _make_annotation()
        jld = ann.to_jsonld()
        del jld["palimpsest:evidenceLevel"]
        errors = validate_annotation(jld)
        assert any("evidencelevel" in e.lower().replace(" ", "").replace("_", "") for e in errors)

    def test_missing_confidence(self):
        ann = _make_annotation()
        jld = ann.to_jsonld()
        del jld["palimpsest:confidence"]
        errors = validate_annotation(jld)
        assert any("confidence" in e.lower() for e in errors)

    def test_invalid_evidence_level(self):
        ann = _make_annotation()
        jld = ann.to_jsonld()
        jld["palimpsest:evidenceLevel"] = "E99"
        errors = validate_annotation(jld)
        assert any("evidence" in e.lower() for e in errors)

    def test_confidence_out_of_range(self):
        ann = _make_annotation()
        jld = ann.to_jsonld()
        jld["palimpsest:confidence"] = 1.5
        errors = validate_annotation(jld)
        assert any("range" in e.lower() for e in errors)

    def test_selector_start_greater_than_end(self):
        ann = _make_annotation()
        jld = ann.to_jsonld()
        jld["target"]["selector"]["start"] = 100
        jld["target"]["selector"]["end"] = 10
        errors = validate_annotation(jld)
        assert any("start" in e.lower() for e in errors)
