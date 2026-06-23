/**
 * AnnotationOverlay — renders colored spans over text for annotation highlights.
 *
 * Supports track-specific rendering modes (highlight, color-band, underline, margin-marker),
 * search match highlighting, and click-to-select.
 */

import { memo, useMemo, type ReactElement } from 'react';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import type { TrackManifest } from '../../adapters/TrackManifest';
import { useViewStore } from '../../stores/viewStore';
import { useTrackManifests } from '../../stores/trackStore';
import { TRACK_COLORS } from '../../utils/trackColors';
import type { SearchMatch } from '../../stores/searchStore';
import { Tooltip } from '../common/Tooltip';
import AnnotationHoverCard from '../common/AnnotationHoverCard';
import AnnotationContextMenu from '../common/AnnotationContextMenu';

const BODY_TYPE_TO_TRACK: Record<string, string> = {
  'palimpsest:EntityAnnotation': 'entities',
  'palimpsest:SentimentAnnotation': 'sentiment',
  'palimpsest:LexicalAnnotation': 'lexical',
  'palimpsest:DialogueAnnotation': 'dialogue',
  'palimpsest:TopicAnnotation': 'topics',
  'palimpsest:CoreferenceAnnotation': 'coreference',
  'palimpsest:SyntaxAnnotation': 'syntax',
  'palimpsest:LitHMMAnnotation': 'lithmm',
  'palimpsest:CompartmentAnnotation': 'compartments',
  'palimpsest:DomainAnnotation': 'compartments',
  'palimpsest:SegmentAnnotation': 'segments',
  'palimpsest:SectionAnnotation': 'sections',
  'palimpsest:EndnoteAnnotation': 'endnotes',
  'palimpsest:ElementAnnotation': 'elements',
};

interface SegmentItem {
  start: number;
  end: number;
  annotations: W3CAnnotation[];
  searchMatch?: { isCurrent: boolean };
  masked?: boolean;
}

// Masked-text styling, matching the Browser's TickerTape (dark band, light text).
const MASKED_BG = '#3a3a3d';
const MASKED_FG = '#f5f5f5';

function getTrackName(ann: W3CAnnotation): string {
  return BODY_TYPE_TO_TRACK[ann.body.type] ?? '';
}

function getColor(ann: W3CAnnotation): string {
  // Per-annotation color (e.g. each Elements subtype carries its own) wins.
  const custom = (ann.body as Record<string, unknown>)['palimpsest:color'];
  if (typeof custom === 'string' && custom) return custom;
  return TRACK_COLORS[getTrackName(ann)] ?? '#888';
}

function getManifest(ann: W3CAnnotation, manifests: Record<string, TrackManifest>): TrackManifest | null {
  const name = getTrackName(ann);
  return manifests[name] ?? null;
}

