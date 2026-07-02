/**
 * Tests for genre-division color resolution and apocrypha indicator detection.
 * Covers the two new Bible content-type layer features:
 *   1. resolveElementColor returns distinct hues for each of the 7 genre_division genres.
 *   2. isApocrypha correctly identifies deuterocanonical/apocryphal book annotations.
 */
import { describe, it, expect } from 'vitest';
import { GENRE_COLORS, resolveElementColor, isApocrypha } from './maskTypeGroups';
import type { W3CAnnotation } from '../adapters/AnnotationAdapter';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeAnn(elementType: string, extra: Record<string, unknown> = {}): W3CAnnotation {
  return {
    '@context': 'http://www.w3.org/ns/anno.jsonld',
    type: 'Annotation',
    id: 'urn:test:ann',
    body: {
      type: 'palimpsest:ElementAnnotation',
      purpose: 'classifying',
      value: 'Test',
      'palimpsest:elementType': elementType,
      'palimpsest:color': '#e0a458', // default genre_division SECTION_COLORS value
      ...extra,
    },
    target: {
      source: 'urn:test:source',
      selector: { type: 'TextPositionSelector', start: 0, end: 100 },
    },
    creator: { name: 'test' },
    confidence: 1,
    evidence_level: 'E1',
  } as unknown as W3CAnnotation;
}

// ---------------------------------------------------------------------------
// Genre color map — basic sanity
// ---------------------------------------------------------------------------

describe('GENRE_COLORS', () => {
  const EXPECTED_GENRES = [
    'Law', 'Historical', 'Wisdom-poetry',
    'Prophets-Major', 'Prophets-Minor', 'Gospels', 'Epistles',
  ];

  it('defines exactly 7 genres', () => {
    expect(Object.keys(GENRE_COLORS)).toHaveLength(7);
  });

  it('covers all required genre labels', () => {
    for (const g of EXPECTED_GENRES) {
      expect(GENRE_COLORS).toHaveProperty(g);
    }
  });

  it('all values are valid hex color strings', () => {
    for (const [genre, color] of Object.entries(GENRE_COLORS)) {
      expect(color, `${genre} color`).toMatch(/^#[0-9a-fA-F]{6}$/);
    }
  });

  it('all 7 colors are distinct', () => {
    const colors = Object.values(GENRE_COLORS).map((c) => c.toLowerCase());
    const unique = new Set(colors);
    expect(unique.size).toBe(7);
  });
});

// ---------------------------------------------------------------------------
// resolveElementColor — genre_division override
// ---------------------------------------------------------------------------

describe('resolveElementColor — genre_division', () => {
  it('returns the genre-specific color for a genre_division annotation', () => {
    const ann = makeAnn('genre_division', { 'palimpsest:genre': 'Gospels' });
    expect(resolveElementColor(ann, '#000')).toBe(GENRE_COLORS['Gospels']);
  });

  it('returns distinct colors for each of the 7 genres', () => {
    const genres = Object.keys(GENRE_COLORS);
    const results = genres.map((g) =>
      resolveElementColor(makeAnn('genre_division', { 'palimpsest:genre': g }), '#000'),
    );
    expect(new Set(results).size).toBe(7);
    for (const [i, g] of genres.entries()) {
      expect(results[i]).toBe(GENRE_COLORS[g]);
    }
  });

  it('falls back to palimpsest:color when genre field is absent from genre_division', () => {
    const ann = makeAnn('genre_division'); // no palimpsest:genre
    expect(resolveElementColor(ann, '#fallback')).toBe('#e0a458');
  });

  it('falls back to palimpsest:color when genre is unrecognised', () => {
    const ann = makeAnn('genre_division', { 'palimpsest:genre': 'SomeFutureGenre' });
    expect(resolveElementColor(ann, '#fallback')).toBe('#e0a458');
  });

  it('uses palimpsest:color for non-genre_division types (e.g. book)', () => {
    const ann = makeAnn('book', { 'palimpsest:color': '#123456' });
    expect(resolveElementColor(ann, '#fallback')).toBe('#123456');
  });

  it('uses the provided fallback when no palimpsest:color is set', () => {
    const ann = makeAnn('book');
    // Remove the palimpsest:color that makeAnn injects
    delete (ann.body as Record<string, unknown>)['palimpsest:color'];
    expect(resolveElementColor(ann, '#myfallback')).toBe('#myfallback');
  });
});

// ---------------------------------------------------------------------------
// isApocrypha
// ---------------------------------------------------------------------------

describe('isApocrypha', () => {
  it('returns true when palimpsest:apocrypha is true', () => {
    const ann = makeAnn('book', { 'palimpsest:apocrypha': true });
    expect(isApocrypha(ann)).toBe(true);
  });

  it('returns false when palimpsest:apocrypha is absent', () => {
    expect(isApocrypha(makeAnn('book'))).toBe(false);
  });

  it('returns false when palimpsest:apocrypha is false', () => {
    const ann = makeAnn('book', { 'palimpsest:apocrypha': false });
    expect(isApocrypha(ann)).toBe(false);
  });

  it('returns false when palimpsest:apocrypha is a string "true" (not boolean)', () => {
    // Backend emits booleans; guard against accidental JSON coercion.
    const ann = makeAnn('book', { 'palimpsest:apocrypha': 'true' });
    expect(isApocrypha(ann)).toBe(false);
  });

  it('returns true for genre_division annotations that are also apocrypha', () => {
    const ann = makeAnn('genre_division', {
      'palimpsest:genre': 'Wisdom-poetry',
      'palimpsest:apocrypha': true,
    });
    expect(isApocrypha(ann)).toBe(true);
  });
});
