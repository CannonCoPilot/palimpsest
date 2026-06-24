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
from palimpsest.ingest.segmenter import Segment, segment_paragraphs, segment_sections, segment_sentences

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


def _complement_spans(masked: list[tuple[int, int]], n: int) -> list[tuple[int, int]]:
    """The unmasked [start,end) spans over [0,n) — the gaps between the masked intervals.

    This is the masking pipeline's partition pivot: it turns the masked set into the kept spans
    that become the analyzable text and OffsetMap, so a malformed masked set here would silently
    corrupt every analysis's coordinates. The precondition — ``masked`` is sorted, disjoint, and
    within [0, n] (the postcondition of :meth:`Project.masked_intervals`) — is therefore enforced:
    a violation raises ``ValueError`` rather than emitting wrong kept spans.
    """
    spans: list[tuple[int, int]] = []
    cur = 0
    for a, b in masked:
        if not (0 <= a < b <= n):
            raise ValueError(f"masked interval ({a}, {b}) is out of bounds for text length {n}")
        if a < cur:
            raise ValueError(
                f"masked intervals must be sorted and disjoint: ({a}, {b}) overlaps prior end {cur}"
            )
        if a > cur:
            spans.append((cur, a))
        cur = b  # precondition guarantees b > a >= cur, so this always advances
    if cur < n:
        spans.append((cur, n))
    return spans


