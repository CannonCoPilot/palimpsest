// Zero-dep svg chart primitives for the per-layer stats panel (P6, FR-14). Same idiom as
// ProfileDashboard: histograms/violins/bars are plain <svg> rects/paths; the one curve (ECDF) is a
// d3-shape <path>. Every chart writes its key numbers into an aria-label so it is assertable by
// vitest/Playwright with no test-only hooks. No data fetching here — the panel owns that.
import { line, curveMonotoneX } from 'd3-shape';

export interface Histo {
  edges: number[]; counts: number[]; n: number; mean: number; median: number; min: number; max: number;
}
export interface ViolinGroup {
  type: string;
  values: number[];
  summary: { n: number; min: number; q1: number; median: number; q3: number; max: number; mean: number };
}
export interface AlignmentItem { label: string; value: number; caption?: string }

const IND = '#6366F1';

// Build a full Histo from raw bin edges + counts (the P3 /distances shape, which omits summary
// stats): mean from bin midpoints, median by cumulative crossing, range from the outer edges.
export function histoFromBins(edges: number[], counts: number[]): Histo {
  const n = counts.reduce((a, b) => a + b, 0);
  if (edges.length < 2 || n === 0) {
    return { edges, counts, n, mean: 0, median: 0, min: edges[0] ?? 0, max: edges[edges.length - 1] ?? 0 };
  }
  const mids = counts.map((_, i) => (edges[i] + edges[i + 1]) / 2);
  const mean = mids.reduce((a, m, i) => a + m * counts[i], 0) / n;
  let cum = 0, median = mids[0];
  for (let i = 0; i < counts.length; i++) {
    cum += counts[i];
    if (cum >= n / 2) { median = mids[i]; break; }
  }
  const round = (v: number) => Math.round(v * 1000) / 1000;
  return { edges, counts, n, mean: round(mean), median: round(median), min: round(edges[0]), max: round(edges[edges.length - 1]) };
}

// svg rect histogram. `counts` come straight from numpy; the tallest bar fills the height.
export function Histogram({ histo, title, width = 300, height = 110, color = IND }: {
  histo: Histo; title: string; width?: number; height?: number; color?: string;
}) {
  const pad = 4;
  const bins = histo.counts.length;
  if (bins === 0) {
    return <div className="text-[0.72em] text-[var(--color-text-muted)]">{title}: no data</div>;
  }
  const maxCount = Math.max(...histo.counts, 1);
  const innerW = width - pad * 2, innerH = height - pad * 2;
  const bw = innerW / bins;
  return (
    <figure className="flex flex-col gap-1 m-0">
      <figcaption className="text-[0.72em] font-medium">
        {title} <span className="text-[var(--color-text-muted)]">· μ={histo.mean} · med={histo.median} · [{histo.min}, {histo.max}] · n={histo.n}</span>
      </figcaption>
      <svg width={width} height={height} role="img"
        aria-label={`${title} histogram, ${bins} bins, n=${histo.n}, mean ${histo.mean}`}
        className="border border-[var(--color-border-subtle)] rounded bg-white">
        {histo.counts.map((c, i) => {
          const bh = (c / maxCount) * innerH;
          return <rect key={i} x={pad + i * bw} y={pad + (innerH - bh)} width={Math.max(1, bw - 0.5)} height={bh} fill={color} fillOpacity={0.6} />;
        })}
      </svg>
    </figure>
  );
}

// ECDF from explicit {x,y} arrays (the backend's ecdf(): x sorted distinct, y the fraction ≤ x).
export function EcdfChart({ x, y, title, width = 300, height = 110 }: {
  x: number[]; y: number[]; title: string; width?: number; height?: number;
}) {
  const pad = 6;
  if (x.length === 0) {
    return <div className="text-[0.72em] text-[var(--color-text-muted)]">{title}: no data</div>;
  }
  const innerW = width - pad * 2, innerH = height - pad * 2;
  const minX = x[0], maxX = x[x.length - 1];
  const sx = (maxX - minX) || 1;
  const pts: [number, number][] = x.map((xi, i) => [
    pad + ((xi - minX) / sx) * innerW,
    pad + (1 - y[i]) * innerH, // y in [0,1]; flip so 1.0 is at the top
  ]);
  const path = line<[number, number]>().x((d) => d[0]).y((d) => d[1]).curve(curveMonotoneX)(pts) ?? '';
  return (
    <figure className="flex flex-col gap-1 m-0">
      <figcaption className="text-[0.72em] font-medium">
        {title} <span className="text-[var(--color-text-muted)]">· ECDF · [{minX}, {maxX}]</span>
      </figcaption>
      <svg width={width} height={height} role="img"
        aria-label={`${title} ECDF over ${x.length} distinct values, range ${minX} to ${maxX}`}
        className="border border-[var(--color-border-subtle)] rounded bg-white">
        <path d={path} fill="none" stroke="#b45309" strokeWidth={1.5} />
      </svg>
    </figure>
  );
}

