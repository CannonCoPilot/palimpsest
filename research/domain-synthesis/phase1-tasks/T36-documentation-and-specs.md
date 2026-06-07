# T36: Final Documentation + Specs

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours
**Dependencies**: All T01-T35 tasks complete
**Outputs**: `specs/annotation-model.md`, `specs/LFO.md`, `specs/signals.md`, `specs/PAF-export.md`, `README.md`, `docs/architecture/ADR-002` through `ADR-006`

---

## v4.0 Critical Review

**Verdict: The documentation scope from v3.x is correct but incomplete for the v4.0 architecture. An entire class of documentation is missing: the Rust core API, the Tauri command interface, the WebGPU shader architecture, and the performance model. A contributor reading only the v3.x specs would have no idea how the application actually works — they would not know that annotations live in a packed 16-byte Rust struct, that viewport queries use an interval tree, or that all density visualizations are GPU fragment shaders. The documentation must cover the full v4.0 architecture.**

### What Is Missing

**No Rust API documentation.** The `palimpsest-core` crate is the performance-critical heart of the system. It has no documented API. Public Rust structs, traits, and `#[tauri::command]` handlers must have `///` doc comments generated into `cargo doc` HTML.

**No Tauri command reference.** The TypeScript frontend calls ~15 Tauri commands. There is no document listing these commands, their parameters, return types, and error conditions. This is the primary integration surface between Rust and TypeScript; it must be specified.

**No WebGPU shader documentation.** Four WGSL shaders are written (dotplot, overviewbar, density_zoom, signal_charts, alphabet_barcode). Their uniform interfaces, binding layouts, and coordinate systems must be documented for any future shader work.

**No performance model documentation.** The v4.0 design makes specific performance claims (48M → 1.2μs filter, <1ms GPU render, <5ms viewport query). These claims are based on architectural choices (PackedAnnotation 16 bytes, SIMD NEON, interval tree). A document explaining why these numbers are achievable — and what would cause them to regress — is essential for maintaining the architecture.

**ADR-001 through ADR-004 are v3.x decisions.** ADR-001 (W3C annotations) and ADR-002 (TrackRegistry) are unchanged. ADR-003 (signal format) is unchanged. ADR-004 (state management: "Zustand, defer MST") must be updated: in v4.0, Zustand holds only UI state — annotation data is not in Zustand at all, it lives in Rust. A new ADR is needed for the core architectural decisions.

---

## v4.0 Rewrite

### Architecture Documentation Additions

These documents are required in addition to the v3.x spec set:

**`docs/architecture/ADR-005-rust-core-architecture.md`**

Title: "ADR-005: Rust Core Engine + Tauri IPC Replaces Python FastAPI Server"

Status: Accepted (supersedes server architecture in doc 10-14)

Context: M1.2 browser unresponsive with 18,760 annotations. Python FastAPI HTTP boundary creates 12MB JSON transfer per project load. V8 heap holds all annotations.

Decision: `palimpsest-core` Rust crate with PackedAnnotation (16 bytes), arena allocation, interval tree RangeIndex, SIMD FilterEngine, and Tauri IPC. All annotation data stays in Rust heap. Frontend receives only viewport-visible annotation records per query.

Consequences: All annotation data access must go through `query_viewport` or `query_single_paragraph` Tauri commands. No annotation data in Zustand stores. Performance invariants: track toggle <2ms, scroll viewport <5ms, project load <100ms.

**`docs/architecture/ADR-006-webgpu-rendering.md`**

Title: "ADR-006: WebGPU Fragment Shaders for All Density and Heatmap Visualizations"

Status: Accepted (supersedes canvas/SVG rendering in T20, T27, T31-T33 v3.x specs)

Context: OverviewBar with 18,760 SVG lines causes layout engine collapse. Canvas `putImageData` loop for dotplot is CPU-bound software rendering. D3 SVG for signal charts creates hundreds of DOM elements.

