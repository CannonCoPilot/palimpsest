/**
 * sweep.ts — pure types + transforms for the recall-dial sweep panel (C7, FR-35).
 *
 * The sweep prunes a collection's O(N×M) chunk-pair space at a chosen recall mode and journals each run.
 * These helpers keep the honesty the backend enforces: an empirical `estimated_recall` of `null` (the
 * oracle could not be sampled) is rendered as "n/a", never a fabricated percentage — the SweepPanel must
 * not turn an unmeasured estimate into a confident-looking number.
 */

export interface PairSummary {
  a: string;
  b: string;
  n_pairs_total: number;
  n_candidates: number;
  n_pruned: number;
  prune_fraction: number;
  estimated_recall: number | null;
  dense: boolean;
}

export interface SweepResult {
  run_id: string;
  collection_id: string;
  metric: string;
  mode: string;
  force_exhaustive: boolean;
  members: string[];
  n_member_pairs: number;
  n_pairs_total: number;
  n_candidates: number;
  n_pruned: number;
  prune_fraction: number;
  mean_estimated_recall: number | null;
  pairs: PairSummary[];
}

export interface RunProgress {
  pairs_total: number;
  pairs_done: number;
}

export type RunHeadline = Omit<SweepResult, 'pairs'> & { progress: RunProgress };

export interface SweepJournalPair extends PairSummary {
  plan?: { dense: boolean; mode?: string } & Record<string, unknown>;
  candidates?: number[][] | null;
  done?: boolean;
}

export interface SweepJournal {
  run_id: string;
  metric: string;
  mode: string;
  force_exhaustive: boolean;
  members: string[];
  pairs: Record<string, SweepJournalPair>;
  progress?: RunProgress;
}

export const SWEEP_MODES = ['exhaustive', 'high-recall', 'fast'] as const;
export type SweepMode = (typeof SWEEP_MODES)[number];

/** Member pairs a sweep will visit = C(n, 2). The honest pre-run estimate — nothing runs until asked. */
export function memberPairCount(n: number): number {
  return n < 2 ? 0 : (n * (n - 1)) / 2;
}

/**
 * Recall is an EMPIRICAL estimate; the backend returns `null` when it could not sample an oracle for a
 * pair. Render that as "n/a" — never invent a number for a null.
 */
export function formatRecall(r: number | null | undefined): string {
  return r === null || r === undefined ? 'n/a' : `${Math.round(r * 100)}%`;
}

/** Fraction → percent string, `—` for a missing value. `digits` lets a near-100% prune keep its tail. */
export function formatPct(f: number | null | undefined, digits = 1): string {
  return f === null || f === undefined ? '—' : `${(f * 100).toFixed(digits)}%`;
}

/** Journal pair-dict → array (keys are opaque `a\x00b` joins, not for display). */
export function journalPairs(journal: SweepJournal): SweepJournalPair[] {
  return Object.values(journal.pairs ?? {});
}
