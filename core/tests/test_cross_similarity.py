"""cross_similarity — embedding-DB path resolution + fail-loud metric (audit 2026-07-01 fixes).

The critical audit finding: cross-alignment's ``_load_embeddings`` read the legacy unlabeled
``cache/embeddings.db`` while the modern embedding track writes ``cache/embeddings_{label}.db`` — so
default *semantic* cross-alignment could never find a pipeline-embedded member. These tests fabricate a
member with ONLY the labeled store and assert the resolver finds it, and that an unknown metric fails
loud instead of silently mislabeling the result as cosine."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from palimpsest.alignment import cross_similarity as xs
from palimpsest.project import Project
from palimpsest.vectorstore.sqlite_vec import SqliteVecStore


def _member(
    workspace: Path, pid: str, paragraphs: list[str], vectors: list[list[float]], *, label: str = "abc123"
) -> Project:
    """A member with real reference paragraphs and ONLY a labeled ``cache/embeddings_{label}.db``."""
    pdir = workspace / pid
    pdir.mkdir(parents=True, exist_ok=True)
    text = "\n\n".join(paragraphs) + "\n"
    (pdir / "metadata.json").write_text(json.dumps({
        "id": pid, "title": pid, "language": "en", "source_format": "txt",
        "source_file": f"{pid}.txt", "ingest_date": "2026-07-01", "palimpsest_version": "0",
        "reference_sha256": f"sha-{pid}", "word_count": len(text.split()),
        "paragraph_count": len(paragraphs), "section_count": 0,
        "sentence_count": len(paragraphs), "character_count": len(text),
    }), encoding="utf-8")
    (pdir / "reference.txt").write_text(text, encoding="utf-8")
    (pdir / "reference.sha256").write_text(f"sha-{pid}", encoding="utf-8")

    db = pdir / "cache" / f"embeddings_{label}.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteVecStore(db, dim=len(vectors[0]))
    try:
        store.add([f"{pid}:{label}:{k}" for k in range(len(vectors))], vectors,
                  [{"chunk_index": k} for k in range(len(vectors))])
    finally:
        store.close()
    return Project.load(pdir)


def test_load_embeddings_resolves_labeled_store(tmp_path: Path) -> None:
    """A member embedded only through the modern pipeline (labeled store, no legacy embeddings.db) is
    found — the path split that made semantic cross-alignment unreachable is closed."""
    a = _member(tmp_path, "alpha", ["one two three", "four five six"], [[1, 0, 0, 0], [0, 1, 0, 0]])
    b = _member(tmp_path, "beta", ["seven eight", "nine ten"], [[1, 0, 0, 0], [0, 0, 1, 0]])
    assert not (tmp_path / "alpha" / "cache" / "embeddings.db").exists()  # only the labeled store exists

    matrix, manifest = xs.compute_cross_similarity(a, b, metric="cosine")
    assert matrix.shape == (2, 2)
    assert manifest.metadata["similarity_metric"] == "cosine"
    assert matrix[0, 0] == pytest.approx(1.0)  # alpha0 and beta0 point the same direction


def test_unknown_metric_fails_loud(tmp_path: Path) -> None:
    a = _member(tmp_path, "alpha", ["one two"], [[1, 0, 0, 0]])
    b = _member(tmp_path, "beta", ["three four"], [[0, 1, 0, 0]])
    with pytest.raises(ValueError, match="Unknown cross-similarity metric"):
        xs.compute_cross_similarity(a, b, metric="bogus")
