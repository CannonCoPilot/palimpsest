"""FastAPI server for Palimpsest — static file serving + API endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from palimpsest.alignment.records import comparison_dir, comparison_dirname
from palimpsest.runner import _remap_signal_dir, extract_masked, persist_track_outputs

logger = logging.getLogger(__name__)

# Limit concurrent CPU-heavy analysis jobs to prevent saturation on O(n²) workloads.
_job_semaphore = asyncio.Semaphore(3)


class SearchRequest(BaseModel):
    project: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$")
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=10, ge=1, le=100)
    model: str = Field(default="qwen3-embedding:4b", pattern=r"^[a-zA-Z0-9_:.\-]{1,64}$")


class SearchResult(BaseModel):
    paragraph_index: int
    score: float
    text: str
    start: int
    end: int


class SearchResponse(BaseModel):
    results: list[SearchResult]
    embedding_available: bool


class SummarizeRequest(BaseModel):
    passage: str = Field(min_length=10, max_length=5000)
    model: str = Field(default="qwen3:8b", pattern=r"^[a-zA-Z0-9_:.\-]{1,64}$")


class SummarizeResponse(BaseModel):
    summary: str | None
    model: str
    ollama_available: bool


class ExplainRequest(BaseModel):
    project: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$")
    state_id: int = Field(ge=0, le=50)
    model: str = Field(default="qwen3:8b", pattern=r"^[a-zA-Z0-9_:.\-]{1,64}$")


class ExplainResponse(BaseModel):
    explanation: str | None
    state_description: str
    feature_profile: dict[str, str]
    sample_passages: list[str]
    model: str
    ollama_available: bool


class LocalImportRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
    title: str = ""
    author: str = ""
    year: int = 0
    process: bool = True  # False = staged (Step 1 ingest only, defer analysis)
    overwrite: bool = False  # True = replace an existing project at the same slug (re-import)
    # Filename of a pre-generated gold masking map under core/tests/fixtures/gold/maps/
    # (e.g. "work-005.map.json"). When set, the server ingests the text then applies the
    # complete stored map verbatim as the project's layout — after verifying the map's
    # reference_sha256 matches the ingested text — instead of auto-detecting sections.
    layout_path: str | None = None


class SectionsUpdateRequest(BaseModel):
    sections: list[dict[str, Any]]
    mask_by_type: dict[str, bool] | None = None
    applied: bool | None = None
    extra_types: list[dict[str, Any]] | None = None  # custom user mask layers


class MaskOverrideRequest(BaseModel):
    """On-demand masking overlay applied to a single analysis run (non-destructive)."""

    enabled: bool = True
    mask_by_type: dict[str, bool] | None = None  # per-type-layer keep/mask overrides
    section_masked: dict[str, bool] | None = None  # per-element keep/mask overrides (by id)
    mask_verse_numbers: bool = True  # verse-number "C:V." markers; default on, toggle off to keep them


class DeriveRequest(BaseModel):
    """Derive a subtext child project from a parent's kept extraction layers."""

    extraction_types: list[str]  # type-layers whose element spans form the subtext text
    excluded_ids: list[str] = []  # Stage-2 per-element deselections
    include_container_ids: list[str] = []  # restrict extraction to these container sections (e.g. appendix)
    title: str = ""
    author: str = ""
    collection_id: str | None = None  # add parent+child to this collection (else auto)


class CollectionRequest(BaseModel):
    """Create or update a collection (a named grouping of related projects)."""

    label: str = ""
    description: str = ""
    project_ids: list[str] = []


class RoleRequest(BaseModel):
    """Set a member's collection-local role (FR-25): ``member`` (co-equal) or ``root`` (lens)."""

    role: str = "member"


class AlignmentRequest(BaseModel):
    """Pairwise alignment request (POST /api/alignment/run, /api/alignment/diff). Must live at
    module scope: ``from __future__ import annotations`` stringizes the endpoint's type hints, and
    FastAPI resolves them via ``get_type_hints`` against module globals — a function-local class is
    invisible there, so the body model silently degrades to a query param and rejects every POST."""

    query_id: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$")
    target_id: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$")
    method: str = Field(default="semantic", pattern=r"^(semantic|alphabet|word)$")


class LiftoverRequest(BaseModel):
    """Project a member's intervals onto another via their alignment (POST collections/{id}/liftover,
    C5/FR-42). Module scope for the same reason as :class:`AlignmentRequest`."""

    source_id: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$")
    target_id: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$")
    intervals: list[list[int]] = []
    kind: str = "mask"
    persist: bool = False


class ProbeRequest(BaseModel):
    """Probe R(q, Corpus) over a collection's shared embedding space (POST collections/{id}/probe,
    C6b/FR-31). Module scope for the same reason as :class:`AlignmentRequest`. Exactly one query source:
    ``q`` (text, embedded here via provider/endpoint/model) or ``ref_project``+``ref_chunk`` (reuse a
    passage already embedded in the corpus — service-free)."""

    q: str | None = None
    provider: str | None = None
    endpoint: str | None = None
    model: str | None = None
    ref_project: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_\-]+$")
    ref_chunk: int | None = None
    metric: str = "cosine"
    embedding_label: str | None = None
    k: int = Field(default=10, ge=1, le=200)
    per_member_k: int | None = Field(default=None, ge=1, le=200)
    snippet_chars: int = Field(default=200, ge=0, le=2000)


class SweepRequest(BaseModel):
    """Run the recall-dial sweep over a collection's member pairs (POST collections/{id}/sweep,
    C6c/FR-35). Module scope for the same reason as :class:`AlignmentRequest`. ``mode`` is the dial
    (exhaustive ↔ high-recall ↔ fast); ``force_exhaustive`` is the escape hatch; ``resume`` re-opens the
    content-addressed run journal and skips member pairs already done."""

    metric: str = "word_overlap"
    mode: str = Field(default="high-recall", pattern=r"^(exhaustive|high-recall|fast)$")
    force_exhaustive: bool = False
    embedding_label: str | None = None
    dense_threshold: int = Field(default=10_000, ge=0)  # 0 = never auto-dense (force candidate-gen)
    resume: bool = True


_STRUCTURAL_TRACKS = {"segments", "sections", "elements", "verses"}


def _job_display_status(job: dict | None, output_exists: bool) -> tuple[str, str | None]:
    """Map a background-job record + on-disk output presence to the UI status vocabulary (G5/B2).

    A failed job surfaces ``("failed", message)`` so the user is told *why* a run failed, instead of a
    failed job masquerading as ``"running"`` until the 30s cleanup silently reverts it to ``"pending"``.
    A ``"completed"`` job (or no job at all) maps to ``"computed"``/``"pending"`` by whether the output
    exists on disk — the vocabulary the frontend ``TrackStatus`` already understands. The error message
    is passed through verbatim (no "Matrix too large" relabel)."""
    job_status = job.get("status") if job else None
    if job_status == "failed":
        return "failed", (job.get("error") if job else None)
    if job_status == "running":
        return "running", None
    return ("computed" if output_exists else "pending"), None


def _track_run_info(project_dir: Path, track_name: str) -> dict[str, Any] | None:
    """Per-track run provenance for the status payload (§5 consumption honesty).

    Surfaces two things the data layer records but the UI could not see: (1) the record-effective
    clamp — what actually ran vs what was requested — read from ``manifests/{track}.run.json`` (the
    G3 provenance file); and (2) for ``lithmm``, the *actual* method and posterior type from its signal
    meta, since an HMM run silently falls back to KMeans on fit/import failure (B5) and the disk is
    honest while the UI was not. Returns ``None`` only when there is nothing to surface — no clamp and
    (for non-lithmm tracks) nothing else. A completed lithmm run always reports its actual method and
    posterior type, so the UI can confirm whether the HMM genuinely ran or fell back to KMeans."""
    info: dict[str, Any] = {}

    run_path = project_dir / "manifests" / f"{track_name}.run.json"
    if run_path.exists():
        try:
            run_data = json.loads(run_path.read_text())
        except (OSError, ValueError):
            run_data = {}
        params = run_data.get("parameters", {})
        clamped = run_data.get("clamped", [])
        # Surface only params we can fully describe — both the effective (ran) value and the
        # {name}_requested value track_provenance records. A partial record (e.g. a run.json from an
        # earlier provenance schema that lacked _requested) is skipped rather than rendered to the user
        # as a nonsensical "ran None (requested None)" note.
        surfacable = [
            k for k in clamped
            if params.get(k) is not None and params.get(f"{k}_requested") is not None
        ]
        if surfacable:
            info["clamped"] = surfacable
            info["effective"] = {k: params[k] for k in surfacable}
            info["requested"] = {k: params[f"{k}_requested"] for k in surfacable}

    if track_name == "lithmm":
        meta_path = project_dir / "signals" / "lithmm_meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except (OSError, ValueError):
                meta = {}
            if meta.get("method"):
                info["method"] = meta["method"]
            if meta.get("posterior_type"):
                info["posteriorType"] = meta["posterior_type"]

    return info or None


def _layer_status_entries(project_dir: Path, name: str) -> list[dict[str, Any]]:
    """Per-layer status rows for a label-keyed layer track (FR-4).

    Enumerates ``signals/{name}_*.json`` — each a plural, content-addressed layer the track produced —
    and reports each with its label, capability descriptor, precomputed stats, render descriptor, and
    per-label run provenance. This is what lets the UI list, compare, and drill into the many layers a
    single registry row cannot express. A manifest that fails to parse is skipped, not faked."""
    signals_dir = project_dir / "signals"
    if not signals_dir.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(signals_dir.glob(f"{name}_*.json")):
        try:
            manifest = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        meta = manifest.get("metadata", {})
        entry: dict[str, Any] = {
            "label": meta.get("label") or path.stem[len(name) + 1:],
            "status": "computed",
            "capability": meta.get("capability"),
            "stats": meta.get("stats"),
            "rendering": meta.get("rendering"),
        }
        run_info = _track_run_info(project_dir, path.stem)
        if run_info:
            entry["runInfo"] = run_info
        entries.append(entry)
    return entries


def _embedding_db_path(project_dir: Path, label: str) -> Path:
    """Resolve a content-addressed embedding label to its vector DB, validating the label first.

    The label is a hex digest (``EmbeddingTrack._label`` → ``sha256(...)[:16]``); validating it as hex
    before building the path forecloses traversal (``../``) and keeps the route a pure lookup. Missing
    layer → 404, not a guess."""
    import re as _re
    if not _re.fullmatch(r"[0-9a-f]{6,64}", label):
        raise HTTPException(status_code=400, detail=f"invalid embedding label: {label!r}")
    db = project_dir / "cache" / f"embeddings_{label}.db"
    if not db.exists():
        raise HTTPException(status_code=404, detail=f"embedding layer {label!r} not found")
    return db


def _load_embedding_vectors(project_dir: Path, label: str) -> Any:
    """Load all vectors of an embedding layer as an ``(n, dim)`` float32 array, in chunk order.

    ``get_all_vectors()`` returns insertion (= chunk) order, so row *i* is chunk *i* — the alignment the
    P3 analytics and the frontend's by-index join both depend on."""
    import numpy as np

    from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

    store = SqliteVecStore.open_existing(_embedding_db_path(project_dir, label))
    try:
        vectors = store.get_all_vectors()
    finally:
        store.close()
    return np.array(vectors, dtype=np.float32)


def _f32_le_bytes(arr: Any) -> bytes:
    """Serialize a numpy array to little-endian float32 bytes (C order) — the DotplotView ``.bin``
    wire contract every binary embedding endpoint shares, so the frontend reuses one fetch path."""
    return arr.astype("<f4").tobytes()


def _analysis_text(project_dir: Path) -> tuple[int, str, Any]:
    """Original text length, the masked-resolved analyzable text, and its OffsetMap (analyzable→
    original via ``inverse_span``). The P4 lexical endpoints compute on the analyzable text — so
    structural noise and verse numbers are excluded — then remap hit spans back to original
    coordinates for rendering against the source document."""
    from palimpsest.project import Project

    project = Project.load(project_dir)
    orig_len = len(project.reference_text())
    view, omap = project.analysis_view()
    return orig_len, view.reference_text(), omap


def _chunk_signals_path(project_dir: Path, label: str) -> Path:
    """Resolve a content-addressed chunk label to its signals manifest, validating the label as hex
    first (like the embedding labels) so the route stays a pure lookup with no traversal. Missing
    layer → 404, not a guess."""
    import re as _re
    if not _re.fullmatch(r"[0-9a-f]{6,64}", label):
        raise HTTPException(status_code=400, detail=f"invalid chunk label: {label!r}")
    path = project_dir / "signals" / f"chunking_{label}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"chunk layer {label!r} not found")
    return path


def _deepest_section_type(sections: list[Any], offset: int) -> str:
    """Element type of the smallest (deepest) structural section containing ``offset`` (original
    coords); ``"none"`` when no section covers it. Smallest span wins, so a chunk inside a verse
    inside a chapter is typed by the verse — the most specific structural unit."""
    best_span: int | None = None
    best_type = "none"
    for sec in sections:
        if sec.start <= offset < sec.end:
            span = sec.end - sec.start
            if best_span is None or span < best_span:
                best_span, best_type = span, sec.type
    return best_type


def _chunk_layer_stats_inputs(project_dir: Path, manifest: dict[str, Any]) -> dict[str, list]:
    """Assemble the parallel per-chunk lists the pure ``chunk_stats`` helper consumes: char/word
    lengths from each chunk's analyzable text, an element type per chunk, and chunk start offsets +
    structural boundaries in a *shared* (original) coordinate system.

    Chunk ``segment_offsets`` are analyzable coordinates; structural sections are original — so each
    chunk start is remapped through the OffsetMap before the alignment comparison. With no layout
    there are no structural boundaries, so the remap (and the heavier analysis-view load it needs) is
    skipped entirely."""
    from palimpsest.analysis.textstats import TOKEN_RE
    from palimpsest.layout import load_layout

    seg = manifest.get("segment_offsets") or []
    meta = manifest.get("metadata", {})
    chunk_texts = meta.get("chunk_texts")
    n = len(seg)

    layout = load_layout(project_dir)
    sections = list(layout.sections) if layout and layout.sections else []

    need_text = not (isinstance(chunk_texts, list) and len(chunk_texts) == n)
    atext = omap = None
    if need_text or sections:
        _, atext, omap = _analysis_text(project_dir)
    if need_text:
        chunk_texts = [atext[s:e] for s, e in seg]

    char_lengths = [len(t) for t in chunk_texts]
    word_counts = [len(TOKEN_RE.findall(t)) for t in chunk_texts]

    if sections:
        orig_starts: list[int] = []
        for s, e in seg:
            mapped = omap.inverse_span(s, e)
            orig_starts.append(mapped[0] if mapped else s)
        element_types = [_deepest_section_type(sections, st) for st in orig_starts]
        structural_boundaries = [sec.start for sec in sections]
        chunk_starts = orig_starts
    else:
        element_types = ["none"] * n
        structural_boundaries = []
        chunk_starts = [s for s, _ in seg]

    return {
        "char_lengths": char_lengths,
        "word_counts": word_counts,
        "element_types": element_types,
        "chunk_starts": chunk_starts,
        "structural_boundaries": structural_boundaries,
    }


