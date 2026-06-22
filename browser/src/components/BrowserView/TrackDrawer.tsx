import { useTrackStore } from '../../stores/trackStore';
import { useBrowserStore } from '../../stores/browserStore';
import { useProjectStore, getActiveProject } from '../../stores/projectStore';
import { TRACK_COLORS } from '../../utils/trackColors';
import { buildElementGroups } from '../../utils/maskTypeGroups';

// The Browser "Tracks" drawer toggles what is shown *in the Browser lanes*: the
// element-type GROUP lanes (Structure / Content / Headings / Notes) and the analysis
// tracks (entities, sentiment, …) — not the bottom overview-bar barcodes.
export default function TrackDrawer() {
  const trackStates = useTrackStore((s) => s.tracks);
  const trackOrder = useTrackStore((s) => s.trackOrder);
  const toggleTrack = useTrackStore((s) => s.toggleTrack);
  const hiddenGroups = useBrowserStore((s) => s.hiddenGroups);
  const toggleGroup = useBrowserStore((s) => s.toggleGroup);
  const toggleDrawer = useBrowserStore((s) => s.toggleDrawer);
  const elements = useProjectStore((s) => getActiveProject(s).tracks['elements'] ?? []);

  const groups = buildElementGroups(elements);
  const analysisTracks = trackOrder.filter((n) => n !== 'segments' && n !== 'sections' && n !== 'elements');

  return (
    <div className="absolute top-0 left-0 bottom-0 w-[240px] bg-[var(--color-bg)] border-r border-[var(--color-border)] shadow-[var(--shadow-popover)] z-[var(--z-popover)] flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--color-border)]">
        <span className="font-semibold text-[0.85em] font-[var(--font-sans)]">Browser Tracks</span>
        <button
          onClick={toggleDrawer}
          className="text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-text)] text-[1.2em]"
        >
          ✕
        </button>
      </div>
      <div className="flex-1 overflow-y-auto py-1 font-[var(--font-sans)]">
        {groups.length > 0 && (
          <div className="px-3 py-1 text-[0.68em] uppercase tracking-wide text-[var(--color-text-muted)]">
            Element groups
          </div>
        )}
        {groups.map((g) => {
          const isVisible = !hiddenGroups.has(g.key);
          const count = g.presentTypes.reduce((n, t) => n + t.count, 0);
          return (
            <label
              key={g.key}
              className="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em]"
            >
              <input
                type="checkbox"
                checked={isVisible}
                onChange={() => toggleGroup(g.key)}
                className="accent-[var(--color-primary)]"
              />
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: g.presentTypes[0]?.color ?? '#5ac8fa' }} />
              <span className="truncate font-semibold">{g.label}</span>
              <span className="ml-auto text-[var(--color-text-muted)] text-[0.85em]">{count}</span>
            </label>
          );
        })}

        {analysisTracks.length > 0 && (
          <div className="px-3 py-1 mt-1 text-[0.68em] uppercase tracking-wide text-[var(--color-text-muted)] border-t border-[var(--color-border-subtle)]">
            Analysis tracks
          </div>
        )}
        {analysisTracks.map((name) => {
          const state = trackStates[name];
          const color = TRACK_COLORS[name] ?? '#888';
          const isVisible = state?.visible ?? false;
          return (
            <label
              key={name}
              className="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em]"
            >
              <input
                type="checkbox"
                checked={isVisible}
                onChange={() => toggleTrack(name)}
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
