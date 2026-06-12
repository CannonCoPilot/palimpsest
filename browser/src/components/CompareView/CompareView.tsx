/**
 * CompareView — container for two-text comparison sub-views.
 * Sub-nav selects: Alignment | Dotplot | Synteny | Circos | Diff
 */

import { useEffect, useState } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useComparisonStore, type CompareSubView } from '../../stores/comparisonStore';

const SUB_VIEWS: { id: CompareSubView; label: string }[] = [
  { id: 'alignment', label: 'Alignment' },
  { id: 'dotplot', label: 'Dotplot' },
  { id: 'synteny', label: 'Synteny' },
  { id: 'circos', label: 'Circos' },
  { id: 'diff', label: 'Diff' },
];

interface ProjectOption {
  id: string;
  title: string;
  author: string;
}

function CompareProjectPicker({ onSelect }: { onSelect: (id: string) => void }) {
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);

  useEffect(() => {
    fetch('/api/projects')
      .then((r) => r.json())
      .then((data: ProjectOption[]) => setProjects(data.filter((p) => p.id !== activeProjectId)))
      .catch(() => {});
  }, [activeProjectId]);

  if (projects.length === 0) {
    return <span className="text-[var(--color-text-muted)] text-[0.85em]">No other projects available for comparison</span>;
  }

  return (
    <select
      onChange={(e) => { if (e.target.value) onSelect(e.target.value); }}
      defaultValue=""
      className="px-2 py-1 border border-[var(--color-border)] rounded bg-[var(--color-bg)] text-[0.85em] cursor-pointer"
    >
      <option value="" disabled>Select text to compare...</option>
      {projects.map((p) => (
        <option key={p.id} value={p.id}>{p.title}{p.author ? ` — ${p.author}` : ''}</option>
      ))}
    </select>
  );
}

