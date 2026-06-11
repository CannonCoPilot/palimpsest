import { useState, useCallback } from 'react';
import { useViewStore } from '../../stores/viewStore';
import { useProjectStore } from '../../stores/projectStore';
import { Tooltip } from '../common/Tooltip';

export default function NavigationToolbar() {
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const selectedParagraphIndex = useViewStore((s) => s.selectedParagraphIndex);
  const setSelectedParagraphIndex = useViewStore((s) => s.setSelectedParagraphIndex);
  const requestScrollToParagraph = useViewStore((s) => s.requestScrollToParagraph);
  const zoomLevel = useViewStore((s) => s.zoomLevel);
  const zoomIn = useViewStore((s) => s.zoomIn);
  const zoomOut = useViewStore((s) => s.zoomOut);

  const [posInput, setPosInput] = useState('');
  const maxPara = paragraphs.length;
  const currentPara = selectedParagraphIndex ?? 0;

  const navigateTo = useCallback((index: number) => {
    const clamped = Math.max(0, Math.min(index, maxPara - 1));
    setSelectedParagraphIndex(clamped);
    requestScrollToParagraph(clamped);
  }, [maxPara, setSelectedParagraphIndex, requestScrollToParagraph]);

  const handlePosSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const val = parseInt(posInput, 10);
    if (!isNaN(val) && val >= 1 && val <= maxPara) {
      navigateTo(val - 1);
      setPosInput('');
    }
  }, [posInput, maxPara, navigateTo]);

  return (
    <div className="flex items-center gap-2">
      {/* Navigation arrows */}
      <div className="flex items-center gap-0.5">
        <Tooltip content="Previous paragraph (k / ↑)" side="bottom">
          <button
            onClick={() => navigateTo(currentPara - 1)}
            disabled={currentPara <= 0}
            className="px-1.5 py-0.5 border border-[var(--color-border)] rounded-l-[var(--radius-md)] bg-[var(--color-bg)] text-[0.85em] cursor-pointer disabled:text-[#ccc] disabled:cursor-default hover:bg-[var(--color-bg-muted)]"
          >
            ◀
          </button>
        </Tooltip>
        <Tooltip content="Next paragraph (j / ↓)" side="bottom">
          <button
            onClick={() => navigateTo(currentPara + 1)}
            disabled={currentPara >= maxPara - 1}
            className="px-1.5 py-0.5 border border-[var(--color-border)] rounded-r-[var(--radius-md)] bg-[var(--color-bg)] text-[0.85em] cursor-pointer disabled:text-[#ccc] disabled:cursor-default hover:bg-[var(--color-bg-muted)] -ml-px"
          >
            ▶
          </button>
        </Tooltip>
      </div>

      {/* Position input */}
      <form onSubmit={handlePosSubmit} className="flex items-center gap-1">
        <Tooltip content="Go to paragraph number" side="bottom">
          <input
            type="text"
            value={posInput}
            onChange={(e) => setPosInput(e.target.value)}
            placeholder={`¶${currentPara + 1}`}
            className="w-[60px] px-1.5 py-0.5 border border-[var(--color-border)] rounded-[var(--radius-md)] text-[0.8em] text-center bg-[var(--color-bg)] focus:border-[var(--color-border-focus)] focus:outline-none"
          />
        </Tooltip>
        <span className="text-[0.7em] text-[var(--color-text-muted)]">/ {maxPara}</span>
      </form>

      {/* Zoom controls */}
      <div className="flex items-center gap-0.5 border border-[var(--color-border)] rounded-[var(--radius-md)] p-0.5">
        <Tooltip content="Zoom out (Ctrl+-)" side="bottom">
          <button
            onClick={zoomOut}
            disabled={zoomLevel === 'work'}
            className="px-2 py-0.5 border-none bg-transparent text-[0.9em] disabled:text-[#ccc] disabled:cursor-default text-[#555] cursor-pointer"
          >
            −
          </button>
        </Tooltip>
        <Tooltip content={`Current zoom: ${zoomLevel}`} side="bottom">
          <span className="text-[0.75em] text-[var(--color-text-secondary)] min-w-[65px] text-center select-none">
            {zoomLevel}
          </span>
        </Tooltip>
        <Tooltip content="Zoom in (Ctrl+=)" side="bottom">
          <button
            onClick={zoomIn}
            disabled={zoomLevel === 'sentence'}
            className="px-2 py-0.5 border-none bg-transparent text-[0.9em] disabled:text-[#ccc] disabled:cursor-default text-[#555] cursor-pointer"
          >
            +
          </button>
        </Tooltip>
      </div>
    </div>
  );
}
