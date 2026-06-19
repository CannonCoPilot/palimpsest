# T08: CLI + Pipeline Provenance

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 4 hours (Python) → 6 hours (v4.0: primary CLI is Rust binary)
**Dependencies**: T05, T06, T07
**Outputs**: `src-tauri/src/commands/` (Rust CLI + Tauri commands), `python/palimpsest/cli_extract.py` (Python subprocess CLI), `python/tests/test_pipeline.py` (CLI tests)

---

## v4.0 Critical Review

**The v3.0 CLI is a Python Click application. In v4.0, this is architecturally incorrect for three reasons, each load-bearing.**

1. **`palimpsest ingest` in Python calls `ingest_file()` in Python, which calls `extract_text()`, `normalize()`, `segment()`, and creates the project directory — all in Python.** In v4.0, all of this is the Rust `ProjectManager`. A Python CLI wrapping a Python function that calls Python modules is not wrong in isolation, but it creates an impossible situation: the Rust pipeline manager and the Python CLI would both try to create project directories, write metadata, and manage the workspace. There would be two authorities for project state. One must win. Rust wins.

2. **`palimpsest serve` starts a FastAPI HTTP server.** In v4.0, there is no HTTP server for local use. The browser is a Tauri webview. Annotation data is accessed via Tauri IPC commands. Starting FastAPI serves nothing. The `serve` command is **eliminated** — its function is replaced by `tauri dev` or the built Tauri application.

3. **`palimpsest analyze` runs extractors in-process in Python.** In v4.0, `analyze` is a Rust command that reads the `track_registry.json` manifest (written by `TrackRegistry.write_manifest()` in T04) and spawns Python subprocesses for each extractor in dependency order. The Rust command handles: subprocess lifecycle, stdout capture (JSONL), arena loading, error recovery (if one extractor crashes, others continue).

4. **`pipeline_run.json` is written by Python `analyze` command.** In v4.0, `pipeline_run.json` is written by the Rust `analyze` command, which captures subprocess metadata (Python version, spaCy version reported on stderr) and writes the provenance record.

5. **`rich` progress bars in the Python CLI.** This is a terminal UX feature. The Rust CLI can use `indicatif` for progress bars. Python subprocesses report progress to stderr which Rust forwards.

**What must change:**
- Primary user-facing CLI becomes a Rust binary (`palimpsest` binary from `src-tauri`)
- `palimpsest ingest <file>` → Rust `ProjectManager.ingest()` + Python subprocess for format extraction
- `palimpsest analyze <project-dir>` → Rust spawns Python subprocesses per extractor
- `palimpsest info <project-dir>` → Rust reads `metadata.json` and prints
- `palimpsest serve` → **eliminated** for local; reserved for future remote deployment mode
- `palimpsest open <project-dir>` → **new** command that launches the Tauri GUI
- Python `cli_extract.py` (T05) is the subprocess interface; no separate Python user CLI needed

---

## v4.0 Rewrite

### Rust CLI: `src-tauri/src/main.rs` + `src-tauri/src/cli/`

The Tauri application also exposes a CLI mode when invoked from the command line. Tauri 2.0 supports both GUI mode (default) and CLI mode via `tauri::Builder::default().plugin(tauri_plugin_cli::init())`.

```
palimpsest ingest <file> [--workspace <dir>] [--title <str>] [--author <str>] [--year <int>]
palimpsest analyze <project-dir> [--tracks <name,...>]
palimpsest info <project-dir>
palimpsest open <project-dir>       ← launches Tauri GUI window for this project
palimpsest export <project-dir> [--format w3c|paf|csv]
```

**`src-tauri/src/cli/ingest.rs`**:

