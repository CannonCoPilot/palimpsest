# T05: Ingestion Pipeline (Extractor + Normalizer + Segmenter)

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 6 hours (Python) → 9 hours (v4.0: adds Rust segmentation ingestion)
**Dependencies**: T03, T04
**Outputs**: `python/palimpsest/ingest/` (Python, format extraction + normalization), Rust `core/src/project/` (segmentation + project creation), `python/tests/test_ingest.py`

---

## v4.0 Critical Review

**The ingestion pipeline has the clearest split in v4.0: Python does what only Python can do (file format parsing), Rust does what must be fast (normalization verification, segmentation write, project structure creation).**

Specific problems with the v3.0 design:

1. **spaCy sentence segmentation is called inside `ingest/segmenter.py`, which is called inside `ingest_file()`, which is called inside the Rust-managed pipeline.** In v4.0, `ingest_file()` is the responsibility of the Rust `ProjectManager`. The Python ingest module is a subprocess that the Rust manager spawns, not a Python function called from Python. Therefore the spaCy call in `segmenter.py` must be expressible as a subprocess that writes JSONL to stdout.

2. **The segmenter runs spaCy with `disable=["ner"]` to avoid duplicate work with `EntityExtractor`.** This optimization is still valid and preserved. However, in v4.0 the segments JSONL file is immediately consumed by the Rust arena loader (`load_jsonl_into_arena(path, track_id=5, arena)`). The segment JSONL structure must therefore be exactly W3C-compliant — not a simplified format.

3. **`normalizer.py` is a Python module.** The normalization steps (NFC, quote replacement, whitespace collapse) are fast enough in Python for Phase 1. However, the normalized text's SHA-256 is used as a content identifier, and the Rust `ProjectManager` needs to verify this hash after writing `reference.txt`. The hash verification must be done in Rust to avoid a Python subprocess roundtrip just for verification.

4. **`_split_paragraphs()` uses `text.index(block, current_pos)` which has O(n²) behavior on texts with repeated substrings.** For a 700KB novel with many repeated words, this will be slow. Replace with a proper linear scan using regex-based position tracking.

5. **The Python `segment()` function loads spaCy at function call time (module-level `_nlp` cache).** This means the first call to `palimpsest-extract segments` subprocess startup pays the spaCy load cost (0.5s). For the Rust pipeline manager, this is a per-track subprocess cost that is acceptable. The Rust manager can pre-load and re-use Python subprocesses across tracks using subprocess pools if needed.

6. **No normalization performance test.** The target is `normalize(700KB novel) < 500ms`. This must be tested.

**What must change:**
- Python ingest retains: `extractor.py` (PDF/EPUB/TXT format extraction), `normalizer.py` (text cleaning)
- Python ingest retains: `segmenter.py` (spaCy sentence segmentation) — output goes to stdout as JSONL
- Python ingest adds: `cli_extract.py` — thin Click CLI wrapping each ingest step for Rust subprocess calls
- Rust adds: project directory creation, reference.txt write, SHA-256 hash verification in `core/src/project/manager.rs`
- `_split_paragraphs()` fixed to linear scan

---

## v4.0 Rewrite

### Architecture: Python Formats, Rust Project

```
User file (PDF/EPUB/TXT)
    ↓ Python: palimpsest-extract normalize <file>
    ↓ → stdout: normalized UTF-8 text

Rust ProjectManager:
    → writes reference.txt
    → computes SHA-256 (in Rust)
    → creates directory structure
    ↓ spawns: palimpsest-extract segment <reference.txt>
    ↓ → stdout: JSONL segments (one W3C annotation per line)
    → loads JSONL into arena (track_id=5, segments)
    → writes tracks/segments.jsonl
    → writes metadata.json
```

### Python: `python/palimpsest/ingest/extractor.py`

Identical to v3.0. No changes. PDF/EPUB/TXT extraction is a Python-only concern.

### Python: `python/palimpsest/ingest/normalizer.py`

```python
"""Text normalization: Unicode NFC, whitespace collapse, quote normalization, SHA-256."""
from __future__ import annotations
import hashlib
import re
import unicodedata

_QUOTE_MAP: dict[str, str] = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "—": "--",  # em dash
    "–": "-",   # en dash
    "…": "...", # ellipsis
}
_QUOTE_TABLE = str.maketrans(_QUOTE_MAP)


def normalize(text: str) -> str:
    """
    Normalize text to Palimpsest canonical form.

    Steps (in order, each idempotent):
    1. Unicode NFC normalization
    2. Typographic quote → ASCII quote substitution
    3. Normalize line endings to '\\n'
    4. Collapse runs of >2 newlines to exactly 2 (paragraph boundary)
    5. Collapse horizontal whitespace within lines; strip each line
    6. Strip full text; ensure single trailing newline

    Idempotent: normalize(normalize(text)) == normalize(text).
    Character offset stability: offsets in the normalized text are the reference
    for all downstream annotations. Rust verifies the SHA-256 matches.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_QUOTE_TABLE)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Linear line processing — no regex on the full string for this step
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines).strip() + "\n"
    return text


def compute_sha256(text: str) -> str:
    """Compute SHA-256 of the normalized text (UTF-8 encoded)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_words(text: str) -> int:
    """Count whitespace-delimited tokens."""
    return len(text.split())


def count_characters(text: str) -> int:
    """Count Unicode code points (not bytes)."""
    return len(text)
```

