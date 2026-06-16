/**
 * Layout-section store for the import pipeline (Steps 2-5). Holds the typed,
 * nestable, maskable sections for one project and talks to the /sections endpoints.
 * Masked intervals are recomputed locally on every edit for instant preview.
 */

import { create } from 'zustand';
import {
  computeMaskedIntervals,
  type ExtraType,
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
  extra_types: ExtraType[];
  masked_style: { color: string; background: string };
}

/** Derive a stable, filesystem-safe key from a custom layer's display name. */
function slugifyTypeKey(label: string): string {
  return label.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40);
}

interface SectionStoreState {
  projectId: string | null;
  textLen: number;
  sections: LayoutSection[];
  maskByType: Record<string, boolean>;
  types: SectionType[];
  extraTypes: ExtraType[];
  applied: boolean;
  maskedStyle: { color: string; background: string };
  busy: boolean;
  selectedId: string | null;

  maskedIntervals: () => Array<[number, number]>;
  load: (projectId: string) => Promise<void>;
  detect: () => Promise<void>;
  save: () => Promise<boolean>;
  apply: () => Promise<boolean>;

  setSelected: (id: string | null) => void;
  setSections: (sections: LayoutSection[]) => void;
  updateSection: (id: string, patch: Partial<LayoutSection>) => void;
  addSection: (type: string, start: number, end: number) => void;
  removeSection: (id: string) => void;
  splitSection: (id: string, at: number) => void;
  setMaskForType: (type: string, masked: boolean) => void;
  addType: (label: string, color: string, masked: boolean) => { ok: true } | { ok: false; error: string };
  removeType: (key: string) => void;
  reset: () => void;
}

function applyPayload(p: SectionsPayload): Partial<SectionStoreState> {
  return {
    sections: p.sections,
    maskByType: p.mask_by_type,
    types: p.types,
    extraTypes: p.extra_types ?? [],
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
  extraTypes: [],
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
      if (!res.ok) { set({ busy: false }); return; }
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
      if (!res.ok) { set({ busy: false }); return; }
      const p: SectionsPayload = await res.json();
      set({ ...applyPayload(p), busy: false });
    } catch {
      set({ busy: false });
    }
  },

  save: async (): Promise<boolean> => {
    const { projectId, sections, maskByType, extraTypes } = get();
    if (!projectId) return false;
    set({ busy: true });
    try {
      const res = await fetch(`/api/projects/${projectId}/sections`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sections, mask_by_type: maskByType, extra_types: extraTypes }),
      });
      if (!res.ok) { set({ busy: false }); return false; }
      const p: SectionsPayload = await res.json();
      set({ ...applyPayload(p), busy: false });
      return true;
    } catch {
      set({ busy: false });
      return false;
    }
  },

  apply: async (): Promise<boolean> => {
    const { projectId } = get();
    if (!projectId) return false;
    // Don't apply on top of un-saved edits — gate on the save succeeding first.
    if (!(await get().save())) return false;
    set({ busy: true });
    try {
      const res = await fetch(`/api/projects/${projectId}/sections/apply`, { method: 'POST' });
      if (!res.ok) { set({ busy: false }); return false; }
      set({ busy: false, applied: true });
      return true;
    } catch {
      set({ busy: false });
      return false;
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

  // Split a section at offset `at` into two same-typed sections (#28).
  splitSection: (id, at) =>
    set((s) => {
      const sec = s.sections.find((x) => x.id === id);
      if (!sec || at <= sec.start || at >= sec.end) return s;
      const right: LayoutSection = { ...sec, id: freshId(), start: at, source: 'user', label: '' };
      return {
        sections: s.sections
          .map((x) => (x.id === id ? { ...x, end: at } : x))
          .concat(right)
          .sort((a, b) => a.start - b.start),
        selectedId: right.id,
      };
    }),

  setMaskForType: (type, masked) =>
    set((s) => ({ maskByType: { ...s.maskByType, [type]: masked } })),

  // #22 — add a custom mask layer. Guards against blank/duplicate names against
  // both builtin and existing custom types (the backend also re-checks on save).
  addType: (label, color, masked) => {
    const name = label.trim();
    if (!name) return { ok: false, error: 'Name is required' };
    const key = slugifyTypeKey(name);
    if (!key) return { ok: false, error: 'Name must contain a letter or number' };
    const { types, extraTypes } = get();
    const clash =
      types.some((t) => t.key === key || t.label.toLowerCase() === name.toLowerCase()) ||
      extraTypes.some((t) => t.key === key);
    if (clash) return { ok: false, error: `“${name}” already exists` };
    const extra: ExtraType = { key, label: name, color, default_mask: masked };
    set((s) => ({
      extraTypes: [...s.extraTypes, extra],
      types: [...s.types, { ...extra, builtin: false }],
      maskByType: { ...s.maskByType, [key]: masked },
    }));
    return { ok: true };
  },

  // Remove a custom layer (builtin types are immutable). Drops any sections of it.
  removeType: (key) =>
    set((s) => {
      if (!s.extraTypes.some((t) => t.key === key)) return s;
      const maskByType = { ...s.maskByType };
      delete maskByType[key];
      return {
        extraTypes: s.extraTypes.filter((t) => t.key !== key),
        types: s.types.filter((t) => t.key !== key),
        sections: s.sections.filter((sec) => sec.type !== key),
        maskByType,
      };
    }),

  reset: () =>
    set({
      projectId: null, textLen: 0, sections: [], maskByType: {}, types: [], extraTypes: [],
      applied: false, busy: false, selectedId: null,
    }),
}));
