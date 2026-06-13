/**
 * CompareView — container for two-text comparison sub-views.
 * Sub-nav selects: Alignment | Dotplot | Synteny | Circos | Diff
 */

import { useEffect, useState, useCallback } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useComparisonStore, type CompareSubView } from '../../stores/comparisonStore';
import AlignmentView from './AlignmentView';
import ComparativeDotplot from './ComparativeDotplot';
import SyntenyView from './SyntenyView';
import CircosView from './CircosView';
import DiffView from './DiffView';

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
  const [fetchError, setFetchError] = useState(false);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);

  useEffect(() => {
    setFetchError(false);
    fetch('/api/projects')
      .then((r) => r.json())
      .then((data: ProjectOption[]) => setProjects(data.filter((p) => p.id !== activeProjectId)))
      .catch(() => setFetchError(true));
  }, [activeProjectId]);

  if (fetchError) {
    return <span className="text-[var(--color-danger)] text-[0.85em]">Failed to load projects</span>;
  }

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
  const loadSecondary = useProjectStore((s) => s.loadSecondaryProject);
  const loading = useComparisonStore((s) => s.loading);
  const error = useComparisonStore((s) => s.error);
  const alignmentRecords = useComparisonStore((s) => s.alignmentRecords);
  const activeMethod = useComparisonStore((s) => s.activeMethod);
  const setActiveMethod = useComparisonStore((s) => s.setActiveMethod);
  const runAlignment = useComparisonStore((s) => s.runAlignment);
  const jobStatus = useComparisonStore((s) => s.jobStatus);

  const handleSelectSecondary = useCallback(async (id: string) => {
    await loadSecondary('', id);
  }, [loadSecondary]);

  const handleRunAlignment = useCallback(() => {
    if (activeProjectId && secondaryProjectId) {
      runAlignment(activeProjectId, secondaryProjectId, activeMethod);
    }
  }, [activeProjectId, secondaryProjectId, activeMethod, runAlignment]);

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
        <div role="tablist" aria-label="Comparison sub-views" className="flex gap-0 border-b border-[var(--color-border)] bg-[var(--color-bg)] text-[0.8em]">
          {SUB_VIEWS.map((sv) => (
            <button
              key={sv.id}
              role="tab"
              aria-selected={activeSubView === sv.id}
              aria-controls={`compare-panel-${sv.id}`}
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
      <div
        id={`compare-panel-${activeSubView}`}
        role="tabpanel"
        className="flex-1 overflow-hidden flex flex-col"
      >
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
              <div
                className="h-full rounded-full animate-[shimmer_1.5s_ease-in-out_infinite]"
                style={{
                  width: '100%',
                  background: 'linear-gradient(90deg, var(--color-primary) 0%, var(--color-primary-light, #93c5fd) 50%, var(--color-primary) 100%)',
                  backgroundSize: '200% 100%',
                }}
              />
            </div>
            <div className="text-[0.85em]">Computing {activeMethod} alignment...</div>
          </div>
        )}

        {!loading && alignmentRecords.length > 0 && activeSubView === 'alignment' && (
          <AlignmentView />
        )}

        {!loading && activeSubView === 'dotplot' && secondaryProjectId && (
          <ComparativeDotplot />
        )}
        {!loading && activeSubView === 'synteny' && secondaryProjectId && (
          <SyntenyView />
        )}
        {!loading && activeSubView === 'circos' && secondaryProjectId && (
          <CircosView />
        )}
        {!loading && activeSubView === 'diff' && secondaryProjectId && (
          <DiffView />
        )}
      </div>
    </div>
  );
}