### Python: `python/palimpsest/ingest/segmenter.py`

The `segment()` function is preserved from v3.0 with one fix: `_split_paragraphs()` now uses a linear scan instead of `str.index()` in a loop.

```python
def _split_paragraphs(text: str) -> list[tuple[str, int, int]]:
    """
    Split text on double newlines into (paragraph_text, start_offset, end_offset) tuples.

    Linear scan: O(n). Previous version used str.index() in a loop which is O(n²)
    on texts with repeated substrings (common in literary prose).
    """
    paragraphs: list[tuple[str, int, int]] = []
    current_pos = 0
    text_len = len(text)

    while current_pos < text_len:
        # Find next double-newline
        sep_pos = text.find("\n\n", current_pos)
        if sep_pos == -1:
            # No more separators — rest of text is one block
            block = text[current_pos:]
            if block.strip():
                paragraphs.append((block, current_pos, text_len))
            break

        block = text[current_pos:sep_pos]
        if block.strip():
            paragraphs.append((block, current_pos, sep_pos))

        # Skip past the double newline (and any additional newlines)
        current_pos = sep_pos + 2
        while current_pos < text_len and text[current_pos] == "\n":
            current_pos += 1

    return paragraphs
```

All other `segmenter.py` code (section detection, spaCy sentence segmentation, `SegmentResult`) is preserved from v3.0.

### Python: `python/palimpsest/cli_extract.py`

**New file.** This is the subprocess interface called by the Rust pipeline manager. It wraps the Python ingest functions as CLI commands that write to stdout or to a file.

```python
"""
Subprocess CLI for Rust pipeline manager integration.

Called by the Rust ProjectManager as:
  palimpsest-extract normalize <source-file>     → writes normalized text to stdout
  palimpsest-extract segment <reference-txt>      → writes JSONL segments to stdout
  palimpsest-extract metadata <project-dir>       → writes metadata fields to stdout (JSON)

These are not user-facing commands. They are internal IPC between Rust and Python.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import click


@click.group()
def main() -> None:
    """Internal subprocess CLI for Rust pipeline manager."""


@main.command()
@click.argument("source_file", type=click.Path(exists=True, path_type=Path))
def normalize(source_file: Path) -> None:
    """
    Extract and normalize a source file. Writes normalized text to stdout (UTF-8).
    Also writes SHA-256 to stderr as: "SHA256:<hex>\\n" for Rust verification.
    """
    from palimpsest.ingest.extractor import extract_text
    from palimpsest.ingest.normalizer import normalize as do_normalize, compute_sha256

    raw_text, _fmt = extract_text(source_file)
    normalized = do_normalize(raw_text)
    sha256 = compute_sha256(normalized)

    # Write normalized text to stdout (binary mode to avoid encoding issues)
    sys.stdout.buffer.write(normalized.encode("utf-8"))
    sys.stderr.write(f"SHA256:{sha256}\n")
    sys.stderr.flush()


@main.command()
@click.argument("reference_txt", type=click.Path(exists=True, path_type=Path))
@click.argument("source_urn")
def segment(reference_txt: Path, source_urn: str) -> None:
    """
    Segment a normalized reference.txt. Writes W3C JSONL to stdout (one annotation per line).
    Writes counts to stderr as JSON: {"paragraphs": N, "sentences": N, "sections": N}
    """
    import json
    from palimpsest.ingest.segmenter import segment as do_segment
    from palimpsest.annotation.serializer import write_track

    text = reference_txt.read_text(encoding="utf-8")
    result = do_segment(text, source_urn)

    all_anns = result.all_annotations
    for ann in sorted(all_anns, key=lambda a: a.target.selector.start if hasattr(a.target.selector, "start") else 0):
        sys.stdout.write(json.dumps(ann.to_jsonld(), ensure_ascii=False) + "\n")
    sys.stdout.flush()

    counts = {
        "paragraphs": result.paragraph_count(),
        "sentences": result.sentence_count(),
        "sections": result.section_count(),
    }
    sys.stderr.write(json.dumps(counts) + "\n")
    sys.stderr.flush()


@main.command()
@click.argument("source_file", type=click.Path(exists=True, path_type=Path))
def detect_format(source_file: Path) -> None:
    """
    Detect the format of a source file. Writes format string to stdout.
    Output: one of 'txt', 'pdf', 'epub'.
    """
    from palimpsest.ingest.extractor import detect_format as do_detect
    fmt = do_detect(source_file)
    print(fmt.value)
```

