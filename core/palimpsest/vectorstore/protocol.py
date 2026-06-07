"""VectorStore protocol — write-side abstraction for paragraph embeddings."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class VectorStore(Protocol):
    def add(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, int]] | None = None,
    ) -> None: ...

    def search(self, query: list[float], k: int = 10) -> list[tuple[str, float]]: ...

    def count(self) -> int: ...

    def delete(self, ids: list[str]) -> None: ...

    def close(self) -> None: ...

    def max_stored_index(self) -> int: ...

    def stored_indices(self) -> set[int]: ...

    def get_all_vectors(self) -> list[list[float]]: ...
