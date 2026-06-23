/**
 * Non-destructive masking overlay (on-demand masking). A live, session-only selection
 * layered ON TOP of the project's persisted layout (sectionStore) — it never writes
 * layout_sections.json. It drives three things: the gray-out in the Reader/Browser, the
 * mask set sent to analysis runs, and the kept-span selection a subtext is derived from.
 *
 * State is stored as SPARSE deltas over the persisted layout:
 *   - `typeOverrides[type]`     overrides the persisted mask_by_type for that type-layer
 *   - `sectionOverrides[id]`    forces an individual element masked/unmasked (Stage 2)
 *   - `extractionTypes`         the type-layer(s) whose element spans define a subtext
 * When `enabled` is false the overlay contributes no masking (nothing grayed/excluded).
 */

import { create } from 'zustand';
import type { LayoutSection } from '../utils/sectionMasking';

interface MaskOverlayState {
  projectId: string | null;
  enabled: boolean;
  typeOverrides: Record<string, boolean>; // type -> masked (overrides persisted mask_by_type)
  sectionOverrides: Record<string, boolean>; // sectionId -> masked (per-element, Stage 2)
  extractionTypes: string[]; // type-layers whose spans form a derived subtext

  setProject: (projectId: string | null) => void;
  setEnabled: (enabled: boolean) => void;
  toggleEnabled: () => void;
  setTypeMask: (type: string, masked: boolean) => void;
  clearTypeMask: (type: string) => void;
  setSectionMask: (id: string, masked: boolean) => void;
  clearSectionMask: (id: string) => void;
  setExtraction: (type: string, on: boolean) => void;
  clearOverrides: () => void;
}

/** Effective mask_by_type = persisted base with the overlay's sparse type deltas applied. */
export function effectiveMaskByType(
  base: Record<string, boolean>,
  typeOverrides: Record<string, boolean>,
): Record<string, boolean> {
  return Object.keys(typeOverrides).length === 0 ? base : { ...base, ...typeOverrides };
}

/** Effective sections = base sections with the overlay's per-element `masked` overrides applied. */
export function effectiveSections(
  base: LayoutSection[],
  sectionOverrides: Record<string, boolean>,
): LayoutSection[] {
  if (Object.keys(sectionOverrides).length === 0) return base;
  return base.map((s) =>
    Object.prototype.hasOwnProperty.call(sectionOverrides, s.id) ? { ...s, masked: sectionOverrides[s.id] } : s,
  );
}

export const useMaskOverlayStore = create<MaskOverlayState>()((set) => ({
  projectId: null,
  // On by default so the saved layout's masking shows as before (with no overrides the
  // overlay is identical to the persisted state); turning it off reveals everything.
  enabled: true,
  typeOverrides: {},
  sectionOverrides: {},
  extractionTypes: [],

  // Switching projects clears the overlay (it is tied to one project's layout).
  setProject: (projectId) =>
    set((s) =>
      s.projectId === projectId
        ? s
        : { projectId, enabled: true, typeOverrides: {}, sectionOverrides: {}, extractionTypes: [] },
    ),

  setEnabled: (enabled) => set({ enabled }),
  toggleEnabled: () => set((s) => ({ enabled: !s.enabled })),

  setTypeMask: (type, masked) => set((s) => ({ typeOverrides: { ...s.typeOverrides, [type]: masked } })),
  clearTypeMask: (type) =>
    set((s) => {
      if (!(type in s.typeOverrides)) return s;
      const next = { ...s.typeOverrides };
      delete next[type];
      return { typeOverrides: next };
    }),

  setSectionMask: (id, masked) => set((s) => ({ sectionOverrides: { ...s.sectionOverrides, [id]: masked } })),
  clearSectionMask: (id) =>
    set((s) => {
      if (!(id in s.sectionOverrides)) return s;
      const next = { ...s.sectionOverrides };
      delete next[id];
      return { sectionOverrides: next };
    }),

  setExtraction: (type, on) =>
    set((s) => ({
      extractionTypes: on
        ? s.extractionTypes.includes(type)
          ? s.extractionTypes
          : [...s.extractionTypes, type]
        : s.extractionTypes.filter((t) => t !== type),
    })),

  clearOverrides: () => set({ typeOverrides: {}, sectionOverrides: {}, extractionTypes: [] }),
}));
