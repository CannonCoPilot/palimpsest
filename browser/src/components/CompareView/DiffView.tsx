/**
 * DiffView — edition comparison with color-coded inline changes.
 * Shows paragraph-level diff between two versions of a text.
 */

import { useEffect } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useComparisonStore } from '../../stores/comparisonStore';

const CHANGE_COLORS: Record<string, { bg: string; border: string; label: string }> = {
  replace: { bg: '#fef3c7', border: '#f59e0b', label: 'Changed' },
  insert: { bg: '#d1fae5', border: '#10b981', label: 'Added' },
  delete: { bg: '#fee2e2', border: '#ef4444', label: 'Removed' },
};

export default function DiffView() {
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const secondaryProjectId = useProjectStore((s) => s.secondaryProjectId);
  const diffRecords = useComparisonStore((s) => s.diffRecords);
  const diffSummary = useComparisonStore((s) => s.diffSummary);
  const runDiff = useComparisonStore((s) => s.runDiff);
  const loading = useComparisonStore((s) => s.loading);
  const diffError = useComparisonStore((s) => s.diffError);

  useEffect(() => {
    if (activeProjectId && secondaryProjectId && diffRecords.length === 0 && !loading && !diffError) {
      runDiff(activeProjectId, secondaryProjectId);
    }
  }, [activeProjectId, secondaryProjectId, diffRecords.length, loading, diffError, runDiff]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)] text-[0.85em]">
        Computing diff...
      </div>
    );
  }

  if (diffError && diffRecords.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-2 text-[0.85em]">
        <div className="text-[var(--color-danger)]">Diff failed: {diffError}</div>
        <button
          onClick={() => {
            if (activeProjectId && secondaryProjectId) {
              runDiff(activeProjectId, secondaryProjectId);
            }
          }}
          className="px-3 py-1 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-subtle)] text-[var(--color-text-muted)]"
        >
          Retry
        </button>
      </div>
    );
  }

  if (diffRecords.length === 0 && !diffSummary) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)] text-[0.85em]">
        No diff results available.
      </div>
    );
  }

  const changeRecords = diffRecords.filter((r) => r.changeType !== 'equal');

  return (
    <div className="flex-1 flex flex-col overflow-hidden font-[var(--font-sans)] text-[0.85em]">
      {/* Summary bar */}
      {diffSummary && (
        <div className="flex items-center gap-4 px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)]">
          <span className="font-semibold">Edition Diff</span>
          <span className="text-[var(--color-text-muted)]">
            {diffSummary.totalParagraphsA} vs {diffSummary.totalParagraphsB} paragraphs
          </span>
          <div className="flex items-center gap-3 ml-auto text-[0.85em]">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#d1fae5', border: '1px solid #10b981' }} />
              {diffSummary.insertions} added
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#fee2e2', border: '1px solid #ef4444' }} />
              {diffSummary.deletions} removed
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: '#fef3c7', border: '1px solid #f59e0b' }} />
              {diffSummary.replacements} changed
            </span>
            <span className="text-[var(--color-text-muted)]">{diffSummary.unchanged} unchanged</span>
          </div>
        </div>
      )}

      {/* Diff records */}
      <div className="flex-1 overflow-auto">
        {changeRecords.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-[var(--color-text-muted)]">
            Texts are identical at paragraph level.
          </div>
        ) : (
          changeRecords.map((r, i) => {
            const style = CHANGE_COLORS[r.changeType] ?? CHANGE_COLORS.replace;
            return (
              <div
                key={i}
                className="px-4 py-2 border-b border-[var(--color-border-subtle)]"
                style={{ borderLeft: `4px solid ${style.border}` }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="px-1.5 py-0.5 rounded text-[0.75em] font-semibold"
                    style={{ backgroundColor: style.bg, color: style.border }}
                  >
                    {style.label}
                  </span>
                  {r.paraIndexA >= 0 && (
                    <span className="text-[var(--color-text-muted)] text-[0.8em] font-[var(--font-mono)]">
                      A:¶{r.paraIndexA}
                    </span>
                  )}
                  {r.paraIndexB >= 0 && (
                    <span className="text-[var(--color-text-muted)] text-[0.8em] font-[var(--font-mono)]">
                      B:¶{r.paraIndexB}
                    </span>
                  )}
                </div>
                {r.changeType === 'replace' && (
                  <div className="grid grid-cols-2 gap-2 text-[0.85em]">
                    <div className="p-2 rounded bg-[#fee2e2] font-[var(--font-serif)]">{r.textA}</div>
                    <div className="p-2 rounded bg-[#d1fae5] font-[var(--font-serif)]">{r.textB}</div>
                  </div>
                )}
                {r.changeType === 'delete' && (
                  <div className="p-2 rounded bg-[#fee2e2] text-[0.85em] font-[var(--font-serif)]">{r.textA}</div>
                )}
                {r.changeType === 'insert' && (
                  <div className="p-2 rounded bg-[#d1fae5] text-[0.85em] font-[var(--font-serif)]">{r.textB}</div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