def _term_spans_original(term: str, atext: str, omap: Any) -> list[list[int]]:
    """Whole-word, case-insensitive occurrences of ``term`` in the analyzable text, each remapped to
    its original-coordinate ``[start, end]``. Occurrences that map cleanly are kept in document order;
    a span with no original pre-image (entirely inside an excised gap) is dropped."""
    import re as _re
    spans: list[list[int]] = []
    for m in _re.finditer(rf"\b{_re.escape(term)}\b", atext, _re.IGNORECASE):
        mapped = omap.inverse_span(m.start(), m.end())
        if mapped is not None:
            spans.append([mapped[0], mapped[1]])
    return spans


def _remap_tracks_dir(tracks_dir: Path, omap: Any) -> None:
    """Remap stored annotation tracks analyzable→original (structural tracks are left untouched)."""
    from palimpsest.derive import inverse_remap_annotation_dicts
    if not tracks_dir.is_dir():
        return
    for tp in tracks_dir.glob("*.jsonl"):
        if tp.stem in _STRUCTURAL_TRACKS:
            continue
        recs = [json.loads(ln) for ln in tp.read_text(encoding="utf-8").splitlines() if ln.strip()]
        recs = inverse_remap_annotation_dicts(recs, omap)
        recs.sort(key=lambda r: ((r.get("target") or {}).get("selector") or {}).get("start", 0))
        tp.write_text(("\n".join(json.dumps(r) for r in recs) + "\n") if recs else "", encoding="utf-8")


def _remap_project_outputs(project_dir: Path, omap: Any) -> None:
    """Remap every analyzable-coordinate output (annotation tracks + signal manifests/alignments)
    of a batch run back to original document coordinates."""
    _remap_tracks_dir(project_dir / "tracks", omap)
    _remap_signal_dir(project_dir / "signals", omap)


def _layout_boundaries(project: Any) -> list[tuple[int, int, str]]:
    """Section boundaries (start, end, heading) from the sections track, else segmenter."""
    out: list[tuple[int, int, str]] = []
    sec_path = project.path / "tracks" / "sections.jsonl"
    if sec_path.exists():
        for line in sec_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            sel = d.get("target", {}).get("selector", {})
            start = sel.get("start")
            end = sel.get("end")
            body = d.get("body", {})
            heading = body.get("palimpsest:headingText") or body.get("value") or ""
            if start is not None:
                out.append((int(start), int(end if end is not None else start), str(heading)))
    if not out:
        out = [(s, e, h) for s, e, h in project.sections()]
    out.sort(key=lambda b: b[0])
    return out


def _endnote_separator(project_dir: Path) -> int:
    """Char offset where the endnote region begins, or -1."""
    coord = project_dir / "coordinates.json"
    if coord.exists():
        c = json.loads(coord.read_text())
        er = c.get("endnote_region")
        if er and int(er.get("separator_offset", -1)) > 0:
            return int(er["separator_offset"])
    return -1


def _sections_payload(
    cfg: Any, text_len: int, masked: list[tuple[int, int]] | None = None
) -> dict[str, Any]:
    """Package a LayoutConfig + the type vocabulary (builtin + custom) + masks for the UI.

    ``masked`` lets the caller supply a precomputed masked set (e.g. structural ∪ the
    verse-number layer); when omitted, the pure structural masking is computed.
    """
    from palimpsest.layout import (
        MASKED_BG_COLOR,
        MASKED_TEXT_COLOR,
        masked_intervals,
        type_vocabulary,
    )

    extra_types = getattr(cfg, "extra_types", [])
    intervals = masked if masked is not None else masked_intervals(cfg.sections, cfg.mask_by_type, text_len)
    return {
        "sections": [s.to_dict() for s in cfg.sections],
        "mask_by_type": cfg.mask_by_type,
        "applied": cfg.applied,
        "extra_types": extra_types,
        "text_len": text_len,
        "masked_intervals": [[a, b] for a, b in intervals],
        "types": type_vocabulary(extra_types),
        "masked_style": {"color": MASKED_TEXT_COLOR, "background": MASKED_BG_COLOR},
    }


def _write_elements_track(project_dir: Path, project_id: str, cfg: Any, text_len: int) -> int:
    """Emit mask elements as a unified 'elements' annotation track + manifest.

    Every layout element (except the full-span body canvas) becomes one annotation, so
    the Reader/Browser can render a single 'Elements' track whose subtypes the user can
    toggle. Masked elements (headers, front matter) are included by design — the track
    is a structural guide, not an analysis result.
    """
    from palimpsest.annotation.model import Annotation, Body, Creator, Target, TextPositionSelector
    from palimpsest.annotation.serializer import write_track
    from palimpsest.layout import SECTION_COLORS, SECTION_LABELS, effective_mask

    source = f"urn:palimpsest:{project_id}"
    anns: list[Annotation] = []
    for s in cfg.sections:
        if s.type == "body":
            continue  # the body is the analyzable canvas, not a guide element
        if not (0 <= s.start < s.end <= text_len):
            continue
        extra: dict[str, Any] = {
            "palimpsest:elementType": s.type,
            "palimpsest:elementName": s.name,
            "palimpsest:masked": effective_mask(s, cfg.mask_by_type),
            "palimpsest:parentId": s.parent_id or "",
            "palimpsest:color": SECTION_COLORS.get(s.type, "#8e8e93"),
        }
        if s.metadata.get("number"):
            extra["palimpsest:chapterNumber"] = s.metadata["number"]
        if s.metadata.get("name"):
            extra["palimpsest:chapterTitle"] = s.metadata["name"]
        body = Body(
            type="palimpsest:ElementAnnotation",
            purpose="classifying",
            value=s.label or SECTION_LABELS.get(s.type, s.type),
            extra=extra,
        )
        anns.append(Annotation(
            body=body,
            target=Target(source=source, selector=TextPositionSelector(s.start, s.end)),
            creator=Creator(name="palimpsest/layout"),
            confidence=1.0,
            evidence_level="E1",
            id=f"urn:palimpsest:{project_id}:elements:{s.name or s.id}",
            project_id=project_id,
            track_name="elements",
        ))

    track_path = project_dir / "tracks" / "elements.jsonl"
    if anns:
        write_track(track_path, anns)
    else:
        track_path.unlink(missing_ok=True)  # drop a stale track if nothing remains
    manifests_dir = project_dir / "manifests"
    manifests_dir.mkdir(exist_ok=True)
    (manifests_dir / "elements.manifest.json").write_text(
        json.dumps({
            "trackName": "elements",
            "bodyType": "palimpsest:ElementAnnotation",
            "colorScheme": {"primary": "#5ac8fa", "secondary": "#98989d"},
            "textViewRendering": "margin-marker",
            "overviewBarRendering": {"type": "state-band"},
            "evidenceLevel": "E1",
        }, indent=2),
        encoding="utf-8",
    )
    return len(anns)


def _write_verses_track(project_dir: Path, text: str) -> int:
    """Write the per-project verse coordinate index as a compact ``verses.jsonl`` track.

    One line per verse: ``{b: book, c: chapter, v: verse, ns: num_start, s: text_start,
    e: text_end}``. The masked number token is ``[ns, s)``; the verse prose is ``[s, e)``.
    This is BOTH the lazy verse track's source and the verse-number mask layer (the union
    of ``[ns, s)`` spans). It is far more compact than W3C element annotations — tens of
    thousands of verses stay a ~1-2MB file the Browser can fetch lazily when zoomed in.
    """
    from palimpsest.verses import detect_verses

    records = detect_verses(text)
    track_path = project_dir / "tracks" / "verses.jsonl"
    track_path.parent.mkdir(parents=True, exist_ok=True)
    if records:
        lines = [
            json.dumps({"b": r["book"], "c": r["chapter"], "v": r["verse"],
                        "ns": r["num_start"], "s": r["text_start"], "e": r["text_end"]},
                       ensure_ascii=False)
            for r in records
        ]
        track_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        track_path.unlink(missing_ok=True)
    return len(records)


def _verse_num_intervals(project_dir: Path) -> list[tuple[int, int]]:
    """Verse-number mask-layer intervals (``[num_start, text_start)`` per verse) from the
    cached ``verses.jsonl`` track, or ``[]`` if the project has none. Union these into
    ``masked_intervals`` so verse numbers are excluded from analysis while verse prose stays.
    """
    from palimpsest.verses import cached_verse_number_intervals
    return cached_verse_number_intervals(project_dir) or []


_COVER_SUFFIXES = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")


def _find_cover_url(project_dir: Path, meta: dict[str, Any]) -> str | None:
    """Return a /data URL for the project's cover image, or None.

    Prefers the filename recorded by import (metadata "cover"), falling back to
    any cover.* image present in the directory so hand-dropped covers also work.
    Served by the read-only /data/{project_id}/{path} route.
    """
    cover_name = meta.get("cover")
    if cover_name and (project_dir / cover_name).is_file():
        return f"/data/{project_dir.name}/{cover_name}"
    for cand in sorted(project_dir.glob("cover.*")):
        if cand.is_file() and cand.suffix.lower() in _COVER_SUFFIXES:
            return f"/data/{project_dir.name}/{cand.name}"
    return None


def _safe_project_dir(workspace: Path, project_id: str) -> Path:
    """Resolve project directory with path traversal protection."""
    if ".." in project_id or "/" in project_id or "\\" in project_id:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    project_dir = (workspace / project_id).resolve()
    if not project_dir.is_relative_to(workspace.resolve()):
        raise HTTPException(status_code=400, detail="Invalid project ID")
    if not project_dir.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")
    return project_dir


def _link_derived_collection(workspace: Path, parent: Any, child_id: str, collection_id: str | None) -> str:
    """Add a parent and its derived subtext to a collection (named, or an auto 'derived' one)."""
    from palimpsest.collections import link_derived

    return link_derived(workspace, parent.metadata.id, parent.metadata.title, child_id, collection_id)


_IMPORT_SUFFIXES = (".epub", ".txt", ".pdf", ".html", ".htm", ".md", ".markdown")


def _default_imports_dir() -> Path:
    """Directory the import browser lists: env override, else the repo's imports/.

    server.py lives at ``<repo>/core/palimpsest/server.py``, so the drop folder the
    user fills with book files resolves to ``<repo>/imports``.
    """
    import os

    env = os.environ.get("PALIMPSEST_IMPORTS_DIR")
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parents[2] / "imports"


