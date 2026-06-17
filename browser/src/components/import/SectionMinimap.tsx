/**
 * Bird's-eye section map (Step 3).
 *  - mode="vertical": the editable workbench — colored blocks down a (zoomable, scrolling)
 *    strip, draggable top/bottom boundary handles (snap to paragraph starts), click to
 *    select, right-click to add a section. A right-hand panel shows the selected section's
 *    raw text with iOS-style start/end handles you drag to adjust the boundary precisely.
 *  - mode="horizontal": a zoomable overview, one lane per nesting depth, with sections
 *    staggered into sub-rows (UCSC-genome-browser style) so labels stay readable.
 * A row of per-type toggles shows/hides each masking layer in both views.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type ReactElement } from 'react';
import { useSectionStore } from '../../stores/sectionStore';
import { computeMaskedIntervals, type LayoutSection } from '../../utils/sectionMasking';
import { MaskContextMenu } from './maskMenu';
import { offsetFromPoint } from './textOffset';

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
  text,
}: {
  mode: 'vertical' | 'horizontal';
  paragraphStarts?: number[];
  text?: string;
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
  // Separate from `menu` (the strip's add/change/delete menu): the rich mask-edit
  // menu opened by right-clicking the selected section's text in the right panel.
  const [textMenu, setTextMenu] = useState<{ x: number; y: number; off: number } | null>(null);
  const [zoom, setZoom] = useState(1);
  const [hidden, setHidden] = useState<Set<string>>(() => new Set());
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

  // Types actually present, in vocabulary order — drives the show/hide legend.
  const usedTypes = useMemo(() => {
    const present = new Set(sections.map((s) => s.type));
    return types.filter((t) => present.has(t.key));
  }, [types, sections]);

  const visibleSections = useMemo(
    () => sections.filter((s) => !hidden.has(s.type)),
    [sections, hidden],
  );
  const selected = useMemo(() => sections.find((s) => s.id === selectedId) ?? null, [sections, selectedId]);

  const toggleType = useCallback((key: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

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

  const offsetRef = useRef(offsetFromClientY);
  offsetRef.current = offsetFromClientY;

  useEffect(() => {
    let raf = 0;
    let pendingY: number | null = null;
    // rAF-coalesced minimap boundary drag — one update per frame (#20).
    function flush(): void {
      raf = 0;
      const drag = dragRef.current;
      if (!drag || pendingY == null) return;
      const off = offsetRef.current(pendingY);
      pendingY = null;
      const sec = useSectionStore.getState().sections.find((s) => s.id === drag.id);
      if (!sec) return;
      if (drag.edge === 'start' && off < sec.end) updateSection(drag.id, { start: off });
      else if (drag.edge === 'end' && off > sec.start) updateSection(drag.id, { end: off });
    }
    function onMove(e: PointerEvent): void {
      if (!dragRef.current) return;
      pendingY = e.clientY;
      if (!raf) raf = requestAnimationFrame(flush);
    }
    function onUp(): void {
      dragRef.current = null;
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
    }
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [updateSection]);

  const startDrag = (id: string, edge: 'start' | 'end') => (e: React.PointerEvent) => {
    e.stopPropagation();
    e.preventDefault();
    dragRef.current = { id, edge };
    setSelected(id);
  };

  const LayerToggles = (
    <div className="flex flex-wrap gap-1.5">
      {usedTypes.map((t) => {
        const off = hidden.has(t.key);
        return (
          <button
            key={t.key}
            type="button"
            onClick={() => toggleType(t.key)}
            title={off ? `Show ${t.label}` : `Hide ${t.label}`}
            className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] ring-1 transition-colors ${
              off ? 'ring-white/10 text-[#6e6e73]' : 'ring-white/25 text-[#e8e8ea] bg-white/5'
            }`}
          >
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: t.color, opacity: off ? 0.3 : 1 }} />
            {t.label}
          </button>
        );
      })}
    </div>
  );

  // Log-scale slider: 1×–1000×. A linear range would crush the useful low end into a
  // sliver, so the slider carries log10(zoom) and a book with thousands of sections can
  // still be spread out enough to grab individual boundaries.
  const ZoomControl = (
    <div className="flex items-center gap-1.5 shrink-0">
      <span className="text-[10px] text-[#8a8a90]">Zoom</span>
      <input
        type="range"
        min={0}
        max={3}
        step={0.01}
        value={Math.log10(zoom)}
        onChange={(e) => setZoom(10 ** Number(e.target.value))}
        className="w-28 accent-[#0a84ff]"
        aria-label="Zoom"
      />
      <span className="text-[10px] text-[#8a8a90] tabular-nums w-12">
        {zoom >= 10 ? Math.round(zoom) : zoom.toFixed(1)}×
      </span>
    </div>
  );

  // ── Horizontal staggered overview ──
  if (mode === 'horizontal') {
    const ROW_H = 24;
    const STAGGER = 2;
    const GAP = 6;
    const byDepth = new Map<number, LayoutSection[]>();
    for (const s of visibleSections) {
      const d = depthOf(s, byId);
      (byDepth.get(d) ?? byDepth.set(d, []).get(d)!).push(s);
    }
    const items: { s: LayoutSection; top: number; leftPct: number; widthPct: number }[] = [];
    let laneTop = 0;
    for (let d = 0; d <= maxDepth; d++) {
      const lane = (byDepth.get(d) ?? []).slice().sort((a, b) => a.start - b.start);
      lane.forEach((s, i) => {
        items.push({
          s,
          top: laneTop + (i % STAGGER) * ROW_H,
          leftPct: (s.start / textLen) * 100,
          widthPct: ((s.end - s.start) / textLen) * 100,
        });
      });
      laneTop += STAGGER * ROW_H + GAP;
    }
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">{LayerToggles}{ZoomControl}</div>
        <div className="overflow-auto rounded-lg ring-1 ring-white/10 bg-[#1c1c1e]" style={{ height: '56vh' }}>
          <div className="relative" style={{ width: `${100 * zoom}%`, minWidth: '100%', height: laneTop + 4 }}>
            {items.map(({ s, top, leftPct, widthPct }) => {
              const isSel = s.id === selectedId;
              return (
                <div
                  key={s.id}
                  onClick={() => setSelected(s.id)}
                  title={`${s.type} · ${s.label}`}
                  className="absolute rounded-sm text-[10px] text-black/80 overflow-hidden whitespace-nowrap px-1 cursor-pointer leading-[20px]"
                  style={{
                    left: `${leftPct}%`,
                    width: `max(3px, ${widthPct}%)`,
                    top,
                    height: ROW_H - 3,
                    background: colorOf(s.type),
                    opacity: isSel ? 1 : 0.85,
                    outline: isSel ? '2px solid #fff' : 'none',
                  }}
                >
                  {s.label || s.type}
                </div>
              );
            })}
          </div>
        </div>
        <div className="text-[10px] text-[#6e6e73]">
          Overview — click a block to select it (edit in the vertical map). Zoom to spread crowded sections.
        </div>
      </div>
    );
  }

  // ── Vertical editable workbench ──
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">{LayerToggles}{ZoomControl}</div>
      <div className="flex gap-3 select-none" style={{ height: '60vh' }}>
        {/* Zoomable, scrolling strip + mask gutter */}
        <div className="overflow-y-auto rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] shrink-0" style={{ width: 200 }}>
          <div className="flex gap-1" style={{ height: `${100 * zoom}%`, minHeight: '100%' }}>
            <div
              ref={ref}
              className="relative flex-1"
              onContextMenu={(e) => {
                e.preventDefault();
                setMenu({ x: e.clientX, y: e.clientY, offset: offsetFromClientY(e.clientY), sectionId: null });
              }}
              onClick={() => setMenu(null)}
            >
              {visibleSections.map((s) => {
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
                      top,
                      height,
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
            <div className="relative w-3 bg-[#101012]" title="Masked (excluded) ranges">
              {masked.map(([a, b], i) => (
                <div
                  key={i}
                  className="absolute left-0 right-0 bg-[#3a3a3d]"
                  style={{ top: `${(a / textLen) * 100}%`, height: `${((b - a) / textLen) * 100}%` }}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Right panel: inspector controls + raw-text boundary editor */}
        <div className="flex-1 min-w-0 flex flex-col gap-2">
          {selected ? (
            <>
              <SectionInspector />
              {text ? (
                <BoundaryTextEditor
                  text={text}
                  section={selected}
                  onChange={(patch) => updateSection(selected.id, patch)}
                  onContext={(off, x, y) => setTextMenu({ off, x, y })}
                />
              ) : (
                <div className="flex-1 rounded-lg ring-1 ring-white/10 bg-[#161618] p-3 text-[#6e6e73] text-xs">
                  Text preview unavailable.
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-center text-[#6e6e73] text-xs px-6 rounded-lg ring-1 ring-white/10 bg-[#161618]">
              Select a section (click a block) to view its text and drag the start/end handles to
              adjust its boundary. Right-click the strip to add a section.
            </div>
          )}
        </div>
      </div>

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

      {textMenu && (
        <MaskContextMenu
          x={textMenu.x}
          y={textMenu.y}
          off={textMenu.off}
          sections={sections}
          types={types}
          selectedId={selectedId}
          onClose={() => setTextMenu(null)}
        />
      )}
    </div>
  );
}

/**
 * Raw-text boundary editor. Shows the selected section's text (with context) and
 * places iOS-selection-style circular handles at the start and end. Dragging a
 * handle over a word sets that boundary to the word's edge (word-granular). For
 * long sections only the two boundary neighborhoods are rendered, with a gap marker.
 */
function BoundaryTextEditor({
  text,
  section,
  onChange,
  onContext,
}: {
  text: string;
  section: LayoutSection;
  onChange: (patch: Partial<LayoutSection>) => void;
  onContext: (off: number, x: number, y: number) => void;
}): ReactElement {
  const dragRef = useRef<'start' | 'end' | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const len = text.length;
  const CTX = 600;

  // When a different section is selected, scroll its start boundary into view so
  // the handle is immediately visible (not buried at the top of the context).
  useEffect(() => {
    const c = containerRef.current;
    if (!c) return;
    const h = c.querySelector('[data-handle="start"]') as HTMLElement | null;
    if (h) {
      const cr = c.getBoundingClientRect();
      const hr = h.getBoundingClientRect();
      c.scrollTop += hr.top - cr.top - c.clientHeight / 3;
    }
  }, [section.id]);
  const longSpan = section.end - section.start > 2 * CTX + 400;
  const regions: Array<[number, number]> = longSpan
    ? [
        [Math.max(0, section.start - CTX), Math.min(len, section.start + CTX)],
        [Math.max(0, section.end - CTX), Math.min(len, section.end + CTX)],
      ]
    : [[Math.max(0, section.start - CTX), Math.min(len, section.end + CTX)]];

  useEffect(() => {
    let raf = 0;
    let pending: { x: number; y: number } | null = null;

    function hit(x: number, y: number): { off: number; end: number } | null {
      const el = document.elementFromPoint(x, y);
      const tok = el && (el as HTMLElement).closest('[data-off]');
      if (!tok) return null;
      const t = tok as HTMLElement;
      return { off: Number(t.dataset.off), end: Number(t.dataset.end) };
    }
    // Coalesce pointer moves to one boundary update per animation frame, and read
    // the live section so the listeners stay attached for the whole drag (#20).
    function flush(): void {
      raf = 0;
      const edge = dragRef.current;
      if (!edge || !pending) return;
      const h = hit(pending.x, pending.y);
      pending = null;
      if (!h) return;
      const sec = useSectionStore.getState().sections.find((s) => s.id === section.id);
      if (!sec) return;
      if (edge === 'start' && h.off < sec.end) onChangeRef.current({ start: h.off });
      else if (edge === 'end' && h.end > sec.start) onChangeRef.current({ end: h.end });
    }
    function onMove(e: PointerEvent): void {
      if (!dragRef.current) return;
      pending = { x: e.clientX, y: e.clientY };
      if (!raf) raf = requestAnimationFrame(flush);
    }
    function onUp(): void {
      dragRef.current = null;
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
    }
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [section.id]);

  const startDrag = (edge: 'start' | 'end') => (e: React.PointerEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragRef.current = edge;
  };

  function renderRegion([from, to]: [number, number], key: number): ReactElement {
    const slice = text.slice(from, to);
    const re = /(\s+|\S+)/g;
    const nodes: ReactElement[] = [];
    let m: RegExpExecArray | null;
    let i = 0;
    let startPlaced = false;
    let endPlaced = false;
    const startHere = section.start >= from && section.start <= to;
    const endHere = section.end >= from && section.end <= to;
    while ((m = re.exec(slice)) !== null) {
      const off = from + m.index;
      const end = off + m[0].length;
      if (startHere && !startPlaced && off >= section.start) {
        nodes.push(<Handle key={`sh${key}`} edge="start" onDown={startDrag('start')} />);
        startPlaced = true;
      }
      const inSec = off >= section.start && off < section.end;
      nodes.push(
        <span
          key={`t${key}-${i}`}
          data-off={off}
          data-end={end}
          className={inSec ? 'bg-[#0a84ff]/30 text-[#f0f4ff]' : 'text-[#76767c]'}
        >
          {m[0]}
        </span>,
      );
      if (endHere && !endPlaced && end >= section.end) {
        nodes.push(<Handle key={`eh${key}`} edge="end" onDown={startDrag('end')} />);
        endPlaced = true;
      }
      i += 1;
    }
    // Section ends at/after the last token (e.g. end of text) → place the handle now.
    if (endHere && !endPlaced) {
      nodes.push(<Handle key={`eh${key}`} edge="end" onDown={startDrag('end')} />);
    }
    return (
      <div key={`r${key}`}>
        {key > 0 && (
          <div className="my-2 text-center text-[10px] text-[#6e6e73]">
            ··· {(section.end - section.start).toLocaleString()} chars in section ···
          </div>
        )}
        {nodes}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      data-reader
      onContextMenu={(e) => {
        // Two-finger tap / Control-click on the trackpad both arrive here as a
        // contextmenu event — suppress Chrome's native menu and open the mask editor.
        e.preventDefault();
        const off = offsetFromPoint(e.clientX, e.clientY, e.target);
        if (off != null) onContext(off, e.clientX, e.clientY);
      }}
      className="flex-1 min-h-0 overflow-y-auto rounded-lg ring-1 ring-white/10 bg-[#161618] p-3 text-[13px] leading-[1.9] font-[var(--font-serif)] whitespace-pre-wrap break-words select-none"
    >
      {regions.map((r, i) => renderRegion(r, i))}
    </div>
  );
}

function Handle({ edge, onDown }: { edge: 'start' | 'end'; onDown: (e: React.PointerEvent) => void }): ReactElement {
  return (
    <span
      onPointerDown={onDown}
      data-handle={edge}
      role="slider"
      aria-label={`Drag ${edge} boundary`}
      title={`Drag to move the ${edge} of this section`}
      className="relative inline-flex align-middle cursor-grab active:cursor-grabbing"
      style={{ width: 12, height: '1em' }}
    >
      <span className="absolute left-1/2 -translate-x-1/2 top-[-0.25em] bottom-[-0.25em] w-[2px] bg-[#0a84ff]" />
      <span
        className="absolute left-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full bg-[#0a84ff] ring-2 ring-[#161618]"
        style={edge === 'start' ? { top: '-0.95em' } : { bottom: '-0.95em' }}
      />
    </span>
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
      <div className="shrink-0 text-[#6e6e73] text-xs p-2">
        Select a block to edit its type and mask. Right-click the strip to add a section.
      </div>
    );
  }
  const typeMeta = types.find((t) => t.key === sec.type);
  const effMask = sec.masked ?? (maskByType[sec.type] ?? true);

  return (
    <div className="shrink-0 rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] text-xs text-[#d6d6d8] p-2 space-y-2">
      <div className="text-[#8e8e93]">{sec.label || '(no heading)'}</div>
      {(sec.metadata?.number || sec.metadata?.name) && (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-[#8e8e93]">
          {sec.metadata?.number && (
            <span>No. <span className="text-[#d6d6d8]">{sec.metadata.number}</span></span>
          )}
          {sec.metadata?.name && (
            <span>Title: <span className="text-[#d6d6d8]">{sec.metadata.name}</span></span>
          )}
        </div>
      )}
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
      <div className="flex items-center justify-between gap-2">
        <span className="text-[#8e8e93]">
          {sec.start.toLocaleString()}–{sec.end.toLocaleString()} · {(sec.end - sec.start).toLocaleString()} chars
        </span>
        <button onClick={() => removeSection(sec.id)} className="text-[#ff453a] hover:underline">
          Delete
        </button>
      </div>
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={effMask}
          onChange={(e) => updateSection(sec.id, { masked: e.target.checked })}
        />
        <span>
          Masked (excluded from analysis){typeMeta ? ` — ${typeMeta.label} default: ${typeMeta.default_mask ? 'masked' : 'analyzed'}` : ''}
        </span>
      </label>
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
