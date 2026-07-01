import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SweepPanel from './SweepPanel';
import type { SweepResult, RunHeadline } from './sweep';

const RESULT: SweepResult = {
  run_id: 'abc123',
  collection_id: 'c1',
  metric: 'word_overlap',
  mode: 'high-recall',
  force_exhaustive: false,
  members: ['a', 'b'],
  n_member_pairs: 1,
  n_pairs_total: 100,
  n_candidates: 8,
  n_pruned: 92,
  prune_fraction: 0.92,
  mean_estimated_recall: 0.1,
  pairs: [
    { a: 'a', b: 'b', n_pairs_total: 100, n_candidates: 8, n_pruned: 92, prune_fraction: 0.92, estimated_recall: 0.1, dense: false },
  ],
};

const RUN: RunHeadline = {
  run_id: 'abc123',
  collection_id: 'c1',
  metric: 'word_overlap',
  mode: 'high-recall',
  force_exhaustive: false,
  members: ['a', 'b'],
  n_member_pairs: 1,
  n_pairs_total: 100,
  n_candidates: 8,
  n_pruned: 92,
  prune_fraction: 0.92,
  mean_estimated_recall: 0.1,
  progress: { pairs_total: 1, pairs_done: 1 },
};

const ok = (body: unknown) => Promise.resolve({ ok: true, json: () => Promise.resolve(body) });

function stubFetch(spy?: (url: string, init?: RequestInit) => void, opts?: { runs?: RunHeadline[]; result?: SweepResult }) {
  const runs = opts?.runs ?? [RUN];
  const result = opts?.result ?? RESULT;
  return vi.fn((url: string, init?: RequestInit) => {
    spy?.(url, init);
    const method = init?.method ?? 'GET';
    if (url.endsWith('/sweeps')) return ok({ runs });
    if (method === 'POST' && url.endsWith('/sweep')) return ok(result);
    if (method === 'DELETE') return ok({ deleted: 'abc123' });
    if (url.includes('/sweep/')) {
      return ok({ run_id: 'abc123', metric: 'word_overlap', mode: 'high-recall', force_exhaustive: false, members: ['a', 'b'], pairs: { 'a\x00b': result.pairs[0] }, progress: { pairs_total: 1, pairs_done: 1 } });
    }
    return ok({});
  });
}

const hasText = (re: RegExp) => (_: string, el: Element | null) =>
  el?.tagName === 'SPAN' && re.test(el.textContent ?? '');

describe('SweepPanel', () => {
  beforeEach(() => vi.stubGlobal('fetch', stubFetch()));
  afterEach(() => vi.unstubAllGlobals());

  it('shows the pre-run member-pair estimate and does NOT auto-run a sweep', async () => {
    const spy = vi.fn();
    vi.stubGlobal('fetch', stubFetch(spy));
    render(<SweepPanel collectionId="c1" members={['a', 'b', 'c']} />);

    // pre-run estimate = C(3,2) = 3 member pairs
    expect(screen.getByText(hasText(/member pairs to sweep/i))).toBeInTheDocument();

    // the run list loads, but no sweep is POSTed until the user asks
    await waitFor(() => expect(spy.mock.calls.some(([u]) => String(u).endsWith('/sweeps'))).toBe(true));
    const postCalls = spy.mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method === 'POST');
    expect(postCalls.length).toBe(0);
  });

  it('running a sweep POSTs the dial params and renders pruned counts + a per-pair row', async () => {
    const spy = vi.fn();
    vi.stubGlobal('fetch', stubFetch(spy));
    render(<SweepPanel collectionId="c1" members={['a', 'b']} />);

    fireEvent.click(screen.getByRole('button', { name: /run sweep/i }));
    await screen.findByText(/a ↔ b/); // the per-pair row rendered from the result

    const post = spy.mock.calls.find(([u, init]) => (init as RequestInit | undefined)?.method === 'POST' && String(u).endsWith('/sweep'));
    expect(post).toBeTruthy();
    expect(JSON.parse((post![1] as RequestInit).body as string)).toMatchObject({ metric: 'word_overlap', mode: 'high-recall', force_exhaustive: false });
    expect(screen.getAllByText(/92\.00%/).length).toBeGreaterThan(0); // prune fraction
  });

  it('renders an unmeasured recall as n/a, never a fabricated number', async () => {
    const nullResult: SweepResult = { ...RESULT, mean_estimated_recall: null, pairs: [{ ...RESULT.pairs[0], estimated_recall: null }] };
    vi.stubGlobal('fetch', stubFetch(undefined, { runs: [], result: nullResult }));
    render(<SweepPanel collectionId="c1" members={['a', 'b']} />);

    fireEvent.click(screen.getByRole('button', { name: /run sweep/i }));
    await screen.findByText(/a ↔ b/);
    expect(screen.getAllByText('n/a').length).toBeGreaterThan(0);
  });

  it('the run manager lists a persisted run and delete calls DELETE', async () => {
    const spy = vi.fn();
    vi.stubGlobal('fetch', stubFetch(spy));
    render(<SweepPanel collectionId="c1" members={['a', 'b']} />);

    await screen.findByText('abc123'); // the run_id in the manager table
    fireEvent.click(screen.getByText('delete'));
    await waitFor(() => expect(spy.mock.calls.some(([u, init]) => (init as RequestInit | undefined)?.method === 'DELETE' && String(u).includes('/sweep/abc123'))).toBe(true));
  });
});
