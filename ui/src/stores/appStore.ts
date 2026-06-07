import { create } from 'zustand';
import { invoke } from '@tauri-apps/api/core';

interface AppState {
  workspace: string | null;
  ready: boolean;
  setWorkspace: (path: string) => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
  workspace: null,
  ready: false,
  setWorkspace: async (path) => {
    await invoke('set_workspace', { path });
    set({ workspace: path, ready: true });
  },
}));
