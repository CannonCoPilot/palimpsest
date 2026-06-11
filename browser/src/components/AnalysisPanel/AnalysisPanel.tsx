import { useEffect, useState, useCallback } from 'react';
import { useProjectStore } from '../../stores/projectStore';

interface TrackStatus {
  name: string;
  status: 'pending' | 'computed' | 'running' | 'failed';
  outputType: string;
  dependsOn: string[];
  evidenceLevel: string;
  hasManifest: boolean;
  lfoTypes: string[];
}

const STATUS_ICONS: Record<string, { icon: string; color: string; label: string }> = {
  computed: { icon: '✓', color: '#10b981', label: 'Computed' },
  pending: { icon: '○', color: '#6b7280', label: 'Not computed' },
  running: { icon: '⟳', color: '#3b82f6', label: 'Running...' },
  failed: { icon: '✕', color: '#ef4444', label: 'Failed' },
};

const TRACK_DESCRIPTIONS: Record<string, string> = {
  entities: 'Named entity recognition (spaCy)',
  sentiment: 'Sentence-level sentiment analysis',
  dialogue: 'Dialogue detection and attribution',
  coreference: 'Coreference chain resolution',
  sections: 'Section/chapter boundary detection',
  segments: 'Text segmentation into paragraphs',
  topics: 'Topic modeling (LDA)',
  lexical: 'Lexical richness and readability metrics',
  syntax: 'Syntactic complexity features',
  lithmm: 'Literary Hidden Markov Model states',
  compartments: 'A/B thematic compartments',
  self_similarity: 'Paragraph embedding similarity matrix',
};

