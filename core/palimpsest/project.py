"""Project directory management for Palimpsest.

A Project represents a single ingested text with its metadata,
reference text, track outputs, and signal outputs.
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable
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

# The Doc is cached per-Project (see Project.spacy_doc), but the underlying model
# load (~0.5 GB, several seconds) is process-wide and reused across projects. This
# is the hot path for the entities/syntax extractors, which call spacy_doc on every
# run; without this cache each new project reloads the model from scratch.
_NLP_MODEL_CACHE: dict[str, Any] = {}


def _load_spacy_model(model: str) -> Any:
    import spacy

    if model not in _NLP_MODEL_CACHE:
        try:
            _NLP_MODEL_CACHE[model] = spacy.load(model)
        except OSError:
            _NLP_MODEL_CACHE[model] = spacy.load("en_core_web_sm")
    return _NLP_MODEL_CACHE[model]


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


def _projects_for_source_file(workspace: Path, source_file: str) -> list[Path]:
    """Existing project dirs whose metadata records this exact source_file.

    Used to enforce one-project-per-source on import: a source file may have been
    ingested previously under a different (legacy/title-based) slug, so matching on
    the directory name alone would miss it and create a duplicate.
    """
    matches: list[Path] = []
    if not workspace.is_dir():
        return matches
    for p in workspace.iterdir():
        meta_path = p / "metadata.json"
        if not meta_path.exists():
            continue
        try:
            m = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if m.get("source_file") == source_file:
            matches.append(p)
    return matches


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
            nlp = _load_spacy_model(model)
            text = self.reference_text()
            nlp.max_length = len(text) + 1000
            self._spacy_doc_cache = nlp(text)
        return self._spacy_doc_cache

    def sections(self) -> list[tuple[int, int, str]]:
        """Return (start, end, heading_text) for each section."""
        text = self.reference_text()
        segs = segment_sections(text)
        return [(s.start, s.end, s.text) for s in segs]

    def masked_intervals(self) -> list[tuple[int, int]]:
        """Masked [start,end) ranges from the layout config, or [] if none configured.

        Downstream analyses skip text intersecting these ranges (Step 4 masking).
        """
        from palimpsest.layout import load_layout, masked_intervals
        cfg = load_layout(self.path)
        if cfg is None:
            return []
        return masked_intervals(cfg.sections, cfg.mask_by_type, len(self.reference_text()))

    @classmethod
    def load(cls, path: Path) -> Project:
        meta_path = path / "metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"No metadata.json in {path}")
        meta = ProjectMetadata.from_dict(json.loads(meta_path.read_text()))
        return cls(path=path, metadata=meta)


def _relocate_sections(epub_sections: list[Any], normalized: str) -> list[tuple[Any, int, int]]:
    """Map EPUB heading offsets onto the normalized reference text.

    The parser records section offsets against the assembled *pre-normalization*
    text; ``normalize()`` collapses whitespace and strips, shifting every offset
    cumulatively (the drift grows with position). We re-find each heading in the
    normalized text — monotonically, in spine order — so the stored offset is the
    heading's true position. The needle is normalized the same way as the text so
    quote/whitespace differences don't defeat the match. Headings that can't be
    located are dropped: a missing boundary is safer than a mislocated mask.
    """
    out: list[tuple[Any, int, int]] = []
    cursor = 0
    for sec in epub_sections:
        needle = normalize(sec.heading_text, strip_paratextual=False)
        if not needle:
            continue
        idx = normalized.find(needle, cursor)
        if idx == -1:
            continue
        end = idx + len(needle)
        out.append((sec, idx, end))
        cursor = end
    return out


def ingest_file(
    source_path: Path,
    workspace: Path,
    title: str = "",
    author: str = "",
    year: int = 0,
    language: str = "en",
    content_profile: Any = None,  # ContentProfile or None
    overwrite: bool = False,
    progress: Callable[[str, str, float], None] | None = None,
    source_name: str | None = None,
) -> Project:
    """Ingest a text file into a new project directory.

    The project ID (slug) is derived deterministically from the source file's
    name so the same file always maps to the same project — re-importing replaces
    it rather than spawning a duplicate. Any existing project for this source file
    is removed first, even if it was created under a different (legacy/title-based)
    slug. ``overwrite`` is retained for API compatibility but no longer gates this.

    ``source_name`` overrides the identity used for the slug and recorded
    ``source_file`` when ``source_path`` is a temporary copy (e.g. an upload),
    so identity tracks the original filename rather than the temp path.

    ``progress(phase, message, fraction)`` is called at each structural phase
    boundary so callers can stream import progress (see the SSE import endpoint).
    """
    src_name = source_name or source_path.name

    def _emit(phase: str, message: str, fraction: float) -> None:
        if progress is not None:
            progress(phase, message, fraction)

    is_epub = source_path.suffix.lower() == ".epub"
    epub_result = None

    _emit("read", "Reading source file…", 0.05)
    if is_epub:
        from palimpsest.ingest.epub_parser import parse_epub
        _emit("parse", "Parsing EPUB structure…", 0.15)
        epub_result = parse_epub(source_path, content_profile=content_profile)
        raw_text = epub_result.text
        if not title and epub_result.metadata.title:
            title = epub_result.metadata.title
        if not author and epub_result.metadata.author:
            author = epub_result.metadata.author
        if not language and epub_result.metadata.language:
            language = epub_result.metadata.language
    else:
        _emit("parse", "Extracting text…", 0.15)
        raw_text = extract_text(source_path)

    _emit("normalize", "Normalizing text…", 0.45)
    normalized = normalize(raw_text)
    sha = compute_sha256(normalized)
    # Re-anchor EPUB heading offsets onto the normalized text (see _relocate_sections).
    relocated_sections = (
        _relocate_sections(epub_result.sections, normalized)
        if epub_result and epub_result.sections else []
    )
    slug = _make_slug(src_name)
    project_dir = workspace / slug

    # One project per source file: remove any prior ingest of this file — including
    # a copy stored under a different (legacy/title-based) slug — then recreate at
    # the deterministic slug. This makes re-import a clean replace, never a dupe.
    for existing in _projects_for_source_file(workspace, src_name):
        shutil.rmtree(existing)
    if project_dir.exists():
        # Reaching here means a *different* source file already slugs to this name
        # (a rare filename collision, since same-source copies were just removed).
        if not overwrite:
            raise FileExistsError(f"Project slug already in use: {project_dir.name}")
        shutil.rmtree(project_dir)

    for subdir in _SUBDIRS:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)

    (project_dir / "reference.txt").write_text(normalized, encoding="utf-8")
    (project_dir / "reference.sha256").write_text(sha)

    _emit("segment", "Segmenting paragraphs & sentences…", 0.55)
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
        if epub_result.cover_image:
            from palimpsest.ingest.epub_parser import cover_extension
            cover_name = f"cover{cover_extension(epub_result.cover_media_type)}"
            (project_dir / cover_name).write_bytes(epub_result.cover_image)
            meta_dict["cover"] = cover_name

    metadata = ProjectMetadata(
        id=slug,
        title=title or Path(src_name).stem.replace("-", " ").replace("_", " ").title(),
        language=language,
        source_format=source_path.suffix.lstrip(".").lower(),
        source_file=src_name,
        ingest_date=datetime.now(UTC).strftime("%Y-%m-%d"),
        palimpsest_version=__version__,
        reference_sha256=sha,
        word_count=count_words(normalized),
        paragraph_count=len(paras),
        section_count=len(relocated_sections) if relocated_sections else len(sections),
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

    _emit("layers", "Building segment layers…", 0.75)
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

    if relocated_sections:
        section_anns: list[Annotation] = []
        for sec, start_offset, end_offset in relocated_sections:
            section_anns.append(
                Annotation(
                    body=section_body(
                        heading_text=sec.heading_text,
                        heading_level=sec.heading_level,
                        section_index=sec.section_index,
                    ),
                    target=Target(
                        source=source_urn,
                        selector=TextPositionSelector(start=start_offset, end=end_offset),
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
        [[start, end] for _, start, end in relocated_sections]
        if relocated_sections
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
            "total": len(relocated_sections) if relocated_sections else len(sections),
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

    _emit("save", "Finalizing project…", 0.97)
    project = Project(path=project_dir, metadata=metadata)
    return project
