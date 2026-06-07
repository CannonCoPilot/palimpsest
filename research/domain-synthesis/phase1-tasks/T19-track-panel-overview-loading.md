# T19: TrackPanel + WebGPU OverviewBar + LoadingOverlay + Multi-Track Canvas Rendering

**Milestone**: 1.2 — Five Tracks + AI Summary + Search
**Estimated effort**: 10 hours (up from 7; WebGPU pipeline is the most complex frontend task)
**Dependencies**: T15 (AnnotationStore loaded via Rust pipeline), T18 (searchStore provides match offsets), T09 (Tauri shell + virtual scroll)
**Outputs**: `src-tauri/src/commands/viewport.rs` (extended); `browser/src/components/TrackPanel/` (created); `browser/src/components/OverviewBar/` (created, WebGPU); `browser/src/components/common/LoadingOverlay.tsx` (created); `browser/src/stores/trackStore.ts` (created); WebGPU shader files `browser/src/shaders/density.wgsl` (created)

---

## v4.0 Critical Review

**Verdict: The SVG `DensityBarcode` component is architecturally unsuitable for the platform's goals. It must not be built. The TrackPanel and ConfidenceSlider logic is sound and largely preserved. The data model for track state is wrong because it stores annotations in JS objects.**

### What is broken — OverviewBar

**1. `DensityBarcode.tsx` creates one SVG `<line>` element per annotation — this is what broke M1.2.**
The performance diagnosis in doc 15 is explicit: "18,760 SVG `<line>` elements in OverviewBar — SVG layout engine overwhelmed." The original T19 specification then documents building the EXACT same thing that caused the crash. This is a failure of the spec to internalize the diagnosis. The entire `DensityBarcode` component as specified is the root cause of the M1.2 performance regression, and it must not be built in any form that uses SVG elements per annotation.

**2. The annotation objects stored in `TrackState.annotations: W3CAnnotation[]` are full JSON-deserialized objects in the JS heap.**
`trackStore.setAnnotations(trackName, annotations: W3CAnnotation[])` — this is exactly the data model that caused 65MB of heap pressure in the failing M1.2 build. Storing 18,760 annotation objects in a Zustand store reproduces the original failure. In v4.0, the JS stores hold **ZERO annotation objects**. Annotations live in Rust's `AnnotationStore` arena. The JS store holds only UI state: which tracks are visible, confidence thresholds, loading status. Annotation data comes from Rust only when specifically queried (viewport queries, density histograms).

**3. `ConfidenceSlider` filters annotations client-side: `track.annotations.filter(a => confidence >= threshold)`.**
This is an O(n) scan of 18,760 annotation objects per slider drag event. In v4.0, confidence filtering is a Rust SIMD operation taking ~1.2 microseconds for the full annotation set. The frontend slider sends a `update_filter({track_mask, min_confidence})` Tauri command; Rust applies the SIMD filter and returns a new density histogram. Zero JS annotation scanning.

**4. The `d3>=7` dependency for density barcode scale is unnecessary overhead.**
D3 is a 70KB library being imported to compute `x = (start / documentLength) * width` — a one-line arithmetic expression. D3 is not justified for this task. If D3 is needed for other visualizations (stacked area charts, etc.), it remains in the project. But `DensityBarcode.tsx` must not import D3.

**5. `LoadingOverlay` tracks whether annotations are in `trackStore.tracks[name].loaded: boolean` — but in v4.0, the store never holds annotations.**
The loading state is reported by Rust pipeline progress events. The LoadingOverlay subscribes to `pipeline:progress` Tauri events, not to a Zustand annotations array.

**6. `trackStore.setTrackByIndex(index, visible)` requires `loadOrder: string[]` to map index → name.**
This is correct logic. But `loadOrder` in v4.0 comes from the Rust manifest (which tracks are registered in which order), not from the order in which `initTrack(manifest)` calls happen. The order must be stable and deterministic, derived from `TrackId` enum values (0-4 for entities through topics).

### What is broken — Multi-track rendering

**7. `applyMultiTrackRendering()` scans `track.annotations` in JS for each visible paragraph.**
`filtered = track.annotations.filter(a => confidence >= threshold && a.target.selector.start < paragraphEnd && a.target.selector.end > paragraphStart)` — this is an O(n_annotations) scan per paragraph per track. For 30 visible paragraphs × 5 tracks × 18,760 annotations = 2.8 million comparisons per render frame. In v4.0, `query_viewport(start_char, end_char)` returns only the 50-300 annotations in the visible viewport, pre-filtered by confidence.

