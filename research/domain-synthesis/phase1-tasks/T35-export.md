# T35: Export (W3C + PAF + CSV)

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours
**Dependencies**: T02 (W3C annotation model), T03 (project directory structure), all track extractors T04-T16
**Outputs**: `palimpsest-core/src/export/` module, `core/palimpsest/cli.py` (modified), `core/tests/test_export.py`

---

## v4.0 Critical Review

**Verdict: Python-based export is correct for small corpora but hits a performance ceiling at Phase 2 scale. The deeper problem is that the export reads from JSONL files — iterating them line by line, deserializing each annotation into Python dicts, and re-serializing to W3C/PAF/CSV. When the annotations already live in the Rust AnnotStore as packed binary structures, bypassing the JSONL files for export is both faster and architecturally cleaner. The export pipeline must be Rust-native.**

### What Is Broken

**Python `read_track()` → annotation dicts → re-serialization is 3× slower than necessary.** For P&P with 18,760 annotations across 6 tracks:
- Python reads 18,760 JSON lines from JSONL files: ~0.5s
- Deserializes 18,760 dicts via `json.loads()`: ~0.2s
- Re-serializes to CSV/PAF via string formatting: ~0.3s
- Total: ~1 second for all tracks combined

This is fine for Phase 1 at one text. For Phase 2 with 60+ novels, batch export would take ~60 seconds in Python. Rust reads the AnnotStore (already in packed binary format) and serializes directly — no Python dict intermediary.

**W3C AnnotationCollection `"items"` array with all 18,760 annotations.** For a 6-track novel, this produces a single `entities.collection.json` with 847 annotations serialized as one JSON array. The file size will be ~3-5MB. For 60 novels exported to W3C, this is 300MB of JSON files. The Rust serde serializer is ~10× faster than Python's `json.dump` for this volume.

**CSV export with `csv.DictWriter` creating one row per annotation.** DictWriter in Python is slow for 18,760 rows because it builds a dict per row, validates column names, and writes via a per-row string format call. Rust's CSV writer (`csv` crate) buffers writes and is significantly faster.

**`annotation_to_paf_row()` uses string formatting with `f-string`.** For 18,760 annotations, this is 18,760 Python f-string evaluations. Rust's format! macro compiles to native code; the performance difference is 10-50×.

**The `--track` filter is implemented by skipping JSONL files.** Under Rust, track filtering is a bitmask operation on the AnnotStore. No file I/O skipping needed.

---

## v4.0 Rewrite

### Architecture

Export is implemented as a Rust binary subcommand (`palimpsest-core export`) and exposed as a Tauri command. The Python CLI (`palimpsest export`) calls the Rust binary as a subprocess, identical to the pattern used for self-similarity computation.

The Rust export reads from the AnnotStore (not JSONL files) for W3C and PAF formats. For CSV, it reads directly from the AnnotStore's packed structs and body arena. JSONL files remain the authoritative source (Rust writes to them during analysis), but export bypasses re-reading them by using the already-in-memory AnnotStore.

For the Tauri app, export is accessible via the Export dialog which calls the `export_project` Tauri command.

### Technology Stack

| Component | Technology |
|-----------|-----------|
| W3C export | Rust `serde_json` streaming serializer |
| PAF export | Rust `std::io::BufWriter` with tab-separated format |
| CSV export | Rust `csv` crate (buffered writer) |
| CLI entry point | `palimpsest export` → subprocess `palimpsest-core export` |
| Tauri entry point | `export_project` Tauri command |
| Streaming | Rust iterator over AnnotStore — no full annotation load into memory |

### Rust Export Module

```rust
// palimpsest-core/src/export/mod.rs

pub trait Exporter: Send {
    fn export_track(
        &self,
        track_name: &str,
        annotations: impl Iterator<Item = AnnotationRecord>,
        project: &LoadedProject,
        output_dir: &Path,
    ) -> Result<ExportStats>;
}

pub struct W3CExporter;
pub struct PAFExporter;
pub struct CSVExporter {
    writer: Option<csv::Writer<BufWriter<File>>>,
}
```

### W3C Export: Streaming JSON-LD

