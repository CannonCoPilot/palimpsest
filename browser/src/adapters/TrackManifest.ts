/**
 * Track rendering manifest loader and types.
 */

export interface TrackManifest {
  trackName: string;
  bodyType: string;
  evidenceLevel?: string;
  colorScheme: {
    primary: string;
    secondary: string;
    scale?: Record<string, string>;
  };
  textViewRendering: 'highlight' | 'underline' | 'margin-marker';
  overviewBarRendering: {
    type: 'density-barcode';
    color: string;
  };
  dedicatedView?: string;
}

const DEFAULT_MANIFEST: TrackManifest = {
  trackName: 'unknown',
  bodyType: '',
  colorScheme: { primary: '#888888', secondary: '#cccccc' },
  textViewRendering: 'highlight',
  overviewBarRendering: { type: 'density-barcode', color: '#888888' },
};

export async function loadTrackManifest(url: string): Promise<TrackManifest> {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      return { ...DEFAULT_MANIFEST };
    }
    const data = await response.json();
    return { ...DEFAULT_MANIFEST, ...data } as TrackManifest;
  } catch {
    return { ...DEFAULT_MANIFEST };
  }
}
