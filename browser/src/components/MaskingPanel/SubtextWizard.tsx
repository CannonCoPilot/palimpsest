/**
 * Two-stage subtext-derivation wizard. Stage 1 picks the extraction type-layer(s) whose
 * element spans form the subtext; Stage 2 deselects individual elements (grouped by their
 * container, e.g. book — so an appendix branch toggles as a unit); Stage 3 names it, previews
 * coverage, and POSTs to /derive. The kept text + all overlapping parent layers are remapped
 * onto the new child project server-side (palimpsest.derive).
 */

import { useMemo, useState, type ReactElement } from 'react';
import { useViewStore } from '../../stores/viewStore';
import { useSectionStore } from '../../stores/sectionStore';
import { useProjectStore } from '../../stores/projectStore';
import type { LayoutSection } from '../../utils/sectionMasking';

interface KeptStats {
  count: number;
  chars: number;
  spans: Array<[number, number]>;
}

/** Merge the (non-excluded) extraction-layer spans; mirrors core compute_kept_spans. */
function keptStats(
  sections: LayoutSection[],
  extractionTypes: Set<string>,
  excludedIds: Set<string>,
): KeptStats {
  const raw = sections
    .filter((s) => extractionTypes.has(s.type) && !excludedIds.has(s.id) && s.start < s.end)
    .map((s): [number, number] => [s.start, s.end])
    .sort((a, b) => a[0] - b[0]);
  const merged: Array<[number, number]> = [];
  for (const [s, e] of raw) {
    const last = merged[merged.length - 1];
    if (last && s <= last[1]) last[1] = Math.max(last[1], e);
    else merged.push([s, e]);
  }
  return { count: raw.length, chars: merged.reduce((n, [s, e]) => n + (e - s), 0), spans: merged };
}

function elementLabel(s: LayoutSection): string {
  if (s.label) return s.label;
  const name = s.metadata?.name;
  const num = s.metadata?.number;
  if (name && num) return `${name} ${num}`;
  if (name) return name;
  return num ? `${s.type} ${num}` : s.type;
}

