/**
 * TrackPanel — left sidebar with track toggles, colors, and annotation counts.
 */

import { useProjectStore } from '../../stores/projectStore';
import { useTrackStore } from '../../stores/trackStore';
import { TRACK_COLORS } from '../../utils/trackColors';

interface TrackRowProps {
  name: string;
  count: number;
  color: string;
  visible: boolean;
  shortcut: number;
  evidenceLevel: string;
  onToggle: () => void;
}

const EVIDENCE_LEVEL_FALLBACK: Record<string, string> = {
  entities: 'E4',
  sentiment: 'E5',
  lexical: 'E5',
  dialogue: 'E5',
  topics: 'E4',
};

function TrackRow({ name, count, color, visible, shortcut, evidenceLevel, onToggle }: TrackRowProps): JSX.Element {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 0',
        borderBottom: '1px solid #f0f0f0',
        opacity: visible ? 1 : 0.4,
        cursor: 'pointer',
      }}
      onClick={onToggle}
    >
      <div
        style={{
          width: '10px',
          height: '10px',
          borderRadius: '2px',
          backgroundColor: color,
          flexShrink: 0,
        }}
      />
      <span style={{ flex: 1, fontSize: '0.9em' }}>{name}</span>
      <span
        style={{
          padding: '1px 4px',
          fontSize: '0.65em',
          color: '#2980b9',
          backgroundColor: '#3498db22',
          borderRadius: '2px',
          fontWeight: 'bold',
        }}
        title={evidenceLevel === 'E4' ? 'ML prediction' : 'Rule-based/statistical'}
      >
        {evidenceLevel}
      </span>
      <span style={{ color: '#999', fontSize: '0.8em' }}>{count}</span>
      <kbd
        style={{
          padding: '0 3px',
          fontSize: '0.7em',
          color: '#aaa',
          border: '1px solid #ddd',
          borderRadius: '2px',
        }}
      >
        {shortcut}
      </kbd>
    </div>
  );
}

export default function TrackPanel(): JSX.Element {
  const projectTracks = useProjectStore((s) => s.tracks);
  const trackStates = useTrackStore((s) => s.tracks);
  const toggleTrack = useTrackStore((s) => s.toggleTrack);
  const trackNames = Object.keys(projectTracks).filter((n) => n !== 'segments').sort();

  return (
    <aside
      aria-label="Track controls"
      style={{
        width: '200px',
        borderRight: '1px solid #ddd',
        overflowY: 'auto',
        padding: '8px',
        fontSize: '0.85em',
      }}
    >
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>Tracks</div>
      {trackNames.map((name, idx) => (
        <TrackRow
          key={name}
          name={name}
          count={projectTracks[name]?.length ?? 0}
          color={TRACK_COLORS[name] ?? '#888'}
          visible={trackStates[name]?.visible ?? true}
          shortcut={idx + 1}
          evidenceLevel={trackStates[name]?.manifest?.evidenceLevel ?? EVIDENCE_LEVEL_FALLBACK[name] ?? 'E5'}
          onToggle={() => toggleTrack(name)}
        />
      ))}
      {trackNames.length === 0 && (
        <div style={{ color: '#999', fontStyle: 'italic' }}>No tracks loaded</div>
      )}
    </aside>
  );
}
