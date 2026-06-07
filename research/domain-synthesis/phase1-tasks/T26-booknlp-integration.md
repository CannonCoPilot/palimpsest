# T26: BookNLP Integration

**Milestone**: 1.3b — BookNLP + DotplotView
**Estimated effort**: 6 hours (Days 32-33)
**Dependencies**: T04 (entities track, `entities.jsonl` stable), T14 (dialogue track, `dialogue.jsonl` stable), T15 (TrackRegistry, pipeline orchestration)
**Outputs**: `core/palimpsest/tracks/booknlp_enrichment.py`, `core/tests/test_tracks.py` (extended), modified `tracks/entities.jsonl` (enriched in-place), modified `tracks/dialogue.jsonl` (enriched in-place), new `tracks/coreference.jsonl`

---

## v4.0 Critical Review

**Verdict: The Python subprocess model for BookNLP is correct and must stay Python — BookNLP cannot be rewritten in Rust. The critical failure is what happens to BookNLP's output: it is parsed into Python dicts, written back to JSONL, and then later re-read by Rust into the AnnotStore. This double-parse (BookNLP output → Python → JSONL → Rust) introduces a ~2-5 second wall-clock delay in the enrichment path and creates a file-locked update window where entities.jsonl is partially written.**

### What Is Broken

**In-place JSONL enrichment is dangerous under concurrent access.** `write_track()` on `entities.jsonl` opens the file for writing while the Rust AnnotStore has the file memory-mapped. Under macOS, a mmap'd file can be concurrently written by another process (the POSIX standard allows it), but the Rust side will read stale pages until the OS invalidates them. In practice this means Rust sees the pre-enrichment entity annotations even after BookNLP writes the enriched ones. The AnnotStore must be invalidated and reloaded after enrichment.

**Parsing 2GB of BookNLP Java output through Python dicts is gratuitously slow.** BookNLP writes structured output files (`.entities`, `.quotes`, `.coref`). The current design reads these, creates Python `Annotation` objects, serializes to JSON strings, writes JSONL. For a 120K-word novel with 850 entity annotations, this involves 850 Python object allocations → 850 JSON serializations → 850 JSONL write calls. Rust can ingest BookNLP's native output files directly using the `serde_json` crate, bypassing the Python intermediary for the Rust AnnotStore update.

**`psutil` memory check before BookNLP is theater.** BookNLP's memory usage depends on the model size, the text length, and the JVM heap configuration — none of which `psutil.virtual_memory().available` can predict. The JVM requests heap pages lazily; `psutil` will show plenty of available memory right before the JVM allocates 2GB and the system starts swapping. Remove the `psutil` check and instead set JVM flags: `-Xmx2g -Xms512m` via `JAVA_OPTS`.

**The `±10 character tolerance` for matching BookNLP quotes to existing dialogue annotations is fragile.** BookNLP uses character offsets from its own tokenization of `reference.txt`, which may differ from spaCy's tokenization. Offset drift can exceed 10 characters for quotes preceded by Unicode normalization differences. The matching should use overlap intersection, not offset proximity.

**The `--enrich` flag is the right design.** BookNLP is slow (2-5 minutes for a full novel), memory-intensive (2GB JVM), and optional. Opt-in is correct.

---

## v4.0 Rewrite

### Architecture

BookNLP runs as a managed Java subprocess under the Rust `AnalysisPipeline`. Python is used only as the BookNLP Python API wrapper — the simplest way to invoke BookNLP's Java code without shelling directly to Java. Rust monitors the subprocess and streams the output files to the AnnotStore as they are written.

```
palimpsest analyze --enrich
  → Rust AnalysisPipeline spawns Python subprocess: booknlp_runner.py
  → Python: booknlp.BookNLP.process(reference_txt, output_dir, project_id)
  → BookNLP Java runs (2-5 min); writes .entities, .quotes, .coref files
  → Rust watches output_dir via inotify/FSEvents for new files
  → As each file appears, Rust ingests it into AnnotStore in parallel
  → After Java exits (code 0), Rust writes enriched entities.jsonl + coreference.jsonl
  → Rust invalidates and reloads AnnotStore for the project
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| BookNLP invocation | Python subprocess: `booknlp_runner.py` (thin wrapper) |
| Subprocess management | Rust `tokio::process::Command` with stdout/stderr streaming |
| Output file ingestion | Rust `serde_json` reading BookNLP `.entities`, `.quotes`, `.coref` |
| Coreference graph | Rust packed graph structure: `Vec<CorefChain>` with `Vec<Mention>` |
| JSONL output | Rust writes enriched `entities.jsonl` and new `coreference.jsonl` |
| AnnotStore invalidation | Rust `ProjectManager.invalidate_and_reload(project_id)` |

### Rust Subprocess Management

```rust
// palimpsest-core/src/pipeline.rs

