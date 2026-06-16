/**
 * 5-step staged import wizard:
 *   1 Scan   — pick a file from imports/ (or upload), staged ingest, text becomes navigable
 *   2 Detect — run layout-formatting detection
 *   3 Map    — review/edit the colored section map (vertical workbench / horizontal overview)
 *   4 Mask   — per-type mask flags
 *   5 Apply  — persist the masking decision (analysis is run later from the Analysis panel)
 */

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactElement } from 'react';
import { useProjectStore, type ProjectMetadata, type Paragraph } from '../../stores/projectStore';
import { useSectionStore } from '../../stores/sectionStore';
import { computeMaskedIntervals } from '../../utils/sectionMasking';
import SectionMinimap from './SectionMinimap';
import { MaskContextMenu } from './maskMenu';
import { offsetFromPoint, deepestSectionAt } from './textOffset';

type ImportStatus = 'new' | 'imported' | 'version';
type ImportFile = {
  path: string;
  name: string;
  folder: string;
  format: string;
  size: number;
  title?: string;
  author?: string;
  isbn?: string;
  status?: ImportStatus;
  matched_project_id?: string | null;
};
const ACCEPTED = '.epub,.txt,.pdf,.html,.htm,.md,.markdown';

// Visual cue for a file's library status (#16). `imported` = exact match already
// in the library; `version` = a different edition/format/language of a title you own.
function statusMeta(status?: ImportStatus): { label: string; cls: string } | null {
  if (status === 'imported')
    return { label: 'In library', cls: 'bg-[#30d158]/15 text-[#30d158] ring-1 ring-[#30d158]/30' };
  if (status === 'version')
    return { label: 'Other version', cls: 'bg-[#ff9f0a]/15 text-[#ff9f0a] ring-1 ring-[#ff9f0a]/30' };
  return null;
}

function Chevron({ open }: { open: boolean }): ReactElement {
  return (
    <svg
      viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth={2}
      strokeLinecap="round" strokeLinejoin="round"
      className={`shrink-0 transition-transform ${open ? 'rotate-90' : ''}`}
      aria-hidden="true"
    >
      <path d="m9 6 6 6-6 6" />
    </svg>
  );
}

type ImportEvent =
  | { type: 'progress'; phase: string; message: string; pct: number }
  | { type: 'done'; project_id: string; [k: string]: unknown }
  | { type: 'error'; detail: string; status?: number };

// Consume the Server-Sent Events from /api/import/local/stream. EventSource is
// GET-only, so we read the fetch body stream and split on the SSE record sep.
async function streamLocalImport(body: unknown, onEvent: (e: ImportEvent) => void): Promise<void> {
  const res = await fetch('/api/import/local/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    onEvent({ type: 'error', detail: err.detail || 'Import failed', status: res.status });
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
      if (dataLine) onEvent(JSON.parse(dataLine.slice(5).trim()) as ImportEvent);
    }
  }
}

type Progress = { pct: number; message: string };

