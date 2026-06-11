import { useRef, useState, useEffect, useCallback } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useTrackStore } from '../../stores/trackStore';
import { useSearchStore } from '../../stores/searchStore';
import { useViewStore } from '../../stores/viewStore';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { TRACK_COLORS } from '../../utils/trackColors';
import { Tooltip } from '../common/Tooltip';

interface BarcodeProps {
  label: string;
  annotations: W3CAnnotation[];
  color: string;
  documentLength: number;
  width: number;
  height: number;
  visible: boolean;
  viewportStart: number;
  viewportEnd: number;
  onClickPosition: (fraction: number) => void;
}

function DensityBarcode({ label, annotations, color, documentLength, width, height, visible, viewportStart, viewportEnd, onClickPosition }: BarcodeProps) {
  function handleClick(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const fraction = (e.clientX - rect.left) / rect.width;
    onClickPosition(fraction);
  }

  const vpX = (viewportStart / documentLength) * width;
  const vpW = Math.max(2, ((viewportEnd - viewportStart) / documentLength) * width);

  return (
    <div className="flex items-center gap-1" style={{ opacity: visible ? 1 : 0.3 }}>
      <Tooltip content={`${label} — ${annotations.length} annotations`} side="top">
        <span className="w-[60px] text-[0.7em] text-[var(--color-text-muted)] text-right truncate">{label}</span>
      </Tooltip>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`${label} density`}
        className="cursor-pointer"
        onClick={handleClick}
      >
        <rect width={width} height={height} fill="#f8f8f8" />
        <rect x={vpX} y={0} width={vpW} height={height} fill={color} fillOpacity={0.08} />
        {annotations.map((ann, i) => {
          const sel = ann.target.selector;
          if (sel.type !== 'TextPositionSelector' || sel.start == null) return null;
          const x = (sel.start / documentLength) * width;
          return <line key={i} x1={x} y1={0} x2={x} y2={height} stroke={color} strokeOpacity={0.6} />;
        })}
        <rect x={vpX} y={0} width={vpW} height={height} fill="none" stroke={color} strokeWidth={1} strokeOpacity={0.4} rx={1} />
      </svg>
    </div>
  );
}

export default function OverviewBar() {
  const tracks = useProjectStore((s) => s.tracks);
  const referenceText = useProjectStore((s) => s.referenceText);
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const trackStates = useTrackStore((s) => s.tracks);
  const searchMatches = useSearchStore((s) => s.matches);
  const visibleRange = useViewStore((s) => s.visibleParagraphRange);
  const docLen = referenceText.length || 1;

  const containerRef = useRef<HTMLDivElement>(null);
  const [barWidth, setBarWidth] = useState(600);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setBarWidth(Math.max(100, entry.contentRect.width - 80));
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const vpStart = visibleRange && paragraphs.length > 0
    ? paragraphs[visibleRange[0]]?.start ?? 0
    : 0;
  const vpEnd = visibleRange && paragraphs.length > 0
    ? paragraphs[Math.min(visibleRange[1], paragraphs.length - 1)]?.end ?? docLen
    : docLen;

  const trackNames = Object.keys(tracks).filter((n) => n !== 'segments');

  const navigateToFraction = useCallback((fraction: number) => {
    const charOffset = Math.round(fraction * docLen);
    const targetPara = paragraphs.findIndex((p) => p.end >= charOffset);
    if (targetPara >= 0) {
      useViewStore.getState().setSelectedParagraphIndex(targetPara);
      useViewStore.getState().requestScrollToParagraph(targetPara);
    }
  }, [docLen, paragraphs]);

  return (
    <div
      ref={containerRef}
      className="border-t border-[var(--color-border)] bg-[var(--color-bg-muted)] px-2 py-1 w-full"
    >
      {trackNames.map((name) => (
        <DensityBarcode
          key={name}
          label={name}
          annotations={tracks[name] ?? []}
          color={TRACK_COLORS[name] ?? '#888'}
          documentLength={docLen}
          width={barWidth}
          height={12}
          visible={trackStates[name]?.visible ?? true}
          viewportStart={vpStart}
          viewportEnd={vpEnd}
          onClickPosition={navigateToFraction}
        />
      ))}
      {searchMatches.length > 0 && (
        <div className="flex items-center gap-1">
          <span className="w-[60px] text-[0.7em] text-[var(--color-text-muted)] text-right">search</span>
          <svg
            width={barWidth}
            height={12}
            role="img"
            aria-label="Search matches"
            className="cursor-pointer"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const fraction = (e.clientX - rect.left) / rect.width;
              navigateToFraction(fraction);
            }}
          >
            <rect width={barWidth} height={12} fill="#f8f8f8" />
            <rect
              x={(vpStart / docLen) * barWidth}
              y={0}
              width={Math.max(2, ((vpEnd - vpStart) / docLen) * barWidth)}
              height={12}
              fill="#f1c40f"
              fillOpacity={0.1}
            />
            {searchMatches.map((m, i) => {
              const x = (m.start / docLen) * barWidth;
              return <line key={i} x1={x} y1={0} x2={x} y2={12} stroke="#f1c40f" strokeWidth={2} />;
            })}
          </svg>
        </div>
      )}
    </div>
  );
}
