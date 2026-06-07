import { useTrackStore } from '../stores/trackStore';
import { useProjectStore } from '../stores/projectStore';

const EVIDENCE_LABELS: Record<number, string> = {
  1: 'E1', 2: 'E2', 3: 'E3', 4: 'E4', 5: 'E5',
};

export default function TrackPanel() {
  const tracks = useTrackStore((s) => s.tracks);
  const toggleTrack = useTrackStore((s) => s.toggleTrack);
  const info = useProjectStore((s) => s.info);
  const trackNames = Object.keys(tracks).sort();

  const trackAnnotationCounts: Record<string, number> = {};
  if (info) {
    for (const t of info.tracks) {
      trackAnnotationCounts[t.name] = t.annotation_count;
    }
  }

  return (
    <aside style={{
      width: '200px',
      borderRight: '1px solid #e0e0e0',
      padding: '12px',
      overflowY: 'auto',
      flexShrink: 0,
      fontSize: '0.85em',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '10px', fontSize: '1em' }}>Tracks</div>
      {trackNames.map((name, idx) => {
        const state = tracks[name];
        const count = trackAnnotationCounts[name] ?? 0;
        return (
          <div
            key={name}
            onClick={() => toggleTrack(name)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 0',
              borderBottom: '1px solid #f0f0f0',
              opacity: state.visible ? 1 : 0.35,
              cursor: 'pointer',
              transition: 'opacity 0.1s',
            }}
          >
            <div style={{
              width: '10px',
              height: '10px',
              borderRadius: '2px',
              backgroundColor: state.color,
              flexShrink: 0,
            }} />
            <span style={{ flex: 1 }}>{name}</span>
            <span style={{
              padding: '1px 4px',
              fontSize: '0.7em',
              color: '#2980b9',
              backgroundColor: '#3498db15',
              borderRadius: '2px',
              fontWeight: 600,
            }}>
              {EVIDENCE_LABELS[info?.tracks.find(t => t.name === name)?.track_id ?? 5] ?? 'E5'}
            </span>
            <span style={{ color: '#999', fontSize: '0.8em' }}>{count}</span>
            <kbd style={{
              padding: '0 3px',
              fontSize: '0.7em',
              color: '#bbb',
              border: '1px solid #eee',
              borderRadius: '2px',
            }}>
              {idx + 1}
            </kbd>
          </div>
        );
      })}
    </aside>
  );
}
