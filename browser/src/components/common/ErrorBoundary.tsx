/**
 * ErrorBoundary — catches render errors in child components.
 * Shows an error message with recovery options instead of crashing the whole app.
 */

import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallbackLabel?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render(): ReactNode {
    if (this.state.hasError) {
      const label = this.props.fallbackLabel || 'Component';
      return (
        <div
          role="alert"
          className="p-4 bg-[var(--color-danger-subtle)] border border-[var(--color-danger)] rounded m-2"
        >
          <div className="font-bold text-[var(--color-danger)] mb-1">
            {label} encountered an error
          </div>
          <div className="text-[0.85em] text-[var(--color-text-secondary)] mb-2">
            {this.state.error?.message ?? 'Unknown error'}
          </div>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-3 py-1 border border-[var(--color-border)] rounded cursor-pointer bg-[var(--color-bg)] hover:bg-[var(--color-bg-muted)]"
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
