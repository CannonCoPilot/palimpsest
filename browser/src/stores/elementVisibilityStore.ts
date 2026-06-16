/**
 * Per-element-type visibility for the unified "elements" track (#27). The track
 * is one annotation layer carrying many subtypes (chapter, header, front_matter…);
 * this store lets the Reader show/hide each subtype independently of the whole track.
 */

import { create } from 'zustand';

interface ElementVisibilityState {
  hidden: Record<string, boolean>; // elementType -> hidden
  toggle: (elementType: string) => void;
  setHidden: (elementType: string, hidden: boolean) => void;
  showAll: () => void;
  hideAll: (elementTypes: string[]) => void;
}

export const useElementVisibilityStore = create<ElementVisibilityState>()((set) => ({
  hidden: {},
  toggle: (elementType) =>
    set((s) => ({ hidden: { ...s.hidden, [elementType]: !s.hidden[elementType] } })),
  setHidden: (elementType, hidden) =>
    set((s) => ({ hidden: { ...s.hidden, [elementType]: hidden } })),
  showAll: () => set({ hidden: {} }),
  hideAll: (elementTypes) =>
    set({ hidden: Object.fromEntries(elementTypes.map((t) => [t, true])) }),
}));
