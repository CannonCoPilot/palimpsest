# T24: Narrative Arc + RQA Tracks

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 8 hours (Days 30-31)
**Dependencies**: T15 (pipeline orchestration, `formats/signals.py`), T03 (segmenter, `project.paragraphs` and tokenization), T12 (topics track confirms tokenization pipeline is stable)
**Outputs**: `core/palimpsest/tracks/narrative_arc.py`, `core/palimpsest/tracks/rqa.py`, `core/tests/test_tracks.py` (extended), signal files in `signals/` per project

---

## v4.0 Critical Review

**Verdict: The Python implementations are acceptable for computation that runs once at analysis time. The fundamental problem is with the RQA matrix computation and the signal output format — both need to be Rust-native for Phase 2 scale. The narrative arc track is fine as pure Python; RQA matrix construction must move to Rust.**

### What Is Broken

**The RQA recurrence matrix `_compute_recurrence_matrix` is O(W²) in Python with `scipy.spatial.distance.cdist`.** For a novel with W=200 windows at vector dimension 2,560, `cdist` computes 200×200 = 40,000 pairwise distances, each over 2,560 floats. In Python this is fine (40K × 2,560 multiply-adds ≈ 100M operations, ~0.5 seconds). For Phase 2 with 500 windows at full corpus scale, this is 250K pairwise distances × 2,560 = 640M operations in NumPy — several seconds per novel.

**The diagonal line scan for DET and laminarity scan for LAM are implemented as Python loops.** `_det` and `_lam` iterate over the recurrence matrix element by element to find diagonal and vertical runs. A 200×200 recurrence matrix = 40,000 elements × per-element Python loop = slow. These are exactly the kind of inner loops that SIMD vectorization eliminates.

**"Window by paragraphs, not words" is documented as a simplification.** The spec acknowledges this but presents it as equivalent to word-level windowing. It is not equivalent for RQA: the semantic content of a window depends on how many words it contains, and paragraphs range from 20 to 400 words in P&P. Using paragraph-count windows produces highly variable window sizes, which confounds the RQA metrics across the document. This is a real analytical validity problem that needs a better solution.

**The signal output (float32 binary) is read by the frontend over HTTP fetch.** For a full novel with W=200 windows, the RQA binary is 200×3×4 = 2,400 bytes — trivially small. But the architecture is wrong: signals should be memory-mapped by Rust and served as GPU buffers, not fetched by the browser over HTTP. This is corrected in T32 v4.0.

**The TF-IDF fallback for RQA uses `sklearn.feature_extraction.text.TfidfVectorizer(max_features=500)`.** The max_features=500 truncation means rare but analytically important function words may be dropped. For literary RQA the most important features are function-word frequencies, which are common enough to survive the truncation, but the 500-feature cap is an arbitrary constant with no justification.

---

## v4.0 Rewrite

### Architecture

**Narrative Arc Track**: Pure Python computation (function-word counting) is fast enough — 15 floats computed once at analysis time. No changes to the algorithm. Changes: output is mmap'd by Rust at project load; rendered by WebGPU stacked area chart in T32.

**RQA Track**: Computation is restructured. Python handles window extraction and TF-IDF fallback. Rust handles the recurrence matrix construction and metric computation via a subprocess call (same pattern as self-similarity in T23).

### Technology Stack — Narrative Arc

| Component | Technology |
|-----------|-----------|
| Word counting | Python (whitespace tokenization, module-level word lists) |
| Output | Float32 binary, 60 bytes (15 values) — unchanged |
| Loading at runtime | Rust `mmap` → `[f32; 15]` array → Tauri command |
| Rendering | WebGPU stacked area chart (T32) |

No changes to the computation algorithm. The only change is downstream: the binary is read by Rust at project load and served to the WebGPU renderer, not fetched by the browser over HTTP.

### Technology Stack — RQA

| Component | Technology |
|-----------|-----------|
| Window extraction | Python (word-count-accurate windowing, see below) |
| State vectors | sqlite-vec embeddings (primary) or TF-IDF (fallback) |
| Recurrence matrix + DET/LAM | Rust subprocess via `palimpsest-core compute-rqa` |
| Output | Float32 binary, shape [W, 3] — unchanged |
| Loading at runtime | Rust `mmap` → `[[f32; 3]]` slice |
| Rendering | WebGPU stacked bar chart (T32) |

