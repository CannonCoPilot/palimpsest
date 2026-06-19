# T09: Browser Scaffolding (Tauri App + WebGPU Canvas + Virtual Scroll)

**Milestone**: 1.1 — Ingest + Normalize + First Track + Minimal Browser
**Estimated effort**: 8 hours → 12 hours (v4.0: Tauri IPC replaces HTTP, canvas overlay replaces DOM spans, virtual scroll from day one)
**Dependencies**: T01 (Tauri scaffold), T03 (annotation model — TypeScript types)
**Outputs**: All stores, Tauri command adapters, layout components, VirtualTextView foundation; browser renders project text with no DOM annotation spans

---

## v4.0 Critical Review

**T09 in v3.0 scaffolds a browser that fetches JSONL over HTTP and puts 18,760 annotation objects into the JavaScript heap. This is precisely the performance pathology the architecture document diagnoses. Starting fresh from this scaffold guarantees reaching the same performance ceiling.**

Specific failures:

1. **`loadTrack(url)` calls `fetch()` then `JSON.parse()`.** This is the root cause of 65MB heap usage. In v4.0 there is no `loadTrack` function — there is no JSONL fetched to the browser at all. Annotation data lives in the Rust arena. The browser calls `invoke('query_viewport', {start, end})` and receives only the 100-300 annotations visible in the current viewport.

2. **`projectStore.tracks` is `Record<string, WC3Annotation[]>`.** Storing full annotation arrays in Zustand state is the v3.0 catastrophe. In v4.0, `projectStore` holds zero annotation objects. It holds metadata only. Annotation data is requested on demand via Tauri commands.

3. **`TextLinearView` renders all 2,569 paragraphs as DOM `<p>` elements.** Even with the lazy annotation overlay, 2,569 `<p>` elements is 2,569 layout objects in the browser. On initial load this causes a layout pass that takes hundreds of milliseconds. In v4.0, `VirtualTextView` renders only 30 visible paragraphs + 20 overscan paragraphs = 50 DOM elements maximum.

4. **`AnnotationOverlay` injects `<mark>` and `<span>` elements.** Each annotation creates DOM nodes. 200 entities in a chapter = 200 `<mark>` elements plus 200+ text node siblings. This causes 200+ style recalculations per scroll event. In v4.0, a `<canvas>` overlaid on the text container draws all annotations as colored rectangles in a single `requestAnimationFrame` paint. Zero DOM nodes per annotation.

5. **`stores/projectStore.ts` calls `loadTrack('/data/{id}/tracks/entities.jsonl')`.** This URL assumes a FastAPI HTTP server that doesn't exist in v4.0. In v4.0, all data access uses `@tauri-apps/api`'s `invoke()` function.

6. **The Vite proxy configuration proxies `/api` and `/data` to `localhost:8080`.** This is meaningless in Tauri — there is no `localhost:8080` server. The proxy config must be removed entirely.

7. **Four stores hold annotation data across multiple concerns.** In v4.0, stores are further thinned: only UI state (track visibility, confidence sliders, selected annotation, scroll position). No annotation arrays anywhere in TypeScript.

**What must change — everything in the data path:**
- `loadTrack()` → eliminated
- `projectStore.tracks` → eliminated
- `AnnotationAdapter.ts` HTTP functions → `tauri.ts` invoke wrappers
- `TextLinearView` → `VirtualTextView` with windowed rendering
- `AnnotationOverlay` DOM spans → Canvas annotation layer (implemented in T10)
- Vite proxy → removed
- All store state that holds `WC3Annotation[]` → eliminated

---

## v4.0 Rewrite

### Tauri Command Interface (`ui/src/adapters/tauri.ts`)

This is the single data access module. All annotation data flows through here.

