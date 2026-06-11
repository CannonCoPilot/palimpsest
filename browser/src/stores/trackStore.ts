/**
 * Track visibility and rendering state store.
 */

import { create } from 'zustand';
import type { TrackManifest } from '../adapters/TrackManifest';

export type DisplayMode = 'dense' | 'pack' | 'inline';

export interface TrackState {
  name: string;
  visible: boolean;
  manifest: TrackManifest;
  annotationCount: number;
  confidenceThreshold: number;
  displayMode: DisplayMode;
}

interface TrackStoreState {
  tracks: Record<string, TrackState>;
  trackOrder: string[];
  setTracks: (tracks: Record<string, TrackState>) => void;
  setTrackOrder: (order: string[]) => void;
  toggleTrack: (name: string) => void;
  toggleTrackByIndex: (index: number) => void;
  setConfidenceThreshold: (name: string, threshold: number) => void;
  setDisplayMode: (name: string, mode: DisplayMode) => void;
}

export const useTrackStore = create<TrackStoreState>((set) => ({
  tracks: {},
  trackOrder: [],

  setTracks: (tracks): void => set((state) => ({
    tracks,
    trackOrder: state.trackOrder.length > 0
      ? state.trackOrder.filter((n) => n in tracks)
      : Object.keys(tracks).filter((n) => n !== 'segments').sort(),
  })),

  setTrackOrder: (order): void => set({ trackOrder: order }),

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

  setDisplayMode: (name, mode): void =>
    set((state) => {
      const track = state.tracks[name];
      if (!track) return state;
      return {
        tracks: {
          ...state.tracks,
          [name]: { ...track, displayMode: mode },
        },
      };
    }),
}));
