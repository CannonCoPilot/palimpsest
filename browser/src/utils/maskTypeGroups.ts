/**
 * Browser-tab grouping of mask-element types into related "gene-track" groups.
 *
 * Each group becomes its own lane in the Browser tab; in 'detail' display mode a lane
 * expands so every present mask-type gets its own sub-row, with a dropdown to toggle
 * each type on/off. The partition mirrors the backend's role-grouped vocabulary
 * (core/palimpsest/layout.py SECTION_TYPES) so a type's color family signals its group.
 *
 * Partition updated 2026-06-22 (user): two lanes — Structure and Content. `header` (name
 * lines: book / chapter / section titles + testament dividers) joins Structure; `heading`
 * (the editorial argument/summary that follows a header) joins Content. The old Headings and
 * Notes groups are dissolved — Notes' types fold into Content. Explicit orders given below;
 * remaining types (absent from the bible, kept for other works) trail the explicit order.
 */
import type { W3CAnnotation } from '../adapters/AnnotationAdapter';

export interface MaskTypeGroup {
  key: string;
  label: string;
  types: string[];
}

export const MASK_TYPE_GROUPS: MaskTypeGroup[] = [
  {
    key: 'structure',
    label: 'Structure',
    // User order: volume, book, section, header (the nesting backbone + name-marker, blue
    // family) lead, then front_matter, title_page, contents, appendix, glossary — then the
    // remaining structural/matter types (other works only).
    types: [
      'volume', 'book', 'section', 'header', 'front_matter', 'title_page', 'contents',
      'appendix', 'glossary',
      'body', 'part', 'copyright', 'dedication', 'foreword',
      'back_matter', 'afterword', 'acknowledgments', 'about_author',
      'index', 'bibliography', 'addendum', 'insert', 'colophon',
    ],
  },
  {
    key: 'content',
    label: 'Content',
    // User order: preface, introduction, chapter, heading, footnotes — then the remaining
    // content + former-Notes types (letter/poetry/translation, endnotes/commentary/etc.).
    types: [
      'preface', 'introduction', 'chapter', 'heading', 'footnotes',
      'letter', 'poetry', 'translation',
      'endnotes', 'commentary', 'discussion', 'epigraph', 'chapter_heading',
    ],
  },
];

// NOTE: verses are NOT an elements-track type. They live in a compact, lazy-loaded
// coordinate index (verses.jsonl → verseStore) and render via BrowserView's VersesLane,
// gated to viewport < VERSE_ZOOM_MAX_CHARS — so there is no 'verse' group here.

const OTHER_GROUP_KEY = 'other';

const TYPE_TO_GROUP: Record<string, string> = Object.fromEntries(
  MASK_TYPE_GROUPS.flatMap((g) => g.types.map((t) => [t, g.key])),
);

/** Group key for a mask-type; unrecognized (custom) types fall into the 'other' group. */
export function groupForType(type: string): string {
  return TYPE_TO_GROUP[type] ?? OTHER_GROUP_KEY;
}

export interface PresentType {
  type: string;
  label: string;
  color: string;
  count: number;
}

export interface ElementGroupData {
  key: string;
  label: string;
  presentTypes: PresentType[]; // mask-types actually present, in group-declared order
  annotations: W3CAnnotation[];
}

const DEFAULT_ELEMENT_COLOR = '#5ac8fa';

function readElementType(ann: W3CAnnotation): string | null {
  const et = (ann.body as Record<string, unknown>)['palimpsest:elementType'];
  return typeof et === 'string' ? et : null;
}

function readElementColor(ann: W3CAnnotation): string {
  const c = (ann.body as Record<string, unknown>)['palimpsest:color'];
  return typeof c === 'string' ? c : DEFAULT_ELEMENT_COLOR;
}

/**
 * Bucket the flat 'elements' annotations into their groups. Returns only non-empty
 * groups, in MASK_TYPE_GROUPS order (then an 'Other' group for any custom types),
 * each carrying its present mask-types (type-declared order) and its annotations.
 */
export function buildElementGroups(annotations: W3CAnnotation[]): ElementGroupData[] {
  const byGroup = new Map<string, W3CAnnotation[]>();
  const typeMeta = new Map<string, { color: string; count: number }>();

  for (const ann of annotations) {
    const et = readElementType(ann);
    if (et === null) continue;
    const gk = groupForType(et);
    (byGroup.get(gk) ?? byGroup.set(gk, []).get(gk)!).push(ann);
    const cur = typeMeta.get(et);
    if (cur) cur.count += 1;
    else typeMeta.set(et, { color: readElementColor(ann), count: 1 });
  }

  const ordered: MaskTypeGroup[] = [...MASK_TYPE_GROUPS];
  const otherAnns = byGroup.get(OTHER_GROUP_KEY) ?? [];
  if (otherAnns.length > 0) {
    const otherTypes = Array.from(new Set(otherAnns.map(readElementType).filter((t): t is string => t !== null)));
    ordered.push({ key: OTHER_GROUP_KEY, label: 'Other', types: otherTypes });
  }

  const out: ElementGroupData[] = [];
  for (const g of ordered) {
    const anns = byGroup.get(g.key);
    if (!anns || anns.length === 0) continue;
    const presentTypes: PresentType[] = g.types
      .filter((t) => typeMeta.has(t))
      .map((t) => ({
        type: t,
        label: t.replace(/_/g, ' '),
        color: typeMeta.get(t)!.color,
        count: typeMeta.get(t)!.count,
      }));
    out.push({ key: g.key, label: g.label, presentTypes, annotations: anns });
  }
  return out;
}
