# Palimpsest Performance Architecture (v4.0)

**Date**: 2026-06-07
**Supersedes**: Phase 1 plan v3.0 (doc 14) browser/rendering/server architecture sections
**Motivation**: M1.2 browser is unresponsive with 18,760 annotations on full novel (130K words). Current React+Python stack has fundamental performance ceilings that prevent the platform's multi-document comparative analysis goals.
**Hardware target**: M4 Max Mac Studio, 128GB unified RAM, 16 cores (12P+4E), 40 GPU cores, 273 GB/s memory bandwidth
**Status**: DEFERRED — Tauri/Rust/WebGPU architecture deferred to M6.1 (Roadmap v4.0, doc 28). Current production stack is Python+React with virtual scrolling and canvas rendering. The performance optimizations described here (Rust pipeline, WebGPU rendering, data tiling) remain valid targets for M6.1. The Rust crate scaffolding from M1.3b has been retained but is not actively used.

---

## 1. Performance Diagnosis

### Current Architecture Failures

| Problem | Impact | Root Cause |
|---------|--------|-----------|
| 18,760 annotation objects in JS heap | ~50-75MB memory per novel | JSON.parse creates individual objects with W3C metadata overhead |
| O(paragraphs × annotations) per render | 48M comparisons, >16ms frame budget blown | `collectVisibleAnnotations` concatenates all tracks, passed to every paragraph |
| 2,569 paragraph DOM nodes | 50,000+ total DOM elements with highlight spans | No virtualization — full document rendered |
| 18,760 SVG `<line>` elements in OverviewBar | SVG layout engine overwhelmed | Individual DOM element per annotation tick |
| Python FastAPI HTTP boundary | 12MB JSON serialized, transferred, parsed per project load | Frontend fetches annotation files over HTTP |
| Full re-render on track toggle | Entire component tree invalidated | Zustand state change propagates to all subscribers |

### Scale Requirements (Phase 2-3 vision)

- 5-10 novels loaded simultaneously (500K+ words each)
- 100K+ annotations visible across multiple views
- Side-by-side synoptic comparison with scroll-locked alignment
- Real-time consensus text generation
- Background NLP pipelines writing results that appear live in UI
- Interactive filtering at 60fps (confidence sliders, entity type chips, temporal ranges)

---

## 2. Architecture Decision: Tauri 2.0 + Rust Core + WebGPU

### Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Application shell | Tauri 2.0 (macOS WKWebView) | Native compositor, 50MB overhead (vs Electron's 200MB), in-process Rust |
| Data engine | Rust (tokio async runtime) | Arena allocation, SIMD filtering, interval tree queries, zero-copy IPC |
| Frontend framework | React 19 + TypeScript | Preserved from current — component structure is sound, data flow changes |
| State management | Zustand (thinned) | Stores hold only UI state; annotation data lives in Rust |
| Visualizations | WebGPU (via wgpu + web canvas) | GPU compute shaders for density, heatmaps, alignment matrices |
| Text rendering | Virtual scroll + Canvas overlay | 30-50 visible paragraphs, annotation highlights as Canvas layers |
| NLP pipeline | Python subprocess (managed by Rust) | spaCy, VADER, scikit-learn, BookNLP — no rewrite needed |
| Storage | Filesystem + mmap signals | W3C JSONL preserved, binary signals memory-mapped directly |

### Why Tauri+Rust Wins

| Alternative | Fatal Flaw |
|-------------|-----------|
| Native Swift/Metal | 4-6 month rewrite, kills cross-platform, TextKit 2 complexity for annotation overlays |
| Electron + Rust (napi-rs) | 200MB Chromium overhead, IPC serialization boundary, V8 heap still holds annotations |
| WebGPU-only browser fix | No shared memory, no mmap, Python IPC remains, scales to ~3 novels max |
| React virtualization only | Fixes 80% of symptoms but hits ceiling at 3-5 novels due to V8 heap pressure |

---

## 3. Core Data Structures (Rust)

### PackedAnnotation (16 bytes)

