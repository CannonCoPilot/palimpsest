/**
 * Signal adapter — loads raw Float32 binary signals with JSON manifests.
 */

export interface SignalManifest {
  type: string;
  name: string;
  source: string;
  reference_sha256: string;
  dimensions: number[];
  dtype: string;
  byte_order: string;
  data_file: string;
  segment_offsets: number[][];
  metadata: Record<string, unknown>;
}

export interface LoadedSignal {
  manifest: SignalManifest;
  data: Float32Array;
}

export async function loadSignal(manifestUrl: string): Promise<LoadedSignal> {
  const manifestResponse = await fetch(manifestUrl);
  if (!manifestResponse.ok) {
    throw new Error(`Failed to load signal manifest: ${manifestResponse.status}`);
  }
  const manifest: SignalManifest = await manifestResponse.json();

  const baseUrl = manifestUrl.substring(0, manifestUrl.lastIndexOf('/') + 1);
  const dataUrl = baseUrl + manifest.data_file;

  const dataResponse = await fetch(dataUrl);
  if (!dataResponse.ok) {
    throw new Error(`Failed to load signal data: ${dataResponse.status}`);
  }
  const buffer = await dataResponse.arrayBuffer();
  const data = new Float32Array(buffer);

  return { manifest, data };
}
