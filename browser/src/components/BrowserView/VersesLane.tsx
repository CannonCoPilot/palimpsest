import { memo, useMemo } from 'react';
import type { VerseRecord } from '../../stores/verseStore';

/** Verse color (matches the backend `verse` type hue in layout.py SECTION_COLORS). */
const VERSE_COLOR = '#6fdc8c';
/** Masked-token shade, matching the TickerTape's masked background. */
const MASKED_COLOR = '#3a3a3d';
const HEIGHT = 28; // ribbon height (LANE_HEIGHTS.ribbon)

interface VersesLaneProps {
  records: VerseRecord[];
  viewStart: number;
  viewEnd: number;
  width: number;
}

/**
 * The Verses lane: one mark per verse, drawn only when zoomed in (BrowserView gates this
 * to viewport < VERSE_ZOOM_MAX_CHARS). Each verse renders its masked `C:V.` number token
 * `[ns, s)` in the masked-gray and its analyzed prose `[s, e)` in verse-green, so the lane
 * doubles as a legend for what the verse-number mask layer removes from analysis.
 *
 * Records come from the lazy verseStore (compact `{b,c,v,ns,s,e}`), so this never inflates
 * the eager elements track.
 */
const VersesLane = memo(function VersesLane({ records, viewStart, viewEnd, width }: VersesLaneProps) {
  const range = Math.max(1, viewEnd - viewStart);

  // Records are position-sorted; keep only those overlapping the viewport. At the gated
  // zoom (< 30k chars) this is a few hundred at most.
  const visible = useMemo(
    () => records.filter((r) => r.e > viewStart && r.ns < viewEnd),
    [records, viewStart, viewEnd],
  );

  const x = (pos: number) => ((Math.max(pos, viewStart) - viewStart) / range) * width;
  const xEnd = (pos: number) => ((Math.min(pos, viewEnd) - viewStart) / range) * width;

  return (
    <div className="flex border-b border-[var(--color-border-subtle)]">
      <div className="w-[100px] shrink-0">
        <div className="h-full flex items-center gap-1 px-2 text-[0.7em] font-[var(--font-sans)] border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-muted)] select-none">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: VERSE_COLOR }} />
          <span className="truncate flex-1">Verses</span>
          <span className="text-[0.8em] text-[var(--color-text-muted)]">{visible.length}</span>
        </div>
      </div>
      <svg width={width} height={HEIGHT} className="shrink-0">
        {visible.map((r, i) => {
          const numX = x(r.ns);
          const proseX = x(r.s);
          const endX = xEnd(r.e);
          const numW = Math.max(0, proseX - numX);
          const proseW = Math.max(1, endX - proseX);
          const label = `${r.c}:${r.v}`;
          return (
            <g key={i}>
              {numW > 0 && <rect x={numX} y={4} width={numW} height={HEIGHT - 8} fill={MASKED_COLOR} rx={1} />}
              <rect x={proseX} y={4} width={proseW} height={HEIGHT - 8} fill={VERSE_COLOR} fillOpacity={0.7} rx={1}>
                <title>{`${r.b} ${label}`}</title>
              </rect>
              {proseW > 22 && (
                <text x={proseX + 2} y={HEIGHT / 2 + 3} fontSize={8} fill="#0b3d1a" fontFamily="var(--font-mono)" className="pointer-events-none">
                  {label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
});

export default VersesLane;
