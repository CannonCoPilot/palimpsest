import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import AnalysesPanel, { reachRows } from './AnalysesPanel';

const ANALYSES = {
  collection_id: 'c1',
  members: ['alpha', 'beta'],
  boilerplate: {
    shared_by_all: ['the', 'and'],
    n_shared_by_all: 2,
    most_discriminative: [
      { term: 'leviathan', idf: 0.6931 },
      { term: 'seraph', idf: 0.4055 },
    ],
    vocab_size: 1200,
  },
  near_duplicate_clusters: [{ members: ['alpha', 'beta'], size: 2 }],
  diffusion: {
    non_directional_note: 'Spread is undirected: breadth across members, not who influenced whom.',
    member_reach: { alpha: 0.9, beta: 0.4 },
    component_spread_histogram: { singleton: 3, narrow: 1, broad: 0, core: 2 },
    core_fraction: 0.33,
  },
};

const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
const notFound = () => Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ detail: 'no graph' }) });

describe('reachRows', () => {
  it('sorts members by breadth descending', () => {
    const rows = reachRows({ a: 0.2, b: 0.9, c: 0.5 });
    expect(rows.map((r) => r.member)).toEqual(['b', 'c', 'a']);
  });
});

describe('AnalysesPanel', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('renders boilerplate, discriminative terms, near-dup cluster, and the non-directional caveat', async () => {
    vi.stubGlobal('fetch', vi.fn(() => ok(ANALYSES)));
    render(<AnalysesPanel collectionId="c1" />);

    await waitFor(() => expect(screen.getByText('leviathan')).toBeInTheDocument());
    expect(screen.getByText('0.6931')).toBeInTheDocument(); // IDF cell
    expect(screen.getByText(/terms shared by all/)).toBeInTheDocument();
    expect(screen.getByText(/breadth across members, not who influenced whom/)).toBeInTheDocument(); // honesty caveat
    // near-duplicate cluster members
    expect(screen.getByText('alpha · beta')).toBeInTheDocument();
  });

  it('surfaces a 404 as a build-the-graph message rather than a blank panel', async () => {
    vi.stubGlobal('fetch', vi.fn(() => notFound()));
    render(<AnalysesPanel collectionId="c1" />);
    await waitFor(() => expect(screen.getByText(/Build the corpus graph first/)).toBeInTheDocument());
  });
});
