import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { IntegrityBadge } from './IntegrityBadge';
import { ProfileDashboard } from './ProfileDashboard';

describe('IntegrityBadge (P4 substrate report)', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('runs GET /integrity and shows green + the per-invariant breakdown', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        framing: 'descriptive', all_green: true,
        invariants: [
          { name: 'offset-monotonic', status: 'ok' },
          { name: 'analyzable-bridge', status: 'ok' },
        ],
        summary: { paragraph_count: 12, section_count: 3, masked_ratio: 0.04 },
      }),
    })));
    render(<IntegrityBadge projectId="p1" />);
    fireEvent.click(screen.getByLabelText('Substrate integrity'));
    expect(await screen.findByText('integrity ✓')).toBeInTheDocument();
    expect(screen.getByText('offset-monotonic')).toBeInTheDocument();
    expect(screen.getByText(/12 paragraphs · 3 sections/)).toBeInTheDocument();
  });

  it('surfaces a violation count when an invariant fails', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        framing: 'descriptive', all_green: false,
        invariants: [{ name: 'encoding-sanity', status: 'violation', detail: 'NFD found' }],
        summary: { paragraph_count: 1, section_count: 0, masked_ratio: 0 },
      }),
    })));
    render(<IntegrityBadge projectId="p1" />);
    fireEvent.click(screen.getByLabelText('Substrate integrity'));
    expect(await screen.findByText('integrity: 1 violation(s)')).toBeInTheDocument();
    expect(screen.getByText(/NFD found/)).toBeInTheDocument();
  });
});

describe('ProfileDashboard (P4 text profile)', () => {
  afterEach(() => vi.unstubAllGlobals());

  const profile = {
    metadata: {
      framing: 'descriptive',
      caveats: ['Descriptive only; not inferential.'],
      report: {
        counts: { tokens: 10215, types: 2904 },
        ttr: 0.284, mattr: 0.71, mtld: 88.2, yules_k: 112.4, zipf_slope: -1.03,
      },
      distributions: {
        word_length: { edges: [1, 2, 3, 4], counts: [10, 40, 20], n: 70, mean: 4.2, median: 4, min: 1, max: 12 },
        sentence_length: { edges: [1, 5, 10], counts: [30, 15], n: 45, mean: 12.1, median: 11, min: 2, max: 40 },
      },
    },
  };

  it('renders summary metrics and a distribution chart per histogram', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(profile) })));
    render(<ProfileDashboard projectId="p1" />);
    const panel = await screen.findByLabelText('Text profile');
    expect(within(panel).getByText('10215')).toBeInTheDocument(); // tokens
    expect(within(panel).getByText('0.284')).toBeInTheDocument(); // TTR
    // One <svg> per distribution, drawn from numpy counts.
    expect(within(panel).getByRole('img', { name: /word length distribution, 3 bins/i })).toBeInTheDocument();
    expect(within(panel).getByRole('img', { name: /sentence length distribution, 2 bins/i })).toBeInTheDocument();
  });

  it('shows an honest "run the profile track" message when absent (404)', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: false, status: 404 })));
    render(<ProfileDashboard projectId="p1" />);
    expect(await screen.findByText(/No profile computed yet/i)).toBeInTheDocument();
  });
});
