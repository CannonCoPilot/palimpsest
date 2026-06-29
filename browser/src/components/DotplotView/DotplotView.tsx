import { useEffect, useRef, useState, useCallback, type ReactElement } from 'react';
import { useViewStore } from '../../stores/viewStore';
import { useProjectStore, getActiveProject } from '../../stores/projectStore';
import { useTrackStore } from '../../stores/trackStore';
import { type LoadedSignal } from '../../adapters/SignalAdapter';
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

export function interpolateColor(value: number, palette: number[][]): [number, number, number] {
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

/**
 * Palette colors at low similarity (Blues low-end, Diverging center) are
 * near-white and unreadable as text on a light panel. Darken toward the same
 * hue until luminance is comfortably readable, preserving the color coding.
 */
export function readableTextColor([r, g, b]: [number, number, number]): string {
  const lum = 0.299 * r + 0.587 * g + 0.114 * b;
  const MAX_LUM = 140;
  if (lum <= MAX_LUM) return `rgb(${r},${g},${b})`;
  const f = MAX_LUM / lum;
  return `rgb(${Math.round(r * f)},${Math.round(g * f)},${Math.round(b * f)})`;
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
  similarity: number;
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

function FixedTextPanel({ win, onClose, colors }: {
  win: FloatingWindow;
  onClose: () => void;
  colors: number[][];
}) {
  const [r, g, b] = interpolateColor(win.similarity, colors);
  const textColor = readableTextColor([r, g, b]);
  const borderColor = `rgb(${r},${g},${b})`;

  return (
    <div
      className="bg-[var(--color-bg)] border-l-4 rounded shadow-sm flex flex-col mb-2"
      style={{ borderLeftColor: borderColor, maxHeight: 260 }}
    >
      <div className="flex items-center justify-between px-2 py-1 text-[0.75em] font-[var(--font-sans)]" style={{ backgroundColor: `rgba(${r},${g},${b},0.08)` }}>
        <span className="font-semibold" style={{ color: textColor }}>{win.title}</span>
        <button onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] cursor-pointer ml-2">✕</button>
      </div>
      <div className="flex-1 overflow-auto p-2 text-[0.8em] font-[var(--font-serif)] leading-relaxed whitespace-pre-wrap" style={{ color: textColor }}>
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
  const stripH = 3;
  const cellPx = size / viewport.span;
  const vpStart = orientation === 'horizontal' ? viewport.x : viewport.y;
  const bars: ReactElement[] = [];
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

export default function DotplotView(): ReactElement | null {
  const textHicOpen = useViewStore((s) => s.textHicOpen);
  const projectId = useProjectStore((s) => getActiveProject(s).metadata?.id);
  const paragraphs = useProjectStore((s) => getActiveProject(s).paragraphs);
  const allTracks = useProjectStore((s) => getActiveProject(s).tracks);
  const trackStates = useTrackStore((s) => s.tracks);
  const trackOrder = useTrackStore((s) => s.trackOrder);

  // Double-buffer: static matrix canvas + dynamic overlay canvas
  const matrixCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
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
  const [showAlignments, setShowAlignments] = useState(true);
  const [alignments, setAlignments] = useState<Array<{
    chunk_start_a: number; chunk_end_a: number;
    chunk_start_b: number; chunk_end_b: number;
    identity: number; length_chunks: number;
    metric?: string;
    // B3: per-record honesty label. "exact" under uniform word/punctuation/verse chunking;
    // "approximate" under slide/smart, where non-uniform windows make the refined boundaries fuzzy.
    refinement?: 'exact' | 'approximate';
  }>>([]);

  const [corner1, setCorner1] = useState<{ i: number; j: number } | null>(null);
  const [floatingWindows, setFloatingWindows] = useState<FloatingWindow[]>([]);
  const [showTrackPanel, setShowTrackPanel] = useState(false);
  const [hiddenTracks, setHiddenTracks] = useState<Set<string>>(new Set());
  const [showChapterGrid, setShowChapterGrid] = useState(false);
  const [showAlignmentsList, setShowAlignmentsList] = useState(false);

  const panning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const vpAtPanStart = useRef({ x: 0, y: 0, span: 0 });

  const [availableMetrics, setAvailableMetrics] = useState<string[]>([]);
  const [availableChunkSizes, setAvailableChunkSizes] = useState<number[]>([]);
  const [metricInfo, setMetricInfo] = useState<Record<string, { unit_type: string; n_units: number; dimensions: number[]; chunk_size?: number; alignment_refinement?: 'exact' | 'approximate' }>>({});

  // Load self-similarity data — responds to metric changes and chunk size changes
  useEffect(() => {
    if (!textHicOpen || !projectId) return;
    setLoading(true);
    setError(null);

    fetch(`/data/${projectId}/signals/self_similarity.json`)
      .then((r) => { if (!r.ok) throw new Error('not found'); return r.json(); })
      .then(async (manifest) => {
        const metrics: string[] = manifest.metadata?.available_metrics ?? [];
        const info = manifest.metadata?.metric_info ?? {};
        const manifestChunkSize: number = manifest.metadata?.chunk_size ?? 17;
        const chunkSizes: number[] = manifest.metadata?.available_chunk_sizes ?? [manifestChunkSize];
        setAvailableMetrics(metrics);
        setMetricInfo(info);
        setAvailableChunkSizes(chunkSizes);
        setLoadedChunkSize(manifestChunkSize);

        // Post-P7 a run may compute only a subset of metrics (e.g. a text-only word_overlap run
        // produces no cosine/jaccard). If the selected metric wasn't computed, fall back to the
        // manifest's primary metric, else the first available one, and let the effect re-run.
        if (metrics.length > 0 && !metrics.includes(similarityMetric)) {
          const primaryMetric = manifest.metadata?.primary;
          setSimilarityMetric(
            typeof primaryMetric === 'string' && metrics.includes(primaryMetric) ? primaryMetric : metrics[0],
          );
          return;
        }

        // Determine which chunk size to load
        const targetCS = chunkSizes.includes(chunkSize) ? chunkSize : manifestChunkSize;
        if (targetCS !== chunkSize) setChunkSize(targetCS);

        // Load from per-chunk-size endpoint if available, else fallback to flat files
        let dataUrl: string;
        let alnUrl: string;
        if (chunkSizes.includes(targetCS)) {
          dataUrl = `/api/projects/${projectId}/self_similarity/cs/${targetCS}/${similarityMetric}`;
          alnUrl = `/api/projects/${projectId}/self_similarity/cs/${targetCS}/alignments`;
        } else {
          dataUrl = `/data/${projectId}/signals/self_similarity_${similarityMetric}.bin`;
          alnUrl = `/data/${projectId}/signals/self_similarity_alignments.json`;
        }

        // Try per-CS endpoint first, fallback to flat
        let buf: ArrayBuffer;
        try {
          const r = await fetch(dataUrl);
          if (!r.ok) throw new Error('not found at cs endpoint');
          buf = await r.arrayBuffer();
        } catch {
          const r2 = await fetch(`/data/${projectId}/signals/self_similarity_${similarityMetric}.bin`);
          if (!r2.ok) throw new Error('metric not available');
          buf = await r2.arrayBuffer();
        }

        const metricDims = info[similarityMetric]?.dimensions ?? manifest.dimensions;
        // Compute actual dimensions from buffer size
        const floatCount = buf.byteLength / 4;
        const actualDim = Math.round(Math.sqrt(floatCount));
        const dims = floatCount === metricDims[0] * metricDims[1] ? metricDims : [actualDim, actualDim];

        const updatedManifest = { ...manifest, data_file: `self_similarity_${similarityMetric}.bin`, dimensions: dims };
        setSignal({ manifest: updatedManifest, data: new Float32Array(buf) });
        setViewport({ x: 0, y: 0, span: dims[0] });
        setLoading(false);

        // Load alignments
        fetch(alnUrl)
          .then((r) => r.ok ? r.json() : [])
          .then((data) => setAlignments(Array.isArray(data) ? data : []))
          .catch(() => setAlignments([]));
      })
      .catch(() => {
        setError('Self-similarity matrix not available. Run analysis first.');
        setLoading(false);
      });
  }, [textHicOpen, projectId, similarityMetric, chunkSize]);

  const n = signal ? signal.manifest.dimensions[0] : 0;
  const colors = PALETTES[palette];

  // B3: alignment-boundary refinement for the currently displayed metric. Prefer the manifest's
  // per-metric label; fall back to the per-record label (all records of one run share it). Drives
  // the "exact vs approximate boundaries" honesty note in the alignments list.
  const viewRefinement: 'exact' | 'approximate' | undefined =
    metricInfo[similarityMetric]?.alignment_refinement ?? alignments[0]?.refinement;

  const clampViewport = useCallback((vp: Viewport): Viewport => {
    const s = Math.max(2, Math.min(n, vp.span));
    let x = Math.max(0, vp.x);
    let y = Math.max(0, vp.y);
    if (x + s > n) x = Math.max(0, n - s);
    if (y + s > n) y = Math.max(0, n - s);
    return { x, y, span: s };
  }, [n]);

  // Render static matrix (only redraws on data/viewport/palette/threshold change)
  const renderMatrix = useCallback(() => {
    if (!signal || n === 0) return;
    const canvas = matrixCanvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rightPanelWidth = floatingWindows.length > 0 ? 320 : 0;
    const size = Math.max(1, Math.min(container.clientWidth - rightPanelWidth - 8, container.clientHeight - 120));
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

    // Axis labels — chunk indices, not paragraph indices
    const labelInterval = span < 20 ? 1 : span < 50 ? 5 : span < 100 ? 10 : span < 300 ? 50 : 100;
    ctx.font = '9px monospace';
    ctx.fillStyle = '#999';
    for (let j = Math.ceil(vpX / labelInterval) * labelInterval; j <= vpX + span && j < n; j += labelInterval) {
      ctx.save();
      ctx.translate((j - vpX) * cellPx + cellPx / 2, size + 2);
      ctx.rotate(-Math.PI / 4);
      ctx.textAlign = 'right';
      ctx.fillText(`${j}`, 0, 0);
      ctx.restore();
    }
    for (let i = Math.ceil(vpY / labelInterval) * labelInterval; i <= vpY + span && i < n; i += labelInterval) {
      ctx.textAlign = 'right';
      ctx.fillText(`${i}`, -4, (i - vpY) * cellPx + cellPx / 2 + 3);
    }

    // Chapter boundary gridlines
    if (showChapterGrid && paragraphs.length > 0) {
      const chapterPattern = /^(chapter\s|CHAPTER\s|Part\s|PART\s|[IVXLCDM]{1,5}[\.\s]|[A-Z]{2,}[\s:])/;
      const offsets = signal?.manifest?.segment_offsets;
      const chapterChunks = new Set<number>();
      paragraphs.forEach((p, paraIdx) => {
        if (chapterPattern.test(p.text.trimStart())) {
          // find which chunk this paragraph index maps to via segment_offsets
          if (offsets) {
            for (let ci = 0; ci < offsets.length; ci++) {
              const [s, e] = offsets[ci];
              if (p.start >= s && p.start < e) { chapterChunks.add(ci); break; }
            }
          } else {
            // no offsets: approximate by paragraph index ratio
            const ci = Math.round((paraIdx / paragraphs.length) * n);
            chapterChunks.add(ci);
          }
        }
      });
      ctx.save();
      ctx.strokeStyle = 'rgba(0,0,0,0.18)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      for (const ci of chapterChunks) {
        if (ci < vpX || ci > vpX + span) continue;
        const px2 = (ci - vpX) * cellPx;
        ctx.beginPath();
        ctx.moveTo(px2, 0);
        ctx.lineTo(px2, size);
        ctx.moveTo(0, px2);
        ctx.lineTo(size, px2);
        ctx.stroke();
      }
      ctx.setLineDash([]);
      ctx.restore();
    }

    // LASTZ alignment lines — complementary color, FIXED axis mapping
    if (showAlignments && alignments.length > 0) {
      const palMid = colors[Math.floor(colors.length / 2)];
      const compR = 255 - palMid[0], compG = 255 - palMid[1], compB = 255 - palMid[2];

      for (const aln of alignments) {
        const startA = aln.chunk_start_a;
        const endA = aln.chunk_end_a;
        const startB = aln.chunk_start_b;
        const endB = aln.chunk_end_b;

        // FIXED: A maps to Y-axis (rows), B maps to X-axis (columns)
        if (endA < vpY || startA > vpY + span || endB < vpX || startB > vpX + span) continue;

        const alpha = Math.min(1.0, 0.4 + aln.identity * 0.6);
        ctx.strokeStyle = `rgba(${compR},${compG},${compB},${alpha})`;
        ctx.lineWidth = Math.max(2, cellPx * 0.6);
        ctx.lineCap = 'round';
        ctx.beginPath();

        // Direct line: (B→X, A→Y)
        const x1 = (startB - vpX) * cellPx + cellPx / 2;
        const y1 = (startA - vpY) * cellPx + cellPx / 2;
        const x2 = (endB - vpX) * cellPx + cellPx / 2;
        const y2 = (endA - vpY) * cellPx + cellPx / 2;
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);

        // Mirror: (A→X, B→Y)
        if (endB < vpY || startB > vpY + span || endA < vpX || startA > vpX + span) {
          ctx.stroke();
          continue;
        }
        const mx1 = (startA - vpX) * cellPx + cellPx / 2;
        const my1 = (startB - vpY) * cellPx + cellPx / 2;
        const mx2 = (endA - vpX) * cellPx + cellPx / 2;
        const my2 = (endB - vpY) * cellPx + cellPx / 2;
        ctx.moveTo(mx1, my1);
        ctx.lineTo(mx2, my2);

        ctx.stroke();
      }
    }
  }, [signal, n, viewport, colors, threshold, showDiagonal, showAlignments, alignments, showChapterGrid, paragraphs, floatingWindows]);

  // Render dynamic overlay (hover crosshair, selection) — lightweight, no matrix repaint
  const renderOverlay = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    const matrixCanvas = matrixCanvasRef.current;
    if (!canvas || !matrixCanvas || !signal || n === 0) return;

    canvas.width = matrixCanvas.width;
    canvas.height = matrixCanvas.height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const size = canvas.width;
    const cellPx = size / viewport.span;
    const { x: vpX, y: vpY } = viewport;

    // Corner1 marker
    if (corner1) {
      const cx = (corner1.j - vpX) * cellPx;
      const cy = (corner1.i - vpY) * cellPx;
      ctx.strokeStyle = 'rgba(255, 100, 0, 0.9)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx + cellPx / 2, cy + cellPx / 2, Math.max(4, cellPx / 2), 0, Math.PI * 2);
      ctx.stroke();
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
  }, [signal, n, viewport, hoveredCell, corner1]);

  // Matrix redraws on data/viewport/palette changes
  useEffect(() => { renderMatrix(); }, [renderMatrix]);
  // Overlay redraws on hover/selection changes (lightweight)
  useEffect(() => { renderOverlay(); }, [renderOverlay]);

  // The render effects above only fire on data/viewport/palette changes, so a
  // container resize (window resize, side-panel toggle) would otherwise leave
  // the canvas at its stale dimensions and truncate the plot. Observe the
  // container and redraw via a ref-to-latest so the observer is created once
  // rather than churning on every hover/viewport change.
  const resizeRenderRef = useRef<() => void>(() => {});
  resizeRenderRef.current = () => { renderMatrix(); renderOverlay(); };
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(() => resizeRenderRef.current());
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const getCellFromEvent = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!signal || n === 0) return null;
    const canvas = overlayCanvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const cellPx = rect.width / viewport.span;
    return {
      i: Math.min(Math.max(Math.floor(viewport.y + (e.clientY - rect.top) / cellPx), 0), n - 1),
      j: Math.min(Math.max(Math.floor(viewport.x + (e.clientX - rect.left) / cellPx), 0), n - 1),
    };
  }, [signal, n, viewport]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (panning.current) {
      const canvas = overlayCanvasRef.current;
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
    if (panning.current) {
      panning.current = false;
      return;
    }
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

      const span = Math.max(rowMax - rowMin + 1, colMax - colMin + 1);
      setViewport(clampViewport({ x: colMin, y: rowMin, span: Math.max(2, span) }));

      const avgSim = signal ? computeAvgSimilarity(signal.data, n, rowMin, rowMax, colMin, colMax) : 0;

      // Use segment_offsets from manifest for text extraction
      const offsets = signal?.manifest?.segment_offsets;
      let rowText = '';
      let colText = '';
      if (offsets && paragraphs.length > 0) {
        const fullText = paragraphs.map((p) => p.text).join('\n');
        const rowStart = offsets[rowMin]?.[0] ?? 0;
        const rowEnd = offsets[Math.min(rowMax, offsets.length - 1)]?.[1] ?? 0;
        const colStart = offsets[colMin]?.[0] ?? 0;
        const colEnd = offsets[Math.min(colMax, offsets.length - 1)]?.[1] ?? 0;
        rowText = fullText.slice(rowStart, Math.min(rowEnd, rowStart + 3000));
        colText = fullText.slice(colStart, Math.min(colEnd, colStart + 3000));
      }
      if (!rowText) {
        rowText = paragraphs.slice(rowMin, Math.min(rowMax + 1, paragraphs.length)).map((p) => p.text).join('\n').slice(0, 3000);
        colText = paragraphs.slice(colMin, Math.min(colMax + 1, paragraphs.length)).map((p) => p.text).join('\n').slice(0, 3000);
      }

      setFloatingWindows([
        { id: 'row', title: `Y [${rowMin}–${rowMax}] sim=${avgSim.toFixed(3)}`, text: rowText, paraRange: [rowMin, rowMax], similarity: avgSim },
        { id: 'col', title: `X [${colMin}–${colMax}]`, text: colText, paraRange: [colMin, colMax], similarity: avgSim },
      ]);
      setCorner1(null);
    }
  }, [corner1, getCellFromEvent, clampViewport, paragraphs, signal, n]);

  // Wheel zoom
  useEffect(() => {
    const canvas = overlayCanvasRef.current;
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
    const canvas = matrixCanvasRef.current;
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

  const activeTab = useViewStore((s) => s.activeTab);
  const isTabMode = activeTab === 'texthic';
  if (!textHicOpen && !isTabMode) return null;

  const hoverValue = hoveredCell && signal ? signal.data[hoveredCell.i * n + hoveredCell.j] : null;
  const zoomPct = n > 0 ? Math.round((viewport.span / n) * 100) : 100;

  const allVisibleTrackNames = trackOrder.filter((name) => {
    const state = trackStates[name];
    return state?.visible && name !== 'segments' && name !== 'sections';
  });

  const visibleTrackNames = allVisibleTrackNames.filter((name) => !hiddenTracks.has(name));

  const rightPanelWidth = floatingWindows.length > 0 ? 320 : 0;
  const canvasSize = containerRef.current ? Math.max(1, Math.min(containerRef.current.clientWidth - rightPanelWidth - 8, containerRef.current.clientHeight - 120)) : 400;

  const chunkSizeHasData = availableChunkSizes.includes(chunkSize);
  const chunkSizeNotCached = !chunkSizeHasData;

  return (
    <div
      ref={containerRef}
      className="p-2 flex flex-col bg-[var(--color-bg-subtle)] relative"
      style={{ height: isTabMode ? '100%' : '35vh', flex: isTabMode ? 1 : undefined }}
    >
      {/* Toolbar */}
      <div className="flex justify-between items-center mb-[4px] text-[0.85em] gap-2 flex-wrap shrink-0">
        <span className="font-bold">
          Self-Similarity Matrix
          {hoveredCell && hoverValue != null ? ` — [${hoveredCell.i}, ${hoveredCell.j}]: ${hoverValue.toFixed(3)}` : ''}
          {corner1 ? ` — Click second corner (first: ${corner1.i},${corner1.j})` : ''}
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
          <button onClick={() => zoomBy(2)} title="Zoom out" className="text-[0.8em] px-1 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)] leading-none font-bold">-</button>
          <button onClick={zoomToFull} title="Fit full matrix" className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">Fit</button>
          {corner1 && (
            <button onClick={() => setCorner1(null)} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[#ef4444] text-[#ef4444] cursor-pointer hover:bg-[#fef2f2]">Cancel selection</button>
          )}
          <button onClick={() => setShowControls(!showControls)} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">
            {showControls ? 'Hide filters' : 'Filters'}
          </button>
          {allVisibleTrackNames.length > 0 && (
            <button onClick={() => setShowTrackPanel(!showTrackPanel)} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">
              {showTrackPanel ? 'Hide tracks' : 'Tracks'}
            </button>
          )}
          <button onClick={() => exportImage('png')} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">PNG</button>
          <button onClick={() => exportImage('svg')} className="text-[0.8em] px-1.5 py-0.5 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)]">SVG</button>
          <span className="text-[0.8em]">{n > 0 ? `${n}×${n} chunks (${chunkSize}w) · ${similarityMetric}` : ''}{alignments.length > 0 ? ` · ${alignments.length} alns` : ''}{loading ? ' · Loading…' : ''} · Wheel=zoom · Ctrl/Right-drag=pan</span>
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
          {availableChunkSizes.length > 1 && (
            <span className="ml-2">Cached: {availableChunkSizes.map(cs => `${cs}w`).join(', ')}</span>
          )}
          <span className="ml-2 text-[var(--color-text-muted)]">Click two points to select region</span>
        </div>
      )}

      {/* Filters */}
      {showControls && (
        <div className="flex items-center gap-3 mb-1 text-[0.75em] font-[var(--font-sans)] py-1 px-2 border border-[var(--color-border-subtle)] rounded bg-[var(--color-bg)] shrink-0 flex-wrap">
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
          <label className="flex items-center gap-1 cursor-pointer"><input type="checkbox" checked={showChapterGrid} onChange={(e) => setShowChapterGrid(e.target.checked)} className="accent-[var(--color-primary)]" /> Chapters</label>
          <span className="text-[var(--color-text-muted)]">|</span>
          <label className="flex items-center gap-1">
            Chunk:
            <input type="range" min="5" max="25" value={chunkSize} onChange={(e) => setChunkSize(parseInt(e.target.value, 10))} className="w-[80px]" title="Words per chunk (5-25)" />
            <span className="w-8 text-right font-[var(--font-mono)]">{chunkSize}w</span>
            {chunkSizeHasData && chunkSize !== loadedChunkSize && (
              <span className="text-green-600 text-[0.85em]">cached</span>
            )}
          </label>
          {chunkSizeNotCached && (
            <span className="text-[0.8em] text-[var(--color-text-muted)]" title="This view shows cached chunk sizes only — produce a new size from the Analysis panel">
              not cached — produce in Analysis panel
            </span>
          )}
        </div>
      )}

      {/* Track visibility panel */}
      {showTrackPanel && allVisibleTrackNames.length > 0 && (
        <div className="flex items-center gap-3 mb-1 text-[0.75em] font-[var(--font-sans)] py-1 px-2 border border-[var(--color-border-subtle)] rounded bg-[var(--color-bg)] shrink-0 flex-wrap">
          <span className="font-semibold text-[var(--color-text-muted)]">Tracks:</span>
          {allVisibleTrackNames.map((name) => (
            <label key={name} className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={!hiddenTracks.has(name)}
                onChange={(e) => {
                  setHiddenTracks((prev) => {
                    const next = new Set(prev);
                    if (e.target.checked) next.delete(name);
                    else next.add(name);
                    return next;
                  });
                }}
                className="accent-[var(--color-primary)]"
              />
              <span style={{ color: TRACK_COLORS[name] ?? '#888' }}>{name}</span>
            </label>
          ))}
        </div>
      )}

      {/* Alignments list panel */}
      {alignments.length > 0 && (
        <div className="mb-1 shrink-0">
          <button
            onClick={() => setShowAlignmentsList(!showAlignmentsList)}
            className="text-[0.75em] px-2 py-0.5 rounded border border-[var(--color-border-subtle)] bg-[var(--color-bg)] cursor-pointer hover:bg-[var(--color-bg-muted)] w-full text-left font-[var(--font-sans)]"
          >
            {showAlignmentsList ? '▾' : '▸'} Alignments ({alignments.length})
            {viewRefinement && (
              <span
                title={viewRefinement === 'approximate'
                  ? 'Non-uniform chunking (slide/smart): similarity scores are exact, but the refined alignment start/end boundaries are approximate.'
                  : 'Uniform chunking: alignment boundaries are exact.'}
                className={viewRefinement === 'approximate'
                  ? 'ml-1 text-[var(--color-warning,#b45309)]'
                  : 'ml-1 text-[var(--color-text-muted)]'}
              >
                · {viewRefinement} boundaries
              </span>
            )}
          </button>
          {showAlignmentsList && (
            <div className="border border-[var(--color-border-subtle)] border-t-0 rounded-b bg-[var(--color-bg)] max-h-[120px] overflow-y-auto">
              {alignments.map((aln, idx) => {
                const [r, g, b] = interpolateColor(aln.identity, colors);
                const identColor = `rgb(${r},${g},${b})`;
                return (
                  <div key={idx} className="flex items-center gap-2 px-2 py-0.5 text-[0.72em] font-[var(--font-mono)] border-b border-[var(--color-border-subtle)] last:border-b-0 hover:bg-[var(--color-bg-muted)]">
                    <span className="text-[var(--color-text-muted)]">A:{aln.chunk_start_a}–{aln.chunk_end_a}</span>
                    <span className="text-[var(--color-text-muted)]">B:{aln.chunk_start_b}–{aln.chunk_end_b}</span>
                    <span style={{ color: identColor }} className="font-semibold">{(aln.identity * 100).toFixed(1)}%</span>
                    <span className="text-[var(--color-text-muted)]">{aln.length_chunks}c</span>
                    {aln.refinement === 'approximate' && (
                      <span
                        title="Approximate boundaries: this alignment came from non-uniform (slide/smart) chunks, so its start/end chunk indices are fuzzy. The identity score itself is exact."
                        className="text-[var(--color-warning,#b45309)] text-[0.92em]"
                      >approx</span>
                    )}
                    <button
                      className="ml-auto px-1.5 py-0 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[var(--color-text-muted)]"
                      onClick={() => {
                        if (!signal || !paragraphs.length) return;
                        const offsets = signal.manifest?.segment_offsets;
                        const rowMin = aln.chunk_start_a, rowMax = aln.chunk_end_a;
                        const colMin = aln.chunk_start_b, colMax = aln.chunk_end_b;
                        let rowText = '', colText = '';
                        if (offsets) {
                          const fullText = paragraphs.map((p) => p.text).join('\n');
                          rowText = fullText.slice(offsets[rowMin]?.[0] ?? 0, Math.min((offsets[Math.min(rowMax, offsets.length - 1)]?.[1] ?? 0), (offsets[rowMin]?.[0] ?? 0) + 3000));
                          colText = fullText.slice(offsets[colMin]?.[0] ?? 0, Math.min((offsets[Math.min(colMax, offsets.length - 1)]?.[1] ?? 0), (offsets[colMin]?.[0] ?? 0) + 3000));
                        }
                        if (!rowText) rowText = paragraphs.slice(rowMin, Math.min(rowMax + 1, paragraphs.length)).map((p) => p.text).join('\n').slice(0, 3000);
                        if (!colText) colText = paragraphs.slice(colMin, Math.min(colMax + 1, paragraphs.length)).map((p) => p.text).join('\n').slice(0, 3000);
                        setFloatingWindows([
                          { id: `aln-row-${idx}`, title: `A [${rowMin}–${rowMax}] id=${(aln.identity * 100).toFixed(1)}%`, text: rowText, paraRange: [rowMin, rowMax], similarity: aln.identity },
                          { id: `aln-col-${idx}`, title: `B [${colMin}–${colMax}]`, text: colText, paraRange: [colMin, colMax], similarity: aln.identity },
                        ]);
                      }}
                    >
                      View
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {loading && <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">Loading self-similarity matrix...</div>}
      {error && <div className="flex-1 flex items-center justify-center text-[#b91c1c]">{error}</div>}

      {!loading && !error && signal && (
        <div className="flex-1 overflow-hidden flex">
          {/* Left: matrix area */}
          <div className="flex-1 flex flex-col min-h-0 min-w-0">
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
                  <div className="relative">
                    <canvas ref={matrixCanvasRef} className="absolute top-0 left-0" />
                    <canvas
                      ref={overlayCanvasRef}
                      onMouseMove={handleMouseMove}
                      onMouseDown={handleMouseDown}
                      onMouseUp={handleMouseUp}
                      onContextMenu={(e) => e.preventDefault()}
                      onMouseLeave={() => { setHoveredCell(null); if (panning.current) panning.current = false; }}
                      className="relative cursor-crosshair"
                      role="img"
                      aria-label={`Self-similarity heatmap, ${n}×${n} chunks (${chunkSize} words each). ${hoveredCell ? `Chunk [${hoveredCell.i}, ${hoveredCell.j}]: similarity ${hoverValue?.toFixed(3) ?? 'N/A'}` : 'Hover to inspect. Click two points to select.'}`}
                    />
                  </div>
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

          {/* Right: fixed text panels */}
          {floatingWindows.length > 0 && (
            <div className="w-[320px] shrink-0 ml-2 overflow-y-auto flex flex-col gap-0">
              {floatingWindows.map((win) => (
                <FixedTextPanel
                  key={win.id}
                  win={win}
                  onClose={() => setFloatingWindows((ws) => ws.filter((w) => w.id !== win.id))}
                  colors={colors}
                />
              ))}
            </div>
          )}
        </div>
      )}
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