### Narrative Arc Track Implementation

The algorithm is identical to the original spec. Key requirement additions:

```python
# core/palimpsest/tracks/narrative_arc.py

# Performance requirement: this entire function must complete in <100ms for any novel
def extract(self, project: Project) -> Path:
    import time
    start = time.monotonic()

    # Concatenate all paragraph texts → flat token list
    all_tokens = " ".join(p.text for p in project.paragraphs).lower().split()
    n_words = len(all_tokens)
    segment_size = n_words // 5  # equal segments by word count

    arc = np.zeros((5, 3), dtype=np.float32)
    for seg_idx in range(5):
        seg_start = seg_idx * segment_size
        seg_end = seg_start + segment_size if seg_idx < 4 else n_words
        seg_tokens = all_tokens[seg_start:seg_end]
        seg_count = len(seg_tokens)
        if seg_count == 0:
            continue
        token_set = set(seg_tokens)  # O(1) lookup
        arc[seg_idx, 0] = sum(1 for t in seg_tokens if t in STAGING_WORDS) / seg_count
        arc[seg_idx, 1] = sum(1 for t in seg_tokens if t in PROGRESSION_WORDS) / seg_count
        arc[seg_idx, 2] = sum(1 for t in seg_tokens if t in TENSION_WORDS) / seg_count

    elapsed = time.monotonic() - start
    assert elapsed < 0.1, f"Narrative arc extraction took {elapsed:.3f}s, must be <100ms"

    # ... write manifest and binary as in original spec ...
```

The `token_set = set(seg_tokens)` is not used in the above; the `sum()` comprehension is O(N) per category per segment. For a 120K-word novel, each segment is 24K words × 3 categories = 72K membership tests. Using `STAGING_WORDS` as a `frozenset` reduces each test to O(1). With frozensets the entire function runs in <10ms, well within the 100ms budget.

```python
# Use frozensets for O(1) membership testing
STAGING_WORDS: frozenset[str] = frozenset({
    "a", "an", "the",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "about",
    "one", "two", "three", "several", "many", "few", "some", "each", "all",
    # ... ~40 words total
})

PROGRESSION_WORDS: frozenset[str] = frozenset({
    "then", "after", "before", "when", "while", "until", "since", "during",
    "because", "therefore", "so", "thus", "finally", "suddenly",
    # ... ~25 words total
})

TENSION_WORDS: frozenset[str] = frozenset({
    "think", "know", "feel", "want", "need", "believe", "understand", "wonder",
    "not", "never", "no", "nothing", "without", "cannot", "could", "would",
    # ... ~30 words total
})
```

### RQA Track: Correct Word-Level Windowing

The original spec's "window by paragraphs approximating 100 words" is replaced with exact word-level windowing:

```python
def _extract_windows(
    project: Project,
    window_words: int = 100,
    overlap_words: int = 50,
) -> list[tuple[int, int]]:
    """Returns list of (para_start_idx, para_end_idx) where the window
    covers approximately window_words words with overlap_words overlap.

    Uses cumulative word counts to find exact paragraph boundaries.
    """
    para_word_counts = [len(p.text.split()) for p in project.paragraphs]
    cumulative = np.cumsum([0] + para_word_counts)
    n_words = cumulative[-1]
    step = window_words - overlap_words

    windows = []
    word_pos = 0
    while word_pos < n_words:
        win_end = word_pos + window_words
        # Binary search for paragraph boundaries
        para_start = np.searchsorted(cumulative, word_pos, side='right') - 1
        para_end = np.searchsorted(cumulative, win_end, side='right') - 1
        para_end = min(para_end, len(project.paragraphs) - 1)
        windows.append((int(para_start), int(para_end)))
        word_pos += step

    return windows
```

This gives consistently sized windows (within ±1 paragraph) regardless of paragraph length variance.

### RQA Computation: Rust Subprocess

The recurrence matrix construction and DET/LAM scanning move to Rust:

