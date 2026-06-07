# T25: Alphabet Track (K-means Placeholder)

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 4 hours (Days 30-31, alongside T24)
**Dependencies**: T12 (topics track), T11 (sentiment track), T13 (lexical track), T15 (pipeline orchestration and signal I/O)
**Outputs**: `core/palimpsest/tracks/alphabet.py`, `core/tests/test_tracks.py` (extended), signal file `signals/alphabet.json` per project (no binary file)

---

## v4.0 Critical Review

**Verdict: The K-means implementation in Python is acceptable for a placeholder track that runs once at analysis time. The serious problem is the feature matrix construction — it loads all dependency track outputs from disk via Python for every `AlphabetTrack.extract()` call. This must be refactored to use the Rust AnnotStore as the source of truth at runtime, while Python retains the analysis-time computation role.**

### What Is Broken

**`_build_feature_matrix` loads 4 separate file formats from disk every run.** It reads `sentiment.jsonl` (N annotations), `lexical.jsonl` (N annotations), `topics_dist.bin` (N×K floats), and `narrative_arc.bin` (15 floats). For P&P at 1,800 paragraphs and 5 tracks, this is 4 file system reads + 4 deserialization passes through Python before KMeans even starts. Total: ~200ms on cold cache.

**KMeans with n_init=10 on 1,800 × 19-dim data takes ~2-3 seconds.** sklearn's KMeans default convergence can take 100+ iterations. With 10 restarts this is 1,000+ iterations of assignment + centroid updates on a 1,800 × 19 matrix. For a placeholder that produces an analytically limited single-text alphabet, this is an embarrassingly long wait. Use `n_init=3, max_iter=100` — sufficient for a placeholder.

**The feature matrix construction is not reproducible across Python versions.** `StandardScaler.fit_transform` on a (1,800, 19) matrix is deterministic given the same input, but the input includes `sentiment.jsonl` annotations loaded via `read_track()` which iterates a file. If the file ordering changes (e.g., after a track re-run that produces annotations in different order), the feature matrix changes and KMeans produces a different alphabet even with `random_state=42`.

**Explicit statement in the spec: "Letters are not comparable across different texts."** This is the correct Phase 1 limitation, but it is stronger than that: letters are not comparable across different runs on the **same** text if the dependency track outputs change order. The idempotency guarantee in the acceptance criteria ("running twice produces identical sequence") is only valid if all dependency files are also byte-identical across runs. This dependency is implicit, not enforced.

**The inline sequence in `alphabet.json` is the right call** — 1,800 chars of ASCII is trivial JSON overhead. No changes needed here.

**At runtime (in Tauri), the alphabet sequence is read by Rust from the JSON manifest.** The current design has the browser fetching `alphabet.json` over HTTP. Under v4.0, Rust reads the manifest at project load, stores the sequence as a `Vec<u8>` (one byte per letter, A=0..P=15), and serves it to the AlphabetBarcode WebGPU renderer (T32) as a GPU buffer. No browser HTTP fetch needed.

---

## v4.0 Rewrite

### Architecture

**Analysis time (Python)**: K-means clustering on 19-dim feature vectors, output is the sequence string inline in `alphabet.json`. This is a one-time computation at `palimpsest analyze` time. Python subprocess, not hot path.

**Runtime (Rust + Tauri)**: Rust reads `alphabet.json` manifest at project load, stores `Vec<u8>` (letter indices 0-15). Serves to frontend via Tauri command `get_alphabet_sequence`. WebGPU renders the AlphabetBarcode in T32 via a GPU buffer upload.

### Technology Stack

| Component | Technology |
|-----------|-----------|
| K-means clustering | Python + scikit-learn KMeans (analysis time only) |
| Feature loading | Rust AnnotStore (from loaded project state) for analysis-time features |
| Output | Inline string in `alphabet.json` — unchanged |
| Runtime loading | Rust reads JSON, `Vec<u8>` letter indices |
| Rendering | WebGPU texture/buffer in T32 AlphabetBarcode shader |

### Feature Matrix via Rust API

Instead of Python re-reading all dependency files from disk, the feature matrix is built by querying the Rust AnnotStore (which already has all annotations loaded into packed structures in memory):

