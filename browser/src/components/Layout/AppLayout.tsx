/**
 * Main application layout — M1.2 complete.
 * Three-panel design: TrackPanel | TextLinearView+Search | DetailPanel
 * Plus OverviewBar below.
 */

import { useEffect } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useViewStore } from '../../stores/viewStore';
import { setupKeyboardHandlers } from '../../utils/keyboard';
import TextLinearView from '../TextLinearView/TextLinearView';
import TextSearch from '../TextLinearView/TextSearch';
import DetailPanel from '../DetailPanel/DetailPanel';
import TrackPanel from '../TrackPanel/TrackPanel';
import OverviewBar from '../OverviewBar/OverviewBar';
import DotplotView from '../DotplotView/DotplotView';
import LoadingOverlay from '../common/LoadingOverlay';
import HelpOverlay from '../common/HelpOverlay';
import ProjectPicker from '../common/ProjectPicker';

export default function AppLayout(): JSX.Element {
  const { loadingState, error, metadata, paragraphs, tracks } = useProjectStore();
  const dotplotOpen = useViewStore((s) => s.dotplotOpen);
  const toggleDotplot = useViewStore((s) => s.toggleDotplot);

  useEffect(() => {
    const cleanup = setupKeyboardHandlers();
    return cleanup;
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const projectId = params.get('project');
    if (projectId) {
      useProjectStore.getState().loadProject('', projectId);
    }
  }, []);

  if (error) {
    return <div className="error-screen">Error: {error}</div>;
  }

  if (!metadata && loadingState !== 'loading') {
    return (
      <div className="welcome-screen" style={{ maxWidth: '600px', margin: '40px auto', fontFamily: "'Georgia', serif" }}>
        <h1>Palimpsest</h1>
        <p style={{ color: '#666' }}>Computational literary analysis platform</p>
        <ProjectPicker />
      </div>
    );
  }

  const trackCount = Object.keys(tracks).filter((k) => k !== 'segments').length;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        fontFamily: "'Georgia', serif",
      }}
    >
      <LoadingOverlay />
      <HelpOverlay />

      {/* Toolbar */}
      {metadata && (
        <div
          style={{
            padding: '8px 16px',
            borderBottom: '1px solid #ddd',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            backgroundColor: '#fafafa',
          }}
        >
          <strong>{metadata.title}</strong>
          {metadata.author && <span style={{ color: '#666' }}>by {metadata.author}</span>}
          <span style={{ color: '#999', fontSize: '0.85em' }}>
            {metadata.word_count.toLocaleString()} words &middot; {paragraphs.length} paragraphs
            &middot; {trackCount} tracks
          </span>
          <button
            onClick={toggleDotplot}
            title="Toggle self-similarity dotplot (d)"
            style={{
              marginLeft: 'auto',
              padding: '4px 10px',
              fontSize: '0.8em',
              border: '1px solid #ccc',
              borderRadius: '4px',
              backgroundColor: dotplotOpen ? '#3498db' : 'transparent',
              color: dotplotOpen ? '#fff' : '#555',
              cursor: 'pointer',
            }}
          >
            Dotplot
          </button>
        </div>
      )}

      {/* Search bar */}
      <TextSearch />

      {/* Main content area */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <TrackPanel />
        <TextLinearView />
        <DetailPanel />
      </div>

      {/* Overview Bar */}
      <OverviewBar />

      {/* DotplotView — collapsible bottom panel (d key toggles) */}
      <DotplotView />
    </div>
  );
}
