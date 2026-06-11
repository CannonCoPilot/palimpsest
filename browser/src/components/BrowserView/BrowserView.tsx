import { useEffect, useRef, useCallback, useState } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useTrackStore } from '../../stores/trackStore';
import { useBrowserStore, LANE_HEIGHTS, type LaneDisplayMode } from '../../stores/browserStore';
import { useViewStore } from '../../stores/viewStore';
import { TRACK_COLORS } from '../../utils/trackColors';
import BrowserToolbar from './BrowserToolbar';
import TrackDrawer from './TrackDrawer';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';

interface TickerTapeProps {
  viewStart: number;
  viewEnd: number;
  referenceText: string;
  containerWidth: number;
  highlight: { start: number; end: number; color: string } | null;
  textHighlightAnns: Array<{ start: number; end: number; color: string }>;
}

function TickerTape({ viewStart, viewEnd, referenceText, containerWidth, highlight, textHighlightAnns }: TickerTapeProps) {
  const width = viewEnd - viewStart;
  const charsPerPixel = width / Math.max(1, containerWidth);
  const tooZoomedOut = charsPerPixel > 2;

  if (tooZoomedOut) {
    return (
      <div className="h-8 flex items-center justify-center text-[0.75em] text-[var(--color-text-muted)] bg-[var(--color-bg)] border-b border-[var(--color-border)]">
        Zoom in to see text (currently viewing {Math.round(width).toLocaleString()} characters)
      </div>
    );
  }

  const text = referenceText.slice(viewStart, viewEnd);
  const charWidth = containerWidth / width;

  // Build highlight spans for the visible range
  type Span = { start: number; end: number; color: string; isSelected: boolean };
  const spans: Span[] = [];

  for (const ann of textHighlightAnns) {
    const s = Math.max(ann.start, viewStart);
    const e = Math.min(ann.end, viewEnd);
    if (s < e) spans.push({ start: s - viewStart, end: e - viewStart, color: ann.color, isSelected: false });
  }
  if (highlight) {
    const s = Math.max(highlight.start, viewStart);
    const e = Math.min(highlight.end, viewEnd);
    if (s < e) spans.push({ start: s - viewStart, end: e - viewStart, color: highlight.color, isSelected: true });
  }

  if (spans.length === 0) {
    return (
      <div className="h-10 overflow-hidden whitespace-nowrap text-[0.85em] leading-[40px] px-2 bg-[var(--color-bg)] border-b border-[var(--color-border)] font-[var(--font-serif)] select-none">
        {text}
      </div>
    );
  }

  // Sort spans by start position
  spans.sort((a, b) => a.start - b.start);

  // Build text fragments with highlight backgrounds
  const fragments: JSX.Element[] = [];
  let cursor = 0;
  for (let i = 0; i < spans.length; i++) {
    const span = spans[i];
    if (cursor < span.start) {
      fragments.push(<span key={`t${i}`}>{text.slice(cursor, span.start)}</span>);
    }
    fragments.push(
      <span
        key={`h${i}`}
        style={{
          backgroundColor: span.color,
          opacity: span.isSelected ? 0.4 : 0.2,
          borderBottom: span.isSelected ? `2px solid ${span.color}` : undefined,
          borderRadius: 2,
        }}
      >
        {text.slice(span.start, span.end)}
      </span>
    );
    cursor = span.end;
  }
  if (cursor < text.length) {
    fragments.push(<span key="tail">{text.slice(cursor)}</span>);
  }

  return (
    <div className="h-10 overflow-hidden whitespace-nowrap text-[0.85em] leading-[40px] px-2 bg-[var(--color-bg)] border-b border-[var(--color-border)] font-[var(--font-serif)] select-none">
      {fragments}
    </div>
  );
}

function formatAxisLabel(value: number, interval: number): string {
  if (interval >= 1000) return `${(value / 1000).toFixed(0)}k`;
  if (interval >= 100) return `${(value / 1000).toFixed(1)}k`;
  if (interval >= 10) return value.toLocaleString();
  return value.toString();
}

