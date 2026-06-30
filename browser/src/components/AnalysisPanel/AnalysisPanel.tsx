import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useProjectStore, getActiveProject } from '../../stores/projectStore';
import { useMaskOverlayStore } from '../../stores/maskOverlayStore';
import { collectLayers, laneKind, type LayerStatus } from './layers/types';
import { LayerWorkbench } from './layers/LayerWorkbench';
import { ProfileDashboard } from './layers/ProfileDashboard';
import { EmbeddingScatter } from './layers/EmbeddingScatter';
import { IntegrityBadge } from './layers/IntegrityBadge';

/**
 * Build the fetch init for an analyze run from the on-demand masking overlay. When the
 * overlay matches the saved layout (enabled, no overrides) no body is sent and the run is
 * unchanged; otherwise the override is posted and the run is forced (it changes the masked
 * set, so cached results must not be reused).
 */
function maskOverrideInit(): { init: RequestInit; override: boolean } {
  const { enabled, maskVerseNumbers, typeOverrides, sectionOverrides } = useMaskOverlayStore.getState();
  const hasOverrides =
    Object.keys(typeOverrides).length > 0 || Object.keys(sectionOverrides).length > 0;
  // Defaults (enabled, verse-masking on, no per-type/element overrides) match the saved layout, so
  // no body is sent. Turning verse masking off changes the masked set, so it forces an override run.
  if (enabled && maskVerseNumbers && !hasOverrides) return { init: { method: 'POST' }, override: false };
  return {
    init: {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mask_override: {
          enabled,
          mask_verse_numbers: maskVerseNumbers,
          mask_by_type: typeOverrides,
          section_masked: sectionOverrides,
        },
      }),
    },
    override: true,
  };
}

function analyzeQuery(params: Record<string, string | number> | undefined, force: boolean): string {
  const obj: Record<string, string> = {};
  for (const [k, v] of Object.entries(params ?? {})) obj[k] = String(v);
  if (force) obj.force = 'true';
  const qs = new URLSearchParams(obj).toString();
  return qs ? `?${qs}` : '';
}

interface TrackStatus {
  name: string;
  status: 'pending' | 'computed' | 'running' | 'failed';
  outputType: string;
  dependsOn: string[];
  evidenceLevel: string;
  hasManifest: boolean;
  lfoTypes: string[];
  // Present only on a failed run — the real error message from the backend (B2/G5). Rendered so the
  // user is told why a run failed instead of a silent revert to "pending".
  error?: string;
  // §5 consumption honesty: per-run provenance the data layer recorded but the UI couldn't see.
  // `clamped`/`effective`/`requested` expose record-effective clamps (e.g. n_topics ran 10, requested
  // 25). `method`/`posteriorType` (lithmm only) expose the silent GaussianHMM→KMeans fallback (B5).
  runInfo?: {
    clamped?: string[];
    effective?: Record<string, number | null>;
    requested?: Record<string, number | null>;
    method?: string;
    posteriorType?: string;
  };
  // FR-13: plural layers this track produced (label-keyed tracks only — chunking, repeat_mask,
  // repeat, embedding). Already emitted by /analysis/status (server.py:1025); the suite's Explore /
  // Representations tabs render these via each layer's `rendering` descriptor.
  layers?: LayerStatus[];
}

type SubTab = 'tracks' | 'profile' | 'representations' | 'explore';

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
  self_similarity: 'Self-similarity matrix over bound layers — cosine/jaccard (embedding) + word_overlap/edit_distance (text-only)',
  boundary_detection: 'HMM Viterbi domain boundary detection (multi-metric)',
};