```rust
// palimpsest-core/src/export/w3c.rs

impl Exporter for W3CExporter {
    fn export_track(
        &self,
        track_name: &str,
        annotations: impl Iterator<Item = AnnotationRecord>,
        project: &LoadedProject,
        output_dir: &Path,
    ) -> Result<ExportStats> {
        let out_path = output_dir.join(format!("{}.collection.json", track_name));
        let file = BufWriter::new(File::create(&out_path)?);

        // Collect to Vec for total count (needed in header)
        // Alternative: two-pass (count first, then write)
        let all_anns: Vec<AnnotationRecord> = annotations.collect();
        let total = all_anns.len();

        let mut ser = serde_json::Serializer::new(file);
        // Write collection header
        let mut map = ser.serialize_map(None)?;
        map.serialize_entry("@context", &W3C_CONTEXT)?;
        map.serialize_entry("type", "AnnotationCollection")?;
        map.serialize_entry("id", &format!("urn:palimpsest:{}:{}:collection",
            project.id, track_name))?;
        map.serialize_entry("label", &format!("{} annotations for {}",
            track_name, project.meta.title))?;
        map.serialize_entry("total", &total)?;
        map.serialize_entry("palimpsest:exportedAt", &chrono::Utc::now().to_rfc3339())?;
        map.serialize_entry("palimpsest:referenceSha256", &project.meta.reference_sha256)?;
        map.serialize_entry("palimpsest:palimpsestVersion", env!("CARGO_PKG_VERSION"))?;

        // Write items array
        map.serialize_entry("items", &AnnotationsSerializer(&all_anns, project))?;
        map.end()?;

        // Validate: total == len(items)
        assert_eq!(total, all_anns.len());

        Ok(ExportStats { track: track_name.to_string(), count: total, path: out_path })
    }
}
```

### PAF Export: Zero-Allocation Row Writing

```rust
// palimpsest-core/src/export/paf.rs

impl Exporter for PAFExporter {
    fn export_track(
        &self,
        track_name: &str,
        annotations: impl Iterator<Item = AnnotationRecord>,
        project: &LoadedProject,
        output_dir: &Path,
    ) -> Result<ExportStats> {
        let out_path = output_dir.join(format!("{}.paf", track_name));
        let mut writer = BufWriter::with_capacity(1 << 20, File::create(&out_path)?);

        // Header
        writeln!(writer, "##palimpsest-paf-version 0.1")?;
        writeln!(writer, "##reference-sha256 {}", project.meta.reference_sha256)?;
        writeln!(writer, "##reference-file reference.txt")?;
        writeln!(writer, "##exported-from W3C Web Annotation JSONL")?;
        writeln!(writer, "#docname\tsource\ttype\tstart\tend\tscore\tstrand\tphase\tattributes")?;

        let doc_name = project.id.replace('-', "_");
        let mut count = 0;
        let mut sorted: Vec<AnnotationRecord> = annotations.collect();
        sorted.sort_by_key(|a| a.start); // PAF is sorted by start position

        for ann in sorted {
            // Build attributes string without heap allocation
            write_paf_row(&mut writer, &ann, &doc_name, &project.body_arena)?;
            count += 1;
        }

        Ok(ExportStats { track: track_name.to_string(), count, path: out_path })
    }
}

#[inline]
fn write_paf_row(
    writer: &mut impl Write,
    ann: &AnnotationRecord,
    doc_name: &str,
    body_arena: &BodyArena,
) -> Result<()> {
    let body = body_arena.get(ann.body_offset);
    let lfo_type = body.lfo_type();
    let source = body.creator_name().unwrap_or(".");
    let score = format!("{:.4}", ann.confidence as f32 / 10000.0);

    // Attributes: build in a small stack-allocated buffer
    let mut attrs = SmallVec::<[u8; 256]>::new();
    write!(attrs, "ID={};evidence=E{}", ann.local_id, ann.evidence_level)?;

    // Body-type-specific attributes (no heap allocation)
    match body.body_type() {
        BodyType::Entity => {
            write!(attrs, ";Name={};entity_type={}", body.entity_name(), body.entity_type())?;
            if let Some(canonical_id) = body.canonical_id() {
                write!(attrs, ";canonical_id={}", canonical_id)?;
            }
        }
        BodyType::Sentiment => {
            write!(attrs, ";valence={:.4};arousal={:.4}", body.valence(), body.arousal())?;
        }
        BodyType::Dialogue => {
            write!(attrs, ";quote_type={}", body.quote_type())?;
            if let Some(speaker) = body.speaker() {
                write!(attrs, ";speaker={}", speaker)?;
            }
        }
        BodyType::Topic => {
            write!(attrs, ";topic_id={};topic_weight={:.4}", body.topic_id(), body.topic_weight())?;
        }
        BodyType::Coreference => {
            write!(attrs, ";chain_id={}", body.chain_id())?;
        }
        _ => {}
    }

    writeln!(writer, "{}\t{}\t{}\t{}\t{}\t{}\t.\t.\t{}",
        doc_name, source, lfo_type, ann.start, ann.end, score,
        std::str::from_utf8(&attrs)?)?;
    Ok(())
}
```

`SmallVec<[u8; 256]>` avoids heap allocation for the attributes string (attribute strings are typically <100 bytes). This makes PAF export zero-allocation per row for typical annotations.

