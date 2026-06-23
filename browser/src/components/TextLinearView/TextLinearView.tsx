/**
 * TextLinearView — main reading area with semantic zoom (4 levels).
 * Work → Chapter → Paragraph → Sentence
 */

import { useCallback, useEffect, useMemo, useRef, type ReactElement } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useProjectStore, getActiveProject, type Paragraph } from '../../stores/projectStore';
import { useTrackStore, type TrackState } from '../../stores/trackStore';
import { useElementVisibilityStore } from '../../stores/elementVisibilityStore';
import { useViewStore } from '../../stores/viewStore';
import { useSearchStore, type SearchMatch } from '../../stores/searchStore';
import { useSectionStore } from '../../stores/sectionStore';
import { useVerseStore } from '../../stores/verseStore';
import { useMaskOverlayStore, effectiveMaskByType, effectiveSections } from '../../stores/maskOverlayStore';
import { computeMaskedIntervals } from '../../utils/sectionMasking';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { TRACK_COLORS } from '../../utils/trackColors';
import AnnotationOverlay from './AnnotationOverlay';

type MaskedRange = readonly [number, number];
const EMPTY_MASKED: ReadonlyArray<MaskedRange> = [];

/**
 * Bucket the merged masked intervals by paragraph so each paragraph overlay only sees its
 * own (small) slice. Both inputs are ordered by start, so one forward sweep suffices; an
 * interval straddling a paragraph boundary is recorded in every paragraph it overlaps.
 */
function bucketMaskedByParagraph(
  paragraphs: Paragraph[],
  intervals: ReadonlyArray<MaskedRange>,
): Map<number, MaskedRange[]> {
  const out = new Map<number, MaskedRange[]>();
  if (paragraphs.length === 0 || intervals.length === 0) return out;
  let j = 0;
  for (const p of paragraphs) {
    while (j < intervals.length && intervals[j][1] <= p.start) j++;
    for (let k = j; k < intervals.length && intervals[k][0] < p.end; k++) {
      if (intervals[k][1] > p.start) {
        let arr = out.get(p.index);
        if (!arr) { arr = []; out.set(p.index, arr); }
        arr.push(intervals[k]);
      }
    }
  }
  return out;
}

/**
 * Build a stable string key representing per-track visibility/threshold/displayMode.
 * This lets useMemo only invalidate when something annotation-relevant actually changes,
 * rather than on every object-reference change to the tracks map.
 */
function buildTrackVisibilityKey(trackStates: Record<string, TrackState>): string {
  return Object.keys(trackStates)
    .sort()
    .map((n) => {
      const s = trackStates[n];
      return `${n}:${s.visible ? 1 : 0}:${s.confidenceThreshold}:${s.displayMode}`;
    })
    .join(',');
}

const VIRTUALIZE_THRESHOLD = 200;

function collectVisibleAnnotations(
  tracks: Record<string, W3CAnnotation[]>,
  trackStates: Record<string, TrackState>,
  hiddenElementTypes: Record<string, boolean>,
): W3CAnnotation[] {
  const all: W3CAnnotation[] = [];
  for (const [name, anns] of Object.entries(tracks)) {
    if (name === 'segments') continue;
    const state = trackStates[name];
    if (state && !state.visible) continue;
    if (state?.displayMode === 'dense') continue;
    const threshold = state?.confidenceThreshold ?? 0;
    let filtered = threshold > 0
      ? anns.filter((a) => (a['palimpsest:confidence'] ?? 1) >= threshold)
      : anns;
    // #27 — within the unified elements track, hide individually-toggled subtypes.
    if (name === 'elements') {
      filtered = filtered.filter((a) => {
        const et = (a.body as Record<string, unknown>)['palimpsest:elementType'];
        return !(typeof et === 'string' && hiddenElementTypes[et]);
      });
    }
    all.push(...filtered);
  }
  return all;
}

const EMPTY_ANNS: W3CAnnotation[] = [];

/**
 * Bucket annotations into per-paragraph slices keyed by paragraph index.
 *
 * Previously every paragraph overlay received the full annotation array and
 * re-filtered it (O(paragraphs × annotations) on every track toggle). Bucketing
 * once — O(annotations · log paragraphs) via binary search on paragraph starts —
 * lets each overlay build segments over only its own (small) slice. `paragraphs`
 * is ordered by `start`, so a binary search finds the first overlapping paragraph
 * and a forward scan collects the rest.
 */
