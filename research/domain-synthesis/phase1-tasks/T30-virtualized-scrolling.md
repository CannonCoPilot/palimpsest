# T30: Virtualized Scrolling

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 10 hours
**Dependencies**: T09 (VirtualTextView design spec), T28 (Rust AnnotStore + Tauri `query_viewport` command)
**Outputs**: `browser/src/components/TextLinearView/VirtualTextView.tsx` (created), `browser/src/components/TextLinearView/CanvasAnnotationOverlay.tsx` (created), Tauri command `query_viewport` in `src-tauri/src/commands/viewport.rs`

---

## v4.0 Critical Review

**Verdict: The VirtualScroller in v3.x is a React component with DOM-based absolute positioning. The performance ceiling of this approach is real but not the dominant failure. The dominant failure is that each "visible" paragraph fetches its annotations from a React prop that contains ALL 18,760 annotations — the virtualization only limits DOM nodes, not annotation data. The v4.0 virtual scroller must be built on a fundamentally different model: Rust provides only the annotations for the visible viewport, and the annotation layer is a Canvas, not DOM spans.**

### What Is Broken

**The `renderItem` callback in v3.x receives annotations from a parent prop.** That parent prop is populated by `annotationsForParagraph(index)` which filters the full annotation array. Even with 30 virtual DOM nodes, each of those 30 nodes still calls `annotationsForParagraph` which scans all 18,760 annotations. The VirtualScroller limits DOM element count but leaves the 48M comparison problem entirely intact.

**ResizeObserver per element.** The v3.x spec creates a `ResizeObserver` instance for each rendered paragraph. With 30 visible paragraphs, that is 30 ResizeObservers. Creating and destroying them on scroll is non-trivial overhead. A single ResizeObserver observing all visible paragraphs is cheaper.

**`computeOffset` prefix sum in a loop.** The v3.x spec computes `cumulativeOffsets` by summing all heights from 0 to index N in a loop. For 1,832 paragraphs this is O(N) per scroll event after height updates. Use a Fenwick tree (Binary Indexed Tree) for O(log N) prefix sum update and query.

**Intersection Observer for annotation loading.** IntersectionObserver's callback is asynchronous — it fires after the browser's layout pass. This means annotations appear one paint cycle after the paragraph becomes visible, causing a visible flash of un-annotated text. The correct approach is to load annotations for the overscan zone ahead of scroll, so annotations are ready before the paragraph enters the viewport.

**The AnnotationOverlay creates thousands of `<mark>` spans.** Even for 30 visible paragraphs with 5 active tracks, a dialogue-heavy scene can have 20+ annotations per paragraph = 600 `<mark>` elements. The v4.0 architecture replaces all annotation DOM elements with a Canvas overlay.

---

## v4.0 Rewrite

### Architecture

The VirtualTextView is built on three layers:

1. **Scroll container**: a `<div>` with `overflow-y: scroll` containing a spacer div of correct total height. Only 30-50 paragraph `<div>` elements exist in the DOM at any time, absolutely positioned.

2. **Text layer**: each visible paragraph renders its text as plain HTML `<p>`. No annotation spans. No `<mark>` elements. Pure text.

3. **Canvas annotation overlay**: a single `<canvas>` element covering the entire scroll container viewport. It is updated by the `CanvasAnnotationOverlay` component on every scroll and filter change. Annotation highlights are colored rectangles drawn at computed pixel positions using character offset → pixel position mapping.

The Tauri command `query_viewport` is the single source of annotation truth:

```
scroll event fires
  → compute visible paragraph range (start_char, end_char)
  → invoke('query_viewport', {projectId, startChar, endChar, trackMask, minConfidence})
  → Rust: RangeIndex.query(start, end) → annotation indices
  → Rust: FilterEngine.filter(indices, trackMask, minConfidence) → BitVec
  → Rust: collect filtered AnnotationRecords → Vec<ViewportAnnotation>
  → frontend: CanvasAnnotationOverlay.repaint(paragraphRects, viewportAnnotations)
  → 30 canvas rectangles drawn
```

