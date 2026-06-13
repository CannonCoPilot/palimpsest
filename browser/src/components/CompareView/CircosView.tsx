/**
 * CircosView — circular arc diagram for relationship visualization.
 * Single-project mode: arcs from endnote cross-references or self-similarity.
 * Comparative mode: two concentric arcs with ribbons between aligned regions.
 */

import { useMemo, useState, useRef, useEffect, useCallback } from 'react';
import { useProjectStore, getActiveProject, getSecondaryProject } from '../../stores/projectStore';
import { useComparisonStore } from '../../stores/comparisonStore';
import type { AlignmentRecord } from '../../stores/comparisonStore';

// Design token candidate — secondary ring color
const COLOR_SECONDARY_RING = '#e67e22';

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number): [number, number] {
  const rad = (angleDeg - 90) * Math.PI / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

function arcPath(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  const [sx, sy] = polarToCartesian(cx, cy, r, startAngle);
  const [ex, ey] = polarToCartesian(cx, cy, r, endAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${sx} ${sy} A ${r} ${r} 0 ${largeArc} 1 ${ex} ${ey}`;
}

// arcPath is exported for future use — keep it
void arcPath;

function ribbonPath(
  cx: number, cy: number,
  r1: number, start1: number, end1: number,
  r2: number, start2: number, end2: number,
): string {
  const [s1x, s1y] = polarToCartesian(cx, cy, r1, start1);
  const [e1x, e1y] = polarToCartesian(cx, cy, r1, end1);
  const [s2x, s2y] = polarToCartesian(cx, cy, r2, start2);
  const [e2x, e2y] = polarToCartesian(cx, cy, r2, end2);
  return `M ${s1x} ${s1y} A ${r1} ${r1} 0 0 1 ${e1x} ${e1y} Q ${cx} ${cy} ${s2x} ${s2y} A ${r2} ${r2} 0 0 0 ${e2x} ${e2y} Q ${cx} ${cy} ${s1x} ${s1y} Z`;
}

function interpolateColor(t: number): string {
  const r = Math.round(59 + t * 200);
  const g = Math.round(130 - t * 80);
  const b = Math.round(246 - t * 150);
  return `rgb(${r},${g},${b})`;
}

export default function CircosView() {
  const activeProject = useProjectStore(getActiveProject);
  const secondaryProject = useProjectStore(getSecondaryProject);
  const records = useComparisonStore((s) => s.alignmentRecords);
  const secondaryId = useProjectStore((s) => s.secondaryProjectId);
  const selectRecord = useComparisonStore((s) => s.selectRecord);
  const setActiveSubView = useComparisonStore((s) => s.setActiveSubView);
  const [hoveredRibbon, setHoveredRibbon] = useState<number | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState(680);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect) setContainerSize(Math.floor(Math.min(rect.width, rect.height) - 16));
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const outerRadius = Math.max(100, containerSize / 2 - 40);
  const innerRadius = outerRadius - 50;
  const comparisonInnerRadius = outerRadius - 100;
  const center = outerRadius + 40;
  const svgSize = center * 2;

  const parasA = activeProject.paragraphs.length;
  const parasB = secondaryProject.paragraphs.length;
  const isComparative = !!secondaryId && parasB > 0;

  const maxScore = useMemo(() =>
    records.length > 0 ? Math.max(...records.map((r) => r.score)) : 1,
    [records]
  );

  // Single-project mode: use endnote cross-references
  const endnoteArcs = useMemo(() => {
    if (isComparative || parasA === 0) return [];
    const endnotes = activeProject.tracks['endnotes'] ?? [];
    return endnotes
      .filter((ann) => {
        const body = ann.body as Record<string, unknown>;
        return body['palimpsest:callSiteStart'] != null;
      })
      .map((ann) => {
        const body = ann.body as Record<string, unknown>;
        const callStart = body['palimpsest:callSiteStart'] as number;
        const noteStart = ann.target.selector.start ?? 0;
        return { from: callStart, to: noteStart };
      });
  }, [activeProject.tracks, isComparative, parasA]);

  const handleRibbonClick = useCallback((record: AlignmentRecord) => {
    selectRecord(record);
    setActiveSubView('alignment');
  }, [selectRecord, setActiveSubView]);

  if (parasA === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)] text-[0.85em]">
        No data available for Circos view.
      </div>
    );
  }

  const totalCharsA = activeProject.referenceText.length || 1;
  const totalCharsB = secondaryProject.referenceText.length || 1;

  const charToAngleA = (offset: number) => (offset / totalCharsA) * 360;
  const charToAngleB = (offset: number) => (offset / totalCharsB) * 360;
  const paraToAngleA = (idx: number) => (idx / parasA) * 360;
  const paraToAngleB = (idx: number) => (idx / parasB) * 360;

  return (
    <div ref={containerRef} className="flex-1 flex flex-col items-center overflow-auto p-4">
      <div className="text-[0.85em] font-[var(--font-sans)] mb-2">
        <span className="font-semibold">{activeProject.metadata?.title}</span>
        {isComparative && (
          <span className="text-[var(--color-text-muted)]"> vs {secondaryProject.metadata?.title}</span>
        )}
        {!isComparative && endnoteArcs.length > 0 && (
          <span className="text-[var(--color-text-muted)]"> — {endnoteArcs.length} endnote cross-references</span>
        )}
        {isComparative && records.length > 0 && (
          <span className="text-[var(--color-text-muted)]"> — {records.length} aligned regions</span>
        )}
      </div>

      <svg width={svgSize} height={svgSize} viewBox={`0 0 ${svgSize} ${svgSize}`} role="img" aria-label="Circos diagram showing text relationships as arcs">
        {/* Outer arc — project A */}
        <circle cx={center} cy={center} r={outerRadius} fill="none" stroke="var(--color-border)" strokeWidth={12} opacity={0.3} />
        <circle cx={center} cy={center} r={outerRadius} fill="none" stroke="var(--color-primary)" strokeWidth={2} />

        {/* Section tick marks for project A */}
        {Array.from({ length: Math.min(20, parasA) }, (_, k) => {
          const angle = (k / Math.min(20, parasA)) * 360;
          const [x1, y1] = polarToCartesian(center, center, outerRadius - 6, angle);
          const [x2, y2] = polarToCartesian(center, center, outerRadius + 6, angle);
          const paraIdx = Math.floor(k * parasA / Math.min(20, parasA));
          return (
            <g key={`tickA-${k}`}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="var(--color-text-muted)" strokeWidth={0.5} />
              {k % 5 === 0 && (
                <text {...{ x: x2, y: y2 }} fontSize={7} fill="var(--color-text-muted)" textAnchor="middle" dy={-2}>
                  ¶{paraIdx}
                </text>
              )}
            </g>
          );
        })}

        {/* Inner arc — project B (comparative mode only) */}
        {isComparative && (
          <>
            <circle cx={center} cy={center} r={comparisonInnerRadius} fill="none" stroke="var(--color-border)" strokeWidth={10} opacity={0.2} />
            <circle cx={center} cy={center} r={comparisonInnerRadius} fill="none" stroke={COLOR_SECONDARY_RING} strokeWidth={2} />
          </>
        )}

        {/* Single-project endnote arcs */}
        {!isComparative && endnoteArcs.map((arc, i) => {
          const a1 = charToAngleA(arc.from);
          const a2 = charToAngleA(arc.to);
          const [x1, y1] = polarToCartesian(center, center, innerRadius, a1);
          const [x2, y2] = polarToCartesian(center, center, innerRadius, a2);
          return (
            <path
              key={`endnote-${i}`}
              d={`M ${x1} ${y1} Q ${center} ${center} ${x2} ${y2}`}
              fill="none"
              stroke="var(--color-danger)"
              strokeWidth={1}
              strokeOpacity={0.3}
              className="cursor-pointer"
              onMouseEnter={(e) => (e.currentTarget.style.strokeOpacity = '0.8')}
              onMouseLeave={(e) => (e.currentTarget.style.strokeOpacity = '0.3')}
            >
              <title>Endnote cross-reference</title>
            </path>
          );
        })}

        {/* Comparative alignment ribbons */}
        {isComparative && records.map((rec, i) => {
          const startA = paraToAngleA(rec.queryStart);
          const endA = paraToAngleA(rec.queryEnd);
          const startB = paraToAngleB(rec.targetStart);
          const endB = paraToAngleB(rec.targetEnd);
          const t = maxScore > 0 ? rec.score / maxScore : 0;
          const color = interpolateColor(t);
          const isHovered = hoveredRibbon === i;

          return (
            <path
              key={`ribbon-${i}`}
              d={ribbonPath(center, center, outerRadius - 6, startA, endA, comparisonInnerRadius + 5, startB, endB)}
              fill={color}
              fillOpacity={isHovered ? 0.5 : 0.15}
              stroke={color}
              strokeWidth={isHovered ? 2 : 0.5}
              strokeOpacity={isHovered ? 0.9 : 0.4}
              className="cursor-pointer"
              onMouseEnter={() => setHoveredRibbon(i)}
              onMouseLeave={() => setHoveredRibbon(null)}
              onClick={() => handleRibbonClick(rec)}
            >
              <title>¶{rec.queryStart}–{rec.queryEnd} ↔ ¶{rec.targetStart}–{rec.targetEnd} (score: {rec.score.toFixed(3)}, p={rec.pValue.toExponential(2)})</title>
            </path>
          );
        })}

        {/* Center labels */}
        <text x={center} y={center - 10} textAnchor="middle" fontSize={11} fill="var(--color-text)" fontFamily="var(--font-sans)">
          {activeProject.metadata?.title?.slice(0, 25)}
        </text>
        {isComparative && (
          <text x={center} y={center + 12} textAnchor="middle" fontSize={9} fill={COLOR_SECONDARY_RING} fontFamily="var(--font-sans)">
            {secondaryProject.metadata?.title?.slice(0, 25)}
          </text>
        )}
      </svg>
    </div>
  );
}