// Per-element-type violins, drawn on a shared vertical scale so groups are comparable. Each violin is
// a symmetric area whose half-width ∝ the binned density of that group's values; a tick marks the
// median. A genuine violin, computed client-side from the raw `values` (no KDE dep).
export function ViolinChart({ groups, metric = 'words', width = 320, height = 150, vbins = 12 }: {
  groups: ViolinGroup[]; metric?: string; width?: number; height?: number; vbins?: number;
}) {
  const pad = 18;
  const nonEmpty = groups.filter((g) => g.values.length > 0);
  if (nonEmpty.length === 0) {
    return <div className="text-[0.72em] text-[var(--color-text-muted)]">by element type: no data</div>;
  }
  const allMin = Math.min(...nonEmpty.map((g) => g.summary.min));
  const allMax = Math.max(...nonEmpty.map((g) => g.summary.max));
  const span = (allMax - allMin) || 1;
  const innerH = height - pad * 2;
  const slot = (width - pad) / nonEmpty.length;
  const halfMax = Math.min(slot, 64) / 2 - 4;
  const yOf = (v: number) => pad + (1 - (v - allMin) / span) * innerH;

  return (
    <figure className="flex flex-col gap-1 m-0">
      <figcaption className="text-[0.72em] font-medium">
        {metric} by element type <span className="text-[var(--color-text-muted)]">· {nonEmpty.length} groups</span>
      </figcaption>
      <svg width={width} height={height} role="img"
        aria-label={`${metric} distribution by element type, ${nonEmpty.length} groups: ${nonEmpty.map((g) => `${g.type} (n=${g.summary.n})`).join(', ')}`}
        className="border border-[var(--color-border-subtle)] rounded bg-white">
        {nonEmpty.map((g, gi) => {
          const cx = pad + slot * gi + slot / 2;
          // Bin the group's values into vbins over the shared range → density half-widths.
          const dens = new Array(vbins).fill(0);
          for (const v of g.values) {
            let b = Math.floor(((v - allMin) / span) * vbins);
            if (b < 0) b = 0; if (b >= vbins) b = vbins - 1;
            dens[b] += 1;
          }
          const dMax = Math.max(...dens, 1);
          // Polygon: up the left edge (bottom→top), then down the right edge (top→bottom). No curve
          // interpolation — the density is noisy, so a straight mirrored outline can't overshoot.
          const left: [number, number][] = [];
          const right: [number, number][] = [];
          for (let b = 0; b < vbins; b++) {
            const vy = pad + (1 - (b + 0.5) / vbins) * innerH;
            const hw = (dens[b] / dMax) * halfMax;
            left.push([cx - hw, vy]);
            right.push([cx + hw, vy]);
          }
          const poly = [...left, ...right.reverse()].map(([px, py]) => `${px.toFixed(1)},${py.toFixed(1)}`).join(' ');
          return (
            <g key={g.type}>
              <polygon points={poly} fill={IND} fillOpacity={0.45} stroke={IND} strokeOpacity={0.6} strokeWidth={0.75} />
              <line x1={cx - halfMax} x2={cx + halfMax} y1={yOf(g.summary.median)} y2={yOf(g.summary.median)} stroke="#b45309" strokeWidth={1.25} />
              <text x={cx} y={height - 4} textAnchor="middle" className="fill-[var(--color-text-muted)]" fontSize={9}>{g.type}</text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

// Horizontal bars for fractions in [0,1] (boundary-alignment breakdown). Width ∝ value; caption at end.
export function FractionBars({ items, title, width = 320, rowH = 18 }: {
  items: AlignmentItem[]; title: string; width?: number; rowH?: number;
}) {
  const labelW = 92, pad = 4, barMax = width - labelW - 64;
  if (items.length === 0) {
    return <div className="text-[0.72em] text-[var(--color-text-muted)]">{title}: no data</div>;
  }
  const height = items.length * rowH + pad * 2;
  return (
    <figure className="flex flex-col gap-1 m-0">
      <figcaption className="text-[0.72em] font-medium">{title}</figcaption>
      <svg width={width} height={height} role="img"
        aria-label={`${title}: ${items.map((it) => `${it.label} ${(it.value * 100).toFixed(0)}%`).join(', ')}`}
        className="border border-[var(--color-border-subtle)] rounded bg-white">
        {items.map((it, i) => {
          const y = pad + i * rowH;
          const w = Math.max(0, Math.min(1, it.value)) * barMax;
          return (
            <g key={it.label}>
              <text x={pad} y={y + rowH * 0.7} fontSize={9} className="fill-[var(--color-text)]">{it.label}</text>
              <rect x={labelW} y={y + 2} width={barMax} height={rowH - 5} fill="#e5e7eb" />
              <rect x={labelW} y={y + 2} width={w} height={rowH - 5} fill={IND} fillOpacity={0.7} />
              <text x={labelW + barMax + 4} y={y + rowH * 0.7} fontSize={9} className="fill-[var(--color-text-muted)]">
                {(it.value * 100).toFixed(0)}%{it.caption ? ` ${it.caption}` : ''}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}

// Generic matrix heatmap (embedding similarity). Values assumed in [0,1]; deeper = higher.
export function Heatmap({ matrix, title, size = 240 }: { matrix: number[][]; title: string; size?: number }) {
  const n = matrix.length;
  if (n === 0) {
    return <div className="text-[0.72em] text-[var(--color-text-muted)]">{title}: no data</div>;
  }
  const cell = size / n;
  return (
    <figure className="flex flex-col gap-1 m-0">
      <figcaption className="text-[0.72em] font-medium">{title} <span className="text-[var(--color-text-muted)]">· {n}×{n}</span></figcaption>
      <svg width={size} height={size} role="img" aria-label={`${title} similarity heatmap, ${n} by ${n}`}
        className="border border-[var(--color-border-subtle)] rounded bg-white">
        {matrix.map((row, i) =>
          row.map((v, j) => {
            const t = Math.max(0, Math.min(1, v));
            return <rect key={`${i}-${j}`} x={j * cell} y={i * cell} width={Math.ceil(cell)} height={Math.ceil(cell)}
              fill={`rgba(99,102,241,${(0.12 + 0.88 * t).toFixed(3)})`} />;
          }),
        )}
      </svg>
    </figure>
  );
}