export function bucketAnnotationsByParagraph(
  paragraphs: Paragraph[],
  annotations: W3CAnnotation[],
): Map<number, W3CAnnotation[]> {
  const buckets = new Map<number, W3CAnnotation[]>();
  if (paragraphs.length === 0) return buckets;
  for (const ann of annotations) {
    const sel = ann.target.selector;
    if (sel.start == null || sel.end == null) continue;
    let lo = 0;
    let hi = paragraphs.length - 1;
    let first = paragraphs.length;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (paragraphs[mid].end > sel.start) { first = mid; hi = mid - 1; }
      else lo = mid + 1;
    }
    for (let i = first; i < paragraphs.length && paragraphs[i].start < sel.end; i++) {
      const key = paragraphs[i].index;
      let arr = buckets.get(key);
      if (!arr) { arr = []; buckets.set(key, arr); }
      arr.push(ann);
    }
  }
  return buckets;
}

function estimateRowHeight(text: string): number {
  const charsPerLine = 80;
  const lineHeight = 27;
  const lines = Math.ceil(text.length / charsPerLine);
  return Math.max(40, lines * lineHeight + 20);
}

// ── Section block for work-level zoom ──

interface SectionBlock {
  index: number;
  heading: string;
  startPara: number;
  endPara: number;
  paraCount: number;
  charStart: number;
  charEnd: number;
}

function buildSectionBlocks(
  paragraphs: Paragraph[],
  tracks: Record<string, W3CAnnotation[]>,
): SectionBlock[] {
  const sectionAnns = (tracks['sections'] ?? [])
    .filter((a) => a.target.selector.start != null)
    .sort((a, b) => (a.target.selector.start ?? 0) - (b.target.selector.start ?? 0));

  if (sectionAnns.length === 0 && paragraphs.length > 0) {
    return [{
      index: 0,
      heading: 'Full Text',
      startPara: 0,
      endPara: paragraphs.length - 1,
      paraCount: paragraphs.length,
      charStart: paragraphs[0].start,
      charEnd: paragraphs[paragraphs.length - 1].end,
    }];
  }

  const blocks: SectionBlock[] = [];
  for (let i = 0; i < sectionAnns.length; i++) {
    const ann = sectionAnns[i];
    const body = ann.body as Record<string, unknown>;
    const heading = (body['palimpsest:headingText'] as string) || ann.body.value || `Section ${i + 1}`;
    const charStart = ann.target.selector.start ?? 0;
    const charEnd = i < sectionAnns.length - 1
      ? (sectionAnns[i + 1].target.selector.start ?? paragraphs[paragraphs.length - 1]?.end ?? charStart)
      : (paragraphs[paragraphs.length - 1]?.end ?? charStart);

    const startPara = paragraphs.findIndex((p) => p.start >= charStart);
    const endPara = i < sectionAnns.length - 1
      ? paragraphs.findIndex((p) => p.start >= charEnd) - 1
      : paragraphs.length - 1;

    blocks.push({
      index: i,
      heading,
      startPara: startPara >= 0 ? startPara : 0,
      endPara: endPara >= 0 ? endPara : paragraphs.length - 1,
      paraCount: Math.max(0, (endPara >= 0 ? endPara : paragraphs.length - 1) - (startPara >= 0 ? startPara : 0) + 1),
      charStart,
      charEnd,
    });
  }
  return blocks;
}

function countAnnotationsInRange(
  annotations: W3CAnnotation[],
  start: number,
  end: number,
): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const ann of annotations) {
    const sel = ann.target.selector;
    if (sel.start != null && sel.end != null && sel.start < end && sel.end > start) {
      const track = ann.body.type.replace('palimpsest:', '').replace('Annotation', '').toLowerCase();
      counts[track] = (counts[track] || 0) + 1;
    }
  }
  return counts;
}

// ── Work-level zoom ──

