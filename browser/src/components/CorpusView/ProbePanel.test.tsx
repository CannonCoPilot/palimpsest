import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ProbePanel from './ProbePanel';

const PROBE_RESULT = {
  collection_id: 'c1',
  metric: 'cosine',
  congruence_key: 'k',
  dim: 4,
  k: 10,
  per_member_k: null,
  members_searched: ['alpha', 'beta'],
  n_candidates: 2,
  results: [
    { project_id: 'alpha', label: 'emb', chunk_index: 3, similarity: 0.9123, text: 'in the beginning' },
    { project_id: 'beta', label: 'emb', chunk_index: 7, similarity: 0.8011, text: 'and the word' },
  ],
};

function stubFetch(spy?: (url: string, init?: RequestInit) => void, opts?: { status?: number }) {
  const status = opts?.status ?? 200;
  return vi.fn((url: string, init?: RequestInit) => {
    spy?.(url, init);
    if (init?.method === 'POST' && url.endsWith('/probe')) {
      if (status !== 200) return Promise.resolve({ ok: false, status, json: () => Promise.resolve({ detail: 'incongruent cohort' }) });
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(PROBE_RESULT) });
    }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
  });
}

const postCalls = (spy: ReturnType<typeof vi.fn>) =>
  spy.mock.calls.filter(([u, init]) => (init as RequestInit | undefined)?.method === 'POST' && String(u).endsWith('/probe'));

describe('ProbePanel', () => {
  beforeEach(() => vi.stubGlobal('fetch', stubFetch()));
  afterEach(() => vi.unstubAllGlobals());

  it('ref mode probes an existing passage directly and ranks the results', async () => {
    const spy = vi.fn();
    vi.stubGlobal('fetch', stubFetch(spy));
    render(<ProbePanel collectionId="c1" members={['alpha', 'beta']} />);

    fireEvent.click(screen.getByRole('button', { name: /run probe/i }));
    await screen.findByText('in the beginning');

    const post = postCalls(spy)[0];
    expect(post).toBeTruthy();
    expect(JSON.parse((post![1] as RequestInit).body as string)).toMatchObject({ ref_project: 'alpha', ref_chunk: 0, metric: 'cosine' });
  });

  it('text mode is gated behind the cost dialog and never auto-runs', async () => {
    const spy = vi.fn();
    vi.stubGlobal('fetch', stubFetch(spy));
    render(<ProbePanel collectionId="c1" members={['alpha', 'beta']} />);

    fireEvent.click(screen.getByRole('tab', { name: /text query/i }));
    fireEvent.change(screen.getByPlaceholderText(/query text/i), { target: { value: 'seraph' } });
    fireEvent.change(screen.getByPlaceholderText('provider'), { target: { value: 'mlx' } });
    fireEvent.change(screen.getByPlaceholderText('endpoint'), { target: { value: 'http://x/embed' } });
    fireEvent.change(screen.getByPlaceholderText('model'), { target: { value: 'qwen' } });

    fireEvent.click(screen.getByRole('button', { name: /run probe/i }));
    // dialog is up, but the embed has NOT fired yet
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(postCalls(spy).length).toBe(0);

    fireEvent.click(screen.getByRole('button', { name: /embed & probe/i }));
    await waitFor(() => expect(postCalls(spy).length).toBe(1));
    expect(JSON.parse((postCalls(spy)[0][1] as RequestInit).body as string)).toMatchObject({ q: 'seraph', provider: 'mlx', model: 'qwen' });
  });

  it('surfaces a 409 incongruence as a reconcile pointer, not a silent empty result', async () => {
    vi.stubGlobal('fetch', stubFetch(undefined, { status: 409 }));
    render(<ProbePanel collectionId="c1" members={['alpha', 'beta']} />);
    fireEvent.click(screen.getByRole('button', { name: /run probe/i }));
    await screen.findByText(/reconcile them first/i);
  });
});