def _safe_import_path(imports_dir: Path, rel_path: str) -> Path:
    """Resolve a relative path under imports_dir with traversal protection."""
    if not rel_path or rel_path.startswith("/") or ".." in Path(rel_path).parts:
        raise HTTPException(status_code=400, detail="Invalid import path")
    resolved = (imports_dir / rel_path).resolve()
    if not resolved.is_relative_to(imports_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid import path")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return resolved


def _gold_maps_dir() -> Path:
    """Directory holding the durable Gold Set masking maps."""
    return Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "gold" / "maps"


def _safe_gold_map_path(layout_path: str) -> Path:
    """Resolve a stored gold map filename under the gold maps dir, with traversal guard."""
    maps_dir = _gold_maps_dir()
    if not layout_path or layout_path.startswith("/") or ".." in Path(layout_path).parts:
        raise HTTPException(status_code=400, detail="Invalid layout path")
    resolved = (maps_dir / layout_path).resolve()
    if not resolved.is_relative_to(maps_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid layout path")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Gold map not found")
    return resolved


def _apply_gold_map(project: Any, layout_path: str) -> dict[str, Any]:
    """Apply a pre-generated gold masking map to a freshly-ingested project.

    Verifies the map's reference_sha256 matches the ingested text (offsets must land
    on the same coordinate space), persists the map verbatim as the project layout,
    and writes the unified 'elements' track. Returns a summary block.
    """
    from palimpsest.layout import LayoutConfig, masked_intervals, save_layout

    gmap = json.loads(_safe_gold_map_path(layout_path).read_text(encoding="utf-8"))
    expected = gmap.get("reference_sha256")
    actual = project.metadata.reference_sha256
    if not expected:
        raise HTTPException(status_code=400, detail="Gold map missing reference_sha256")
    if expected != actual:
        raise HTTPException(
            status_code=409,
            detail=(f"reference_sha256 mismatch — map {expected[:12]} vs text {actual[:12]}; "
                    "offsets would not align, refusing to apply"),
        )
    cfg = LayoutConfig.from_dict(gmap)
    cfg.applied = True
    save_layout(project.path, cfg)
    text = project.reference_text()
    text_len = len(text)
    track_n = _write_elements_track(project.path, project.metadata.id, cfg, text_len)
    verse_n = _write_verses_track(project.path, text)
    # Masked set = structural deepest-wins UNION the verse-number layer (the "C:V." tokens).
    mi = masked_intervals(cfg.sections, cfg.mask_by_type, text_len,
                          extra_masked=_verse_num_intervals(project.path))
    return {
        "layout_path": layout_path,
        "sha_verified": True,
        "element_count": len(cfg.sections),
        "track_elements": track_n,
        "verse_count": verse_n,
        "masked_spans": len(mi),
        "masked_chars": sum(b - a for a, b in mi),
    }


_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
_TITLE_NOISE = frozenset({"the", "a", "an", "enhanced", "novel", "edition", "unabridged", "of"})


def _roman_to_int(s: str) -> int | None:
    total = prev = 0
    for ch in reversed(s.lower()):
        v = _ROMAN.get(ch, 0)
        if v == 0:
            return None
        total += -v if v < prev else v
        prev = max(prev, v)
    return total or None


_STRUCTURAL_WORDS = frozenset({"vol", "part", "book", "no", "chapter"})


def _title_signature(title: str) -> str:
    """Normalize a title for cross-edition matching: unify volume wording, convert
    roman numerals that follow a structural word to arabic, drop noise words. So
    'Ante-Nicene Fathers, Vol_ I', 'Vol. I', and 'The Ante-Nicene Fathers: Volume 1'
    collapse to one signature, while Vol 1 vs Vol 2 stay distinct.

    Tokenizing first (rather than regex over raw text) makes this robust to the odd
    separators Anna's-Archive filenames use ('Vol_ I', 'Vol., I')."""
    t = re.sub(r"\bvolumes?\b", "vol", title.lower())
    out: list[str] = []
    for tok in re.findall(r"[a-z0-9]+", t):
        if tok in _TITLE_NOISE:
            continue
        if out and out[-1] in _STRUCTURAL_WORDS:
            n = _roman_to_int(tok)
            if n is not None:
                out.append(str(n))
                continue
        out.append(tok)
    return " ".join(out)


def _parse_import_filename(name: str) -> tuple[str, str, str]:
    """Parse (title, author, isbn) from an Anna's-Archive-style filename
    ('Title -- Author -- ... -- isbn13 NNN -- ... .ext'); degrade gracefully."""
    stem = name.rsplit(".", 1)[0]
    parts = [p.strip() for p in stem.split(" -- ")]
    title = parts[0] if parts and parts[0] else stem
    author = parts[1] if len(parts) > 1 else ""
    m = re.search(r"isbn(?:13|10)?\s*([0-9Xx]{10,13})", stem, re.IGNORECASE)
    return title, author, (m.group(1).upper() if m else "")


def _imported_index(workspace: Path) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Index existing projects by source filename, title signature, and ISBN."""
    by_file: dict[str, str] = {}
    by_sig: dict[str, str] = {}
    by_isbn: dict[str, str] = {}
    if workspace.is_dir():
        for p in workspace.iterdir():
            mp = p / "metadata.json"
            if not mp.exists():
                continue
            try:
                m = json.loads(mp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            pid = m.get("id", p.name)
            if m.get("source_file"):
                by_file[m["source_file"]] = pid
            sig = _title_signature(m.get("title", ""))
            if sig:
                by_sig.setdefault(sig, pid)
            isbn = re.sub(r"[^0-9X]", "", str(m.get("isbn", "")).upper())
            if isbn:
                by_isbn.setdefault(isbn, pid)
    return by_file, by_sig, by_isbn


def _import_status(
    name: str, indexes: tuple[dict[str, str], dict[str, str], dict[str, str]]
) -> tuple[str, str | None, str, str, str]:
    """Classify an importable file as new / imported / version of an imported title.

    Returns (status, matched_project_id, parsed_title, parsed_author, parsed_isbn).
    """
    by_file, by_sig, by_isbn = indexes
    title, author, isbn = _parse_import_filename(name)
    if name in by_file:
        return "imported", by_file[name], title, author, isbn
    isbn_norm = re.sub(r"[^0-9X]", "", isbn)
    if isbn_norm and isbn_norm in by_isbn:
        return "version", by_isbn[isbn_norm], title, author, isbn
    sig = _title_signature(title)
    if sig and sig in by_sig:
        return "version", by_sig[sig], title, author, isbn
    return "new", None, title, author, isbn


def create_app(workspace: Path, imports_dir: Path | None = None) -> FastAPI:
    """Create the FastAPI application for a workspace directory."""
    app = FastAPI(title="Palimpsest", version="0.1.0")
    imports_dir = imports_dir or _default_imports_dir()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    @app.get("/api/projects")
    async def list_projects() -> JSONResponse:
        """List all projects in the workspace."""
        projects = []
        if workspace.is_dir():
            for p in sorted(workspace.iterdir()):
                meta_path = p / "metadata.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text())
                    projects.append({
                        "id": meta.get("id", p.name),
                        "title": meta.get("title", p.name),
                        "author": meta.get("author", ""),
                        "word_count": meta.get("word_count", 0),
                        "cover": _find_cover_url(p, meta),
                        "source_file": meta.get("source_file", ""),
                    })
        return JSONResponse(content=projects)

    @app.delete("/api/projects/{project_id}")
    async def delete_project(project_id: str) -> JSONResponse:
        """Delete a project and all its artifacts (irreversible)."""
        project_dir = _safe_project_dir(workspace, project_id)
        shutil.rmtree(project_dir)
        return JSONResponse(content={"status": "ok", "deleted": project_id})

    @app.get("/api/projects/{project_id}/tracks")
    async def list_tracks(project_id: str) -> JSONResponse:
        """List available tracks for a project."""
        project_dir = _safe_project_dir(workspace, project_id)
        tracks_dir = project_dir / "tracks"
        if not tracks_dir.is_dir():
            return JSONResponse(content=[])
        track_names = sorted(
            f.stem for f in tracks_dir.glob("*.jsonl") if f.is_file()
        )
        return JSONResponse(content=track_names)

    @app.post("/api/summarize")
    async def summarize(request: SummarizeRequest) -> SummarizeResponse:
        """Generate an AI summary of a text passage."""
        import asyncio

        from palimpsest.services.manager import OllamaManager

        mgr = OllamaManager(llm_model=request.model)
        status = await asyncio.to_thread(mgr.health_check)
        if not status.running:
            return SummarizeResponse(
                summary=None, model=request.model, ollama_available=False
            )
        client = mgr.llm_client()
        summary = await asyncio.to_thread(client.summarize, request.passage)
        return SummarizeResponse(
            summary=summary, model=request.model, ollama_available=True
        )

    @app.post("/api/explain")
    async def explain_state(request: ExplainRequest) -> ExplainResponse:
        """Explain a LitHMM state using its feature profile and sample passages."""
        import asyncio

        if ".." in request.project:
            raise HTTPException(status_code=400, detail="Invalid project ID")

        meta_path = workspace / request.project / "signals" / "lithmm_meta.json"
        if not meta_path.exists():
            raise HTTPException(status_code=404, detail="LitHMM metadata not found — run analysis first")

        meta = json.loads(meta_path.read_text())
        state_descriptions = meta.get("state_descriptions", {})
        feature_names = meta.get("feature_names", [])
        state_desc = state_descriptions.get(str(request.state_id), f"State {request.state_id}")

        from palimpsest.project import Project

        proj = Project.load(workspace / request.project)
        ref_text = proj.reference_text()

        track_path = workspace / request.project / "tracks" / "lithmm.jsonl"
        sample_passages: list[str] = []
        feature_profile: dict[str, str] = {}

        if track_path.exists():
            annotations = []
            for line in track_path.read_text().strip().split("\n"):
                if line:
                    annotations.append(json.loads(line))

            state_anns = [
                a for a in annotations
                if a.get("body", {}).get("palimpsest:stateId") == request.state_id
            ]

            for ann in state_anns[:5]:
                sel = ann.get("target", {}).get("selector", {})
                start, end = sel.get("start"), sel.get("end")
                if start is not None and end is not None:
                    sample_passages.append(ref_text[start:end][:300])

        state_means = meta.get("state_means", {})
        per_state = state_means.get(str(request.state_id))
        if per_state and len(per_state) == len(feature_names):
            for name, val in zip(feature_names, per_state):
                feature_profile[name] = f"{val:+.2f} (z-score)"
        else:
            for name in feature_names:
                feature_profile[name] = state_desc

        from palimpsest.services.manager import OllamaManager

        mgr = OllamaManager(llm_model=request.model)
        status = await asyncio.to_thread(mgr.health_check)
        if not status.running:
            return ExplainResponse(
                explanation=None,
                state_description=state_desc,
                feature_profile=feature_profile,
                sample_passages=sample_passages,
                model=request.model,
                ollama_available=False,
            )

        passages_context = "\n---\n".join(sample_passages[:3]) if sample_passages else "(no passages)"
        prompt = (
            f"You are a literary analysis assistant. Explain what LitHMM State {request.state_id} "
            f"represents in this text.\n\n"
            f"Statistical description: {state_desc}\n\n"
            f"Feature names: {', '.join(feature_names)}\n\n"
            f"Representative passages from this state:\n{passages_context}\n\n"
            f"Provide a clear, 2-4 sentence explanation of what kind of writing this state "
            f"captures. Describe the narrative qualities, not the statistics."
        )

        client = mgr.llm_client()
        messages = [
            {"role": "system", "content": "You are a literary analysis assistant that explains computational findings in human terms."},
            {"role": "user", "content": prompt},
        ]
        explanation = await asyncio.to_thread(client.chat, messages, 0.3, 300)

        return ExplainResponse(
            explanation=explanation,
            state_description=state_desc,
            feature_profile=feature_profile,
            sample_passages=sample_passages,
            model=request.model,
            ollama_available=True,
        )

    @app.get("/api/search")
    async def search(
        project: str,
        query: str,
        k: int = 10,
        model: str = "qwen3-embedding:4b",
    ) -> SearchResponse:
        """Similarity search over paragraph embeddings."""
        import asyncio

        if ".." in project or "/" in project or "\\" in project:
            raise HTTPException(status_code=400, detail="Invalid project ID")
        project_dir = (workspace / project).resolve()
        if not project_dir.is_relative_to(workspace.resolve()):
            raise HTTPException(status_code=400, detail="Invalid project ID")
        if not project_dir.is_dir():
            return SearchResponse(results=[], embedding_available=False)

        embeddings_db = project_dir / "cache" / "embeddings.db"
        if not embeddings_db.exists():
            return SearchResponse(results=[], embedding_available=False)

        from palimpsest.project import Project
        from palimpsest.services.manager import OllamaManager
        from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

        try:
            mgr = OllamaManager(embedding_model=model)
            client = mgr.embedding_client()
            query_vec = await asyncio.to_thread(client.embed_one, query)
            if query_vec is None:
                return SearchResponse(results=[], embedding_available=False)

            store = SqliteVecStore.open_existing(embeddings_db)
            try:
                hits = store.search(query_vec, k=k)
            finally:
                store.close()

            proj = Project.load(project_dir)
            paras = proj.paragraphs()
            results = []
            for hit_id, score in hits:
                parts = hit_id.split(":")
                if len(parts) >= 3:
                    idx = int(parts[2])
                    if idx < len(paras):
                        start, end, text = paras[idx]
                        results.append(SearchResult(
                            paragraph_index=idx,
                            score=round(score, 4),
                            text=text[:300],
                            start=start,
                            end=end,
                        ))

            return SearchResponse(results=results, embedding_available=True)
        except (FileNotFoundError, OSError):
            return SearchResponse(results=[], embedding_available=False)
        except Exception as exc:
            logger.error("Search failed: %s", exc)
            raise HTTPException(status_code=500, detail=f"Search error: {exc}")

    @app.get("/api/projects/{project_id}/characters")
    async def get_characters(project_id: str) -> JSONResponse:
        """Get character index for a project (built from coreference + entity tracks)."""
        import asyncio

        project_dir = _safe_project_dir(workspace, project_id)

        cache_path = project_dir / "cache" / "characters.json"
        if cache_path.exists():
            return JSONResponse(content=json.loads(cache_path.read_text()))

        from palimpsest.characters import build_character_index
        from palimpsest.project import Project

        proj = Project.load(project_dir)
        paras = [{"start": p[0], "end": p[1]} for p in proj.paragraphs()]
        characters = await asyncio.to_thread(build_character_index, project_dir, paras)

        cache_path.parent.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(characters, indent=2), encoding="utf-8")

        return JSONResponse(content=characters)

    @app.get("/api/projects/{project_id}/characters/cooccurrence")
    async def get_cooccurrence(project_id: str, top_n: int = 20) -> JSONResponse:
        """Get character co-occurrence matrix."""
        import asyncio

        project_dir = _safe_project_dir(workspace, project_id)
        cache_path = project_dir / "cache" / "characters.json"

        if cache_path.exists():
            characters = json.loads(cache_path.read_text())
        else:
            from palimpsest.characters import build_character_index
            from palimpsest.project import Project

            proj = Project.load(project_dir)
            paras = [{"start": p[0], "end": p[1]} for p in proj.paragraphs()]
            characters = await asyncio.to_thread(build_character_index, project_dir, paras)

            cache_path.parent.mkdir(exist_ok=True)
            cache_path.write_text(json.dumps(characters, indent=2), encoding="utf-8")

        from palimpsest.characters import compute_cooccurrence

        matrix = compute_cooccurrence(characters, top_n=top_n)
        return JSONResponse(content=matrix)

    _running_jobs: dict[str, dict] = {}

    @app.get("/api/projects/{project_id}/analysis/status")
    async def analysis_status(project_id: str) -> JSONResponse:
        """Get status of all track extractors for a project."""
        project_dir = _safe_project_dir(workspace, project_id)

        from palimpsest.tracks.registry import TrackRegistry

        registry = TrackRegistry.discover()
        tracks_dir = project_dir / "tracks"
        manifests_dir = project_dir / "manifests"

        result = []
        for extractor_cls in registry.dependency_order():
            ext = extractor_cls()
            name = ext.name
            output_exists = False
            # Label-keyed layer tracks (chunking/embedding) have no single signals/{name}.json — they
            # produce plural signals/{name}_{label}.json. Enumerate those as nested `layers` and treat
            # the track as "computed" when at least one layer exists (FR-4).
            layers = _layer_status_entries(project_dir, name) if getattr(ext, "layer_keyed", False) else None
            if layers is not None:
                output_exists = bool(layers)
            elif ext.output_type == "annotation":
                output_exists = (tracks_dir / f"{name}.jsonl").exists()
            elif ext.output_type == "signal":
                output_exists = (project_dir / "signals" / f"{name}.json").exists()

            manifest_path = manifests_dir / f"{name}.manifest.json"
            manifest_data = None
            if manifest_path.exists():
                manifest_data = json.loads(manifest_path.read_text())

            # A present job is not always "running": _job_display_status surfaces a failed job's real
            # status + error so the user is told *why* a run failed (B2), instead of a failed job
            # masquerading as "running" until the 30s cleanup silently reverts it to "pending".
            job = _running_jobs.get(f"{project_id}:{name}")
            status, error = _job_display_status(job, output_exists)

            entry = {
                "name": name,
                "status": status,
                "outputType": ext.output_type,
                "dependsOn": ext.depends_on,
                "evidenceLevel": ext.evidence_level,
                "hasManifest": manifest_data is not None,
                "lfoTypes": ext.lfo_types,
            }
            if error:
                entry["error"] = error
            run_info = _track_run_info(project_dir, name)
            if run_info:
                entry["runInfo"] = run_info
            if layers is not None:
                # Plural layers for this track, each carrying its own label/capability/stats/runInfo. The
                # track-level row stays (it advertises the producible track even at zero layers).
                entry["layers"] = layers
            result.append(entry)

        return JSONResponse(content=result)

    @app.post("/api/projects/{project_id}/analyze/{track_name}")
    async def run_analysis(
        project_id: str,
        track_name: str,
        force: bool = False,
        n_states: int | None = None,
        n_topics: int | None = None,
        method: str | None = None,
        metric: str | None = None,
        metrics: str | None = None,
        inputs: str | None = None,
        granularity: str | None = None,
        analyzable_sep: str | None = None,
        chunk_size: int | None = None,
        chunk_mode: str | None = None,
        smart_unit: str | None = None,
        delimiters: list[str] | None = Query(None),
        grow_factor: float | None = None,
        remainder_ratio: float | None = None,
        embed_provider: str | None = None,
        embed_endpoint: str | None = None,
        embed_model: str | None = None,
        embed_batch_size: int | None = None,
        chunk_label: str | None = None,
        mask_override: MaskOverrideRequest | None = None,
    ) -> JSONResponse:
        """Run a single track extractor with optional parameters and an optional
        on-demand masking override (non-destructive; scopes this run's masked set)."""
        import asyncio

        project_dir = _safe_project_dir(workspace, project_id)

        from palimpsest.tracks.registry import TrackRegistry

        registry = TrackRegistry.discover()
        all_extractors = {type(e)().name: type(e) for e in [cls() for cls in registry.dependency_order()]}
        if track_name not in all_extractors:
            raise HTTPException(status_code=404, detail=f"Unknown track: {track_name}")

        job_key = f"{project_id}:{track_name}"
        if _running_jobs.get(job_key, {}).get("status") == "running":
            return JSONResponse(content={"status": "already_running"})

        from palimpsest.project import Project

        project = Project.load(project_dir)
        if mask_override is not None:
            project.set_mask_override(mask_override.model_dump())
        extractor = all_extractors[track_name]()

        params: dict[str, Any] = {}
        # n_states / n_topics pass through verbatim — NOT clamped. The owning track's validate_params
        # rejects out-of-range values with a 400 (below), so the user is told instead of having the
        # value silently rewritten.
        if n_states is not None:
            params["n_states"] = n_states
        if n_topics is not None:
            params["n_topics"] = n_topics
        if method is not None:
            params["method"] = method
        if metric is not None:
            params["metric"] = metric
        if metrics is not None:
            selected = [m.strip() for m in metrics.split(",") if m.strip()]
            if selected:
                params["metrics"] = selected
        if inputs is not None:
            # self_similarity's explicit layer-bundle list (P7), forwarded verbatim as a JSON string;
            # the track's `_parse_inputs` converter decodes + validates it (malformed → 400 below).
            params["inputs"] = inputs
        if granularity is not None:
            params["granularity"] = granularity
        # Chunking + embedding stage parameters pass through verbatim — NOT clamped or defaulted.
        # ChunkingConfig / EmbeddingConfig validate them; bad/missing values are rejected with a 400
        # below so the user is told, never silently corrected.
        if chunk_size is not None:
            params["chunk_size"] = chunk_size
        if chunk_mode is not None:
            params["chunk_mode"] = chunk_mode
        if smart_unit is not None:
            params["smart_unit"] = smart_unit
        if delimiters is not None:
            # Each repeated `delimiters` query param is one full clause delimiter — multi-character
            # allowed (e.g. "||", " -- ", "<<")—not split into characters. Empty values are dropped;
            # ChunkingConfig rejects an all-empty set, so this is never a silent no-op.
            params["delimiters"] = tuple(d for d in delimiters if d)
        if grow_factor is not None:
            params["grow_factor"] = grow_factor
        if remainder_ratio is not None:
            params["remainder_ratio"] = remainder_ratio
        if embed_provider is not None:
            params["embed_provider"] = embed_provider
        if embed_endpoint is not None:
            params["embed_endpoint"] = embed_endpoint
        if embed_model is not None:
            params["embed_model"] = embed_model
        if embed_batch_size is not None:
            params["embed_batch_size"] = embed_batch_size
        if chunk_label is not None:
            # Selects which persisted chunk layer EmbeddingTrack embeds (the {label} in
            # signals/chunking_{label}.json). Only EmbeddingTrack declares it; any other track rejects
            # it as an unknown parameter (resolve_params), so a stray chunk_label can't pass silently.
            params["chunk_label"] = chunk_label
        if force:
            params["force"] = True
        if params and hasattr(extractor, "set_params"):
            # A bad param (wrong type / out of range) must surface as a 400, not an uncaught 500:
            # set_params + resolve_params raise ValueError/TypeError, which we map to a clean 400 here.
            try:
                extractor.set_params(params)
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        # Validate the chunking+embedding parameters synchronously where the extractor supports it,
        # so the user gets an immediate 400 (with the reason) instead of a silently-defaulted run or
        # a failure surfacing only later in the async job. The returned dict echoes the resolved
        # parameters so the caller can confirm exactly what will run.
        resolved_params: dict[str, Any] | None = None
        if hasattr(extractor, "validate_params"):
            try:
                resolved_params = extractor.validate_params()
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        # Analyzable-stream separator: the string inserted between kept (unmasked) spans when the
        # masked-resolved analyzable text is assembled. Exposed as a runtime parameter so it is never
        # a hidden default — "" (the canonical pure-excision semantic, masked spans vanishing "as if
        # not there") applies only when the caller omits it, and the resolved value is echoed back.
        resolved_sep = analyzable_sep if analyzable_sep is not None else ""

        _running_jobs[job_key] = {"status": "running", "track": track_name, "params": params}

        async def run() -> None:
            try:
                async with _job_semaphore:
                    result = await asyncio.to_thread(extract_masked, project, extractor, resolved_sep)
                # Persist exactly as the CLI run-track command does, through the one shared writer in
                # runner.persist_track_outputs — annotation track + static manifest + per-label run
                # provenance (FR-4) — so a track produced from either entry point leaves identical
                # artifacts and the two paths can never disagree on the on-disk shape.
                persist_track_outputs(project_dir, extractor, result)
                _running_jobs[job_key] = {"status": "completed", "track": track_name}
            except Exception as exc:
                # One honest failure path. The previous code relabelled EVERY extract ValueError as
                # "Matrix too large" — wrong 100% of the time, since no matrix-size error exists (the
                # size guard is warn-only, B4). Carry the real message *and* the exception type, so a
                # missing per-metric size, an embedding-service ConnectError, or a degenerate corpus
                # each reads as what it actually was — end-to-end to the UI (B2).
                _running_jobs[job_key] = {
                    "status": "failed",
                    "track": track_name,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            finally:
                asyncio.get_running_loop().call_later(30.0, lambda: _running_jobs.pop(job_key, None))

        asyncio.create_task(run())
        content: dict[str, Any] = {"status": "started", "track": track_name}
        if resolved_params is not None:
            content["resolved_params"] = resolved_params
        content["analyzable_sep"] = resolved_sep
        return JSONResponse(content=content)

    @app.get("/api/projects/{project_id}/analyze/{track_name}/status")
    async def job_status(project_id: str, track_name: str) -> JSONResponse:
        """Check status of a running analysis job."""
        job_key = f"{project_id}:{track_name}"
        job = _running_jobs.get(job_key)
        if not job:
            return JSONResponse(content={"status": "idle"})
        return JSONResponse(content=job)

    @app.get("/api/projects/{project_id}/self_similarity/chunk_sizes")
    async def self_similarity_chunk_sizes(project_id: str) -> JSONResponse:
        """List all computed chunk sizes for self-similarity."""
        project_dir = _safe_project_dir(workspace, project_id)
        signals_dir = project_dir / "signals"
        sizes: list[int] = []
        if signals_dir.is_dir():
            for entry in signals_dir.iterdir():
                if entry.is_dir() and entry.name.startswith("self_similarity_cs"):
                    try:
                        cs = int(entry.name.replace("self_similarity_cs", ""))
                        sizes.append(cs)
                    except ValueError:
                        pass
        return JSONResponse(content={"chunk_sizes": sorted(sizes)})

    @app.get("/api/projects/{project_id}/self_similarity/inputs")
    async def self_similarity_inputs(project_id: str) -> JSONResponse:
        """Discovery: the layers bindable into a self_similarity run (FR-7, Vision §3.3).

        The consumer binds layers by explicit label (one {chunk, repeat_mask, embedding?} bundle per
        chunk size), so the picker needs the *coherent* options pre-grouped and server-validated. The
        same predicate run-time binding uses (``bundles.coherence_reason``) decides nesting here, so
        discovery and binding can never disagree; incoherent layers are surfaced in ``incompatible``,
        never silently dropped (NFR-3). Finding no layers is a valid 200 with empty ``chunk_layers``,
        not an error — producing a layer is a separate, explicit user action.

        Field names are family-neutral (nothing prefixed ``self_similarity_*``) so this can later be
        promoted to a generic ``…/layers/consumable?for=<track>`` route as a rename, not a redesign.
        """
        from palimpsest.tracks.bundles import coherence_reason
        from palimpsest.tracks.self_similarity import _METHODS

        project_dir = _safe_project_dir(workspace, project_id)

        chunk_layers: list[dict[str, Any]] = []
        chunks_by_label: dict[str, dict[str, Any]] = {}
        for c in _layer_status_entries(project_dir, "chunking"):
            cap = c.get("capability") or {}
            entry: dict[str, Any] = {
                "label": c["label"],
                "size": cap.get("size"),
                "bundle_ready": False,  # set once coherent repeat_masks are counted
                "capability": cap,
                "stats": c.get("stats"),
                "rendering": c.get("rendering"),
                "repeat_masks": [],
                "embeddings": [],
            }
            if "runInfo" in c:
                entry["runInfo"] = c["runInfo"]
            chunk_layers.append(entry)
            chunks_by_label[c["label"]] = entry

        incompatible: list[dict[str, Any]] = []

        def _classify(deps: list[dict[str, Any]], kind: str, bucket: str) -> None:
            # A dependent layer names its parent chunk via capability.chunk_layer_id, so the join is a
            # direct lookup (not an O(n*m) scan). Present + coherent → nest; otherwise → incompatible
            # with the reason from the shared predicate (or "not present" when the parent is gone).
            for dep in deps:
                cap = dep.get("capability") or {}
                claimed = cap.get("chunk_layer_id")
                parent = chunks_by_label.get(claimed)
                if parent is None:
                    incompatible.append({
                        "kind": kind,
                        "label": dep["label"],
                        "reason": (
                            f"{kind} layer '{dep['label']}' was built on chunk layer "
                            f"'{claimed}', which is not present"
                        ),
                    })
                    continue
                reason = coherence_reason(
                    cap, kind, dep["label"],
                    parent["label"], parent["capability"].get("analyzable_digest"),
                )
                if reason:
                    incompatible.append({"kind": kind, "label": dep["label"], "reason": reason})
                    continue
                parent[bucket].append({
                    "label": dep["label"], "capability": cap, "stats": dep.get("stats"),
                })

        _classify(_layer_status_entries(project_dir, "repeat_mask"), "repeat-mask", "repeat_masks")
        _classify(_layer_status_entries(project_dir, "embedding"), "embedding", "embeddings")

        for entry in chunk_layers:
            entry["bundle_ready"] = len(entry["repeat_masks"]) >= 1

        methods = [
            {"name": m.name, "requires_embedding": m.requires_embedding}
            for m in _METHODS.values()
        ]

        return JSONResponse(content={
            "consumer": "self_similarity",
            "chunk_layers": chunk_layers,
            "methods": methods,
            "incompatible": incompatible,
        })

    # NOTE: the literal "/alignments" routes MUST be declared before the generic
    # "/{metric}" route below — Starlette matches in declaration order, so a
    # generic-first ordering would shadow "/cs/{cs}/alignments" (metric="alignments").
    @app.get("/api/projects/{project_id}/self_similarity/cs/{chunk_size}/alignments")
    async def self_similarity_chunk_alignments(project_id: str, chunk_size: int) -> JSONResponse:
        """Serve per-chunk-size alignment records."""
        project_dir = _safe_project_dir(workspace, project_id)
        aln_path = project_dir / "signals" / f"self_similarity_cs{chunk_size}" / "alignments.json"
        if not aln_path.exists():
            return JSONResponse(content=[])
        return JSONResponse(content=json.loads(aln_path.read_text(encoding="utf-8")))

    @app.get("/api/projects/{project_id}/self_similarity/cs/{chunk_size}/alignments/{metric}")
    async def self_similarity_chunk_alignments_metric(
        project_id: str, chunk_size: int, metric: str
    ) -> JSONResponse:
        """Serve per-metric alignment records for a specific chunk size."""
        from palimpsest.tracks.self_similarity import METRICS
        if metric not in METRICS:
            raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")
        project_dir = _safe_project_dir(workspace, project_id)
        aln_path = (
            project_dir / "signals" / f"self_similarity_cs{chunk_size}" / f"alignments_{metric}.json"
        )
        if not aln_path.exists():
            return JSONResponse(content=[])
        return JSONResponse(content=json.loads(aln_path.read_text(encoding="utf-8")))

    @app.get("/api/projects/{project_id}/self_similarity/cs/{chunk_size}/{metric}")
    async def self_similarity_chunk_data(project_id: str, chunk_size: int, metric: str) -> FileResponse:
        """Serve per-chunk-size similarity matrix binary."""
        from palimpsest.tracks.self_similarity import METRICS
        if metric not in METRICS:
            raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")
        project_dir = _safe_project_dir(workspace, project_id)
        bin_path = project_dir / "signals" / f"self_similarity_cs{chunk_size}" / f"{metric}.bin"
        if not bin_path.exists():
            raise HTTPException(status_code=404, detail=f"No data for chunk_size={chunk_size}, metric={metric}")
        return FileResponse(bin_path, media_type="application/octet-stream")

    @app.get("/api/projects/{project_id}/embeddings/status")
    async def embeddings_status(project_id: str) -> JSONResponse:
        """Check if paragraph embeddings exist for a project."""
        project_dir = _safe_project_dir(workspace, project_id)
        embeddings_db = project_dir / "cache" / "embeddings.db"
        if not embeddings_db.exists():
            return JSONResponse(content={"available": False, "count": 0})

        from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

        store = SqliteVecStore.open_existing(embeddings_db)
        try:
            count = len(store.stored_indices())
        finally:
            store.close()
        return JSONResponse(content={"available": True, "count": count})

    @app.post("/api/projects/{project_id}/embeddings/compute")
    async def compute_embeddings(project_id: str) -> JSONResponse:
        """Compute paragraph embeddings via MLX or Ollama."""
        import asyncio

        project_dir = _safe_project_dir(workspace, project_id)

        job_key = f"{project_id}:_embeddings"
        if _running_jobs.get(job_key, {}).get("status") == "running":
            return JSONResponse(content={"status": "already_running"})

        from palimpsest.project import Project
        from palimpsest.services.embedding import embed_paragraphs_async
        from palimpsest.vectorstore.sqlite_vec import SqliteVecStore

        project = Project.load(project_dir)
        embeddings_db = project_dir / "cache" / "embeddings.db"

        # Probe for embedding dimension
        import httpx as httpx_sync

        dim: int | None = None
        try:
            resp = httpx_sync.post(
                "http://localhost:8000/embed",
                json={"text": "probe"},
                timeout=3.0,
            )
            if resp.status_code == 200 and "embedding" in resp.json():
                dim = len(resp.json()["embedding"])
        except (httpx_sync.ConnectError, httpx_sync.TimeoutException):
            pass

        if dim is None:
            try:
                from palimpsest.services.manager import OllamaManager

                mgr = OllamaManager()
                client = mgr.embedding_client()
                probe = client.embed_one("probe")
                if probe is not None:
                    dim = len(probe)
            except Exception:
                pass

        if dim is None:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "error": "No embedding service available (need MLX on :8000 or Ollama on :11434)"},
            )

        _running_jobs[job_key] = {"status": "running", "track": "_embeddings"}

        async def run() -> None:
            try:
                embeddings_db.parent.mkdir(parents=True, exist_ok=True)
                store = SqliteVecStore(embeddings_db, dim=dim)
                try:
                    count, backend = await embed_paragraphs_async(
                        project, store, batch_size=32, max_concurrent=4,
                    )
                finally:
                    store.close()
                _running_jobs[job_key] = {
                    "status": "completed",
                    "track": "_embeddings",
                    "count": count,
                    "backend": backend,
                }
            except Exception as exc:
                _running_jobs[job_key] = {"status": "failed", "track": "_embeddings", "error": str(exc)}
            finally:
                asyncio.get_running_loop().call_later(30.0, lambda: _running_jobs.pop(job_key, None))

        asyncio.create_task(run())
        return JSONResponse(content={"status": "started", "dim": dim})

    # ---- P3: embedding-as-analysis + visualization suite (FR-3/6/13/14, NFR-4) ----------------------
    # On-read semantic-space toolkit over a persisted embedding layer (cache/embeddings_{label}.db).
    # Every binary endpoint emits the DotplotView wire contract (little-endian Float32Array, C order);
    # N comes from the embedding manifest's dimensions, so the frontend reuses one fetch path. All
    # compute is deterministic and numpy-only (palimpsest.vectorstore.analytics) — nothing here calls an
    # embedding service or persists a new artifact.

    # Rough local-embedding throughput (chunks/sec) for the pre-run estimate only. Deliberately
    # conservative and provider-agnostic — the estimate is a guard against surprise cost (NFR-4), not a
    # benchmark; the response says so.
    _EST_CHUNKS_PER_SEC = 40.0

    @app.get("/api/projects/{project_id}/embedding/estimate")
    async def embedding_estimate(project_id: str, chunk_label: str = Query(...)) -> JSONResponse:
        """Pre-run cost estimate (NFR-4): chunk_count → vector_count → rough wall-time, read from the
        *chunk* layer before any embedding exists. Embedding never auto-runs; this is the confirmation
        the param dialog shows first. Keyed by chunk_label (not an embedding label) because the
        embedding layer it would produce does not exist yet — a deliberate deviation from the plan's
        literal ``/embedding/{label}/estimate`` path, which cannot apply before the run."""
        project_dir = _safe_project_dir(workspace, project_id)
        chunk_path = project_dir / "signals" / f"chunking_{chunk_label}.json"
        if not chunk_path.exists():
            raise HTTPException(
                status_code=404, detail=f"chunk layer 'chunking_{chunk_label}' not found"
            )
        manifest = json.loads(chunk_path.read_text())
        chunk_texts = manifest.get("metadata", {}).get("chunk_texts", [])
        n = len(chunk_texts)
        return JSONResponse(content={
            "chunk_label": chunk_label,
            "chunk_count": n,
            "vector_count": n,
            "total_chars": sum(len(t) for t in chunk_texts),
            "estimated_seconds": round(n / _EST_CHUNKS_PER_SEC, 1),
            "note": "rough estimate; actual time depends on provider, model, and batch size",
        })

    @app.get("/api/projects/{project_id}/embedding/{label}/projection")
    async def embedding_projection(
        project_id: str, label: str, method: str = Query("pca")
    ) -> Response:
        """2-D projection of the embedding layer → N×2 little-endian Float32Array. PCA (numpy,
        deterministic, zero new deps) is the only method; UMAP is deferred to Vision OQ#4 and rejected
        loudly rather than silently substituted."""
        if method != "pca":
            raise HTTPException(
                status_code=400,
                detail=f"projection method {method!r} unsupported; only 'pca' (UMAP deferred, OQ#4)",
            )
        from palimpsest.vectorstore import analytics
        project_dir = _safe_project_dir(workspace, project_id)
        coords = analytics.pca_projection(_load_embedding_vectors(project_dir, label), 2)
        return Response(content=_f32_le_bytes(coords), media_type="application/octet-stream")

    @app.get("/api/projects/{project_id}/embedding/{label}/distances")
    async def embedding_distances(
        project_id: str, label: str, kind: str = Query("nn"), bins: int = Query(50, ge=1, le=500)
    ) -> JSONResponse:
        """Cosine-distance histogram (fixed range [0,2]). ``nn`` (each chunk's nearest-neighbour
        distance, O(N²) scan, scalable) or ``pairwise`` (all pairs, sampled above the budget). When
        sampled, ``sampled_pairs`` < ``total_pairs`` reports the realised count — no silent cap."""
        if kind not in ("pairwise", "nn"):
            raise HTTPException(status_code=400, detail=f"distance kind {kind!r} must be pairwise|nn")
        from palimpsest.vectorstore import analytics
        project_dir = _safe_project_dir(workspace, project_id)
        vectors = _load_embedding_vectors(project_dir, label)
        n = int(vectors.shape[0])
        if kind == "pairwise":
            edges, counts, sampled = analytics.pairwise_distance_histogram(vectors, bins=bins)
            total = n * (n - 1) // 2
            if sampled < total:
                logger.info("embedding distances: sampled %d of %d pairs for layer %s",
                            sampled, total, label)
            return JSONResponse(content={
                "kind": "pairwise", "bins": bins, "edges": edges.tolist(),
                "counts": counts.tolist(), "sampled_pairs": int(sampled), "total_pairs": total,
            })
        edges, counts, count = analytics.nn_distance_histogram(vectors, bins=bins)
        return JSONResponse(content={
            "kind": "nn", "bins": bins, "edges": edges.tolist(),
            "counts": counts.tolist(), "count": int(count),
        })

    @app.get("/api/projects/{project_id}/embedding/{label}/heatmap")
    async def embedding_heatmap(
        project_id: str, label: str, order: str = Query("chunk"),
        k: int = Query(8, ge=1, le=256), seed: int = Query(0),
    ) -> Response:
        """Cosine-similarity matrix → little-endian Float32Array (C order). ``order=chunk`` keeps chunk
        order; ``order=cluster`` permutes rows/cols by k-means cluster (returned in ``X-Matrix-Order``
        so the frontend can map cells back to chunks). Above analytics.HEATMAP_MAX_N the matrix is
        block-reduced (``X-Matrix-Reduced: 1``); cluster order is not applied to a reduced matrix
        because reduced cells are index-blocks, not chunks. ``X-Matrix-N`` is the served dimension."""
        if order not in ("chunk", "cluster"):
            raise HTTPException(status_code=400, detail=f"heatmap order {order!r} must be chunk|cluster")
        import numpy as np

        from palimpsest.vectorstore import analytics
        project_dir = _safe_project_dir(workspace, project_id)
        vectors = _load_embedding_vectors(project_dir, label)
        n = int(vectors.shape[0])
        order_arr = None
        if order == "cluster" and n <= analytics.HEATMAP_MAX_N:
            labels, _ = analytics.kmeans(vectors, k, seed=seed)
            order_arr = np.argsort(labels, kind="stable")
        matrix, served_order = analytics.similarity_matrix(vectors, order=order_arr)
        headers = {
            "X-Matrix-N": str(matrix.shape[0]),
            "X-Matrix-Reduced": "1" if matrix.shape[0] < n else "0",
        }
        if served_order is not None:
            headers["X-Matrix-Order"] = ",".join(map(str, served_order.tolist()))
        return Response(
            content=_f32_le_bytes(matrix), media_type="application/octet-stream", headers=headers,
        )

    @app.get("/api/projects/{project_id}/embedding/{label}/clusters")
    async def embedding_clusters(
        project_id: str, label: str, k: int = Query(8, ge=1, le=256), seed: int = Query(0),
    ) -> JSONResponse:
        """k-means cluster id per chunk (chunk order) + cluster sizes. ``k`` is clamped to the chunk
        count; ``effective_k`` reports the realised cluster count vs the requested ``k``. Deterministic
        for a given seed (LOCK policy: seed is an explicit param, not hidden)."""
        from palimpsest.vectorstore import analytics
        project_dir = _safe_project_dir(workspace, project_id)
        labels, sizes = analytics.kmeans(_load_embedding_vectors(project_dir, label), k, seed=seed)
        return JSONResponse(content={
            "requested_k": k, "effective_k": len(sizes), "seed": seed,
            "labels": labels.tolist(), "sizes": sizes,
        })

    @app.get("/api/projects/{project_id}/embedding/{label}/lane")
    async def embedding_lane(
        project_id: str, label: str, encoding: str = Query("nn-density"),
        k: int = Query(8, ge=1, le=256), seed: int = Query(0),
    ) -> Response:
        """In-text embedding-lane scalar per chunk (FR-13) → little-endian Float32Array, chunk order.
        ``pc1`` (first PC), ``cluster`` (k-means id), or ``nn-density`` (inverse nearest-neighbour
        distance)."""
        if encoding not in ("cluster", "pc1", "nn-density"):
            raise HTTPException(
                status_code=400, detail=f"lane encoding {encoding!r} must be cluster|pc1|nn-density"
            )
        from palimpsest.vectorstore import analytics
        project_dir = _safe_project_dir(workspace, project_id)
        lane = analytics.lane_encoding(
            _load_embedding_vectors(project_dir, label), encoding, k=k, seed=seed
        )
        return Response(content=_f32_le_bytes(lane), media_type="application/octet-stream")

    # ---- P6: per-chunk-layer distributions (FR-14) -------------------------------------------------
    @app.get("/api/projects/{project_id}/chunking/{label}/stats")
    async def chunking_layer_stats(
        project_id: str, label: str,
        bins: int = Query(30, ge=2, le=200), tolerance: int = Query(0, ge=0, le=100000),
    ) -> JSONResponse:
        """Per-chunk-layer distribution data behind the stats panel (FR-14): word/char length
        histograms + ECDFs, by-element-type length groups (violins), and the chunk-boundary-vs-
        structural alignment breakdown. Computed on-read from the layer's ``segment_offsets`` + the
        structural layout — deterministic, numpy-only. Distinct from the text-level ProfileTrack
        (P4): these describe *this chunk layer*, sharing tokenization but not endpoints."""
        from palimpsest.analysis import chunk_stats
        project_dir = _safe_project_dir(workspace, project_id)
        manifest = json.loads(_chunk_signals_path(project_dir, label).read_text())
        inputs = _chunk_layer_stats_inputs(project_dir, manifest)
        payload = chunk_stats.compute_chunk_layer_stats(**inputs, bins=bins, tolerance=tolerance)
        payload["label"] = label
        return JSONResponse(content=payload)

    # ---- P4: substrate integrity report (FR-9) -----------------------------------------------------
    @app.get("/api/projects/{project_id}/integrity")
    async def integrity_report(project_id: str) -> JSONResponse:
        """Run the substrate contract validators and report pass/violation/na per invariant. Reuses the
        exact validator functions the producers call (no re-implementation), so the report cannot drift
        from the real contract."""
        from palimpsest.analysis.integrity import run_integrity_report
        from palimpsest.project import Project

        project = Project.load(_safe_project_dir(workspace, project_id))
        return JSONResponse(content=run_integrity_report(project))

    # ---- P4: positional/lexical analytics (FR-10) --------------------------------------------------
    # Transient query endpoints (KWIC / collocations / duplicate-finder) + dispersion. All compute on
    # the analyzable view and return original-coordinate spans; none persist a layer (nothing downstream
    # depends on them). NOTE: the plan also specifies dispersion as a persisted layer-keyed *annotation*
    # track (a lexical barcode). That is deferred — label-keyed annotation persistence needs new runner
    # plumbing, and the barcode render is a P5 concern. The dispersion endpoint here returns the same
    # hit-span data a barcode would render, so P5 is unblocked.

    @app.get("/api/projects/{project_id}/kwic")
    async def kwic(
        project_id: str, term: str = Query(..., min_length=1),
        window: int = Query(40, ge=0, le=500), limit: int = Query(200, ge=1, le=2000),
    ) -> JSONResponse:
        """Keyword-in-context concordance: whole-word, case-insensitive occurrences of ``term`` with
        ``window`` characters of surrounding context. ``start``/``end`` are original coordinates; the
        ``left``/``keyword``/``right`` context strings come from the analyzable text. ``total`` reports
        the full match count even when ``limit`` truncates the returned rows (no silent cap)."""
        project_dir = _safe_project_dir(workspace, project_id)
        _, atext, omap = _analysis_text(project_dir)
        import re as _re
        rows: list[dict[str, Any]] = []
        total = 0
        for m in _re.finditer(rf"\b{_re.escape(term)}\b", atext, _re.IGNORECASE):
            total += 1
            if len(rows) >= limit:
                continue
            mapped = omap.inverse_span(m.start(), m.end())
            if mapped is None:
                continue
            rows.append({
                "start": mapped[0], "end": mapped[1],
                "left": atext[max(0, m.start() - window):m.start()],
                "keyword": m.group(),
                "right": atext[m.end():m.end() + window],
            })
        return JSONResponse(content={"term": term, "total": total, "returned": len(rows), "rows": rows})

    @app.get("/api/projects/{project_id}/collocations")
    async def collocations(
        project_id: str, window: int = Query(2, ge=1, le=10),
        min_count: int = Query(3, ge=1), top: int = Query(50, ge=1, le=500),
    ) -> JSONResponse:
        """Within-window bigram associations (PMI + Dunning's G²) over the analyzable token stream →
        ``[[a, b, pmi, log_likelihood, count], …]`` ranked by count."""
        project_dir = _safe_project_dir(workspace, project_id)
        from palimpsest.analysis import textstats
        _, atext, _ = _analysis_text(project_dir)
        cols = textstats.collocations(
            textstats.tokenize(atext), window=window, min_count=min_count, top=top
        )
        return JSONResponse(content={"window": window, "min_count": min_count, "collocations": cols})

    @app.get("/api/projects/{project_id}/duplicates")
    async def duplicates(
        project_id: str, min_words: int = Query(5, ge=2, le=50),
        min_occurrences: int = Query(2, ge=2, le=50),
    ) -> JSONResponse:
        """Near-duplicate / repeated-passage finder: surfaces the same exact-repeat signal the masking
        layer uses (``tracks.repeats.detect_repeats``), with each repeated span remapped to original
        coordinates. Descriptive only."""
        project_dir = _safe_project_dir(workspace, project_id)
        from palimpsest.tracks.repeats import detect_repeats
        _, atext, omap = _analysis_text(project_dir)
        phrases, intervals = detect_repeats(
            atext, min_words=min_words, min_occurrences=min_occurrences
        )
        spans: list[list[int]] = []
        for s, e in intervals:
            mapped = omap.inverse_span(s, e)
            if mapped is not None:
                spans.append([mapped[0], mapped[1]])
        return JSONResponse(content={
            "min_words": min_words, "min_occurrences": min_occurrences,
            "phrase_count": len(phrases), "phrases": sorted(phrases), "spans": spans,
        })

    @app.get("/api/projects/{project_id}/dispersion")
    async def dispersion(project_id: str, term: str = Query(..., min_length=1)) -> JSONResponse:
        """Lexical dispersion of ``term``: every whole-word occurrence as an original-coordinate
        ``[start, end]`` span, plus the document length, so the frontend can draw a dispersion barcode
        (where in the text the term clusters)."""
        project_dir = _safe_project_dir(workspace, project_id)
        orig_len, atext, omap = _analysis_text(project_dir)
        spans = _term_spans_original(term, atext, omap)
        return JSONResponse(content={
            "term": term, "count": len(spans), "doc_length": orig_len, "spans": spans,
        })

    async def _ingest_and_compute(
        src_path: Path, title: str, author: str, year: int, overwrite: bool = False,
        source_name: str | None = None,
    ) -> dict[str, Any]:
        """Ingest a source file and compute all tracks (legacy one-shot path)."""
        project = await _ingest_only(src_path, title, author, year, overwrite, source_name)
        failed = await _compute_tracks(project)
        return _ingest_summary(project, staged=False, failed_tracks=failed)

    async def _ingest_only(
        src_path: Path, title: str, author: str, year: int, overwrite: bool = False,
        source_name: str | None = None,
    ) -> Any:
        """Step 1: structural ingest only (text/segments/sections/endnotes). No analysis.

        ``source_name`` carries the original filename when ``src_path`` is a temp
        upload, so the project's identity (slug + source_file) tracks the real file.
        """
        import asyncio

        from palimpsest.project import ingest_file

        return await asyncio.to_thread(
            ingest_file, src_path, workspace,
            title=title, author=author, year=year, overwrite=overwrite,
            source_name=source_name,
        )

    def _ingest_summary(
        project: Any, *, staged: bool, failed_tracks: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        meta = json.loads((project.path / "metadata.json").read_text())
        track_count = len(list((project.path / "tracks").glob("*.jsonl")))
        out: dict[str, Any] = {
            "status": "ok",
            "project_id": project.metadata.id,
            "title": project.metadata.title,
            "word_count": project.metadata.word_count,
            "track_count": track_count,
            "staged": staged,
            "metadata": meta,
        }
        if failed_tracks:
            out["failed_tracks"] = failed_tracks
        return out

    async def _compute_tracks(project: Any) -> list[dict[str, str]]:
        """Step 5: run every analysis extractor over the masked-resolved analyzable stream.

        The whole batch runs against a single analysis view, so all intermediate cross-track data
        (e.g. self_similarity's offsets consumed by boundary_detection) lives in one consistent
        analyzable coordinate space. A final pass then remaps every output — annotation tracks and
        signal manifests/alignments — back to original document coordinates."""
        import asyncio

        from palimpsest.annotation.serializer import write_track
        from palimpsest.tracks.registry import TrackRegistry

        failed_tracks: list[dict[str, str]] = []
        registry = TrackRegistry.discover()
        view, omap = project.analysis_view()
        try:
            for extractor_cls in registry.dependency_order():
                extractor = extractor_cls()
                try:
                    result = await asyncio.to_thread(extractor.extract, view)
                    if extractor.output_type == "annotation" and isinstance(result, list):
                        write_track(view.path / "tracks" / f"{extractor.name}.jsonl", result)
                    manifest_dir = view.path / "manifests"
                    manifest_dir.mkdir(exist_ok=True)
                    (manifest_dir / f"{extractor.name}.manifest.json").write_text(
                        json.dumps(extractor.manifest(), indent=2), encoding="utf-8",
                    )
                except Exception as exc:
                    logger.warning("Track %s failed: %s", extractor.name, exc)
                    failed_tracks.append({"track": extractor.name, "error": str(exc)})
            await asyncio.to_thread(_remap_project_outputs, project.path, omap)
        finally:
            view.close_analysis_view()
        return failed_tracks

    @app.get("/api/imports")
    async def list_imports() -> JSONResponse:
        """List importable book files under the configured imports/ drop folder."""
        files: list[dict[str, Any]] = []
        indexes = _imported_index(workspace)
        if imports_dir.is_dir():
            for p in sorted(imports_dir.rglob("*")):
                if not p.is_file() or p.suffix.lower() not in _IMPORT_SUFFIXES:
                    continue
                rel = p.relative_to(imports_dir)
                folder = "" if rel.parent == Path(".") else str(rel.parent)
                status, matched, title, author, isbn = _import_status(p.name, indexes)
                files.append({
                    "path": str(rel),
                    "name": p.name,
                    "folder": folder,
                    "format": p.suffix.lower().lstrip("."),
                    "size": p.stat().st_size,
                    "title": title,
                    "author": author,
                    "isbn": isbn,
                    "status": status,                 # "new" | "imported" | "version"
                    "matched_project_id": matched,     # set when imported/version
                })
        return JSONResponse(content={
            "root": str(imports_dir),
            "available": imports_dir.is_dir(),
            "files": files,
        })

    @app.post("/api/import")
    async def import_epub(
        file: UploadFile,
        title: str = "",
        author: str = "",
        year: int = 0,
        process: bool = True,
    ) -> JSONResponse:
        """Import an uploaded file. process=False stages it (ingest only, defer analysis)."""
        import tempfile

        if not file.filename or not file.filename.lower().endswith(_IMPORT_SUFFIXES):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Accepted: EPUB, TXT, PDF, HTML, Markdown",
            )

        with tempfile.NamedTemporaryFile(
            suffix=Path(file.filename).suffix, delete=False
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            if process:
                return JSONResponse(content=await _ingest_and_compute(
                    tmp_path, title, author, year, source_name=file.filename))
            project = await _ingest_only(tmp_path, title, author, year, source_name=file.filename)
            return JSONResponse(content=_ingest_summary(project, staged=True))
        except FileExistsError:
            raise HTTPException(status_code=409, detail="Project already exists")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            tmp_path.unlink(missing_ok=True)

    @app.post("/api/import/local")
    async def import_local(req: LocalImportRequest) -> JSONResponse:
        """Import a file from the imports/ folder. process=False stages it (ingest only)."""
        src = _safe_import_path(imports_dir, req.path)
        if src.suffix.lower() not in _IMPORT_SUFFIXES:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        try:
            if req.layout_path:
                # Ingest the text, then apply the stored gold map verbatim (no auto-detect).
                project = await _ingest_only(src, req.title, req.author, req.year, req.overwrite)
                summary = _ingest_summary(project, staged=False)
                summary["gold_map"] = _apply_gold_map(project, req.layout_path)
                return JSONResponse(content=summary)
            if req.process:
                return JSONResponse(
                    content=await _ingest_and_compute(
                        src, req.title, req.author, req.year, req.overwrite
                    )
                )
            project = await _ingest_only(src, req.title, req.author, req.year, req.overwrite)
            return JSONResponse(content=_ingest_summary(project, staged=True))
        except FileExistsError:
            raise HTTPException(status_code=409, detail="Project already exists")
        except HTTPException:
            raise  # preserve 400/404/409 from gold-map validation (don't re-wrap as 500)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/import/local/stream")
    async def import_local_stream(req: LocalImportRequest) -> StreamingResponse:
        """Staged import with live progress as Server-Sent Events.

        Emits ``progress`` events ({phase, message, pct}) at each ingest phase,
        then a terminal ``done`` (ingest summary) or ``error`` ({detail, status}).
        The ingest runs in a worker thread; its progress callback hands events
        back to the event loop through a thread-safe queue.
        """
        from palimpsest.project import ingest_file

        src = _safe_import_path(imports_dir, req.path)
        if src.suffix.lower() not in _IMPORT_SUFFIXES:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _on_progress(phase: str, message: str, fraction: float) -> None:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "progress", "phase": phase, "message": message, "pct": round(fraction * 100)},
            )

        async def _run() -> None:
            try:
                project = await asyncio.to_thread(
                    ingest_file, src, workspace,
                    title=req.title or src.stem, author=req.author, year=req.year,
                    overwrite=req.overwrite, progress=_on_progress,
                )
                if req.layout_path:
                    gold = await asyncio.to_thread(_apply_gold_map, project, req.layout_path)
                    summary = _ingest_summary(project, staged=False)
                    summary["gold_map"] = gold
                    await queue.put({"type": "done", **summary})
                else:
                    await queue.put({"type": "done", **_ingest_summary(project, staged=True)})
            except FileExistsError:
                await queue.put({"type": "error", "detail": "Project already exists", "status": 409})
            except HTTPException as he:
                await queue.put({"type": "error", "detail": str(he.detail), "status": he.status_code})
            except Exception as exc:  # noqa: BLE001
                logger.exception("Streamed import failed")
                await queue.put({"type": "error", "detail": str(exc), "status": 500})

        async def _events():
            task = asyncio.create_task(_run())
            try:
                while True:
                    evt = await queue.get()
                    yield f"data: {json.dumps(evt)}\n\n"
                    if evt.get("type") in ("done", "error"):
                        break
            finally:
                await task

        return StreamingResponse(
            _events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/projects/{project_id}/sections/detect")
    async def detect_sections(project_id: str) -> JSONResponse:
        """Step 2: classify the text into typed layout sections and persist them."""
        from palimpsest.layout import LayoutConfig, detect_layout_sections, load_layout, save_layout
        from palimpsest.project import Project

        project_dir = _safe_project_dir(workspace, project_id)
        project = Project.load(project_dir)
        reference = project.reference_text()
        text_len = len(reference)
        sections = detect_layout_sections(
            _layout_boundaries(project), text_len, _endnote_separator(project_dir),
            text=reference,
        )
        cfg = load_layout(project_dir) or LayoutConfig()
        cfg.sections = sections
        cfg.applied = False
        cfg.parents_computed = True  # detect_layout_sections already computed parent links
        save_layout(project_dir, cfg)
        return JSONResponse(content=_sections_payload(cfg, text_len))

    @app.get("/api/projects/{project_id}/sections")
    async def get_sections(project_id: str) -> JSONResponse:
        """Load the persisted layout config (empty default if none yet)."""
        from palimpsest.layout import LayoutConfig, load_layout, masked_intervals
        from palimpsest.project import Project

        project_dir = _safe_project_dir(workspace, project_id)
        text_len = len(Project.load(project_dir).reference_text())
        # On first load of a legacy layout, load_layout lazily backfills parent_id via an
        # O(n²) pass (then re-saves). For ~9k-section scripture layouts that is multi-second,
        # so offload it to a worker thread to keep the event loop responsive on this hot path.
        cfg = await asyncio.to_thread(load_layout, project_dir) or LayoutConfig()
        masked = masked_intervals(cfg.sections, cfg.mask_by_type, text_len,
                                  extra_masked=_verse_num_intervals(project_dir))
        return JSONResponse(content=_sections_payload(cfg, text_len, masked=masked))

    @app.put("/api/projects/{project_id}/sections")
    async def put_sections(project_id: str, req: SectionsUpdateRequest) -> JSONResponse:
        """Steps 3+4: persist user-edited section ranges, types, and mask flags."""
        from palimpsest.layout import (
            DEFAULT_MASK_BY_TYPE,
            LayoutConfig,
            LayoutSection,
            _compute_parents,
            load_layout,
            sanitize_extra_types,
            save_layout,
        )
        from palimpsest.project import Project

        project_dir = _safe_project_dir(workspace, project_id)
        text_len = len(Project.load(project_dir).reference_text())
        cfg = load_layout(project_dir) or LayoutConfig()
        cfg.sections = [LayoutSection.from_dict(s) for s in req.sections]
        _compute_parents(cfg.sections)  # user edits may change containment; refresh parent links
        cfg.parents_computed = True
        if req.extra_types is not None:
            cfg.extra_types = sanitize_extra_types(req.extra_types)
        if req.mask_by_type is not None:
            merged = dict(DEFAULT_MASK_BY_TYPE)
            for et in cfg.extra_types:  # seed custom-layer defaults before overrides
                merged[et["key"]] = bool(et.get("default_mask", True))
            merged.update(req.mask_by_type)
            cfg.mask_by_type = merged
        if req.applied is not None:
            cfg.applied = req.applied
        save_layout(project_dir, cfg)
        return JSONResponse(content=_sections_payload(cfg, text_len))

    @app.post("/api/projects/{project_id}/sections/apply")
    async def apply_sections(project_id: str) -> JSONResponse:
        """Step 5: persist the masking decision (applied=true). Analysis is NOT
        run here — the user reviews and launches analyses from the Analysis panel
        afterward, so masks are computed lazily by each extractor at run time."""
        from palimpsest.layout import LayoutConfig, load_layout, save_layout
        from palimpsest.project import Project

        project_dir = _safe_project_dir(workspace, project_id)
        cfg = load_layout(project_dir) or LayoutConfig()
        cfg.applied = True
        save_layout(project_dir, cfg)
        text_len = len(Project.load(project_dir).reference_text())
        _write_elements_track(project_dir, project_id, cfg, text_len)
        return JSONResponse(content=_sections_payload(cfg, text_len))

    @app.post("/api/projects/{project_id}/derive")
    async def derive_subtext_endpoint(project_id: str, req: DeriveRequest) -> JSONResponse:
        """Derive a subtext child project from the parent's kept extraction layers.

        The kept layers' element spans form the child text; overlapping parent layers (the
        containers, the verse-number index, annotation tracks) are remapped onto the child with
        their mask state preserved. The child is auto-linked to its parent in a collection."""
        import asyncio

        from palimpsest.derive import derive_subtext
        from palimpsest.project import Project

        parent_dir = _safe_project_dir(workspace, project_id)
        parent = Project.load(parent_dir)
        try:
            child, child_cfg, summary = await asyncio.to_thread(
                derive_subtext,
                parent,
                workspace,
                extraction_types=req.extraction_types,
                excluded_ids=req.excluded_ids,
                include_container_ids=req.include_container_ids,
                title=req.title,
                author=req.author,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        text_len = len(child.reference_text())
        _write_elements_track(child.path, child.metadata.id, child_cfg, text_len)

        collection_id = _link_derived_collection(
            workspace, parent, child.metadata.id, req.collection_id
        )
        summary["collection_id"] = collection_id
        return JSONResponse(content=summary)

    @app.post("/api/projects/{project_id}/derive/stream")
    async def derive_subtext_stream(project_id: str, req: DeriveRequest) -> StreamingResponse:
        """Derive a subtext with live per-phase progress as Server-Sent Events.

        Emits ``progress`` events ({phase, message, pct}) as the kept layers are assembled and the
        parent's overlapping layers remapped, then a terminal ``done`` (derive summary +
        collection_id) or ``error`` ({detail, status}). The derive runs in a worker thread; its
        progress callback hands events back to the event loop through a thread-safe queue (mirrors
        the streamed import endpoint)."""
        from palimpsest.derive import derive_subtext
        from palimpsest.project import Project

        parent_dir = _safe_project_dir(workspace, project_id)
        parent = Project.load(parent_dir)

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _on_progress(phase: str, message: str, fraction: float) -> None:
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "progress", "phase": phase, "message": message, "pct": round(fraction * 100)},
            )

        async def _run() -> None:
            try:
                child, child_cfg, summary = await asyncio.to_thread(
                    derive_subtext,
                    parent,
                    workspace,
                    extraction_types=req.extraction_types,
                    excluded_ids=req.excluded_ids,
                    include_container_ids=req.include_container_ids,
                    title=req.title,
                    author=req.author,
                    progress=_on_progress,
                )
                await queue.put({"type": "progress", "phase": "elements",
                                 "message": "Writing elements track…", "pct": 96})
                text_len = len(child.reference_text())
                _write_elements_track(child.path, child.metadata.id, child_cfg, text_len)
                collection_id = _link_derived_collection(
                    workspace, parent, child.metadata.id, req.collection_id
                )
                summary["collection_id"] = collection_id
                await queue.put({"type": "done", **summary})
            except ValueError as exc:
                await queue.put({"type": "error", "detail": str(exc), "status": 400})
            except Exception as exc:  # noqa: BLE001
                logger.exception("Streamed derive failed")
                await queue.put({"type": "error", "detail": str(exc), "status": 500})

        async def _events():
            task = asyncio.create_task(_run())
            try:
                while True:
                    evt = await queue.get()
                    yield f"data: {json.dumps(evt)}\n\n"
                    if evt.get("type") in ("done", "error"):
                        break
            finally:
                await task

        return StreamingResponse(
            _events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── Collections API ──

    @app.get("/api/collections")
    async def list_collections() -> JSONResponse:
        """List all collections with member counts."""
        from palimpsest.collections import load_collections

        cols = load_collections(workspace)
        return JSONResponse(content=[{**c, "project_count": len(c.get("project_ids", []))} for c in cols])

    @app.post("/api/collections")
    async def create_collection_endpoint(req: CollectionRequest) -> JSONResponse:
        from palimpsest.collections import create_collection

        col = create_collection(workspace, req.label, req.description, req.project_ids, kind="manual")
        return JSONResponse(content=col)

    @app.get("/api/collections/{collection_id}")
    async def get_collection_endpoint(collection_id: str) -> JSONResponse:
        """A collection plus lightweight metadata for each member project."""
        from palimpsest.collections import get_collection

        col = get_collection(workspace, collection_id)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        members = []
        for pid in col.get("project_ids", []):
            meta_path = workspace / pid / "metadata.json"
            if meta_path.exists():
                m = json.loads(meta_path.read_text(encoding="utf-8"))
                members.append({
                    "id": pid, "title": m.get("title", pid), "author": m.get("author"),
                    "parent_project_id": m.get("parent_project_id"),
                    "cover": _find_cover_url(workspace / pid, m),
                })
        return JSONResponse(content={**col, "members": members})

    @app.put("/api/collections/{collection_id}")
    async def update_collection_endpoint(collection_id: str, req: CollectionRequest) -> JSONResponse:
        from palimpsest.collections import update_collection

        col = update_collection(workspace, collection_id, label=req.label, description=req.description)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return JSONResponse(content=col)

    @app.delete("/api/collections/{collection_id}")
    async def delete_collection_endpoint(collection_id: str) -> JSONResponse:
        from palimpsest.collections import delete_collection

        if not delete_collection(workspace, collection_id):
            raise HTTPException(status_code=404, detail="Collection not found")
        return JSONResponse(content={"status": "deleted", "id": collection_id})

    @app.post("/api/collections/{collection_id}/projects/{project_id}")
    async def add_collection_member(collection_id: str, project_id: str) -> JSONResponse:
        from palimpsest.collections import add_member

        col = add_member(workspace, collection_id, project_id)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return JSONResponse(content=col)

    @app.delete("/api/collections/{collection_id}/projects/{project_id}")
    async def remove_collection_member(collection_id: str, project_id: str) -> JSONResponse:
        from palimpsest.collections import remove_member

        col = remove_member(workspace, collection_id, project_id)
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return JSONResponse(content=col)

    @app.get("/api/projects/{project_id}/lattice")
    async def project_lattice_endpoint(project_id: str) -> JSONResponse:
        """Inverse navigation for a project (FR-24): its Work tag, parent + derived children (subtext
        edge), edition siblings (shared Work), and the collections it belongs to."""
        from palimpsest.collections_ops import project_lattice

        try:
            return JSONResponse(content=project_lattice(workspace, project_id))
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @app.put("/api/collections/{collection_id}/roles/{project_id}")
    async def set_collection_role(
        collection_id: str, project_id: str, req: RoleRequest
    ) -> JSONResponse:
        """Assign a member's collection-local role (FR-25). Fails 400 on an invalid role or a non-member."""
        from palimpsest.collections import set_member_role

        try:
            col = set_member_role(workspace, collection_id, project_id, req.role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if col is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return JSONResponse(content=col)

    @app.get("/api/collections/{collection_id}/congruence")
    async def collection_congruence(
        collection_id: str, metric: str = "cosine", embedding_label: str | None = None
    ) -> JSONResponse:
        """Per-metric congruence across a collection's members — the compatibility-badge data
        (FR-27/FR-39): each member's congruence key, the congruent cohorts, members missing the
        required layer, and whether the whole collection is comparable on the metric."""
        from palimpsest.collections_ops import congruence_report

        try:
            return JSONResponse(
                content=congruence_report(workspace, collection_id, metric, embedding_label)
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Collection not found")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # ── Corpus graph API (C3, reference-free pangenome model) ──

    @app.post("/api/collections/{collection_id}/corpus-graph")
    async def build_collection_corpus_graph(
        collection_id: str, anchor_trim: float = 0.0
    ) -> JSONResponse:
        """Assemble + persist the reference-free corpus graph (C3, FR-31) from the collection's
        computed pairwise edges. Returns the pangenome summary (core/shell/singleton counts plus the
        pairs that did and did not contribute edges).

        ``anchor_trim`` (C6a anchor honesty): when ``> 0``, trims each aligned block inward past
        boundary cells below that cross-similarity before the homology union, so a trailing/leading
        mismatch no longer pulls a disjoint passage into a core/shell component."""
        from palimpsest.corpus_graph import build_corpus_graph, write_corpus_graph

        try:
            graph = build_corpus_graph(workspace, collection_id, anchor_trim=anchor_trim)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        write_corpus_graph(workspace, collection_id, graph)
        return JSONResponse(content={"summary": graph.summary, "provenance": graph.provenance})

    @app.get("/api/collections/{collection_id}/corpus-graph")
    async def get_collection_corpus_graph(collection_id: str) -> JSONResponse:
        """Read the persisted corpus graph (nodes, edges, components, summary). 404 until built."""
        from palimpsest.corpus_graph import read_corpus_graph

        graph = read_corpus_graph(workspace, collection_id)
        if graph is None:
            raise HTTPException(status_code=404, detail="Corpus graph not built; POST to build it first")
        return JSONResponse(content=graph.to_dict())

    @app.get("/api/collections/{collection_id}/corpus-graph/projection")
    async def project_collection_corpus_graph(collection_id: str, root: str) -> JSONResponse:
        """Project the corpus graph onto a chosen root member's paragraph frame (the synteny lens —
        derived on demand, never stored ground truth)."""
        from palimpsest.corpus_graph import project_to_root, read_corpus_graph

        graph = read_corpus_graph(workspace, collection_id)
        if graph is None:
            raise HTTPException(status_code=404, detail="Corpus graph not built; POST to build it first")
        try:
            return JSONResponse(content=project_to_root(graph, root))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/collections/{collection_id}/phyletic-tree")
    async def collection_phyletic_tree(collection_id: str, root: str | None = None) -> JSONResponse:
        """The phyletic/stemma tree over the corpus graph's distance structure (C4, FR-38): pangenome
        Jaccard distances, a neighbor-joining tree, and a suggested root (the most component-complete
        member) the caller may override with ``?root=``."""
        from palimpsest.corpus_graph import phyletic_tree, read_corpus_graph

        graph = read_corpus_graph(workspace, collection_id)
        if graph is None:
            raise HTTPException(status_code=404, detail="Corpus graph not built; POST to build it first")
        try:
            return JSONResponse(content=phyletic_tree(graph, root))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/collections/{collection_id}/corpus-analyses")
    async def collection_corpus_analyses(
        collection_id: str, duplicate_threshold: float = 0.15, top_terms: int = 25
    ) -> JSONResponse:
        """Corpus-level analyses over the persisted graph + member texts (C6a, FR-31): cross-member
        boilerplate / IDF, near-duplicate clusters over the pangenome distance, and undirected
        diffusion/spread (breadth across members — never a directional influence claim)."""
        from palimpsest.corpus_graph import corpus_analyses, read_corpus_graph

        graph = read_corpus_graph(workspace, collection_id)
        if graph is None:
            raise HTTPException(status_code=404, detail="Corpus graph not built; POST to build it first")
        return JSONResponse(content=corpus_analyses(
            workspace, graph, duplicate_threshold=duplicate_threshold, top_terms=top_terms))

    @app.post("/api/collections/{collection_id}/probe")
    async def collection_probe(collection_id: str, request: ProbeRequest) -> JSONResponse:
        """R(q, Corpus): rank corpus passages against a query over the shared embedding space (C6b,
        FR-31). Query is either ``q`` text (embedded here, then checked into the corpus's space) or a
        ``ref_project``/``ref_chunk`` passage already in the corpus (service-free). Gated by the C1
        metric-congruence contract — fail-loud (409) on incongruent members or a mismatched query
        space, never a silent cross-key probe."""
        from palimpsest.collections_ops import MetricCongruenceError
        from palimpsest.collections_probe import (
            embed_probe_query,
            probe_corpus,
            query_vector_from_ref,
        )

        has_text = bool(request.q and request.q.strip())
        has_ref = request.ref_project is not None and request.ref_chunk is not None
        if has_text == has_ref:
            raise HTTPException(
                status_code=400,
                detail="provide exactly one query source: 'q' (text) or 'ref_project'+'ref_chunk'",
            )
        query_fingerprint: str | None = None
        try:
            if has_text:
                if not (request.provider and request.endpoint and request.model):
                    raise HTTPException(
                        status_code=400,
                        detail="text query requires 'provider', 'endpoint' and 'model' to embed it",
                    )
                query_vector, query_fingerprint = embed_probe_query(
                    request.q, provider=request.provider,
                    endpoint=request.endpoint, model=request.model,
                )
            else:
                query_vector = query_vector_from_ref(
                    workspace, request.ref_project, int(request.ref_chunk),
                    embedding_label=request.embedding_label,
                )
            result = probe_corpus(
                workspace, collection_id, query_vector,
                metric=request.metric, embedding_label=request.embedding_label,
                k=request.k, per_member_k=request.per_member_k,
                snippet_chars=request.snippet_chars, query_fingerprint=query_fingerprint,
            )
        except MetricCongruenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except KeyError:
            raise HTTPException(status_code=404, detail=f"collection {collection_id!r} not found")
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return JSONResponse(content=result)

    @app.post("/api/collections/{collection_id}/sweep")
    async def collection_sweep(collection_id: str, request: SweepRequest) -> JSONResponse:
        """Recall-dial sweep over the collection's member pairs (C6c, FR-35): prune the O(N×M) chunk-pair
        space at ``mode`` (exhaustive ↔ high-recall ↔ fast; ``force_exhaustive`` overrides), report
        estimated recall + pruned counts (never a silent cap), and journal to a resumable sidecar.
        Embedding metrics are congruence-gated (409). Re-POSTing the same params resumes the journal."""
        from palimpsest.collections_ops import MetricCongruenceError
        from palimpsest.collections_sweep import sweep_pairwise

        try:
            result = sweep_pairwise(
                workspace, collection_id,
                metric=request.metric, mode=request.mode,
                force_exhaustive=request.force_exhaustive,
                embedding_label=request.embedding_label,
                dense_threshold=request.dense_threshold, resume=request.resume,
            )
        except MetricCongruenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except KeyError:
            raise HTTPException(status_code=404, detail=f"collection {collection_id!r} not found")
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return JSONResponse(content=result)

    @app.get("/api/collections/{collection_id}/sweep/{run_id}")
    async def collection_sweep_journal(collection_id: str, run_id: str) -> JSONResponse:
        """The persisted run journal for a sweep (C6c): full per-pair candidate sets + progress. 404 if
        no such run — the run_id is content-addressed from the sweep params."""
        from palimpsest.collections_sweep import read_sweep_journal

        journal = read_sweep_journal(workspace, collection_id, run_id)
        if journal is None:
            raise HTTPException(status_code=404, detail=f"no sweep run {run_id!r} for {collection_id!r}")
        return JSONResponse(content=journal)

    # ── Cross-text masking, tracks & liftover (C5, FR-29/30/42) ──

    @app.get("/api/collections/{collection_id}/corpus-repeats")
    async def collection_corpus_repeats(
        collection_id: str,
        min_members: int = 2,
        min_words: int = 3,
        max_phrase_len: int = 7,
    ) -> JSONResponse:
        """Phrases recurring across ``>= min_members`` members, with per-member intervals (FR-29). A
        corpus-scale generalisation of Wave-0 repeats: a phrase appearing once per member is found here
        though no single text repeats it."""
        from palimpsest.collections_masking import corpus_repeats

        try:
            return JSONResponse(content=corpus_repeats(
                workspace, collection_id,
                min_members=min_members, min_words=min_words, max_phrase_len=max_phrase_len,
            ))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/collections/{collection_id}/low-correspondence")
    async def collection_low_correspondence(collection_id: str) -> JSONResponse:
        """Per-member char spans that aligned to no other member — the corpus graph's singletons.
        404-equivalent (400) until the graph is built."""
        from palimpsest.collections_masking import low_correspondence_intervals

        try:
            return JSONResponse(content=low_correspondence_intervals(workspace, collection_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/collections/{collection_id}/cross-text-mask/{member}")
    async def collection_cross_text_mask(
        collection_id: str,
        member: str,
        repeats: bool = True,
        low_correspondence: bool = True,
        min_members: int = 2,
    ) -> JSONResponse:
        """A member's cross-text mask (corpus-repeat ∪ low-correspondence), original-coordinate
        intervals ready for ``extra_masked`` (FR-29)."""
        from palimpsest.collections_masking import cross_text_mask

        try:
            return JSONResponse(content=cross_text_mask(
                workspace, collection_id, member,
                include_repeats=repeats, include_low_correspondence=low_correspondence,
                min_members=min_members,
            ))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/collections/{collection_id}/root-track")
    async def collection_root_track(
        collection_id: str, root: str, kind: str = "conservation"
    ) -> JSONResponse:
        """A cross-text similarity track on the ``root`` member's coordinate frame (FR-30): each in-root
        passage annotated with its corpus conservation, as a root-frame lane."""
        from palimpsest.collections_masking import cross_text_track

        try:
            return JSONResponse(content=cross_text_track(workspace, collection_id, root, kind=kind))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/collections/{collection_id}/liftover")
    async def collection_liftover(collection_id: str, request: LiftoverRequest) -> JSONResponse:
        """Project ``source_id``'s intervals onto ``target_id``'s frame across their alignment (FR-42).
        ``dropped`` intervals (touching no aligned block) are reported. With ``persist=true`` the lift
        lands on the target as a new additive run version (FR-41)."""
        from palimpsest.collections_masking import (
            lift_intervals_across,
            lifted_track_is_stale,
            persist_lifted_track,
        )

        intervals = [(int(s), int(e)) for s, e in request.intervals]
        try:
            result = lift_intervals_across(
                workspace, request.source_id, request.target_id, intervals
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if request.persist:
            result["stale"] = lifted_track_is_stale(
                workspace, collection_id, result, kind=request.kind
            )
            result["version"] = persist_lifted_track(
                workspace, collection_id, result, kind=request.kind
            )
        return JSONResponse(content=result)

    @app.get("/api/collections/{collection_id}/mask-effect")
    async def collection_mask_effect(
        collection_id: str, a: str, b: str, metric: str = "word_overlap"
    ) -> JSONResponse:
        """Demonstrate that a cross-text mask *changes* a downstream alignment (FR-29): the word-overlap
        matrix of (a, b) unmasked vs with a's cross-text mask excised. ``changed`` is the done-criterion
        signal — masking a member alters its paragraph token-sets, so the matrix must differ."""
        import numpy as np

        from palimpsest.collections_masking import cross_text_mask, masked_cross_similarity
        from palimpsest.project import Project

        pa = Project.load(_safe_project_dir(workspace, a))
        pb = Project.load(_safe_project_dir(workspace, b))
        try:
            mask_a = [(s, e) for s, e in cross_text_mask(workspace, collection_id, a)["intervals"]]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        unmasked = masked_cross_similarity(pa, pb, metric=metric)
        masked = masked_cross_similarity(pa, pb, mask_a=mask_a, metric=metric)
        changed = unmasked.shape != masked.shape or not np.array_equal(unmasked, masked)
        return JSONResponse(content={
            "collection_id": collection_id, "a": a, "b": b, "metric": metric,
            "mask_intervals": len(mask_a),
            "unmasked_shape": list(unmasked.shape),
            "masked_shape": list(masked.shape),
            "changed": bool(changed),
        })

    # ── Alignment API ──

    _alignment_jobs: dict[str, dict] = {}

    import re as _re
    _ID_PATTERN = _re.compile(r"^[a-zA-Z0-9_\-]+$")

    def _validate_ids(query_id: str, target_id: str) -> None:
        if not _ID_PATTERN.match(query_id) or not _ID_PATTERN.match(target_id):
            raise HTTPException(status_code=400, detail="Invalid project ID format")

    @app.post("/api/alignment/run")
    async def run_alignment(request: AlignmentRequest) -> JSONResponse:
        """Run pairwise alignment between two projects."""
        import asyncio

        query_dir = _safe_project_dir(workspace, request.query_id)
        target_dir = _safe_project_dir(workspace, request.target_id)

        job_key = f"{request.query_id}:{request.target_id}"
        if job_key in _alignment_jobs and _alignment_jobs[job_key].get("status") == "running":
            return JSONResponse(content={"status": "already_running"})

        _alignment_jobs[job_key] = {"status": "running", "method": request.method}

        async def run() -> None:
            try:
                from palimpsest.alignment.cross_similarity import compute_cross_similarity
                from palimpsest.alignment.smith_waterman import smith_waterman as sw_align
                from palimpsest.alignment.alphabet_align import align_alphabets
                from palimpsest.alignment.gumbel import calibrate_gumbel, p_value
                from palimpsest.alignment.records import write_alignment_records
                from palimpsest.formats.signals import write_signal
                from palimpsest.project import Project

                proj_a = Project.load(query_dir)
                proj_b = Project.load(target_dir)

                comp_dir = comparison_dir(workspace, request.query_id, request.target_id)
                comp_dir.mkdir(parents=True, exist_ok=True)

                if request.method == "alphabet":
                    records = await asyncio.to_thread(align_alphabets, proj_a, proj_b)
                elif request.method == "word":
                    from palimpsest.alignment.cross_similarity import compute_word_overlap
                    matrix, manifest = await asyncio.to_thread(
                        compute_word_overlap, proj_a, proj_b
                    )
                    await asyncio.to_thread(write_signal, comp_dir, matrix, manifest)

                    records = await asyncio.to_thread(
                        sw_align, matrix, request.query_id, request.target_id, "word"
                    )
                else:
                    matrix, manifest = await asyncio.to_thread(
                        compute_cross_similarity, proj_a, proj_b, "cosine"
                    )
                    await asyncio.to_thread(write_signal, comp_dir, matrix, manifest)

                    records = await asyncio.to_thread(
                        sw_align, matrix, request.query_id, request.target_id, request.method
                    )

                    mu, beta = await asyncio.to_thread(calibrate_gumbel, matrix)
                    for rec in records:
                        rec.p_value = p_value(rec.score, mu, beta)

                await asyncio.to_thread(
                    write_alignment_records, comp_dir / "alignment.jsonl", records
                )

                (comp_dir / "metadata.json").write_text(
                    json.dumps({
                        "query_id": request.query_id,
                        "target_id": request.target_id,
                        "method": request.method,
                        "record_count": len(records),
                    }, indent=2),
                    encoding="utf-8",
                )

                _alignment_jobs[job_key] = {"status": "completed", "record_count": len(records)}
            except Exception as exc:
                logger.exception("Alignment failed: %s", exc)
                _alignment_jobs[job_key] = {"status": "failed", "error": str(exc)}
            finally:
                asyncio.get_running_loop().call_later(60.0, lambda: _alignment_jobs.pop(job_key, None))

        asyncio.create_task(run())
        return JSONResponse(content={"status": "started"})

    @app.get("/api/alignment/{query_id}/{target_id}/status")
    async def alignment_status(query_id: str, target_id: str) -> JSONResponse:
        _validate_ids(query_id, target_id)
        job_key = f"{query_id}:{target_id}"
        job = _alignment_jobs.get(job_key)
        if not job:
            comp_dir = comparison_dir(workspace, query_id, target_id)
            if (comp_dir / "alignment.jsonl").exists():
                return JSONResponse(content={"status": "completed"})
            return JSONResponse(content={"status": "idle"})
        return JSONResponse(content=job)

    def _read_alignment(query_id: str, target_id: str):
        """Load persisted alignment records for a comparison, or 404."""
        comp_dir = comparison_dir(workspace, query_id, target_id)
        records_path = comp_dir / "alignment.jsonl"
        if not records_path.exists():
            raise HTTPException(status_code=404, detail="No alignment results found")
        from palimpsest.alignment.records import read_alignment_records

        return read_alignment_records(records_path)

    def _char_count(pid: str) -> int:
        mp = workspace / pid / "metadata.json"
        if mp.exists():
            try:
                return int(json.loads(mp.read_text(encoding="utf-8")).get("character_count", 0))
            except (ValueError, json.JSONDecodeError):
                pass
        return 0

    @app.get("/api/alignment/{query_id}/{target_id}/records")
    async def alignment_records(
        query_id: str, target_id: str,
        min_score: float | None = None, max_p_value: float | None = None,
    ) -> JSONResponse:
        """Alignment records, optionally thresholded — the dotplot's empirical cutoff (FR-40). Filter
        by ``min_score`` and/or ``max_p_value`` to show only high-scoring local alignments."""
        _validate_ids(query_id, target_id)
        records = _read_alignment(query_id, target_id)
        if min_score is not None:
            records = [r for r in records if r.score >= min_score]
        if max_p_value is not None:
            records = [r for r in records if r.p_value <= max_p_value]
        return JSONResponse(content=[r.to_dict() for r in records])

    @app.get("/api/alignment/{query_id}/{target_id}/scores")
    async def alignment_scores(query_id: str, target_id: str) -> JSONResponse:
        """The alignment-score distribution + a suggested empirical threshold for the dotplot (FR-40).
        The frontend uses this to set the threshold slider's range and default cutoff."""
        _validate_ids(query_id, target_id)
        records = _read_alignment(query_id, target_id)
        scores = sorted(r.score for r in records)
        if not scores:
            return JSONResponse(content={"count": 0, "scores": [], "suggested_threshold": None})

        def _q(p: float) -> float:
            return scores[min(len(scores) - 1, max(0, int(p * (len(scores) - 1))))]

        return JSONResponse(content={
            "count": len(scores),
            "min": scores[0], "max": scores[-1],
            "median": _q(0.5), "p75": _q(0.75), "p90": _q(0.90),
            # default cutoff: the 75th percentile — show the upper quartile of alignments by score
            "suggested_threshold": _q(0.75),
            "scores": scores,
        })

    @app.get("/api/alignment/{query_id}/{target_id}/export.paf")
    async def alignment_export_paf(
        query_id: str, target_id: str,
        min_score: float | None = None, max_p_value: float | None = None,
    ):
        """Export (optionally thresholded) alignment records as minimap2 PAF (FR-36)."""
        from fastapi.responses import PlainTextResponse

        from palimpsest.alignment.records import records_to_paf

        _validate_ids(query_id, target_id)
        records = _read_alignment(query_id, target_id)
        if min_score is not None:
            records = [r for r in records if r.score >= min_score]
        if max_p_value is not None:
            records = [r for r in records if r.p_value <= max_p_value]
        lines = records_to_paf(records, _char_count(query_id), _char_count(target_id))
        body = "\n".join(lines) + ("\n" if lines else "")
        return PlainTextResponse(
            content=body, media_type="text/x-paf",
            headers={"Content-Disposition": f'attachment; filename="{comparison_dirname(query_id, target_id)}.paf"'},
        )

    @app.get("/api/alignment/{query_id}/{target_id}/matrix")
    async def alignment_matrix(query_id: str, target_id: str) -> JSONResponse:
        _validate_ids(query_id, target_id)
        comp_dir = comparison_dir(workspace, query_id, target_id)
        manifest_path = comp_dir / "cross_similarity.json"
        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail="No cross-similarity matrix found")
        return JSONResponse(content=json.loads(manifest_path.read_text()))

    @app.post("/api/alignment/diff")
    async def run_diff(request: AlignmentRequest) -> JSONResponse:
        """Compute edition-level diff between two projects."""
        import asyncio

        query_dir = _safe_project_dir(workspace, request.query_id)
        target_dir = _safe_project_dir(workspace, request.target_id)

        from palimpsest.alignment.edition_diff import compute_edition_diff, write_diff_results
        from palimpsest.project import Project as Proj

        proj_a = Proj.load(query_dir)
        proj_b = Proj.load(target_dir)

        records, summary = await asyncio.to_thread(compute_edition_diff, proj_a, proj_b)

        comp_dir = comparison_dir(workspace, request.query_id, request.target_id)
        await asyncio.to_thread(write_diff_results, comp_dir / "diff.json", records, summary)

        return JSONResponse(content={
            "summary": summary.to_dict(),
            "records": [r.to_dict() for r in records[:500]],
        })

    @app.get("/api/alignment/{query_id}/{target_id}/diff")
    async def get_diff(query_id: str, target_id: str) -> JSONResponse:
        _validate_ids(query_id, target_id)
        comp_dir = comparison_dir(workspace, query_id, target_id)
        diff_path = comp_dir / "diff.json"
        if not diff_path.exists():
            raise HTTPException(status_code=404, detail="No diff results found")
        from palimpsest.alignment.edition_diff import read_diff_results
        records, summary = read_diff_results(diff_path)
        return JSONResponse(content={
            "summary": summary.to_dict(),
            "records": [r.to_dict() for r in records[:500]],
        })

    @app.get("/api/alignment/{query_id}/{target_id}/matrix.bin")
    async def alignment_matrix_bin(query_id: str, target_id: str) -> FileResponse:
        _validate_ids(query_id, target_id)
        comp_dir = comparison_dir(workspace, query_id, target_id)
        bin_path = comp_dir / "cross_similarity.bin"
        if not bin_path.exists():
            raise HTTPException(status_code=404, detail="No cross-similarity binary found")
        return FileResponse(bin_path, media_type="application/octet-stream")

    @app.get("/api/comparisons")
    async def list_comparisons() -> JSONResponse:
        """Discover computed pairwise comparisons under ``.comparisons/`` — the index the frontend
        needs to surface prior cross-text results (none existed before)."""
        comps_dir = workspace / ".comparisons"
        out: list[dict] = []
        if comps_dir.is_dir():
            for d in sorted(comps_dir.iterdir()):
                if not d.is_dir():
                    continue
                meta_path = d / "metadata.json"
                entry: dict = {"id": d.name}
                if meta_path.exists():
                    try:
                        entry.update(json.loads(meta_path.read_text(encoding="utf-8")))
                    except json.JSONDecodeError:
                        pass
                entry["has_matrix"] = (d / "cross_similarity.bin").exists()
                entry["has_records"] = (d / "alignment.jsonl").exists()
                out.append(entry)
        return JSONResponse(content=out)

    @app.get("/data/{project_id}/{path:path}")
    async def serve_project_file(project_id: str, path: str) -> FileResponse:
        """Serve static project files (read-only)."""
        if ".." in project_id or "/" in project_id or "\\" in project_id:
            raise HTTPException(status_code=400, detail="Invalid project ID")

        resolved = (workspace / project_id / path).resolve()
        if not resolved.is_relative_to(workspace.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")

        if not resolved.exists() or not resolved.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(resolved)

    # Mount browser dist if available (dev mode only)
    browser_dist = Path(__file__).parent.parent.parent / "browser" / "dist"
    if browser_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(browser_dist), html=True))

    return app


def run_server(workspace: Path, port: int = 8080, imports_dir: Path | None = None) -> None:
    """Start the server with uvicorn."""
    import uvicorn

    app = create_app(workspace, imports_dir=imports_dir)
    uvicorn.run(app, host="127.0.0.1", port=port)
