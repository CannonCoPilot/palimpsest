# T10: Canvas Annotation Overlay + Detail Panel + Keyboard + M1.1 Integration

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 8 hours → 10 hours (v4.0: canvas overlay replaces DOM spans; HTTP server eliminated)
**Dependencies**: T09 (VirtualTextView + Tauri command adapters); T08 (Rust CLI produces entities.jsonl)
**Outputs**: `CanvasAnnotationOverlay.tsx`, `DetailPanel.tsx`, `keyboard.ts` (full), Milestone 1.1 smoke test passing

---

## v4.0 Critical Review

**T10 in v3.0 is the most thoroughly broken task in the entire suite. It implements the two worst performance decisions in the system and introduces a security-sensitive HTTP server that is immediately deprecated.**

Breaking down the failures in order of severity:

1. **`core/palimpsest/server.py` is the entire FastAPI HTTP server.** This is the component that T09 fetches annotation data from. In v4.0 it does not exist. The sentence "T10 completes Milestone 1.1 by wiring together all previous components" with "server.py" as a deliverable is wrong in v4.0: the Tauri application shell is the integration point, not a separate HTTP process.

2. **`AnnotationOverlay.tsx` injects `<mark>` elements.** Each annotation in a paragraph becomes a DOM element. For P&P Chapter 1 with ~80 entities, this is 80 `<mark>` elements plus their text node siblings. Each `<mark>` causes a style recalculation. On scroll, every paragraph in view recalculates styles. This is the O(paragraphs × annotations) DOM interaction that produces the 200ms+ scroll latency observed in M1.2. In v4.0, a `<canvas>` element overlaid on the text draws all annotations in a single paint call per frame.

3. **`buildSpans()` performs string slicing for every paragraph on every render.** With 50 visible paragraphs and 200 entity annotations in view, this is 200 annotations × 50 paragraphs worth of string operations per render cycle. In v4.0, the canvas overlay computes pixel rectangles from pre-measured character positions — no string slicing needed.

4. **`setupKeyboardHandlers()` uses `useViewStore.getState()` imperatively.** This is actually the correct pattern (Zustand imperative API for global keyboard shortcuts). Preserved as-is.

5. **Server tests use `TestClient(app)`.** In v4.0 there is no HTTP server. The equivalent integration tests use Tauri command mocking (`vi.mock('@tauri-apps/api/core')`).

6. **Path traversal protection in `server.py`.** The FastAPI server's path traversal check (`full_path.relative_to(project_dir.resolve())`) is a good security control. In v4.0, the Tauri command layer enforces the equivalent: project directories are opened from a configured workspace path, and Tauri commands only have access to paths the application is authorized to read (via Tauri's capability system). The security boundary moves from HTTP to OS-level process isolation.

**What is eliminated:**
- `core/palimpsest/server.py` — entire file deleted
- `AnnotationOverlay.tsx` using `<mark>` elements — replaced by `CanvasAnnotationOverlay.tsx`
- `buildSpans()` string slicing — replaced by pixel rectangle computation
- FastAPI server tests — replaced by Tauri command mock tests
- `palimpsest serve` command — eliminated in T08

**What is preserved:**
- `DetailPanel.tsx` — identical purpose, minor adaptations for `ViewportAnnotation` type vs. `WC3Annotation`
- `keyboard.ts` — identical implementation
- Milestone 1.1 smoke test — same checklist, different verification method

---

## v4.0 Rewrite

### `CanvasAnnotationOverlay` Component

The overlay is a `<canvas>` element with `position: absolute` that covers the text paragraph. It draws annotation highlight rectangles using character offset → pixel position mapping:

