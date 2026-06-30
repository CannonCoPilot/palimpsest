import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// vi.mock factories are hoisted above imports, so the mock state must exist before
// the component imports the stores — vi.hoisted is the sanctioned way to provide it.
const mocks = vi.hoisted(() => {
  const rec = (queryStart: number, targetStart: number, score: number) => ({
    queryId: 'q1', targetId: 't1',
    queryStart, queryEnd: queryStart + 2,
    targetStart, targetEnd: targetStart + 2,
    score, pValue: 1 / score, method: 'semantic', strand: '+' as const, identity: 0.9,
  });
  return {
    comparisonState: {
      crossSimilarityMatrix: new Float32Array(12).fill(0.5), // n*m = 3*4
      crossSimilarityDims: [3, 4] as [number, number],
      loadCrossMatrix: () => {},
      alignmentRecords: [rec(0, 0, 10), rec(4, 5, 50), rec(8, 9, 90)],
    },
    projectState: {
      activeProjectId: 'q1',
      secondaryProjectId: 't1',
      projects: {
        q1: { metadata: { title: 'Query' } },
        t1: { metadata: { title: 'Target' } },
      },
    },
  };
});

vi.mock('../../stores/comparisonStore', () => ({
  useComparisonStore: (sel: (s: unknown) => unknown) => sel(mocks.comparisonState),
}));
vi.mock('../../stores/projectStore', () => ({
  useProjectStore: (sel: (s: unknown) => unknown) => sel(mocks.projectState),
  getActiveProject: (s: { projects: Record<string, unknown>; activeProjectId: string }) =>
    s.projects[s.activeProjectId],
  getSecondaryProject: (s: { projects: Record<string, unknown>; secondaryProjectId: string }) =>
    s.projects[s.secondaryProjectId],
}));

import ComparativeDotplot from './ComparativeDotplot';

describe('ComparativeDotplot — C2 controls', () => {
  it('renders the palette switcher with blues + viridis options', () => {
    render(<ComparativeDotplot />);
    const select = screen.getByRole('combobox', { name: /palette/i }) as HTMLSelectElement;
    expect(select.value).toBe('blues');
    expect(screen.getByRole('option', { name: 'viridis' })).toBeInTheDocument();
    fireEvent.change(select, { target: { value: 'viridis' } });
    expect(select.value).toBe('viridis');
  });

  it('score-threshold slider filters the shown/total count (FR-40)', () => {
    render(<ComparativeDotplot />);
    // scores are [10, 50, 90] → default threshold 0 shows all three
    expect(screen.getByText('3/3')).toBeInTheDocument();
    const slider = screen.getByRole('slider') as HTMLInputElement;
    expect(slider.min).toBe('10');
    expect(slider.max).toBe('90');
    fireEvent.change(slider, { target: { value: '60' } });
    // only the score-90 record clears a cutoff of 60
    expect(screen.getByText('1/3')).toBeInTheDocument();
  });

  it('PAF link targets export.paf and gains min_score only when thresholded', () => {
    render(<ComparativeDotplot />);
    const link = screen.getByRole('link', { name: 'PAF' });
    // default threshold (0) is below the score floor (10) → unfiltered export
    expect(link.getAttribute('href')).toBe('/api/alignment/q1/t1/export.paf');
    fireEvent.change(screen.getByRole('slider'), { target: { value: '60' } });
    expect(link.getAttribute('href')).toBe('/api/alignment/q1/t1/export.paf?min_score=60');
  });
});
