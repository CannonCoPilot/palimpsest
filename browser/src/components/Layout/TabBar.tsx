import { useViewStore, type TabId } from '../../stores/viewStore';
import { Tooltip } from '../common/Tooltip';

const TABS: { id: TabId; label: string; shortcut: string; tip: string }[] = [
  { id: 'reading', label: 'Reading', shortcut: 'Alt+1', tip: 'Linear text view with annotation overlays (Alt+1)' },
  { id: 'browser', label: 'Browser', shortcut: 'Alt+2', tip: 'UCSC-style genome browser with tracks (Alt+2)' },
  { id: 'texthic', label: 'TextHiC', shortcut: 'Alt+3', tip: 'Self-similarity heatmap (Alt+3)' },
  { id: 'characters', label: 'Characters', shortcut: 'Alt+4', tip: 'Entity index and co-occurrence (Alt+4)' },
  { id: 'analysis', label: 'Analysis', shortcut: 'Alt+5', tip: 'Track computation and parameters (Alt+5)' },
];

export default function TabBar() {
  const activeTab = useViewStore((s) => s.activeTab);
  const setActiveTab = useViewStore((s) => s.setActiveTab);

  return (
    <div className="flex border-b border-[var(--color-border)] bg-[var(--color-bg)]" role="tablist" aria-label="Main views">
      {TABS.map((tab) => (
        <Tooltip key={tab.id} content={tab.tip} side="bottom">
          <button
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-sans border-b-2 transition-colors duration-[var(--duration-fast)] cursor-pointer ${
              activeTab === tab.id
                ? 'border-[var(--color-primary)] text-[var(--color-primary)] font-medium'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:border-[var(--color-border)]'
            }`}
          >
            {tab.label}
            <kbd className="ml-1.5 text-[0.65em] text-[var(--color-text-muted)] opacity-60">{tab.shortcut}</kbd>
          </button>
        </Tooltip>
      ))}
    </div>
  );
}
