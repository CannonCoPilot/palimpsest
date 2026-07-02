import { useEffect, useMemo, useRef, useState, memo } from 'react';
import { useBrowserStore, LANE_HEIGHTS, type LaneDisplayMode } from '../../stores/browserStore';
import { useElementVisibilityStore } from '../../stores/elementVisibilityStore';
import type { ElementGroupData } from '../../utils/maskTypeGroups';
import { resolveElementColor, isApocrypha } from '../../utils/maskTypeGroups';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';

const EXPANDED_ROW_H = 18; // clean per-type sub-row (no labels/titles) — the former 'detail' height
const DETAIL_ROW_H = 27;   // 1.5x EXPANDED_ROW_H — thicker rows that print each element's title
const MIN_DETAIL_H = 22; // keep the dropdown reachable even if all types hidden

const GROUP_MODE_OPTIONS: { mode: LaneDisplayMode; label: string; icon: string }[] = [
  { mode: 'ribbon', label: 'Ribbon', icon: '▬' },
  { mode: 'detail', label: 'Detail', icon: '▤' },
  { mode: 'expanded', label: 'Expanded', icon: '▥' },
  { mode: 'condensed', label: 'Condensed', icon: '─' },
];

function elementTypeOf(ann: W3CAnnotation): string {
  return String((ann.body as Record<string, unknown>)['palimpsest:elementType'] ?? '');
}

function elementColorOf(ann: W3CAnnotation, fallback: string): string {
  return resolveElementColor(ann, fallback);
}

// Exon/intron connectors: `chapter` is carved into verse-run segments split by inline
// footnotes. Segments sharing a chapter title belong to one logical chapter; link
// consecutive segments [prevEnd, nextStart] so the lane reads like a gene model.
const CONNECTOR_TYPE = 'chapter';
function buildChapterConnectors(annotations: W3CAnnotation[]): Array<[number, number]> {
  const byTitle = new Map<string, Array<{ start: number; end: number }>>();
  for (const a of annotations) {
    if (elementTypeOf(a) !== CONNECTOR_TYPE) continue;
    const title = String((a.body as Record<string, unknown>)['palimpsest:chapterTitle'] ?? '');
    const sel = a.target.selector;
    if (!title || sel.start == null || sel.end == null) continue;
    const arr = byTitle.get(title) ?? byTitle.set(title, []).get(title)!;
    arr.push({ start: sel.start, end: sel.end });
  }
  const conns: Array<[number, number]> = [];
  for (const segs of byTitle.values()) {
    segs.sort((x, y) => x.start - y.start);
    for (let i = 0; i < segs.length - 1; i++) conns.push([segs[i].end, segs[i + 1].start]);
  }
  return conns;
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
  onAnnotationDoubleClick: (ann: W3CAnnotation) => void;
}

