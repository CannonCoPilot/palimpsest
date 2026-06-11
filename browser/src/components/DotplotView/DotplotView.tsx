import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useViewStore } from '../../stores/viewStore';
import { useProjectStore } from '../../stores/projectStore';
import { useTrackStore } from '../../stores/trackStore';
import { loadSignal, type LoadedSignal } from '../../adapters/SignalAdapter';
import { TRACK_COLORS } from '../../utils/trackColors';

const PALETTES: Record<string, number[][]> = {
  blues: [
    [239, 246, 255], [147, 197, 253], [59, 130, 246], [30, 64, 175], [30, 58, 138],
  ],
  viridis: [
    [68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37],
  ],
  plasma: [
    [13, 8, 135], [126, 3, 168], [204, 71, 120], [248, 149, 64], [240, 249, 33],
  ],
  diverging: [
    [178, 24, 43], [239, 138, 98], [247, 247, 247], [103, 169, 207], [33, 102, 172],
  ],
};

type PaletteKey = keyof typeof PALETTES;

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

function AxisAnnotationStrip({ orientation, trackName, annotations, color, paragraphs, viewport, size }: {
  orientation: 'horizontal' | 'vertical';
  trackName: string;
  annotations: Array<{ target: { selector: { start?: number; end?: number } } }>;
  color: string;
  paragraphs: Array<{ start: number; end: number }>;
  viewport: Viewport;
  size: number;
}) {
  const { x: vpX, y: vpY, span } = viewport;
  const n = paragraphs.length;
  if (n === 0 || span === 0) return null;

  const density = new Float32Array(n);
  for (const ann of annotations) {
    const sel = ann.target.selector;
    if (sel.start == null || sel.end == null) continue;
    const startP = paragraphs.findIndex((p) => p.end > sel.start!);
    const endP = paragraphs.findIndex((p) => p.start >= sel.end!);
    const sp = Math.max(0, startP);
    const ep = endP < 0 ? n : endP;
    for (let i = sp; i < ep; i++) density[i]++;
  }
  const maxDensity = Math.max(1, ...Array.from(density));

  const stripThickness = 8;
  const cellPx = size / span;
  const vpStart = orientation === 'horizontal' ? vpX : vpY;

  const bars: JSX.Element[] = [];
  const startIdx = Math.max(0, Math.floor(vpStart));
  const endIdx = Math.min(n, Math.ceil(vpStart + span));
  for (let i = startIdx; i < endIdx; i++) {
    if (density[i] === 0) continue;
    const pos = (i - vpStart) * cellPx;
    const opacity = 0.3 + 0.7 * (density[i] / maxDensity);
    if (orientation === 'horizontal') {
      bars.push(<rect key={i} x={pos} y={0} width={Math.ceil(cellPx)} height={stripThickness} fill={color} fillOpacity={opacity} />);
    } else {
      bars.push(<rect key={i} x={0} y={pos} width={stripThickness} height={Math.ceil(cellPx)} fill={color} fillOpacity={opacity} />);
    }
  }

  if (orientation === 'horizontal') {
    return <svg width={size} height={stripThickness} className="shrink-0">{bars}</svg>;
  }
  return <svg width={stripThickness} height={size} className="shrink-0">{bars}</svg>;
}

interface Viewport {
  x: number; // top-left cell column (fractional)
  y: number; // top-left cell row (fractional)
  span: number; // how many cells visible in each dimension
}

