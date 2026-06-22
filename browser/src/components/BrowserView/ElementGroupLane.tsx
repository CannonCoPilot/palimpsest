import { useEffect, useRef, useState, memo } from 'react';
import { useBrowserStore, LANE_HEIGHTS, type LaneDisplayMode } from '../../stores/browserStore';
import { useElementVisibilityStore } from '../../stores/elementVisibilityStore';
import type { ElementGroupData } from '../../utils/maskTypeGroups';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';

const ROW_H = 18; // per-type sub-row height in 'detail' mode
const MIN_DETAIL_H = 22; // keep the header (and its dropdown) reachable even if all types hidden

const GROUP_MODE_OPTIONS: { mode: LaneDisplayMode; label: string; icon: string }[] = [
  { mode: 'ribbon', label: 'Ribbon', icon: '▬' },
  { mode: 'detail', label: 'Detail', icon: '▤' },
  { mode: 'condensed', label: 'Condensed', icon: '─' },
];

function elementTypeOf(ann: W3CAnnotation): string {
  return String((ann.body as Record<string, unknown>)['palimpsest:elementType'] ?? '');
}

function elementColorOf(ann: W3CAnnotation, fallback: string): string {
  const c = (ann.body as Record<string, unknown>)['palimpsest:color'];
  return typeof c === 'string' ? c : fallback;
}

interface ElementGroupLaneProps {
  group: ElementGroupData;
  laneKey: string; // 'elements:<groupKey>' — its own display-mode slot in browserStore
  viewStart: number;
  viewEnd: number;
  width: number;
  displayMode: LaneDisplayMode;
  selectedAnnRange: { start: number; end: number } | null;
  onAnnotationClick: (ann: W3CAnnotation, trackName: string) => void;
}

