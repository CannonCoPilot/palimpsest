import { useEffect, useRef, useCallback, useState, useMemo, memo, Fragment, type ReactElement } from 'react';
import { useProjectStore, getActiveProject } from '../../stores/projectStore';
import { useSectionStore } from '../../stores/sectionStore';
import { useMaskOverlayStore, effectiveMaskByType, effectiveSections } from '../../stores/maskOverlayStore';
import { computeMaskedIntervals } from '../../utils/sectionMasking';
import { useTrackStore } from '../../stores/trackStore';
import { useBrowserStore, LANE_HEIGHTS, type LaneDisplayMode } from '../../stores/browserStore';
import { useViewStore } from '../../stores/viewStore';
import { useVerseStore } from '../../stores/verseStore';
import { TRACK_COLORS } from '../../utils/trackColors';
import { buildElementGroups } from '../../utils/maskTypeGroups';
import BrowserToolbar from './BrowserToolbar';
import TrackDrawer from './TrackDrawer';
import ElementGroupLane from './ElementGroupLane';
import VersesLane from './VersesLane';
import { AnnotationDetail } from '../DetailPanel/DetailPanel';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';

// The Verses lane is only shown once the viewport is zoomed in below this many characters
// (verses are too dense to be legible — or cheap to render — at a wider span).
const VERSE_ZOOM_MAX_CHARS = 30000;

interface TickerTapeProps {
  viewStart: number;
  viewEnd: number;
  referenceText: string;
  containerWidth: number;
  highlight: { start: number; end: number; color: string } | null;
  textHighlightAnns: Array<{ start: number; end: number; color: string }>;
  maskedIntervals: Array<[number, number]>;
  locationLabel: string;
}