```typescript
// ui/src/adapters/tauri.ts
//
// Tauri command wrappers. All data access goes through invoke().
// No HTTP fetch for annotation data — ever.

import { invoke } from '@tauri-apps/api/core';

// --- Types returned by Rust Tauri commands ---

/** Metadata returned by load_project command */
export interface ProjectMeta {
  id: string;
  title: string;
  author: string | null;
  year: number | null;
  language: string;
  word_count: number;
  sentence_count: number;
  paragraph_count: number;
  section_count: number;
  character_count: number;
  reference_sha256: string;
  palimpsest_version: string;
}

/** A packed annotation slice returned for a viewport query.
 *  Only the fields needed for rendering are included.
 *  Full W3C body is fetched separately when user clicks an annotation. */
export interface ViewportAnnotation {
  start: number;               // character offset (inclusive)
  end: number;                 // character offset (exclusive)
  confidence: number;          // float 0.0-1.0 (decoded from u16 fixed-point)
  track_id: number;            // 0=entities, 1=sentiment, etc.
  evidence_level: string;      // "E1" through "E5"
  body_type: string;           // "palimpsest:EntityAnnotation" etc.
  entity_type: string | null;  // "PER", "LOC", "ORG", "WORK", or null
}

/** Full W3C annotation object — only fetched when user clicks */
export interface FullAnnotation {
  id: string;
  body: Record<string, unknown>;
  confidence: number;
  evidence_level: string;
  creator_name: string;
  start: number;
  end: number;
}

/** Pre-computed density histogram for OverviewBar */
export interface DensityHistogram {
  bins: Float32Array;     // annotation counts per bin
  bin_width: number;      // characters per bin
  doc_length: number;     // total document character count
  track_ids: number[];    // which tracks contributed
}

/** Filter state sent to Rust on track toggle */
export interface FilterState {
  track_mask: number;         // u64 as number (JS bigint issues avoided with u32 per track)
  min_confidence: number;     // float 0.0-1.0
}

// --- Tauri command invocations ---

/** Load a project by directory path. Returns metadata only — no annotation data. */
export async function loadProject(projectDir: string): Promise<ProjectMeta> {
  return invoke<ProjectMeta>('load_project', { project_dir: projectDir });
}

/** List all projects in the workspace. */
export async function listProjects(workspaceDir: string): Promise<ProjectMeta[]> {
  return invoke<ProjectMeta[]>('list_projects', { workspace_dir: workspaceDir });
}

/**
 * Query annotations visible in the current viewport.
 *
 * Calls Rust RangeIndex.query(start, end) + FilterEngine.filter(track_mask, confidence).
 * Returns only the annotations for visible paragraphs.
 * Target: < 5ms round-trip.
 */
export async function queryViewport(
  projectId: string,
  startChar: number,
  endChar: number,
): Promise<ViewportAnnotation[]> {
  return invoke<ViewportAnnotation[]>('query_viewport', {
    project_id: projectId,
    start_char: startChar,
    end_char: endChar,
  });
}

/**
 * Update the filter state (track visibility + confidence threshold).
 *
 * Rust applies bitmask in ~1μs (SIMD pass). Does not return data —
 * caller must re-invoke queryViewport to get updated results.
 * Target: < 2ms total (filter update + viewport re-query).
 */
export async function updateFilter(
  projectId: string,
  filter: FilterState,
): Promise<void> {
  return invoke<void>('update_filter', {
    project_id: projectId,
    track_mask: filter.track_mask,
    min_confidence: Math.round(filter.min_confidence * 10_000), // convert to u16 fixed-point
  });
}

/**
 * Get pre-computed density histogram for the OverviewBar.
 * Returned as flat array of bin counts, uploaded to GPU as Float32 buffer.
 */
export async function getDensityHistogram(
  projectId: string,
  binCount: number,
): Promise<DensityHistogram> {
  return invoke<DensityHistogram>('get_histogram', {
    project_id: projectId,
    bin_count: binCount,
  });
}

/**
 * Get the full W3C annotation body for a clicked annotation.
 * Only called on user click — not on every render.
 */
export async function getAnnotationDetail(
  projectId: string,
  annotationIndex: number,
): Promise<FullAnnotation> {
  return invoke<FullAnnotation>('get_annotation_detail', {
    project_id: projectId,
    annotation_index: annotationIndex,
  });
}

/**
 * Get the reference text for a project.
 * Called once on project load; stored in projectStore.referenceText.
 * ~700KB string — acceptable for one-time load.
 */
export async function getReferenceText(projectId: string): Promise<string> {
  return invoke<string>('get_reference_text', { project_id: projectId });
}
```

