import { useCallback, useEffect, useRef } from 'react';
import { useSearchStore } from '../../stores/searchStore';
import { useProjectStore } from '../../stores/projectStore';
import { Tooltip } from '../common/Tooltip';

export default function TextSearch(): JSX.Element | null {
  const isOpen = useSearchStore((s) => s.isOpen);
  const query = useSearchStore((s) => s.query);
  const matches = useSearchStore((s) => s.matches);
  const currentMatchIndex = useSearchStore((s) => s.currentMatchIndex);
  const caseSensitive = useSearchStore((s) => s.caseSensitive);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const { referenceText, paragraphs } = useProjectStore.getState();
      useSearchStore.getState().setQuery(e.target.value, referenceText, paragraphs);
    },
    [],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && e.shiftKey) {
        e.preventDefault();
        useSearchStore.getState().prevMatch();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        useSearchStore.getState().nextMatch();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        useSearchStore.getState().close();
      }
    },
    [],
  );

  const handleToggleCase = useCallback(() => {
    const { referenceText, paragraphs } = useProjectStore.getState();
    useSearchStore.getState().toggleCaseSensitive(referenceText, paragraphs);
  }, []);

  if (!isOpen) return null;

  const matchText =
    matches.length > 0
      ? `${currentMatchIndex + 1} of ${matches.length}`
      : query.length >= 2
        ? 'No matches'
        : '';

  return (
    <div className="flex items-center gap-2 px-3 py-[6px] bg-[var(--color-bg-overlay)] border-b border-[var(--color-border)] text-[0.85em]">
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Search..."
        className="flex-1 px-2 py-[4px] border border-[#ccc] rounded-[3px] text-[1em]"
      />

      <Tooltip content="Toggle case sensitivity" side="bottom">
        <button
          onClick={handleToggleCase}
          className="px-[6px] py-[2px] border border-[#ccc] rounded-[3px] font-bold cursor-pointer"
          style={{
            backgroundColor: caseSensitive ? '#3498db' : 'transparent',
            color: caseSensitive ? '#fff' : '#666',
          }}
        >
          Aa
        </button>
      </Tooltip>

      <span className="text-[#888] min-w-[70px] text-center" aria-live="polite">
        {matchText}
      </span>

      <Tooltip content="Previous match (Shift+Enter)" side="bottom">
        <button
          onClick={() => useSearchStore.getState().prevMatch()}
          disabled={matches.length === 0}
          className="px-[6px] py-[2px]"
          style={{ cursor: matches.length ? 'pointer' : 'default' }}
        >
          ↑
        </button>
      </Tooltip>
      <Tooltip content="Next match (Enter)" side="bottom">
        <button
          onClick={() => useSearchStore.getState().nextMatch()}
          disabled={matches.length === 0}
          className="px-[6px] py-[2px]"
          style={{ cursor: matches.length ? 'pointer' : 'default' }}
        >
          ↓
        </button>
      </Tooltip>

      <Tooltip content="Close search (Escape)" side="bottom">
        <button
          onClick={() => useSearchStore.getState().close()}
          className="bg-none border-none cursor-pointer text-[var(--color-text-muted)] text-[1.2em]"
        >
          ✕
        </button>
      </Tooltip>
    </div>
  );
}