```rust
//! palimpsest ingest: normalize + segment + create project directory.

use std::path::PathBuf;
use anyhow::Result;
use indicatif::{ProgressBar, ProgressStyle};
use crate::project::ProjectManager;

pub struct IngestArgs {
    pub file: PathBuf,
    pub workspace: PathBuf,
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i32>,
    pub language: String,
}

pub fn run(args: IngestArgs, python_extract_bin: PathBuf) -> Result<()> {
    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::default_spinner()
        .template("{spinner} {msg}")?);

    let manager = ProjectManager::new(python_extract_bin);
    let slug = filename_to_slug(&args.file)?;

    args.workspace.create_dir_all().unwrap_or(());

    pb.set_message(format!("Normalizing {}...", args.file.display()));
    let project_dir = manager.ingest(&args.file, &args.workspace, &slug)?;

    pb.finish_with_message(format!("Project created: {}", project_dir.display()));

    // Print summary
    let metadata = palimpsest_core::project::ProjectMetadata::load(&project_dir)?;
    println!();
    println!("  Title:      {}", metadata.title);
    println!("  Words:      {}", format_number(metadata.word_count));
    println!("  Sentences:  {}", format_number(metadata.sentence_count));
    println!("  Paragraphs: {}", format_number(metadata.paragraph_count));
    println!("  SHA-256:    {}...", &metadata.reference_sha256[..16]);

    Ok(())
}

fn filename_to_slug(path: &PathBuf) -> Result<String> {
    let stem = path.file_stem()
        .and_then(|s| s.to_str())
        .ok_or_else(|| anyhow::anyhow!("Cannot determine filename stem"))?;
    let slug = stem.to_lowercase()
        .replace(|c: char| !c.is_alphanumeric() && c != '-', "-")
        .trim_matches('-')
        .to_string();
    if slug.is_empty() {
        anyhow::bail!("Cannot create slug from filename: {}", path.display());
    }
    Ok(slug)
}

fn format_number(n: u64) -> String {
    // Simple thousands formatting
    let s = n.to_string();
    let mut result = String::new();
    for (i, c) in s.chars().rev().enumerate() {
        if i > 0 && i % 3 == 0 { result.push(','); }
        result.push(c);
    }
    result.chars().rev().collect()
}
```

**`src-tauri/src/cli/analyze.rs`**:

```rust
//! palimpsest analyze: spawn Python extractors, load results into arenas.

use std::path::PathBuf;
use std::process::Command;
use std::time::Instant;
use anyhow::Result;
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use palimpsest_core::project::{LoadedProject, ProjectMetadata};
use palimpsest_core::annotation::{load_jsonl_into_arena, track_name_to_id};

pub struct AnalyzeArgs {
    pub project_dir: PathBuf,
    pub tracks: Option<Vec<String>>,  // None = all tracks from registry manifest
}

pub fn run(args: AnalyzeArgs, python_extract_bin: PathBuf) -> Result<()> {
    let start = Instant::now();
    let metadata = ProjectMetadata::load(&args.project_dir)?;

    // Read track registry manifest (written by TrackRegistry.write_manifest())
    let registry_path = args.project_dir.join("track_registry.json");
    if !registry_path.exists() {
        anyhow::bail!(
            "track_registry.json not found in {}. \
             Run: palimpsest-extract write-registry <project-dir>",
            args.project_dir.display()
        );
    }
    let registry: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&registry_path)?)?;

    let execution_order: Vec<String> = registry["execution_order"]
        .as_array()
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default();

    let tracks_to_run: Vec<String> = match &args.tracks {
        Some(specified) => specified.clone(),
        None => execution_order,
    };

    println!(
        "Analyzing {} ({} words) — {} track(s)",
        metadata.title,
        format_number(metadata.word_count),
        tracks_to_run.len()
    );

    let mp = MultiProgress::new();
    let style = ProgressStyle::default_bar()
        .template("[{elapsed_precise}] {bar:30} {msg}")?;

    let mut tracks_computed: Vec<String> = Vec::new();
    let mut run_metadata: serde_json::Map<String, serde_json::Value> = serde_json::Map::new();

    for track_name in &tracks_to_run {
        let pb = mp.add(ProgressBar::new(100));
        pb.set_style(style.clone());
        pb.set_message(format!("Running {track_name}..."));

        let track_start = Instant::now();
        let output_path = args.project_dir.join("tracks").join(format!("{track_name}.jsonl"));

        // Spawn Python subprocess: palimpsest-extract track <track_name> <project_dir>
        let result = Command::new(&python_extract_bin)
            .args(["track", track_name, &args.project_dir.to_string_lossy()])
            .output();

        match result {
            Ok(output) if output.status.success() => {
                // Write JSONL output to tracks/
                std::fs::write(&output_path, &output.stdout)?;

                // Load into arena (validates format)
                let track_id = track_name_to_id(track_name);
                let mut arena = palimpsest_core::annotation::AnnotationArena::new();
                let count = load_jsonl_into_arena(&output_path, track_id, &mut arena)?;

                let elapsed_ms = track_start.elapsed().as_millis();
                pb.finish_with_message(format!("{track_name}: {count} annotations ({elapsed_ms}ms)"));
                tracks_computed.push(track_name.clone());

                // Capture stderr metadata (Python version, model version, etc.)
                let stderr = String::from_utf8_lossy(&output.stderr);
                if let Some(meta_line) = stderr.lines().find(|l| l.starts_with("META:")) {
                    if let Ok(meta) = serde_json::from_str::<serde_json::Value>(&meta_line[5..]) {
                        run_metadata.insert(track_name.clone(), meta);
                    }
                }
            }
            Ok(output) => {
                let stderr = String::from_utf8_lossy(&output.stderr);
                pb.finish_with_message(format!("{track_name}: FAILED — {}", &stderr[..stderr.len().min(80)]));
                eprintln!("Track {track_name} failed: {stderr}");
                // Continue with other tracks (resilient pipeline)
            }
            Err(e) => {
                pb.finish_with_message(format!("{track_name}: ERROR — {e}"));
                eprintln!("Failed to spawn extractor for {track_name}: {e}");
            }
        }
    }

    let elapsed = start.elapsed();

    // Write pipeline_run.json (§2.8)
    let run_id = uuid::Uuid::new_v4().to_string();
    let pipeline_run = serde_json::json!({
        "run_id": run_id,
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "palimpsest_version": env!("CARGO_PKG_VERSION"),
        "annotation_format": "W3C Web Annotation JSON-LD (JSONL)",
        "tracks_computed": tracks_computed,
        "signals_computed": [],
        "elapsed_seconds": elapsed.as_secs_f64().round() * 100.0 / 100.0,
        "track_metadata": run_metadata,
    });

    let run_path = args.project_dir.join("pipeline_run.json");
    std::fs::write(&run_path, serde_json::to_string_pretty(&pipeline_run)?)?;

    println!(
        "\nDone: {} track(s) in {:.1}s",
        tracks_computed.len(),
        elapsed.as_secs_f64()
    );
    println!("Pipeline run saved: {}", run_path.display());

    Ok(())
}
```

