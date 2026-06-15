import { useEffect, useRef } from 'react';
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
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!helpOpen) return;
    const dialog = dialogRef.current;
    if (dialog) dialog.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { toggleHelp(); return; }
      if (e.key !== 'Tab') return;
      const focusable = dialog?.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (!focusable || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [helpOpen, toggleHelp]);

  if (!helpOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-[var(--z-overlay)]"
      onClick={toggleHelp}
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label="Keyboard shortcuts"
        className="bg-[var(--color-bg)] rounded-[var(--radius-lg)] p-6 max-w-[420px] w-[90%] shadow-[0_4px_24px_rgba(0,0,0,0.2)] outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="font-bold text-[1.1em] mb-4">
          Keyboard Shortcuts
        </div>
        <table className="w-full border-collapse">
          <tbody>
            {SHORTCUTS.map((s) => (
              <tr key={s.key} className="border-b border-[var(--color-border-subtle)]">
                <td className="px-2 py-[6px] w-[120px]">
                  <kbd className="px-[6px] py-[2px] bg-[#f5f5f5] border border-[var(--color-border)] rounded-[3px] text-[0.85em] font-mono">
                    {s.key}
                  </kbd>
                </td>
                <td className="px-2 py-[6px] text-[0.9em] text-[#333]">{s.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-4 text-right">
          <button
            onClick={toggleHelp}
            className="px-4 py-[6px] bg-[var(--color-primary)] text-[var(--color-text-inverted)] border-none rounded-[var(--radius-md)] cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
