import { useEffect } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useViewStore } from '../../stores/viewStore';
import { setupKeyboardHandlers } from '../../utils/keyboard';
import TextLinearView from '../TextLinearView/TextLinearView';
import TextSearch from '../TextLinearView/TextSearch';
import DetailPanel from '../DetailPanel/DetailPanel';
import TrackPanel from '../TrackPanel/TrackPanel';
import OverviewBar from '../OverviewBar/OverviewBar';
import BrowserView from '../BrowserView/BrowserView';
import DotplotView from '../DotplotView/DotplotView';
import CharactersPanel from '../CharactersPanel/CharactersPanel';
import AnalysisPanel from '../AnalysisPanel/AnalysisPanel';
import CompareView from '../CompareView/CompareView';
import LoadingOverlay from '../common/LoadingOverlay';
import HelpOverlay from '../common/HelpOverlay';
import ProjectPicker from '../common/ProjectPicker';
import SectionNav from '../common/SectionNav';
import ErrorBoundary from '../common/ErrorBoundary';
import TabBar from './TabBar';
import NavigationToolbar from './NavigationToolbar';
import CoordinateRuler from './CoordinateRuler';

export default function AppLayout() {
  const { loadingState, error, metadata, paragraphs, tracks } = useProjectStore();
  const activeTab = useViewStore((s) => s.activeTab);

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
  const showSidePanels = activeTab === 'reading';

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
          <div className="ml-auto">
            <NavigationToolbar />
          </div>
        </div>
      )}

      <TabBar />

      {activeTab === 'reading' && <CoordinateRuler />}
      {activeTab === 'reading' && <TextSearch />}

      <div className="flex-1 flex overflow-hidden">
        {showSidePanels && (
          <nav aria-label="Track and section navigation" className="flex flex-col border-r border-[var(--color-border)]">
            <SectionNav />
            <TrackPanel />
          </nav>
        )}

        <main
          role="tabpanel"
          id={`panel-${activeTab}`}
          aria-label={`${activeTab} view`}
          className="flex-1 flex flex-col overflow-hidden"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              useViewStore.getState().selectAnnotation(null);
            }
          }}
        >
          <ErrorBoundary fallbackLabel={activeTab}>
            {activeTab === 'reading' && <TextLinearView />}
            {activeTab === 'browser' && <BrowserView />}
            {activeTab === 'texthic' && <DotplotView />}
            {activeTab === 'characters' && <CharactersPanel />}
            {activeTab === 'analysis' && <AnalysisPanel />}
            {activeTab === 'compare' && <CompareView />}
          </ErrorBoundary>
        </main>

        {showSidePanels && (
          <aside role="complementary" aria-label="Annotation details" className="contents">
            <ErrorBoundary fallbackLabel="Detail Panel">
              <DetailPanel />
            </ErrorBoundary>
          </aside>
        )}
      </div>

      {activeTab !== 'texthic' && activeTab !== 'compare' && <OverviewBar />}
    </div>
  );
}