Total time: <5ms on any scroll event.

### Data Structures

```typescript
// browser/src/types/viewport.ts

interface ViewportAnnotation {
  start: number;          // char offset
  end: number;            // char offset
  trackId: number;        // 0-255
  confidence: number;     // 0.0-1.0
  color: string;          // resolved from track color scheme
}

interface ParagraphRect {
  index: number;
  top: number;            // px, relative to scroll container top
  height: number;         // px
  charStart: number;
  charEnd: number;
}
```

### Rust `query_viewport` Command

```rust
// src-tauri/src/commands/viewport.rs

#[derive(serde::Serialize)]
pub struct ViewportAnnotation {
    pub start: u32,
    pub end: u32,
    pub track_id: u8,
    pub confidence: f32,
}

#[tauri::command]
pub fn query_viewport(
    project_id: String,
    start_char: u32,
    end_char: u32,
    track_mask: u64,
    min_confidence: u16,
    state: tauri::State<'_, AppState>,
) -> Result<Vec<ViewportAnnotation>, String> {
    let core = state.core.blocking_lock();
    let project = core.get_project(&project_id)
        .ok_or("Project not found")?;

    // O(log N + k): interval tree query
    let candidate_indices = project.range_index.query(start_char, end_char);

    // O(k / 16): SIMD filter on candidates only
    let candidates: Vec<&PackedAnnotation> = candidate_indices.iter()
        .map(|&i| &project.annot_store.packed[i as usize])
        .collect();

    let passed = project.filter_engine.filter_candidates(
        &candidates, track_mask, min_confidence
    );

    let results: Vec<ViewportAnnotation> = candidates.iter()
        .zip(passed.iter())
        .filter(|(_, pass)| *pass)
        .map(|(ann, _)| ViewportAnnotation {
            start: ann.start,
            end: ann.end,
            track_id: ann.track_id,
            confidence: ann.confidence as f32 / 10000.0,
        })
        .collect();

    Ok(results)
}
```

Typical call for a viewport of 30 paragraphs (~7,000 characters):
- `RangeIndex.query`: returns ~200-400 candidate indices (from 18,760 total)
- `FilterEngine.filter_candidates`: 200-400 / 16 = 13-25 SIMD iterations ≈ ~0.1μs
- Serialize 200-400 `ViewportAnnotation` structs to JSON: ~0.5ms
- Total `query_viewport` time: <1ms

### VirtualTextView Component

