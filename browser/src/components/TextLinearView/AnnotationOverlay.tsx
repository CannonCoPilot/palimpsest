/**
 * AnnotationOverlay — renders colored spans over text for annotation highlights.
 *
 * Supports track-specific rendering modes (highlight, color-band, underline, margin-marker),
 * search match highlighting, and click-to-select.
 */

import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import type { TrackManifest } from '../../adapters/TrackManifest';
import { useViewStore } from '../../stores/viewStore';
import { useTrackStore } from '../../stores/trackStore';
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
};

interface SegmentItem {
  start: number;
  end: number;
  annotations: W3CAnnotation[];
  searchMatch?: { isCurrent: boolean };
}

function getTrackName(ann: W3CAnnotation): string {
  return BODY_TYPE_TO_TRACK[ann.body.type] ?? '';
}

function getColor(ann: W3CAnnotation): string {
  return TRACK_COLORS[getTrackName(ann)] ?? '#888';
}

function getManifest(ann: W3CAnnotation, trackStates: Record<string, { manifest: TrackManifest }>): TrackManifest | null {
  const name = getTrackName(ann);
  return trackStates[name]?.manifest ?? null;
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
  text: string,
  annotations: W3CAnnotation[],
  paraStart: number,
  paraEnd: number,
  searchMatches: SearchMatch[],
  currentMatchIndex: number,
): SegmentItem[] {
  type Event = { pos: number; type: 'start' | 'end'; ann?: W3CAnnotation; searchCurrent?: boolean };
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

  if (events.length === 0) return [];

  events.sort((a, b) => a.pos - b.pos || (a.type === 'end' ? -1 : 1));

  const segments: SegmentItem[] = [];
  const activeAnns: Set<W3CAnnotation> = new Set();
  let activeSearch: { isCurrent: boolean } | undefined;
  let lastPos = 0;

  for (const ev of events) {
    if (ev.pos > lastPos && (activeAnns.size > 0 || activeSearch)) {
      segments.push({
        start: lastPos,
        end: ev.pos,
        annotations: [...activeAnns],
        searchMatch: activeSearch,
      });
    }
    lastPos = ev.pos;
    if (ev.ann) {
      if (ev.type === 'start') activeAnns.add(ev.ann);
      else activeAnns.delete(ev.ann);
    } else {
      if (ev.type === 'start') activeSearch = { isCurrent: ev.searchCurrent ?? false };
      else activeSearch = undefined;
    }
  }

  return segments;
}

function buildAnnotationTitle(ann: W3CAnnotation): string {
  const typeName = ann.body.type.replace('palimpsest:', '');
  const body = ann.body as Record<string, unknown>;

  const stateId = body['palimpsest:stateId'];
  const stateDesc = body['palimpsest:stateDescription'];
  if (typeof stateId === 'number' && stateDesc) {
    return `${typeName} — State ${stateId}: ${stateDesc}`;
  }

  const noteNum = body['palimpsest:noteNumber'];
  const noteText = body['palimpsest:noteText'];
  if (typeof noteNum === 'number' && typeof noteText === 'string') {
    return `Endnote ${noteNum}: ${noteText.slice(0, 100)}${noteText.length > 100 ? '...' : ''}`;
  }

  const headingText = body['palimpsest:headingText'];
  if (typeof headingText === 'string') {
    return `Section: ${headingText}`;
  }

  const topic = body['palimpsest:topicLabel'];
  if (topic) return `${typeName} — ${topic}`;
  return `${typeName} — ${ann.body.value || ''}`;
}

interface Props {
  text: string;
  paraStart: number;
  paraEnd: number;
  annotations: W3CAnnotation[];
  searchMatches?: SearchMatch[];
  currentMatchIndex?: number;
}

export default function AnnotationOverlay({
  text,
  paraStart,
  paraEnd,
  annotations,
  searchMatches = [],
  currentMatchIndex = -1,
}: Props): JSX.Element {
  const selectAnnotation = useViewStore((s) => s.selectAnnotation);
  const selectedAnnotation = useViewStore((s) => s.selectedAnnotation);
  const trackStates = useTrackStore((s) => s.tracks);
  const segments = buildSegments(text, annotations, paraStart, paraEnd, searchMatches, currentMatchIndex);

  if (segments.length === 0 && searchMatches.length === 0) {
    return <span>{text}</span>;
  }

  const elements: JSX.Element[] = [];
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
      const manifest = getManifest(topAnn, trackStates);
      style = getAnnotationStyle(topAnn, isSelected, manifest);
    } else {
      style = {};
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
