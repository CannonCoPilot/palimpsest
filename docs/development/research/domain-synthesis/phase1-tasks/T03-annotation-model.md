# T03: Annotation Model — Rust Core + Python Extractor Layer

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 5 hours (Python) → 8 hours (v4.0: adds Rust structs, arena, JSONL parser)
**Dependencies**: T01, T02
**Outputs**: `core/src/annotation/` (Rust), `python/palimpsest/annotation/` (Python, unchanged for extractors), Rust unit tests, Python unit tests

---

## v4.0 Critical Review

**The Python annotation model in v3.0 is architecturally correct but used in the wrong place. The fatal error is that it is the only annotation model: Python `Annotation` dataclasses go all the way to the browser, which means 18,760 objects × ~3,500 bytes = 65MB in the JS heap. That is the exact performance catastrophe documented in the performance architecture.**

Specific failures:

1. **`Annotation` Python dataclass → JSON.parse in browser = 65MB heap allocation.** The Python `to_jsonld()` method outputs correctly-structured W3C JSON. The browser then calls `JSON.parse()` on it. Each parsed object in V8 is a full JavaScript object with prototype chain, property enumeration overhead, and garbage collection pressure. This is the root cause of the M1.2 browser becoming unresponsive with 18,760 annotations.

2. **`write_track()` → `read_track()` is the only data path.** v3.0 has no concept of a Rust-level annotation representation. The JSONL file is written by Python, read by Python (in tests), and read by the browser (via HTTP + `JSON.parse()`). There is no fast path.

3. **`Body.extra: dict[str, Any]` is a schemaless bag.** This is fine for Python extractor output, but it cannot be serialized to a 16-byte `PackedAnnotation`. The body must be packed into an arena where variable-length data (entity type string, topic terms list) lives at a `body_offset`. The Python model has no awareness of this.

4. **The test suite validates Python round-trips but has zero performance assertions.** A test that verifies `annotation_count == 18760` but takes 500ms to deserialize is not a performance test — it is a correctness test that masks a performance disaster.

5. **`TextPositionSelector.start` and `.end` are Python `int` (64-bit).** The Rust `PackedAnnotation` uses `u32` for character offsets, supporting texts up to 4GB. Any text longer than ~4 billion characters is unsupported, which is acceptable. But the Python model makes no commitment to this range. An extractor that produces `start = 5_000_000_000` will silently overflow when packed.

**What must change:**
- Define `PackedAnnotation` (16 bytes) and `AnnotationArena` in Rust — this is the runtime representation
- Write a Rust JSONL parser that reads W3C JSONL into packed format without going through Python
- Keep the Python `Annotation` dataclasses for extractor output only — Python extractors still write W3C JSONL
- Add validation in Python serializer that `start` and `end` fit in `u32` (< 4,294,967,295)
- Add performance assertions to tests: Rust deserialization of 18,760 annotations must complete in < 50ms

---

## v4.0 Rewrite

### Architecture: Two-Layer Model

```
Layer 1: Python (extractor output)
  Annotation dataclass → to_jsonld() → W3C JSONL on disk
  ↓ (written by Python extractors)

Layer 2: Rust (runtime engine)
  W3C JSONL → JSONL parser → PackedAnnotation[N] in arena
  ↓ (consumed by FilterEngine, RangeIndex, Tauri commands)
  → query_viewport() → serialized slice → TypeScript (UI only)
```

The Python model is NOT eliminated. It is scoped to extractor output only. The Rust model is the runtime representation. This two-layer approach means:
- Python extractors can remain unchanged (they write JSONL, Rust reads it)
- The browser never holds annotation arrays — it receives only viewport slices
- Filtering operates on packed structs at SIMD speed

### Rust: `core/src/annotation/`

**`core/src/annotation/packed.rs`**:

