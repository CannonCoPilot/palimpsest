import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useProjectLabelStore, memberLabel, shortSlug, type ProjectLabel } from './projectLabelStore';

const LABELS: Record<string, ProjectLabel> = {
  'douay-rheims-…-chapter-in-book-0047': { title: 'Douay-Rheims -- Matthew', author: 'Douay-Rheims (1582-1610)' },
};

describe('memberLabel / shortSlug', () => {
  it('prefers the project title', () => {
    expect(memberLabel(LABELS, 'douay-rheims-…-chapter-in-book-0047')).toBe('Douay-Rheims -- Matthew');
  });

  it('falls back to a shortened slug when unknown', () => {
    const id = 'the-holy-bible-king-james-version-of-1611-1769-chapter-in-book-luke';
    expect(memberLabel({}, id)).toBe(shortSlug(id));
    expect(shortSlug(id)).toContain('…');
    expect(shortSlug(id).length).toBeLessThan(id.length);
  });

  it('leaves short ids intact', () => {
    expect(shortSlug('alpha')).toBe('alpha');
  });
});

describe('projectLabelStore.ensureLoaded', () => {
  beforeEach(() => {
    useProjectLabelStore.setState({ labels: {}, loaded: false });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches /api/projects once and builds the id→title map', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ id: 'x', title: 'King James -- Luke', author: 'KJV' }],
    });
    vi.stubGlobal('fetch', fetchMock);

    useProjectLabelStore.getState().ensureLoaded();
    useProjectLabelStore.getState().ensureLoaded(); // second call is a no-op (loaded guard)

    // fetch → r.json() → set() is a multi-step microtask chain; poll until it lands.
    await vi.waitFor(() =>
      expect(useProjectLabelStore.getState().labels.x?.title).toBe('King James -- Luke'),
    );
    expect(fetchMock).toHaveBeenCalledTimes(1); // the dup call was a no-op
  });
});
