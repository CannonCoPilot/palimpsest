# T15: Pipeline Orchestration (Rust + tokio)

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 6 hours (up from 4; Rust implementation adds complexity)
**Dependencies**: T11, T12, T13, T14 (all extractors converted to streaming subprocess CLIs), T04 (entities extractor)
**Outputs**: `src-tauri/src/pipeline.rs` (created); `src-tauri/src/annotation_store.rs` (created); `core/tests/test_pipeline.py` (modified, integration tests updated)

---

## v4.0 Critical Review

**Verdict: The entire Python CLI orchestrator described here is obsolete. It must be replaced with a Rust binary that manages Python subprocesses. The `rich` progress bars, the `TrackRegistry.discover()` auto-import chain, and `pipeline_run.json` all survive — but the execution model is fundamentally different.**

### What is broken

**1. `palimpsest analyze` as a Python Click command is the wrong process model.**
The original design is: Python CLI → Python `for extractor_cls in ordered: extractor.extract(project)`. This is a single Python process running all extractors sequentially, sharing one GIL, one heap, one event loop. Under v4.0, the orchestrator is a Rust `tokio` binary that:
- Spawns each Python extractor as a separate OS subprocess
- Runs them on separate cores (M4 Max has 16 cores; we use up to 5 for the 5 extractors)
- Reads each extractor's stdout as an async JSONL stream
- Ingests into `AnnotationStore` in the Rust runtime
- Emits progress events to the Tauri frontend via `tauri::emit_all()`

A Python Click CLI cannot do this. The Python GIL prevents true parallelism. The `rich` progress bar will not update while blocked on `extractor.extract()`.

**2. `TrackRegistry.discover()` with Python `__subclasses__()` and `importlib` auto-import is the wrong mechanism for a subprocess-based model.**
The registry was designed to find Python classes in the same process. In v4.0, the "registry" is a static Rust `Vec<ExtractorSpec>` that maps track names to Python module paths:
```rust
struct ExtractorSpec {
    name: &'static str,
    module: &'static str,    // e.g., "palimpsest.tracks.sentiment"
    track_id: TrackId,
    args_builder: fn(&ProjectPaths) -> Vec<String>,
}
```
Adding a new track extractor means adding one entry to this static list, not auto-discovery via module introspection. This is more explicit, more auditable, and faster.

**3. "Skip if already computed" logic based on `output_jsonl.exists()` is wrong — the AnnotationStore is the truth, not files.**
In v4.0, `AnnotationStore` is the authoritative annotation database (in-memory arena during a session, persisted to a binary file between sessions). The `--force` / skip logic must check the `AnnotationStore` state, not the filesystem. If `store.has_track(TrackId::Sentiment)` is true, skip re-running the sentiment subprocess. This check happens in Rust, not by looking for JSONL files.

**4. Sequential execution is a 5x performance tax.**
The original design runs extractors in topological order, sequentially. With the v4.0 subprocess model, all five Phase 1 extractors can run in parallel — they have no data dependencies on each other's outputs (only on `reference.txt` and the spaCy cache, which are both read-only). Running 5 extractors in parallel on a 16-core M4 Max should cut total analysis time from ~25s to **~8s** (dominated by the slowest single extractor: topics at ~5s).

**5. `rich` progress bars cannot be updated from inside a subprocess's output.**
The original code uses `rich.progress.Progress` with a spinner updated after `extractor.extract()` returns. The Rust implementation uses Tauri's event system to stream progress to the frontend in real time. However, `palimpsest analyze` as a **CLI command** (not via Tauri UI) should still produce terminal output. The Rust binary must support both modes: Tauri event emission when invoked from the app, and `println!` to stderr when invoked as a CLI command.

**6. `_collect_parameters(ordered)` introspects Python objects — cannot work when extractors are subprocesses.**
Parameters are now declared in the static `ExtractorSpec` or passed as CLI flags. The `pipeline_run.json` is written by Rust after all subprocesses complete, pulling parameters from the `ExtractorSpec` definitions and any user-overridden CLI flags.

---

## v4.0 Rewrite

### Architecture

