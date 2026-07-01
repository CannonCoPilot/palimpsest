/**
 * CorpusView — the reference-free collection overview (C4, FR-33/FR-38).
 *
 * The N-text counterpart to the pair-centric Compare tab. Builds/reads the corpus graph and phyletic
 * tree for a chosen collection and renders three linked surfaces over them: a pangenome summary, a
 * Mauve-style block-map (per-member lanes colored by homology component), an all-pairs shared-component
 * matrix (click a cell → that pair's dotplot on the Compare tab), and a phyletic/stemma dendrogram with
 * a user-overridable root. Clicking a member opens its single-text browser — the three zoom tiers.
 */

import { useEffect, useState, useCallback } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useComparisonStore } from '../../stores/comparisonStore';
import { useViewStore } from '../../stores/viewStore';
import {
  blockMapLanes,
  sharedComponentMatrix,
  layoutTree,
  blockColor,
  type CorpusGraph,
  type PhyleticTree,
} from './corpusOverview';

interface CollectionOption {
  id: string;
  label: string;
  project_ids: string[];
}

function ClassBadge({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[0.8em]" style={{ background: 'var(--color-bg-subtle)' }}>
      <span className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
      <span className="font-medium">{count}</span> {label}
    </span>
  );
}

function BlockMap({ graph, onMember }: { graph: CorpusGraph; onMember: (m: string) => void }) {
  const lanes = blockMapLanes(graph);
  const globalMax = Math.max(1, ...lanes.map((l) => l.span));
  const W = 460;
  return (
    <div className="flex flex-col gap-1.5">
      {lanes.map((lane) => (
        <div key={lane.member} className="flex items-center gap-2">
          <button
            onClick={() => onMember(lane.member)}
            title={`Open ${lane.member} in the single-text browser`}
            className="w-28 shrink-0 truncate text-right text-[0.78em] text-[var(--color-primary)] hover:underline cursor-pointer"
          >
            {lane.member}
          </button>
          <svg width={W} height={16} role="img" aria-label={`${lane.member} block map`}>
            <rect x={0} y={0} width={W} height={16} fill="var(--color-bg-muted, #f3f4f6)" />
            {lane.blocks.map((b, i) => (
              <rect
                key={i}
                x={(b.start / globalMax) * W}
                y={0}
                width={Math.max(1, ((b.end - b.start) / globalMax) * W)}
                height={16}
                fill={blockColor(b.componentId, b.classification)}
              >
                <title>{`${b.classification} · ¶${b.start}–${b.end} · ${b.componentId}`}</title>
              </rect>
            ))}
          </svg>
        </div>
      ))}
    </div>
  );
}