**8. `<mark>` and `<span style="text-decoration:underline">` DOM elements for annotation highlights are eliminated.**
The Canvas overlay replaces all DOM span-based highlighting. Annotation highlights are drawn as colored rectangles or line segments on a canvas layer. Zero DOM nodes added per annotation.

---

## v4.0 Rewrite

### Architecture

```
React TrackPanel (UI state only)
  │
  ├── visible bitmask (u64, bit per track)
  ├── confidence thresholds (f32 per track)
  └── on change → invoke("update_filter", { track_mask, confidence_thresholds })
                       │
                       ▼
              Rust FilterEngine (SIMD/NEON)
                       │
                       ├── apply bitmask + confidence in ~1.2μs
                       ├── update RangeIndex active set
                       └── return DensityHistograms (one per visible track)

WebGPU OverviewBar
  ├── receives DensityHistogram[5] from Rust (5 * 2000 floats = 40KB)
  ├── uploads to GPU as Float32Array buffer
  └── fragment shader renders 5 density rows in a single draw call

VirtualTextView
  ├── scroll event → invoke("query_viewport", { start_char, end_char })
  │                          → 50-300 packed annotation results
  └── CanvasAnnotationOverlay draws highlights from these 50-300 results
        (zero DOM annotation nodes)
```

### Rust: filter + histogram command

```rust
// src-tauri/src/commands/viewport.rs

#[derive(serde::Deserialize)]
pub struct FilterParams {
    pub project_id: String,
    pub track_mask: u64,                   // bitfield: bit N = TrackId N visible
    pub confidence_thresholds: Vec<f32>,   // one per track, index = TrackId
}

#[derive(serde::Serialize)]
pub struct FilterResult {
    pub histograms: Vec<DensityHistogram>, // one per visible track
    pub visible_annotation_counts: Vec<u32>,
    pub filter_us: f64,                    // microseconds for SIMD filter pass
}

#[tauri::command]
pub async fn update_filter(
    params: FilterParams,
    state: tauri::State<'_, AppState>,
) -> Result<FilterResult, String> {
    let start = std::time::Instant::now();
    let mut manager = state.project_manager.write().await;
    let project = manager
        .get_project_mut(&params.project_id)
        .ok_or("Project not loaded")?;

    // SIMD filter pass — ~1.2μs for 18,760 annotations
    let filter_mask = project.filter_engine.filter(
        &project.annotation_store,
        params.track_mask,
        &params.confidence_thresholds,
    );

    // Update RangeIndex active set
    project.range_index.update_active(&filter_mask);

    // Compute density histograms for visible tracks
    let histograms = (0..5u8)
        .filter(|&track_id| (params.track_mask >> track_id) & 1 == 1)
        .map(|track_id| {
            project.annotation_store.density_histogram(
                track_id,
                &filter_mask,
                2000, // bins
                project.doc_length,
            )
        })
        .collect();

    let visible_counts = (0..5u8)
        .map(|track_id| filter_mask.count_set_for_track(track_id))
        .collect();

    Ok(FilterResult {
        histograms,
        visible_annotation_counts: visible_counts,
        filter_us: start.elapsed().as_secs_f64() * 1_000_000.0,
    })
}

/// DensityHistogram: pre-computed by Rust, uploaded to GPU as Float32 buffer.
#[derive(serde::Serialize, Clone)]
pub struct DensityHistogram {
    pub track_id: u8,
    pub color: [f32; 3],          // RGB from manifest
    pub bins: Vec<f32>,            // length = n_bins (2000)
    pub max_value: f32,            // for normalization in shader
}
```

### WebGPU OverviewBar

**`browser/src/components/OverviewBar/OverviewBar.tsx`**:

