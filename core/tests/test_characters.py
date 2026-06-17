"""Tests for the character/entity index builder (pure JSONL → index logic)."""

from __future__ import annotations

import json
from pathlib import Path

from palimpsest.characters import (
    _find_paragraph,
    _map_entity_type,
    _normalize_name,
    build_character_index,
    compute_cooccurrence,
)

PARAGRAPHS = [
    {"start": 0, "end": 50},
    {"start": 50, "end": 120},
    {"start": 120, "end": 200},
]


def _write_tracks(project_dir: Path, coref: list[dict] | None = None,
                  entities: list[dict] | None = None) -> None:
    tracks = project_dir / "tracks"
    tracks.mkdir(parents=True, exist_ok=True)
    if coref is not None:
        (tracks / "coreference.jsonl").write_text(
            "\n".join(json.dumps(a) for a in coref) + "\n"
        )
    if entities is not None:
        (tracks / "entities.jsonl").write_text(
            "\n".join(json.dumps(a) for a in entities) + "\n"
        )


def _entity(value: str, etype: str, start: int, end: int) -> dict:
    return {
        "body": {"value": value, "palimpsest:entityType": etype},
        "target": {"selector": {"start": start, "end": end}},
    }


def _coref(chain_id: str, referent: str, mention_type: str, start: int, end: int) -> dict:
    return {
        "body": {
            "palimpsest:chainId": chain_id,
            "palimpsest:referentId": referent,
            "palimpsest:mentionType": mention_type,
        },
        "target": {"selector": {"start": start, "end": end}},
    }


class TestNormalizeName:
    def test_multiword_capitalizes_and_drops_articles(self):
        assert _normalize_name("the bennet family") == "Bennet Family"

    def test_single_word_capitalizes(self):
        assert _normalize_name("darcy") == "Darcy"

    def test_strips_whitespace(self):
        assert _normalize_name("  elizabeth  bennet ") == "Elizabeth Bennet"


class TestMapEntityType:
    def test_known_types(self):
        assert _map_entity_type("PERSON") == "person"
        assert _map_entity_type("ORG") == "organization"
        assert _map_entity_type("GPE") == "place"
        assert _map_entity_type("NORP") == "group"

    def test_unknown_type_is_other(self):
        assert _map_entity_type("WORK_OF_ART") == "other"


class TestFindParagraph:
    def test_offset_inside_range(self):
        assert _find_paragraph(60, PARAGRAPHS) == 1

    def test_offset_at_boundary_is_start_inclusive(self):
        assert _find_paragraph(50, PARAGRAPHS) == 1

    def test_offset_out_of_range_returns_minus_one(self):
        assert _find_paragraph(999, PARAGRAPHS) == -1


class TestBuildCharacterIndexEmpty:
    def test_no_track_files_returns_empty(self, tmp_path):
        assert build_character_index(tmp_path, PARAGRAPHS) == []

    def test_blank_lines_are_skipped(self, tmp_path):
        (tmp_path / "tracks").mkdir()
        (tmp_path / "tracks" / "entities.jsonl").write_text("\n\n")
        assert build_character_index(tmp_path, PARAGRAPHS) == []