function TickerTape({ viewStart, viewEnd, referenceText, containerWidth, highlight, textHighlightAnns, maskedIntervals, locationLabel }: TickerTapeProps) {
  const width = viewEnd - viewStart;
  const charsPerPixel = width / Math.max(1, containerWidth);
  const tooZoomedOut = charsPerPixel > 2;

  if (tooZoomedOut) {
    // Too zoomed out to render glyphs: show the current Book : Chapter for orientation
    // (updates live as the viewport pans/zooms) instead of a "zoom in" message.
    return (
      <div className="h-10 flex items-center gap-2 px-3 text-[0.85em] bg-[var(--color-bg)] border-b border-[var(--color-border)] select-none">
        <span className="font-[var(--font-sans)] font-semibold text-[var(--color-text)]">
          {locationLabel || '—'}
        </span>
        <span className="text-[0.8em] text-[var(--color-text-muted)]">
          (zoom in to read text · {Math.round(width).toLocaleString()} chars in view)
        </span>
      </div>
    );
  }

  const text = referenceText.slice(viewStart, viewEnd);

  // Build highlight spans for the visible range
  type Span = { start: number; end: number; color: string; isSelected: boolean; masked?: boolean };
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
  // Masked (analysis-excluded) ranges: near-white text on dark-gray.
  for (const [a, b] of maskedIntervals) {
    const s = Math.max(a, viewStart);
    const e = Math.min(b, viewEnd);
    if (s < e) spans.push({ start: s - viewStart, end: e - viewStart, color: '#3a3a3d', isSelected: false, masked: true });
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
  const fragments: ReactElement[] = [];
  let cursor = 0;
  for (let i = 0; i < spans.length; i++) {
    const span = spans[i];
    if (cursor < span.start) {
      fragments.push(<span key={`t${i}`}>{text.slice(cursor, span.start)}</span>);
    }
    fragments.push(
      <span
        key={`h${i}`}
        style={
          span.masked
            ? { backgroundColor: '#3a3a3d', color: '#f5f5f5', borderRadius: 2 }
            : {
                backgroundColor: span.color,
                opacity: span.isSelected ? 0.4 : 0.2,
                borderBottom: span.isSelected ? `2px solid ${span.color}` : undefined,
                borderRadius: 2,
              }
        }
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
  { mode: 'expanded', label: 'Expanded', icon: '▥' },
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

const TrackLane = memo(function TrackLane({ name, annotations, color, viewStart, viewEnd, width, displayMode, textHighlightActive, selectedAnnRange, onAnnotationClick }: TrackLaneProps) {
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

          if (displayMode === 'detail' || displayMode === 'expanded') {
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
});

export default function BrowserView() {
  const referenceText = useProjectStore((s) => getActiveProject(s).referenceText);
  const tracks = useProjectStore((s) => getActiveProject(s).tracks);
  const paragraphs = useProjectStore((s) => getActiveProject(s).paragraphs);
  const trackStates = useTrackStore((s) => s.tracks);
  const trackOrder = useTrackStore((s) => s.trackOrder);

  const { viewStart, viewEnd, totalChars, laneDisplayModes, textHighlightTracks, highlightedAnnotation, drawerOpen, hiddenGroups } = useBrowserStore();
  const { setTotalChars, pan } = useBrowserStore();
  const selectedAnnotation = useViewStore((s) => s.selectedAnnotation);
  const [popupAnn, setPopupAnn] = useState<W3CAnnotation | null>(null);

  // The Verses lane (and the verse-number mask layer) only matter once zoomed in close.
  // Guard on totalChars matching the loaded text: browserStore's default viewEnd (10000)
  // is itself < the threshold, so without this the lane would fetch eagerly during the
  // brief window before setTotalChars widens the view to the full document.
  const versesActive =
    referenceText.length > 0 &&
    totalChars === referenceText.length &&
    viewEnd - viewStart < VERSE_ZOOM_MAX_CHARS;

  // Masked (analysis-excluded) ranges for this project, if its layout has been configured.
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const secProjectId = useSectionStore((s) => s.projectId);
  const secSections = useSectionStore((s) => s.sections);
  const secMask = useSectionStore((s) => s.maskByType);
  const secTextLen = useSectionStore((s) => s.textLen);

  // On-demand masking overlay (non-destructive session selection layered over the layout).
  const ovEnabled = useMaskOverlayStore((s) => s.enabled);
  const ovTypeOverrides = useMaskOverlayStore((s) => s.typeOverrides);
  const ovSectionOverrides = useMaskOverlayStore((s) => s.sectionOverrides);

  // Lazy verse index: drives both the Verses lane and the verse-number mask layer.
  const verseProjectId = useVerseStore((s) => s.projectId);
  const verseRecords = useVerseStore((s) => s.records);
  const verseNumIntervals = useVerseStore((s) => s.numIntervals);
  const versesLoaded = verseProjectId === activeProjectId;

  // Fetch the verse index the first time the user zooms in past the threshold; the store
  // is idempotent, so this fires at most one network request per project.
  useEffect(() => {
    if (versesActive && activeProjectId) void useVerseStore.getState().load(activeProjectId);
  }, [versesActive, activeProjectId]);

  const maskedIntervals = useMemo(
    () => {
      if (!ovEnabled || !secProjectId || secProjectId !== activeProjectId) return [];
      // Union the verse-number tokens ([ns, s) per verse) on top of structural masking so
      // the `C:V.` tokens gray out in the readable TickerTape — mirroring the backend's
      // _verse_num_intervals union. Numbers gray once the lazy index has loaded.
      // The overlay's per-type and per-element overrides apply before computing the set.
      const extra = versesLoaded ? verseNumIntervals : [];
      const effSections = effectiveSections(secSections, ovSectionOverrides);
      const effMask = effectiveMaskByType(secMask, ovTypeOverrides);
      return computeMaskedIntervals(effSections, effMask, secTextLen, extra);
    },
    [ovEnabled, secProjectId, activeProjectId, secSections, secMask, secTextLen,
     ovSectionOverrides, ovTypeOverrides, versesLoaded, verseNumIntervals],
  );

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
      const { viewStart: vs, viewEnd: ve, pan: doPan, zoomAroundCenter: doZoom } = useBrowserStore.getState();
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        doZoom(e.deltaY > 0 ? 1.3 : 0.7);
        return;
      }
      // Note G: horizontal (side) swipe pans the tracks forward/back; vertical swipe is left
      // to native page scroll (the viewport is overflow-y-auto), so up/down moves the page.
      if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
        e.preventDefault();
        const range = ve - vs;
        doPan(e.deltaX * (range / 1000));
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

  // Remembers the last annotation selected *from this Browser* so the Reader→Browser
  // sync effect below doesn't re-zoom the viewport onto a selection it just originated.
  const lastBrowserSelectId = useRef<string | null>(null);

  const handleAnnotationClick = useCallback((ann: W3CAnnotation, trackName: string) => {
    const sel = ann.target.selector;
    lastBrowserSelectId.current = ann.id;
    const view = useViewStore.getState();
    view.selectAnnotation(ann);
    if (sel.start != null && sel.end != null) {
      useBrowserStore.getState().setHighlightedAnnotation({ start: sel.start, end: sel.end, trackName });
      // Note A: don't steal focus to the Reader. Stage a scroll request to this element's
      // paragraph; the Reader tab only mounts when activated, so the scroll fires lazily when
      // the user switches to it — clicking a Browser element never yanks the view away.
      const para = paragraphs.find((p) => p.start <= sel.start! && sel.start! < p.end);
      if (para) view.requestScrollToParagraph(para.index);
    }
  }, [paragraphs]);

  const handleAnnotationDoubleClick = useCallback((ann: W3CAnnotation) => {
    setPopupAnn(ann);
  }, []);

  // Item 5: selecting an element elsewhere (e.g. the Reader) moves the Browser viewport
  // onto it. Skip selections that originated here to avoid a focus feedback loop.
  useEffect(() => {
    if (!selectedAnnotation) return;
    if (selectedAnnotation.id === lastBrowserSelectId.current) return;
    const sel = selectedAnnotation.target.selector;
    if (sel.start == null || sel.end == null) return;
    const b = useBrowserStore.getState();
    const pad = Math.max(40, Math.round((sel.end - sel.start) * 2));
    b.zoomToRange(Math.max(0, sel.start - pad), sel.end + pad);
    b.setHighlightedAnnotation({ start: sel.start, end: sel.end, trackName: 'elements' });
  }, [selectedAnnotation]);

  const visibleTracks = useMemo(
    () => trackOrder.filter((name) => {
      const state = trackStates[name];
      const mode = laneDisplayModes[name] ?? 'ribbon';
      return state?.visible && name !== 'segments' && mode !== 'hidden';
    }),
    [trackOrder, trackStates, laneDisplayModes],
  );

  // The unified "elements" track is rendered as one lane per related-type group
  // (Structure / Content / Headings / Notes); empty or user-hidden groups drop out.
  const elementGroups = useMemo(
    () => buildElementGroups(tracks['elements'] ?? []).filter((g) => !hiddenGroups.has(g.key)),
    [tracks, hiddenGroups],
  );

  // Item 3: Book : Chapter at the viewport center, from `section` spans (gold-faithful),
  // updating live as the viewport pans/zooms.
  const sectionSpans = useMemo(() => {
    const out: Array<{ start: number; end: number; title: string }> = [];
    for (const a of tracks['elements'] ?? []) {
      const b = a.body as Record<string, unknown>;
      if (b['palimpsest:elementType'] !== 'section') continue;
      const sel = a.target.selector;
      if (sel.start == null || sel.end == null) continue;
      out.push({ start: sel.start, end: sel.end, title: String(b['palimpsest:chapterTitle'] ?? a.body.value ?? '') });
    }
    return out.sort((x, y) => x.start - y.start);
  }, [tracks]);

  const locationLabel = useMemo(() => {
    const center = (viewStart + viewEnd) / 2;
    let label = '';
    for (const s of sectionSpans) {
      if (s.start > center) break;
      label = s.title;            // nearest preceding span keeps the book in view across gaps
      if (center < s.end) break;  // exact containing span
    }
    return label.replace(' Chapter ', ' : Chapter ');
  }, [sectionSpans, viewStart, viewEnd]);

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
      <div className="h-6 flex items-center px-3 gap-2 text-[0.78em] bg-[var(--color-bg-subtle)] border-b border-[var(--color-border-subtle)] select-none">
        <span className="text-[var(--color-text-muted)]">Location</span>
        <span className="font-[var(--font-sans)] font-semibold text-[var(--color-text)] truncate">{locationLabel || '—'}</span>
      </div>
      <div
        ref={viewportRef}
        // overscroll-x-none + overflow-x-hidden stop Chrome/macOS two-finger horizontal swipe
        // from triggering browser back/forward nav while hovering the track view; the wheel
        // handler turns that side-swipe into track side-scroll (pan) instead.
        className="flex-1 flex flex-col overflow-y-auto overflow-x-hidden overscroll-x-none cursor-grab active:cursor-grabbing"
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
          maskedIntervals={maskedIntervals}
          locationLabel={locationLabel}
        />
        <div className="flex-1 overflow-y-auto">
          {visibleTracks.map((name) => {
            if (name === 'elements') {
              const elSel = highlightedAnnotation && highlightedAnnotation.trackName === 'elements' ? highlightedAnnotation : null;
              return (
                <Fragment key="elements">
                  {elementGroups.map((g) => {
                    const laneKey = `elements:${g.key}`;
                    return (
                      <ElementGroupLane
                        key={laneKey}
                        group={g}
                        laneKey={laneKey}
                        viewStart={viewStart}
                        viewEnd={viewEnd}
                        width={viewportWidth}
                        displayMode={laneDisplayModes[laneKey] ?? 'ribbon'}
                        selectedAnnRange={elSel}
                        onAnnotationClick={handleAnnotationClick}
                        onAnnotationDoubleClick={handleAnnotationDoubleClick}
                      />
                    );
                  })}
                  {/* The Verses lane lazy-loads from verses.jsonl and auto-hides until the
                      viewport is zoomed in below VERSE_ZOOM_MAX_CHARS — both a legibility
                      gate and a guard against walking tens of thousands of verses per pan. */}
                  {versesActive && versesLoaded && verseRecords.length > 0 && (
                    <VersesLane
                      records={verseRecords}
                      viewStart={viewStart}
                      viewEnd={viewEnd}
                      width={viewportWidth}
                    />
                  )}
                </Fragment>
              );
            }
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
      {popupAnn && <ElementDetailPopup ann={popupAnn} onClose={() => setPopupAnn(null)} />}
    </div>
  );
}

// Item 6: floating element-details popup opened by double-clicking a Browser element.
function ElementDetailPopup({ ann, onClose }: { ann: W3CAnnotation; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    const onDown = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) onClose(); };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onDown);
    return () => { document.removeEventListener('keydown', onKey); document.removeEventListener('mousedown', onDown); };
  }, [onClose]);
  return (
    <div className="absolute inset-0 z-[var(--z-modal)] flex items-center justify-center bg-black/30">
      <div ref={ref} className="w-[380px] max-h-[70%] overflow-y-auto bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg shadow-[var(--shadow-popover)] p-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[0.8em] font-semibold text-[var(--color-text-muted)]">Element details</span>
          <button onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer text-[1.1em] leading-none">×</button>
        </div>
        <AnnotationDetail ann={ann} />
      </div>
    </div>
  );
}
