import React, { useEffect, useState, useCallback } from 'react';
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

const TRACK_DETAILS: Record<string, { method: string; explanation: string }> = {
  entities: {
    method: 'spaCy en_core_web_lg NER pipeline',
    explanation: 'Identifies named entities (people, places, organizations) in the text using a pre-trained transformer model. Each entity is classified by type (PERSON, ORG, GPE, LOC) and assigned a confidence score based on the model\'s prediction probability.',
  },
  sentiment: {
    method: 'Sentence-level VADER sentiment + hedonometer valence',
    explanation: 'Computes sentiment polarity (-1 to +1) and arousal for each sentence using the VADER lexicon. The hedonometer valence score measures word-level happiness. Results are aggregated to paragraph level as mean, min, max, and volatility (standard deviation across sentences).',
  },
  dialogue: {
    method: 'Rule-based quotation detection + BookNLP speaker attribution',
    explanation: 'Detects quoted speech using quotation mark patterns, then attributes each quote to a speaker using BookNLP\'s coreference-aware attribution model. Non-dialogue paragraphs are classified as narration, description, or exposition.',
  },
  coreference: {
    method: 'BookNLP 2.0 coreference resolution',
    explanation: 'Groups mentions of the same entity into chains (e.g., "Dr. Jekyll", "the doctor", "he" all refer to the same person). Each mention is typed as proper noun (prop), common noun (nom), or pronoun (pron). Chain IDs link all co-referent mentions.',
  },
  sections: {
    method: 'Heading detection + TextTiling boundary segmentation',
    explanation: 'Identifies chapter/section boundaries by detecting heading patterns (capitalized lines, Roman numerals) and computing lexical cohesion shifts using the TextTiling algorithm. Each section gets a title extracted from the heading text.',
  },
  topics: {
    method: 'Latent Dirichlet Allocation (LDA) with TF-IDF',
    explanation: 'Discovers latent topic distributions across paragraphs using LDA. Each paragraph gets a probability distribution over K topics (default 10). Topic labels are derived from the top-weighted words. The dominant topic per paragraph is assigned as the annotation.',
  },
  lexical: {
    method: 'Type-token ratio, hapax ratio, Flesch-Kincaid, word frequency',
    explanation: 'Measures vocabulary richness per paragraph: type-token ratio (unique/total words), hapax legomena ratio (words appearing once), mean word length, sentence length distribution, and Flesch-Kincaid readability grade. Z-scored across the document.',
  },
  syntax: {
    method: 'Dependency parse tree depth + clause count + POS distribution',
    explanation: 'Analyzes syntactic complexity using spaCy dependency parsing. Measures: mean parse tree depth, subordinate clause count, noun/verb/adjective ratios, passive voice frequency, and sentence type distribution (simple/compound/complex).',
  },
  lithmm: {
    method: 'Gaussian Hidden Markov Model over 6 literary features',
    explanation: 'Fits an HMM to the paragraph-level feature vectors (sentiment, lexical richness, dialogue ratio, entity density, topic entropy, syntactic complexity). Each paragraph is assigned to a hidden state representing a distinct "writing mode" (e.g., action, reflection, dialogue). State descriptions are auto-generated from feature z-scores.',
  },
  compartments: {
    method: 'Eigenvector decomposition of self-similarity matrix',
    explanation: 'Analogous to A/B compartments in Hi-C genomics. Computes the first eigenvector of the self-similarity correlation matrix. Positive values = compartment A (one thematic mode), negative = compartment B (the other). Reveals large-scale thematic bipartition of the text.',
  },
  self_similarity: {
    method: 'Cosine similarity of paragraph embeddings (Qwen3-Embedding-4B)',
    explanation: 'Each paragraph is embedded into a 2560-dimensional vector using the Qwen3-Embedding model. The NxN similarity matrix is computed as the dot product of L2-normalized vectors (cosine similarity). Values range 0-1 where 1 = semantically identical. The diagonal is always 1. Off-diagonal bright spots reveal parallel passages, echoes, and thematic recurrences.',
  },
  narrative_arc: {
    method: 'Sliding window smoothing of sentiment + tension features',
    explanation: 'Computes a smoothed narrative arc signal by applying a Gaussian window to sentence-level sentiment and tension scores. Reveals the story\'s emotional trajectory — rising action, climax, resolution — as a continuous curve.',
  },
  rqa: {
    method: 'Recurrence Quantification Analysis of embedding sequences',
    explanation: 'Constructs a recurrence plot from paragraph embeddings and computes RQA metrics: recurrence rate (how often the text returns to similar themes), determinism (predictability of transitions), entropy (complexity of recurrence patterns), and laminarity (tendency to stay in the same state).',
  },
  alphabet: {
    method: 'Foldseek-inspired narrative alphabet encoding',
    explanation: 'Encodes each paragraph as a letter from a structural alphabet based on its feature profile (like Foldseek encodes protein structure). The resulting "narrative sequence" can be aligned between texts to find structural homology — texts with similar dramatic arcs share similar alphabet strings.',
  },
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

  const [expandedTrack, setExpandedTrack] = useState<string | null>(null);
  const [trackStats, setTrackStats] = useState<Record<string, { count: number }>>({});

  useEffect(() => {
    if (!projectId) return;
    fetch(`/api/projects/${projectId}/tracks`)
      .then((r) => r.json())
      .then((trackNames: string[]) => {
        const stats: Record<string, { count: number }> = {};
        const promises = trackNames.map((name) =>
          fetch(`/data/${projectId}/tracks/${name}.jsonl`)
            .then((r) => r.text())
            .then((text) => { stats[name] = { count: text.trim().split('\n').filter(Boolean).length }; })
            .catch(() => {})
        );
        Promise.all(promises).then(() => setTrackStats(stats));
      })
      .catch(() => {});
  }, [projectId]);

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

              return (<React.Fragment key={track.name}>
                <tr className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-muted)]">
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
                    <button
                      onClick={() => setExpandedTrack(expandedTrack === track.name ? null : track.name)}
                      className="ml-1 px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em]"
                    >
                      {expandedTrack === track.name ? 'Hide' : 'Details'}
                    </button>
                  </td>
                </tr>
                {expandedTrack === track.name && (
                  <tr className="bg-[var(--color-bg)]">
                    <td colSpan={6} className="px-4 py-3">
                      <div className="border border-[var(--color-border-subtle)] rounded p-3 bg-[var(--color-bg-subtle)]">
                        <div className="grid grid-cols-[120px_1fr] gap-y-2 text-[0.85em]">
                          <span className="text-[var(--color-text-muted)] font-semibold">Method</span>
                          <span>{TRACK_DETAILS[track.name]?.method ?? 'N/A'}</span>
                          <span className="text-[var(--color-text-muted)] font-semibold">How it works</span>
                          <span>{TRACK_DETAILS[track.name]?.explanation ?? 'No detailed description available.'}</span>
                          <span className="text-[var(--color-text-muted)] font-semibold">Output type</span>
                          <span>{track.outputType === 'annotation' ? 'JSONL annotations (W3C Web Annotation)' : 'Binary signal matrix + JSON manifest'}</span>
                          <span className="text-[var(--color-text-muted)] font-semibold">Evidence level</span>
                          <span>{track.evidenceLevel} — {track.evidenceLevel === 'E5' ? 'Deterministic algorithm' : track.evidenceLevel === 'E4' ? 'Statistical/ML model' : 'Other'}</span>
                          {trackStats[track.name] && (
                            <>
                              <span className="text-[var(--color-text-muted)] font-semibold">Annotations</span>
                              <span>{trackStats[track.name].count.toLocaleString()} annotations in this project</span>
                            </>
                          )}
                          {track.dependsOn.filter((d) => !d.startsWith('_')).length > 0 && (
                            <>
                              <span className="text-[var(--color-text-muted)] font-semibold">Requires</span>
                              <span>{track.dependsOn.filter((d) => !d.startsWith('_')).join(', ')}</span>
                            </>
                          )}
                          <span className="text-[var(--color-text-muted)] font-semibold">LFO types</span>
                          <span className="font-[var(--font-mono)] text-[0.9em]">{track.lfoTypes.join(', ')}</span>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>);
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
