/**
 * On-demand masking control panel. A right-side drawer (available on any tab) that drives
 * the non-destructive masking overlay: a master on/off, plus per-mask-type-layer keep/mask
 * toggles. Choices are a live session overlay — they gray text in the Reader/Browser and
 * scope analysis + subtext derivation WITHOUT rewriting the saved layout.
 */

import { useMemo, type ReactElement } from 'react';
import { useViewStore } from '../../stores/viewStore';
import { useSectionStore } from '../../stores/sectionStore';
import { useMaskOverlayStore, effectiveMaskByType } from '../../stores/maskOverlayStore';
import { MASK_TYPE_GROUPS, groupForType } from '../../utils/maskTypeGroups';

interface PresentType {
  type: string;
  label: string;
  color: string;
  count: number;
}

/** Mask-types actually present in the layout, with label/color/count, in group order. */
function presentTypes(
  sections: { type: string }[],
  types: { key: string; label: string; color: string }[],
): { groupKey: string; groupLabel: string; items: PresentType[] }[] {
  const counts = new Map<string, number>();
  for (const s of sections) counts.set(s.type, (counts.get(s.type) ?? 0) + 1);
  const meta = new Map(types.map((t) => [t.key, t]));
  const groups = [
    ...MASK_TYPE_GROUPS,
    { key: 'other', label: 'Other', types: [...counts.keys()].filter((t) => groupForType(t) === 'other') },
  ];
  const out: { groupKey: string; groupLabel: string; items: PresentType[] }[] = [];
  for (const g of groups) {
    const items = g.types
      .filter((t) => counts.has(t))
      .map((t) => ({
        type: t,
        label: meta.get(t)?.label ?? t.replace(/_/g, ' '),
        color: meta.get(t)?.color ?? '#8e8e93',
        count: counts.get(t)!,
      }));
    if (items.length > 0) out.push({ groupKey: g.key, groupLabel: g.label, items });
  }
  return out;
}

export default function MaskingPanel(): ReactElement | null {
  const open = useViewStore((s) => s.maskPanelOpen);
  const setOpen = useViewStore((s) => s.setMaskPanelOpen);
  const openWizard = useViewStore((s) => s.setSubtextWizardOpen);

  const sections = useSectionStore((s) => s.sections);
  const baseMask = useSectionStore((s) => s.maskByType);
  const types = useSectionStore((s) => s.types);

  const enabled = useMaskOverlayStore((s) => s.enabled);
  const setEnabled = useMaskOverlayStore((s) => s.setEnabled);
  const typeOverrides = useMaskOverlayStore((s) => s.typeOverrides);
  const setTypeMask = useMaskOverlayStore((s) => s.setTypeMask);
  const clearOverrides = useMaskOverlayStore((s) => s.clearOverrides);

  const groups = useMemo(() => presentTypes(sections, types), [sections, types]);
  const eff = effectiveMaskByType(baseMask, typeOverrides);
  const overrideCount = Object.keys(typeOverrides).length;

  if (!open) return null;

  return (
    <div className="w-[300px] shrink-0 border-l border-[var(--color-border)] bg-[var(--color-bg)] flex flex-col overflow-hidden font-[var(--font-sans)]">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--color-border)]">
        <strong className="text-[0.9em]">Masking</strong>
        <label className="ml-auto flex items-center gap-1.5 text-[0.8em] cursor-pointer select-none">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          {enabled ? 'On' : 'Off'}
        </label>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="px-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer"
          aria-label="Close masking panel"
        >
          ✕
        </button>
      </div>

      <p className="px-3 py-2 text-[0.72em] text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
        A live overlay — grays text and scopes analysis &amp; subtext export. Does not change the
        saved layout.
      </p>

      <div className={`flex-1 overflow-y-auto ${enabled ? '' : 'opacity-40 pointer-events-none'}`}>
        {groups.map((g) => (
          <div key={g.groupKey}>
            <div className="px-3 pt-2.5 pb-1 text-[0.65em] uppercase tracking-wide text-[var(--color-text-muted)]">
              {g.groupLabel}
            </div>
            {g.items.map((it) => {
              const masked = eff[it.type] ?? true;
              const overridden = it.type in typeOverrides;
              return (
                <button
                  key={it.type}
                  type="button"
                  onClick={() => setTypeMask(it.type, !masked)}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-left text-[0.8em] hover:bg-[var(--color-bg-muted)] cursor-pointer"
                  title={masked ? 'Masked (excluded). Click to keep.' : 'Kept (analyzed). Click to mask.'}
                >
                  <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: it.color }} />
                  <span className="truncate flex-1">{it.label}</span>
                  <span className="text-[0.85em] text-[var(--color-text-muted)] tabular-nums">{it.count}</span>
                  <span
                    className={`text-[0.72em] px-1.5 py-0.5 rounded ${
                      masked
                        ? 'bg-[#3a3a3d] text-[#f5f5f5]'
                        : 'bg-[var(--color-success-bg,#e6f4ea)] text-[var(--color-success,#137333)]'
                    }`}
                  >
                    {masked ? 'Masked' : 'Kept'}
                  </span>
                  {overridden && <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-border-focus,#1a73e8)]" title="Overridden" />}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2 px-3 py-2 border-t border-[var(--color-border)]">
        <button
          type="button"
          onClick={clearOverrides}
          disabled={overrideCount === 0}
          className="text-[0.78em] px-2 py-1 rounded border border-[var(--color-border)] hover:bg-[var(--color-bg-muted)] disabled:opacity-40 cursor-pointer"
        >
          Reset{overrideCount > 0 ? ` (${overrideCount})` : ''}
        </button>
        <button
          type="button"
          onClick={() => openWizard(true)}
          className="ml-auto text-[0.78em] px-2.5 py-1 rounded bg-[var(--color-accent,#1a73e8)] text-white hover:opacity-90 cursor-pointer"
        >
          Derive subtext…
        </button>
      </div>
    </div>
  );
}
