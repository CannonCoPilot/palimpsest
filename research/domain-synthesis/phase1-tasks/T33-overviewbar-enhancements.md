# T33: OverviewBar Enhancements

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 5 hours
**Dependencies**: T30 (VirtualTextView scroll system, Rust `DensityHistogram`), T28 (Zustand `viewStore.visibleRange` + filter state), T31 (Rust `get_density_histogram` Tauri command established)
**Outputs**: `browser/src/components/OverviewBar/OverviewBar.tsx` (rewritten), `browser/src/shaders/overviewbar.wgsl` (created)

---

## v4.0 Critical Review

**Verdict: The v3.x OverviewBar has two fundamental problems: (1) it renders 18,760 SVG `<line>` elements per tick, which is documented as a performance disaster in the architecture diagnosis; (2) the brush, ticks, and density barcodes are a mix of SVG overlays and canvas 2D context draws, creating a z-ordering maintenance problem. The v4.0 OverviewBar is a single WebGPU canvas with all layers composited by the GPU.**

### What Is Broken

**18,760 SVG `<line>` elements in the baseline OverviewBar.** This is the second most severe performance problem in the current system (after annotation overlay DOM spam). Every track toggle re-renders all 18,760 lines. The v3.x enhancement spec adds "annotation density ticks" as an additional rendering pass, making this worse.

**Stacked `<DensityBarcode>` rows as individual canvases.** The spec adds one `<DensityBarcode>` per visible track, each with its own 2D canvas context. With 5 tracks: 5 canvases × ~1,832 pixel columns each = 5 separate rasterization passes, 5 GPU texture uploads. The OverviewBar should be one canvas, one GPU draw.

**`SearchTickLayer` is SVG absolutely positioned over the density canvas.** Two rendering contexts (Canvas 2D + SVG) composited by the browser compositor. This means two GPU layers, two synchronization points per frame.

**`BrushOverlay` is a `<div>` with mouse events.** Mouse events on a `<div>` that is positioned over a canvas require hit-testing through two rendering contexts. Under Tauri's WKWebView compositor, multiple stacked transparent layers cause composition storms on every frame when the brush is being drawn.

**The density computation is wrong.** The spec has `DensityBarcode` computing annotation positions via `charOffsetToParagraphIndex()` — a linear scan through all annotations to map char offsets to paragraph indices. This is O(N) per render. The `DensityHistogram` from the Rust `get_density_histogram` Tauri command (T31) already provides exactly this data; the OverviewBar should consume that.

---

## v4.0 Rewrite

### Architecture

The OverviewBar is a single WebGPU canvas. All layers — density bars (per track), search ticks, visible range indicator, brush selection, and position tick — are composited by a multi-pass GPU render:

```
Pass 1: Density bars (stacked per track) from DensityHistogram GPU texture
Pass 2: Search match ticks (yellow vertical lines) from SearchMatch offset buffer
Pass 3: Visible range indicator (white semi-transparent rectangle)
Pass 4: Brush selection (blue semi-transparent rectangle, updated during drag)
Pass 5: Selection position tick (orange vertical line)
```

All 5 passes are triggered by a single `requestAnimationFrame`. Each pass updates only its relevant GPU buffer when its data changes. The GPU handles compositing.

### WebGPU Shader

