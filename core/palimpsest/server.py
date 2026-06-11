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
        if ".." in project_id:
            raise HTTPException(status_code=400, detail="Invalid project ID")
        tracks_dir = workspace / project_id / "tracks"
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
