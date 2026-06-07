/**
 * OverviewBar — density barcodes for each visible track + search ticks.
 * Clicking on the bar navigates to that position in the text.
 */

import { useProjectStore } from '../../stores/projectStore';
import { useTrackStore } from '../../stores/trackStore';
import { useSearchStore } from '../../stores/searchStore';
import { useViewStore } from '../../stores/viewStore';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { TRACK_COLORS } from '../../utils/trackColors';

interface BarcodeProps {
  label: string;
  annotations: W3CAnnotation[];
  color: string;
  documentLength: number;
  width: number;
  height: number;
  visible: boolean;
  onClickPosition: (fraction: number) => void;
}

function DensityBarcode({ label, annotations, color, documentLength, width, height, visible, onClickPosition }: BarcodeProps): JSX.Element {
  function handleClick(e: React.MouseEvent<SVGSVGElement>): void {
    const rect = e.currentTarget.getBoundingClientRect();
    const fraction = (e.clientX - rect.left) / rect.width;
    onClickPosition(fraction);
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', opacity: visible ? 1 : 0.3 }}>
      <span style={{ width: '60px', fontSize: '0.7em', color: '#888', textAlign: 'right' }}>{label}</span>
      <svg
        width={width}
        height={height}
        role="img"
        aria-label={`${label} density`}
        style={{ cursor: 'pointer' }}
        onClick={handleClick}
      >
        <rect width={width} height={height} fill="#f8f8f8" />
        {annotations.map((ann, i) => {
          const sel = ann.target.selector;
          if (sel.type !== 'TextPositionSelector' || sel.start == null) return null;
          const x = (sel.start / documentLength) * width;
          return <line key={i} x1={x} y1={0} x2={x} y2={height} stroke={color} strokeOpacity={0.6} />;
        })}
      </svg>
    </div>
  );
}

export default function OverviewBar(): JSX.Element {
  const tracks = useProjectStore((s) => s.tracks);
  const referenceText = useProjectStore((s) => s.referenceText);
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const trackStates = useTrackStore((s) => s.tracks);
  const searchMatches = useSearchStore((s) => s.matches);
  const docLen = referenceText.length || 1;
  const barWidth = 600;

  const trackNames = Object.keys(tracks).filter((n) => n !== 'segments');

  function navigateToFraction(fraction: number): void {
    const charOffset = Math.round(fraction * docLen);
    const targetPara = paragraphs.findIndex((p) => p.end >= charOffset);
    if (targetPara >= 0) {
      useViewStore.getState().setSelectedParagraphIndex(targetPara);
      useViewStore.getState().requestScrollToParagraph(targetPara);
    }
  }

  return (
    <div
      style={{
        borderTop: '1px solid #ddd',
        backgroundColor: '#f5f5f5',
        padding: '4px 8px',
        overflowX: 'auto',
      }}
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
          onClickPosition={navigateToFraction}
        />
      ))}
      {searchMatches.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ width: '60px', fontSize: '0.7em', color: '#888', textAlign: 'right' }}>search</span>
          <svg
            width={barWidth}
            height={12}
            role="img"
            aria-label="Search matches"
            style={{ cursor: 'pointer' }}
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const fraction = (e.clientX - rect.left) / rect.width;
              navigateToFraction(fraction);
            }}
          >
            <rect width={barWidth} height={12} fill="#f8f8f8" />
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
