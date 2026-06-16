"""FastAPI server for Palimpsest — static file serving + API endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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


class SectionsUpdateRequest(BaseModel):
    sections: list[dict[str, Any]]
    mask_by_type: dict[str, bool] | None = None
    applied: bool | None = None
    extra_types: list[dict[str, Any]] | None = None  # custom user mask layers


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


def _sections_payload(cfg: Any, text_len: int) -> dict[str, Any]:
    """Package a LayoutConfig + the type vocabulary (builtin + custom) + masks for the UI."""
    from palimpsest.layout import (
        MASKED_BG_COLOR,
        MASKED_TEXT_COLOR,
        masked_intervals,
        type_vocabulary,
    )

    extra_types = getattr(cfg, "extra_types", [])
    intervals = masked_intervals(cfg.sections, cfg.mask_by_type, text_len)
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
        body = Body(
            type="palimpsest:ElementAnnotation",
            purpose="classifying",
            value=s.label or SECTION_LABELS.get(s.type, s.type),
            extra={
                "palimpsest:elementType": s.type,
                "palimpsest:elementName": s.name,
                "palimpsest:masked": effective_mask(s, cfg.mask_by_type),
                "palimpsest:parentId": s.parent_id or "",
                "palimpsest:color": SECTION_COLORS.get(s.type, "#8e8e93"),
            },
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
            if ext.output_type == "annotation":
                output_exists = (tracks_dir / f"{name}.jsonl").exists()
            elif ext.output_type == "signal":
                output_exists = (project_dir / "signals" / f"{name}.json").exists()

            manifest_path = manifests_dir / f"{name}.manifest.json"
            manifest_data = None
            if manifest_path.exists():
                manifest_data = json.loads(manifest_path.read_text())

            job = _running_jobs.get(f"{project_id}:{name}")
            status = "running" if job else ("computed" if output_exists else "pending")

            result.append({
                "name": name,
                "status": status,
                "outputType": ext.output_type,
                "dependsOn": ext.depends_on,
                "evidenceLevel": ext.evidence_level,
                "hasManifest": manifest_data is not None,
                "lfoTypes": ext.lfo_types,
            })

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
        granularity: str | None = None,
        chunk_size: int | None = None,
        chunk_size_cosine: int | None = None,
        chunk_size_jaccard: int | None = None,
        chunk_size_word_overlap: int | None = None,
        chunk_size_edit_distance: int | None = None,
    ) -> JSONResponse:
        """Run a single track extractor with optional parameters."""
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
        extractor = all_extractors[track_name]()

        params: dict[str, Any] = {}
        if n_states is not None:
            params["n_states"] = max(2, min(20, n_states))
        if n_topics is not None:
            params["n_topics"] = max(2, min(50, n_topics))
        if method is not None:
            params["method"] = method
        if metric is not None:
            params["metric"] = metric
        if metrics is not None:
            selected = [m.strip() for m in metrics.split(",") if m.strip()]
            if selected:
                params["metrics"] = selected
        if granularity is not None:
            params["granularity"] = granularity
        if chunk_size is not None:
            params["chunk_size"] = max(5, min(25, chunk_size))
        for _mkey, _mval in (
            ("cosine", chunk_size_cosine),
            ("jaccard", chunk_size_jaccard),
            ("word_overlap", chunk_size_word_overlap),
            ("edit_distance", chunk_size_edit_distance),
        ):
            if _mval is not None:
                params[f"chunk_size_{_mkey}"] = max(5, min(25, _mval))
        if force:
            params["force"] = True
        if params and hasattr(extractor, "set_params"):
            extractor.set_params(params)

        _running_jobs[job_key] = {"status": "running", "track": track_name, "params": params}

        async def run() -> None:
            try:
                async with _job_semaphore:
                    try:
                        result = await asyncio.to_thread(extractor.extract, project)
                    except ValueError as exc:
                        _running_jobs[job_key] = {
                            "status": "failed",
                            "track": track_name,
                            "error": f"Matrix too large: {exc}",
                        }
                        return
                if extractor.output_type == "annotation" and isinstance(result, list):
                    from palimpsest.annotation.serializer import write_track
                    track_path = project_dir / "tracks" / f"{track_name}.jsonl"
                    write_track(track_path, result)

                manifest_dir = project_dir / "manifests"
                manifest_dir.mkdir(exist_ok=True)
                (manifest_dir / f"{track_name}.manifest.json").write_text(
                    json.dumps(extractor.manifest(), indent=2), encoding="utf-8",
                )
                _running_jobs[job_key] = {"status": "completed", "track": track_name}
            except Exception as exc:
                _running_jobs[job_key] = {"status": "failed", "track": track_name, "error": str(exc)}
            finally:
                asyncio.get_running_loop().call_later(30.0, lambda: _running_jobs.pop(job_key, None))

        asyncio.create_task(run())
        return JSONResponse(content={"status": "started", "track": track_name})

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

    # Default chunk sizes queued by auto_run
    _AUTO_RUN_CHUNK_SIZES = (7, 11, 15)

    @app.post("/api/projects/{project_id}/analyze/self_similarity/auto_run")
    async def auto_run_self_similarity(project_id: str) -> JSONResponse:
        """Auto-queue self-similarity computation at chunk sizes 7, 11, and 15.

        Only queues if self-similarity has not been computed yet and paragraph
        embeddings are available. If self-similarity already exists, returns its
        current status without re-queuing.
        """
        import asyncio

        project_dir = _safe_project_dir(workspace, project_id)
        signals_dir = project_dir / "signals"

        # Check if already computed
        manifest_path = signals_dir / "self_similarity.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            return JSONResponse(content={
                "status": "already_computed",
                "available_chunk_sizes": manifest.get("metadata", {}).get("available_chunk_sizes", []),
                "available_metrics": manifest.get("metadata", {}).get("available_metrics", []),
            })

        # Check for paragraph embeddings
        embeddings_db = project_dir / "cache" / "embeddings.db"
        if not embeddings_db.exists():
            return JSONResponse(content={
                "status": "no_embeddings",
                "message": "Paragraph embeddings must be computed before auto-running self-similarity.",
            })

        from palimpsest.project import Project
        from palimpsest.tracks.registry import TrackRegistry

        registry = TrackRegistry.discover()
        all_extractors = {
            type(e)().name: type(e)
            for e in [cls() for cls in registry.dependency_order()]
        }
        if "self_similarity" not in all_extractors:
            raise HTTPException(status_code=500, detail="self_similarity track not registered")

        project = Project.load(project_dir)
        queued_sizes: list[int] = []
        job_keys: list[str] = []

        # Identify chunk sizes that still need to be run
        pending_sizes: list[tuple[str, Any, int]] = []
        for cs in _AUTO_RUN_CHUNK_SIZES:
            job_key = f"{project_id}:self_similarity:cs{cs}"
            if _running_jobs.get(job_key, {}).get("status") == "running":
                job_keys.append(job_key)
                continue
            extractor = all_extractors["self_similarity"]()
            extractor.set_params({"chunk_size": cs})
            _running_jobs[job_key] = {
                "status": "running",
                "track": "self_similarity",
                "chunk_size": cs,
            }
            queued_sizes.append(cs)
            job_keys.append(job_key)
            pending_sizes.append((job_key, extractor, cs))

        async def run_sequential(
            _project: Any = project,
            _pending: list[tuple[str, Any, int]] = pending_sizes,
        ) -> None:
            """Run each chunk-size job one at a time under the semaphore.

            Each self-similarity computation is already CPU-heavy, so they are
            run sequentially rather than concurrently.  External concurrency
            (e.g. from other projects) is still bounded by _job_semaphore.
            """
            for _key, _extractor, _cs in _pending:
                try:
                    async with _job_semaphore:
                        try:
                            await asyncio.to_thread(_extractor.extract, _project)
                        except ValueError as exc:
                            _running_jobs[_key] = {
                                "status": "failed",
                                "track": "self_similarity",
                                "chunk_size": _cs,
                                "error": f"Matrix too large: {exc}",
                            }
                            continue
                    _running_jobs[_key] = {
                        "status": "completed",
                        "track": "self_similarity",
                        "chunk_size": _cs,
                    }
                except Exception as exc:
                    _running_jobs[_key] = {
                        "status": "failed",
                        "track": "self_similarity",
                        "chunk_size": _cs,
                        "error": str(exc),
                    }
                finally:
                    asyncio.get_running_loop().call_later(30.0, lambda k=_key: _running_jobs.pop(k, None))

        if pending_sizes:
            asyncio.create_task(run_sequential())

        return JSONResponse(content={
            "status": "queued",
            "queued_chunk_sizes": queued_sizes,
            "job_keys": job_keys,
        })

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

    async def _ingest_and_compute(
        src_path: Path, title: str, author: str, year: int, overwrite: bool = False
    ) -> dict[str, Any]:
        """Ingest a source file and compute all tracks (legacy one-shot path)."""
        project = await _ingest_only(src_path, title, author, year, overwrite)
        failed = await _compute_tracks(project)
        return _ingest_summary(project, staged=False, failed_tracks=failed)

    async def _ingest_only(
        src_path: Path, title: str, author: str, year: int, overwrite: bool = False
    ) -> Any:
        """Step 1: structural ingest only (text/segments/sections/endnotes). No analysis."""
        import asyncio

        from palimpsest.project import ingest_file

        return await asyncio.to_thread(
            ingest_file, src_path, workspace,
            title=title or src_path.stem, author=author, year=year, overwrite=overwrite,
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
        """Step 5: run analysis extractors, dropping annotations inside masked ranges."""
        import asyncio

        from palimpsest.annotation.serializer import write_track
        from palimpsest.layout import range_is_masked
        from palimpsest.tracks.registry import TrackRegistry

        masked = await asyncio.to_thread(project.masked_intervals)

        def _keep(ann: Any) -> bool:
            sel = getattr(ann.target, "selector", None)
            start = getattr(sel, "start", None)
            end = getattr(sel, "end", None)
            if start is None or end is None:
                return True  # no position → can't mask → keep
            return not range_is_masked(masked, start, end)

        failed_tracks: list[dict[str, str]] = []
        registry = TrackRegistry.discover()
        for extractor_cls in registry.dependency_order():
            extractor = extractor_cls()
            try:
                result = await asyncio.to_thread(extractor.extract, project)
                if extractor.output_type == "annotation" and isinstance(result, list):
                    if masked:
                        result = [a for a in result if _keep(a)]
                    track_path = project.path / "tracks" / f"{extractor.name}.jsonl"
                    write_track(track_path, result)
                manifest_dir = project.path / "manifests"
                manifest_dir.mkdir(exist_ok=True)
                (manifest_dir / f"{extractor.name}.manifest.json").write_text(
                    json.dumps(extractor.manifest(), indent=2), encoding="utf-8",
                )
            except Exception as exc:
                logger.warning("Track %s failed: %s", extractor.name, exc)
                failed_tracks.append({"track": extractor.name, "error": str(exc)})
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
                return JSONResponse(content=await _ingest_and_compute(tmp_path, title, author, year))
            project = await _ingest_only(tmp_path, title, author, year)
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
                await queue.put({"type": "done", **_ingest_summary(project, staged=True)})
            except FileExistsError:
                await queue.put({"type": "error", "detail": "Project already exists", "status": 409})
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
        save_layout(project_dir, cfg)
        return JSONResponse(content=_sections_payload(cfg, text_len))

    @app.get("/api/projects/{project_id}/sections")
    async def get_sections(project_id: str) -> JSONResponse:
        """Load the persisted layout config (empty default if none yet)."""
        from palimpsest.layout import LayoutConfig, load_layout
        from palimpsest.project import Project

        project_dir = _safe_project_dir(workspace, project_id)
        text_len = len(Project.load(project_dir).reference_text())
        cfg = load_layout(project_dir) or LayoutConfig()
        return JSONResponse(content=_sections_payload(cfg, text_len))

    @app.put("/api/projects/{project_id}/sections")
    async def put_sections(project_id: str, req: SectionsUpdateRequest) -> JSONResponse:
        """Steps 3+4: persist user-edited section ranges, types, and mask flags."""
        from palimpsest.layout import (
            DEFAULT_MASK_BY_TYPE,
            LayoutConfig,
            LayoutSection,
            load_layout,
            sanitize_extra_types,
            save_layout,
        )
        from palimpsest.project import Project

        project_dir = _safe_project_dir(workspace, project_id)
        text_len = len(Project.load(project_dir).reference_text())
        cfg = load_layout(project_dir) or LayoutConfig()
        cfg.sections = [LayoutSection.from_dict(s) for s in req.sections]
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

    # ── Alignment API ──

    _alignment_jobs: dict[str, dict] = {}

    import re as _re
    _ID_PATTERN = _re.compile(r"^[a-zA-Z0-9_\-]+$")

    def _validate_ids(query_id: str, target_id: str) -> None:
        if not _ID_PATTERN.match(query_id) or not _ID_PATTERN.match(target_id):
            raise HTTPException(status_code=400, detail="Invalid project ID format")

    class AlignmentRequest(BaseModel):
        query_id: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$")
        target_id: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$")
        method: str = Field(default="semantic", pattern=r"^(semantic|alphabet|word)$")

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

                comp_dir = workspace / ".comparisons" / f"{request.query_id}_vs_{request.target_id}"
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
            comp_dir = workspace / ".comparisons" / f"{query_id}_vs_{target_id}"
            if (comp_dir / "alignment.jsonl").exists():
                return JSONResponse(content={"status": "completed"})
            return JSONResponse(content={"status": "idle"})
        return JSONResponse(content=job)

    @app.get("/api/alignment/{query_id}/{target_id}/records")
    async def alignment_records(query_id: str, target_id: str) -> JSONResponse:
        _validate_ids(query_id, target_id)
        comp_dir = workspace / ".comparisons" / f"{query_id}_vs_{target_id}"
        records_path = comp_dir / "alignment.jsonl"
        if not records_path.exists():
            raise HTTPException(status_code=404, detail="No alignment results found")
        from palimpsest.alignment.records import read_alignment_records
        records = read_alignment_records(records_path)
        return JSONResponse(content=[r.to_dict() for r in records])

    @app.get("/api/alignment/{query_id}/{target_id}/matrix")
    async def alignment_matrix(query_id: str, target_id: str) -> JSONResponse:
        _validate_ids(query_id, target_id)
        comp_dir = workspace / ".comparisons" / f"{query_id}_vs_{target_id}"
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

        comp_dir = workspace / ".comparisons" / f"{request.query_id}_vs_{request.target_id}"
        await asyncio.to_thread(write_diff_results, comp_dir / "diff.json", records, summary)

        return JSONResponse(content={
            "summary": summary.to_dict(),
            "records": [r.to_dict() for r in records[:500]],
        })

    @app.get("/api/alignment/{query_id}/{target_id}/diff")
    async def get_diff(query_id: str, target_id: str) -> JSONResponse:
        _validate_ids(query_id, target_id)
        comp_dir = workspace / ".comparisons" / f"{query_id}_vs_{target_id}"
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
        comp_dir = workspace / ".comparisons" / f"{query_id}_vs_{target_id}"
        bin_path = comp_dir / "cross_similarity.bin"
        if not bin_path.exists():
            raise HTTPException(status_code=404, detail="No cross-similarity binary found")
        return FileResponse(bin_path, media_type="application/octet-stream")

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
