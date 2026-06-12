import { useEffect, useState } from 'react';

interface CooccurrenceData {
  names: string[];
  matrix: number[][];
}

function interpolateHeat(value: number, max: number): string {
  const t = max > 0 ? value / max : 0;
  const r = Math.round(255 - t * 200);
  const g = Math.round(255 - t * 120);
  const b = Math.round(255 - t * 50);
  return `rgb(${r},${g},${b})`;
}

export default function CooccurrenceHeatmap({ projectId }: { projectId: string }) {
  const [data, setData] = useState<CooccurrenceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [hoveredCell, setHoveredCell] = useState<{ i: number; j: number } | null>(null);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    fetch(`/api/projects/${projectId}/characters/cooccurrence?top_n=15`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  if (loading) return <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">Computing co-occurrence...</div>;
  if (!data) return null;

  const { names, matrix } = data;
  const n = names.length;
  const maxVal = Math.max(1, ...matrix.flat().filter((v, i) => Math.floor(i / n) !== i % n));
  const cellSize = Math.min(40, Math.floor(600 / n));
  const labelWidth = 120;

  const hoverInfo = hoveredCell
    ? `${names[hoveredCell.i]} × ${names[hoveredCell.j]}: ${matrix[hoveredCell.i][hoveredCell.j]} shared paragraphs`
    : '';

  return (
    <div className="flex-1 overflow-auto p-3" role="img" aria-label={`Character co-occurrence matrix showing ${n} characters. ${hoverInfo || 'Hover cells to see shared paragraph counts between character pairs.'}`}>
      <div className="text-[0.8em] text-[var(--color-text-muted)] mb-2 h-4" aria-live="polite">{hoverInfo || 'Hover to see shared paragraph count'}</div>
      <div className="inline-block">
        {/* Column headers */}
        <div className="flex" style={{ marginLeft: labelWidth }}>
          {names.map((name, j) => (
            <div
              key={j}
              className="overflow-hidden text-[0.65em] text-[var(--color-text-muted)]"
              style={{ width: cellSize, height: labelWidth * 0.6, writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
            >
              {name.slice(0, 15)}
            </div>
          ))}
        </div>
        {/* Matrix rows */}
        {names.map((rowName, i) => (
          <div key={i} className="flex items-center">
            <div className="text-[0.7em] text-right pr-2 truncate" style={{ width: labelWidth }}>{rowName}</div>
            {matrix[i].map((val, j) => (
              <div
                key={j}
                className="border border-[var(--color-border-subtle)] flex items-center justify-center text-[0.6em] cursor-pointer"
                style={{
                  width: cellSize,
                  height: cellSize,
                  backgroundColor: i === j ? 'var(--color-bg-muted)' : interpolateHeat(val, maxVal),
                  color: val > maxVal * 0.5 ? 'white' : 'var(--color-text-muted)',
                }}
                onMouseEnter={() => setHoveredCell({ i, j })}
                onMouseLeave={() => setHoveredCell(null)}
              >
                {val > 0 && i !== j ? val : i === j ? '·' : ''}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
