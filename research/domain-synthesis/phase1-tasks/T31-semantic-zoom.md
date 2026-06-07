# T31: Semantic Zoom

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 6 hours
**Dependencies**: T30 (VirtualTextView with CanvasAnnotationOverlay and Rust viewport query), T28 (Rust FilterEngine + track visibility state)
**Outputs**: `browser/src/components/TextLinearView/SemanticZoom.tsx`, `browser/src/shaders/density_zoom.wgsl`, `browser/src/stores/viewStore.ts` (modified), `browser/src/components/Layout/Toolbar.tsx` (modified)

---

## v4.0 Critical Review

**Verdict: The three-level semantic zoom concept is right. The implementation is wrong at medium and far zoom because it recreates the annotation-scanning problem in a different form, and because the density bars are DOM `<div>` elements that cannot sustain 60fps at far zoom with 1,832 visible paragraphs.**

### What Is Broken

**Medium view: `annotationsForParagraph.filter(a => a.body.type === manifest.bodyType)`** — this is a JS filter over the annotations array for every paragraph row. With 30 visible rows × 5 tracks × (up to 50 annotations per paragraph) = 7,500 filter calls per render. Not catastrophic at medium zoom but it is the wrong data source. The annotation count per paragraph should come from the Rust `DensityHistogram`, not from a JS array filter.

**Far view: each `<div className="paragraph-far">` at 4px height creates a DOM node.** At far zoom, 100-200 "visible" paragraphs are shown (because each is only 4px). 200 DOM divs with `flex` children for each active track = 200 × 5 = 1,000 DOM nodes visible simultaneously. This is not catastrophic but it contradicts the v4.0 principle that all density visualizations are GPU-rendered.

**The zoom threshold arithmetic is done in React.** `computeZoomLevel(visibleParagraphCount)` runs on every scroll event and triggers a React state update which re-renders `TextLinearView`. This creates a chain: scroll → height computation → visible count → zoom level → re-render. Every scroll causes a re-render when crossing zoom boundaries.

**Transition animation with `opacity: 0 → 1`** mounts and unmounts components per zoom transition. Component mount/unmount is expensive — React must reconcile the full subtree. For zoom transitions (which happen on every Ctrl+scroll), this is jarring.

**Medium and far views use `track.annotations` from `trackStore`.** This means the full annotation array is in JS memory even at medium/far zoom, where annotations are shown as aggregate counts, not individual spans. The full annotation data should not be in the JS heap.

---

## v4.0 Rewrite

### Architecture

Close zoom is handled by the VirtualTextView and CanvasAnnotationOverlay (T30) — no changes at this level.

Medium and far zoom are handled by a **GPU Density Renderer**: a WebGPU render pass that reads the `DensityHistogram` (computed by Rust at each filter change, uploaded as a GPU buffer) and renders stacked density bars or heatmap rows using a fragment shader. No DOM nodes. No JS iteration. No annotation array in JS heap.

```
Zoom level change
  → if zoom == 'close':
      VirtualTextView renders text + CanvasAnnotationOverlay
      (already implemented in T30)
  → if zoom == 'medium' or 'far':
      DensityView renders GPU stacked bars
      Rust provides DensityHistogram per track per paragraph
      WebGPU fragment shader draws the bars from GPU buffer
```

### DensityHistogram (Rust)

The `DensityHistogram` is computed by Rust on every filter change:

```rust
// palimpsest-core/src/density.rs

/// Per-paragraph annotation counts per track, for density rendering.
/// Uploaded to GPU as a 2D Float32 texture: [N × T] where N=paragraphs, T=tracks.
pub struct DensityHistogram {
    pub counts: Vec<f32>,    // flat [N * T], row-major
    pub n_paragraphs: usize,
    pub n_tracks: usize,
    pub max_count: f32,      // for normalization
}

impl DensityHistogram {
    /// Compute from filtered annotation set. O(k) where k = filtered annotation count.
    pub fn compute(
        filtered_annotations: &[&PackedAnnotation],
        n_paragraphs: usize,
        n_tracks: usize,
        paragraph_boundaries: &[u32],  // char offsets at paragraph starts
    ) -> Self {
        let mut counts = vec![0.0f32; n_paragraphs * n_tracks];

        for ann in filtered_annotations {
            // Binary search for paragraph index
            let para_idx = paragraph_boundaries.partition_point(|&b| b <= ann.start);
            let para_idx = para_idx.saturating_sub(1).min(n_paragraphs - 1);
            let track_idx = ann.track_id as usize;
            if track_idx < n_tracks {
                counts[para_idx * n_tracks + track_idx] += 1.0;
            }
        }

        let max_count = counts.iter().cloned().fold(0.0f32, f32::max);
        Self { counts, n_paragraphs, n_tracks, max_count }
    }
}
```

The histogram is uploaded to GPU as a `R32Float` texture (N × T pixels). The fragment shader normalizes by `max_count`.

### Tauri Command: `get_density_histogram`

```rust
#[tauri::command]
pub fn get_density_histogram(
    project_id: String,
    track_mask: u64,
    min_confidence: u16,
    state: tauri::State<'_, AppState>,
) -> Result<DensityHistogramResponse, String> {
    let core = state.core.blocking_lock();
    let project = core.get_project(&project_id).ok_or("Project not found")?;

    // Get filtered annotations (from cached filter result if mask unchanged)
    let filtered = project.filter_engine.get_filtered_set(
        &project.annot_store.packed,
        track_mask,
        min_confidence,
    );

    let histogram = DensityHistogram::compute(
        &filtered,
        project.paragraphs.len(),
        project.n_tracks(),
        &project.paragraph_starts,
    );

    // Upload to GPU texture
    let texture = core.upload_density_texture(&project_id, &histogram)?;
    Ok(DensityHistogramResponse {
        texture_handle: texture,
        n_paragraphs: histogram.n_paragraphs,
        n_tracks: histogram.n_tracks,
        max_count: histogram.max_count,
    })
}
```

### WebGPU Density Shader

```wgsl
// browser/src/shaders/density_zoom.wgsl

struct Uniforms {
    n_paragraphs: u32,
    n_tracks: u32,
    max_count: f32,
    zoom_level: u32,      // 0=medium, 1=far
    start_para: u32,      // first visible paragraph
    end_para: u32,        // last visible paragraph
    selected_para: i32,
}

@group(0) @binding(0) var<uniform> uniforms: Uniforms;
@group(0) @binding(1) var density_texture: texture_2d<f32>;  // [N × T]
@group(0) @binding(2) var density_sampler: sampler;
@group(0) @binding(3) var<storage> track_colors: array<vec4<f32>>;  // one color per track

@fragment
fn fs_density(in: VertexOutput) -> @location(0) vec4<f32> {
    // Map canvas UV → (paragraph index, track blend position)
    let visible_count = uniforms.end_para - uniforms.start_para;
    let para_f = in.uv.y * f32(visible_count) + f32(uniforms.start_para);
    let para_idx = u32(para_f);

    if para_idx >= uniforms.n_paragraphs { discard; }

    // Stack track colors horizontally proportional to density
    let x = in.uv.x;
    var cumulative = 0.0;

    for (var t = 0u; t < uniforms.n_tracks; t++) {
        let tex_u = (f32(para_idx) + 0.5) / f32(uniforms.n_paragraphs);
        let tex_v = (f32(t) + 0.5) / f32(uniforms.n_tracks);
        let count = textureSample(density_texture, density_sampler, vec2(tex_u, tex_v)).r;
        let normalized = min(count / uniforms.max_count, 1.0);
        let track_width = normalized / f32(uniforms.n_tracks);

        if x >= cumulative && x < cumulative + track_width {
            var color = track_colors[t];
            // Selected paragraph highlight
            if uniforms.selected_para >= 0 && para_idx == u32(uniforms.selected_para) {
                color = mix(color, vec4(0.2, 0.5, 1.0, 1.0), 0.4);
            }
            return color;
        }
        cumulative += track_width;
    }

    // Background for sparse rows
    return vec4(0.95, 0.95, 0.96, 1.0);
}
```