const ElementGroupLane = memo(function ElementGroupLane({
  group, laneKey, viewStart, viewEnd, width, displayMode, selectedAnnRange, onAnnotationClick,
}: ElementGroupLaneProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const hidden = useElementVisibilityStore((s) => s.hidden);
  const toggleType = useElementVisibilityStore((s) => s.toggle);
  const setHidden = useElementVisibilityStore((s) => s.setHidden);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  const mode: LaneDisplayMode = displayMode === 'hidden' ? 'ribbon' : displayMode;
  const groupColor = group.presentTypes[0]?.color ?? '#5ac8fa';
  const visibleTypes = group.presentTypes.filter((t) => !hidden[t.type]);
  const typeRow = new Map(visibleTypes.map((t, i) => [t.type, i]));
  const anyHidden = group.presentTypes.some((t) => hidden[t.type]);
  const visibleCount = visibleTypes.reduce((n, t) => n + t.count, 0);

  const height = mode === 'detail'
    ? Math.max(MIN_DETAIL_H, visibleTypes.length * ROW_H)
    : LANE_HEIGHTS[mode];

  const inView = group.annotations.filter((ann) => {
    const sel = ann.target.selector;
    if (sel.start == null || sel.end == null) return false;
    if (sel.end <= viewStart || sel.start >= viewEnd) return false;
    return !hidden[elementTypeOf(ann)];
  });
  const range = viewEnd - viewStart;

  const showAllInGroup = (): void => group.presentTypes.forEach((t) => setHidden(t.type, false));

  return (
    <div className="flex border-b border-[var(--color-border-subtle)]">
      <div className="w-[100px] relative shrink-0" ref={menuRef}>
        <div
          className="h-full flex items-center gap-1 px-2 text-[0.7em] font-[var(--font-sans)] border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-muted)] cursor-pointer select-none"
          onClick={() => setMenuOpen(!menuOpen)}
          title={`${group.label} — ${visibleCount} elements`}
        >
          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: groupColor }} />
          <span className="truncate flex-1 font-semibold">{group.label}</span>
          <span className="text-[0.8em] text-[var(--color-text-muted)]">▾</span>
        </div>
        {menuOpen && (
          <div className="absolute top-full left-0 z-[var(--z-popover)] w-[190px] bg-[var(--color-bg)] border border-[var(--color-border)] rounded shadow-[var(--shadow-popover)] py-1 text-[0.75em] font-[var(--font-sans)]">
            <div className="px-2 py-1 text-[var(--color-text-muted)] font-semibold">{group.label}</div>
            <div className="h-px bg-[var(--color-border-subtle)] my-0.5" />
            {GROUP_MODE_OPTIONS.map((opt) => (
              <button
                key={opt.mode}
                className={`w-full text-left px-2 py-1 hover:bg-[var(--color-bg-muted)] cursor-pointer flex items-center gap-1.5 ${mode === opt.mode ? 'font-semibold text-[var(--color-primary)]' : ''}`}
                onClick={() => useBrowserStore.getState().setLaneDisplayMode(laneKey, opt.mode)}
              >
                <span className="w-3 text-center">{opt.icon}</span>
                {opt.label}
              </button>
            ))}
            <div className="h-px bg-[var(--color-border-subtle)] my-0.5" />
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-[var(--color-text-muted)] font-semibold">Element types</span>
              {anyHidden && (
                <button onClick={showAllInGroup} className="text-[0.85em] text-[var(--color-primary)] hover:underline">show all</button>
              )}
            </div>
            <div className="max-h-[220px] overflow-y-auto">
              {group.presentTypes.map((t) => {
                const isHidden = hidden[t.type] === true;
                return (
                  <button
                    key={t.type}
                    className="w-full text-left px-2 py-0.5 hover:bg-[var(--color-bg-muted)] cursor-pointer flex items-center gap-1.5"
                    style={{ opacity: isHidden ? 0.45 : 1 }}
                    onClick={() => toggleType(t.type)}
                    role="switch"
                    aria-checked={!isHidden}
                  >
                    <span className="w-3 text-center text-[var(--color-primary)]">{isHidden ? ' ' : '✓'}</span>
                    <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: t.color }} />
                    <span className="flex-1 capitalize truncate">{t.label}</span>
                    <span className="text-[var(--color-text-muted)] text-[0.85em]">{t.count}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
      <svg width={width} height={height} className="shrink-0">
        {mode === 'detail' && visibleTypes.map((t) => {
          const row = typeRow.get(t.type)!;
          return (
            <text
              key={`lbl-${t.type}`}
              x={4}
              y={row * ROW_H + ROW_H / 2 + 3}
              fontSize={9}
              fill={t.color}
              stroke="rgba(0,0,0,0.65)"
              strokeWidth={2}
              paintOrder="stroke"
              fontFamily="var(--font-sans)"
              className="pointer-events-none capitalize"
            >
              {t.label}
            </text>
          );
        })}
        {inView.map((ann, i) => {
          const sel = ann.target.selector;
          const start = Math.max(sel.start!, viewStart);
          const end = Math.min(sel.end!, viewEnd);
          const x = ((start - viewStart) / range) * width;
          const w = Math.max(1, ((end - start) / range) * width);
          const fill = elementColorOf(ann, groupColor);
          const isSelected = selectedAnnRange != null && sel.start === selectedAnnRange.start && sel.end === selectedAnnRange.end;

          let y: number;
          let h: number;
          if (mode === 'detail') {
            const row = typeRow.get(elementTypeOf(ann)) ?? 0;
            y = row * ROW_H + 3;
            h = ROW_H - 6;
          } else if (mode === 'condensed') {
            y = 1;
            h = height - 2;
          } else {
            y = 2;
            h = height - 4;
          }

          return (
            <rect
              key={i}
              x={x}
              y={y}
              width={w}
              height={h}
              fill={fill}
              fillOpacity={isSelected ? 1 : 0.7}
              rx={mode === 'condensed' ? 1 : 2}
              className="cursor-pointer"
              onClick={() => onAnnotationClick(ann, 'elements')}
            >
              <title>{`${elementTypeOf(ann)}: ${ann.body.value || ''}`.trim()}</title>
            </rect>
          );
        })}
      </svg>
    </div>
  );
});

export default ElementGroupLane;