```
palimpsest analyze CLI (Rust binary)
  │
  ├── parse args: --project <dir> [--force] [--tracks entities,sentiment,...] [--n-topics 10]
  ├── load ProjectPaths from project directory
  ├── spawn tokio runtime
  │
  └── tokio::spawn per extractor (parallel):
        ├── entities subprocess   → ingest stdout into AnnotationStore[TrackId::Entities]
        ├── sentiment subprocess  → ingest stdout into AnnotationStore[TrackId::Sentiment]
        ├── lexical subprocess    → ingest stdout into AnnotationStore[TrackId::Lexical]
        ├── dialogue subprocess   → ingest stdout into AnnotationStore[TrackId::Dialogue]
        └── topics subprocess     → ingest stdout into AnnotationStore[TrackId::Topics]
              └── also writes signals/ directory (not via stdout)
        │
        ├── progress: stream PipelineProgress events to Tauri / stderr
        └── on all complete: write pipeline_run.json + AnnotationStore binary cache
```

### Rust implementation

**`src-tauri/src/pipeline.rs`**:

```rust
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};
use tokio::process::Command;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::sync::mpsc;
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize)]
pub struct PipelineProgress {
    pub track: String,
    pub status: TrackStatus,
    pub annotations_ingested: usize,
    pub elapsed_ms: u64,
}

#[derive(Debug, Clone, Serialize)]
pub enum TrackStatus {
    Starting,
    Running { lines_read: usize },
    Complete { count: usize, elapsed_ms: u64 },
    Failed { message: String },
}

/// Static registry: all Phase 1 extractors.
/// Adding a new track = adding one entry here.
pub fn extractor_specs() -> Vec<ExtractorSpec> {
    vec![
        ExtractorSpec {
            name: "entities",
            track_id: TrackId::Entities,
            module: "palimpsest.tracks.entities",
            evidence_level: 4,
        },
        ExtractorSpec {
            name: "sentiment",
            track_id: TrackId::Sentiment,
            module: "palimpsest.tracks.sentiment",
            evidence_level: 5,
        },
        ExtractorSpec {
            name: "lexical",
            track_id: TrackId::Lexical,
            module: "palimpsest.tracks.lexical",
            evidence_level: 5,
        },
        ExtractorSpec {
            name: "dialogue",
            track_id: TrackId::Dialogue,
            module: "palimpsest.tracks.dialogue",
            evidence_level: 5,
        },
        ExtractorSpec {
            name: "topics",
            track_id: TrackId::Topics,
            module: "palimpsest.tracks.topics",
            evidence_level: 4,
        },
    ]
}

pub struct PipelineManager {
    python_bin: PathBuf,
    store: AnnotationStore,
    progress_tx: mpsc::Sender<PipelineProgress>,
}

impl PipelineManager {
    /// Run all extractors in parallel. Returns total annotation count and elapsed time.
    pub async fn run_all(
        &mut self,
        paths: &ProjectPaths,
        force: bool,
        params: &PipelineParams,
    ) -> Result<PipelineResult, PipelineError> {
        let start = Instant::now();
        let specs = extractor_specs();

        // Filter to specs not already in store (unless --force)
        let to_run: Vec<&ExtractorSpec> = specs.iter()
            .filter(|s| force || !self.store.has_track(s.track_id))
            .collect();

        // Spawn all in parallel
        let mut handles = Vec::new();
        for spec in &to_run {
            let args = build_args(spec, paths, params);
            let python_bin = self.python_bin.clone();
            let track_id = spec.track_id;
            let track_name = spec.name.to_string();
            let tx = self.progress_tx.clone();

            let handle = tokio::spawn(async move {
                run_extractor_subprocess(
                    &python_bin,
                    &args,
                    track_id,
                    &track_name,
                    tx,
                ).await
            });
            handles.push((spec.name, track_id, handle));
        }

        // Collect results, ingest into store
        let mut total_annotations = 0usize;
        let mut results: Vec<TrackResult> = Vec::new();
        for (name, track_id, handle) in handles {
            match handle.await? {
                Ok((lines, annotations)) => {
                    for packed in annotations {
                        self.store.insert(track_id, packed);
                    }
                    total_annotations += lines;
                    results.push(TrackResult { name, count: lines, status: "ok" });
                }
                Err(e) => {
                    results.push(TrackResult { name, count: 0, status: &e.to_string() });
                    // Non-fatal: continue with other tracks
                    eprintln!("ERROR: track {} failed: {}", name, e);
                }
            }
        }

        let elapsed = start.elapsed();
        self.write_pipeline_run(paths, &results, elapsed, params)?;

        Ok(PipelineResult {
            total_annotations,
            elapsed,
            results,
        })
    }
}

/// Spawn a single Python extractor subprocess, stream its stdout into packed annotations.
/// Returns (line_count, Vec<PackedAnnotation>).
async fn run_extractor_subprocess(
    python_bin: &Path,
    args: &[String],
    track_id: TrackId,
    track_name: &str,
    progress_tx: mpsc::Sender<PipelineProgress>,
) -> Result<(usize, Vec<PackedAnnotation>), PipelineError> {
    let mut child = Command::new(python_bin)
        .args(args)
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()?;

    let stdout = child.stdout.take().unwrap();
    let stderr = child.stderr.take().unwrap();

    // Forward stderr to our stderr (for Python warnings, tracebacks)
    tokio::spawn(async move {
        let mut lines = BufReader::new(stderr).lines();
        while let Ok(Some(line)) = lines.next_line().await {
            eprintln!("[{}] {}", track_name, line);
        }
    });

    let mut stdout_lines = BufReader::new(stdout).lines();
    let mut annotations: Vec<PackedAnnotation> = Vec::new();
    let mut count = 0usize;
    let start = Instant::now();

    while let Some(line) = stdout_lines.next_line().await? {
        if line.is_empty() { continue; }
        match parse_jsonl_line(&line, track_id) {
            Ok(packed) => {
                annotations.push(packed);
                count += 1;
                if count % 1000 == 0 {
                    let _ = progress_tx.try_send(PipelineProgress {
                        track: track_name.to_string(),
                        status: TrackStatus::Running { lines_read: count },
                        annotations_ingested: count,
                        elapsed_ms: start.elapsed().as_millis() as u64,
                    });
                }
            }
            Err(e) => {
                eprintln!("[{}] Failed to parse line {}: {} — {:?}", track_name, count, e, &line[..line.len().min(80)]);
                // Continue: one bad line does not abort the track
            }
        }
    }

    let status = child.wait().await?;
    if !status.success() {
        return Err(PipelineError::ExtractorFailed(
            track_name.to_string(),
            status.code().unwrap_or(-1),
        ));
    }

    let elapsed_ms = start.elapsed().as_millis() as u64;
    let _ = progress_tx.try_send(PipelineProgress {
        track: track_name.to_string(),
        status: TrackStatus::Complete { count, elapsed_ms },
        annotations_ingested: count,
        elapsed_ms,
    });

    Ok((count, annotations))
}
```