```tsx
import { useEffect, useRef, useCallback } from "react";
import { useTrackStore } from "../../stores/trackStore";
import { initDensityPipeline, renderDensity } from "./densityPipeline";

export function OverviewBar() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pipelineRef = useRef<GPURenderPipeline | null>(null);
  const { histograms, searchMatchPositions } = useTrackStore();

  // Initialize WebGPU pipeline once
  useEffect(() => {
    if (!canvasRef.current) return;
    initDensityPipeline(canvasRef.current).then((pipeline) => {
      pipelineRef.current = pipeline;
    });
  }, []);

  // Re-render when histograms or search matches change
  useEffect(() => {
    if (!pipelineRef.current || !canvasRef.current) return;
    renderDensity(pipelineRef.current, canvasRef.current, histograms, searchMatchPositions);
  }, [histograms, searchMatchPositions]);

  return (
    <div className="overview-bar">
      <canvas
        ref={canvasRef}
        width={1200}
        height={histograms.length * 20 + 20}  // 20px per track + 20px search row
        className="overview-bar__canvas"
        aria-label="Document density overview"
      />
    </div>
  );
}
```

**`browser/src/components/OverviewBar/densityPipeline.ts`**:

```typescript
// WebGPU density rendering pipeline

const DENSITY_SHADER = /* wgsl */ `
struct DensityUniforms {
  n_bins: u32,
  n_tracks: u32,
  bar_height: f32,
  canvas_width: f32,
}

@group(0) @binding(0) var<uniform> uniforms: DensityUniforms;
@group(0) @binding(1) var<storage, read> bins: array<f32>;       // [n_tracks * n_bins]
@group(0) @binding(2) var<storage, read> colors: array<vec4<f32>>; // [n_tracks]
@group(0) @binding(3) var<storage, read> max_values: array<f32>; // [n_tracks]

struct VertexOut {
  @builtin(position) position: vec4<f32>,
  @location(0) track_idx: f32,
  @location(1) bin_x: f32,
}

@vertex
fn vs_main(@builtin(vertex_index) vi: u32) -> VertexOut {
  // Full-screen quad
  let positions = array<vec2<f32>, 4>(
    vec2(-1.0, -1.0), vec2(1.0, -1.0), vec2(-1.0, 1.0), vec2(1.0, 1.0)
  );
  var out: VertexOut;
  out.position = vec4(positions[vi], 0.0, 1.0);
  return out;
}

@fragment
fn fs_main(@builtin(position) frag_coord: vec4<f32>) -> @location(0) vec4<f32> {
  let x = frag_coord.x / uniforms.canvas_width;
  let y = frag_coord.y;

  let track_idx = u32(y / uniforms.bar_height);
  if (track_idx >= uniforms.n_tracks) {
    return vec4(0.94, 0.94, 0.94, 1.0);  // background
  }

  let bin = u32(x * f32(uniforms.n_bins));
  let density = bins[track_idx * uniforms.n_bins + bin];
  let max_val = max_values[track_idx];
  let normalized = density / max(max_val, 0.001);

  let color = colors[track_idx];
  // Blend track color with background based on density
  let bg = vec4(0.94, 0.94, 0.94, 1.0);
  return mix(bg, color, normalized * 0.85);
}
`;

export async function initDensityPipeline(canvas: HTMLCanvasElement): Promise<{
  device: GPUDevice;
  pipeline: GPURenderPipeline;
  context: GPUCanvasContext;
}> {
  if (!navigator.gpu) {
    throw new Error("WebGPU not supported");
  }
  const adapter = await navigator.gpu.requestAdapter();
  if (!adapter) throw new Error("No GPU adapter");
  const device = await adapter.requestDevice();
  const context = canvas.getContext("webgpu") as GPUCanvasContext;
  const format = navigator.gpu.getPreferredCanvasFormat();
  context.configure({ device, format });

  const shaderModule = device.createShaderModule({ code: DENSITY_SHADER });
  const pipeline = device.createRenderPipeline({
    layout: "auto",
    vertex: { module: shaderModule, entryPoint: "vs_main" },
    fragment: { module: shaderModule, entryPoint: "fs_main", targets: [{ format }] },
    primitive: { topology: "triangle-strip" },
  });

  return { device, pipeline, context };
}

export function renderDensity(
  gpu: { device: GPUDevice; pipeline: GPURenderPipeline; context: GPUCanvasContext },
  canvas: HTMLCanvasElement,
  histograms: DensityHistogram[],
  searchMatches: Float32Array,  // normalized positions [0,1]
): void {
  const { device, pipeline, context } = gpu;
  const nTracks = histograms.length + 1;  // +1 for search row
  const nBins = histograms[0]?.bins.length ?? 2000;

  // Pack all bin data into a single Float32Array
  const allBins = new Float32Array(nTracks * nBins);
  histograms.forEach((hist, i) => {
    allBins.set(hist.bins, i * nBins);
  });
  // Search row: mark search match positions as density=1.0
  const searchRow = new Float32Array(nBins);
  for (const pos of searchMatches) {
    const bin = Math.floor(pos * nBins);
    if (bin < nBins) searchRow[bin] = 1.0;
  }
  allBins.set(searchRow, (nTracks - 1) * nBins);

  // Pack colors
  const colors = new Float32Array(nTracks * 4);
  histograms.forEach((hist, i) => {
    colors.set([...hist.color, 1.0], i * 4);
  });
  colors.set([0.945, 0.769, 0.059, 1.0], (nTracks - 1) * 4);  // yellow for search

  const maxValues = new Float32Array(nTracks);
  histograms.forEach((hist, i) => { maxValues[i] = hist.max_value; });
  maxValues[nTracks - 1] = 1.0;

  // Upload to GPU
  const binBuffer = device.createBuffer({
    size: allBins.byteLength,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
  });
  device.queue.writeBuffer(binBuffer, 0, allBins);

  // ... (uniform buffer, color buffer, bind group, render pass — abbreviated for spec)
  // Full render pass submits one draw call for 4 vertices (full-screen quad).
  // The fragment shader does all the work.
}
```

