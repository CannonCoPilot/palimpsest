/**
 * Project data store — loaded project metadata, reference text, and annotations.
 * Discovers available tracks from the API rather than using a hardcoded list.
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

interface ProjectState {
  projectId: string | null;
  metadata: ProjectMetadata | null;
  referenceText: string;
  paragraphs: Paragraph[];
  tracks: Record<string, W3CAnnotation[]>;
  loadingState: LoadingState;
  loadingStep: string;
  error: string | null;
  loadProject: (baseUrl: string, projectId: string) => Promise<void>;
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

export const useProjectStore = create<ProjectState>((set) => ({
  projectId: null,
  metadata: null,
  referenceText: '',
  paragraphs: [],
  tracks: {},
  loadingState: 'idle',
  loadingStep: '',
  error: null,

  loadProject: async (baseUrl: string, projectId: string): Promise<void> => {
    set({ loadingState: 'loading', loadingStep: 'Loading metadata...', error: null });
    try {
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

      set({ loadingStep: 'Loading tracks...' });

      const trackNames = await discoverTracks(baseUrl, projectId);
      const tracks: Record<string, W3CAnnotation[]> = {};

      for (const name of trackNames) {
        try {
          tracks[name] = await loadTrack(`${dataBase}/tracks/${name}.jsonl`);
        } catch {
          // Track may not exist yet — skip silently
        }
      }

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
        };
      }
      useTrackStore.getState().setTracks(trackStates);

      set({
        projectId,
        metadata,
        referenceText,
        paragraphs,
        tracks,
        loadingState: 'ready',
        loadingStep: '',
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        loadingState: 'error',
        loadingStep: '',
      });
    }
  },
}));
