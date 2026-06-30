// FR-13 layer rendering contract. Mirrors server.py `_layer_status_entries` (the per-layer rows
// nested in /analysis/status) and the producer tracks' `rendering` descriptors. The frontend draws
// any layer by `rendering.track_view`, so a new layer — or a whole new band-type track — renders
// with no per-label code (Vision §3.4 plural-safety).

export interface LayerRendering {
  track_view: string; // "chunk-band" | "repeat-band" | "embedding-lane" | …
  // *-band layers (chunking, repeat_mask, repeat): a color for the ribbon.
  overviewBarRendering?: { type: string; color?: string };
  // embedding-lane: the scalar encoding (e.g. "nn-density") and the on-read 2-D projection route.
  encoding?: string;
  projection_ref?: string;
}

export interface LayerRunInfo {
  clamped?: string[];
  effective?: Record<string, number | null>;
  requested?: Record<string, number | null>;
  method?: string;
  posteriorType?: string;
}

export interface LayerStatus {
  label: string;
  status: 'computed';
  capability?: Record<string, unknown> | null;
  stats?: Record<string, unknown> | null;
  rendering?: LayerRendering | null;
  runInfo?: LayerRunInfo;
}

// A layer plus the track that produced it — the track name resolves the static signals manifest
// path (/data/{id}/signals/{trackName}_{label}.json) the band renderer fetches its geometry from.
export interface LayerRef {
  trackName: string;
  layer: LayerStatus;
}

export const layerKey = (ref: LayerRef): string => `${ref.trackName}:${ref.layer.label}`;

// Family dispatch is the whole plural-safety mechanism: every `*-band` view shares one renderer,
// `embedding-lane` its own. Keying on the *family* (not the exact track_view string) means the 5th
// chunk layer and a brand-new band-type layer both render with zero new code.
export type LaneKind = 'band' | 'embedding-lane' | 'unknown';

export function laneKind(rendering: LayerRendering | null | undefined): LaneKind {
  const tv = rendering?.track_view;
  if (!tv) return 'unknown';
  if (tv.endsWith('-band')) return 'band';
  if (tv === 'embedding-lane') return 'embedding-lane';
  return 'unknown';
}

// Flatten the /analysis/status track rows into a single layer list (track name carried along).
// Only computed layers are rendered; a track row with no `layers` (non-layer-keyed track) is skipped.
export function collectLayers(
  tracks: { name: string; layers?: LayerStatus[] }[],
): LayerRef[] {
  const out: LayerRef[] = [];
  for (const t of tracks) {
    for (const layer of t.layers ?? []) out.push({ trackName: t.name, layer });
  }
  return out;
}
