# T28: Linked Views

**Milestone**: 1.3b — BookNLP + DotplotView
**Estimated effort**: 5 hours (Day 37)
**Dependencies**: T27 (DotplotView GPU render pipeline), T09 (VirtualTextView + CanvasAnnotationOverlay), T20 (OverviewBar density histogram), T22 (similarity search Tauri command)
**Outputs**: `browser/src/stores/viewStore.ts` (finalized), `browser/src/components/TextLinearView/VirtualTextView.tsx` (modified), `browser/src/components/DotplotView/DotplotView.tsx` (modified), `browser/src/components/OverviewBar/OverviewBar.tsx` (modified), `browser/src/components/DetailPanel/DetailPanel.tsx` (modified)

---

## v4.0 Critical Review

**Verdict: The Zustand-based shared selection primitive is the right design. The scrollToParagraphRequest pattern is correct. The serious flaw is the underlying data flow: in v3.x, selection state changes trigger React re-renders that cause `collectVisibleAnnotations()` to re-scan 18,760 annotations. In v4.0 the view re-renders must only update the Tauri viewport query — they must not trigger annotation rescanning.**

### What Is Broken

**Selection changes in v3.x trigger full annotation re-renders.** When `selectedParagraphIndex` changes in Zustand:
- `TextLinearView` subscribes → re-renders → `collectVisibleAnnotations()` runs over all annotations → `AnnotationOverlay` for every paragraph re-computes its highlights
- This is the same 48M-comparison bug from the performance diagnosis. The linked-views implementation cannot simply wire selection state without also fixing how selection changes propagate to annotation rendering.

**The OverviewBar selection tick is a DOM element.** In v3.x, `OverviewBar` renders a `<div>` with computed `left` position for the selection indicator. When selection changes rapidly (e.g., user is clicking quickly through DotplotView cells), this causes repeated DOM mutations. The OverviewBar density bars are already canvas-rendered; the selection indicator must also be canvas-drawn, not DOM-positioned.

**Similarity search results trigger `requestScrollToParagraph` which causes VirtualScroller to scroll.** In v3.x VirtualScroller, scrolling triggers a ResizeObserver cascade, which triggers height map updates, which triggers re-render. Under the v4.0 virtual scroller (T30), scroll must only update the visible paragraph range and re-query the Rust viewport, not trigger annotation re-renders.

**The Playwright e2e test spec (test_linked_views.py) assumes a browser can communicate with a FastAPI server.** Under Tauri there is no FastAPI server. Playwright cannot test Tauri native commands. The e2e test strategy must change to use Tauri's testing utilities or a mock mode.

---

## v4.0 Rewrite

### Architecture

The linked-views system in v4.0 is built on two principles:

1. **Selection state is Zustand (UI-only).** `selectedParagraphIndex` is a number in Zustand. It is the only shared state. Views subscribe to it.

2. **Selection changes do NOT trigger annotation re-renders.** The VirtualTextView (T30) already re-queries the Rust AnnotStore for the current viewport on every scroll. Selection changes only update the CanvasAnnotationOverlay to draw a selection highlight rectangle — they do not re-query annotations.

```
selectedParagraphIndex changes
  → VirtualTextView: CanvasAnnotationOverlay draws selection rect at paragraph N (fast canvas repaint)
  → DotplotView: shader uniform updated (selected_row = N, selected_col = N) → fragment shader re-runs (fast)
  → OverviewBar: canvas repaints selection tick at proportional position N/totalParas (fast)
  → DetailPanel: shows annotations for paragraph N (calls Rust query_viewport for N only → ~1ms)
No: annotation re-scans. No: 48M comparisons. No: React re-renders of annotation spans.
```

### Tauri Event System for Cross-Component Coordination

Selection propagation uses the Tauri event system in addition to Zustand. This allows Rust to participate in view synchronization (e.g., when a background analysis updates annotations, it can emit a Tauri event that updates the visible view):

```typescript
// browser/src/stores/viewStore.ts

import { emit, listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';

interface ViewStore {
  selectedParagraphIndex: number | null;
  setSelectedParagraphIndex: (idx: number | null) => void;
  scrollToParagraphRequest: number | null;
  requestScrollToParagraph: (idx: number) => void;
  clearScrollRequest: () => void;
}

const useViewStore = create<ViewStore>((set, get) => ({
  selectedParagraphIndex: null,

  setSelectedParagraphIndex: (idx) => {
    set({ selectedParagraphIndex: idx });
    // Notify Rust coordinator (for cross-view sync and future synoptic split-view)
    if (idx !== null) {
      invoke('notify_paragraph_selected', { paragraphIndex: idx }).catch(() => {});
    }
  },

  scrollToParagraphRequest: null,
  requestScrollToParagraph: (idx) => set({ scrollToParagraphRequest: idx }),
  clearScrollRequest: () => set({ scrollToParagraphRequest: null }),
}));
```