This shader renders medium and far zoom identically — the only difference is the row height (28px at medium, 4px at far), which is controlled by the VirtualTextView layout, not the shader. The shader is called once per frame with a single draw call.

### SemanticZoom Component

```typescript
// browser/src/components/TextLinearView/SemanticZoom.tsx

export type ZoomLevel = 'close' | 'medium' | 'far';

export function computeZoomLevel(visibleParagraphCount: number): ZoomLevel {
  if (visibleParagraphCount <= 5) return 'close';
  if (visibleParagraphCount <= 30) return 'medium';
  return 'far';
}

interface SemanticZoomContainerProps {
  zoomLevel: ZoomLevel;
  projectId: string;
  visibleRange: [number, number];
  selectedParagraphIndex: number | null;
  // Close zoom props (pass-through to VirtualTextView)
  paragraphs: ParagraphData[];
}

export function SemanticZoomContainer({
  zoomLevel, projectId, visibleRange, selectedParagraphIndex, paragraphs,
}: SemanticZoomContainerProps): JSX.Element {
  if (zoomLevel === 'close') {
    return (
      <VirtualTextView
        paragraphs={paragraphs}
        projectId={projectId}
        overscanCount={2}
      />
    );
  }

  // Medium and far: GPU density renderer
  return (
    <DensityView
      projectId={projectId}
      zoomLevel={zoomLevel}
      visibleRange={visibleRange}
      selectedParagraphIndex={selectedParagraphIndex}
      rowHeightPx={zoomLevel === 'medium' ? 28 : 4}
    />
  );
}
```

### DensityView

```typescript
// browser/src/components/TextLinearView/DensityView.tsx

export function DensityView({
  projectId, zoomLevel, visibleRange, selectedParagraphIndex, rowHeightPx,
}: DensityViewProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gpuStateRef = useRef<DensityGPUState | null>(null);
  const { trackMask, minConfidence } = useTrackStore();
  const [textureHandle, setTextureHandle] = useState<DensityTextureHandle | null>(null);

  // Fetch density histogram when filter changes
  useEffect(() => {
    invoke<DensityHistogramResponse>('get_density_histogram', {
      projectId,
      trackMask: Number(trackMask),
      minConfidence: Math.round(minConfidence * 10000),
    }).then(response => {
      setTextureHandle(response.textureHandle);
      // Update GPU uniforms
      if (gpuStateRef.current) {
        updateDensityUniforms(gpuStateRef.current, response, visibleRange, selectedParagraphIndex);
        renderDensityFrame(gpuStateRef.current);
      }
    });
  }, [trackMask, minConfidence, visibleRange, selectedParagraphIndex, projectId]);

  // Click on density row → set selectedParagraphIndex
  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current!;
    const y = e.clientY - canvas.getBoundingClientRect().top;
    const [startPara, endPara] = visibleRange;
    const visibleCount = endPara - startPara;
    const paraIdx = startPara + Math.floor((y / canvas.height) * visibleCount);
    setSelectedParagraphIndex(paraIdx);
    requestScrollToParagraph(paraIdx); // Switch to close zoom to read the paragraph
  };

  return (
    <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        style={{ width: '100%', height: '100%', cursor: 'pointer' }}
      />
      <ZoomHint level={zoomLevel} />
    </div>
  );
}
```

### Zoom Transition: No Component Mount/Unmount

The zoom transition does NOT unmount components. It switches between two React subtrees that are both kept mounted but shown/hidden:

```typescript
// In TextLinearView parent:

return (
  <>
    {/* Close zoom — always mounted, shown/hidden via CSS */}
    <div style={{ display: zoomLevel === 'close' ? 'block' : 'none' }}>
      <VirtualTextView ... />
    </div>
    {/* Medium/far zoom — always mounted, shown/hidden via CSS */}
    <div style={{ display: zoomLevel !== 'close' ? 'block' : 'none' }}>
      <DensityView ... />
    </div>
  </>
);
```

