// The layer manager: lists every layer (across all layer-keyed tracks) with its provenance, render
// descriptor, and instant stats — read straight from the /analysis/status row, no fetch — and
// controls lane order (drag, reusing the TrackPanel @dnd-kit pattern), visibility, and overlay.
// Controlled: the LayerWorkbench owns order/hidden/overlay so the lane stack stays in lock-step.
import { memo } from 'react';
import { DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors, closestCenter, type DragEndEvent } from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy, arrayMove, sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { layerKey, laneKind, type LayerRef } from './types';

const str = (c: Record<string, unknown> | null | undefined, k: string): string =>
  c && c[k] != null ? String(c[k]) : '';

// A one-line, human-readable descriptor from the capability block — kind-specific but derived
// generically (no per-label code): chunk shows mode·size, embedding shows model·dim.
function describe(ref: LayerRef): string {
  const cap = ref.layer.capability ?? {};
  const kind = str(cap, 'kind') || ref.trackName;
  if (kind === 'embedding') {
    const model = str(cap, 'model') || 'embedding';
    const dim = str(cap, 'dim');
    return dim ? `${model} · d${dim}` : model;
  }
  const mode = str(cap, 'mode');
  const size = str(cap, 'size');
  return [kind, mode, size && `size ${size}`].filter(Boolean).join(' · ');
}

// The single most useful stat per kind, shown inline so the row is informative without opening P6.
function instantStat(ref: LayerRef): string {
  const s = ref.layer.stats ?? {};
  const count = str(s, 'count') || str(s, 'phrase_count');
  const cov = str(s, 'coverage_pct');
  return [count && `${count} units`, cov && `${cov}% cov`].filter(Boolean).join(' · ');
}

interface RowProps {
  refItem: LayerRef;
  id: string;
  index: number;
  hidden: boolean;
  overlaid: boolean;
  onToggleHidden: () => void;
  onToggleOverlay: () => void;
  onOpenStats: () => void;
}

const LayerRow = memo(function LayerRow(p: RowProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: p.id });
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: p.hidden ? 0.45 : 1 };
  const kind = laneKind(p.refItem.layer.rendering);
  const color = p.refItem.layer.rendering?.overviewBarRendering?.color ?? '#6366F1';

  return (
    <div ref={setNodeRef} style={style}
      className="flex items-center gap-2 py-1.5 px-2 border-b border-[var(--color-border-subtle)]">
      <span {...attributes} {...listeners}
        className="cursor-grab text-[0.8em] text-[var(--color-text-muted)] select-none focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)]"
        aria-label="Drag to reorder">⠿</span>
      <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: kind === 'embedding-lane' ? '#08306b' : color }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-[0.85em] truncate">{p.refItem.trackName}</span>
          <code className="text-[0.7em] text-[var(--color-text-muted)]">{p.refItem.layer.label.slice(0, 10)}</code>
        </div>
        <div className="text-[0.72em] text-[var(--color-text-muted)] truncate">
          {describe(p.refItem)}{instantStat(p.refItem) ? ` — ${instantStat(p.refItem)}` : ''}
        </div>
      </div>
      <button onClick={p.onOpenStats}
        className="px-1.5 py-0.5 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.7em]">
        stats →
      </button>
      <button onClick={p.onToggleOverlay} aria-pressed={p.overlaid} aria-label={`Overlay ${p.refItem.trackName} ${p.refItem.layer.label}`}
        className={`px-1.5 py-0.5 rounded border text-[0.7em] cursor-pointer ${p.overlaid
          ? 'bg-[var(--color-primary-subtle,#eff6ff)] text-[var(--color-primary)] border-[var(--color-primary)]'
          : 'border-[var(--color-border)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-muted)]'}`}>
        overlay
      </button>
      <button onClick={p.onToggleHidden} role="switch" aria-checked={!p.hidden}
        aria-label={`Toggle ${p.refItem.trackName} ${p.refItem.layer.label}`}
        className={`px-1.5 py-0.5 rounded border text-[0.7em] cursor-pointer ${p.hidden
          ? 'border-[var(--color-border)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-muted)]'
          : 'bg-[var(--color-primary-subtle,#eff6ff)] text-[var(--color-primary)] border-[var(--color-primary)]'}`}>
        {p.hidden ? 'show' : 'hide'}
      </button>
    </div>
  );
});

export function LayerManager({ order, hidden, overlay, onReorder, onToggleHidden, onToggleOverlay, onOpenStats }: {
  order: LayerRef[];
  hidden: Set<string>;
  overlay: Set<string>;
  onReorder: (next: LayerRef[]) => void;
  onToggleHidden: (key: string) => void;
  onToggleOverlay: (key: string) => void;
  onOpenStats: (ref: LayerRef) => void;
}) {
  const ids = order.map(layerKey);
  // Pointer for mouse drag; keyboard (with sortable coordinates) so reorder is accessible without a
  // pointer — a small a11y win over the TrackPanel pattern this otherwise reuses.
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const from = ids.indexOf(active.id as string);
    const to = ids.indexOf(over.id as string);
    if (from === -1 || to === -1) return;
    onReorder(arrayMove(order, from, to));
  }

  if (order.length === 0) {
    return (
      <div className="text-[0.8em] text-[var(--color-text-muted)] italic px-2 py-3">
        No layers yet. Run a chunking, repeat_mask, or embedding track to produce layers.
      </div>
    );
  }

  return (
    <div aria-label="Layer manager" className="border border-[var(--color-border)] rounded">
      <div className="px-2 py-1.5 text-[0.75em] font-semibold text-[var(--color-text-muted)] border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)]">
        Layers ({order.length}) — drag to reorder · toggle visibility · overlay to compare
      </div>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          {order.map((ref, i) => {
            const key = layerKey(ref);
            return (
              <LayerRow key={key} id={key} index={i} refItem={ref}
                hidden={hidden.has(key)} overlaid={overlay.has(key)}
                onToggleHidden={() => onToggleHidden(key)}
                onToggleOverlay={() => onToggleOverlay(key)}
                onOpenStats={() => onOpenStats(ref)} />
            );
          })}
        </SortableContext>
      </DndContext>
    </div>
  );
}
