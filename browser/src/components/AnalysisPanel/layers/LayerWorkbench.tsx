// The Explore tab: the plural layer workbench. Owns lane order / visibility / overlay (the
// LayerManager is controlled), and renders the lane stack from those — every visible layer as its
// own lane, with overlaid layers superimposed in one shared lane for side-by-side comparison. This
// is where FR-13 "plural layers coexist; reorder / toggle / overlay" is realized.
import { useEffect, useMemo, useState } from 'react';
import { LayerManager } from './LayerManager';
import { LayerLane, LANE_W, LANE_H } from './LayerLane';
import { LayerStatsPanel } from './LayerStatsPanel';
import { layerKey, type LayerRef } from './types';

function laneLabel(ref: LayerRef): string {
  return `${ref.trackName} · ${ref.layer.label.slice(0, 8)}`;
}

export function LayerWorkbench({ projectId, layers }: { projectId: string; layers: LayerRef[] }) {
  // Keyed maps so order/visibility/overlay survive layers arriving/leaving across status polls.
  const [orderKeys, setOrderKeys] = useState<string[]>([]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [overlay, setOverlay] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<LayerRef[]>([]); // up to 2, for side-by-side compare

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

  // Toggle a layer's stats panel; keep at most two open so a compare flow can sit them side by side.
  const openStats = (ref: LayerRef) => setSelected((cur) => {
    const key = layerKey(ref);
    if (cur.some((r) => layerKey(r) === key)) return cur.filter((r) => layerKey(r) !== key);
    return [...cur, ref].slice(-2);
  });

  return (
    <div className="flex flex-col gap-3 p-3">
      <LayerManager
        order={orderedRefs}
        hidden={hidden}
        overlay={overlay}
        onReorder={(next) => setOrderKeys(next.map(layerKey))}
        onToggleHidden={(key) => setHidden((s) => toggle(s, key))}
        onToggleOverlay={(key) => setOverlay((s) => toggle(s, key))}
        onOpenStats={openStats}
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
            <button onClick={() => openStats(ref)} aria-label={`Open stats for ${laneLabel(ref)}`}
              className="px-1.5 py-0.5 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.68em] shrink-0">
              stats
            </button>
          </div>
        ))}
        {visible.length === 0 && (
          <div className="text-[0.78em] text-[var(--color-text-muted)] italic">All layers hidden.</div>
        )}
      </div>

      {/* Per-layer stats panels (P6, FR-14): instant summary + selectable distributions. Up to two
          sit side by side for compare; opened from a LayerManager row or a lane's stats action. */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-3" aria-label="Layer stats panels" data-testid="stats-panels">
          {selected.map((ref) => (
            <LayerStatsPanel key={layerKey(ref)} projectId={projectId} refItem={ref}
              onClose={() => openStats(ref)} />
          ))}
        </div>
      )}
    </div>
  );
}