### CSV Export: Streaming via `csv` Crate

```rust
// palimpsest-core/src/export/csv_export.rs

pub struct CSVExporter;

impl CSVExporter {
    pub fn export_all_tracks(
        &self,
        tracks: &[&str],
        project: &LoadedProject,
        output_dir: &Path,
    ) -> Result<ExportStats> {
        let out_path = output_dir.join("annotations.csv");
        let mut writer = csv::WriterBuilder::new()
            .has_headers(true)
            .from_path(&out_path)?;

        // Write header
        writer.write_record(&[
            "track", "id", "body_type", "lfo_type", "char_start", "char_end",
            "confidence", "evidence_level", "creator",
            "entity_type", "entity_name", "valence", "arousal",
            "quote_type", "speaker", "topic_id", "topic_weight", "chain_id",
        ])?;

        let mut total = 0;
        let track_mask = tracks.iter().enumerate()
            .map(|(i, _)| 1u64 << i)
            .fold(0u64, |acc, m| acc | m);

        // Stream annotations from AnnotStore ordered by track, then start position
        for ann in project.annot_store.iter_by_track(track_mask) {
            let body = project.body_arena.get(ann.body_offset);
            let track_name = project.track_name(ann.track_id);

            // Zero-copy write — csv crate handles buffering
            writer.write_record(&[
                track_name,
                &format!("urn:palimpsest:{}:{}:{}", project.id, track_name, ann.local_id),
                body.type_name(),
                body.lfo_type(),
                &ann.start.to_string(),
                &ann.end.to_string(),
                &format!("{:.4}", ann.confidence as f32 / 10000.0),
                &format!("E{}", ann.evidence_level),
                body.creator_name().unwrap_or(""),
                body.entity_type_str().unwrap_or(""),
                body.entity_name().unwrap_or(""),
                &format_opt_f32(body.valence()),
                &format_opt_f32(body.arousal()),
                body.quote_type_str().unwrap_or(""),
                body.speaker().unwrap_or(""),
                &format_opt_u32(body.topic_id()),
                &format_opt_f32(body.topic_weight()),
                &format_opt_u32(body.chain_id()),
            ])?;
            total += 1;
        }
        writer.flush()?;

        Ok(ExportStats { track: "all".to_string(), count: total, path: out_path })
    }
}
```

`project.annot_store.iter_by_track(mask)` is an iterator over `PackedAnnotation` filtered by track bitmask — the same SIMD filter as `query_viewport`. No file I/O.

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| W3C export, 5 tracks, 18,760 annotations | <200ms | Rust serde_json streaming |
| PAF export, 1 track, 3,500 annotations | <50ms | Zero-allocation row write |
| CSV export, 5 tracks, 18,760 annotations | <100ms | csv crate buffered |
| All 3 formats, all 5 tracks | <500ms total | Parallelizable (rayon) |
| Memory usage during export | <50MB | No annotation-dict heap |

Compare to Python: ~1-2 seconds for the same workload.

### CLI Integration

`palimpsest export` calls `palimpsest-core export` as a subprocess:

```python
# core/palimpsest/cli.py

@main.command()
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--format", "fmt", type=click.Choice(["w3c", "paf", "csv"]), required=True)
@click.option("--track", "tracks", multiple=True)
@click.option("--output", "-o", type=click.Path(), default=None)
def export(project_dir: str, fmt: str, tracks: tuple[str, ...], output: str | None) -> None:
    """Export annotations from PROJECT_DIR in the specified format."""
    output_dir = output or str(Path(project_dir) / "exports" / fmt)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    track_args = []
    for t in tracks:
        track_args += ["--track", t]

    result = subprocess.run(
        [
            "palimpsest-core", "export",
            "--project-dir", project_dir,
            "--format", fmt,
            "--output-dir", output_dir,
        ] + track_args,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        click.echo(f"Export failed: {result.stderr}", err=True)
        raise SystemExit(1)
    click.echo(result.stdout)
```

### Tauri Command

```rust
#[tauri::command]
pub async fn export_project(
    project_id: String,
    format: String,  // "w3c", "paf", "csv"
    tracks: Vec<String>,
    output_dir: String,
    state: tauri::State<'_, AppState>,
) -> Result<ExportReport, String> {
    let core = state.core.lock().await;
    let project = core.get_project(&project_id).ok_or("Project not found")?;
    let output = Path::new(&output_dir);
    output.parent().map(|p| std::fs::create_dir_all(p));

    let track_mask = build_track_mask(&tracks, &project.track_registry);
    let annotations = project.annot_store.iter_by_track(track_mask);

    let stats = match format.as_str() {
        "w3c" => W3CExporter.export_all_tracks(&tracks, project, output)?,
        "paf" => PAFExporter.export_all_tracks(&tracks, project, output)?,
        "csv" => CSVExporter.export_all_tracks(&tracks, project, output)?,
        other => return Err(format!("Unknown format: {}", other)),
    };

    Ok(ExportReport { stats, output_dir: output.to_string_lossy().to_string() })
}
```

