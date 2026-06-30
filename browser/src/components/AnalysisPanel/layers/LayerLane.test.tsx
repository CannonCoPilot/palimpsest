import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LayerLane } from './LayerLane';
import { laneKind, collectLayers, type LayerStatus } from './types';

// Route the global fetch by URL: band layers read a static manifest (JSON with segment_offsets);
// embedding lanes read the P3 endpoint (LE float32 bytes). Everything else 404s.
function stubFetch(opts?: { segments?: [number, number][]; lane?: number[] }) {
  const segments = opts?.segments ?? [[0, 100], [100, 250], [250, 400]];
  const lane = opts?.lane ?? [0.1, 0.4, 0.9];
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.includes('/signals/')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ segment_offsets: segments }) });
    }
    if (url.includes('/lane')) {
      return Promise.resolve({ ok: true, arrayBuffer: () => Promise.resolve(new Float32Array(lane).buffer) });
    }
    return Promise.resolve({ ok: false, status: 404 });
  }));
}

const bandLayer = (label: string, view = 'chunk-band'): LayerStatus => ({
  label, status: 'computed',
  capability: { kind: 'chunk', mode: 'word', size: 200 },
  stats: { count: 3 },
  rendering: { track_view: view, overviewBarRendering: { type: view, color: '#6366F1' } },
});

const embeddingLayer = (label: string): LayerStatus => ({
  label, status: 'computed',
  capability: { kind: 'embedding', dim: 2560 },
  stats: { count: 3, dim: 2560 },
  rendering: { track_view: 'embedding-lane', encoding: 'nn-density', projection_ref: `/x/${label}/projection` },
});

describe('laneKind family dispatch', () => {
  it('maps every *-band view to the one band renderer', () => {
    expect(laneKind({ track_view: 'chunk-band' })).toBe('band');
    expect(laneKind({ track_view: 'repeat-band' })).toBe('band');
    // The whole point of FR-13 plural-safety: a brand-new band type the frontend has never seen
    // still routes to the band renderer with no code change.
    expect(laneKind({ track_view: 'sentence-band' })).toBe('band');
  });
  it('maps embedding-lane to its own renderer and unknowns to a placeholder', () => {
    expect(laneKind({ track_view: 'embedding-lane' })).toBe('embedding-lane');
    expect(laneKind({ track_view: 'galaxy-brain' })).toBe('unknown');
    expect(laneKind(null)).toBe('unknown');
  });
});

describe('collectLayers', () => {
  it('flattens track rows into (trackName, layer) refs and skips layerless tracks', () => {
    const refs = collectLayers([
      { name: 'chunking', layers: [bandLayer('aaa'), bandLayer('bbb')] },
      { name: 'sentiment' }, // non-layer-keyed track — contributes nothing
      { name: 'embedding', layers: [embeddingLayer('ccc')] },
    ]);
    expect(refs.map((r) => `${r.trackName}:${r.layer.label}`)).toEqual([
      'chunking:aaa', 'chunking:bbb', 'embedding:ccc',
    ]);
  });
});

describe('LayerLane dispatch (renders by descriptor, not label)', () => {
  beforeEach(() => stubFetch());
  afterEach(() => vi.unstubAllGlobals());

  it('renders a chunk-band layer as a segment ribbon', async () => {
    render(<LayerLane projectId="p1" trackName="chunking" layer={bandLayer('aaa')} />);
    const svg = await screen.findByRole('img', { name: /chunking aaa band, 3 segments/i });
    expect(svg).toHaveAttribute('data-track-view', 'chunk-band');
    // One <rect> background + 3 segment rects.
    expect(svg.querySelectorAll('rect').length).toBe(4);
  });

  it('PLURAL SAFETY: a second chunk layer renders through the identical code path', async () => {
    // This is the explicit FR-13 proof — the "fifth chunk layer renders with no new branch". Two
    // distinct labels, same track_view, must both produce a band ribbon with no per-label code.
    const { rerender } = render(<LayerLane projectId="p1" trackName="chunking" layer={bandLayer('aaa')} />);
    expect((await screen.findByRole('img', { name: /chunking aaa band/i }))
      .getAttribute('data-track-view')).toBe('chunk-band');
    rerender(<LayerLane projectId="p1" trackName="chunking" layer={bandLayer('zzz')} />);
    expect((await screen.findByRole('img', { name: /chunking zzz band/i }))
      .getAttribute('data-track-view')).toBe('chunk-band');
  });

  it('renders a NEW band type (repeat-band) with no new code path', async () => {
    render(<LayerLane projectId="p1" trackName="repeat" layer={bandLayer('rep', 'repeat-band')} />);
    const svg = await screen.findByRole('img', { name: /repeat rep band/i });
    expect(svg).toHaveAttribute('data-track-view', 'repeat-band');
  });

  it('renders an embedding-lane layer as a colored strip', async () => {
    render(<LayerLane projectId="p1" trackName="embedding" layer={embeddingLayer('ccc')} />);
    const svg = await screen.findByRole('img', { name: /embedding ccc lane \(nn-density\), 3 chunks/i });
    expect(svg).toHaveAttribute('data-track-view', 'embedding-lane');
    expect(svg.querySelectorAll('rect').length).toBe(4); // background + 3 chunk cells
  });

  it('renders an honest placeholder for an unknown track_view (no crash, no silent blank)', async () => {
    const weird: LayerStatus = { label: 'q', status: 'computed', rendering: { track_view: 'hologram' } };
    render(<LayerLane projectId="p1" trackName="future" layer={weird} />);
    expect(await screen.findByText(/no lane renderer for "hologram"/i)).toBeInTheDocument();
  });
});
