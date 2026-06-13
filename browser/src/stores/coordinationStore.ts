/**
 * Coordination store — cross-view selection propagation.
 * When a region is selected in any compare sub-view, all other views
 * highlight the corresponding region (JBrowse 2 pattern).
 */

import { create } from 'zustand';

export interface SelectedRegion {
  projectId: string;
  paragraphStart: number;
  paragraphEnd: number;
  source: string;  // which view triggered the selection
}

interface CoordinationState {
  selectedRegion: SelectedRegion | null;
  linkedViews: boolean;

  selectRegion: (region: SelectedRegion | null) => void;
  toggleLinkedViews: () => void;
}

export const useCoordinationStore = create<CoordinationState>((set) => ({
  selectedRegion: null,
  linkedViews: true,

  selectRegion: (region) => set({ selectedRegion: region }),
  toggleLinkedViews: () => set((s) => ({ linkedViews: !s.linkedViews })),
}));
