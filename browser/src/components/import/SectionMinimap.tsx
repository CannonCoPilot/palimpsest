/**
 * Bird's-eye section map (Step 3).
 *  - mode="vertical": the editable workbench — colored blocks down a strip, draggable
 *    top/bottom boundary handles (snap to paragraph starts), click to select,
 *    right-click to add a section. A right-hand gutter previews masked ranges.
 *  - mode="horizontal": a view-only overview with one lane per nesting depth.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type ReactElement } from 'react';
import { useSectionStore } from '../../stores/sectionStore';
import { computeMaskedIntervals, type LayoutSection } from '../../utils/sectionMasking';

const SNAP_PX = 6;

function depthOf(section: LayoutSection, byId: Map<string, LayoutSection>): number {
  let d = 0;
  let cur = section.parent_id ? byId.get(section.parent_id) : undefined;
  while (cur && d < 8) {
    d += 1;
    cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
  }
  return d;
}

type Menu = { x: number; y: number; offset: number; sectionId: string | null };

export default function SectionMinimap({
  mode,
  paragraphStarts,
}: {
  mode: 'vertical' | 'horizontal';
  paragraphStarts?: number[];
}): ReactElement {
  const sections = useSectionStore((s) => s.sections);
  const types = useSectionStore((s) => s.types);
  const textLen = useSectionStore((s) => s.textLen);
  const maskByType = useSectionStore((s) => s.maskByType);
  const selectedId = useSectionStore((s) => s.selectedId);
  const setSelected = useSectionStore((s) => s.setSelected);
  const updateSection = useSectionStore((s) => s.updateSection);
  const addSection = useSectionStore((s) => s.addSection);
  const removeSection = useSectionStore((s) => s.removeSection);

  const ref = useRef<HTMLDivElement>(null);
  const [menu, setMenu] = useState<Menu | null>(null);
  const dragRef = useRef<{ id: string; edge: 'start' | 'end' } | null>(null);

  const colorOf = useMemo(() => {
    const m = new Map(types.map((t) => [t.key, t.color]));
    return (type: string) => m.get(type) ?? '#8e8e93';
  }, [types]);

  const byId = useMemo(() => new Map(sections.map((s) => [s.id, s])), [sections]);
  const masked = useMemo(
    () => computeMaskedIntervals(sections, maskByType, textLen),
    [sections, maskByType, textLen],
  );
  const maxDepth = useMemo(
    () => Math.max(0, ...sections.map((s) => depthOf(s, byId))),
    [sections, byId],
  );

  const offsetFromClientY = useCallback(
    (clientY: number): number => {
      const el = ref.current;
      if (!el || textLen === 0) return 0;
      const r = el.getBoundingClientRect();
      const frac = Math.min(1, Math.max(0, (clientY - r.top) / r.height));
      let off = Math.round(frac * textLen);
      if (paragraphStarts && paragraphStarts.length) {
        const pxPerChar = r.height / textLen;
        let best = off;
        let bestDist = Infinity;
        for (const p of paragraphStarts) {
          const dist = Math.abs(p - off) * pxPerChar;
          if (dist < bestDist) {
            bestDist = dist;
            best = p;
          }
        }
        if (bestDist <= SNAP_PX) off = best;
      }
      return off;
    },
    [textLen, paragraphStarts],
  );

  useEffect(() => {
    if (!dragRef.current) return;
    function onMove(e: PointerEvent): void {
      const drag = dragRef.current;
      if (!drag) return;
      const off = offsetFromClientY(e.clientY);
      const sec = useSectionStore.getState().sections.find((s) => s.id === drag.id);
      if (!sec) return;
      if (drag.edge === 'start' && off < sec.end) updateSection(drag.id, { start: off });
      else if (drag.edge === 'end' && off > sec.start) updateSection(drag.id, { end: off });
    }
    function onUp(): void {
      dragRef.current = null;
    }
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  });

  const startDrag = (id: string, edge: 'start' | 'end') => (e: React.PointerEvent) => {
    e.stopPropagation();
    e.preventDefault();
    dragRef.current = { id, edge };
    // Re-render to attach the move/up listeners via the effect.
    setSelected(id);
  };

  // ── Horizontal view-only overview ──
  if (mode === 'horizontal') {
    const laneH = 26;
    return (
      <div className="w-full">
        <div className="relative w-full" style={{ height: (maxDepth + 1) * laneH + 4 }}>
          {sections.map((s) => {
            const d = depthOf(s, byId);
            const left = `${(s.start / textLen) * 100}%`;
            const width = `${((s.end - s.start) / textLen) * 100}%`;
            return (
              <div
                key={s.id}
                title={`${s.type} · ${s.label}`}
                className="absolute rounded-sm text-[9px] text-black/70 overflow-hidden whitespace-nowrap px-1"
                style={{
                  left, width, top: d * laneH, height: laneH - 4,
                  background: colorOf(s.type), opacity: 0.85,
                }}
              >
                {s.label || s.type}
              </div>
            );
          })}
        </div>
        <div className="mt-1 text-[10px] text-[#6e6e73]">View only — switch to the vertical map to edit.</div>
      </div>
    );
  }

  // ── Vertical editable workbench ──
  return (
    <div className="flex gap-2 select-none" style={{ height: '52vh' }}>
      <div
        ref={ref}
        className="relative w-[170px] rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] overflow-hidden"
        onContextMenu={(e) => {
          e.preventDefault();
          setMenu({ x: e.clientX, y: e.clientY, offset: offsetFromClientY(e.clientY), sectionId: null });
        }}
        onClick={() => setMenu(null)}
      >
        {sections.map((s) => {
          const d = depthOf(s, byId);
          const top = `${(s.start / textLen) * 100}%`;
          const height = `${((s.end - s.start) / textLen) * 100}%`;
          const isSel = s.id === selectedId;
          return (
            <div
              key={s.id}
              onClick={(e) => {
                e.stopPropagation();
                setSelected(s.id);
                setMenu(null);
              }}
              onContextMenu={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setMenu({ x: e.clientX, y: e.clientY, offset: offsetFromClientY(e.clientY), sectionId: s.id });
              }}
              title={`${s.type} · ${s.label}`}
              className="absolute cursor-pointer overflow-hidden text-[9px] text-black/75 px-1"
              style={{
                top, height,
                left: 6 + d * 10,
                right: 4,
                background: colorOf(s.type),
                opacity: isSel ? 1 : 0.8,
                outline: isSel ? '2px solid #fff' : 'none',
                borderRadius: 3,
              }}
            >
              <span className="truncate block leading-tight">{s.label || s.type}</span>
              <div
                onPointerDown={startDrag(s.id, 'start')}
                className="absolute top-0 left-0 right-0 h-1.5 cursor-ns-resize bg-white/0 hover:bg-white/40"
              />
              <div
                onPointerDown={startDrag(s.id, 'end')}
                className="absolute bottom-0 left-0 right-0 h-1.5 cursor-ns-resize bg-white/0 hover:bg-white/40"
              />
            </div>
          );
        })}
      </div>

      {/* Mask gutter — dark where text will be excluded from analysis. */}
      <div className="relative w-3 rounded ring-1 ring-white/10 bg-[#101012] overflow-hidden" title="Masked (excluded) ranges">
        {masked.map(([a, b], i) => (
          <div
            key={i}
            className="absolute left-0 right-0 bg-[#3a3a3d]"
            style={{ top: `${(a / textLen) * 100}%`, height: `${((b - a) / textLen) * 100}%` }}
          />
        ))}
      </div>

      {/* Selected-section inspector. */}
      <SectionInspector />

      {menu && (
        <ContextMenu
          menu={menu}
          types={types.map((t) => ({ key: t.key, label: t.label, color: t.color }))}
          onAdd={(type) => {
            const span = Math.max(200, Math.round(textLen * 0.02));
            addSection(type, menu.offset, Math.min(textLen, menu.offset + span));
            setMenu(null);
          }}
          onChangeType={(type) => {
            if (menu.sectionId) updateSection(menu.sectionId, { type });
            setMenu(null);
          }}
          onDelete={() => {
            if (menu.sectionId) removeSection(menu.sectionId);
            setMenu(null);
          }}
          onClose={() => setMenu(null)}
        />
      )}
    </div>
  );
}

