/**
 * Shared mask-editing context menu for the import wizard's text views.
 *
 * Both Step 2 (the full-text reader) and Step 3 (the boundary-editor panel beside
 * the section map) render the manuscript text with per-character `data-off` spans.
 * A right-click — including a MacBook trackpad two-finger tap or Control-click,
 * both of which Chrome delivers as a `contextmenu` event — resolves to an absolute
 * character offset and opens this menu for precise, drag-free mask operations.
 */

import { useEffect, useMemo, useState, type ReactElement } from 'react';
import { useSectionStore } from '../../stores/sectionStore';
import type { LayoutSection, SectionType } from '../../utils/sectionMasking';
import { deepestSectionAt } from './textOffset';

// #28 — right-click mask editor for the wizard's text views. Precise per-point ops
// that work across arbitrarily large intervals without dragging: set the selected
// element's start/end at this point, change its type, split the element under the
// cursor, or add a new element here. Drag editing in Step 3 stays available too.
export function MaskContextMenu({
  x,
  y,
  off,
  sections,
  types,
  selectedId,
  onClose,
}: {
  x: number;
  y: number;
  off: number;
  sections: LayoutSection[];
  types: SectionType[];
  selectedId: string | null;
  onClose: () => void;
}): ReactElement {
  const [sub, setSub] = useState<'change' | 'add' | null>(null);
  const selected = sections.find((s) => s.id === selectedId) ?? null;
  const hit = useMemo(() => deepestSectionAt(sections, off), [sections, off]);
  const typeLabel = (key: string): string => types.find((t) => t.key === key)?.label ?? key;
  const store = useSectionStore.getState;

  useEffect(() => {
    const close = (): void => onClose();
    // Capture-phase + stopImmediatePropagation so Esc closes the menu only, not the
    // surrounding full-screen import view (whose own Esc handler is registered first).
    const esc = (e: KeyboardEvent): void => { if (e.key === 'Escape') { e.stopImmediatePropagation(); onClose(); } };
    window.addEventListener('click', close);
    window.addEventListener('keydown', esc, true);
    return () => { window.removeEventListener('click', close); window.removeEventListener('keydown', esc, true); };
  }, [onClose]);

  const run = (fn: () => void) => () => { fn(); onClose(); };
  const item = 'w-full text-left px-3 py-1.5 text-[13px] flex items-center gap-2 enabled:hover:bg-white/10 disabled:opacity-35';
  const left = Math.min(x, window.innerWidth - 244);
  const top = Math.min(y, window.innerHeight - 360);

  const TypeList = ({ onPick }: { onPick: (key: string) => void }): ReactElement => (
    <div className="max-h-[200px] overflow-y-auto bg-black/20">
      {types.map((t) => (
        <button key={t.key} type="button" className={`${item} pl-6`} onClick={run(() => onPick(t.key))}>
          <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: t.color }} />
          <span className="truncate">{t.label}</span>
        </button>
      ))}
    </div>
  );

  return (
    <div
      className="fixed z-[var(--z-overlay)] min-w-[214px] max-h-[80vh] overflow-y-auto rounded-lg bg-[#2a2a2c] ring-1 ring-white/15 shadow-[0_16px_40px_rgba(0,0,0,0.5)] py-1 text-[#e8e8ea]"
      style={{ left, top }}
      onClick={(e) => e.stopPropagation()}
      onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); }}
    >
      {selected ? (
        <>
          <div className="px-3 py-1 text-[10px] uppercase tracking-wide text-[#8a8a90] truncate">
            Selected: {selected.label || typeLabel(selected.type)}
          </div>
          <button type="button" className={item} disabled={off >= selected.end} onClick={run(() => store().updateSection(selected.id, { start: off }))}>Set start here</button>
          <button type="button" className={item} disabled={off <= selected.start} onClick={run(() => store().updateSection(selected.id, { end: off }))}>Set end here</button>
          <button type="button" className={item} onClick={() => setSub(sub === 'change' ? null : 'change')}>
            Change type<span className="ml-auto text-[#8a8a90]">{sub === 'change' ? '▾' : '▸'}</span>
          </button>
          {sub === 'change' && <TypeList onPick={(key) => store().updateSection(selected.id, { type: key })} />}
          <div className="my-1 border-t border-white/10" />
        </>
      ) : (
        <div className="px-3 py-1 text-[11px] text-[#8a8a90]">Left-click text to select an element.</div>
      )}

      {hit && (
        <>
          {hit.id !== selectedId && (
            <button type="button" className={item} onClick={run(() => store().setSelected(hit.id))}>
              Select “{(hit.label || typeLabel(hit.type)).slice(0, 24)}”
            </button>
          )}
          <button type="button" className={item} disabled={off <= hit.start || off >= hit.end} onClick={run(() => store().splitSection(hit.id, off))}>Split element here</button>
          <button type="button" className={`${item} text-[#ff453a]`} onClick={run(() => store().removeSection(hit.id))}>Delete this element</button>
          <div className="my-1 border-t border-white/10" />
        </>
      )}

      <button type="button" className={item} onClick={() => setSub(sub === 'add' ? null : 'add')}>
        Add mask element here<span className="ml-auto text-[#8a8a90]">{sub === 'add' ? '▾' : '▸'}</span>
      </button>
      {sub === 'add' && <TypeList onPick={(key) => store().addSection(key, off, Math.min(store().textLen, off + 400))} />}
    </div>
  );
}
