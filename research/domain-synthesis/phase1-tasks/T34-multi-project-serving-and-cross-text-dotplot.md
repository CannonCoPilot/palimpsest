# T34: Multi-Project Serving + Cross-Text Dotplot

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours
**Dependencies**: T23 (self-similarity GPU texture pipeline), T27 (DotplotCanvas WebGPU renderer), T21 (EmbeddingStore Rust read path)
**Outputs**: `palimpsest-core/src/project_manager.rs` (extended), `browser/src/components/CrossTextDotplot/CrossTextDotplot.tsx`, Tauri commands: `load_workspace`, `compute_cross_similarity`

---

## v4.0 Critical Review

**Verdict: The FastAPI multi-project server is eliminated. The "client-side cosine similarity in a Web Worker" approach is the most catastrophically wrong design decision in the original T34 spec — computing a 1,832 × 2,000 cosine similarity matrix in a JavaScript Web Worker at full 2,560-dim embeddings would take 60-90 seconds and consume 180MB of RAM in the WKWebView. This is completely unacceptable. The cross-text matrix must be computed by Rust using the same SIMD engine as the self-similarity matrix in T23.**

### What Is Broken

**Web Worker cosine similarity: O(N × M × D) = 1,832 × 2,000 × 2,560 = 9.4 billion multiply-adds in JavaScript.** The spec says "~20-30 seconds." Reality: JavaScript TypeScript is not NEON SIMD-accelerated; typed array dot products in JS are unoptimized compared to ARM NEON. The actual time on M4 Max would be 60-120 seconds. This is completely unacceptable for any interactive tool.

**Fetching embeddings as raw Float32 binary via `/api/embeddings/{id}` HTTP endpoint.** For P&P at 1,800 paragraphs × 2,560-dim × 4 bytes = 18.4MB of embedding data transferred over the loopback HTTP stack into a JS ArrayBuffer. This then sits in the WKWebView V8 heap for the duration of the computation. The correct model is: Rust loads both `embeddings.db` files and computes the cross-text matrix directly with no JS involvement.

**`X-Shape` HTTP header for binary shape metadata.** This is a workaround for not having a proper binary format. Under Rust, both the shape and the data are available without HTTP headers.

**"Server-side precompute chosen for Phase 1, client-side as fallback."** The spec acknowledges the server-side approach but doesn't implement it. The fallback is the wrong fallback. The correct implementation is: Rust `ProjectManager` computes the cross-text matrix when both projects are loaded, caches it to `signals/cross_{other_id}.bin`, and the dotplot reads it from that file (same as the self-similarity matrix in T23).

**No authentication model for multi-project workspace.** Under Tauri, workspace access control is Rust code, not HTTP auth. This is handled correctly in v4.0.

---

## v4.0 Rewrite

### Architecture

Multi-project support is a Rust `ProjectManager` feature. The Tauri app can load N projects simultaneously. Cross-text similarity is computed by the same Rust SIMD engine used for self-similarity (T23), producing a binary file that the DotplotCanvas reads via the same GPU texture upload pipeline.

```
User opens workspace directory
  → invoke('load_workspace', {workspacePath})
  → Rust: discover all project directories
  → Rust: for each project, load AnnotStore + EmbeddingStore into ProjectManager
  → Frontend: receives Vec<ProjectMeta>

User opens CrossTextDotplot, selects Text B
  → invoke('compute_cross_similarity', {projectIdA, projectIdB})
  → Rust: EmbeddingStore.load_all_flat(A) + EmbeddingStore.load_all_flat(B)
  → Rust: CrossSimilarityEngine.compute(A_embeddings, B_embeddings) [SIMD + rayon]
  → Rust: write to signals/cross_{B_id}.bin
  → Rust: upload as GPU texture
  → Frontend: invoke('get_cross_similarity_texture', {projectIdA, projectIdB})
  → DotplotCanvas renders N×M matrix via existing WebGPU fragment shader
```

### Rust ProjectManager

