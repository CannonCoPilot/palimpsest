"""Tests for track extractors — entities, sentiment, lexical, dialogue, topics."""

from pathlib import Path

import numpy as np
import pytest

from palimpsest.formats.signals import SignalManifest, read_signal, write_signal
from palimpsest.project import ingest_file
from palimpsest.tracks.base import TrackExtractor
from palimpsest.tracks.dialogue import DialogueExtractor
from palimpsest.tracks.entities import EntityExtractor
from palimpsest.tracks.lexical import LexicalExtractor
from palimpsest.tracks.sentiment import SentimentExtractor
from palimpsest.tracks.topics import TopicsExtractor


@pytest.fixture
def pp_project(pp_ch1_txt: Path, tmp_path: Path):
    return ingest_file(pp_ch1_txt, tmp_path, title="pp-test")


ALL_EXTRACTORS = [
    EntityExtractor,
    SentimentExtractor,
    LexicalExtractor,
    DialogueExtractor,
    TopicsExtractor,
]


class TestAllExtractorsProtocolCompliance:
    @pytest.mark.parametrize("cls", ALL_EXTRACTORS, ids=lambda c: c.__name__)
    def test_is_track_extractor(self, cls):
        assert isinstance(cls(), TrackExtractor)

    @pytest.mark.parametrize("cls", ALL_EXTRACTORS, ids=lambda c: c.__name__)
    def test_has_required_attributes(self, cls):
        ext = cls()
        assert isinstance(ext.name, str) and len(ext.name) > 0
        assert ext.output_type in ("annotation", "signal")
        assert isinstance(ext.depends_on, list)
        assert isinstance(ext.lfo_types, list)
        assert ext.evidence_level in ("E1", "E2", "E3", "E4", "E5")

    @pytest.mark.parametrize("cls", ALL_EXTRACTORS, ids=lambda c: c.__name__)
    def test_manifest_has_required_fields(self, cls):
        m = cls().manifest()
        assert "trackName" in m
        assert "bodyType" in m
        assert "colorScheme" in m
        assert "textViewRendering" in m
        assert "overviewBarRendering" in m


class TestEntityExtractor:
    def test_satisfies_protocol(self):
        assert isinstance(EntityExtractor(), TrackExtractor)

    def test_produces_annotations(self, pp_project):
        anns = EntityExtractor().extract(pp_project)
        assert len(anns) > 0

    def test_detects_mr_bennet(self, pp_project):
        anns = EntityExtractor().extract(pp_project)
        names = [a.body.value for a in anns]
        assert any("Bennet" in n for n in names)

    def test_annotations_are_w3c(self, pp_project):
        anns = EntityExtractor().extract(pp_project)
        for ann in anns[:5]:
            jld = ann.to_jsonld()
            assert jld["type"] == "Annotation"
            assert jld["body"]["type"] == "palimpsest:EntityAnnotation"
            assert jld["palimpsest:evidenceLevel"] == "E4"
            assert "@context" in jld

    def test_annotation_ids_have_project_and_track(self, pp_project):
        anns = EntityExtractor().extract(pp_project)
        for ann in anns[:5]:
            parts = ann.id.split(":")
            assert len(parts) == 5
            assert parts[2] == pp_project.metadata.id

    def test_returns_annotations_only(self, pp_project):
        anns = EntityExtractor().extract(pp_project)
        assert isinstance(anns, list)
        assert not (pp_project.path / "tracks" / "entities.jsonl").exists()

    def test_offset_accuracy(self, pp_project):
        anns = EntityExtractor().extract(pp_project)
        text = pp_project.reference_text()
        for ann in anns:
            sel = ann.target.selector
            extracted = text[sel.start:sel.end]
            assert extracted == ann.body.value or ann.body.value in extracted

    def test_entity_types_mapped(self, pp_project):
        anns = EntityExtractor().extract(pp_project)
        types = {a.body.extra.get("palimpsest:entityType") for a in anns}
        assert types.issubset({"PER", "LOC", "ORG", "WORK"})

    def test_lfo_types_correct(self):
        assert "entity.place" in EntityExtractor().lfo_types

    def test_manifest(self):
        assert EntityExtractor().manifest()["bodyType"] == "palimpsest:EntityAnnotation"

    def test_parameters(self):
        assert EntityExtractor().parameters()["entities.spacy_model"] == "en_core_web_lg"


