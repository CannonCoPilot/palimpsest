# T27: DotplotView

**Milestone**: 1.3b — BookNLP + DotplotView
**Estimated effort**: 10 hours (Days 34-36)
**Dependencies**: T23 (self_similarity.bin produced + GPU texture uploaded), T09 (browser scaffolding), `SimilarityTexture` handle from Tauri AppState
**Outputs**: `browser/src/components/DotplotView/DotplotView.tsx`, `browser/src/components/DotplotView/DotplotCanvas.tsx`, `browser/src/shaders/dotplot.wgsl`, `browser/src/stores/viewStore.ts` (modified)

---

## v4.0 Critical Review

**Verdict: The Canvas ImageData approach is fundamentally the wrong rendering technology for an N×N similarity matrix. Writing 1M pixels to a Uint8ClampedArray in a JavaScript loop, then calling putImageData once, is 1M iterations of JS-to-ArrayBuffer writes. For a 1,000×1,000 matrix this takes 50-200ms in practice — not "under 1 second" as the original spec claims; measured under realistic conditions with the color mapping computation included, it will frequently blow the 16ms frame budget on scroll interactions. The fix is WebGPU: the matrix is already a GPU texture (from T23). The dotplot renders with a single draw call in a fragment shader.**

### What Is Broken

**`putImageData` is not a GPU operation.** It copies a CPU-side ArrayBuffer into a software canvas backing store that the browser compositor then uploads to GPU for display. For a 1,000×1,000 matrix that is 4MB of CPU memory, written by a JavaScript loop, transferred to GPU. There is no shader involved. This is CPU-bound software rendering.

**The color mapping loop `similarityToColor(score)` is called 1M times for a 1,000×1,000 matrix.** Linear RGB interpolation in JavaScript: 3 multiplications + 3 additions + string formatting per pixel = 7M+ JS arithmetic operations. Even at 1 ns per operation that is 7ms of CPU time, in addition to the memory write time. For a 2,000×2,000 matrix (Phase 2 with larger novels) this is 28ms — more than the 16ms frame budget.

**`Float32Array` for the full matrix lives in the JS heap.** For a 1,800×1,800 P&P matrix, `Float32Array` of 3.24M elements = 12.96MB in the WKWebView V8 heap. For five novels at Phase 2 scale: 64MB+ of Float32Arrays in the JS heap, alongside annotation data, React state, and all other browser overhead. The v4.0 architecture explicitly moves all data out of the JS heap and into Rust/GPU.

**The `CSS transform: scale(...)` zoom approach** does not provide analytical fidelity at zoom-in. The user needs to read individual cell values when zoomed in. CSS scaling just upscales pixels — the tooltip must read from the original matrix (which is now a GPU texture, not a JS array). The interaction model needs to be redesigned.

**"CSS overflow: hidden + programmatic scrollLeft/scrollTop"** for pan is wrong for a GPU-rendered surface. WebGPU renders to a canvas; panning changes the viewport matrix in the shader, not the DOM scroll position.

---

## v4.0 Rewrite

### Architecture

The DotplotView is a WebGPU render pass. The similarity matrix is already a `wgpu::Texture` uploaded in T23. The render pipeline:

1. **Fragment shader** samples the `R32Float` texture at UV coordinates corresponding to cell (i, j)
2. **Color LUT** is a 1D `Rgba8Unorm` texture, pre-computed from the `white-to-dark-blue` gradient, sampled by the fragment shader
3. **Uniform buffer** holds viewport state: `(offset_x, offset_y, zoom, n, selected_row, selected_col)`
4. **Row/column highlight** is a second render pass that draws two 1-pixel-wide quads in semi-transparent blue