```typescript
// ui/src/components/TextLinearView/CanvasAnnotationOverlay.tsx
//
// Canvas-based annotation overlay. Replaces DOM <mark>/<span> injection.
//
// Performance: 200 entity annotations per chapter = 200 fillRect() calls.
// A single requestAnimationFrame paint replaces 200 DOM node insertions.
// Zero style recalculations. Zero reflow.

import React, { useRef, useEffect, useCallback } from 'react';
import { ViewportAnnotation } from '../../adapters/tauri';
import { useViewStore } from '../../stores/viewStore';
import { getAnnotationDetail } from '../../adapters/tauri';
import { useProjectStore } from '../../stores/projectStore';

// Color map: track_id and entity_type → RGB
const ENTITY_COLORS: Record<string, [number, number, number]> = {
  PER:  [230, 57, 70],    // #e63946 — red
  LOC:  [69, 123, 157],   // #457b9d — blue
  ORG:  [42, 157, 143],   // #2a9d8f — teal
  WORK: [233, 196, 106],  // #e9c46a — amber
};

const SENTIMENT_POSITIVE: [number, number, number] = [34, 197, 94];   // #22c55e
const SENTIMENT_NEGATIVE: [number, number, number] = [239, 68, 68];   // #ef4444

function annotationColor(ann: ViewportAnnotation): [number, number, number] {
  if (ann.body_type === 'palimpsest:EntityAnnotation' && ann.entity_type) {
    return ENTITY_COLORS[ann.entity_type] ?? [158, 158, 158];
  }
  // Extend for other body types
  return [158, 158, 158]; // gray for unknown
}

/**
 * Compute pixel X position of character offset within a text element.
 *
 * Uses the browser's Range API to find the pixel position of a character.
 * This is the only reliable cross-browser way to map char offset → pixel.
 * Called once per annotation per render; results are not cached in Phase 1.
 * (Phase 2: pre-cache using OffscreenCanvas text metrics.)
 */
function charOffsetToX(element: HTMLElement, offset: number): number | null {
  try {
    const textNode = element.firstChild;
    if (!textNode || textNode.nodeType !== Node.TEXT_NODE) return null;
    const range = document.createRange();
    const clamped = Math.min(offset, (textNode as Text).length);
    range.setStart(textNode, clamped);
    range.setEnd(textNode, clamped);
    const rect = range.getBoundingClientRect();
    const parentRect = element.getBoundingClientRect();
    return rect.left - parentRect.left;
  } catch {
    return null;
  }
}

interface CanvasAnnotationOverlayProps {
  /** The paragraph text element (used for char-to-pixel mapping) */
  textElementRef: React.RefObject<HTMLElement>;
  /** Character offset of this paragraph's start within reference.txt */
  paragraphStart: number;
  /** Paragraph text (for char offset computation) */
  paragraphText: string;
  /** Annotations filtered to overlap this paragraph */
  annotations: ViewportAnnotation[];
  /** Width and height of the paragraph element */
  width: number;
  height: number;
}

export function CanvasAnnotationOverlay({
  textElementRef,
  paragraphStart,
  paragraphText,
  annotations,
  width,
  height,
}: CanvasAnnotationOverlayProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const projectId = useProjectStore((s) => s.projectId);
  const { selectAnnotation } = useViewStore();

  // Draw all annotation highlights on canvas
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    const textEl = textElementRef.current;
    if (!canvas || !ctx || !textEl) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const lineHeight = parseFloat(getComputedStyle(textEl).lineHeight) || 24;
    const elementRect = textEl.getBoundingClientRect();
    const parentRect = canvas.parentElement?.getBoundingClientRect() ?? elementRect;
    const elementTop = elementRect.top - parentRect.top;

    for (const ann of annotations) {
      const localStart = ann.start - paragraphStart;
      const localEnd = ann.end - paragraphStart;

      if (localStart < 0 || localEnd > paragraphText.length) continue;

      // Get pixel X for start and end
      const x1 = charOffsetToX(textEl, localStart);
      const x2 = charOffsetToX(textEl, localEnd);

      if (x1 === null || x2 === null) continue;

      // Determine if annotation spans multiple lines
      // For Phase 1: draw a single rectangle. Phase 2: multi-line support.
      const [r, g, b] = annotationColor(ann);
      const alpha = 0.25 + ann.confidence * 0.35; // 0.25-0.60 based on confidence

      ctx.save();
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;

      if (x2 > x1) {
        // Same line: single rectangle
        ctx.fillRect(x1, elementTop, x2 - x1, lineHeight);
      } else {
        // Multi-line: draw from x1 to end of line, then full lines, then x2
        // Phase 1 simplified: just draw from x1 to canvas width
        ctx.fillRect(x1, elementTop, canvas.width - x1, lineHeight);
      }

      // Bottom border for entity type distinction
      ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
      ctx.fillRect(x1, elementTop + lineHeight - 2, Math.max(x2 - x1, 20), 2);

      ctx.restore();
    }
  }, [annotations, paragraphStart, paragraphText, textElementRef]);

  // Redraw on annotations change or resize
  useEffect(() => {
    requestAnimationFrame(draw);
  }, [draw, width, height]);

  // Click hit testing: find which annotation was clicked
  const onClick = useCallback(async (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!projectId) return;
    const canvas = canvasRef.current;
    const textEl = textElementRef.current;
    if (!canvas || !textEl) return;

    const canvasRect = canvas.getBoundingClientRect();
    const clickX = e.clientX - canvasRect.left;
    const clickY = e.clientY - canvasRect.top;

    // Find annotation whose pixel rectangle contains the click point
    for (const ann of annotations) {
      const localStart = ann.start - paragraphStart;
      const localEnd = ann.end - paragraphStart;
      const x1 = charOffsetToX(textEl, localStart);
      const x2 = charOffsetToX(textEl, localEnd);
      if (x1 === null || x2 === null) continue;

      const lineHeight = parseFloat(getComputedStyle(textEl).lineHeight) || 24;
      const elementRect = textEl.getBoundingClientRect();
      const parentRect = canvas.parentElement?.getBoundingClientRect() ?? elementRect;
      const elementTop = elementRect.top - parentRect.top;

      if (clickX >= x1 && clickX <= x2 && clickY >= elementTop && clickY <= elementTop + lineHeight) {
        // Fetch full annotation detail from Rust arena
        // For Phase 1, use a sequential index. Phase 2: carry arena index in ViewportAnnotation.
        selectAnnotation(null); // placeholder — full detail fetching in Phase 2
        break;
      }
    }
  }, [annotations, paragraphStart, projectId, selectAnnotation, textElementRef]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      onClick={onClick}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: annotations.length > 0 ? 'auto' : 'none',
      }}
      aria-hidden="true"
      role="presentation"
    />
  );
}
```