The Rust command `notify_paragraph_selected` is a lightweight coordinator that can forward the selection to other views in synoptic mode (Phase 2) — in Phase 1 it is a no-op that logs the event.

### VirtualTextView Selection Wiring

```typescript
// browser/src/components/TextLinearView/VirtualTextView.tsx

// Selection change: repaint canvas overlay only, no annotation re-query
useEffect(() => {
  const overlay = canvasOverlayRef.current;
  if (!overlay) return;
  // Repaint with selection highlight at paragraph N
  repaintCanvasOverlay(overlay, visibleAnnotations, selectedParagraphIndex);
}, [selectedParagraphIndex]); // NOT a dependency that triggers Tauri query_viewport

// Scroll request: scroll VirtualTextView to paragraph N
useEffect(() => {
  if (scrollToParagraphRequest === null) return;
  const offset = heightCache.offsetForIndex(scrollToParagraphRequest);
  containerRef.current?.scrollTo({ top: offset, behavior: 'smooth' });
  clearScrollRequest();
}, [scrollToParagraphRequest]);

// Paragraph click: set selection, do NOT scroll (user is already there)
const handleParagraphClick = useCallback((paragraphIndex: number) => {
  setSelectedParagraphIndex(paragraphIndex);
  // No requestScrollToParagraph here — user clicked, element is visible
}, [setSelectedParagraphIndex]);
```

The `repaintCanvasOverlay` function only redraws the selection highlight rectangle — it does not re-query the Rust AnnotStore. It uses the already-rendered `visibleAnnotations` that were fetched on the last `query_viewport` call.

### DotplotView Selection Wiring (already handled by fragment shader)

No React re-render needed. Selection is a shader uniform:

```typescript
// browser/src/components/DotplotView/DotplotCanvas.tsx

// Selection change: update GPU uniform buffer only (no React state change, no re-render)
useEffect(() => {
  if (!gpuStateRef.current) return;
  const uniformData = buildUniformData(viewportRef.current, selectedParagraphIndex);
  gpuStateRef.current.device.queue.writeBuffer(
    gpuStateRef.current.uniformBuffer, 0, uniformData
  );
  // Trigger one GPU render pass
  renderFrame(gpuStateRef.current);
}, [selectedParagraphIndex]); // This updates GPU uniform, not React state — no cascade
```

This is the key v4.0 advantage: selection change in DotplotView = 1 `writeBuffer` call + 1 GPU draw call = <1ms. In v3.x it was a React re-render + canvas pixel buffer rebuild + putImageData = 50-200ms.

### OverviewBar Selection Indicator

The OverviewBar selection tick is drawn on the existing density canvas, not as a DOM element:

```typescript
// browser/src/components/OverviewBar/OverviewBar.tsx

// Selection tick drawn directly on density canvas — no DOM mutation
useEffect(() => {
  const canvas = canvasRef.current;
  if (!canvas || selectedParagraphIndex === null) return;
  const ctx = canvas.getContext('2d')!;
  const x = Math.floor((selectedParagraphIndex / totalParagraphs) * canvas.width);
  // Draw 2px orange tick over the density bars
  ctx.save();
  ctx.fillStyle = 'rgba(255, 160, 0, 0.9)';
  ctx.fillRect(x - 1, 0, 2, canvas.height);
  ctx.restore();
}, [selectedParagraphIndex, totalParagraphs]);
```

No DOM mutation, no React reconciliation. Canvas `fillRect` is a GPU-accelerated operation; at 2 pixels wide it completes in microseconds.

### DetailPanel: Annotation Display on Selection

```typescript
// browser/src/components/DetailPanel/DetailPanel.tsx

// On selection change: query Rust for ONLY paragraph N's annotations
useEffect(() => {
  if (selectedParagraphIndex === null) {
    setSelectedAnnotations([]);
    return;
  }
  invoke<AnnotationRecord[]>('query_single_paragraph', {
    projectId,
    paragraphIndex: selectedParagraphIndex,
  }).then(setSelectedAnnotations);
}, [selectedParagraphIndex, projectId]);
```

`query_single_paragraph` is a Tauri command that uses `RangeIndex.query(para.start, para.end)` in Rust — O(log N + k) interval tree lookup. For paragraph N with k=50 annotations, this takes ~0.1ms.

### Rust Coordinator Command