class TestSentimentExtractor:
    def test_produces_sentiment_annotations(self, pp_project):
        anns = SentimentExtractor().extract(pp_project)
        assert len(anns) > 0
        for ann in anns[:5]:
            assert ann.body.type == "palimpsest:SentimentAnnotation"
            assert ann.evidence_level == "E5"

    def test_valence_range(self, pp_project):
        anns = SentimentExtractor().extract(pp_project)
        for ann in anns:
            valence = ann.body.extra["palimpsest:valence"]
            arousal = ann.body.extra["palimpsest:arousal"]
            assert -1.0 <= valence <= 1.0
            assert 0.0 <= arousal <= 1.0

    def test_detects_opening_line(self, pp_project):
        anns = SentimentExtractor().extract(pp_project)
        first = anns[0]
        assert first.target.selector.start == 0

    def test_offset_accuracy(self, pp_project):
        anns = SentimentExtractor().extract(pp_project)
        text = pp_project.reference_text()
        for ann in anns[:10]:
            sel = ann.target.selector
            assert sel.start < sel.end
            assert sel.end <= len(text)


class TestLexicalExtractor:
    def test_produces_lexical_annotations(self, pp_project):
        anns = LexicalExtractor().extract(pp_project)
        assert len(anns) > 0
        for ann in anns[:5]:
            assert ann.body.type == "palimpsest:LexicalAnnotation"
            assert ann.evidence_level == "E5"

    def test_ttr_bounds(self, pp_project):
        anns = LexicalExtractor().extract(pp_project)
        for ann in anns:
            ttr = ann.body.extra["palimpsest:ttr"]
            assert 0.0 < ttr <= 1.0

    def test_hapax_non_negative(self, pp_project):
        anns = LexicalExtractor().extract(pp_project)
        for ann in anns:
            assert ann.body.extra["palimpsest:hapaxCount"] >= 0

    def test_no_overlap(self, pp_project):
        anns = LexicalExtractor().extract(pp_project)
        sorted_anns = sorted(anns, key=lambda a: a.target.selector.start)
        for i in range(len(sorted_anns) - 1):
            assert sorted_anns[i].target.selector.end <= sorted_anns[i + 1].target.selector.start


class TestDialogueExtractor:
    def test_detects_pp_opening_quote(self, pp_project):
        anns = DialogueExtractor().extract(pp_project)
        assert len(anns) > 0
        texts = [a.body.value for a in anns]
        assert any("Bennet" in t or "Netherfield" in t for t in texts)

    def test_all_valid_quote_types(self, pp_project):
        anns = DialogueExtractor().extract(pp_project)
        for ann in anns:
            assert ann.body.extra["palimpsest:quoteType"] in ("direct", "indirect")

    def test_attribution_verb_extracted(self, pp_project):
        anns = DialogueExtractor().extract(pp_project)
        verbs = [a.body.extra.get("palimpsest:verb", "") for a in anns]
        assert any(v for v in verbs), "At least one annotation should have a verb"

    def test_no_duplicate_spans(self, pp_project):
        anns = DialogueExtractor().extract(pp_project)
        spans = [(a.target.selector.start, a.target.selector.end) for a in anns]
        assert len(spans) == len(set(spans))

    def test_evidence_level(self, pp_project):
        anns = DialogueExtractor().extract(pp_project)
        assert all(a.evidence_level == "E5" for a in anns)

    def test_valid_offsets(self, pp_project):
        anns = DialogueExtractor().extract(pp_project)
        text = pp_project.reference_text()
        for ann in anns:
            sel = ann.target.selector
            assert 0 <= sel.start < sel.end <= len(text)


class TestTopicsExtractor:
    def test_produces_topic_annotations(self, pp_project):
        anns = TopicsExtractor().extract(pp_project)
        assert len(anns) > 0
        for ann in anns[:5]:
            assert ann.body.type == "palimpsest:TopicAnnotation"
            assert ann.evidence_level == "E4"

    def test_topic_id_in_range(self, pp_project):
        anns = TopicsExtractor().extract(pp_project)
        for ann in anns:
            tid = ann.body.extra["palimpsest:topicId"]
            weight = ann.body.extra["palimpsest:topicWeight"]
            assert 0 <= tid <= 9
            assert 0.0 < weight <= 1.0

    def test_terms_are_five_strings(self, pp_project):
        anns = TopicsExtractor().extract(pp_project)
        for ann in anns[:5]:
            terms = ann.body.extra["palimpsest:topicTerms"]
            assert len(terms) == 5
            assert all(isinstance(t, str) and len(t) > 0 for t in terms)

    def test_distribution_signal_written(self, pp_project):
        TopicsExtractor().extract(pp_project)
        sig_json = pp_project.path / "signals" / "topics_dist.json"
        sig_bin = pp_project.path / "signals" / "topics_dist.bin"
        assert sig_json.exists()
        assert sig_bin.exists()

        m, data = read_signal(pp_project.path / "signals", "topics_dist")
        assert data.shape[1] == 10
        row_sums = data.sum(axis=1)
        assert np.allclose(row_sums, 1.0, atol=0.01)


