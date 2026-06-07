import { create } from 'zustand';
import { invoke } from '@tauri-apps/api/core';

export interface TrackInfo {
  name: string;
  annotation_count: number;
  track_id: number;
}

export interface ProjectInfo {
  id: string;
  title: string;
  author: string | null;
  year: number | null;
  word_count: number;
  paragraph_count: number;
  sentence_count: number;
  character_count: number;
  total_annotations: number;
  tracks: TrackInfo[];
}

export interface ViewportAnnotation {
  index: number;
  start: number;
  end: number;
  confidence: number;
  track_id: number;
  evidence_level: number;
}

interface ProjectState {
  loaded: boolean;
  loading: boolean;
  info: ProjectInfo | null;
  referenceText: string;
  paragraphs: { start: number; end: number; text: string }[];
  error: string | null;

  loadProject: (id: string) => Promise<void>;
  queryViewport: (start: number, end: number) => Promise<ViewportAnnotation[]>;
}

function splitParagraphs(text: string): { start: number; end: number; text: string }[] {
  const parts = text.split(/\n\n+/);
  const result: { start: number; end: number; text: string }[] = [];
  let offset = 0;

  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) {
      offset += part.length + 2;
      continue;
    }
    const idx = text.indexOf(part, offset);
    result.push({ start: idx, end: idx + part.length, text: trimmed });
    offset = idx + part.length;
  }
  return result;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  loaded: false,
  loading: false,
  info: null,
  referenceText: '',
  paragraphs: [],
  error: null,

  loadProject: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const info = await invoke<ProjectInfo>('load_project', { projectId: id });
      const text = await invoke<string>('get_reference_text', { projectId: id });

      const paragraphs = text ? splitParagraphs(text) : [];
      set({ loaded: true, loading: false, info, referenceText: text, paragraphs });
    } catch (e) {
      set({ loading: false, error: String(e) });
    }
  },

  queryViewport: async (start: number, end: number) => {
    const info = get().info;
    if (!info) return [];
    return invoke<ViewportAnnotation[]>('query_viewport', {
      projectId: info.id,
      start,
      end,
    });
  },
}));