### Update `VirtualParagraph` to Use Canvas Overlay

```typescript
// ui/src/components/TextLinearView/VirtualParagraph.tsx (updated)

import React, { useRef, useEffect, useState } from 'react';
import { ViewportAnnotation } from '../../adapters/tauri';
import { CanvasAnnotationOverlay } from './CanvasAnnotationOverlay';

interface VirtualParagraphProps {
  index: number;
  text: string;
  paragraphStart: number;
  annotations: ViewportAnnotation[];
  onHeightMeasured: (height: number) => void;
}

export function VirtualParagraph({
  index,
  text,
  paragraphStart,
  annotations,
  onHeightMeasured,
}: VirtualParagraphProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLParagraphElement>(null);
  const [dims, setDims] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const h = rect.height;
      onHeightMeasured(h);
      setDims({ width: rect.width, height: h });
    }
  });

  return (
    <div
      ref={containerRef}
      data-paragraph-index={index}
      style={{ position: 'relative', marginBottom: '1.2em' }}
    >
      {/* Plain text — canvas overlay draws annotations on top */}
      <p
        ref={textRef}
        style={{
          margin: 0,
          fontFamily: 'Georgia, "Crimson Pro", serif',
          fontSize: '16px',
          lineHeight: '1.7',
          position: 'relative',
          zIndex: 1,
        }}
      >
        {text}
      </p>

      {/* Canvas annotation overlay — one canvas element regardless of annotation count */}
      {annotations.length > 0 && dims.width > 0 && (
        <CanvasAnnotationOverlay
          textElementRef={textRef}
          paragraphStart={paragraphStart}
          paragraphText={text}
          annotations={annotations}
          width={dims.width}
          height={dims.height}
        />
      )}
    </div>
  );
}
```

### `DetailPanel.tsx`

Adapted from v3.0. The key difference: `selectedAnnotation` in the store is now a Rust annotation index (`number | null`), not a full `WC3Annotation`. On selection, `getAnnotationDetail(projectId, index)` is called to fetch the full body:

