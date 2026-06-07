# T06: Project Directory Manager + Metadata Schema

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 4 hours (Python) → 7 hours (v4.0: Rust ProjectManager is primary)
**Dependencies**: T03, T04, T05
**Outputs**: `core/src/project/` (Rust — primary), `python/palimpsest/project.py` (Python — extractor interface only), tests

---

## v4.0 Critical Review

**The Python `Project` class in v3.0 is doing three jobs that must be separated in v4.0: project creation (now Rust), extractor interface (still Python), and metadata I/O (both).**

Specific failures:

1. **`ingest_file()` is a Python function that creates the project directory, writes `reference.txt`, runs segmentation, and writes `metadata.json`.** In v4.0 all of this is the Rust `ProjectManager.ingest()` responsibility. The Python `ingest_file()` function must be eliminated or reduced to a test-only convenience wrapper around the subprocess calls.

2. **`Project.reference_text` loads `reference.txt` on first access from Python.** Python extractors do need this — they read `reference.txt` to perform NLP. This lazy-loading property is correct for the Python extractor interface. However, the Rust engine uses `mmap` to access `reference.txt`, not Python file reading. These are two separate access patterns for the same file, which is fine.

3. **Signal binary files are accessed via `Project.signal_binary_path()` in Python.** In v4.0, signal files are memory-mapped by the Rust `SignalStore`, not read by Python. Python extractors that produce signals write them; Rust reads them via mmap. The `Project` class's signal path helpers are still valid for extractor output, but the browser never fetches signal data through Python.

4. **`ProjectMetadata` has 15 fields defined in Python.** This schema must also be expressible in Rust (as a `serde`-deserializable struct) for the Rust engine to read `metadata.json`. The two definitions must be kept in sync. Adding a field to one requires updating both. This is a maintenance risk.

