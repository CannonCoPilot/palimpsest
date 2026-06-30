// The text-level Profile (FR-8 / P4): the ProfileTrack's descriptive statistics + distributions,
// rendered in the repo's zero-viz-dep idiom — histograms as plain <svg> rects, the ECDF as a single
// d3-shape <path>. d3-shape is the one default new dep (path-string generation only, no DOM). The
// data is the static profile.json the track writes (.metadata.report + .metadata.distributions).
import { useEffect, useState } from 'react';
import { line, curveMonotoneX } from 'd3-shape';

interface Histo {
  edges: number[]; counts: number[]; n: number; mean: number; median: number; min: number; max: number;
}
interface ProfileReport {
  counts?: Record<string, number>;
  ttr?: number; mattr?: number; mtld?: number; yules_k?: number; zipf_slope?: number;
  [k: string]: unknown;
}
interface ProfileMeta {
  framing?: string;
  caveats?: string[];
  report?: ProfileReport;
  distributions?: Record<string, Histo>;
}

const W = 260, H = 90, PAD = 4;

// Histogram bars + an ECDF overlay. The bars come from numpy's counts; the ECDF is the normalized
// cumulative fraction, drawn as one d3-shape path so the "one curve dep" earns its place.
function DistributionChart({ title, histo }: { title: string; histo: Histo }) {
  const bins = histo.counts.length;
  if (bins === 0) {
    return <div className="text-[0.72em] text-[var(--color-text-muted)]">{title}: no data</div>;
  }
  const maxCount = Math.max(...histo.counts, 1);
  const total = histo.counts.reduce((a, b) => a + b, 0) || 1;
  const innerW = W - PAD * 2, innerH = H - PAD * 2;

  let cum = 0;
  const ecdfPoints: [number, number][] = histo.counts.map((c, i) => {
    cum += c;
    const x = PAD + ((i + 1) / bins) * innerW;
    const y = PAD + (1 - cum / total) * innerH;
    return [x, y];
  });
  const ecdfPath = line<[number, number]>().x((d) => d[0]).y((d) => d[1]).curve(curveMonotoneX)(ecdfPoints) ?? '';

  return (
    <div className="flex flex-col gap-1">
      <div className="text-[0.72em] font-medium">
        {title} <span className="text-[var(--color-text-muted)]">· μ={histo.mean} · med={histo.median} · [{histo.min}, {histo.max}]</span>
      </div>
      <svg width={W} height={H} role="img" aria-label={`${title} distribution, ${bins} bins`} className="border border-[var(--color-border-subtle)] rounded bg-white">
        {histo.counts.map((c, i) => {
          const bw = innerW / bins;
          const bh = (c / maxCount) * innerH;
          return <rect key={i} x={PAD + i * bw} y={PAD + (innerH - bh)} width={Math.max(1, bw - 0.5)} height={bh} fill="#6366F1" fillOpacity={0.55} />;
        })}
        <path d={ecdfPath} fill="none" stroke="#b45309" strokeWidth={1.25} />
      </svg>
    </div>
  );
}

const metric = (r: ProfileReport, k: string): string =>
  r[k] != null && typeof r[k] === 'number' ? String(r[k]) : '—';

export function ProfileDashboard({ projectId }: { projectId: string | undefined }) {
  const [meta, setMeta] = useState<ProfileMeta | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'absent' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setState('loading'); setError(null);
    fetch(`/data/${projectId}/signals/profile.json`)
      .then((r) => {
        if (r.status === 404) { if (!cancelled) setState('absent'); return null; }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((m) => {
        if (cancelled || m == null) return;
        setMeta(m.metadata ?? m);
        setState('ready');
      })
      .catch((e) => { if (!cancelled) { setState('error'); setError(String(e)); } });
    return () => { cancelled = true; };
  }, [projectId]);

  if (state === 'loading') return <div className="text-[0.8em] text-[var(--color-text-muted)] p-3">Loading profile…</div>;
  if (state === 'absent') return (
    <div className="text-[0.8em] text-[var(--color-text-muted)] italic p-3">
      No profile computed yet. Run the <code>profile</code> track to produce text-level statistics.
    </div>
  );
  if (state === 'error') return <div className="text-[0.8em] text-[var(--color-warning,#b45309)] p-3">Profile load failed: {error}</div>;

  const report = meta?.report ?? {};
  const distributions = meta?.distributions ?? {};
  const counts = report.counts ?? {};

  return (
    <div className="p-3 flex flex-col gap-3" aria-label="Text profile">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[0.78em]">
        <Stat label="tokens" value={counts.tokens != null ? String(counts.tokens) : '—'} />
        <Stat label="types" value={counts.types != null ? String(counts.types) : '—'} />
        <Stat label="TTR" value={metric(report, 'ttr')} />
        <Stat label="MATTR" value={metric(report, 'mattr')} />
        <Stat label="MTLD" value={metric(report, 'mtld')} />
        <Stat label="Yule's K" value={metric(report, 'yules_k')} />
        <Stat label="Zipf slope" value={metric(report, 'zipf_slope')} />
      </div>
      <div className="flex flex-wrap gap-4">
        {Object.entries(distributions).map(([name, h]) => (
          <DistributionChart key={name} title={name.replace(/_/g, ' ')} histo={h} />
        ))}
      </div>
      {meta?.framing && (
        <div className="text-[0.7em] text-[var(--color-text-muted)] border-t border-[var(--color-border-subtle)] pt-1.5">
          {meta.framing} statistics{meta.caveats?.length ? ` — ${meta.caveats[0]}` : ''}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-[var(--color-border-subtle)] rounded px-2 py-1">
      <div className="text-[var(--color-text-muted)] text-[0.85em]">{label}</div>
      <div className="font-[var(--font-mono)] font-medium">{value}</div>
    </div>
  );
}