### Python Subprocess: `track` Command

The `python/palimpsest/cli_extract.py` (T05) gets one new command:

```python
@main.command()
@click.argument("track_name")
@click.argument("project_dir", type=click.Path(exists=True, path_type=Path))
def track(track_name: str, project_dir: Path) -> None:
    """
    Run a single track extractor on a project. Writes JSONL to stdout.
    Writes metadata (Python version, model version) to stderr as: META:{json}

    Called by Rust analyze command for each track in dependency order.
    """
    import sys
    import json as json_module
    from palimpsest.project import Project
    from palimpsest.tracks.registry import TrackRegistry
    import palimpsest.tracks.entities    # ensure registered
    import palimpsest.tracks.sentiment  # noqa: F401
    # etc. — import all track modules to trigger registration

    try:
        project = Project.load(project_dir)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"Error loading project: {exc}\n")
        sys.exit(1)

    reg = TrackRegistry.discover()
    try:
        extractor_cls = reg.get(track_name)
    except KeyError:
        sys.stderr.write(f"Unknown track: {track_name!r}\n")
        sys.exit(1)

    extractor = extractor_cls()

    try:
        result = extractor.extract(project)
    except Exception as exc:
        sys.stderr.write(f"Extractor {track_name} failed: {exc}\n")
        sys.exit(1)

    # Write JSONL to stdout
    if extractor.output_type == "annotation":
        assert isinstance(result, list)
        for ann in sorted(result, key=lambda a: a.target.selector.start
                          if hasattr(a.target.selector, "start") else 0):
            sys.stdout.write(json_module.dumps(ann.to_jsonld(), ensure_ascii=False) + "\n")
        sys.stdout.flush()

    # Write metadata to stderr for provenance
    import spacy
    meta = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "spacy_version": spacy.__version__,
        "annotation_count": len(result) if isinstance(result, list) else 0,
    }
    sys.stderr.write(f"META:{json_module.dumps(meta)}\n")
    sys.stderr.flush()
```

### Python Tests (adapted from v3.0)

Tests in `python/tests/test_pipeline.py` are restructured. The original Click `CliRunner` tests for the Python CLI are replaced with:

1. Tests of `python/palimpsest/cli_extract.py` using Click `CliRunner` (verifying subprocess CLI)
2. Integration tests that create a fixture project using the Rust CLI and verify outputs