All rendering happens in the GPU. The CPU side triggers re-renders by updating the uniform buffer (cheap) and calling `requestAnimationFrame`. Zero JS loops over pixel data.

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Similarity data | `wgpu::Texture` (`R32Float`, N×N) — already on GPU from T23 |
| Color mapping | 1D `Rgba8Unorm` LUT texture, 256 entries |
| Render pipeline | WebGPU `GPURenderPipeline` with custom WGSL shaders |
| Viewport control | Uniform buffer updated on pan/zoom; no DOM scroll |
| Interaction | JS mouse event → compute (i, j) from GPU viewport matrix → update uniforms |
| Chapter overlays | Second render pass: line primitives from segment_offsets buffer |
| Row/column highlight | Overlay render pass: two quads, blended |
| Tooltip | Off-GPU: JS computes (i, j) from mouse position + viewport uniforms |

### WGSL Shaders

```wgsl
// browser/src/shaders/dotplot.wgsl

struct Uniforms {
    n: u32,                 // matrix dimension
    offset_x: f32,          // viewport pan X (in matrix cells)
    offset_y: f32,          // viewport pan Y (in matrix cells)
    zoom: f32,              // cells per canvas pixel (>1 = zoomed out)
    selected_row: i32,      // -1 if no selection
    selected_col: i32,
}

@group(0) @binding(0) var<uniform> uniforms: Uniforms;
@group(0) @binding(1) var similarity_texture: texture_2d<f32>;
@group(0) @binding(2) var similarity_sampler: sampler;
@group(0) @binding(3) var color_lut: texture_1d<f32>;
@group(0) @binding(4) var lut_sampler: sampler;

struct VertexOutput {
    @builtin(position) pos: vec4<f32>,
    @location(0) uv: vec2<f32>,
}

// Full-screen quad vertex shader
@vertex
fn vs_main(@builtin(vertex_index) idx: u32) -> VertexOutput {
    var positions = array<vec2<f32>, 4>(
        vec2(-1.0, -1.0), vec2(1.0, -1.0),
        vec2(-1.0,  1.0), vec2(1.0,  1.0),
    );
    var uvs = array<vec2<f32>, 4>(
        vec2(0.0, 1.0), vec2(1.0, 1.0),
        vec2(0.0, 0.0), vec2(1.0, 0.0),
    );
    var out: VertexOutput;
    out.pos = vec4(positions[idx], 0.0, 1.0);
    out.uv = uvs[idx];
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    // Convert canvas UV → matrix cell (i, j) via viewport transform
    let canvas_cell_x = in.uv.x / uniforms.zoom;
    let canvas_cell_y = in.uv.y / uniforms.zoom;
    let matrix_x = uniforms.offset_x + canvas_cell_x;
    let matrix_y = uniforms.offset_y + canvas_cell_y;

    // Out of bounds → background color
    if matrix_x < 0.0 || matrix_x >= f32(uniforms.n) ||
       matrix_y < 0.0 || matrix_y >= f32(uniforms.n) {
        return vec4(0.15, 0.15, 0.18, 1.0);  // dark background
    }

    // Sample similarity texture (nearest-neighbor when zoomed in, linear when zoomed out)
    let tex_uv = vec2(matrix_x / f32(uniforms.n), matrix_y / f32(uniforms.n));
    let similarity = textureSample(similarity_texture, similarity_sampler, tex_uv).r;

    // Map similarity [0,1] → color via LUT
    let lut_u = clamp(similarity, 0.0, 1.0);
    var color = textureSample(color_lut, lut_sampler, lut_u);

    // Row/column highlight
    let row = i32(matrix_y);
    let col = i32(matrix_x);
    if uniforms.selected_row >= 0 {
        if row == uniforms.selected_row || col == uniforms.selected_row {
            color = mix(color, vec4(0.2, 0.5, 1.0, 1.0), 0.35);
        }
    }

    return color;
}
```

The entire dotplot — including color mapping, row/column highlight, and zoom — is computed in the fragment shader. No JavaScript loops over pixel data.

### TypeScript: DotplotCanvas Component

