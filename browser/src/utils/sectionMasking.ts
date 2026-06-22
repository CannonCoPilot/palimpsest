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
export function computeMaskedIntervals(
  sections: LayoutSection[],
  maskByType: Record<string, boolean>,
  textLen: number,
  extraMasked: ReadonlyArray<readonly [number, number]> = [],
): Array<[number, number]> {
  const raw: Array<[number, number]> = [];

  const valid = sections.filter((s) => s.start >= 0 && s.start < s.end && s.end <= textLen);
  if (valid.length > 0) {
    const points = Array.from(
      new Set<number>([0, textLen, ...valid.flatMap((s) => [s.start, s.end])]),
    ).sort((a, b) => a - b);

    for (let i = 0; i < points.length - 1; i++) {
      const a = points[i];
      const b = points[i + 1];
      if (a >= b) continue;
      const covering = valid.filter((s) => s.start <= a && s.end >= b);
      if (covering.length === 0) continue; // uncovered = unmasked
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

/** True if [start,end)'s midpoint lies inside a masked interval. */
export function rangeIsMasked(intervals: Array<[number, number]>, start: number, end: number): boolean {
  const mid = Math.floor((start + end) / 2);
  return intervals.some(([a, b]) => a <= mid && mid < b);
}
