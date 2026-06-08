/**
 * AnnotationOverlay — renders colored spans over text for annotation highlights.
 *
 * Merges overlapping annotations into non-overlapping highlight segments,
 * handles click-to-select, and applies track-specific colors.
 */

import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { useViewStore } from '../../stores/viewStore';
import { TRACK_COLORS } from '../../utils/trackColors';

// Map body type → track name so overlay uses the same colors as TrackPanel/OverviewBar
const BODY_TYPE_TO_TRACK: Record<string, string> = {
  'palimpsest:EntityAnnotation': 'entities',
  'palimpsest:SentimentAnnotation': 'sentiment',
  'palimpsest:LexicalAnnotation': 'lexical',
  'palimpsest:DialogueAnnotation': 'dialogue',
  'palimpsest:TopicAnnotation': 'topics',
  'palimpsest:CoreferenceAnnotation': 'coreference',
  'palimpsest:SegmentAnnotation': 'segments',
};

interface AnnotationSpan {
  start: number;
  end: number;
  annotations: W3CAnnotation[];
}

function getColor(ann: W3CAnnotation): string {
  const trackName = BODY_TYPE_TO_TRACK[ann.body.type] ?? '';
  return TRACK_COLORS[trackName] ?? '#888';
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