impl AnalysisPipeline {
    pub async fn run_booknlp(
        &self,
        project: &Project,
        output_dir: &Path,
    ) -> Result<BookNLPOutput> {
        // Check Java available
        let java_check = tokio::process::Command::new("java")
            .arg("-version")
            .output().await?;
        if !java_check.status.success() {
            return Err(PipelineError::BookNLPUnavailable("Java not found".into()));
        }

        // Spawn Python wrapper (thin — just calls booknlp.BookNLP)
        let mut child = tokio::process::Command::new(&self.python_bin)
            .args([
                "-m", "palimpsest.booknlp_runner",
                "--input", project.reference_txt().to_str().unwrap(),
                "--output-dir", output_dir.to_str().unwrap(),
                "--project-id", &project.id,
                "--model", "big",
            ])
            .env("JAVA_OPTS", "-Xmx2g -Xms512m")
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()?;

        // Stream stderr for progress reporting via Tauri events
        let project_id = project.id.clone();
        tokio::spawn(async move {
            if let Some(stderr) = child.stderr.take() {
                let reader = tokio::io::BufReader::new(stderr);
                let mut lines = reader.lines();
                while let Ok(Some(line)) = lines.next_line().await {
                    // Forward progress to frontend via Tauri event
                    let _ = tauri::async_runtime::spawn(async move {
                        // emit("booknlp_progress", &line) ...
                    });
                }
            }
        });

        let status = child.wait().await?;
        if !status.success() {
            return Err(PipelineError::BookNLPFailed(status.code().unwrap_or(-1)));
        }

        // Ingest BookNLP output files
        self.ingest_booknlp_output(project, output_dir).await
    }

    async fn ingest_booknlp_output(
        &self,
        project: &Project,
        output_dir: &Path,
    ) -> Result<BookNLPOutput> {
        let entities_file = output_dir.join(format!("{}.entities", project.id));
        let quotes_file = output_dir.join(format!("{}.quotes", project.id));
        let coref_file = output_dir.join(format!("{}.coref", project.id));

        // Parse BookNLP entity list: canonical IDs and types
        let canonical_entities = self.parse_booknlp_entities(&entities_file)?;

        // Parse coreference chains
        let coref_chains = self.parse_booknlp_coref(&coref_file)?;

        // Build packed coreference graph
        let packed_graph = CorefGraph::from_chains(&coref_chains);

        Ok(BookNLPOutput { canonical_entities, coref_chains, packed_graph })
    }
}
```

### Packed Coreference Graph

```rust
// palimpsest-core/src/annotation/coreference.rs

/// Packed in-memory coreference representation.
/// Designed for O(1) lookup of all mentions in a given character range.
pub struct CorefGraph {
    /// One entry per chain. chains[i] = Vec of mention indices in `mentions`.
    pub chains: Vec<Vec<u32>>,

    /// All mentions, sorted by start offset.
    /// Augmented interval tree over these for range queries.
    pub mentions: Vec<CorefMention>,

    pub mention_index: RangeIndex<u32, u32>,  // [start, end] → mention index
}

#[repr(C)]
pub struct CorefMention {
    pub start: u32,
    pub end: u32,
    pub chain_id: u32,
    pub mention_type: MentionType,  // Pronoun=0, Name=1, Description=2
    pub referent_id: u32,           // canonical character ID
}

#[derive(Clone, Copy)]
#[repr(u8)]
pub enum MentionType {
    Pronoun = 0,
    Name = 1,
    Description = 2,
}
```

Memory: each `CorefMention` is 17 bytes (4+4+4+1+4). For P&P with ~5,000 coreference mentions: 85KB. Fits entirely in L2 cache. Range queries via the interval tree are O(log N + k).

### JSONL Output from Rust

After BookNLP completes, Rust writes the enriched JSONL files directly — no Python serialization:

```rust
// palimpsest-core/src/annotation/jsonl_writer.rs

