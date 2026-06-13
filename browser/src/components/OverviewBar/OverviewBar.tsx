import { useRef, useState, useEffect, useCallback } from 'react';
import { useProjectStore, getActiveProject } from '../../stores/projectStore';
import { useTrackStore } from '../../stores/trackStore';
import { useSearchStore } from '../../stores/searchStore';
import { useViewStore } from '../../stores/viewStore';
import { useBrowserStore } from '../../stores/browserStore';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import type { TrackManifest } from '../../adapters/TrackManifest';
import { TRACK_COLORS } from '../../utils/trackColors';
import { Tooltip } from '../common/Tooltip';

interface BarcodeProps {
  label: string;
  annotations: W3CAnnotation[];
  color: string;
  manifest: TrackManifest | null;
  documentLength: number;
  width: number;
  height: number;
  visible: boolean;
  viewportStart: number;
  viewportEnd: number;
  dragRange: [number, number] | null;
  onClickPosition: (fraction: number) => void;
}

function renderStateBand(annotations: W3CAnnotation[], manifest: TrackManifest | null, documentLength: number, width: number, height: number) {
  const scale = manifest?.colorScheme?.scale;
  return annotations.map((ann, i) => {
    const sel = ann.target.selector;
    if (sel.type !== 'TextPositionSelector' || sel.start == null || sel.end == null) return null;
    const x = (sel.start / documentLength) * width;
    const w = Math.max(1, ((sel.end - sel.start) / documentLength) * width);
    const stateId = (ann.body as Record<string, unknown>)['palimpsest:stateId'];
    let fill = manifest?.colorScheme?.primary ?? '#888';
    if (scale && typeof stateId === 'number') {
      const val = scale[String(stateId)];
      if (val) fill = val;
    }
    return <rect key={i} x={x} y={0} width={w} height={height} fill={fill} fillOpacity={0.7} />;
  });
}

function renderABBand(annotations: W3CAnnotation[], manifest: TrackManifest | null, documentLength: number, width: number, height: number) {
  const primary = manifest?.colorScheme?.primary ?? '#c0392b';
  const secondary = manifest?.colorScheme?.secondary ?? '#2980b9';
  return annotations.map((ann, i) => {
    const sel = ann.target.selector;
    if (sel.type !== 'TextPositionSelector' || sel.start == null || sel.end == null) return null;
    const x = (sel.start / documentLength) * width;
    const w = Math.max(1, ((sel.end - sel.start) / documentLength) * width);
    const compartment = (ann.body as Record<string, unknown>)['palimpsest:compartment'];
    const fill = compartment === 'A' ? primary : secondary;
    return <rect key={i} x={x} y={0} width={w} height={height} fill={fill} fillOpacity={0.6} />;
  });
}

function renderDensityTicks(annotations: W3CAnnotation[], color: string, documentLength: number, width: number, height: number) {
  return annotations.map((ann, i) => {
    const sel = ann.target.selector;
    if (sel.type !== 'TextPositionSelector' || sel.start == null) return null;
    const x = (sel.start / documentLength) * width;
    return <line key={i} x1={x} y1={0} x2={x} y2={height} stroke={color} strokeOpacity={0.6} />;
  });
}

function findNearestAnnotation(annotations: W3CAnnotation[], charOffset: number): W3CAnnotation | null {
  let best: W3CAnnotation | null = null;
  let bestDist = Infinity;
  for (const ann of annotations) {
    const s = ann.target.selector;
    if (s.type !== 'TextPositionSelector' || s.start == null) continue;
    const dist = Math.abs(s.start - charOffset);
    if (dist < bestDist) { bestDist = dist; best = ann; }
  }
  return bestDist < 500 ? best : null;
}