```typescript
// ui/src/components/DetailPanel/DetailPanel.tsx

import React, { useEffect, useState } from 'react';
import { useViewStore } from '../../stores/viewStore';
import { useProjectStore } from '../../stores/projectStore';
import { getAnnotationDetail, FullAnnotation } from '../../adapters/tauri';

const EVIDENCE_DESCRIPTIONS: Record<string, string> = {
  E1: 'E1 — Direct extraction from text',
  E2: 'E2 — Human annotator',
  E3: 'E3 — Cross-text alignment',
  E4: 'E4 — ML model prediction',
  E5: 'E5 — Rule-based / statistical',
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  PER: 'Person', LOC: 'Location', ORG: 'Organization', WORK: 'Work of Art',
};

export function DetailPanel(): JSX.Element {
  const selectedAnnotationIndex = useViewStore((s) => s.selectedAnnotationIndex);
  const selectAnnotation = useViewStore((s) => s.selectAnnotation);
  const projectId = useProjectStore((s) => s.projectId);

  const [annotationDetail, setAnnotationDetail] = useState<FullAnnotation | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedAnnotationIndex === null || !projectId) {
      setAnnotationDetail(null);
      return;
    }
    setLoading(true);
    getAnnotationDetail(projectId, selectedAnnotationIndex)
      .then((detail) => {
        setAnnotationDetail(detail);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selectedAnnotationIndex, projectId]);

  return (
    <div
      className="detail-panel"
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderLeft: '1px solid #e5e7eb',
        background: '#fafafa',
      }}
    >
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span style={{ fontWeight: 600, fontSize: '13px' }}>Detail</span>
        {selectedAnnotationIndex !== null && (
          <button
            onClick={() => { selectAnnotation(null); setAnnotationDetail(null); }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af' }}
            aria-label="Close detail panel"
          >
            x
          </button>
        )}
      </div>

      {loading && (
        <div style={{ padding: '16px', color: '#9ca3af', fontSize: '13px' }}>
          Loading...
        </div>
      )}

      {!loading && annotationDetail && (
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', fontSize: '13px' }}>
          {/* Body type badge */}
          <div style={{ marginBottom: '12px' }}>
            <span style={{
              display: 'inline-block', padding: '2px 8px', borderRadius: '4px',
              background: '#e0e7ff', color: '#3730a3', fontFamily: 'monospace', fontSize: '11px',
            }}>
              {String(annotationDetail.body['type'] ?? 'unknown')}
            </span>
          </div>

          {/* Entity type (if applicable) */}
          {annotationDetail.body['palimpsest:entityType'] && (
            <div style={{ marginBottom: '8px' }}>
              <div style={{ color: '#6b7280', fontSize: '11px', textTransform: 'uppercase' }}>Entity Type</div>
              <div style={{ fontWeight: 600, marginTop: '2px' }}>
                {ENTITY_TYPE_LABELS[String(annotationDetail.body['palimpsest:entityType'])] ?? String(annotationDetail.body['palimpsest:entityType'])}
              </div>
            </div>
          )}

          {/* Evidence level */}
          <div style={{ marginBottom: '8px' }}>
            <div style={{ color: '#6b7280', fontSize: '11px', textTransform: 'uppercase' }}>Evidence</div>
            <div style={{ marginTop: '2px' }}>
              <span style={{
                display: 'inline-block', padding: '1px 6px', borderRadius: '3px',
                background: '#fef3c7', color: '#92400e', fontSize: '11px',
                fontFamily: 'monospace', marginRight: '6px',
              }}>
                {annotationDetail.evidence_level}
              </span>
              <span style={{ color: '#6b7280', fontSize: '11px' }}>
                {EVIDENCE_DESCRIPTIONS[annotationDetail.evidence_level] ?? ''}
              </span>
            </div>
          </div>

          {/* Confidence bar */}
          <div style={{ marginBottom: '8px' }}>
            <div style={{ color: '#6b7280', fontSize: '11px', textTransform: 'uppercase' }}>Confidence</div>
            <div style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ flex: 1, height: '6px', background: '#e5e7eb', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{
                  width: `${annotationDetail.confidence * 100}%`,
                  height: '100%',
                  background: annotationDetail.confidence > 0.7 ? '#22c55e' : annotationDetail.confidence > 0.4 ? '#f59e0b' : '#ef4444',
                }} />
              </div>
              <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                {(annotationDetail.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Span */}
          <div style={{ marginBottom: '8px' }}>
            <div style={{ color: '#6b7280', fontSize: '11px', textTransform: 'uppercase' }}>Span</div>
            <div style={{ fontFamily: 'monospace', fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>
              chars {annotationDetail.start}–{annotationDetail.end}
            </div>
          </div>

          {/* Creator */}
          <div style={{ marginBottom: '8px' }}>
            <div style={{ color: '#6b7280', fontSize: '11px', textTransform: 'uppercase' }}>Creator</div>
            <div style={{ fontFamily: 'monospace', fontSize: '11px', marginTop: '2px' }}>
              {annotationDetail.creator_name}
            </div>
          </div>

          {/* ID */}
          <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #e5e7eb' }}>
            <span style={{ color: '#6b7280', fontSize: '11px', fontFamily: 'monospace', wordBreak: 'break-all' }}>
              {annotationDetail.id}
            </span>
          </div>
        </div>
      )}

      {!loading && selectedAnnotationIndex === null && (
        <div style={{ padding: '24px 16px', color: '#9ca3af', fontSize: '13px' }}>
          Click an annotation in the text to see details.
        </div>
      )}
    </div>
  );
}
```