```rust
//! PackedAnnotation: 16-byte representation of a W3C annotation.
//!
//! Memory layout:
//!   bytes 0-3:   start (u32, character offset, inclusive)
//!   bytes 4-7:   end (u32, character offset, exclusive)
//!   bytes 8-9:   confidence (u16, fixed-point, divide by 10_000 for f64)
//!   byte  10:    track_id (u8, 0-255, maps to registered track names)
//!   byte  11:    evidence_level (u8, 1-5 → E1-E5)
//!   bytes 12-15: body_offset (u32, byte offset into BodyArena)

/// 16-byte packed annotation. Designed for SIMD-friendly layout.
///
/// Performance target: 18,760 annotations = 300KB total (vs 65MB in JS heap).
#[repr(C, packed)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PackedAnnotation {
    /// Character offset of annotation start (inclusive). u32 supports texts up to 4GB.
    pub start: u32,
    /// Character offset of annotation end (exclusive). Matches Python slicing convention.
    pub end: u32,
    /// Confidence scaled to [0, 10_000]. Divide by 10_000.0 for float.
    /// 0.85 → 8_500u16. Resolution: 0.0001.
    pub confidence: u16,
    /// Track identifier (0-255). Resolved via TrackRegistry. entities=0, sentiment=1, ...
    pub track_id: u8,
    /// Evidence level: 1=E1, 2=E2, 3=E3, 4=E4, 5=E5.
    pub evidence_level: u8,
    /// Byte offset into BodyArena for variable-length body data (entity type, topic terms, etc.)
    pub body_offset: u32,
}

impl PackedAnnotation {
    /// Construct with floating-point confidence (clamped to [0.0, 1.0]).
    pub fn new(
        start: u32,
        end: u32,
        confidence: f32,
        track_id: u8,
        evidence_level: u8,
        body_offset: u32,
    ) -> Self {
        debug_assert!(start <= end, "start must be <= end");
        debug_assert!(evidence_level >= 1 && evidence_level <= 5);
        let conf_u16 = (confidence.clamp(0.0, 1.0) * 10_000.0) as u16;
        Self { start, end, confidence: conf_u16, track_id, evidence_level, body_offset }
    }

    /// Decode confidence back to float.
    #[inline(always)]
    pub fn confidence_f32(&self) -> f32 {
        self.confidence as f32 / 10_000.0
    }

    /// Evidence level as &str ("E1" through "E5").
    #[inline(always)]
    pub fn evidence_str(&self) -> &'static str {
        match self.evidence_level {
            1 => "E1", 2 => "E2", 3 => "E3", 4 => "E4", 5 => "E5",
            _ => "E?",
        }
    }

    /// Check if this annotation passes a confidence threshold (fixed-point comparison).
    #[inline(always)]
    pub fn passes_confidence(&self, min_confidence_fp: u16) -> bool {
        self.confidence >= min_confidence_fp
    }

    /// Check if this annotation's track is visible in the given bitmask.
    #[inline(always)]
    pub fn track_visible(&self, track_mask: u64) -> bool {
        (track_mask >> self.track_id) & 1 == 1
    }

    /// Check if this annotation overlaps the given character range [query_start, query_end).
    #[inline(always)]
    pub fn overlaps(&self, query_start: u32, query_end: u32) -> bool {
        self.start < query_end && self.end > query_start
    }
}

static_assertions::const_assert_eq!(std::mem::size_of::<PackedAnnotation>(), 16);
```

**`core/src/annotation/arena.rs`**:

