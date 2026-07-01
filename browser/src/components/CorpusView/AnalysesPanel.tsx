/**
 * AnalysesPanel — the corpus-level analyses tab (C7c, FR-31 / C6a).
 *
 * Read-only surface over `GET /api/collections/{id}/corpus-analyses`: cross-member boilerplate and the
 * most discriminative terms (corpus IDF), near-duplicate member clusters over the pangenome distance, and
 * an **undirected** diffusion/spread readout. The diffusion caveat is load-bearing and rendered verbatim:
 * this is breadth-across-members, never a directional "A influenced B" claim — surfacing the backend's own
 * non-directional note keeps the UI from implying a causal story the metric cannot support.
 */

import { useEffect, useState } from 'react';

interface CorpusAnalyses {
  collection_id: string;
  members: string[];
  boilerplate: {
    shared_by_all: string[];
    n_shared_by_all: number;
    most_discriminative: { term: string; idf: number }[];
    vocab_size: number;
  };
  near_duplicate_clusters: { members: string[]; size: number }[];
  diffusion: {
    non_directional_note: string;
    member_reach: Record<string, number>;
    component_spread_histogram: { singleton: number; narrow: number; broad: number; core: number };
    core_fraction: number;
  };
}

/** member_reach dict → rows sorted by breadth (descending), values already fractions in [0, 1]. */
export function reachRows(reach: Record<string, number>): { member: string; value: number }[] {
  return Object.entries(reach)
    .map(([member, value]) => ({ member, value }))
    .sort((a, b) => b.value - a.value);
}

const SPREAD_BANDS = [
  { key: 'core', label: 'core', color: 'var(--color-success, #16a34a)' },
  { key: 'broad', label: 'broad', color: 'hsl(210,70%,55%)' },
  { key: 'narrow', label: 'narrow', color: 'hsl(38,85%,55%)' },
  { key: 'singleton', label: 'singleton', color: 'var(--color-bg-muted, #d1d5db)' },
] as const;

export default function AnalysesPanel({ collectionId }: { collectionId: string }) {
  const [data, setData] = useState<CorpusAnalyses | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    fetch(`/api/collections/${collectionId}/corpus-analyses`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status === 404 ? 'Build the corpus graph first (Overview tab).' : `corpus-analyses failed (${r.status})`))))
      .then((d: CorpusAnalyses) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [collectionId]);

  if (error) {
    return <div className="px-3 py-2 rounded bg-[var(--color-danger-subtle)] text-[var(--color-danger)] text-[0.85em]">{error}</div>;
  }
  if (!data) {
    return <div className="text-[var(--color-text-muted)] text-[0.9em]">Computing corpus analyses…</div>;
  }

  const reach = reachRows(data.diffusion.member_reach);
  const hist = data.diffusion.component_spread_histogram;
  const histTotal = Math.max(1, hist.singleton + hist.narrow + hist.broad + hist.core);

  return (
    <div className="flex flex-col gap-6 max-w-[900px]">
      {/* ── Boilerplate + discriminative terms (corpus IDF) ── */}
      <section className="flex flex-col gap-2">
        <h3 className="text-[0.8em] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Boilerplate &amp; discriminative terms
        </h3>
        <div className="text-[0.82em] text-[var(--color-text-muted)]">
          <span className="font-medium text-[var(--color-text)]">{data.boilerplate.n_shared_by_all}</span> term
          {data.boilerplate.n_shared_by_all !== 1 ? 's' : ''} shared by all {data.members.length} members · vocab {data.boilerplate.vocab_size.toLocaleString()}
        </div>
        {data.boilerplate.shared_by_all.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {data.boilerplate.shared_by_all.map((t) => (
              <span key={t} className="px-1.5 py-0.5 rounded text-[0.78em] bg-[var(--color-bg-subtle)] text-[var(--color-text-muted)]">{t}</span>
            ))}
          </div>
        ) : (
          <div className="text-[0.8em] text-[var(--color-text-muted)] opacity-70">No terms shared by every member.</div>
        )}
        {data.boilerplate.most_discriminative.length > 0 && (
          <table className="border-collapse text-[0.78em] mt-1">
            <thead>
              <tr className="text-left text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                <th className="py-1 pr-4 font-medium">Most discriminative</th>
                <th className="py-1 font-medium text-right">IDF</th>
              </tr>
            </thead>
            <tbody>
              {data.boilerplate.most_discriminative.slice(0, 12).map((d) => (
                <tr key={d.term} className="border-b border-[var(--color-border)]">
                  <td className="py-0.5 pr-4">{d.term}</td>
                  <td className="py-0.5 text-right tabular-nums">{d.idf.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* ── Near-duplicate clusters ── */}
      <section className="flex flex-col gap-2">
        <h3 className="text-[0.8em] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Near-duplicate members
        </h3>
        {data.near_duplicate_clusters.length === 0 ? (
          <div className="text-[0.82em] text-[var(--color-text-muted)] opacity-70">No members cluster as near-duplicates at the current threshold.</div>
        ) : (
          <ul className="flex flex-col gap-1 text-[0.82em]">
            {data.near_duplicate_clusters.map((c, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 rounded bg-[var(--color-bg-subtle)] text-[var(--color-text-muted)] tabular-nums">{c.size}</span>
                <span className="truncate" title={c.members.join(', ')}>{c.members.join(' · ')}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Diffusion / spread (undirected) ── */}
      <section className="flex flex-col gap-2">
        <h3 className="text-[0.8em] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Spread across the corpus
        </h3>
        <div className="text-[0.78em] text-[var(--color-text-muted)] italic border-l-2 border-[var(--color-border)] pl-2">
          {data.diffusion.non_directional_note}
        </div>

        <div className="text-[0.82em] text-[var(--color-text-muted)]">
          core fraction <span className="font-medium text-[var(--color-text)] tabular-nums">{(data.diffusion.core_fraction * 100).toFixed(1)}%</span>
        </div>

        {/* component spread histogram */}
        <div className="flex h-4 w-full max-w-[460px] rounded overflow-hidden border border-[var(--color-border)]" role="img" aria-label="component spread histogram">
          {SPREAD_BANDS.map((band) => {
            const v = hist[band.key];
            if (v === 0) return null;
            return (
              <div key={band.key} style={{ width: `${(v / histTotal) * 100}%`, background: band.color }} title={`${band.label}: ${v}`} />
            );
          })}
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[0.72em] text-[var(--color-text-muted)]">
          {SPREAD_BANDS.map((band) => (
            <span key={band.key} className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-sm" style={{ background: band.color }} />
              {band.label} {hist[band.key]}
            </span>
          ))}
        </div>

        {/* per-member reach bars */}
        <div className="flex flex-col gap-1 mt-1">
          {reach.map((r) => (
            <div key={r.member} className="flex items-center gap-2 text-[0.78em]">
              <span className="w-40 shrink-0 truncate text-right text-[var(--color-text-muted)]" title={r.member}>{r.member}</span>
              <div className="flex-1 h-3 bg-[var(--color-bg-muted,#f3f4f6)] rounded overflow-hidden max-w-[300px]">
                <div className="h-3" style={{ width: `${r.value * 100}%`, background: 'var(--color-primary)' }} />
              </div>
              <span className="w-10 tabular-nums text-[var(--color-text-muted)]">{(r.value * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
