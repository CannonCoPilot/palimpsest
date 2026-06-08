"""Project directory management for Palimpsest.

A Project represents a single ingested text with its metadata,
reference text, track outputs, and signal outputs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from palimpsest import __version__
from palimpsest.annotation.bodies import segment_body
from palimpsest.annotation.model import Annotation, Creator, Target, TextPositionSelector
from palimpsest.annotation.serializer import write_track
from palimpsest.ingest.extractor import extract_text
from palimpsest.ingest.normalizer import (
    compute_sha256,
    count_characters,
    count_words,
    normalize,
)
from palimpsest.ingest.segmenter import segment_paragraphs, segment_sections, segment_sentences

_SUBDIRS = [
    "tracks",
    "signals",
    "manifests",
    "cache",
    "x-config/schemas",
    "x-config/detectors",
    "exports",
]


@dataclass
class ProjectMetadata:
    id: str
    title: str
    language: str
    source_format: str
    source_file: str
    ingest_date: str
    palimpsest_version: str
    reference_sha256: str
    word_count: int
    paragraph_count: int
    section_count: int
    sentence_count: int
    character_count: int
    author: str = ""
    year: int = 0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "language": self.language,
            "source_format": self.source_format,
            "source_file": self.source_file,
            "ingest_date": self.ingest_date,
            "palimpsest_version": self.palimpsest_version,
            "reference_sha256": self.reference_sha256,
            "word_count": self.word_count,
            "paragraph_count": self.paragraph_count,
            "section_count": self.section_count,
            "sentence_count": self.sentence_count,
            "character_count": self.character_count,
        }
        d["author"] = self.author
        d["year"] = self.year
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProjectMetadata:
        return cls(
            id=d["id"],
            title=d["title"],
            language=d.get("language", "en"),
            source_format=d["source_format"],
            source_file=d["source_file"],
            ingest_date=d["ingest_date"],
            palimpsest_version=d["palimpsest_version"],
            reference_sha256=d["reference_sha256"],
            word_count=d["word_count"],
            paragraph_count=d["paragraph_count"],
            section_count=d["section_count"],
            sentence_count=d.get("sentence_count", 0),
            character_count=d.get("character_count", 0),
            author=d.get("author", ""),
            year=d.get("year", 0),
        )


def _make_slug(name: str) -> str:
    """Create a URL-safe slug from a filename or title."""
    stem = Path(name).stem
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower())
    return slug.strip("-")


class Project:
    """Represents a Palimpsest project directory."""

    def __init__(self, path: Path, metadata: ProjectMetadata) -> None:
        self.path = path
        self.metadata = metadata

    def reference_text(self) -> str:
        return (self.path / "reference.txt").read_text(encoding="utf-8")

    def paragraphs(self) -> list[tuple[int, int, str]]:
        """Return (start, end, text) for each paragraph."""
        text = self.reference_text()
        segs = segment_paragraphs(text)
        return [(s.start, s.end, s.text) for s in segs]

    def sections(self) -> list[tuple[int, int, str]]:
        """Return (start, end, heading_text) for each section."""
        text = self.reference_text()
        segs = segment_sections(text)
        return [(s.start, s.end, s.text) for s in segs]

    @classmethod
    def load(cls, path: Path) -> Project:
        meta_path = path / "metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"No metadata.json in {path}")
        meta = ProjectMetadata.from_dict(json.loads(meta_path.read_text()))
        return cls(path=path, metadata=meta)


def ingest_file(
    source_path: Path,
    workspace: Path,
    title: str = "",
    author: str = "",
    year: int = 0,
    language: str = "en",
) -> Project:
    """Ingest a text file into a new project directory."""
    raw_text = extract_text(source_path)
    normalized = normalize(raw_text)
    sha = compute_sha256(normalized)
    slug = _make_slug(title or source_path.name)
    project_dir = workspace / slug

    if project_dir.exists():
        raise FileExistsError(f"Project already exists: {project_dir}")

    for subdir in _SUBDIRS:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)

    (project_dir / "reference.txt").write_text(normalized, encoding="utf-8")
    (project_dir / "reference.sha256").write_text(sha)

    paras = segment_paragraphs(normalized)
    sections = segment_sections(normalized)
    sentences = segment_sentences(normalized)

    metadata = ProjectMetadata(
        id=slug,
        title=title or source_path.stem.replace("-", " ").replace("_", " ").title(),
        language=language,
        source_format=source_path.suffix.lstrip(".").lower(),
        source_file=source_path.name,
        ingest_date=datetime.now(UTC).strftime("%Y-%m-%d"),
        palimpsest_version=__version__,
        reference_sha256=sha,
        word_count=count_words(normalized),
        paragraph_count=len(paras),
        section_count=len(sections),
        sentence_count=len(sentences),
        character_count=count_characters(normalized),
        author=author,
        year=year,
    )

    (project_dir / "metadata.json").write_text(
        json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    source_urn = f"urn:palimpsest:{slug}"
    seg_annotations: list[Annotation] = []
    for seg in paras:
        seg_annotations.append(
            Annotation(
                body=segment_body(segment_type="paragraph", segment_index=seg.index),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=seg.start, end=seg.end),
                ),
                creator=Creator(name="palimpsest-segmenter/0.1"),
                confidence=1.0,
                evidence_level="E1",
                project_id=slug,
                track_name="segments",
            )
        )
    for seg in sections:
        seg_annotations.append(
            Annotation(
                body=segment_body(segment_type="section", segment_index=seg.index),
                target=Target(
                    source=source_urn,
                    selector=TextPositionSelector(start=seg.start, end=seg.end),
                ),
                creator=Creator(name="palimpsest-segmenter/0.1"),
                confidence=1.0,
                evidence_level="E1",
                project_id=slug,
                track_name="segments",
            )
        )

    write_track(project_dir / "tracks" / "segments.jsonl", seg_annotations)

    manifest_dir = project_dir / "manifests"
    manifest_dir.mkdir(exist_ok=True)
    (manifest_dir / "segments.manifest.json").write_text(
        json.dumps({
            "trackName": "segments",
            "bodyType": "palimpsest:SegmentAnnotation",
            "colorScheme": {"primary": "#95a5a6", "secondary": "#bdc3c7"},
            "textViewRendering": "none",
            "overviewBarRendering": {"type": "none"},
            "evidenceLevel": "E1",
        }, indent=2),
        encoding="utf-8",
    )

    project = Project(path=project_dir, metadata=metadata)
    return project
