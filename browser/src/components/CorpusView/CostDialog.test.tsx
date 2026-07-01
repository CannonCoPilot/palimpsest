import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CostDialog from './CostDialog';

describe('CostDialog', () => {
  it('renders its title + cost body and fires confirm / cancel (never auto-runs)', () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <CostDialog title="Embed the query" confirmLabel="Embed & probe" onConfirm={onConfirm} onCancel={onCancel}>
        <p>This calls the embedding service.</p>
      </CostDialog>,
    );
    expect(screen.getByRole('dialog', { name: 'Embed the query' })).toBeInTheDocument();
    expect(screen.getByText('This calls the embedding service.')).toBeInTheDocument();
    // nothing runs on mount
    expect(onConfirm).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Embed & probe' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('disables both buttons while busy', () => {
    render(
      <CostDialog title="t" busy onConfirm={() => {}} onCancel={() => {}}>
        <p>x</p>
      </CostDialog>,
    );
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /working/i })).toBeDisabled();
  });
});