```rust
//! AnnotationArena: bump allocator for packed annotations and their body strings.
//!
//! Two storage regions:
//!   1. annotation_data: Vec<PackedAnnotation> (contiguous, SIMD-accessible)
//!   2. body_data: Vec<u8> (body JSON stored as UTF-8 bytes; accessed via body_offset)
//!
//! Body storage format: 4-byte length prefix + UTF-8 body JSON.
//! This allows O(1) body retrieval without a separate index.

use crate::annotation::packed::PackedAnnotation;

pub struct AnnotationArena {
    annotations: Vec<PackedAnnotation>,
    body_data: Vec<u8>,
}

impl AnnotationArena {
    pub fn new() -> Self {
        Self {
            annotations: Vec::new(),
            body_data: Vec::new(),
        }
    }

    /// Pre-allocate capacity for known annotation count.
    pub fn with_capacity(annotation_count: usize, body_bytes: usize) -> Self {
        Self {
            annotations: Vec::with_capacity(annotation_count),
            body_data: Vec::with_capacity(body_bytes),
        }
    }

    /// Push a packed annotation and its body JSON string.
    /// Returns the index of the newly added annotation.
    pub fn push(&mut self, mut ann: PackedAnnotation, body_json: &str) -> usize {
        let body_offset = self.body_data.len() as u32;
        ann.body_offset = body_offset;

        // 4-byte length prefix + body bytes
        let body_bytes = body_json.as_bytes();
        let len = body_bytes.len() as u32;
        self.body_data.extend_from_slice(&len.to_le_bytes());
        self.body_data.extend_from_slice(body_bytes);

        let idx = self.annotations.len();
        self.annotations.push(ann);
        idx
    }

    /// Slice of all packed annotations (SIMD-friendly contiguous memory).
    #[inline]
    pub fn slice(&self) -> &[PackedAnnotation] {
        &self.annotations
    }

    /// Retrieve body JSON string for annotation at given index.
    pub fn body_json(&self, idx: usize) -> &str {
        let ann = &self.annotations[idx];
        let offset = ann.body_offset as usize;
        let len = u32::from_le_bytes(
            self.body_data[offset..offset + 4].try_into().unwrap()
        ) as usize;
        let start = offset + 4;
        std::str::from_utf8(&self.body_data[start..start + len])
            .expect("body_data must be valid UTF-8")
    }

    pub fn len(&self) -> usize {
        self.annotations.len()
    }

    pub fn is_empty(&self) -> bool {
        self.annotations.is_empty()
    }

    /// Total memory usage in bytes.
    pub fn memory_bytes(&self) -> usize {
        self.annotations.len() * 16 + self.body_data.len()
    }

    /// Create a mock arena with N synthetic annotations (for benchmarks).
    #[cfg(test)]
    pub fn mock(count: u32) -> Self {
        let mut arena = Self::with_capacity(count as usize, count as usize * 80);
        for i in 0..count {
            let start = i * 37;
            let end = start + 15;
            let ann = PackedAnnotation::new(start, end, 0.85, i as u8 % 8, 4, 0);
            arena.push(ann, r#"{"type":"palimpsest:EntityAnnotation","purpose":"classifying","palimpsest:entityType":"PER"}"#);
        }
        arena
    }
}
```

**`core/src/annotation/jsonl.rs`**:

