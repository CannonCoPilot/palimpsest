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
  boxColor: string;
  boxBorderColor: string;
  boxFillOpacity: number;
  viewportGrabbable: boolean;
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
    const body = ann.body as Record<string, unknown>;
    const stateId = body['palimpsest:stateId'];
    let fill = manifest?.colorScheme?.primary ?? '#888';
    if (scale && typeof stateId === 'number') {
      const val = scale[String(stateId)];
      if (val) fill = val;
    } else if (typeof body['palimpsest:color'] === 'string') {
      fill = body['palimpsest:color'] as string;  // per-element type color (e.g. mask elements)
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

function TrackBarcode({ label, annotations, color, manifest, documentLength, width, height, visible, viewportStart, viewportEnd, boxColor, boxBorderColor, boxFillOpacity, viewportGrabbable, dragRange, onClickPosition }: BarcodeProps) {
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
        <rect x={vpX} y={0} width={vpW} height={height} fill={boxColor} fillOpacity={boxFillOpacity} />
        {renderType === 'state-band' && renderStateBand(annotations, manifest, documentLength, width, height)}
        {renderType === 'ab-band' && renderABBand(annotations, manifest, documentLength, width, height)}
        {renderType === 'density-barcode' && renderDensityTicks(annotations, color, documentLength, width, height)}
        <rect
          x={vpX} y={0} width={vpW} height={height} fill="none" stroke={boxBorderColor}
          strokeWidth={viewportGrabbable ? 1.5 : 1} strokeOpacity={viewportGrabbable ? 0.95 : 0.7} rx={1}
        />
        {viewportGrabbable && (
          // Grip walls at the box edges so the persistent viewport box reads as grabbable.
          <>
            <line x1={vpX} y1={0} x2={vpX} y2={height} stroke={boxBorderColor} strokeWidth={2} strokeOpacity={0.95} />
            <line x1={vpX + vpW} y1={0} x2={vpX + vpW} y2={height} stroke={boxBorderColor} strokeWidth={2} strokeOpacity={0.95} />
          </>
        )}
        {dragRange && (
          <rect x={dragX} y={0} width={Math.max(1, dragW)} height={height} fill={boxColor} fillOpacity={0.25} stroke={boxBorderColor} strokeWidth={1.5} rx={1} />
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
  const activeTab = useViewStore((s) => s.activeTab);
  const overviewBarHidden = useBrowserStore((s) => s.overviewBarHidden);
  const bvStart = useBrowserStore((s) => s.viewStart);
  const bvEnd = useBrowserStore((s) => s.viewEnd);
  const docLen = referenceText.length || 1;
  // On the Browser tab the ticker tracks the Browser viewport (yellow box) and drag drives
  // browserStore; elsewhere it keeps driving the Reader's paragraph range.
  const browserMode = activeTab === 'browser';

  const containerRef = useRef<HTMLDivElement>(null);
  const [barWidth, setBarWidth] = useState(600);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const dragging = useRef(false);
  const dragMode = useRef<'pan' | 'zoom' | 'reader'>('reader');
  const panLastChar = useRef(0);
  // The track svg the drag started on. Captured at pointerdown so move/up keep resolving offsets
  // against it even after the pointer strays off the track (pointer capture retargets the events
  // to the container, where e.target is no longer an svg).
  const dragSvg = useRef<SVGSVGElement | null>(null);

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

  // Viewport box: Browser viewport on the Browser tab, Reader paragraph range elsewhere.
  const boxStart = browserMode ? bvStart : vpStart;
  const boxEnd = browserMode ? bvEnd : vpEnd;

  const trackNames = Object.keys(tracks).filter((n) => n !== 'segments' && n !== 'sections');

  const navigateToFraction = useCallback((fraction: number) => {
    if (browserMode) return; // Browser-tab navigation is handled by drag (zoom / box-pan).
    const charOffset = Math.round(fraction * docLen);
    const targetPara = paragraphs.findIndex((p) => p.end >= charOffset);
    if (targetPara >= 0) {
      useViewStore.getState().setSelectedParagraphIndex(targetPara);
      useViewStore.getState().requestScrollToParagraph(targetPara);
    }
  }, [browserMode, docLen, paragraphs]);

  const fractionToCharOffset = useCallback((clientX: number, svgEl: SVGSVGElement) => {
    const rect = svgEl.getBoundingClientRect();
    const fraction = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return Math.round(fraction * docLen);
  }, [docLen]);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    const svg = (e.target as Element).closest('svg');
    if (!svg) return;
    // Capture the pointer so the drag owns it until release — straying off the track (or out of the
    // bar entirely) no longer drops mid-drag pan/zoom-select.
    e.currentTarget.setPointerCapture(e.pointerId);
    dragSvg.current = svg as SVGSVGElement;
    dragging.current = true;
    const offset = fractionToCharOffset(e.clientX, svg as SVGSVGElement);
    if (browserMode) {
      // Grab the yellow viewport box to pan; drag anywhere else to rubber-band zoom-select.
      // When the box spans (nearly) the whole bar there is no pan room and no "outside" to
      // start a zoom from, so any drag zoom-selects instead — this keeps zoom-select reachable
      // from the default full-extent view (otherwise dragging the full-width box is a no-op pan).
      const hasPanRoom = bvEnd - bvStart < docLen * 0.98;
      const inBox = offset >= bvStart && offset <= bvEnd;
      const panning = inBox && hasPanRoom;
      dragMode.current = panning ? 'pan' : 'zoom';
      panLastChar.current = offset;
      if (panning) { setDragStart(null); setDragEnd(null); }
      else { setDragStart(offset); setDragEnd(offset); }
    } else {
      dragMode.current = 'reader';
      setDragStart(offset);
      setDragEnd(offset);
    }
  }, [fractionToCharOffset, browserMode, bvStart, bvEnd, docLen]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging.current) return;
    const svg = dragSvg.current;
    if (!svg) return;
    const offset = fractionToCharOffset(e.clientX, svg);
    if (browserMode && dragMode.current === 'pan') {
      useBrowserStore.getState().pan(offset - panLastChar.current);
      panLastChar.current = offset;
    } else {
      setDragEnd(offset);
    }
  }, [fractionToCharOffset, browserMode]);

  const handlePointerUp = useCallback(() => {
    if (!dragging.current) return;
    dragging.current = false;
    dragSvg.current = null;
    if (browserMode) {
      if (dragMode.current === 'zoom' && dragStart != null && dragEnd != null) {
        const s = Math.min(dragStart, dragEnd);
        const en = Math.max(dragStart, dragEnd);
        if (en - s >= docLen * 0.002) {
          useBrowserStore.getState().zoomToRange(s, en);
        } else {
          // No rubber-band: treat as a click and recenter the viewport on the click point.
          const b = useBrowserStore.getState();
          b.pan(s - (b.viewStart + b.viewEnd) / 2);
        }
      }
      dragMode.current = 'reader';
      setDragStart(null);
      setDragEnd(null);
      return;
    }
    if (dragStart == null || dragEnd == null) return;
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
    setDragStart(null);
    setDragEnd(null);
  }, [dragStart, dragEnd, docLen, paragraphs, browserMode, bvStart, bvEnd]);

  const dragRange: [number, number] | null = dragStart != null && dragEnd != null
    ? [Math.min(dragStart, dragEnd), Math.max(dragStart, dragEnd)]
    : null;

  return (
    <div
      ref={containerRef}
      className="border-t border-[var(--color-border)] bg-[var(--color-bg-muted)] px-2 py-1 w-full"
      style={{ touchAction: 'none' }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
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
          viewportStart={boxStart}
          viewportEnd={boxEnd}
          boxColor={browserMode ? '#0a84ff' : (TRACK_COLORS[name] ?? '#888')}
          boxBorderColor={browserMode ? '#ff453a' : (TRACK_COLORS[name] ?? '#888')}
          boxFillOpacity={browserMode ? 0.15 : 0.08}
          viewportGrabbable={browserMode}
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
              x={(boxStart / docLen) * barWidth} y={0}
              width={Math.max(2, ((boxEnd - boxStart) / docLen) * barWidth)}
              height={12} fill={browserMode ? '#0a84ff' : '#f1c40f'} fillOpacity={browserMode ? 0.15 : 0.1}
              stroke={browserMode ? '#ff453a' : 'none'} strokeWidth={browserMode ? 1 : 0}
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
