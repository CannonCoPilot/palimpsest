import { describe, it, expect, beforeEach } from 'vitest';
import { useCollectionStore, activeCollection, type CollectionOption } from './collectionStore';

const A: CollectionOption = { id: 'a', label: 'A', project_ids: ['x', 'y'], roles: { x: 'root' } };
const B: CollectionOption = { id: 'b', label: 'B', project_ids: ['p', 'q'] };

describe('collectionStore', () => {
  beforeEach(() => {
    useCollectionStore.setState({ collections: [], collectionId: '' });
  });

  it('holds the fetched list and selection across reads (the C4 re-mount fix)', () => {
    useCollectionStore.getState().setCollections([A, B]);
    useCollectionStore.getState().setCollectionId('b');
    expect(useCollectionStore.getState().collections).toHaveLength(2);
    expect(useCollectionStore.getState().collectionId).toBe('b');
  });

  it('activeCollection resolves the selected option, incl. its roles', () => {
    useCollectionStore.setState({ collections: [A, B], collectionId: 'a' });
    const active = activeCollection(useCollectionStore.getState());
    expect(active?.id).toBe('a');
    expect(active?.roles).toEqual({ x: 'root' });
  });

  it('activeCollection is undefined when nothing selected', () => {
    useCollectionStore.setState({ collections: [A], collectionId: '' });
    expect(activeCollection(useCollectionStore.getState())).toBeUndefined();
  });
});
