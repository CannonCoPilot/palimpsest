"""FastAPI server for Palimpsest — static file serving + API endpoints."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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


def create_app(workspace: Path) -> FastAPI:
    """Create the FastAPI application for a workspace directory."""
    app = FastAPI(title="Palimpsest", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
        allow_methods=["GET", "POST"],
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
                    })
        return JSONResponse(content=projects)

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

        if ".." in project:
            raise HTTPException(status_code=400, detail="Invalid project ID")

        embeddings_db = workspace / project / "cache" / "embeddings.db"
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
            hits = store.search(query_vec, k=k)
            store.close()

            proj = Project.load(workspace / project)
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
        granularity: str | None = None,
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
        if job_key in _running_jobs:
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
        if granularity is not None:
            params["granularity"] = granularity
        if params and hasattr(extractor, "set_params"):
            extractor.set_params(params)
        if force:
            params["force"] = True

        _running_jobs[job_key] = {"status": "running", "track": track_name, "params": params}

        async def run() -> None:
            try:
                result = await asyncio.to_thread(extractor.extract, project)
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
                import threading
                threading.Timer(30.0, lambda: _running_jobs.pop(job_key, None)).start()

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

    @app.post("/api/import")
    async def import_epub(
        file: UploadFile,
        title: str = "",
        author: str = "",
        year: int = 0,
    ) -> JSONResponse:
        """Import an EPUB file: ingest + compute all tracks."""
        import asyncio
        import tempfile

        failed_tracks: list[dict[str, str]] = []

        if not file.filename or not file.filename.lower().endswith(
            (".epub", ".txt", ".pdf", ".html", ".htm", ".md")
        ):
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
            from palimpsest.project import ingest_file

            project = await asyncio.to_thread(
                ingest_file, tmp_path, workspace,
                title=title or Path(file.filename).stem,
                author=author, year=year,
            )

            from palimpsest.tracks.registry import TrackRegistry

            registry = TrackRegistry.discover()
            for extractor_cls in registry.dependency_order():
                extractor = extractor_cls()
                try:
                    result = await asyncio.to_thread(extractor.extract, project)
                    if extractor.output_type == "annotation" and isinstance(result, list):
                        from palimpsest.annotation.serializer import write_track
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

            meta = json.loads((project.path / "metadata.json").read_text())
            track_count = len(list((project.path / "tracks").glob("*.jsonl")))

            response: dict[str, Any] = {
                "status": "ok",
                "project_id": project.metadata.id,
                "title": project.metadata.title,
                "word_count": project.metadata.word_count,
                "track_count": track_count,
                "metadata": meta,
            }
            if failed_tracks:
                response["failed_tracks"] = failed_tracks
            return JSONResponse(content=response)
        except FileExistsError:
            raise HTTPException(status_code=409, detail="Project already exists")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            tmp_path.unlink(missing_ok=True)

    # ── Alignment API ──

    _alignment_jobs: dict[str, dict] = {}

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
                import threading
                threading.Timer(60.0, lambda: _alignment_jobs.pop(job_key, None)).start()

        asyncio.create_task(run())
        return JSONResponse(content={"status": "started"})

    @app.get("/api/alignment/{query_id}/{target_id}/status")
    async def alignment_status(query_id: str, target_id: str) -> JSONResponse:
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
        comp_dir = workspace / ".comparisons" / f"{query_id}_vs_{target_id}"
        records_path = comp_dir / "alignment.jsonl"
        if not records_path.exists():
            raise HTTPException(status_code=404, detail="No alignment results found")
        from palimpsest.alignment.records import read_alignment_records
        records = read_alignment_records(records_path)
        return JSONResponse(content=[r.to_dict() for r in records])

    @app.get("/api/alignment/{query_id}/{target_id}/matrix")
    async def alignment_matrix(query_id: str, target_id: str) -> JSONResponse:
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
        comp_dir = workspace / ".comparisons" / f"{query_id}_vs_{target_id}"
        bin_path = comp_dir / "cross_similarity.bin"
        if not bin_path.exists():
            raise HTTPException(status_code=404, detail="No cross-similarity binary found")
        return FileResponse(bin_path, media_type="application/octet-stream")

    @app.get("/data/{project_id}/{path:path}")
    async def serve_project_file(project_id: str, path: str) -> FileResponse:
        """Serve static project files (read-only)."""
        if ".." in project_id or ".." in path:
            raise HTTPException(status_code=400, detail="Invalid path")

        file_path = workspace / project_id / path
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.resolve().is_relative_to(workspace.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(file_path)

    # Mount browser dist if available (dev mode only)
    browser_dist = Path(__file__).parent.parent.parent / "browser" / "dist"
    if browser_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(browser_dist), html=True))

    return app


def run_server(workspace: Path, port: int = 8080) -> None:
    """Start the server with uvicorn."""
    import uvicorn

    app = create_app(workspace)
    uvicorn.run(app, host="127.0.0.1", port=port)
