import { useEffect } from 'react';
import { useProjectStore } from '../stores/projectStore';
import { useTrackStore } from '../stores/trackStore';
import TrackPanel from './TrackPanel';
import VirtualTextView from './VirtualTextView';
import OverviewBar from './OverviewBar';
import DetailPanel from './DetailPanel';

export default function MainLayout() {
  const info = useProjectStore((s) => s.info);
  const tracks = useTrackStore((s) => s.tracks);
  const trackCount = Object.keys(tracks).length;

  useEffect(() => {
    function handleKeydown(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

      if (e.key >= '1' && e.key <= '9') {
        const names = Object.keys(tracks).sort();
        const idx = parseInt(e.key) - 1;
        if (idx < names.length) {
          useTrackStore.getState().toggleTrack(names[idx]);
        }
      } else if (e.key === '0') {
        const allVisible = Object.values(tracks).every((t) => t.visible);
        const names = Object.keys(tracks);
        for (const name of names) {
          if (allVisible) {
            useTrackStore.getState().toggleTrack(name);
          } else if (!tracks[name].visible) {
            useTrackStore.getState().toggleTrack(name);
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeydown);
    return () => document.removeEventListener('keydown', handleKeydown);
  }, [tracks]);

  if (!info) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Toolbar */}
      <header style={{
        padding: '8px 16px',
        borderBottom: '1px solid #e0e0e0',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        backgroundColor: '#fafafa',
        flexShrink: 0,
      }}>
        <strong style={{ fontFamily: "'Crimson Pro', Georgia, serif" }}>{info.title}</strong>
        {info.author && <span style={{ color: '#666' }}>by {info.author}</span>}
        <span style={{ color: '#999', fontSize: '0.85em' }}>
          {info.word_count.toLocaleString()} words · {info.paragraph_count} paragraphs · {trackCount} tracks · {info.total_annotations.toLocaleString()} annotations
        </span>
      </header>

      {/* Main content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <TrackPanel />
        <VirtualTextView />
        <DetailPanel />
      </div>

      {/* Overview */}
      <OverviewBar />
    </div>
  );
}
