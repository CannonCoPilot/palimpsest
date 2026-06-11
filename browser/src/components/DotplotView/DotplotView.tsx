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
  const paragraphs = useProjectStore((s) => s.paragraphs);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const cachedImageRef = useRef<ImageData | null>(null);
  const cachedSizeRef = useRef(0);

  const [signal, setSignal] = useState<LoadedSignal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredCell, setHoveredCell] = useState<{ i: number; j: number } | null>(null);
  const [brushStart, setBrushStart] = useState<{ i: number; j: number } | null>(null);
  const [brushEnd, setBrushEnd] = useState<{ i: number; j: number } | null>(null);
  const [brushSelection, setBrushSelection] = useState<{ rowMin: number; rowMax: number; colMin: number; colMax: number } | null>(null);
  const brushing = useRef(false);

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

    if (brushStart && brushEnd) {
      const cellSize = size / n;
      const bx = Math.min(brushStart.j, brushEnd.j) * cellSize;
      const by = Math.min(brushStart.i, brushEnd.i) * cellSize;
      const bw = (Math.abs(brushEnd.j - brushStart.j) + 1) * cellSize;
      const bh = (Math.abs(brushEnd.i - brushStart.i) + 1) * cellSize;
      ctx.strokeStyle = 'rgba(52, 152, 219, 0.9)';
      ctx.lineWidth = 2;
      ctx.strokeRect(bx, by, bw, bh);
      ctx.fillStyle = 'rgba(52, 152, 219, 0.1)';
      ctx.fillRect(bx, by, bw, bh);
    }
  }, [hoveredCell, brushStart, brushEnd, n]);

  const getCellFromEvent = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!signal || n === 0) return null;
      const canvas = canvasRef.current;
      if (!canvas) return null;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cellSize = rect.width / n;
      return {
        i: Math.min(Math.max(Math.floor(y / cellSize), 0), n - 1),
        j: Math.min(Math.max(Math.floor(x / cellSize), 0), n - 1),
      };
    },
    [signal, n],
  );

  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const cell = getCellFromEvent(e);
      if (!cell) return;
      setHoveredCell(cell);
      if (brushing.current) {
        setBrushEnd(cell);
      }
    },
    [getCellFromEvent],
  );

  const handleCanvasMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const cell = getCellFromEvent(e);
      if (!cell) return;
      brushing.current = true;
      setBrushStart(cell);
      setBrushEnd(cell);
    },
    [getCellFromEvent],
  );

  const handleCanvasMouseUp = useCallback(
    () => {
      if (!brushing.current || !brushStart || !brushEnd) {
        brushing.current = false;
        return;
      }
      brushing.current = false;
      const rowMin = Math.min(brushStart.i, brushEnd.i);
      const rowMax = Math.max(brushStart.i, brushEnd.i);
      const colMin = Math.min(brushStart.j, brushEnd.j);
      const colMax = Math.max(brushStart.j, brushEnd.j);
      if (rowMax - rowMin < 1 && colMax - colMin < 1) {
        setSelectedParagraphIndex(rowMin);
        requestScrollToParagraph(rowMin);
      } else {
        setBrushSelection({ rowMin, rowMax, colMin, colMax });
      }
      setBrushStart(null);
      setBrushEnd(null);
    },
    [brushStart, brushEnd, setSelectedParagraphIndex, requestScrollToParagraph],
  );

  const activeTab = useViewStore((s) => s.activeTab);
  const isTabMode = activeTab === 'texthic';

  if (!textHicOpen && !isTabMode) return null;

  const hoverValue = hoveredCell && signal
    ? signal.data[hoveredCell.i * n + hoveredCell.j]
    : null;

  const rowText = brushSelection && paragraphs.length > 0
    ? paragraphs.slice(brushSelection.rowMin, brushSelection.rowMax + 1).map((p) => p.text).join('\n')
    : null;
  const colText = brushSelection && paragraphs.length > 0
    ? paragraphs.slice(brushSelection.colMin, brushSelection.colMax + 1).map((p) => p.text).join('\n')
    : null;

  return (
    <div
      ref={containerRef}
      className="p-2 min-h-[200px] flex flex-col bg-[var(--color-bg-subtle)]"
      style={{
        borderTop: isTabMode ? undefined : '1px solid #ddd',
        height: isTabMode ? '100%' : '35vh',
        flex: isTabMode ? 1 : undefined,
      }}
    >
      <div className="flex justify-between items-center mb-[4px] text-[0.85em]">
        <span className="font-bold">
          Self-Similarity Matrix
          {hoveredCell && hoverValue != null
            ? ` — [¶${hoveredCell.i}, ¶${hoveredCell.j}]: ${hoverValue.toFixed(3)}`
            : ''}
        </span>
        <span className="text-[var(--color-text-muted)]">
          {n > 0 ? `${n}×${n} paragraphs · cosine similarity` : ''}
          {' · Drag to compare segments'}
        </span>
        {brushSelection && (
          <button
            onClick={() => setBrushSelection(null)}
            className="text-[0.8em] px-2 py-0.5 rounded bg-[var(--color-bg-muted)] border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg)]"
          >
            Clear selection
          </button>
        )}
      </div>
      {loading && (
        <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">
          Loading self-similarity matrix...
        </div>
      )}
      {error && (
        <div className="flex-1 flex items-center justify-center text-[#b91c1c]">
          {error}
        </div>
      )}
      {!loading && !error && signal && (
        <div className="flex-1 flex gap-2 overflow-hidden">
          <canvas
            ref={canvasRef}
            onMouseMove={handleCanvasMouseMove}
            onMouseDown={handleCanvasMouseDown}
            onMouseUp={handleCanvasMouseUp}
            onMouseLeave={() => { setHoveredCell(null); if (brushing.current) handleCanvasMouseUp(); }}
            className="cursor-crosshair object-contain"
            style={{
              flex: brushSelection ? '0 0 60%' : '1',
              maxHeight: isTabMode ? undefined : 'calc(35vh - 40px)',
            }}
          />
          {brushSelection && rowText && colText && (
            <div className="flex-1 flex flex-col gap-1 overflow-hidden text-[0.8em] font-[var(--font-serif)]">
              <div className="flex-1 overflow-auto border border-[var(--color-border)] rounded p-2 bg-[var(--color-bg)]">
                <div className="text-[0.75em] font-[var(--font-sans)] font-semibold text-[var(--color-text-muted)] mb-1">
                  Y-axis: ¶{brushSelection.rowMin}–¶{brushSelection.rowMax}
                </div>
                <div className="whitespace-pre-wrap leading-relaxed">{rowText.slice(0, 2000)}</div>
              </div>
              <div className="flex-1 overflow-auto border border-[var(--color-border)] rounded p-2 bg-[var(--color-bg)]">
                <div className="text-[0.75em] font-[var(--font-sans)] font-semibold text-[var(--color-text-muted)] mb-1">
                  X-axis: ¶{brushSelection.colMin}–¶{brushSelection.colMax}
                </div>
                <div className="whitespace-pre-wrap leading-relaxed">{colText.slice(0, 2000)}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