```rust
// src-tauri/src/commands/coordinator.rs

#[tauri::command]
pub fn notify_paragraph_selected(
    paragraph_index: u32,
    state: tauri::State<'_, AppState>,
) -> Result<(), String> {
    // Phase 1: log for debugging, no-op
    log::debug!("Paragraph selected: {}", paragraph_index);
    // Phase 2: will forward to synoptic split-view mirror project
    Ok(())
}

#[tauri::command]
pub fn query_single_paragraph(
    project_id: String,
    paragraph_index: usize,
    state: tauri::State<'_, AppState>,
) -> Result<Vec<AnnotationRecord>, String> {
    let core = state.core.blocking_lock();
    let project = core.get_project(&project_id)
        .ok_or("Project not found")?;

    let para = project.paragraphs.get(paragraph_index)
        .ok_or("Paragraph index out of range")?;

    // O(log N + k) interval tree query
    let annotation_indices = project.range_index.query(para.start, para.end);

    let records = annotation_indices.iter().map(|&idx| {
        let ann = &project.annot_store.packed[idx as usize];
        AnnotationRecord {
            start: ann.start,
            end: ann.end,
            track_id: ann.track_id,
            confidence: ann.confidence as f32 / 10000.0,
            body_offset: ann.body_offset,
            // ... body text from body arena
        }
    }).collect();

    Ok(records)
}
```

### Performance Targets (Hard Requirements)

| Operation | Target | Measurement Method |
|-----------|--------|-------------------|
| Selection state change → all views updated | <2ms total | Chrome DevTools Timeline |
| DotplotView response to selection | <1ms | uniform write + draw call |
| OverviewBar selection tick paint | <0.1ms | canvas fillRect |
| VirtualTextView canvas overlay repaint | <2ms | canvas repaint (no Tauri call) |
| DetailPanel annotation query (single para) | <1ms | Tauri `query_single_paragraph` |
| End-to-end: click DotplotView cell → TextLinearView scrolled | <16ms | 1 frame budget |

### Acceptance Criteria (v4.0)

- Clicking paragraph N in VirtualTextView: selection updates, DotplotView GPU uniform updates in same frame, OverviewBar tick repaints — all within 2ms
- Clicking DotplotView cell (i, j): TextLinearView scrolls to paragraph i within one 16ms frame; no annotation re-scan
- OverviewBar click: TextLinearView scrolls, DotplotView updates — within 16ms
- Similarity search "Jump to": TextLinearView scrolls; DotplotView highlights; OverviewBar updates — within 16ms
- DetailPanel annotation display updates on selection: <1ms Tauri query
- No annotation re-scans triggered by selection changes (verified: `query_viewport` Tauri command NOT called on selection change, only on scroll)
- `tsc --strict` passes on all modified files
- `cargo test` passes all coordinator command tests

### Tests

```typescript
// browser/src/stores/viewStore.test.ts

test('setSelectedParagraphIndex updates state and calls notify_paragraph_selected', async () => {
  const { invoke } = await import('@tauri-apps/api/core');
  const mockInvoke = vi.fn().mockResolvedValue(null);
  (invoke as ReturnType<typeof vi.fn>).mockImplementation(mockInvoke);

  const store = useViewStore.getState();
  store.setSelectedParagraphIndex(42);

  expect(store.selectedParagraphIndex).toBe(42);
  expect(mockInvoke).toHaveBeenCalledWith('notify_paragraph_selected', { paragraphIndex: 42 });
});

test('requestScrollToParagraph sets scrollToParagraphRequest', () => {
  const store = useViewStore.getState();
  store.requestScrollToParagraph(100);
  expect(store.scrollToParagraphRequest).toBe(100);
});

test('clearScrollRequest resets to null', () => {
  const store = useViewStore.getState();
  store.requestScrollToParagraph(50);
  store.clearScrollRequest();
  expect(store.scrollToParagraphRequest).toBeNull();
});
```

```rust
// src-tauri/src/commands/coordinator_tests.rs

#[test]
fn test_query_single_paragraph_returns_correct_annotations() {
    let state = mock_state_with_annotations(100, 5); // 100 paragraphs, 5 annotations each
    let results = query_single_paragraph("project".to_string(), 0, state).unwrap();
    assert!(results.len() <= 5);
    // All results must be within paragraph 0's character range
    let para_start = 0u32;
    let para_end = 500u32; // mock paragraph end
    for ann in &results {
        assert!(ann.start >= para_start && ann.end <= para_end);
    }
}

#[test]
fn test_query_single_paragraph_out_of_range_returns_error() {
    let state = mock_state_with_annotations(10, 5);
    let err = query_single_paragraph("project".to_string(), 999, state).unwrap_err();
    assert!(err.contains("out of range"));
}
```

---

## Original Content (Reference)

**Milestone**: 1.3b — BookNLP + DotplotView
**Estimated effort**: 5 hours (Day 37)

### Context (original)

T28 wires four distinct views (TextLinearView, DotplotView, OverviewBar, DetailPanel) through a single Zustand `viewStore` so that a selection in any view propagates to all others. The shared primitive is `selectedParagraphIndex: number | null`.

### Design Decisions (original)

- **Single shared integer, not a region object**: Paragraph-granularity for all Phase 1 views.
- **Imperative scroll trigger pattern**: `scrollToParagraphRequest` Zustand value as event channel.
- **Selection does not trigger scroll from TextLinearView click**: User clicked, element is already visible.
- **OverviewBar tick color**: Yellow/orange to distinguish from search match ticks.
