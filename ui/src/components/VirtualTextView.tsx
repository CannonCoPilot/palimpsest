import { useCallback, useEffect, useRef, useState } from 'react';
import { useProjectStore, type ViewportAnnotation } from '../stores/projectStore';
import { useTrackStore } from '../stores/trackStore';
import { invoke } from '@tauri-apps/api/core';

const OVERSCAN = 10;
const ESTIMATED_PARA_HEIGHT = 60;

const TRACK_COLORS: Record<number, string> = {};

function getTrackColor(trackId: number): string {
  if (TRACK_COLORS[trackId]) return TRACK_COLORS[trackId];
  const colors = ['#3498db', '#2ecc71', '#9b59b6', '#e67e22', '#e74c3c', '#95a5a6'];
  TRACK_COLORS[trackId] = colors[trackId % colors.length];
  return TRACK_COLORS[trackId];
}

export default function VirtualTextView() {
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const info = useProjectStore((s) => s.info);
  const tracks = useTrackStore((s) => s.tracks);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(800);
  const [annotations, setAnnotations] = useState<ViewportAnnotation[]>([]);
  const [heights] = useState<number[]>(() => paragraphs.map(() => ESTIMATED_PARA_HEIGHT));

  const totalHeight = heights.reduce((sum, h) => sum + h, 0);

  const getVisibleRange = useCallback(() => {
    let accumulated = 0;
    let startIdx = 0;
    for (let i = 0; i < heights.length; i++) {
      if (accumulated + heights[i] > scrollTop) {
        startIdx = i;
        break;
      }
      accumulated += heights[i];
    }

    let endIdx = startIdx;
    let visibleHeight = 0;
    for (let i = startIdx; i < heights.length; i++) {
      visibleHeight += heights[i];
      endIdx = i;
      if (visibleHeight > containerHeight) break;
    }

    return {
      start: Math.max(0, startIdx - OVERSCAN),
      end: Math.min(paragraphs.length - 1, endIdx + OVERSCAN),
      offsetTop: heights.slice(0, Math.max(0, startIdx - OVERSCAN)).reduce((s, h) => s + h, 0),
    };
  }, [scrollTop, containerHeight, heights, paragraphs.length]);

  const { start, end, offsetTop } = getVisibleRange();

  useEffect(() => {
    if (!info || paragraphs.length === 0) return;

    const startChar = paragraphs[start]?.start ?? 0;
    const endChar = paragraphs[end]?.end ?? info.character_count;

    invoke<ViewportAnnotation[]>('query_viewport', {
      projectId: info.id,
      start: startChar,
      end: endChar,
    }).then(setAnnotations).catch(() => {});
  }, [start, end, info, paragraphs, tracks]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    setContainerHeight(el.clientHeight);
    const obs = new ResizeObserver(() => setContainerHeight(el.clientHeight));
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  function handleScroll(e: React.UIEvent<HTMLDivElement>) {
    setScrollTop(e.currentTarget.scrollTop);
  }

  const visibleParagraphs = paragraphs.slice(start, end + 1);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      style={{
        flex: 1,
        overflowY: 'auto',
        fontFamily: "'Crimson Pro', Georgia, serif",
        fontSize: '1rem',
        lineHeight: 1.8,
      }}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div style={{ position: 'absolute', top: offsetTop, left: 0, right: 0, padding: '16px 32px' }}>
          {visibleParagraphs.map((para, localIdx) => {
            const globalIdx = start + localIdx;
            const paraAnnotations = annotations.filter(
              (a) => a.start < para.end && a.end > para.start
            );
            return (
              <ParagraphWithHighlights
                key={globalIdx}
                text={para.text}
                paraStart={para.start}
                annotations={paraAnnotations}
                onHeightMeasured={(h) => { heights[globalIdx] = h; }}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ParagraphWithHighlights({
  text,
  paraStart,
  annotations,
  onHeightMeasured,
}: {
  text: string;
  paraStart: number;
  annotations: ViewportAnnotation[];
  onHeightMeasured: (h: number) => void;
}) {
  const ref = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (ref.current) {
      onHeightMeasured(ref.current.offsetHeight + 16);
    }
  });

  if (annotations.length === 0) {
    return <p ref={ref} style={{ marginBottom: '1em' }}>{text}</p>;
  }

  const segments = buildHighlightedSegments(text, paraStart, annotations);

  return (
    <p ref={ref} style={{ marginBottom: '1em' }}>
      {segments.map((seg, i) =>
        seg.color ? (
          <mark key={i} style={{ backgroundColor: seg.color + '30', borderBottom: `2px solid ${seg.color}`, padding: '0 1px' }}>
            {seg.text}
          </mark>
        ) : (
          <span key={i}>{seg.text}</span>
        )
      )}
    </p>
  );
}

interface Segment {
  text: string;
  color: string | null;
}

function buildHighlightedSegments(
  text: string,
  paraStart: number,
  annotations: ViewportAnnotation[],
): Segment[] {
  const events: { pos: number; type: 'start' | 'end'; color: string }[] = [];

  for (const ann of annotations) {
    const relStart = Math.max(0, ann.start - paraStart);
    const relEnd = Math.min(text.length, ann.end - paraStart);
    if (relStart >= relEnd) continue;
    const color = getTrackColor(ann.track_id);
    events.push({ pos: relStart, type: 'start', color });
    events.push({ pos: relEnd, type: 'end', color });
  }

  events.sort((a, b) => a.pos - b.pos || (a.type === 'end' ? -1 : 1));

  const segments: Segment[] = [];
  const active = new Set<string>();
  let lastPos = 0;

  for (const ev of events) {
    if (ev.pos > lastPos) {
      const color = active.size > 0 ? [...active][0] : null;
      segments.push({ text: text.slice(lastPos, ev.pos), color });
    }
    if (ev.type === 'start') active.add(ev.color);
    else active.delete(ev.color);
    lastPos = ev.pos;
  }

  if (lastPos < text.length) {
    segments.push({ text: text.slice(lastPos), color: null });
  }

  return segments;
}
