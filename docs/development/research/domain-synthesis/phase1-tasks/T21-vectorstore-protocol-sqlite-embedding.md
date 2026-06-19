# T21: VectorStore Protocol + SqliteVecStore + Embedding Pipeline

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 8 hours (Days 26-27)
**Dependencies**: T16 (Ollama service manager / `embedding.py` stub), T15 (pipeline orchestration, `project.py` stable)
**Outputs**: `core/palimpsest/vectorstore/protocol.py`, `core/palimpsest/vectorstore/sqlite_vec.py`, `core/palimpsest/vectorstore/__init__.py`, `core/palimpsest/services/embedding.py` (modified), `core/tests/test_vectorstore.py`

---

## v4.0 Critical Review

**Verdict: The entire server boundary and Python-owned embedding pipeline must be restructured. The Protocol design is sound; the storage and IPC assumptions are not.**

### What Is Broken

**The HTTP boundary for embedding is catastrophic at scale.** `embed_batch` issuing one `httpx.POST` per batch of 32 is fine for Pride and Prejudice at 1,800 paragraphs (~56 HTTP calls). Load five novels simultaneously (Phase 2-3 goal) and you have 280+ sequential HTTP calls, each carrying 32 paragraphs × 2,560-dim vectors in JSON. At ~12ms per call (Ollama local latency, per MEMORY.md), that is 3.4 seconds per novel in network overhead before any actual embedding computation. And the results all land in Python heap as `list[list[float]]` — 1,800 × 2,560 floats = 18.4M floats × 8 bytes = 147MB per novel in Python, immediately.

**sqlite-vec is accessed from both the Python pipeline and the Rust core, with no ownership model.** The Python write path (`embed_paragraphs`) and the Rust read path (`RangeIndex` rebuild, cross-text dotplot) both open `cache/embeddings.db`. sqlite-vec with WAL mode can handle this, but the current design has no locking discipline, no connection pool, and no assertion about which process owns write access. This is a latent data corruption vector.

**The `VectorStore.search()` returning `list[tuple[str, float]]` is the wrong abstraction for the Rust core.** When Rust needs to query the N nearest paragraphs to build the self-similarity matrix, it does not want a Python list returned through the FFI boundary. It wants direct sqlite-vec query access. The current Protocol adds an indirection that costs memory on every call.

**No performance target is specified for the embedding pipeline itself.** "Under 2 minutes for P&P on M1" is noted as a manual benchmark. This is not a gate. M4 Max should embed 1,800 paragraphs in under 20 seconds. No CI assertion enforces this.

**The `embed_paragraphs` idempotency check is O(N) per call.** `store.count()` tells you how many are stored, not which IDs. The current spec says "check individual IDs" — that is N separate sqlite reads before embedding begins. For 1,800 paragraphs this is 1,800 SQL lookups before a single embedding is computed.

---

## v4.0 Rewrite

### Architecture

Under Tauri+Rust+WebGPU, the vectorstore ownership model is:

- **Python** (via `AnalysisPipeline` subprocess): writes embeddings to `cache/embeddings.db` via the sqlite-vec Python bindings. This is the sole writer. Python is the NLP subprocess; it owns the write path.
- **Rust** (`palimpsest-core`): reads embeddings via `rusqlite` with the sqlite-vec extension loaded. Rust implements the search, matrix construction, and self-similarity computation. Rust never writes to `embeddings.db`.
- **Tauri commands** (`get_embeddings`, `search_similar`): expose Rust search results to the frontend over zero-copy IPC.

The `VectorStore` Python Protocol still exists as the write-side abstraction for the Python subprocess. It is not used by Rust.

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Write path | Python + `sqlite-vec` (pip package) |
| Read path | Rust + `rusqlite` + `sqlite-vec` C extension via `libloading` |
| Embedding model | Ollama async via `httpx.AsyncClient` with connection pool |
| Batch async | `asyncio.gather` over all paragraph batches in parallel |
| Rust search | `sqlite-vec` ANN query via rusqlite, returns `Vec<(u32, f32)>` |
| IPC to frontend | Tauri `invoke` returning `Vec<SimilarityResult>` |

