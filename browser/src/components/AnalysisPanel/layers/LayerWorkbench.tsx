// The Explore tab: the plural layer workbench. Owns lane order / visibility / overlay (the
// LayerManager is controlled), and renders the lane stack from those — every visible layer as its
// own lane, with overlaid layers superimposed in one shared lane for side-by-side comparison. This
// is where FR-13 "plural layers coexist; reorder / toggle / overlay" is realized.
import { useEffect, useMemo, useState } from 'react';
import { LayerManager } from './LayerManager';
import { LayerLane, LANE_W, LANE_H } from './LayerLane';
import { EmbeddingScatter } from './EmbeddingScatter';
import { layerKey, laneKind, type LayerRef } from './types';

function laneLabel(ref: LayerRef): string {
  return `${ref.trackName} · ${ref.layer.label.slice(0, 8)}`;
}

export function LayerWorkbench({ projectId, layers }: { projectId: string; layers: LayerRef[] }) {
  // Keyed maps so order/visibility/overlay survive layers arriving/leaving across status polls.
  const [orderKeys, setOrderKeys] = useState<string[]>([]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [overlay, setOverlay] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<LayerRef | null>(null);

  const byKey = useMemo(() => {
    const m = new Map<string, LayerRef>();
    for (const ref of layers) m.set(layerKey(ref), ref);
    return m;
  }, [layers]);

  // Reconcile the persisted order with the live layer set: keep known order, append newcomers, drop
  // departed keys. No fetch, no churn when the set is unchanged.
  useEffect(() => {
    setOrderKeys((prev) => {
      const live = layers.map(layerKey);
      const liveSet = new Set(live);
      const kept = prev.filter((k) => liveSet.has(k));
      const added = live.filter((k) => !kept.includes(k));
      const next = [...kept, ...added];
      return next.length === prev.length && next.every((k, i) => k === prev[i]) ? prev : next;
    });
  }, [layers]);

  const orderedRefs = orderKeys.map((k) => byKey.get(k)).filter((r): r is LayerRef => !!r);
  const visible = orderedRefs.filter((r) => !hidden.has(layerKey(r)));
  const overlaid = visible.filter((r) => overlay.has(layerKey(r)));
  const solo = visible.filter((r) => !overlay.has(layerKey(r)));

  const toggle = (set: Set<string>, key: string): Set<string> => {
    const next = new Set(set);
    if (next.has(key)) next.delete(key); else next.add(key);
    return next;
  };

  return (
    <div className="flex flex-col gap-3 p-3">
      <LayerManager
        order={orderedRefs}
        hidden={hidden}
        overlay={overlay}
        onReorder={(next) => setOrderKeys(next.map(layerKey))}
        onToggleHidden={(key) => setHidden((s) => toggle(s, key))}
        onToggleOverlay={(key) => setOverlay((s) => toggle(s, key))}
        onOpenStats={(ref) => setSelected((cur) => (cur && layerKey(cur) === layerKey(ref) ? null : ref))}
      />

      {/* Lane stack — the visible proof that plural layers render simultaneously. */}
      <div aria-label="Lane stack" className="flex flex-col gap-1.5">
        {overlaid.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="w-[120px] shrink-0 text-[0.7em] text-[var(--color-text-muted)] text-right truncate">
              overlay ({overlaid.length})
            </span>
            <div className="relative" style={{ width: LANE_W, height: LANE_H }} data-testid="overlay-lane">
              {overlaid.map((ref) => (
                <div key={layerKey(ref)} className="absolute inset-0" style={{ opacity: 0.55, mixBlendMode: 'multiply' }}>
                  <LayerLane projectId={projectId} trackName={ref.trackName} layer={ref.layer} />
                </div>
              ))}
            </div>
          </div>
        )}
        {solo.map((ref) => (
          <div key={layerKey(ref)} className="flex items-center gap-2">
            <span className="w-[120px] shrink-0 text-[0.7em] text-[var(--color-text-muted)] text-right truncate"
              title={laneLabel(ref)}>
              {laneLabel(ref)}
            </span>
            <LayerLane projectId={projectId} trackName={ref.trackName} layer={ref.layer} />
          </div>
        ))}
        {visible.length === 0 && (
          <div className="text-[0.78em] text-[var(--color-text-muted)] italic">All layers hidden.</div>
        )}
      </div>

      {/* Instant stats drill-in (provenance + the manifest's precomputed stats, no fetch). The P6
          stats panel will deepen this with selectable distributions. */}
      {selected && (
        <div className="border border-[var(--color-border)] rounded p-2 text-[0.78em]" aria-label="Layer detail">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold">{selected.trackName} · <code>{selected.layer.label.slice(0, 12)}</code></span>
            <button onClick={() => setSelected(null)} className="text-[var(--color-text-muted)] hover:underline cursor-pointer">close</button>
          </div>
          <KeyVals title="capability" obj={selected.layer.capability} />
          <KeyVals title="stats" obj={selected.layer.stats} />
          {laneKind(selected.layer.rendering) === 'embedding-lane' && (
            <div className="mt-2">
              <EmbeddingScatter projectId={projectId} layer={selected.layer} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function KeyVals({ title, obj }: { title: string; obj: Record<string, unknown> | null | undefined }) {
  const entries = obj ? Object.entries(obj).filter(([, v]) => v != null && typeof v !== 'object') : [];
  if (entries.length === 0) return null;
  return (
    <div className="mb-1">
      <div className="text-[0.72em] font-semibold text-[var(--color-text-muted)]">{title}</div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 font-[var(--font-mono)] text-[0.75em]">
        {entries.map(([k, v]) => (
          <span key={k}><span className="text-[var(--color-text-muted)]">{k}:</span> {String(v)}</span>
        ))}
      </div>
    </div>
  );
}
