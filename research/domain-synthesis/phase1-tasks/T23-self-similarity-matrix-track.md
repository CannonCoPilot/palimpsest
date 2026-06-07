# T23: Self-Similarity Matrix Track

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 6 hours (Days 28-29)
**Dependencies**: T21 (VectorStore populated with paragraph embeddings), T15 (TrackRegistry, signal I/O in `formats/signals.py`)
**Outputs**: `core/palimpsest/tracks/self_similarity.py`, `core/tests/test_tracks.py` (new test class), signal files `signals/self_similarity.json` + `signals/self_similarity.bin` (written to each project at analysis time)

---

## v4.0 Critical Review

**Verdict: NumPy cosine similarity on the Python side is the wrong architecture. The computation must move to Rust (for large-matrix SIMD work) and the rendering must move to WebGPU. The Python track still writes the binary file — that part is fine. Everything downstream of the file must change.**

### What Is Broken

**NumPy `cosine_similarity(E)` is O(N²) compute and O(N²) memory in Python.** For P&P at 1,800 paragraphs and 2,560-dim embeddings, `E` is shape (1,800, 2,560) = 18.4M floats = 147MB in Python. The cosine similarity matrix is (1,800, 1,800) = 12.96MB. The intermediate `E_norm @ E_norm.T` operation allocates a (1,800, 1,800) float64 intermediate before the result is cast to float32. Total peak Python memory: ~300MB. Fine for P&P alone. For Phase 2 with five 200K-word novels simultaneously (each ~3,000 paragraphs), each matrix is 36MB, and the computation is O(9M) per novel — you are in OOM territory or waiting minutes.

**The `get_all()` method on SqliteVecStore iterates N rows with N Python → C bridge crossings.** 1,800 rows × one sqlite fetch each = 1,800 Python/C boundary crossings. Rust's `load_all_flat()` (T21 v4.0) does this in a single sequential scan of the sqlite b-tree, returning a flat `Vec<f32>` with no per-row overhead.

**"Under 60 seconds for P&P on M1"** is the target. That is not a number to be proud of. With Rust + SIMD, this should be under 2 seconds on M4 Max.

**The full matrix is stored uncompressed — both triangles.** For P&P this is 12.96MB and the spec says "acceptable." For a 5,000-paragraph novel it is 100MB. The real question is: who reads this file? The answer is the WebGPU shader. And the WebGPU shader reads it as a 2D texture. We should store the matrix in a format the GPU can consume directly.

**The DotplotView (T27) loads the full 12.96MB binary into JS heap via `fetch().arrayBuffer()`.** This is 12.96MB of data sitting in the WKWebView process that the GPU will copy into a texture. With WebGPU, the binary should be read from disk by Rust and uploaded to the GPU as a `wgpu::Texture` without the JS heap ever touching it.

---

## v4.0 Rewrite

### Architecture

The self-similarity matrix computation is split:

1. **Python track** (`self_similarity.py`): still loads embeddings from sqlite-vec, but calls a Rust subprocess for the actual matrix computation via `palimpsest-core --compute-self-similarity`. Python writes the binary manifest file. This keeps the Python track extractor as a thin orchestrator.

2. **Rust computation** (`palimpsest-core`): `SelfSimilarityEngine` loads embeddings via `EmbeddingStore.load_all_flat()`, computes the N×N cosine similarity matrix using SIMD-vectorized dot products (ARM NEON on M4), writes the float32 binary to `signals/self_similarity.bin`.

3. **Tauri loading** (`load_self_similarity` command): reads the binary file, uploads it as a `wgpu::Texture` to GPU memory. The texture is reused by the WebGPU render pass — no JS heap involvement.

4. **WebGPU render** (T27): a fragment shader samples the texture at UV coordinates corresponding to (i, j) and applies the color map.

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Embedding loading | Rust `EmbeddingStore.load_all_flat()` — one sequential scan |
| Matrix computation | Rust SIMD (ARM NEON via `std::arch` or `nalgebra`) |
| Memory model | Stack-allocated work tiles; output written directly to mmap'd file |
| Output format | Raw float32 little-endian, row-major, identical to original |
| GPU upload | `wgpu::Texture` format `R32Float`, size N×N |
| Render | WebGPU fragment shader samples texture, applies color LUT |

### Rust Computation Engine