### JSONL parsing: the 100K ann/sec requirement

`parse_jsonl_line()` is the hot path. It must parse a W3C annotation JSON line and pack it into `PackedAnnotation` in **<10 microseconds** per line to hit 100K/sec. Use `serde_json::from_str` with a custom deserializer that directly reads `target.selector.start`, `target.selector.end`, `palimpsest:confidence`, and `palimpsest:evidenceLevel` without allocating the full object tree:

```rust
fn parse_jsonl_line(line: &str, track_id: TrackId) -> Result<PackedAnnotation, ParseError> {
    // serde_json with borrowed strings — no allocation for string fields we don't use
    #[derive(serde::Deserialize)]
    struct MinimalAnnotation<'a> {
        target: Target<'a>,
        #[serde(rename = "palimpsest:confidence")]
        confidence: f64,
        #[serde(rename = "palimpsest:evidenceLevel")]
        evidence_level: &'a str,
        id: &'a str,
    }
    #[derive(serde::Deserialize)]
    struct Target<'a> {
        selector: Selector,
        #[allow(dead_code)]
        source: &'a str,
    }
    #[derive(serde::Deserialize)]
    struct Selector {
        start: u32,
        end: u32,
    }

    let ann: MinimalAnnotation = serde_json::from_str(line)?;
    let evidence = match ann.evidence_level {
        "E1" => 1u8, "E2" => 2, "E3" => 3, "E4" => 4, "E5" => 5, _ => 0,
    };
    let confidence_u16 = (ann.confidence * 10000.0).round() as u16;

    // body_offset: hash the annotation ID to get a stable arena key
    let body_offset = fnv1a_32(ann.id.as_bytes());

    Ok(PackedAnnotation {
        start: ann.target.selector.start,
        end: ann.target.selector.end,
        confidence: confidence_u16,
        track_id: track_id as u8,
        evidence_level: evidence,
        body_offset,
    })
}
```

This avoids allocating Rust `String`s for fields we don't need. The full JSON body is preserved in the body arena as a raw bytes slice only if the frontend explicitly requests annotation detail.

### Argument builders

