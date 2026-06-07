"""SqliteVecStore — sqlite-vec implementation of VectorStore protocol."""

from __future__ import annotations

import json
import sqlite3
import struct
from pathlib import Path

import sqlite_vec


class SqliteVecStore:
    """Vector store backed by sqlite-vec with WAL mode for concurrent read access."""

    def __init__(self, db_path: Path, dim: int, wal: bool = True) -> None:
        self._dim = dim
        self._conn = sqlite3.connect(str(db_path))
        self._conn.enable_load_extension(True)
        sqlite_vec.load(self._conn)
        self._conn.enable_load_extension(False)
        if wal:
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        if dim > 0:
            self._conn.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_items USING vec0("
                f"  embedding float[{dim}] distance_metric=cosine"
                f")"
            )
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS vec_meta ("
                "  rowid INTEGER PRIMARY KEY,"
                "  id TEXT NOT NULL,"
                "  para_index INTEGER DEFAULT -1,"
                "  metadata TEXT"
                ")"
            )
            self._conn.commit()

    @classmethod
    def open_existing(cls, db_path: Path, wal: bool = True) -> SqliteVecStore:
        """Open an existing embeddings DB for read-only access (no DDL)."""
        if not db_path.exists():
            raise FileNotFoundError(f"Embeddings DB not found: {db_path}")
        store = cls.__new__(cls)
        store._dim = 0
        store._conn = sqlite3.connect(str(db_path))
        store._conn.enable_load_extension(True)
        sqlite_vec.load(store._conn)
        store._conn.enable_load_extension(False)
        if wal:
            store._conn.execute("PRAGMA journal_mode=WAL")
        store._conn.execute("PRAGMA synchronous=NORMAL")
        return store

    def add(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, int]] | None = None,
    ) -> None:
        for i, (vid, vec) in enumerate(zip(ids, vectors)):
            blob = struct.pack(f"<{len(vec)}f", *vec)
            cursor = self._conn.execute(
                "INSERT INTO vec_items(embedding) VALUES (?)",
                (blob,),
            )
            rowid = cursor.lastrowid
            para_idx = -1
            meta_json = None
            if metadata and i < len(metadata):
                para_idx = metadata[i].get("para_index", -1)
                meta_json = json.dumps(metadata[i])
            self._conn.execute(
                "INSERT INTO vec_meta(rowid, id, para_index, metadata) VALUES (?, ?, ?, ?)",
                (rowid, vid, para_idx, meta_json),
            )
        self._conn.commit()

    def search(self, query: list[float], k: int = 10) -> list[tuple[str, float]]:
        blob = struct.pack(f"<{len(query)}f", *query)
        rows = self._conn.execute(
            "SELECT v.rowid, v.distance FROM vec_items v "
            "WHERE v.embedding MATCH ? "
            "ORDER BY v.distance LIMIT ?",
            (blob, k),
        ).fetchall()
        results: list[tuple[str, float]] = []
        for rowid, distance in rows:
            row = self._conn.execute(
                "SELECT id FROM vec_meta WHERE rowid = ?", (rowid,)
            ).fetchone()
            if row:
                # cosine distance ∈ [0, 2]; similarity = 1 - distance ∈ [-1, 1]
                results.append((row[0], 1.0 - distance))
        return results

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM vec_meta").fetchone()
        return row[0] if row else 0

    def stored_indices(self) -> set[int]:
        """Return set of all stored para_index values for gap detection."""
        rows = self._conn.execute(
            "SELECT para_index FROM vec_meta WHERE para_index >= 0"
        ).fetchall()
        return {row[0] for row in rows}

    def delete(self, ids: list[str]) -> None:
        for vid in ids:
            row = self._conn.execute(
                "SELECT rowid FROM vec_meta WHERE id = ?", (vid,)
            ).fetchone()
            if row:
                self._conn.execute("DELETE FROM vec_items WHERE rowid = ?", (row[0],))
                self._conn.execute("DELETE FROM vec_meta WHERE rowid = ?", (row[0],))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def max_stored_index(self) -> int:
        row = self._conn.execute(
            "SELECT MAX(para_index) FROM vec_meta"
        ).fetchone()
        return row[0] if row and row[0] is not None else -1

    def get_all_vectors(self) -> list[list[float]]:
        """Load all vectors ordered by para_index for matrix computations."""
        rows = self._conn.execute(
            "SELECT v.embedding FROM vec_items v "
            "JOIN vec_meta m ON v.rowid = m.rowid "
            "ORDER BY m.para_index"
        ).fetchall()
        results: list[list[float]] = []
        for (blob,) in rows:
            n = len(blob) // 4
            vec = list(struct.unpack(f"<{n}f", blob))
            results.append(vec)
        return results