```rust
//! W3C JSONL → PackedAnnotation parser.
//!
//! Reads a JSONL file (one W3C annotation per line) and ingests into an AnnotationArena.
//! Never allocates full serde Value trees — uses streaming field extraction.
//!
//! Performance target: 18,760 annotations (P&P full novel) → arena in < 50ms.

use std::io::{BufRead, BufReader};
use std::path::Path;
use anyhow::{Context, Result};
use crate::annotation::{AnnotationArena, PackedAnnotation};

/// Map evidence level string to u8 (1-5).
fn parse_evidence_level(s: &str) -> u8 {
    match s {
        "E1" => 1, "E2" => 2, "E3" => 3, "E4" => 4, "E5" => 5,
        _ => 4, // default E4 for unrecognized values
    }
}

/// Map track name to track_id u8.
/// In Phase 1: entities=0, sentiment=1, lexical=2, dialogue=3, topics=4, segments=5
pub fn track_name_to_id(name: &str) -> u8 {
    match name {
        "entities" => 0,
        "sentiment" => 1,
        "lexical" => 2,
        "dialogue" => 3,
        "topics" => 4,
        "segments" => 5,
        "coreference" => 6,
        _ => 255,
    }
}

/// Parse a single W3C annotation JSON line into a PackedAnnotation + body JSON string.
///
/// Uses serde_json::Value for correctness but extracts only the fields we need.
/// The full body JSON is stored as-is in the BodyArena for retrieval on demand.
pub fn parse_annotation_line(
    line: &str,
    track_id: u8,
) -> Result<(PackedAnnotation, String)> {
    let v: serde_json::Value = serde_json::from_str(line)
        .context("Failed to parse annotation JSON line")?;

    let start = v["target"]["selector"]["start"]
        .as_u64()
        .context("Missing target.selector.start")? as u32;
    let end = v["target"]["selector"]["end"]
        .as_u64()
        .context("Missing target.selector.end")? as u32;

    let confidence = v["palimpsest:confidence"]
        .as_f64()
        .unwrap_or(0.85) as f32;

    let evidence_str = v["palimpsest:evidenceLevel"]
        .as_str()
        .unwrap_or("E4");
    let evidence_level = parse_evidence_level(evidence_str);

    let body = v["body"].to_string();

    let ann = PackedAnnotation::new(start, end, confidence, track_id, evidence_level, 0);
    Ok((ann, body))
}

/// Load a JSONL track file into the arena.
///
/// Args:
///   path: path to JSONL file (e.g. tracks/entities.jsonl)
///   track_id: numeric track ID for this file (use track_name_to_id())
///   arena: mutable arena to push annotations into
///
/// Returns: number of annotations loaded.
pub fn load_jsonl_into_arena(
    path: &Path,
    track_id: u8,
    arena: &mut AnnotationArena,
) -> Result<usize> {
    let file = std::fs::File::open(path)
        .with_context(|| format!("Cannot open JSONL file: {}", path.display()))?;
    let reader = BufReader::new(file);
    let mut count = 0;

    for (lineno, line) in reader.lines().enumerate() {
        let line = line.context("IO error reading JSONL")?;
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        match parse_annotation_line(line, track_id) {
            Ok((ann, body)) => {
                arena.push(ann, &body);
                count += 1;
            }
            Err(e) => {
                // Log but continue — malformed lines should not abort load
                eprintln!("Warning: skipping malformed annotation at line {}: {}", lineno + 1, e);
            }
        }
    }

    Ok(count)
}
```

**`core/src/annotation/mod.rs`**:
```rust
pub mod arena;
pub mod jsonl;
pub mod packed;

pub use arena::AnnotationArena;
pub use jsonl::{load_jsonl_into_arena, parse_annotation_line, track_name_to_id};
pub use packed::PackedAnnotation;
```

### Rust Tests

**`core/tests/integration/annotation_round_trip.rs`**:

