import { describe, it, expect } from 'vitest';
import { computeMaskedIntervals, effectiveMask, type LayoutSection } from './sectionMasking';

function sec(id: string, type: string, start: number, end: number, masked: boolean | null = null): LayoutSection {
  return { id, type, start, end, label: id, parent_id: null, source: 'test', masked };
}

const MASK: Record<string, boolean> = { chapter: false, heading: true };

/** Reference brute-force port of the prior O(N²) algorithm — the oracle the sweep-line must match. */
function bruteMaskedIntervals(
  sections: LayoutSection[],
  maskByType: Record<string, boolean>,
  textLen: number,
  extraMasked: ReadonlyArray<readonly [number, number]> = [],
): Array<[number, number]> {
  const raw: Array<[number, number]> = [];
  const valid = sections.filter((s) => s.start >= 0 && s.start < s.end && s.end <= textLen);
  if (valid.length > 0) {
    const points = Array.from(new Set<number>([0, textLen, ...valid.flatMap((s) => [s.start, s.end])])).sort(
      (a, b) => a - b,
    );
    for (let i = 0; i < points.length - 1; i++) {
      const a = points[i];
      const b = points[i + 1];
      if (a >= b) continue;
      const covering = valid.filter((s) => s.start <= a && s.end >= b);
      if (covering.length === 0) continue;
      const minSpan = Math.min(...covering.map((s) => s.end - s.start));
      const chosen = covering.filter((s) => s.end - s.start === minSpan).at(-1)!;
      if (effectiveMask(chosen, maskByType)) raw.push([a, b]);
    }
  }
  for (const [s, e] of extraMasked) {
    const cs = Math.max(0, s);
    const ce = Math.min(textLen, e);
    if (cs < ce) raw.push([cs, ce]);
  }
  if (raw.length === 0) return [];
  raw.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged: Array<[number, number]> = [];
  for (const [s, e] of raw) {
    const last = merged[merged.length - 1];
    if (last && s <= last[1]) last[1] = Math.max(last[1], e);
    else merged.push([s, e]);
  }
  return merged;
}

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

describe('computeMaskedIntervals — sweep-line equivalence (vs brute-force oracle)', () => {
  it('matches the brute-force on partially-overlapping (non-nested) sections', () => {
    // a:[0,20] masked, b:[10,30] masked-false; segment [10,20] is covered by both, equal-span
    // tie → last-defined (b) wins → unmasked. [0,10] only a → masked. [20,30] only b → unmasked.
    const sections = [sec('a', 'heading', 0, 20), sec('b', 'chapter', 10, 30)];
    expect(computeMaskedIntervals(sections, MASK, 30)).toEqual(bruteMaskedIntervals(sections, MASK, 30));
    expect(computeMaskedIntervals(sections, MASK, 30)).toEqual([[0, 10]]);
  });

  it('matches the brute-force when equal-span duplicates resolve by last-defined', () => {
    const sections = [sec('a', 'chapter', 0, 10), sec('b', 'heading', 0, 10)]; // same span, b later → masked
    expect(computeMaskedIntervals(sections, MASK, 10)).toEqual([[0, 10]]);
    expect(computeMaskedIntervals(sections, MASK, 10)).toEqual(bruteMaskedIntervals(sections, MASK, 10));
  });

  it('equals the brute-force across 5000 randomized cases (nested/overlap/tie-break/extraMasked)', () => {
    // Deterministic LCG so failures reproduce.
    let state = 1234567;
    const rnd = () => {
      state = (state * 1103515245 + 12345) & 0x7fffffff;
      return state / 0x7fffffff;
    };
    const randint = (lo: number, hi: number) => lo + Math.floor(rnd() * (hi - lo + 1));
    const types = ['body', 'chapter', 'heading', 'footnotes', 'verse', 'appendix'];

    for (let t = 0; t < 5000; t++) {
      const textLen = randint(1, 40);
      const n = randint(0, 8);
      const sections: LayoutSection[] = [];
      for (let i = 0; i < n; i++) {
        let a = randint(0, textLen);
        let b = randint(0, textLen);
        if (a === b) b = Math.min(textLen, a + 1);
        const lo = Math.min(a, b);
        const hi = Math.max(a, b);
        const masked = [null, true, false][randint(0, 2)] as boolean | null;
        sections.push(sec(`s${i}`, types[randint(0, types.length - 1)], lo, hi, masked));
      }
      const maskByType: Record<string, boolean> = {};
      for (const ty of types) maskByType[ty] = rnd() < 0.5;
      let extra: Array<[number, number]> = [];
      if (rnd() < 0.4) {
        for (let k = randint(0, 4); k > 0; k--) {
          const a = randint(-2, textLen + 2);
          const b = randint(-2, textLen + 2);
          extra.push([Math.min(a, b), Math.max(a, b)]);
        }
      }
      const got = computeMaskedIntervals(sections, maskByType, textLen, extra);
      const want = bruteMaskedIntervals(sections, maskByType, textLen, extra);
      if (JSON.stringify(got) !== JSON.stringify(want)) {
        throw new Error(
          `mismatch trial ${t}: sections=${JSON.stringify(
            sections.map((s) => [s.type, s.start, s.end, s.masked]),
          )} mask=${JSON.stringify(maskByType)} len=${textLen} extra=${JSON.stringify(extra)}\n got=${JSON.stringify(
            got,
          )}\nwant=${JSON.stringify(want)}`,
        );
      }
    }
  });
});