function AllPairsMatrix({ graph, onPair }: { graph: CorpusGraph; onPair: (a: string, b: string) => void }) {
  const M = sharedComponentMatrix(graph);
  const members = graph.members;
  const maxCount = Math.max(1, ...M.flat());
  const cell = 30;
  return (
    <table className="border-collapse text-[0.72em]">
      <tbody>
        {members.map((rowM, i) => (
          <tr key={rowM}>
            <td className="pr-2 text-right whitespace-nowrap text-[var(--color-text-muted)] max-w-24 truncate" title={rowM}>{rowM}</td>
            {members.map((colM, j) => {
              const v = M[i][j];
              const intensity = v / maxCount;
              const isSelf = i === j;
              return (
                <td key={colM} className="p-0">
                  <button
                    disabled={isSelf || v === 0}
                    onClick={() => onPair(rowM, colM)}
                    title={isSelf ? rowM : `${rowM} ↔ ${colM}: ${v} shared component${v !== 1 ? 's' : ''} — open dotplot`}
                    className={`block ${isSelf || v === 0 ? 'cursor-default' : 'cursor-pointer hover:outline hover:outline-1 hover:outline-[var(--color-primary)]'}`}
                    style={{
                      width: cell,
                      height: cell,
                      background: isSelf
                        ? 'var(--color-bg-muted, #e5e7eb)'
                        : `hsl(210, 80%, ${92 - intensity * 45}%)`,
                      color: intensity > 0.5 ? 'white' : 'var(--color-text)',
                    }}
                  >
                    {isSelf ? '·' : v || ''}
                  </button>
                </td>
              );
            })}
          </tr>
        ))}
        <tr>
          <td />
          {members.map((m) => (
            <td key={m} className="text-center text-[var(--color-text-muted)] max-w-8 truncate" title={m}>{m.slice(0, 4)}</td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}

function PhyleticTreeView({ tree, onRoot, onMember }: {
  tree: PhyleticTree;
  onRoot: (root: string) => void;
  onMember: (m: string) => void;
}) {
  const { nodes } = layoutTree(tree.tree);
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const W = 300;
  const H = Math.max(80, tree.members.length * 34);
  const padL = 8;
  const padR = 90;
  const px = (x: number) => padL + x * (W - padL - padR);
  const py = (y: number) => 14 + y * (H - 28);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-[0.78em]">
        <label className="text-[var(--color-text-muted)]">Root</label>
        <select
          value={tree.root}
          onChange={(e) => onRoot(e.target.value)}
          className="px-1.5 py-0.5 border border-[var(--color-border)] rounded bg-[var(--color-bg)] cursor-pointer"
        >
          {tree.members.map((m) => (
            <option key={m} value={m}>
              {m}{m === tree.suggested_root ? ' (suggested)' : ''}
            </option>
          ))}
        </select>
      </div>
      <svg width={W} height={H} role="img" aria-label="Phyletic tree">
        {nodes.map((n) =>
          n.parent && byId.has(n.parent) ? (
            <g key={`e-${n.id}`} stroke="var(--color-border)" strokeWidth={1.5} fill="none">
              <path d={`M ${px(byId.get(n.parent)!.x)} ${py(byId.get(n.parent)!.y)} H ${px(n.x)} V ${py(n.y)}`} />
            </g>
          ) : null,
        )}
        {nodes.filter((n) => n.member).map((n) => (
          <g key={`n-${n.id}`}>
            <circle cx={px(n.x)} cy={py(n.y)} r={3} fill="var(--color-primary)" />
            <text
              x={px(n.x) + 6}
              y={py(n.y) + 3}
              className="text-[10px] fill-[var(--color-primary)] cursor-pointer"
              onClick={() => onMember(n.member!)}
            >
              {n.member}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function CorpusView() {
  const [collections, setCollections] = useState<CollectionOption[]>([]);
  const [collectionId, setCollectionId] = useState<string>('');
  const [graph, setGraph] = useState<CorpusGraph | null>(null);
  const [tree, setTree] = useState<PhyleticTree | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProject = useProjectStore((s) => s.loadProject);
  const loadSecondary = useProjectStore((s) => s.loadSecondaryProject);
  const activeProjectId = useProjectStore((s) => s.activeProjectId);
  const runAlignment = useComparisonStore((s) => s.runAlignment);
  const activeMethod = useComparisonStore((s) => s.activeMethod);
  const setActiveSubView = useComparisonStore((s) => s.setActiveSubView);
  const setActiveTab = useViewStore((s) => s.setActiveTab);

  useEffect(() => {
    fetch('/api/collections')
      .then((r) => (r.ok ? r.json() : []))
      .then((data: CollectionOption[]) => {
        const usable = data.filter((c) => c.project_ids.length >= 2);
        setCollections(usable);
        if (usable.length && !collectionId) setCollectionId(usable[0].id);
      })
      .catch(() => setError('Failed to load collections'));
  }, []);

  const loadOverview = useCallback(async (id: string, root?: string) => {
    setLoading(true);
    setError(null);
    try {
      const built = await fetch(`/api/collections/${id}/corpus-graph`, { method: 'POST' });
      if (!built.ok) {
        const j = await built.json().catch(() => ({}));
        throw new Error(j.detail ?? 'Failed to build corpus graph');
      }
      const g: CorpusGraph = await fetch(`/api/collections/${id}/corpus-graph`).then((r) => r.json());
      const t: PhyleticTree = await fetch(
        `/api/collections/${id}/phyletic-tree${root ? `?root=${encodeURIComponent(root)}` : ''}`,
      ).then((r) => r.json());
      setGraph(g);
      setTree(t);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setGraph(null);
      setTree(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (collectionId) loadOverview(collectionId);
  }, [collectionId, loadOverview]);

  const reRoot = useCallback((root: string) => {
    if (collectionId) loadOverview(collectionId, root);
  }, [collectionId, loadOverview]);

  const openMember = useCallback(async (member: string) => {
    await loadProject('', member);
    setActiveTab('browser');
  }, [loadProject, setActiveTab]);

  const openPair = useCallback(async (a: string, b: string) => {
    if (activeProjectId !== a) await loadProject('', a);
    await loadSecondary('', b);
    setActiveSubView('dotplot');
    setActiveTab('compare');
    runAlignment(a, b, activeMethod);
  }, [activeProjectId, loadProject, loadSecondary, setActiveSubView, setActiveTab, runAlignment, activeMethod]);

  const summary = graph?.summary as { core?: number; shell?: number; singleton?: number; n_edges?: number } | undefined;

  return (
    <div className="flex-1 flex flex-col overflow-hidden font-[var(--font-sans)]">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)] text-[0.85em]">
        <span className="font-semibold shrink-0">Corpus</span>
        {collections.length === 0 ? (
          <span className="text-[var(--color-text-muted)]">No multi-text collections — add ≥2 members to a collection.</span>
        ) : (
          <select
            value={collectionId}
            onChange={(e) => setCollectionId(e.target.value)}
            className="px-2 py-1 border border-[var(--color-border)] rounded bg-[var(--color-bg)] cursor-pointer text-[0.9em]"
          >
            {collections.map((c) => (
              <option key={c.id} value={c.id}>{c.label} ({c.project_ids.length})</option>
            ))}
          </select>
        )}
        {loading && <span className="text-[var(--color-text-muted)]">Assembling graph…</span>}
        {summary && !loading && (
          <div className="ml-auto flex items-center gap-1.5">
            <ClassBadge label="core" count={summary.core ?? 0} color={blockColor('core-legend', 'core')} />
            <ClassBadge label="shell" count={summary.shell ?? 0} color={blockColor('shell-legend', 'shell')} />
            <ClassBadge label="singleton" count={summary.singleton ?? 0} color="var(--color-bg-muted, #e5e7eb)" />
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto p-4">
        {error && (
          <div className="mb-3 px-3 py-2 rounded bg-[var(--color-danger-subtle)] text-[var(--color-danger)] text-[0.85em]">{error}</div>
        )}
        {!graph && !loading && !error && (
          <div className="text-[var(--color-text-muted)] text-[0.9em]">Select a collection to assemble its corpus graph.</div>
        )}
        {graph && tree && (
          <div className="flex flex-col gap-6 max-w-[900px]">
            <section>
              <h3 className="text-[0.8em] font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-2">Block map · homology components across members</h3>
              <BlockMap graph={graph} onMember={openMember} />
            </section>
            <div className="flex flex-wrap gap-10">
              <section>
                <h3 className="text-[0.8em] font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-2">All-pairs shared components</h3>
                <AllPairsMatrix graph={graph} onPair={openPair} />
              </section>
              <section>
                <h3 className="text-[0.8em] font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-2">Phyletic tree</h3>
                <PhyleticTreeView tree={tree} onRoot={reRoot} onMember={openMember} />
              </section>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