```python
from click.testing import CliRunner
from palimpsest.cli_extract import main

@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_extract_normalize_pp_ch1(runner: CliRunner, pp_ch1_txt: Path) -> None:
    result = runner.invoke(main, ["normalize", str(pp_ch1_txt)])
    assert result.exit_code == 0
    assert "It is a truth universally acknowledged" in result.output


def test_cli_extract_track_entities(
    runner: CliRunner, pp_ch1_project: "Project", tmp_path: Path
) -> None:
    """track subcommand outputs valid W3C JSONL to stdout."""
    import json
    result = runner.invoke(main, ["track", "entities", str(pp_ch1_project.path)])
    assert result.exit_code == 0, result.output
    lines = [l for l in result.output.strip().split("\n") if l.strip()]
    assert len(lines) > 0
    # Each line must be valid JSON with W3C structure
    for line in lines:
        ann = json.loads(line)
        assert ann["type"] == "Annotation"
        assert ann["palimpsest:evidenceLevel"] == "E4"


def test_pipeline_run_json_structure(pp_ch1_project: "Project") -> None:
    """pipeline_run.json written by Rust analyze must have required fields."""
    import json
    run_path = pp_ch1_project.path / "pipeline_run.json"
    if not run_path.exists():
        pytest.skip("pipeline_run.json not present (run palimpsest analyze first)")
    data = json.loads(run_path.read_text())
    required = ["run_id", "timestamp", "palimpsest_version",
                 "annotation_format", "tracks_computed", "elapsed_seconds"]
    for field in required:
        assert field in data, f"Missing field: {field!r}"
    assert data["annotation_format"] == "W3C Web Annotation JSON-LD (JSONL)"
    assert isinstance(data["tracks_computed"], list)
```

## Acceptance Criteria

- `palimpsest ingest fixtures/pride-prejudice-ch1.txt --workspace /tmp/test/` creates project directory with `reference.txt`, `metadata.json`, `tracks/segments.jsonl`
- `palimpsest analyze <project-dir>` spawns Python subprocess for entities track, writes `tracks/entities.jsonl` and `pipeline_run.json`
- `palimpsest info <project-dir>` prints title, word count, and lists computed tracks
- `palimpsest open <project-dir>` launches Tauri window (not testable in CI; manual verification)
- `pipeline_run.json` contains: `run_id` (UUID format), `timestamp` (ISO 8601), `annotation_format: "W3C Web Annotation JSON-LD (JSONL)"`, `tracks_computed: ["entities"]`
- `palimpsest ingest` called twice on same file + workspace exits with non-zero error code
- `palimpsest-extract track entities <project-dir>` writes valid W3C JSONL to stdout
- Python CLI tests pass: `pytest python/tests/test_pipeline.py`
- `cargo build --bin palimpsest` exits 0
- `palimpsest serve` command **does not exist** (eliminated — raises error if attempted)

## Design Decisions

- **Rust primary CLI, Python subprocess**: This eliminates the ambiguity of two CLIs (Python and Rust) with overlapping responsibilities. The Rust binary is the user-facing entry point. Python subprocesses are internal details.

- **`pipeline_run.json` written by Rust**: Provenance belongs with the pipeline orchestrator. Rust controls the subprocess lifecycle, knows which extractors succeeded or failed, and captures their exit codes. Python's role in provenance is limited to what it reports on stderr (META: line).

- **`serve` command eliminated**: In v4.0, the local use case has no HTTP server. Serving projects over HTTP for remote access is a Phase 3+ feature (remote/collaborative mode). Adding it now as a stub would imply it works when it doesn't — the browser can't fetch data over HTTP when it uses Tauri IPC commands.

- **`indicatif` for Rust progress bars**: Equivalent to Python's `rich.progress`. Rust crate `indicatif` provides spinner + bar + multi-progress support. Terminal output quality is identical.

- **Track `META:` stderr protocol**: A structured stderr line prefixed with `META:` is a simple IPC convention. It avoids having Rust parse arbitrary stderr text. The Rust `analyze` command checks for this prefix and parses the JSON portion for provenance recording.

---

## Original Content (v3.0, preserved for reference)

The v3.0 T08 defined a Python Click CLI with `ingest`, `analyze`, `info`, and `serve` commands. In v4.0, the user-facing CLI is rewritten in Rust. The Python `cli_extract.py` provides the subprocess interface. The `serve` command is eliminated. `pipeline_run.json` is written by Rust. All provenance fields from §2.8 are preserved.