**The critical result**: 18,760 SVG `<line>` elements → **one draw call**. The shader loop over bins is GPU-parallel.

### TrackPanel (updated — zero annotation objects in JS)

```typescript
// browser/src/stores/trackStore.ts

import { create } from "zustand";
import { invoke } from "@tauri-apps/api/tauri";

interface TrackUIState {
  name: string;
  trackId: number;        // u8 from manifest
  visible: boolean;
  color: string;          // hex from manifest.colorScheme.primary
  confidenceThreshold: number;
  annotationCount: number;  // reported by Rust after filter
  loading: boolean;
  loaded: boolean;
  evidenceLevel: string;
}

interface TrackStore {
  tracks: Record<string, TrackUIState>;
  loadOrder: string[];
  histograms: DensityHistogram[];     // from Rust update_filter result
  searchMatchPositions: Float32Array; // normalized [0,1] positions for GPU

  initFromManifests: (manifests: TrackManifest[]) => void;
  applyFilter: (projectId: string) => Promise<void>;
  toggleTrack: (trackName: string, projectId: string) => Promise<void>;
  setConfidenceThreshold: (trackName: string, threshold: number, projectId: string) => Promise<void>;
  setTrackByIndex: (index: number, visible: boolean, projectId: string) => Promise<void>;
  updateSearchMatches: (matches: SearchMatch[]) => void;
}

export const useTrackStore = create<TrackStore>((set, get) => ({
  tracks: {},
  loadOrder: [],
  histograms: [],
  searchMatchPositions: new Float32Array(0),

  initFromManifests: (manifests) => {
    const tracks: Record<string, TrackUIState> = {};
    const loadOrder: string[] = [];
    for (const m of manifests) {
      tracks[m.trackName] = {
        name: m.trackName,
        trackId: m.trackId,
        visible: true,
        color: m.colorScheme.primary,
        confidenceThreshold: 0.0,
        annotationCount: 0,
        loading: true,
        loaded: false,
        evidenceLevel: m.evidenceLevel ?? "",
      };
      loadOrder.push(m.trackName);
    }
    set({ tracks, loadOrder });
  },

  applyFilter: async (projectId) => {
    const { tracks, loadOrder } = get();
    let trackMask = 0n;
    const confidenceThresholds: number[] = new Array(5).fill(0.0);

    for (const name of loadOrder) {
      const t = tracks[name];
      if (t.visible) trackMask |= (1n << BigInt(t.trackId));
      confidenceThresholds[t.trackId] = t.confidenceThreshold;
    }

    try {
      const result = await invoke<FilterResult>("update_filter", {
        params: {
          project_id: projectId,
          track_mask: Number(trackMask),  // safe for u64 with 5 tracks
          confidence_thresholds: confidenceThresholds,
        },
      });

      // Update annotation counts from Rust result
      const updatedTracks = { ...tracks };
      for (let i = 0; i < loadOrder.length; i++) {
        const name = loadOrder[i];
        updatedTracks[name] = {
          ...updatedTracks[name],
          annotationCount: result.visible_annotation_counts[i] ?? 0,
          loaded: true,
          loading: false,
        };
      }

      set({ tracks: updatedTracks, histograms: result.histograms });
    } catch (e) {
      console.error("Filter update failed:", e);
    }
  },

  toggleTrack: async (trackName, projectId) => {
    set((state) => ({
      tracks: {
        ...state.tracks,
        [trackName]: { ...state.tracks[trackName], visible: !state.tracks[trackName].visible },
      },
    }));
    await get().applyFilter(projectId);
  },

  setConfidenceThreshold: async (trackName, threshold, projectId) => {
    set((state) => ({
      tracks: {
        ...state.tracks,
        [trackName]: { ...state.tracks[trackName], confidenceThreshold: threshold },
      },
    }));
    await get().applyFilter(projectId);
  },

  setTrackByIndex: async (index, visible, projectId) => {
    const { loadOrder } = get();
    const name = loadOrder[index - 1];
    if (name) {
      set((state) => ({
        tracks: { ...state.tracks, [name]: { ...state.tracks[name], visible } },
      }));
      await get().applyFilter(projectId);
    }
  },

  updateSearchMatches: (matches) => {
    // Convert match start offsets to normalized [0,1] positions for GPU
    // docLength is available from projectStore
    const positions = new Float32Array(matches.map((m) => m.start / 600000));  // TODO: real docLength
    set({ searchMatchPositions: positions });
  },
}));
```