```python
# core/palimpsest/tracks/alphabet.py

def _build_feature_matrix(self, project: Project) -> np.ndarray:
    """Build (N, 19) feature matrix from already-loaded Rust AnnotStore.

    Under v4.0, project.annot_store is a Python binding to the Rust AnnotStore.
    Each query is a vectorized operation over the packed annotation arena.

    Under v3.x fallback (no Rust), reads from JSONL files as before.
    """
    n = len(project.paragraphs)

    if hasattr(project, 'annot_store'):
        # v4.0 path: query Rust AnnotStore via Python bindings
        sentiment = project.annot_store.paragraph_sentiment_features(n)    # (N, 2)
        lexical = project.annot_store.paragraph_lexical_features(n)        # (N, 4)
        topics = project.annot_store.paragraph_topic_features(n)           # (N, 10)
        arc_proj = project.annot_store.narrative_arc_projection(n)         # (N, 3)
    else:
        # v3.x fallback: read from JSONL files
        sentiment = self._load_sentiment_features(project, n)
        lexical = self._load_lexical_features(project, n)
        topics = self._load_topic_features(project, n)
        arc_proj = self._load_arc_projection(project, n)

    X = np.hstack([sentiment, lexical, topics, arc_proj])  # (N, 19)
    assert X.shape == (n, 19), f"Expected (N, 19), got {X.shape}"

    # Standardize
    X = StandardScaler().fit_transform(X.astype(np.float64))
    return X.astype(np.float32)
```

The Rust AnnotStore Python bindings are exposed via `pyo3`:

```rust
// palimpsest-core/src/python_bindings.rs (pyo3)

#[pymethods]
impl PyAnnotStore {
    /// Returns (N, 2) float32 array: [mean_valence, mean_arousal] per paragraph.
    /// SIMD vectorized over PackedAnnotation arena.
    pub fn paragraph_sentiment_features(&self, n: usize) -> PyResult<PyReadonlyArray2<f32>> {
        let features = self.inner.sentiment_features_by_paragraph(n);
        Ok(features.into_pyarray(py).readonly())
    }

    // ... similar for lexical, topics, arc_projection
}
```

This eliminates 4 file reads and replaces them with 4 SIMD passes over the already-loaded packed annotation arena — total time for feature matrix construction: <10ms.

### KMeans Parameters

```python
N_CLUSTERS = 16
RANDOM_STATE = 42
N_INIT = 3          # Reduced from 10; sufficient for a Phase 1 placeholder
MAX_ITER = 100      # Reduced from default 300

kmeans = KMeans(
    n_clusters=N_CLUSTERS,
    random_state=RANDOM_STATE,
    n_init=N_INIT,
    max_iter=MAX_ITER,
    algorithm="lloyd",  # Explicit: deterministic for same random_state
)
```

### Idempotency Guarantee

The sequence is deterministic **only if** the dependency feature values are deterministic. The feature matrix construction must be documented as: "Sequence is identical across two runs if and only if all dependency tracks (sentiment, lexical, topics, narrative_arc) produce identical outputs." Add a checksum field to the manifest:

```json
{
  "metadata": {
    "phase1_placeholder": true,
    "dependency_checksums": {
      "sentiment": "<sha256 of sentiment.jsonl>",
      "lexical": "<sha256 of lexical.jsonl>",
      "topics_dist": "<sha256 of topics_dist.bin>",
      "narrative_arc": "<sha256 of narrative_arc.bin>"
    }
  }
}
```

On subsequent analyze runs, if `alphabet.json` exists and all dependency checksums match, skip KMeans entirely and return the cached sequence. This makes the idempotency check explicit and O(N) SHA-256 hashes rather than KMeans re-execution.

### Runtime: Tauri Command

```rust
// src-tauri/src/commands/signals.rs

#[derive(serde::Serialize)]
pub struct AlphabetSequence {
    pub sequence: Vec<u8>,   // letter indices 0-15 (A=0, B=1, ..., P=15)
    pub n_paragraphs: usize,
    pub n_clusters: usize,
}

#[tauri::command]
pub fn get_alphabet_sequence(
    project_id: String,
    state: tauri::State<'_, AppState>,
) -> Result<AlphabetSequence, String> {
    let core = state.core.blocking_lock();
    let project = core.get_project(&project_id)
        .ok_or("Project not found")?;

    let manifest_path = project.signals_dir().join("alphabet.json");
    let manifest: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string(&manifest_path)
            .map_err(|_| "alphabet.json not found — run palimpsest analyze")?
    ).map_err(|e| e.to_string())?;

    let sequence_str = manifest["sequence"]
        .as_str()
        .ok_or("No sequence field in alphabet.json")?;

    let sequence: Vec<u8> = sequence_str
        .bytes()
        .map(|b| b - b'A')  // A=0, B=1, ..., P=15
        .collect();

    Ok(AlphabetSequence {
        n_paragraphs: sequence.len(),
        n_clusters: manifest["metadata"]["n_clusters"].as_u64().unwrap_or(16) as usize,
        sequence,
    })
}
```

