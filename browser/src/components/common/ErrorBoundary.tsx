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
          style={{
            padding: '16px',
            backgroundColor: '#fdf0f0',
            border: '1px solid #e74c3c',
            borderRadius: '4px',
            margin: '8px',
          }}
        >
          <div style={{ fontWeight: 'bold', color: '#e74c3c', marginBottom: '4px' }}>
            {label} encountered an error
          </div>
          <div style={{ fontSize: '0.85em', color: '#666', marginBottom: '8px' }}>
            {this.state.error?.message ?? 'Unknown error'}
          </div>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              padding: '4px 12px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              cursor: 'pointer',
              backgroundColor: '#fff',
            }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
