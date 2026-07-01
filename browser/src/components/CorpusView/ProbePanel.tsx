/**
 * ProbePanel — corpus probe R(q, Corpus) over the shared embedding space (C7c, FR-31 / C6b).
 *
 * Ranks corpus passages against a query. Two query sources: a **ref** passage already embedded in the
 * corpus (service-free — a direct vector lookup) or free **text** (embedded here first, an expensive op
 * gated behind the CostDialog so it never auto-runs). Probing is embedding-space work, so it is gated by
 * the C1 metric-congruence contract: a word-method / mixed-space collection fails loud (409) and the panel
 * surfaces that honestly with a pointer to reconcile — never a silent cross-space probe.
 */

import { useCallback, useState } from 'react';
import CostDialog from './CostDialog';

interface ProbeResult {
  collection_id: string;
  metric: string;
  congruence_key: string | null;
  dim: number;
  k: number;
  per_member_k: number | null;
  members_searched: string[];
  n_candidates: number;
  results: { project_id: string; label: string; chunk_index: number; similarity: number; text: string }[];
}

type QueryMode = 'ref' | 'text';

export default function ProbePanel({ collectionId, members }: { collectionId: string; members: string[] }) {
  const [mode, setMode] = useState<QueryMode>('ref');
  const [refProject, setRefProject] = useState(members[0] ?? '');
  const [refChunk, setRefChunk] = useState(0);
  const [text, setText] = useState('');
  const [provider, setProvider] = useState('');
  const [endpoint, setEndpoint] = useState('');
  const [model, setModel] = useState('');
  const [k, setK] = useState(10);

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ProbeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [costOpen, setCostOpen] = useState(false);

  const doProbe = useCallback(async () => {
    setRunning(true);
    setError(null);
    setCostOpen(false);
    try {
      const body =
        mode === 'ref'
          ? { ref_project: refProject, ref_chunk: refChunk, metric: 'cosine', k }
          : { q: text, provider, endpoint, model, metric: 'cosine', k };
      const resp = await fetch(`/api/collections/${collectionId}/probe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const j = await resp.json().catch(() => ({}));
        const hint = resp.status === 409 ? ' — members lack a shared embedding space; reconcile them first (congruence badge).' : '';
        throw new Error((j.detail ?? `probe failed (${resp.status})`) + hint);
      }
      setResult((await resp.json()) as ProbeResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setRunning(false);
    }
  }, [collectionId, mode, refProject, refChunk, text, provider, endpoint, model, k]);

  // NEVER auto-run. A ref probe reuses an existing embedding (a cheap lookup) → run directly. A text probe
  // must embed the query first (expensive) → confirm the cost dialog first.
  const onRun = useCallback(() => {
    if (mode === 'text') setCostOpen(true);
    else void doProbe();
  }, [mode, doProbe]);

  const textReady = text.trim().length > 0 && provider.trim() && endpoint.trim() && model.trim();
  const canRun = mode === 'ref' ? Boolean(refProject) : Boolean(textReady);

  return (
    <div className="flex flex-col gap-5 max-w-[900px]">
      <section className="flex flex-col gap-3">
        <h3 className="text-[0.8em] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          Probe · rank corpus passages against a query
        </h3>

        <div className="flex items-center gap-1 text-[0.82em]" role="tablist" aria-label="Query source">
          {(['ref', 'text'] as QueryMode[]).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              onClick={() => setMode(m)}
              className={`px-2.5 py-1 rounded border cursor-pointer ${mode === m ? 'border-[var(--color-primary)] text-[var(--color-primary)]' : 'border-[var(--color-border)] text-[var(--color-text-muted)]'}`}
            >
              {m === 'ref' ? 'existing passage' : 'text query'}
            </button>
          ))}
        </div>

        {mode === 'ref' ? (
          <div className="flex flex-wrap items-end gap-3 text-[0.82em]">
            <label className="flex flex-col gap-1">
              <span className="text-[var(--color-text-muted)]">Member</span>
              <select
                value={refProject}
                onChange={(e) => setRefProject(e.target.value)}
                className="px-2 py-1 border border-[var(--color-border)] rounded bg-[var(--color-bg)] cursor-pointer max-w-64 truncate"
              >
                {members.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[var(--color-text-muted)]">Chunk index</span>
              <input
                type="number"
                min={0}
                value={refChunk}
                onChange={(e) => setRefChunk(Math.max(0, Number(e.target.value) || 0))}
                className="w-24 px-2 py-1 border border-[var(--color-border)] rounded bg-[var(--color-bg)]"
              />
            </label>
          </div>
        ) : (
          <div className="flex flex-col gap-2 text-[0.82em]">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Query text to embed and rank against the corpus…"
              rows={2}
              className="w-full px-2 py-1 border border-[var(--color-border)] rounded bg-[var(--color-bg)] resize-y"
            />
            <div className="flex flex-wrap gap-2">
              <input value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="provider" className="w-28 px-2 py-1 border border-[var(--color-border)] rounded bg-[var(--color-bg)]" />
              <input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="endpoint" className="flex-1 min-w-40 px-2 py-1 border border-[var(--color-border)] rounded bg-[var(--color-bg)]" />
              <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="model" className="w-40 px-2 py-1 border border-[var(--color-border)] rounded bg-[var(--color-bg)]" />
            </div>
            <span className="text-[0.75em] text-[var(--color-text-muted)]">The query is embedded via this service before ranking — its cost is confirmed first.</span>
          </div>
        )}

        <div className="flex items-center gap-3 text-[0.82em]">
          <label className="flex items-center gap-1.5">
            <span className="text-[var(--color-text-muted)]">top-k</span>
            <input
              type="number"
              min={1}
              max={200}
              value={k}
              onChange={(e) => setK(Math.min(200, Math.max(1, Number(e.target.value) || 1)))}
              className="w-16 px-2 py-1 border border-[var(--color-border)] rounded bg-[var(--color-bg)]"
            />
          </label>
          <button
            onClick={onRun}
            disabled={running || !canRun}
            className="px-3 py-1 rounded border border-[var(--color-primary)] bg-[var(--color-primary)] text-white cursor-pointer disabled:opacity-50 font-medium"
          >
            {running ? 'Probing…' : 'Run probe'}
          </button>
        </div>

        {error && (
          <div className="px-3 py-2 rounded bg-[var(--color-danger-subtle)] text-[var(--color-danger)] text-[0.85em]">{error}</div>
        )}
      </section>

      {result && (
        <section className="flex flex-col gap-2">
          <div className="text-[0.82em] text-[var(--color-text-muted)]">
            {result.n_candidates} candidate{result.n_candidates !== 1 ? 's' : ''} across {result.members_searched.length} member{result.members_searched.length !== 1 ? 's' : ''} · dim {result.dim} · {result.metric}
          </div>
          <table className="w-full border-collapse text-[0.78em]">
            <thead>
              <tr className="text-left text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
                <th className="py-1 pr-3 font-medium">#</th>
                <th className="py-1 pr-3 font-medium">Member</th>
                <th className="py-1 pr-3 font-medium text-right">chunk</th>
                <th className="py-1 pr-3 font-medium text-right">sim</th>
                <th className="py-1 font-medium">passage</th>
              </tr>
            </thead>
            <tbody>
              {result.results.map((r, i) => (
                <tr key={`${r.project_id}-${r.chunk_index}`} className="border-b border-[var(--color-border)] align-top">
                  <td className="py-1 pr-3 tabular-nums text-[var(--color-text-muted)]">{i + 1}</td>
                  <td className="py-1 pr-3 truncate max-w-40" title={r.project_id}>{r.project_id}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{r.chunk_index}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{r.similarity.toFixed(4)}</td>
                  <td className="py-1 text-[var(--color-text-muted)]">{r.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {costOpen && (
        <CostDialog
          title="Embed the query"
          confirmLabel="Embed & probe"
          busy={running}
          onConfirm={() => void doProbe()}
          onCancel={() => setCostOpen(false)}
        >
          <p>The query text will be embedded once via <span className="font-mono">{model || 'the chosen model'}</span> at <span className="font-mono">{endpoint || 'the chosen endpoint'}</span>, then ranked against every member's embedding store (top-{k}).</p>
          <p>This calls the embedding service — it runs only when you confirm.</p>
        </CostDialog>
      )}
    </div>
  );
}