// #18 — progress bar + ticker shown while a file is scanned & imported. pct < 0
// renders an indeterminate bar (upload path, which has no phase stream).
function ImportProgress({ pct, message }: Progress): ReactElement {
  const indeterminate = pct < 0;
  return (
    <div className="py-16 flex flex-col items-center gap-4">
      <div className="text-[#e8e8ea] text-sm font-medium">Scanning &amp; importing…</div>
      <div className="w-full max-w-md h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className={`h-full rounded-full bg-[#0a84ff] ${indeterminate ? 'w-full animate-pulse' : 'transition-[width] duration-300'}`}
          style={indeterminate ? undefined : { width: `${Math.max(3, pct)}%` }}
        />
      </div>
      <div className="text-[#b0b0b6] text-xs tabular-nums">
        {!indeterminate && <span className="text-[#e8e8ea]">{pct}% · </span>}
        {message}
      </div>
    </div>
  );
}
const STEPS = ['Scan', 'Detect', 'Map', 'Mask', 'Apply'] as const;

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ImportWizard({
  initialSourceFile,
  resumeProjectId,
}: { initialSourceFile?: string; resumeProjectId?: string } = {}): ReactElement {
  // Resume (#11/#26): re-run Steps 2–5 on an already-imported text — open at the
  // Detect step with the existing project's text + sections, no re-ingest.
  const [step, setStep] = useState(resumeProjectId ? 2 : 1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(resumeProjectId ?? null);
  const [mapMode, setMapMode] = useState<'vertical' | 'horizontal'>('vertical');

  useEffect(() => {
    if (!resumeProjectId) return;
    void useProjectStore.getState().loadProjectIntoStore(resumeProjectId);
    void useSectionStore.getState().load(resumeProjectId);
  }, [resumeProjectId]);

  const sectionStore = useSectionStore();
  const paragraphs = useProjectStore((s) => (projectId ? s.projects[projectId]?.paragraphs : undefined));
  const paragraphStarts = useMemo(() => paragraphs?.map((p) => p.start) ?? [], [paragraphs]);
  const referenceText = useProjectStore((s) => (projectId ? s.projects[projectId]?.referenceText ?? '' : ''));
  const projectMeta = useProjectStore((s) => (projectId ? s.projects[projectId]?.metadata ?? null : null));

  const goDetect = useCallback(async () => {
    setBusy(true);
    await useSectionStore.getState().detect();
    setBusy(false);
    // Stay on Step 2 so masked regions appear inline in the reader for review.
  }, []);

  const goApply = useCallback(async () => {
    setBusy(true);
    setStep(5);
    await useSectionStore.getState().apply();
    setBusy(false);
  }, []);

  const openProject = useCallback(() => {
    if (!projectId) return;
    const url = new URL(window.location.href);
    url.searchParams.set('project', projectId);
    window.history.pushState({}, '', url.toString());
    // Evict the wizard-hydrated copy so the reader re-discovers tracks from disk —
    // applying masks adds/removes the elements track since this project was loaded.
    useProjectStore.setState((s) => {
      const projects = { ...s.projects };
      delete projects[projectId];
      return { projects };
    });
    useProjectStore.getState().loadProject('', projectId);
  }, [projectId]);

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-8">
      <StepBar step={step} />

      {error && <div className="text-[#ff453a] text-sm mb-3">{error}</div>}

      {step === 1 && (
        <ScanStep
          initialSourceFile={initialSourceFile}
          onImported={(pid) => {
            setProjectId(pid);
            void useProjectStore.getState().loadProjectIntoStore(pid);
            void useSectionStore.getState().load(pid);
            setStep(2);
          }}
          setError={setError}
        />
      )}

      {step === 2 && (
        <DetectStep
          paragraphs={paragraphs ?? []}
          text={referenceText}
          meta={projectMeta}
          busy={busy}
          onDetect={goDetect}
          onNext={() => setStep(3)}
          onOpen={openProject}
        />
      )}

      {step === 3 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-[#d6d6d8] text-sm">
              {sectionStore.sections.length} sections detected. Drag boundaries, right-click to add.
            </p>
            <div className="flex rounded-md overflow-hidden ring-1 ring-white/10 text-xs">
              <button
                onClick={() => setMapMode('vertical')}
                className={`px-2 py-1 ${mapMode === 'vertical' ? 'bg-[#0a84ff] text-white' : 'text-[#b0b0b6]'}`}
              >Edit</button>
              <button
                onClick={() => setMapMode('horizontal')}
                className={`px-2 py-1 ${mapMode === 'horizontal' ? 'bg-[#0a84ff] text-white' : 'text-[#b0b0b6]'}`}
              >Overview</button>
            </div>
          </div>
          <SectionMinimap mode={mapMode} paragraphStarts={paragraphStarts} text={referenceText} />
          <div className="flex gap-2">
            <button onClick={() => setStep(2)} className={btnGhost}>Back</button>
            <button onClick={async () => { await useSectionStore.getState().save(); setStep(4); }} className={btnPrimary}>
              Next: Masking
            </button>
          </div>
        </div>
      )}

      {step === 4 && <MaskStep text={referenceText} onBack={() => setStep(3)} onNext={() => setStep(5)} />}

      {step === 5 && (
        <ApplyStep busy={busy} onApply={goApply} onOpen={openProject} onBack={() => setStep(4)} />
      )}
    </div>
  );
}

const btnPrimary =
  'px-4 py-2 rounded-lg bg-[#0a84ff] hover:bg-[#0a78e6] disabled:bg-white/10 disabled:text-[#6e6e73] text-white text-sm font-medium';
const btnGhost =
  'px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-[#d6d6d8] text-sm ring-1 ring-white/10';

