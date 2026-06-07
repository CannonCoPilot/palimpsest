/**
 * LoadingOverlay — shows track loading progress; auto-dismisses when done.
 */

import { useProjectStore } from '../../stores/projectStore';

export default function LoadingOverlay(): JSX.Element | null {
  const loadingState = useProjectStore((s) => s.loadingState);
  const loadingStep = useProjectStore((s) => s.loadingStep);

  if (loadingState !== 'loading') return null;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          padding: '24px 32px',
          backgroundColor: '#fff',
          borderRadius: '8px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
          textAlign: 'center',
        }}
      >
        <h2 style={{ margin: '0 0 8px' }}>Loading Palimpsest</h2>
        <div style={{ color: '#888' }}>{loadingStep || 'Preparing...'}</div>
      </div>
    </div>
  );
}