export default function SubtextWizard(): ReactElement | null {
  const open = useViewStore((s) => s.subtextWizardOpen);
  const close = useViewStore((s) => s.setSubtextWizardOpen);

  const parentId = useProjectStore((s) => s.activeProjectId);
  const parentTitle = useProjectStore((s) => s.projects[s.activeProjectId ?? '']?.metadata?.title ?? '');
  const sections = useSectionStore((s) => s.sections);
  const types = useSectionStore((s) => s.types);
  const textLen = useSectionStore((s) => s.textLen);

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [extraction, setExtraction] = useState<Set<string>>(new Set());
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ project_id: string; char_count: number; element_count: number; verse_count: number } | null>(null);

  // Present mask-types (those with at least one element), with label/color/count.
  const present = useMemo(() => {
    const counts = new Map<string, number>();
    for (const s of sections) counts.set(s.type, (counts.get(s.type) ?? 0) + 1);
    const meta = new Map(types.map((t) => [t.key, t]));
    return [...counts.entries()]
      .map(([type, count]) => ({ type, count, label: meta.get(type)?.label ?? type, color: meta.get(type)?.color ?? '#8e8e93' }))
      .sort((a, b) => b.count - a.count);
  }, [sections, types]);

  // Extraction elements grouped by their container (parent_id) for Stage 2.
  const groups = useMemo(() => {
    const byId = new Map(sections.map((s) => [s.id, s]));
    const els = sections
      .filter((s) => extraction.has(s.type))
      .sort((a, b) => a.start - b.start);
    const out = new Map<string, { label: string; els: LayoutSection[] }>();
    for (const el of els) {
      const key = el.parent_id ?? '__none__';
      if (!out.has(key)) {
        const parent = el.parent_id ? byId.get(el.parent_id) : null;
        out.set(key, { label: parent ? elementLabel(parent) : 'Ungrouped', els: [] });
      }
      out.get(key)!.els.push(el);
    }
    return [...out.entries()].map(([key, v]) => ({ key, ...v }));
  }, [sections, extraction]);

  const stats = useMemo(() => keptStats(sections, extraction, excluded), [sections, extraction, excluded]);

  if (!open) return null;

  const reset = (): void => {
    setStep(1); setExtraction(new Set()); setExcluded(new Set()); setTitle('');
    setBusy(false); setError(null); setResult(null); setCollapsed(new Set());
  };
  const dismiss = (): void => { reset(); close(false); };

  const toggleExtraction = (t: string): void =>
    setExtraction((prev) => { const n = new Set(prev); n.has(t) ? n.delete(t) : n.add(t); return n; });
  const toggleExcluded = (id: string): void =>
    setExcluded((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const toggleGroup = (els: LayoutSection[], drop: boolean): void =>
    setExcluded((prev) => { const n = new Set(prev); for (const e of els) drop ? n.add(e.id) : n.delete(e.id); return n; });
  const toggleCollapse = (key: string): void =>
    setCollapsed((prev) => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n; });

  const generate = async (): Promise<void> => {
    if (!parentId) return;
    setBusy(true); setError(null);
    try {
      const res = await fetch(`/api/projects/${parentId}/derive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          extraction_types: [...extraction],
          excluded_ids: [...excluded],
          title: title.trim(),
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.detail ?? `Derivation failed (${res.status})`);
        setBusy(false);
        return;
      }
      setResult(await res.json());
      setBusy(false);
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  };

  const openChild = (): void => {
    if (!result) return;
    const pid = result.project_id;
    useProjectStore.setState((s) => { const projects = { ...s.projects }; delete projects[pid]; return { projects }; });
    useProjectStore.getState().loadProject('', pid);
    dismiss();
  };

  const pct = textLen > 0 ? Math.round((stats.chars / textLen) * 100) : 0;
  const btn = 'px-3 py-1.5 rounded text-[0.85em] cursor-pointer';
  const btnPrimary = `${btn} bg-[var(--color-accent,#1a73e8)] text-white hover:opacity-90 disabled:opacity-40`;
  const btnGhost = `${btn} border border-[var(--color-border)] hover:bg-[var(--color-bg-muted)]`;

  return (
    <div className="fixed inset-0 z-[var(--z-overlay)] flex items-center justify-center bg-black/40 font-[var(--font-sans)]">
      <div className="w-[640px] max-h-[85vh] flex flex-col bg-[var(--color-bg)] rounded-lg shadow-[0_16px_48px_rgba(0,0,0,0.4)] overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[var(--color-border)]">
          <strong className="text-[0.95em]">Derive subtext</strong>
          <span className="text-[0.78em] text-[var(--color-text-muted)] truncate">from {parentTitle}</span>
          <button onClick={dismiss} className="ml-auto px-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer" aria-label="Close">✕</button>
        </div>

        <div className="flex items-center gap-1 px-4 py-1.5 text-[0.72em] text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
          {['1 · Extract layers', '2 · Refine elements', '3 · Generate'].map((s, i) => (
            <span key={s} className={step === i + 1 ? 'text-[var(--color-text)] font-semibold' : ''}>
              {s}{i < 2 ? '  →  ' : ''}
            </span>
          ))}
        </div>

        {error && <div className="px-4 py-2 text-[0.8em] text-[#ff453a]">{error}</div>}

        <div className="flex-1 overflow-y-auto p-4">
          {result ? (
            <div className="text-[0.85em] space-y-2">
              <p className="text-[var(--color-success,#137333)] font-semibold">Subtext created.</p>
              <p>{result.char_count.toLocaleString()} characters · {result.element_count.toLocaleString()} elements · {result.verse_count.toLocaleString()} verses.</p>
              <p className="text-[var(--color-text-muted)]">It has been added to a collection with its parent.</p>
            </div>
          ) : step === 1 ? (
            <div>
              <p className="text-[0.8em] text-[var(--color-text-muted)] mb-2">
                Choose the layer(s) whose text becomes the subtext. Overlapping containers (book,
                volume) and the verse layer are carried automatically; other layers are dropped.
              </p>
              {present.map((p) => (
                <label key={p.type} className="flex items-center gap-2 px-2 py-1.5 text-[0.85em] hover:bg-[var(--color-bg-muted)] rounded cursor-pointer">
                  <input type="checkbox" checked={extraction.has(p.type)} onChange={() => toggleExtraction(p.type)} />
                  <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: p.color }} />
                  <span className="flex-1">{p.label}</span>
                  <span className="text-[0.85em] text-[var(--color-text-muted)] tabular-nums">{p.count}</span>
                </label>
              ))}
            </div>
          ) : step === 2 ? (
            <div>
              <p className="text-[0.8em] text-[var(--color-text-muted)] mb-2">
                Deselect any elements (or whole containers) to exclude from the subtext.
                {' '}{stats.count} of {sections.filter((s) => extraction.has(s.type)).length} kept.
              </p>
              {groups.map((g) => {
                const allDropped = g.els.every((e) => excluded.has(e.id));
                const isCollapsed = collapsed.has(g.key);
                return (
                  <div key={g.key} className="mb-1 border border-[var(--color-border-subtle,#eee)] rounded">
                    <div className="flex items-center gap-2 px-2 py-1.5 text-[0.82em] bg-[var(--color-bg-subtle)]">
                      <input type="checkbox" checked={!allDropped} ref={(el) => { if (el) el.indeterminate = !allDropped && g.els.some((e) => excluded.has(e.id)); }} onChange={() => toggleGroup(g.els, !allDropped)} />
                      <button onClick={() => toggleCollapse(g.key)} className="flex-1 text-left truncate cursor-pointer">{g.label}</button>
                      <span className="text-[0.85em] text-[var(--color-text-muted)] tabular-nums">{g.els.length}</span>
                      <button onClick={() => toggleCollapse(g.key)} className="text-[var(--color-text-muted)] cursor-pointer">{isCollapsed ? '▸' : '▾'}</button>
                    </div>
                    {!isCollapsed && (
                      <div className="max-h-[160px] overflow-y-auto">
                        {g.els.map((e) => (
                          <label key={e.id} className="flex items-center gap-2 px-2 py-1 pl-6 text-[0.8em] hover:bg-[var(--color-bg-muted)] cursor-pointer">
                            <input type="checkbox" checked={!excluded.has(e.id)} onChange={() => toggleExcluded(e.id)} />
                            <span className="truncate">{elementLabel(e)}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="space-y-3">
              <label className="block text-[0.85em]">
                <span className="text-[var(--color-text-muted)]">Title</span>
                <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={`${parentTitle} — core`}
                  className="mt-1 w-full px-2 py-1.5 border border-[var(--color-border)] rounded bg-[var(--color-bg)] focus:border-[var(--color-border-focus)] focus:outline-none" />
              </label>
              <div className="text-[0.82em] space-y-1">
                <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Kept elements</span><span className="tabular-nums">{stats.count.toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Characters</span><span className="tabular-nums">{stats.chars.toLocaleString()} ({pct}% of parent)</span></div>
              </div>
              <div className="relative h-3 w-full rounded bg-[var(--color-bg-muted)] overflow-hidden">
                {stats.spans.map(([s, e], i) => (
                  <div key={i} className="absolute top-0 bottom-0 bg-[var(--color-accent,#1a73e8)]"
                    style={{ left: `${(s / Math.max(1, textLen)) * 100}%`, width: `${((e - s) / Math.max(1, textLen)) * 100}%` }} />
                ))}
              </div>
              <p className="text-[0.72em] text-[var(--color-text-muted)]">Kept regions (blue) over the parent text. Generation can take up to a minute for large texts.</p>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 px-4 py-2.5 border-t border-[var(--color-border)]">
          {result ? (
            <>
              <button onClick={dismiss} className={btnGhost}>Close</button>
              <button onClick={openChild} className={`${btnPrimary} ml-auto`}>Open subtext</button>
            </>
          ) : (
            <>
              {step > 1 && <button onClick={() => setStep((step - 1) as 1 | 2)} disabled={busy} className={btnGhost}>Back</button>}
              <button onClick={dismiss} disabled={busy} className={`${btnGhost} ${step > 1 ? '' : ''}`}>Cancel</button>
              {step === 1 && <button onClick={() => setStep(2)} disabled={extraction.size === 0} className={`${btnPrimary} ml-auto`}>Next: refine</button>}
              {step === 2 && <button onClick={() => setStep(3)} disabled={stats.count === 0} className={`${btnPrimary} ml-auto`}>Next: generate</button>}
              {step === 3 && <button onClick={generate} disabled={busy || stats.count === 0} className={`${btnPrimary} ml-auto`}>{busy ? 'Generating…' : 'Generate subtext'}</button>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
