import { describe, it, expect } from 'vitest';
import {
  memberPairCount,
  formatRecall,
  formatPct,
  journalPairs,
  type SweepJournal,
} from './sweep';

describe('sweep transforms', () => {
  it('memberPairCount = C(n,2), and 0 below two members', () => {
    expect(memberPairCount(0)).toBe(0);
    expect(memberPairCount(1)).toBe(0);
    expect(memberPairCount(2)).toBe(1);
    expect(memberPairCount(3)).toBe(3);
    expect(memberPairCount(5)).toBe(10);
  });

  it('formatRecall renders null/undefined as n/a — never a fabricated number', () => {
    expect(formatRecall(null)).toBe('n/a');
    expect(formatRecall(undefined)).toBe('n/a');
    expect(formatRecall(0)).toBe('0%'); // a measured zero is NOT the same as unmeasured
    expect(formatRecall(0.102)).toBe('10%');
    expect(formatRecall(1)).toBe('100%');
  });

  it('formatPct keeps a near-100% prune tail when asked for more digits', () => {
    expect(formatPct(null)).toBe('—');
    expect(formatPct(undefined)).toBe('—');
    expect(formatPct(0.9998, 2)).toBe('99.98%');
    expect(formatPct(0.102, 1)).toBe('10.2%');
  });

  it('journalPairs turns the opaque pair dict into an array', () => {
    const j = { pairs: { 'a\x00b': { a: 'a', b: 'b' }, 'a\x00c': { a: 'a', b: 'c' } } } as unknown as SweepJournal;
    expect(journalPairs(j).length).toBe(2);
    expect(journalPairs({ pairs: {} } as SweepJournal)).toEqual([]);
  });
});