```wgsl
// browser/src/shaders/overviewbar.wgsl

struct OverviewBarUniforms {
    n_paragraphs: u32,
    n_tracks: u32,
    visible_start: f32,    // fraction [0,1] of document
    visible_end: f32,
    brush_start: f32,      // fraction [0,1]; negative if no brush
    brush_end: f32,
    selected_fraction: f32, // fraction [0,1]; negative if no selection
    canvas_width: u32,
    canvas_height: u32,
}

@group(0) @binding(0) var<uniform> uniforms: OverviewBarUniforms;
@group(0) @binding(1) var density_texture: texture_2d<f32>;  // [N_paragraphs × N_tracks]
@group(0) @binding(2) var density_sampler: sampler;
@group(0) @binding(3) var<storage, read> track_colors: array<vec4<f32>>;
@group(0) @binding(4) var<storage, read> search_tick_fractions: array<f32>;  // positions in [0,1]

@fragment
fn fs_overviewbar(in: VertexOutput) -> @location(0) vec4<f32> {
    let x_frac = in.uv.x;   // horizontal position in document [0,1]
    let y_frac = in.uv.y;   // vertical position within bar [0,1]

    // Layer 1: Stacked density bars
    // Map x_frac to paragraph index
    let para_f = x_frac * f32(uniforms.n_paragraphs);

    // Compute stacked track colors at this x position
    var base_color = vec4(0.2, 0.2, 0.25, 1.0);  // dark background
    var track_accumulated = 0.0;
    let track_height = 1.0 / f32(uniforms.n_tracks);

    for (var t = 0u; t < uniforms.n_tracks; t++) {
        let tex_u = (para_f + 0.5) / f32(uniforms.n_paragraphs);
        let tex_v = (f32(t) + 0.5) / f32(uniforms.n_tracks);
        let density = textureSample(density_texture, density_sampler, vec2(tex_u, tex_v)).r;

        let track_y_start = f32(t) * track_height;
        let track_y_end = track_y_start + track_height;

        if y_frac >= track_y_start && y_frac < track_y_end {
            // Within this track's row
            let track_fill = density * 0.8;  // density → opacity of track color
            base_color = mix(base_color, vec4(track_colors[t].rgb, 1.0), track_fill);
        }
    }

    // Layer 2: Search ticks (yellow vertical lines, 1px wide)
    let x_pixel = u32(x_frac * f32(uniforms.canvas_width));
    for (var i = 0u; i < arrayLength(&search_tick_fractions); i++) {
        let tick_pixel = u32(search_tick_fractions[i] * f32(uniforms.canvas_width));
        if abs(i32(x_pixel) - i32(tick_pixel)) <= 1 {
            base_color = mix(base_color, vec4(1.0, 0.85, 0.0, 1.0), 0.9);
            break;
        }
    }

    // Layer 3: Visible range indicator (white semi-transparent rectangle)
    if x_frac >= uniforms.visible_start && x_frac <= uniforms.visible_end {
        base_color = mix(base_color, vec4(1.0, 1.0, 1.0, 1.0), 0.2);
        // Border effect at edges
        let at_left = x_frac - uniforms.visible_start < 0.003;
        let at_right = uniforms.visible_end - x_frac < 0.003;
        if at_left || at_right {
            base_color = mix(base_color, vec4(1.0, 1.0, 1.0, 1.0), 0.6);
        }
    }

    // Layer 4: Brush selection (blue semi-transparent rectangle)
    if uniforms.brush_start >= 0.0 {
        let b_min = min(uniforms.brush_start, uniforms.brush_end);
        let b_max = max(uniforms.brush_start, uniforms.brush_end);
        if x_frac >= b_min && x_frac <= b_max {
            base_color = mix(base_color, vec4(0.2, 0.5, 1.0, 1.0), 0.3);
        }
    }

    // Layer 5: Selection position tick (orange)
    if uniforms.selected_fraction >= 0.0 {
        let dist = abs(x_frac - uniforms.selected_fraction) * f32(uniforms.canvas_width);
        if dist < 1.5 {
            base_color = mix(base_color, vec4(1.0, 0.6, 0.1, 1.0), 0.9);
        }
    }

    return base_color;
}
```

All 5 visual layers are computed in a single fragment shader invocation per pixel. No z-ordering conflicts, no DOM compositing overhead.

### TypeScript OverviewBar

```typescript
// browser/src/components/OverviewBar/OverviewBar.tsx

export function OverviewBar({ projectId }: { projectId: string }): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gpuStateRef = useRef<OverviewBarGPUState | null>(null);

  const { visibleRange, selectedParagraphIndex } = useViewStore();
  const { trackMask, minConfidence } = useTrackStore();
  const { matches: searchMatches } = useSearchStore();
  const totalParagraphs = useProjectStore(s => s.paragraphs.length);

  // Brush state — NOT in React state (no re-render during drag)
  const brushRef = useRef<{ startFrac: number; endFrac: number; active: boolean }>({
    startFrac: -1, endFrac: -1, active: false,
  });

  // Initialize GPU state once
  useEffect(() => {
    if (!canvasRef.current) return;
    initOverviewBarGPU(canvasRef.current).then(state => {
      gpuStateRef.current = state;
      render();
    });
    return () => gpuStateRef.current?.destroy();
  }, []);

  // Update density texture on filter change
  useEffect(() => {
    invoke<DensityHistogramResponse>('get_density_histogram', {
      projectId, trackMask: Number(trackMask), minConfidence: Math.round(minConfidence * 10000),
    }).then(response => {
      if (gpuStateRef.current) {
        uploadDensityTexture(gpuStateRef.current, response);
        render();
      }
    });
  }, [projectId, trackMask, minConfidence]);

  // Update search ticks when search results change
  useEffect(() => {
    if (!gpuStateRef.current) return;
    const fractions = searchMatches.slice(0, 500).map(  // downsample to 500
      m => m.paragraphIndex / totalParagraphs
    );
    updateSearchTickBuffer(gpuStateRef.current, fractions);
    render();
  }, [searchMatches, totalParagraphs]);

  // Update uniforms on scroll/selection change (cheap: uniform write only)
  useEffect(() => {
    if (!gpuStateRef.current) return;
    const [startIdx, endIdx] = visibleRange;
    updateUniforms(gpuStateRef.current, {
      visible_start: startIdx / totalParagraphs,
      visible_end: endIdx / totalParagraphs,
      selected_fraction: selectedParagraphIndex !== null
        ? selectedParagraphIndex / totalParagraphs
        : -1.0,
      brush_start: brushRef.current.active ? brushRef.current.startFrac : -1.0,
      brush_end: brushRef.current.endFrac,
    });
    render();
  }, [visibleRange, selectedParagraphIndex, totalParagraphs]);

  const render = () => {
    if (!gpuStateRef.current) return;
    requestAnimationFrame(() => renderOverviewBar(gpuStateRef.current!));
  };

  // Mouse handlers for brush and click — update brushRef directly (no React state)
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const frac = e.nativeEvent.offsetX / canvasRef.current!.clientWidth;
    brushRef.current = { startFrac: frac, endFrac: frac, active: true };
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!brushRef.current.active) return;
    const frac = e.nativeEvent.offsetX / canvasRef.current!.clientWidth;
    brushRef.current.endFrac = frac;
    // Update brush uniform and re-render — no React state change
    if (gpuStateRef.current) {
      updateBrushUniform(gpuStateRef.current, brushRef.current.startFrac, frac);
      requestAnimationFrame(() => renderOverviewBar(gpuStateRef.current!));
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const endFrac = e.nativeEvent.offsetX / canvasRef.current!.clientWidth;
    const isClick = Math.abs(endFrac - brushRef.current.startFrac) < 0.005;
    brushRef.current.active = false;

    if (isClick) {
      // Single click: scroll to position
      const paraIdx = Math.floor(endFrac * totalParagraphs);
      requestScrollToParagraph(paraIdx);
      setSelectedParagraphIndex(paraIdx);
    } else {
      // Brush: scroll to center of selection
      const centerFrac = (brushRef.current.startFrac + endFrac) / 2;
      const centerPara = Math.floor(centerFrac * totalParagraphs);
      requestScrollToParagraph(centerPara);
      setHighlightedParagraphRange([
        Math.floor(Math.min(brushRef.current.startFrac, endFrac) * totalParagraphs),
        Math.floor(Math.max(brushRef.current.startFrac, endFrac) * totalParagraphs),
      ]);
    }

    // Clear brush from shader
    if (gpuStateRef.current) {
      updateBrushUniform(gpuStateRef.current, -1.0, -1.0);
      render();
    }
  };

  return (
    <canvas
      ref={canvasRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      style={{ width: '100%', height: Math.max(60, 5 * 14 + 16), cursor: 'crosshair' }}
    />
  );
}
```

