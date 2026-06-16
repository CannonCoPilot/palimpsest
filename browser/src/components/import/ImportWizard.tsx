/**
 * 5-step staged import wizard:
 *   1 Scan   — pick a file from imports/ (or upload), staged ingest, text becomes navigable
 *   2 Detect — run layout-formatting detection
 *   3 Map    — review/edit the colored section map (vertical workbench / horizontal overview)
 *   4 Mask   — per-type mask flags
 *   5 Apply  — confirm masking and run the deferred analysis
 */

import { useCallback, useEffect, useMemo, useRef, useState, type ReactElement } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useSectionStore } from '../../stores/sectionStore';
import SectionMinimap from './SectionMinimap';

type ImportFile = { path: string; name: string; folder: string; format: string; size: number };
const ACCEPTED = '.epub,.txt,.pdf,.html,.htm,.md,.markdown';
const STEPS = ['Scan', 'Detect', 'Map', 'Mask', 'Apply'] as const;

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ImportWizard(): ReactElement {
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [mapMode, setMapMode] = useState<'vertical' | 'horizontal'>('vertical');

  const sectionStore = useSectionStore();
  const paragraphs = useProjectStore((s) => (projectId ? s.projects[projectId]?.paragraphs : undefined));
  const paragraphStarts = useMemo(() => paragraphs?.map((p) => p.start) ?? [], [paragraphs]);

  const goDetect = useCallback(async () => {
    setBusy(true);
    await useSectionStore.getState().detect();
    setBusy(false);
    setStep(3);
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
    useProjectStore.getState().loadProject('', projectId);
  }, [projectId]);

  return (
    <div className="p-5">
      <div className="text-[#e8e8ea] text-lg font-semibold mb-3">Import a Text</div>
      <StepBar step={step} />

      {error && <div className="text-[#ff453a] text-sm mb-3">{error}</div>}

      {step === 1 && (
        <ScanStep
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
        <div className="space-y-4">
          <p className="text-[#d6d6d8] text-sm">
            The full text is now imported and navigable. Review it if you like, then detect the
            publication layout (front matter, chapters, notes…).
          </p>
          <div className="rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] p-3 max-h-[180px] overflow-y-auto text-[#b0b0b6] text-xs whitespace-pre-wrap font-[var(--font-serif)]">
            {useProjectStore.getState().projects[projectId ?? '']?.referenceText.slice(0, 1200) || 'Loading…'}
          </div>
          <div className="flex gap-2">
            <button onClick={goDetect} disabled={busy} className={btnPrimary}>
              {busy ? 'Detecting…' : 'Detect Formatting'}
            </button>
            <button onClick={openProject} className={btnGhost}>Open in reader</button>
          </div>
        </div>
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
          <SectionMinimap mode={mapMode} paragraphStarts={paragraphStarts} />
          <div className="flex gap-2">
            <button onClick={() => setStep(2)} className={btnGhost}>Back</button>
            <button onClick={async () => { await useSectionStore.getState().save(); setStep(4); }} className={btnPrimary}>
              Next: Masking
            </button>
          </div>
        </div>
      )}

      {step === 4 && <MaskStep onBack={() => setStep(3)} onNext={() => setStep(5)} />}

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

function ScanStep({
  onImported,
  setError,
}: {
  onImported: (projectId: string) => void;
  setError: (e: string | null) => void;
}): ReactElement {
  const [files, setFiles] = useState<ImportFile[] | null>(null);
  const [available, setAvailable] = useState(true);
  const [root, setRoot] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    fetch('/api/imports')
      .then((r) => r.json())
      .then((d) => {
        if (!active) return;
        setFiles(d.files ?? []);
        setAvailable(Boolean(d.available));
        setRoot(d.root ?? '');
      })
      .catch(() => active && (setFiles([]), setAvailable(false)));
    return () => { active = false; };
  }, []);

  const grouped = useMemo(() => {
    const m = new Map<string, ImportFile[]>();
    for (const f of files ?? []) {
      const k = f.folder || '—';
      (m.get(k) ?? m.set(k, []).get(k)!).push(f);
    }
    return Array.from(m.entries());
  }, [files]);

  const finishImport = useCallback(
    async (res: Response) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        setError(err.detail || 'Import failed');
        setBusy(false);
        return;
      }
      const data = await res.json();
      setBusy(false);
      onImported(data.project_id);
    },
    [onImported, setError],
  );

  const importLocal = useCallback(async () => {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch('/api/import/local', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selected, title, author, process: false }),
      });
      await finishImport(res);
    } catch {
      setError('Failed to connect to server');
      setBusy(false);
    }
  }, [selected, title, author, finishImport, setError]);

  const importUpload = useCallback(async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    const fd = new FormData();
    fd.append('file', file);
    if (title) fd.append('title', title);
    if (author) fd.append('author', author);
    try {
      await finishImport(await fetch('/api/import?process=false', { method: 'POST', body: fd }));
    } catch {
      setError('Failed to connect to server');
      setBusy(false);
    }
  }, [title, author, finishImport, setError]);

  const inputCls =
    'px-3 py-2 rounded-lg bg-[#1c1c1e] text-[#e8e8ea] placeholder:text-[#6e6e73] ring-1 ring-white/10 focus:outline-none focus:ring-2 focus:ring-[#0a84ff] text-sm';

  if (busy) {
    return <div className="p-8 text-center text-[#e8e8ea]">Scanning &amp; importing…</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2">
        <input className={inputCls} placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
        <input className={inputCls} placeholder="Author (optional)" value={author} onChange={(e) => setAuthor(e.target.value)} />
      </div>
      <div className="rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] max-h-[240px] overflow-y-auto">
        {files === null ? (
          <div className="p-4 text-[#8e8e93] text-sm">Loading…</div>
        ) : !available ? (
          <div className="p-4 text-[#8e8e93] text-sm">No imports folder. Drop files into <code className="text-[#b0b0b6]">{root || 'imports/'}</code>.</div>
        ) : files.length === 0 ? (
          <div className="p-4 text-[#8e8e93] text-sm">Imports folder is empty.</div>
        ) : (
          grouped.map(([folder, items]) => (
            <div key={folder}>
              <div className="sticky top-0 bg-[#242426] px-3 py-1 text-[#8a8a90] text-[11px] border-b border-white/5">{folder}</div>
              {items.map((f) => (
                <button
                  key={f.path}
                  onClick={() => setSelected(f.path)}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-left border-b border-white/5 ${selected === f.path ? 'bg-[#0a84ff]/20' : 'hover:bg-white/5'}`}
                >
                  <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${selected === f.path ? 'bg-[#0a84ff] text-white' : 'bg-white/10 text-[#b0b0b6]'}`}>{f.format}</span>
                  <span className="flex-1 min-w-0 truncate text-[#e8e8ea] text-sm">{f.name}</span>
                  <span className="shrink-0 text-[#6e6e73] text-xs">{formatBytes(f.size)}</span>
                </button>
              ))}
            </div>
          ))
        )}
      </div>
      <button disabled={!selected} onClick={importLocal} className={`w-full ${btnPrimary}`}>
        {selected ? 'Import & Scan' : 'Select a file'}
      </button>
      <input ref={fileRef} type="file" accept={ACCEPTED} onChange={importUpload} className="hidden" />
      <div className="text-center">
        <button onClick={() => fileRef.current?.click()} className="text-[#0a84ff] hover:text-[#0a78e6] text-sm">Upload from elsewhere…</button>
      </div>
    </div>
  );
}