### Zustand Stores (dramatically thinned)

**`ui/src/stores/projectStore.ts`** — holds only metadata and reference text, no annotations:

```typescript
import { create } from 'zustand';
import { ProjectMeta, loadProject, getReferenceText } from '../adapters/tauri';

interface ProjectState {
  projectId: string | null;
  projectDir: string | null;
  metadata: ProjectMeta | null;
  referenceText: string | null;
  loadingState: 'idle' | 'loading' | 'ready' | 'error';
  loadingStep: string;
  error: string | null;

  loadProject: (projectDir: string) => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projectId: null,
  projectDir: null,
  metadata: null,
  referenceText: null,
  loadingState: 'idle',
  loadingStep: '',
  error: null,

  loadProject: async (projectDir: string) => {
    set({ loadingState: 'loading', loadingStep: 'Loading project...', error: null });
    try {
      // Tauri command: loads JSONL into Rust arena, returns metadata only
      set({ loadingStep: 'Loading annotation data...' });
      const metadata = await loadProject(projectDir);

      set({ loadingStep: 'Loading reference text...' });
      const referenceText = await getReferenceText(metadata.id);

      set({
        projectId: metadata.id,
        projectDir,
        metadata,
        referenceText,
        loadingState: 'ready',
        loadingStep: '',
      });
    } catch (err) {
      set({ loadingState: 'error', error: String(err), loadingStep: '' });
    }
  },
}));
```

**`ui/src/stores/trackStore.ts`** — track visibility + confidence. No annotation arrays:

```typescript
import { create } from 'zustand';
import { updateFilter, queryViewport } from '../adapters/tauri';
import { useProjectStore } from './projectStore';
import { useViewStore } from './viewStore';

// Track IDs match Rust track_name_to_id()
export const TRACK_IDS: Record<string, number> = {
  entities: 0, sentiment: 1, lexical: 2, dialogue: 3, topics: 4, segments: 5,
};

interface TrackState {
  // Bitfield: bit N is set if track N is visible
  trackMask: number;
  // Confidence threshold per track [0.0, 1.0]
  confidenceThreshold: number;  // shared across all tracks in Phase 1

  toggleTrack: (trackName: string) => Promise<void>;
  showAllTracks: () => Promise<void>;
  setConfidenceThreshold: (threshold: number) => Promise<void>;
  isTrackVisible: (trackName: string) => boolean;
  currentMask: () => number;
}

const ALL_TRACKS_MASK = 0b1111_1111; // 8 tracks, all visible

export const useTrackStore = create<TrackState>((set, get) => ({
  trackMask: ALL_TRACKS_MASK,
  confidenceThreshold: 0.0,

  toggleTrack: async (trackName: string) => {
    const trackId = TRACK_IDS[trackName] ?? 255;
    const newMask = get().trackMask ^ (1 << trackId);
    set({ trackMask: newMask });

    const projectId = useProjectStore.getState().projectId;
    if (!projectId) return;

    // Inform Rust of updated filter — SIMD pass takes ~1μs
    await updateFilter(projectId, {
      track_mask: newMask,
      min_confidence: get().confidenceThreshold,
    });
    // Trigger viewport re-query via viewStore
    useViewStore.getState().triggerViewportRefresh();
  },

  showAllTracks: async () => {
    set({ trackMask: ALL_TRACKS_MASK });
    const projectId = useProjectStore.getState().projectId;
    if (!projectId) return;
    await updateFilter(projectId, {
      track_mask: ALL_TRACKS_MASK,
      min_confidence: get().confidenceThreshold,
    });
    useViewStore.getState().triggerViewportRefresh();
  },

  setConfidenceThreshold: async (threshold: number) => {
    set({ confidenceThreshold: threshold });
    const projectId = useProjectStore.getState().projectId;
    if (!projectId) return;
    await updateFilter(projectId, {
      track_mask: get().trackMask,
      min_confidence: threshold,
    });
    useViewStore.getState().triggerViewportRefresh();
  },

  isTrackVisible: (trackName: string) => {
    const trackId = TRACK_IDS[trackName] ?? 255;
    return (get().trackMask >> trackId & 1) === 1;
  },

  currentMask: () => get().trackMask,
}));
```

