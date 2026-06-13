/**
 * Project data store — supports loading multiple projects for comparison.
 * Backward-compatible: top-level selectors (metadata, paragraphs, tracks, referenceText)
 * always reflect the active project.
 */

import { create } from 'zustand';
import type { W3CAnnotation } from '../adapters/AnnotationAdapter';
import { loadTrack } from '../adapters/AnnotationAdapter';
import { loadTrackManifest, type TrackManifest } from '../adapters/TrackManifest';
import { useTrackStore, type TrackState } from './trackStore';
import { TRACK_COLORS } from '../utils/trackColors';

export interface ProjectMetadata {
  id: string;
  title: string;
  author?: string;
  year?: number;
  word_count: number;
  paragraph_count: number;
  section_count: number;
  sentence_count: number;
}

export interface Paragraph {
  index: number;
  start: number;
  end: number;
  text: string;
}

type LoadingState = 'idle' | 'loading' | 'ready' | 'error';

export interface SingleProjectState {
  metadata: ProjectMetadata | null;
  referenceText: string;
  paragraphs: Paragraph[];
  tracks: Record<string, W3CAnnotation[]>;
}

const EMPTY_PROJECT: SingleProjectState = {
  metadata: null,
  referenceText: '',
  paragraphs: [],
  tracks: {},
};

interface ProjectStoreState {
  // Multi-project map
  projects: Record<string, SingleProjectState>;
  activeProjectId: string | null;
  secondaryProjectId: string | null;

  // Loading state (for the most recent load operation)
  loadingState: LoadingState;
  loadingStep: string;
  error: string | null;

  // NOTE: backward-compat getters were removed — ES6 getters break after
  // Zustand's set() merges state via Object.assign (getter evaluated once,
  // value frozen). Use getActiveProject(s) in selectors instead.

  // Actions
  loadProject: (baseUrl: string, projectId: string) => Promise<void>;
  loadSecondaryProject: (baseUrl: string, projectId: string) => Promise<void>;
  setSecondaryProject: (id: string | null) => void;
  closeProject: () => void;
  reloadActiveProject: () => Promise<void>;
}

function splitParagraphs(text: string): Paragraph[] {
  const parts = text.split(/\n\n+/);
  const paragraphs: Paragraph[] = [];
  let offset = 0;
  let index = 0;

  for (const part of parts) {
    const trimmed = part.trim();
    const partStart = text.indexOf(part, offset);
    if (trimmed) {
      paragraphs.push({
        index,
        start: partStart,
        end: partStart + part.length,
        text: trimmed,
      });
      index++;
    }
    offset = partStart + part.length;
  }
  return paragraphs;
}

async function discoverTracks(baseUrl: string, projectId: string): Promise<string[]> {
  try {
    const res = await fetch(`${baseUrl}/api/projects/${projectId}/tracks`);
    if (res.ok) {
      const names: string[] = await res.json();
      if (Array.isArray(names) && names.length > 0) {
        return names;
      }
    }
  } catch {
    // Fall back to known tracks
  }
  return ['segments', 'entities'];
}

async function loadProjectData(baseUrl: string, projectId: string): Promise<SingleProjectState> {
  const dataBase = `${baseUrl}/data/${projectId}`;

  const [metaRes, textRes] = await Promise.all([
    fetch(`${dataBase}/metadata.json`),
    fetch(`${dataBase}/reference.txt`),
  ]);

  if (!metaRes.ok || !textRes.ok) {
    throw new Error('Failed to load project data');
  }

  const metadata: ProjectMetadata = await metaRes.json();
  const referenceText = await textRes.text();
  const paragraphs = splitParagraphs(referenceText);

  const trackNames = await discoverTracks(baseUrl, projectId);
  const tracks: Record<string, W3CAnnotation[]> = {};

  const trackEntries = await Promise.all(
    trackNames.map(async (name) => {
      try {
        const anns = await loadTrack(`${dataBase}/tracks/${name}.jsonl`);
        return [name, anns] as [string, W3CAnnotation[]];
      } catch {
        return null;
      }
    })
  );
  for (const entry of trackEntries) {
    if (entry) tracks[entry[0]] = entry[1];
  }

  return { metadata, referenceText, paragraphs, tracks };
}