### Rust: `core/src/project/manager.rs` (project creation)

The Rust `ProjectManager` handles directory creation and orchestrates Python subprocess calls:

```rust
//! ProjectManager: Creates and manages Palimpsest project directories.
//!
//! Responsibilities:
//! - Creates project directory structure
//! - Spawns Python subprocess: `palimpsest-extract normalize <file>`
//! - Writes reference.txt + verifies SHA-256
//! - Spawns Python subprocess: `palimpsest-extract segment <reference.txt> <urn>`
//! - Loads segment JSONL into arena
//! - Writes metadata.json

use std::path::{Path, PathBuf};
use std::process::Command;
use anyhow::{Context, Result, bail};
use crate::annotation::{AnnotationArena, load_jsonl_into_arena, track_name_to_id};

/// Subdirectories created for each project (§2.6).
const PROJECT_SUBDIRS: &[&str] = &[
    "tracks", "signals", "manifests", "cache",
    "x-config/schemas", "x-config/detectors",
    "exports/w3c", "exports/paf", "exports/csv",
];

pub struct ProjectManager {
    /// Path to `palimpsest-extract` Python CLI binary (inside .venv).
    python_extract_bin: PathBuf,
}

impl ProjectManager {
    pub fn new(python_extract_bin: PathBuf) -> Self {
        Self { python_extract_bin }
    }

    /// Ingest a source file into a new project directory.
    ///
    /// Returns: path to the created project directory.
    pub fn ingest(
        &self,
        source_path: &Path,
        workspace_dir: &Path,
        slug: &str,
    ) -> Result<PathBuf> {
        let project_dir = workspace_dir.join(slug);
        if project_dir.exists() {
            bail!("Project directory already exists: {}", project_dir.display());
        }

        // Step 1: Create directory structure
        std::fs::create_dir_all(&project_dir)?;
        for subdir in PROJECT_SUBDIRS {
            std::fs::create_dir_all(project_dir.join(subdir))?;
        }

        // Step 2: Normalize source file via Python subprocess
        let (normalized_text, sha256) = self.normalize_source(source_path)?;

        // Step 3: Write reference.txt
        let reference_path = project_dir.join("reference.txt");
        std::fs::write(&reference_path, normalized_text.as_bytes())?;

        // Step 4: Write reference.sha256 sidecar
        std::fs::write(project_dir.join("reference.sha256"), format!("{sha256}\n"))?;

        // Step 5: Segment via Python subprocess → JSONL
        let source_urn = format!("urn:palimpsest:{slug}");
        let (segment_jsonl, counts) = self.segment_text(&reference_path, &source_urn)?;

        // Step 6: Write segments.jsonl
        let segments_path = project_dir.join("tracks/segments.jsonl");
        std::fs::write(&segments_path, &segment_jsonl)?;

        // Step 7: Load segments into arena (validates JSONL format)
        let mut arena = AnnotationArena::new();
        let segment_count = load_jsonl_into_arena(&segments_path, track_name_to_id("segments"), &mut arena)?;
        tracing::info!("Loaded {segment_count} segment annotations");

        Ok(project_dir)
    }

    /// Spawn `palimpsest-extract normalize <file>` and return (text, sha256).
    fn normalize_source(&self, source_path: &Path) -> Result<(String, String)> {
        let output = Command::new(&self.python_extract_bin)
            .args(["normalize", &source_path.to_string_lossy()])
            .output()
            .context("Failed to spawn palimpsest-extract normalize")?;

        if !output.status.success() {
            bail!("normalize subprocess failed: {}", String::from_utf8_lossy(&output.stderr));
        }

        let normalized = String::from_utf8(output.stdout)
            .context("normalize output is not valid UTF-8")?;

        // Extract SHA-256 from stderr line "SHA256:<hex>"
        let stderr = String::from_utf8_lossy(&output.stderr);
        let sha256 = stderr
            .lines()
            .find(|l| l.starts_with("SHA256:"))
            .map(|l| l.trim_start_matches("SHA256:").to_string())
            .context("normalize subprocess did not output SHA256")?;

        // Verify SHA-256 matches (defense-in-depth)
        let computed = sha256_of_str(&normalized);
        if computed != sha256 {
            bail!("SHA-256 mismatch: Python reported {sha256}, Rust computed {computed}");
        }

        Ok((normalized, sha256))
    }

    /// Spawn `palimpsest-extract segment <reference.txt> <urn>` and return JSONL bytes + counts.
    fn segment_text(&self, reference_path: &Path, source_urn: &str) -> Result<(Vec<u8>, serde_json::Value)> {
        let output = Command::new(&self.python_extract_bin)
            .args(["segment", &reference_path.to_string_lossy(), source_urn])
            .output()
            .context("Failed to spawn palimpsest-extract segment")?;

        if !output.status.success() {
            bail!("segment subprocess failed: {}", String::from_utf8_lossy(&output.stderr));
        }

        let stderr = String::from_utf8_lossy(&output.stderr);
        let counts: serde_json::Value = stderr
            .lines()
            .find_map(|l| serde_json::from_str(l).ok())
            .unwrap_or(serde_json::json!({}));

        Ok((output.stdout, counts))
    }
}

fn sha256_of_str(s: &str) -> String {
    use std::fmt::Write;
    // SHA-256 without external dependency (use std or ring)
    // For brevity, using a placeholder — replace with actual SHA-256 impl
    // In practice: use ring::digest or sha2 crate
    format!("{:x}", sha2_hash(s.as_bytes()))
}
```