```rust
fn build_args(spec: &ExtractorSpec, paths: &ProjectPaths, params: &PipelineParams) -> Vec<String> {
    let mut args = vec![
        "-m".to_string(), spec.module.to_string(),
        "--project".to_string(), paths.project_id.clone(),
        "--reference".to_string(), paths.reference.to_str().unwrap().to_string(),
    ];
    match spec.track_id {
        TrackId::Sentiment | TrackId::Entities | TrackId::Dialogue => {
            if let Some(cache) = &paths.spacy_cache {
                args.extend(["--spacy-cache".to_string(), cache.to_str().unwrap().to_string()]);
            }
        }
        TrackId::Topics => {
            args.extend([
                "--signals-dir".to_string(), paths.signals_dir.to_str().unwrap().to_string(),
                "--n-topics".to_string(), params.n_topics.to_string(),
                "--random-state".to_string(), params.random_state.to_string(),
            ]);
        }
        _ => {}
    }
    args
}
```

### Pipeline run JSON (written by Rust)

```rust
fn write_pipeline_run(
    paths: &ProjectPaths,
    results: &[TrackResult],
    elapsed: Duration,
    params: &PipelineParams,
) -> Result<(), std::io::Error> {
    let run = serde_json::json!({
        "run_id": uuid::Uuid::new_v4().to_string(),
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "palimpsest_version": env!("CARGO_PKG_VERSION"),
        "architecture": "v4.0-tauri-rust",
        "tracks": results,
        "parameters": {
            "n_topics": params.n_topics,
            "random_state": params.random_state,
        },
        "elapsed_seconds": elapsed.as_secs_f64().round_to(2),
        "parallel_execution": true,
    });
    std::fs::write(
        paths.project_dir.join("pipeline_run.json"),
        serde_json::to_string_pretty(&run)?,
    )
}
```

### Tauri command integration

```rust
// src-tauri/src/commands.rs

#[tauri::command]
pub async fn analyze_project(
    project_path: String,
    force: bool,
    state: tauri::State<'_, AppState>,
    app: tauri::AppHandle,
) -> Result<PipelineResult, String> {
    let paths = ProjectPaths::from_dir(Path::new(&project_path))
        .map_err(|e| e.to_string())?;

    let (progress_tx, mut progress_rx) = mpsc::channel(64);

    // Forward progress events to frontend
    let app_clone = app.clone();
    tokio::spawn(async move {
        while let Some(progress) = progress_rx.recv().await {
            let _ = app_clone.emit_all("pipeline:progress", &progress);
        }
    });

    let mut manager = PipelineManager::new(
        state.python_bin.clone(),
        state.annotation_store.lock().await.take().unwrap_or_default(),
        progress_tx,
    );

    manager
        .run_all(&paths, force, &PipelineParams::default())
        .await
        .map_err(|e| e.to_string())
}
```

### Test strategy

**Integration tests** (`core/tests/test_pipeline.py`):

```python
import subprocess, json, time
from pathlib import Path

def test_pipeline_parallel_runs_all_tracks(pp_full_project_dir):
    """All 5 tracks are produced; pipeline_run.json records parallel execution."""
    result = subprocess.run(
        ["palimpsest", "analyze", str(pp_full_project_dir)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    for track in ["entities", "sentiment", "lexical", "dialogue", "topics"]:
        jsonl = pp_full_project_dir / "tracks" / f"{track}.jsonl"
        assert jsonl.exists(), f"Missing {track}.jsonl"
        lines = [l for l in jsonl.read_text().splitlines() if l.strip()]
        assert len(lines) > 0, f"{track}.jsonl is empty"

    run = json.loads((pp_full_project_dir / "pipeline_run.json").read_text())
    assert run["architecture"] == "v4.0-tauri-rust"
    assert run["parallel_execution"] is True

@pytest.mark.benchmark
def test_pipeline_benchmark_full_pp(pp_full_project_dir, tmp_path):
    """Full 5-track parallel analysis of P&P completes in under 15 seconds."""
    import shutil
    fresh = tmp_path / "pp-bench"
    shutil.copytree(pp_full_project_dir, fresh)
    start = time.monotonic()
    subprocess.run(
        ["palimpsest", "analyze", "--force", str(fresh)],
        check=True, timeout=30,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 15.0, (
        f"Parallel pipeline exceeded 15s target: {elapsed:.1f}s. "
        f"Expected ~8s on M4 Max (limited by topics extractor at ~5s)."
    )

def test_pipeline_force_flag_recomputes(pp_full_project_dir):
    """--force flag re-runs all extractors even if JSONL files exist."""
    subprocess.run(["palimpsest", "analyze", str(pp_full_project_dir)], check=True, timeout=60)
    mtime_before = (pp_full_project_dir / "tracks" / "sentiment.jsonl").stat().st_mtime
    time.sleep(0.1)
    subprocess.run(["palimpsest", "analyze", "--force", str(pp_full_project_dir)], check=True, timeout=60)
    mtime_after = (pp_full_project_dir / "tracks" / "sentiment.jsonl").stat().st_mtime
    assert mtime_after > mtime_before, "--force did not rewrite sentiment.jsonl"

def test_pipeline_extractor_failure_is_non_fatal(pp_full_project_dir, tmp_path):
    """If one extractor fails, the others still complete."""
    # Corrupt the reference file for topics (simulate failure)
    # Other tracks should still produce output
    # (Implementation: patch topics module to exit non-zero for a specific project ID)
    pass  # TODO: implement with subprocess mock
```