```typescript
// browser/src/components/DotplotView/DotplotCanvas.tsx

interface DotplotCanvasProps {
  textureHandle: SimilarityTextureHandle; // from Tauri, contains GPU texture ID
  n: number;
  segmentOffsets: [number, number][];
  selectedParagraphIndex: number | null;
  onCellClick: (i: number, j: number) => void;
  onCellHover: (i: number, j: number, similarity: number) => void;
}

// Internal viewport state — NOT in React state (no re-render on pan/zoom)
interface Viewport {
  offsetX: number;  // cells
  offsetY: number;
  zoom: number;     // canvas pixels per cell; >1 = zoomed out, <1 = zoomed in
}

export function DotplotCanvas({
  textureHandle, n, segmentOffsets, selectedParagraphIndex,
  onCellClick, onCellHover,
}: DotplotCanvasProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gpuStateRef = useRef<DotplotGPUState | null>(null);
  const viewportRef = useRef<Viewport>({ offsetX: 0, offsetY: 0, zoom: 1.0 });

  // Initialize WebGPU pipeline on mount
  useEffect(() => {
    const canvas = canvasRef.current!;
    initDotplotGPU(canvas, textureHandle).then(state => {
      gpuStateRef.current = state;
      render();
    });
    return () => gpuStateRef.current?.destroy();
  }, [textureHandle]);

  // Re-render whenever selection changes (cheap: just update uniform buffer)
  useEffect(() => {
    updateUniforms();
    render();
  }, [selectedParagraphIndex]);

  const updateUniforms = () => {
    const state = gpuStateRef.current;
    if (!state) return;
    const { offsetX, offsetY, zoom } = viewportRef.current;
    const uniformData = new Float32Array([
      n, offsetX, offsetY, zoom,
      selectedParagraphIndex ?? -1, selectedParagraphIndex ?? -1,
    ]);
    state.device.queue.writeBuffer(state.uniformBuffer, 0, uniformData);
  };

  const render = () => {
    const state = gpuStateRef.current;
    if (!state) return;
    // Single draw call: 2 triangles (full-screen quad)
    const encoder = state.device.createCommandEncoder();
    const pass = encoder.beginRenderPass(state.renderPassDescriptor);
    pass.setPipeline(state.pipeline);
    pass.setBindGroup(0, state.bindGroup);
    pass.draw(4); // 4 vertices of full-screen quad
    pass.end();
    state.device.queue.submit([encoder.finish()]);
  };

  // Pan: mouse drag updates viewportRef directly, calls render() via rAF
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (e.buttons === 1) {
      // Dragging: pan
      const dpr = window.devicePixelRatio;
      viewportRef.current.offsetX -= (e.movementX / dpr) * viewportRef.current.zoom;
      viewportRef.current.offsetY -= (e.movementY / dpr) * viewportRef.current.zoom;
      updateUniforms();
      requestAnimationFrame(render);
    } else {
      // Hovering: compute (i, j), fetch similarity from GPU (via readback or CPU-side)
      const [i, j, similarity] = mouseToCell(e, viewportRef.current, n, canvasRef.current!);
      if (i >= 0 && i < n && j >= 0 && j < n) {
        onCellHover(i, j, similarity);
      }
    }
  }, [n, viewportRef, onCellHover]);

  // Zoom: wheel event updates zoom factor
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 1.15 : 0.87;
    viewportRef.current.zoom = Math.max(0.1, Math.min(100.0,
      viewportRef.current.zoom * factor
    ));
    updateUniforms();
    requestAnimationFrame(render);
  }, [viewportRef]);

  return (
    <canvas
      ref={canvasRef}
      onMouseMove={handleMouseMove}
      onWheel={handleWheel}
      onClick={e => {
        const [i, j] = mouseToCell(e, viewportRef.current, n, canvasRef.current!).slice(0, 2) as [number, number];
        if (i >= 0 && j >= 0) onCellClick(i, j);
      }}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  );
}
```

### Similarity Readback for Tooltip

When the user hovers a cell, we need the similarity value for the tooltip. Two options:
1. GPU readback (`copyBufferToBuffer` + `mapAsync`) — accurate but ~1-2ms latency
2. CPU-side lookup — read `self_similarity.bin` as a mmap'd Float32Array in the Tauri app, expose via `get_similarity(i, j)` Tauri command