### Performance Targets

| Operation | Target | Technique |
|-----------|--------|-----------|
| Embed 1,800 paragraphs (P&P) | <20s on M4 Max | Async parallel batches to Ollama |
| Embed 1,800 paragraphs (P&P) | <60s on M1 | Same |
| sqlite-vec ANN search (top-10) | <5ms for 1M vectors | Native ANN index in sqlite-vec |
| Load all embeddings into Rust arena | <100ms for 1M vectors at 2560-dim | mmap'd read |
| Idempotency check | <1ms | Single `COUNT(*)` + stored watermark |

### Python Write Path

#### `vectorstore/protocol.py`

The `VectorStore` Protocol is preserved. Add `add_batch_async` for the new async pipeline:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class VectorStore(Protocol):
    def add(self, ids: list[str], vectors: list[list[float]],
            metadata: list[dict] | None = None) -> None: ...
    def add_batch_async(self, ids: list[str], vectors: list[list[float]]) -> None: ...
    def search(self, query: list[float], k: int = 10) -> list[tuple[str, float]]: ...
    def count(self) -> int: ...
    def delete(self, ids: list[str]) -> None: ...
    def close(self) -> None: ...
    def max_stored_index(self) -> int: ...  # NEW: O(1) watermark for idempotency
```

`max_stored_index()` runs `SELECT MAX(para_index) FROM vectors` — one query, constant time. On subsequent `embed_paragraphs` calls, only paragraphs with index > watermark are embedded. This replaces N individual ID lookups.

#### `vectorstore/sqlite_vec.py`

```python
class SqliteVecStore:
    def __init__(self, db_path: Path, dim: int, wal: bool = True) -> None:
        self._conn = sqlite3.connect(str(db_path))
        # Load sqlite-vec extension
        self._conn.enable_load_extension(True)
        sqlite_vec.load(self._conn)
        self._conn.enable_load_extension(False)
        if wal:
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        # Schema: id TEXT, para_index INTEGER for O(1) watermark
        self._conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_items USING vec0(
                para_index INTEGER PRIMARY KEY,
                embedding float[{dim}]
            )
        """.format(dim=dim))
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS vec_meta (
                para_index INTEGER PRIMARY KEY,
                id TEXT NOT NULL,
                metadata TEXT
            )
        """)
        self._conn.commit()

    def max_stored_index(self) -> int:
        row = self._conn.execute(
            "SELECT MAX(para_index) FROM vec_meta"
        ).fetchone()
        return row[0] if row[0] is not None else -1
```

The key change: the primary key in `vec_items` is `para_index` (integer), not `id` (string). This enables the O(1) watermark. The string `id` lives in `vec_meta` as metadata.

#### `services/embedding.py`

Replace synchronous `httpx.Client` with an async pipeline:

```python
import asyncio
import httpx

