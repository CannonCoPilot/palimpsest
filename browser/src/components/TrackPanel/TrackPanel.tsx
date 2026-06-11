import { useProjectStore } from '../../stores/projectStore';
import { useTrackStore, type DisplayMode } from '../../stores/trackStore';
import { TRACK_COLORS } from '../../utils/trackColors';
import { Tooltip } from '../common/Tooltip';

const EVIDENCE_LEVEL_FALLBACK: Record<string, string> = {
  entities: 'E4',
  sentiment: 'E5',
  lexical: 'E5',
  dialogue: 'E5',
  topics: 'E4',
};

const MODE_LABELS: { mode: DisplayMode; label: string; tip: string }[] = [
  { mode: 'dense', label: 'D', tip: 'Dense — barcode only in OverviewBar' },
  { mode: 'pack', label: 'P', tip: 'Pack — block annotations' },
  { mode: 'inline', label: 'I', tip: 'Inline — colored text spans' },
];

interface TrackRowProps {
  name: string;
  count: number;
  color: string;
  visible: boolean;
  shortcut: number;
  evidenceLevel: string;
  displayMode: DisplayMode;
  onToggle: () => void;
  onModeChange: (mode: DisplayMode) => void;
}

function TrackRow({ name, count, color, visible, shortcut, evidenceLevel, displayMode, onToggle, onModeChange }: TrackRowProps) {
  return (
    <div className="flex items-center gap-1.5 py-1 border-b border-[var(--color-border-subtle)]" style={{ opacity: visible ? 1 : 0.4 }}>
      <div
        className="w-2.5 h-2.5 rounded-sm shrink-0 cursor-pointer"
        style={{ backgroundColor: color }}
        onClick={onToggle}
        role="switch"
        aria-checked={visible}
        aria-label={`Toggle ${name} track`}
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } }}
      />
      <span className="flex-1 text-[0.9em] cursor-pointer truncate" onClick={onToggle}>{name}</span>
      <div className="flex gap-px" onClick={(e) => e.stopPropagation()}>
        {MODE_LABELS.map(({ mode, label, tip }) => (
          <Tooltip key={mode} content={tip} side="right">
            <button
              onClick={() => onModeChange(mode)}
              className={`w-4 h-4 text-[0.55em] leading-none border rounded-sm cursor-pointer ${
                displayMode === mode
                  ? 'bg-[var(--color-primary-subtle)] text-[var(--color-primary)] border-[var(--color-primary)] font-bold'
                  : 'bg-transparent text-[var(--color-text-muted)] border-[var(--color-border-subtle)] hover:border-[var(--color-border)]'
              }`}
            >
              {label}
            </button>
          </Tooltip>
        ))}
      </div>
      <Tooltip content={evidenceLevel === 'E4' ? 'ML prediction' : 'Rule-based/statistical'} side="right">
        <span className="px-1 text-[0.65em] text-[var(--color-primary-hover)] bg-[var(--color-primary-subtle)] rounded-sm font-bold">
          {evidenceLevel}
        </span>
      </Tooltip>
      <span className="text-[var(--color-text-muted)] text-[0.8em]">{count}</span>
      <kbd className="px-0.5 text-[0.7em] text-[#aaa] border border-[var(--color-border)] rounded-sm">
        {shortcut}
      </kbd>
    </div>
  );
}

export default function TrackPanel() {
  const projectTracks = useProjectStore((s) => s.tracks);
  const trackStates = useTrackStore((s) => s.tracks);
  const toggleTrack = useTrackStore((s) => s.toggleTrack);
  const setDisplayMode = useTrackStore((s) => s.setDisplayMode);
  const trackNames = Object.keys(projectTracks).filter((n) => n !== 'segments').sort();

  return (
    <aside
      aria-label="Track controls"
      className="w-[var(--width-track-panel)] border-r border-[var(--color-border)] overflow-y-auto p-2 text-[0.85em]"
    >
      <div className="font-bold mb-2">Tracks</div>
      {trackNames.map((name, idx) => (
        <TrackRow
          key={name}
          name={name}
          count={projectTracks[name]?.length ?? 0}
          color={TRACK_COLORS[name] ?? '#888'}
          visible={trackStates[name]?.visible ?? true}
          shortcut={idx + 1}
          evidenceLevel={trackStates[name]?.manifest?.evidenceLevel ?? EVIDENCE_LEVEL_FALLBACK[name] ?? 'E5'}
          displayMode={trackStates[name]?.displayMode ?? 'inline'}
          onToggle={() => toggleTrack(name)}
          onModeChange={(mode) => setDisplayMode(name, mode)}
        />
      ))}
      {trackNames.length === 0 && (
        <div className="text-[var(--color-text-muted)] italic">No tracks loaded</div>
      )}
    </aside>
  );
}