function SectionInspector(): ReactElement {
  const selectedId = useSectionStore((s) => s.selectedId);
  const sections = useSectionStore((s) => s.sections);
  const types = useSectionStore((s) => s.types);
  const maskByType = useSectionStore((s) => s.maskByType);
  const updateSection = useSectionStore((s) => s.updateSection);
  const removeSection = useSectionStore((s) => s.removeSection);

  const sec = sections.find((s) => s.id === selectedId);
  if (!sec) {
    return (
      <div className="flex-1 text-[#6e6e73] text-xs p-2">
        Select a block to edit its type and mask. Right-click the strip to add a section.
      </div>
    );
  }
  const typeMeta = types.find((t) => t.key === sec.type);
  const effMask = sec.masked ?? (maskByType[sec.type] ?? true);

  return (
    <div className="flex-1 text-xs text-[#d6d6d8] p-2 space-y-2 overflow-y-auto">
      <div className="text-[#8e8e93]">{sec.label || '(no heading)'}</div>
      <div className="flex flex-wrap gap-1">
        {types.map((t) => (
          <button
            key={t.key}
            onClick={() => updateSection(sec.id, { type: t.key })}
            className={`px-1.5 py-0.5 rounded text-[10px] ${
              t.key === sec.type ? 'text-black font-semibold' : 'text-[#b0b0b6] bg-white/5'
            }`}
            style={t.key === sec.type ? { background: t.color } : undefined}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="text-[#8e8e93]">
        {sec.start.toLocaleString()}–{sec.end.toLocaleString()} · {(sec.end - sec.start).toLocaleString()} chars
      </div>
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={effMask}
          onChange={(e) => updateSection(sec.id, { masked: e.target.checked })}
        />
        <span>Masked (excluded from analysis){typeMeta ? ` — ${typeMeta.label} default: ${typeMeta.default_mask ? 'masked' : 'analyzed'}` : ''}</span>
      </label>
      <button
        onClick={() => removeSection(sec.id)}
        className="text-[#ff453a] hover:underline"
      >
        Delete section
      </button>
    </div>
  );
}

function ContextMenu({
  menu,
  types,
  onAdd,
  onChangeType,
  onDelete,
  onClose,
}: {
  menu: Menu;
  types: Array<{ key: string; label: string; color: string }>;
  onAdd: (type: string) => void;
  onChangeType: (type: string) => void;
  onDelete: () => void;
  onClose: () => void;
}): ReactElement {
  const [sub, setSub] = useState<'add' | 'type' | null>(menu.sectionId ? null : 'add');
  useEffect(() => {
    const h = (): void => onClose();
    window.addEventListener('click', h);
    return () => window.removeEventListener('click', h);
  }, [onClose]);

  return (
    <div
      className="fixed z-[9999] min-w-[160px] rounded-lg bg-[#2a2a2c] ring-1 ring-white/15 shadow-xl py-1 text-xs text-[#e8e8ea]"
      style={{ left: menu.x, top: menu.y }}
      onClick={(e) => e.stopPropagation()}
    >
      {!sub && menu.sectionId && (
        <>
          <button className="w-full text-left px-3 py-1.5 hover:bg-white/10" onClick={() => setSub('add')}>
            Add section here…
          </button>
          <button className="w-full text-left px-3 py-1.5 hover:bg-white/10" onClick={() => setSub('type')}>
            Change type…
          </button>
          <button className="w-full text-left px-3 py-1.5 hover:bg-white/10 text-[#ff453a]" onClick={onDelete}>
            Delete section
          </button>
        </>
      )}
      {sub && (
        <div className="max-h-[260px] overflow-y-auto">
          <div className="px-3 py-1 text-[10px] uppercase text-[#8a8a90]">
            {sub === 'add' ? 'Add section' : 'Change type'}
          </div>
          {types.map((t) => (
            <button
              key={t.key}
              className="w-full flex items-center gap-2 text-left px-3 py-1.5 hover:bg-white/10"
              onClick={() => (sub === 'add' ? onAdd(t.key) : onChangeType(t.key))}
            >
              <span className="w-2.5 h-2.5 rounded-sm" style={{ background: t.color }} />
              {t.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
