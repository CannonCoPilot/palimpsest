import { describe, it, expect } from 'vitest';
import {
  blockMapLanes,
  sharedComponentMatrix,
  layoutTree,
  blockColor,
  repeatLanes,
  conservationLane,
  conservationColor,
  type CorpusGraph,
  type TreeNode,
  type CorpusRepeats,
  type RootTrack,
} from './corpusOverview';

// alpha:[0]core [1]singleton [2]shell   beta:[0]core [1]singleton [2]shell   gamma:[0]core [1]singleton
const GRAPH: CorpusGraph = {
  collection_id: 'corpus',
  members: ['alpha', 'beta', 'gamma'],
  nodes: [
    { id: 'n0', member: 'alpha', para_start: 0, para_end: 1, char_start: 0, char_end: 10 },
    { id: 'n1', member: 'alpha', para_start: 1, para_end: 2, char_start: 11, char_end: 20 },
    { id: 'n2', member: 'alpha', para_start: 2, para_end: 3, char_start: 21, char_end: 30 },
    { id: 'n3', member: 'beta', para_start: 0, para_end: 1, char_start: 0, char_end: 10 },
    { id: 'n4', member: 'beta', para_start: 1, para_end: 2, char_start: 11, char_end: 20 },
    { id: 'n5', member: 'beta', para_start: 2, para_end: 3, char_start: 21, char_end: 30 },
    { id: 'n6', member: 'gamma', para_start: 0, para_end: 1, char_start: 0, char_end: 10 },
    { id: 'n7', member: 'gamma', para_start: 1, para_end: 2, char_start: 11, char_end: 20 },
  ],
  edges: [{ a: 'n0', b: 'n3', comparison: 'x', score: 30 }],
  components: [
    { id: 'c0', classification: 'core', members: ['alpha', 'beta', 'gamma'], node_ids: ['n0', 'n3', 'n6'] },
    { id: 'c1', classification: 'shell', members: ['alpha', 'beta'], node_ids: ['n2', 'n5'] },
    { id: 'c2', classification: 'singleton', members: ['alpha'], node_ids: ['n1'] },
    { id: 'c3', classification: 'singleton', members: ['beta'], node_ids: ['n4'] },
    { id: 'c4', classification: 'singleton', members: ['gamma'], node_ids: ['n7'] },
  ],
  summary: {},
  provenance: {},
};

describe('blockMapLanes', () => {
  it('produces one lane per member, blocks ordered and colored by component', () => {
    const lanes = blockMapLanes(GRAPH);
    expect(lanes.map((l) => l.member)).toEqual(['alpha', 'beta', 'gamma']);

    const alpha = lanes[0];
    expect(alpha.span).toBe(3);
    expect(alpha.blocks.map((b) => b.classification)).toEqual(['core', 'singleton', 'shell']);
    expect(alpha.blocks.map((b) => b.componentId)).toEqual(['c0', 'c2', 'c1']);

    // the core block shares its component id across every member's lane (Mauve same-color rule).
    expect(lanes[1].blocks[0].componentId).toBe('c0');
    expect(lanes[2].blocks[0].componentId).toBe('c0');
    expect(lanes[2].span).toBe(2);
  });
});

describe('sharedComponentMatrix', () => {
  it('counts core+shell components shared by each pair, ignoring singletons', () => {
    const M = sharedComponentMatrix(GRAPH);
    // alpha-beta share core + shell = 2; either with gamma shares only core = 1.
    expect(M[0][1]).toBe(2);
    expect(M[0][2]).toBe(1);
    expect(M[1][2]).toBe(1);
    expect(M[0][0]).toBe(0); // diagonal untouched
    expect(M).toEqual(M.map((row, i) => M.map((_, j) => M[j][i]))); // symmetric
  });
});