impl JonlWriter {
    /// Enrich existing entities.jsonl with canonical IDs from BookNLP.
    pub fn enrich_entities_with_canonical(
        &self,
        entities_path: &Path,
        canonical_map: &HashMap<u32, CanonicalCharacter>,
        output_path: &Path,
    ) -> Result<()> {
        let reader = BufReader::new(File::open(entities_path)?);
        let writer = BufWriter::new(File::create(output_path)?);

        for line in reader.lines() {
            let line = line?;
            if line.trim().is_empty() { continue; }
            let mut ann: serde_json::Value = serde_json::from_str(&line)?;

            // Match by character offset (using overlap, not proximity)
            let start = ann["target"]["selector"]["start"].as_u64().unwrap_or(0) as u32;
            let end = ann["target"]["selector"]["end"].as_u64().unwrap_or(0) as u32;

            if let Some(canonical) = canonical_map.get(&self.find_character_at(start, end)) {
                ann["body"]["palimpsest:canonicalId"] = json!(canonical.id.to_string());
                ann["body"]["palimpsest:characterType"] = json!(canonical.character_type);
            }

            serde_json::to_writer(&mut writer, &ann)?;
            writer.write_all(b"\n")?;
        }
        Ok(())
    }

    /// Write coreference.jsonl from packed CorefGraph.
    pub fn write_coreference_jsonl(
        &self,
        graph: &CorefGraph,
        project_id: &str,
        output_path: &Path,
    ) -> Result<()> {
        let writer = BufWriter::new(File::create(output_path)?);
        for (chain_idx, chain) in graph.chains.iter().enumerate() {
            for &mention_idx in chain {
                let mention = &graph.mentions[mention_idx as usize];
                let ann = json!({
                    "@context": ["http://www.w3.org/ns/anno.jsonld",
                                 {"palimpsest": "https://palimpsest.dev/ns/"}],
                    "type": "Annotation",
                    "id": format!("urn:palimpsest:{}:coreference:c{}m{}", project_id, chain_idx, mention_idx),
                    "body": {
                        "type": "palimpsest:CoreferenceAnnotation",
                        "purpose": "linking",
                        "palimpsest:chainId": format!("chain_{}", chain_idx),
                        "palimpsest:referentId": format!("character_{}", mention.referent_id),
                        "palimpsest:mentionType": match mention.mention_type {
                            MentionType::Pronoun => "pronoun",
                            MentionType::Name => "name",
                            MentionType::Description => "description",
                        }
                    },
                    "target": {
                        "source": format!("urn:palimpsest:{}", project_id),
                        "selector": {
                            "type": "TextPositionSelector",
                            "start": mention.start,
                            "end": mention.end
                        }
                    },
                    "creator": {"type": "Software", "name": "booknlp/2.0"},
                    "palimpsest:confidence": 0.85,
                    "palimpsest:evidenceLevel": "E4"
                });
                serde_json::to_writer(&mut writer, &ann)?;
                writer.write_all(b"\n")?;
            }
        }
        Ok(())
    }
}
```

### Offset Matching Strategy (Fixing the ±10 char Flaw)

BookNLP mentions are matched to existing spaCy annotations using **overlap intersection**, not proximity:

```rust
fn mentions_overlap(a_start: u32, a_end: u32, b_start: u32, b_end: u32) -> bool {
    a_start < b_end && b_start < a_end
}
```

Any BookNLP mention that overlaps with an existing entity annotation (even partially) is considered a match. The annotation with the highest overlap ratio is selected. This is robust to tokenization differences between spaCy and BookNLP.

### AnnotStore Invalidation

After enrichment writes new JSONL files, the Rust ProjectManager must reload:

```rust
impl ProjectManager {
    pub async fn reload_after_enrichment(&mut self, project_id: &str) -> Result<()> {
        // Drop existing AnnotStore (releases mmap handles)
        self.projects.get_mut(project_id)
            .ok_or("Project not found")?
            .annot_store = None;

        // Reload from enriched JSONL files
        let project = self.projects.get_mut(project_id).unwrap();
        project.annot_store = Some(
            AnnotStore::load_from_jsonl(&project.tracks_dir).await?
        );

        // Notify frontend via Tauri event
        // emit("project_enriched", project_id)
        Ok(())
    }
}
```

### Python Runner (Thin Wrapper)

```python
# core/palimpsest/booknlp_runner.py
"""
Thin wrapper invoked by Rust AnalysisPipeline as a subprocess.
Does nothing except call BookNLP and exit. All orchestration is in Rust.
"""

import sys
import argparse
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--model", default="big")
    args = parser.parse_args()

    try:
        from booknlp.booknlp import BookNLP
    except ImportError:
        print("ERROR: booknlp package not installed", file=sys.stderr)
        sys.exit(2)

    model_params = {"pipeline": "entity,quote,coref", "model": args.model}
    nlp = BookNLP("en", model_params)
    nlp.process(args.input, args.output_dir, args.project_id)
    sys.exit(0)

