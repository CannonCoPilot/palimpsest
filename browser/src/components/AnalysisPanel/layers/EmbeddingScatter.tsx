// The Representations view of an embedding layer: its 2-D projection as a scatter, mirroring
// DotplotView's canvas idiom (fetch LE float32 bytes → Float32Array → draw). The projection is
// computed on-read by the P3 endpoint named in the layer's rendering.projection_ref, so this is a
// pure consumer — no persisted file, no new dep. The in-text presence of the same embedding is its
// EmbeddingLane; the scatter is its bird's-eye view.
import { useEffect, useRef, useState } from 'react';
import type { LayerStatus } from './types';

const SIZE = 320;
const PAD = 12;

export function EmbeddingScatter({ projectId, layer, size = SIZE }: {
  projectId: string; layer: LayerStatus; size?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [points, setPoints] = useState<Float32Array | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ref = layer.rendering?.projection_ref
    ?? `/api/projects/${projectId}/embedding/${layer.label}/projection`;

  useEffect(() => {
    let cancelled = false;
    setPoints(null); setError(null);
    fetch(ref)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.arrayBuffer(); })
      .then((buf) => { if (!cancelled) setPoints(new Float32Array(buf)); })
      .catch((e) => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, [ref]);

  const nPoints = points ? Math.floor(points.length / 2) : 0;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !points || nPoints === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return; // jsdom / no-2d-context: the caption still reports the point count.
    ctx.clearRect(0, 0, size, size);
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (let i = 0; i < nPoints; i++) {
      const x = points[i * 2], y = points[i * 2 + 1];
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
    const sx = (maxX - minX) || 1, sy = (maxY - minY) || 1;
    const inner = size - PAD * 2;
    for (let i = 0; i < nPoints; i++) {
      const px = PAD + ((points[i * 2] - minX) / sx) * inner;
      // Flip Y so the scatter reads in screen space; color by chunk index for a faint sequence cue.
      const py = PAD + (1 - (points[i * 2 + 1] - minY) / sy) * inner;
      ctx.fillStyle = `hsl(${Math.round((i / nPoints) * 270)}, 65%, 50%)`;
      ctx.beginPath();
      ctx.arc(px, py, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [points, nPoints, size]);

  return (
    <div className="inline-flex flex-col gap-1">
      <div className="text-[0.75em] text-[var(--color-text-muted)]">
        Embedding projection · <code>{layer.label.slice(0, 10)}</code>
      </div>
      {error ? (
        <div role="status" className="text-[0.75em] text-[var(--color-warning,#b45309)]"
          style={{ width: size, height: size }}>
          projection load failed: {error}
        </div>
      ) : (
        <canvas ref={canvasRef} width={size} height={size}
          role="img" aria-label={`embedding ${layer.label} projection scatter, ${nPoints} points`}
          className="border border-[var(--color-border)] rounded bg-white" />
      )}
      <div className="text-[0.7em] text-[var(--color-text-muted)]">
        {points ? `${nPoints} chunks` : 'loading…'}
      </div>
    </div>
  );
}
