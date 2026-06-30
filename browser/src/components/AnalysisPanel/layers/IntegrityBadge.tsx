// Substrate-integrity badge (FR-9 / P4): "are my coordinates sound?" The first thing the suite
// header answers. One click runs GET /integrity (the P4 report that re-runs the producers' own
// invariant checks) and shows green / violation, expandable to the per-invariant breakdown.
import { useState } from 'react';

interface Invariant { name: string; status: string; detail?: string }
interface IntegrityReport {
  framing: string;
  all_green: boolean;
  invariants: Invariant[];
  summary: Record<string, number>;
}

export function IntegrityBadge({ projectId }: { projectId: string | undefined }) {
  const [report, setReport] = useState<IntegrityReport | null>(null);
  const [state, setState] = useState<'idle' | 'loading' | 'error'>('idle');
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!projectId) return;
    setState('loading'); setError(null);
    try {
      const r = await fetch(`/api/projects/${projectId}/integrity`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setReport(await r.json());
      setState('idle');
      setOpen(true);
    } catch (e) {
      setState('error'); setError(String(e));
    }
  }

  const green = report?.all_green;
  const pill = state === 'error'
    ? { bg: '#fef2f2', fg: '#b91c1c', text: 'integrity: error' }
    : report == null
      ? { bg: 'var(--color-bg-muted)', fg: 'var(--color-text-muted)', text: 'check integrity' }
      : green
        ? { bg: '#ecfdf5', fg: '#047857', text: 'integrity ✓' }
        : { bg: '#fffbeb', fg: '#b45309', text: `integrity: ${report.invariants.filter((i) => i.status === 'violation').length} violation(s)` };

  return (
    <div className="relative">
      <button onClick={report == null ? run : () => setOpen((o) => !o)}
        aria-label="Substrate integrity"
        className="px-2 py-0.5 rounded text-[0.75em] font-medium cursor-pointer border border-[var(--color-border-subtle)]"
        style={{ background: pill.bg, color: pill.fg }}>
        {state === 'loading' ? 'checking…' : pill.text}
      </button>
      {open && report && (
        <div className="absolute right-0 mt-1 z-20 w-[320px] p-2 rounded border border-[var(--color-border)] bg-[var(--color-bg)] shadow-lg text-[0.78em]">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold">Substrate integrity ({report.framing})</span>
            <button onClick={run} className="text-[var(--color-text-muted)] hover:underline cursor-pointer">re-run</button>
          </div>
          {report.invariants.map((inv) => (
            <div key={inv.name} className="flex items-start gap-1.5 py-0.5">
              <span style={{ color: inv.status === 'violation' ? '#b45309' : '#047857' }}>
                {inv.status === 'violation' ? '✕' : '✓'}
              </span>
              <span className="font-[var(--font-mono)] text-[0.95em]">{inv.name}</span>
              {inv.detail && <span className="text-[var(--color-text-muted)] truncate" title={inv.detail}>— {inv.detail}</span>}
            </div>
          ))}
          <div className="mt-1.5 pt-1.5 border-t border-[var(--color-border-subtle)] text-[var(--color-text-muted)]">
            {report.summary.paragraph_count} paragraphs · {report.summary.section_count} sections ·
            {' '}{Math.round((report.summary.masked_ratio ?? 0) * 100)}% masked
          </div>
        </div>
      )}
      {state === 'error' && error && (
        <div className="absolute right-0 mt-1 z-20 text-[0.7em] text-[#b91c1c]">{error}</div>
      )}
    </div>
  );
}