```typescript
// browser/src/components/TextLinearView/VirtualTextView.tsx

interface VirtualTextViewProps {
  paragraphs: ParagraphData[];       // text + char offsets, NO annotation data
  projectId: string;
  overscanCount?: number;             // default 2 screens
  estimatedItemHeight?: number;       // default 120px
}

export function VirtualTextView({
  paragraphs, projectId,
  overscanCount = 2,
  estimatedItemHeight = 120,
}: VirtualTextViewProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const [heightCache, setHeightCache] = useState(() => new FenwickHeightCache(paragraphs.length, estimatedItemHeight));
  const [visibleRange, setVisibleRange] = useState<[number, number]>([0, 20]);
  const [viewportAnnotations, setViewportAnnotations] = useState<ViewportAnnotation[]>([]);
  const [paragraphRects, setParagraphRects] = useState<ParagraphRect[]>([]);

  const { selectedParagraphIndex, scrollToParagraphRequest, clearScrollRequest } = useViewStore();
  const { trackMask, minConfidence } = useTrackStore();

  // Single ResizeObserver for all visible elements
  const resizeObserverRef = useRef<ResizeObserver>();
  useEffect(() => {
    resizeObserverRef.current = new ResizeObserver(entries => {
      const updates: Map<number, number> = new Map();
      for (const entry of entries) {
        const idx = Number(entry.target.getAttribute('data-para-idx'));
        updates.set(idx, entry.contentRect.height);
      }
      setHeightCache(prev => prev.withUpdates(updates));
    });
    return () => resizeObserverRef.current?.disconnect();
  }, []);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;

    requestAnimationFrame(() => {
      const scrollTop = el.scrollTop;
      const viewportHeight = el.clientHeight;
      const overscanPx = viewportHeight * overscanCount;

      // Fenwick tree: O(log N) range queries
      const [startIdx, endIdx] = heightCache.visibleRange(
        Math.max(0, scrollTop - overscanPx),
        scrollTop + viewportHeight + overscanPx,
      );

      setVisibleRange([startIdx, endIdx]);

      // Compute char range for Rust query
      const startChar = paragraphs[startIdx]?.charStart ?? 0;
      const endChar = paragraphs[endIdx]?.charEnd ?? 0;

      // Query Rust for viewport annotations — the ONLY annotation data source
      invoke<ViewportAnnotation[]>('query_viewport', {
        projectId,
        startChar,
        endChar,
        trackMask: Number(trackMask),
        minConfidence: Math.round(minConfidence * 10000),
      }).then(annotations => {
        setViewportAnnotations(annotations);
        // Compute paragraph pixel rects for canvas overlay
        const rects = computeParagraphRects(
          paragraphs.slice(startIdx, endIdx + 1),
          heightCache,
          startIdx,
          scrollTop,
        );
        setParagraphRects(rects);
      });
    });
  }, [heightCache, paragraphs, projectId, trackMask, minConfidence, overscanCount]);

  // Scroll to paragraph on request
  useEffect(() => {
    if (scrollToParagraphRequest === null) return;
    const offset = heightCache.offsetFor(scrollToParagraphRequest);
    containerRef.current?.scrollTo({ top: offset, behavior: 'smooth' });
    clearScrollRequest();
  }, [scrollToParagraphRequest]);

  const totalHeight = heightCache.totalHeight();
  const [startIdx, endIdx] = visibleRange;

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      style={{ overflowY: 'scroll', height: '100%', position: 'relative' }}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        {paragraphs.slice(startIdx, endIdx + 1).map((para, relIdx) => {
          const absIdx = startIdx + relIdx;
          const top = heightCache.offsetFor(absIdx);
          return (
            <div
              key={para.index}
              data-para-idx={absIdx}
              ref={el => { if (el) resizeObserverRef.current?.observe(el); }}
              style={{
                position: 'absolute',
                top,
                width: '100%',
                padding: '8px 16px',
              }}
              onClick={() => setSelectedParagraphIndex(absIdx)}
            >
              <p className={`paragraph ${selectedParagraphIndex === absIdx ? 'selected' : ''}`}>
                {para.text}
              </p>
            </div>
          );
        })}

        {/* Canvas overlay: annotation highlights drawn here, no DOM spans */}
        <CanvasAnnotationOverlay
          containerRef={containerRef}
          paragraphRects={paragraphRects}
          annotations={viewportAnnotations}
          selectedParagraphIndex={selectedParagraphIndex}
        />
      </div>
    </div>
  );
}
```

### FenwickHeightCache

```typescript
// browser/src/utils/FenwickHeightCache.ts

/**
 * O(log N) prefix sum for paragraph height management.
 * Replaces the O(N) prefix sum loop in the v3.x VirtualScroller.
 */
export class FenwickHeightCache {
  private tree: Float64Array;  // Fenwick tree for prefix sums
  private heights: Float64Array;
  private n: number;

  constructor(n: number, defaultHeight: number) {
    this.n = n;
    this.heights = new Float64Array(n).fill(defaultHeight);
    this.tree = new Float64Array(n + 1);
    // Build tree from initial heights
    for (let i = 0; i < n; i++) {
      this.update(i, defaultHeight);
    }
  }

  update(index: number, height: number): void {
    const delta = height - this.heights[index];
    this.heights[index] = height;
    for (let i = index + 1; i <= this.n; i += i & (-i)) {
      this.tree[i] += delta;
    }
  }

  withUpdates(updates: Map<number, number>): FenwickHeightCache {
    const next = this; // mutable update for simplicity
    for (const [idx, h] of updates) {
      next.update(idx, h);
    }
    return next;
  }

  // Prefix sum: O(log N)
  offsetFor(index: number): number {
    let sum = 0;
    for (let i = index; i > 0; i -= i & (-i)) {
      sum += this.tree[i];
    }
    return sum;
  }

  // Binary search for visible range: O(log² N)
  visibleRange(rangeTop: number, rangeBottom: number): [number, number] {
    const start = this.binarySearch(rangeTop);
    const end = this.binarySearch(rangeBottom);
    return [Math.max(0, start), Math.min(this.n - 1, end)];
  }

  totalHeight(): number {
    return this.offsetFor(this.n);
  }

  private binarySearch(targetOffset: number): number {
    let lo = 0, hi = this.n - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (this.offsetFor(mid + 1) <= targetOffset) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  }
}
```

