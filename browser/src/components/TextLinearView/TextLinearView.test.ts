import { describe, it, expect } from 'vitest';
import { bucketAnnotationsByParagraph } from './TextLinearView';
import type { Paragraph } from '../../stores/projectStore';
import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';

function para(index: number, start: number, end: number): Paragraph {
  return { index, start, end, text: 'x'.repeat(end - start) } as unknown as Paragraph;
}

function ann(start: number | null, end: number | null): W3CAnnotation {
  return { target: { selector: { start, end } } } as unknown as W3CAnnotation;
}

const PARAS = [para(0, 0, 100), para(1, 100, 200), para(2, 200, 300)];

describe('bucketAnnotationsByParagraph', () => {
  it('places a single-paragraph annotation in only that paragraph', () => {
    const a = ann(10, 50);
    const buckets = bucketAnnotationsByParagraph(PARAS, [a]);
    expect(buckets.get(0)).toEqual([a]);
    expect(buckets.has(1)).toBe(false);
    expect(buckets.has(2)).toBe(false);
  });

  it('places a cross-boundary annotation in every paragraph it overlaps', () => {
    const a = ann(90, 150); // spans para 0 (..100) and para 1 (100..)
    const buckets = bucketAnnotationsByParagraph(PARAS, [a]);
    expect(buckets.get(0)).toEqual([a]);
    expect(buckets.get(1)).toEqual([a]);
    expect(buckets.has(2)).toBe(false);
  });

  it('skips annotations that fall outside every paragraph', () => {
    const buckets = bucketAnnotationsByParagraph(PARAS, [ann(500, 600)]);
    expect(buckets.size).toBe(0);
  });

  it('skips annotations with null start/end selectors', () => {
    const buckets = bucketAnnotationsByParagraph(PARAS, [ann(null, 50), ann(10, null)]);
    expect(buckets.size).toBe(0);
  });

  it('keys by paragraph.index, not array position (character-filtered, non-contiguous)', () => {
    // Simulates a filtered paragraph list whose indices are non-contiguous.
    const filtered = [para(0, 0, 100), para(5, 500, 600)];
    const a = ann(510, 520);
    const buckets = bucketAnnotationsByParagraph(filtered, [a]);
    expect(buckets.get(5)).toEqual([a]);
    expect(buckets.has(0)).toBe(false);
  });

  it('preserves annotation order within a bucket', () => {
    const a1 = ann(10, 20);
    const a2 = ann(30, 40);
    const buckets = bucketAnnotationsByParagraph(PARAS, [a1, a2]);
    expect(buckets.get(0)).toEqual([a1, a2]);
  });
});
