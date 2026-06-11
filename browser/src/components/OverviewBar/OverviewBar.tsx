import { useRef, useState, useEffect, useCallback } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useTrackStore } from '../../stores/trackStore';
import { useSearchStore } from '../../stores/searchStore';
import { useViewStore } from '../../stores/viewStore';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { TRACK_COLORS } from '../../utils/trackColors';
import { Tooltip } from '../common/Tooltip';

interface BarcodeProps {
  label: string;
  annotations: W3CAnnotation[];
  color: string;
  documentLength: number;
  width: number;
  height: number;
  visible: boolean;
  viewportStart: number;
  viewportEnd: number;
  dragRange: [number, number] | null;
  onClickPosition: (fraction: number) => void;
}

function DensityBarcode({ label, annotations, color, documentLength, width, height, visible, viewportStart, viewportEnd, dragRange, onClickPosition }: BarcodeProps) {
  const vpX = (viewportStart / documentLength) * width;
  const vpW = Math.max(2, ((viewportEnd - viewportStart) / documentLength) * width);

  const dragX = dragRange ? (dragRange[0] / documentLength) * width : 0;
  const dragW = dragRange ? ((dragRange[1] - dragRange[0]) / documentLength) * width : 0;

  return (
    <div className="flex items-center gap-1" style={{ opacity: visible ? 1 : 0.3 }}>
      <Tooltip content={`${label} — ${annotations.length} annotations`} side="top">
        <span className="w-[60px] text-[0.7em] text-[var(--color-text-muted)] text-right truncate">{label}</span>
      </Tooltip>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`${label} density`}
        className="cursor-crosshair select-none"
        onClick={(e) => {
          if (!dragRange) {
            const rect = e.currentTarget.getBoundingClientRect();
            onClickPosition((e.clientX - rect.left) / rect.width);
          }
        }}
      >
        <rect width={width} height={height} fill="#f8f8f8" />
        <rect x={vpX} y={0} width={vpW} height={height} fill={color} fillOpacity={0.08} />
        {annotations.map((ann, i) => {
          const sel = ann.target.selector;
          if (sel.type !== 'TextPositionSelector' || sel.start == null) return null;
          const x = (sel.start / documentLength) * width;
          return <line key={i} x1={x} y1={0} x2={x} y2={height} stroke={color} strokeOpacity={0.6} />;
        })}
        <rect x={vpX} y={0} width={vpW} height={height} fill="none" stroke={color} strokeWidth={1} strokeOpacity={0.4} rx={1} />
        {dragRange && (
          <rect x={dragX} y={0} width={Math.max(1, dragW)} height={height} fill={color} fillOpacity={0.25} stroke={color} strokeWidth={1} rx={1} />
        )}
      </svg>
    </div>
  );
}

export default function OverviewBar() {
  const tracks = useProjectStore((s) => s.tracks);
  const referenceText = useProjectStore((s) => s.referenceText);
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const trackStates = useTrackStore((s) => s.tracks);
  const searchMatches = useSearchStore((s) => s.matches);
  const visibleRange = useViewStore((s) => s.visibleParagraphRange);
  const docLen = referenceText.length || 1;

  const containerRef = useRef<HTMLDivElement>(null);
  const [barWidth, setBarWidth] = useState(600);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const dragging = useRef(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setBarWidth(Math.max(100, entry.contentRect.width - 80));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const vpStart = visibleRange && paragraphs.length > 0
    ? paragraphs[visibleRange[0]]?.start ?? 0 : 0;
  const vpEnd = visibleRange && paragraphs.length > 0
    ? paragraphs[Math.min(visibleRange[1], paragraphs.length - 1)]?.end ?? docLen : docLen;

  const trackNames = Object.keys(tracks).filter((n) => n !== 'segments');

  const navigateToFraction = useCallback((fraction: number) => {
    const charOffset = Math.round(fraction * docLen);
    const targetPara = paragraphs.findIndex((p) => p.end >= charOffset);
    if (targetPara >= 0) {
      useViewStore.getState().setSelectedParagraphIndex(targetPara);
      useViewStore.getState().requestScrollToParagraph(targetPara);
    }
  }, [docLen, paragraphs]);

  const fractionToCharOffset = useCallback((clientX: number, svgEl: SVGSVGElement) => {
    const rect = svgEl.getBoundingClientRect();
    const fraction = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return Math.round(fraction * docLen);
  }, [docLen]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const svg = (e.target as Element).closest('svg');
    if (!svg) return;
    dragging.current = true;
    const offset = fractionToCharOffset(e.clientX, svg as SVGSVGElement);
    setDragStart(offset);
    setDragEnd(offset);
  }, [fractionToCharOffset]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging.current) return;
    const svg = (e.target as Element).closest('svg');
    if (!svg) return;
    setDragEnd(fractionToCharOffset(e.clientX, svg as SVGSVGElement));
  }, [fractionToCharOffset]);

  const handleMouseUp = useCallback(() => {
    if (!dragging.current || dragStart == null || dragEnd == null) {
      dragging.current = false;
      return;
    }
    dragging.current = false;
    const start = Math.min(dragStart, dragEnd);
    const end = Math.max(dragStart, dragEnd);
    if (end - start < docLen * 0.005) {
      setDragStart(null);
      setDragEnd(null);
      return;
    }
    const targetPara = paragraphs.findIndex((p) => p.end >= start);
    if (targetPara >= 0) {
      useViewStore.getState().setSelectedParagraphIndex(targetPara);
      useViewStore.getState().requestScrollToParagraph(targetPara);
    }
  }, [dragStart, dragEnd, docLen, paragraphs]);

  const dragRange: [number, number] | null = dragStart != null && dragEnd != null
    ? [Math.min(dragStart, dragEnd), Math.max(dragStart, dragEnd)]
    : null;

  return (
    <div
      ref={containerRef}
      className="border-t border-[var(--color-border)] bg-[var(--color-bg-muted)] px-2 py-1 w-full"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => { if (dragging.current) handleMouseUp(); }}
    >
      {trackNames.map((name) => (
        <DensityBarcode
          key={name}
          label={name}
          annotations={tracks[name] ?? []}
          color={TRACK_COLORS[name] ?? '#888'}
          documentLength={docLen}
          width={barWidth}
          height={12}
          visible={trackStates[name]?.visible ?? true}
          viewportStart={vpStart}
          viewportEnd={vpEnd}
          dragRange={dragRange}
          onClickPosition={navigateToFraction}
        />
      ))}
      {searchMatches.length > 0 && (
        <div className="flex items-center gap-1">
          <span className="w-[60px] text-[0.7em] text-[var(--color-text-muted)] text-right">search</span>
          <svg width={barWidth} height={12} role="img" aria-label="Search matches" className="cursor-crosshair">
            <rect width={barWidth} height={12} fill="#f8f8f8" />
            <rect
              x={(vpStart / docLen) * barWidth} y={0}
              width={Math.max(2, ((vpEnd - vpStart) / docLen) * barWidth)}
              height={12} fill="#f1c40f" fillOpacity={0.1}
            />
            {searchMatches.map((m, i) => {
              const x = (m.start / docLen) * barWidth;
              return <line key={i} x1={x} y1={0} x2={x} y2={12} stroke="#f1c40f" strokeWidth={2} />;
            })}
          </svg>
        </div>
      )}
    </div>
  );
}
