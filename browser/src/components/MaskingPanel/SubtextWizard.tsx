/**
 * Two-stage subtext-derivation wizard. Stage 1 picks the extraction type-layer(s) whose
 * element spans form the subtext; Stage 2 deselects individual elements (grouped by their
 * container, e.g. book — so an appendix branch toggles as a unit); Stage 3 names it, previews
 * coverage, and POSTs to /derive. The kept text + all overlapping parent layers are remapped
 * onto the new child project server-side (palimpsest.derive).
 */

import { useEffect, useMemo, useState, type ReactElement } from 'react';
import { useViewStore } from '../../stores/viewStore';
import { useSectionStore } from '../../stores/sectionStore';
import { useProjectStore } from '../../stores/projectStore';
import type { LayoutSection } from '../../utils/sectionMasking';

interface KeptStats {
  count: number;
  chars: number;
  spans: Array<[number, number]>;
}

/** Structural container types offered as optional extraction scopes (e.g. "only the Appendix"). */
const CONTAINER_TYPES = new Set(['volume', 'part', 'book', 'appendix']);

/** True when an element lies fully within at least one selected container span (empty = no scope). */
function inScope(s: LayoutSection, scopeSpans: Array<[number, number]>): boolean {
  return scopeSpans.length === 0 || scopeSpans.some(([cs, ce]) => cs <= s.start && s.end <= ce);
}

