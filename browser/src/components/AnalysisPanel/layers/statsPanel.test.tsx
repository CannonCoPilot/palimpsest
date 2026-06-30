import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { Histogram, EcdfChart, ViolinChart, FractionBars, Heatmap, histoFromBins } from './charts';
import { LayerStatsPanel } from './LayerStatsPanel';
import type { LayerRef } from './types';

const histo = { edges: [2, 4, 6, 8], counts: [1, 1, 1], n: 3, mean: 4, median: 4, min: 2, max: 8 };

const chunkStats = {
  n_chunks: 3,
  label: 'abc1234567',
  length: {
    words: { histogram: histo, ecdf: { x: [2, 4, 6], y: [0.33, 0.66, 1.0] } },
    chars: { histogram: { ...histo, edges: [10, 20, 30, 40], min: 10, max: 40 }, ecdf: { x: [10, 20, 30], y: [0.33, 0.66, 1.0] } },
  },
  by_element_type: {
    metric: 'words',
    groups: [
      { type: 'verse', values: [2, 4], summary: { n: 2, min: 2, q1: 2.5, median: 3, q3: 3.5, max: 4, mean: 3 } },
      { type: 'chapter', values: [6], summary: { n: 1, min: 6, q1: 6, median: 6, q3: 6, max: 6, mean: 6 } },
    ],
  },
  boundary_alignment: {
    tolerance: 0, n_chunk_boundaries: 3, n_aligned: 1, fraction_aligned: 0.333,
    n_structural_boundaries: 2, n_structural_hit: 1, fraction_structural_hit: 0.5,
    by_type: [{ type: 'verse', n: 2, aligned: 1, fraction: 0.5 }, { type: 'chapter', n: 1, aligned: 0, fraction: 0 }],
  },
};

const chunkRef: LayerRef = {
  trackName: 'chunking',
  layer: { label: 'abc1234567', status: 'computed', capability: { kind: 'chunk', mode: 'word', size: 7 }, stats: { count: 3 }, rendering: { track_view: 'chunk-band' } },
};
const embRef: LayerRef = {
  trackName: 'embedding',
  layer: { label: 'def4567890', status: 'computed', capability: { kind: 'embedding', model: 'qwen', dim: 2560 }, stats: { count: 2 }, rendering: { track_view: 'embedding-lane', projection_ref: '/api/projects/p1/embedding/def4567890/projection' } },
};
const repeatRef: LayerRef = {
  trackName: 'repeat',
  layer: { label: 'aaa111bbb2', status: 'computed', capability: { kind: 'repeat' }, stats: { phrase_count: 5 }, rendering: { track_view: 'repeat-band' } },
};

// A fetch router: each entry is [url-substring, () => Response-like].
function routedFetch(routes: [string, () => unknown][]) {
  return vi.fn((url: string) => {
    for (const [pat, resp] of routes) if (url.includes(pat)) return Promise.resolve(resp());
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
  });
}
const json = (body: unknown) => () => ({ ok: true, json: () => Promise.resolve(body) });
const bin = (arr: number[], dim?: number) => () => ({
  ok: true,
  arrayBuffer: () => Promise.resolve(new Float32Array(arr).buffer),
  headers: { get: (h: string) => (h === 'X-Matrix-N' && dim != null ? String(dim) : null) },
});

describe('chart primitives', () => {
  it('Histogram renders an svg with the bin count + n in its label', () => {
    render(<Histogram histo={histo} title="words / chunk" />);
    expect(screen.getByRole('img', { name: /words \/ chunk histogram, 3 bins, n=3/i })).toBeInTheDocument();
  });
  it('EcdfChart renders an ECDF path', () => {
    render(<EcdfChart x={[2, 4, 6]} y={[0.33, 0.66, 1]} title="words / chunk" />);
    expect(screen.getByRole('img', { name: /words \/ chunk ECDF over 3 distinct values/i })).toBeInTheDocument();
  });
  it('ViolinChart names each element-type group', () => {
    render(<ViolinChart groups={chunkStats.by_element_type.groups} metric="words" />);
    expect(screen.getByRole('img', { name: /by element type, 2 groups: verse \(n=2\), chapter \(n=1\)/i })).toBeInTheDocument();
  });
  it('FractionBars renders percentages', () => {
    render(<FractionBars title="boundary alignment (±0)" items={[{ label: 'chunk→struct', value: 0.333 }]} />);
    expect(screen.getByRole('img', { name: /chunk→struct 33%/i })).toBeInTheDocument();
  });
  it('Heatmap renders an n×n matrix', () => {
    render(<Heatmap matrix={[[1, 0.5], [0.5, 1]]} title="cosine similarity" />);
    expect(screen.getByRole('img', { name: /cosine similarity similarity heatmap, 2 by 2/i })).toBeInTheDocument();
  });
  it('histoFromBins derives n/min/max from edges+counts', () => {
    const h = histoFromBins([0, 1, 2], [3, 1]);
    expect(h.n).toBe(4);
    expect(h.min).toBe(0);
    expect(h.max).toBe(2);
  });
});