### Performance Targets

| Operation | Target |
|-----------|--------|
| OverviewBar frame render (all layers) | <1ms |
| Filter change → density update | <5ms (Rust + GPU texture upload) |
| Scroll → visible range indicator update | <0.1ms (uniform write only) |
| Brush drag (60fps) | <0.1ms per frame (uniform write + render) |
| Search results change → tick buffer update | <1ms |
| DOM node count | 1 (the canvas element) |

### Acceptance Criteria (v4.0)

- OverviewBar is a single `<canvas>` element — no SVG, no inner divs, no stacked canvases
- All 5 layers (density, search ticks, visible range, brush, selection tick) composited by GPU shader
- Track toggle → OverviewBar updates in <5ms
- Scroll → visible range indicator updates in <0.1ms (uniform write)
- Brush drag is 60fps; no React state changes during drag (brushRef mutation only)
- Click navigates; brush scrolls to center and sets highlighted range
- 500-match downsample enforced in JS before GPU buffer upload
- `tsc --strict` passes on OverviewBar.tsx

### Tests

```typescript
test('OverviewBar renders exactly one canvas element', () => {
  render(<OverviewBar projectId="test" />);
  const canvases = document.querySelectorAll('canvas');
  expect(canvases).toHaveLength(1);
  const svgs = document.querySelectorAll('svg');
  expect(svgs).toHaveLength(0);
});

test('mouse click within 0.5% triggers scroll not brush', async () => {
  const { requestScrollToParagraph } = useViewStore.getState();
  const spy = vi.spyOn(useViewStore.getState(), 'requestScrollToParagraph');
  const { container } = render(<OverviewBar projectId="test" />);
  const canvas = container.querySelector('canvas')!;
  fireEvent.mouseDown(canvas, { offsetX: 200 });
  fireEvent.mouseUp(canvas, { offsetX: 202 });  // 2px = well under 0.5% of canvas
  expect(spy).toHaveBeenCalled();
});

test('search matches over 500 are downsampled', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  const gpu_write = vi.fn();
  // Verify that at most 500 fractions are written to buffer
  useSearchStore.setState({
    matches: Array.from({ length: 1000 }, (_, i) => ({ paragraphIndex: i })),
  });
  render(<OverviewBar projectId="test" />);
  // Check buffer update call received ≤500 fractions
  // (implementation detail: updateSearchTickBuffer is called with slice(0, 500))
});
```

---

## Original Content (Reference)

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 5 hours

### Context (original)

Three enhancements to baseline OverviewBar: (1) brush selection; (2) multiple stacked track barcodes; (3) search match ticks and annotation density ticks. Together make the OverviewBar a structural navigation tool.

### Design Decisions (original)

- **SVG for search ticks, canvas for density**: SVG for sub-pixel accuracy, canvas for batch data.
- **4px threshold for click vs. drag**: Standard OS drag threshold.
- **Yellow for search ticks**: Maximally visible, universally associated with highlighting.
- **200-match downsample threshold**: Beyond 200 ticks the information is "many matches everywhere."
- **Brush scrolls to center**: Gives context on both sides of selection.