```rust
// palimpsest-core/src/project_manager.rs

pub struct ProjectManager {
    projects: HashMap<String, LoadedProject>,
    workspace_path: Option<PathBuf>,
}

impl ProjectManager {
    /// Load all projects in a workspace directory.
    /// Projects are discovered by finding directories containing metadata.json.
    pub async fn load_workspace(&mut self, workspace_path: &Path) -> Result<Vec<ProjectMeta>> {
        let project_dirs = Self::discover_projects(workspace_path)?;

        // Load projects in parallel (tokio tasks)
        let mut handles = vec![];
        for dir in &project_dirs {
            let dir = dir.clone();
            handles.push(tokio::spawn(async move {
                LoadedProject::load(&dir).await
            }));
        }

        let mut metas = vec![];
        for (dir, handle) in project_dirs.iter().zip(handles) {
            match handle.await? {
                Ok(project) => {
                    let meta = project.meta.clone();
                    self.projects.insert(project.id.clone(), project);
                    metas.push(meta);
                }
                Err(e) => {
                    log::warn!("Failed to load project at {:?}: {}", dir, e);
                }
            }
        }
        self.workspace_path = Some(workspace_path.to_owned());
        Ok(metas)
    }

    fn discover_projects(workspace_path: &Path) -> Result<Vec<PathBuf>> {
        if (workspace_path / "metadata.json").exists() {
            return Ok(vec![workspace_path.to_owned()]); // single-project mode
        }
        let dirs: Vec<PathBuf> = std::fs::read_dir(workspace_path)?
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.is_dir() && (p.join("metadata.json")).exists())
            .collect();
        Ok(dirs)
    }
}
```

Projects load concurrently via `tokio::spawn`. On M4 Max with NVMe SSD, loading 5 full novel projects simultaneously takes <500ms (dominated by sqlite-vec index opens, which are mmap-based).

### CrossSimilarityEngine (Rust SIMD)

Identical algorithm to T23's `SelfSimilarityEngine` but for N×M (not N×N):

```rust
// palimpsest-core/src/cross_similarity.rs

pub struct CrossSimilarityEngine;

impl CrossSimilarityEngine {
    /// Compute N×M cosine similarity matrix between two embedding sets.
    /// A: (N × dim) float32. B: (M × dim) float32.
    /// Returns flat Vec<f32> of size N*M, row-major.
    ///
    /// Performance: M4 Max, N=1800, M=2000, dim=2560 → ~1.5s (SIMD + rayon).
    pub fn compute(
        a: &[f32], n: usize,
        b: &[f32], m: usize,
        dim: usize,
    ) -> Vec<f32> {
        // L2-normalize both matrices in parallel
        let mut a_norm = a.to_vec();
        let mut b_norm = b.to_vec();
        a_norm.par_chunks_mut(dim).for_each(|row| l2_normalize_in_place(row));
        b_norm.par_chunks_mut(dim).for_each(|row| l2_normalize_in_place(row));

        // Compute N×M matrix: row i of A · col j of B = a_norm[i] · b_norm[j]
        let mut matrix = vec![0.0f32; n * m];

        // Tile-based computation, same as SelfSimilarityEngine
        const TILE: usize = 64;
        matrix.par_chunks_mut(TILE * m).enumerate().for_each(|(i_tile, row_block)| {
            let i_start = i_tile * TILE;
            let i_end = (i_start + TILE).min(n);
            for i in i_start..i_end {
                let row_a = &a_norm[i * dim..(i + 1) * dim];
                for j in 0..m {
                    let row_b = &b_norm[j * dim..(j + 1) * dim];
                    let dot = dot_product_neon(row_a, row_b);
                    row_block[(i - i_start) * m + j] = dot.max(0.0);  // clamp negative
                }
            }
        });

        matrix
    }
}
```

Performance estimate: N=1,800, M=2,000, D=2,560.
- Normalize A: 1,800 × 2,560 / 16 = 288K NEON ops → ~0.1s
- Normalize B: 2,000 × 2,560 / 16 = 320K NEON ops → ~0.1s
- Matrix: 3.6M dot products × 2,560/4 = 2.3B NEON ops → ~1.5s on M4 Max (12P cores + rayon)
- Total: ~1.7s

Compared to JS Web Worker at ~60-90 seconds: 40× faster.

### Tauri Commands