class Project:
    """Represents a Palimpsest project directory."""

    def __init__(self, path: Path, metadata: ProjectMetadata) -> None:
        self.path = path
        self.metadata = metadata
        self._text_cache: str | None = None
        self._para_cache: list[tuple[int, int, str]] | None = None
        self._para_starts: list[int] | None = None
        self._spacy_doc_cache: Any | None = None
        # On-demand masking override for one analysis run (set by the server before extract):
        # {enabled: bool, mask_by_type?: {type: bool}, section_masked?: {id: bool}}.
        self._mask_override: dict[str, Any] | None = None
        self._verse_iv_cache: list[tuple[int, int]] | None = None
        # Set on an analysis-view clone whose text is ALREADY mask-resolved: masking is
        # materialized into the text, so masked_intervals() reports nothing further to mask.
        self._pre_masked: bool = False
        # Overrides the on-disk text path for extractors that need a real file (e.g. BookNLP);
        # an analysis view points this at the materialized analyzable text.
        self._text_path: Path | None = None
        # On an analysis view, the OffsetMap (original→analyzable) so unit boundaries from the
        # original-coordinate verse index can be projected into the analyzable stream.
        self._omap: Any = None

    def set_mask_override(self, override: dict[str, Any] | None) -> None:
        """Apply a transient masking override to this instance's ``masked_intervals``."""
        self._mask_override = override

    def reference_text(self) -> str:
        if self._text_cache is None:
            self._text_cache = self.reference_path().read_text(encoding="utf-8")
        return self._text_cache

    def reference_path(self) -> Path:
        """The on-disk path of the text to analyse — the project's ``reference.txt`` normally. On
        an analysis view it lazily materializes the in-memory analyzable text to a temp file (only
        when a file-path extractor like BookNLP actually asks for it) and returns that."""
        if self._text_path is not None:
            return self._text_path
        if self._pre_masked and self._text_cache is not None:
            import os
            import tempfile
            adir = self.path / ".analysis"
            adir.mkdir(exist_ok=True)
            fd, name = tempfile.mkstemp(suffix=".txt", dir=adir)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(self._text_cache)
            self._text_path = Path(name)
            return self._text_path
        return self.path / "reference.txt"

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

    def _verse_intervals(self) -> list[tuple[int, int]]:
        """The always-on verse-number token spans (cached per instance). Empty for works with no
        recognised verse markers. Prefers the cached verses.jsonl track over a full-text scan."""
        iv = self._verse_iv_cache
        if iv is None:
            from palimpsest.verses import (
                cached_verse_number_intervals,
                detect_verses,
                verse_number_intervals,
            )
            iv = cached_verse_number_intervals(self.path)
            if iv is None:
                iv = verse_number_intervals(detect_verses(self.reference_text()))
            self._verse_iv_cache = iv
        return iv

    def masked_intervals(self) -> list[tuple[int, int]]:
        """Masked [start,end) ranges excluded from analysis (Step 4 masking).

        The masked set is the structural deepest-wins masking UNION the verse-number layer — the
        "C:V." marker tokens (verse prose is untouched). Verse-number masking defaults on, since
        the markers are structural noise, but is a runtime toggle: an on-demand override may set
        ``mask_verse_numbers: False`` to keep them. With structural masking also off this yields a
        fully unmasked run. Returns ``[]`` only when nothing is masked at all.

        Postcondition (the masking contract relied on by :func:`_complement_spans` and the
        OffsetMap): the returned intervals are sorted, mutually disjoint, merged, and each lies
        within [0, len(reference_text)]. Guaranteed by delegating to :func:`layout.masked_intervals`.
        """
        import dataclasses

        from palimpsest.layout import load_layout, masked_intervals
        # An analysis view's text is already mask-resolved — nothing remains to mask.
        if self._pre_masked:
            return []
        text_len = len(self.reference_text())
        cfg = load_layout(self.path)
        ov = self._mask_override
        masking_off = ov is not None and not ov.get("enabled", True)
        # Verse-number masking defaults on; an explicit override toggle turns it off (R10).
        mask_verses = ov.get("mask_verse_numbers", True) if ov is not None else True
        verse_layer = self._verse_intervals() if mask_verses else []
        # No structural masking (none configured, or toggled off) → verse-number layer only.
        if cfg is None or masking_off:
            return masked_intervals([], {}, text_len, extra_masked=verse_layer)
        sections, mask_by_type = cfg.sections, cfg.mask_by_type
        if ov is not None:
            if ov.get("mask_by_type"):
                mask_by_type = {**cfg.mask_by_type, **ov["mask_by_type"]}
            sm = ov.get("section_masked") or {}
            if sm:
                sections = [
                    dataclasses.replace(s, masked=sm[s.id]) if s.id in sm else s for s in cfg.sections
                ]
        return masked_intervals(sections, mask_by_type, text_len, extra_masked=verse_layer)

    def analyzable_text(self, sep: str | None = None) -> tuple[str, Any]:
        """The masked-resolved analyzable text plus an :class:`~palimpsest.derive.OffsetMap`.

        Every unmasked character span (the complement of :meth:`masked_intervals`) is concatenated
        with ``sep``; the OffsetMap translates analyzable offsets back to original document offsets
        so analysis results can be re-anchored. Because masked_intervals always unions the
        verse-number layer, those tokens are absent from the analyzable text by construction.

        Postcondition: ``len(analyzable_text) == OffsetMap.child_len``. Both outputs are built from
        the same kept spans and separator, so they must agree on length; a divergence (e.g.
        normalization slipping into the text path but not the map) would drift every analyzable
        offset, so it is asserted before returning rather than allowed to corrupt re-anchoring.
        """
        from palimpsest.derive import OffsetMap, assemble_text
        if sep is None:
            sep = ""  # pure excision — masked spans vanish "as if not there"; windows span the gap
        text = self.reference_text()
        kept = _complement_spans(self.masked_intervals(), len(text))
        atext = assemble_text(text, kept, sep)
        omap = OffsetMap(kept, len(sep))
        if len(atext) != omap.child_len:
            raise ValueError(
                f"analyzable text ({len(atext)} chars) and its offset map ({omap.child_len}) "
                "disagree on length — the assembled text and its coordinate map have drifted"
            )
        return atext, omap

    def analysis_view(self, sep: str | None = None) -> tuple[Project, Any]:
        """A lightweight clone whose reference text IS the analyzable text, for running extractors
        against pre-masked content (they chunk it at their own runtime). Shares this project's path
        so results are written back to it; its own masked_intervals() is empty. A file-path
        extractor triggers lazy materialization of the analyzable text via ``reference_path()``;
        call :meth:`close_analysis_view` afterwards to remove any temp file."""
        atext, omap = self.analyzable_text(sep)
        view = Project(self.path, self.metadata)
        view._text_cache = atext
        view._pre_masked = True
        view._verse_iv_cache = []  # nothing left to mask in the resolved text
        view._omap = omap  # lets verse-based chunking project verse units into analyzable coords
        return view, omap

    def analyzable_verse_spans(self) -> list[tuple[int, int]]:
        """Verse-prose spans projected into THIS analysis view's analyzable coordinates, in order.

        Reads the project's verse index (original coordinates) and maps each verse body through the
        view's OffsetMap (original→analyzable, spanning any internal excised gaps). Returns ``[]``
        when this is not an analysis view or the project has no verse index, so verse/smart-verse
        chunking can log and fall back rather than silently masking missing data."""
        omap = self._omap
        if omap is None:
            return []
        from palimpsest.verses import cached_verse_text_spans
        spans = cached_verse_text_spans(self.path)
        if not spans:
            return []
        out: list[tuple[int, int]] = []
        for s, e in spans:
            m = omap.remap_element(s, e)
            if m is not None and m[1] > m[0]:
                out.append(m)
        return out

    def close_analysis_view(self) -> None:
        """Remove the lazily-materialized analyzable-text temp file backing an analysis view."""
        if self._text_path is not None and self._text_path.parent.name == ".analysis":
            self._text_path.unlink(missing_ok=True)
            self._text_path = None

    @classmethod
    def load(cls, path: Path) -> Project:
        meta_path = path / "metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"No metadata.json in {path}")
        meta = ProjectMetadata.from_dict(json.loads(meta_path.read_text()))
        return cls(path=path, metadata=meta)


