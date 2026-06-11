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
import SectionNav from '../common/SectionNav';
import ErrorBoundary from '../common/ErrorBoundary';
import { Tooltip } from '../common/Tooltip';

export default function AppLayout() {
  const { loadingState, error, metadata, paragraphs, tracks } = useProjectStore();
  const textHicOpen = useViewStore((s) => s.textHicOpen);
  const toggleTextHic = useViewStore((s) => s.toggleTextHic);
  const zoomLevel = useViewStore((s) => s.zoomLevel);
  const zoomIn = useViewStore((s) => s.zoomIn);
  const zoomOut = useViewStore((s) => s.zoomOut);

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
    return <div className="p-8 text-[var(--color-danger)] text-center">Error: {error}</div>;
  }

  if (!metadata && loadingState !== 'loading') {
    return (
      <div className="max-w-[600px] mx-auto mt-10 font-[var(--font-serif)]">
        <h1>Palimpsest</h1>
        <p className="text-[var(--color-text-secondary)]">Computational literary analysis platform</p>
        <ProjectPicker />
      </div>
    );
  }

  const trackCount = Object.keys(tracks).filter((k) => k !== 'segments').length;

  return (
    <div className="flex flex-col h-screen font-[var(--font-serif)]">
      <LoadingOverlay />
      <HelpOverlay />

      {metadata && (
        <div className="flex items-center gap-4 px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-subtle)]">
          <strong>{metadata.title}</strong>
          {metadata.author && <span className="text-[var(--color-text-secondary)]">by {metadata.author}</span>}
          <span className="text-[var(--color-text-muted)] text-[0.85em]">
            {metadata.word_count.toLocaleString()} words &middot; {paragraphs.length} paragraphs
            &middot; {trackCount} tracks
          </span>
          <div className="ml-auto flex items-center gap-2">
            <div className="flex items-center gap-1 border border-[#ccc] rounded-[var(--radius-md)] p-0.5">
              <Tooltip content="Zoom out (Ctrl+-)" side="bottom">
                <button
                  onClick={zoomOut}
                  disabled={zoomLevel === 'work'}
                  className="px-2 py-0.5 border-none bg-transparent text-[0.9em] disabled:text-[#ccc] disabled:cursor-default text-[#555] cursor-pointer"
                >
                  -
                </button>
              </Tooltip>
              <span className="text-[0.75em] text-[var(--color-text-secondary)] min-w-[65px] text-center">
                {zoomLevel}
              </span>
              <Tooltip content="Zoom in (Ctrl+=)" side="bottom">
                <button
                  onClick={zoomIn}
                  disabled={zoomLevel === 'sentence'}
                  className="px-2 py-0.5 border-none bg-transparent text-[0.9em] disabled:text-[#ccc] disabled:cursor-default text-[#555] cursor-pointer"
                >
                  +
                </button>
              </Tooltip>
            </div>
            <Tooltip content="Toggle self-similarity TextHiC (d)" side="bottom">
              <button
                onClick={toggleTextHic}
                className={`px-2.5 py-1 text-[0.8em] border rounded-[var(--radius-md)] cursor-pointer ${
                  textHicOpen
                    ? 'bg-[var(--color-primary)] text-[var(--color-text-inverted)] border-[var(--color-primary)]'
                    : 'bg-transparent text-[#555] border-[#ccc]'
                }`}
              >
                TextHiC
              </button>
            </Tooltip>
          </div>
        </div>
      )}

      <TextSearch />

      <div className="flex-1 flex overflow-hidden">
        <nav aria-label="Track and section navigation" className="flex flex-col border-r border-[var(--color-border)]">
          <SectionNav />
          <TrackPanel />
        </nav>
        <main role="main" aria-label="Reading area" className="flex-1 flex flex-col overflow-hidden">
          <ErrorBoundary fallbackLabel="Reading View">
            <TextLinearView />
          </ErrorBoundary>
        </main>
        <aside role="complementary" aria-label="Annotation details" className="contents">
          <ErrorBoundary fallbackLabel="Detail Panel">
            <DetailPanel />
          </ErrorBoundary>
        </aside>
      </div>

      <OverviewBar />

      <ErrorBoundary fallbackLabel="TextHiC Dotplot">
        <DotplotView />
      </ErrorBoundary>
    </div>
  );
}
