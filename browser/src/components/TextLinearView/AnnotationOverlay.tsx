/**
 * AnnotationOverlay — renders colored spans over text for annotation highlights.
 *
 * Merges overlapping annotations into non-overlapping highlight segments,
 * handles click-to-select, and applies track-specific colors.
 */

import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { useViewStore } from '../../stores/viewStore';

const TRACK_COLORS: Record<string, string> = {
  'palimpsest:EntityAnnotation': '#3498db',
  'palimpsest:SentimentAnnotation': '#e67e22',
  'palimpsest:LexicalAnnotation': '#27ae60',
  'palimpsest:DialogueAnnotation': '#9b59b6',
  'palimpsest:TopicAnnotation': '#e74c3c',
  'palimpsest:CoreferenceAnnotation': '#1abc9c',
  'palimpsest:SegmentAnnotation': '#95a5a6',
};

const ENTITY_COLORS: Record<string, string> = {
  PER: '#3498db',
  LOC: '#2ecc71',
  ORG: '#e74c3c',
  WORK: '#9b59b6',
};

interface AnnotationSpan {
  start: number;
  end: number;
  annotations: W3CAnnotation[];
}

function getColor(ann: W3CAnnotation): string {
  if (ann.body.type === 'palimpsest:EntityAnnotation') {
    const entityType = (ann.body as Record<string, unknown>)['palimpsest:entityType'] as string;
    return ENTITY_COLORS[entityType] || TRACK_COLORS[ann.body.type] || '#888';
  }
  return TRACK_COLORS[ann.body.type] || '#888';
}

function buildSpans(text: string, annotations: W3CAnnotation[], paraStart: number, paraEnd: number): AnnotationSpan[] {
  const relevant = annotations.filter((a) => {
    const sel = a.target.selector;
    if (sel.type !== 'TextPositionSelector' || sel.start == null || sel.end == null) return false;
    return sel.start < paraEnd && sel.end > paraStart;
  });

  if (relevant.length === 0) return [];

  const events: Array<{ pos: number; type: 'start' | 'end'; ann: W3CAnnotation }> = [];
  for (const ann of relevant) {
    const sel = ann.target.selector;
    const s = Math.max(sel.start! - paraStart, 0);
    const e = Math.min(sel.end! - paraStart, paraEnd - paraStart);
    events.push({ pos: s, type: 'start', ann });
    events.push({ pos: e, type: 'end', ann });
  }

  events.sort((a, b) => a.pos - b.pos || (a.type === 'end' ? -1 : 1));

  const spans: AnnotationSpan[] = [];
  const active: Set<W3CAnnotation> = new Set();
  let lastPos = 0;

  for (const ev of events) {
    if (ev.pos > lastPos && active.size > 0) {
      spans.push({ start: lastPos, end: ev.pos, annotations: [...active] });
    }
    lastPos = ev.pos;
    if (ev.type === 'start') {
      active.add(ev.ann);
    } else {
      active.delete(ev.ann);
    }
  }

  return spans;
}

interface Props {
  text: string;
  paraStart: number;
  paraEnd: number;
  annotations: W3CAnnotation[];
}

export default function AnnotationOverlay({ text, paraStart, paraEnd, annotations }: Props): JSX.Element {
  const selectAnnotation = useViewStore((s) => s.selectAnnotation);
  const selectedAnnotation = useViewStore((s) => s.selectedAnnotation);
  const spans = buildSpans(text, annotations, paraStart, paraEnd);

  if (spans.length === 0) {
    return <span>{text}</span>;
  }

  const elements: JSX.Element[] = [];
  let cursor = 0;

  for (let i = 0; i < spans.length; i++) {
    const span = spans[i];
    if (span.start > cursor) {
      elements.push(<span key={`t-${i}`}>{text.slice(cursor, span.start)}</span>);
    }

    const topAnn = span.annotations[0];
    const color = getColor(topAnn);
    const isSelected = selectedAnnotation?.id === topAnn.id;

    elements.push(
      <span
        key={`a-${i}`}
        onClick={(e) => {
          e.stopPropagation();
          selectAnnotation(topAnn);
        }}
        style={{
          backgroundColor: isSelected ? color : `${color}33`,
          borderBottom: `2px solid ${color}`,
          cursor: 'pointer',
          color: isSelected ? '#fff' : 'inherit',
          borderRadius: '2px',
          padding: '0 1px',
          transition: 'background-color 0.15s',
        }}
        title={`${topAnn.body.type.replace('palimpsest:', '')} — ${topAnn.body.value || ''}`}
      >
        {text.slice(span.start, span.end)}
      </span>
    );
    cursor = span.end;
  }

  if (cursor < text.length) {
    elements.push(<span key="tail">{text.slice(cursor)}</span>);
  }

  return <>{elements}</>;
}
