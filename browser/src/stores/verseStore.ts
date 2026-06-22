/**
 * Verse coordinate index store — lazy source for the Browser's Verses lane and the
 * verse-number mask layer.
 *
 * The backend writes a compact `tracks/verses.jsonl` (one line per verse:
 * `{b,c,v,ns,s,e}`) rather than tens of thousands of W3C element annotations, so it
 * stays a ~2-3MB file we fetch on demand instead of eagerly on project load. It is
 * fetched the first time the Browser viewport zooms in past VERSE_ZOOM_MAX_CHARS — by
 * which point it is needed both to draw the lane and to gray the `C:V.` number tokens
 * in the readable TickerTape.
 */

import { create } from 'zustand';

export interface VerseRecord {
  /** book name */
  b: string;
  /** chapter */
  c: number;
  /** verse */
  v: number;
  /** num_start — start of the masked `C:V.` number token */
  ns: number;
  /** text_start — start of the verse prose (== num token end) */
  s: number;
  /** text_end — end of the verse prose */
  e: number;
}

interface VerseStoreState {
  projectId: string | null;
  records: VerseRecord[];
  /** `[num_start, text_start)` per verse — the verse-number mask layer for computeMaskedIntervals. */
  numIntervals: Array<[number, number]>;
  loading: boolean;
  /** Lazy-load (idempotent per project). No-op while already loaded or in flight. */
  load: (projectId: string) => Promise<void>;
}

export const useVerseStore = create<VerseStoreState>()((set, get) => ({
  projectId: null,
  records: [],
  numIntervals: [],
  loading: false,

  load: async (projectId: string): Promise<void> => {
    const s = get();
    if (s.loading) return;
    if (s.projectId === projectId && s.records.length > 0) return;

    set({ loading: true });
    try {
      const res = await fetch(`/data/${projectId}/tracks/verses.jsonl`);
      if (!res.ok) {
        // No verse index for this project (most works have none) — settle empty.
        set({ projectId, records: [], numIntervals: [], loading: false });
        return;
      }
      const text = await res.text();
      const records: VerseRecord[] = [];
      const numIntervals: Array<[number, number]> = [];
      for (const line of text.split('\n')) {
        if (!line) continue;
        const r = JSON.parse(line) as VerseRecord;
        records.push(r);
        numIntervals.push([r.ns, r.s]);
      }
      set({ projectId, records, numIntervals, loading: false });
    } catch {
      set({ projectId, records: [], numIntervals: [], loading: false });
    }
  },
}));