async def embed_batch_async(
    texts: list[str],
    client: httpx.AsyncClient,
    model: str = "qwen3-embedding",
    timeout: float = 30.0,
) -> list[list[float]]:
    """Embed a batch of texts via Ollama async API."""
    response = await client.post(
        "/api/embed",
        json={"model": model, "input": texts},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["embeddings"]

async def embed_paragraphs_async(
    project: Project,
    store: VectorStore,
    batch_size: int = 32,
    max_concurrent: int = 4,
) -> int:
    """Embed all paragraphs using concurrent async batches.

    Uses max_stored_index() watermark for O(1) idempotency check.
    Submits up to max_concurrent batches to Ollama simultaneously.

    Returns count of newly embedded paragraphs.
    """
    watermark = store.max_stored_index()
    pending = [p for p in project.paragraphs if p.index > watermark]
    if not pending:
        return 0

    sem = asyncio.Semaphore(max_concurrent)
    async with httpx.AsyncClient(base_url="http://localhost:11434") as client:
        async def embed_one_batch(batch: list[Paragraph]) -> None:
            async with sem:
                texts = [p.text for p in batch]
                vectors = await embed_batch_async(texts, client)
                ids = [f"{project.id}:para:{p.index}" for p in batch]
                indices = [p.index for p in batch]
                store.add(ids, vectors, [{"para_index": i} for i in indices])

        batches = [
            pending[i:i+batch_size] for i in range(0, len(pending), batch_size)
        ]
        await asyncio.gather(*[embed_one_batch(b) for b in batches])
    return len(pending)

def embed_paragraphs(project: Project, store: VectorStore, **kwargs: Any) -> int:
    """Synchronous wrapper for embed_paragraphs_async."""
    return asyncio.run(embed_paragraphs_async(project, store, **kwargs))
```

`max_concurrent=4` submits 4 batches to Ollama simultaneously. On M4 Max, Ollama processes them in parallel (each batch is ~1 second compute). Total time for 1,800 paragraphs: ceil(1800/32) = 57 batches ÷ 4 concurrent = ~15 batches × 1s = ~15 seconds. The MEMORY.md notes direct Ollama latency is ~0.25s per call; 57 calls at 0.25s each sequentially = 14.25s. Async concurrency reduces wall time further.

### Rust Read Path

In `palimpsest-core/src/vectorstore.rs`:

```rust
use rusqlite::{Connection, params};

pub struct EmbeddingStore {
    conn: Connection,
    dim: usize,
}

impl EmbeddingStore {
    pub fn open(db_path: &Path) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        // Load sqlite-vec native extension
        unsafe {
            conn.load_extension(Path::new("sqlite-vec"), None)?;
        }
        let dim = conn.query_row(
            "SELECT vec_length(embedding) FROM vec_items LIMIT 1",
            [],
            |row| row.get::<_, usize>(0),
        )?;
        Ok(Self { conn, dim })
    }

    /// ANN search: returns (para_index, cosine_similarity) pairs, sorted desc.
    /// <5ms for 1M vectors via sqlite-vec native ANN index.
    pub fn search(&self, query: &[f32], k: usize) -> Result<Vec<(u32, f32)>> {
        let query_blob = bytemuck::cast_slice(query);
        let mut stmt = self.conn.prepare(
            "SELECT para_index, distance FROM vec_items
             WHERE embedding MATCH ?1
             ORDER BY distance LIMIT ?2"
        )?;
        let results = stmt.query_map(params![query_blob, k as i64], |row| {
            Ok((row.get::<_, u32>(0)?, 1.0 - row.get::<_, f32>(1)?))
        })?
        .collect::<Result<Vec<_>, _>>()?;
        Ok(results)
    }

    /// Load all embeddings as a flat f32 arena for matrix computation.
    /// Returns (N, dim, flat_data) suitable for BLAS/SIMD cosine similarity.
    pub fn load_all_flat(&self) -> Result<(usize, usize, Vec<f32>)> {
        let n: usize = self.conn.query_row(
            "SELECT COUNT(*) FROM vec_items", [], |r| r.get(0)
        )?;
        let mut data = Vec::with_capacity(n * self.dim);
        let mut stmt = self.conn.prepare(
            "SELECT embedding FROM vec_items ORDER BY para_index"
        )?;
        stmt.query_map([], |row| {
            let blob: Vec<u8> = row.get(0)?;
            Ok(blob)
        })?.for_each(|blob| {
            let floats: &[f32] = bytemuck::cast_slice(&blob.unwrap());
            data.extend_from_slice(floats);
        });
        Ok((n, self.dim, data))
    }
}
```

This `load_all_flat` is called by the self-similarity matrix computation in T23. It returns a contiguous `Vec<f32>` which is handed to the SIMD cosine similarity kernel — no Python, no JSON, no HTTP.

### Tauri Commands

```rust
// src-tauri/src/commands/search.rs

