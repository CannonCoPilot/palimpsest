// The FR-13 render dispatch loop. Each layer is drawn by its `rendering.track_view` family — never
// by its label — so producing the Nth chunk layer or a new band-type track adds a lane with no new
// code. The dispatcher is the single switch; the band/embedding renderers below fetch their own
// geometry lazily (the /analysis/status row carries only the lightweight descriptor + stats).
import { useEffect, useState } from 'react';
import { laneKind, type LayerRendering, type LayerStatus } from './types';

const LANE_W = 520;
const LANE_H = 16;

function LaneFrame({ width, height, children, label, trackView }: {
  width: number; height: number; children: React.ReactNode; label: string; trackView?: string;
}) {
  return (
    <svg width={width} height={height} role="img" aria-label={label} data-track-view={trackView}
      className="rounded-sm">
      <rect width={width} height={height} fill="#f8f8f8" />
      {children}
    </svg>
  );
}

function LaneMessage({ width, height, text, tone }: {
  width: number; height: number; text: string; tone: 'muted' | 'warn';
}) {
  return (
    <div
      role="status"
      className={`flex items-center px-2 text-[0.7em] ${tone === 'warn' ? 'text-[var(--color-warning,#b45309)]' : 'text-[var(--color-text-muted)]'}`}
      style={{ width, height, background: '#f8f8f8' }}
    >
      {text}
    </div>
  );
}

interface BandManifest {
  segment_offsets?: [number, number][];
}

// Any *-band layer: an SVG ribbon of segment rects from the layer's static manifest segment_offsets.
// One renderer for the whole band family (chunk-band, repeat-band, …); color comes from the
// descriptor, so a new band type needs no new branch.
export function BandLane({ projectId, trackName, label, rendering, width = LANE_W, height = LANE_H }: {
  projectId: string; trackName: string; label: string;
  rendering?: LayerRendering | null; width?: number; height?: number;
}) {
  const [offsets, setOffsets] = useState<[number, number][] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setOffsets(null); setError(null);
    fetch(`/data/${projectId}/signals/${trackName}_${label}.json`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((m: BandManifest) => { if (!cancelled) setOffsets(m.segment_offsets ?? []); })
      .catch((e) => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, [projectId, trackName, label]);

  const color = rendering?.overviewBarRendering?.color ?? '#6366F1';
  if (error) return <LaneMessage width={width} height={height} text={`load failed: ${error}`} tone="warn" />;
  if (!offsets) return <LaneMessage width={width} height={height} text="loading…" tone="muted" />;
  // Standalone lane (not overlaid on text): normalize by the last segment end so the ribbon fills
  // the lane. segment_offsets are analyzable-text coords (the first chunk starts past masked front
  // matter), so a 0-based document length would mis-scale — the last end is the right domain.
  const maxEnd = offsets.length ? offsets[offsets.length - 1][1] : 1;
  return (
    <LaneFrame width={width} height={height} trackView={rendering?.track_view}
      label={`${trackName} ${label} band, ${offsets.length} segments`}>
      {offsets.map(([s, e], i) => {
        const x = (s / maxEnd) * width;
        const w = Math.max(1, ((e - s) / maxEnd) * width);
        return <rect key={i} x={x} y={0} width={w} height={height} fill={color}
          fillOpacity={0.72} stroke="#fff" strokeWidth={0.25} />;
      })}
    </LaneFrame>
  );
}

// ColorBrewer Blues two-stop ramp (light→dark). Hand-rolled to keep the lane zero-dep, matching the
// repo's no-viz-lib idiom; t is the value's normalized position in the lane's [min,max].
function rampBlue(t: number): string {
  const c = Math.max(0, Math.min(1, t));
  const lerp = (a: number, b: number) => Math.round(a + (b - a) * c);
  const r = lerp(0xf7, 0x08), g = lerp(0xfb, 0x30), b = lerp(0xff, 0x6b);
  return `rgb(${r},${g},${b})`;
}

// embedding-lane: a colored strip, one cell per chunk, fed by the P3 lane endpoint's scalar
// (Float32Array, one value per chunk) mapped through a sequential ramp.
export function EmbeddingLane({ projectId, label, rendering, width = LANE_W, height = LANE_H }: {
  projectId: string; label: string; rendering?: LayerRendering | null; width?: number; height?: number;
}) {
  const [values, setValues] = useState<number[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const encoding = rendering?.encoding ?? 'nn-density';

  useEffect(() => {
    let cancelled = false;
    setValues(null); setError(null);
    fetch(`/api/projects/${projectId}/embedding/${label}/lane?encoding=${encodeURIComponent(encoding)}`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.arrayBuffer(); })
      .then((buf) => { if (!cancelled) setValues(Array.from(new Float32Array(buf))); })
      .catch((e) => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, [projectId, label, encoding]);

  if (error) return <LaneMessage width={width} height={height} text={`load failed: ${error}`} tone="warn" />;
  if (!values) return <LaneMessage width={width} height={height} text="loading…" tone="muted" />;
  const n = values.length || 1;
  let min = Infinity, max = -Infinity;
  for (const v of values) { if (v < min) min = v; if (v > max) max = v; }
  const span = max - min || 1;
  return (
    <LaneFrame width={width} height={height} trackView={rendering?.track_view}
      label={`embedding ${label} lane (${encoding}), ${values.length} chunks`}>
      {values.map((v, i) => {
        const x = (i / n) * width;
        const w = Math.max(1, width / n);
        return <rect key={i} x={x} y={0} width={w} height={height} fill={rampBlue((v - min) / span)} />;
      })}
    </LaneFrame>
  );
}

// The dispatcher. Switches on the rendering descriptor's *family*, never the label. An unknown view
// renders an honest placeholder (not a crash, not a silent blank) so a future track_view is visible
// as "unsupported here" rather than mysteriously missing.
export function LayerLane({ projectId, trackName, layer, width = LANE_W, height = LANE_H }: {
  projectId: string; trackName: string; layer: LayerStatus; width?: number; height?: number;
}) {
  const kind = laneKind(layer.rendering);
  switch (kind) {
    case 'band':
      return <BandLane projectId={projectId} trackName={trackName} label={layer.label}
        rendering={layer.rendering} width={width} height={height} />;
    case 'embedding-lane':
      return <EmbeddingLane projectId={projectId} label={layer.label}
        rendering={layer.rendering} width={width} height={height} />;
    default:
      return (
        <LaneMessage width={width} height={height}
          text={`no lane renderer for "${layer.rendering?.track_view ?? 'unknown'}"`} tone="muted" />
      );
  }
}

export { LANE_W, LANE_H };