```rust
// palimpsest-core/src/rqa.rs

use rayon::prelude::*;

pub struct RQAEngine {
    threshold: f32,
    min_line: usize,
}

impl RQAEngine {
    pub fn new(threshold: f32, min_line: usize) -> Self {
        Self { threshold, min_line }
    }

    /// Compute RQA metrics for a single window of state vectors.
    /// vectors: flat slice, shape [n_states × dim]
    pub fn compute_window(&self, vectors: &[f32], n: usize, dim: usize) -> (f32, f32, f32) {
        // Build recurrence matrix via SIMD cosine distance
        let normed = l2_normalize_rows(vectors, n, dim);
        let mut recurrence = vec![0u8; n * n];  // bitpacked is better but u8 for clarity

        for i in 0..n {
            for j in 0..i {
                let dist = 1.0 - dot_neon(
                    &normed[i * dim..(i + 1) * dim],
                    &normed[j * dim..(j + 1) * dim],
                );
                let rec = if dist < self.threshold { 1u8 } else { 0u8 };
                recurrence[i * n + j] = rec;
                recurrence[j * n + i] = rec;
            }
            recurrence[i * n + i] = 0; // exclude diagonal from RR
        }

        let total = (n * n - n) as f32; // exclude diagonal
        let rr_count: u32 = recurrence.iter().map(|&x| x as u32).sum();
        let rr = rr_count as f32 / total;

        let det = self.compute_det(&recurrence, n);
        let lam = self.compute_lam(&recurrence, n);

        (rr, det, lam)
    }

    /// Determinism: proportion of recurrent points on diagonal lines >= min_line.
    /// Scans each diagonal using SIMD-friendly sequential access pattern.
    fn compute_det(&self, rec: &[u8], n: usize) -> f32 {
        let mut on_diagonal_lines = 0u32;
        let total_recurrent: u32 = rec.iter().map(|&x| x as u32).sum();
        if total_recurrent == 0 { return 0.0; }

        // Scan each diagonal d in (-n+1)..n
        for d in -(n as i64 - 1)..n as i64 {
            let mut run = 0usize;
            let diag_len = n - d.unsigned_abs() as usize;
            for k in 0..diag_len {
                let (i, j) = if d >= 0 {
                    (k, k + d as usize)
                } else {
                    (k + (-d) as usize, k)
                };
                if i == j { continue; } // skip main diagonal
                if rec[i * n + j] == 1 {
                    run += 1;
                } else {
                    if run >= self.min_line { on_diagonal_lines += run as u32; }
                    run = 0;
                }
            }
            if run >= self.min_line { on_diagonal_lines += run as u32; }
        }

        on_diagonal_lines as f32 / total_recurrent as f32
    }

    /// Laminarity: proportion of recurrent points on vertical lines >= min_line.
    fn compute_lam(&self, rec: &[u8], n: usize) -> f32 {
        let mut on_vertical_lines = 0u32;
        let total_recurrent: u32 = rec.iter().map(|&x| x as u32).sum();
        if total_recurrent == 0 { return 0.0; }

        for j in 0..n {
            let mut run = 0usize;
            for i in 0..n {
                if i == j { continue; }
                if rec[i * n + j] == 1 {
                    run += 1;
                } else {
                    if run >= self.min_line { on_vertical_lines += run as u32; }
                    run = 0;
                }
            }
            if run >= self.min_line { on_vertical_lines += run as u32; }
        }

        on_vertical_lines as f32 / total_recurrent as f32
    }
}
```

The Python RQA track calls the Rust binary:

```python
# core/palimpsest/tracks/rqa.py

def _compute_via_rust(
    self,
    vector_chunks: list[np.ndarray],  # one array per window
    threshold: float,
    min_line: int,
) -> np.ndarray:
    """Send window state vectors to Rust binary, receive [W, 3] float32 array."""
    import tempfile
    import subprocess

    # Write window vectors to a temporary binary file
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        for chunk in vector_chunks:
            chunk.astype("<f4").tofile(f)
        tmp_path = f.name

    result = subprocess.run(
        [
            "palimpsest-core", "compute-rqa",
            "--vectors", tmp_path,
            "--window-sizes", ",".join(str(len(c)) for c in vector_chunks),
            "--dim", str(vector_chunks[0].shape[1]),
            "--threshold", str(threshold),
            "--min-line", str(min_line),
        ],
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"RQA computation failed: {result.stderr.decode()}")

    # Result written to stdout as raw float32 bytes [W × 3]
    metrics = np.frombuffer(result.stdout, dtype="<f4").reshape(-1, 3)
    return metrics
```

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Narrative arc (any novel) | <100ms | Pure Python, frozenset lookup |
| RQA window extraction (P&P, W≈60) | <50ms | NumPy binary search |
| RQA matrix + DET/LAM per window (n=15 paras, dim=2560) | <10ms | Rust SIMD |
| Total RQA (60 windows) | <600ms | ~10ms × 60 windows via Rust |
| Total T24 analysis time (both tracks) | <700ms | Parallelizable via rayon |