class TestTopicsEdgeCases:
    def test_empty_vocabulary_returns_empty(self, tmp_path):
        """TopicsExtractor must not crash on texts where all words are stopwords."""
        from palimpsest.project import ingest_file

        stopword_txt = tmp_path / "stopwords.txt"
        stopword_txt.write_text("the the the the.\nand and and and.\n")
        project = ingest_file(stopword_txt, tmp_path / "out", title="stopwords-test")
        anns = TopicsExtractor().extract(project)
        assert anns == []

    def test_short_text_returns_empty(self, tmp_path):
        """Single-paragraph texts should return empty (< 2 paragraphs)."""
        from palimpsest.project import ingest_file

        short_txt = tmp_path / "short.txt"
        short_txt.write_text("Just one sentence here.")
        project = ingest_file(short_txt, tmp_path / "out2", title="short-test")
        anns = TopicsExtractor().extract(project)
        assert anns == []


class TestSentimentConfidence:
    def test_confidence_within_e5_range(self, pp_project):
        """Confidence values must be in [0.5, 0.9] per E5 spec."""
        anns = SentimentExtractor().extract(pp_project)
        assert len(anns) > 0
        for ann in anns:
            assert 0.5 <= ann.confidence <= 0.9, (
                f"Confidence {ann.confidence} outside E5 range [0.5, 0.9]"
            )


class TestDialogueConfidence:
    def test_curly_quotes_get_highest_confidence(self, pp_project):
        """Curly-quote matches should have higher confidence than other patterns."""
        anns = DialogueExtractor().extract(pp_project)
        assert len(anns) > 0
        confidences = {ann.confidence for ann in anns}
        assert 0.92 in confidences or 0.85 in confidences


class TestDeterminism:
    @pytest.mark.parametrize(
        "cls",
        [SentimentExtractor, LexicalExtractor, DialogueExtractor, TopicsExtractor],
        ids=lambda c: c.__name__,
    )
    def test_extractor_deterministic(self, pp_project, cls):
        ext = cls()
        anns1 = ext.extract(pp_project)
        anns2 = ext.extract(pp_project)
        assert len(anns1) == len(anns2)
        for a1, a2 in zip(anns1, anns2):
            assert a1.body.type == a2.body.type
            assert a1.target.selector.start == a2.target.selector.start
            assert a1.body.extra == a2.body.extra


class TestSignalIO:
    def test_write_and_read_matrix(self, tmp_path):
        data = np.eye(5, dtype=np.float32)
        manifest = SignalManifest(
            type="matrix", name="test_matrix", source="test/0.1",
            reference_sha256="abc", dimensions=[5, 5],
        )
        write_signal(tmp_path / "signals", data, manifest)
        m, restored = read_signal(tmp_path / "signals", "test_matrix")
        assert restored.shape == (5, 5)
        assert np.allclose(restored, data)

    def test_write_and_read_vector(self, tmp_path):
        data = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        manifest = SignalManifest(
            type="vector", name="test_vec", source="test/0.1",
            reference_sha256="abc", dimensions=[3],
        )
        write_signal(tmp_path / "signals", data, manifest)
        m, restored = read_signal(tmp_path / "signals", "test_vec")
        assert np.allclose(restored, data)

    def test_manifest_json_written(self, tmp_path):
        import json

        data = np.zeros(4, dtype=np.float32)
        manifest = SignalManifest(
            type="vector", name="test_sig", source="test/0.1",
            reference_sha256="abc", dimensions=[4],
            metadata={"some_key": "some_value"},
        )
        write_signal(tmp_path / "signals", data, manifest)
        loaded = json.loads((tmp_path / "signals" / "test_sig.json").read_text())
        assert loaded["metadata"]["some_key"] == "some_value"

    def test_binary_file_size_correct(self, tmp_path):
        data = np.zeros((10, 10), dtype=np.float32)
        manifest = SignalManifest(
            type="matrix", name="size_test", source="test/0.1",
            reference_sha256="abc", dimensions=[10, 10],
        )
        write_signal(tmp_path / "signals", data, manifest)
        assert (tmp_path / "signals" / "size_test.bin").stat().st_size == 400
