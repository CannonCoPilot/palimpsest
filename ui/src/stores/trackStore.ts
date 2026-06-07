import { create } from 'zustand';
import { invoke } from '@tauri-apps/api/core';
import { useProjectStore } from './projectStore';

const TRACK_COLORS: Record<string, string> = {
  entities: '#3498db',
  sentiment: '#2ecc71',
  lexical: '#9b59b6',
  dialogue: '#e67e22',
  topics: '#e74c3c',
  segments: '#95a5a6',
};

export interface TrackState {
  visible: boolean;
  color: string;
  trackId: number;
}

interface TrackStoreState {
  tracks: Record<string, TrackState>;
  confidenceThreshold: number;
  initTracks: (trackInfos: { name: string; track_id: number }[]) => void;
  toggleTrack: (name: string) => void;
  setConfidenceThreshold: (v: number) => void;
  getTrackMask: () => number;
}

export const useTrackStore = create<TrackStoreState>((set, get) => ({
  tracks: {},
  confidenceThreshold: 0,

  initTracks: (trackInfos) => {
    const tracks: Record<string, TrackState> = {};
    for (const t of trackInfos) {
      if (t.name === 'segments') continue;
      tracks[t.name] = {
        visible: true,
        color: TRACK_COLORS[t.name] ?? '#888',
        trackId: t.track_id,
      };
    }
    set({ tracks });
  },

  toggleTrack: (name) => {
    const tracks = { ...get().tracks };
    if (tracks[name]) {
      tracks[name] = { ...tracks[name], visible: !tracks[name].visible };
      set({ tracks });
      syncFilter(get);
    }
  },

  setConfidenceThreshold: (v) => {
    set({ confidenceThreshold: v });
    syncFilter(get);
  },

  getTrackMask: () => {
    let mask = 0xFFFFFFFFFFFFFFFF;
    for (const [_, state] of Object.entries(get().tracks)) {
      if (!state.visible) {
        mask &= ~(1 << state.trackId);
      }
    }
    return mask;
  },
}));

function syncFilter(get: () => TrackStoreState) {
  const state = get();
  const info = useProjectStore.getState().info;
  if (!info) return;

  const mask = state.getTrackMask();
  invoke('update_filter', {
    projectId: info.id,
    trackMask: mask,
    minConfidence: state.confidenceThreshold,
  }).catch(() => {});
}