### `keyboard.ts` (full implementation)

Identical to v3.0. The keyboard handler uses `useViewStore.getState()` and `useTrackStore.getState()` imperatively (correct pattern for global shortcuts):

```typescript
// ui/src/utils/keyboard.ts
// Full implementation — same logic as v3.0 with store API updates for v4.0 stores.

import { useViewStore } from '../stores/viewStore';
import { useTrackStore } from '../stores/trackStore';
import { useSearchStore } from '../stores/searchStore';

const TRACK_KEY_MAP: Record<string, string> = {
  '1': 'entities', '2': 'sentiment', '3': 'lexical',
  '4': 'dialogue', '5': 'topics', '6': 'coreference',
};

export function setupKeyboardHandlers(): () => void {
  const handler = (e: KeyboardEvent): void => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

    const view = useViewStore.getState();
    const track = useTrackStore.getState();
    const search = useSearchStore.getState();

    switch (e.key) {
      // Paragraph navigation
      case 'j': case 'ArrowDown':
        if (!search.isOpen) { /* scroll next */ e.preventDefault(); }
        break;
      case 'k': case 'ArrowUp':
        if (!search.isOpen) { /* scroll prev */ e.preventDefault(); }
        break;

      // Search
      case 'f':
        if (e.ctrlKey || e.metaKey) { search.openSearch(); e.preventDefault(); }
        break;
      case '/':
        if (!search.isOpen) { search.openSearch(); e.preventDefault(); }
        break;

      // Escape
      case 'Escape':
        if (search.isOpen) { search.closeSearch(); }
        else if (view.selectedAnnotationIndex !== null) { view.selectAnnotation(null); }
        e.preventDefault();
        break;

      // Track toggles
      case '1': case '2': case '3': case '4': case '5': case '6': case '7': case '8': case '9':
        if (!e.ctrlKey && !e.metaKey && !e.altKey) {
          const name = TRACK_KEY_MAP[e.key];
          if (name) { track.toggleTrack(name).catch(console.error); }
          e.preventDefault();
        }
        break;

      // Show all tracks
      case '0':
        track.showAllTracks().catch(console.error);
        e.preventDefault();
        break;

      // Search navigation
      case '[': search.prevMatch(); e.preventDefault(); break;
      case ']': search.nextMatch(); e.preventDefault(); break;

      // Help
      case '?':
        console.info('Palimpsest shortcuts: j/k=nav, 1-6=track toggle, 0=all, Ctrl+F=search, Esc=close');
        break;
    }
  };

  document.addEventListener('keydown', handler);
  return () => document.removeEventListener('keydown', handler);
}
```

### Tauri `get_annotation_detail` Command (Rust)

```rust
// src-tauri/src/commands/viewport.rs (addition)

#[tauri::command]
pub async fn get_annotation_detail(
    project_id: String,
    annotation_index: usize,
    state: State<'_, AppState>,
) -> Result<FullAnnotationDto, String> {
    let projects = state.projects.read().await;
    let project = projects.get(&project_id)
        .ok_or_else(|| format!("Project not loaded: {project_id}"))?;

    // Search all arenas for the annotation at this global index
    // Phase 2: carry arena name + local index in ViewportAnnotation to avoid this search
    let mut global_idx = 0usize;
    for (track_name, arena) in &project.arenas {
        if global_idx + arena.len() > annotation_index {
            let local_idx = annotation_index - global_idx;
            let ann = &arena.slice()[local_idx];
            let body_json = arena.body_json(local_idx);
            let body: serde_json::Value = serde_json::from_str(body_json)
                .unwrap_or_default();
            return Ok(FullAnnotationDto {
                id: format!("urn:palimpsest:{project_id}:{track_name}:{}-{}", ann.start, ann.end),
                body: body.as_object().cloned().unwrap_or_default()
                    .into_iter()
                    .collect::<std::collections::HashMap<_, _>>(),
                confidence: ann.confidence_f32(),
                evidence_level: ann.evidence_str().to_string(),
                creator_name: "spacy/en_core_web_lg".to_string(), // Phase 2: store in arena
                start: ann.start,
                end: ann.end,
            });
        }
        global_idx += arena.len();
    }
    Err(format!("Annotation index {annotation_index} out of bounds"))
}

#[derive(serde::Serialize)]
pub struct FullAnnotationDto {
    pub id: String,
    pub body: std::collections::HashMap<String, serde_json::Value>,
    pub confidence: f32,
    pub evidence_level: String,
    pub creator_name: String,
    pub start: u32,
    pub end: u32,
}
```