function getAnnotationStyle(
  ann: W3CAnnotation,
  isSelected: boolean,
  manifest: TrackManifest | null,
): React.CSSProperties {
  const color = getColor(ann);
  const renderMode = manifest?.textViewRendering ?? 'highlight';

  if (renderMode === 'color-band') {
    const stateId = (ann.body as Record<string, unknown>)['palimpsest:stateId'];
    const scale = manifest?.colorScheme?.scale;
    let bandColor = color;
    if (scale && typeof stateId === 'number' && Array.isArray(scale) && scale[stateId]) {
      bandColor = scale[stateId];
    } else if (scale && typeof stateId === 'number' && typeof scale === 'object') {
      const val = (scale as Record<string, string>)[String(stateId)];
      if (val) bandColor = val;
    }
    return {
      backgroundColor: isSelected ? bandColor : `${bandColor}40`,
      borderLeft: `3px solid ${bandColor}`,
      cursor: 'pointer',
      color: isSelected ? '#fff' : 'inherit',
      padding: '0 2px',
      transition: 'background-color 0.15s',
    };
  }

  if (renderMode === 'underline') {
    return {
      textDecoration: `underline ${color}`,
      textDecorationThickness: isSelected ? '3px' : '2px',
      textUnderlineOffset: '3px',
      backgroundColor: isSelected ? `${color}22` : 'transparent',
      cursor: 'pointer',
      transition: 'background-color 0.15s',
    };
  }

  if (renderMode === 'margin-marker') {
    return {
      borderLeft: `3px solid ${color}`,
      paddingLeft: '4px',
      backgroundColor: isSelected ? `${color}22` : 'transparent',
      cursor: 'pointer',
      transition: 'background-color 0.15s',
    };
  }

  if (renderMode === 'superscript') {
    return {
      fontSize: '0.75em',
      verticalAlign: 'super',
      color,
      cursor: 'pointer',
      fontWeight: isSelected ? 'bold' : 'normal',
      backgroundColor: isSelected ? `${color}22` : 'transparent',
      borderRadius: '2px',
      padding: '0 1px',
    };
  }

  if (renderMode === 'none') {
    return { display: 'none' };
  }

  // Default: highlight
  const sentimentValue = (ann.body as Record<string, unknown>)['palimpsest:valence'];
  if (typeof sentimentValue === 'number') {
    const hue = sentimentValue >= 0 ? 120 : 0;
    const sat = Math.min(Math.abs(sentimentValue) * 100, 100);
    const alpha = isSelected ? 0.5 : 0.15;
    return {
      backgroundColor: `hsla(${hue}, ${sat}%, 50%, ${alpha})`,
      borderBottom: `2px solid hsl(${hue}, ${sat}%, 40%)`,
      cursor: 'pointer',
      color: isSelected ? '#fff' : 'inherit',
      borderRadius: '2px',
      padding: '0 1px',
      transition: 'background-color 0.15s',
    };
  }

  return {
    backgroundColor: isSelected ? color : `${color}33`,
    borderBottom: `2px solid ${color}`,
    cursor: 'pointer',
    color: isSelected ? '#fff' : 'inherit',
    borderRadius: '2px',
    padding: '0 1px',
    transition: 'background-color 0.15s',
  };
}

function buildSegments(
  annotations: W3CAnnotation[],
  paraStart: number,
  paraEnd: number,
  searchMatches: SearchMatch[],
  currentMatchIndex: number,
  maskedRanges: ReadonlyArray<readonly [number, number]>,
): SegmentItem[] {
  type Event = {
    pos: number;
    type: 'start' | 'end';
    ann?: W3CAnnotation;
    searchCurrent?: boolean;
    masked?: boolean;
  };
  const events: Event[] = [];

  for (const ann of annotations) {
    const sel = ann.target.selector;
    if (sel.type !== 'TextPositionSelector' || sel.start == null || sel.end == null) continue;
    if (sel.start >= paraEnd || sel.end <= paraStart) continue;
    const s = Math.max(sel.start - paraStart, 0);
    const e = Math.min(sel.end - paraStart, paraEnd - paraStart);
    events.push({ pos: s, type: 'start', ann });
    events.push({ pos: e, type: 'end', ann });
  }

  for (let mi = 0; mi < searchMatches.length; mi++) {
    const m = searchMatches[mi];
    if (m.start >= paraEnd || m.end <= paraStart) continue;
    const s = Math.max(m.start - paraStart, 0);
    const e = Math.min(m.end - paraStart, paraEnd - paraStart);
    events.push({ pos: s, type: 'start', searchCurrent: mi === currentMatchIndex });
    events.push({ pos: e, type: 'end', searchCurrent: mi === currentMatchIndex });
  }

  // Masked (analysis-excluded) ranges — the on-demand masking overlay grays these.
  for (const [ms, me] of maskedRanges) {
    if (ms >= paraEnd || me <= paraStart) continue;
    const s = Math.max(ms - paraStart, 0);
    const e = Math.min(me - paraStart, paraEnd - paraStart);
    if (e <= s) continue;
    events.push({ pos: s, type: 'start', masked: true });
    events.push({ pos: e, type: 'end', masked: true });
  }

  if (events.length === 0) return [];

  events.sort((a, b) => a.pos - b.pos || (a.type === 'end' ? -1 : 1));

  const segments: SegmentItem[] = [];
  const activeAnns: Set<W3CAnnotation> = new Set();
  let activeSearch: { isCurrent: boolean } | undefined;
  let activeMasked = 0;
  let lastPos = 0;

  for (const ev of events) {
    if (ev.pos > lastPos && (activeAnns.size > 0 || activeSearch || activeMasked > 0)) {
      segments.push({
        start: lastPos,
        end: ev.pos,
        annotations: [...activeAnns],
        searchMatch: activeSearch,
        masked: activeMasked > 0,
      });
    }
    lastPos = ev.pos;
    if (ev.ann) {
      if (ev.type === 'start') activeAnns.add(ev.ann);
      else activeAnns.delete(ev.ann);
    } else if (ev.masked) {
      activeMasked += ev.type === 'start' ? 1 : -1;
    } else {
      if (ev.type === 'start') activeSearch = { isCurrent: ev.searchCurrent ?? false };
      else activeSearch = undefined;
    }
  }

  return segments;
}