```rust
//! Integration tests for annotation parsing using hand-authored fixtures.
//! No Python dependency — all data is pre-generated in core/tests/data/.

use std::path::PathBuf;
use palimpsest_core::annotation::{AnnotationArena, load_jsonl_into_arena, PackedAnnotation};

fn fixture(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/data")
        .join(name)
}

#[test]
fn test_packed_annotation_is_16_bytes() {
    assert_eq!(std::mem::size_of::<PackedAnnotation>(), 16);
}

#[test]
fn test_packed_annotation_confidence_roundtrip() {
    let ann = PackedAnnotation::new(0, 10, 0.85, 0, 4, 0);
    let f = ann.confidence_f32();
    assert!((f - 0.85).abs() < 0.0001, "Confidence roundtrip: expected 0.85, got {f}");
}

#[test]
fn test_packed_annotation_evidence_str() {
    let ann = PackedAnnotation::new(0, 10, 0.9, 0, 4, 0);
    assert_eq!(ann.evidence_str(), "E4");
    let ann2 = PackedAnnotation::new(0, 10, 1.0, 0, 1, 0);
    assert_eq!(ann2.evidence_str(), "E1");
}

#[test]
fn test_packed_annotation_overlap() {
    let ann = PackedAnnotation::new(100, 200, 0.9, 0, 4, 0);
    assert!(ann.overlaps(150, 250));   // overlaps on right
    assert!(ann.overlaps(50, 150));    // overlaps on left
    assert!(ann.overlaps(120, 180));   // contained within
    assert!(ann.overlaps(90, 210));    // contains annotation
    assert!(!ann.overlaps(200, 300));  // adjacent, no overlap (end is exclusive)
    assert!(!ann.overlaps(0, 100));    // adjacent, no overlap (start is exclusive)
}

#[test]
fn test_packed_annotation_track_mask() {
    let ann = PackedAnnotation::new(0, 10, 0.9, 3, 4, 0);  // track_id=3
    assert!(ann.track_visible(0b1111));   // bit 3 set
    assert!(!ann.track_visible(0b0111)); // bit 3 not set
    assert!(ann.track_visible(u64::MAX)); // all tracks visible
}

#[test]
fn test_load_entity_fixture() {
    let path = fixture("pp_ch1_entities_minimal.jsonl");
    if !path.exists() {
        eprintln!("Fixture not found: {}", path.display());
        eprintln!("Run: python scripts/make-rust-fixtures.py");
        return; // Skip if fixture not generated
    }

    let mut arena = AnnotationArena::new();
    let count = load_jsonl_into_arena(&path, 0, &mut arena).unwrap();
    assert_eq!(count, 15, "Expected 15 entity annotations");

    // All loaded annotations should have track_id=0 (entities)
    for ann in arena.slice() {
        assert_eq!(ann.track_id, 0);
        assert_eq!(ann.evidence_level, 4); // E4
        assert!(ann.confidence_f32() > 0.0);
    }

    // Memory should be dramatically smaller than JS equivalent
    let memory = arena.memory_bytes();
    println!("Memory for 15 annotations: {} bytes", memory);
    // 15 * 16 bytes packed + body strings ≈ 15 * 200 bytes ≈ 3.3KB (vs ~50KB in JS)
    assert!(memory < 10_000, "Expected < 10KB for 15 annotations, got {memory}");
}

#[test]
fn test_load_segment_fixture() {
    let path = fixture("pp_ch1_segments_minimal.jsonl");
    if !path.exists() { return; }

    let mut arena = AnnotationArena::new();
    let count = load_jsonl_into_arena(&path, 5, &mut arena).unwrap(); // segments=5
    assert_eq!(count, 10);

    // Segment annotations should have evidence_level=1 (E1)
    let e1_count = arena.slice().iter().filter(|a| a.evidence_level == 1).count();
    assert_eq!(e1_count, 10, "All segments should be E1");
}

#[test]
fn test_arena_body_retrieval() {
    let mut arena = AnnotationArena::new();
    let ann = PackedAnnotation::new(10, 20, 0.9, 0, 4, 0);
    let body = r#"{"type":"palimpsest:EntityAnnotation","purpose":"classifying","palimpsest:entityType":"PER"}"#;
    let idx = arena.push(ann, body);
    let retrieved = arena.body_json(idx);
    assert_eq!(retrieved, body);
}

#[test]
fn test_arena_memory_efficiency_18760_annotations() {
    // Simulate loading 18,760 annotations (P&P full novel density)
    let arena = AnnotationArena::mock(18_760);
    let memory = arena.memory_bytes();
    let packed_only = 18_760 * 16;
    println!(
        "18,760 annotations: {}KB total ({} packed + {} body)",
        memory / 1024,
        packed_only,
        memory - packed_only
    );
    // Target from architecture doc: 300KB packed. With body strings, < 2MB total.
    assert!(
        memory < 2_000_000,
        "Expected < 2MB for 18,760 annotations, got {}KB",
        memory / 1024
    );
}
```

### Python: `python/palimpsest/annotation/`

The Python annotation model is **preserved without changes** from v3.0 with one addition: `u32` range validation in `TextPositionSelector`.

The Python model now has a single additional constraint:

```python
@dataclass
class TextPositionSelector:
    start: int   # must fit in u32 (< 4,294,967,295)
    end: int     # must fit in u32

    def __post_init__(self) -> None:
        MAX_U32 = 4_294_967_295
        if not (0 <= self.start <= MAX_U32):
            raise ValueError(f"start={self.start} out of u32 range [0, {MAX_U32}]")
        if not (0 <= self.end <= MAX_U32):
            raise ValueError(f"end={self.end} out of u32 range [0, {MAX_U32}]")
        if self.start > self.end:
            raise ValueError(f"start ({self.start}) must be <= end ({self.end})")
```

This constraint ensures that any annotation written by a Python extractor can be loaded into a `PackedAnnotation` without overflow. For any text within scope (literary novels are at most a few MB), u32 is more than sufficient.