#[tauri::command]
pub async fn semantic_search(
    project_id: String,
    query_text: String,
    k: usize,
    state: tauri::State<'_, AppState>,
) -> Result<Vec<SimilarityResult>, String> {
    let core = state.core.lock().await;

    // Embed query via Ollama (direct, not through Python)
    let query_vec = core.embed_one(&query_text).await
        .map_err(|e| e.to_string())?;

    // Search via Rust EmbeddingStore
    let store = core.embedding_store(&project_id)
        .map_err(|e| e.to_string())?;
    let hits = store.search(&query_vec, k)
        .map_err(|e| e.to_string())?;

    // Resolve paragraph text from AnnotStore (already in Rust)
    let results = hits.into_iter().map(|(idx, score)| {
        let para = core.get_paragraph(&project_id, idx as usize);
        SimilarityResult {
            paragraph_index: idx,
            score,
            text: para.text[..para.text.len().min(200)].to_string(),
            start: para.start,
            end: para.end,
        }
    }).collect();

    Ok(results)
}
```

Note: `embed_one` in the Tauri command hits Ollama directly from Rust using `reqwest` — no Python round-trip for query embedding. The search happens entirely in Rust. Latency from user query to results: ~250ms (Ollama embed) + <5ms (sqlite-vec ANN) = ~255ms total vs. the current Python HTTP stack at ~1-2 seconds.

### Data Flow

```
palimpsest analyze (Python subprocess)
  → embed_paragraphs_async()
  → asyncio.gather() × 4 concurrent batches to Ollama
  → SqliteVecStore.add() writes to embeddings.db (WAL mode)
  → Rust detects file change, updates EmbeddingStore

User types search query (Tauri frontend)
  → invoke("semantic_search", {project_id, query, k})
  → Rust: reqwest → Ollama /api/embed (250ms)
  → Rust: EmbeddingStore.search() via sqlite-vec ANN (<5ms)
  → Rust: resolve paragraph text from AnnotStore (<1ms)
  → Frontend receives Vec<SimilarityResult> (~256ms total)
```

### Files

| File | Language | Role |
|------|----------|------|
| `core/palimpsest/vectorstore/protocol.py` | Python | VectorStore Protocol (write side) |
| `core/palimpsest/vectorstore/sqlite_vec.py` | Python | SqliteVecStore with WAL, para_index watermark |
| `core/palimpsest/services/embedding.py` | Python | Async embed pipeline, max_concurrent=4 |
| `palimpsest-core/src/vectorstore.rs` | Rust | EmbeddingStore read path, ANN search, flat load |
| `src-tauri/src/commands/search.rs` | Rust | semantic_search Tauri command |
| `core/tests/test_vectorstore.py` | Python | Write-path unit tests |
| `core/tests/test_embedding_perf.py` | Python | Benchmark: embed 1,800 paragraphs <20s on M4 |

### Performance Benchmarks Required

These are CI gates, not manual notes:

```python
# core/tests/test_embedding_perf.py

@pytest.mark.benchmark
@pytest.mark.skipif(not os.getenv("PALIMPSEST_TEST_OLLAMA"), reason="requires Ollama")
def test_embed_1800_paragraphs_under_20s(pp_full_project, tmp_path):
    """Embedding P&P (1,800 paras, 2560-dim) must complete in <20s on M4 Max."""
    store = SqliteVecStore(tmp_path / "emb.db", dim=2560)
    start = time.monotonic()
    count = embed_paragraphs(pp_full_project, store, batch_size=32, max_concurrent=4)
    elapsed = time.monotonic() - start
    assert count == pp_full_project.paragraph_count
    assert elapsed < 20.0, f"Embedding took {elapsed:.1f}s, target <20s on M4"