Option 2 is chosen: Rust reads the mmap'd binary at O(1) via `similarity.bin[i * n + j]`. The tooltip call `invoke('get_similarity', {projectId, i, j})` returns a single f32 in <1ms.

### Chapter Boundary Overlay

A second render pass draws horizontal and vertical lines at chapter boundary paragraph indices:

```wgsl
// browser/src/shaders/dotplot_overlay.wgsl

@group(0) @binding(0) var<uniform> uniforms: Uniforms;
@group(0) @binding(5) var<storage> boundaries: array<u32>; // paragraph indices at chapter starts

@fragment
fn fs_overlay(in: VertexOutput) -> @location(0) vec4<f32> {
    let matrix_x = uniforms.offset_x + in.uv.x / uniforms.zoom;
    let matrix_y = uniforms.offset_y + in.uv.y / uniforms.zoom;

    // Check if this pixel is within 0.5 matrix-cells of any boundary
    for (var b = 0u; b < arrayLength(&boundaries); b++) {
        let boundary = f32(boundaries[b]);
        if abs(matrix_x - boundary) < 0.5 || abs(matrix_y - boundary) < 0.5 {
            return vec4(0.7, 0.7, 0.7, 0.6);  // semi-transparent gray
        }
    }
    discard;
}
```

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Initial GPU texture upload (12.96MB, P&P) | <16ms | Done in T23 at project load |
| Frame render (full dotplot, any size) | <1ms | Single draw call + fragment shader |
| Pan (mouse drag → next frame) | <16ms (60fps) | Uniform buffer update only |
| Zoom (wheel → next frame) | <16ms (60fps) | Uniform buffer update only |
| Selection change → highlight update | <1ms | Uniform write + re-draw |
| Tooltip similarity readback | <1ms | Rust mmap O(1) lookup |
| Phase 2: 3,000×3,000 matrix (36MB) | <16ms first frame | Same shader, larger texture |

### TypeScript DotplotView Outer Component

```typescript
// browser/src/components/DotplotView/DotplotView.tsx

export function DotplotView(): JSX.Element {
  const { dotplotOpen } = useViewStore();
  const { selectedParagraphIndex, setSelectedParagraphIndex, requestScrollToParagraph } = useViewStore();
  const projectId = useProjectStore(s => s.primaryProjectId);

  const [textureHandle, setTextureHandle] = useState<SimilarityTextureHandle | null>(null);
  const [manifest, setManifest] = useState<SelfSimilarityManifest | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredCell, setHoveredCell] = useState<{i: number; j: number; sim: number} | null>(null);

  useEffect(() => {
    if (!dotplotOpen || !projectId) return;
    setLoading(true);
    // Load GPU texture via Tauri command (defined in T23)
    invoke<SimilarityTextureHandle>('load_self_similarity_texture', { projectId })
      .then(handle => {
        setTextureHandle(handle);
        return invoke<SelfSimilarityManifest>('get_signal_manifest', {
          projectId, signalName: 'self_similarity'
        });
      })
      .then(setManifest)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [dotplotOpen, projectId]);

  if (!dotplotOpen) return <></>;

  return (
    <div className="dotplot-view" style={{ position: 'relative', width: '100%', height: '100%' }}>
      {loading && <LoadingSpinner label="Loading similarity matrix..." />}
      {error && (
        <ErrorState message={error} hint="Run 'palimpsest analyze' to compute self-similarity data." />
      )}
      {textureHandle && manifest && (
        <>
          <DotplotCanvas
            textureHandle={textureHandle}
            n={manifest.dimensions[0]}
            segmentOffsets={manifest.segment_offsets ?? []}
            selectedParagraphIndex={selectedParagraphIndex}
            onCellClick={(i, j) => {
              setSelectedParagraphIndex(i);
              requestScrollToParagraph(i);
            }}
            onCellHover={async (i, j) => {
              const sim = await invoke<number>('get_similarity_value', { projectId, i, j });
              setHoveredCell({ i, j, sim });
            }}
          />
          {hoveredCell && (
            <div className="dotplot-tooltip" style={{ position: 'absolute', top: 8, right: 8, pointerEvents: 'none' }}>
              Para {hoveredCell.i} × Para {hoveredCell.j}: {(hoveredCell.sim * 100).toFixed(1)}%
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

### Acceptance Criteria (v4.0)

- DotplotView renders in <1ms per frame at any matrix size (WebGPU fragment shader)
- Pan and zoom are 60fps (uniform buffer update, no re-render)
- For P&P (N=1,800): block-diagonal chapter structure is visually apparent
- Chapter boundary overlay lines are visible as semi-transparent gray lines
- Clicking cell (i, j) sets `viewStore.selectedParagraphIndex = i` and triggers TextLinearView scroll
- Hovering shows tooltip with row, col, and similarity value in <1ms (Rust mmap lookup)
- `d` keyboard shortcut toggles panel open/closed
- No JS heap allocation on pan/zoom (confirmed via Chrome DevTools Memory panel — allocation timeline flat during interaction)
- Phase 2 readiness: same shader handles 3,000×3,000 matrix without modification

### Tests

```typescript
// browser/src/components/DotplotView/DotplotView.test.tsx