describe('layoutTree', () => {
  const TREE: TreeNode[] = [
    { id: 'alpha', is_leaf: true, member: 'alpha', parent: null, branch_length: 0, children: ['node0'] },
    { id: 'node0', is_leaf: false, member: null, parent: 'alpha', branch_length: 0.5, children: ['beta', 'gamma'] },
    { id: 'beta', is_leaf: true, member: 'beta', parent: 'node0', branch_length: 0.3, children: [] },
    { id: 'gamma', is_leaf: true, member: 'gamma', parent: 'node0', branch_length: 0.3, children: [] },
  ];

  it('places the root at x=0 and tips at x=1, with leaves spread over y', () => {
    const { nodes, leafCount } = layoutTree(TREE);
    expect(leafCount).toBe(2);
    const by = Object.fromEntries(nodes.map((n) => [n.id, n]));

    expect(by.alpha.x).toBe(0);
    expect(by.beta.x).toBeCloseTo(1); // deepest tip (0.5 + 0.3 = maxDepth)
    expect(by.node0.x).toBeCloseTo(0.625);
    expect(by.beta.y).toBe(0);
    expect(by.gamma.y).toBe(1);
    expect(by.node0.y).toBeCloseTo(0.5); // centered over its two children
  });

  it('returns empty for a rootless list', () => {
    expect(layoutTree([]).nodes).toEqual([]);
  });
});

describe('blockColor', () => {
  it('mutes singletons and gives shared components a stable hue', () => {
    expect(blockColor('c2', 'singleton')).toContain('muted');
    expect(blockColor('c0', 'core')).toMatch(/^hsl\(/);
    expect(blockColor('c0', 'core')).toBe(blockColor('c0', 'core')); // deterministic
  });
});

describe('repeatLanes', () => {
  const CR: CorpusRepeats = {
    collection_id: 'corpus',
    members: ['alpha', 'beta'],
    min_members: 2,
    phrases: ['eternal covenant endures'],
    phrase_members: { 'eternal covenant endures': 2 },
    intervals: { alpha: [[0, 25], [50, 75]], beta: [[10, 30]] },
    lengths: { alpha: 100, beta: 40 },
    summary: { phrase_count: 1, masked_chars: { alpha: 50, beta: 20 } },
  };

  it('x-scales each member’s intervals against its own text length', () => {
    const lanes = repeatLanes(CR);
    expect(lanes.map((l) => l.member)).toEqual(['alpha', 'beta']);
    // alpha: [0,25]/100 and [50,75]/100 → bands at fractions.
    expect(lanes[0].bands).toEqual([{ start: 0, end: 0.25 }, { start: 0.5, end: 0.75 }]);
    expect(lanes[0].maskedFraction).toBeCloseTo(0.5);
    // beta uses beta's own length (40), not alpha's.
    expect(lanes[1].bands).toEqual([{ start: 0.25, end: 0.75 }]);
    expect(lanes[1].maskedFraction).toBeCloseTo(0.5);
  });

  it('handles a member with no repeats', () => {
    const lanes = repeatLanes({
      ...CR,
      intervals: { alpha: [], beta: [] },
      summary: { phrase_count: 0, masked_chars: { alpha: 0, beta: 0 } },
    });
    expect(lanes[0].bands).toEqual([]);
    expect(lanes[0].maskedFraction).toBe(0);
  });
});

describe('conservationLane', () => {
  const TRACK: RootTrack = {
    collection_id: 'corpus',
    root: 'alpha',
    kind: 'conservation',
    member_total: 3,
    root_length: 200,
    segment_offsets: [[0, 50], [50, 100]],
    values: [1, 2 / 3],
    segments: [
      { component: 'c0', classification: 'core', char_start: 0, char_end: 50, conservation: 1, members: ['alpha', 'beta', 'gamma'] },
      { component: 'c1', classification: 'shell', char_start: 50, char_end: 100, conservation: 2 / 3, members: ['alpha', 'beta'] },
    ],
    rendering: { track_view: 'root-conservation-lane', encoding: 'heat', domain: [0, 1] },
  };

  it('x-scales segments against the root length and carries conservation values', () => {
    const segs = conservationLane(TRACK);
    expect(segs[0]).toMatchObject({ start: 0, end: 0.25, value: 1, classification: 'core' });
    expect(segs[1]).toMatchObject({ start: 0.25, end: 0.5, classification: 'shell' });
    expect(segs[1].value).toBeCloseTo(2 / 3);
  });

  it('darkens with conservation (more-shared passages render stronger)', () => {
    // higher value → lower lightness in the hsl string.
    const light = (c: string) => Number(c.match(/(\d+(?:\.\d+)?)%\)$/)![1]);
    expect(light(conservationColor(1))).toBeLessThan(light(conservationColor(0)));
  });
});