**`ui/src/stores/viewStore.ts`** — scroll position, selected annotation index, viewport refresh trigger:

```typescript
import { create } from 'zustand';

interface ViewState {
  // Scroll position as character offset (drives viewport query)
  viewportStartChar: number;
  viewportEndChar: number;
  // Selected annotation (Rust index, for getAnnotationDetail call)
  selectedAnnotationIndex: number | null;
  // Refresh counter — increment to trigger viewport re-query
  viewportRefreshCount: number;
  // Paragraph heights (cached after initial measure)
  paragraphHeights: number[];

  setViewport: (startChar: number, endChar: number) => void;
  selectAnnotation: (index: number | null) => void;
  triggerViewportRefresh: () => void;
  setParagraphHeights: (heights: number[]) => void;
}

export const useViewStore = create<ViewState>((set) => ({
  viewportStartChar: 0,
  viewportEndChar: 7000,
  selectedAnnotationIndex: null,
  viewportRefreshCount: 0,
  paragraphHeights: [],

  setViewport: (startChar, endChar) => set({ viewportStartChar: startChar, viewportEndChar: endChar }),
  selectAnnotation: (index) => set({ selectedAnnotationIndex: index }),
  triggerViewportRefresh: () => set((state) => ({ viewportRefreshCount: state.viewportRefreshCount + 1 })),
  setParagraphHeights: (heights) => set({ paragraphHeights: heights }),
}));
```

**`ui/src/stores/searchStore.ts`** — unchanged from v3.0 (search is UI state only).

### `VirtualTextView` Component

The critical performance component. Renders only ~50 paragraphs at a time:

```typescript
// ui/src/components/TextLinearView/VirtualTextView.tsx
//
// Virtual scroll: renders only paragraphs in the visible viewport + overscan.
// Paragraph heights are measured once; a spacer div maintains scroll position.
// Annotations are fetched via Tauri invoke for the visible char range only.

import React, { useEffect, useRef, useCallback, useState } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useViewStore } from '../../stores/viewStore';
import { useTrackStore } from '../../stores/trackStore';
import { queryViewport, ViewportAnnotation } from '../../adapters/tauri';

const OVERSCAN_PARAGRAPHS = 10;  // render 10 paragraphs above/below visible area
const ESTIMATED_PARAGRAPH_HEIGHT = 80;  // pixels, before measurement

export function VirtualTextView(): JSX.Element {
  const referenceText = useProjectStore((s) => s.referenceText);
  const projectId = useProjectStore((s) => s.projectId);
  const { viewportRefreshCount, setParagraphHeights, setViewport } = useViewStore();

  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(600);
  const [paragraphs, setParagraphs] = useState<string[]>([]);
  const [paragraphOffsets, setParagraphOffsets] = useState<[number, number][]>([]);
  const [paragraphHeights, setParagraphHeightsLocal] = useState<number[]>([]);
  const [viewportAnnotations, setViewportAnnotations] = useState<ViewportAnnotation[]>([]);
  const [isFetchingAnnotations, setIsFetchingAnnotations] = useState(false);

  // Split text into paragraphs + compute char offsets (once)
  useEffect(() => {
    if (!referenceText) return;
    const paras: string[] = [];
    const offsets: [number, number][] = [];
    let pos = 0;
    const re = /\n\n+/g;
    let match: RegExpExecArray | null;
    let lastEnd = 0;

    while ((match = re.exec(referenceText)) !== null) {
      const block = referenceText.slice(lastEnd, match.index);
      if (block.trim()) {
        paras.push(block);
        offsets.push([lastEnd, match.index]);
      }
      lastEnd = match.index + match[0].length;
      pos = lastEnd;
    }
    // Last paragraph
    const last = referenceText.slice(lastEnd);
    if (last.trim()) {
      paras.push(last);
      offsets.push([lastEnd, referenceText.length]);
    }

    setParagraphs(paras);
    setParagraphOffsets(offsets);
    setParagraphHeightsLocal(new Array(paras.length).fill(ESTIMATED_PARAGRAPH_HEIGHT));
  }, [referenceText]);

  // Handle scroll
  const onScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop: st, clientHeight } = e.currentTarget;
    setScrollTop(st);
    setContainerHeight(clientHeight);
  }, []);

  // Compute which paragraphs are visible
  const totalHeight = paragraphHeights.reduce((s, h) => s + h, 0);
  let cumulativeHeight = 0;
  let firstVisible = 0;
  let lastVisible = paragraphs.length - 1;

  for (let i = 0; i < paragraphHeights.length; i++) {
    if (cumulativeHeight + paragraphHeights[i] > scrollTop) {
      firstVisible = i;
      break;
    }
    cumulativeHeight += paragraphHeights[i];
  }

  cumulativeHeight = 0;
  for (let i = 0; i < paragraphHeights.length; i++) {
    cumulativeHeight += paragraphHeights[i];
    if (cumulativeHeight >= scrollTop + containerHeight) {
      lastVisible = i;
      break;
    }
  }

  const renderStart = Math.max(0, firstVisible - OVERSCAN_PARAGRAPHS);
  const renderEnd = Math.min(paragraphs.length - 1, lastVisible + OVERSCAN_PARAGRAPHS);

  // Compute spacer height above rendered paragraphs
  const spacerTop = paragraphHeights.slice(0, renderStart).reduce((s, h) => s + h, 0);
  const spacerBottom = paragraphHeights.slice(renderEnd + 1).reduce((s, h) => s + h, 0);

  // Query viewport annotations when visible char range changes
  useEffect(() => {
    if (!projectId || paragraphOffsets.length === 0) return;

    const startChar = paragraphOffsets[renderStart]?.[0] ?? 0;
    const endChar = paragraphOffsets[renderEnd]?.[1] ?? 7000;

    setViewport(startChar, endChar);

    setIsFetchingAnnotations(true);
    queryViewport(projectId, startChar, endChar)
      .then((anns) => {
        setViewportAnnotations(anns);
        setIsFetchingAnnotations(false);
      })
      .catch((err) => {
        console.error('queryViewport failed:', err);
        setIsFetchingAnnotations(false);
      });
  }, [projectId, renderStart, renderEnd, viewportRefreshCount, paragraphOffsets]);

  if (!referenceText || paragraphs.length === 0) {
    return <div style={{ padding: '24px', color: '#aaa' }}>No text loaded.</div>;
  }

  return (
    <div
      ref={containerRef}
      onScroll={onScroll}
      style={{ height: '100%', overflowY: 'auto', position: 'relative' }}
      role="document"
      aria-label="Reference text"
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        {/* Top spacer */}
        {spacerTop > 0 && <div style={{ height: spacerTop }} aria-hidden="true" />}

        {/* Rendered paragraphs — maximum ~50 at a time */}
        <div
          style={{ padding: '24px', maxWidth: '720px', margin: '0 auto', lineHeight: 1.7 }}
        >
          {paragraphs.slice(renderStart, renderEnd + 1).map((para, relIdx) => {
            const absIdx = renderStart + relIdx;
            const [paraStart, paraEnd] = paragraphOffsets[absIdx] ?? [0, 0];

            // Filter viewport annotations to this paragraph
            const paraAnns = viewportAnnotations.filter(
              (a) => a.start < paraEnd && a.end > paraStart,
            );

            return (
              <VirtualParagraph
                key={absIdx}
                index={absIdx}
                text={para}
                paragraphStart={paraStart}
                annotations={paraAnns}
                onHeightMeasured={(h) => {
                  setParagraphHeightsLocal((prev) => {
                    const next = [...prev];
                    next[absIdx] = h;
                    return next;
                  });
                  setParagraphHeights(paragraphHeights); // sync to viewStore
                }}
              />
            );
          })}
        </div>

        {/* Bottom spacer */}
        {spacerBottom > 0 && <div style={{ height: spacerBottom }} aria-hidden="true" />}
      </div>
    </div>
  );
}
```