5. **`metadata.validate()` runs in Python.** Validation should run at metadata creation time (Rust) and optionally be callable from Python for test assertions. The canonical validator is Rust (it's the authoritative writer). Python validation is a convenience for extractor tests.

6. **`project.py` imports from `palimpsest.ingest.*` at module level.** In v4.0, the Python `project.py` should have minimal imports — it's loaded by extractors which don't need to import the full ingest pipeline.

**What must change:**
- Rust `core/src/project/manager.rs` is the primary project manager (T05 already describes ingest)
- Rust `core/src/project/metadata.rs` defines `ProjectMetadata` as a serde struct
- Rust `core/src/project/loader.rs` defines `ProjectLoader` for loading existing projects (used by Tauri commands)
- Python `python/palimpsest/project.py` is reduced to an extractor interface: lazy reference_text, path helpers, metadata loading
- `metadata.json` schema is defined by the Rust struct and documented in specs

---

## v4.0 Rewrite

### Rust: `core/src/project/metadata.rs`

```rust
//! ProjectMetadata: canonical 15-field schema (§2.7).
//! This struct is authoritative. Python mirrors it as a dataclass.

use serde::{Deserialize, Serialize};

/// 15-field project metadata schema (§2.7).
/// Written by Rust ProjectManager on ingest; read by Rust loader and Python extractors.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectMetadata {
    pub id: String,
    pub title: String,
    pub language: String,
    pub source_format: String,
    pub source_file: String,
    pub ingest_date: String,              // ISO 8601 date: "2026-06-07"
    pub palimpsest_version: String,
    pub reference_sha256: String,         // SHA-256 of normalized reference.txt
    pub word_count: u64,
    pub paragraph_count: u64,
    pub section_count: u64,
    pub sentence_count: u64,
    pub character_count: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub author: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub year: Option<i32>,
}

impl ProjectMetadata {
    /// Validate that required fields are non-empty and id is a valid slug.
    pub fn validate(&self) -> Vec<String> {
        let mut errors = Vec::new();

        let required = [
            ("id", &self.id),
            ("title", &self.title),
            ("language", &self.language),
            ("source_format", &self.source_format),
            ("source_file", &self.source_file),
            ("ingest_date", &self.ingest_date),
            ("palimpsest_version", &self.palimpsest_version),
            ("reference_sha256", &self.reference_sha256),
        ];
        for (field, value) in &required {
            if value.is_empty() {
                errors.push(format!("Missing required field: {field:?}"));
            }
        }

        if !self.id.is_empty() && !is_valid_slug(&self.id) {
            errors.push(format!(
                "id must be URL-safe slug (lowercase, hyphens only): got {:?}",
                self.id
            ));
        }

        if self.reference_sha256.len() != 64 {
            errors.push(format!(
                "reference_sha256 must be 64 hex chars, got {} chars",
                self.reference_sha256.len()
            ));
        }

        errors
    }

    /// Load metadata from a project directory.
    pub fn load(project_dir: &std::path::Path) -> anyhow::Result<Self> {
        let path = project_dir.join("metadata.json");
        let text = std::fs::read_to_string(&path)
            .map_err(|_| anyhow::anyhow!("metadata.json not found in {}", project_dir.display()))?;
        let meta: Self = serde_json::from_str(&text)
            .map_err(|e| anyhow::anyhow!("Failed to parse metadata.json: {e}"))?;
        let errors = meta.validate();
        if !errors.is_empty() {
            anyhow::bail!("Invalid metadata.json: {:?}", errors);
        }
        Ok(meta)
    }
}

fn is_valid_slug(s: &str) -> bool {
    !s.is_empty()
        && s.chars().all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
        && !s.starts_with('-')
        && !s.ends_with('-')
}
```

### Rust: `core/src/project/loader.rs`

```rust
//! ProjectLoader: loads an existing Palimpsest project into memory.
//! Called by Tauri commands: load_project(project_dir).

use std::path::{Path, PathBuf};
use anyhow::Result;
use crate::annotation::{AnnotationArena, load_jsonl_into_arena, track_name_to_id};
use crate::project::metadata::ProjectMetadata;

/// A loaded Palimpsest project: metadata + annotation arenas for each track.
pub struct LoadedProject {
    pub dir: PathBuf,
    pub metadata: ProjectMetadata,
    /// One arena per track. Key: track name ("entities", "segments", etc.)
    pub arenas: std::collections::HashMap<String, AnnotationArena>,
}

impl LoadedProject {
    /// Load project from directory. Discovers and loads all JSONL tracks found in tracks/.
    ///
    /// Performance target: full novel with 18,760 annotations → < 100ms.
    pub fn load(project_dir: &Path) -> Result<Self> {
        let dir = project_dir.to_owned();
        let metadata = ProjectMetadata::load(project_dir)?;

        let mut arenas = std::collections::HashMap::new();

        let tracks_dir = project_dir.join("tracks");
        if tracks_dir.is_dir() {
            for entry in std::fs::read_dir(&tracks_dir)? {
                let entry = entry?;
                let path = entry.path();
                if path.extension().map(|e| e == "jsonl").unwrap_or(false) {
                    let track_name = path
                        .file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("unknown")
                        .to_string();
                    let track_id = track_name_to_id(&track_name);
                    let mut arena = AnnotationArena::new();
                    match load_jsonl_into_arena(&path, track_id, &mut arena) {
                        Ok(count) => {
                            tracing::debug!("Loaded {count} annotations from {track_name}");
                            arenas.insert(track_name, arena);
                        }
                        Err(e) => {
                            tracing::warn!("Failed to load track {track_name}: {e}");
                        }
                    }
                }
            }
        }

        Ok(Self { dir, metadata, arenas })
    }

    /// Return the source URN for this project.
    pub fn source_urn(&self) -> String {
        format!("urn:palimpsest:{}", self.metadata.id)
    }

    /// Path to tracks/ directory.
    pub fn tracks_dir(&self) -> PathBuf {
        self.dir.join("tracks")
    }

    /// Path to signals/ directory.
    pub fn signals_dir(&self) -> PathBuf {
        self.dir.join("signals")
    }

    /// Path to a specific track JSONL file.
    pub fn track_path(&self, name: &str) -> PathBuf {
        self.tracks_dir().join(format!("{name}.jsonl"))
    }

    /// Total memory used by all annotation arenas.
    pub fn memory_bytes(&self) -> usize {
        self.arenas.values().map(|a| a.memory_bytes()).sum()
    }
}
```

### Rust: `core/src/project/mod.rs`

```rust
pub mod loader;
pub mod manager;
pub mod metadata;
pub mod signals;

pub use loader::LoadedProject;
pub use manager::ProjectManager;
pub use metadata::ProjectMetadata;
```

### Python: `python/palimpsest/project.py` (reduced)

The Python `project.py` is now an extractor interface only. It does not create projects (Rust does) or validate metadata authoritatively (Rust does). It provides lazy access to project data for Python NLP extractors:

```python
"""Project: extractor interface for accessing project data from Python.

This module is used by Python TrackExtractors via extract(project).
Project creation and management is handled by the Rust ProjectManager.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProjectMetadata:
    """Mirror of the Rust ProjectMetadata struct. Load from metadata.json."""
    id: str
    title: str
    language: str
    source_format: str
    source_file: str
    ingest_date: str
    palimpsest_version: str
    reference_sha256: str
    word_count: int
    paragraph_count: int
    section_count: int
    sentence_count: int
    character_count: int
    author: str | None = None
    year: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id, "title": self.title, "language": self.language,
            "source_format": self.source_format, "source_file": self.source_file,
            "ingest_date": self.ingest_date, "palimpsest_version": self.palimpsest_version,
            "reference_sha256": self.reference_sha256, "word_count": self.word_count,
            "paragraph_count": self.paragraph_count, "section_count": self.section_count,
            "sentence_count": self.sentence_count, "character_count": self.character_count,
        }
        if self.author is not None:
            d["author"] = self.author
        if self.year is not None:
            d["year"] = self.year
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectMetadata":
        return cls(
            id=data["id"], title=data["title"], language=data["language"],
            source_format=data["source_format"], source_file=data["source_file"],
            ingest_date=data["ingest_date"], palimpsest_version=data["palimpsest_version"],
            reference_sha256=data["reference_sha256"], word_count=data["word_count"],
            paragraph_count=data["paragraph_count"], section_count=data["section_count"],
            sentence_count=data["sentence_count"], character_count=data["character_count"],
            author=data.get("author"), year=data.get("year"),
        )

    def validate(self) -> list[str]:
        """Python-side validation (mirrors Rust validator; for extractor tests only)."""
        errors: list[str] = []
        for f in ["id", "title", "language", "source_format", "source_file",
                  "ingest_date", "palimpsest_version", "reference_sha256"]:
            if not getattr(self, f):
                errors.append(f"Missing required field: {f!r}")
        if self.id and not re.match(r"^[a-z0-9][a-z0-9\-]*$", self.id):
            errors.append(f"id must be URL-safe slug: got {self.id!r}")
        return errors


@dataclass
class Project:
    """
    Extractor interface for a Palimpsest project.

    Python TrackExtractors receive this as `project` in extract(project).
    The project directory was created by the Rust ProjectManager.
    This class provides lazy-loaded access to reference.txt and path helpers.
    """
    path: Path
    metadata: ProjectMetadata
    _reference_text: str | None = field(default=None, repr=False)

    @property
    def reference_text(self) -> str:
        """Load reference.txt on first access; cached thereafter."""
        if self._reference_text is None:
            self._reference_text = (self.path / "reference.txt").read_text(encoding="utf-8")
        return self._reference_text

    @property
    def source_urn(self) -> str:
        return f"urn:palimpsest:{self.metadata.id}"

    @property
    def tracks_dir(self) -> Path:
        return self.path / "tracks"

    @property
    def signals_dir(self) -> Path:
        return self.path / "signals"

    @property
    def manifests_dir(self) -> Path:
        return self.path / "manifests"

    @property
    def cache_dir(self) -> Path:
        return self.path / "cache"

    def track_path(self, track_name: str) -> Path:
        return self.tracks_dir / f"{track_name}.jsonl"

    def signal_manifest_path(self, signal_name: str) -> Path:
        return self.signals_dir / f"{signal_name}.json"

    def signal_binary_path(self, signal_name: str) -> Path:
        return self.signals_dir / f"{signal_name}.bin"

    @classmethod
    def load(cls, project_dir: Path) -> "Project":
        """Load project from directory (created by Rust ProjectManager)."""
        meta_path = project_dir / "metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"No metadata.json in {project_dir}")
        metadata = ProjectMetadata.from_dict(json.loads(meta_path.read_text()))
        errors = metadata.validate()
        if errors:
            raise ValueError(f"Invalid metadata.json: {errors}")
        return cls(path=project_dir.resolve(), metadata=metadata)
```

Note: `ingest_file()` is **removed** from Python `project.py`. It exists now only in Rust. For Python tests that need a project directory, use `conftest.py` fixtures that call the Rust CLI or use `Project.load()` on a pre-created fixture project.

### Test Strategy

**Rust tests** (`core/tests/integration/project_load.rs`):

```rust
#[test]
fn test_project_metadata_validate_valid() {
    let meta = ProjectMetadata {
        id: "pride-and-prejudice".to_string(),
        title: "Pride and Prejudice".to_string(),
        language: "en".to_string(),
        source_format: "txt".to_string(),
        source_file: "pp.txt".to_string(),
        ingest_date: "2026-06-07".to_string(),
        palimpsest_version: "0.1.0".to_string(),
        reference_sha256: "a".repeat(64),
        word_count: 100_000,
        paragraph_count: 5000,
        section_count: 61,
        sentence_count: 12000,
        character_count: 700_000,
        author: Some("Jane Austen".to_string()),
        year: Some(1813),
    };
    assert!(meta.validate().is_empty());
}

#[test]
fn test_project_metadata_validate_invalid_slug() {
    let mut meta = /* valid metadata */ ...;
    meta.id = "Pride and Prejudice".to_string();  // spaces not allowed
    let errors = meta.validate();
    assert!(!errors.is_empty());
    assert!(errors.iter().any(|e| e.contains("slug")));
}

#[test]
fn test_loaded_project_memory_budget() {
    // A full-novel project with 18,760 annotations should fit in < 5MB total arena memory
    let arena = AnnotationArena::mock(18_760);
    assert!(arena.memory_bytes() < 5_000_000);
}
```

**Python tests** (in `python/tests/test_pipeline.py`):

The v3.0 tests for `ingest_file()` must be rewritten as tests of `Project.load()` on fixture projects created by the Rust CLI or by the `python_project` conftest fixture. The logic remains the same — we verify that:
- `metadata.validate()` returns [] for valid projects
- `project.reference_text` loads correctly
- `project.track_path("entities")` returns the right path
- `Project.load()` raises `FileNotFoundError` for directories without `metadata.json`

The test `test_ingest_pdf_same_sha256_as_txt` is preserved but is now a Rust integration test (Rust does the normalization and hashing).

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| `LoadedProject::load` (P&P full, 18K annotations) | < 100ms | Criterion benchmark |
| `ProjectMetadata::load` | < 5ms | JSON parse only |
| `arena.memory_bytes()` for 18,760 annotations | < 2MB | Measured in T03 |
| `Project.load()` (Python) | < 50ms | JSON parse + path resolution |
| `project.reference_text` first access | < 20ms | File read (700KB) |

## Acceptance Criteria

### Rust
- `cargo test -p palimpsest-core project` passes all unit tests
- `ProjectMetadata::validate()` returns empty vec for valid metadata
- `ProjectMetadata::validate()` catches empty `id`, invalid slug, wrong-length SHA-256
- `ProjectMetadata` serializes to/from JSON matching the v3.0 15-field schema exactly
- `LoadedProject::load` successfully loads a project with entity + segment JSONL tracks
- `LoadedProject::memory_bytes()` for 18,760-annotation project < 2MB

### Python
- `pytest python/tests/test_pipeline.py` passes all tests (restructured for v4.0)
- `mypy --strict python/palimpsest/project.py` exits 0
- `Project.load()` raises `FileNotFoundError` for directory without `metadata.json`
- `Project.load()` raises `ValueError` for invalid `metadata.json`
- `project.reference_text` loads `reference.txt` lazily and caches
- Python `ProjectMetadata` and Rust `ProjectMetadata` produce identical JSON for same inputs

## Design Decisions

- **Rust is authoritative for project creation, Python is authoritative for NLP.** This boundary is strictly enforced: no Python code creates project directories, no Rust code runs spaCy. The `ingest_file()` Python function is eliminated entirely.

- **Metadata schema defined in Rust, mirrored in Python.** Keeping two definitions is a maintenance burden, but the alternative (calling Python from Rust just to deserialize metadata) is worse. The schema is stable and small (15 fields). Changes to it must update both. This is documented in the Rust `metadata.rs` file header.

- **`LoadedProject` holds named arenas, not a single merged arena.** Keeping tracks separate allows per-track filtering (track_mask bitmask) without re-parsing. The `FilterEngine` can apply the mask over the merged annotation slice when needed, or query arenas individually.

---

## Original Content (v3.0, preserved for reference)

The original T06 defined `core/palimpsest/project.py` with `ProjectMetadata`, `Project`, and `ingest_file()`. In v4.0, `ingest_file()` is replaced by Rust `ProjectManager.ingest()`, `ProjectMetadata` is mirrored in Rust, and the Python `project.py` is reduced to the extractor interface. All 15 metadata fields are preserved.