if __name__ == "__main__":
    main()
```

Total Python code for BookNLP integration: ~30 lines. All logic is in Rust.

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| BookNLP Java runtime (full novel) | 2-5 min | Cannot be improved; JVM + NLP pipeline |
| Rust ingest of BookNLP output files | <5s | Rust serde_json parsing |
| Enriched JSONL write (entities + coreference) | <1s | Rust BufWriter |
| AnnotStore reload after enrichment | <100ms | Re-mmap from updated files |
| `CorefMention` range query (any char range) | <1ms | Interval tree O(log N + k) |

### Acceptance Criteria (v4.0)

- Without `--enrich`: `BookNLPEnrichmentTrack` is never invoked; runtime unchanged
- Java not found: Rust detects it in subprocess spawn, logs warning, records `booknlp_available: false`
- BookNLP unavailable (pip package): Python subprocess exits 2, Rust logs warning, exit code 0
- BookNLP completes: `tracks/coreference.jsonl` written by Rust with valid W3C annotations (evidenceLevel E4)
- `entities.jsonl` enriched in-place with `palimpsest:canonicalId` using overlap matching
- `coreference.jsonl` loads correctly into Rust `CorefGraph` (range queries work)
- AnnotStore reloaded after enrichment (Tauri emits `project_enriched` event)
- `cargo test` passes all BookNLP integration tests
- `mypy --strict` passes on `booknlp_runner.py`

### Tests

```python
# core/tests/test_tracks.py — TestBookNLPEnrichmentTrack

def test_booknlp_runner_exits_2_if_not_installed(tmp_project, monkeypatch):
    """Python subprocess exits with code 2 when booknlp not installed."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "palimpsest.booknlp_runner",
         "--input", str(tmp_project.reference_txt),
         "--output-dir", str(tmp_project.cache_dir / "booknlp"),
         "--project-id", tmp_project.id],
        env={**os.environ, "PYTHONPATH": ""},  # strip booknlp from path
    )
    assert result.returncode == 2
```

```rust
// palimpsest-core/src/pipeline_tests.rs

#[tokio::test]
async fn test_booknlp_unavailable_returns_error_not_panic() {
    let pipeline = AnalysisPipeline::new_test();
    let result = pipeline.run_booknlp(&mock_project(), &tempdir().path()).await;
    // Java not found in test env: should be Err, not panic
    assert!(result.is_err());
    match result.unwrap_err() {
        PipelineError::BookNLPUnavailable(_) => {},
        other => panic!("Expected BookNLPUnavailable, got {:?}", other),
    }
}

#[test]
fn test_coref_graph_range_query() {
    let mentions = vec![
        CorefMention { start: 100, end: 150, chain_id: 0, mention_type: MentionType::Name, referent_id: 1 },
        CorefMention { start: 500, end: 520, chain_id: 0, mention_type: MentionType::Pronoun, referent_id: 1 },
    ];
    let graph = CorefGraph::from_mentions(mentions);
    // Query overlapping [90, 160]
    let results = graph.mention_index.query(90, 160);
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].chain_id, 0);
}

#[test]
fn test_offset_overlap_matching() {
    // spaCy annotation: [100, 120]. BookNLP mention: [98, 118]. Overlap = 20 chars.
    assert!(mentions_overlap(100, 120, 98, 118));
    // No overlap: [100, 120] and [125, 140]
    assert!(!mentions_overlap(100, 120, 125, 140));
}
```

---

## Original Content (Reference)

**Milestone**: 1.3b — BookNLP + DotplotView
**Estimated effort**: 6 hours (Days 32-33)

### Context (original)

BookNLP provides higher-quality character identification and coreference resolution than spaCy alone. It canonicalizes entity mentions, attributes dialogue to speakers, and produces coreference chains. BookNLP requires Java 11+ and is memory-intensive (~2GB at runtime). It is an optional dependency invoked via `--enrich` flag.

### Design Decisions (original)

- **In-place enrichment, not replacement**: Existing annotations updated by adding BookNLP-derived fields.
- **Coreference as a separate track**: Coreference chains cross many paragraphs, one `CoreferenceAnnotation` per mention.
- **Fallback to 8 tracks**: Pipeline degrades gracefully to 8 tracks when BookNLP unavailable.
- **`--enrich` opt-in**: Keeps default `palimpsest analyze` fast (<30 seconds target).