export default function AnalysisPanel() {
  const projectId = useProjectStore((s) => s.metadata?.id);
  const [tracks, setTracks] = useState<TrackStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [pollingTracks, setPollingTracks] = useState<Set<string>>(new Set());

  const fetchStatus = useCallback(() => {
    if (!projectId) return;
    fetch(`/api/projects/${projectId}/analysis/status`)
      .then((r) => r.json())
      .then(setTracks)
      .catch(() => {});
  }, [projectId]);

  useEffect(() => {
    setLoading(true);
    fetchStatus();
    setLoading(false);
  }, [fetchStatus]);

  // Poll running tracks
  useEffect(() => {
    if (pollingTracks.size === 0) return;
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [pollingTracks.size, fetchStatus]);

  // Update polling set when status changes
  useEffect(() => {
    const running = new Set(tracks.filter((t) => t.status === 'running').map((t) => t.name));
    setPollingTracks(running);
  }, [tracks]);

  const handleRun = useCallback(async (trackName: string) => {
    if (!projectId) return;
    await fetch(`/api/projects/${projectId}/analyze/${trackName}`, { method: 'POST' });
    fetchStatus();
  }, [projectId, fetchStatus]);

  const handleRunAll = useCallback(async () => {
    if (!projectId) return;
    const pending = tracks.filter((t) => t.status === 'pending');
    for (const t of pending) {
      await fetch(`/api/projects/${projectId}/analyze/${t.name}`, { method: 'POST' });
    }
    fetchStatus();
  }, [projectId, tracks, fetchStatus]);

  const pendingCount = tracks.filter((t) => t.status === 'pending').length;
  const computedCount = tracks.filter((t) => t.status === 'computed').length;
  const runningCount = tracks.filter((t) => t.status === 'running').length;

  if (loading) {
    return <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">Loading analysis status...</div>;
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden font-[var(--font-sans)] text-[0.85em]">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)]">
        <div className="flex items-center gap-3">
          <span className="font-semibold">Track Analysis</span>
          <span className="text-[var(--color-text-muted)] text-[0.85em]">
            {computedCount} computed · {pendingCount} pending · {runningCount} running
          </span>
        </div>
        {pendingCount > 0 && (
          <button
            onClick={handleRunAll}
            className="px-3 py-1 rounded bg-[var(--color-primary)] text-white cursor-pointer hover:opacity-90 text-[0.85em]"
          >
            Compute All ({pendingCount})
          </button>
        )}
      </div>

      <div className="flex-1 overflow-auto">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 bg-[var(--color-bg-subtle)] z-10">
            <tr className="text-left text-[0.8em] text-[var(--color-text-muted)]">
              <th className="px-4 py-2 w-[30px]"></th>
              <th className="px-4 py-2">Track</th>
              <th className="px-4 py-2 w-[100px]">Type</th>
              <th className="px-4 py-2 w-[80px]">Evidence</th>
              <th className="px-4 py-2">Dependencies</th>
              <th className="px-4 py-2 w-[120px]"></th>
            </tr>
          </thead>
          <tbody>
            {tracks.map((track) => {
              const si = STATUS_ICONS[track.status] ?? STATUS_ICONS.pending;
              const deps = track.dependsOn.filter((d) => !d.startsWith('_'));
              const unmetDeps = deps.filter((d) => {
                const depTrack = tracks.find((t) => t.name === d);
                return !depTrack || depTrack.status !== 'computed';
              });

              return (
                <tr key={track.name} className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-muted)]">
                  <td className="px-4 py-2.5 text-center">
                    <span
                      style={{ color: si.color }}
                      className={track.status === 'running' ? 'animate-spin inline-block' : ''}
                      title={si.label}
                    >
                      {si.icon}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="font-medium">{track.name}</div>
                    <div className="text-[0.8em] text-[var(--color-text-muted)]">
                      {TRACK_DESCRIPTIONS[track.name] ?? track.lfoTypes.join(', ')}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="px-1.5 py-0.5 rounded text-[0.75em] bg-[var(--color-bg-muted)] border border-[var(--color-border-subtle)]">
                      {track.outputType}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-[0.85em] font-[var(--font-mono)]">{track.evidenceLevel}</td>
                  <td className="px-4 py-2.5">
                    {deps.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {deps.map((d) => {
                          const isUnmet = unmetDeps.includes(d);
                          return (
                            <span
                              key={d}
                              className="px-1 py-0.5 rounded text-[0.7em]"
                              style={{
                                backgroundColor: isUnmet ? '#fef3c7' : 'var(--color-bg-muted)',
                                color: isUnmet ? '#92400e' : 'var(--color-text-muted)',
                                border: `1px solid ${isUnmet ? '#fcd34d' : 'var(--color-border-subtle)'}`,
                              }}
                            >
                              {d}{isUnmet ? ' ⚠' : ''}
                            </span>
                          );
                        })}
                      </div>
                    ) : (
                      <span className="text-[var(--color-text-muted)] text-[0.8em]">none</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    {track.status === 'pending' && (
                      <button
                        onClick={() => handleRun(track.name)}
                        disabled={unmetDeps.length > 0}
                        className="px-2 py-1 rounded border border-[var(--color-primary)] text-[var(--color-primary)] cursor-pointer hover:bg-[var(--color-primary)] hover:text-white text-[0.8em] disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        Compute
                      </button>
                    )}
                    {track.status === 'computed' && (
                      <button
                        onClick={() => handleRun(track.name)}
                        className="px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em]"
                      >
                        Re-run
                      </button>
                    )}
                    {track.status === 'running' && (
                      <span className="text-[var(--color-primary)] text-[0.8em]">Running...</span>
                    )}
                    {track.status === 'failed' && (
                      <button
                        onClick={() => handleRun(track.name)}
                        className="px-2 py-1 rounded border border-[#ef4444] text-[#ef4444] cursor-pointer hover:bg-[#ef4444] hover:text-white text-[0.8em]"
                      >
                        Retry
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* Dependency graph */}
        {tracks.length > 0 && (
          <div className="px-4 py-3 border-t border-[var(--color-border)] bg-[var(--color-bg-subtle)]">
            <div className="font-semibold text-[0.85em] mb-2">Dependency Graph</div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[0.75em] font-[var(--font-mono)]">
              {tracks.filter((t) => t.dependsOn.filter((d) => !d.startsWith('_')).length > 0).map((t) => (
                <div key={t.name} className="text-[var(--color-text-muted)]">
                  {t.dependsOn.filter((d) => !d.startsWith('_')).join(' + ')} → <span className="text-[var(--color-text)]">{t.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