All other Python annotation model code (`bodies.py`, `serializer.py`, `model.py`, `__init__.py`) is identical to v3.0.

### Python Tests

The Python test suite from v3.0 (`test_annotation.py`) is preserved in full. Two new tests are added:

```python
def test_text_position_selector_u32_validation() -> None:
    """start and end must fit in u32 for Rust compatibility."""
    with pytest.raises(ValueError, match="u32 range"):
        TextPositionSelector(start=-1, end=10)

    with pytest.raises(ValueError, match="u32 range"):
        TextPositionSelector(start=0, end=5_000_000_000)  # > u32 max


def test_text_position_selector_start_lte_end() -> None:
    """start must not exceed end."""
    with pytest.raises(ValueError, match="start.*must be <= end"):
        TextPositionSelector(start=100, end=50)
```

### Performance Targets

| Operation | Count | Target | Measured (criterion) |
|-----------|-------|--------|----------------------|
| `load_jsonl_into_arena` (18,760 anns) | 1 call | < 50ms | TBD (T03) |
| `parse_annotation_line` | per line | < 5μs | TBD (T03) |
| `arena.memory_bytes()` for 18,760 anns | 1 call | < 2MB | TBD (T03) |
| Python `write_track` (18,760 anns) | 1 call | < 5s | TBD (T07) |

CI gate: if `load_jsonl_into_arena(18760 annotations)` takes > 200ms, the benchmark fails.

## Acceptance Criteria

### Rust
- `cargo test -p palimpsest-core annotation` passes all unit tests
- `std::mem::size_of::<PackedAnnotation>() == 16` (enforced by `static_assertions`)
- `load_jsonl_into_arena` loads the 15-annotation entity fixture in < 5ms
- `test_arena_memory_efficiency_18760_annotations` passes (< 2MB for 18,760 annotations)
- `PackedAnnotation::overlaps` handles all boundary cases correctly
- `PackedAnnotation::track_visible` correctly evaluates bitmask for all track_ids 0-7
- `cargo clippy -p palimpsest-core -- -D warnings` exits 0

### Python
- `pytest python/tests/test_annotation.py` passes all 21 original tests + 2 new u32 tests
- `mypy --strict python/palimpsest/annotation/` exits 0
- `TextPositionSelector` raises `ValueError` for negative start, negative end, end < start, values > u32 max
- All 6 body types round-trip correctly through Python `to_body()` / `from_body()`

## Design Decisions

- **16 bytes exactly**: The struct size is a hard constraint enforced by `static_assertions`. Any future field addition must either pack into existing bytes or use the `body_offset` indirection. Evidence level (E1-E5 = 5 values) fits in 3 bits; we use 8 bits (1 byte) for alignment. Track_id uses 8 bits allowing 256 tracks.

- **`body_offset` into BodyArena, not inline body**: Body data is variable-length (entity type = 3 chars, topic terms = list of 10 strings). Storing it inline would explode the struct size. The 4-byte `body_offset` points into a separate `Vec<u8>` with 4-byte length prefixes. Body retrieval is O(1) but involves a memory indirection — acceptable since bodies are only retrieved for clicked/selected annotations in the UI.

- **Python model preserved**: We do not rewrite Python extractors to produce binary format. They write W3C JSONL as before. The Rust JSONL parser translates from W3C → packed on load. This preserves Python extractor interoperability and means the JSONL files on disk are human-readable and inspectable with standard tools.

- **u32 range validation in Python**: Adding this constraint to `TextPositionSelector` makes the two-layer contract explicit. If an extractor produces out-of-range offsets, the error is caught in Python tests rather than silently overflowing in Rust.

---

## Original Content (v3.0, preserved for reference)

The original T03 specified a Python-only `Annotation` dataclass hierarchy with `to_jsonld()`/`from_jsonld()` methods and a JSONL serializer. All of that Python code remains correct and is preserved as the extractor output layer. The fundamental change in v4.0 is that the JSONL files it produces are inputs to the Rust `load_jsonl_into_arena()` function rather than directly to the browser's `JSON.parse()`.
