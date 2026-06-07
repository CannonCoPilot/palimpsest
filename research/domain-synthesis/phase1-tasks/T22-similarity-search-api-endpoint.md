# T22: Similarity Search API Endpoint

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 4 hours (Days 26-27, alongside T21)
**Dependencies**: T21 (VectorStore + embedding pipeline), T10 (FastAPI server skeleton, `/api/projects` endpoint)
**Outputs**: `core/palimpsest/server.py` (modified), `browser/src/components/DetailPanel/DetailPanel.tsx` (modified), `browser/src/stores/searchStore.ts` (modified), `core/tests/test_pipeline.py` (new test)

---

## v4.0 Critical Review

**Verdict: The FastAPI HTTP server for similarity search is eliminated. The entire search path is rebuilt as a Tauri command backed by Rust + sqlite-vec ANN. The browser component survives with a different data source.**

### What Is Broken

**The FastAPI server is the wrong transport for a desktop application.** Every similarity search round-trips from the WKWebView through the loopback network stack to a Python FastAPI process, which opens `embeddings.db`, calls into `embed_one()` (another HTTP call to Ollama), then queries the vector store, then serializes the result to JSON, then sends it back over HTTP. That is four hops (WebView → FastAPI → Ollama → sqlite-vec) when the correct answer is one hop (WebView → Rust Tauri command).

