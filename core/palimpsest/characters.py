"""Character/entity index builder — groups coreference chains + entity annotations."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def build_character_index(project_dir: Path, paragraphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build character index from coreference + entity tracks."""
    coref_path = project_dir / "tracks" / "coreference.jsonl"
    entity_path = project_dir / "tracks" / "entities.jsonl"

    chains: dict[str, list[dict]] = defaultdict(list)
    entity_anns: list[dict] = []

    if coref_path.exists():
        for line in coref_path.read_text().strip().split("\n"):
            if not line:
                continue
            ann = json.loads(line)
            chain_id = ann.get("body", {}).get("palimpsest:chainId", "")
            if chain_id:
                chains[chain_id].append(ann)

    if entity_path.exists():
        for line in entity_path.read_text().strip().split("\n"):
            if not line:
                continue
            ann = json.loads(line)
            entity_type = ann.get("body", {}).get("palimpsest:entityType", "")
            if entity_type in ("PERSON", "ORG", "GPE", "LOC", "FAC", "NORP"):
                entity_anns.append(ann)

    characters: dict[str, dict[str, Any]] = {}

    for chain_id, mentions in chains.items():
        referent_id = mentions[0].get("body", {}).get("palimpsest:referentId", f"Chain {chain_id}")
        canonical = _normalize_name(referent_id)

        if canonical not in characters:
            characters[canonical] = {
                "canonicalName": canonical,
                "aliases": set(),
                "type": "person",
                "mentions": [],
                "chainIds": set(),
            }

        char = characters[canonical]
        char["chainIds"].add(chain_id)

        for m in mentions:
            sel = m.get("target", {}).get("selector", {})
            start = sel.get("start")
            end = sel.get("end")
            if start is None or end is None:
                continue

            mention_type = m.get("body", {}).get("palimpsest:mentionType", "")
            ref_text = m.get("body", {}).get("palimpsest:referentId", "")
            if mention_type == "prop" and ref_text:
                char["aliases"].add(ref_text.strip())

            para_idx = _find_paragraph(start, paragraphs)
            char["mentions"].append({
                "start": start,
                "end": end,
                "paragraphIndex": para_idx,
                "mentionType": mention_type,
            })

    for ann in entity_anns:
        body = ann.get("body", {})
        value = body.get("value", "").strip()
        if not value or len(value) < 2:
            continue

        entity_type = body.get("palimpsest:entityType", "")
        canonical = _normalize_name(value)

        sel = ann.get("target", {}).get("selector", {})
        start = sel.get("start")
        end = sel.get("end")
        if start is None or end is None:
            continue

        if canonical not in characters:
            characters[canonical] = {
                "canonicalName": canonical,
                "aliases": set(),
                "type": _map_entity_type(entity_type),
                "mentions": [],
                "chainIds": set(),
            }

        char = characters[canonical]
        char["aliases"].add(value)
        para_idx = _find_paragraph(start, paragraphs)
        char["mentions"].append({
            "start": start,
            "end": end,
            "paragraphIndex": para_idx,
            "mentionType": "name",
        })

    result = []
    for char in characters.values():
        mentions = char["mentions"]
        if not mentions:
            continue

        mentions.sort(key=lambda m: m["start"])
        para_indices = sorted(set(m["paragraphIndex"] for m in mentions if m["paragraphIndex"] >= 0))

        density = [0] * len(paragraphs)
        for m in mentions:
            pi = m["paragraphIndex"]
            if 0 <= pi < len(density):
                density[pi] += 1

        result.append({
            "canonicalName": char["canonicalName"],
            "aliases": sorted(char["aliases"]),
            "type": char["type"],
            "mentionCount": len(mentions),
            "firstOccurrence": mentions[0]["start"],
            "lastOccurrence": mentions[-1]["start"],
            "firstParagraph": para_indices[0] if para_indices else 0,
            "lastParagraph": para_indices[-1] if para_indices else 0,
            "paragraphIndices": para_indices,
            "density": density,
        })

    result.sort(key=lambda c: c["mentionCount"], reverse=True)
    return result


def compute_cooccurrence(characters: list[dict[str, Any]], top_n: int = 20) -> dict[str, Any]:
    """Compute character co-occurrence matrix."""
    top = characters[:top_n]
    names = [c["canonicalName"] for c in top]
    n = len(names)
    matrix = [[0] * n for _ in range(n)]

    para_sets = []
    for c in top:
        para_sets.append(set(c["paragraphIndices"]))

    for i in range(n):
        for j in range(i, n):
            shared = len(para_sets[i] & para_sets[j])
            matrix[i][j] = shared
            matrix[j][i] = shared

    return {"names": names, "matrix": matrix}


def _normalize_name(name: str) -> str:
    name = name.strip()
    words = name.split()
    if len(words) > 1:
        return " ".join(w.capitalize() for w in words if w.lower() not in ("the", "a", "an"))
    return name.capitalize()


def _map_entity_type(etype: str) -> str:
    mapping = {"PERSON": "person", "ORG": "organization", "GPE": "place", "LOC": "place", "FAC": "place", "NORP": "group"}
    return mapping.get(etype, "other")


def _find_paragraph(char_offset: int, paragraphs: list[dict[str, Any]]) -> int:
    for i, p in enumerate(paragraphs):
        if p.get("start", 0) <= char_offset < p.get("end", 0):
            return i
    return -1
