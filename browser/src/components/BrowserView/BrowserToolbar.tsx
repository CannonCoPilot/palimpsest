import { useCallback, useState } from 'react';
import { useBrowserStore } from '../../stores/browserStore';
import { useProjectStore } from '../../stores/projectStore';
import { Tooltip } from '../common/Tooltip';

export default function BrowserToolbar() {
  const { viewStart, viewEnd, totalChars, zoomAroundCenter, zoomToFull, pan, setViewport, toggleDrawer } = useBrowserStore();
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const [jumpInput, setJumpInput] = useState('');

  const viewWidth = viewEnd - viewStart;
  const rawPct = totalChars > 0 ? (viewWidth / totalChars) * 100 : 100;
  const zoomLabel = rawPct >= 1 ? `${Math.round(rawPct)}%` : rawPct >= 0.1 ? `${rawPct.toFixed(1)}%` : '<0.1%';

  const handleJump = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== 'Enter') return;
    const val = jumpInput.trim();
    if (!val) return;

    if (val.startsWith('¶') || val.startsWith('p')) {
      const paraIdx = parseInt(val.slice(1), 10);
      if (!isNaN(paraIdx) && paraIdx >= 0 && paraIdx < paragraphs.length) {
        const para = paragraphs[paraIdx];
        setViewport(para.start, para.end);
      }
    } else {
      const charPos = parseInt(val, 10);
      if (!isNaN(charPos) && charPos >= 0 && charPos <= totalChars) {
        const halfView = viewWidth / 2;
        setViewport(charPos - halfView, charPos + halfView);
      }
    }
    setJumpInput('');
  }, [jumpInput, paragraphs, totalChars, viewWidth, setViewport]);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)] text-[0.8em] font-[var(--font-sans)]">
      <Tooltip content="Show/hide track drawer" side="bottom">
        <button
          onClick={toggleDrawer}
          className="px-2 py-0.5 rounded border border-[var(--color-border)] bg-[var(--color-bg)] cursor-pointer hover:bg-[var(--color-bg-muted)]"
        >
          ☰ Tracks
        </button>
      </Tooltip>

      <span className="text-[var(--color-text-muted)] mx-1">|</span>

      <Tooltip content="Zoom out (×2)" side="bottom">
        <button onClick={() => zoomAroundCenter(2)} className="px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">−</button>
      </Tooltip>
      <span className="min-w-[50px] text-center text-[var(--color-text-secondary)]">
        {zoomLabel}
      </span>
      <Tooltip content="Zoom in (×2)" side="bottom">
        <button onClick={() => zoomAroundCenter(0.5)} className="px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">+</button>
      </Tooltip>
      <Tooltip content="Zoom to full document" side="bottom">
        <button onClick={zoomToFull} className="px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.85em]">⊡</button>
      </Tooltip>

      <span className="text-[var(--color-text-muted)] mx-1">|</span>

      <Tooltip content="Pan left" side="bottom">
        <button onClick={() => pan(-viewWidth * 0.3)} className="px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">◀</button>
      </Tooltip>
      <Tooltip content="Pan right" side="bottom">
        <button onClick={() => pan(viewWidth * 0.3)} className="px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">▶</button>
      </Tooltip>

      <span className="text-[var(--color-text-muted)] mx-1">|</span>

      <span className="text-[var(--color-text-secondary)] font-[var(--font-mono)] text-[0.9em]">
        {Math.round(viewStart).toLocaleString()} – {Math.round(viewEnd).toLocaleString()}
      </span>

      <Tooltip content="Jump to position (e.g., 5000 or ¶42)" side="bottom">
        <input
          type="text"
          value={jumpInput}
          onChange={(e) => setJumpInput(e.target.value)}
          onKeyDown={handleJump}
          placeholder="Jump to..."
          className="w-[80px] px-1.5 py-0.5 border border-[var(--color-border)] rounded text-[0.9em] font-[var(--font-mono)]"
        />
      </Tooltip>

      <span className="ml-auto text-[var(--color-text-muted)]">
        {totalChars.toLocaleString()} chars · Drag to pan · Ctrl+scroll to zoom
      </span>
    </div>
  );
}