```rust
#[repr(C, packed)]
struct PackedAnnotation {
    start: u32,          // character offset (supports texts up to 4GB)
    end: u32,            // character offset
    confidence: u16,     // fixed-point 0.0000-1.0000 (divide by 10000)
    track_id: u8,        // up to 256 tracks
    evidence_level: u8,  // E1-E5 encoded as 1-5
    body_offset: u32,    // offset into body arena for variable-length data
}
```

**Memory comparison:**
- Current (JS objects): 18,760 annotations × ~3,500 bytes = **65MB**
- Packed (Rust arena): 18,760 annotations × 16 bytes = **300KB** (217x reduction)
- Five simultaneous novels: **1.5MB** instead of 325MB

### RangeIndex (Augmented Interval Tree)

```rust
struct RangeIndex {
    tree: IntervalTree<u32, u32>,  // maps [start, end] → annotation index
}

impl RangeIndex {
    /// Returns indices of annotations overlapping [query_start, query_end]
    /// O(log n + k) where k = results count
    fn query(&self, start: u32, end: u32) -> Vec<u32>;
}
```

A viewport showing 30 paragraphs (~7000 characters) queries the interval tree and gets back 100-300 annotation indices instead of scanning all 18,760.

### FilterEngine (SIMD)

```rust
impl FilterEngine {
    /// Apply visibility mask + confidence threshold in a single NEON pass
    /// Processes 16 annotations per cycle on M4 Max
    fn filter(
        &self,
        annotations: &[PackedAnnotation],
        track_mask: u64,          // bitfield: which tracks are visible
        min_confidence: u16,      // threshold (fixed-point)
    ) -> BitVec;                  // result: which annotations pass
}
```

Filtering 18,760 annotations: 18,760 / 16 = 1,173 SIMD iterations × ~1ns each = **~1.2 microseconds**. Compare to current: 48 million JS comparisons at ~100ns each = **4.8 seconds**.

### DensityHistogram

```rust
struct DensityHistogram {
    bins: Vec<f32>,      // counts per bin (typically 2000 bins)
    bin_width: u32,      // characters per bin
    doc_length: u32,
}
```

Pre-computed by Rust on filter change. Uploaded to GPU as a Float32 buffer. WebGPU fragment shader renders as filled area chart in a single draw call.

---