The store holds **zero annotation objects**. The `histograms` field contains 5 × 2000 floats (40KB), received from Rust. This is the only annotation-derived data in the JS heap.

### TrackPanel, TrackToggle, ConfidenceSlider

These components are structurally correct from the original. Key changes:
- `TrackToggle` reads `track.annotationCount` (not `track.annotations.length`)
- `ConfidenceSlider.onChange` calls `setConfidenceThreshold(name, value, projectId)` — async, triggers Rust SIMD filter + GPU upload
- No `TrackState.annotations: W3CAnnotation[]` field exists

```tsx
export function ConfidenceSlider({ trackName, value }: ConfidenceSliderProps) {
  const { setConfidenceThreshold } = useTrackStore();
  const { currentProjectId } = useProjectStore();

  const handleChange = useCallback(
    debounce((v: number) => {
      if (currentProjectId) {
        void setConfidenceThreshold(trackName, v, currentProjectId);
      }
    }, 50),  // 50ms debounce: don't fire on every pixel of slider drag
    [trackName, setConfidenceThreshold, currentProjectId]
  );

  return (
    <div className="confidence-slider">
      <label htmlFor={`conf-${trackName}`}>Min confidence</label>
      <input
        id={`conf-${trackName}`}
        type="range" min={0} max={1} step={0.05} value={value}
        onChange={(e) => handleChange(parseFloat(e.target.value))}
      />
      <span>{Math.round(value * 100)}%</span>
    </div>
  );
}
```

### LoadingOverlay (Tauri event driven)

