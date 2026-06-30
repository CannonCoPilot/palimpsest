import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { LayerWorkbench } from './LayerWorkbench';
import type { LayerRef, LayerStatus } from './types';

function stubFetch() {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.includes('/signals/')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ segment_offsets: [[0, 100], [100, 250]] }) });
    }
    if (url.includes('/lane')) {
      return Promise.resolve({ ok: true, arrayBuffer: () => Promise.resolve(new Float32Array([0.2, 0.8, 0.5]).buffer) });
    }
    return Promise.resolve({ ok: false, status: 404 });
  }));
}

const band = (label: string): LayerStatus => ({
  label, status: 'computed',
  capability: { kind: 'chunk', mode: 'word', size: 200 },
  stats: { count: 2, coverage_pct: 99.9 },
  rendering: { track_view: 'chunk-band', overviewBarRendering: { type: 'chunk-band', color: '#6366F1' } },
});
const embed = (label: string): LayerStatus => ({
  label, status: 'computed',
  capability: { kind: 'embedding', model: 'qwen3', dim: 2560 },
  stats: { count: 3, dim: 2560 },
  rendering: { track_view: 'embedding-lane', encoding: 'nn-density', projection_ref: `/x/${label}/projection` },
});

const refs: LayerRef[] = [
  { trackName: 'chunking', layer: band('word7') },
  { trackName: 'chunking', layer: band('slide10') },
  { trackName: 'embedding', layer: embed('emb01') },
];

describe('LayerWorkbench — plural coexistence + manager controls (FR-13)', () => {
  beforeEach(() => stubFetch());
  afterEach(() => vi.unstubAllGlobals());

  it('lists every layer in the manager with provenance + instant stats', async () => {
    render(<LayerWorkbench projectId="p1" layers={refs} />);
    const manager = screen.getByLabelText('Layer manager');
    expect(within(manager).getByText('Layers (3) — drag to reorder · toggle visibility · overlay to compare')).toBeInTheDocument();
    // Provenance descriptor + instant stat, straight from the manifest (no fetch needed for these).
    // Both chunk layers share the same capability, so the descriptor appears twice — that identity is
    // expected; assert the count rather than uniqueness.
    expect(within(manager).getAllByText(/chunk · word · size 200 — 2 units · 99.9% cov/)).toHaveLength(2);
    expect(within(manager).getByText(/qwen3 · d2560 — 3 units/)).toBeInTheDocument();
  });

  it('renders all three layers as distinct lanes simultaneously', async () => {
    render(<LayerWorkbench projectId="p1" layers={refs} />);
    const stack = screen.getByLabelText('Lane stack');
    // Two band ribbons + one embedding lane, each its own <svg role=img>.
    expect(await within(stack).findByRole('img', { name: /chunking word7 band/i })).toBeInTheDocument();
    expect(await within(stack).findByRole('img', { name: /chunking slide10 band/i })).toBeInTheDocument();
    expect(await within(stack).findByRole('img', { name: /embedding emb01 lane/i })).toBeInTheDocument();
  });

  it('toggling visibility removes a lane from the stack', async () => {
    render(<LayerWorkbench projectId="p1" layers={refs} />);
    const stack = screen.getByLabelText('Lane stack');
    // Let both band lanes resolve before mutating, so the removal assertion isn't racing a fetch.
    await within(stack).findByRole('img', { name: /chunking word7 band/i });
    await within(stack).findByRole('img', { name: /chunking slide10 band/i });
    // Hide the word7 layer from its manager row.
    fireEvent.click(screen.getByLabelText('Toggle chunking word7'));
    expect(within(stack).queryByRole('img', { name: /chunking word7 band/i })).not.toBeInTheDocument();
    // The others remain.
    expect(within(stack).getByRole('img', { name: /chunking slide10 band/i })).toBeInTheDocument();
  });

  it('overlay groups flagged layers into one shared lane', async () => {
    render(<LayerWorkbench projectId="p1" layers={refs} />);
    const stack = screen.getByLabelText('Lane stack');
    await within(stack).findByRole('img', { name: /chunking word7 band/i });
    fireEvent.click(screen.getByLabelText('Overlay chunking word7'));
    fireEvent.click(screen.getByLabelText('Overlay chunking slide10'));
    expect(screen.getByText('overlay (2)')).toBeInTheDocument();
    // The two overlaid ribbons now share the single overlay lane container. They remount on the move
    // (new parent), so re-fetch and resolve asynchronously — await rather than query synchronously.
    const overlay = screen.getByTestId('overlay-lane');
    expect(await within(overlay).findByRole('img', { name: /chunking word7 band/i })).toBeInTheDocument();
    expect(await within(overlay).findByRole('img', { name: /chunking slide10 band/i })).toBeInTheDocument();
  });

  it('opens the per-layer stats panel (instant summary + viz selector) from a manager row', async () => {
    render(<LayerWorkbench projectId="p1" layers={refs} />);
    fireEvent.click(screen.getAllByText('stats →')[0]);
    const panel = await screen.findByLabelText('Layer stats: chunking word7');
    // Instant summary — straight from the manifest, no fetch.
    expect(within(panel).getByLabelText('instant stats summary')).toBeInTheDocument();
    expect(within(panel).getByText(/size:/)).toBeInTheDocument();
    // A chunk layer offers the selectable distribution set.
    expect(within(panel).getByRole('tab', { name: 'length histogram' })).toBeInTheDocument();
  });

  it('opens two stats panels side by side for compare', async () => {
    render(<LayerWorkbench projectId="p1" layers={refs} />);
    const statsButtons = screen.getAllByText('stats →');
    fireEvent.click(statsButtons[0]);
    fireEvent.click(statsButtons[1]);
    const panels = screen.getByTestId('stats-panels');
    expect(within(panels).getAllByTestId('layer-stats-panel')).toHaveLength(2);
  });
});
