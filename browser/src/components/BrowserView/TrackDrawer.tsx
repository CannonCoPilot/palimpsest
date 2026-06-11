import { useTrackStore } from '../../stores/trackStore';
import { useBrowserStore } from '../../stores/browserStore';
import { TRACK_COLORS } from '../../utils/trackColors';

export default function TrackDrawer() {
  const trackStates = useTrackStore((s) => s.tracks);
  const trackOrder = useTrackStore((s) => s.trackOrder);
  const overviewBarHidden = useBrowserStore((s) => s.overviewBarHidden);
  const toggleOverviewBarTrack = useBrowserStore((s) => s.toggleOverviewBarTrack);
  const toggleDrawer = useBrowserStore((s) => s.toggleDrawer);

  const trackNames = trackOrder.filter((n) => n !== 'segments');

  return (
    <div className="absolute top-0 left-0 bottom-0 w-[240px] bg-[var(--color-bg)] border-r border-[var(--color-border)] shadow-[var(--shadow-popover)] z-[var(--z-popover)] flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--color-border)]">
        <span className="font-semibold text-[0.85em] font-[var(--font-sans)]">Overview Bar Tracks</span>
        <button
          onClick={toggleDrawer}
          className="text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-text)] text-[1.2em]"
        >
          ✕
        </button>
      </div>
      <div className="px-3 py-1.5 text-[0.7em] text-[var(--color-text-muted)] border-b border-[var(--color-border-subtle)]">
        Show/hide tracks in the bottom overview bar.
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {trackNames.map((name) => {
          const state = trackStates[name];
          const color = TRACK_COLORS[name] ?? '#888';
          const isVisible = !overviewBarHidden.has(name);
          return (
            <label
              key={name}
              className="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em] font-[var(--font-sans)]"
            >
              <input
                type="checkbox"
                checked={isVisible}
                onChange={() => toggleOverviewBarTrack(name)}
                className="accent-[var(--color-primary)]"
              />
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
              <span className="truncate">{name}</span>
              <span className="ml-auto text-[var(--color-text-muted)] text-[0.85em]">
                {state?.annotationCount ?? 0}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