function ScanStats({ meta, charCount }: { meta: ProjectMetadata | null; charCount: number }): ReactElement {
  const words = meta?.word_count ?? 0;
  const stats: Array<[string, string]> = [
    ['Words', words.toLocaleString()],
    ['Pages (est.)', words ? `~${Math.max(1, Math.round(words / 250)).toLocaleString()}` : '—'],
    ['Paragraphs', (meta?.paragraph_count ?? 0).toLocaleString()],
    ['Sentences', (meta?.sentence_count ?? 0).toLocaleString()],
    ['Characters', charCount.toLocaleString()],
  ];
  return (
    <div className="grid grid-cols-5 gap-2">
      {stats.map(([label, value]) => (
        <div key={label} className="rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] px-2.5 py-2 text-center">
          <div className="text-[#e8e8ea] text-[15px] font-semibold tabular-nums">{value}</div>
          <div className="text-[#8a8a90] text-[10px] uppercase tracking-wide mt-0.5">{label}</div>
        </div>
      ))}
    </div>
  );
}

function StepBar({ step }: { step: number }): ReactElement {
  return (
    <div className="flex items-center gap-1 mb-4">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const active = n === step;
        const done = n < step;
        return (
          <div key={label} className="flex items-center gap-1">
            <span
              className={`px-2 py-0.5 rounded text-[11px] ${
                active ? 'bg-[#0a84ff] text-white' : done ? 'bg-white/15 text-[#e8e8ea]' : 'bg-white/5 text-[#6e6e73]'
              }`}
            >
              {n}. {label}
            </span>
            {n < STEPS.length && <span className="text-[#3a3a3d]">→</span>}
          </div>
        );
      })}
    </div>
  );
}

type ReaderSegment = { text: string; start: number; masked: boolean; selected: boolean };

// Split a paragraph into runs at every masked-interval and selected-range boundary
// inside it, so each run is uniformly masked/selected and carries its char offset.
function paragraphSegments(
  text: string,
  pStart: number,
  pEnd: number,
  masked: Array<[number, number]>,
  sel: [number, number] | null,
): ReaderSegment[] {
  const cuts = new Set<number>([pStart, pEnd]);
  for (const [a, b] of masked) {
    if (a > pStart && a < pEnd) cuts.add(a);
    if (b > pStart && b < pEnd) cuts.add(b);
  }
  if (sel) {
    if (sel[0] > pStart && sel[0] < pEnd) cuts.add(sel[0]);
    if (sel[1] > pStart && sel[1] < pEnd) cuts.add(sel[1]);
  }
  const points = Array.from(cuts).sort((a, b) => a - b);
  const segs: ReaderSegment[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const s = points[i];
    const e = points[i + 1];
    if (e <= s) continue;
    const mid = (s + e) / 2;
    const isMasked = masked.some(([a, b]) => mid >= a && mid < b);
    const isSel = !!sel && mid >= sel[0] && mid < sel[1];
    segs.push({ text: text.slice(s, e), start: s, masked: isMasked, selected: isSel });
  }
  return segs;
}

const MASKED_SPAN_STYLE = { backgroundColor: '#3a3a3d', color: '#f5f5f5', borderRadius: 2 } as const;
const SELECTED_SPAN_STYLE = { outline: '1.5px solid #0a84ff', outlineOffset: '-1px', borderRadius: 2 } as CSSProperties;
// content-visibility lets the browser skip layout of offscreen paragraphs cheaply;
// progressive loading caps how many <p> nodes exist at once for very long texts.
const PARAGRAPH_CV_STYLE = { contentVisibility: 'auto', containIntrinsicSize: 'auto 60px' } as CSSProperties;
const READER_PAGE = 400;