function MaskStep({ onBack, onNext }: { onBack: () => void; onNext: () => void }): ReactElement {
  const types = useSectionStore((s) => s.types);
  const maskByType = useSectionStore((s) => s.maskByType);
  const sections = useSectionStore((s) => s.sections);
  const setMaskForType = useSectionStore((s) => s.setMaskForType);

  const usedTypes = useMemo(() => new Set(sections.map((s) => s.type)), [sections]);

  return (
    <div className="space-y-3">
      <p className="text-[#d6d6d8] text-sm">
        Choose which section types are masked (excluded from downstream analysis). Default:
        everything except chapter text.
      </p>
      <div className="rounded-lg ring-1 ring-white/10 bg-[#1c1c1e] divide-y divide-white/5">
        {types.map((t) => (
          <label key={t.key} className={`flex items-center gap-3 px-3 py-2 ${usedTypes.has(t.key) ? '' : 'opacity-40'}`}>
            <input
              type="checkbox"
              checked={maskByType[t.key] ?? t.default_mask}
              onChange={(e) => setMaskForType(t.key, e.target.checked)}
            />
            <span className="w-3 h-3 rounded-sm" style={{ background: t.color }} />
            <span className="flex-1 text-[#e8e8ea] text-sm">{t.label}</span>
            <span className="text-[#6e6e73] text-xs">{(maskByType[t.key] ?? t.default_mask) ? 'masked' : 'analyzed'}{usedTypes.has(t.key) ? '' : ' · unused'}</span>
          </label>
        ))}
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
        <div className="text-[#30d158] font-semibold">Masking applied — analysis complete.</div>
        <button onClick={onOpen} className={btnPrimary}>Open Project</button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-[#d6d6d8] text-sm">
        {pct}% of the text ({maskedChars.toLocaleString()} of {textLen.toLocaleString()} chars) will be
        masked and excluded from analysis. Confirm to apply masking and run the analysis.
      </p>
      <div className="flex gap-2">
        <button onClick={onBack} disabled={busy} className={btnGhost}>Back</button>
        <button onClick={onApply} disabled={busy} className={btnPrimary}>
          {busy ? 'Applying & analyzing…' : 'Confirm & Apply'}
        </button>
      </div>
    </div>
  );
}