const ElementGroupLane = memo(function ElementGroupLane({
  group, laneKey, viewStart, viewEnd, width, displayMode, selectedAnnRange,
  onAnnotationClick, onAnnotationDoubleClick,
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

  // Types with >=1 element intersecting the current viewport — drives auto-collapse: a
  // sub-row is allotted only to a type that is both enabled (not hidden) AND in view.
  const typesInView = useMemo(() => {
    const s = new Set<string>();
    for (const ann of group.annotations) {
      const sel = ann.target.selector;
      if (sel.start == null || sel.end == null) continue;
      if (sel.end <= viewStart || sel.start >= viewEnd) continue;
      s.add(elementTypeOf(ann));
    }
    return s;
  }, [group.annotations, viewStart, viewEnd]);

  const enabledTypes = group.presentTypes.filter((t) => !hidden[t.type]);
  const rowTypes = enabledTypes.filter((t) => typesInView.has(t.type));
  const typeRow = new Map(rowTypes.map((t, i) => [t.type, i]));
  const anyHidden = group.presentTypes.some((t) => hidden[t.type]);
  const visibleCount = enabledTypes.reduce((n, t) => n + t.count, 0);

  // 'detail' and 'expanded' both split into one sub-row per shown type. 'detail' uses
  // thicker rows and prints each element's title on its bar; 'expanded' is clean bars only.
  const rowMode = mode === 'detail' || mode === 'expanded';
  const rowH = mode === 'detail' ? DETAIL_ROW_H : EXPANDED_ROW_H;
  const height = rowMode
    ? Math.max(MIN_DETAIL_H, rowTypes.length * rowH)
    : LANE_HEIGHTS[mode];

  const inView = group.annotations.filter((ann) => {
    const sel = ann.target.selector;
    if (sel.start == null || sel.end == null) return false;
    if (sel.end <= viewStart || sel.start >= viewEnd) return false;
    return !hidden[elementTypeOf(ann)];
  });
  const range = viewEnd - viewStart;

  // Connectors only matter for the lane that owns `chapter` (Content); empty elsewhere.
  const allConnectors = useMemo(() => buildChapterConnectors(group.annotations), [group.annotations]);
  const chapterType = group.presentTypes.find((t) => t.type === CONNECTOR_TYPE);
  const showConnectors = chapterType != null && !hidden[CONNECTOR_TYPE];
  const chapterRow = typeRow.get(CONNECTOR_TYPE);
  const chapterYCenter = rowMode && chapterRow != null ? chapterRow * rowH + rowH / 2 : height / 2;

  const showAllInGroup = (): void => group.presentTypes.forEach((t) => setHidden(t.type, false));

  return (
    <div className="flex border-b border-[var(--color-border-subtle)]">
      <div className="w-[100px] relative shrink-0" ref={menuRef}>
        <div
          className="h-full border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-muted)] cursor-pointer select-none"
          onClick={() => setMenuOpen(!menuOpen)}
          title={`${group.label} — ${visibleCount} elements`}
        >
          {rowMode && rowTypes.length > 0 ? (
            // Detail/Expanded: the group label is replaced by the per-type track names,
            // one per sub-row, vertically aligned with the bars in the SVG. Single-clicking
            // a color dot hides that type's track (re-show via the dropdown menu).
            <div className="relative h-full">
              {rowTypes.map((t) => (
                <div
                  key={t.type}
                  className="flex items-center gap-1 px-2 text-[0.65em] font-[var(--font-sans)] overflow-hidden"
                  style={{ height: rowH }}
                  title={t.label}
                >
                  <button
                    type="button"
                    className="w-2.5 h-2.5 rounded-full shrink-0 cursor-pointer border-0 p-0"
                    style={{ backgroundColor: t.color }}
                    title={`Hide ${t.label}`}
                    onClick={(e) => { e.stopPropagation(); toggleType(t.type); }}
                  />
                  <span className="truncate flex-1 capitalize text-[var(--color-text)]">{t.label}</span>
                </div>
              ))}
              <span className="absolute top-0.5 right-1 text-[0.7em] text-[var(--color-text-muted)]">▾</span>
            </div>
          ) : (
            <div className="h-full flex items-center gap-1 px-2 text-[0.7em] font-[var(--font-sans)]">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: groupColor }} />
              <span className="truncate flex-1 font-semibold">{group.label}</span>
              <span className="text-[0.8em] text-[var(--color-text-muted)]">▾</span>
            </div>
          )}
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
        {/* Apocrypha hatch pattern — diagonal white stripes at 30% opacity overlaid on
            any book element whose palimpsest:apocrypha field is true. The pattern is
            defined once and referenced by rect elements per annotation. */}
        <defs>
          <pattern
            id={`apocrypha-hatch-${laneKey}`}
            patternUnits="userSpaceOnUse"
            width={6}
            height={6}
            patternTransform="rotate(45)"
          >
            <line x1={0} y1={0} x2={0} y2={6} stroke="#fff" strokeWidth={2} strokeOpacity={0.35} />
          </pattern>
        </defs>
        {showConnectors && allConnectors.map(([aEnd, bStart], i) => {
          if (bStart <= viewStart || aEnd >= viewEnd) return null; // intron gap off-screen
          const x1 = ((aEnd - viewStart) / range) * width;
          const x2 = ((bStart - viewStart) / range) * width;
          if (x2 - x1 < 0.5) return null;
          return (
            <line
              key={`conn-${i}`}
              x1={x1}
              y1={chapterYCenter}
              x2={x2}
              y2={chapterYCenter}
              stroke={chapterType?.color ?? groupColor}
              strokeWidth={1.5}
              opacity={0.55}
              className="pointer-events-none"
            />
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
          const apocrypha = isApocrypha(ann);

          let y: number;
          let h: number;
          if (rowMode) {
            const row = typeRow.get(elementTypeOf(ann)) ?? 0;
            y = row * rowH + 3;
            h = rowH - 6;
          } else if (mode === 'condensed') {
            y = 1;
            h = height - 2;
          } else {
            y = 2;
            h = height - 4;
          }

          const title = (ann.body.value || '').trim();
          // Detail mode prints the element's title directly on the bar (Expanded stays clean).
          const showTitle = mode === 'detail' && w > 24 && title.length > 0;
          const apocryphaLabel = apocrypha ? ' [Apocrypha]' : '';

          return (
            <g
              key={i}
              className="cursor-pointer"
              onClick={() => onAnnotationClick(ann, 'elements')}
              onDoubleClick={() => onAnnotationDoubleClick(ann)}
            >
              <rect
                x={x}
                y={y}
                width={w}
                height={h}
                fill={fill}
                fillOpacity={isSelected ? 1 : 0.7}
                rx={mode === 'condensed' ? 1 : 2}
              >
                <title>{`${elementTypeOf(ann)}: ${title}${apocryphaLabel}`.trim()}</title>
              </rect>
              {/* Apocrypha diagonal-stripe overlay — sits on top of the base fill rect */}
              {apocrypha && (
                <rect
                  x={x}
                  y={y}
                  width={w}
                  height={h}
                  fill={`url(#apocrypha-hatch-${laneKey})`}
                  rx={mode === 'condensed' ? 1 : 2}
                  className="pointer-events-none"
                />
              )}
              {showTitle && (
                <text
                  x={x + 3}
                  y={y + h / 2 + 3}
                  fontSize={10}
                  fill="#fff"
                  stroke="rgba(0,0,0,0.55)"
                  strokeWidth={2}
                  paintOrder="stroke"
                  fontFamily="var(--font-sans)"
                  className="pointer-events-none"
                >
                  {title.slice(0, Math.max(0, Math.floor(w / 6)))}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
});

export default ElementGroupLane;
