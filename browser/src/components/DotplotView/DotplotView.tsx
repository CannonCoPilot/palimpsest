/**
 * TextHiCView — Canvas-rendered self-similarity matrix heatmap (TextHiC).
 * Loads the self_similarity signal and renders it as an interactive heatmap.
 * Click a cell to navigate to the corresponding paragraphs.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useViewStore } from '../../stores/viewStore';
import { useProjectStore } from '../../stores/projectStore';
import { loadSignal, type LoadedSignal } from '../../adapters/SignalAdapter';

const COLORS = [
  [239, 246, 255],  // 0.0 - lightest blue
  [147, 197, 253],  // 0.25
  [59, 130, 246],   // 0.5 - mid blue
  [30, 64, 175],    // 0.75
  [30, 58, 138],    // 1.0 - darkest blue
];

function interpolateColor(value: number): [number, number, number] {
  const clamped = Math.max(0, Math.min(1, value));
  const idx = clamped * (COLORS.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, COLORS.length - 1);
  const t = idx - lo;
  return [
    Math.round(COLORS[lo][0] + t * (COLORS[hi][0] - COLORS[lo][0])),
    Math.round(COLORS[lo][1] + t * (COLORS[hi][1] - COLORS[lo][1])),
    Math.round(COLORS[lo][2] + t * (COLORS[hi][2] - COLORS[lo][2])),
  ];
}

export default function DotplotView(): JSX.Element | null {
  const textHicOpen = useViewStore((s) => s.textHicOpen);
  const requestScrollToParagraph = useViewStore((s) => s.requestScrollToParagraph);
  const setSelectedParagraphIndex = useViewStore((s) => s.setSelectedParagraphIndex);
  const projectId = useProjectStore((s) => s.metadata?.id);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const cachedImageRef = useRef<ImageData | null>(null);
  const cachedSizeRef = useRef(0);

  const [signal, setSignal] = useState<LoadedSignal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredCell, setHoveredCell] = useState<{ i: number; j: number } | null>(null);

  useEffect(() => {
    if (!textHicOpen || !projectId) return;

    setLoading(true);
    setError(null);
    loadSignal(`/data/${projectId}/signals/self_similarity.json`)
      .then((s) => {
        setSignal(s);
        cachedImageRef.current = null;
        setLoading(false);
      })
      .catch(() => {
        setError('Self-similarity matrix not available. Run analysis with Ollama first.');
        setLoading(false);
      });
  }, [textHicOpen, projectId]);

  const n = signal ? signal.manifest.dimensions[0] : 0;

  // Build the heatmap ImageData once when signal or container size changes
  const buildHeatmap = useCallback(() => {
    if (!signal || n === 0) return;
    const container = containerRef.current;
    if (!container) return;

    const size = Math.max(1, Math.min(container.clientWidth, container.clientHeight) - 40);
    if (size === cachedSizeRef.current && cachedImageRef.current) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = size;
    canvas.height = size;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const cellSize = size / n;
    const imageData = ctx.createImageData(size, size);
    const pixels = imageData.data;

    for (let py = 0; py < size; py++) {
      const i = Math.min(Math.floor(py / cellSize), n - 1);
      for (let px = 0; px < size; px++) {
        const j = Math.min(Math.floor(px / cellSize), n - 1);
        const value = signal.data[i * n + j];
        const [r, g, b] = interpolateColor(value);
        const offset = (py * size + px) * 4;
        pixels[offset] = r;
        pixels[offset + 1] = g;
        pixels[offset + 2] = b;
        pixels[offset + 3] = 255;
      }
    }

    cachedImageRef.current = imageData;
    cachedSizeRef.current = size;
    ctx.putImageData(imageData, 0, 0);
  }, [signal, n]);

  // Render heatmap when signal loads
  useEffect(() => {
    buildHeatmap();
  }, [buildHeatmap]);

  // Draw crosshair overlay on hover — no pixel recomputation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !cachedImageRef.current || n === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const size = cachedSizeRef.current;
    ctx.putImageData(cachedImageRef.current, 0, 0);

    if (hoveredCell) {
      const cellSize = size / n;
      ctx.strokeStyle = 'rgba(255, 255, 0, 0.8)';
      ctx.lineWidth = 2;
      ctx.strokeRect(
        hoveredCell.j * cellSize,
        hoveredCell.i * cellSize,
        cellSize,
        cellSize,
      );
      ctx.strokeStyle = 'rgba(255, 255, 0, 0.3)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, hoveredCell.i * cellSize + cellSize / 2);
      ctx.lineTo(size, hoveredCell.i * cellSize + cellSize / 2);
      ctx.moveTo(hoveredCell.j * cellSize + cellSize / 2, 0);
      ctx.lineTo(hoveredCell.j * cellSize + cellSize / 2, size);
      ctx.stroke();
    }
  }, [hoveredCell, n]);

  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!signal || n === 0) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cellSize = canvas.width / n;
      const i = Math.min(Math.floor(y / cellSize), n - 1);
      const j = Math.min(Math.floor(x / cellSize), n - 1);
      setHoveredCell({ i, j });
    },
    [signal, n],
  );

  const handleCanvasClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!signal || n === 0) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cellSize = canvas.width / n;
      const i = Math.min(Math.floor(y / cellSize), n - 1);
      const j = Math.min(Math.floor(x / cellSize), n - 1);

      const targetParagraph = e.shiftKey ? j : i;
      setSelectedParagraphIndex(targetParagraph);
      requestScrollToParagraph(targetParagraph);
    },
    [signal, n, setSelectedParagraphIndex, requestScrollToParagraph],
  );

  const activeTab = useViewStore((s) => s.activeTab);
  const isTabMode = activeTab === 'texthic';

  if (!textHicOpen && !isTabMode) return null;

  const hoverValue = hoveredCell && signal
    ? signal.data[hoveredCell.i * n + hoveredCell.j]
    : null;

  return (
    <div
      ref={containerRef}
      style={{
        borderTop: isTabMode ? undefined : '1px solid #ddd',
        padding: '8px',
        height: isTabMode ? '100%' : '35vh',
        minHeight: '200px',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#fafafa',
        flex: isTabMode ? 1 : undefined,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '4px',
          fontSize: '0.85em',
        }}
      >
        <span style={{ fontWeight: 'bold' }}>
          Self-Similarity Matrix
          {hoveredCell && hoverValue != null
            ? ` — [${hoveredCell.i}, ${hoveredCell.j}]: ${hoverValue.toFixed(3)}`
            : ''}
        </span>
        <span style={{ color: '#999' }}>
          {n > 0 ? `${n}×${n} paragraphs` : ''}
          {' · Click to navigate · Shift+click for column'}
        </span>
      </div>
      {loading && (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
          Loading self-similarity matrix...
        </div>
      )}
      {error && (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#b91c1c' }}>
          {error}
        </div>
      )}
      {!loading && !error && signal && (
        <canvas
          ref={canvasRef}
          onMouseMove={handleCanvasMouseMove}
          onMouseLeave={() => setHoveredCell(null)}
          onClick={handleCanvasClick}
          style={{
            flex: 1,
            cursor: 'crosshair',
            maxHeight: 'calc(35vh - 40px)',
            objectFit: 'contain',
          }}
        />
      )}
    </div>
  );
}
