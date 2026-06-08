/**
 * Text search state store.
 */

import { create } from 'zustand';
import { useViewStore } from './viewStore';

export interface SearchMatch {
  start: number;
  end: number;
  paragraphIndex: number;
}

interface SearchState {
  query: string;
  matches: SearchMatch[];
  currentMatchIndex: number;
  isOpen: boolean;
  caseSensitive: boolean;

  open: () => void;
  close: () => void;
  setQuery: (query: string, referenceText: string, paragraphs: Array<{start: number; end: number}>) => void;
  nextMatch: () => void;
  prevMatch: () => void;
  toggleCaseSensitive: (referenceText?: string, paragraphs?: Array<{ start: number; end: number }>) => void;
}

function findMatches(
  query: string,
  text: string,
  caseSensitive: boolean,
  paragraphs: Array<{start: number; end: number}>,
): SearchMatch[] {
  if (query.length < 2) return [];

  const searchText = caseSensitive ? text : text.toLowerCase();
  const searchQuery = caseSensitive ? query : query.toLowerCase();
  const matches: SearchMatch[] = [];
  let pos = 0;

  while (pos < searchText.length) {
    const idx = searchText.indexOf(searchQuery, pos);
    if (idx === -1) break;

    const paraIdx = paragraphs.findIndex((p) => idx >= p.start && idx < p.end);
    matches.push({
      start: idx,
      end: idx + searchQuery.length,
      paragraphIndex: paraIdx >= 0 ? paraIdx : 0,
    });
    pos = idx + 1;
  }
  return matches;
}

export const useSearchStore = create<SearchState>((set, get) => ({
  query: '',
  matches: [],
  currentMatchIndex: -1,
  isOpen: false,
  caseSensitive: false,

  open: (): void => set({ isOpen: true }),
  close: (): void => set({ isOpen: false, query: '', matches: [], currentMatchIndex: -1 }),

  setQuery: (query, referenceText, paragraphs): void => {
    const { caseSensitive } = get();
    const matches = findMatches(query, referenceText, caseSensitive, paragraphs);
    const idx = matches.length > 0 ? 0 : -1;
    set({ query, matches, currentMatchIndex: idx });
    if (idx >= 0) {
      useViewStore.getState().requestScrollToParagraph(matches[idx].paragraphIndex);
    }
  },

  nextMatch: (): void => {
    const s = get();
    if (s.matches.length === 0) return;
    const idx = (s.currentMatchIndex + 1) % s.matches.length;
    set({ currentMatchIndex: idx });
    useViewStore.getState().requestScrollToParagraph(s.matches[idx].paragraphIndex);
  },

  prevMatch: (): void => {
    const s = get();
    if (s.matches.length === 0) return;
    const idx = (s.currentMatchIndex - 1 + s.matches.length) % s.matches.length;
    set({ currentMatchIndex: idx });
    useViewStore.getState().requestScrollToParagraph(s.matches[idx].paragraphIndex);
  },

  toggleCaseSensitive: (referenceText?: string, paragraphs?: Array<{ start: number; end: number }>): void => {
    const s = get();
    const newCs = !s.caseSensitive;
    if (referenceText && paragraphs && s.query) {
      const matches = findMatches(s.query, referenceText, newCs, paragraphs);
      set({ caseSensitive: newCs, matches, currentMatchIndex: matches.length > 0 ? 0 : -1 });
    } else {
      set({ caseSensitive: newCs });
    }
  },
}));