function WorkLevelView({ sectionBlocks, annotations }: {
  sectionBlocks: SectionBlock[];
  annotations: W3CAnnotation[];
}): ReactElement {
  const setZoom = useViewStore((s) => s.setZoomLevel);
  const requestScroll = useViewStore((s) => s.requestScrollToParagraph);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 font-[var(--font-serif)]">
      {sectionBlocks.map((block) => {
        const counts = countAnnotationsInRange(annotations, block.charStart, block.charEnd);
        const trackNames = Object.keys(counts).sort();
        return (
          <div
            key={block.index}
            onClick={() => {
              requestScroll(block.startPara);
              setZoom('chapter');
            }}
            className="px-4 py-3 mb-2 border border-[var(--color-border-subtle)] rounded-md cursor-pointer transition-colors bg-[var(--color-bg-subtle)] hover:bg-[#f0f7ff] hover:shadow-sm"
          >
            <div className="font-bold text-[1em] mb-1">{block.heading}</div>
            <div className="text-[var(--color-text-muted)] text-[0.8em] mb-1.5">{block.paraCount} paragraphs</div>
            <div className="flex gap-1 flex-wrap">
              {trackNames.map((track) => {
                const color = TRACK_COLORS[track] ?? '#888';
                return (
                  <span
                    key={track}
                    className="inline-block px-1.5 py-px rounded text-[0.7em] font-bold"
                    style={{ backgroundColor: `${color}22`, color }}
                  >
                    {track}: {counts[track]}
                  </span>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Chapter-level zoom ──

function ChapterLevelView({ paragraphs, annotations }: {
  paragraphs: Paragraph[];
  annotations: W3CAnnotation[];
}): ReactElement {
  const setZoom = useViewStore((s) => s.setZoomLevel);
  const requestScroll = useViewStore((s) => s.requestScrollToParagraph);
  const selectedParagraphIndex = useViewStore((s) => s.selectedParagraphIndex);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRequest = useViewStore((s) => s.scrollToParagraphRequest);
  const clearScrollRequest = useViewStore((s) => s.clearScrollRequest);

  const virtualizer = useVirtualizer({
    count: paragraphs.length,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 28,
    overscan: 30,
  });

  useEffect(() => {
    if (scrollRequest !== null) {
      virtualizer.scrollToIndex(scrollRequest, { align: 'center', behavior: 'smooth' });
      clearScrollRequest();
    }
  }, [scrollRequest, clearScrollRequest, virtualizer]);

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-2 font-[var(--font-serif)] text-[0.85rem]"
    >
      <div style={{ height: `${virtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}>
        {virtualizer.getVirtualItems().map((vRow) => {
          const p = paragraphs[vRow.index];
          const counts = countAnnotationsInRange(annotations, p.start, p.end);
          const trackNames = Object.keys(counts);
          const isSelected = selectedParagraphIndex === p.index;
          const preview = p.text.length > 120 ? p.text.slice(0, 120) + '...' : p.text;
          return (
            <div
              key={p.index}
              ref={virtualizer.measureElement}
              data-index={vRow.index}
              onClick={() => {
                requestScroll(p.index);
                setZoom('paragraph');
              }}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${vRow.start}px)`,
                display: 'flex',
                alignItems: 'center',
                padding: '3px 8px',
                borderLeft: isSelected ? '3px solid #3498db' : '3px solid transparent',
                backgroundColor: isSelected ? '#f0f7ff' : 'transparent',
                cursor: 'pointer',
                gap: '8px',
              }}
              onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = '#fafafa'; }}
              onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent'; }}
            >
              <span className="text-[var(--color-text-muted)] text-[0.75em] w-[30px] text-right shrink-0">
                {p.index + 1}
              </span>
              <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-[var(--color-text)]">
                {preview}
              </span>
              <span className="flex gap-0.5 shrink-0">
                {trackNames.slice(0, 5).map((t) => {
                  const color = TRACK_COLORS[t] ?? '#888';
                  return <span key={t} className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />;
                })}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Paragraph-level zoom (current default) ──

interface ParagraphViewProps {
  paragraph: Paragraph;
  annotations: W3CAnnotation[];
  searchMatches: SearchMatch[];
  currentMatchIndex: number;
  isSelected: boolean;
  onSelect: () => void;
  maskedRanges?: ReadonlyArray<MaskedRange>;
}

function ParagraphView({ paragraph, annotations, searchMatches, currentMatchIndex, isSelected, onSelect, maskedRanges }: ParagraphViewProps): ReactElement {
  return (
    <div
      data-para-index={paragraph.index}
      onClick={(e) => {
        onSelect();
        if (e.target === e.currentTarget) {
          useViewStore.getState().selectAnnotation(null);
        }
      }}
      className={`mb-4 px-2 py-1 border-l-[3px] cursor-pointer leading-[1.7] transition-colors ${isSelected ? 'border-l-[var(--color-primary)] bg-[#f0f7ff]' : 'border-l-transparent bg-transparent'}`}
    >
      <AnnotationOverlay
        text={paragraph.text}
        paraStart={paragraph.start}
        paraEnd={paragraph.end}
        annotations={annotations}
        searchMatches={searchMatches}
        currentMatchIndex={currentMatchIndex}
        maskedRanges={maskedRanges}
      />
    </div>
  );
}

function VirtualizedParagraphView({
  paragraphs, annotationsByPara, maskedByPara, searchMatches, currentMatchIndex,
  selectedParagraphIndex, setSelectedParagraphIndex, scrollRequest, clearScrollRequest,
}: {
  paragraphs: Paragraph[]; annotationsByPara: Map<number, W3CAnnotation[]>;
  maskedByPara: Map<number, MaskedRange[]>;
  searchMatches: SearchMatch[]; currentMatchIndex: number;
  selectedParagraphIndex: number | null; setSelectedParagraphIndex: (i: number | null) => void;
  scrollRequest: number | null; clearScrollRequest: () => void;
}): ReactElement {
  const containerRef = useRef<HTMLDivElement>(null);
  const setVisibleRange = useViewStore((s) => s.setVisibleParagraphRange);
  const virtualizer = useVirtualizer({
    count: paragraphs.length,
    getScrollElement: () => containerRef.current,
    estimateSize: (i) => estimateRowHeight(paragraphs[i].text),
    overscan: 10,
    onChange: (v) => {
      const items = v.getVirtualItems();
      if (items.length > 0) {
        setVisibleRange([items[0].index, items[items.length - 1].index]);
      }
    },
  });

  useEffect(() => {
    if (scrollRequest !== null) {
      virtualizer.scrollToIndex(scrollRequest, { align: 'center', behavior: 'smooth' });
      clearScrollRequest();
    }
  }, [scrollRequest, clearScrollRequest, virtualizer]);

  return (
    <div ref={containerRef} style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', fontFamily: "'Georgia', serif", fontSize: '1rem' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}>
        {virtualizer.getVirtualItems().map((vRow) => {
          const p = paragraphs[vRow.index];
          return (
            <div key={p.index} ref={virtualizer.measureElement} data-index={vRow.index}
              style={{ position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${vRow.start}px)` }}>
              <ParagraphView
                paragraph={p} annotations={annotationsByPara.get(p.index) ?? EMPTY_ANNS} searchMatches={searchMatches}
                currentMatchIndex={currentMatchIndex}
                maskedRanges={maskedByPara.get(p.index) ?? EMPTY_MASKED}
                isSelected={selectedParagraphIndex === p.index}
                onSelect={() => setSelectedParagraphIndex(selectedParagraphIndex === p.index ? null : p.index)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SimpleParagraphView({
  paragraphs, annotationsByPara, maskedByPara, searchMatches, currentMatchIndex,
  selectedParagraphIndex, setSelectedParagraphIndex, scrollRequest, clearScrollRequest,
}: {
  paragraphs: Paragraph[]; annotationsByPara: Map<number, W3CAnnotation[]>;
  maskedByPara: Map<number, MaskedRange[]>;
  searchMatches: SearchMatch[]; currentMatchIndex: number;
  selectedParagraphIndex: number | null; setSelectedParagraphIndex: (i: number | null) => void;
  scrollRequest: number | null; clearScrollRequest: () => void;
}): ReactElement {
  const containerRef = useRef<HTMLDivElement>(null);
  const handleScroll = useCallback(() => {
    if (scrollRequest !== null && containerRef.current) {
      const el = containerRef.current.querySelector(`[data-para-index="${scrollRequest}"]`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      clearScrollRequest();
    }
  }, [scrollRequest, clearScrollRequest]);

  useEffect(() => { handleScroll(); }, [handleScroll]);

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto px-6 py-4 font-[var(--font-serif)] text-[1rem]">
      {paragraphs.map((p) => (
        <ParagraphView key={p.index} paragraph={p} annotations={annotationsByPara.get(p.index) ?? EMPTY_ANNS}
          searchMatches={searchMatches} currentMatchIndex={currentMatchIndex}
          maskedRanges={maskedByPara.get(p.index) ?? EMPTY_MASKED}
          isSelected={selectedParagraphIndex === p.index}
          onSelect={() => setSelectedParagraphIndex(selectedParagraphIndex === p.index ? null : p.index)} />
      ))}
    </div>
  );
}

// ── Sentence-level zoom ──

function SentenceLevelView({
  paragraphs, annotationsByPara, maskedByPara, searchMatches, currentMatchIndex,
  selectedParagraphIndex, setSelectedParagraphIndex, scrollRequest, clearScrollRequest,
}: {
  paragraphs: Paragraph[]; annotationsByPara: Map<number, W3CAnnotation[]>;
  maskedByPara: Map<number, MaskedRange[]>;
  searchMatches: SearchMatch[]; currentMatchIndex: number;
  selectedParagraphIndex: number | null; setSelectedParagraphIndex: (i: number | null) => void;
  scrollRequest: number | null; clearScrollRequest: () => void;
}): ReactElement {
  const containerRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: paragraphs.length,
    getScrollElement: () => containerRef.current,
    estimateSize: (i) => estimateRowHeight(paragraphs[i].text) + 24,
    overscan: 5,
  });

  useEffect(() => {
    if (scrollRequest !== null) {
      virtualizer.scrollToIndex(scrollRequest, { align: 'center', behavior: 'smooth' });
      clearScrollRequest();
    }
  }, [scrollRequest, clearScrollRequest, virtualizer]);

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto px-6 py-4 font-[var(--font-serif)] text-[1.05rem]">
      <div style={{ height: `${virtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}>
        {virtualizer.getVirtualItems().map((vRow) => {
          const p = paragraphs[vRow.index];
          const isSelected = selectedParagraphIndex === p.index;
          const paraAnns = annotationsByPara.get(p.index) ?? EMPTY_ANNS;
          return (
            <div key={p.index} ref={virtualizer.measureElement} data-index={vRow.index}
              style={{ position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${vRow.start}px)` }}>
              <div
                data-para-index={p.index}
                onClick={() => setSelectedParagraphIndex(selectedParagraphIndex === p.index ? null : p.index)}
                style={{
                  marginBottom: '1.2em', padding: '8px 12px',
                  borderLeft: isSelected ? '3px solid #3498db' : '3px solid transparent',
                  backgroundColor: isSelected ? '#f0f7ff' : 'transparent',
                  cursor: 'pointer', lineHeight: 1.8,
                }}
              >
                <div className="text-[0.7em] text-[var(--color-text-muted)] mb-0.5">
                  P{p.index + 1} &middot; {p.text.split(/\s+/).length} words &middot; {paraAnns.length} annotations
                </div>
                <AnnotationOverlay
                  text={p.text} paraStart={p.start} paraEnd={p.end}
                  annotations={paraAnns} searchMatches={searchMatches}
                  currentMatchIndex={currentMatchIndex}
                  maskedRanges={maskedByPara.get(p.index) ?? EMPTY_MASKED}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main component with zoom dispatch ──

export default function TextLinearView(): ReactElement {
  const paragraphs = useProjectStore((s) => getActiveProject(s).paragraphs);
  const tracks = useProjectStore((s) => getActiveProject(s).tracks);
  const trackStates = useTrackStore((s) => s.tracks);
  const selectedParagraphIndex = useViewStore((s) => s.selectedParagraphIndex);
  const setSelectedParagraphIndex = useViewStore((s) => s.setSelectedParagraphIndex);
  const scrollRequest = useViewStore((s) => s.scrollToParagraphRequest);
  const clearScrollRequest = useViewStore((s) => s.clearScrollRequest);
  const searchMatches = useSearchStore((s) => s.matches);
  const currentMatchIndex = useSearchStore((s) => s.currentMatchIndex);
  const zoomLevel = useViewStore((s) => s.zoomLevel);

  const characterFilter = useViewStore((s) => s.characterFilter);

  // Derive a stable primitive key so the memo only fires when visibility/threshold/mode
  // actually changes — not on every object-reference churn from the track store.
  const trackVisibilityKey = useMemo(
    () => buildTrackVisibilityKey(trackStates),
    [trackStates],
  );

  const hiddenElementTypes = useElementVisibilityStore((s) => s.hidden);
  const hiddenElementKey = useMemo(
    () => Object.keys(hiddenElementTypes).filter((k) => hiddenElementTypes[k]).sort().join(','),
    [hiddenElementTypes],
  );

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const allAnnotations = useMemo(
    () => collectVisibleAnnotations(tracks, trackStates, hiddenElementTypes),
    // tracks (annotation data) changes only on project load; trackVisibilityKey changes on toggle.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tracks, trackVisibilityKey, hiddenElementKey],
  );

  const sectionBlocks = useMemo(
    () => buildSectionBlocks(paragraphs, tracks),
    [paragraphs, tracks],
  );

  const filteredParagraphs = useMemo(() => {
    if (!characterFilter) return paragraphs;
    const entityAnns = tracks['entities'] ?? [];
    const corefAnns = tracks['coreference'] ?? [];
    const matchAnns = [...entityAnns, ...corefAnns];
    const paraIndices = new Set<number>();
    const filterLower = characterFilter.toLowerCase();
    for (const ann of matchAnns) {
      const body = ann.body as Record<string, unknown>;
      const name = ((body.value as string) || (body['palimpsest:canonicalName'] as string) || '').toLowerCase();
      if (!name.includes(filterLower)) continue;
      const sel = ann.target.selector;
      if (sel.start == null) continue;
      const idx = paragraphs.findIndex((p) => p.start <= sel.start! && p.end >= sel.start!);
      if (idx >= 0) paraIndices.add(idx);
    }
    return paragraphs.filter((p) => paraIndices.has(p.index));
  }, [paragraphs, tracks, characterFilter]);

  const clearCharFilter = useViewStore((s) => s.setCharacterFilter);

  const annotationsByPara = useMemo(
    () => bucketAnnotationsByParagraph(filteredParagraphs, allAnnotations),
    [filteredParagraphs, allAnnotations],
  );

  // On-demand masking overlay → grayed-out ranges in the reader (mirrors BrowserView).
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const secProjectId = useSectionStore((s) => s.projectId);
  const secSections = useSectionStore((s) => s.sections);
  const secMask = useSectionStore((s) => s.maskByType);
  const secTextLen = useSectionStore((s) => s.textLen);
  const ovEnabled = useMaskOverlayStore((s) => s.enabled);
  const ovTypeOverrides = useMaskOverlayStore((s) => s.typeOverrides);
  const ovSectionOverrides = useMaskOverlayStore((s) => s.sectionOverrides);
  const verseProjectId = useVerseStore((s) => s.projectId);
  const verseNumIntervals = useVerseStore((s) => s.numIntervals);

  const maskedIntervals = useMemo(() => {
    if (!ovEnabled || !secProjectId || secProjectId !== activeProjectId) return EMPTY_MASKED;
    const extra = verseProjectId === activeProjectId ? verseNumIntervals : [];
    const effSections = effectiveSections(secSections, ovSectionOverrides);
    const effMask = effectiveMaskByType(secMask, ovTypeOverrides);
    return computeMaskedIntervals(effSections, effMask, secTextLen, extra);
  }, [ovEnabled, secProjectId, activeProjectId, secSections, secMask, secTextLen,
      ovSectionOverrides, ovTypeOverrides, verseProjectId, verseNumIntervals]);

  const maskedByPara = useMemo(
    () => bucketMaskedByParagraph(filteredParagraphs, maskedIntervals),
    [filteredParagraphs, maskedIntervals],
  );

  const commonProps = {
    paragraphs: filteredParagraphs, annotationsByPara, maskedByPara, searchMatches, currentMatchIndex,
    selectedParagraphIndex, setSelectedParagraphIndex, scrollRequest, clearScrollRequest,
  };

  const filterBanner = characterFilter ? (
    <div className="flex items-center gap-2 px-4 py-1.5 bg-[#eff6ff] border-b border-[var(--color-border)] text-[0.85em] font-[var(--font-sans)]">
      <span>Showing {filteredParagraphs.length} of {paragraphs.length} paragraphs mentioning</span>
      <span className="font-semibold text-[var(--color-primary)]">{characterFilter}</span>
      <button onClick={() => clearCharFilter(null)} className="ml-auto px-2 py-0.5 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.85em]">
        Clear filter
      </button>
    </div>
  ) : null;

  if (zoomLevel === 'work') {
    return <>{filterBanner}<WorkLevelView sectionBlocks={sectionBlocks} annotations={allAnnotations} /></>;
  }

  if (zoomLevel === 'chapter') {
    return <>{filterBanner}<ChapterLevelView paragraphs={filteredParagraphs} annotations={allAnnotations} /></>;
  }

  if (zoomLevel === 'sentence') {
    return <>{filterBanner}<SentenceLevelView {...commonProps} /></>;
  }

  // Default: paragraph level
  const useVirtual = filteredParagraphs.length >= VIRTUALIZE_THRESHOLD;
  return <>{filterBanner}{useVirtual
    ? <VirtualizedParagraphView {...commonProps} />
    : <SimpleParagraphView {...commonProps} />}</>;
}
