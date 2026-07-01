/**
 * ComparativeDotplot — NxM heatmap showing cross-text similarity.
 * Reuses the canvas zoom/pan infrastructure from DotplotView,
 * generalized for non-square matrices.
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useProjectStore, getActiveProject, getSecondaryProject } from '../../stores/projectStore';
import { useComparisonStore } from '../../stores/comparisonStore';

const PALETTES: Record<string, number[][]> = {
  blues: [[239, 246, 255], [147, 197, 253], [59, 130, 246], [30, 64, 175], [30, 58, 138]],
  viridis: [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]],
};

function interpolateColor(value: number, palette: number[][]): [number, number, number] {
  const clamped = Math.max(0, Math.min(1, value));
  const idx = clamped * (palette.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, palette.length - 1);
  const t = idx - lo;
  return [
    Math.round(palette[lo][0] + t * (palette[hi][0] - palette[lo][0])),
    Math.round(palette[lo][1] + t * (palette[hi][1] - palette[lo][1])),
    Math.round(palette[lo][2] + t * (palette[hi][2] - palette[lo][2])),
  ];
}

interface Viewport { x: number; y: number; spanX: number; spanY: number }

export default function ComparativeDotplot() {
  const matrix = useComparisonStore((s) => s.crossSimilarityMatrix);
  const dims = useComparisonStore((s) => s.crossSimilarityDims);
  const loadMatrix = useComparisonStore((s) => s.loadCrossMatrix);
  const records = useComparisonStore((s) => s.alignmentRecords);
  const activeProject = useProjectStore(getActiveProject);
  const secondaryProject = useProjectStore(getSecondaryProject);
  const queryId = useProjectStore((s) => s.activeProjectId);
  const targetId = useProjectStore((s) => s.secondaryProjectId);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, spanX: 0, spanY: 0 });
  const [hoveredCell, setHoveredCell] = useState<{ i: number; j: number } | null>(null);
  const [palette, setPalette] = useState<'blues' | 'viridis'>('blues');
  const [scoreThreshold, setScoreThreshold] = useState(0);

  const n = dims?.[0] ?? 0;
  const m = dims?.[1] ?? 0;

  // Score range drives the threshold slider — the dotplot's empirical cutoff (FR-40): below the
  // threshold, alignments are hidden so only high-scoring local structure renders.
  const { minScore, maxScore } = useMemo(() => {
    if (!records.length) return { minScore: 0, maxScore: 0 };
    const s = records.map((r) => r.score);
    return { minScore: Math.min(...s), maxScore: Math.max(...s) };
  }, [records]);

  // Honest metric/domain label. The cross-similarity manifest carries no metric field, so the
  // served metric is inferred from the records' method: cosine lives in [-1,1] but interpolateColor
  // clamps to [0,1] (negatives floor to the 0-end color — the sign is lost, so we say so); word
  // overlap is natively [0,1]. Falls back to a generic label when no records pin down the metric.
  const metricCaption = useMemo(() => {
    const method = (records[0]?.method ?? '').toLowerCase();
    if (method.includes('semantic') || method.includes('cosine'))
      return 'cosine · negatives clamped to 0';
    if (method.includes('word')) return 'word-overlap (Jaccard) · 0–1';
    if (method.includes('alphabet') || method.includes('edit')) return 'alphabet similarity · 0–1';
    return 'similarity · 0–1';
  }, [records]);

  useEffect(() => {
    if (!matrix && queryId && targetId) {
      loadMatrix(queryId, targetId);
    }
  }, [matrix, queryId, targetId, loadMatrix]);

  useEffect(() => {
    if (n > 0 && m > 0) {
      setViewport({ x: 0, y: 0, spanX: m, spanY: n });
    }
  }, [n, m]);

  const clampViewport = useCallback((vp: Viewport): Viewport => {
    const sx = Math.max(2, Math.min(m, vp.spanX));
    const sy = Math.max(2, Math.min(n, vp.spanY));
    let x = Math.max(0, vp.x);
    let y = Math.max(0, vp.y);
    if (x + sx > m) x = Math.max(0, m - sx);
    if (y + sy > n) y = Math.max(0, n - sy);
    return { x, y, spanX: sx, spanY: sy };
  }, [n, m]);

  // Render
  useEffect(() => {
    if (!matrix || n === 0 || m === 0) return;
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const maxW = container.clientWidth - 40;
    const maxH = container.clientHeight - 40;
    const aspect = m / n;  // width:height ratio
    let canvasW: number, canvasH: number;
    if (aspect >= 1) {
      canvasW = Math.max(1, Math.min(maxW, maxH * aspect));
      canvasH = Math.max(1, canvasW / aspect);
    } else {
      canvasH = Math.max(1, Math.min(maxH, maxW / aspect));
      canvasW = Math.max(1, canvasH * aspect);
    }
    // Clamp to container
    if (canvasW > maxW) { canvasW = maxW; canvasH = canvasW / aspect; }
    if (canvasH > maxH) { canvasH = maxH; canvasW = canvasH * aspect; }
    canvas.width = Math.round(canvasW);
    canvas.height = Math.round(canvasH);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { x: vpX, y: vpY, spanX, spanY } = viewport;
    const cellW = canvasW / spanX;
    const cellH = canvasH / spanY;
    const colors = PALETTES[palette];

    ctx.fillStyle = '#f8f8f8';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const startI = Math.max(0, Math.floor(vpY));
    const endI = Math.min(n, Math.ceil(vpY + spanY));
    const startJ = Math.max(0, Math.floor(vpX));
    const endJ = Math.min(m, Math.ceil(vpX + spanX));

    for (let i = startI; i < endI; i++) {
      for (let j = startJ; j < endJ; j++) {
        const value = matrix[i * m + j];
        if (value < 0.1) continue;
        const [r, g, b] = interpolateColor(value, colors);
        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.fillRect((j - vpX) * cellW, (i - vpY) * cellH, Math.ceil(cellW), Math.ceil(cellH));
      }
    }

    // Alignment record overlays
    ctx.strokeStyle = 'rgba(255, 100, 0, 0.6)';
    ctx.lineWidth = 2;
    for (const rec of records) {
      if (rec.score < scoreThreshold) continue;  // thresholded dotplot (FR-40)
      const rx = (rec.targetStart - vpX) * cellW;
      const ry = (rec.queryStart - vpY) * cellH;
      const rw = (rec.targetEnd - rec.targetStart) * cellW;
      const rh = (rec.queryEnd - rec.queryStart) * cellH;
      ctx.strokeRect(rx, ry, rw, rh);
    }

    // Axis labels
    ctx.font = '9px monospace';
    ctx.fillStyle = 'var(--color-text-muted, #767676)';
    const labelIntX = spanX < 20 ? 1 : spanX < 50 ? 5 : spanX < 200 ? 10 : 50;
    for (let j = Math.ceil(vpX / labelIntX) * labelIntX; j <= vpX + spanX && j < m; j += labelIntX) {
      ctx.save();
      ctx.translate((j - vpX) * cellW + cellW / 2, canvas.height + 2);
      ctx.rotate(-Math.PI / 4);
      ctx.textAlign = 'right';
      ctx.fillText(`¶${j}`, 0, 0);
      ctx.restore();
    }
    const labelIntY = spanY < 20 ? 1 : spanY < 50 ? 5 : spanY < 200 ? 10 : 50;
    for (let i = Math.ceil(vpY / labelIntY) * labelIntY; i <= vpY + spanY && i < n; i += labelIntY) {
      ctx.textAlign = 'right';
      ctx.fillText(`¶${i}`, -4, (i - vpY) * cellH + cellH / 2 + 3);
    }

    // Hover crosshair
    if (hoveredCell) {
      const hx = (hoveredCell.j - vpX) * cellW;
      const hy = (hoveredCell.i - vpY) * cellH;
      ctx.strokeStyle = 'rgba(255, 255, 0, 0.8)';
      ctx.lineWidth = 2;
      ctx.strokeRect(hx, hy, cellW, cellH);
    }
  }, [matrix, n, m, viewport, records, hoveredCell, palette, scoreThreshold]);

  // Wheel zoom
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || n === 0) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mx = (e.clientX - rect.left) / rect.width;
      const my = (e.clientY - rect.top) / rect.height;
      const factor = e.deltaY > 0 ? 1.2 : 0.8;
      setViewport((prev) => clampViewport({
        x: prev.x + mx * prev.spanX - mx * prev.spanX * factor,
        y: prev.y + my * prev.spanY - my * prev.spanY * factor,
        spanX: prev.spanX * factor,
        spanY: prev.spanY * factor,
      }));
    };
    canvas.addEventListener('wheel', handler, { passive: false });
    return () => canvas.removeEventListener('wheel', handler);
  }, [n, m, clampViewport]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!matrix || n === 0 || m === 0) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const i = Math.min(Math.max(Math.floor(viewport.y + (e.clientY - rect.top) / rect.height * viewport.spanY), 0), n - 1);
    const j = Math.min(Math.max(Math.floor(viewport.x + (e.clientX - rect.left) / rect.width * viewport.spanX), 0), m - 1);
    setHoveredCell({ i, j });
  }, [matrix, n, m, viewport]);

  const hoverValue = hoveredCell && matrix ? matrix[hoveredCell.i * m + hoveredCell.j] : null;

  if (!matrix) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-[var(--color-text-muted)] text-[0.85em] gap-2">
        <div>No cross-similarity matrix computed yet.</div>
        <div>Run a semantic alignment first to generate the matrix.</div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex-1 flex flex-col p-2 bg-[var(--color-bg-subtle)]">
      <div className="flex items-center gap-2 mb-1 text-[0.8em] font-[var(--font-sans)] shrink-0">
        <span className="font-semibold">
          Cross-Similarity: {activeProject.metadata?.title} vs {secondaryProject.metadata?.title}
        </span>
        {hoveredCell && hoverValue != null && (
          <span className="text-[var(--color-text-muted)]">
            [{hoveredCell.i}, {hoveredCell.j}]: {hoverValue.toFixed(3)}
          </span>
        )}
        <label className="flex items-center gap-1">
          palette
          <select
            value={palette}
            onChange={(e) => setPalette(e.target.value as 'blues' | 'viridis')}
            className="border border-[var(--color-border)] rounded px-1 bg-[var(--color-bg)]"
          >
            <option value="blues">blues</option>
            <option value="viridis">viridis</option>
          </select>
        </label>
        {records.length > 0 && maxScore > minScore && (
          <label
            className="flex items-center gap-1"
            title="Show only alignments scoring ≥ threshold — the dotplot's empirical cutoff"
          >
            score ≥ {scoreThreshold.toFixed(1)}
            <input
              type="range"
              min={minScore}
              max={maxScore}
              step={(maxScore - minScore) / 100 || 1}
              value={scoreThreshold}
              onChange={(e) => setScoreThreshold(Number(e.target.value))}
            />
            <span className="text-[var(--color-text-muted)]">
              {records.filter((r) => r.score >= scoreThreshold).length}/{records.length}
            </span>
          </label>
        )}
        {queryId && targetId && records.length > 0 && (
          <a
            href={`/api/alignment/${queryId}/${targetId}/export.paf${
              scoreThreshold > minScore ? `?min_score=${scoreThreshold}` : ''
            }`}
            download
            className="text-[var(--color-accent,#2563eb)] underline"
          >
            PAF
          </a>
        )}
        <span className="ml-auto text-[var(--color-text-muted)]">
          {n}×{m} · Wheel=zoom
        </span>
      </div>
      {/* Legend — color ramp + honest metric/domain caption + hidden-cell disclosure (#12b-d) */}
      <div className="flex items-center gap-2 mb-1 text-[0.7em] text-[var(--color-text-muted)] shrink-0 flex-wrap">
        <span>0</span>
        <div className="h-3 rounded-sm overflow-hidden flex" style={{ width: 160 }}>
          {Array.from({ length: 40 }, (_, i) => {
            const [r, g, b] = interpolateColor(i / 39, PALETTES[palette]);
            return <div key={i} className="flex-1" style={{ backgroundColor: `rgb(${r},${g},${b})` }} />;
          })}
        </div>
        <span>1</span>
        <span className="ml-1">{metricCaption}</span>
        <span className="ml-2">cells &lt; 0.1 not drawn</span>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHoveredCell(null)}
          className="cursor-crosshair"
          role="img"
          aria-label={`Cross-similarity heatmap, ${n} query paragraphs × ${m} target paragraphs`}
        />
      </div>
    </div>
  );
}
