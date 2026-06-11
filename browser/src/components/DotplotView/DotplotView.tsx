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

interface Viewport {
  x: number;
  y: number;
  span: number;
}

interface FloatingWindow {
  id: string;
  title: string;
  text: string;
  paraRange: [number, number];
  x: number;
  y: number;
}

function DraggableWindow({ win, onClose, onDragStart }: { win: FloatingWindow; onClose: () => void; onDragStart: (id: string, e: React.MouseEvent) => void }) {
  return (
    <div
      className="absolute bg-[var(--color-bg)] border border-[var(--color-border)] rounded shadow-lg z-[var(--z-popover)] flex flex-col"
      style={{ left: win.x, top: win.y, width: 350, maxHeight: 300 }}
    >
      <div
        className="flex items-center justify-between px-2 py-1 bg-[var(--color-bg-subtle)] border-b border-[var(--color-border)] cursor-move text-[0.75em] font-[var(--font-sans)]"
        onMouseDown={(e) => onDragStart(win.id, e)}
      >
        <span className="font-semibold">{win.title}</span>
        <button onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer">✕</button>
      </div>
      <div className="flex-1 overflow-auto p-2 text-[0.8em] font-[var(--font-serif)] leading-relaxed whitespace-pre-wrap">
        {win.text}
      </div>
    </div>
  );
}

function AxisAnnotationStrip({ orientation, annotations, color, paragraphs, viewport, size }: {
  orientation: 'horizontal' | 'vertical';
  annotations: Array<{ target: { selector: { start?: number; end?: number } } }>;
  color: string;
  paragraphs: Array<{ start: number; end: number }>;
  viewport: Viewport;
  size: number;
}) {
  const n = paragraphs.length;
  if (n === 0 || viewport.span === 0) return null;

  const density = new Float32Array(n);
  for (const ann of annotations) {
    const sel = ann.target.selector;
    if (sel.start == null || sel.end == null) continue;
    const sp = paragraphs.findIndex((p) => p.end > sel.start!);
    const ep = paragraphs.findIndex((p) => p.start >= sel.end!);
    for (let i = Math.max(0, sp); i < (ep < 0 ? n : ep); i++) density[i]++;
  }
  const maxD = Math.max(1, ...Array.from(density));
  const stripH = 6;
  const cellPx = size / viewport.span;
  const vpStart = orientation === 'horizontal' ? viewport.x : viewport.y;
  const bars: JSX.Element[] = [];
  const s = Math.max(0, Math.floor(vpStart));
  const e = Math.min(n, Math.ceil(vpStart + viewport.span));
  for (let i = s; i < e; i++) {
    if (density[i] === 0) continue;
    const pos = (i - vpStart) * cellPx;
    const op = 0.3 + 0.7 * (density[i] / maxD);
    if (orientation === 'horizontal') bars.push(<rect key={i} x={pos} y={0} width={Math.ceil(cellPx)} height={stripH} fill={color} fillOpacity={op} />);
    else bars.push(<rect key={i} x={0} y={pos} width={stripH} height={Math.ceil(cellPx)} fill={color} fillOpacity={op} />);
  }
  return orientation === 'horizontal'
    ? <svg width={size} height={stripH} className="shrink-0">{bars}</svg>
    : <svg width={stripH} height={size} className="shrink-0">{bars}</svg>;
}

