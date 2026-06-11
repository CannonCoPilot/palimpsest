import { useProjectStore } from '../../stores/projectStore';
import { TRACK_COLORS } from '../../utils/trackColors';

const EXPECTED_TRACKS = [
  'entities', 'sentiment', 'lexical', 'syntax', 'dialogue',
  'topics', 'narrative_arc', 'coreference', 'self_similarity',
  'lithmm', 'compartments', 'sections',
];

function TrackSkeletonRow({ name, loaded }: { name: string; loaded: boolean }) {
  const color = TRACK_COLORS[name] ?? '#888';
  return (
    <div className="flex items-center gap-2 py-1">
      <div className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: loaded ? color : '#e0e0e0' }} />
      <span className={`text-[0.8em] flex-1 ${loaded ? 'text-[var(--color-text)]' : 'text-[var(--color-text-muted)]'}`}>
        {name}
      </span>
      {loaded ? (
        <span className="text-[0.7em] text-[var(--color-success)]">✓</span>
      ) : (
        <div className="w-3 h-3 border-2 border-[var(--color-bg-muted)] border-t-[var(--color-primary)] rounded-full animate-spin" />
      )}
    </div>
  );
}

export default function LoadingOverlay() {
  const loadingState = useProjectStore((s) => s.loadingState);
  const loadingStep = useProjectStore((s) => s.loadingStep);
  const loadedTracks = useProjectStore((s) => Object.keys(s.tracks));

  if (loadingState !== 'loading') return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 bg-white/90 flex items-center justify-center z-[var(--z-overlay)]"
    >
      <div className="p-6 bg-[var(--color-bg)] rounded-[var(--radius-lg)] shadow-[var(--shadow-popover)] min-w-[300px]">
        <div className="text-center mb-4">
          <div className="inline-block w-8 h-8 border-3 border-[var(--color-bg-muted)] border-t-[var(--color-primary)] rounded-full animate-spin mb-2" />
          <h2 className="text-lg font-semibold font-[var(--font-serif)]">Loading Palimpsest</h2>
          <div className="text-[var(--color-text-muted)] text-sm">{loadingStep || 'Preparing...'}</div>
        </div>

        <div className="border-t border-[var(--color-border-subtle)] pt-3">
          <div className="text-[0.7em] text-[var(--color-text-muted)] font-semibold mb-1">Tracks</div>
          {EXPECTED_TRACKS.map((name) => (
            <TrackSkeletonRow
              key={name}
              name={name}
              loaded={loadedTracks.includes(name)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