def _nearest_occurrence(haystack: str, needle: str, expected: int, lo: int = 0) -> int:
    """Index of the occurrence of ``needle`` in ``haystack[lo:]`` nearest ``expected``.

    Occurrences are ascending, so the nearest to ``expected`` is the last one below
    it or the first at/above it — scan until we reach ``expected``, then stop.
    Returns -1 if ``needle`` does not occur at/after ``lo``.
    """
    best = -1
    pos = haystack.find(needle, lo)
    while pos != -1:
        if best == -1 or abs(pos - expected) < abs(best - expected):
            best = pos
        if pos >= expected:
            break
        pos = haystack.find(needle, pos + 1)
    return best


def _relocate_sections(
    epub_sections: list[Any], normalized: str, raw_len: int | None = None
) -> list[tuple[Any, int, int]]:
    """Map EPUB heading offsets onto the normalized reference text.

    The parser records section offsets against the assembled *pre-normalization*
    text; ``normalize()`` applies NFC, strips boilerplate, and collapses whitespace,
    shifting every offset cumulatively (the drift grows with position). We re-find
    each heading in the normalized text so the stored offset is the heading's true
    position. The needle is normalized the same way as the text so quote/whitespace
    differences don't defeat the match.

    A heading's text usually recurs when a book inlines its table of contents: each
    chapter title appears once as a TOC link near the front and again at the real
    division. Anchoring to the first match would drag every section into the TOC
    (the relocation misfire). Instead we anchor to the occurrence nearest the
    heading's *expected* position — the parser offset scaled by the normalization
    shrink ratio — which picks the real division over its TOC link.

    A monotonic cursor keeps reading order and stops two headings claiming the same
    spot. But choosing a later (correct) occurrence advances the cursor further than
    a first-match scan would, which can leave a following heading with all of its
    occurrences behind the cursor. Rather than drop it, we retry the search from the
    start: a unique heading's lone occurrence is its true position, and the
    expected-position bias still keeps the choice out of the front TOC. Only headings
    that occur nowhere are dropped — a missing boundary beats a mislocated mask. The
    result is sorted so recovered (out-of-order) anchors stay in document order.
    """
    out: list[tuple[Any, int, int]] = []
    cursor = 0
    scale = len(normalized) / raw_len if raw_len else 1.0
    for sec in epub_sections:
        needle = normalize(sec.heading_text, strip_paratextual=False)
        if not needle:
            continue
        expected = int(getattr(sec, "offset", 0) * scale)
        best = _nearest_occurrence(normalized, needle, expected, cursor)
        if best == -1:  # cursor overran every occurrence; recover from the start
            best = _nearest_occurrence(normalized, needle, expected, 0)
        if best == -1:
            continue
        end = best + len(needle)
        out.append((sec, best, end))
        cursor = max(cursor, end)
    out.sort(key=lambda t: t[1])
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
    text_extractor: Callable[[Path], str] | None = None,
    segmentation: tuple[list[Segment], list[Segment], list[Segment]] | None = None,
    pre_normalized: bool = False,
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
        raw_text = (text_extractor or extract_text)(source_path)

    _emit("normalize", "Normalizing text…", 0.45)
    # Derived subtexts arrive already normalized (slices of the parent's normalized reference). Re-
    # normalizing would re-collapse whitespace at the separator junctions, shifting every offset and
    # desyncing the remapped layers (segments/verses/elements) from reference.txt. Skip it so the
    # written reference exactly matches the offset map the caller remapped against.
    normalized = raw_text if pre_normalized else normalize(raw_text)
    sha = compute_sha256(normalized)
    # Re-anchor EPUB heading offsets onto the normalized text (see _relocate_sections).
    relocated_sections = (
        _relocate_sections(epub_result.sections, normalized, len(raw_text))
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

    if segmentation is not None:
        # Subtext derivation supplies the parent's segmentation remapped onto the child, so we
        # skip re-running the (expensive) spaCy sentence segmenter on text we already segmented.
        _emit("segment", "Reusing parent segmentation…", 0.55)
        paras, sections, sentences = segmentation
    else:
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
