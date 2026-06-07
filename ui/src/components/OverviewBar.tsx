import { useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useProjectStore } from '../stores/projectStore';
import { useTrackStore } from '../stores/trackStore';

interface DensityData {
  bins: number[];
  track_name: string;
  max_value: number;
}

const TRACK_COLORS: Record<string, string> = {
  entities: '#3498db',
  sentiment: '#2ecc71',
  lexical: '#9b59b6',
  dialogue: '#e67e22',
  topics: '#e74c3c',
  segments: '#95a5a6',
};

export default function OverviewBar() {
  const info = useProjectStore((s) => s.info);
  const tracks = useTrackStore((s) => s.tracks);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [densityData, setDensityData] = useState<DensityData[]>([]);

  useEffect(() => {
    if (!info) return;
    invoke<DensityData[]>('get_density', { projectId: info.id, numBins: 1200 })
      .then(setDensityData)
      .catch(() => {});
  }, [info, tracks]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || densityData.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const trackHeight = 14;
    const gap = 2;
    const totalHeight = densityData.length * (trackHeight + gap);
    canvas.height = totalHeight;

    ctx.clearRect(0, 0, width, totalHeight);

    densityData.forEach((track, trackIdx) => {
      if (track.track_name === 'segments') return;
      const state = tracks[track.track_name];
      const alpha = state?.visible !== false ? 1.0 : 0.2;
      const color = TRACK_COLORS[track.track_name] ?? '#888';
      const y = trackIdx * (trackHeight + gap);
      const maxVal = track.max_value || 1;

      ctx.fillStyle = '#f8f8f8';
      ctx.fillRect(0, y, width, trackHeight);

      ctx.globalAlpha = alpha;
      ctx.fillStyle = color;

      const binWidth = width / track.bins.length;
      for (let i = 0; i < track.bins.length; i++) {
        if (track.bins[i] === 0) continue;
        const h = (track.bins[i] / maxVal) * trackHeight;
        ctx.fillRect(i * binWidth, y + trackHeight - h, binWidth, h);
      }
      ctx.globalAlpha = 1.0;

      ctx.fillStyle = '#666';
      ctx.font = '9px -apple-system, sans-serif';
      ctx.fillText(track.track_name, 4, y + 10);
    });
  }, [densityData, tracks]);

  return (
    <div style={{
      borderTop: '1px solid #e0e0e0',
      backgroundColor: '#fafafa',
      padding: '4px 8px',
      flexShrink: 0,
    }}>
      <canvas
        ref={canvasRef}
        width={1200}
        style={{ width: '100%', height: 'auto', display: 'block', cursor: 'pointer' }}
      />
    </div>
  );
}