Decision: All density and heatmap visualizations rendered via WebGPU fragment shaders. Data uploaded to GPU as `R32Float` textures or storage buffers. Fragment shaders apply color mapping, compositing, and interaction state (selection, brush) in a single pass.

Consequences: WebGPU must be available in the WKWebView. As of macOS 14+ with Tauri 2.0, WebGPU is available via the native Metal backend. Fallback to Canvas 2D is not implemented — WebGPU is a hard requirement of the v4.0 architecture.

**`docs/architecture/perf-model.md`**

Performance budget document:

```markdown
# Palimpsest v4.0 Performance Model

## Budget per 16ms Frame

Total: 16ms (60fps)
- Tauri IPC call (query_viewport): <5ms
- Rust interval tree + SIMD filter: <1ms
- JSON serialization of results: <1ms
- CanvasAnnotationOverlay repaint: <2ms
- React re-render (30 DOM nodes): <3ms
- GPU shader render: <1ms
- Remaining headroom: >3ms

## Critical Path: Track Toggle

1. User clicks track chip → Zustand toggleTrack() fires (synchronous)
2. trackMask updated → invoke('update_filter', {trackMask, minConfidence})
3. Rust FilterEngine.filter(): 18,760 annotations / 16 NEON lanes = ~1.2μs
4. Rust updates RangeIndex active set: O(1) bitmask update
5. Frontend re-queries viewport: invoke('query_viewport', {...})
6. Rust returns 100-300 ViewportAnnotation records: ~1ms
7. CanvasAnnotationOverlay.repaint(): ~2ms
8. Total: <5ms ✓ (within 16ms frame budget)

## Critical Path: Project Load

1. palimpsest-core reads JSONL files into packed arena: ~50ms (1.5MB, mmap)
2. RangeIndex build from interval tree: ~20ms (18,760 intervals)
3. EmbeddingStore open: ~10ms (sqlite WAL)
4. Signal files mmap: ~5ms each (4 signals × 5ms = 20ms)
5. Total: <100ms ✓

## Failure Modes (Must Not Happen)

- "annotation re-scan": query_viewport is the ONLY source of annotation data for the UI
- "full re-render on filter": track toggle must not re-render TextLinearView
- "JS heap annotations": annotation data must never be stored in Zustand or React state
- "GPU stall": WebGPU render passes must not block the main thread
```

### `specs/annotation-model.md` (Extended)

Add v4.0 section documenting the Rust `PackedAnnotation` struct alongside the W3C JSON-LD format:

```markdown
## 8. In-Memory Representation (v4.0)

At runtime, annotations from all JSONL files are loaded into the Rust AnnotStore as
packed 16-byte structs:

```rust
#[repr(C, packed)]
struct PackedAnnotation {
    start: u32,          // char offset (supports texts up to 4GB)
    end: u32,            // char offset
    confidence: u16,     // fixed-point / 10000 = float confidence
    track_id: u8,        // up to 256 tracks
    evidence_level: u8,  // E1=1 through E5=5
    body_offset: u32,    // offset into body arena for variable-length data
}
```

Memory comparison:
- JSONL (disk): ~3,500 bytes per annotation (JSON-LD overhead)
- PackedAnnotation (RAM): 16 bytes per annotation
- P&P 18,760 annotations: 300KB packed vs. 65MB JSON
- 5 novels simultaneously: 1.5MB packed vs. 325MB JSON

The body arena stores variable-length fields (entity name, speaker, topic ID etc.)
in a compact byte sequence, accessed via `body_offset`.

The JSONL files remain the authoritative source. The AnnotStore is rebuilt on each
`palimpsest analyze` run. The packed format is not persisted — it is constructed
from JSONL at project load time.
```

### `specs/signals.md` (Extended)

Add GPU loading section:

