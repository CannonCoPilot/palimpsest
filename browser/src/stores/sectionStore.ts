/**
 * Layout-section store for the import pipeline (Steps 2-5). Holds the typed,
 * nestable, maskable sections for one project and talks to the /sections endpoints.
 * Masked intervals are recomputed locally on every edit for instant preview.
 */

import { create } from 'zustand';
import {
  computeMaskedIntervals,
  type LayoutSection,
  type SectionType,
} from '../utils/sectionMasking';

interface SectionsPayload {
  sections: LayoutSection[];
  mask_by_type: Record<string, boolean>;
  applied: boolean;
  text_len: number;
  masked_intervals: Array<[number, number]>;
  types: SectionType[];
  masked_style: { color: string; background: string };
}

interface SectionStoreState {
  projectId: string | null;
  textLen: number;
  sections: LayoutSection[];
  maskByType: Record<string, boolean>;
  types: SectionType[];
  applied: boolean;
  maskedStyle: { color: string; background: string };
  busy: boolean;
  selectedId: string | null;

  maskedIntervals: () => Array<[number, number]>;
  load: (projectId: string) => Promise<void>;
  detect: () => Promise<void>;
  save: () => Promise<void>;
  apply: () => Promise<void>;

  setSelected: (id: string | null) => void;
  setSections: (sections: LayoutSection[]) => void;
  updateSection: (id: string, patch: Partial<LayoutSection>) => void;
  addSection: (type: string, start: number, end: number) => void;
  removeSection: (id: string) => void;
  setMaskForType: (type: string, masked: boolean) => void;
  reset: () => void;
}

function applyPayload(p: SectionsPayload): Partial<SectionStoreState> {
  return {
    sections: p.sections,
    maskByType: p.mask_by_type,
    types: p.types,
    applied: p.applied,
    textLen: p.text_len,
    maskedStyle: p.masked_style,
  };
}

let idCounter = 0;
function freshId(): string {
  idCounter += 1;
  return `ls-user-${idCounter}-${idCounter * 2654435761 % 100000}`;
}

export const useSectionStore = create<SectionStoreState>()((set, get) => ({
  projectId: null,
  textLen: 0,
  sections: [],
  maskByType: {},
  types: [],
  applied: false,
  maskedStyle: { color: '#f5f5f5', background: '#3a3a3d' },
  busy: false,
  selectedId: null,

  maskedIntervals: () => {
    const { sections, maskByType, textLen } = get();
    return computeMaskedIntervals(sections, maskByType, textLen);
  },

  load: async (projectId: string): Promise<void> => {
    set({ busy: true, projectId });
    try {
      const res = await fetch(`/api/projects/${projectId}/sections`);
      const p: SectionsPayload = await res.json();
      set({ ...applyPayload(p), busy: false });
    } catch {
      set({ busy: false });
    }
  },

  detect: async (): Promise<void> => {
    const projectId = get().projectId;
    if (!projectId) return;
    set({ busy: true });
    try {
      const res = await fetch(`/api/projects/${projectId}/sections/detect`, { method: 'POST' });
      const p: SectionsPayload = await res.json();
      set({ ...applyPayload(p), busy: false });
    } catch {
      set({ busy: false });
    }
  },

  save: async (): Promise<void> => {
    const { projectId, sections, maskByType } = get();
    if (!projectId) return;
    set({ busy: true });
    try {
      const res = await fetch(`/api/projects/${projectId}/sections`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sections, mask_by_type: maskByType }),
      });
      const p: SectionsPayload = await res.json();
      set({ ...applyPayload(p), busy: false });
    } catch {
      set({ busy: false });
    }
  },

  apply: async (): Promise<void> => {
    const { projectId } = get();
    if (!projectId) return;
    await get().save();
    set({ busy: true });
    try {
      await fetch(`/api/projects/${projectId}/sections/apply`, { method: 'POST' });
      set({ busy: false, applied: true });
    } catch {
      set({ busy: false });
    }
  },

  setSelected: (id) => set({ selectedId: id }),
  setSections: (sections) => set({ sections }),

  updateSection: (id, patch) =>
    set((s) => ({ sections: s.sections.map((sec) => (sec.id === id ? { ...sec, ...patch } : sec)) })),

  addSection: (type, start, end) =>
    set((s) => {
      const lo = Math.max(0, Math.min(start, end));
      const hi = Math.min(s.textLen, Math.max(start, end));
      if (hi <= lo) return s;
      const sec: LayoutSection = {
        id: freshId(), type, start: lo, end: hi,
        label: '', parent_id: null, source: 'user', masked: null,
      };
      return { sections: [...s.sections, sec].sort((a, b) => a.start - b.start), selectedId: sec.id };
    }),

  removeSection: (id) =>
    set((s) => ({
      sections: s.sections.filter((sec) => sec.id !== id),
      selectedId: s.selectedId === id ? null : s.selectedId,
    })),

  setMaskForType: (type, masked) =>
    set((s) => ({ maskByType: { ...s.maskByType, [type]: masked } })),

  reset: () =>
    set({
      projectId: null, textLen: 0, sections: [], maskByType: {}, types: [],
      applied: false, busy: false, selectedId: null,
    }),
}));