const TRACK_DETAILS: Record<string, { method: string; explanation: string }> = {
  entities: {
    method: 'spaCy en_core_web_lg NER pipeline',
    explanation: 'Identifies named entities (people, places, organizations) in the text using a pre-trained transformer model. Each entity is classified by type (PERSON, ORG, GPE, LOC) and assigned a confidence score based on the model\'s prediction probability.',
  },
  sentiment: {
    method: 'VADER sentiment per sentence or paragraph',
    explanation: 'Computes sentiment polarity (-1 to +1) and arousal for each unit using the VADER lexicon. The Granularity knob selects the scoring unit — each sentence (default) or each whole paragraph.',
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
    method: 'Multi-metric self-similarity (4 metrics computed simultaneously)',
    explanation: 'Computes four complementary similarity matrices:\n\n' +
      '• Cosine (paragraph-level): Each paragraph is embedded into a 2560-dim vector via Qwen3-Embedding. Matrix = dot product of L2-normalized vectors. Captures semantic similarity — passages about the same topic score high even with different wording.\n\n' +
      '• Jaccard (paragraph-level): Binarizes embedding dimensions (positive = 1, else 0), computes set intersection/union. A coarser semantic signal that emphasizes shared feature activation patterns.\n\n' +
      '• Word overlap (sentence-level): Jaccard similarity on content-word token sets with stopword removal. Finds sentences sharing actual vocabulary — formulaic phrases, repeated instructions, parallel constructions. Operates at sentence granularity for precision.\n\n' +
      '• Edit distance (sentence-level): Normalized token-level Levenshtein distance on content words. Finds near-duplicate sentences and textual variants — passages that differ by only a few words. Also sentence-level with stopword removal.',
  },
  narrative_arc: {
    method: 'Sliding window smoothing of sentiment + tension features',
    explanation: 'Computes a smoothed narrative arc signal by applying a Gaussian window to sentence-level sentiment and tension scores. Reveals the story\'s emotional trajectory — rising action, climax, resolution — as a continuous curve.',
  },
  rqa: {
    method: 'Recurrence Quantification Analysis of embedding sequences',
    explanation: 'Constructs a recurrence plot from paragraph embeddings and computes RQA metrics: recurrence rate (how often the text returns to similar themes), determinism (predictability of transitions), entropy (complexity of recurrence patterns), and laminarity (tendency to stay in the same state).',
  },
  boundary_detection: {
    method: 'HMM Viterbi over aggregated directionality index + insulation score',
    explanation: 'Aggregates self-similarity evidence from all computed metrics (cosine, jaccard, word overlap, edit distance) across all computed window sizes. For each metric/size combination, computes a directionality index (upstream vs downstream similarity bias) and an insulation score (local diagonal block density). These signals are fed into a 3-state Hidden Markov Model (inside-domain, boundary, transition) solved via the Viterbi algorithm. Domains are contiguous "boxes" of internally similar text; boundaries are the "stripes" of low similarity between them. More metrics and window sizes = more robust boundaries.',
  },
  alphabet: {
    method: 'Foldseek-inspired narrative alphabet encoding',
    explanation: 'Encodes each paragraph as a letter from a structural alphabet based on its feature profile (like Foldseek encodes protein structure). The resulting "narrative sequence" can be aligned between texts to find structural homology — texts with similar dramatic arcs share similar alphabet strings.',
  },
};

interface TrackParam {
  key: string;
  label: string;
  type: 'number' | 'select';
  default: number | string;
  options?: { label: string; value: string }[];
  min?: number;
  max?: number;
}

const TRACK_PARAMS: Record<string, TrackParam[]> = {
  lithmm: [
    // Default matches the backend's DEFAULT_N_STATES (10) so the interactive default and the
    // batch/manifest default don't diverge.
    { key: 'n_states', label: 'Number of states', type: 'number', default: 10, min: 2, max: 20 },
  ],
  topics: [
    { key: 'n_topics', label: 'Number of topics', type: 'number', default: 10, min: 2, max: 50 },
    { key: 'method', label: 'Method', type: 'select', default: 'lda', options: [
      { label: 'LDA', value: 'lda' }, { label: 'NMF', value: 'nmf' },
    ]},
  ],
  // self_similarity has no generic params — it is configured by SelfSimilarityParamDialog, the
  // layer-picker that builds the explicit {chunk, repeat_mask, embedding?} bundles + metric selection.
  self_similarity: [],
  sentiment: [
    // Only VADER is implemented; Hedonometer is not offered until its scoring path exists (P5:
    // don't advertise a value the backend rejects).
    { key: 'method', label: 'Method', type: 'select', default: 'vader', options: [
      { label: 'VADER', value: 'vader' },
    ]},
    { key: 'granularity', label: 'Granularity', type: 'select', default: 'sentence', options: [
      { label: 'Sentence', value: 'sentence' }, { label: 'Paragraph', value: 'paragraph' },
    ]},
  ],
};

interface SsLayerView {
  label: string;
  capability?: Record<string, unknown>;
  stats?: Record<string, unknown> | null;
}
interface SsChunkLayer extends SsLayerView {
  size: number | null;
  bundle_ready: boolean;
  repeat_masks: SsLayerView[];
  embeddings: SsLayerView[];
}
interface SsMethod { name: string; requires_embedding: boolean; }
interface SsIncompatible { kind: string; label: string; reason: string; }
interface SelfSimInputs {
  consumer: string;
  chunk_layers: SsChunkLayer[];
  methods: SsMethod[];
  incompatible: SsIncompatible[];
}
interface BundlePick { include: boolean; repeatMask: string; embedding: string; }

const capStr = (c: Record<string, unknown> | undefined | null, k: string): string =>
  c && c[k] != null ? String(c[k]) : '';

