/**
 * View state store — viewport, zoom, selection, scroll requests.
 */

import { create } from 'zustand';
import type { W3CAnnotation } from '../adapters/AnnotationAdapter';

export type ZoomLevel = 'work' | 'chapter' | 'paragraph' | 'sentence';
export type TabId = 'reading' | 'texthic' | 'characters' | 'analysis';

const ZOOM_ORDER: ZoomLevel[] = ['work', 'chapter', 'paragraph', 'sentence'];

interface ViewState {
  activeTab: TabId;
  selectedParagraphIndex: number | null;
  selectedAnnotation: W3CAnnotation | null;
  scrollToParagraphRequest: number | null;
  textHicOpen: boolean;
  helpOpen: boolean;
  zoomLevel: ZoomLevel;
  visibleParagraphRange: [number, number] | null;

  setActiveTab: (tab: TabId) => void;
  setSelectedParagraphIndex: (index: number | null) => void;
  selectAnnotation: (ann: W3CAnnotation | null) => void;
  requestScrollToParagraph: (index: number) => void;
  clearScrollRequest: () => void;
  toggleTextHic: () => void;
  toggleHelp: () => void;
  setZoomLevel: (level: ZoomLevel) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  setVisibleParagraphRange: (range: [number, number]) => void;
}

export const useViewStore = create<ViewState>((set, get) => ({
  activeTab: 'reading',
  selectedParagraphIndex: null,
  selectedAnnotation: null,
  scrollToParagraphRequest: null,
  textHicOpen: false,
  helpOpen: false,
  zoomLevel: 'paragraph',
  visibleParagraphRange: null,

  setActiveTab: (tab): void => {
    set({ activeTab: tab });
    if (tab === 'texthic') set({ textHicOpen: true });
  },
  setSelectedParagraphIndex: (index): void => set({ selectedParagraphIndex: index }),
  selectAnnotation: (ann): void => set({ selectedAnnotation: ann }),
  requestScrollToParagraph: (index): void => set({ scrollToParagraphRequest: index }),
  clearScrollRequest: (): void => set({ scrollToParagraphRequest: null }),
  toggleTextHic: (): void => {
    const next = !get().textHicOpen;
    set({ textHicOpen: next, activeTab: next ? 'texthic' : 'reading' });
  },
  toggleHelp: (): void => set((s) => ({ helpOpen: !s.helpOpen })),
  setZoomLevel: (level): void => set({ zoomLevel: level }),

  zoomIn: (): void => {
    const idx = ZOOM_ORDER.indexOf(get().zoomLevel);
    if (idx < ZOOM_ORDER.length - 1) {
      set({ zoomLevel: ZOOM_ORDER[idx + 1] });
    }
  },

  zoomOut: (): void => {
    const idx = ZOOM_ORDER.indexOf(get().zoomLevel);
    if (idx > 0) {
      set({ zoomLevel: ZOOM_ORDER[idx - 1] });
    }
  },

  setVisibleParagraphRange: (range): void => set({ visibleParagraphRange: range }),
}));