### CanvasAnnotationOverlay

```typescript
// browser/src/components/TextLinearView/CanvasAnnotationOverlay.tsx

interface CanvasAnnotationOverlayProps {
  containerRef: React.RefObject<HTMLDivElement>;
  paragraphRects: ParagraphRect[];
  annotations: ViewportAnnotation[];
  selectedParagraphIndex: number | null;
}

export function CanvasAnnotationOverlay({
  containerRef, paragraphRects, annotations, selectedParagraphIndex,
}: CanvasAnnotationOverlayProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d')!;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw annotation highlight rectangles
    for (const ann of annotations) {
      const color = TRACK_COLORS[ann.trackId] ?? '#888888';
      const alpha = Math.max(0.15, ann.confidence * 0.4);

      for (const rect of paragraphRects) {
        if (ann.start >= rect.charEnd || ann.end <= rect.charStart) continue;

        // Compute pixel x positions within paragraph
        const paraCharLen = rect.charEnd - rect.charStart;
        const xStart = Math.floor(
          ((Math.max(ann.start, rect.charStart) - rect.charStart) / paraCharLen) * canvas.width
        );
        const xEnd = Math.ceil(
          ((Math.min(ann.end, rect.charEnd) - rect.charStart) / paraCharLen) * canvas.width
        );

        ctx.fillStyle = color;
        ctx.globalAlpha = alpha;
        ctx.fillRect(xStart, rect.top, xEnd - xStart, rect.height);
      }
    }

    // Draw selection highlight
    if (selectedParagraphIndex !== null) {
      const selectedRect = paragraphRects.find(r => r.index === selectedParagraphIndex);
      if (selectedRect) {
        ctx.fillStyle = 'rgba(52, 100, 200, 0.15)';
        ctx.globalAlpha = 1.0;
        ctx.fillRect(0, selectedRect.top, canvas.width, selectedRect.height);
      }
    }
  }, [paragraphRects, annotations, selectedParagraphIndex]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0, left: 0,
        width: '100%', height: '100%',
        pointerEvents: 'none',  // clicks pass through to text paragraphs
      }}
    />
  );
}
```

**Result**: 1 canvas element replaces 10,000+ `<mark>` spans. The canvas is repainted on each `query_viewport` response (~5ms total including Rust query).

### Click Hit-Testing

Annotation click detection is handled by computing the character offset from the mouse position:

```typescript
const handleCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
  const container = containerRef.current!;
  const rect = container.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const clickY = e.clientY - rect.top + container.scrollTop;

  // Find which paragraph was clicked
  const para = paragraphRects.find(r => clickY >= r.top && clickY < r.top + r.height);
  if (!para) return;

  // Compute character offset from x position
  const charOffset = para.charStart + Math.round(
    (clickX / container.clientWidth) * (para.charEnd - para.charStart)
  );

  // Find topmost annotation at this offset (by track priority)
  const clickedAnn = viewportAnnotations.find(
    ann => ann.start <= charOffset && ann.end >= charOffset
  );

  if (clickedAnn) {
    detailStore.showAnnotation(clickedAnn);
  }
  setSelectedParagraphIndex(para.index);
};
```

