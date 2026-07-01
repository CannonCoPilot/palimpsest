import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CongruenceBadge from './CongruenceBadge';

const CONGRUENT = {
  metric: 'word_overlap', needs_embedding: false,
  members: ['alpha', 'beta'],
  keys: { alpha: 'tokens:word_overlap', beta: 'tokens:word_overlap' },
  groups: { 'tokens:word_overlap': ['alpha', 'beta'] },
  missing: [], all_congruent: true, reconcile_hint: null,
};

const INCONGRUENT = {
  metric: 'cosine', needs_embedding: true,
  members: ['alpha', 'beta'],
  keys: { alpha: null, beta: null },
  groups: {}, missing: ['alpha', 'beta'],
  all_congruent: false,
  reconcile_hint: 're-embed members into a common space (same model + params + dim) to compare on this metric',
};

function mockFetch(report: object) {
  return vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(report) });
}

describe('CongruenceBadge', () => {
  beforeEach(() => vi.stubGlobal('fetch', mockFetch(INCONGRUENT)));
  afterEach(() => vi.unstubAllGlobals());

  it('flags an incongruent embedding metric and routes to reconcile', async () => {
    const onReconcile = vi.fn();
    render(<CongruenceBadge collectionId="c1" onReconcile={onReconcile} />);

    await waitFor(() => expect(screen.getByText('incongruent')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('status'));  // open the detail popover

    // per-member keys show the missing layer, and the reconcile action is offered
    expect(screen.getAllByText('missing layer').length).toBe(2);
    const reconcile = screen.getByText('Reconcile…');
    fireEvent.click(reconcile);
    expect(onReconcile).toHaveBeenCalledOnce();
  });

  it('shows congruent for a token metric (no reconcile offered)', async () => {
    vi.stubGlobal('fetch', mockFetch(CONGRUENT));
    render(<CongruenceBadge collectionId="c1" />);
    await waitFor(() => expect(screen.getByText('congruent')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('status'));
    expect(screen.queryByText('Reconcile…')).not.toBeInTheDocument();
  });
});
