/**
 * Project display-label store.
 *
 * Collection members are carried as opaque id slugs (e.g. "douay-rheims-…-chapter-in-book-0047"),
 * which render indistinguishably across the corpus workbench. This holds the id→{title, author} map
 * from /api/projects so every panel can show a human label. Loaded once (idempotent) and shared, the
 * same way collectionStore hoists the selected collection.
 */

import { useCallback } from 'react';
import { create } from 'zustand';

export interface ProjectLabel {
  title: string;
  author: string;
}

interface ProjectLabelState {
  labels: Record<string, ProjectLabel>;
  loaded: boolean;
  setLabels: (labels: Record<string, ProjectLabel>) => void;
  ensureLoaded: () => void;
}

export const useProjectLabelStore = create<ProjectLabelState>((set, get) => ({
  labels: {},
  loaded: false,
  setLabels: (labels) => set({ labels, loaded: true }),
  ensureLoaded: () => {
    if (get().loaded) return;
    set({ loaded: true }); // guard against duplicate concurrent fetches; labels fill in when it resolves
    fetch('/api/projects')
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Array<{ id: string; title?: string; author?: string }>) => {
        const labels: Record<string, ProjectLabel> = {};
        for (const p of data) labels[p.id] = { title: p.title || p.id, author: p.author || '' };
        set({ labels });
      })
      .catch(() => {
        /* leave labels empty → memberLabel() falls back to the shortened slug */
      });
  },
}));

/** A shortened slug for when no title is known (keeps head + tail so it is at least anchorable). */
export function shortSlug(id: string): string {
  return id.length <= 24 ? id : `${id.slice(0, 12)}…${id.slice(-8)}`;
}

/** Human label for a member id: its project title, else a shortened slug fallback. */
export function memberLabel(labels: Record<string, ProjectLabel>, id: string): string {
  return labels[id]?.title || shortSlug(id);
}

/**
 * Subscribe to the label map and get a stable id→label resolver for render sites. Side-effect-free:
 * the caller triggers the one-time fetch via `ensureLoaded()` (so panels rendered in isolation, e.g.
 * under test, simply fall back to the slug rather than firing a network call on mount).
 */
export function useMemberLabel(): (id: string) => string {
  const labels = useProjectLabelStore((s) => s.labels);
  return useCallback((id: string) => memberLabel(labels, id), [labels]);
}