### Performance Targets (Hard Requirements)

| Operation | Target | Notes |
|-----------|--------|-------|
| Scroll handler (RAF throttled) | <0ms CPU (async) | Deferred to next frame |
| `query_viewport` Tauri command | <5ms | Rust interval tree + SIMD filter |
| CanvasAnnotationOverlay repaint | <2ms | 30 paragraphs × ~10 rects each |
| FenwickHeightCache update (N=1832) | O(log N) ≈ 11 operations | vs O(N)=1832 in v3.x |
| DOM node count at any scroll position | ≤60 | 30 paragraphs + overhead |
| Full P&P scroll-through (1832 paras) at 60fps | 0 dropped frames | Verified via DevTools |

### Acceptance Criteria (v4.0)

- DOM node count never exceeds 60 during scroll (verified via DevTools Elements count)
- No `<mark>` elements exist in DOM at any time (replaced by canvas)
- Scroll FPS ≥ 60 throughout full P&P at 6× CPU throttle in DevTools
- `query_viewport` is called at most once per animation frame (RAF throttle verified)
- Track toggle → `query_viewport` fires immediately → canvas repainted in <5ms
- `tsc --strict` passes on all new/modified files
- `cargo test` passes all viewport command tests

### Tests

```typescript
// VirtualTextView.test.tsx

test('renders at most 60 DOM nodes during scroll', async () => {
  const paragraphs = Array.from({ length: 2000 }, (_, i) => mockParagraph(i));
  const { container } = render(<VirtualTextView paragraphs={paragraphs} projectId="test" />);
  const allNodes = container.querySelectorAll('div');
  expect(allNodes.length).toBeLessThan(60);
});

test('no mark elements exist in DOM', () => {
  render(<VirtualTextView paragraphs={mockParagraphs(100)} projectId="test" />);
  expect(document.querySelectorAll('mark')).toHaveLength(0);
});

test('query_viewport called on scroll', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  const mockInvoke = vi.fn().mockResolvedValue([]);
  (invoke as ReturnType<typeof vi.fn>).mockImplementation(mockInvoke);
  const { container } = render(<VirtualTextView paragraphs={mockParagraphs(100)} projectId="test" />);
  fireEvent.scroll(container.firstChild as HTMLElement, { target: { scrollTop: 500 } });
  await waitFor(() => {
    expect(mockInvoke).toHaveBeenCalledWith('query_viewport', expect.objectContaining({
      projectId: 'test',
    }));
  });
});

test('FenwickHeightCache offsetFor is O(log N) correct', () => {
  const cache = new FenwickHeightCache(10, 120);
  // First 3 items: [120, 120, 120, ...]
  expect(cache.offsetFor(0)).toBe(0);
  expect(cache.offsetFor(1)).toBe(120);
  expect(cache.offsetFor(2)).toBe(240);
  // Update item 1 height to 200
  cache.update(1, 200);
  expect(cache.offsetFor(2)).toBe(320); // 120 + 200
  expect(cache.offsetFor(3)).toBe(440); // 120 + 200 + 120
});
```

---

## Original Content (Reference)

**Milestone**: 1.4 — Full Text Browser + Cross-Text Dotplot + Export
**Estimated effort**: 10 hours

### Context (original)

TextLinearView currently renders the entire reference text as DOM nodes, which collapses at full-novel scale. VirtualScroller renders only the paragraphs in the visible viewport plus a two-screen buffer, recycling DOM elements as the user scrolls. IntersectionObserver drives lazy loading of annotation overlays.

### Design Decisions (original)

- **Absolute positioning over CSS `transform: translateY`**: Simpler with variable heights.
- **Prefix-sum approach over react-window**: ~120 lines, no external dependency.
- **ResizeObserver per element**: Fires when content box changes size.
- **`overscanCount = 2` as default**: 2 screens ensures fast scroll doesn't outrun rendering.