### Tests

**`python/tests/test_ingest.py`** — all v3.0 tests preserved. Two new tests added:

```python
def test_split_paragraphs_linear_scan_correctness() -> None:
    """_split_paragraphs linear scan produces same results as naive method."""
    from palimpsest.ingest.segmenter import _split_paragraphs

    # Text with repeated substrings that would be slow with str.index()
    text = "hello world\n\nhello world\n\nhello world\n"
    result = _split_paragraphs(text)
    assert len(result) == 3
    # All offsets should be in increasing order
    for i in range(len(result) - 1):
        assert result[i][2] <= result[i + 1][1], "Paragraphs must not overlap"


def test_normalize_performance_benchmark(pp_full_txt: Path, benchmark) -> None:
    """normalize() must complete full novel in < 500ms. Requires pytest-benchmark."""
    from palimpsest.ingest.normalizer import normalize
    text = pp_full_txt.read_text(encoding="utf-8")
    # Benchmark: average of multiple runs
    result = benchmark(normalize, text)
    # Assert correctness too
    assert result.endswith("\n")
    assert "It is a truth universally acknowledged" in result
```

Note: `test_normalize_performance_benchmark` requires `pytest-benchmark` and `pp_full_txt` fixture (added to conftest in T02). This test is marked `slow` and skipped in CI unless explicitly enabled.

**Performance targets:**
- `normalize(700KB novel)` → < 500ms (Python)
- `_split_paragraphs(700KB novel)` → < 200ms (Python)
- `palimpsest-extract normalize` subprocess call → < 5s total (including Python startup)
- `palimpsest-extract segment` subprocess call → < 30s (spaCy model load + processing)
- Rust `normalize_source()` round-trip → dominated by Python startup, acceptable

## Acceptance Criteria

- `pytest python/tests/test_ingest.py` passes all tests (v3.0 + 2 new)
- `mypy --strict python/palimpsest/ingest/` exits 0
- `palimpsest-extract normalize fixtures/pride-prejudice-ch1.txt` outputs normalized text to stdout and SHA-256 to stderr
- `palimpsest-extract segment reference.txt urn:palimpsest:test` outputs valid W3C JSONL (one line per annotation, each parseable as JSON)
- `_split_paragraphs` produces non-overlapping paragraph tuples with correct offsets
- `normalize()` is idempotent on P&P Chapter 1 text
- TXT and PDF of same chapter produce identical SHA-256 after normalization
- All segment annotations have `palimpsest:evidenceLevel: "E1"` and `palimpsest:confidence: 1.0`
- Rust `load_jsonl_into_arena` successfully loads segment JSONL produced by Python `palimpsest-extract segment`

## Design Decisions

- **Python for format extraction, Rust for project management**: This is the v4.0 boundary. Python knows about PDF, EPUB, spaCy — Rust knows about files, arenas, and speed. The boundary at stdout/file prevents tight coupling.

- **SHA-256 verified twice**: Python computes it, writes to stderr; Rust recomputes from the written file and compares. This catches bugs where the file write is incomplete or corrupted. Defense-in-depth costs < 5ms.

- **`segment` writes to stdout, not a file**: The Rust manager can pipe stdout directly to `tracks/segments.jsonl` without a temp file. For very large texts, this reduces disk I/O by avoiding a double-write.

---

## Original Content (v3.0, preserved for reference)

The original T05 specified `ingest/extractor.py`, `ingest/normalizer.py`, and `ingest/segmenter.py` as a Python-only pipeline called from `ingest_file()`. In v4.0, the same Python modules exist with the same logic but are wrapped in `cli_extract.py` for subprocess invocation by the Rust `ProjectManager`. The `_split_paragraphs()` function is fixed from O(n²) to O(n). All other code is preserved.
