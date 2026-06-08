/**
 * Track visibility and rendering state store.
 */

import { create } from 'zustand';
import type { TrackManifest } from '../adapters/TrackManifest';

export interface TrackState {
  name: string;
  visible: boolean;
  manifest: TrackManifest;
  annotationCount: number;
  confidenceThreshold: number;
}

interface TrackStoreState {
  tracks: Record<string, TrackState>;
  setTracks: (tracks: Record<string, TrackState>) => void;
  toggleTrack: (name: string) => void;
  toggleTrackByIndex: (index: number) => void;
  setConfidenceThreshold: (name: string, threshold: number) => void;
}

export const useTrackStore = create<TrackStoreState>((set) => ({
  tracks: {},

  setTracks: (tracks): void => set({ tracks }),

  toggleTrack: (name): void =>
    set((state) => {
      const track = state.tracks[name];
      if (!track) return state;
      return {
        tracks: {
          ...state.tracks,
          [name]: { ...track, visible: !track.visible },
        },
      };
    }),

  toggleTrackByIndex: (index): void =>
    set((state) => {
      const names = Object.keys(state.tracks).filter((n) => n !== 'segments').sort();
      const name = names[index - 1];
      if (!name) return state;
      const track = state.tracks[name];
      return {
        tracks: {
          ...state.tracks,
          [name]: { ...track, visible: !track.visible },
        },
      };
    }),

  setConfidenceThreshold: (name, threshold): void =>
    set((state) => {
      const track = state.tracks[name];
      if (!track) return state;
      return {
        tracks: {
          ...state.tracks,
          [name]: { ...track, confidenceThreshold: threshold },
        },
      };
    }),
}));