```rust
// palimpsest-core/src/self_similarity.rs

use rayon::prelude::*;
use std::arch::aarch64::*;

pub struct SelfSimilarityEngine;

impl SelfSimilarityEngine {
    /// Compute N×N cosine similarity matrix from flat embedding data.
    ///
    /// Tile-based SIMD computation: processes 16-row tiles to stay in L2 cache.
    /// On M4 Max (L2 = 16MB), each tile (16 rows × 2560 floats × 4 bytes = 163KB)
    /// fits entirely in cache.
    ///
    /// Performance: ~800ms for N=1800, D=2560 on M4 Max (SIMD + rayon parallelism).
    pub fn compute(embeddings: &[f32], n: usize, dim: usize) -> Vec<f32> {
        // Step 1: L2-normalize all rows in parallel
        let mut normed = embeddings.to_vec();
        normed.par_chunks_mut(dim).for_each(|row| {
            let norm = row.iter().map(|&x| x * x).sum::<f32>().sqrt();
            if norm > 1e-8 {
                row.iter_mut().for_each(|x| *x /= norm);
            }
        });

        // Step 2: Compute lower triangle, mirror upper. Output: N*N float32.
        let mut matrix = vec![0.0f32; n * n];

        // Tile size chosen to fit two tiles (row_tile + col_tile) in L2 cache
        const TILE: usize = 64;

        (0..n).into_par_iter().step_by(TILE).for_each(|i_start| {
            let i_end = (i_start + TILE).min(n);
            for j_start in (0..=i_start).step_by(TILE) {
                let j_end = (j_start + TILE).min(i_start + 1);
                // Compute tile
                for i in i_start..i_end {
                    for j in j_start..j_end.min(i + 1) {
                        let dot = dot_product_neon(
                            &normed[i * dim..(i + 1) * dim],
                            &normed[j * dim..(j + 1) * dim],
                        );
                        // Safety: single-threaded per (i_start, j_start) tile pair
                        unsafe {
                            let ptr = matrix.as_ptr() as *mut f32;
                            *ptr.add(i * n + j) = dot;
                            if i != j {
                                *ptr.add(j * n + i) = dot;
                            }
                        }
                    }
                }
            }
        });

        // Diagonal must be 1.0 (self-similarity)
        for i in 0..n {
            matrix[i * n + i] = 1.0;
        }

        matrix
    }

    /// Write matrix to mmap'd output file.
    /// Uses memmap2 for zero-copy write directly to the file's page cache.
    pub fn write_to_file(matrix: &[f32], output_path: &Path) -> Result<()> {
        let byte_len = matrix.len() * 4;
        let file = std::fs::OpenOptions::new()
            .write(true).create(true).truncate(true)
            .open(output_path)?;
        file.set_len(byte_len as u64)?;
        let mut mmap = unsafe { memmap2::MmapMut::map_mut(&file)? };
        let bytes: &[u8] = bytemuck::cast_slice(matrix);
        mmap.copy_from_slice(bytes);
        mmap.flush()?;
        Ok(())
    }
}

#[cfg(target_arch = "aarch64")]
unsafe fn dot_product_neon(a: &[f32], b: &[f32]) -> f32 {
    let mut sum = vdupq_n_f32(0.0);
    let chunks = a.len() / 4;
    for i in 0..chunks {
        let va = vld1q_f32(a.as_ptr().add(i * 4));
        let vb = vld1q_f32(b.as_ptr().add(i * 4));
        sum = vmlaq_f32(sum, va, vb);
    }
    let mut result = vaddvq_f32(sum);
    // Handle remainder
    for i in chunks * 4..a.len() {
        result += a[i] * b[i];
    }
    result
}
```

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Load 1,800 embeddings from sqlite-vec | <100ms | Rust sequential scan |
| L2-normalize 1,800 rows (rayon) | <50ms | Embarrassingly parallel |
| Compute 1,800×1,800 cosine matrix | <800ms | SIMD tiles + rayon |
| Write 12.96MB to mmap'd file | <20ms | Page cache write |
| Total: analyze → `self_similarity.bin` written | <1s on M4 Max | Full pipeline |
| GPU texture upload (12.96MB) | <16ms | One-time at project load |
| GPU render dotplot (WebGPU fragment shader) | <1ms per frame | Per T27 |

### Python Track (Thin Orchestrator)

`self_similarity.py` becomes a subprocess caller:

```python
# core/palimpsest/tracks/self_similarity.py

import subprocess
import sys
from pathlib import Path
from palimpsest.tracks.base import TrackExtractor

class SelfSimilarityTrack(TrackExtractor):
    name = "self_similarity"
    output_type = "signal"
    depends_on = ["embeddings"]
    evidence_level = "E4"

    def extract(self, project: Project) -> Path:
        embeddings_db = project.cache_dir / "embeddings.db"
        if not embeddings_db.exists():
            raise FileNotFoundError(
                f"Embeddings not found at {embeddings_db}. "
                "Run `palimpsest analyze` with Ollama available."
            )

        signals_dir = project.signals_dir
        signals_dir.mkdir(parents=True, exist_ok=True)
        bin_path = signals_dir / "self_similarity.bin"
        manifest_path = signals_dir / "self_similarity.json"

        # Delegate computation to Rust binary
        result = subprocess.run(
            [
                "palimpsest-core",
                "compute-self-similarity",
                "--embeddings-db", str(embeddings_db),
                "--output", str(bin_path),
                "--project-id", project.id,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Self-similarity computation failed: {result.stderr}"
            )

        # Parse dimensions from Rust output (printed as JSON to stdout)
        import json
        stats = json.loads(result.stdout)
        n = stats["paragraph_count"]

        # Write manifest
        manifest = {
            "type": "matrix",
            "name": "self_similarity",
            "source": "embedding_cosine_rust_simd/0.1",
            "reference_sha256": project.reference_sha256,
            "dimensions": [n, n],
            "dtype": "float32",
            "byte_order": "little-endian",
            "data_file": "self_similarity.bin",
            "segment_offsets": [[p.start, p.end] for p in project.paragraphs],
            "metadata": {
                "similarity_metric": "cosine",
                "embedding_model": project.config.get("embedding_model", "qwen3-embedding"),
                "paragraph_count": n,
                "compute_backend": "rust-simd-neon",
            }
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return manifest_path
```

### WebGPU Texture Upload (Tauri Command)

```rust
// src-tauri/src/commands/signals.rs

#[tauri::command]
pub async fn load_self_similarity_texture(
    project_id: String,
    state: tauri::State<'_, AppState>,
) -> Result<SimilarityTextureHandle, String> {
    let core = state.core.lock().await;
    let project = core.get_project(&project_id)
        .ok_or("Project not found")?;

    let bin_path = project.signals_dir().join("self_similarity.bin");
    let manifest_path = project.signals_dir().join("self_similarity.json");

    let manifest: SelfSimilarityManifest = serde_json::from_str(
        &std::fs::read_to_string(&manifest_path)
            .map_err(|_| "self_similarity.json not found")?
    ).map_err(|e| e.to_string())?;

    let n = manifest.dimensions[0];

    // mmap the binary — zero-copy, kernel handles page faults
    let file = std::fs::File::open(&bin_path)
        .map_err(|_| "self_similarity.bin not found")?;
    let mmap = unsafe { memmap2::Mmap::map(&file).map_err(|e| e.to_string())? };

    // Upload to GPU as R32Float texture
    let texture = core.gpu.device.create_texture(&wgpu::TextureDescriptor {
        label: Some("self_similarity"),
        size: wgpu::Extent3d { width: n as u32, height: n as u32, depth_or_array_layers: 1 },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::R32Float,
        usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
        view_formats: &[],
    });

    core.gpu.queue.write_texture(
        texture.as_image_copy(),
        &mmap,
        wgpu::ImageDataLayout {
            offset: 0,
            bytes_per_row: Some(n as u32 * 4),
            rows_per_image: Some(n as u32),
        },
        wgpu::Extent3d { width: n as u32, height: n as u32, depth_or_array_layers: 1 },
    );

    // Store in AppState GPU resource registry
    let handle = core.register_texture(project_id, "self_similarity", texture);
    Ok(SimilarityTextureHandle { handle, n: n as u32 })
}
```

The texture lives on the GPU. The dotplot WebGPU fragment shader (T27) samples it directly. The matrix data never touches the JS heap.

### Acceptance Criteria (v4.0)

