/**
 * Browser tab viewport state — UCSC-style linear coordinate navigation.
 */

import { create } from 'zustand';

export type LaneDisplayMode = 'ribbon' | 'detail' | 'condensed' | 'hidden';

interface BrowserState {
  viewStart: number;
  viewEnd: number;
  totalChars: number;
  drawerOpen: boolean;
  laneDisplayModes: Record<string, LaneDisplayMode>;
  textHighlightTracks: Set<string>;
  highlightedAnnotation: { start: number; end: number; trackName: string } | null;
  overviewBarHidden: Set<string>;

  setViewport: (start: number, end: number) => void;
  setTotalChars: (total: number) => void;
  pan: (deltaChars: number) => void;
  zoomAroundCenter: (factor: number) => void;
  zoomToRange: (start: number, end: number) => void;
  zoomToFull: () => void;
  toggleDrawer: () => void;
  setLaneDisplayMode: (name: string, mode: LaneDisplayMode) => void;
  toggleTextHighlight: (name: string) => void;
  setHighlightedAnnotation: (ann: { start: number; end: number; trackName: string } | null) => void;
  toggleOverviewBarTrack: (name: string) => void;
}

const MIN_VIEWPORT = 50;

export const LANE_HEIGHTS: Record<LaneDisplayMode, number> = {
  ribbon: 28,
  detail: 56,
  condensed: 12,
  hidden: 0,
};

export const useBrowserStore = create<BrowserState>((set, get) => ({
  viewStart: 0,
  viewEnd: 10000,
  totalChars: 10000,
  drawerOpen: false,
  laneDisplayModes: {},
  textHighlightTracks: new Set(),
  highlightedAnnotation: null,
  overviewBarHidden: new Set(),

  setViewport: (start, end): void => {
    const { totalChars } = get();
    const s = Math.max(0, start);
    const e = Math.min(totalChars, end);
    if (e - s >= MIN_VIEWPORT) set({ viewStart: s, viewEnd: e });
  },

  setTotalChars: (total): void => set({ totalChars: total, viewEnd: total }),

  pan: (deltaChars): void => {
    const { viewStart, viewEnd, totalChars } = get();
    const width = viewEnd - viewStart;
    let newStart = viewStart + deltaChars;
    if (newStart < 0) newStart = 0;
    if (newStart + width > totalChars) newStart = totalChars - width;
    set({ viewStart: newStart, viewEnd: newStart + width });
  },

  zoomAroundCenter: (factor): void => {
    const { viewStart, viewEnd, totalChars } = get();
    const center = (viewStart + viewEnd) / 2;
    const halfWidth = ((viewEnd - viewStart) / 2) * factor;
    const clampedHalf = Math.min(totalChars / 2, Math.max(MIN_VIEWPORT / 2, halfWidth));
    const s = Math.max(0, center - clampedHalf);
    const e = Math.min(totalChars, center + clampedHalf);
    set({ viewStart: s, viewEnd: e });
  },

  zoomToRange: (start, end): void => {
    const { totalChars } = get();
    set({ viewStart: Math.max(0, start), viewEnd: Math.min(totalChars, end) });
  },

  zoomToFull: (): void => {
    const { totalChars } = get();
    set({ viewStart: 0, viewEnd: totalChars });
  },

  toggleDrawer: (): void => set((s) => ({ drawerOpen: !s.drawerOpen })),

  setLaneDisplayMode: (name, mode): void => set((s) => ({
    laneDisplayModes: { ...s.laneDisplayModes, [name]: mode },
  })),

  toggleTextHighlight: (name): void => set((s) => {
    const next = new Set(s.textHighlightTracks);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    return { textHighlightTracks: next };
  }),

  setHighlightedAnnotation: (ann): void => set({ highlightedAnnotation: ann }),

  toggleOverviewBarTrack: (name): void => set((s) => {
    const next = new Set(s.overviewBarHidden);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    return { overviewBarHidden: next };
  }),
}));