@pytest.mark.benchmark
def test_sqlite_vec_search_under_5ms(tmp_path):
    """sqlite-vec ANN search must return top-10 in <5ms for 10K stored vectors."""
    store = SqliteVecStore(tmp_path / "emb.db", dim=128)  # smaller dim for speed
    # Pre-populate 10K vectors
    rng = np.random.default_rng(42)
    vectors = rng.standard_normal((10_000, 128)).tolist()
    ids = [f"project:para:{i}" for i in range(10_000)]
    store.add(ids, vectors)
    query = rng.standard_normal(128).tolist()
    start = time.monotonic()
    results = store.search(query, k=10)
    elapsed = (time.monotonic() - start) * 1000
    assert len(results) == 10
    assert elapsed < 5.0, f"ANN search took {elapsed:.2f}ms, target <5ms"
```

### Test Strategy

All tests from the original T21 are preserved. Additional tests:

```python
def test_max_stored_index_watermark(tmp_path):
    """max_stored_index() returns -1 when empty, correct max after add."""
    store = SqliteVecStore(tmp_path / "test.db", dim=4)
    assert store.max_stored_index() == -1
    store.add(["p:0", "p:1", "p:2"], [[0.1]*4, [0.2]*4, [0.3]*4],
              [{"para_index": 0}, {"para_index": 1}, {"para_index": 2}])
    assert store.max_stored_index() == 2

def test_embed_paragraphs_async_concurrent(tmp_path, mock_ollama_async):
    """embed_paragraphs_async submits batches concurrently (max_concurrent=4)."""
    # mock_ollama_async records concurrent request count
    # Assert peak concurrent requests >= 2 (would be 4 on large corpus)

def test_wal_mode_allows_concurrent_read(tmp_path):
    """sqlite-vec in WAL mode allows simultaneous reader + writer."""
    store = SqliteVecStore(tmp_path / "test.db", dim=4, wal=True)
    # Open second connection, assert read succeeds while first is mid-write
```

---

## Original Content (Reference)

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 8 hours (Days 26-27)
**Dependencies**: T16 (Ollama service manager / `embedding.py` stub), T15 (pipeline orchestration, `project.py` stable)
**Outputs**: `core/palimpsest/vectorstore/protocol.py`, `core/palimpsest/vectorstore/sqlite_vec.py`, `core/palimpsest/vectorstore/__init__.py`, `core/palimpsest/services/embedding.py` (modified), `core/tests/test_vectorstore.py`

### Context

The self-similarity matrix (T23) and similarity search endpoint (T22) both require paragraph embeddings stored in a queryable vector index. The `VectorStore` is defined as a Protocol so that `SqliteVecStore` (Phase 1 implementation) can be swapped for a FAISS or Qdrant backend without changing any caller code. Per §6 of the plan, the Protocol is the architectural boundary: callers depend only on `add`, `search`, `count`, and `delete`.

Embeddings are produced via the Ollama HTTP API (model `qwen3-embedding-4b`, 2560-dim or whatever the configured model returns). The pipeline embeds all paragraphs in batches and persists them to `cache/embeddings.db` using sqlite-vec. On subsequent `analyze` runs, already-embedded paragraphs (identified by paragraph SHA-256 derived from the reference SHA-256 + paragraph offset) are skipped.

### Acceptance Criteria (original)

- `isinstance(SqliteVecStore(tmp_path / "test.db", dim=4), VectorStore)` returns `True` at runtime
- `store.add(["a"], [[0.1, 0.2, 0.3, 0.4]])` followed by `store.count()` returns `1`
- `store.search([0.1, 0.2, 0.3, 0.4], k=1)` returns `[("a", pytest.approx(1.0, abs=1e-5))]`
- `store.delete(["a"])` then `store.count()` returns `0`
- `embed_paragraphs` called twice on the same project does not re-embed already-stored paragraphs
- P&P full text embeds in under 2 minutes on M1 hardware and under 45 seconds on M4 hardware
- `embed_paragraphs` with Ollama unreachable raises `EmbeddingServiceUnavailable`
- `mypy --strict` passes on `vectorstore/` package
- `ruff check` passes with zero violations
