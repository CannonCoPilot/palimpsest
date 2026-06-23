"""Standalone embedding stage for the chunking+embedding pipeline.

Turns a list of chunk texts into an embedding matrix. Every parameter — provider, endpoint, model,
batch size — is user-defined at runtime via :class:`EmbeddingConfig`; there are no hidden defaults,
no auto-selection between providers, and no silent failure. Any provider/HTTP/shape error raises so
the caller (and the user) learns the run did not produce embeddings, rather than getting ``None``
and a silently-skipped analysis.

Providers (both honor the configured ``model`` — name or server alias — so the user's choice is
actually used, and an unknown model fails loud rather than being silently swapped):
  - ``ollama``  POST ``{endpoint}/api/embed`` with ``{model, input: [texts]}`` → ``{embeddings}``.
  - ``mlx``     POST ``{endpoint}/embed_batch`` with ``{texts, model}`` → ``{embeddings}``.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_PROVIDERS = ("mlx", "ollama")


@dataclass(frozen=True)
class EmbeddingConfig:
    """Fully explicit embedding parameters for one run."""

    provider: str
    endpoint: str
    model: str
    batch_size: int

    def __post_init__(self) -> None:
        if self.provider not in EMBEDDING_PROVIDERS:
            raise ValueError(
                f"embedding provider must be one of {EMBEDDING_PROVIDERS}, got {self.provider!r}"
            )
        if not self.endpoint:
            raise ValueError("embedding endpoint is required")
        if not self.model:
            raise ValueError("embedding model is required")
        if self.batch_size < 1:
            raise ValueError(f"embedding batch_size must be >= 1, got {self.batch_size}")

    def provenance(self) -> dict[str, object]:
        """The config as a plain dict for echoing into output manifests."""
        return asdict(self)


def _post_json(client: object, path: str, payload: dict, timeout: float) -> dict:
    resp = client.post(path, json=payload, timeout=timeout)  # type: ignore[attr-defined]
    resp.raise_for_status()
    return resp.json()


def probe_dim(config: EmbeddingConfig) -> int:
    """Return the embedding dimension for ``config`` by embedding one probe token. Raises on any
    connection/HTTP/shape error — the dimension is a fact about the chosen service, so an
    unreachable service is an error, not a reason to guess or skip."""
    import httpx

    with httpx.Client(base_url=config.endpoint) as client:
        if config.provider == "mlx":
            data = _post_json(client, "/embed", {"text": "probe", "model": config.model}, 30.0)
            vector = data["embedding"]
        else:  # ollama
            data = _post_json(client, "/api/embed", {"model": config.model, "input": ["probe"]}, 30.0)
            vector = data["embeddings"][0]
    return len(vector)


def embed_texts(texts: list[str], config: EmbeddingConfig) -> np.ndarray:
    """Embed every text in ``texts`` with ``config`` and return an ``(n, dim)`` float32 matrix.

    Raises on empty input, any provider/HTTP error, or a returned count that does not match the
    input — never returns ``None`` or a partial result, so a failed embedding can never be mistaken
    for "no analysis needed"."""
    import httpx

    if not texts:
        raise ValueError("embed_texts called with no texts")

    vectors: list[list[float]] = []
    with httpx.Client(base_url=config.endpoint) as client:
        for start in range(0, len(texts), config.batch_size):
            batch = texts[start:start + config.batch_size]
            if config.provider == "mlx":
                data = _post_json(client, "/embed_batch", {"texts": batch, "model": config.model}, 120.0)
            else:  # ollama
                data = _post_json(client, "/api/embed", {"model": config.model, "input": batch}, 120.0)
            batch_vectors = data["embeddings"]
            if len(batch_vectors) != len(batch):
                raise ValueError(
                    f"embedding provider returned {len(batch_vectors)} vectors for a batch of "
                    f"{len(batch)} texts"
                )
            vectors.extend(batch_vectors)

    matrix = np.array(vectors, dtype=np.float32)
    if matrix.shape[0] != len(texts):
        raise ValueError(f"embedded {matrix.shape[0]} vectors for {len(texts)} texts")
    logger.info(
        "Embedded %d texts via %s (%s, dim=%d)",
        len(texts), config.provider, config.model, matrix.shape[1],
    )
    return matrix