import { vi } from 'vitest';
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

test('DotplotView calls load_self_similarity_texture on open', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  (invoke as ReturnType<typeof vi.fn>).mockResolvedValue({ handle: 42, n: 100 });
  const store = useViewStore.getState();
  store.setDotplotOpen(true);
  render(<DotplotView />);
  await waitFor(() => {
    expect(invoke).toHaveBeenCalledWith('load_self_similarity_texture',
      expect.objectContaining({ projectId: expect.any(String) })
    );
  });
});

test('DotplotView shows error state when invoke fails', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  (invoke as ReturnType<typeof vi.fn>).mockRejectedValue('self_similarity.bin not found');
  useViewStore.getState().setDotplotOpen(true);
  render(<DotplotView />);
  await screen.findByText(/run.*palimpsest analyze/i);
});

test('mouseToCell converts mouse position to matrix cell correctly', () => {
  const canvas = { width: 400, height: 400 } as HTMLCanvasElement;
  const viewport = { offsetX: 0, offsetY: 0, zoom: 1.0 };
  const n = 100;
  // Mouse at canvas center (200, 200) → cell (50, 50)
  const [i, j] = mouseToCell({ clientX: 200, clientY: 200 } as MouseEvent, viewport, n, canvas);
  expect(i).toBe(50);
  expect(j).toBe(50);
});
```

```rust
// src-tauri/src/commands/signals_tests.rs

#[test]
fn test_get_similarity_value_range() {
    let state = mock_state_with_similarity_matrix(10);
    // Diagonal must be 1.0
    let diag = get_similarity_value("p".to_string(), 5, 5, state.clone()).unwrap();
    assert!((diag - 1.0).abs() < 1e-5);
    // Off-diagonal must be in [0, 1]
    let off = get_similarity_value("p".to_string(), 3, 7, state).unwrap();
    assert!((0.0..=1.0).contains(&off));
}
```

---

## Original Content (Reference)

**Milestone**: 1.3b — BookNLP + DotplotView
**Estimated effort**: 10 hours (Days 34-36)

### Context (original)

The DotplotView renders the self-similarity matrix as a 2D heatmap on an HTML Canvas element. Each pixel at position (i, j) is colored according to cosine similarity between paragraphs i and j. This is the visually distinctive feature of Palimpsest. Performance: a 1,000×1,000 matrix must render in under 1 second.

### Design Decisions (original)

- **ImageData bulk write, not fillRect**: Writing directly to Uint8ClampedArray and calling putImageData once.
- **CSS scale for zoom, not canvas re-render**: Scales canvas element via CSS transform.
- **Secondary view slot, not inline**: DotplotView renders in collapsible bottom panel.
- **selectedIndex highlights row and column**: Selection shown as row and column highlight overlay.
