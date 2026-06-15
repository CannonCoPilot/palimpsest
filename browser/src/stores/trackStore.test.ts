import { describe, it, expect, beforeEach } from 'vitest';
import { useTrackStore, type TrackState } from './trackStore';
import type { TrackManifest } from '../adapters/TrackManifest';

function makeTrack(name: string, visible = true): TrackState {
  return {
    name,
    visible,
    manifest: {} as TrackManifest,
    annotationCount: 0,
    confidenceThreshold: 0,
    displayMode: 'dense',
  };
}

describe('trackStore', () => {
  beforeEach(() => {
    useTrackStore.setState({ tracks: {}, trackOrder: [] });
  });

  it('setTracks derives a sorted order that excludes segments', () => {
    useTrackStore.getState().setTracks({
      entities: makeTrack('entities'),
      segments: makeTrack('segments'),
      alphabet: makeTrack('alphabet'),
    });
    expect(useTrackStore.getState().trackOrder).toEqual(['alphabet', 'entities']);
  });

  it('toggleTrack flips visibility for the named track', () => {
    useTrackStore.getState().setTracks({ entities: makeTrack('entities', true) });
    useTrackStore.getState().toggleTrack('entities');
    expect(useTrackStore.getState().tracks.entities.visible).toBe(false);
  });

  it('toggleTrack is a no-op for an unknown track', () => {
    useTrackStore.getState().setTracks({ entities: makeTrack('entities', true) });
    useTrackStore.getState().toggleTrack('does-not-exist');
    expect(useTrackStore.getState().tracks.entities.visible).toBe(true);
  });

  it('toggleTrackByIndex toggles the i-th sorted non-segment track (1-based)', () => {
    useTrackStore.getState().setTracks({
      bravo: makeTrack('bravo', true),
      alpha: makeTrack('alpha', true),
    });
    // sorted non-segment names: ['alpha', 'bravo'] → index 1 = alpha
    useTrackStore.getState().toggleTrackByIndex(1);
    expect(useTrackStore.getState().tracks.alpha.visible).toBe(false);
    expect(useTrackStore.getState().tracks.bravo.visible).toBe(true);
  });

  it('setConfidenceThreshold updates only the named track', () => {
    useTrackStore.getState().setTracks({ a: makeTrack('a'), b: makeTrack('b') });
    useTrackStore.getState().setConfidenceThreshold('a', 0.7);
    expect(useTrackStore.getState().tracks.a.confidenceThreshold).toBe(0.7);
    expect(useTrackStore.getState().tracks.b.confidenceThreshold).toBe(0);
  });

  it('setDisplayMode updates only the named track', () => {
    useTrackStore.getState().setTracks({ a: makeTrack('a') });
    useTrackStore.getState().setDisplayMode('a', 'inline');
    expect(useTrackStore.getState().tracks.a.displayMode).toBe('inline');
  });
});
