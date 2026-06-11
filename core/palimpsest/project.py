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
from palimpsest.annotation.bodies import endnote_body, section_body, segment_body
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
        self._text_cache: str | None = None
        self._para_cache: list[tuple[int, int, str]] | None = None
        self._para_starts: list[int] | None = None
        self._spacy_doc_cache: Any | None = None

    def reference_text(self) -> str:
        if self._text_cache is None:
            self._text_cache = (self.path / "reference.txt").read_text(encoding="utf-8")
        return self._text_cache

    def paragraphs(self) -> list[tuple[int, int, str]]:
        """Return (start, end, text) for each paragraph."""
        if self._para_cache is None:
            text = self.reference_text()
            segs = segment_paragraphs(text)
            self._para_cache = [(s.start, s.end, s.text) for s in segs]
            self._para_starts = [s.start for s in segs]
        return self._para_cache

    def find_paragraph(self, char_offset: int) -> int:
        """Return paragraph index for a character offset. O(log n) via bisect."""
        from bisect import bisect_right
        if self._para_starts is None:
            self.paragraphs()
        assert self._para_starts is not None
        idx = bisect_right(self._para_starts, char_offset) - 1
        return max(0, idx)

    def spacy_doc(self, model: str = "en_core_web_lg") -> Any:
        """Return a cached spaCy Doc for the reference text."""
        if self._spacy_doc_cache is None:
            import spacy
            try:
                nlp = spacy.load(model)
            except OSError:
                nlp = spacy.load("en_core_web_sm")
            text = self.reference_text()
            nlp.max_length = len(text) + 1000
            self._spacy_doc_cache = nlp(text)
        return self._spacy_doc_cache

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
    is_epub = source_path.suffix.lower() == ".epub"
    epub_result = None

    if is_epub:
        from palimpsest.ingest.epub_parser import parse_epub
        epub_result = parse_epub(source_path)
        raw_text = epub_result.text
        if not title and epub_result.metadata.title:
            title = epub_result.metadata.title
        if not author and epub_result.metadata.author:
            author = epub_result.metadata.author
        if not language and epub_result.metadata.language:
            language = epub_result.metadata.language
    else:
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

    meta_dict: dict[str, Any] = {}
    if epub_result:
        meta_dict["isbn"] = epub_result.metadata.isbn
        meta_dict["publisher"] = epub_result.metadata.publisher
        meta_dict["pub_date"] = epub_result.metadata.date
        meta_dict["epub_uuid"] = epub_result.metadata.uuid
        meta_dict["endnote_count"] = len(epub_result.endnotes)
        meta_dict["epub_section_count"] = len(epub_result.sections)

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
        section_count=len(epub_result.sections) if epub_result and epub_result.sections else len(sections),
        sentence_count=len(sentences),
        character_count=count_characters(normalized),
        author=author,
        year=year,
    )

    full_meta = metadata.to_dict()
    full_meta.update(meta_dict)
    (project_dir / "metadata.json").write_text(
        json.dumps(full_meta, indent=2, ensure_ascii=False),
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

    for seg in sentences:
        seg_annotations.append(
            Annotation(
                body=segment_body(segment_type="sentence", segment_index=seg.index),
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

    if epub_result and epub_result.sections:
        section_anns: list[Annotation] = []
        for sec in epub_result.sections:
            end_offset = sec.offset + len(sec.heading_text)
            if end_offset > len(normalized):
                end_offset = len(normalized)
            section_anns.append(
                Annotation(
                    body=section_body(
                        heading_text=sec.heading_text,
                        heading_level=sec.heading_level,
                        section_index=sec.section_index,
                    ),
                    target=Target(
                        source=source_urn,
                        selector=TextPositionSelector(start=sec.offset, end=end_offset),
                    ),
                    creator=Creator(name="palimpsest-epub-parser/0.1"),
                    confidence=1.0,
                    evidence_level="E1",
                    project_id=slug,
                    track_name="sections",
                )
            )
        write_track(project_dir / "tracks" / "sections.jsonl", section_anns)

        (project_dir / "manifests" / "sections.manifest.json").write_text(
            json.dumps({
                "trackName": "sections",
                "bodyType": "palimpsest:SectionAnnotation",
                "colorScheme": {"primary": "#8e44ad", "secondary": "#9b59b6"},
                "textViewRendering": "margin-marker",
                "overviewBarRendering": {"type": "density-barcode", "color": "#8e44ad"},
                "evidenceLevel": "E1",
            }, indent=2),
            encoding="utf-8",
        )

    if epub_result and epub_result.endnotes:
        endnote_anns: list[Annotation] = []
        for en in epub_result.endnotes:
            if en.call_site_start >= 0 and en.call_site_end > en.call_site_start:
                start = min(en.call_site_start, len(normalized) - 1)
                end = min(en.call_site_end, len(normalized))
                endnote_anns.append(
                    Annotation(
                        body=endnote_body(
                            note_number=en.note_number,
                            note_text=en.note_text,
                            call_site_start=en.call_site_start,
                            call_site_end=en.call_site_end,
                        ),
                        target=Target(
                            source=source_urn,
                            selector=TextPositionSelector(start=start, end=end),
                        ),
                        creator=Creator(name="palimpsest-epub-parser/0.1"),
                        confidence=1.0,
                        evidence_level="E1",
                        project_id=slug,
                        track_name="endnotes",
                    )
                )
        if endnote_anns:
            write_track(project_dir / "tracks" / "endnotes.jsonl", endnote_anns)

            (project_dir / "manifests" / "endnotes.manifest.json").write_text(
                json.dumps({
                    "trackName": "endnotes",
                    "bodyType": "palimpsest:EndnoteAnnotation",
                    "colorScheme": {"primary": "#e74c3c", "secondary": "#c0392b"},
                    "textViewRendering": "superscript",
                    "overviewBarRendering": {"type": "density-barcode", "color": "#e74c3c"},
                    "evidenceLevel": "E1",
                }, indent=2),
                encoding="utf-8",
            )

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

    epub_section_offsets = (
        [[s.offset, s.offset + len(s.heading_text)] for s in epub_result.sections]
        if epub_result and epub_result.sections
        else [[s.start, s.end] for s in sections]
    )

    coordinates: dict[str, Any] = {
        "character_offset": {
            "type": "linear",
            "label": "Character Offset",
            "total": count_characters(normalized),
        },
        "paragraph_index": {
            "type": "discrete",
            "label": "Paragraph",
            "total": len(paras),
            "offsets": [[p.start, p.end] for p in paras],
        },
        "section_index": {
            "type": "discrete",
            "label": "Section",
            "total": len(epub_result.sections) if epub_result and epub_result.sections else len(sections),
            "offsets": epub_section_offsets,
        },
        "sentence_index": {
            "type": "discrete",
            "label": "Sentence",
            "total": len(sentences),
        },
    }

    if epub_result and epub_result.endnote_separator_offset > 0:
        coordinates["endnote_region"] = {
            "type": "boolean",
            "label": "Endnote Region",
            "separator_offset": epub_result.endnote_separator_offset,
        }

    (project_dir / "coordinates.json").write_text(
        json.dumps(coordinates, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    project = Project(path=project_dir, metadata=metadata)
    return project