**The shared connection problem.** `SqliteVecStore` opened per-request (the original design's answer to write concurrency) means every search query pays the sqlite connection setup cost, plus extension loading overhead. At P&P scale this is imperceptible. At Phase 2 scale with five novels and concurrent search queries, you pay that cost every time.

**`embed_one(query)` is Python calling Ollama.** The query embedding call runs in the FastAPI handler thread, blocking it for ~250ms. FastAPI is async but the Ollama call would need `async httpx` to not block. The original spec uses `httpx.Client` (synchronous). This is a hidden blocking operation in an async context — it will cause thread starvation under any real load.

**Response payload contains truncated text.** The original spec returns first 200 characters of paragraph text in the API response. The paragraph text already lives in the Rust `AnnotStore` (loaded at project open). Why serialize it again over HTTP? The Tauri command can return paragraph indices alone; the frontend resolves text from already-loaded data.

**No latency target is specified.** "Similarity search returns within 10 seconds" appears in the smoke test. That is not a performance target — that is a timeout. The correct target is <500ms end-to-end for a query against 1,800 paragraphs: ~250ms for Ollama embed + <5ms for ANN search + <1ms for result assembly.

---

## v4.0 Rewrite

### Architecture

Similarity search is a Tauri command, not an HTTP endpoint. The Python FastAPI server is not involved.

```
User types query in DetailPanel
  → invoke("semantic_search", {project_id, query_text, k})
  → Rust: reqwest POST to Ollama /api/embed (~250ms)
  → Rust: EmbeddingStore.search() via sqlite-vec ANN (<5ms)
  → Rust: resolve paragraph snippets from AnnotStore (<1ms)
  → Tauri returns Vec<SimilarityResult> to frontend
  → React renders ranked list
Total: ~256ms
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Search trigger | React `invoke` via `@tauri-apps/api` |
| Query embedding | Rust `reqwest` → Ollama `/api/embed` |
| Vector search | Rust `EmbeddingStore.search()` (sqlite-vec ANN, <5ms) |
| Result assembly | Rust resolves paragraph data from `AnnotStore` arena |
| State management | Zustand `searchStore` holds results, loading, error state |
| Frontend display | DetailPanel semantic search section |

### Rust Tauri Command

```rust
// src-tauri/src/commands/search.rs

#[derive(serde::Serialize)]
pub struct SimilarityResult {
    pub paragraph_index: u32,
    pub score: f32,           // cosine similarity [0, 1]
    pub text_snippet: String, // first 200 chars from AnnotStore
    pub start: u32,           // char offset
    pub end: u32,
}

#[tauri::command]
pub async fn semantic_search(
    project_id: String,
    query_text: String,
    k: usize,
    state: tauri::State<'_, AppState>,
) -> Result<Vec<SimilarityResult>, String> {
    // Clamp k to [1, 50]
    let k = k.max(1).min(50);

    let core = state.core.lock().await;

    // Validate project exists
    let project = core.get_project(&project_id)
        .ok_or_else(|| format!("Project not found: {}", project_id))?;

    // Validate embeddings available
    let store = core.embedding_store(&project_id)
        .map_err(|_| "Embeddings not computed. Run palimpsest analyze first.".to_string())?;

    // Embed the query directly from Rust
    let query_vec = core.ollama_client
        .embed_one(&query_text)
        .await
        .map_err(|e| format!("Embedding service unavailable: {}", e))?;

    // ANN search: <5ms for 1M vectors
    let hits = store.search(&query_vec, k)
        .map_err(|e| e.to_string())?;

    // Resolve paragraph text from AnnotStore (already in Rust memory)
    let results = hits.into_iter().map(|(para_idx, score)| {
        let para = project.annot_store.get_paragraph(para_idx as usize);
        let snippet = para.text().chars().take(200).collect::<String>();
        SimilarityResult {
            paragraph_index: para_idx,
            score,
            text_snippet: snippet,
            start: para.start(),
            end: para.end(),
        }
    }).collect();

    Ok(results)
}
```

### Frontend

The `searchStore.ts` similarity search slice changes from `fetch('/api/search?...')` to `invoke`:

```typescript
// browser/src/stores/searchStore.ts

import { invoke } from '@tauri-apps/api/core';

interface SimilarityResult {
  paragraph_index: number;
  score: number;
  text_snippet: string;
  start: number;
  end: number;
}

interface SimilaritySearchSlice {
  similarityQuery: string;
  similarityResults: SimilarityResult[];
  similarityLoading: boolean;
  similarityError: string | null;
  setSimilarityQuery: (q: string) => void;
  runSimilaritySearch: (projectId: string, k?: number) => Promise<void>;
  clearSimilarityResults: () => void;
}

// In Zustand store:
runSimilaritySearch: async (projectId, k = 10) => {
  const { similarityQuery } = get();
  if (!similarityQuery.trim()) return;
  set({ similarityLoading: true, similarityError: null });
  try {
    const results = await invoke<SimilarityResult[]>('semantic_search', {
      projectId,
      queryText: similarityQuery,
      k,
    });
    set({ similarityResults: results, similarityLoading: false });
  } catch (err) {
    set({
      similarityError: String(err),
      similarityLoading: false,
      similarityResults: [],
    });
  }
},
```

The `DetailPanel` "Find similar passages" UI is identical to the original spec — input field, submit, ranked list, "Jump to" buttons. Only the data source changes.

### Performance Targets

| Operation | Target | Measured at |
|-----------|--------|-------------|
| Query embedding (Ollama direct) | <300ms | M4 Max, qwen3-embedding |
| sqlite-vec ANN search, k=10 | <5ms | 1,800 vectors, 2560-dim |
| Result assembly from AnnotStore | <1ms | Rust arena lookup |
| Total end-to-end (invoke → results) | <350ms | P&P full novel |
| Total end-to-end (5 novels loaded) | <350ms | No degradation with multiple projects |

### Test Strategy

Python server tests are removed. Rust command tests are added:

```rust
// src-tauri/src/commands/search_tests.rs

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[tokio::test]
    async fn test_semantic_search_returns_k_results() {
        // Set up mock AppState with pre-populated EmbeddingStore
        let state = mock_app_state_with_embeddings(100, 64).await;
        let results = semantic_search(
            "project-a".to_string(),
            "test query".to_string(),
            10,
            state,
        ).await.unwrap();
        assert_eq!(results.len(), 10);
    }

    #[tokio::test]
    async fn test_semantic_search_k_clamped() {
        let state = mock_app_state_with_embeddings(100, 64).await;
        let results = semantic_search(
            "project-a".to_string(),
            "test".to_string(),
            200,  // exceeds max of 50
            state,
        ).await.unwrap();
        assert!(results.len() <= 50);
    }

    #[tokio::test]
    async fn test_semantic_search_project_not_found() {
        let state = mock_app_state_with_embeddings(100, 64).await;
        let err = semantic_search(
            "nonexistent".to_string(),
            "test".to_string(),
            10,
            state,
        ).await.unwrap_err();
        assert!(err.contains("Project not found"));
    }

    #[tokio::test]
    async fn test_semantic_search_no_embeddings() {
        let state = mock_app_state_no_embeddings().await;
        let err = semantic_search(
            "project-a".to_string(),
            "test".to_string(),
            10,
            state,
        ).await.unwrap_err();
        assert!(err.contains("Embeddings not computed"));
    }

    #[tokio::test]
    async fn test_semantic_search_results_sorted_by_score() {
        let state = mock_app_state_with_embeddings(50, 64).await;
        let results = semantic_search(
            "project-a".to_string(),
            "test".to_string(),
            10,
            state,
        ).await.unwrap();
        // Scores should be in descending order
        let scores: Vec<f32> = results.iter().map(|r| r.score).collect();
        assert!(scores.windows(2).all(|w| w[0] >= w[1]));
    }
}
```

TypeScript (Vitest) — frontend only:

```typescript
// browser/src/stores/searchStore.test.ts

