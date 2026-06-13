/**
 * Comparison store — alignment results, cross-similarity matrix, and comparison UI state.
 * Used by Compare tab views (AlignmentView, ComparativeDotplot, SyntenyView, CircosView, DiffView).
 */

import { create } from 'zustand';

export interface AlignmentRecord {
  queryId: string;
  queryStart: number;
  queryEnd: number;
  targetId: string;
  targetStart: number;
  targetEnd: number;
  score: number;
  pValue: number;
  method: string;
  strand: '+' | '-';
  identity: number;
}

export interface DiffRecord {
  paraIndexA: number;
  paraIndexB: number;
  changeType: 'insert' | 'delete' | 'replace' | 'equal';
  textA: string;
  textB: string;
}

export interface DiffSummary {
  totalParagraphsA: number;
  totalParagraphsB: number;
  alignedPairs: number;
  insertions: number;
  deletions: number;
  replacements: number;
  unchanged: number;
}

export type AlignmentMethod = 'semantic' | 'alphabet' | 'word';
export type CompareSubView = 'alignment' | 'dotplot' | 'synteny' | 'circos' | 'diff';

interface ComparisonState {
  // Alignment results
  alignmentRecords: AlignmentRecord[];
  crossSimilarityMatrix: Float32Array | null;
  crossSimilarityDims: [number, number] | null;

  // Edition diff results
  diffRecords: DiffRecord[];
  diffSummary: DiffSummary | null;

  // UI state
  activeSubView: CompareSubView;
  activeMethod: AlignmentMethod;
  selectedRecord: AlignmentRecord | null;
  loading: boolean;
  error: string | null;
  diffError: string | null;
  jobStatus: 'idle' | 'running' | 'completed' | 'failed';
  pollIntervalId: ReturnType<typeof setInterval> | null;

  // Actions
  setActiveSubView: (view: CompareSubView) => void;
  setActiveMethod: (method: AlignmentMethod) => void;
  selectRecord: (record: AlignmentRecord | null) => void;
  runAlignment: (queryId: string, targetId: string, method: AlignmentMethod) => Promise<void>;
  runDiff: (queryId: string, targetId: string) => Promise<void>;
  loadAlignmentResults: (queryId: string, targetId: string) => Promise<void>;
  loadCrossMatrix: (queryId: string, targetId: string) => Promise<void>;
  reset: () => void;
}

export const useComparisonStore = create<ComparisonState>((set, get) => ({
  alignmentRecords: [],
  crossSimilarityMatrix: null,
  crossSimilarityDims: null,
  diffRecords: [],
  diffSummary: null,
  activeSubView: 'alignment',
  activeMethod: 'semantic',
  selectedRecord: null,
  loading: false,
  error: null,
  diffError: null,
  jobStatus: 'idle',
  pollIntervalId: null,

  setActiveSubView: (view) => set({ activeSubView: view }),
  setActiveMethod: (method) => set({ activeMethod: method }),
  selectRecord: (record) => set({ selectedRecord: record }),

  runAlignment: async (queryId, targetId, method) => {
    // Clear any existing poll
    const existing = get().pollIntervalId;
    if (existing) clearInterval(existing);

    set({ loading: true, error: null, jobStatus: 'running', pollIntervalId: null });
    try {
      const res = await fetch('/api/alignment/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_id: queryId, target_id: targetId, method }),
      });
      if (!res.ok) throw new Error('Failed to start alignment');

      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/alignment/${queryId}/${targetId}/status`);
          const status = await statusRes.json();
          if (status.status === 'completed') {
            clearInterval(pollInterval);
            await get().loadAlignmentResults(queryId, targetId);
            set({ jobStatus: 'completed', loading: false, pollIntervalId: null });
          } else if (status.status === 'failed') {
            clearInterval(pollInterval);
            set({ error: status.error ?? 'Alignment failed', jobStatus: 'failed', loading: false, pollIntervalId: null });
          }
        } catch {
          clearInterval(pollInterval);
          set({ error: 'Lost connection to server', jobStatus: 'failed', loading: false, pollIntervalId: null });
        }
      }, 2000);
      set({ pollIntervalId: pollInterval });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Unknown error', jobStatus: 'failed', loading: false });
    }
  },

  runDiff: async (queryId, targetId) => {
    set({ loading: true, diffError: null });
    try {
      const res = await fetch('/api/alignment/diff', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query_id: queryId, target_id: targetId }),
      });
      if (!res.ok) throw new Error('Failed to compute diff');
      const data = await res.json();
      set({
        diffRecords: data.records ?? [],
        diffSummary: data.summary ?? null,
        loading: false,
      });
    } catch (err) {
      set({ diffError: err instanceof Error ? err.message : 'Unknown error', loading: false });
    }
  },

  loadAlignmentResults: async (queryId, targetId) => {
    try {
      const res = await fetch(`/api/alignment/${queryId}/${targetId}/records`);
      if (!res.ok) throw new Error('No alignment results found');
      const records: AlignmentRecord[] = await res.json();
      set({ alignmentRecords: records });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Unknown error' });
    }
  },

  loadCrossMatrix: async (queryId, targetId) => {
    try {
      const manifestRes = await fetch(`/api/alignment/${queryId}/${targetId}/matrix`);
      if (!manifestRes.ok) return;
      const manifest = await manifestRes.json();
      const binRes = await fetch(`/api/alignment/${queryId}/${targetId}/matrix.bin`);
      if (!binRes.ok) return;
      const buffer = await binRes.arrayBuffer();
      const matrix = new Float32Array(buffer);
      set({
        crossSimilarityMatrix: matrix,
        crossSimilarityDims: manifest.dimensions as [number, number],
      });
    } catch { /* matrix is optional — views degrade gracefully */ }
  },

  reset: () => {
    const interval = get().pollIntervalId;
    if (interval) clearInterval(interval);
    set({
      alignmentRecords: [],
      crossSimilarityMatrix: null,
      crossSimilarityDims: null,
      diffRecords: [],
      diffSummary: null,
      selectedRecord: null,
      loading: false,
      error: null,
      diffError: null,
      jobStatus: 'idle',
      pollIntervalId: null,
    });
  },
}));