// #19/#28 — the full text, scrollable, with masked ranges highlighted inline.
// Left-click selects the element at a point; right-click opens the mask-edit menu.
function FullTextReader({
  paragraphs,
  text,
  masked,
  fontScale,
  sel,
  onSelect,
  onContext,
}: {
  paragraphs: Paragraph[];
  text: string;
  masked: Array<[number, number]>;
  fontScale: number;
  sel: [number, number] | null;
  onSelect: (off: number) => void;
  onContext: (off: number, x: number, y: number) => void;
}): ReactElement {
  const [limit, setLimit] = useState(READER_PAGE);
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => { setLimit(READER_PAGE); }, [paragraphs]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) setLimit((n) => Math.min(n + READER_PAGE, paragraphs.length)); },
      { rootMargin: '800px' },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [paragraphs.length]);

  const shown = paragraphs.slice(0, limit);
  return (
    <div
      data-reader
      className="rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] overflow-y-auto px-6 py-4 max-h-[64vh] leading-relaxed font-[var(--font-serif)] text-[#cfcfd2] select-none"
      style={{ fontSize: `${fontScale}rem` }}
      onClick={(e) => {
        // On macOS a Control-click is a secondary (right) click: it also fires this
        // click with ctrlKey set. Let onContextMenu handle it instead of selecting.
        if (e.ctrlKey) return;
        const off = offsetFromPoint(e.clientX, e.clientY, e.target);
        if (off != null) onSelect(off);
      }}
      onContextMenu={(e) => {
        e.preventDefault(); // always suppress the native menu inside the reader
        const off = offsetFromPoint(e.clientX, e.clientY, e.target);
        if (off != null) onContext(off, e.clientX, e.clientY);
      }}
    >
      {text.length === 0 ? (
        <div className="text-[#6e6e73] text-sm">Loading text…</div>
      ) : (
        shown.map((p) => (
          <p key={p.index} className="mb-3 whitespace-pre-wrap" style={PARAGRAPH_CV_STYLE}>
            {paragraphSegments(text, p.start, p.end, masked, sel).map((seg, i) => (
              <span
                key={i}
                data-off={seg.start}
                data-end={seg.start + seg.text.length}
                style={{
                  ...(seg.masked ? MASKED_SPAN_STYLE : null),
                  ...(seg.selected ? SELECTED_SPAN_STYLE : null),
                }}
              >
                {seg.text}
              </span>
            ))}
          </p>
        ))
      )}
      {limit < paragraphs.length && (
        <div ref={sentinelRef} className="py-4 text-center text-[#6e6e73] text-xs">
          Loading more… ({limit.toLocaleString()} / {paragraphs.length.toLocaleString()} paragraphs)
        </div>
      )}
    </div>
  );
}