### `VirtualParagraph` Component

Renders a single paragraph. The canvas annotation overlay is implemented in T10. This component is the mount point:

```typescript
// ui/src/components/TextLinearView/VirtualParagraph.tsx

import React, { useRef, useEffect } from 'react';
import { ViewportAnnotation } from '../../adapters/tauri';

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
  const ref = useRef<HTMLDivElement>(null);

  // Measure height after render and report to parent
  useEffect(() => {
    if (ref.current) {
      const h = ref.current.getBoundingClientRect().height;
      onHeightMeasured(h);
    }
  });

  return (
    <div
      ref={ref}
      data-paragraph-index={index}
      style={{ position: 'relative', marginBottom: '1.2em' }}
    >
      {/* Plain text — canvas overlay renders annotations in T10 */}
      <p style={{ margin: 0, fontFamily: 'Georgia, "Crimson Pro", serif', fontSize: '16px' }}>
        {text}
      </p>
      {/* CanvasAnnotationOverlay mounted here in T10 */}
      {/* {annotations.length > 0 && (
        <CanvasAnnotationOverlay
          text={text}
          paragraphStart={paragraphStart}
          annotations={annotations}
        />
      )} */}
    </div>
  );
}
```

### Layout Components

`AppLayout.tsx`, `Toolbar.tsx`, `ResizablePanel.tsx` — identical structure to v3.0 with one change: no `server.proxy` assumptions, no `loadTrack` calls. The `Toolbar` displays metadata from `projectStore` (same as v3.0). `ResizablePanel` is identical (drag-to-resize, DOM event listeners).

### Tauri Commands (Rust)

**`src-tauri/src/commands/viewport.rs`**:

```rust
//! query_viewport Tauri command: returns annotations for visible character range.

use tauri::State;
use palimpsest_core::project::LoadedProject;
use crate::AppState;

/// Serialized viewport annotation (sent to TypeScript).
#[derive(serde::Serialize)]
pub struct ViewportAnnotationDto {
    pub start: u32,
    pub end: u32,
    pub confidence: f32,
    pub track_id: u8,
    pub evidence_level: String,
    pub body_type: String,
    pub entity_type: Option<String>,
}

#[tauri::command]
pub async fn query_viewport(
    project_id: String,
    start_char: u32,
    end_char: u32,
    state: State<'_, AppState>,
) -> Result<Vec<ViewportAnnotationDto>, String> {
    let projects = state.projects.read().await;
    let project = projects.get(&project_id)
        .ok_or_else(|| format!("Project not loaded: {project_id}"))?;

    let mut results = Vec::new();

    // Query each track's arena using RangeIndex
    for (track_name, arena) in &project.arenas {
        let indices = project.range_indices
            .get(track_name)
            .map(|idx| idx.query(start_char, end_char))
            .unwrap_or_default();

        for idx in indices {
            let ann = &arena.slice()[idx];
            // Apply current filter mask
            if !ann.track_visible(project.filter_state.track_mask) {
                continue;
            }
            if !ann.passes_confidence(project.filter_state.min_confidence_fp) {
                continue;
            }

            // Decode body JSON to extract body_type and entity_type
            let body_json = arena.body_json(idx);
            let (body_type, entity_type) = parse_body_fields(body_json);

            results.push(ViewportAnnotationDto {
                start: ann.start,
                end: ann.end,
                confidence: ann.confidence_f32(),
                track_id: ann.track_id,
                evidence_level: ann.evidence_str().to_string(),
                body_type,
                entity_type,
            });
        }
    }

    // Sort by start offset for consistent rendering
    results.sort_by_key(|a| a.start);
    Ok(results)
}

fn parse_body_fields(body_json: &str) -> (String, Option<String>) {
    if let Ok(v) = serde_json::from_str::<serde_json::Value>(body_json) {
        let body_type = v["type"].as_str().unwrap_or("unknown").to_string();
        let entity_type = v["palimpsest:entityType"].as_str().map(String::from);
        (body_type, entity_type)
    } else {
        ("unknown".to_string(), None)
    }
}
```