**Performance benchmark** (`palimpsest-core/benches/parse_jsonl.rs`):

```rust
fn bench_parse_jsonl_line(c: &mut Criterion) {
    let line = r#"{"type":"Annotation","@context":["http://www.w3.org/ns/anno.jsonld"],"id":"urn:palimpsest:pp:sentiment:3a7f2c1b","body":{"type":"palimpsest:SentimentAnnotation","palimpsest:valence":-0.2732,"palimpsest:arousal":0.1841,"palimpsest:model":"vader","palimpsest:lfoType":"signal.sentiment"},"target":{"source":"urn:palimpsest:pp","selector":{"type":"TextPositionSelector","start":1024,"end":1267}},"palimpsest:confidence":0.6366,"palimpsest:evidenceLevel":"E5","creator":{"type":"Software","name":"vaderSentiment/3.3"}}"#;

    c.bench_function("parse_jsonl_to_packed", |b| {
        b.iter(|| parse_jsonl_line(line, TrackId::Sentiment).unwrap())
    });
}
// REQUIRED: assert throughput > 100K/sec
// 100K/sec means each call must be < 10 microseconds.
// criterion will measure: typical serde_json parse on M4 = 2-4 microseconds. This is achievable.
```

**Performance targets**:
| Operation | Target | Notes |
|-----------|--------|-------|
| Full P&P 5-track parallel analysis | <15s | Limited by topics ~5s; others are faster |
| JSONL parse to PackedAnnotation | <10μs | Must achieve 100K/sec |
| AnnotationStore insert (arena) | <1μs | Direct Vec push, no allocation |
| Tauri progress event emission | <1ms per event | Non-blocking `try_send` |

---

## Original Content (preserved for reference)

### Context

This task wires the five Milestone 1.2 track extractors into a unified `palimpsest analyze` command driven by `TrackRegistry.dependency_order()`. Before this task, `analyze` ran extractors in hardcoded order or only ran the entities track. After this task, all registered extractors run automatically in topological order, with per-track rich progress bars in the terminal, and a complete `pipeline_run.json` provenance record. The benchmark target — full P&P (122K words, 5 tracks) in under 30 seconds — is validated here.

### Design Decisions (original, some superseded)

- **Registry-driven, not hardcoded**: the plan §3.2 makes clear that the entire Base/X thesis depends on new tracks being addable without modifying core code. `TrackRegistry.discover()` with module auto-import is the correct pattern. (Note: v4.0 replaces this with a static Rust `Vec<ExtractorSpec>` — explicit is better than dynamic for a subprocess model.)
- **`--force` flag instead of always recomputing**: on a 122K-word novel, spaCy parsing alone takes ~8 seconds. If only one track config changed, recomputing everything wastes time.
- **Virtual `spacy_parse` dependency**: treating the spaCy parse as a virtual dependency (pre-condition) rather than a registered extractor avoids adding a non-annotation, non-signal producer to the registry.
- **Rich progress bars with `TimeElapsedColumn`**: the plan's CLI output in §9.1 shows elapsed time per track. (Note: v4.0 uses Tauri events for UI progress and stderr println for CLI progress.)
- **Manifest writing in CLI, not extractor**: the CLI is the authoritative orchestrator. Extractors expose `manifest() -> dict` but do not write files.
- **`palimpsest.__version__`**: must be defined in `core/palimpsest/__init__.py` as a string.