// #19/#21 — Step 2 (Detect): a reader-like full-text view. Before detection it
// shows the plain text; after, masked regions are highlighted so the whole text
// can be scrolled and evaluated before refining boundaries in Step 3.
function DetectStep({
  paragraphs,
  text,
  meta,
  busy,
  onDetect,
  onNext,
  onOpen,
}: {
  paragraphs: Paragraph[];
  text: string;
  meta: ProjectMetadata | null;
  busy: boolean;
  onDetect: () => void;
  onNext: () => void;
  onOpen: () => void;
}): ReactElement {
  const sections = useSectionStore((s) => s.sections);
  const maskByType = useSectionStore((s) => s.maskByType);
  const textLen = useSectionStore((s) => s.textLen);
  const types = useSectionStore((s) => s.types);
  const selectedId = useSectionStore((s) => s.selectedId);
  const setSelected = useSectionStore((s) => s.setSelected);
  const [fontScale, setFontScale] = useState(1);
  const [menu, setMenu] = useState<{ x: number; y: number; off: number } | null>(null);

  const detected = sections.length > 0;
  const masked = useMemo(
    () => computeMaskedIntervals(sections, maskByType, textLen || text.length),
    [sections, maskByType, textLen, text.length],
  );
  const maskedChars = masked.reduce((sum, [a, b]) => sum + (b - a), 0);
  const pct = text.length ? ((maskedChars / text.length) * 100).toFixed(1) : '0';

  const selectedRange = useMemo((): [number, number] | null => {
    const s = sections.find((x) => x.id === selectedId);
    return s ? [s.start, s.end] : null;
  }, [sections, selectedId]);
  const selectedSection = sections.find((x) => x.id === selectedId) ?? null;

  return (
    <div className="space-y-3">
      <ScanStats meta={meta} charCount={text.length} />
      <div className="flex items-center justify-between gap-3">
        <p className="text-[#d6d6d8] text-sm flex-1">
          {detected
            ? `Detected layout below — masked regions are highlighted (${pct}% masked, ${sections.length} sections). Left-click an element to select it; right-click for precise mask operations.`
            : 'The full text is below — scroll to navigate it. Detect the publication layout (front matter, chapters, notes…) to mask non-body text.'}
        </p>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[#8a8a90] text-[11px]">A</span>
          <input
            type="range" min={0.8} max={1.6} step={0.1} value={fontScale}
            onChange={(e) => setFontScale(Number(e.target.value))}
            aria-label="Text size" className="w-24 accent-[#0a84ff]"
          />
          <span className="text-[#8a8a90] text-[15px]">A</span>
        </div>
      </div>
      {detected && selectedSection && (
        <div className="rounded-lg ring-1 ring-[#0a84ff]/40 bg-[#0a84ff]/10 px-3 py-1.5 text-[12px] text-[#d6e7ff] flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: types.find((t) => t.key === selectedSection.type)?.color ?? '#8e8e93' }} />
          Selected: <strong className="text-white">{selectedSection.label || types.find((t) => t.key === selectedSection.type)?.label || selectedSection.type}</strong>
          <span className="text-[#9ab8e0]">({selectedSection.start.toLocaleString()}–{selectedSection.end.toLocaleString()}, {(selectedSection.end - selectedSection.start).toLocaleString()} chars)</span>
          <button onClick={() => setSelected(null)} className="ml-auto text-[#9ab8e0] hover:text-white">clear</button>
        </div>
      )}
      <FullTextReader
        paragraphs={paragraphs}
        text={text}
        masked={masked}
        fontScale={fontScale}
        sel={selectedRange}
        onSelect={(off) => { setSelected(deepestSectionAt(sections, off)?.id ?? null); }}
        onContext={(off, x, y) => setMenu({ off, x, y })}
      />
      <div className="flex gap-2">
        <button onClick={onDetect} disabled={busy} className={btnPrimary}>
          {busy ? 'Detecting…' : detected ? 'Re-detect Formatting' : 'Detect Formatting'}
        </button>
        {detected && <button onClick={onNext} className={btnPrimary}>Next: Refine sections</button>}
        <button onClick={onOpen} className={btnGhost}>Open in reader</button>
      </div>
      {menu && (
        <MaskContextMenu
          x={menu.x} y={menu.y} off={menu.off}
          sections={sections} types={types} selectedId={selectedId}
          onClose={() => setMenu(null)}
        />
      )}
    </div>
  );
}

function ScanStep({
  onImported,
  setError,
  initialSourceFile,
}: {
  onImported: (projectId: string) => void;
  setError: (e: string | null) => void;
  initialSourceFile?: string;
}): ReactElement {
  const [files, setFiles] = useState<ImportFile[] | null>(null);
  const [available, setAvailable] = useState(true);
  const [root, setRoot] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [titleQuery, setTitleQuery] = useState('');
  const [authorQuery, setAuthorQuery] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [progress, setProgress] = useState<Progress | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    fetch('/api/imports')
      .then((r) => r.json())
      .then((d) => {
        if (!active) return;
        const list: ImportFile[] = d.files ?? [];
        setFiles(list);
        setAvailable(Boolean(d.available));
        setRoot(d.root ?? '');
        // Re-import: pre-select the book's source file and open its folder.
        if (initialSourceFile) {
          const match = list.find((f) => f.name === initialSourceFile);
          if (match) {
            setSelected(match.path);
            setExpanded(new Set([match.folder || '—']));
          }
        }
      })
      .catch(() => active && (setFiles([]), setAvailable(false)));
    return () => { active = false; };
  }, [initialSourceFile]);

  const selectedFile = useMemo(
    () => files?.find((f) => f.path === selected) ?? null,
    [files, selected],
  );

  // #14 — filter the list by parsed title / author (falls back to filename).
  const filtered = useMemo(() => {
    const tq = titleQuery.trim().toLowerCase();
    const aq = authorQuery.trim().toLowerCase();
    if (!tq && !aq) return files ?? [];
    return (files ?? []).filter((f) => {
      const t = (f.title || f.name).toLowerCase();
      const a = (f.author || '').toLowerCase();
      const okT = !tq || t.includes(tq) || f.name.toLowerCase().includes(tq);
      const okA = !aq || a.includes(aq);
      return okT && okA;
    });
  }, [files, titleQuery, authorQuery]);

  const grouped = useMemo(() => {
    const m = new Map<string, ImportFile[]>();
    for (const f of filtered) {
      const k = f.folder || '—';
      (m.get(k) ?? m.set(k, []).get(k)!).push(f);
    }
    return Array.from(m.entries());
  }, [filtered]);

  const searching = Boolean(titleQuery.trim() || authorQuery.trim());
  // While searching, every matching group is forced open so hits are visible.
  const isOpen = useCallback((folder: string) => searching || expanded.has(folder), [searching, expanded]);
  const toggleFolder = useCallback((folder: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(folder)) next.delete(folder);
      else next.add(folder);
      return next;
    });
  }, []);

  const importLocal = useCallback(async () => {
    if (!selected) return;
    setError(null);
    setProgress({ pct: 0, message: 'Starting…' });
    try {
      // Metadata comes from the file's parsed title/author (the boxes are search
      // filters now); the backend re-parses from the filename if empty.
      await streamLocalImport(
        {
          path: selected,
          title: selectedFile?.title ?? '',
          author: selectedFile?.author ?? '',
          process: false,
          overwrite: Boolean(initialSourceFile),
        },
        (evt) => {
          if (evt.type === 'progress') setProgress({ pct: evt.pct, message: evt.message });
          else if (evt.type === 'done') { setProgress({ pct: 100, message: 'Imported' }); onImported(evt.project_id); }
          else { setError(evt.detail || 'Import failed'); setProgress(null); }
        },
      );
    } catch {
      setError('Failed to connect to server');
      setProgress(null);
    }
  }, [selected, selectedFile, onImported, setError, initialSourceFile]);

  const importUpload = useCallback(async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setError(null);
    setProgress({ pct: -1, message: file.name });  // upload path has no phase stream
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/import?process=false', { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        setError(err.detail || 'Import failed');
        setProgress(null);
        return;
      }
      const data = await res.json();
      setProgress({ pct: 100, message: 'Imported' });
      onImported(data.project_id);
    } catch {
      setError('Failed to connect to server');
      setProgress(null);
    }
  }, [onImported, setError]);

  const inputCls =
    'flex-1 px-3 py-2 rounded-lg bg-[#1c1c1e] text-[#e8e8ea] placeholder:text-[#6e6e73] ring-1 ring-white/10 focus:outline-none focus:ring-2 focus:ring-[#0a84ff] text-sm';

  const totalFiles = files?.length ?? 0;
  const shownFiles = filtered.length;
  const importLabel = selectedFile?.status === 'imported' ? 'Re-import & Scan' : 'Import & Scan';

  if (progress) return <ImportProgress pct={progress.pct} message={progress.message} />;

  return (
    <div className="space-y-3">
      {initialSourceFile && (
        <div className="rounded-lg ring-1 ring-[#0a84ff]/40 bg-[#0a84ff]/15 px-3 py-2 text-[12px] text-[#d6e7ff]">
          Re-importing <strong className="text-white">{initialSourceFile}</strong>. Completing the wizard replaces the existing analysis.
        </div>
      )}
      <div className="flex flex-col sm:flex-row gap-2">
        <input className={inputCls} placeholder="Search by title" value={titleQuery} onChange={(e) => setTitleQuery(e.target.value)} />
        <input className={inputCls} placeholder="Search by author" value={authorQuery} onChange={(e) => setAuthorQuery(e.target.value)} />
      </div>
      {searching && (
        <div className="text-[#8a8a90] text-[12px]">
          {shownFiles} of {totalFiles} files match
          {' · '}
          <button onClick={() => { setTitleQuery(''); setAuthorQuery(''); }} className="text-[#0a84ff] hover:text-[#0a78e6]">clear</button>
        </div>
      )}
      <div className="rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] max-h-[58vh] overflow-y-auto">
        {files === null ? (
          <div className="p-4 text-[#8e8e93] text-sm">Loading…</div>
        ) : !available ? (
          <div className="p-4 text-[#8e8e93] text-sm">No imports folder. Drop files into <code className="text-[#b0b0b6]">{root || 'imports/'}</code>.</div>
        ) : totalFiles === 0 ? (
          <div className="p-4 text-[#8e8e93] text-sm">Imports folder is empty.</div>
        ) : grouped.length === 0 ? (
          <div className="p-4 text-[#8e8e93] text-sm">No files match the current search.</div>
        ) : (
          grouped.map(([folder, items]) => {
            const open = isOpen(folder);
            const imported = items.filter((f) => f.status === 'imported').length;
            const version = items.filter((f) => f.status === 'version').length;
            return (
              <div key={folder}>
                <button
                  type="button"
                  onClick={() => toggleFolder(folder)}
                  className="w-full sticky top-0 z-10 flex items-center gap-2 px-3 py-1.5 bg-[#242426] hover:bg-[#2a2a2c] border-b border-white/5 text-left"
                >
                  <span className="text-[#8a8a90]"><Chevron open={open} /></span>
                  <span className="flex-1 min-w-0 truncate text-[#d6d6d8] text-[12px]">{folder}</span>
                  {imported > 0 && <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] bg-[#30d158]/15 text-[#30d158]">{imported} in library</span>}
                  {version > 0 && <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] bg-[#ff9f0a]/15 text-[#ff9f0a]">{version} other ver.</span>}
                  <span className="shrink-0 text-[#6e6e73] text-[11px] tabular-nums">{items.length}</span>
                </button>
                {open && items.map((f) => {
                  const badge = statusMeta(f.status);
                  return (
                    <button
                      key={f.path}
                      onClick={() => setSelected(f.path)}
                      title={f.name}
                      className={`w-full flex items-center gap-2 pl-8 pr-3 py-2 text-left border-b border-white/5 ${selected === f.path ? 'bg-[#0a84ff]/20' : 'hover:bg-white/5'}`}
                    >
                      <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${selected === f.path ? 'bg-[#0a84ff] text-white' : 'bg-white/10 text-[#b0b0b6]'}`}>{f.format}</span>
                      <span className="flex-1 min-w-0 truncate text-[#e8e8ea] text-sm">
                        {f.title || f.name}
                        {f.author && <span className="text-[#8a8a90] text-xs"> · {f.author}</span>}
                      </span>
                      {badge && <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] ${badge.cls}`}>{badge.label}</span>}
                      <span className="shrink-0 text-[#6e6e73] text-xs tabular-nums">{formatBytes(f.size)}</span>
                    </button>
                  );
                })}
              </div>
            );
          })
        )}
      </div>
      <button disabled={!selected} onClick={importLocal} className={`w-full ${btnPrimary}`}>
        {selected ? importLabel : 'Select a file'}
      </button>
      <input ref={fileRef} type="file" accept={ACCEPTED} onChange={importUpload} className="hidden" />
      <div className="text-center">
        <button onClick={() => fileRef.current?.click()} className="text-[#0a84ff] hover:text-[#0a78e6] text-sm">Upload from file</button>
      </div>
    </div>
  );
}

