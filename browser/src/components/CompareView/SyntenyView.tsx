/**
 * SyntenyView — JBrowse 2-style linear synteny visualization.
 * Two stacked linear views with SVG ribbons connecting aligned regions.
 */

import { useMemo, useRef, useEffect, useState } from 'react';
import { useProjectStore, getActiveProject, getSecondaryProject } from '../../stores/projectStore';
import { useComparisonStore } from '../../stores/comparisonStore';

const TRACK_HEIGHT = 40;
const RIBBON_AREA_HEIGHT = 120;

function interpolateColor(score: number, maxScore: number): string {
  const t = maxScore > 0 ? Math.min(score / maxScore, 1) : 0;
  const r = Math.round(59 + t * 170);
  const g = Math.round(130 - t * 60);
  const b = Math.round(246 - t * 100);
  return `rgb(${r},${g},${b})`;
}

interface LinearTrackProps {
  title: string;
  paraCount: number;
  width: number;
  highlightRanges: Array<{ start: number; end: number; color: string }>;
  position: 'top' | 'bottom';
}

function LinearTrack({ title, paraCount, width, highlightRanges, position }: LinearTrackProps) {
  const cellW = width / paraCount;

  return (
    <div className="shrink-0">
      <div className={`text-[0.75em] font-[var(--font-sans)] font-semibold px-2 py-0.5 ${position === 'top' ? '' : ''}`}>
        {title} ({paraCount} ¶)
      </div>
      <svg width={width} height={TRACK_HEIGHT} className="block">
        <rect x={0} y={0} width={width} height={TRACK_HEIGHT} fill="var(--color-bg-muted)" rx={2} />
        {highlightRanges.map((r, i) => (
          <rect
            key={i}
            x={r.start * cellW}
            y={2}
            width={Math.max(1, (r.end - r.start) * cellW)}
            height={TRACK_HEIGHT - 4}
            fill={r.color}
            fillOpacity={0.6}
            rx={1}
          >
            <title>¶{r.start}–¶{r.end}</title>
          </rect>
        ))}
        {/* Tick marks */}
        {Array.from({ length: Math.min(10, paraCount) }, (_, k) => {
          const idx = Math.floor(k * paraCount / 10);
          return (
            <g key={k}>
              <line x1={idx * cellW} y1={position === 'top' ? TRACK_HEIGHT - 3 : 0} x2={idx * cellW} y2={position === 'top' ? TRACK_HEIGHT : 3} stroke="var(--color-text-muted)" strokeWidth={0.5} />
              <text x={idx * cellW + 2} y={position === 'top' ? TRACK_HEIGHT - 5 : 12} fontSize={7} fill="var(--color-text-muted)">{idx}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function SyntenyView() {
  const activeProject = useProjectStore(getActiveProject);
  const secondaryProject = useProjectStore(getSecondaryProject);
  const records = useComparisonStore((s) => s.alignmentRecords);

  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(900);
  const [hoveredRibbon, setHoveredRibbon] = useState<number | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 100) setWidth(Math.floor(w - 32));
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const parasA = activeProject.paragraphs.length;
  const parasB = secondaryProject.paragraphs.length;

  const maxScore = useMemo(() =>
    records.length > 0 ? Math.max(...records.map((r) => r.score)) : 1,
    [records]
  );

  const highlightsA = useMemo(() =>
    records.map((r) => ({
      start: r.queryStart,
      end: r.queryEnd,
      color: interpolateColor(r.score, maxScore),
    })),
    [records, maxScore]
  );

  const highlightsB = useMemo(() =>
    records.map((r) => ({
      start: r.targetStart,
      end: r.targetEnd,
      color: interpolateColor(r.score, maxScore),
    })),
    [records, maxScore]
  );

  if (records.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)] text-[0.85em]">
        No alignment records. Run alignment first to see synteny ribbons.
      </div>
    );
  }

  const cellWA = width / parasA;
  const cellWB = width / parasB;

  return (
    <div ref={containerRef} className="flex-1 flex flex-col items-center overflow-auto p-4">
      <LinearTrack
        title={activeProject.metadata?.title ?? 'Query'}
        paraCount={parasA}
        width={width}
        highlightRanges={highlightsA}
        position="top"
      />

      {/* Ribbon area */}
      <svg width={width} height={RIBBON_AREA_HEIGHT} className="block shrink-0">
        {records.map((rec, i) => {
          const topLeft = rec.queryStart * cellWA;
          const topRight = rec.queryEnd * cellWA;
          const botLeft = rec.targetStart * cellWB;
          const botRight = rec.targetEnd * cellWB;
          const color = interpolateColor(rec.score, maxScore);

          return (
            <path
              key={i}
              d={`M ${topLeft} 0 L ${topRight} 0 C ${topRight} ${RIBBON_AREA_HEIGHT * 0.5}, ${botRight} ${RIBBON_AREA_HEIGHT * 0.5}, ${botRight} ${RIBBON_AREA_HEIGHT} L ${botLeft} ${RIBBON_AREA_HEIGHT} C ${botLeft} ${RIBBON_AREA_HEIGHT * 0.5}, ${topLeft} ${RIBBON_AREA_HEIGHT * 0.5}, ${topLeft} 0 Z`}
              fill={color}
              fillOpacity={hoveredRibbon === i ? 0.5 : 0.3}
              stroke={color}
              strokeWidth={1}
              strokeOpacity={0.6}
              className="cursor-pointer"
              onMouseEnter={() => setHoveredRibbon(i)}
              onMouseLeave={() => setHoveredRibbon(null)}
            >
              <title>¶{rec.queryStart}–{rec.queryEnd} ↔ ¶{rec.targetStart}–{rec.targetEnd} (score: {rec.score.toFixed(3)})</title>
            </path>
          );
        })}
      </svg>

      <LinearTrack
        title={secondaryProject.metadata?.title ?? 'Target'}
        paraCount={parasB}
        width={width}
        highlightRanges={highlightsB}
        position="bottom"
      />

      <div className="mt-2 text-[0.75em] text-[var(--color-text-muted)] font-[var(--font-sans)]">
        {records.length} aligned region{records.length !== 1 ? 's' : ''} · Ribbons connect corresponding passages
      </div>
    </div>
  );
}