interface Props {
  text: string;
  paraStart: number;
  paraEnd: number;
  annotations: W3CAnnotation[];
  searchMatches?: SearchMatch[];
  currentMatchIndex?: number;
  maskedRanges?: ReadonlyArray<readonly [number, number]>;
}

const EMPTY_MASKED: ReadonlyArray<readonly [number, number]> = [];

function AnnotationOverlayInner({
  text,
  paraStart,
  paraEnd,
  annotations,
  searchMatches = [],
  currentMatchIndex = -1,
  maskedRanges = EMPTY_MASKED,
}: Props): ReactElement {
  const selectAnnotation = useViewStore((s) => s.selectAnnotation);
  const selectedAnnotation = useViewStore((s) => s.selectedAnnotation);
  const trackManifests = useTrackManifests();

  // Memoize the expensive segment-building step.  It only needs to rerun when
  // the annotation list, paragraph bounds, search state, or masked ranges change.
  const segments = useMemo(
    () => buildSegments(annotations, paraStart, paraEnd, searchMatches, currentMatchIndex, maskedRanges),
    [annotations, paraStart, paraEnd, searchMatches, currentMatchIndex, maskedRanges],
  );

  if (segments.length === 0 && searchMatches.length === 0) {
    return <span>{text}</span>;
  }

  const elements: ReactElement[] = [];
  let cursor = 0;

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    if (seg.start > cursor) {
      elements.push(<span key={`t-${i}`}>{text.slice(cursor, seg.start)}</span>);
    }

    const hasAnnotation = seg.annotations.length > 0;
    const topAnn = seg.annotations[0] ?? null;
    const isSelected = topAnn != null && selectedAnnotation?.id === topAnn.id;

    let style: React.CSSProperties;

    if (hasAnnotation && topAnn) {
      const manifest = getManifest(topAnn, trackManifests);
      style = getAnnotationStyle(topAnn, isSelected, manifest);
    } else {
      style = {};
    }

    // Masking overrides annotation styling (the text is excluded from analysis); a search
    // hit still wins below so masked text stays findable.
    if (seg.masked) {
      style = { ...style, backgroundColor: MASKED_BG, color: MASKED_FG, borderRadius: '2px', padding: '0 1px' };
    }

    if (seg.searchMatch) {
      style = {
        ...style,
        backgroundColor: seg.searchMatch.isCurrent ? '#ffeb3b' : '#fff59d',
        color: '#000',
        borderRadius: '2px',
      };
    }

    const span = (
      <span
        key={`a-${i}`}
        onClick={
          topAnn
            ? (e) => {
                e.stopPropagation();
                selectAnnotation(topAnn);
              }
            : undefined
        }
        style={style}
      >
        {text.slice(seg.start, seg.end)}
      </span>
    );
    elements.push(
      topAnn ? (
        <AnnotationContextMenu key={`c-${i}`} annotation={topAnn}>
          <Tooltip content={<AnnotationHoverCard annotation={topAnn} excerpt={text.slice(seg.start, seg.end)} />} side="bottom" delayDuration={400}>
            {span}
          </Tooltip>
        </AnnotationContextMenu>
      ) : span
    );
    cursor = seg.end;
  }

  if (cursor < text.length) {
    elements.push(<span key="tail">{text.slice(cursor)}</span>);
  }

  return <>{elements}</>;
}

// Wrap in React.memo so the component only re-renders when its own props change.
// Since paragraphs are virtualized and annotations are filtered upstream, the vast
// majority of paragraph overlays can skip re-rendering on unrelated track toggles.
const AnnotationOverlay = memo(AnnotationOverlayInner);
export default AnnotationOverlay;