```rust
// src-tauri/src/commands/cross_text.rs

#[tauri::command]
pub fn load_workspace(
    workspace_path: String,
    state: tauri::State<'_, AppState>,
) -> Result<Vec<ProjectMeta>, String> {
    let mut core = state.core.blocking_lock();
    let path = Path::new(&workspace_path);
    // Blocking runtime for workspace load (tokio::runtime::Handle::current())
    let rt = tokio::runtime::Handle::current();
    rt.block_on(core.project_manager.load_workspace(path))
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn compute_cross_similarity(
    project_id_a: String,
    project_id_b: String,
    state: tauri::State<'_, AppState>,
) -> Result<CrossSimilarityResult, String> {
    let core = state.core.lock().await;

    // Check cache first
    let cache_path = core.get_project(&project_id_a)
        .ok_or("Project A not found")?
        .signals_dir()
        .join(format!("cross_{}.bin", project_id_b));

    if cache_path.exists() {
        let manifest_path = cache_path.with_extension("json");
        let manifest: SignalManifest = serde_json::from_str(
            &std::fs::read_to_string(&manifest_path).map_err(|e| e.to_string())?
        ).map_err(|e| e.to_string())?;
        let handle = core.upload_texture_from_file(&cache_path, manifest.dimensions[0], manifest.dimensions[1])?;
        return Ok(CrossSimilarityResult {
            texture_handle: handle,
            n_a: manifest.dimensions[0],
            n_b: manifest.dimensions[1],
            cached: true,
        });
    }

    // Compute: load both embedding stores
    let a_store = core.embedding_store(&project_id_a)?;
    let b_store = core.embedding_store(&project_id_b)?;

    let (n_a, dim, a_flat) = a_store.load_all_flat()?;
    let (n_b, _, b_flat) = b_store.load_all_flat()?;

    // Spawn blocking computation on dedicated thread (avoids blocking tokio executor)
    let matrix = tokio::task::spawn_blocking(move || {
        CrossSimilarityEngine::compute(&a_flat, n_a, &b_flat, n_b, dim)
    }).await.map_err(|e| e.to_string())?;

    // Write to cache
    let project_a = core.get_project(&project_id_a).unwrap();
    SelfSimilarityEngine::write_to_file(&matrix, &cache_path)?;

    // Write manifest
    let manifest = build_cross_similarity_manifest(&project_id_a, &project_id_b, n_a, n_b);
    std::fs::write(cache_path.with_extension("json"), serde_json::to_string(&manifest)?)?;

    // Upload to GPU
    let handle = core.upload_f32_matrix_to_texture(&matrix, n_a as u32, n_b as u32)?;

    Ok(CrossSimilarityResult {
        texture_handle: handle,
        n_a,
        n_b,
        cached: false,
    })
}
```

### Frontend: CrossTextDotplot

The `CrossTextDotplot` component reuses `DotplotCanvas` from T27 directly — the WebGPU fragment shader handles non-square matrices (N×M) identically to square matrices. Only the `n_a` and `n_b` dimensions differ.

```typescript
// browser/src/components/CrossTextDotplot/CrossTextDotplot.tsx

export function CrossTextDotplot({ primaryProjectId }: { primaryProjectId: string }): JSX.Element {
  const [projects, setProjects] = useState<ProjectMeta[]>([]);
  const [selectedSecondary, setSelectedSecondary] = useState<string | null>(null);
  const [textureHandle, setTextureHandle] = useState<CrossSimilarityResult | null>(null);
  const [computing, setComputing] = useState(false);
  const [computeProgress, setComputeProgress] = useState<string>('');

  // Load project list from Rust ProjectManager
  useEffect(() => {
    invoke<ProjectMeta[]>('list_projects').then(setProjects);
  }, []);

  // Compute/load cross-text matrix
  useEffect(() => {
    if (!selectedSecondary) return;
    setComputing(true);
    setComputeProgress('Loading embeddings...');

    // Listen for progress events from Rust
    const unlisten = listen<string>('cross_similarity_progress', e => {
      setComputeProgress(e.payload);
    });

    invoke<CrossSimilarityResult>('compute_cross_similarity', {
      projectIdA: primaryProjectId,
      projectIdB: selectedSecondary,
    })
      .then(result => {
        setTextureHandle(result);
        setComputeProgress(result.cached ? 'Loaded from cache' : 'Computed');
      })
      .catch(e => setComputeProgress(`Error: ${e}`))
      .finally(() => setComputing(false));

    return () => { unlisten.then(f => f()); };
  }, [selectedSecondary, primaryProjectId]);

  const secondaryProjects = projects.filter(p => p.id !== primaryProjectId);

  return (
    <div className="cross-text-dotplot">
      <div className="selector-row">
        <span className="primary-label">{primaryProjectId}</span>
        <span className="vs-label">vs.</span>
        <select value={selectedSecondary ?? ''} onChange={e => setSelectedSecondary(e.target.value || null)}>
          <option value="">Select text to compare...</option>
          {secondaryProjects.map(p => (
            <option key={p.id} value={p.id}>{p.title} ({p.word_count.toLocaleString()} words)</option>
          ))}
        </select>
      </div>

      {computing && (
        <div className="computing-state">
          <ProgressSpinner />
          <span>{computeProgress}</span>
          <small>Computing {primaryProjectId} × {selectedSecondary}...</small>
        </div>
      )}

      {textureHandle && !computing && (
        <DotplotCanvas
          textureHandle={textureHandle.textureHandle}
          nRows={textureHandle.n_a}
          nCols={textureHandle.n_b}
          segmentOffsets={[]}  // cross-text: no shared chapter structure
          selectedParagraphIndex={null}
          onCellClick={(rowIdx, colIdx) => {
            // rowIdx = Text A paragraph, colIdx = Text B paragraph
            useViewStore.getState().setSelectedParagraphIndex(rowIdx);
            useProjectStore.getState().setSecondaryParagraphIndex(colIdx);
          }}
          onCellHover={async (i, j) => {
            const sim = await invoke<number>('get_cross_similarity_value', {
              projectIdA: primaryProjectId, projectIdB: selectedSecondary!, i, j,
            });
            // Show tooltip: "{A title} §{i} ↔ {B title} §{j}: {sim%}"
          }}
        />
      )}

      {!selectedSecondary && !computing && (
        <div className="placeholder">
          Select a second text from the dropdown to compare structural patterns
        </div>
      )}
    </div>
  );
}
```