const NEW_TYPE_COLORS = ['#ff9f0a', '#bf5af2', '#5ac8fa', '#ff375f', '#30d158', '#ffd60a', '#64d2ff', '#ac8e68'];

function MaskStep({ text, onBack, onNext }: { text: string; onBack: () => void; onNext: () => void }): ReactElement {
  const types = useSectionStore((s) => s.types);
  const maskByType = useSectionStore((s) => s.maskByType);
  const sections = useSectionStore((s) => s.sections);
  const textLen = useSectionStore((s) => s.textLen);
  const setMaskForType = useSectionStore((s) => s.setMaskForType);
  const maskedIntervals = useSectionStore((s) => s.maskedIntervals);
  const addType = useSectionStore((s) => s.addType);
  const removeType = useSectionStore((s) => s.removeType);

  const [newName, setNewName] = useState('');
  const [newColor, setNewColor] = useState(NEW_TYPE_COLORS[0]);
  const [newMasked, setNewMasked] = useState(true);
  const [addError, setAddError] = useState<string | null>(null);

  // #24 — per-type element COUNT (how many sections of each type) and word totals.
  const { countByType, wordsByType } = useMemo(() => {
    const counts: Record<string, number> = {};
    const words: Record<string, number> = {};
    for (const s of sections) {
      counts[s.type] = (counts[s.type] ?? 0) + 1;
      words[s.type] = (words[s.type] ?? 0) + (text.slice(s.start, s.end).match(/\S+/g) ?? []).length;
    }
    return { countByType: counts, wordsByType: words };
  }, [sections, text]);

  // #25 — live masked total; recomputes on every mask toggle (maskByType subscription).
  const maskedChars = useMemo(
    () => maskedIntervals().reduce((sum, [a, b]) => sum + (b - a), 0),
    [maskedIntervals, maskByType, sections, textLen],
  );
  const pct = textLen ? ((maskedChars / textLen) * 100).toFixed(1) : '0';

  const submitNewType = (): void => {
    const res = addType(newName, newColor, newMasked);
    if (res.ok) {
      setNewName('');
      setAddError(null);
      setNewColor(NEW_TYPE_COLORS[(NEW_TYPE_COLORS.indexOf(newColor) + 1) % NEW_TYPE_COLORS.length]);
    } else {
      setAddError(res.error);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-[#d6d6d8] text-sm">
        Choose which section types are masked (excluded from downstream analysis). Default:
        everything except chapter text.
      </p>
      <div className="rounded-lg ring-1 ring-[#0a84ff]/40 bg-[#0a84ff]/15 px-3 py-2 text-[13px] text-[#d6e7ff]">
        <strong className="text-white tabular-nums">{pct}%</strong> of the text will be masked
        {' '}({maskedChars.toLocaleString()} of {textLen.toLocaleString()} chars).
      </div>
      <div className="rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] divide-y divide-white/5 max-h-[42vh] overflow-y-auto">
        {types.map((t) => {
          const isMasked = maskByType[t.key] ?? t.default_mask;
          const count = countByType[t.key] ?? 0;
          const used = count > 0;
          const removable = t.builtin === false && count === 0;
          return (
            <div key={t.key} className={`flex items-center gap-3 px-3 py-2 ${used ? '' : 'opacity-40'}`}>
              <label className="flex items-center gap-3 flex-1 min-w-0 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isMasked}
                  onChange={(e) => setMaskForType(t.key, e.target.checked)}
                />
                <span className="w-3 h-3 rounded-sm shrink-0" style={{ background: t.color }} />
                <span className="flex-1 min-w-0 truncate text-[#e8e8ea] text-sm">
                  {t.label}
                  {t.builtin === false && <span className="ml-1.5 text-[#8a8a90] text-[10px] uppercase tracking-wide">custom</span>}
                </span>
                <span className="text-[#8a8a90] text-xs tabular-nums shrink-0">
                  {count.toLocaleString()} {count === 1 ? 'section' : 'sections'}
                  {used && <span className="text-[#6e6e73]"> · {(wordsByType[t.key] ?? 0).toLocaleString()} words</span>}
                </span>
                <span className="w-16 text-right text-[#6e6e73] text-xs shrink-0">{used ? (isMasked ? 'masked' : 'analyzed') : 'unused'}</span>
              </label>
              {removable && (
                <button
                  type="button"
                  onClick={() => removeType(t.key)}
                  aria-label={`Remove custom layer ${t.label}`}
                  className="shrink-0 w-5 h-5 rounded text-[#8e8e93] hover:text-white hover:bg-white/10 text-xs"
                >
                  ✕
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* #22 — add a custom mask layer */}
      <div className="rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] px-3 py-2.5 space-y-2">
        <div className="text-[#8a8a90] text-[11px] uppercase tracking-wide">Add custom layer</div>
        <div className="flex items-center gap-2">
          <input
            type="color" value={newColor} onChange={(e) => setNewColor(e.target.value)}
            aria-label="Layer color" className="w-8 h-8 rounded bg-transparent cursor-pointer shrink-0"
          />
          <input
            value={newName}
            onChange={(e) => { setNewName(e.target.value); setAddError(null); }}
            onKeyDown={(e) => { if (e.key === 'Enter') submitNewType(); }}
            placeholder="Layer name (e.g. Marginalia)"
            className="flex-1 px-3 py-1.5 rounded-lg bg-[#161618] text-[#e8e8ea] placeholder:text-[#6e6e73] ring-1 ring-white/10 focus:outline-none focus:ring-2 focus:ring-[#0a84ff] text-sm"
          />
          <label className="flex items-center gap-1.5 text-[#b0b0b6] text-xs shrink-0">
            <input type="checkbox" checked={newMasked} onChange={(e) => setNewMasked(e.target.checked)} />
            masked
          </label>
          <button type="button" onClick={submitNewType} disabled={!newName.trim()} className={btnPrimary}>Add</button>
        </div>
        {addError && <div className="text-[#ff453a] text-xs">{addError}</div>}
      </div>

      <div className="flex gap-2">
        <button onClick={onBack} className={btnGhost}>Back</button>
        <button onClick={async () => { await useSectionStore.getState().save(); onNext(); }} className={btnPrimary}>Next: Confirm</button>
      </div>
    </div>
  );
}

function ApplyStep({
  busy,
  onApply,
  onOpen,
  onBack,
}: {
  busy: boolean;
  onApply: () => void;
  onOpen: () => void;
  onBack: () => void;
}): ReactElement {
  const textLen = useSectionStore((s) => s.textLen);
  const applied = useSectionStore((s) => s.applied);
  const maskedIntervals = useSectionStore((s) => s.maskedIntervals);
  const masked = maskedIntervals();
  const maskedChars = masked.reduce((sum, [a, b]) => sum + (b - a), 0);
  const pct = textLen ? ((maskedChars / textLen) * 100).toFixed(1) : '0';

  if (applied) {
    return (
      <div className="space-y-3">
        <div className="text-[#30d158] font-semibold">Masking applied.</div>
        <p className="text-[#8e8e93] text-xs">
          No analysis has been run yet — open the project and launch the analyses you want
          from the Analysis panel.
        </p>
        <button onClick={onOpen} className={btnPrimary}>Open Project</button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-[#d6d6d8] text-sm">
        {pct}% of the text ({maskedChars.toLocaleString()} of {textLen.toLocaleString()} chars) will be
        masked and excluded from analysis. Applying saves these masks — you can then review and run
        the analyses from the Analysis panel whenever you're ready.
      </p>
      <div className="flex gap-2">
        <button onClick={onBack} disabled={busy} className={btnGhost}>Back</button>
        <button onClick={onApply} disabled={busy} className={btnPrimary}>
          {busy ? 'Applying…' : 'Confirm & Apply'}
        </button>
      </div>
    </div>
  );
}
