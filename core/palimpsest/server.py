"""FastAPI server for Palimpsest — static file serving + API endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


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


def create_app(workspace: Path) -> FastAPI:
    """Create the FastAPI application for a workspace directory."""
    app = FastAPI(title="Palimpsest", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
        except Exception:
            return SearchResponse(results=[], embedding_available=False)

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
