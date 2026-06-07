"""Embedding pipeline — batch embed paragraphs via MLX or Ollama into VectorStore.

Tries MLX first (localhost:8000, ~14x faster on Apple Silicon), falls back to Ollama.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from palimpsest.project import Project
    from palimpsest.vectorstore.protocol import VectorStore

logger = logging.getLogger(__name__)

MLX_BASE_URL = "http://localhost:8000"
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen3-embedding:4b"
EMBED_TIMEOUT = 30.0
BATCH_SIZE = 32
MAX_CONCURRENT = 4


class EmbeddingServiceUnavailableError(Exception):
    pass


async def _probe_mlx(client: httpx.AsyncClient) -> int | None:
    """Check if MLX embedding server is available. Returns dimension or None."""
    try:
        resp = await client.post(
            "/embed",
            json={"text": "probe"},
            timeout=3.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            if "embedding" in data:
                return len(data["embedding"])
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    return None


async def _embed_batch_mlx(
    texts: list[str],
    client: httpx.AsyncClient,
) -> list[list[float]]:
    """Embed via MLX batch endpoint (much faster than sequential)."""
    resp = await client.post(
        "/embed_batch",
        json={"texts": texts},
        timeout=EMBED_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


async def _embed_batch_ollama(
    texts: list[str],
    client: httpx.AsyncClient,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> list[list[float]]:
    """Embed via Ollama /api/embed endpoint."""
    resp = await client.post(
        "/api/embed",
        json={"model": model, "input": texts},
        timeout=EMBED_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


async def embed_paragraphs_async(
    project: Project,
    store: VectorStore,
    model: str = DEFAULT_OLLAMA_MODEL,
    batch_size: int = BATCH_SIZE,
    max_concurrent: int = MAX_CONCURRENT,
) -> tuple[int, str]:
    """Embed all paragraphs using concurrent async batches.

    Tries MLX first (14-56x faster on Apple Silicon), falls back to Ollama.
    Uses stored_indices() for gap-aware idempotency.
    Returns (count_embedded, backend_name).
    """
    paras = project.paragraphs()
    already_stored = store.stored_indices()
    pending = [
        (i, start, end, text)
        for i, (start, end, text) in enumerate(paras)
        if i not in already_stored
    ]
    if not pending:
        return 0, "cached"

    sem = asyncio.Semaphore(max_concurrent)
    slug = project.metadata.id
    embedded_count = 0

    # Try MLX first
    async with httpx.AsyncClient(base_url=MLX_BASE_URL) as mlx_client:
        mlx_dim = await _probe_mlx(mlx_client)
        if mlx_dim is not None:
            logger.info("Using MLX embedding server (dim=%d)", mlx_dim)

            async def embed_one_batch_mlx(
                batch: list[tuple[int, int, int, str]],
            ) -> int:
                async with sem:
                    texts = [text for _, _, _, text in batch]
                    vectors = await _embed_batch_mlx(texts, mlx_client)
                    ids = [f"{slug}:para:{idx}" for idx, _, _, _ in batch]
                    meta = [{"para_index": idx} for idx, _, _, _ in batch]
                    store.add(ids, vectors, meta)
                    return len(batch)

            batches = [
                pending[i : i + batch_size]
                for i in range(0, len(pending), batch_size)
            ]
            results = await asyncio.gather(
                *[embed_one_batch_mlx(b) for b in batches],
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, int):
                    embedded_count += r
                elif isinstance(r, Exception):
                    logger.warning("MLX batch failed: %s", r)

            return embedded_count, "mlx"

    # Fall back to Ollama
    try:
        async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL) as ollama_client:
            try:
                health = await ollama_client.get("/api/tags", timeout=3.0)
                health.raise_for_status()
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise EmbeddingServiceUnavailableError(
                    f"Neither MLX (:{MLX_BASE_URL}) nor Ollama (:{OLLAMA_BASE_URL}) reachable: {e}"
                ) from e

            logger.info("Using Ollama embedding server")

            async def embed_one_batch_ollama(
                batch: list[tuple[int, int, int, str]],
            ) -> int:
                async with sem:
                    texts = [text for _, _, _, text in batch]
                    vectors = await _embed_batch_ollama(texts, ollama_client, model)
                    ids = [f"{slug}:para:{idx}" for idx, _, _, _ in batch]
                    meta = [{"para_index": idx} for idx, _, _, _ in batch]
                    store.add(ids, vectors, meta)
                    return len(batch)

            batches = [
                pending[i : i + batch_size]
                for i in range(0, len(pending), batch_size)
            ]
            results = await asyncio.gather(
                *[embed_one_batch_ollama(b) for b in batches],
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, int):
                    embedded_count += r
                elif isinstance(r, Exception):
                    logger.warning("Ollama batch failed: %s", r)

            return embedded_count, "ollama"

    except EmbeddingServiceUnavailableError:
        raise
    except Exception as e:
        raise EmbeddingServiceUnavailableError(f"Embedding failed: {e}") from e


def embed_paragraphs(
    project: Project,
    store: VectorStore,
    model: str = DEFAULT_OLLAMA_MODEL,
    batch_size: int = BATCH_SIZE,
    max_concurrent: int = MAX_CONCURRENT,
) -> tuple[int, str]:
    """Synchronous wrapper. Returns (count_embedded, backend_name)."""
    return asyncio.run(
        embed_paragraphs_async(
            project, store, model=model,
            batch_size=batch_size, max_concurrent=max_concurrent,
        )
    )
