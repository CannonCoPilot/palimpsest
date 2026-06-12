/**
 * AlignmentView — split-panel ribbon visualization connecting aligned passages.
 * Left pane: query text (project A). Right pane: target text (project B).
 * Center: SVG ribbons connecting aligned paragraph ranges.
 */

import { useRef, useCallback, useMemo } from 'react';
import { useProjectStore, getActiveProject, getSecondaryProject } from '../../stores/projectStore';
import { useComparisonStore, type AlignmentRecord } from '../../stores/comparisonStore';

const PARA_HEIGHT = 24;
const RIBBON_WIDTH = 80;

function interpolateRibbonColor(score: number, maxScore: number): string {
  const t = maxScore > 0 ? Math.min(score / maxScore, 1) : 0;
  const r = Math.round(59 + t * (30 - 59));
  const g = Math.round(130 + t * (64 - 130));
  const b = Math.round(246 + t * (175 - 246));
  return `rgb(${r},${g},${b})`;
}

interface TextPaneProps {
  paragraphs: Array<{ index: number; text: string }>;
  title: string;
  highlightRanges: Array<{ start: number; end: number; color: string }>;
  scrollRef: React.RefObject<HTMLDivElement | null>;
  onScroll: () => void;
}

function TextPane({ paragraphs, title, highlightRanges, scrollRef, onScroll }: TextPaneProps) {
  return (
    <div className="flex-1 flex flex-col min-w-0 border border-[var(--color-border)] rounded overflow-hidden">
      <div className="px-3 py-1.5 bg-[var(--color-bg-subtle)] border-b border-[var(--color-border)] text-[0.8em] font-semibold font-[var(--font-sans)] truncate">
        {title}
      </div>
      <div ref={scrollRef} onScroll={onScroll} className="flex-1 overflow-y-auto text-[0.8em] font-[var(--font-serif)]">
        {paragraphs.map((p) => {
          const hl = highlightRanges.find((r) => p.index >= r.start && p.index < r.end);
          return (
            <div
              key={p.index}
              data-para={p.index}
              className="px-3 py-1 border-b border-[var(--color-border-subtle)] leading-relaxed"
              style={hl ? { backgroundColor: `${hl.color}15`, borderLeft: `3px solid ${hl.color}` } : undefined}
            >
              <span className="text-[var(--color-text-muted)] text-[0.75em] mr-1.5 select-none">¶{p.index}</span>
              {p.text.length > 200 ? p.text.slice(0, 200) + '...' : p.text}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AlignmentView() {
  const activeProject = useProjectStore(getActiveProject);
  const secondaryProject = useProjectStore(getSecondaryProject);
  const records = useComparisonStore((s) => s.alignmentRecords);
  const selectedRecord = useComparisonStore((s) => s.selectedRecord);
  const selectRecord = useComparisonStore((s) => s.selectRecord);

  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const parasA = useMemo(() =>
    activeProject.paragraphs.map((p) => ({ index: p.index, text: p.text })),
    [activeProject.paragraphs]
  );
  const parasB = useMemo(() =>
    secondaryProject.paragraphs.map((p) => ({ index: p.index, text: p.text })),
    [secondaryProject.paragraphs]
  );

  const maxScore = useMemo(() =>
    records.length > 0 ? Math.max(...records.map((r) => r.score)) : 1,
    [records]
  );

  const highlightsA = useMemo(() =>
    records.map((r) => ({
      start: r.queryStart,
      end: r.queryEnd,
      color: interpolateRibbonColor(r.score, maxScore),
    })),
    [records, maxScore]
  );

  const highlightsB = useMemo(() =>
    records.map((r) => ({
      start: r.targetStart,
      end: r.targetEnd,
      color: interpolateRibbonColor(r.score, maxScore),
    })),
    [records, maxScore]
  );

  const getParaY = useCallback((paneRef: React.RefObject<HTMLDivElement | null>, paraIndex: number): number | null => {
    const container = paneRef.current;
    if (!container) return null;
    const el = container.querySelector(`[data-para="${paraIndex}"]`) as HTMLElement | null;
    if (!el) return null;
    const containerRect = container.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();
    return elRect.top - containerRect.top + elRect.height / 2;
  }, []);

  const handleRibbonClick = useCallback((record: AlignmentRecord) => {
    selectRecord(record);
    // Scroll both panes to the aligned regions
    const leftEl = leftRef.current?.querySelector(`[data-para="${record.queryStart}"]`);
    const rightEl = rightRef.current?.querySelector(`[data-para="${record.targetStart}"]`);
    leftEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    rightEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [selectRecord]);

  const handleScroll = useCallback(() => {
    // Force SVG re-render by triggering a state update
    svgRef.current?.setAttribute('data-scroll', Date.now().toString());
  }, []);

  if (records.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)] text-[0.85em]">
        No alignment records. Run alignment from the toolbar above.
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden p-2 gap-0">
      <TextPane
        paragraphs={parasA}
        title={`${activeProject.metadata?.title ?? 'Query'} (${parasA.length} ¶)`}
        highlightRanges={highlightsA}
        scrollRef={leftRef}
        onScroll={handleScroll}
      />

      {/* Ribbon SVG */}
      <div className="shrink-0 relative" style={{ width: RIBBON_WIDTH }}>
        <svg
          ref={svgRef}
          width={RIBBON_WIDTH}
          height="100%"
          className="absolute inset-0"
          style={{ pointerEvents: 'none' }}
        >
          {records.map((r, i) => {
            const leftY = getParaY(leftRef, Math.floor((r.queryStart + r.queryEnd) / 2));
            const rightY = getParaY(rightRef, Math.floor((r.targetStart + r.targetEnd) / 2));
            if (leftY == null || rightY == null) return null;

            const color = interpolateRibbonColor(r.score, maxScore);
            const isSelected = selectedRecord?.queryStart === r.queryStart && selectedRecord?.targetStart === r.targetStart;
            const opacity = isSelected ? 0.9 : 0.4;
            const strokeWidth = isSelected ? 3 : 1.5;

            return (
              <path
                key={i}
                d={`M 0 ${leftY} C ${RIBBON_WIDTH * 0.4} ${leftY}, ${RIBBON_WIDTH * 0.6} ${rightY}, ${RIBBON_WIDTH} ${rightY}`}
                stroke={color}
                strokeWidth={strokeWidth}
                fill="none"
                opacity={opacity}
                style={{ pointerEvents: 'stroke', cursor: 'pointer' }}
                onClick={() => handleRibbonClick(r)}
              >
                <title>¶{r.queryStart}–{r.queryEnd} ↔ ¶{r.targetStart}–{r.targetEnd} (score: {r.score.toFixed(3)})</title>
              </path>
            );
          })}
        </svg>
      </div>

      <TextPane
        paragraphs={parasB}
        title={`${secondaryProject.metadata?.title ?? 'Target'} (${parasB.length} ¶)`}
        highlightRanges={highlightsB}
        scrollRef={rightRef}
        onScroll={handleScroll}
      />
    </div>
  );
}