The `sequence: Vec<u8>` (one byte per paragraph, value 0-15) is uploaded as a GPU buffer in T32 and consumed by the AlphabetBarcode WebGPU compute shader directly.

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Feature matrix construction (v4.0 Rust path) | <10ms | SIMD AnnotStore queries |
| Feature matrix construction (v3.x fallback) | <200ms | File reads, acceptable at analysis time |
| KMeans clustering (n=1800, k=16, n_init=3) | <1s | sklearn, reduced restarts |
| Total AlphabetTrack.extract() | <1.1s | Analysis time, not hot path |
| Sequence retrieval at runtime (Tauri command) | <5ms | JSON parse + Vec<u8> |
| GPU buffer upload (1800 bytes) | <1ms | Trivial buffer copy |

### Acceptance Criteria (v4.0)

- `signals/alphabet.json` contains `"sequence"` field with length == paragraph_count
- Sequence contains only characters from `"ABCDEFGHIJKLMNOP"`
- `"data_file": null` in manifest (no binary companion)
- `"phase1_placeholder": true` in metadata
- `"dependency_checksums"` present in metadata with sha256 for each dependency
- On second run with identical dependency files, KMeans is skipped (cache hit)
- `get_alphabet_sequence` Tauri command returns Vec<u8> in <5ms
- `cargo test` passes all alphabet command tests
- `mypy --strict` passes; `ruff check` passes

### Tests

```python
# core/tests/test_tracks.py — TestAlphabetTrack

def test_alphabet_dependency_checksums_present(tmp_project_with_all_tracks):
    """manifest.metadata contains dependency_checksums for all 4 tracks."""
    AlphabetTrack().extract(tmp_project_with_all_tracks)
    manifest = json.loads(
        (tmp_project_with_all_tracks.signals_dir / "alphabet.json").read_text()
    )
    checksums = manifest["metadata"]["dependency_checksums"]
    assert set(checksums.keys()) == {"sentiment", "lexical", "topics_dist", "narrative_arc"}
    for v in checksums.values():
        assert len(v) == 64  # SHA-256 hex

def test_alphabet_cache_hit_skips_kmeans(tmp_project_with_all_tracks, monkeypatch):
    """Second extract() with same dependencies returns cached sequence."""
    from sklearn.cluster import KMeans
    fit_calls = []
    original_fit = KMeans.fit
    def patched_fit(self, X):
        fit_calls.append(1)
        return original_fit(self, X)
    monkeypatch.setattr(KMeans, "fit", patched_fit)

    AlphabetTrack().extract(tmp_project_with_all_tracks)  # first run
    fit_calls.clear()
    AlphabetTrack().extract(tmp_project_with_all_tracks)  # second run
    assert len(fit_calls) == 0, "KMeans.fit called on cache-hit run"

def test_alphabet_kmeans_params():
    """AlphabetTrack uses n_init=3 and max_iter=100."""
    track = AlphabetTrack()
    assert track.N_INIT == 3
    assert track.MAX_ITER == 100
```

```rust
// src-tauri/src/commands/signals_tests.rs (Rust unit tests)

#[test]
fn test_get_alphabet_sequence_converts_letters_to_indices() {
    let manifest_json = r#"{"sequence": "ABCDA", "metadata": {"n_clusters": 16}}"#;
    // Mock project with alphabet.json containing above
    let result = get_alphabet_sequence_from_str(manifest_json).unwrap();
    assert_eq!(result.sequence, vec![0, 1, 2, 3, 0]);
    assert_eq!(result.n_paragraphs, 5);
}

#[test]
fn test_get_alphabet_sequence_missing_file_returns_error() {
    let err = get_alphabet_sequence("nonexistent-project".to_string(), mock_state()).unwrap_err();
    assert!(err.contains("alphabet.json not found"));
}
```

---

## Original Content (Reference)

**Milestone**: 1.3a — Remaining Base Tracks + Embedding Service
**Estimated effort**: 4 hours (Days 30-31, alongside T24)

### Context (original)

The narrative alphabet assigns each paragraph a single letter (one of 16 symbols) representing its dominant narrative mode, computed by K-means clustering on a 19-dim feature vector. This is a Phase 1 placeholder for ModeHMM (ChromHMM-analogue for Phase 2).

### Design Decisions (original)

- **Inline sequence, no binary file**: 1,800-char string is trivial JSON overhead.
- **`phase1_placeholder: true` in metadata**: Machine-readable flag for Phase 2 migration tooling.
- **Letters not semantically labeled**: K-means cluster index → letter assignment is arbitrary within a single text.
- **19 features**: sentiment (2) + lexical (4) + topics (10) + narrative arc projection (3).