export default function CompareView() {
  const activeSubView = useComparisonStore((s) => s.activeSubView);
  const setActiveSubView = useComparisonStore((s) => s.setActiveSubView);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const secondaryProjectId = useProjectStore((s) => s.secondaryProjectId);
  const secondaryMeta = useProjectStore((s) => s.projects[s.secondaryProjectId ?? '']?.metadata);
  const activeMeta = useProjectStore((s) => s.projects[s.activeProjectId ?? '']?.metadata);
  const setSecondary = useProjectStore((s) => s.setSecondaryProject);
  const loadProject = useProjectStore((s) => s.loadProject);
  const loading = useComparisonStore((s) => s.loading);
  const error = useComparisonStore((s) => s.error);
  const alignmentRecords = useComparisonStore((s) => s.alignmentRecords);
  const activeMethod = useComparisonStore((s) => s.activeMethod);
  const setActiveMethod = useComparisonStore((s) => s.setActiveMethod);
  const runAlignment = useComparisonStore((s) => s.runAlignment);
  const jobStatus = useComparisonStore((s) => s.jobStatus);

  const handleSelectSecondary = async (id: string) => {
    await loadProject('', id);
    setSecondary(id);
  };

  const handleRunAlignment = () => {
    if (activeProjectId && secondaryProjectId) {
      runAlignment(activeProjectId, secondaryProjectId, activeMethod);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden font-[var(--font-sans)]">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)] text-[0.85em]">
        <span className="font-semibold shrink-0">Compare</span>
        <span className="text-[var(--color-text-muted)]">
          {activeMeta?.title ?? 'No project loaded'}
        </span>
        <span className="text-[var(--color-text-muted)]">vs</span>
        {secondaryMeta ? (
          <span className="font-medium text-[var(--color-primary)]">{secondaryMeta.title}</span>
        ) : (
          <CompareProjectPicker onSelect={handleSelectSecondary} />
        )}
        {secondaryProjectId && (
          <button
            onClick={() => { setSecondary(null); useComparisonStore.getState().reset(); }}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-danger)] cursor-pointer text-[0.85em]"
            title="Remove comparison"
          >
            Clear
          </button>
        )}

        <div className="ml-auto flex items-center gap-2">
          {secondaryProjectId && (
            <>
              <select
                value={activeMethod}
                onChange={(e) => setActiveMethod(e.target.value as typeof activeMethod)}
                className="px-1.5 py-0.5 border border-[var(--color-border)] rounded bg-[var(--color-bg)] cursor-pointer text-[0.85em]"
              >
                <option value="semantic">Semantic (SBERT)</option>
                <option value="alphabet">Alphabet</option>
                <option value="word">Word overlap</option>
              </select>
              <button
                onClick={handleRunAlignment}
                disabled={loading}
                className="px-3 py-1 rounded bg-[var(--color-primary)] text-white cursor-pointer hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed text-[0.85em]"
              >
                {loading ? 'Running...' : 'Align'}
              </button>
              {alignmentRecords.length > 0 && (
                <span className="text-[var(--color-text-muted)]">
                  {alignmentRecords.length} alignment{alignmentRecords.length !== 1 ? 's' : ''}
                </span>
              )}
            </>
          )}
        </div>
      </div>

      {/* Sub-view tabs */}
      {secondaryProjectId && (
        <div className="flex gap-0 border-b border-[var(--color-border)] bg-[var(--color-bg)] text-[0.8em]">
          {SUB_VIEWS.map((sv) => (
            <button
              key={sv.id}
              onClick={() => setActiveSubView(sv.id)}
              className={`px-3 py-1.5 border-b-2 cursor-pointer transition-colors ${
                activeSubView === sv.id
                  ? 'border-[var(--color-primary)] text-[var(--color-primary)] font-medium'
                  : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {sv.label}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {error && (
          <div className="px-4 py-2 bg-[var(--color-danger-subtle)] text-[var(--color-danger)] text-[0.85em]">
            {error}
          </div>
        )}

        {!activeProjectId && (
          <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">
            Load a project first, then select a second text to compare.
          </div>
        )}

        {activeProjectId && !secondaryProjectId && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-[var(--color-text-muted)]">
            <div className="text-[1.1em]">Select a second text to begin comparison</div>
            <div className="text-[0.85em]">Choose from the dropdown above to load a comparison target.</div>
          </div>
        )}

        {activeProjectId && secondaryProjectId && !loading && jobStatus === 'idle' && alignmentRecords.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-[var(--color-text-muted)]">
            <div className="text-[1.1em]">Ready to align</div>
            <div className="text-[0.85em]">
              {activeMeta?.title} ({activeMeta?.paragraph_count} paragraphs) vs {secondaryMeta?.title} ({secondaryMeta?.paragraph_count} paragraphs)
            </div>
            <div className="text-[0.85em]">Select a method and click "Align" to compute pairwise alignment.</div>
          </div>
        )}

        {loading && (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 text-[var(--color-text-muted)]">
            <div className="w-32 h-2 bg-[var(--color-bg-muted)] rounded-full overflow-hidden">
              <div className="h-full bg-[var(--color-primary)] rounded-full animate-pulse" style={{ width: '60%' }} />
            </div>
            <div className="text-[0.85em]">Computing {activeMethod} alignment...</div>
          </div>
        )}

        {!loading && alignmentRecords.length > 0 && activeSubView === 'alignment' && (
          <AlignmentPlaceholder records={alignmentRecords} />
        )}

        {!loading && activeSubView !== 'alignment' && secondaryProjectId && (
          <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)] text-[0.85em]">
            {activeSubView.charAt(0).toUpperCase() + activeSubView.slice(1)} view — coming in Phase {
              activeSubView === 'dotplot' ? '4' : activeSubView === 'synteny' ? '5' : activeSubView === 'circos' ? '6' : '3'
            }
          </div>
        )}
      </div>
    </div>
  );
}

function AlignmentPlaceholder({ records }: { records: readonly { queryStart: number; queryEnd: number; targetStart: number; targetEnd: number; score: number; pValue: number; method: string }[] }) {
  return (
    <div className="flex-1 overflow-auto p-4">
      <div className="text-[0.85em] font-semibold mb-2">
        {records.length} aligned region{records.length !== 1 ? 's' : ''} found
      </div>
      <table className="w-full border-collapse text-[0.8em]">
        <thead className="sticky top-0 bg-[var(--color-bg-subtle)]">
          <tr className="text-left text-[var(--color-text-muted)]">
            <th className="px-3 py-1.5">#</th>
            <th className="px-3 py-1.5">Query Range</th>
            <th className="px-3 py-1.5">Target Range</th>
            <th className="px-3 py-1.5">Score</th>
            <th className="px-3 py-1.5">p-value</th>
            <th className="px-3 py-1.5">Method</th>
          </tr>
        </thead>
        <tbody>
          {records.slice(0, 100).map((r, i) => (
            <tr key={i} className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-muted)]">
              <td className="px-3 py-1.5 text-[var(--color-text-muted)]">{i + 1}</td>
              <td className="px-3 py-1.5 font-[var(--font-mono)]">¶{r.queryStart}–¶{r.queryEnd}</td>
              <td className="px-3 py-1.5 font-[var(--font-mono)]">¶{r.targetStart}–¶{r.targetEnd}</td>
              <td className="px-3 py-1.5 font-[var(--font-mono)]">{r.score.toFixed(3)}</td>
              <td className="px-3 py-1.5 font-[var(--font-mono)]">{r.pValue.toExponential(2)}</td>
              <td className="px-3 py-1.5">{r.method}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