class TestBuildCharacterIndexEntities:
    def test_builds_character_from_entity(self, tmp_path):
        _write_tracks(tmp_path, entities=[_entity("Darcy", "PERSON", 10, 15)])
        chars = build_character_index(tmp_path, PARAGRAPHS)
        assert len(chars) == 1
        c = chars[0]
        assert c["canonicalName"] == "Darcy"
        assert c["type"] == "person"
        assert c["aliases"] == ["Darcy"]
        assert c["mentionCount"] == 1
        assert c["firstOccurrence"] == 10
        assert c["lastOccurrence"] == 10
        assert c["paragraphIndices"] == [0]  # offset 10 falls in paragraph 0

    def test_filters_unwanted_entity_types(self, tmp_path):
        _write_tracks(tmp_path, entities=[
            _entity("Darcy", "PERSON", 10, 15),
            _entity("1813", "DATE", 20, 24),  # filtered out
        ])
        chars = build_character_index(tmp_path, PARAGRAPHS)
        assert [c["canonicalName"] for c in chars] == ["Darcy"]

    def test_short_value_skipped(self, tmp_path):
        _write_tracks(tmp_path, entities=[_entity("X", "PERSON", 10, 11)])
        assert build_character_index(tmp_path, PARAGRAPHS) == []

    def test_mention_without_offsets_skipped(self, tmp_path):
        ann = _entity("Darcy", "PERSON", 10, 15)
        ann["target"]["selector"] = {}  # no start/end
        _write_tracks(tmp_path, entities=[ann])
        assert build_character_index(tmp_path, PARAGRAPHS) == []

    def test_density_array_matches_paragraph_count(self, tmp_path):
        _write_tracks(tmp_path, entities=[
            _entity("Darcy", "PERSON", 10, 15),
            _entity("Darcy", "PERSON", 60, 65),
            _entity("Darcy", "PERSON", 70, 75),
        ])
        c = build_character_index(tmp_path, PARAGRAPHS)[0]
        assert len(c["density"]) == len(PARAGRAPHS)
        assert c["density"] == [1, 2, 0]
        assert c["mentionCount"] == 3

    def test_sorted_by_mention_count_desc(self, tmp_path):
        _write_tracks(tmp_path, entities=[
            _entity("Darcy", "PERSON", 10, 15),
            _entity("Bingley", "PERSON", 20, 27),
            _entity("Bingley", "PERSON", 60, 67),
        ])
        chars = build_character_index(tmp_path, PARAGRAPHS)
        assert [c["canonicalName"] for c in chars] == ["Bingley", "Darcy"]


class TestBuildCharacterIndexCoreference:
    def test_chain_builds_person_with_aliases(self, tmp_path):
        _write_tracks(tmp_path, coref=[
            _coref("c1", "Elizabeth Bennet", "prop", 10, 25),
            _coref("c1", "she", "pron", 60, 63),
        ])
        chars = build_character_index(tmp_path, PARAGRAPHS)
        assert len(chars) == 1
        c = chars[0]
        assert c["canonicalName"] == "Elizabeth Bennet"
        assert c["type"] == "person"
        assert "Elizabeth Bennet" in c["aliases"]  # prop mention adds alias
        assert c["mentionCount"] == 2  # both the prop and pron mentions counted

    def test_entity_and_chain_merge_on_canonical_name(self, tmp_path):
        _write_tracks(
            tmp_path,
            coref=[_coref("c1", "Darcy", "prop", 10, 15)],
            entities=[_entity("Darcy", "PERSON", 60, 65)],
        )
        chars = build_character_index(tmp_path, PARAGRAPHS)
        assert len(chars) == 1
        assert chars[0]["mentionCount"] == 2


class TestCooccurrence:
    def test_shared_paragraph_counts_and_symmetry(self):
        characters = [
            {"canonicalName": "A", "paragraphIndices": [0, 1, 2]},
            {"canonicalName": "B", "paragraphIndices": [1, 2]},
            {"canonicalName": "C", "paragraphIndices": [3]},
        ]
        result = compute_cooccurrence(characters)
        assert result["names"] == ["A", "B", "C"]
        m = result["matrix"]
        assert m[0][1] == 2  # A & B share paragraphs 1, 2
        assert m[0][1] == m[1][0]  # symmetric
        assert m[0][2] == 0  # A & C share nothing
        assert m[0][0] == 3  # diagonal = own paragraph count

    def test_top_n_limits_characters(self):
        characters = [
            {"canonicalName": str(i), "paragraphIndices": [i]} for i in range(30)
        ]
        result = compute_cooccurrence(characters, top_n=5)
        assert len(result["names"]) == 5
        assert len(result["matrix"]) == 5
