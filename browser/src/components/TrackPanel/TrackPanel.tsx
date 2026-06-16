import { useMemo, useState, memo, type ReactElement } from 'react';
import { DndContext, closestCenter, type DragEndEvent } from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useProjectStore, getActiveProject } from '../../stores/projectStore';
import { useTrackStore, type DisplayMode } from '../../stores/trackStore';
import { useElementVisibilityStore } from '../../stores/elementVisibilityStore';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
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
  id: string;
  name: string;
  count: number;
  color: string;
  visible: boolean;
  shortcut: number;
  evidenceLevel: string;
  displayMode: DisplayMode;
  confidenceThreshold: number;
  onToggle: () => void;
  onModeChange: (mode: DisplayMode) => void;
  onThresholdChange: (value: number) => void;
}

const SortableTrackRow = memo(function SortableTrackRow(props: TrackRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: props.id });
  const [expanded, setExpanded] = useState(false);
  const { name, count, color, visible, shortcut, evidenceLevel, displayMode, confidenceThreshold, onToggle, onModeChange, onThresholdChange } = props;

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: visible ? 1 : 0.4,
  };

  return (
    <div ref={setNodeRef} style={style} className="border-b border-[var(--color-border-subtle)]">
      <div className="flex items-center gap-1.5 py-1">
        <Tooltip content="Drag to reorder" side="left">
          <span {...attributes} {...listeners} className="cursor-grab text-[0.7em] text-[var(--color-text-muted)] select-none">⠿</span>
        </Tooltip>
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
        <Tooltip content="Click to expand settings" side="right">
          <span className="flex-1 text-[0.9em] cursor-pointer truncate" onClick={() => setExpanded(!expanded)}>
            {name}
          </span>
        </Tooltip>
        <div className="flex gap-px" onClick={(e) => e.stopPropagation()}>
          {MODE_LABELS.map(({ mode, label, tip }) => (
            <Tooltip key={mode} content={tip} side="right">
              <button
                onClick={() => onModeChange(mode)}
                className={`w-4 h-4 text-[0.55em] leading-none border rounded-sm cursor-pointer focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)] focus-visible:outline-offset-1 ${
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
      {expanded && visible && (
        <div className="flex items-center gap-1.5 pb-1.5 pl-6 pr-1">
          <Tooltip content={`Min confidence: ${Math.round(confidenceThreshold * 100)}%`} side="bottom">
            <span className="text-[0.65em] text-[var(--color-text-muted)] w-5 text-right">
              {Math.round(confidenceThreshold * 100)}%
            </span>
          </Tooltip>
          <input
            type="range"
            min="0"
            max="100"
            value={Math.round(confidenceThreshold * 100)}
            onChange={(e) => onThresholdChange(parseInt(e.target.value, 10) / 100)}
            className="flex-1 h-1 accent-[var(--color-primary)] cursor-pointer"
            aria-label={`Confidence threshold for ${name}`}
          />
        </div>
      )}
    </div>
  );
});

// #27 — per-element-type show/hide for the unified "elements" track. The subtypes
// (chapter, header, front_matter, custom layers…) are derived from the track's
// annotations; each carries its own color via palimpsest:color.
function ElementTypeToggles({ annotations }: { annotations: W3CAnnotation[] }): ReactElement | null {
  const hidden = useElementVisibilityStore((s) => s.hidden);
  const toggle = useElementVisibilityStore((s) => s.toggle);
  const showAll = useElementVisibilityStore((s) => s.showAll);

  const types = useMemo(() => {
    const m = new Map<string, { label: string; color: string; count: number }>();
    for (const a of annotations) {
      const b = a.body as Record<string, unknown>;
      const et = b['palimpsest:elementType'];
      if (typeof et !== 'string') continue;
      const color = typeof b['palimpsest:color'] === 'string' ? (b['palimpsest:color'] as string) : '#5ac8fa';
      const cur = m.get(et);
      if (cur) cur.count += 1;
      else m.set(et, { label: et.replace(/_/g, ' '), color, count: 1 });
    }
    return Array.from(m.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [annotations]);

  if (types.length === 0) return null;
  const anyHidden = types.some(([k]) => hidden[k]);

  return (
    <div className="mt-3 pt-2 border-t border-[var(--color-border-subtle)]">
      <div className="flex items-center justify-between mb-1">
        <span className="font-bold">Element types</span>
        {anyHidden && (
          <button onClick={showAll} className="text-[0.75em] text-[var(--color-primary)] hover:underline">show all</button>
        )}
      </div>
      {types.map(([key, t]) => {
        const isHidden = hidden[key] === true;
        return (
          <div key={key} className="flex items-center gap-1.5 py-0.5" style={{ opacity: isHidden ? 0.4 : 1 }}>
            <div
              className="w-2.5 h-2.5 rounded-sm shrink-0 cursor-pointer"
              style={{ backgroundColor: t.color }}
              onClick={() => toggle(key)}
              role="switch"
              aria-checked={!isHidden}
              aria-label={`Toggle ${t.label} elements`}
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(key); } }}
            />
            <span className="flex-1 text-[0.9em] capitalize cursor-pointer truncate" onClick={() => toggle(key)}>{t.label}</span>
            <span className="text-[var(--color-text-muted)] text-[0.8em]">{t.count}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function TrackPanel() {
  const projectTracks = useProjectStore((s) => getActiveProject(s).tracks);
  const trackStates = useTrackStore((s) => s.tracks);
  const trackOrder = useTrackStore((s) => s.trackOrder);
  const setTrackOrder = useTrackStore((s) => s.setTrackOrder);
  const toggleTrack = useTrackStore((s) => s.toggleTrack);
  const setDisplayMode = useTrackStore((s) => s.setDisplayMode);
  const setConfidenceThreshold = useTrackStore((s) => s.setConfidenceThreshold);

  const trackNames = trackOrder.length > 0
    ? trackOrder.filter((n) => n in projectTracks && n !== 'segments')
    : Object.keys(projectTracks).filter((n) => n !== 'segments').sort();

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = trackNames.indexOf(active.id as string);
    const newIndex = trackNames.indexOf(over.id as string);
    if (oldIndex === -1 || newIndex === -1) return;
    setTrackOrder(arrayMove(trackNames, oldIndex, newIndex));
  }

  return (
    <aside
      aria-label="Track controls"
      className="w-[var(--width-track-panel)] border-r border-[var(--color-border)] overflow-y-auto p-2 text-[0.85em]"
    >
      <div className="font-bold mb-2">Tracks</div>
      <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={trackNames} strategy={verticalListSortingStrategy}>
          {trackNames.map((name, idx) => (
            <SortableTrackRow
              key={name}
              id={name}
              name={name}
              count={projectTracks[name]?.length ?? 0}
              color={TRACK_COLORS[name] ?? '#888'}
              visible={trackStates[name]?.visible ?? true}
              shortcut={idx + 1}
              evidenceLevel={trackStates[name]?.manifest?.evidenceLevel ?? EVIDENCE_LEVEL_FALLBACK[name] ?? 'E5'}
              displayMode={trackStates[name]?.displayMode ?? 'inline'}
              confidenceThreshold={trackStates[name]?.confidenceThreshold ?? 0}
              onToggle={() => toggleTrack(name)}
              onModeChange={(mode) => setDisplayMode(name, mode)}
              onThresholdChange={(val) => setConfidenceThreshold(name, val)}
            />
          ))}
        </SortableContext>
      </DndContext>
      {trackNames.length === 0 && (
        <div className="text-[var(--color-text-muted)] italic">No tracks loaded</div>
      )}
      {projectTracks['elements'] && (trackStates['elements']?.visible ?? true) && (
        <ElementTypeToggles annotations={projectTracks['elements']} />
      )}
    </aside>
  );
}