import { vi } from 'vitest';
// Mock @tauri-apps/api/core
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
}));

test('runSimilaritySearch calls invoke with correct args', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  (invoke as ReturnType<typeof vi.fn>).mockResolvedValue([
    { paragraph_index: 42, score: 0.91, text_snippet: 'It is a truth...', start: 100, end: 250 },
  ]);
  const store = useSearchStore.getState();
  store.setSimilarityQuery('marriage and money');
  await store.runSimilaritySearch('pride-and-prejudice', 10);
  expect(invoke).toHaveBeenCalledWith('semantic_search', {
    projectId: 'pride-and-prejudice',
    queryText: 'marriage and money',
    k: 10,
  });
  expect(store.similarityResults).toHaveLength(1);
  expect(store.similarityError).toBeNull();
});

test('runSimilaritySearch sets error on invoke failure', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  (invoke as ReturnType<typeof vi.fn>).mockRejectedValue('Embeddings not computed');
  const store = useSearchStore.getState();
  store.setSimilarityQuery('test');
  await store.runSimilaritySearch('project-a');
  expect(store.similarityError).toContain('Embeddings not computed');
  expect(store.similarityResults).toHaveLength(0);
});

test('runSimilaritySearch sets loading during invoke', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  let resolveInvoke!: (v: unknown) => void;
  (invoke as ReturnType<typeof vi.fn>).mockReturnValue(
    new Promise(resolve => { resolveInvoke = resolve; })
  );
  const store = useSearchStore.getState();
  store.setSimilarityQuery('test');
  const searchPromise = store.runSimilaritySearch('project-a');
  expect(store.similarityLoading).toBe(true);
  resolveInvoke([]);
  await searchPromise;
  expect(store.similarityLoading).toBe(false);
});
```

### What Is Removed

- `GET /api/search` FastAPI route — eliminated entirely
- `test_search_endpoint_*` Python tests — replaced by Rust unit tests
- `embed_one(query)` from `services/embedding.py` — query embedding done in Rust via `reqwest`
- Per-request `SqliteVecStore` open/close — replaced by persistent `EmbeddingStore` in AppState

### Acceptance Criteria (v4.0)

- `invoke('semantic_search', {projectId: 'pride-and-prejudice', queryText: 'marriage money', k: 5})` returns 5 results in <350ms when embeddings exist
- Each result has `paragraph_index` (u32), `score` (f32 in [0,1]), `text_snippet` (str), `start` (u32), `end` (u32)
- `k > 50` is clamped to 50; `k < 1` is clamped to 1
- Project not found → error string containing "Project not found"
- No embeddings → error string containing "Embeddings not computed"
- Ollama unavailable → error string containing "Embedding service unavailable"
- All Rust unit tests pass (`cargo test`)
- `tsc --strict` passes on all modified TypeScript files
- DetailPanel renders search form; submitting shows ranked results; "Jump to" updates viewStore

---

## Original Content (Reference)

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 4 hours (Days 26-27, alongside T21)
**Dependencies**: T21 (VectorStore + embedding pipeline), T10 (FastAPI server skeleton, `/api/projects` endpoint)
**Outputs**: `core/palimpsest/server.py` (modified), `browser/src/components/DetailPanel/DetailPanel.tsx` (modified), `browser/src/stores/searchStore.ts` (modified), `core/tests/test_pipeline.py` (new test)

### Context (original)

Once paragraph embeddings are stored in `cache/embeddings.db`, the most immediately useful feature is letting a scholar type a query and retrieve the paragraphs most semantically similar to it. The similarity search endpoint embeds the query string via Ollama, calls `VectorStore.search()`, and returns the top-k paragraph objects with their similarity scores.

### Design Decisions (original)

- **Paragraph text truncation in response**: The API returns the first 200 characters of paragraph text rather than the full text.
- **Shared VectorStore connection**: The server should not hold a long-lived open connection to `embeddings.db` because `embed_paragraphs` needs exclusive write access.
- **No authentication on search endpoint**: Consistent with §0.4 (local-only, no accounts).
- **`k` default of 10**: Matches the URL spec in §8.1 of the plan.