Using CSS `display: none` to show/hide means the GPU state in `DensityView` is retained across zoom transitions — no re-initialization, no texture re-upload. The transition is instantaneous.

### Performance Targets (Hard Requirements)

| Operation | Target |
|-----------|--------|
| Zoom level change (close ↔ medium) | <1ms (CSS display toggle) |
| DensityView frame render (GPU) | <1ms (single draw call) |
| `get_density_histogram` Tauri command | <5ms (Rust compute + GPU upload) |
| Track toggle at medium/far zoom | <5ms (Rust recompute + GPU uniform update) |
| DOM node count at medium zoom | ≤10 (canvas + container) |
| DOM node count at far zoom | ≤10 (same) |

### Acceptance Criteria (v4.0)

- Close zoom: VirtualTextView renders text + canvas annotation highlights (from T30)
- Medium zoom: GPU-rendered stacked density bars per track per paragraph, no `<mark>` spans, no DOM rows per paragraph
- Far zoom: GPU-rendered 4px heatmap rows, 1,832 paragraphs visible as density field
- Track toggle at medium/far zoom: <5ms (Rust DensityHistogram recompute + GPU texture update)
- Zoom transition: <1ms (CSS display toggle, no component remount)
- Ctrl+scroll changes zoom level; slider in Toolbar also works
- DOM nodes: ≤10 at medium and far zoom regardless of paragraph count
- `tsc --strict` passes on all new/modified files
- `cargo test` passes `get_density_histogram` command tests

### Tests

```typescript
test('computeZoomLevel classifies correctly', () => {
  expect(computeZoomLevel(3)).toBe('close');
  expect(computeZoomLevel(30)).toBe('medium');
  expect(computeZoomLevel(31)).toBe('far');
});

test('DensityView renders canvas not paragraph divs', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  (invoke as ReturnType<typeof vi.fn>).mockResolvedValue({ textureHandle: 1, nParagraphs: 100, nTracks: 5 });
  const { container } = render(
    <DensityView projectId="test" zoomLevel="medium" visibleRange={[0, 100]}
      selectedParagraphIndex={null} rowHeightPx={28} />
  );
  expect(container.querySelector('canvas')).toBeTruthy();
  expect(container.querySelectorAll('[data-para-idx]')).toHaveLength(0);
});

test('SemanticZoomContainer uses VirtualTextView at close zoom', () => {
  const { container } = render(
    <SemanticZoomContainer zoomLevel="close" projectId="test"
      visibleRange={[0, 5]} selectedParagraphIndex={null} paragraphs={mockParagraphs(10)} />
  );
  // VirtualTextView renders, DensityView hidden
  expect(container.querySelector('.virtual-text-view')).toBeTruthy();
});
```

```rust
#[test]
fn test_density_histogram_compute() {
    let ann = PackedAnnotation { start: 500, end: 510, track_id: 0,
                                 confidence: 8000, evidence_level: 4, body_offset: 0 };
    let boundaries = vec![0u32, 200, 400, 600, 800];
    let hist = DensityHistogram::compute(&[&ann], 4, 2, &boundaries);
    // Annotation at char 500-510 falls in paragraph 2 (boundary 400-600)
    assert_eq!(hist.counts[2 * 2 + 0], 1.0); // para 2, track 0
    assert_eq!(hist.max_count, 1.0);
}
```

---

## Original Content (Reference)

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 6 hours

### Context (original)

Semantic zoom changes the rendering detail of each paragraph based on zoom level, following JBrowse 2's principle. Three levels: close (annotation spans), medium (density bars), far (heatmap rows). Zoom stored in `viewStore`; auto-computed from visible paragraph count; user-overridable via slider.

### Design Decisions (original)

- **Three fixed levels over continuous zoom**: Discrete levels map to semantically meaningful scales.
- **`visibleParagraphCount` as zoom trigger**: Natural semantic unit for literary text.
- **4px row height in far view**: 1,832 paragraphs = ~7,300px total scroll height.
- **Density normalization cap**: Cap at 10 (medium) and 5 (far) to prevent dense paragraphs washing out signal.