```markdown
## 8. GPU Loading (v4.0)

At project load, Rust uploads signal binary files to GPU textures via the following
Tauri commands:

| Signal | Tauri Command | GPU Format |
|--------|--------------|-----------|
| self_similarity.bin | load_self_similarity_texture | R32Float N×N texture |
| topics_dist.bin | get_topics_texture_handle | R32Float N×K texture |
| narrative_arc.bin | get_narrative_arc | Returned as 15-element JSON array (small) |
| rqa.bin | get_rqa_signal | Returned as W×3 JSON array (small) |
| alphabet.json | get_alphabet_sequence | Returned as Vec<u8> (letter indices) |

The self_similarity and topics_dist textures are uploaded once at project load and
reused across all renders. They never enter the JS heap.

Memory comparison for self_similarity:
- Browser JS ArrayBuffer (v3.x): 12.96MB in WKWebView V8 heap
- GPU texture (v4.0): 12.96MB in GPU VRAM (unified memory on M4 Max)
- JS heap overhead: 0 bytes (texture handle is a u32)
```

### README.md (v4.0 Updates)

The README must document the Tauri architecture in the Installation section:

```markdown
## Requirements

- macOS 14.0+ (WebGPU required via Metal backend)
- Rust 1.75+ with `cargo` and `cargo tauri`
- Python 3.12+
- Node.js 20+
- Ollama (optional, for semantic search and self-similarity)

## Installation

```bash
# Install the Tauri app
cargo install palimpsest

# Install Python extractors (NLP pipeline)
pip install palimpsest-python
python -m spacy download en_core_web_lg

# Optional: embedding model for semantic search
brew install ollama
ollama pull qwen3:8b
ollama pull qwen3-embedding
```

## Quick Start

```bash
palimpsest ingest pride-and-prejudice.txt
palimpsest analyze projects/pride-and-prejudice/
palimpsest open projects/pride-and-prejudice/
# Opens Tauri native app
```

## Architecture Overview

Palimpsest uses a Tauri 2.0 + Rust + WebGPU architecture:

- **Rust core** (`palimpsest-core`): loads annotations as 16-byte packed structs,
  provides interval tree range queries and SIMD filtering, manages GPU texture uploads
- **Python extractors**: spaCy, VADER, scikit-learn, BookNLP for NLP analysis
- **WebGPU frontend**: all density maps, heatmaps, and signal charts are GPU fragment shaders
- **Tauri IPC**: frontend queries Rust via `invoke()` — no HTTP server

Track toggle and scroll viewport queries complete in <2ms and <5ms respectively,
allowing 60fps interaction with full novels.
```

### `docs/architecture/tauri-commands.md`

Complete reference for all `#[tauri::command]` handlers:

```markdown
# Tauri Command Reference

All commands are invoked via `invoke(commandName, params)` in TypeScript.

## Project Management

### `load_workspace(workspacePath: string) → ProjectMeta[]`
Discovers and loads all projects in the given directory. Returns project metadata.

### `list_projects() → ProjectMeta[]`
Returns metadata for all currently loaded projects.

## Viewport Queries

### `query_viewport(projectId, startChar, endChar, trackMask, minConfidence) → ViewportAnnotation[]`
Returns filtered annotations in the given character range. <5ms. Primary data path.

### `query_single_paragraph(projectId, paragraphIndex) → AnnotationRecord[]`
Returns all annotations for one paragraph. O(log N + k). <1ms.

## Filter Management

### `update_filter(projectId, trackMask, minConfidence) → void`
Updates the active filter state in Rust. Triggers DensityHistogram recomputation.

### `get_density_histogram(projectId, trackMask, minConfidence) → DensityHistogramResponse`
Returns GPU texture handle for density data. <5ms.

## Signal Access

### `load_self_similarity_texture(projectId) → SimilarityTextureHandle`
Loads and uploads self_similarity.bin to GPU. Called once at project open.

### `get_narrative_arc(projectId) → NarrativeArcResponse`
Returns 5×3 float array. <1ms. Small payload.

### `get_rqa_signal(projectId) → RQAResponse`
Returns W×3 float array. <1ms.

### `get_alphabet_sequence(projectId) → AlphabetSequence`
Returns Vec<u8> letter indices. <1ms.

### `get_topics_texture_handle(projectId) → GPUTextureHandle`
Returns handle to already-uploaded topics GPU texture.

## Search

### `semantic_search(projectId, queryText, k) → SimilarityResult[]`
Embeds query via Ollama, queries sqlite-vec ANN. ~256ms total.

### `get_similarity_value(projectId, i, j) → number`
Returns single float from self_similarity.bin via mmap O(1). <1ms.

## Cross-Text

### `compute_cross_similarity(projectIdA, projectIdB) → CrossSimilarityResult`
Computes N×M similarity matrix via Rust SIMD. ~1.7s first time, <100ms cached.

## Export

### `export_project(projectId, format, tracks, outputDir) → ExportReport`
Exports annotations to W3C/PAF/CSV. <500ms for full novel.

## Navigation

### `notify_paragraph_selected(paragraphIndex) → void`
Informs Rust coordinator of selection change. No-op in Phase 1, used in Phase 2 synoptic view.
```

