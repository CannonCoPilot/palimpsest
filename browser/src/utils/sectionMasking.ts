/**
 * Client-side port of the backend layout masking (core/palimpsest/layout.py) so the
 * section editor can preview masked ranges instantly while dragging, without a
 * round-trip. Must stay in sync with the Python "deepest section wins" rule.
 */

export interface LayoutSection {
  id: string;
  type: string;
  start: number;
  end: number;
  label: string;
  parent_id: string | null;
  source: string;
  masked: boolean | null;
  metadata?: Record<string, string>;
}

export interface SectionType {
  key: string;
  label: string;
  color: string;
  default_mask: boolean;
  builtin?: boolean;
}

export interface ExtraType {
  key: string;
  label: string;
  color: string;
  default_mask: boolean;
}

export function effectiveMask(s: LayoutSection, maskByType: Record<string, boolean>): boolean {
  if (s.masked !== null && s.masked !== undefined) return s.masked;
  return maskByType[s.type] ?? true;
}

/**
 * Merged masked [start,end) intervals.
 *
 * Structural sections use "deepest (smallest) covering section wins". On top of that,
 * `extraMasked` carries flat interval mask-layers — disjoint, leaf-level token spans that
 * never nest or participate in deepest-wins (e.g. verse-number tokens). They are unioned
 * in AFTER the structural pass, mirroring the backend's
 * `layout.masked_intervals(..., extra_masked=...)`. Passing `[]` (the default) reproduces
 * the pure-structural result byte-for-byte.
 */
// A covering section in the sweep below: span (end-start) and negIndex (-index in `valid`)
// form the order key so the heap top is the deepest (smallest span), ties broken by
// last-defined (highest index); `end` drives lazy removal once a section has closed.
interface SweepEntry {
  span: number;
  negIndex: number;
  end: number;
  index: number;
}

/** Minimal binary min-heap on (span asc, negIndex asc) — JS has no built-in heap. */
class SweepHeap {
  private a: SweepEntry[] = [];
  get size(): number {
    return this.a.length;
  }
  peek(): SweepEntry {
    return this.a[0];
  }
  private less(x: SweepEntry, y: SweepEntry): boolean {
    return x.span < y.span || (x.span === y.span && x.negIndex < y.negIndex);
  }
  push(e: SweepEntry): void {
    const a = this.a;
    a.push(e);
    let i = a.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (!this.less(a[i], a[p])) break;
      [a[i], a[p]] = [a[p], a[i]];
      i = p;
    }
  }
  pop(): void {
    const a = this.a;
    const last = a.pop()!;
    if (a.length === 0) return;
    a[0] = last;
    let i = 0;
    const n = a.length;
    for (;;) {
      let s = i;
      const l = 2 * i + 1;
      const r = 2 * i + 2;
      if (l < n && this.less(a[l], a[s])) s = l;
      if (r < n && this.less(a[r], a[s])) s = r;
      if (s === i) break;
      [a[i], a[s]] = [a[s], a[i]];
      i = s;
    }
  }
}

export function computeMaskedIntervals(
  sections: LayoutSection[],
  maskByType: Record<string, boolean>,
  textLen: number,
  extraMasked: ReadonlyArray<readonly [number, number]> = [],
): Array<[number, number]> {
  const raw: Array<[number, number]> = [];

  const valid = sections.filter((s) => s.start >= 0 && s.start < s.end && s.end <= textLen);
  if (valid.length > 0) {
    // Sweep breakpoints left→right, keeping a heap of opened-but-not-closed sections. The
    // heap top is the deepest covering section (smallest span, ties to last-defined); closed
    // sections are lazily discarded. O(N log N) vs. the prior O(N²) per-segment rescan, and
    // byte-identical to it. Mirrors core/palimpsest/layout.py masked_intervals.
    const startsAt = new Map<number, number[]>();
    valid.forEach((s, i) => {
      const arr = startsAt.get(s.start);
      if (arr) arr.push(i);
      else startsAt.set(s.start, [i]);
    });
    const points = Array.from(
      new Set<number>([0, textLen, ...valid.flatMap((s) => [s.start, s.end])]),
    ).sort((a, b) => a - b);

    const heap = new SweepHeap();
    for (let i = 0; i < points.length - 1; i++) {
      const a = points[i];
      const b = points[i + 1];
      const starts = startsAt.get(a);
      if (starts) {
        for (const idx of starts) {
          const s = valid[idx];
          heap.push({ span: s.end - s.start, negIndex: -idx, end: s.end, index: idx });
        }
      }
      while (heap.size > 0 && heap.peek().end <= a) heap.pop(); // closed → no longer covering
      if (heap.size > 0 && effectiveMask(valid[heap.peek().index], maskByType)) raw.push([a, b]);
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
