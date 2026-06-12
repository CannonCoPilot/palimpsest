import { useEffect, useState, useMemo, useCallback } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useViewStore } from '../../stores/viewStore';
import { useSearchStore } from '../../stores/searchStore';
import CharacterDetail from './CharacterDetail';
import CooccurrenceHeatmap from './CooccurrenceHeatmap';

interface CharacterRecord {
  canonicalName: string;
  aliases: string[];
  type: string;
  mentionCount: number;
  firstOccurrence: number;
  lastOccurrence: number;
  firstParagraph: number;
  lastParagraph: number;
  paragraphIndices: number[];
  density: number[];
}

type SortKey = 'name' | 'mentions' | 'type' | 'first';

function Sparkline({ density, width = 120, height = 16 }: { density: number[]; width?: number; height?: number }) {
  if (density.length === 0) return null;
  const max = Math.max(1, ...density);
  const barW = width / density.length;

  return (
    <svg width={width} height={height} className="inline-block align-middle">
      {density.map((v, i) => {
        if (v === 0) return null;
        const h = (v / max) * height;
        return <rect key={i} x={i * barW} y={height - h} width={Math.max(0.5, barW - 0.2)} height={h} fill="var(--color-primary)" fillOpacity={0.6} />;
      })}
    </svg>
  );
}

export default function CharactersPanel() {
  const projectId = useProjectStore((s) => s.metadata?.id);
  const paragraphs = useProjectStore((s) => s.paragraphs);
  const referenceText = useProjectStore((s) => s.referenceText);
  const [characters, setCharacters] = useState<CharacterRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('mentions');
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedChar, setSelectedChar] = useState<CharacterRecord | null>(null);
  const [showCooccurrence, setShowCooccurrence] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    fetch(`/api/projects/${projectId}/characters`)
      .then((r) => r.json())
      .then((data) => { setCharacters(data); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [projectId]);

  const handleSort = useCallback((key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(key === 'name');
    }
  }, [sortKey, sortAsc]);

  const filtered = useMemo(() => {
    let list = characters;
    if (filter) {
      const q = filter.toLowerCase();
      list = list.filter((c) => c.canonicalName.toLowerCase().includes(q) || c.aliases.some((a) => a.toLowerCase().includes(q)));
    }
    list = [...list].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'name': cmp = a.canonicalName.localeCompare(b.canonicalName); break;
        case 'mentions': cmp = a.mentionCount - b.mentionCount; break;
        case 'type': cmp = a.type.localeCompare(b.type); break;
        case 'first': cmp = a.firstOccurrence - b.firstOccurrence; break;
      }
      return sortAsc ? cmp : -cmp;
    });
    return list;
  }, [characters, filter, sortKey, sortAsc]);

  const handleChainFollow = useCallback((char: CharacterRecord) => {
    useViewStore.getState().setCharacterFilter(char.canonicalName);
    useViewStore.getState().setActiveTab('reading');
    const search = useSearchStore.getState();
    search.open();
    search.setQuery(char.canonicalName, referenceText, paragraphs);
  }, [referenceText, paragraphs]);

  if (loading) {
    return <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)]">Loading character index...</div>;
  }
  if (error) {
    return <div className="flex-1 flex items-center justify-center text-[#b91c1c]">Error: {error}</div>;
  }

  const sortIndicator = (key: SortKey) => sortKey === key ? (sortAsc ? ' ↑' : ' ↓') : '';
  const typeBadgeColor: Record<string, string> = { person: '#3b82f6', organization: '#f59e0b', place: '#10b981', group: '#8b5cf6', other: '#6b7280' };

  return (
    <div className="flex-1 flex overflow-hidden font-[var(--font-sans)] text-[0.85em]">
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--color-border)]">
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search characters..."
            className="flex-1 px-2 py-1 border border-[var(--color-border)] rounded text-[0.9em]"
          />
          <span className="text-[var(--color-text-muted)] text-[0.85em]">{filtered.length} of {characters.length}</span>
          <button
            onClick={() => setShowCooccurrence(!showCooccurrence)}
            className="px-2 py-1 rounded border border-[var(--color-border)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.85em]"
          >
            {showCooccurrence ? 'List' : 'Co-occurrence'}
          </button>
        </div>

        {showCooccurrence ? (
          <CooccurrenceHeatmap projectId={projectId ?? ''} />
        ) : (
          <div className="flex-1 overflow-auto">
            <table className="w-full border-collapse">
              <thead className="sticky top-0 bg-[var(--color-bg-subtle)] z-10">
                <tr className="text-left text-[0.8em] text-[var(--color-text-muted)]">
                  <th className="px-3 py-1.5 cursor-pointer hover:text-[var(--color-text)]" onClick={() => handleSort('name')}>Name{sortIndicator('name')}</th>
                  <th className="px-3 py-1.5 cursor-pointer hover:text-[var(--color-text)] w-[70px] text-right" onClick={() => handleSort('mentions')}>Mentions{sortIndicator('mentions')}</th>
                  <th className="px-3 py-1.5 cursor-pointer hover:text-[var(--color-text)] w-[80px]" onClick={() => handleSort('type')}>Type{sortIndicator('type')}</th>
                  <th className="px-3 py-1.5 w-[130px]">Distribution</th>
                  <th className="px-3 py-1.5 w-[60px]"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((char) => (
                  <tr
                    key={char.canonicalName}
                    tabIndex={0}
                    className={`border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-muted)] cursor-pointer focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[var(--color-primary)] ${selectedChar?.canonicalName === char.canonicalName ? 'bg-[var(--color-bg-muted)]' : ''}`}
                    onClick={() => setSelectedChar(selectedChar?.canonicalName === char.canonicalName ? null : char)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedChar(selectedChar?.canonicalName === char.canonicalName ? null : char); } }}
                  >
                    <td className="px-3 py-1.5 font-medium">{char.canonicalName}</td>
                    <td className="px-3 py-1.5 text-right font-[var(--font-mono)] text-[0.9em]">{char.mentionCount}</td>
                    <td className="px-3 py-1.5">
                      <span className="px-1.5 py-0.5 rounded-full text-[0.75em] text-white" style={{ backgroundColor: typeBadgeColor[char.type] ?? '#6b7280' }}>
                        {char.type}
                      </span>
                    </td>
                    <td className="px-3 py-1.5"><Sparkline density={char.density} /></td>
                    <td className="px-3 py-1.5">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleChainFollow(char); }}
                        className="text-[var(--color-primary)] hover:underline text-[0.85em] cursor-pointer"
                        title="Show all mentions in Reading view"
                      >
                        Find
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedChar && !showCooccurrence && (
        <CharacterDetail character={selectedChar} onClose={() => setSelectedChar(null)} onChainFollow={handleChainFollow} />
      )}
    </div>
  );
}
