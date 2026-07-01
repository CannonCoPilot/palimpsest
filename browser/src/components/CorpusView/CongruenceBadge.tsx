/**
 * CongruenceBadge — the metric-congruence compatibility badge (C7, FR-39).
 *
 * The UI face of the C1 metric-congruence contract: for a chosen metric it asks
 * `GET /api/collections/{id}/congruence?metric=` and shows whether the collection's members are
 * comparable on that metric. Token metrics (word_overlap/edit_distance) read raw chunk strings and are
 * congruent across any two chunked texts; embedding metrics (cosine) require the same embedding space,
 * so a collection whose members lack a shared embedding layer flags **incongruent** and surfaces the
 * reconcile action (re-embed into a common space) — never a silent cross-space comparison.
 */

import { useEffect, useState } from 'react';

interface CongruenceReport {
  metric: string;
  needs_embedding: boolean;
  members: string[];
  keys: Record<string, string | null>;
  groups: Record<string, string[]>;
  missing: string[];
  all_congruent: boolean;
  reconcile_hint: string | null;
}

const METRICS = ['cosine', 'word_overlap'] as const;

export default function CongruenceBadge({
  collectionId,
  onReconcile,
}: {
  collectionId: string;
  onReconcile?: (report: CongruenceReport) => void;
}) {
  const [metric, setMetric] = useState<string>('cosine');
  const [report, setReport] = useState<CongruenceReport | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!collectionId) return;
    setReport(null);
    setError(null);
    fetch(`/api/collections/${collectionId}/congruence?metric=${encodeURIComponent(metric)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('congruence fetch failed'))))
      .then((data: CongruenceReport) => setReport(data))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [collectionId, metric]);

  const congruent = report?.all_congruent ?? false;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        role="status"
        aria-label={`metric congruence: ${report ? (congruent ? 'congruent' : 'incongruent') : 'loading'}`}
        title="Metric-congruence compatibility (FR-39) — can these members be compared on this metric?"
        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[0.8em] cursor-pointer border"
        style={{
          background: 'var(--color-bg-subtle)',
          borderColor: report ? (congruent ? 'var(--color-success, #16a34a)' : 'var(--color-warning, #d97706)') : 'var(--color-border)',
          color: report ? (congruent ? 'var(--color-success, #16a34a)' : 'var(--color-warning, #d97706)') : 'var(--color-text-muted)',
        }}
      >
        <span className="w-2 h-2 rounded-full" style={{ background: 'currentColor' }} />
        {report ? (congruent ? 'congruent' : 'incongruent') : '…'}
        <span className="text-[var(--color-text-muted)]">· {metric}</span>
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-1 w-80 p-3 rounded border border-[var(--color-border)] bg-[var(--color-bg)] shadow-lg text-[0.8em] flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <label className="text-[var(--color-text-muted)]">Metric</label>
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              className="px-1.5 py-0.5 border border-[var(--color-border)] rounded bg-[var(--color-bg)] cursor-pointer"
            >
              {METRICS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            {report && (
              <span className="ml-auto text-[var(--color-text-muted)]">
                {report.needs_embedding ? 'embedding space' : 'raw tokens'}
              </span>
            )}
          </div>

          {error && <div className="text-[var(--color-danger)]">{error}</div>}

          {report && (
            <>
              <ul className="flex flex-col gap-0.5 max-h-40 overflow-auto">
                {report.members.map((m) => {
                  const key = report.keys[m];
                  return (
                    <li key={m} className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: key ? 'var(--color-success, #16a34a)' : 'var(--color-danger, #ef4444)' }} />
                      <span className="truncate max-w-40" title={m}>{m}</span>
                      <span className="ml-auto text-[var(--color-text-muted)] font-mono text-[0.9em] truncate max-w-28" title={key ?? 'missing layer'}>
                        {key ? key.split(':').slice(-1)[0] : 'missing layer'}
                      </span>
                    </li>
                  );
                })}
              </ul>

              {!congruent && (
                <div className="flex flex-col gap-1.5 pt-1 border-t border-[var(--color-border)]">
                  <div className="text-[var(--color-warning, #d97706)]">
                    {report.missing.length > 0
                      ? `${report.missing.length} member(s) missing the required embedding layer.`
                      : 'Members sit in different embedding spaces.'}
                  </div>
                  {report.reconcile_hint && (
                    <div className="text-[var(--color-text-muted)]">{report.reconcile_hint}</div>
                  )}
                  <button
                    onClick={() => onReconcile?.(report)}
                    className="self-start px-2 py-0.5 rounded border border-[var(--color-warning, #d97706)] text-[var(--color-warning, #d97706)] hover:bg-[var(--color-bg-subtle)] cursor-pointer"
                  >
                    Reconcile…
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