## 4. Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Tauri 2.0 Shell                              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  React Frontend (WKWebView)                                   │   │
│  │                                                               │   │
│  │  ┌─────────────┐  ┌────────────────┐  ┌──────────────────┐  │   │
│  │  │ VirtualText  │  │ WebGPU Canvas  │  │  DetailPanel     │  │   │
│  │  │ View         │  │ (density/heat/ │  │  (annotation     │  │   │
│  │  │ (30 paras)   │  │  alignment)    │  │   inspector)     │  │   │
│  │  └──────┬───────┘  └───────┬────────┘  └──────────────────┘  │   │
│  │         │ query_viewport()  │ get_histogram()                  │   │
│  │         └────────┬──────────┘                                  │   │
│  │                  │ Tauri invoke (zero-copy)                    │   │
│  └──────────────────┼────────────────────────────────────────────┘   │
│                     ▼                                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Rust Core Engine (in-process, async)                         │   │
│  │                                                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │ ProjectMgr   │  │ FilterEngine │  │ AlignmentEngine  │   │   │
│  │  │ (multi-doc)  │  │ (SIMD+NEON)  │  │ (Smith-Waterman) │   │   │
│  │  └──────┬───────┘  └──────────────┘  └──────────────────┘   │   │
│  │         │                                                     │   │
│  │  ┌──────┴───────┐  ┌──────────────┐  ┌──────────────────┐   │   │
│  │  │ AnnotStore   │  │ RangeIndex   │  │ SignalStore      │   │   │
│  │  │ (arena alloc)│  │ (interval    │  │ (mmap'd f32)    │   │   │
│  │  │              │  │  tree)        │  │                  │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘   │   │
│  │                                                               │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │  Pipeline Manager (tokio subprocess)                   │    │   │
│  │  │  → spawns Python for NLP, streams results to store    │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Data Flow (Critical Path: Track Toggle)

**Current (broken):**
1. User clicks track → Zustand `toggleTrack()` fires
2. React re-renders `TextLinearView` (subscribes to trackStore)
3. `collectVisibleAnnotations()` iterates all tracks, builds combined array
4. 2,569 `ParagraphView` components each receive full annotation array
5. Each `AnnotationOverlay` scans full array for its character range
6. Result: 48M comparisons, hundreds of ms, UI frozen

**New (Tauri+Rust):**
1. User clicks track → Zustand `toggleTrack()` fires
2. Track visibility bitmask updated → Tauri command: `update_filter({track_mask, confidence})`
3. Rust FilterEngine applies bitmask in ~1μs (SIMD pass over 300KB)
4. Rust updates RangeIndex active set
5. Frontend re-queries viewport: `query_viewport(scroll_start_char, scroll_end_char)`
6. Rust returns 100-300 annotation records for visible paragraphs only
7. React re-renders only the ~30 visible virtual paragraphs
8. Total time: **<2ms** (within 60fps budget of 16ms)

---

## 6. Frontend Rendering Strategy

### Virtual Text Scroller

- Renders only paragraphs in the visible viewport + overscan buffer (10 above, 10 below)
- Each paragraph's annotations are fetched via `query_viewport` — only the relevant ones
- Scroll events trigger async Tauri commands to fetch new annotation ranges
- Paragraph heights measured once on initial load, stored in a height cache

### Canvas Annotation Overlay

Instead of DOM `<span>` elements for highlights (which creates thousands of nodes):
- A `<canvas>` element overlays the text container
- Annotation highlight rectangles are drawn as colored rectangles at computed positions
- On scroll/resize: canvas repaints with requestAnimationFrame
- Click hit-testing done via character offset calculation from mouse position
- Result: 1 canvas element replaces 10,000+ span elements

### WebGPU Visualizations

- **OverviewBar**: Single compute shader generates density texture, rendered as 1 quad
- **Topic evolution**: Stacked area chart via vertex shader from topics_dist signal
- **Heatmap views**: 2D texture from Rust-computed matrix, rendered with color map shader
- **Alignment dotplot**: Compute shader generates similarity matrix, fragment shader renders

---

## 7. Python Integration Strategy

Python remains the NLP engine. The Rust core manages Python as a subprocess:

```rust
struct AnalysisPipeline {
    python_bin: PathBuf,     // .venv/bin/python
    active_jobs: Vec<AnalysisJob>,
}

impl AnalysisPipeline {
    /// Spawn analysis, stream results to AnnotationStore as they complete
    async fn run_analysis(&self, project: &Project, tracks: &[&str]) -> Result<()>;
}
```

- `palimpsest analyze` becomes a Rust binary that spawns Python per-extractor
- Each extractor writes JSONL to stdout; Rust ingests line-by-line into the arena
- Progress events forwarded to frontend via Tauri event system
- If an extractor crashes, Rust catches it and continues (already implemented in Python CLI)

---

## 8. Migration Path

### Phase 0: Rust Core Library (Week 1-2)

Create `palimpsest-core` crate:
- `PackedAnnotation` struct + arena allocator
- JSONL parser (reads existing W3C JSONL into packed format)
- `RangeIndex` interval tree
- `FilterEngine` with ARM NEON SIMD
- `DensityHistogram` computation
- Unit tests against existing P&P annotation data
- **Preserves all existing files — pure addition**

### Phase 1: Tauri Shell + Data Bridge (Week 3)

- Scaffold Tauri 2.0 project wrapping existing React frontend
- Implement Tauri commands: `load_project`, `query_viewport`, `update_filter`, `get_histogram`
- React calls Tauri commands instead of HTTP fetch
- Immediate performance gain: annotations never enter JS heap

### Phase 2: Virtual Scroller + Canvas Overlay (Week 4)

- Replace `TextLinearView` with virtualized scroll component
- Replace `AnnotationOverlay` DOM spans with Canvas layer
- 50 DOM nodes instead of 50,000+
- **This is where the UI becomes instant**

### Phase 3: WebGPU Visualizations (Week 5-6)

- GPU-rendered OverviewBar (density compute shader)
- Topic stacked area chart
- Sentiment heatmap
- Interactive confidence threshold with instant visual feedback

### Phase 4: Multi-Document + Alignment (Week 7-8)

- Multi-project loading in Rust core
- Synoptic split-view
- Smith-Waterman alignment engine
- Scroll-locked synchronized navigation

### Phase 5: Polish + Pipeline Integration (Week 9-10)

- Rust manages Python subprocess lifecycle
- Streaming ingestion of analysis results (live annotation appearance)
- Export from Rust (faster than Python for CSV generation)
- Final performance profiling and optimization

---

## 9. What Is Preserved vs. Rewritten

### Preserved (zero changes)

- W3C Web Annotation data model and JSONL storage format
- All 5 track extractors (Python: entities, sentiment, lexical, dialogue, topics)
- Project directory structure (reference.txt, tracks/, signals/, manifests/)
- TrackExtractor protocol and TrackRegistry
- Signal binary format (Float32 + manifest JSON)
- CLI subcommands (ingest, analyze, export, info)
- Test fixtures (Pride & Prejudice, Moby-Dick)

### Preserved with adaptation

- React components (same visual structure, different data flow)
- Zustand stores (thinned — hold UI state only, not annotation data)
- TrackManifest format (loaded by Rust, passed to frontend)
- conftest.py and test assertions (Python tests still validate extractors)

### Rewritten in Rust

- Data loading (JSONL → arena, not JSON.parse)
- Annotation filtering (SIMD, not JS array.filter)
- Density computation (pre-computed histogram, not per-element SVG)
- Server (eliminated for local; Tauri commands replace HTTP)
- Range queries (interval tree, not O(n) scan)

### New components (Rust + TypeScript)

- `palimpsest-core` Rust crate (core data engine)
- Tauri application shell
- VirtualTextView (windowed scroll)
- CanvasAnnotationOverlay (replaces DOM spans)
- WebGPU render pipeline (density, heatmaps, alignment)
- AlignmentEngine (Smith-Waterman)
- Multi-document ProjectManager

---

## 10. Performance Targets

| Operation | Current | Target | Technique |
|-----------|---------|--------|-----------|
| Project load (full novel) | 3-5s (HTTP + JSON.parse) | <100ms (Rust arena load) | Memory-mapped JSONL parse |
| Track toggle | 500ms+ (full re-render) | <2ms (SIMD filter + range query) | Packed structs + interval tree |
| Scroll (new viewport) | 200ms+ (DOM reflow) | <5ms (virtual scroll + canvas) | 30 paragraphs + canvas overlay |
| Search (Ctrl+F) | 100ms (string scan) | <10ms (Rust regex + index) | Pre-built suffix array |
| OverviewBar render | 300ms (18K SVG lines) | <1ms (GPU compute shader) | WebGPU density texture |
| Filter by confidence | 500ms+ (re-render) | <50μs (SIMD bitmask) | ARM NEON vectorized |
| Load 5 novels simultaneously | Impossible (OOM) | <500ms total | 1.5MB packed per novel |
| Alignment dotplot (500K×500K) | N/A | <100ms (GPU) | Compute shader |

---

## 11. Visual Design Principles

- **Scientific aesthetic**: Dark header, light reading area, high-contrast annotation colors
- **Transparency**: All settings exposed (confidence thresholds, pattern options, model parameters)
- **Information density**: Dense but readable — inspired by genome browsers and scientific dashboards
- **Responsive controls**: Every slider/toggle provides instant visual feedback (<16ms)
- **Multi-panel**: Resizable panels (drag handles), dockable views, saveable layouts
- **Typography**: Serif for literary text (Georgia/Crimson Pro), monospace for data, sans-serif for UI chrome

---

## 12. Dependency Summary

### Rust (palimpsest-core)

```toml
[dependencies]
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
memmap2 = "0.9"             # mmap for signal files
intervaltree = "0.2"        # interval tree for range queries
tauri = "2"
bitvec = "1"                # compact filter results
rayon = "1"                 # parallel iteration for batch ops
wgpu = "0.20"               # WebGPU compute (optional, for server-side pre-computation)
```

### Frontend (existing + additions)

```json
{
  "dependencies": {
    "react": "^19",
    "react-dom": "^19",
    "zustand": "^4",
    "@aspect-build/react-virtualized": "^1",
    "@tauri-apps/api": "^2"
  }
}
```

### Python (unchanged)

Existing requirements.txt — spaCy, VADER, scikit-learn, click, FastAPI (optional remote mode).
