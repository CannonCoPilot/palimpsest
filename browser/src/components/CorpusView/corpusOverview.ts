/**
 * corpusOverview — pure transforms behind the collection overview (C4, FR-33/FR-38).
 *
 * The backend corpus-graph + phyletic-tree endpoints already carry everything the overview draws;
 * these helpers reshape that data for the three surfaces (Mauve block-map, all-pairs matrix, phyletic
 * dendrogram) with no fetching or rendering, so the maths is unit-testable in isolation. Mirrors the
 * backend's leaf/IO split.
 */

export interface PassageNode {
  id: string;
  member: string;
  para_start: number;
  para_end: number;
  char_start: number | null;
  char_end: number | null;
}

export type Classification = 'core' | 'shell' | 'singleton';

export interface Component {
  id: string;
  classification: Classification;
  members: string[];
  node_ids: string[];
}

export interface CorpusGraph {
  collection_id: string;
  members: string[];
  nodes: PassageNode[];
  edges: { a: string; b: string; comparison: string; score: number }[];
  components: Component[];
  summary: Record<string, unknown>;
  provenance: Record<string, unknown>;
}

export interface TreeNode {
  id: string;
  is_leaf: boolean;
  member: string | null;
  parent: string | null;
  branch_length: number;
  children: string[];
}

export interface PhyleticTree {
  collection_id: string;
  members: string[];
  distances: number[][];
  participation: Record<string, number>;
  suggested_root: string;
  root: string;
  tree: TreeNode[];
}

export interface Block {
  start: number;
  end: number;
  componentId: string;
  classification: Classification;
}

export interface BlockLane {
  member: string;
  span: number; // paragraph count spanned (max para_end)
  blocks: Block[];
}

/** Per-member paragraph lanes for the Mauve block-map: each passage colored by its homology
 * component (a shared component is the same block id across every member's lane). */
export function blockMapLanes(graph: CorpusGraph): BlockLane[] {
  const compOf = new Map<string, Component>();
  for (const c of graph.components) for (const nid of c.node_ids) compOf.set(nid, c);

  return graph.members.map((member) => {
    const nodes = graph.nodes
      .filter((n) => n.member === member)
      .sort((a, b) => a.para_start - b.para_start);
    const span = nodes.reduce((mx, n) => Math.max(mx, n.para_end), 0);
    const blocks: Block[] = nodes.map((n) => {
      const c = compOf.get(n.id);
      return {
        start: n.para_start,
        end: n.para_end,
        componentId: c?.id ?? '?',
        classification: c?.classification ?? 'singleton',
      };
    });
    return { member, span, blocks };
  });
}

/** All-pairs shared-component counts (core + shell only; singletons never cross members). The Circos
 * chord weights and the click-to-compare matrix both read this symmetric n×n matrix. */
export function sharedComponentMatrix(graph: CorpusGraph): number[][] {
  const idx = new Map(graph.members.map((m, i) => [m, i]));
  const n = graph.members.length;
  const M = Array.from({ length: n }, () => Array<number>(n).fill(0));
  for (const c of graph.components) {
    if (c.members.length < 2) continue;
    for (let a = 0; a < c.members.length; a++) {
      for (let b = a + 1; b < c.members.length; b++) {
        const i = idx.get(c.members[a]);
        const j = idx.get(c.members[b]);
        if (i === undefined || j === undefined) continue;
        M[i][j]++;
        M[j][i]++;
      }
    }
  }
  return M;
}

export interface TreePlacement {
  id: string;
  x: number; // 0..1, cumulative branch length from root (normalized)
  y: number; // 0..1, leaf order
  is_leaf: boolean;
  member: string | null;
  parent: string | null;
}

/** Dendrogram layout for the phyletic tree: x is cumulative branch length from the root (normalized to
 * the deepest tip), y is leaf order (internal nodes centered over their descendants). Both in [0,1] so
 * the SVG can scale to any box. */
export function layoutTree(tree: TreeNode[]): { nodes: TreePlacement[]; leafCount: number } {
  const byId = new Map(tree.map((n) => [n.id, n]));
  const root = tree.find((n) => n.parent === null);
  if (!root) return { nodes: [], leafCount: 0 };

  const depth = new Map<string, number>();
  const walkDepth = (id: string, accumulated: number): void => {
    const node = byId.get(id);
    if (!node) return;
    const d = accumulated + (node.parent === null ? 0 : node.branch_length);
    depth.set(id, d);
    for (const ch of node.children) walkDepth(ch, d);
  };
  walkDepth(root.id, 0);
  const maxDepth = Math.max(...depth.values(), 1e-9);

  let leafCounter = 0;
  const yPos = new Map<string, number>();
  const walkY = (id: string): number => {
    const node = byId.get(id);
    if (!node) return 0;
    if (node.children.length === 0) {
      const y = leafCounter++;
      yPos.set(id, y);
      return y;
    }
    const childYs = node.children.map(walkY);
    const mid = (Math.min(...childYs) + Math.max(...childYs)) / 2;
    yPos.set(id, mid);
    return mid;
  };
  walkY(root.id);
  const leafCount = leafCounter;

  const nodes: TreePlacement[] = tree.map((n) => ({
    id: n.id,
    x: (depth.get(n.id) ?? 0) / maxDepth,
    y: leafCount > 1 ? (yPos.get(n.id) ?? 0) / (leafCount - 1) : 0.5,
    is_leaf: n.is_leaf,
    member: n.member,
    parent: n.parent,
  }));
  return { nodes, leafCount };
}

/** Stable, deterministic color for a homology component (shared blocks same-colored across lanes).
 * Singletons render muted; core/shell get a saturated hue from a hash of the component id. */
export function blockColor(componentId: string, classification: Classification): string {
  if (classification === 'singleton') return 'var(--color-bg-muted, #e5e7eb)';
  let h = 0;
  for (let i = 0; i < componentId.length; i++) h = (h * 31 + componentId.charCodeAt(i)) % 360;
  const light = classification === 'core' ? 45 : 62; // core darker/stronger than shell
  return `hsl(${h}, 65%, ${light}%)`;
}
