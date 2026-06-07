/**
 * View state store — viewport, zoom, selection, scroll requests.
 */

import { create } from 'zustand';
import type { W3CAnnotation } from '../adapters/AnnotationAdapter';

interface ViewState {
  selectedParagraphIndex: number | null;
  selectedAnnotation: W3CAnnotation | null;
  scrollToParagraphRequest: number | null;
  dotplotOpen: boolean;
  helpOpen: boolean;
  zoomLevel: 'close' | 'medium' | 'far';
  zoomManualOverride: boolean;

  setSelectedParagraphIndex: (index: number | null) => void;
  selectAnnotation: (ann: W3CAnnotation | null) => void;
  requestScrollToParagraph: (index: number) => void;
  clearScrollRequest: () => void;
  toggleDotplot: () => void;
  toggleHelp: () => void;
  setZoomLevel: (level: 'close' | 'medium' | 'far') => void;
  setZoomManualOverride: (v: boolean) => void;
}

export const useViewStore = create<ViewState>((set) => ({
  selectedParagraphIndex: null,
  selectedAnnotation: null,
  scrollToParagraphRequest: null,
  dotplotOpen: false,
  helpOpen: false,
  zoomLevel: 'close',
  zoomManualOverride: false,

  setSelectedParagraphIndex: (index): void => set({ selectedParagraphIndex: index }),
  selectAnnotation: (ann): void => set({ selectedAnnotation: ann }),
  requestScrollToParagraph: (index): void => set({ scrollToParagraphRequest: index }),
  clearScrollRequest: (): void => set({ scrollToParagraphRequest: null }),
  toggleDotplot: (): void => set((s) => ({ dotplotOpen: !s.dotplotOpen })),
  toggleHelp: (): void => set((s) => ({ helpOpen: !s.helpOpen })),
  setZoomLevel: (level): void => set({ zoomLevel: level }),
  setZoomManualOverride: (v): void => set({ zoomManualOverride: v }),
}));