function TrackBarcode({ label, annotations, color, manifest, documentLength, width, height, visible, viewportStart, viewportEnd, dragRange, onClickPosition }: BarcodeProps) {
  const [hoverInfo, setHoverInfo] = useState<string | null>(null);
  const [hoverX, setHoverX] = useState(0);

  const vpX = (viewportStart / documentLength) * width;
  const vpW = Math.max(2, ((viewportEnd - viewportStart) / documentLength) * width);
  const dragX = dragRange ? (dragRange[0] / documentLength) * width : 0;
  const dragW = dragRange ? ((dragRange[1] - dragRange[0]) / documentLength) * width : 0;
  const renderType = manifest?.overviewBarRendering?.type ?? 'density-barcode';

  return (
    <div className="flex items-center gap-1 relative" style={{ opacity: visible ? 1 : 0.3 }}>
      <Tooltip content={`${label} — ${annotations.length} annotations`} side="top">
        <span className="w-[60px] text-[0.7em] text-[var(--color-text-muted)] text-right truncate">{label}</span>
      </Tooltip>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`${label} ${renderType}`}
        className="cursor-crosshair select-none"
        onClick={(e) => {
          if (!dragRange) {
            const rect = e.currentTarget.getBoundingClientRect();
            onClickPosition((e.clientX - rect.left) / rect.width);
          }
        }}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const frac = (e.clientX - rect.left) / rect.width;
          const charOffset = Math.round(frac * documentLength);
          setHoverX(e.clientX - rect.left);
          const nearest = findNearestAnnotation(annotations, charOffset);
          if (nearest) {
            const t = nearest.body.type.replace('palimpsest:', '');
            const v = nearest.body.value || '';
            setHoverInfo(`${t}${v ? ': ' + v.slice(0, 40) : ''}`);
          } else {
            setHoverInfo(null);
          }
        }}
        onMouseLeave={() => setHoverInfo(null)}
      >
        <rect width={width} height={height} fill="#f8f8f8" />
        <rect x={vpX} y={0} width={vpW} height={height} fill={color} fillOpacity={0.08} />
        {renderType === 'state-band' && renderStateBand(annotations, manifest, documentLength, width, height)}
        {renderType === 'ab-band' && renderABBand(annotations, manifest, documentLength, width, height)}
        {renderType === 'density-barcode' && renderDensityTicks(annotations, color, documentLength, width, height)}
        <rect x={vpX} y={0} width={vpW} height={height} fill="none" stroke={color} strokeWidth={1} strokeOpacity={0.4} rx={1} />
        {dragRange && (
          <rect x={dragX} y={0} width={Math.max(1, dragW)} height={height} fill={color} fillOpacity={0.25} stroke={color} strokeWidth={1} rx={1} />
        )}
      </svg>
      {hoverInfo && (
        <div
          className="absolute -mt-6 px-1.5 py-0.5 text-[0.6em] bg-[#1a1a1a] text-white rounded-sm whitespace-nowrap pointer-events-none z-[var(--z-tooltip)]"
          style={{ left: `${hoverX + 64}px` }}
        >
          {hoverInfo}
        </div>
      )}
    </div>
  );
}

export default function OverviewBar() {
  const tracks = useProjectStore((s) => getActiveProject(s).tracks);
  const referenceText = useProjectStore((s) => getActiveProject(s).referenceText);
  const paragraphs = useProjectStore((s) => getActiveProject(s).paragraphs);
  const trackStates = useTrackStore((s) => s.tracks);
  const searchMatches = useSearchStore((s) => s.matches);
  const visibleRange = useViewStore((s) => s.visibleParagraphRange);
  const overviewBarHidden = useBrowserStore((s) => s.overviewBarHidden);
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
    const startPara = paragraphs.findIndex((p) => p.end >= start);
    const endPara = paragraphs.findIndex((p) => p.end >= end);
    const resolvedEnd = endPara >= 0 ? endPara : paragraphs.length - 1;
    if (startPara >= 0) {
      useViewStore.getState().setSelectedParagraphIndex(startPara);
      useViewStore.getState().requestScrollToParagraph(startPara);
      useViewStore.getState().setVisibleParagraphRange([startPara, resolvedEnd]);
      useViewStore.getState().setZoomLevel('paragraph');
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
      {trackNames.filter((name) => !overviewBarHidden.has(name)).map((name) => (
        <TrackBarcode
          key={name}
          label={name}
          annotations={tracks[name] ?? []}
          color={TRACK_COLORS[name] ?? '#888'}
          manifest={trackStates[name]?.manifest ?? null}
          documentLength={docLen}
          width={barWidth}
          height={12}
          visible={true}
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
