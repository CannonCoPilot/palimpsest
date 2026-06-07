/**
 * TextLinearView — main reading area with text paragraphs and annotation overlays.
 * Analogous to JBrowse 2's LinearGenomeView.
 */

import { useCallback, useEffect, useRef } from 'react';
import { useProjectStore, type Paragraph } from '../../stores/projectStore';
import { useTrackStore, type TrackState } from '../../stores/trackStore';
import { useViewStore } from '../../stores/viewStore';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import AnnotationOverlay from './AnnotationOverlay';

function collectVisibleAnnotations(
  tracks: Record<string, W3CAnnotation[]>,
  trackStates: Record<string, TrackState>,
): W3CAnnotation[] {
  const all: W3CAnnotation[] = [];
  for (const [name, anns] of Object.entries(tracks)) {
    if (name === 'segments') continue;
    const state = trackStates[name];
    if (state && !state.visible) continue;
    const threshold = state?.confidenceThreshold ?? 0;
    if (threshold > 0) {
      all.push(...anns.filter((a) => (a['palimpsest:confidence'] ?? 1) >= threshold));
    } else {
      all.push(...anns);
    }
  }
  return all;
}

interface ParagraphViewProps {
  paragraph: Paragraph;
  annotations: W3CAnnotation[];
  isSelected: boolean;
  onSelect: () => void;
}

function ParagraphView({ paragraph, annotations, isSelected, onSelect }: ParagraphViewProps): JSX.Element {
  return (
    <div
      data-para-index={paragraph.index}
      onClick={onSelect}
      style={{
        marginBottom: '1em',
        padding: '4px 8px',
        borderLeft: isSelected ? '3px solid #3498db' : '3px solid transparent',
        backgroundColor: isSelected ? '#f0f7ff' : 'transparent',
        cursor: 'pointer',
        lineHeight: 1.7,
        transition: 'background-color 0.15s, border-color 0.15s',
      }}
    >
      <AnnotationOverlay
        text={paragraph.text}
        paraStart={paragraph.start}
        paraEnd={paragraph.end}
        annotations={annotations}
      />
    </div>
  );
}

export default function TextLinearView(): JSX.Element {
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const tracks = useProjectStore((s) => s.tracks);
  const trackStates = useTrackStore((s) => s.tracks);
  const selectedParagraphIndex = useViewStore((s) => s.selectedParagraphIndex);
  const setSelectedParagraphIndex = useViewStore((s) => s.setSelectedParagraphIndex);
  const scrollRequest = useViewStore((s) => s.scrollToParagraphRequest);
  const clearScrollRequest = useViewStore((s) => s.clearScrollRequest);
  const containerRef = useRef<HTMLDivElement>(null);

  const allAnnotations = collectVisibleAnnotations(tracks, trackStates);

  const handleScroll = useCallback(() => {
    if (scrollRequest !== null && containerRef.current) {
      const el = containerRef.current.querySelector(`[data-para-index="${scrollRequest}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      clearScrollRequest();
    }
  }, [scrollRequest, clearScrollRequest]);

  useEffect(() => {
    handleScroll();
  }, [handleScroll]);

  return (
    <div
      ref={containerRef}
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px 24px',
        fontFamily: "'Georgia', serif",
        fontSize: '1rem',
      }}
    >
      {paragraphs.map((p) => (
        <ParagraphView
          key={p.index}
          paragraph={p}
          annotations={allAnnotations}
          isSelected={selectedParagraphIndex === p.index}
          onSelect={() => setSelectedParagraphIndex(p.index)}
        />
      ))}
    </div>
  );
}
