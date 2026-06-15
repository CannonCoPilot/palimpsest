import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import HelpOverlay from './HelpOverlay';
import { useViewStore } from '../../stores/viewStore';

describe('HelpOverlay (W4 dialog semantics)', () => {
  beforeEach(() => {
    useViewStore.setState({ helpOpen: false });
  });

  it('renders nothing when help is closed', () => {
    const { container } = render(<HelpOverlay />);
    expect(container.firstChild).toBeNull();
  });

  it('puts role=dialog + aria-modal on the focused inner box, not the backdrop', () => {
    useViewStore.setState({ helpOpen: true });
    render(<HelpOverlay />);
    const dialog = screen.getByRole('dialog');
    // W4: the role belongs on the inner content box, NOT the full-screen backdrop.
    expect(dialog.className).not.toContain('inset-0');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-label', 'Keyboard shortcuts');
    // The component focuses the dialog on open — the role element being the focus
    // target is exactly what the fix established.
    expect(dialog).toHaveFocus();
  });

  it('lists documented keyboard shortcuts', () => {
    useViewStore.setState({ helpOpen: true });
    render(<HelpOverlay />);
    expect(screen.getByText('Keyboard Shortcuts')).toBeInTheDocument();
    expect(screen.getByText('Open search')).toBeInTheDocument();
  });
});