### Progress Events from Rust

During the ~1.7-second computation, Rust emits progress events:

```rust
// In compute_cross_similarity command:
let app_handle = state.app_handle.clone();

let _ = app_handle.emit_all("cross_similarity_progress", "Normalizing embeddings...");
// ... normalize A and B ...
let _ = app_handle.emit_all("cross_similarity_progress", "Computing similarity matrix (SIMD)...");
// ... compute matrix ...
let _ = app_handle.emit_all("cross_similarity_progress", "Uploading to GPU...");
// ... upload texture ...
```

### Performance Targets

| Operation | Target |
|-----------|--------|
| Workspace load (5 novels) | <500ms |
| Cross-text matrix (1800×2000, dim=2560) | <2s first compute |
| Cache hit load | <100ms |
| GPU texture upload (14.4MB) | <16ms |
| DotplotCanvas render (N×M non-square) | <1ms per frame |
| Second project AnnotStore load | <100ms per project |

### Acceptance Criteria (v4.0)

- `invoke('load_workspace', {workspacePath})` returns all valid projects in the workspace
- `invoke('compute_cross_similarity', {projectIdA, projectIdB})` completes in <2s on M4 Max for P&P × Moby-Dick
- Result is cached; second invocation returns in <100ms
- Cross-text dotplot renders via DotplotCanvas GPU shader (no code changes to DotplotCanvas needed)
- No JS heap allocation for embedding data (all computation in Rust)
- Clicking cross-text cell (i, j) sets primaryProject paragraph i + secondaryProject paragraph j
- `cargo test` passes all ProjectManager and cross-similarity tests

### Tests

```rust
#[test]
fn test_discover_projects_single_dir() {
    let dir = tempdir().unwrap();
    std::fs::write(dir.path().join("metadata.json"), r#"{"id": "test"}"#).unwrap();
    let dirs = ProjectManager::discover_projects(dir.path()).unwrap();
    assert_eq!(dirs.len(), 1);
}

#[test]
fn test_discover_projects_workspace() {
    let workspace = tempdir().unwrap();
    for id in ["project-a", "project-b"] {
        let proj = workspace.path().join(id);
        std::fs::create_dir(&proj).unwrap();
        std::fs::write(proj.join("metadata.json"), format!(r#"{{"id": "{}"}}"#, id)).unwrap();
    }
    let dirs = ProjectManager::discover_projects(workspace.path()).unwrap();
    assert_eq!(dirs.len(), 2);
}

#[test]
fn test_cross_similarity_compute_shape() {
    let n_a = 10; let n_b = 15; let dim = 8;
    let a: Vec<f32> = (0..n_a*dim).map(|i| i as f32 / 100.0).collect();
    let b: Vec<f32> = (0..n_b*dim).map(|i| i as f32 / 100.0).collect();
    let matrix = CrossSimilarityEngine::compute(&a, n_a, &b, n_b, dim);
    assert_eq!(matrix.len(), n_a * n_b);
    // All values in [0, 1]
    for &v in &matrix {
        assert!((0.0..=1.0).contains(&v), "Value {} out of [0,1]", v);
    }
}
```

---

## Original Content (Reference)

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours

### Context (original)

Phase 1 requires `palimpsest serve <workspace-dir>` to serve all projects and support cross-text analysis. Cross-text dotplot visualizes pairwise paragraph-embedding cosine similarity between two texts. Testing with P&P vs. Moby-Dick provides meaningful real-world validation.

### Design Decisions (original)

- **Client-side cosine similarity in Web Worker**: For Phase 1 with two texts, ~20-30 seconds acceptable.
- **Embedding dimension 2,560**: Consistent with Qwen3-Embedding-4B.
- **Backward-compatible workspace detection**: Directory containing `metadata.json` = single-project mode.
- **`X-Shape` header for embedding response**: Shape passed as HTTP header.
- **White-to-blue for cross-text, different scale from self-similarity**: Prevents confusion between views.
