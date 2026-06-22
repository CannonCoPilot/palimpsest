/**
 * Browser-tab grouping of mask-element types into related "gene-track" groups.
 *
 * Each group becomes its own lane in the Browser tab; in 'detail' display mode a lane
 * expands so every present mask-type gets its own sub-row, with a dropdown to toggle
 * each type on/off. The partition mirrors the backend's role-grouped vocabulary
 * (core/palimpsest/layout.py SECTION_TYPES) so a type's color family signals its group.
 *
 * Partition ratified with the user (2026-06-21): chapter/letter live with Content,
 * commentary/preface/introduction/discussion live with Notes.
 */
import type { W3CAnnotation } from '../adapters/AnnotationAdapter';

export interface MaskTypeGroup {
  key: string;
  label: string;
  types: string[];
}

export const MASK_TYPE_GROUPS: MaskTypeGroup[] = [
  { key: 'structure', label: 'Structure', types: ['body', 'volume', 'book', 'part'] },
  { key: 'content', label: 'Content', types: ['chapter', 'letter', 'poetry', 'translation'] },
  { key: 'headings', label: 'Headings', types: ['header', 'chapter_heading', 'epigraph'] },
  {
    key: 'notes',
    label: 'Notes',
    types: ['footnotes', 'endnotes', 'commentary', 'preface', 'introduction', 'discussion'],
  },
  {
    key: 'front_matter',
    label: 'Front Matter',
    types: ['front_matter', 'title_page', 'copyright', 'contents', 'dedication', 'foreword'],
  },
  {
    key: 'back_matter',
    label: 'Back Matter',
    types: [
      'back_matter', 'afterword', 'acknowledgments', 'about_author', 'glossary',
      'index', 'bibliography', 'appendix', 'addendum', 'insert', 'colophon',
    ],
  },
];

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
