/**
 * Unit tests for GoldLibrary's pure logic — the appliability rule and the display
 * ordering that drive the grid, exercised without a React render (mirrors the
 * ProjectPicker.test.ts convention).
 */
import { describe, it, expect } from 'vitest';

import { goldApplyState, sortGold, type GoldBible } from './GoldLibrary';

function bible(over: Partial<GoldBible> & { id: number }): GoldBible {
  return {
    translation: `Bible ${over.id}`,
    year: null,
    spelling: 'modern',
    typeset: 'modern',
    canon: 'protestant-66',
    kind: 'marker',
    source_origin: 'reconstructed-from-web-scrape',
    source_present: true,
    map_present: true,
    gold_map: `maps/work-${String(over.id).padStart(3, '0')}.map.json`,
    annotation_gold: null,
    accuracy_source: 'canon-oracle',
    structure: { books: 66, chapters: 1189, verses: 31102 },
    validated: { cli: true, api: true, ui: true },
    ...over,
  };
}

describe('goldApplyState — appliability gate', () => {
  it('is ready when both the map and the source are present locally', () => {
    const { canApply, reason } = goldApplyState({ map_present: true, source_present: true });
    expect(canApply).toBe(true);
    expect(reason).toBe('ready');
  });

  it('blocks (and explains) when the source binary is not on this machine', () => {
    const { canApply, reason } = goldApplyState({ map_present: true, source_present: false });
    expect(canApply).toBe(false);
    expect(reason).toMatch(/source/i);
  });

  it('blocks when the committed map is missing, before considering the source', () => {
    const { canApply, reason } = goldApplyState({ map_present: false, source_present: false });
    expect(canApply).toBe(false);
    expect(reason).toMatch(/map/i);
  });
});

describe('sortGold — stable display order', () => {
  it('orders Bibles by ascending gold id', () => {
    const out = sortGold([bible({ id: 219 }), bible({ id: 5 }), bible({ id: 108 })]);
    expect(out.map((b) => b.id)).toEqual([5, 108, 219]);
  });

  it('does not mutate the input array', () => {
    const input = [bible({ id: 3 }), bible({ id: 1 })];
    const snapshot = input.map((b) => b.id);
    sortGold(input);
    expect(input.map((b) => b.id)).toEqual(snapshot);
  });
});
