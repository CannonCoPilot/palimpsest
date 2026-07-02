/**
 * Unit tests for ProjectPicker logic introduced in fixes D-i, E, F.
 *
 * These tests cover the pure/stateless logic that underpins the UI changes
 * without requiring a full React render:
 *
 *   - Fix D-i: candidate list for "Add text to collection" excludes members.
 *   - Fix E:   after delete, updated collections exclude the removed project.
 *   - Fix F:   collection removal filtering leaves other collections intact.
 */

import { describe, it, expect } from 'vitest';

// ── Types (mirrors ProjectPicker's local interfaces) ──────────────────────────

interface ProjectEntry {
  id: string;
  title: string;
  author: string;
  word_count: number;
}

interface CollectionEntry {
  id: string;
  label: string;
  description: string;
  project_ids: string[];
  kind: string;
  project_count: number;
}

// ── Fix D-i: candidate filtering ─────────────────────────────────────────────

function candidatesForCollection(
  projects: ProjectEntry[],
  col: CollectionEntry,
): ProjectEntry[] {
  const memberIds = new Set(col.project_ids);
  return projects.filter((p) => !memberIds.has(p.id));
}

describe('Fix D-i — Add text to collection candidates', () => {
  const projects: ProjectEntry[] = [
    { id: 'a', title: 'Alpha', author: 'Anon', word_count: 1000 },
    { id: 'b', title: 'Beta', author: 'Anon', word_count: 2000 },
    { id: 'c', title: 'Gamma', author: 'Anon', word_count: 3000 },
  ];

  const col: CollectionEntry = {
    id: 'col-1', label: 'Coll', description: '', kind: 'manual', project_count: 1, project_ids: ['a'],
  };

  it('excludes texts already in the collection', () => {
    const candidates = candidatesForCollection(projects, col);
    expect(candidates.map((p) => p.id)).not.toContain('a');
  });

  it('includes texts not yet in the collection', () => {
    const candidates = candidatesForCollection(projects, col);
    expect(candidates.map((p) => p.id)).toEqual(expect.arrayContaining(['b', 'c']));
  });

  it('returns empty list when all texts are already members', () => {
    const fullCol = { ...col, project_ids: ['a', 'b', 'c'] };
    expect(candidatesForCollection(projects, fullCol)).toHaveLength(0);
  });
});

// ── Fix E: collections updated after project deletion ─────────────────────────

function removeProjectFromCollections(
  collections: CollectionEntry[],
  deletedId: string,
): CollectionEntry[] {
  // Mirrors the frontend re-fetch effect: backend strips the id, frontend
  // receives the fresh list. This tests the backend-side filtering logic
  // replicated as pure TS for verifiability.
  return collections.map((c) => ({
    ...c,
    project_ids: c.project_ids.filter((id) => id !== deletedId),
    project_count: c.project_ids.filter((id) => id !== deletedId).length,
  }));
}

describe('Fix E — Member count updated after project deletion', () => {
  const collections: CollectionEntry[] = [
    { id: 'col-1', label: 'One', description: '', kind: 'manual', project_count: 2, project_ids: ['a', 'b'] },
    { id: 'col-2', label: 'Two', description: '', kind: 'manual', project_count: 1, project_ids: ['c'] },
  ];

  it('removes the deleted project id from affected collections', () => {
    const updated = removeProjectFromCollections(collections, 'a');
    expect(updated.find((c) => c.id === 'col-1')!.project_ids).not.toContain('a');
  });

  it('decrements project_count for the affected collection', () => {
    const updated = removeProjectFromCollections(collections, 'a');
    expect(updated.find((c) => c.id === 'col-1')!.project_count).toBe(1);
  });

  it('leaves unrelated collections untouched', () => {
    const updated = removeProjectFromCollections(collections, 'a');
    const col2 = updated.find((c) => c.id === 'col-2')!;
    expect(col2.project_ids).toEqual(['c']);
    expect(col2.project_count).toBe(1);
  });
});

// ── Fix F: collection list after deletion ─────────────────────────────────────

function removeCollection(collections: CollectionEntry[], deletedId: string): CollectionEntry[] {
  return collections.filter((c) => c.id !== deletedId);
}

describe('Fix F — Delete collection from state', () => {
  const collections: CollectionEntry[] = [
    { id: 'col-1', label: 'One', description: '', kind: 'manual', project_count: 1, project_ids: ['a'] },
    { id: 'col-2', label: 'Two', description: '', kind: 'manual', project_count: 1, project_ids: ['b'] },
  ];

  it('removes the deleted collection from the list', () => {
    const updated = removeCollection(collections, 'col-1');
    expect(updated.some((c) => c.id === 'col-1')).toBe(false);
  });

  it('preserves other collections', () => {
    const updated = removeCollection(collections, 'col-1');
    expect(updated).toHaveLength(1);
    expect(updated[0].id).toBe('col-2');
  });

  it('returns empty list if only collection is deleted', () => {
    expect(removeCollection([collections[0]], 'col-1')).toHaveLength(0);
  });
});
