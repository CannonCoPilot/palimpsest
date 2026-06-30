// The per-layer stats panel (P6, FR-14): an instant stats summary (from the manifest — no fetch)
// plus a selectable set of distribution visualizations. Chunk layers draw from the new
// /chunking/{label}/stats endpoint (one fetch backs all four chunk views); embedding layers reuse
// the P3 endpoints (projection / distances / heatmap / clusters). The panel launches in one click
// from a LayerManager row or a lane action, and two can sit side by side for compare.
import { useEffect, useState } from 'react';
import { laneKind, type LayerRef, type LayerStatus } from './types';
import { EmbeddingScatter } from './EmbeddingScatter';
import {
  Histogram, EcdfChart, ViolinChart, FractionBars, Heatmap, histoFromBins,
  type Histo, type ViolinGroup,
} from './charts';

interface Ecdf { x: number[]; y: number[] }
interface ChunkStats {
  n_chunks: number;
  label: string;
  length: {
    words: { histogram: Histo; ecdf: Ecdf };
    chars: { histogram: Histo; ecdf: Ecdf };
  };
  by_element_type: { metric: string; groups: ViolinGroup[] };
  boundary_alignment: {
    tolerance: number;
    n_chunk_boundaries: number; n_aligned: number; fraction_aligned: number;
    n_structural_boundaries: number; n_structural_hit: number; fraction_structural_hit: number;
    by_type: { type: string; n: number; aligned: number; fraction: number }[];
  };
}

type ChunkView = 'length' | 'ecdf' | 'violin' | 'alignment';
type EmbView = 'scatter' | 'pairwise' | 'nn' | 'heatmap' | 'cluster';

const CHUNK_VIEWS: { id: ChunkView; label: string }[] = [
  { id: 'length', label: 'length histogram' },
  { id: 'ecdf', label: 'ECDF' },
  { id: 'violin', label: 'by-element violin' },
  { id: 'alignment', label: 'boundary alignment' },
];
const EMB_VIEWS: { id: EmbView; label: string }[] = [
  { id: 'scatter', label: 'projection scatter' },
  { id: 'pairwise', label: 'pairwise dist' },
  { id: 'nn', label: 'NN dist' },
  { id: 'heatmap', label: 'similarity heatmap' },
  { id: 'cluster', label: 'clusters' },
];

function Selector<T extends string>({ views, active, onPick }: {
  views: { id: T; label: string }[]; active: T; onPick: (v: T) => void;
}) {
  return (
    <div role="tablist" aria-label="visualization options" className="flex flex-wrap gap-1">
      {views.map((v) => (
        <button key={v.id} role="tab" aria-selected={active === v.id} onClick={() => onPick(v.id)}
          className={`px-2 py-0.5 rounded text-[0.72em] border cursor-pointer ${active === v.id
            ? 'bg-[var(--color-primary-subtle,#eff6ff)] text-[var(--color-primary)] border-[var(--color-primary)]'
            : 'border-[var(--color-border)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-muted)]'}`}>
          {v.label}
        </button>
      ))}
    </div>
  );
}

// The manifest's precomputed capability + stats, shown with no fetch — the "instant summary" the
// panel always leads with, regardless of layer kind.
function InstantSummary({ layer }: { layer: LayerStatus }) {
  const rows = [
    ...Object.entries(layer.capability ?? {}),
    ...Object.entries(layer.stats ?? {}),
  ].filter(([, v]) => v != null && typeof v !== 'object');
  if (rows.length === 0) return null;
  return (
    <div aria-label="instant stats summary"
      className="flex flex-wrap gap-x-3 gap-y-0.5 font-[var(--font-mono)] text-[0.72em] mb-2 pb-1.5 border-b border-[var(--color-border-subtle)]">
      {rows.map(([k, v]) => (
        <span key={k}><span className="text-[var(--color-text-muted)]">{k}:</span> {String(v)}</span>
      ))}
    </div>
  );
}

function ChunkStatsBody({ projectId, label }: { projectId: string; label: string }) {
  const [view, setView] = useState<ChunkView>('length');
  const [data, setData] = useState<ChunkStats | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState('loading'); setErr(null);
    fetch(`/api/projects/${projectId}/chunking/${label}/stats`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: ChunkStats) => { if (!cancelled) { setData(d); setState('ready'); } })
      .catch((e) => { if (!cancelled) { setErr(String(e)); setState('error'); } });
    return () => { cancelled = true; };
  }, [projectId, label]);

  return (
    <div className="flex flex-col gap-2">
      <Selector views={CHUNK_VIEWS} active={view} onPick={setView} />
      {state === 'loading' && <div className="text-[0.75em] text-[var(--color-text-muted)]">loading distributions…</div>}
      {state === 'error' && <div role="status" className="text-[0.75em] text-[var(--color-warning,#b45309)]">stats load failed: {err}</div>}
      {state === 'ready' && data && (
        <div data-testid={`chunk-view-${view}`}>
          {view === 'length' && (
            <div className="flex flex-wrap gap-4">
              <Histogram histo={data.length.words.histogram} title="words / chunk" />
              <Histogram histo={data.length.chars.histogram} title="chars / chunk" color="#0ea5e9" />
            </div>
          )}
          {view === 'ecdf' && (
            <div className="flex flex-wrap gap-4">
              <EcdfChart x={data.length.words.ecdf.x} y={data.length.words.ecdf.y} title="words / chunk" />
              <EcdfChart x={data.length.chars.ecdf.x} y={data.length.chars.ecdf.y} title="chars / chunk" />
            </div>
          )}
          {view === 'violin' && (
            <ViolinChart groups={data.by_element_type.groups} metric={data.by_element_type.metric} />
          )}
          {view === 'alignment' && (
            <FractionBars
              title={`boundary alignment (±${data.boundary_alignment.tolerance})`}
              items={[
                { label: 'chunk→struct', value: data.boundary_alignment.fraction_aligned, caption: `${data.boundary_alignment.n_aligned}/${data.boundary_alignment.n_chunk_boundaries}` },
                { label: 'struct covered', value: data.boundary_alignment.fraction_structural_hit, caption: `${data.boundary_alignment.n_structural_hit}/${data.boundary_alignment.n_structural_boundaries}` },
                ...data.boundary_alignment.by_type.map((t) => ({ label: t.type, value: t.fraction, caption: `${t.aligned}/${t.n}` })),
              ]}
            />
          )}
        </div>
      )}
    </div>
  );
}