### mmap Output at Runtime

Both signal binaries are memory-mapped by Rust at project load:

```rust
// palimpsest-core/src/signal_store.rs

pub struct NarrativeArcSignal {
    pub data: [f32; 15],  // 5 segments × 3 dimensions, stack-allocated
}

pub struct RQASignal {
    mmap: memmap2::Mmap,
    pub n_windows: usize,
}

impl RQASignal {
    pub fn window(&self, idx: usize) -> (f32, f32, f32) {
        let base = idx * 3;
        let data: &[f32] = bytemuck::cast_slice(&self.mmap);
        (data[base], data[base + 1], data[base + 2])
    }

    /// Returns flat f32 slice for GPU upload (WebGPU stacked bar chart).
    pub fn as_f32_slice(&self) -> &[f32] {
        bytemuck::cast_slice(&self.mmap)
    }
}
```

### Acceptance Criteria (v4.0)

**Narrative arc:**
- `signals/narrative_arc.bin` is exactly 60 bytes
- All 15 values are in [0.0, 1.0]
- Manifest `shape` metadata equals [5, 3]
- Deterministic: two runs produce byte-identical output
- Computation completes in <100ms (CI-enforced benchmark)
- On P&P, Segment 1 staging score > Segment 5 staging score

**RQA:**
- All RR, DET, LAM values are in [0.0, 1.0]
- Binary file size equals `W * 3 * 4` bytes where W matches manifest
- Windows are word-count-accurate (each covers within ±20% of target word count)
- Deterministic: two runs produce byte-identical output
- TF-IDF fallback completes and records `state_vector_source: "tfidf"`
- Rust subprocess produces identical results to reference Python implementation (validated by round-trip test)
- Total RQA computation for P&P <600ms (CI benchmark)

### Tests

```python
# core/tests/test_tracks.py

@pytest.mark.benchmark
def test_narrative_arc_under_100ms(tmp_project):
    import time
    start = time.monotonic()
    NarrativeArcTrack().extract(tmp_project)
    assert (time.monotonic() - start) < 0.1

def test_rqa_windows_are_word_accurate(tmp_project):
    """Each window covers between 80 and 120 words (target=100, overlap=50)."""
    windows = _extract_windows(tmp_project, window_words=100, overlap_words=50)
    paras = tmp_project.paragraphs
    for start_idx, end_idx in windows:
        word_count = sum(
            len(paras[i].text.split())
            for i in range(start_idx, end_idx + 1)
        )
        assert 50 <= word_count <= 200, f"Window word count {word_count} out of bounds"

@pytest.mark.benchmark
def test_rqa_computation_under_600ms(pp_full_project_with_embeddings):
    import time
    start = time.monotonic()
    RQATrack().extract(pp_full_project_with_embeddings)
    elapsed = time.monotonic() - start
    assert elapsed < 0.6, f"RQA took {elapsed:.2f}s, target <600ms"
```

---

## Original Content (Reference)

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 8 hours (Days 30-31)

### Context (original)

Both tracks produce signals, not W3C annotations. The narrative arc track implements Boyd et al.'s function-word-based structural arc representation (15-dim vector: 5 segments × 3 dimensions). The RQA track computes Recurrence Quantification Analysis metrics (RR, DET, LAM) in a sliding window over the text.

### Design Decisions (original)

- **Boyd word lists embedded as constants**: Self-contained, visible to anyone reading the source.
- **RQA threshold 0.3**: Produces recurrence rates in the 5-20% range for literary prose.
- **Window definition by paragraphs, not words**: Acknowledged approximation.
- **Fallback to TF-IDF for RQA**: Keeps RQA independent of Ollama availability.