async function setupTrackStates(baseUrl: string, projectId: string, tracks: Record<string, W3CAnnotation[]>): Promise<void> {
  const dataBase = `${baseUrl}/data/${projectId}`;
  const trackStates: Record<string, TrackState> = {};
  const manifestPromises: Promise<[string, TrackManifest]>[] = [];
  for (const name of Object.keys(tracks)) {
    manifestPromises.push(
      loadTrackManifest(`${dataBase}/manifests/${name}.manifest.json`)
        .then((m) => [name, m] as [string, TrackManifest])
    );
  }
  const manifests = await Promise.all(manifestPromises);
  for (const [name, manifest] of manifests) {
    const fallbackColor = TRACK_COLORS[name] ?? '#888';
    trackStates[name] = {
      name,
      visible: true,
      manifest: {
        ...manifest,
        colorScheme: manifest.colorScheme.primary !== '#888888'
          ? manifest.colorScheme
          : { primary: fallbackColor, secondary: '#ccc' },
      },
      annotationCount: (tracks[name] ?? []).length,
      confidenceThreshold: 0,
      displayMode: 'inline',
    };
  }
  useTrackStore.getState().setTracks(trackStates);
}

export const useProjectStore = create<ProjectStoreState>()((set, get) => ({
  projects: {},
  activeProjectId: null,
  secondaryProjectId: null,
  loadingState: 'idle',
  loadingStep: '',
  error: null,

  // Backward-compat getters removed — use getActiveProject(s) in selectors

  loadProject: async (baseUrl: string, projectId: string): Promise<void> => {
    // If already loaded, just switch active
    if (get().projects[projectId]?.metadata) {
      set({ activeProjectId: projectId, loadingState: 'ready', error: null });
      // Re-setup track states for the active project
      await setupTrackStates(baseUrl, projectId, get().projects[projectId].tracks);
      return;
    }

    set({ loadingState: 'loading', loadingStep: 'Loading metadata...', error: null });
    try {
      set({ loadingStep: 'Loading tracks...' });
      const projectData = await loadProjectData(baseUrl, projectId);

      set((state) => ({
        projects: { ...state.projects, [projectId]: projectData },
        activeProjectId: projectId,
        loadingState: 'ready',
        loadingStep: '',
      }));

      await setupTrackStates(baseUrl, projectId, projectData.tracks);
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        loadingState: 'error',
        loadingStep: '',
      });
    }
  },

  loadSecondaryProject: async (baseUrl: string, projectId: string): Promise<void> => {
    if (get().projects[projectId]?.metadata) {
      set({ secondaryProjectId: projectId });
      return;
    }

    try {
      const projectData = await loadProjectData(baseUrl, projectId);
      set((state) => ({
        projects: { ...state.projects, [projectId]: projectData },
        secondaryProjectId: projectId,
      }));
    } catch {
      // Don't set global error — secondary load failure should not white-screen the app
    }
  },

  setSecondaryProject: (id: string | null): void => {
    set({ secondaryProjectId: id });
  },

  closeProject: (): void => {
    set({
      activeProjectId: null,
      secondaryProjectId: null,
      loadingState: 'idle',
      loadingStep: '',
      error: null,
    });
  },

  reloadActiveProject: async (): Promise<void> => {
    const projectId = get().activeProjectId;
    if (!projectId) return;

    try {
      const projectData = await loadProjectData('', projectId);
      set((state) => ({
        projects: { ...state.projects, [projectId]: projectData },
      }));
      await setupTrackStates('', projectId, projectData.tracks);
    } catch {
      // Reload is best-effort — don't disrupt current state on failure
    }
  },
}));

/** Get the active project's state. Use in components that only care about one project. */
export function getActiveProject(state: ProjectStoreState): SingleProjectState {
  return state.projects[state.activeProjectId ?? ''] ?? EMPTY_PROJECT;
}

/** Get the secondary project's state (for comparison views). */
export function getSecondaryProject(state: ProjectStoreState): SingleProjectState {
  return state.projects[state.secondaryProjectId ?? ''] ?? EMPTY_PROJECT;
}