export default function DotplotView(): JSX.Element | null {
  const textHicOpen = useViewStore((s) => s.textHicOpen);
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
  const [palette, setPalette] = useState<PaletteKey>('blues');
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, span: 0 });
  const [threshold, setThreshold] = useState(0);
  const [showDiagonal, setShowDiagonal] = useState(true);
  const [showControls, setShowControls] = useState(false);
  const [similarityMetric, setSimilarityMetric] = useState('cosine');

  // Click-click selection: first click sets corner1, second click sets corner2 and auto-zooms
  const [corner1, setCorner1] = useState<{ i: number; j: number } | null>(null);
  const [floatingWindows, setFloatingWindows] = useState<FloatingWindow[]>([]);

  const panning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const vpAtPanStart = useRef({ x: 0, y: 0 });
  const draggingWindowId = useRef<string | null>(null);
  const dragWindowStart = useRef({ mx: 0, my: 0, wx: 0, wy: 0 });

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

  const clampViewport = useCallback((vp: Viewport): Viewport => {
    const s = Math.max(2, Math.min(n, vp.span));
    let x = Math.max(0, vp.x);
    let y = Math.max(0, vp.y);
    if (x + s > n) x = Math.max(0, n - s);
    if (y + s > n) y = Math.max(0, n - s);
    return { x, y, span: s };
  }, [n]);

  const renderHeatmap = useCallback(() => {
    if (!signal || n === 0) return;
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const size = Math.max(1, Math.min(container.clientWidth - 60, container.clientHeight - 60));
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
          ctx.fillStyle = `rgb(${r},${g},${b})`;
          ctx.fillRect((j - vpX) * cellPx, (i - vpY) * cellPx, Math.ceil(cellPx), Math.ceil(cellPx));
        }
      }
    } else {
      const imageData = ctx.createImageData(size, size);
      const px = imageData.data;
      for (let py = 0; py < size; py++) {
        const i = Math.min(Math.floor(vpY + (py / size) * span), n - 1);
        for (let ppx = 0; ppx < size; ppx++) {
          const j = Math.min(Math.floor(vpX + (ppx / size) * span), n - 1);
          const off = (py * size + ppx) * 4;
          if ((!showDiagonal && i === j) || signal.data[i * n + j] < threshold) {
            px[off] = 248; px[off + 1] = 248; px[off + 2] = 248; px[off + 3] = 255;
          } else {
            const [r, g, b] = interpolateColor(signal.data[i * n + j], colors);
            px[off] = r; px[off + 1] = g; px[off + 2] = b; px[off + 3] = 255;
          }
        }
      }
      ctx.putImageData(imageData, 0, 0);
    }

    // Axis labels
    const labelInterval = span < 20 ? 1 : span < 50 ? 5 : span < 100 ? 10 : span < 300 ? 50 : 100;
    ctx.font = '9px monospace';
    ctx.fillStyle = '#999';
    for (let j = Math.ceil(vpX / labelInterval) * labelInterval; j <= vpX + span && j < n; j += labelInterval) {
      ctx.save();
      ctx.translate((j - vpX) * cellPx + cellPx / 2, size + 2);
      ctx.rotate(-Math.PI / 4);
      ctx.textAlign = 'right';
      ctx.fillText(`¶${j}`, 0, 0);
      ctx.restore();
    }
    for (let i = Math.ceil(vpY / labelInterval) * labelInterval; i <= vpY + span && i < n; i += labelInterval) {
      ctx.textAlign = 'right';
      ctx.fillText(`¶${i}`, -4, (i - vpY) * cellPx + cellPx / 2 + 3);
    }

    // Corner1 marker
    if (corner1) {
      const cx = (corner1.j - vpX) * cellPx;
      const cy = (corner1.i - vpY) * cellPx;
      ctx.strokeStyle = 'rgba(255, 100, 0, 0.9)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx + cellPx / 2, cy + cellPx / 2, Math.max(4, cellPx / 2), 0, Math.PI * 2);
      ctx.stroke();
      // Crosshair lines from corner1
      ctx.strokeStyle = 'rgba(255, 100, 0, 0.3)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, cy + cellPx / 2); ctx.lineTo(size, cy + cellPx / 2);
      ctx.moveTo(cx + cellPx / 2, 0); ctx.lineTo(cx + cellPx / 2, size);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Hover crosshair
    if (hoveredCell) {
      const hx = (hoveredCell.j - vpX) * cellPx;
      const hy = (hoveredCell.i - vpY) * cellPx;
      ctx.strokeStyle = 'rgba(255, 255, 0, 0.8)';
      ctx.lineWidth = 2;
      ctx.strokeRect(hx, hy, cellPx, cellPx);
      ctx.strokeStyle = 'rgba(255, 255, 0, 0.3)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, hy + cellPx / 2); ctx.lineTo(size, hy + cellPx / 2);
      ctx.moveTo(hx + cellPx / 2, 0); ctx.lineTo(hx + cellPx / 2, size);
      ctx.stroke();

      // If corner1 set, draw preview rectangle
      if (corner1) {
        const rx = Math.min(corner1.j, hoveredCell.j);
        const ry = Math.min(corner1.i, hoveredCell.i);
        const rw = Math.abs(hoveredCell.j - corner1.j) + 1;
        const rh = Math.abs(hoveredCell.i - corner1.i) + 1;
        ctx.strokeStyle = 'rgba(255, 100, 0, 0.7)';
        ctx.lineWidth = 2;
        ctx.strokeRect((rx - vpX) * cellPx, (ry - vpY) * cellPx, rw * cellPx, rh * cellPx);
        ctx.fillStyle = 'rgba(255, 100, 0, 0.05)';
        ctx.fillRect((rx - vpX) * cellPx, (ry - vpY) * cellPx, rw * cellPx, rh * cellPx);
      }
    }
  }, [signal, n, viewport, colors, threshold, showDiagonal, hoveredCell, corner1]);

  useEffect(() => { renderHeatmap(); }, [renderHeatmap]);

  const getCellFromEvent = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!signal || n === 0) return null;
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const cellPx = rect.width / viewport.span;
    return {
      i: Math.min(Math.max(Math.floor(viewport.y + (e.clientY - rect.top) / cellPx), 0), n - 1),
      j: Math.min(Math.max(Math.floor(viewport.x + (e.clientX - rect.left) / cellPx), 0), n - 1),
    };
  }, [signal, n, viewport]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    // Window dragging
    if (draggingWindowId.current) {
      const dx = e.clientX - dragWindowStart.current.mx;
      const dy = e.clientY - dragWindowStart.current.my;
      setFloatingWindows((ws) => ws.map((w) =>
        w.id === draggingWindowId.current ? { ...w, x: dragWindowStart.current.wx + dx, y: dragWindowStart.current.wy + dy } : w
      ));
      return;
    }
    // Panning
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
    if (cell) setHoveredCell(cell);
  }, [getCellFromEvent, viewport, clampViewport]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (e.button === 2 || e.ctrlKey || e.metaKey) {
      // Right-click or Ctrl+click = pan
      panning.current = true;
      panStart.current = { x: e.clientX, y: e.clientY };
      vpAtPanStart.current = { x: viewport.x, y: viewport.y };
      e.preventDefault();
      return;
    }
  }, [viewport]);

  const handleMouseUp = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (draggingWindowId.current) {
      draggingWindowId.current = null;
      return;
    }
    if (panning.current) {
      panning.current = false;
      return;
    }
    // Click-click selection
    const cell = getCellFromEvent(e);
    if (!cell) return;

    if (!corner1) {
      setCorner1(cell);
    } else {
      const rowMin = Math.min(corner1.i, cell.i);
      const rowMax = Math.max(corner1.i, cell.i);
      const colMin = Math.min(corner1.j, cell.j);
      const colMax = Math.max(corner1.j, cell.j);

      if (rowMax === rowMin && colMax === colMin) {
        setCorner1(null);
        return;
      }

      // Auto-zoom to selection
      const span = Math.max(rowMax - rowMin + 1, colMax - colMin + 1);
      setViewport(clampViewport({ x: colMin, y: rowMin, span: Math.max(2, span) }));

      // Open floating text comparison windows
      const rowText = paragraphs.slice(rowMin, rowMax + 1).map((p) => p.text).join('\n').slice(0, 3000);
      const colText = paragraphs.slice(colMin, colMax + 1).map((p) => p.text).join('\n').slice(0, 3000);

      const avgSim = signal ? computeAvgSimilarity(signal.data, n, rowMin, rowMax, colMin, colMax) : 0;

      setFloatingWindows([
        { id: 'row', title: `Y-axis ¶${rowMin}–¶${rowMax} (avg sim: ${avgSim.toFixed(3)})`, text: rowText, paraRange: [rowMin, rowMax], x: 20, y: 40 },
        { id: 'col', title: `X-axis ¶${colMin}–¶${colMax}`, text: colText, paraRange: [colMin, colMax], x: 390, y: 40 },
      ]);
      setCorner1(null);
    }
  }, [corner1, getCellFromEvent, clampViewport, paragraphs, signal, n]);

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
        return clampViewport({
          x: prev.x + mx * prev.span - mx * newSpan,
          y: prev.y + my * prev.span - my * newSpan,
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
    setCorner1(null);
    setFloatingWindows([]);
  }, [n]);

  const handleWindowDragStart = useCallback((id: string, e: React.MouseEvent) => {
    draggingWindowId.current = id;
    const win = floatingWindows.find((w) => w.id === id);
    if (win) dragWindowStart.current = { mx: e.clientX, my: e.clientY, wx: win.x, wy: win.y };
    e.preventDefault();
  }, [floatingWindows]);

  const activeTab = useViewStore((s) => s.activeTab);
  const isTabMode = activeTab === 'texthic';
  if (!textHicOpen && !isTabMode) return null;

  const hoverValue = hoveredCell && signal ? signal.data[hoveredCell.i * n + hoveredCell.j] : null;
  const zoomPct = n > 0 ? Math.round((viewport.span / n) * 100) : 100;

  const visibleTrackNames = trackOrder.filter((name) => {
    const state = trackStates[name];
    return state?.visible && name !== 'segments' && name !== 'sections';
  }).slice(0, 5);

  const canvasSize = containerRef.current ? Math.max(1, Math.min(containerRef.current.clientWidth - 60, containerRef.current.clientHeight - 60)) : 400;

  return (
    <div
      ref={containerRef}
      className="p-2 flex flex-col bg-[var(--color-bg-subtle)] relative"
      style={{ height: isTabMode ? '100%' : '35vh', flex: isTabMode ? 1 : undefined }}
      onMouseMove={(e) => { if (draggingWindowId.current) handleMouseMove(e as unknown as React.MouseEvent<HTMLCanvasElement>); }}
      onMouseUp={() => { if (draggingWindowId.current) draggingWindowId.current = null; }}
    >
      {/* Toolbar */}
      <div className="flex justify-between items-center mb-[4px] text-[0.85em] gap-2 flex-wrap shrink-0">
        <span className="font-bold">
          Self-Similarity Matrix
          {hoveredCell && hoverValue != null ? ` — [¶${hoveredCell.i}, ¶${hoveredCell.j}]: ${hoverValue.toFixed(3)}` : ''}
          {corner1 ? ` — Click second corner (first: ¶${corner1.i},¶${corner1.j})` : ''}
        </span>
        <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
          <select value={palette} onChange={(e) => setPalette(e.target.value as PaletteKey)}
            className="text-[0.85em] border border-[var(--color-border)] rounded px-1 py-0.5 bg-[var(--color-bg)] cursor-pointer">
            <option value="blues">Blues</option>
            <option value="viridis">Viridis</option>
            <option value="plasma">Plasma</option>
            <option value="diverging">Diverging</option>
          </select>
          <span className="text-[0.85em]">{zoomPct}%</span>
          {viewport.span < n && (
            <button onClick={zoomToFull} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">Reset</button>
          )}
          {corner1 && (
            <button onClick={() => setCorner1(null)} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[#ef4444] text-[#ef4444] cursor-pointer hover:bg-[#fef2f2]">Cancel selection</button>
          )}
          <button onClick={() => setShowControls(!showControls)} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">
            {showControls ? 'Hide filters' : 'Filters'}
          </button>
          <button onClick={exportPNG} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">Export PNG</button>
          <span className="text-[0.8em]">{n > 0 ? `${n}×${n} · ${similarityMetric}` : ''} · Scroll zoom · Right-drag pan</span>
        </div>
      </div>

      {/* Legend */}
      {signal && (
        <div className="flex items-center gap-2 mb-1 text-[0.75em] text-[var(--color-text-muted)] shrink-0">
          <span>0</span>
          <div className="flex-1 h-3 rounded-sm overflow-hidden flex" style={{ maxWidth: 200 }}>
            {Array.from({ length: 40 }, (_, i) => {
              const [r, g, b] = interpolateColor(i / 39, colors);
              return <div key={i} className="flex-1" style={{ backgroundColor: `rgb(${r},${g},${b})` }} />;
            })}
          </div>
          <span>1</span>
          <span className="ml-1">similarity</span>
          <span className="ml-2 text-[var(--color-text-muted)]">Click two points to select region</span>
        </div>
      )}

      {/* Filters */}
      {showControls && (
        <div className="flex items-center gap-3 mb-1 text-[0.75em] font-[var(--font-sans)] py-1 px-2 border border-[var(--color-border-subtle)] rounded bg-[var(--color-bg)] shrink-0">
          <label className="flex items-center gap-1">Threshold: <input type="range" min="0" max="100" value={Math.round(threshold * 100)} onChange={(e) => setThreshold(parseInt(e.target.value, 10) / 100)} className="w-[80px]" /> <span className="w-8 text-right">{(threshold * 100).toFixed(0)}%</span></label>
          <label className="flex items-center gap-1 cursor-pointer"><input type="checkbox" checked={showDiagonal} onChange={(e) => setShowDiagonal(e.target.checked)} className="accent-[var(--color-primary)]" /> Diagonal</label>
          <span className="text-[var(--color-text-muted)]">|</span>
          <label className="flex items-center gap-1">Metric: <select value={similarityMetric} onChange={(e) => setSimilarityMetric(e.target.value)} className="border border-[var(--color-border)] rounded px-1 py-0.5 bg-[var(--color-bg)] cursor-pointer">
            <option value="cosine">Cosine</option><option value="jaccard">Jaccard</option><option value="word_overlap">Word overlap</option><option value="edit_distance">Edit distance</option>
          </select></label>
        </div>
      )}

      {loading && <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">Loading self-similarity matrix...</div>}
      {error && <div className="flex-1 flex items-center justify-center text-[#b91c1c]">{error}</div>}

      {!loading && !error && signal && (
        <div className="flex-1 overflow-auto flex">
          <div className="flex flex-col">
            {visibleTrackNames.map((name) => (
              <AxisAnnotationStrip key={`top-${name}`} orientation="horizontal" annotations={allTracks[name] ?? []} color={TRACK_COLORS[name] ?? '#888'} paragraphs={paragraphs} viewport={viewport} size={canvasSize} />
            ))}
            <div className="flex">
              <div className="flex shrink-0">
                {visibleTrackNames.map((name) => (
                  <AxisAnnotationStrip key={`left-${name}`} orientation="vertical" annotations={allTracks[name] ?? []} color={TRACK_COLORS[name] ?? '#888'} paragraphs={paragraphs} viewport={viewport} size={canvasSize} />
                ))}
              </div>
              <canvas
                ref={canvasRef}
                onMouseMove={handleMouseMove}
                onMouseDown={handleMouseDown}
                onMouseUp={handleMouseUp}
                onContextMenu={(e) => e.preventDefault()}
                onMouseLeave={() => { setHoveredCell(null); if (panning.current) panning.current = false; }}
                className="cursor-crosshair"
                style={{ aspectRatio: '1', maxWidth: '100%' }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Floating text windows */}
      {floatingWindows.map((win) => (
        <DraggableWindow
          key={win.id}
          win={win}
          onClose={() => setFloatingWindows((ws) => ws.filter((w) => w.id !== win.id))}
          onDragStart={handleWindowDragStart}
        />
      ))}
    </div>
  );
}

function computeAvgSimilarity(data: Float32Array, n: number, rowMin: number, rowMax: number, colMin: number, colMax: number): number {
  let sum = 0;
  let count = 0;
  for (let i = rowMin; i <= rowMax; i++) {
    for (let j = colMin; j <= colMax; j++) {
      sum += data[i * n + j];
      count++;
    }
  }
  return count > 0 ? sum / count : 0;
}
