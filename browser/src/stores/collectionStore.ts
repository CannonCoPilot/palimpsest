/**
 * Collection selection store (C7).
 *
 * Hoists the selected collection out of CorpusView's local state so the workbench sub-tabs (Overview /
 * Members / Corpus / Masking) share one selection and it survives a tab-away/return re-mount — the C4
 * known-bug fix. Holds only selection + the fetched list; each panel fetches its own backing data.
 */

import { create } from 'zustand';

export interface CollectionOption {
  id: string;
  label: string;
  project_ids: string[];
  roles?: Record<string, string>;
}

interface CollectionState {
  collections: CollectionOption[];
  collectionId: string;
  setCollections: (collections: CollectionOption[]) => void;
  setCollectionId: (collectionId: string) => void;
}

export const useCollectionStore = create<CollectionState>((set) => ({
  collections: [],
  collectionId: '',
  setCollections: (collections) => set({ collections }),
  setCollectionId: (collectionId) => set({ collectionId }),
}));

/** The currently-selected collection option, or undefined. */
export function activeCollection(s: CollectionState): CollectionOption | undefined {
  return s.collections.find((c) => c.id === s.collectionId);
}