### Acceptance Criteria (v4.0)

- `specs/annotation-model.md` includes `PackedAnnotation` struct and memory comparison table
- `specs/signals.md` includes GPU loading section with texture format for each signal
- `README.md` documents Tauri architecture, macOS 14+ requirement, `cargo install` installation
- `docs/architecture/ADR-005-rust-core-architecture.md` is written and accepted
- `docs/architecture/ADR-006-webgpu-rendering.md` is written and accepted
- `docs/architecture/tauri-commands.md` documents all ~15 Tauri commands with types and latency
- `docs/architecture/perf-model.md` documents performance budgets and failure modes
- `cargo doc --no-deps` produces HTML docs for all public `palimpsest-core` types
- `KeyboardHelp.tsx` renders the `?` overlay; pressing `?` opens it
- All LFO types in JSONL output are listed in `specs/LFO.md`
- `tsc --strict` passes on `KeyboardHelp.tsx`

### Tests

The spec conformance test is extended to check v4.0 documentation:

```python
# core/tests/test_annotation.py

def test_all_tauri_commands_documented(docs_path: Path = Path("docs/architecture/tauri-commands.md")):
    """Every invoke() call in TypeScript source has a corresponding entry in tauri-commands.md."""
    import subprocess
    # Find all invoke() calls in browser/src
    result = subprocess.run(
        ["grep", "-r", "invoke('", "browser/src/", "--include=*.ts", "--include=*.tsx", "-h"],
        capture_output=True, text=True,
    )
    invoke_calls = set(
        line.split("invoke('")[1].split("'")[0]
        for line in result.stdout.splitlines()
        if "invoke('" in line
    )
    doc_text = docs_path.read_text()
    for cmd in invoke_calls:
        assert f"### `{cmd}(" in doc_text or f"### `{cmd}" in doc_text, \
            f"Tauri command '{cmd}' not documented in tauri-commands.md"
```

---

## Original Content (Reference)

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours

### Context (original)

T36 fills in the spec stubs created in T01 to form durable reference documents valid through Phase 2 and 3. Specs are normative references, not retrospective writeups.

### Deliverables (original)

- `specs/annotation-model.md` — normative W3C body types + evidence hierarchy
- `specs/LFO.md` — ~60 Literary Feature Ontology terms
- `specs/signals.md` — binary signal format specification
- `specs/PAF-export.md` — PAF export format specification
- `README.md` — installation, quick start, keyboard shortcuts
- `docs/architecture/ADR-002` through `ADR-004`

### Design Decisions (original)

- **Specs as normative, not descriptive**: Spec is the contract.
- **~60 LFO terms**: All Phase 1 terms + sketched Phase 2/3 stubs.
- **README at repo root**: Standard location.
- **Three ADRs in T36**: Document decisions made during implementation, not at planning time.
