import { useState, useCallback } from 'react';
import { useViewStore, type CoordinateSystem } from '../../stores/viewStore';
import { useProjectStore } from '../../stores/projectStore';
import { Tooltip } from '../common/Tooltip';

const COORD_LABELS: Record<CoordinateSystem, string> = {
  paragraph: '¶',
  character: 'chr',
  section: '§',
};

export default function NavigationToolbar() {
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const referenceText = useProjectStore((s) => s.referenceText);
  const tracks = useProjectStore((s) => s.tracks);
  const selectedParagraphIndex = useViewStore((s) => s.selectedParagraphIndex);
  const setSelectedParagraphIndex = useViewStore((s) => s.setSelectedParagraphIndex);
  const requestScrollToParagraph = useViewStore((s) => s.requestScrollToParagraph);
  const zoomLevel = useViewStore((s) => s.zoomLevel);
  const zoomIn = useViewStore((s) => s.zoomIn);
  const zoomOut = useViewStore((s) => s.zoomOut);
  const coordSystem = useViewStore((s) => s.coordinateSystem);
  const setCoordSystem = useViewStore((s) => s.setCoordinateSystem);

  const [posInput, setPosInput] = useState('');
  const maxPara = paragraphs.length;
  const currentPara = selectedParagraphIndex ?? 0;
  const sectionCount = (tracks['sections'] ?? []).length;

  const currentPosition = (() => {
    switch (coordSystem) {
      case 'character':
        return paragraphs[currentPara]?.start ?? 0;
      case 'section': {
        const sections = tracks['sections'] ?? [];
        const paraStart = paragraphs[currentPara]?.start ?? 0;
        const secIdx = sections.findLastIndex((s) => {
          const sel = s.target.selector;
          return sel.start != null && sel.start <= paraStart;
        });
        return Math.max(0, secIdx) + 1;
      }
      default:
        return currentPara + 1;
    }
  })();

  const maxPosition = coordSystem === 'character' ? referenceText.length
    : coordSystem === 'section' ? sectionCount
    : maxPara;

  const navigateTo = useCallback((index: number) => {
    const clamped = Math.max(0, Math.min(index, maxPara - 1));
    setSelectedParagraphIndex(clamped);
    requestScrollToParagraph(clamped);
  }, [maxPara, setSelectedParagraphIndex, requestScrollToParagraph]);

  const handlePosSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const val = parseInt(posInput, 10);
    if (isNaN(val)) return;

    if (coordSystem === 'character') {
      const paraIdx = paragraphs.findIndex((p) => p.end >= val);
      if (paraIdx >= 0) navigateTo(paraIdx);
    } else if (coordSystem === 'section') {
      const sections = tracks['sections'] ?? [];
      const sec = sections[val - 1];
      if (sec?.target.selector.start != null) {
        const paraIdx = paragraphs.findIndex((p) => p.end >= sec.target.selector.start!);
        if (paraIdx >= 0) navigateTo(paraIdx);
      }
    } else {
      if (val >= 1 && val <= maxPara) navigateTo(val - 1);
    }
    setPosInput('');
  }, [posInput, coordSystem, maxPara, paragraphs, tracks, navigateTo]);

  return (
    <div className="flex items-center gap-2">
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

      <form onSubmit={handlePosSubmit} className="flex items-center gap-1">
        <Tooltip content="Switch coordinate system" side="bottom">
          <select
            value={coordSystem}
            onChange={(e) => setCoordSystem(e.target.value as CoordinateSystem)}
            className="px-1 py-0.5 border border-[var(--color-border)] rounded-[var(--radius-md)] text-[0.75em] bg-[var(--color-bg)] cursor-pointer"
          >
            <option value="paragraph">¶ Paragraph</option>
            <option value="character">chr Offset</option>
            <option value="section">§ Section</option>
          </select>
        </Tooltip>
        <Tooltip content={`Go to ${coordSystem} position`} side="bottom">
          <input
            type="text"
            value={posInput}
            onChange={(e) => setPosInput(e.target.value)}
            placeholder={`${COORD_LABELS[coordSystem]}${currentPosition}`}
            className="w-[70px] px-1.5 py-0.5 border border-[var(--color-border)] rounded-[var(--radius-md)] text-[0.8em] text-center bg-[var(--color-bg)] focus:border-[var(--color-border-focus)] focus:outline-none"
          />
        </Tooltip>
        <span className="text-[0.7em] text-[var(--color-text-muted)]">/ {maxPosition}</span>
      </form>

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