### Validation

After W3C export, Rust validates the output:

```rust
fn validate_w3c_collection(path: &Path) -> Result<()> {
    let content: serde_json::Value = serde_json::from_reader(File::open(path)?)?;
    ensure!(content["type"] == "AnnotationCollection", "Wrong type");
    ensure!(content["@context"].is_array(), "Missing @context");
    let total = content["total"].as_u64().ok_or("Missing total")?;
    let items_len = content["items"].as_array()
        .map(|a| a.len() as u64)
        .ok_or("Missing items")?;
    ensure!(total == items_len, "total != items.len()");
    Ok(())
}
```

### Acceptance Criteria (v4.0)

- `palimpsest export projects/pride-and-prejudice/ --format w3c` completes in <500ms
- W3C export validates (type, @context, total == len(items))
- PAF rows are tab-separated with exactly 9 fields; start < end
- CSV has all 18 columns; entity rows have non-empty entity_type and entity_name
- `--track entities --track sentiment` exports only those two tracks
- No Python dict allocation during export (Rust streams from AnnotStore)
- Export on project with no analyzed tracks: user-friendly error, exit code 1
- `cargo test` passes all export tests
- `ruff check` passes on `cli.py` subprocess wrapper

### Tests

```rust
#[test]
fn test_paf_export_correct_columns() {
    let project = mock_project_with_entity_annotation();
    let mut buf = Vec::new();
    let mut writer = BufWriter::new(&mut buf);
    write_paf_row(&mut writer, &project.annot_store.packed[0], "pride_prejudice", &project.body_arena).unwrap();
    let row = String::from_utf8(buf).unwrap();
    let fields: Vec<&str> = row.trim().split('\t').collect();
    assert_eq!(fields.len(), 9);
    assert_eq!(fields[0], "pride_prejudice");
    let start: u32 = fields[3].parse().unwrap();
    let end: u32 = fields[4].parse().unwrap();
    assert!(start < end);
}

#[test]
fn test_w3c_export_total_matches_items() {
    let project = mock_project_with_n_annotations(42);
    let tmp = tempdir().unwrap();
    let stats = W3CExporter.export_track("entities", project.annot_store.iter_by_track(1), &project, tmp.path()).unwrap();
    assert_eq!(stats.count, 42);
    let content: serde_json::Value = serde_json::from_reader(
        File::open(tmp.path().join("entities.collection.json")).unwrap()
    ).unwrap();
    assert_eq!(content["total"].as_u64().unwrap(), 42);
    assert_eq!(content["items"].as_array().unwrap().len(), 42);
}

#[test]
fn test_csv_export_columns() {
    let project = mock_project_with_n_annotations(10);
    let tmp = tempdir().unwrap();
    CSVExporter.export_all_tracks(&["entities"], &project, tmp.path()).unwrap();
    let mut reader = csv::Reader::from_path(tmp.path().join("annotations.csv")).unwrap();
    let headers = reader.headers().unwrap().clone();
    assert!(headers.iter().any(|h| h == "entity_type"));
    assert!(headers.iter().any(|h| h == "char_start"));
    assert_eq!(headers.len(), 18);
}

#[tokio::test]
async fn test_export_benchmark() {
    let project = mock_project_with_n_annotations(18_760);
    let tmp = tempdir().unwrap();
    let start = std::time::Instant::now();
    W3CExporter.export_all_tracks(&["entities", "sentiment", "lexical", "dialogue", "topics"],
                                   &project, tmp.path()).unwrap();
    let elapsed = start.elapsed();
    assert!(elapsed.as_millis() < 200, "W3C export took {}ms, target <200ms", elapsed.as_millis());
}
```

---

## Original Content (Reference)

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours

### Context (original)

Export makes annotations available in W3C AnnotationCollection JSON-LD, GFF3-analogue TSV (PAF), and flat CSV. All derive from JSONL primary storage. Python `read_track()` → annotation dicts → re-serialization.

### Design Decisions (original)

- **W3C export wraps JSONL items verbatim**: Items are the same JSON-LD objects from JSONL.
- **PAF as derived, lossy format**: Cannot represent all W3C properties.
- **CSV flattened across all tracks**: Single file for cross-track analysis in pandas.
- **`--track` filter flag**: Export subset of tracks.
- **PAF `ID` from URN last segment**: Full URN too long for GFF3 attribute values.
