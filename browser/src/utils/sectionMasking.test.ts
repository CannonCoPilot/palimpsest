import { describe, it, expect } from 'vitest';
import { computeMaskedIntervals, type LayoutSection } from './sectionMasking';

function sec(id: string, type: string, start: number, end: number, masked: boolean | null = null): LayoutSection {
  return { id, type, start, end, label: id, parent_id: null, source: 'test', masked };
}

const MASK: Record<string, boolean> = { chapter: false, heading: true };

describe('computeMaskedIntervals — structural (extraMasked default [])', () => {
  it('masks a masked type and leaves an analyzed type uncovered', () => {
    const sections = [sec('a', 'heading', 0, 10), sec('b', 'chapter', 10, 30)];
    expect(computeMaskedIntervals(sections, MASK, 30)).toEqual([[0, 10]]);
  });

  it('deepest (smallest) covering section wins ties by last-defined', () => {
    // chapter (analyzed) contains a heading (masked) — only the inner heading masks.
    const sections = [sec('outer', 'chapter', 0, 100), sec('inner', 'heading', 40, 50)];
    expect(computeMaskedIntervals(sections, MASK, 100)).toEqual([[40, 50]]);
  });

  it('is byte-identical whether extraMasked is omitted or []', () => {
    const sections = [sec('a', 'heading', 0, 10), sec('b', 'chapter', 10, 30)];
    const withDefault = computeMaskedIntervals(sections, MASK, 30);
    const withEmpty = computeMaskedIntervals(sections, MASK, 30, []);
    expect(withEmpty).toEqual(withDefault);
  });
});

describe('computeMaskedIntervals — verse-number interval layer (extraMasked)', () => {
  it('masks a verse-number token sitting inside an analyzed chapter', () => {
    const sections = [sec('ch', 'chapter', 0, 100)];
    // verse-number tokens [ns, s): two tokens inside the analyzed chapter body.
    const result = computeMaskedIntervals(sections, MASK, 100, [[10, 15], [40, 46]]);
    expect(result).toEqual([[10, 15], [40, 46]]);
  });

  it('merges an extra interval adjacent to a structural masked span', () => {
    // heading masks [0,10); verse number [10,15) abuts it → one merged span.
    const sections = [sec('h', 'heading', 0, 10), sec('ch', 'chapter', 10, 100)];
    const result = computeMaskedIntervals(sections, MASK, 100, [[10, 15]]);
    expect(result).toEqual([[0, 15]]);
  });

  it('clips extra intervals to [0, textLen) and drops empties', () => {
    const sections = [sec('ch', 'chapter', 0, 50)];
    const result = computeMaskedIntervals(sections, MASK, 50, [[-5, 5], [48, 999], [20, 20]]);
    expect(result).toEqual([[0, 5], [48, 50]]);
  });

  it('applies the verse layer even when there are no structural sections', () => {
    expect(computeMaskedIntervals([], {}, 100, [[10, 15], [30, 36]])).toEqual([[10, 15], [30, 36]]);
  });

  it('coalesces overlapping/out-of-order extra intervals', () => {
    const result = computeMaskedIntervals([], {}, 100, [[30, 40], [10, 20], [18, 25]]);
    expect(result).toEqual([[10, 25], [30, 40]]);
  });
});