```tsx
// browser/src/components/common/LoadingOverlay.tsx

import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";

interface PipelineProgress {
  track: string;
  status: { type: "Starting" } | { type: "Running"; lines_read: number } | { type: "Complete"; count: number; elapsed_ms: number } | { type: "Failed"; message: string };
  annotations_ingested: number;
  elapsed_ms: number;
}

export function LoadingOverlay() {
  const [trackProgress, setTrackProgress] = useState<Record<string, PipelineProgress>>({});
  const [allDone, setAllDone] = useState(false);

  useEffect(() => {
    const unlisten = listen<PipelineProgress>("pipeline:progress", (event) => {
      setTrackProgress((prev) => ({
        ...prev,
        [event.payload.track]: event.payload,
      }));
    });

    return () => { unlisten.then((f) => f()); };
  }, []);

  useEffect(() => {
    const all = Object.values(trackProgress);
    if (all.length === 5 && all.every((p) => p.status.type === "Complete" || p.status.type === "Failed")) {
      const timer = setTimeout(() => setAllDone(true), 500);
      return () => clearTimeout(timer);
    }
  }, [trackProgress]);

  if (allDone || Object.keys(trackProgress).length === 0) return null;

  return (
    <div className="loading-overlay" role="status">
      <div className="loading-overlay__card">
        <h3>Loading Palimpsest</h3>
        {Object.entries(trackProgress).map(([track, progress]) => (
          <div key={track} className="loading-overlay__track">
            <span>{track}</span>
            <span>
              {progress.status.type === "Complete"
                ? `${progress.status.count.toLocaleString()} annotations (${progress.status.elapsed_ms}ms)`
                : progress.status.type === "Running"
                ? `${progress.annotations_ingested.toLocaleString()}…`
                : progress.status.type === "Failed"
                ? `Failed: ${(progress.status as any).message}`
                : "Starting"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Subscribes to `pipeline:progress` Tauri events — NOT to a Zustand annotations array. Works in real time as Rust ingests each extractor's output.

### Test strategy

**Rust unit tests** (`src-tauri/src/filter_engine_test.rs`):

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simd_filter_full_pass() {
        let mut store = AnnotationStore::new();
        // Insert 100 test annotations with various confidence values
        for i in 0..100 {
            store.insert(TrackId::Sentiment, PackedAnnotation {
                start: i * 100,
                end: i * 100 + 50,
                confidence: (i as u16 * 100).min(10000),
                track_id: TrackId::Sentiment as u8,
                evidence_level: 5,
                body_offset: i,
            });
        }
        let engine = FilterEngine::new();
        let mask = engine.filter(
            &store,
            1 << (TrackId::Sentiment as u64),  // only sentiment visible
            &[0.0; 5],  // no confidence threshold
        );
        assert_eq!(mask.count_ones(), 100, "All annotations should pass with 0.0 threshold");
    }

    #[test]
    fn test_simd_filter_confidence_threshold() {
        let mut store = AnnotationStore::new();
        for i in 0..100 {
            store.insert(TrackId::Sentiment, PackedAnnotation {
                confidence: (i as u16) * 100,  // 0 to 9900
                ..Default::default()
            });
        }
        let engine = FilterEngine::new();
        let mut thresholds = [0.0f32; 5];
        thresholds[TrackId::Sentiment as usize] = 0.5;  // filter to >= 50% confidence

        let mask = engine.filter(
            &store,
            1 << (TrackId::Sentiment as u64),
            &thresholds,
        );
        // confidence >= 5000 (u16) → confidence >= 0.5 → indices 50-99 pass
        assert_eq!(mask.count_ones(), 50);
    }

    #[test]
    fn test_density_histogram_bin_count() {
        let store = AnnotationStore::new_with_test_data();
        let hist = store.density_histogram(TrackId::Sentiment as u8, &BitVec::all_set(store.len()), 2000, 600_000);
        assert_eq!(hist.bins.len(), 2000);
        assert!(hist.max_value >= 0.0);
    }
}
```

**Performance benchmarks** (`palimpsest-core/benches/filter.rs`):

```rust
fn bench_simd_filter_full_novel(c: &mut Criterion) {
    let store = AnnotationStore::load_test_fixture("pp-full-all-tracks");
    let engine = FilterEngine::new();

    c.bench_function("simd_filter_18760_annotations", |b| {
        b.iter(|| {
            engine.filter(
                &store,
                0b11111u64,  // all 5 tracks visible
                &[0.5, 0.5, 0.5, 0.5, 0.5],
            )
        })
    });
    // REQUIRED: assert elapsed < 2μs (1.2μs target from architecture doc)
}

fn bench_density_histogram_2000_bins(c: &mut Criterion) {
    let store = AnnotationStore::load_test_fixture("pp-full-all-tracks");
    let mask = BitVec::all_set(store.len());

    c.bench_function("density_histogram_2000_bins", |b| {
        b.iter(|| {
            store.density_histogram(TrackId::Sentiment as u8, &mask, 2000, 600_000)
        })
    });
    // REQUIRED: <1ms
}
```

**Browser tests** (Vitest, `browser/src/stores/__tests__/trackStore.test.ts`):