- `palimpsest analyze` produces `signals/self_similarity.json` and `signals/self_similarity.bin` with N×N float32 data
- `self_similarity.bin` size equals `N * N * 4` bytes
- Diagonal values are all 1.0 ± 1e-5
- Matrix is symmetric (values[i,j] == values[j,i] ± 1e-5)
- **Computation completes in under 1 second on M4 Max for P&P full text (1,800 paragraphs)** — enforced by benchmark test
- For P&P, mean within-chapter similarity exceeds mean cross-chapter similarity by at least 0.05
- `load_self_similarity_texture` Tauri command uploads the texture to GPU in <16ms
- `cargo test` passes all self-similarity tests
- `mypy --strict` passes on `self_similarity.py`

### Test Strategy

```python
# core/tests/test_tracks.py — TestSelfSimilarityTrack

def test_self_similarity_produces_signal_files(tmp_project_with_embeddings):
    """extract() creates self_similarity.json and self_similarity.bin."""

def test_self_similarity_matrix_shape(tmp_project_with_embeddings):
    """Matrix shape is (N, N) where N == paragraph count."""

def test_self_similarity_matrix_diagonal(tmp_project_with_embeddings):
    """All diagonal entries equal 1.0 within float32 tolerance."""

def test_self_similarity_matrix_symmetric(tmp_project_with_embeddings):
    """matrix[i,j] == matrix[j,i] for all i, j."""

@pytest.mark.benchmark
def test_self_similarity_computation_speed(pp_full_project_with_embeddings, tmp_path):
    """Matrix computation for P&P (1,800 paras) completes in <1s on M4 Max."""
    import time
    start = time.monotonic()
    SelfSimilarityTrack().extract(pp_full_project_with_embeddings)
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, f"Took {elapsed:.2f}s, target <1s on M4"

def test_self_similarity_block_diagonal_pp(pp_full_project_with_embeddings):
    """P&P matrix shows higher within-chapter than cross-chapter similarity."""
```

```rust
// palimpsest-core/src/self_similarity_tests.rs

#[test]
fn test_diagonal_is_one() {
    let embeddings = vec![1.0f32, 0.0, 0.0, 1.0]; // 2 rows, dim=2
    let matrix = SelfSimilarityEngine::compute(&embeddings, 2, 2);
    assert!((matrix[0] - 1.0).abs() < 1e-6); // [0,0]
    assert!((matrix[3] - 1.0).abs() < 1e-6); // [1,1]
}

#[test]
fn test_matrix_symmetric() {
    let rng_data: Vec<f32> = (0..1800 * 64).map(|i| (i as f32).sin()).collect();
    let matrix = SelfSimilarityEngine::compute(&rng_data, 1800, 64);
    for i in 0..1800 {
        for j in 0..i {
            let diff = (matrix[i * 1800 + j] - matrix[j * 1800 + i]).abs();
            assert!(diff < 1e-5, "Not symmetric at ({},{}: diff={}", i, j, diff);
        }
    }
}

#[test]
fn test_performance_1800_paragraphs() {
    // 1800 × 64-dim (smaller dim for CI speed, full dim in integration test)
    let data: Vec<f32> = (0..1800 * 64).map(|i| (i as f32 / 1000.0).sin()).collect();
    let start = std::time::Instant::now();
    let _ = SelfSimilarityEngine::compute(&data, 1800, 64);
    let elapsed = start.elapsed();
    // At 64-dim, must complete in <100ms. At 2560-dim (integration), <1s.
    assert!(elapsed.as_millis() < 100, "Took {}ms, target <100ms at dim=64", elapsed.as_millis());
}
```

---

## Original Content (Reference)

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 6 hours (Days 28-29)
**Dependencies**: T21 (VectorStore populated with paragraph embeddings), T15 (TrackRegistry, signal I/O in `formats/signals.py`)

### Context (original)

The self-similarity matrix is a pairwise cosine similarity matrix over all paragraph embeddings: entry `[i, j]` is the cosine similarity between embedding of paragraph `i` and paragraph `j`. It is the foundational data for the DotplotView (T27). The matrix is a signal, not a W3C annotation track, stored as raw little-endian Float32 binary alongside a JSON manifest.

### Design Decisions (original)

- **float32 throughout**: The matrix is computed and stored in float32. For P&P at 1,800 paragraphs, the full float32 matrix is 12.96MB.
- **Full matrix, not compressed**: Stored in full for simplicity of browser access.
- **Segment offsets in manifest**: Character offsets stored in manifest so browser can correlate matrix rows/columns with W3C annotation selectors.
- **`output_type = "signal"`, not `"annotation"`**: Protocol contract — signal tracks write to `signals/*.bin` not `tracks/*.jsonl`.