/** Merge the (non-excluded, in-scope) extraction-layer spans; mirrors core compute_kept_spans. */
function keptStats(
  sections: LayoutSection[],
  extractionTypes: Set<string>,
  excludedIds: Set<string>,
  scopeSpans: Array<[number, number]>,
): KeptStats {
  const raw = sections
    .filter((s) => extractionTypes.has(s.type) && !excludedIds.has(s.id) && s.start < s.end && inScope(s, scopeSpans))
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

type DeriveResult = { project_id: string; char_count: number; element_count: number; verse_count: number };
type DeriveEvent =
  | { type: 'progress'; phase: string; message: string; pct: number }
  | ({ type: 'done' } & DeriveResult & { collection_id?: string })
  | { type: 'error'; detail: string; status?: number };

// Consume the Server-Sent Events from /derive/stream. EventSource is GET-only, so we read the
// fetch body stream and split on the SSE record separator (mirrors the streamed import consumer).
async function streamDerive(parentId: string, body: unknown, onEvent: (e: DeriveEvent) => void): Promise<void> {
  const res = await fetch(`/api/projects/${parentId}/derive/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    onEvent({ type: 'error', detail: (err as { detail?: string }).detail || 'Derivation failed', status: res.status });
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buf.indexOf('\n\n')) >= 0) {
      const record = buf.slice(0, sep);
      buf = buf.slice(sep + 2);
      const dataLine = record.split('\n').find((l) => l.startsWith('data:'));
      if (dataLine) onEvent(JSON.parse(dataLine.slice(5).trim()) as DeriveEvent);
    }
  }
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
  const [scope, setScope] = useState<Set<string>>(new Set());
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [title, setTitle] = useState('');
  const [collectionId, setCollectionId] = useState('');  // '' = auto-create a {parent}+subtexts collection
  const [collections, setCollections] = useState<Array<{ id: string; label: string }>>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ pct: number; message: string } | null>(null);
  const [result, setResult] = useState<DeriveResult | null>(null);

  // Load existing collections so the subtext can be routed into a chosen one (else auto).
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    void fetch('/api/collections')
      .then((r) => (r.ok ? r.json() : []))
      .then((cols) => { if (!cancelled) setCollections(Array.isArray(cols) ? cols : []); })
      .catch(() => { /* non-fatal: fall back to auto-collection */ });
    return () => { cancelled = true; };
  }, [open]);

  // Present mask-types (those with at least one element), with label/color/count.
  const present = useMemo(() => {
    const counts = new Map<string, number>();
    for (const s of sections) counts.set(s.type, (counts.get(s.type) ?? 0) + 1);
    const meta = new Map(types.map((t) => [t.key, t]));
    return [...counts.entries()]
      .map(([type, count]) => ({ type, count, label: meta.get(type)?.label ?? type, color: meta.get(type)?.color ?? '#8e8e93' }))
      .sort((a, b) => b.count - a.count);
  }, [sections, types]);

  // Container sections offered as optional extraction scopes (appendix, book, volume, part).
  const containers = useMemo(
    () => sections
      .filter((s) => CONTAINER_TYPES.has(s.type) && s.start < s.end)
      .sort((a, b) => a.start - b.start),
    [sections],
  );
  const scopeSpans = useMemo(
    (): Array<[number, number]> => containers.filter((c) => scope.has(c.id)).map((c) => [c.start, c.end]),
    [containers, scope],
  );

  // Extraction elements (within scope) grouped by their container (parent_id) for Stage 2.
  const groups = useMemo(() => {
    const byId = new Map(sections.map((s) => [s.id, s]));
    const els = sections
      .filter((s) => extraction.has(s.type) && inScope(s, scopeSpans))
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
  }, [sections, extraction, scopeSpans]);

  const stats = useMemo(() => keptStats(sections, extraction, excluded, scopeSpans), [sections, extraction, excluded, scopeSpans]);

  if (!open) return null;

  const reset = (): void => {
    setStep(1); setExtraction(new Set()); setScope(new Set()); setExcluded(new Set()); setTitle(''); setCollectionId('');
    setBusy(false); setError(null); setProgress(null); setResult(null); setCollapsed(new Set());
  };
  const dismiss = (): void => { reset(); close(false); };

  const toggleExtraction = (t: string): void =>
    setExtraction((prev) => { const n = new Set(prev); n.has(t) ? n.delete(t) : n.add(t); return n; });
  const toggleScope = (id: string): void =>
    setScope((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const toggleExcluded = (id: string): void =>
    setExcluded((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const toggleGroup = (els: LayoutSection[], drop: boolean): void =>
    setExcluded((prev) => { const n = new Set(prev); for (const e of els) drop ? n.add(e.id) : n.delete(e.id); return n; });
  const toggleCollapse = (key: string): void =>
    setCollapsed((prev) => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n; });

  const generate = async (): Promise<void> => {
    if (!parentId) return;
    setBusy(true); setError(null); setProgress({ pct: 0, message: 'Starting…' });
    try {
      await streamDerive(parentId, {
        extraction_types: [...extraction],
        excluded_ids: [...excluded],
        include_container_ids: [...scope],
        collection_id: collectionId || null,
        title: title.trim(),
      }, (e) => {
        if (e.type === 'progress') {
          setProgress({ pct: e.pct, message: e.message });
        } else if (e.type === 'done') {
          setResult({ project_id: e.project_id, char_count: e.char_count, element_count: e.element_count, verse_count: e.verse_count });
          setProgress(null); setBusy(false);
        } else {
          setError(e.detail || 'Derivation failed');
          setProgress(null); setBusy(false);
        }
      });
    } catch (e) {
      setError(String(e));
      setProgress(null); setBusy(false);
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
  // Kept characters "completed" so far, mapped from the live derive progress fraction. The content
  // track fills green left-to-right over the kept (blue) regions as this advances.
  const greenChars = progress ? (progress.pct / 100) * stats.chars : 0;
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
              {containers.length > 0 && (
                <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
                  <p className="text-[0.8em] text-[var(--color-text-muted)] mb-1.5">
                    Restrict to section(s) <span className="opacity-70">(optional)</span> — e.g. just the Appendix.
                    Leave empty to use the whole document.
                  </p>
                  <div className="max-h-[160px] overflow-y-auto">
                    {containers.map((c) => (
                      <label key={c.id} className="flex items-center gap-2 px-2 py-1 text-[0.82em] hover:bg-[var(--color-bg-muted)] rounded cursor-pointer">
                        <input type="checkbox" checked={scope.has(c.id)} onChange={() => toggleScope(c.id)} />
                        <span className="flex-1 truncate">{elementLabel(c)}</span>
                        <span className="text-[0.78em] text-[var(--color-text-muted)]">{c.type}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : step === 2 ? (
            <div>
              <p className="text-[0.8em] text-[var(--color-text-muted)] mb-2">
                Deselect any elements (or whole containers) to exclude from the subtext.
                {' '}{stats.count} of {sections.filter((s) => extraction.has(s.type) && inScope(s, scopeSpans)).length} kept.
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
              <label className="block text-[0.85em]">
                <span className="text-[var(--color-text-muted)]">Add to collection</span>
                <select value={collectionId} onChange={(e) => setCollectionId(e.target.value)}
                  className="mt-1 w-full px-2 py-1.5 border border-[var(--color-border)] rounded bg-[var(--color-bg)] focus:border-[var(--color-border-focus)] focus:outline-none">
                  <option value="">New collection with parent (automatic)</option>
                  {collections.map((c) => (<option key={c.id} value={c.id}>{c.label}</option>))}
                </select>
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
                {progress && (() => {
                  // Paint green over the completed head of the kept regions (in document order),
                  // so each blue section turns green as generation reaches it.
                  let cum = 0;
                  const segs: ReactElement[] = [];
                  for (let i = 0; i < stats.spans.length; i++) {
                    const [s, e] = stats.spans[i];
                    const spanChars = e - s;
                    const filled = Math.max(0, Math.min(spanChars, greenChars - cum));
                    cum += spanChars;
                    if (filled > 0) {
                      segs.push(
                        <div key={`g${i}`} className="absolute top-0 bottom-0 bg-[var(--color-success,#137333)] transition-[width] duration-200"
                          style={{ left: `${(s / Math.max(1, textLen)) * 100}%`, width: `${(filled / Math.max(1, textLen)) * 100}%` }} />,
                      );
                    }
                  }
                  return segs;
                })()}
              </div>
              {progress ? (
                <p className="text-[0.72em] text-[var(--color-text-muted)] tabular-nums">
                  <span className="text-[var(--color-success,#137333)] font-semibold">{progress.pct}%</span> · {progress.message}
                </p>
              ) : (
                <p className="text-[0.72em] text-[var(--color-text-muted)]">Kept regions (blue) over the parent text; they fill green as each section is generated.</p>
              )}
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