```typescript
import { vi, it, expect, describe, beforeEach } from "vitest";

vi.mock("@tauri-apps/api/tauri", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn(() => Promise.resolve(() => {})) }));

import { invoke } from "@tauri-apps/api/tauri";
import { useTrackStore } from "../trackStore";

describe("trackStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTrackStore.setState({ tracks: {}, loadOrder: [], histograms: [] });
  });

  it("initFromManifests populates tracks with zero annotation count", () => {
    useTrackStore.getState().initFromManifests([
      { trackName: "sentiment", trackId: 1, colorScheme: { primary: "#2ecc71" }, evidenceLevel: "E5" } as any,
    ]);
    const t = useTrackStore.getState().tracks["sentiment"];
    expect(t.annotationCount).toBe(0);
    expect(t.visible).toBe(true);
    // CRITICAL: no 'annotations' array field
    expect((t as any).annotations).toBeUndefined();
  });

  it("toggleTrack calls update_filter Tauri command", async () => {
    vi.mocked(invoke).mockResolvedValue({
      histograms: [],
      visible_annotation_counts: [0, 0, 0, 0, 0],
      filter_us: 1.2,
    });
    useTrackStore.getState().initFromManifests([
      { trackName: "sentiment", trackId: 1, colorScheme: { primary: "#2ecc71" }, evidenceLevel: "E5" } as any,
    ]);
    await useTrackStore.getState().toggleTrack("sentiment", "pp-full");
    expect(invoke).toHaveBeenCalledWith("update_filter", expect.objectContaining({
      params: expect.objectContaining({ project_id: "pp-full" }),
    }));
    expect(useTrackStore.getState().tracks["sentiment"].visible).toBe(false);
  });

  it("applyFilter updates annotation counts from Rust result", async () => {
    vi.mocked(invoke).mockResolvedValue({
      histograms: [],
      visible_annotation_counts: [5000, 18760, 2500, 3200, 2400],
      filter_us: 1.1,
    });
    useTrackStore.getState().initFromManifests([
      { trackName: "entities",  trackId: 0, colorScheme: { primary: "#e74c3c" }, evidenceLevel: "E4" } as any,
      { trackName: "sentiment", trackId: 1, colorScheme: { primary: "#2ecc71" }, evidenceLevel: "E5" } as any,
    ]);
    await useTrackStore.getState().applyFilter("pp-full");
    expect(useTrackStore.getState().tracks["sentiment"].annotationCount).toBe(18760);
  });
});
```

**Performance targets**:
| Operation | Current (broken) | Target (v4.0) | Mechanism |
|-----------|-----------------|---------------|-----------|
| Track toggle → re-render | 500ms+ | <2ms | SIMD filter + interval tree |
| OverviewBar render | 300ms (SVG) | <1ms (GPU) | WebGPU compute shader |
| Confidence slider drag | 500ms+ | <2ms | 50ms debounce + SIMD |
| JS heap for 5 novels | 325MB | 1.5MB packed | Zero annotation objects in JS |
| Density histogram build | N/A | <1ms | Rust arena scan |
| GPU bin upload (5 tracks) | N/A | <0.5ms | `writeBuffer` 40KB |

---

## Original Content (preserved for reference)

### Context

This task delivers the three scaffolding UI systems that make multi-track annotation browsing usable: the TrackPanel (left sidebar listing tracks with toggles and confidence filters), the OverviewBar (full-document density barcodes plus search ticks), and the LoadingOverlay (track-by-track loading progress). It also upgrades `TextLinearView` from single-track to multi-track rendering, with a priority system for overlapping annotations.

### Design Decisions (original, superseded by v4.0)

- **TrackManifest drives all rendering decisions**: colors, rendering style, overview bar color all come from the manifest file. (Preserved in v4.0.)
- **Maximum 3 concurrent tracks**: rendering more than 3 overlapping annotation types simultaneously creates visual clutter. (Preserved in v4.0 — handled in Canvas draw ordering.)
- **OverviewBar as SVG, not Canvas**: "SVG handles this well and supports click events naturally. Canvas would be needed only if the tick count exceeded ~10,000." — This limit was immediately exceeded at 18,760. The assessment was wrong. v4.0 uses WebGPU. (Superseded.)
- **`LoadingOverlay` tracks loading state from `trackStore`**: when all tracks are `loaded: true`, the overlay auto-dismisses. (v4.0: driven by `pipeline:progress` Tauri events, not a Zustand annotation array.)
- **Confidence slider range 0.0–1.0, step 0.05**: gives 20 positions — granular enough. (Preserved. Step size of 0.05 + 50ms debounce prevents SIMD filter spam.)
- **Search ticks as a separate SVG layer**: yellow ticks by convention. (v4.0: rendered in the GPU density shader as an additional row — same visual result, zero SVG elements.)