describe('LayerStatsPanel — chunk layer', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('shows instant summary and switches across all four chunk views', async () => {
    vi.stubGlobal('fetch', routedFetch([['/chunking/', json(chunkStats)]]));
    render(<LayerStatsPanel projectId="p1" refItem={chunkRef} />);

    // Instant summary (no fetch) — from capability/stats.
    const summary = screen.getByLabelText('instant stats summary');
    expect(within(summary).getByText(/chunk/)).toBeInTheDocument();

    // Default: length histograms (words + chars).
    const lenView = await screen.findByTestId('chunk-view-length');
    expect(within(lenView).getByRole('img', { name: /words \/ chunk histogram/i })).toBeInTheDocument();
    expect(within(lenView).getByRole('img', { name: /chars \/ chunk histogram/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'ECDF' }));
    const ecdfView = await screen.findByTestId('chunk-view-ecdf');
    expect(within(ecdfView).getByRole('img', { name: /words \/ chunk ECDF/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'by-element violin' }));
    const violinView = await screen.findByTestId('chunk-view-violin');
    expect(within(violinView).getByRole('img', { name: /by element type, 2 groups/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'boundary alignment' }));
    const alignView = await screen.findByTestId('chunk-view-alignment');
    expect(within(alignView).getByRole('img', { name: /chunk→struct 33%/i })).toBeInTheDocument();
  });

  it('surfaces an honest error when the stats endpoint fails', async () => {
    vi.stubGlobal('fetch', routedFetch([['/chunking/', () => ({ ok: false, status: 500 })]]));
    render(<LayerStatsPanel projectId="p1" refItem={chunkRef} />);
    expect(await screen.findByText(/stats load failed/i)).toBeInTheDocument();
  });
});

describe('LayerStatsPanel — embedding layer', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('reuses P3 endpoints across scatter / pairwise / nn / heatmap / cluster', async () => {
    vi.stubGlobal('fetch', routedFetch([
      ['/projection', bin([0, 0, 1, 1])], // EmbeddingScatter (2 points)
      ['/distances?kind=pairwise', json({ kind: 'pairwise', edges: [0, 1, 2], counts: [3, 2], sampled_pairs: 5, total_pairs: 5 })],
      ['/distances?kind=nn', json({ kind: 'nn', edges: [0, 1, 2], counts: [4, 1], count: 5 })],
      ['/heatmap', bin([1, 0.2, 0.2, 1], 2)],
      ['/clusters', json({ requested_k: 8, effective_k: 2, seed: 0, labels: [0, 1], sizes: [1, 1] })],
    ]));
    render(<LayerStatsPanel projectId="p1" refItem={embRef} />);

    // Default scatter present.
    expect(await screen.findByTestId('emb-view-scatter')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'pairwise dist' }));
    const pw = await screen.findByTestId('emb-view-pairwise');
    expect(await within(pw).findByRole('img', { name: /pairwise cosine distance histogram/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'NN dist' }));
    const nn = await screen.findByTestId('emb-view-nn');
    expect(await within(nn).findByRole('img', { name: /nearest-neighbour distance histogram/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'similarity heatmap' }));
    const hm = await screen.findByTestId('emb-view-heatmap');
    expect(await within(hm).findByRole('img', { name: /cosine similarity similarity heatmap, 2 by 2/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'clusters' }));
    const cl = await screen.findByTestId('emb-view-cluster');
    expect(await within(cl).findByRole('img', { name: /2 clusters/i })).toBeInTheDocument();
  });
});

describe('LayerStatsPanel — non-distribution layer', () => {
  it('shows the summary and an honest note for a repeat band layer', () => {
    render(<LayerStatsPanel projectId="p1" refItem={repeatRef} />);
    expect(screen.getByLabelText('instant stats summary')).toBeInTheDocument();
    expect(screen.getByText(/Distribution views are available for chunk and embedding layers/i)).toBeInTheDocument();
  });
});
