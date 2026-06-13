/**
 * TextLinearView — main reading area with semantic zoom (4 levels).
 * Work → Chapter → Paragraph → Sentence
 */

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useProjectStore, getActiveProject, type Paragraph } from '../../stores/projectStore';
import { useTrackStore, type TrackState } from '../../stores/trackStore';
import { useViewStore, type ZoomLevel } from '../../stores/viewStore';
import { useSearchStore, type SearchMatch } from '../../stores/searchStore';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { TRACK_COLORS } from '../../utils/trackColors';
import AnnotationOverlay from './AnnotationOverlay';

const VIRTUALIZE_THRESHOLD = 200;

function collectVisibleAnnotations(
  tracks: Record<string, W3CAnnotation[]>,
  trackStates: Record<string, TrackState>,
): W3CAnnotation[] {
  const all: W3CAnnotation[] = [];
  for (const [name, anns] of Object.entries(tracks)) {
    if (name === 'segments') continue;
    const state = trackStates[name];
    if (state && !state.visible) continue;
    if (state?.displayMode === 'dense') continue;
    const threshold = state?.confidenceThreshold ?? 0;
    const filtered = threshold > 0
      ? anns.filter((a) => (a['palimpsest:confidence'] ?? 1) >= threshold)
      : anns;
    all.push(...filtered);
  }
  return all;
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
}): JSX.Element {
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
}): JSX.Element {
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
}

function ParagraphView({ paragraph, annotations, searchMatches, currentMatchIndex, isSelected, onSelect }: ParagraphViewProps): JSX.Element {
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
      />
    </div>
  );
}

function VirtualizedParagraphView({
  paragraphs, allAnnotations, searchMatches, currentMatchIndex,
  selectedParagraphIndex, setSelectedParagraphIndex, scrollRequest, clearScrollRequest,
}: {
  paragraphs: Paragraph[]; allAnnotations: W3CAnnotation[];
  searchMatches: SearchMatch[]; currentMatchIndex: number;
  selectedParagraphIndex: number | null; setSelectedParagraphIndex: (i: number | null) => void;
  scrollRequest: number | null; clearScrollRequest: () => void;
}): JSX.Element {
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
                paragraph={p} annotations={allAnnotations} searchMatches={searchMatches}
                currentMatchIndex={currentMatchIndex}
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
  paragraphs, allAnnotations, searchMatches, currentMatchIndex,
  selectedParagraphIndex, setSelectedParagraphIndex, scrollRequest, clearScrollRequest,
}: {
  paragraphs: Paragraph[]; allAnnotations: W3CAnnotation[];
  searchMatches: SearchMatch[]; currentMatchIndex: number;
  selectedParagraphIndex: number | null; setSelectedParagraphIndex: (i: number | null) => void;
  scrollRequest: number | null; clearScrollRequest: () => void;
}): JSX.Element {
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
        <ParagraphView key={p.index} paragraph={p} annotations={allAnnotations}
          searchMatches={searchMatches} currentMatchIndex={currentMatchIndex}
          isSelected={selectedParagraphIndex === p.index}
          onSelect={() => setSelectedParagraphIndex(selectedParagraphIndex === p.index ? null : p.index)} />
      ))}
    </div>
  );
}

// ── Sentence-level zoom ──

function SentenceLevelView({
  paragraphs, allAnnotations, searchMatches, currentMatchIndex,
  selectedParagraphIndex, setSelectedParagraphIndex, scrollRequest, clearScrollRequest,
}: {
  paragraphs: Paragraph[]; allAnnotations: W3CAnnotation[];
  searchMatches: SearchMatch[]; currentMatchIndex: number;
  selectedParagraphIndex: number | null; setSelectedParagraphIndex: (i: number | null) => void;
  scrollRequest: number | null; clearScrollRequest: () => void;
}): JSX.Element {
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
          const paraAnns = allAnnotations.filter((a) => {
            const s = a.target.selector;
            return s.start != null && s.end != null && s.start < p.end && s.end > p.start;
          });
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
                  annotations={allAnnotations} searchMatches={searchMatches}
                  currentMatchIndex={currentMatchIndex}
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

export default function TextLinearView(): JSX.Element {
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

  const allAnnotations = useMemo(
    () => collectVisibleAnnotations(tracks, trackStates),
    [tracks, trackStates],
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

  const commonProps = {
    paragraphs: filteredParagraphs, allAnnotations: allAnnotations, searchMatches, currentMatchIndex,
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
