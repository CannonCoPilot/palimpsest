/**
 * HelpOverlay — keyboard shortcut reference, toggled by '?'.
 */

import { useViewStore } from '../../stores/viewStore';

const SHORTCUTS = [
  { key: 'j / ↓', action: 'Next paragraph' },
  { key: 'k / ↑', action: 'Previous paragraph' },
  { key: 'Ctrl+F / /', action: 'Open search' },
  { key: 'Enter', action: 'Next search match' },
  { key: 'Shift+Enter', action: 'Previous search match' },
  { key: '[ / ]', action: 'Previous / next search match' },
  { key: 'Ctrl+=', action: 'Zoom in (work → chapter → paragraph → sentence)' },
  { key: 'Ctrl+-', action: 'Zoom out' },
  { key: '1–9', action: 'Toggle track by number' },
  { key: '0', action: 'Show / hide all tracks' },
  { key: 'd', action: 'Toggle TextHiC dotplot' },
  { key: '?', action: 'Toggle this help' },
  { key: 'Escape', action: 'Close search / deselect' },
];

export default function HelpOverlay(): JSX.Element | null {
  const helpOpen = useViewStore((s) => s.helpOpen);
  const toggleHelp = useViewStore((s) => s.toggleHelp);

  if (!helpOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={toggleHelp}
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '24px',
          maxWidth: '420px',
          width: '90%',
          boxShadow: '0 4px 24px rgba(0,0,0,0.2)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontWeight: 'bold', fontSize: '1.1em', marginBottom: '16px' }}>
          Keyboard Shortcuts
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <tbody>
            {SHORTCUTS.map((s) => (
              <tr key={s.key} style={{ borderBottom: '1px solid #f0f0f0' }}>
                <td style={{ padding: '6px 8px', width: '120px' }}>
                  <kbd
                    style={{
                      padding: '2px 6px',
                      backgroundColor: '#f5f5f5',
                      border: '1px solid #ddd',
                      borderRadius: '3px',
                      fontSize: '0.85em',
                      fontFamily: 'monospace',
                    }}
                  >
                    {s.key}
                  </kbd>
                </td>
                <td style={{ padding: '6px 8px', fontSize: '0.9em', color: '#333' }}>{s.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: '16px', textAlign: 'right' }}>
          <button
            onClick={toggleHelp}
            style={{
              padding: '6px 16px',
              backgroundColor: '#3498db',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
