/**
 * Pure geometry helpers shared by the import wizard's text views. Kept in a
 * JSX-free module so the component files (which import these) stay component-only
 * exports for React Fast Refresh.
 */

import type { LayoutSection } from '../../utils/sectionMasking';

// Resolve a click/right-click to an absolute character offset. Each rendered run
// carries data-off (its start); the caret API refines to the exact character.
export function offsetFromPoint(clientX: number, clientY: number, target: EventTarget | null): number | null {
  const el = target as HTMLElement | null;
  let span = el?.closest?.('[data-off]') as HTMLElement | null;
  if (!span && el) {
    // Click landed in a paragraph-margin gap or on a boundary handle — snap to the
    // vertically nearest run so point operations still work between runs (#28).
    const container = el.closest('[data-reader]');
    if (container) {
      let bestDist = Infinity;
      for (const cand of Array.from(container.querySelectorAll<HTMLElement>('[data-off]'))) {
        const r = cand.getBoundingClientRect();
        if (r.bottom < 0 || r.top > window.innerHeight) continue;
        const dy = clientY < r.top ? r.top - clientY : clientY > r.bottom ? clientY - r.bottom : 0;
        if (dy < bestDist) { bestDist = dy; span = cand; }
      }
    }
  }
  if (!span) return null;
  const base = Number(span.getAttribute('data-off'));
  if (Number.isNaN(base)) return null;
  const doc = document as Document & {
    caretRangeFromPoint?: (x: number, y: number) => Range | null;
    caretPositionFromPoint?: (x: number, y: number) => { offsetNode: Node; offset: number } | null;
  };
  try {
    if (doc.caretRangeFromPoint) {
      const r = doc.caretRangeFromPoint(clientX, clientY);
      if (r && span.contains(r.startContainer)) {
        const pre = document.createRange();
        pre.selectNodeContents(span);
        pre.setEnd(r.startContainer, r.startOffset);
        return base + pre.toString().length;
      }
    } else if (doc.caretPositionFromPoint) {
      const p = doc.caretPositionFromPoint(clientX, clientY);
      if (p && span.contains(p.offsetNode)) {
        const pre = document.createRange();
        pre.selectNodeContents(span);
        pre.setEnd(p.offsetNode, p.offset);
        return base + pre.toString().length;
      }
    }
  } catch {
    /* fall back to the run's start offset */
  }
  return base;
}

// Smallest section covering an offset (the most specific layer at that point).
export function deepestSectionAt(sections: LayoutSection[], off: number): LayoutSection | null {
  let best: LayoutSection | null = null;
  for (const s of sections) {
    if (off >= s.start && off < s.end && (!best || s.end - s.start < best.end - best.start)) best = s;
  }
  return best;
}