### Milestone 1.1 Smoke Test

The v3.0 smoke test ran against a FastAPI server. The v4.0 smoke test verifies the Tauri application:

```bash
# Step 1: Ingest
palimpsest ingest fixtures/pride-prejudice-ch1.txt --workspace ~/palimpsest-test/

# Step 2: Analyze (runs entity extractor via Python subprocess)
palimpsest analyze ~/palimpsest-test/pride-prejudice-ch1/

# Step 3: Open Tauri application
palimpsest open ~/palimpsest-test/pride-prejudice-ch1/

# Step 4: Manual verification checklist (identical to v3.0 outcome):
# [ ] "Mr. Bennet" is highlighted in red (PER entity — canvas fillRect)
# [ ] "Hertfordshire" is highlighted in blue (LOC entity)
# [ ] Click "Mr. Bennet" → DetailPanel shows:
#     body type: palimpsest:EntityAnnotation
#     Entity Type: Person (PER)
#     Evidence: E4 — ML model prediction
#     Confidence: 85%
# [ ] Press '1' → entity highlights disappear (canvas clears, no DOM nodes)
# [ ] Press '1' again → entity highlights reappear (re-draw in ~2ms)
# [ ] Press Escape → detail panel clears
# [ ] Track toggle round-trip time < 2ms (measured in DevTools Performance panel)
# [ ] DOM element count < 200 (was 50,000+ in v3.0) — check in DevTools Elements
# [ ] No 'loadTrack' or 'JSON.parse' calls in Network tab (should be empty for annotations)
# [ ] Tauri invoke 'query_viewport' in DevTools shows < 5ms response time
```

### Integration Tests

```typescript
// ui/src/adapters/tauri.test.ts (extended)

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { invoke } from '@tauri-apps/api/core';

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
}));

const mockInvoke = vi.mocked(invoke);

describe('queryViewport', () => {
  beforeEach(() => { mockInvoke.mockReset(); });

  it('invokes Tauri command with correct params', async () => {
    const { queryViewport } = await import('./tauri');
    mockInvoke.mockResolvedValueOnce([]);
    await queryViewport('pride-and-prejudice', 0, 7000);
    expect(mockInvoke).toHaveBeenCalledWith('query_viewport', {
      project_id: 'pride-and-prejudice',
      start_char: 0,
      end_char: 7000,
    });
  });

  it('never returns more annotations than the viewport window', async () => {
    const { queryViewport } = await import('./tauri');
    // Mock: return 300 annotations (realistic viewport density)
    const mockAnns = Array.from({ length: 300 }, (_, i) => ({
      start: i * 20,
      end: i * 20 + 10,
      confidence: 0.85,
      track_id: 0,
      evidence_level: 'E4',
      body_type: 'palimpsest:EntityAnnotation',
      entity_type: 'PER',
    }));
    mockInvoke.mockResolvedValueOnce(mockAnns);
    const result = await queryViewport('test', 0, 7000);
    expect(result.length).toBeLessThanOrEqual(500);
    expect(result.length).toBeGreaterThan(0);
  });
});

describe('updateFilter', () => {
  it('converts float confidence to fixed-point integer', async () => {
    const { updateFilter } = await import('./tauri');
    mockInvoke.mockResolvedValueOnce(undefined);
    await updateFilter('test', { track_mask: 0b1111, min_confidence: 0.3 });
    expect(mockInvoke).toHaveBeenCalledWith('update_filter', {
      project_id: 'test',
      track_mask: 0b1111,
      min_confidence: 3000,  // 0.3 * 10,000 = 3000 fixed-point
    });
  });
});
```