function EmbeddingStatsBody({ projectId, layer }: { projectId: string; layer: LayerStatus }) {
  const [view, setView] = useState<EmbView>('scatter');
  const [pairwise, setPairwise] = useState<Histo | null>(null);
  const [nn, setNn] = useState<Histo | null>(null);
  const [heatmap, setHeatmap] = useState<number[][] | null>(null);
  const [cluster, setCluster] = useState<{ effective_k: number; sizes: number[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const base = `/api/projects/${projectId}/embedding/${layer.label}`;

  useEffect(() => {
    const have = view === 'scatter'
      || (view === 'pairwise' && pairwise) || (view === 'nn' && nn)
      || (view === 'heatmap' && heatmap) || (view === 'cluster' && cluster);
    if (have) return;
    let cancelled = false;
    setBusy(true); setErr(null);
    (async () => {
      try {
        if (view === 'pairwise' || view === 'nn') {
          const r = await fetch(`${base}/distances?kind=${view}`);
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const j = await r.json();
          const h = histoFromBins(j.edges, j.counts);
          if (!cancelled) (view === 'pairwise' ? setPairwise : setNn)(h);
        } else if (view === 'cluster') {
          const r = await fetch(`${base}/clusters`);
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          if (!cancelled) setCluster(await r.json());
        } else if (view === 'heatmap') {
          const r = await fetch(`${base}/heatmap?order=chunk`);
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const dim = parseInt(r.headers.get('X-Matrix-N') ?? '0', 10);
          const flat = new Float32Array(await r.arrayBuffer());
          const m: number[][] = [];
          for (let i = 0; i < dim; i++) {
            const row: number[] = [];
            for (let j = 0; j < dim; j++) row.push((flat[i * dim + j] + 1) / 2); // cosine [-1,1] → [0,1]
            m.push(row);
          }
          if (!cancelled) setHeatmap(m);
        }
      } catch (e) {
        if (!cancelled) setErr(String(e));
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => { cancelled = true; };
  }, [view, base, pairwise, nn, heatmap, cluster]);

  return (
    <div className="flex flex-col gap-2">
      <Selector views={EMB_VIEWS} active={view} onPick={setView} />
      {busy && <div className="text-[0.75em] text-[var(--color-text-muted)]">loading…</div>}
      {err && <div role="status" className="text-[0.75em] text-[var(--color-warning,#b45309)]">load failed: {err}</div>}
      <div data-testid={`emb-view-${view}`}>
        {view === 'scatter' && <EmbeddingScatter projectId={projectId} layer={layer} />}
        {view === 'pairwise' && pairwise && <Histogram histo={pairwise} title="pairwise cosine distance" />}
        {view === 'nn' && nn && <Histogram histo={nn} title="nearest-neighbour distance" color="#0ea5e9" />}
        {view === 'heatmap' && heatmap && <Heatmap matrix={heatmap} title="cosine similarity" />}
        {view === 'cluster' && cluster && (
          <FractionBars title={`${cluster.effective_k} clusters`}
            items={cluster.sizes.map((s, i) => ({
              label: `cluster ${i}`, value: s / (cluster.sizes.reduce((a, b) => a + b, 0) || 1), caption: `${s}`,
            }))} />
        )}
      </div>
    </div>
  );
}

export function LayerStatsPanel({ projectId, refItem, onClose }: {
  projectId: string; refItem: LayerRef; onClose?: () => void;
}) {
  const isChunk = refItem.trackName === 'chunking';
  const isEmbedding = laneKind(refItem.layer.rendering) === 'embedding-lane';
  return (
    <section data-testid="layer-stats-panel"
      aria-label={`Layer stats: ${refItem.trackName} ${refItem.layer.label}`}
      className="border border-[var(--color-border)] rounded p-2 text-[0.8em] min-w-[340px] flex-1">
      <header className="flex items-center justify-between mb-1.5">
        <span className="font-semibold">{refItem.trackName} · <code>{refItem.layer.label.slice(0, 12)}</code></span>
        {onClose && (
          <button onClick={onClose} aria-label="close stats panel"
            className="text-[var(--color-text-muted)] hover:underline cursor-pointer text-[0.85em]">close</button>
        )}
      </header>
      <InstantSummary layer={refItem.layer} />
      {isChunk ? (
        <ChunkStatsBody projectId={projectId} label={refItem.layer.label} />
      ) : isEmbedding ? (
        <EmbeddingStatsBody projectId={projectId} layer={refItem.layer} />
      ) : (
        <div className="text-[0.78em] text-[var(--color-text-muted)] italic mt-1">
          Distribution views are available for chunk and embedding layers; this layer’s summary is shown above.
        </div>
      )}
    </section>
  );
}