export default function DotplotView(): JSX.Element | null {
  const textHicOpen = useViewStore((s) => s.textHicOpen);
  const requestScrollToParagraph = useViewStore((s) => s.requestScrollToParagraph);
  const setSelectedParagraphIndex = useViewStore((s) => s.setSelectedParagraphIndex);
  const projectId = useProjectStore((s) => s.metadata?.id);
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const allTracks = useProjectStore((s) => s.tracks);
  const trackStates = useTrackStore((s) => s.tracks);
  const trackOrder = useTrackStore((s) => s.trackOrder);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [signal, setSignal] = useState<LoadedSignal | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredCell, setHoveredCell] = useState<{ i: number; j: number } | null>(null);
  const [brushStart, setBrushStart] = useState<{ i: number; j: number } | null>(null);
  const [brushEnd, setBrushEnd] = useState<{ i: number; j: number } | null>(null);
  const [brushSelection, setBrushSelection] = useState<{ rowMin: number; rowMax: number; colMin: number; colMax: number } | null>(null);
  const [palette, setPalette] = useState<PaletteKey>('blues');
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, span: 0 });
  const [threshold, setThreshold] = useState(0);
  const [showDiagonal, setShowDiagonal] = useState(true);
  const [showControls, setShowControls] = useState(false);
  const [similarityMetric, setSimilarityMetric] = useState('cosine');
  const brushing = useRef(false);
  const panning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const vpAtPanStart = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!textHicOpen || !projectId) return;
    setLoading(true);
    setError(null);
    loadSignal(`/data/${projectId}/signals/self_similarity.json`)
      .then((s) => {
        setSignal(s);
        const dim = s.manifest.dimensions[0];
        setViewport({ x: 0, y: 0, span: dim });
        setLoading(false);
      })
      .catch(() => {
        setError('Self-similarity matrix not available. Run analysis with Ollama first.');
        setLoading(false);
      });
  }, [textHicOpen, projectId]);

  const n = signal ? signal.manifest.dimensions[0] : 0;
  const colors = PALETTES[palette];

  const renderHeatmap = useCallback(() => {
    if (!signal || n === 0) return;
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const size = Math.max(1, Math.min(container.clientWidth, container.clientHeight) - 60);
    canvas.width = size;
    canvas.height = size;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { x: vpX, y: vpY, span } = viewport;
    const cellPx = size / span;

    if (cellPx >= 1) {
      const startI = Math.max(0, Math.floor(vpY));
      const endI = Math.min(n, Math.ceil(vpY + span));
      const startJ = Math.max(0, Math.floor(vpX));
      const endJ = Math.min(n, Math.ceil(vpX + span));

      ctx.fillStyle = '#f8f8f8';
      ctx.fillRect(0, 0, size, size);

      for (let i = startI; i < endI; i++) {
        for (let j = startJ; j < endJ; j++) {
          if (!showDiagonal && i === j) continue;
          const value = signal.data[i * n + j];
          if (value < threshold) continue;
          const [r, g, b] = interpolateColor(value, colors);
          const px = (j - vpX) * cellPx;
          const py = (i - vpY) * cellPx;
          ctx.fillStyle = `rgb(${r},${g},${b})`;
          ctx.fillRect(px, py, Math.ceil(cellPx), Math.ceil(cellPx));
        }
      }
    } else {
      const imageData = ctx.createImageData(size, size);
      const pixels = imageData.data;
      const bg = [248, 248, 248];
      for (let py = 0; py < size; py++) {
        const i = Math.min(Math.floor(vpY + (py / size) * span), n - 1);
        for (let px = 0; px < size; px++) {
          const j = Math.min(Math.floor(vpX + (px / size) * span), n - 1);
          const offset = (py * size + px) * 4;
          if (!showDiagonal && i === j) {
            pixels[offset] = bg[0]; pixels[offset + 1] = bg[1]; pixels[offset + 2] = bg[2]; pixels[offset + 3] = 255;
            continue;
          }
          const value = signal.data[i * n + j];
          if (value < threshold) {
            pixels[offset] = bg[0]; pixels[offset + 1] = bg[1]; pixels[offset + 2] = bg[2]; pixels[offset + 3] = 255;
            continue;
          }
          const [r, g, b] = interpolateColor(value, colors);
          pixels[offset] = r;
          pixels[offset + 1] = g;
          pixels[offset + 2] = b;
          pixels[offset + 3] = 255;
        }
      }
      ctx.putImageData(imageData, 0, 0);
    }

    // Axis labels
    const labelInterval = span < 20 ? 1 : span < 50 ? 5 : span < 100 ? 10 : span < 300 ? 50 : 100;
    ctx.font = '9px var(--font-mono, monospace)';
    ctx.fillStyle = 'var(--color-text-muted, #999)';
    const startLabel = Math.ceil((vpX) / labelInterval) * labelInterval;
    for (let j = startLabel; j <= vpX + span && j < n; j += labelInterval) {
      const px = (j - vpX) * cellPx;
      ctx.save();
      ctx.translate(px + cellPx / 2, size + 2);
      ctx.rotate(-Math.PI / 4);
      ctx.textAlign = 'right';
      ctx.fillText(`¶${j}`, 0, 0);
      ctx.restore();
    }
    const startLabelY = Math.ceil(vpY / labelInterval) * labelInterval;
    for (let i = startLabelY; i <= vpY + span && i < n; i += labelInterval) {
      const py = (i - vpY) * cellPx;
      ctx.textAlign = 'right';
      ctx.fillText(`¶${i}`, -4, py + cellPx / 2 + 3);
    }
  }, [signal, n, viewport, colors, threshold, showDiagonal]);

  useEffect(() => { renderHeatmap(); }, [renderHeatmap]);

  // Draw overlays (crosshair, brush) on top of heatmap
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || n === 0 || !signal) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    renderHeatmap();

    const size = canvas.width;
    const cellPx = size / viewport.span;

    if (hoveredCell) {
      const px = (hoveredCell.j - viewport.x) * cellPx;
      const py = (hoveredCell.i - viewport.y) * cellPx;
      ctx.strokeStyle = 'rgba(255, 255, 0, 0.8)';
      ctx.lineWidth = 2;
      ctx.strokeRect(px, py, cellPx, cellPx);
      ctx.strokeStyle = 'rgba(255, 255, 0, 0.3)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, py + cellPx / 2);
      ctx.lineTo(size, py + cellPx / 2);
      ctx.moveTo(px + cellPx / 2, 0);
      ctx.lineTo(px + cellPx / 2, size);
      ctx.stroke();
    }

    if (brushStart && brushEnd) {
      const bx = (Math.min(brushStart.j, brushEnd.j) - viewport.x) * cellPx;
      const by = (Math.min(brushStart.i, brushEnd.i) - viewport.y) * cellPx;
      const bw = (Math.abs(brushEnd.j - brushStart.j) + 1) * cellPx;
      const bh = (Math.abs(brushEnd.i - brushStart.i) + 1) * cellPx;
      ctx.strokeStyle = 'rgba(52, 152, 219, 0.9)';
      ctx.lineWidth = 2;
      ctx.strokeRect(bx, by, bw, bh);
      ctx.fillStyle = 'rgba(52, 152, 219, 0.1)';
      ctx.fillRect(bx, by, bw, bh);
    }
  }, [hoveredCell, brushStart, brushEnd, n, signal, viewport, renderHeatmap]);

  const getCellFromEvent = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!signal || n === 0) return null;
      const canvas = canvasRef.current;
      if (!canvas) return null;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const cellPx = rect.width / viewport.span;
      return {
        i: Math.min(Math.max(Math.floor(viewport.y + y / cellPx), 0), n - 1),
        j: Math.min(Math.max(Math.floor(viewport.x + x / cellPx), 0), n - 1),
      };
    },
    [signal, n, viewport],
  );

  const clampViewport = useCallback((vp: Viewport): Viewport => {
    const s = Math.max(2, Math.min(n, vp.span));
    let x = vp.x;
    let y = vp.y;
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    if (x + s > n) x = n - s;
    if (y + s > n) y = n - s;
    return { x: Math.max(0, x), y: Math.max(0, y), span: s };
  }, [n]);

  const handleCanvasMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (panning.current) {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const dx = (e.clientX - panStart.current.x) / rect.width * viewport.span;
        const dy = (e.clientY - panStart.current.y) / rect.height * viewport.span;
        setViewport(clampViewport({
          x: vpAtPanStart.current.x - dx,
          y: vpAtPanStart.current.y - dy,
          span: viewport.span,
        }));
        return;
      }
      const cell = getCellFromEvent(e);
      if (!cell) return;
      setHoveredCell(cell);
      if (brushing.current) {
        setBrushEnd(cell);
      }
    },
    [getCellFromEvent, viewport, clampViewport],
  );

  const handleCanvasMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (e.ctrlKey || e.metaKey || e.button === 1) {
        // Pan mode
        panning.current = true;
        panStart.current = { x: e.clientX, y: e.clientY };
        vpAtPanStart.current = { x: viewport.x, y: viewport.y };
        e.preventDefault();
        return;
      }
      const cell = getCellFromEvent(e);
      if (!cell) return;
      brushing.current = true;
      setBrushStart(cell);
      setBrushEnd(cell);
    },
    [getCellFromEvent, viewport],
  );

  const handleCanvasMouseUp = useCallback(
    () => {
      if (panning.current) {
        panning.current = false;
        return;
      }
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

      setViewport((prev) => {
        const newSpan = prev.span * factor;
        const cellUnderMouseX = prev.x + mx * prev.span;
        const cellUnderMouseY = prev.y + my * prev.span;
        return clampViewport({
          x: cellUnderMouseX - mx * newSpan,
          y: cellUnderMouseY - my * newSpan,
          span: newSpan,
        });
      });
    };
    canvas.addEventListener('wheel', handler, { passive: false });
    return () => canvas.removeEventListener('wheel', handler);
  }, [n, clampViewport]);

  const exportPNG = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `texthic-${projectId ?? 'heatmap'}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, [projectId]);

  const zoomToFull = useCallback(() => {
    setViewport({ x: 0, y: 0, span: n });
    setBrushSelection(null);
  }, [n]);

  const zoomToSelection = useCallback(() => {
    if (!brushSelection) return;
    const { rowMin, rowMax, colMin, colMax } = brushSelection;
    const span = Math.max(rowMax - rowMin + 1, colMax - colMin + 1);
    setViewport(clampViewport({ x: colMin, y: rowMin, span: Math.max(2, span) }));
  }, [brushSelection, clampViewport]);

  const activeTab = useViewStore((s) => s.activeTab);
  const isTabMode = activeTab === 'texthic';

  if (!textHicOpen && !isTabMode) return null;

  const hoverValue = hoveredCell && signal
    ? signal.data[hoveredCell.i * n + hoveredCell.j]
    : null;

  const zoomPct = n > 0 ? Math.round((viewport.span / n) * 100) : 100;

  const visibleTrackNames = useMemo(() =>
    trackOrder.filter((name) => {
      const state = trackStates[name];
      return state?.visible && name !== 'segments' && name !== 'sections';
    }).slice(0, 5),
    [trackOrder, trackStates],
  );

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
      <div className="flex justify-between items-center mb-[4px] text-[0.85em] gap-2 flex-wrap">
        <span className="font-bold">
          Self-Similarity Matrix
          {hoveredCell && hoverValue != null
            ? ` — [¶${hoveredCell.i}, ¶${hoveredCell.j}]: ${hoverValue.toFixed(3)}`
            : ''}
        </span>
        <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
          <select
            value={palette}
            onChange={(e) => setPalette(e.target.value as PaletteKey)}
            className="text-[0.85em] border border-[var(--color-border)] rounded px-1 py-0.5 bg-[var(--color-bg)] cursor-pointer"
          >
            <option value="blues">Blues</option>
            <option value="viridis">Viridis</option>
            <option value="plasma">Plasma</option>
            <option value="diverging">Diverging</option>
          </select>
          <span className="text-[0.85em]">{zoomPct}%</span>
          {viewport.span < n && (
            <button
              onClick={zoomToFull}
              className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]"
            >
              Reset
            </button>
          )}
          {brushSelection && (
            <>
              <button
                onClick={zoomToSelection}
                className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]"
              >
                Zoom to selection
              </button>
              <button
                onClick={() => setBrushSelection(null)}
                className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]"
              >
                Clear
              </button>
            </>
          )}
          <button
            onClick={() => setShowControls(!showControls)}
            className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]"
          >
            {showControls ? 'Hide filters' : 'Filters'}
          </button>
          <button
            onClick={exportPNG}
            className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]"
          >
            Export PNG
          </button>
          <span className="text-[0.8em]">
            {n > 0 ? `${n}×${n} · ${similarityMetric}` : ''}
            {' · Scroll zoom · Ctrl+drag pan'}
          </span>
        </div>
      </div>
      {/* Gradient legend */}
      {signal && (
        <div className="flex items-center gap-2 mb-1 text-[0.75em] text-[var(--color-text-muted)]">
          <span>0</span>
          <div className="flex-1 h-3 rounded-sm overflow-hidden flex" style={{ maxWidth: 200 }}>
            {Array.from({ length: 40 }, (_, i) => {
              const val = i / 39;
              const [r, g, b] = interpolateColor(val, colors);
              return <div key={i} className="flex-1" style={{ backgroundColor: `rgb(${r},${g},${b})` }} />;
            })}
          </div>
          <span>1</span>
          <span className="ml-1">similarity</span>
        </div>
      )}
      {/* Filter controls */}
      {showControls && (
        <div className="flex items-center gap-3 mb-1 text-[0.75em] font-[var(--font-sans)] py-1 px-2 border border-[var(--color-border-subtle)] rounded bg-[var(--color-bg)]">
          <label className="flex items-center gap-1">
            Threshold:
            <input
              type="range" min="0" max="100" value={Math.round(threshold * 100)}
              onChange={(e) => setThreshold(parseInt(e.target.value, 10) / 100)}
              className="w-[80px]"
            />
            <span className="w-8 text-right">{(threshold * 100).toFixed(0)}%</span>
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="checkbox" checked={showDiagonal}
              onChange={(e) => setShowDiagonal(e.target.checked)}
              className="accent-[var(--color-primary)]"
            />
            Diagonal
          </label>
          <span className="text-[var(--color-text-muted)]">|</span>
          <label className="flex items-center gap-1">
            Metric:
            <select
              value={similarityMetric}
              onChange={(e) => setSimilarityMetric(e.target.value)}
              className="border border-[var(--color-border)] rounded px-1 py-0.5 bg-[var(--color-bg)] cursor-pointer"
            >
              <option value="cosine">Cosine</option>
              <option value="jaccard">Jaccard</option>
              <option value="word_overlap">Word overlap</option>
              <option value="edit_distance">Edit distance</option>
            </select>
          </label>
        </div>
      )}
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
          <div className="flex flex-col" style={{ flex: brushSelection ? '0 0 60%' : '1', maxWidth: '100%' }}>
            {/* Top axis annotation strips */}
            {visibleTrackNames.map((name) => (
              <AxisAnnotationStrip
                key={`top-${name}`}
                orientation="horizontal"
                trackName={name}
                annotations={allTracks[name] ?? []}
                color={TRACK_COLORS[name] ?? '#888'}
                paragraphs={paragraphs}
                viewport={viewport}
                size={canvasRef.current?.clientWidth ?? 400}
              />
            ))}
            <div className="flex">
              {/* Left axis annotation strips */}
              <div className="flex shrink-0">
                {visibleTrackNames.map((name) => (
                  <AxisAnnotationStrip
                    key={`left-${name}`}
                    orientation="vertical"
                    trackName={name}
                    annotations={allTracks[name] ?? []}
                    color={TRACK_COLORS[name] ?? '#888'}
                    paragraphs={paragraphs}
                    viewport={viewport}
                    size={canvasRef.current?.clientHeight ?? 400}
                  />
                ))}
              </div>
              <canvas
                ref={canvasRef}
                onMouseMove={handleCanvasMouseMove}
                onMouseDown={handleCanvasMouseDown}
                onMouseUp={handleCanvasMouseUp}
                onMouseLeave={() => { setHoveredCell(null); if (brushing.current) handleCanvasMouseUp(); if (panning.current) panning.current = false; }}
                className="cursor-crosshair flex-1"
                style={{
                  maxHeight: isTabMode ? undefined : 'calc(35vh - 40px)',
                  aspectRatio: '1',
                }}
              />
            </div>
          </div>
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