### Vitest Tests

```typescript
// ui/src/adapters/tauri.test.ts
import { describe, it, expect, vi } from 'vitest';
import { TRACK_IDS } from '../stores/trackStore';

// Mock @tauri-apps/api/core to avoid Tauri runtime dependency in tests
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
}));

describe('TRACK_IDS', () => {
  it('matches Rust track_name_to_id constants', () => {
    expect(TRACK_IDS.entities).toBe(0);
    expect(TRACK_IDS.sentiment).toBe(1);
    expect(TRACK_IDS.segments).toBe(5);
  });
});

describe('trackMask bitmask', () => {
  it('toggle entities clears bit 0', () => {
    const initial = 0b1111_1111;
    const toggled = initial ^ (1 << TRACK_IDS.entities);
    expect(toggled & (1 << TRACK_IDS.entities)).toBe(0);  // entities hidden
    expect(toggled & (1 << TRACK_IDS.sentiment)).toBe(2); // sentiment still visible
  });
});
```

```typescript
// ui/src/components/TextLinearView/VirtualParagraph.test.tsx
import { describe, it, expect } from 'vitest';
// Test that VirtualParagraph renders text content
// (annotation overlay tested separately in T10)
```

## Acceptance Criteria

- `cd ui && npx tsc --noEmit` exits 0
- `cd ui && npx eslint src --ext .ts,.tsx` exits 0
- `cd ui && npx vitest run` passes all unit tests
- `cargo tauri dev` starts without errors; browser shows "Palimpsest — loading..."
- Loading a project via `loadProject(projectDir)` returns `ProjectMeta` with no annotation arrays in JS
- `queryViewport` mocked test returns 0-300 `ViewportAnnotation` objects (never the full 18,760)
- `VirtualTextView` renders at most `2 * OVERSCAN_PARAGRAPHS + visible_count` paragraph DOM elements (never > 70)
- No `loadTrack(url)` call exists anywhere in the codebase (grep must find zero hits)
- No `WC3Annotation[]` stored in any Zustand store (grep for `WC3Annotation` in store files must be zero)
- `projectStore.tracks` field does not exist
- `trackStore.toggleTrack('entities')` calls `invoke('update_filter', ...)` (verified by mock in test)

## Design Decisions

- **`queryViewport` returns ~100-300 annotations, never the full 18,760**: The Rust `RangeIndex.query(start, end)` returns only the annotations overlapping the visible 7,000-character window. This is the architectural guarantee that the JS heap stays empty.

- **`VirtualTextView` builds paragraph offsets in a linear scan, not `indexOf`**: Same fix as `_split_paragraphs` in T05. Literary prose has repeated substrings; `indexOf` in a loop is O(n²).

- **Paragraph heights cached after first measurement**: Heights are measured via `getBoundingClientRect()` after the first render. Subsequent re-renders use the cached height for virtual scroll calculations, avoiding repeated layout passes.

- **Canvas overlay deferred to T10**: T09 scaffolds `VirtualParagraph` as the mount point for the canvas layer but does not implement it. The paragraph renders plain text only in T09. T10 adds the canvas overlay without changing the component structure.

---

## Original Content (v3.0, preserved for reference)

The v3.0 T09 defined HTTP-based adapters, annotation-array stores, and DOM-span-based rendering. All of these are replaced. The layout structure (Toolbar, ResizablePanel, main area) is preserved. The store names are preserved with thinned interfaces. The component hierarchy (AppLayout > VirtualTextView > VirtualParagraph) replaces the v3.0 (AppLayout > TextLinearView > ParagraphView > AnnotationOverlay) hierarchy.
