import { useEffect, useRef, useState, useCallback } from 'react';
import { useViewStore } from '../../stores/viewStore';
import { useProjectStore, getActiveProject } from '../../stores/projectStore';
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

function VirtualScrollbar({ orientation, viewportOffset, viewportSpan, total, onScroll }: {
  orientation: 'horizontal' | 'vertical';
  viewportOffset: number;
  viewportSpan: number;
  total: number;
  onScroll: (offset: number) => void;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => { return () => { cleanupRef.current?.(); }; }, []);

  if (total <= 0 || viewportSpan >= total) return null;

  const ratio = viewportSpan / total;
  const thumbPct = Math.max(8, ratio * 100);
  const offsetPct = (viewportOffset / total) * 100;
  const isH = orientation === 'horizontal';

  const handleThumbDown = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const startOffset = viewportOffset;
    const startMouse = isH ? e.clientX : e.clientY;

    const onMove = (ev: MouseEvent) => {
      if (!trackRef.current) return;
      const trackSize = isH ? trackRef.current.clientWidth : trackRef.current.clientHeight;
      const delta = ((isH ? ev.clientX : ev.clientY) - startMouse) / trackSize * total;
      onScroll(Math.max(0, Math.min(total - viewportSpan, startOffset + delta)));
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      cleanupRef.current = null;
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    cleanupRef.current = onUp;
  };

  const handleTrackClick = (e: React.MouseEvent) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const clickPos = isH ? (e.clientX - rect.left) / rect.width : (e.clientY - rect.top) / rect.height;
    const targetCenter = clickPos * total;
    onScroll(Math.max(0, Math.min(total - viewportSpan, targetCenter - viewportSpan / 2)));
  };

  return (
    <div
      ref={trackRef}
      onClick={handleTrackClick}
      role="scrollbar"
      aria-orientation={orientation}
      aria-valuenow={Math.round(viewportOffset)}
      aria-valuemin={0}
      aria-valuemax={Math.round(total - viewportSpan)}
      className={`${isH ? 'h-3 w-full' : 'w-3 h-full'} bg-[var(--color-bg-muted)] rounded-sm relative cursor-pointer shrink-0`}
    >
      <div
        onMouseDown={handleThumbDown}
        className={`absolute ${isH ? 'h-full' : 'w-full'} bg-[var(--color-text-muted)] rounded-sm opacity-40 hover:opacity-60 active:opacity-80 cursor-grab active:cursor-grabbing`}
        style={isH
          ? { left: `${offsetPct}%`, width: `${thumbPct}%` }
          : { top: `${offsetPct}%`, height: `${thumbPct}%` }
        }
      />
    </div>
  );
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
  const projectId = useProjectStore((s) => getActiveProject(s).metadata?.id);
  const paragraphs = useProjectStore((s) => getActiveProject(s).paragraphs);
  const allTracks = useProjectStore((s) => getActiveProject(s).tracks);
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
  const [chunkSize, setChunkSize] = useState(17);
  const [loadedChunkSize, setLoadedChunkSize] = useState(17);
  const [recomputing, setRecomputing] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [showAlignments, setShowAlignments] = useState(true);
  const [alignments, setAlignments] = useState<Array<{
    chunk_start_a: number; chunk_end_a: number;
    chunk_start_b: number; chunk_end_b: number;
    identity: number; length_chunks: number;
  }>>([]);

  // Click-click selection: first click sets corner1, second click sets corner2 and auto-zooms
  const [corner1, setCorner1] = useState<{ i: number; j: number } | null>(null);
  const [floatingWindows, setFloatingWindows] = useState<FloatingWindow[]>([]);

  const panning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const vpAtPanStart = useRef({ x: 0, y: 0, span: 0 });
  const draggingWindowId = useRef<string | null>(null);
  const dragWindowStart = useRef({ mx: 0, my: 0, wx: 0, wy: 0 });

  const [availableMetrics, setAvailableMetrics] = useState<string[]>([]);
  const [metricInfo, setMetricInfo] = useState<Record<string, { unit_type: string; n_units: number; dimensions: number[]; chunk_size?: number }>>({});

  useEffect(() => {
    if (!textHicOpen || !projectId) return;
    setLoading(true);
    setError(null);

    fetch(`/data/${projectId}/signals/self_similarity.json`)
      .then((r) => { if (!r.ok) throw new Error('not found'); return r.json(); })
      .then((manifest) => {
        const metrics: string[] = manifest.metadata?.available_metrics ?? [];
        const info = manifest.metadata?.metric_info ?? {};
        const manifestChunkSize: number = manifest.metadata?.chunk_size ?? 17;
        setAvailableMetrics(metrics);
        setMetricInfo(info);
        setLoadedChunkSize(manifestChunkSize);
        setChunkSize(manifestChunkSize);
        setRecomputing(false);

        const dataFile = metrics.length > 0
          ? `self_similarity_${similarityMetric}.bin`
          : manifest.data_file;

        // Use per-metric dimensions if available
        const metricDims = info[similarityMetric]?.dimensions ?? manifest.dimensions;

        return fetch(`/data/${projectId}/signals/${dataFile}`)
          .then((r) => { if (!r.ok) throw new Error('metric not available'); return r.arrayBuffer(); })
          .then((buf) => {
            const updatedManifest = { ...manifest, data_file: dataFile, dimensions: metricDims };
            setSignal({ manifest: updatedManifest, data: new Float32Array(buf) });
            const dim = metricDims[0];
            setViewport({ x: 0, y: 0, span: dim });
            setLoading(false);
          });
      })
      .catch(() => {
        setError('Self-similarity matrix not available. Run analysis with Ollama first.');
        setLoading(false);
      });

    // Load alignment records if available
    fetch(`/data/${projectId}/signals/self_similarity_alignments.json`)
      .then((r) => r.ok ? r.json() : [])
      .then((data) => setAlignments(Array.isArray(data) ? data : []))
      .catch(() => setAlignments([]));
  }, [textHicOpen, projectId, similarityMetric, reloadKey]);

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

    const size = Math.max(1, Math.min(container.clientWidth - 60, container.clientHeight - 120));
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

    // LASTZ alignment lines — draw in complementary color
    if (showAlignments && alignments.length > 0) {
      // Compute complementary color from palette
      const palMid = colors[Math.floor(colors.length / 2)];
      const compR = 255 - palMid[0], compG = 255 - palMid[1], compB = 255 - palMid[2];

      for (const aln of alignments) {
        const startA = aln.chunk_start_a;
        const endA = aln.chunk_end_a;
        const startB = aln.chunk_start_b;
        const endB = aln.chunk_end_b;

        // Check if alignment is in viewport
        if (endA < vpX || startA > vpX + span || endB < vpY || startB > vpY + span) continue;
        if (endB < vpX || startB > vpX + span || endA < vpY || startA > vpY + span) continue;

        const alpha = Math.min(1.0, 0.4 + aln.identity * 0.6);
        ctx.strokeStyle = `rgba(${compR},${compG},${compB},${alpha})`;
        ctx.lineWidth = Math.max(2, cellPx * 0.6);
        ctx.lineCap = 'round';
        ctx.beginPath();

        // Draw line from (startB, startA) to (endB, endA) — both triangle halves
        const x1 = (startB - vpX) * cellPx + cellPx / 2;
        const y1 = (startA - vpY) * cellPx + cellPx / 2;
        const x2 = (endB - vpX) * cellPx + cellPx / 2;
        const y2 = (endA - vpY) * cellPx + cellPx / 2;
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);

        // Mirror: (startA, startB) to (endA, endB)
        const mx1 = (startA - vpX) * cellPx + cellPx / 2;
        const my1 = (startB - vpY) * cellPx + cellPx / 2;
        const mx2 = (endA - vpX) * cellPx + cellPx / 2;
        const my2 = (endB - vpY) * cellPx + cellPx / 2;
        ctx.moveTo(mx1, my1);
        ctx.lineTo(mx2, my2);

        ctx.stroke();
      }
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
  }, [signal, n, viewport, colors, threshold, showDiagonal, hoveredCell, corner1, showAlignments, alignments]);

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
      const span = vpAtPanStart.current.span;
      const dx = (e.clientX - panStart.current.x) / rect.width * span;
      const dy = (e.clientY - panStart.current.y) / rect.height * span;
      setViewport(clampViewport({
        x: vpAtPanStart.current.x - dx,
        y: vpAtPanStart.current.y - dy,
        span,
      }));
      return;
    }
    const cell = getCellFromEvent(e);
    if (cell) setHoveredCell(cell);
  }, [getCellFromEvent, clampViewport]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (e.button === 2 || e.button === 1 || e.ctrlKey || e.metaKey) {
      panning.current = true;
      panStart.current = { x: e.clientX, y: e.clientY };
      vpAtPanStart.current = { x: viewport.x, y: viewport.y, span: viewport.span };
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

  const exportImage = useCallback((format: 'png' | 'svg') => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    if (format === 'svg') {
      const dataUrl = canvas.toDataURL('image/png');
      const svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}">
<image href="${dataUrl}" width="${canvas.width}" height="${canvas.height}"/>
</svg>`;
      link.download = `texthic-${projectId ?? 'heatmap'}.svg`;
      link.href = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgContent);
    } else {
      link.download = `texthic-${projectId ?? 'heatmap'}.png`;
      link.href = canvas.toDataURL('image/png');
    }
    link.click();
  }, [projectId]);

  const zoomToFull = useCallback(() => {
    setViewport({ x: 0, y: 0, span: n });
    setCorner1(null);
    setFloatingWindows([]);
  }, [n]);

  const zoomBy = useCallback((factor: number) => {
    setViewport((prev) => {
      const cx = prev.x + prev.span / 2;
      const cy = prev.y + prev.span / 2;
      const newSpan = prev.span * factor;
      return clampViewport({ x: cx - newSpan / 2, y: cy - newSpan / 2, span: newSpan });
    });
  }, [clampViewport]);

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

  const canvasSize = containerRef.current ? Math.max(1, Math.min(containerRef.current.clientWidth - 60, containerRef.current.clientHeight - 120)) : 400;

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
          <button onClick={() => zoomBy(0.5)} title="Zoom in" className="text-[0.8em] px-1 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)] leading-none font-bold">+</button>
          <span className="text-[0.85em] min-w-[3em] text-center">{zoomPct}%</span>
          <button onClick={() => zoomBy(2)} title="Zoom out" className="text-[0.8em] px-1 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)] leading-none font-bold">−</button>
          <button onClick={zoomToFull} title="Fit full matrix" className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">Fit</button>
          {corner1 && (
            <button onClick={() => setCorner1(null)} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[#ef4444] text-[#ef4444] cursor-pointer hover:bg-[#fef2f2]">Cancel selection</button>
          )}
          <button onClick={() => setShowControls(!showControls)} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">
            {showControls ? 'Hide filters' : 'Filters'}
          </button>
          <button onClick={() => exportImage('png')} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">PNG</button>
          <button onClick={() => exportImage('svg')} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">SVG</button>
          <span className="text-[0.8em]">{n > 0 ? `${n}×${n} chunks · ${similarityMetric}${metricInfo[similarityMetric]?.chunk_size ? ` (${metricInfo[similarityMetric].chunk_size}w)` : ''}` : ''}{alignments.length > 0 ? ` · ${alignments.length} alignments` : ''}{loading ? ' · Loading…' : ''} · Wheel=zoom · Ctrl/Right-drag=pan</span>
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
          <label className="flex items-center gap-1">Metric: <select value={similarityMetric} onChange={(e) => {
            setSimilarityMetric(e.target.value);
          }} className="border border-[var(--color-border)] rounded px-1 py-0.5 bg-[var(--color-bg)] cursor-pointer" title="Switch similarity metric — all metrics are pre-computed">
            {(availableMetrics.length > 0 ? availableMetrics : ['cosine', 'jaccard', 'word_overlap', 'edit_distance']).map((m) => (
              <option key={m} value={m}>{m === 'word_overlap' ? 'Word overlap' : m === 'edit_distance' ? 'Edit distance' : m.charAt(0).toUpperCase() + m.slice(1)}</option>
            ))}
          </select></label>
          {alignments.length > 0 && (<>
            <span className="text-[var(--color-text-muted)]">|</span>
            <label className="flex items-center gap-1 cursor-pointer"><input type="checkbox" checked={showAlignments} onChange={(e) => setShowAlignments(e.target.checked)} className="accent-[var(--color-primary)]" /> Alignments ({alignments.length})</label>
          </>)}
          <span className="text-[var(--color-text-muted)]">|</span>
          <label className="flex items-center gap-1">
            Chunk:
            <input type="range" min="5" max="25" value={chunkSize} onChange={(e) => setChunkSize(parseInt(e.target.value, 10))} className="w-[80px]" title="Words per chunk (5-25)" />
            <span className="w-8 text-right font-[var(--font-mono)]">{chunkSize}w</span>
          </label>
          {chunkSize !== loadedChunkSize && (
            <button
              onClick={async () => {
                if (!projectId || recomputing) return;
                setRecomputing(true);
                await fetch(`/api/projects/${projectId}/analyze/self_similarity?chunk_size=${chunkSize}`, { method: 'POST' });
                const poll = setInterval(async () => {
                  const r = await fetch(`/api/projects/${projectId}/analyze/self_similarity/status`);
                  const d = await r.json();
                  if (d.status !== 'running') {
                    clearInterval(poll);
                    setRecomputing(false);
                    setReloadKey((k) => k + 1);
                  }
                }, 3000);
              }}
              disabled={recomputing}
              className="px-2 py-0.5 rounded bg-[var(--color-primary)] text-white cursor-pointer hover:opacity-90 disabled:opacity-50 disabled:cursor-wait"
            >
              {recomputing ? 'Computing…' : 'Recompute'}
            </button>
          )}
        </div>
      )}

      {loading && <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">Loading self-similarity matrix...</div>}
      {error && <div className="flex-1 flex items-center justify-center text-[#b91c1c]">{error}</div>}

      {!loading && !error && signal && (
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 flex flex-col min-h-0">
            {visibleTrackNames.map((name) => (
              <AxisAnnotationStrip key={`top-${name}`} orientation="horizontal" annotations={allTracks[name] ?? []} color={TRACK_COLORS[name] ?? '#888'} paragraphs={paragraphs} viewport={viewport} size={canvasSize} />
            ))}
            <div className="flex flex-1 min-h-0">
              <div className="flex shrink-0">
                {visibleTrackNames.map((name) => (
                  <AxisAnnotationStrip key={`left-${name}`} orientation="vertical" annotations={allTracks[name] ?? []} color={TRACK_COLORS[name] ?? '#888'} paragraphs={paragraphs} viewport={viewport} size={canvasSize} />
                ))}
              </div>
              <div className="flex flex-col flex-1 min-w-0 min-h-0">
                <div className="flex-1 min-h-0 flex items-start">
                  <canvas
                    ref={canvasRef}
                    onMouseMove={handleMouseMove}
                    onMouseDown={handleMouseDown}
                    onMouseUp={handleMouseUp}
                    onContextMenu={(e) => e.preventDefault()}
                    onMouseLeave={() => { setHoveredCell(null); if (panning.current) panning.current = false; }}
                    className="cursor-crosshair"
                    role="img"
                    aria-label={`Self-similarity heatmap, ${n}×${n} paragraphs. ${hoveredCell ? `Cell [${hoveredCell.i}, ${hoveredCell.j}]: similarity ${hoverValue?.toFixed(3) ?? 'N/A'}` : 'Hover to inspect cells. Click two points to select a region.'}`}
                  />
                </div>
                <VirtualScrollbar
                  orientation="horizontal"
                  viewportOffset={viewport.x}
                  viewportSpan={viewport.span}
                  total={n}
                  onScroll={(x) => setViewport((prev) => clampViewport({ ...prev, x }))}
                />
              </div>
              <VirtualScrollbar
                orientation="vertical"
                viewportOffset={viewport.y}
                viewportSpan={viewport.span}
                total={n}
                onScroll={(y) => setViewport((prev) => clampViewport({ ...prev, y }))}
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