function CoordinateAxis({ viewStart, viewEnd, width }: { viewStart: number; viewEnd: number; width: number }) {
  const range = viewEnd - viewStart;
  const rawInterval = range / 5;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawInterval)));
  const normalized = rawInterval / magnitude;
  const niceMultiplier = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  const tickInterval = Math.max(1, niceMultiplier * magnitude);

  const firstTick = Math.ceil(viewStart / tickInterval) * tickInterval;
  const ticks: number[] = [];
  for (let t = firstTick; t <= viewEnd; t += tickInterval) {
    ticks.push(t);
  }

  return (
    <svg width={width} height={20} className="bg-[var(--color-bg-subtle)] border-t border-[var(--color-border)]">
      {ticks.map((t) => {
        const x = ((t - viewStart) / (viewEnd - viewStart)) * width;
        return (
          <g key={t}>
            <line x1={x} y1={0} x2={x} y2={6} stroke="var(--color-text-muted)" strokeWidth={1} />
            <text x={x} y={16} textAnchor="middle" fontSize={9} fill="var(--color-text-muted)" fontFamily="var(--font-mono)">
              {formatAxisLabel(t, tickInterval)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

const DISPLAY_MODE_OPTIONS: { mode: LaneDisplayMode; label: string; icon: string }[] = [
  { mode: 'ribbon', label: 'Ribbon', icon: '▬' },
  { mode: 'detail', label: 'Detail', icon: '▤' },
  { mode: 'condensed', label: 'Condensed', icon: '─' },
  { mode: 'hidden', label: 'Hide', icon: '✕' },
];

interface TrackLaneProps {
  name: string;
  annotations: W3CAnnotation[];
  color: string;
  viewStart: number;
  viewEnd: number;
  width: number;
  displayMode: LaneDisplayMode;
  textHighlightActive: boolean;
  selectedAnnRange: { start: number; end: number } | null;
  onAnnotationClick: (ann: W3CAnnotation, trackName: string) => void;
}

function TrackLane({ name, annotations, color, viewStart, viewEnd, width, displayMode, textHighlightActive, selectedAnnRange, onAnnotationClick }: TrackLaneProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const range = viewEnd - viewStart;
  const height = LANE_HEIGHTS[displayMode];

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [menuOpen]);

  const visibleAnns = annotations.filter((ann) => {
    const sel = ann.target.selector;
    if (sel.start == null || sel.end == null) return false;
    return sel.end > viewStart && sel.start < viewEnd;
  });

  return (
    <div className="flex border-b border-[var(--color-border-subtle)]">
      <div className="w-[100px] relative shrink-0" ref={menuRef}>
        <div
          className="h-full flex items-center gap-1 px-2 text-[0.7em] font-[var(--font-sans)] border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-muted)] cursor-pointer select-none"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
          <span className="truncate flex-1">{name}</span>
          <span className="text-[0.8em] text-[var(--color-text-muted)]">▾</span>
        </div>
        {menuOpen && (
          <div className="absolute top-full left-0 z-[var(--z-popover)] w-[160px] bg-[var(--color-bg)] border border-[var(--color-border)] rounded shadow-[var(--shadow-popover)] py-1 text-[0.75em] font-[var(--font-sans)]">
            <div className="px-2 py-1 text-[var(--color-text-muted)] font-semibold">{name}</div>
            <div className="h-px bg-[var(--color-border-subtle)] my-0.5" />
            <button
              className={`w-full text-left px-2 py-1 hover:bg-[var(--color-bg-muted)] cursor-pointer flex items-center gap-1.5 ${textHighlightActive ? 'text-[var(--color-primary)]' : ''}`}
              onClick={() => { useBrowserStore.getState().toggleTextHighlight(name); setMenuOpen(false); }}
            >
              <span>{textHighlightActive ? '✓' : ' '}</span>
              Highlight in text
            </button>
            <div className="h-px bg-[var(--color-border-subtle)] my-0.5" />
            {DISPLAY_MODE_OPTIONS.map((opt) => (
              <button
                key={opt.mode}
                className={`w-full text-left px-2 py-1 hover:bg-[var(--color-bg-muted)] cursor-pointer flex items-center gap-1.5 ${displayMode === opt.mode ? 'font-semibold text-[var(--color-primary)]' : ''}`}
                onClick={() => { useBrowserStore.getState().setLaneDisplayMode(name, opt.mode); setMenuOpen(false); }}
              >
                <span className="w-3 text-center">{opt.icon}</span>
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>
      <svg width={width} height={height} className="shrink-0">
        {visibleAnns.map((ann, i) => {
          const sel = ann.target.selector;
          const start = Math.max(sel.start!, viewStart);
          const end = Math.min(sel.end!, viewEnd);
          const x = ((start - viewStart) / range) * width;
          const w = Math.max(1, ((end - start) / range) * width);

          const isSelected = selectedAnnRange && sel.start === selectedAnnRange.start && sel.end === selectedAnnRange.end;

          if (displayMode === 'detail') {
            const label = ann.body.value || ann.body.type.replace('palimpsest:', '');
            return (
              <g key={i} className="cursor-pointer" onClick={() => onAnnotationClick(ann, name)}>
                <rect x={x} y={2} width={w} height={24} fill={color} fillOpacity={isSelected ? 1 : 0.7} rx={2} />
                <text x={x + 2} y={16} fontSize={9} fill="white" fontFamily="var(--font-sans)" className="pointer-events-none">
                  {w > 30 ? label.slice(0, Math.floor(w / 6)) : ''}
                </text>
                <text x={x + 2} y={38} fontSize={8} fill="var(--color-text-muted)" fontFamily="var(--font-mono)" className="pointer-events-none">
                  {w > 50 ? `${sel.start}–${sel.end}` : ''}
                </text>
                {isSelected && <rect x={x} y={0} width={w} height={height} fill="none" stroke="var(--color-primary)" strokeWidth={2} rx={2} />}
              </g>
            );
          }

          return (
            <rect
              key={i}
              x={x}
              y={displayMode === 'condensed' ? 1 : 2}
              width={w}
              height={height - (displayMode === 'condensed' ? 2 : 4)}
              fill={color}
              fillOpacity={isSelected ? 1 : 0.7}
              rx={displayMode === 'condensed' ? 1 : 2}
              className="cursor-pointer"
              onClick={() => onAnnotationClick(ann, name)}
            >
              <title>{ann.body.value || ann.body.type.replace('palimpsest:', '')}</title>
            </rect>
          );
        })}
      </svg>
    </div>
  );
}

export default function BrowserView() {
  const referenceText = useProjectStore((s) => s.referenceText);
  const tracks = useProjectStore((s) => s.tracks);
  const trackStates = useTrackStore((s) => s.tracks);
  const trackOrder = useTrackStore((s) => s.trackOrder);

  const { viewStart, viewEnd, totalChars, laneDisplayModes, textHighlightTracks, highlightedAnnotation, drawerOpen } = useBrowserStore();
  const { setTotalChars, pan } = useBrowserStore();

  const viewportRef = useRef<HTMLDivElement>(null);
  const [viewportWidth, setViewportWidth] = useState(800);
  const isDragging = useRef(false);
  const dragLastX = useRef(0);

  useEffect(() => {
    if (referenceText.length > 0 && referenceText.length !== totalChars) {
      setTotalChars(referenceText.length);
    }
  }, [referenceText.length, totalChars, setTotalChars]);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setViewportWidth(Math.max(200, entry.contentRect.width - 100));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const { viewStart: vs, viewEnd: ve, pan: doPan, zoomAroundCenter: doZoom } = useBrowserStore.getState();
      if (e.ctrlKey || e.metaKey) {
        const factor = e.deltaY > 0 ? 1.3 : 0.7;
        doZoom(factor);
      } else {
        const range = ve - vs;
        const delta = (e.deltaX || e.deltaY) * (range / 1000);
        doPan(delta);
      }
    };
    el.addEventListener('wheel', handler, { passive: false });
    return () => el.removeEventListener('wheel', handler);
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    isDragging.current = true;
    dragLastX.current = e.clientX;
    e.preventDefault();
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging.current) return;
    const dx = e.clientX - dragLastX.current;
    dragLastX.current = e.clientX;
    const range = viewEnd - viewStart;
    const charsPerPixel = range / viewportWidth;
    pan(-dx * charsPerPixel);
  }, [viewStart, viewEnd, viewportWidth, pan]);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  const handleAnnotationClick = useCallback((ann: W3CAnnotation, trackName: string) => {
    const sel = ann.target.selector;
    if (sel.start != null && sel.end != null) {
      useBrowserStore.getState().setHighlightedAnnotation({ start: sel.start, end: sel.end, trackName });
    }
    useViewStore.getState().selectAnnotation(ann);
  }, []);

  const visibleTracks = trackOrder.filter((name) => {
    const state = trackStates[name];
    const mode = laneDisplayModes[name] ?? 'ribbon';
    return state?.visible && name !== 'segments' && mode !== 'hidden';
  });

  // Build text highlight annotations from enabled tracks
  const textHighlightAnns: Array<{ start: number; end: number; color: string }> = [];
  for (const name of Array.from(textHighlightTracks)) {
    const anns = tracks[name];
    const color = TRACK_COLORS[name] ?? '#888';
    if (!anns) continue;
    for (const ann of anns) {
      const sel = ann.target.selector;
      if (sel.start != null && sel.end != null && sel.end > viewStart && sel.start < viewEnd) {
        textHighlightAnns.push({ start: sel.start, end: sel.end, color });
      }
    }
  }

  const highlightForTape = highlightedAnnotation
    ? { start: highlightedAnnotation.start, end: highlightedAnnotation.end, color: TRACK_COLORS[highlightedAnnotation.trackName] ?? '#333' }
    : null;

  return (
    <div className="flex-1 flex flex-col overflow-hidden select-none relative">
      <BrowserToolbar />
      <div
        ref={viewportRef}
        className="flex-1 flex flex-col overflow-y-auto cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <TickerTape
          viewStart={viewStart}
          viewEnd={viewEnd}
          referenceText={referenceText}
          containerWidth={viewportWidth}
          highlight={highlightForTape}
          textHighlightAnns={textHighlightAnns}
        />
        <div className="flex-1 overflow-y-auto">
          {visibleTracks.map((name) => {
            const mode = laneDisplayModes[name] ?? 'ribbon';
            return (
              <TrackLane
                key={name}
                name={name}
                annotations={tracks[name] ?? []}
                color={TRACK_COLORS[name] ?? '#888'}
                viewStart={viewStart}
                viewEnd={viewEnd}
                width={viewportWidth}
                displayMode={mode}
                textHighlightActive={textHighlightTracks.has(name)}
                selectedAnnRange={highlightedAnnotation && highlightedAnnotation.trackName === name ? highlightedAnnotation : null}
                onAnnotationClick={handleAnnotationClick}
              />
            );
          })}
          {visibleTracks.length === 0 && (
            <div className="flex items-center justify-center h-32 text-[var(--color-text-muted)] text-[0.85em]">
              No visible tracks. Open the track drawer to enable tracks.
            </div>
          )}
        </div>
        <CoordinateAxis viewStart={viewStart} viewEnd={viewEnd} width={viewportWidth} />
      </div>
      {drawerOpen && <TrackDrawer />}
    </div>
  );
}
