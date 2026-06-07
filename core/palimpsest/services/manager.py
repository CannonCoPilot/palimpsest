"""Ollama service manager — health checks, model management, client factories."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_EMBEDDING_MODEL = "qwen3-embedding:4b"
DEFAULT_LLM_MODEL = "qwen3:8b"
HEALTH_TIMEOUT = 3.0


@dataclass
class OllamaStatus:
    running: bool
    models: list[str] = field(default_factory=list)
    error: str | None = None


class OllamaManager:
    """Manages Ollama lifecycle — never raises on connection failure."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        llm_model: str = DEFAULT_LLM_MODEL,
    ) -> None:
        self.base_url = base_url
        self._embedding_model = embedding_model
        self._llm_model = llm_model

    def health_check(self) -> OllamaStatus:
        try:
            resp = httpx.get(
                f"{self.base_url}/api/tags",
                timeout=HEALTH_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return OllamaStatus(running=True, models=models)
            return OllamaStatus(running=False, error=f"HTTP {resp.status_code}")
        except (httpx.ConnectError, httpx.TimeoutException, Exception) as e:
            return OllamaStatus(running=False, error=str(e))

    def is_model_available(self, model_name: str) -> bool:
        status = self.health_check()
        if not status.running:
            return False
        return any(m.startswith(model_name) for m in status.models)

    def embedding_client(self) -> EmbeddingClient:
        return EmbeddingClient(self.base_url, self._embedding_model)

    def llm_client(self) -> LLMClient:
        return LLMClient(self.base_url, self._llm_model)


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    model: str
    dimension: int


EMBED_TIMEOUT = 30.0
BATCH_SIZE = 32


class EmbeddingClient:
    """Ollama embedding client — returns None on any failure."""

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url
        self.model = model

    def embed_one(self, text: str) -> list[float] | None:
        result = self.embed_batch([text])
        if result and result.vectors:
            return result.vectors[0]
        return None

    def embed_batch(self, texts: list[str]) -> EmbeddingResult | None:
        if not texts:
            return EmbeddingResult(vectors=[], model=self.model, dimension=0)
        try:
            all_vectors: list[list[float]] = []
            for i in range(0, len(texts), BATCH_SIZE):
                batch = texts[i : i + BATCH_SIZE]
                resp = httpx.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": batch},
                    timeout=EMBED_TIMEOUT,
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                all_vectors.extend(data.get("embeddings", []))
            if not all_vectors:
                return None
            return EmbeddingResult(
                vectors=all_vectors,
                model=self.model,
                dimension=len(all_vectors[0]),
            )
        except (httpx.ConnectError, httpx.TimeoutException, Exception):
            return None


LLM_TIMEOUT = 60.0


class LLMClient:
    """Ollama LLM client — returns None on any failure."""

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url
        self.model = model

    def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 256,
    ) -> str | None:
        try:
            payload: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            if "qwen" in self.model.lower():
                payload["think"] = False
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=LLM_TIMEOUT,
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except (httpx.ConnectError, httpx.TimeoutException, Exception):
            return None

    def summarize(self, passage: str) -> str | None:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a literary analysis assistant. Summarize the given passage "
                    "in 1-3 concise sentences, focusing on key events, characters, and themes."
                ),
            },
            {"role": "user", "content": passage[:2000]},
        ]
        return self.chat(messages)
