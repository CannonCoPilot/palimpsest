# T32: Signal Visualizations

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours
**Dependencies**: T23 (signal binary format, Rust mmap loading), T31 (DensityView GPU pipeline established), T28 (Rust SignalStore with mmap'd signal access)
**Outputs**: `browser/src/components/SignalPanel/SignalPanel.tsx`, four WebGPU chart components, `browser/src/shaders/signal_charts.wgsl`, Tauri commands for signal data access

---

## v4.0 Critical Review

**Verdict: Using D3 SVG for signal visualizations is the wrong rendering technology for a WebGPU application. D3 constructs DOM elements — hundreds of `<rect>` and `<path>` elements — that must be reconciled by React on every data change. For a stacked bar TopicsChart at N=1,832 with 50 bins, D3 creates 50×10 = 500 `<rect>` SVG elements. For the AlphabetBarcode, the original spec acknowledges "1,832 DOM elements is acceptable" — it is not acceptable in a system optimizing for minimal DOM. All four signal visualizations must be GPU-rendered.**

### What Is Broken

**D3 `schemeCategory10` for topics.** D3 is a 72KB dependency being imported solely for `scaleBand`, `scaleLinear`, and `schemeCategory10`. These are trivial to implement directly in TypeScript. Under v4.0, D3 is not needed and should not be added.

**"3 SVG `<path>` elements for NarrativeArcChart"** — each path is a D3-generated cubic Bezier. React re-renders the SVG on every signal load. Under v4.0 this is a canvas draw call.

**"1,832 canvas pixels for AlphabetBarcode"** — the original spec does use canvas here, which is closer to correct. But the canvas is drawn in a JavaScript `forEach` loop over the sequence string. The correct approach is a WebGPU compute shader that maps the 1,832 letter indices to RGBA colors in parallel.

**Signal data flows through the browser.** Signals are mmap'd by Rust at project load (`SignalStore`). Under the original spec, they are served over HTTP (`/data/{id}/signals/*.bin`) and `fetch()`'d into JS `Float32Array`. This means 12.96MB of self-similarity data and the signals all live in the JS heap alongside annotations. The signals should be uploaded to GPU buffers by Rust, not by the browser.

**`SignalAdapter.ts` loading signals via `fetch`.** This is eliminated. Rust mmap's signals at project load and uploads them to GPU. Tauri commands expose typed query interfaces, not raw bytes.

---

## v4.0 Rewrite

### Architecture

All signal visualizations are WebGPU canvas renders. Signal data lives in Rust `SignalStore` (mmap'd), accessed via Tauri commands that return GPU buffer handles or small typed structs, never raw Float32 binary blobs in JS.

```
Project loads
  → Rust reads signals/narrative_arc.bin → [f32; 15] stack-allocated
  → Rust reads signals/rqa.bin → mmap'd Vec<[f32; 3]>
  → Rust reads signals/alphabet.json → Vec<u8> letter indices
  → Rust reads signals/topics_dist.bin → mmap'd Vec<[f32; K]> (N×K)

Signal panel opens
  → invoke('get_narrative_arc', {projectId}) → NarrativeArcData {segments: [[f32;3]; 5]}
  → invoke('get_rqa_signal', {projectId}) → RQAData (small struct)
  → invoke('get_alphabet_sequence', {projectId}) → AlphabetData {sequence: Vec<u8>}
  → invoke('get_topic_distribution', {projectId}) → TopicsGPUBuffer handle
  → Each chart: WebGPU draw call using data
```

### Technology Stack

| Chart | Technology | Approach |
|-------|-----------|----------|
| NarrativeArcChart | WebGPU canvas, line shader | 3 curve passes via vertex buffer |
| RQAChart | WebGPU canvas, bar shader | Grouped bars via instanced draw |
| AlphabetBarcode | WebGPU canvas, color LUT shader | Compute shader maps Vec<u8> → RGBA |
| TopicsChart | WebGPU canvas, stacked bar shader | Stacked from GPU texture |

### NarrativeArcChart: WebGPU Line Curves

Signal data: `[f32; 15]` = 5 segments × 3 dimensions. Returned from Rust as a small JSON struct:

```rust
#[tauri::command]
pub fn get_narrative_arc(
    project_id: String,
    state: tauri::State<'_, AppState>,
) -> Result<NarrativeArcResponse, String> {
    let core = state.core.blocking_lock();
    let project = core.get_project(&project_id).ok_or("Project not found")?;
    let arc = project.signal_store.narrative_arc
        .as_ref().ok_or("narrative_arc signal not loaded")?;
    // Return 5×3 as nested array — 15 f32 values, trivial JSON
    Ok(NarrativeArcResponse {
        segments: [
            [arc[0], arc[1], arc[2]],
            [arc[3], arc[4], arc[5]],
            [arc[6], arc[7], arc[8]],
            [arc[9], arc[10], arc[11]],
            [arc[12], arc[13], arc[14]],
        ],
        labels: ["staging", "plot_progression", "cognitive_tension"],
    })
}
```

Frontend renders three curves. Each curve is 5 points; a WebGPU line-strip draw with 5 vertices:

```typescript
// browser/src/components/SignalPanel/NarrativeArcChart.tsx

export function NarrativeArcChart({ projectId }: { projectId: string }): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [data, setData] = useState<NarrativeArcResponse | null>(null);

  useEffect(() => {
    invoke<NarrativeArcResponse>('get_narrative_arc', { projectId }).then(setData);
  }, [projectId]);

  useEffect(() => {
    if (!data || !canvasRef.current) return;
    drawNarrativeArcGPU(canvasRef.current, data);
  }, [data]);

  return <canvas ref={canvasRef} width={280} height={80} />;
}

async function drawNarrativeArcGPU(canvas: HTMLCanvasElement, data: NarrativeArcResponse) {
  const context = canvas.getContext('webgpu')!;
  const device = await getGPUDevice();
  const format = navigator.gpu.getPreferredCanvasFormat();
  context.configure({ device, format });

  const COLORS = [[0.9, 0.2, 0.2, 1.0], [0.1, 0.8, 0.4, 1.0], [0.2, 0.4, 0.9, 1.0]];

  // For each of 3 dimensions, draw a line strip of 5 points
  for (let dim = 0; dim < 3; dim++) {
    const points: number[] = [];
    for (let seg = 0; seg < 5; seg++) {
      const x = -1.0 + (seg / 4) * 2.0;  // NDC x
      const y = -1.0 + data.segments[seg][dim] * 2.0;  // NDC y
      points.push(x, y);
    }
    const vertexBuffer = device.createBuffer({
      size: points.length * 4,
      usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
    });
    device.queue.writeBuffer(vertexBuffer, 0, new Float32Array(points));
    // Draw line strip (5 vertices) with color uniform
    // ... standard WebGPU pipeline draw ...
  }
}
```

### AlphabetBarcode: Compute Shader

```wgsl
// browser/src/shaders/alphabet_barcode.wgsl
// Compute shader: maps Vec<u8> letter indices to RGBA pixels

@group(0) @binding(0) var<storage, read> sequence: array<u32>;  // packed u8 as u32
@group(0) @binding(1) var<storage, read> color_lut: array<vec4<f32>>;  // 16 colors
@group(0) @binding(2) var output_texture: texture_storage_2d<rgba8unorm, write>;

@compute @workgroup_size(64)
fn cs_alphabet(@builtin(global_invocation_id) gid: vec3<u32>) {
    let para_idx = gid.x;
    let tex_width = textureDimensions(output_texture).x;
    if para_idx >= arrayLength(&sequence) { return; }

    // Unpack letter index from packed u32 (4 bytes per u32)
    let word_idx = para_idx / 4u;
    let byte_idx = para_idx % 4u;
    let letter_idx = (sequence[word_idx] >> (byte_idx * 8u)) & 0xFFu;

    let color = color_lut[letter_idx];
    let pixel_x = (para_idx * u32(tex_width)) / arrayLength(&sequence);
    let pixel_width = max(1u, u32(tex_width) / arrayLength(&sequence));

    for (var x = pixel_x; x < min(pixel_x + pixel_width, u32(tex_width)); x++) {
        textureStore(output_texture, vec2(x, 0u), color);
    }
}
```

The compute shader runs once when the alphabet data is loaded, writing to a 1D texture. The texture is then rendered by a full-canvas quad. For 1,832 paragraphs, the compute shader runs in 1,832/64 = 29 workgroups — effectively instantaneous on M4's 40 GPU cores.

### RQAChart: Instanced GPU Bars

```wgsl
// browser/src/shaders/signal_charts.wgsl — RQA grouped bars

struct RQAInstance {
    window_idx: u32,
    metric_idx: u32,  // 0=RR, 1=DET, 2=LAM
    value: f32,
}

@group(0) @binding(0) var<uniform> uniforms: RQAUniforms;
@group(0) @binding(1) var<storage, read> instances: array<RQAInstance>;

@vertex
fn vs_rqa_bar(@builtin(vertex_index) vidx: u32,
              @builtin(instance_index) instance: u32) -> VertexOutput {
    let inst = instances[instance];
    let n_windows = uniforms.n_windows;

    // Bar geometry: 4 vertices of a rectangle
    let bar_width = (1.0 / f32(n_windows)) * 0.28;  // 28% of window slot
    let bar_x_base = f32(inst.window_idx) / f32(n_windows) + f32(inst.metric_idx) * bar_width;
    let bar_height = inst.value;

    let corners = array<vec2<f32>, 4>(
        vec2(bar_x_base, 0.0),
        vec2(bar_x_base + bar_width, 0.0),
        vec2(bar_x_base, bar_height),
        vec2(bar_x_base + bar_width, bar_height),
    );
    // Map [0,1] → NDC [-1, 1]
    let pos = corners[vidx] * 2.0 - vec2(1.0, 1.0);
    // ...
}
```

Each bar is one instance. For 60 windows × 3 metrics = 180 instances, rendered in a single `drawInstanced(4, 180)` call.

### TopicsChart: Stacked from GPU Texture

The topics distribution (`signals/topics_dist.bin`, shape [N, K]) is the largest signal. Rust uploads it as a 2D `R32Float` texture at project load. The stacked bar chart reads this texture directly:

```wgsl
// In signal_charts.wgsl

@group(0) @binding(3) var topics_texture: texture_2d<f32>;  // [N × K] pixels
@group(0) @binding(4) var topics_sampler: sampler;
@group(0) @binding(5) var<storage, read> topic_colors: array<vec4<f32>>;  // K colors

@fragment
fn fs_topics_stacked(in: VertexOutput) -> @location(0) vec4<f32> {
    // x: bin index, y: within-bin vertical
    let bin_f = in.uv.x * f32(uniforms.n_bins);
    let bin = u32(bin_f);

    // Average topics across paragraphs in this bin
    let paras_per_bin = uniforms.n_paragraphs / uniforms.n_bins;
    let para_start = bin * paras_per_bin;

    var accumulated = 0.0;
    for (var t = 0u; t < uniforms.n_topics; t++) {
        var bin_avg = 0.0;
        for (var p = para_start; p < para_start + paras_per_bin; p++) {
            let tex_u = (f32(p) + 0.5) / f32(uniforms.n_paragraphs);
            let tex_v = (f32(t) + 0.5) / f32(uniforms.n_topics);
            bin_avg += textureSample(topics_texture, topics_sampler, vec2(tex_u, tex_v)).r;
        }
        bin_avg /= f32(paras_per_bin);

        if in.uv.y >= accumulated && in.uv.y < accumulated + bin_avg {
            return topic_colors[t];
        }
        accumulated += bin_avg;
    }
    return vec4(0.95, 0.95, 0.96, 1.0);  // background
}
```

Note: the inner loop over `paras_per_bin` in the fragment shader runs on GPU and is parallelized across all pixels. For 50 bins × ~37 paragraphs per bin = 1,850 texture samples per pixel column, running across ~280 pixel columns = ~517,800 texture samples per frame. On M4's 40 GPU cores at 400 billion operations/second, this is well under 1ms.

### Tauri Commands for Signal Data

```rust
// src-tauri/src/commands/signals.rs

#[tauri::command]
pub fn get_rqa_signal(
    project_id: String,
    state: tauri::State<'_, AppState>,
) -> Result<RQAResponse, String> {
    let core = state.core.blocking_lock();
    let project = core.get_project(&project_id).ok_or("Project not found")?;
    let rqa = project.signal_store.rqa
        .as_ref().ok_or("RQA signal not computed")?;

    // Return all window metrics as a flat Vec<f32> (W × 3 values)
    // Small enough for JSON (max ~2400 bytes for 200 windows)
    let metrics: Vec<f32> = rqa.as_f32_slice().to_vec();
    Ok(RQAResponse {
        metrics,
        n_windows: rqa.n_windows,
        window_labels: project.rqa_manifest().window_character_ranges(),
    })
}

#[tauri::command]
pub fn get_topics_texture_handle(
    project_id: String,
    state: tauri::State<'_, AppState>,
) -> Result<GPUTextureHandle, String> {
    let core = state.core.blocking_lock();
    let project = core.get_project(&project_id).ok_or("Project not found")?;
    // topics_dist.bin already uploaded to GPU at project load (T23 pattern)
    project.gpu_textures.get("topics_dist")
        .ok_or("Topics distribution not computed".to_string())
        .cloned()
}
```

### SignalPanel

```typescript
// browser/src/components/SignalPanel/SignalPanel.tsx

export function SignalPanel({ projectId }: { projectId: string }): JSX.Element {
  return (
    <div className="signal-panel">
      <CollapsibleSection title="Narrative Arc">
        <NarrativeArcChart projectId={projectId} />
      </CollapsibleSection>
      <CollapsibleSection title="RQA">
        <RQAChart projectId={projectId} />
      </CollapsibleSection>
      <CollapsibleSection title="Narrative Alphabet">
        <AlphabetBarcode projectId={projectId} />
      </CollapsibleSection>
      <CollapsibleSection title="Topic Distribution">
        <TopicsChart projectId={projectId} />
      </CollapsibleSection>
    </div>
  );
}
```

Each child component manages its own GPU state. When a section collapses, the canvas is hidden (CSS), but GPU resources are retained.

### Performance Targets

| Chart | Render time | Notes |
|-------|-------------|-------|
| NarrativeArcChart | <1ms | 3 line strip draw calls |
| RQAChart | <1ms | 180 instances, single draw call |
| AlphabetBarcode | <1ms | Compute shader (29 workgroups) + 1 quad draw |
| TopicsChart | <1ms | Fragment shader with texture sampling |
| All 4 charts visible | <2ms total | Parallel GPU render passes |
| Track filter change → all charts update | <5ms | Rust recompute + GPU buffer update |

### Acceptance Criteria (v4.0)

- All 4 signal charts render via WebGPU canvas (no SVG elements, no D3 dependency)
- NarrativeArcChart: 3 visible curves rendered as GPU line primitives
- RQAChart: grouped bars rendered via instanced draw; RR/DET/LAM values in [0,1]
- AlphabetBarcode: 1,832 colored segments rendered by compute shader in <1ms
- TopicsChart: stacked distribution rendered from GPU texture
- SignalPanel renders gracefully (empty state) when any signal is unavailable
- Total DOM node count for all 4 charts: ≤5 (one `<canvas>` per chart)
- `tsc --strict` passes on all new files
- `cargo test` passes all signal Tauri command tests

### Tests

```typescript
test('NarrativeArcChart requests get_narrative_arc on mount', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  (invoke as ReturnType<typeof vi.fn>).mockResolvedValue({
    segments: Array(5).fill([0.3, 0.5, 0.2]),
    labels: ['staging', 'plot_progression', 'cognitive_tension'],
  });
  render(<NarrativeArcChart projectId="test" />);
  await waitFor(() => expect(invoke).toHaveBeenCalledWith('get_narrative_arc', { projectId: 'test' }));
});

test('SignalPanel renders 4 canvas elements', async () => {
  // Mock all 4 invoke calls
  const { invoke } = await import('@tauri-apps/api/core');
  (invoke as ReturnType<typeof vi.fn>).mockResolvedValue({});
  const { container } = render(<SignalPanel projectId="test" />);
  await waitFor(() => {
    expect(container.querySelectorAll('canvas')).toHaveLength(4);
  });
  expect(container.querySelectorAll('rect')).toHaveLength(0); // No SVG rects
  expect(container.querySelectorAll('path')).toHaveLength(0); // No SVG paths
});
```

---

## Original Content (Reference)

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 8 hours

### Context (original)

Four signal visualizations: NarrativeArcChart (D3 SVG sparklines), RQAChart (D3 bar chart), AlphabetBarcode (canvas barcode), TopicsChart (D3 stacked bars). Signals loaded via `SignalAdapter.ts` from HTTP endpoint.

### Design Decisions (original)

- **SVG for NarrativeArcChart and RQAChart, canvas for AlphabetBarcode**: SVG for interactive charts, canvas for barcode.
- **Downsampling TopicsChart to 50 bins**: 1,832 stacked bars invisible at 0.15px each.
- **Three Boyd curves, not all 15**: tension, resolution, orientation most interpretable.
- **D3 for charts**: Full control, existing `d3@^7` dependency.