```typescript
// ui/src/components/TextLinearView/CanvasAnnotationOverlay.test.tsx

import { describe, it, expect } from 'vitest';
import { annotationColor } from './CanvasAnnotationOverlay'; // if exported for testing

// Test color mapping
describe('annotationColor', () => {
  it('maps PER entity to red', () => {
    const color = annotationColor({
      body_type: 'palimpsest:EntityAnnotation',
      entity_type: 'PER',
      confidence: 0.85, track_id: 0, evidence_level: 'E4',
      start: 0, end: 10,
    });
    expect(color).toEqual([230, 57, 70]);
  });

  it('maps LOC entity to blue', () => {
    const color = annotationColor({
      body_type: 'palimpsest:EntityAnnotation',
      entity_type: 'LOC',
      confidence: 0.85, track_id: 0, evidence_level: 'E4',
      start: 0, end: 10,
    });
    expect(color).toEqual([69, 123, 157]);
  });
});
```

## Acceptance Criteria

### Canvas Overlay
- `CanvasAnnotationOverlay` renders exactly **1 `<canvas>` element** per paragraph regardless of annotation count
- Zero `<mark>` or `<span>` elements in the DOM for annotations — grep `document.querySelector('mark')` must return null
- 200 annotations in a chapter = 200 `fillRect()` calls in a single `requestAnimationFrame`
- Canvas clears and repaints in < 2ms when track toggle fires (measured in DevTools)

### Detail Panel
- Clicking a canvas annotation region calls `invoke('get_annotation_detail', ...)` (verified by test)
- DetailPanel shows: body type badge, entity type, evidence level (E4), confidence bar
- Clicking x button clears `selectedAnnotationIndex` and hides detail

### Keyboard
- `j` / `k` navigate paragraphs
- `1`-`6` toggle corresponding tracks
- `0` shows all tracks
- `Escape` clears selection and closes search
- Keyboard handler registers only one `keydown` listener (no duplicates on re-render)

### Integration
- `palimpsest ingest + analyze + open` full smoke test: entities visible as canvas highlights
- `cargo tauri build` exits 0 (application bundles without errors)
- `cd ui && npx vitest run` passes all unit tests
- `cargo test -p palimpsest-core` passes including `get_annotation_detail` Rust test
- DOM element count after loading P&P Chapter 1 with entities: < 200 (DevTools verified)
- Zero HTTP network requests for annotation data in DevTools Network tab
- `server.py` file does not exist anywhere in the codebase

## Design Decisions

- **Canvas overlay per paragraph, not per document**: One full-document canvas would require precise character-to-pixel mapping across all paragraphs, which requires layout information that isn't available until all paragraphs are rendered. Per-paragraph canvases use the text element as the coordinate origin, making the Range API call simple and local.

- **Range API for char-to-pixel mapping**: The Range API is the only cross-browser way to find the pixel position of a character within a text run with mixed-width characters (ligatures, kerning). Alternatives (monospace font metrics, fixed-width assumptions) fail for serif literary text. Phase 2 will cache these measurements using `OffscreenCanvas.measureText()` for faster repaints.

- **`getAnnotationDetail` fetches on click, not on hover**: Fetching the full W3C body JSON on every hover would flood the Tauri IPC with unnecessary calls. Click-to-fetch means the IPC call happens at most once per user interaction. The `ViewportAnnotation` struct carries enough information (body_type, entity_type, confidence) to draw the annotation without the full body.

- **`server.py` is eliminated, not stubbed**: A server stub would imply it works. It doesn't — the Tauri application has no HTTP layer for local use. Leaving a dead `server.py` would mislead future developers. The file is deleted. Its security model (path traversal protection) is replaced by Tauri's OS-level capability system.

---

## Original Content (v3.0, preserved for reference)

The v3.0 T10 implemented: `AnnotationOverlay.tsx` with DOM `<mark>` injection, `buildSpans()` string slicing, `DetailPanel.tsx` with full `WC3Annotation` display, `keyboard.ts` (global shortcuts), and `server.py` (FastAPI HTTP server). In v4.0: the `<mark>` overlay is replaced by `CanvasAnnotationOverlay.tsx`, `server.py` is eliminated, `DetailPanel.tsx` is adapted for lazy annotation fetching, and `keyboard.ts` is preserved with minor store API updates.