// The self_similarity consumer binds layers by explicit label (one {chunk, repeat_mask, embedding?}
// bundle per chunk size). This dialog is a *picker* over the server-validated discovery endpoint
// (GET …/self_similarity/inputs): the backend pre-groups each chunk layer's coherent repeat_masks /
// embeddings, so the UI never reconstructs binding rules — it just lets the user choose and emits the
// `inputs` JSON. It never chunks or embeds; producing a layer is a separate track run.
function SelfSimilarityParamDialog({ onRun, onCancel, projectId }: {
  onRun: (params: Record<string, string | number>) => void;
  onCancel: () => void;
  projectId: string | undefined;
}) {
  const [data, setData] = useState<SelfSimInputs | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [methodOn, setMethodOn] = useState<Record<string, boolean>>({});
  const [pick, setPick] = useState<Record<string, BundlePick>>({});

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    fetch(`/api/projects/${projectId}/self_similarity/inputs`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d: SelfSimInputs) => {
        if (cancelled) return;
        setData(d);
        setMethodOn(Object.fromEntries(d.methods.map((m) => [m.name, true])));
        // Pre-pick the sole repeat_mask/embedding when a chunk layer has exactly one (the common
        // case), so a single-layer project is one checkbox from a valid run. Nothing is *included*
        // by default — the user opts each chunk size into the run explicitly.
        const seeded: Record<string, BundlePick> = {};
        for (const cl of d.chunk_layers) {
          seeded[cl.label] = {
            include: false,
            repeatMask: cl.repeat_masks.length === 1 ? cl.repeat_masks[0].label : '',
            embedding: cl.embeddings.length === 1 ? cl.embeddings[0].label : '',
          };
        }
        setPick(seeded);
      })
      .catch((e) => { if (!cancelled) setLoadError(String(e)); });
    return () => { cancelled = true; };
  }, [projectId]);

  const methods = data?.methods ?? [];
  const chunkLayers = data?.chunk_layers ?? [];
  const incompatible = data?.incompatible ?? [];
  const enabledMetrics = methods.filter((m) => methodOn[m.name]).map((m) => m.name);
  // Embedding is needed exactly when a selected metric declares requires_embedding — the same
  // single source (the endpoint's method registry) the backend validates against.
  const needsEmbedding = methods.some((m) => methodOn[m.name] && m.requires_embedding);

  const setPickFor = (label: string, patch: Partial<BundlePick>) =>
    setPick((prev) => ({ ...prev, [label]: { ...prev[label], ...patch } }));

  const included = chunkLayers.filter((cl) => pick[cl.label]?.include);
  const rowReady = (cl: SsChunkLayer): boolean => {
    const p = pick[cl.label];
    return !!p && !!p.repeatMask && (!needsEmbedding || !!p.embedding);
  };
  const canRun = enabledMetrics.length > 0 && included.length > 0 && included.every(rowReady);

  const handleRun = () => {
    if (!canRun) return;
    const inputs = included.map((cl) => {
      const p = pick[cl.label];
      const bundle: Record<string, string> = {
        chunk_label: cl.label, repeat_mask_label: p.repeatMask,
      };
      if (needsEmbedding) bundle.embedding_label = p.embedding;
      return bundle;
    });
    onRun({ metrics: enabledMetrics.join(','), inputs: JSON.stringify(inputs) });
  };

  return (
    <div className="border border-[var(--color-border)] rounded p-3 bg-[var(--color-bg)] mt-1 text-[0.85em]">
      <div className="font-semibold mb-2">Self-Similarity Inputs</div>
      <div className="text-[0.78em] text-[var(--color-text-muted)] mb-3">
        Bind existing layers — one chunk size per bundle. Produce chunk, repeat_mask
        {needsEmbedding ? ' and embedding' : ''} layers from their own tracks first; this consumer
        never chunks or embeds on its own.
      </div>

      {loadError && (
        <div className="text-[0.78em] text-[var(--color-warning,#b45309)] mb-2">
          Could not load layers: {loadError}
        </div>
      )}
      {!data && !loadError && (
        <div className="text-[0.8em] text-[var(--color-text-muted)] mb-2">Loading layers…</div>
      )}

      {data && (
        <>
          <div className="mb-3">
            <div className="font-medium mb-1.5">Metrics</div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1">
              {methods.map((m) => (
                <label key={m.name} className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" checked={!!methodOn[m.name]}
                    onChange={(e) => setMethodOn({ ...methodOn, [m.name]: e.target.checked })}
                    className="accent-[var(--color-primary)]" />
                  <span className={methodOn[m.name] ? 'font-medium' : 'text-[var(--color-text-muted)]'}>{m.name}</span>
                  {m.requires_embedding && (
                    <span className="text-[0.7em] text-[var(--color-text-muted)]">(needs embedding)</span>
                  )}
                </label>
              ))}
            </div>
          </div>

          <div className="mb-3 border-t border-[var(--color-border)] pt-2">
            <div className="font-medium mb-1.5">Chunk layers (one bundle per size)</div>
            {chunkLayers.length === 0 && (
              <div className="text-[0.8em] text-[var(--color-text-muted)]">
                No chunk layers yet. Run a chunking track, then a repeat_mask track on it.
              </div>
            )}
            <div className="flex flex-col gap-2">
              {chunkLayers.map((cl) => {
                const p = pick[cl.label];
                const sizeLabel = cl.size != null ? `${cl.size}` : cl.label.slice(0, 8);
                const count = capStr(cl.stats, 'count');
                return (
                  <div key={cl.label} className="border border-[var(--color-border)] rounded px-2 py-1.5">
                    <label className={`flex items-center gap-2 ${cl.bundle_ready ? 'cursor-pointer' : 'opacity-60'}`}>
                      <input type="checkbox" disabled={!cl.bundle_ready} checked={!!p?.include}
                        onChange={(e) => setPickFor(cl.label, { include: e.target.checked })}
                        className="accent-[var(--color-primary)]" />
                      <span className="font-medium">size {sizeLabel}</span>
                      <span className="text-[0.78em] text-[var(--color-text-muted)]">
                        {capStr(cl.capability, 'mode')}{count ? ` · ${count} chunks` : ''}
                      </span>
                    </label>

                    {!cl.bundle_ready && (
                      <div className="text-[0.72em] text-[var(--color-text-muted)] mt-1 ml-6">
                        No repeat_mask layer for this chunk — run a repeat_mask track on it first.
                      </div>
                    )}

                    {cl.bundle_ready && p?.include && (
                      <div className="grid grid-cols-[7rem_1fr] gap-x-2 gap-y-1.5 items-center mt-1.5 ml-6">
                        <span className="text-[var(--color-text-muted)]">repeat_mask</span>
                        <select value={p.repeatMask}
                          onChange={(e) => setPickFor(cl.label, { repeatMask: e.target.value })}
                          className="px-1 py-0.5 border border-[var(--color-border)] rounded bg-[var(--color-bg)]">
                          <option value="">— select —</option>
                          {cl.repeat_masks.map((rm) => (
                            <option key={rm.label} value={rm.label}>
                              {rm.label.slice(0, 14)}
                              {capStr(rm.stats, 'masked_count') ? ` (${capStr(rm.stats, 'masked_count')} masked)` : ''}
                            </option>
                          ))}
                        </select>

                        {needsEmbedding && (
                          <>
                            <span className="text-[var(--color-text-muted)]">embedding</span>
                            {cl.embeddings.length === 0 ? (
                              <span className="text-[0.75em] text-[var(--color-warning,#b45309)]">
                                none — run an embedding track on this chunk, or deselect cosine/jaccard
                              </span>
                            ) : (
                              <select value={p.embedding}
                                onChange={(e) => setPickFor(cl.label, { embedding: e.target.value })}
                                className="px-1 py-0.5 border border-[var(--color-border)] rounded bg-[var(--color-bg)]">
                                <option value="">— select —</option>
                                {cl.embeddings.map((em) => (
                                  <option key={em.label} value={em.label}>
                                    {capStr(em.capability, 'model') || em.label.slice(0, 12)}
                                    {capStr(em.capability, 'dim') ? ` · d${capStr(em.capability, 'dim')}` : ''}
                                  </option>
                                ))}
                              </select>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {incompatible.length > 0 && (
            <div className="mb-3 text-[0.72em] text-[var(--color-text-muted)]">
              <div className="font-medium mb-0.5">Not bindable ({incompatible.length})</div>
              {incompatible.map((inc, i) => (
                <div key={i}>• {inc.kind} <code>{inc.label.slice(0, 12)}</code>: {inc.reason}</div>
              ))}
            </div>
          )}
        </>
      )}

      <div className="flex gap-2">
        <button onClick={handleRun} disabled={!canRun} className="px-2 py-1 rounded bg-[var(--color-primary)] text-white cursor-pointer hover:opacity-90 text-[0.8em] disabled:opacity-40 disabled:cursor-not-allowed">Run Selected</button>
        <button onClick={onCancel} className="px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em]">Cancel</button>
      </div>
    </div>
  );
}

function ParamDialog({ trackName, onRun, onCancel }: { trackName: string; onRun: (params: Record<string, string | number>) => void; onCancel: () => void }) {
  const params = TRACK_PARAMS[trackName] ?? [];
  const [values, setValues] = useState<Record<string, string | number>>(() => {
    const init: Record<string, string | number> = {};
    for (const p of params) init[p.key] = p.default;
    return init;
  });

  return (
    <div className="border border-[var(--color-border)] rounded p-3 bg-[var(--color-bg)] mt-1 text-[0.85em]">
      <div className="font-semibold mb-2">Re-run {trackName} with parameters</div>
      <div className="flex flex-col gap-2 mb-3">
        {params.map((p) => (
          <label key={p.key} className="flex items-center gap-2">
            <span className="w-[140px] text-[var(--color-text-muted)]">{p.label}</span>
            {p.type === 'number' ? (
              <input
                type="number"
                value={values[p.key]}
                min={p.min}
                max={p.max}
                onChange={(e) => setValues({ ...values, [p.key]: parseInt(e.target.value, 10) || p.default })}
                className="w-16 px-1 py-0.5 border border-[var(--color-border)] rounded text-center"
              />
            ) : (
              <select
                value={values[p.key]}
                onChange={(e) => setValues({ ...values, [p.key]: e.target.value })}
                className="px-1 py-0.5 border border-[var(--color-border)] rounded bg-[var(--color-bg)] cursor-pointer"
              >
                {p.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            )}
          </label>
        ))}
      </div>
      <div className="flex gap-2">
        <button onClick={() => onRun(values)} className="px-2 py-1 rounded bg-[var(--color-primary)] text-white cursor-pointer hover:opacity-90 text-[0.8em]">Run</button>
        <button onClick={onCancel} className="px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em]">Cancel</button>
      </div>
    </div>
  );
}

// Tracks that auto-consume the legacy paragraph-embedding cache (/embeddings/compute → cache/embeddings.db).
// self_similarity is deliberately EXCLUDED post-P7: it binds explicit embedding *layers* via its
// layer-picker (only for metrics that require them), so forcing the paragraph cache here would both
// block text-only runs (word_overlap/edit_distance) and compute the wrong embedding family.
const EMBEDDING_DEPENDENT_TRACKS = new Set(['compartments', 'rqa', 'alphabet']);

function EmbeddingDialog({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg p-5 shadow-lg max-w-[420px]">
        <div className="font-semibold text-[1em] mb-2">Embeddings Required</div>
        <div className="text-[0.85em] text-[var(--color-text-muted)] mb-4">
          This track requires paragraph embeddings, which have not been computed yet for this text.
          Embeddings will be generated using the available embedding service (MLX or Ollama).
          This typically takes 10–30 seconds.
        </div>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.85em]"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-3 py-1.5 rounded bg-[var(--color-primary)] text-white cursor-pointer hover:opacity-90 text-[0.85em]"
          >
            Compute Embeddings
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AnalysisPanel() {
  const projectId = useProjectStore((s) => getActiveProject(s).metadata?.id);
  const [tracks, setTracks] = useState<TrackStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [pollingTracks, setPollingTracks] = useState<Set<string>>(new Set());
  const [paramDialogTrack, setParamDialogTrack] = useState<string | null>(null);
  const [embeddingDialog, setEmbeddingDialog] = useState<{ trackName: string; params?: Record<string, string | number> } | null>(null);
  const [embeddingStatus, setEmbeddingStatus] = useState<'unknown' | 'available' | 'missing' | 'computing'>('unknown');
  const [subTab, setSubTab] = useState<SubTab>('tracks');

  const fetchStatus = useCallback(async () => {
    if (!projectId) return;
    try {
      const r = await fetch(`/api/projects/${projectId}/analysis/status`);
      const data = await r.json();
      setTracks(data);
    } catch { /* swallow */ }
  }, [projectId]);

  const checkEmbeddings = useCallback(async (): Promise<boolean> => {
    if (!projectId) return false;
    try {
      const r = await fetch(`/api/projects/${projectId}/embeddings/status`);
      const data = await r.json();
      setEmbeddingStatus(data.available ? 'available' : 'missing');
      return data.available;
    } catch {
      return false;
    }
  }, [projectId]);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchStatus(), checkEmbeddings()]).finally(() => setLoading(false));
  }, [fetchStatus, checkEmbeddings]);

  // Poll running tracks + embedding jobs
  useEffect(() => {
    if (pollingTracks.size === 0 && embeddingStatus !== 'computing') return;
    const interval = setInterval(() => {
      fetchStatus();
      if (embeddingStatus === 'computing') checkEmbeddings();
    }, 2000);
    return () => clearInterval(interval);
  }, [pollingTracks.size, embeddingStatus, fetchStatus, checkEmbeddings]);

  const prevRunningRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const runningNames = new Set(tracks.filter((t) => t.status === 'running').map((t) => t.name));

    // Detect tracks that just finished (were running, now aren't)
    const justFinished = [...prevRunningRef.current].filter((name) => !runningNames.has(name));
    if (justFinished.length > 0) {
      useProjectStore.getState().reloadActiveProject();
    }

    prevRunningRef.current = runningNames;
    setPollingTracks((prev) => {
      const prevArr = Array.from(prev).sort();
      const nextArr = [...runningNames].sort();
      if (prevArr.length === nextArr.length && prevArr.every((v, i) => v === nextArr[i])) return prev;
      return new Set(runningNames);
    });
  }, [tracks]);

  const computeEmbeddingsThenRun = useCallback(async (trackName: string, params?: Record<string, string | number>) => {
    if (!projectId) return;
    setEmbeddingStatus('computing');
    setEmbeddingDialog(null);

    const resp = await fetch(`/api/projects/${projectId}/embeddings/compute`, { method: 'POST' });
    const data = await resp.json();
    if (data.status === 'error') {
      setEmbeddingStatus('missing');
      return;
    }

    // Poll until embeddings are ready
    const poll = async (): Promise<void> => {
      for (let i = 0; i < 120; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const available = await checkEmbeddings();
        if (available) {
          // Now run the actual track, honoring the on-demand masking overlay.
          const { init, override } = maskOverrideInit();
          await fetch(`/api/projects/${projectId}/analyze/${trackName}${analyzeQuery(params, override)}`, init);
          fetchStatus();
          return;
        }
      }
    };
    poll();
  }, [projectId, fetchStatus, checkEmbeddings]);

  const handleRun = useCallback(async (trackName: string, params?: Record<string, string | number>) => {
    if (!projectId) return;

    // Check if this track needs embeddings
    if (EMBEDDING_DEPENDENT_TRACKS.has(trackName) && embeddingStatus !== 'available') {
      const available = await checkEmbeddings();
      if (!available) {
        setEmbeddingDialog({ trackName, params });
        return;
      }
    }

    const { init, override } = maskOverrideInit();
    await fetch(`/api/projects/${projectId}/analyze/${trackName}${analyzeQuery(params, override)}`, init);
    setParamDialogTrack(null);
    fetchStatus();
  }, [projectId, fetchStatus, embeddingStatus, checkEmbeddings]);

  const handleRunAll = useCallback(async () => {
    if (!projectId) return;
    const pending = tracks.filter((t) => t.status === 'pending');

    // Check if any pending track needs embeddings
    const needsEmbeddings = pending.some((t) => EMBEDDING_DEPENDENT_TRACKS.has(t.name));
    if (needsEmbeddings && embeddingStatus !== 'available') {
      const available = await checkEmbeddings();
      if (!available) {
        // Compute embeddings first, then run all
        setEmbeddingStatus('computing');
        const resp = await fetch(`/api/projects/${projectId}/embeddings/compute`, { method: 'POST' });
        const data = await resp.json();
        if (data.status === 'error') {
          setEmbeddingStatus('missing');
          // Run non-embedding tracks anyway
          for (const t of pending.filter((t) => !EMBEDDING_DEPENDENT_TRACKS.has(t.name))) {
            await fetch(`/api/projects/${projectId}/analyze/${t.name}`, { method: 'POST' });
          }
          fetchStatus();
          return;
        }
        // Poll for embeddings, then run all pending
        const poll = async (): Promise<void> => {
          for (let i = 0; i < 120; i++) {
            await new Promise((r) => setTimeout(r, 2000));
            const ready = await checkEmbeddings();
            if (ready) {
              for (const t of pending) {
                await fetch(`/api/projects/${projectId}/analyze/${t.name}`, { method: 'POST' });
              }
              fetchStatus();
              return;
            }
          }
        };
        // Run non-embedding tracks immediately
        for (const t of pending.filter((t) => !EMBEDDING_DEPENDENT_TRACKS.has(t.name))) {
          await fetch(`/api/projects/${projectId}/analyze/${t.name}`, { method: 'POST' });
        }
        fetchStatus();
        poll();
        return;
      }
    }

    for (const t of pending) {
      await fetch(`/api/projects/${projectId}/analyze/${t.name}`, { method: 'POST' });
    }
    fetchStatus();
  }, [projectId, tracks, fetchStatus, embeddingStatus, checkEmbeddings]);

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

  // FR-13 layer surface: flatten every track's plural layers; embedding layers also feed the
  // Representations scatter. Derived each render (no fetch — the status poll already carries them).
  const layerRefs = collectLayers(tracks);
  const embeddingLayers = layerRefs.filter((r) => laneKind(r.layer.rendering) === 'embedding-lane');

  if (loading) {
    return <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">Loading analysis status...</div>;
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden font-[var(--font-sans)] text-[0.85em]">
      {embeddingDialog && (
        <EmbeddingDialog
          onConfirm={() => computeEmbeddingsThenRun(embeddingDialog.trackName, embeddingDialog.params)}
          onCancel={() => setEmbeddingDialog(null)}
        />
      )}

      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)]">
        <div className="flex items-center gap-3">
          <span className="font-semibold">Analysis Suite</span>
          <span className="text-[var(--color-text-muted)] text-[0.85em]">
            {computedCount} computed · {pendingCount} pending · {runningCount} running
            {layerRefs.length > 0 ? ` · ${layerRefs.length} layers` : ''}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <IntegrityBadge projectId={projectId} />
          {subTab === 'tracks' && pendingCount > 0 && (
            <button
              onClick={handleRunAll}
              className="px-3 py-1 rounded bg-[var(--color-primary)] text-white cursor-pointer hover:opacity-90 text-[0.85em]"
            >
              Compute All ({pendingCount})
            </button>
          )}
        </div>
      </div>

      {/* Suite sub-tabs (Vision §3.4): Tracks runs producers; Profile / Representations / Explore are
          the consumer workbench over the layers those producers emit. */}
      <div role="tablist" aria-label="Analysis suite views" className="flex gap-1 px-4 pt-2 border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)]">
        {([
          ['tracks', 'Tracks'],
          ['profile', 'Profile'],
          ['representations', 'Representations'],
          ['explore', 'Explore'],
        ] as [SubTab, string][]).map(([id, label]) => (
          <button
            key={id}
            role="tab"
            aria-selected={subTab === id}
            onClick={() => setSubTab(id)}
            className={`px-3 py-1.5 text-[0.85em] rounded-t cursor-pointer border-b-2 ${
              subTab === id
                ? 'border-[var(--color-primary)] text-[var(--color-primary)] font-semibold'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            {label}
            {id === 'explore' && layerRefs.length > 0 ? ` (${layerRefs.length})` : ''}
            {id === 'representations' && embeddingLayers.length > 0 ? ` (${embeddingLayers.length})` : ''}
          </button>
        ))}
      </div>

      {embeddingStatus === 'computing' && (
        <div className="mx-4 mt-2 mb-1 px-3 py-2 rounded border border-[var(--color-primary)] bg-[var(--color-primary-subtle,#eff6ff)] text-[0.85em] flex items-center gap-2">
          <span className="animate-spin inline-block">⟳</span>
          <span>Computing paragraph embeddings… Embedding-dependent tracks will run automatically when ready.</span>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        {subTab === 'tracks' && (<>
        {pendingCount > 0 && computedCount === 0 && runningCount === 0 && (
          <div className="mx-4 mt-3 mb-2 p-4 rounded border border-[var(--color-primary)] bg-[var(--color-primary-subtle,#eff6ff)] text-center">
            <div className="text-[1em] font-semibold mb-1">No tracks computed yet</div>
            <div className="text-[0.85em] text-[var(--color-text-muted)] mb-3">
              Run analysis to compute NLP tracks (sentiment, entities, topics, etc.) for this text.
              Results will appear across all views automatically.
            </div>
            <button
              onClick={handleRunAll}
              className="px-4 py-2 rounded bg-[var(--color-primary)] text-white cursor-pointer hover:opacity-90 font-semibold"
            >
              Compute All Tracks ({pendingCount})
            </button>
          </div>
        )}

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
                    {track.runInfo?.clamped?.length ? (
                      <div className="text-[0.75em] text-[#b45309] mt-0.5 flex flex-wrap gap-x-2">
                        {track.runInfo.clamped.map((k) => (
                          <span
                            key={k}
                            title={`Requested ${String(track.runInfo!.requested?.[k])}, clamped to ${String(track.runInfo!.effective?.[k])} to fit the corpus.`}
                          >
                            {k}: ran {String(track.runInfo!.effective?.[k])} (requested {String(track.runInfo!.requested?.[k])})
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {track.runInfo?.posteriorType === 'hard-assignment' && (
                      <div
                        className="text-[0.75em] text-[#b45309] mt-0.5"
                        title="The Gaussian HMM could not be fit, so this run fell back to KMeans hard clustering. State labels are one-hot assignments, not probabilistic posteriors."
                      >
                        ⚠ KMeans fallback — hard assignment, not probabilities
                      </div>
                    )}
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
                      // self_similarity has no runnable defaults — it requires an explicit input
                      // bundle, so the action opens its layer-picker rather than firing a bare
                      // (guaranteed-400) run. It is NOT dep-gated like other tracks: `embedding`
                      // is an optional dep (only cosine/jaccard need it; word_overlap/edit_distance
                      // are text-only), and the picker itself enforces validity per metric.
                      track.name === 'self_similarity' ? (
                        <button
                          onClick={() => setParamDialogTrack(paramDialogTrack === track.name ? null : track.name)}
                          className="px-2 py-1 rounded border border-[var(--color-primary)] text-[var(--color-primary)] cursor-pointer hover:bg-[var(--color-primary)] hover:text-white text-[0.8em] disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          Configure…
                        </button>
                      ) : (
                        <button
                          onClick={() => handleRun(track.name)}
                          disabled={unmetDeps.length > 0}
                          className="px-2 py-1 rounded border border-[var(--color-primary)] text-[var(--color-primary)] cursor-pointer hover:bg-[var(--color-primary)] hover:text-white text-[0.8em] disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          Compute
                        </button>
                      )
                    )}
                    {track.status === 'computed' && (
                      TRACK_PARAMS[track.name] ? (
                        <button
                          onClick={() => setParamDialogTrack(paramDialogTrack === track.name ? null : track.name)}
                          className="px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em]"
                        >
                          Re-run...
                        </button>
                      ) : (
                        <button
                          onClick={() => handleRun(track.name)}
                          className="px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em]"
                        >
                          Re-run
                        </button>
                      )
                    )}
                    {track.status === 'running' && (
                      <div className="flex items-center gap-1.5">
                        <div className="w-16 h-1.5 bg-[var(--color-bg-muted)] rounded-full overflow-hidden">
                          <div className="h-full bg-[var(--color-primary)] rounded-full animate-pulse" style={{ width: '60%' }} />
                        </div>
                        <span className="text-[var(--color-primary)] text-[0.75em]">Running</span>
                      </div>
                    )}
                    {track.status === 'failed' && (
                      <div className="flex items-center gap-2">
                        <span
                          className="text-[#ef4444] text-[0.75em] max-w-[20rem] truncate"
                          title={track.error ?? 'Analysis failed'}
                        >
                          {track.error ?? 'Analysis failed'}
                        </span>
                        <button
                          onClick={() => track.name === 'self_similarity'
                            ? setParamDialogTrack(paramDialogTrack === track.name ? null : track.name)
                            : handleRun(track.name)}
                          className="px-2 py-1 rounded border border-[#ef4444] text-[#ef4444] cursor-pointer hover:bg-[#ef4444] hover:text-white text-[0.8em]"
                        >
                          {track.name === 'self_similarity' ? 'Reconfigure…' : 'Retry'}
                        </button>
                      </div>
                    )}
                    <button
                      onClick={() => setExpandedTrack(expandedTrack === track.name ? null : track.name)}
                      className="ml-1 px-2 py-1 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.8em]"
                    >
                      {expandedTrack === track.name ? 'Hide' : 'Details'}
                    </button>
                  </td>
                </tr>
                {paramDialogTrack === track.name && (
                  <tr className="bg-[var(--color-bg)]">
                    <td colSpan={6} className="px-4 py-2">
                      {track.name === 'self_similarity' ? (
                        <SelfSimilarityParamDialog
                          projectId={projectId}
                          onRun={(params) => handleRun(track.name, params)}
                          onCancel={() => setParamDialogTrack(null)}
                        />
                      ) : (
                        <ParamDialog
                          trackName={track.name}
                          onRun={(params) => handleRun(track.name, params)}
                          onCancel={() => setParamDialogTrack(null)}
                        />
                      )}
                    </td>
                  </tr>
                )}
                {expandedTrack === track.name && (
                  <tr className="bg-[var(--color-bg)]">
                    <td colSpan={6} className="px-4 py-3">
                      <div className="border border-[var(--color-border-subtle)] rounded p-3 bg-[var(--color-bg-subtle)]">
                        <div className="grid grid-cols-[120px_1fr] gap-y-2 text-[0.85em]">
                          <span className="text-[var(--color-text-muted)] font-semibold">Method</span>
                          <span>
                            {track.runInfo?.method
                              ? `${track.runInfo.method}${track.runInfo.posteriorType ? ` · ${track.runInfo.posteriorType} posteriors` : ''} (actual run)`
                              : (TRACK_DETAILS[track.name]?.method ?? 'N/A')}
                          </span>
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
        </>)}

        {subTab === 'profile' && <ProfileDashboard projectId={projectId} />}

        {subTab === 'representations' && (
          embeddingLayers.length === 0 ? (
            <div className="text-[0.8em] text-[var(--color-text-muted)] italic p-3">
              No embedding layers yet. Run an embedding track to see its 2-D projection here.
            </div>
          ) : (
            <div className="flex flex-wrap gap-4 p-3">
              {embeddingLayers.map((r) => (
                <EmbeddingScatter key={`${r.trackName}:${r.layer.label}`} projectId={projectId ?? ''} layer={r.layer} />
              ))}
            </div>
          )
        )}

        {subTab === 'explore' && (
          <LayerWorkbench projectId={projectId ?? ''} layers={layerRefs} />
        )}
      </div>
    </div>
  );
}
