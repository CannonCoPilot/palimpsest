import { useRef, useState, useEffect, useCallback } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useViewStore } from '../../stores/viewStore';

export default function CoordinateRuler() {
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const referenceText = useProjectStore((s) => s.referenceText);
  const visibleRange = useViewStore((s) => s.visibleParagraphRange);
  const requestScroll = useViewStore((s) => s.requestScrollToParagraph);
  const setSelected = useViewStore((s) => s.setSelectedParagraphIndex);

  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  const totalParas = paragraphs.length;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) setWidth(w);
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const handleClick = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (totalParas === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const frac = (e.clientX - rect.left) / rect.width;
    const paraIdx = Math.min(Math.floor(frac * totalParas), totalParas - 1);
    setSelected(paraIdx);
    requestScroll(paraIdx);
  }, [totalParas, setSelected, requestScroll]);

  if (totalParas === 0) return null;

  const vpStart = visibleRange ? visibleRange[0] : 0;
  const vpEnd = visibleRange ? visibleRange[1] : totalParas - 1;
  const vpFracStart = vpStart / totalParas;
  const vpFracEnd = (vpEnd + 1) / totalParas;

  const tickInterval = totalParas <= 50 ? 5 : totalParas <= 200 ? 25 : totalParas <= 500 ? 50 : 100;

  const ticks: { x: number; label: string }[] = [];
  for (let i = 0; i <= totalParas; i += tickInterval) {
    ticks.push({ x: (i / totalParas) * width, label: `¶${i}` });
  }

  return (
    <div ref={containerRef} className="w-full border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)] px-0">
      <svg width={width} height={20} className="cursor-pointer" onClick={handleClick}>
        <rect width={width} height={20} fill="transparent" />
        <rect
          x={vpFracStart * width}
          y={0}
          width={Math.max(2, (vpFracEnd - vpFracStart) * width)}
          height={20}
          fill="var(--color-primary)"
          fillOpacity={0.1}
          stroke="var(--color-primary)"
          strokeWidth={1}
          strokeOpacity={0.3}
          rx={2}
        />
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={t.x} y1={14} x2={t.x} y2={20} stroke="var(--color-text-muted)" strokeWidth={1} />
            <text x={t.x + 2} y={12} fontSize="9" fill="var(--color-text-muted)" fontFamily="var(--font-sans)">
              {t.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
