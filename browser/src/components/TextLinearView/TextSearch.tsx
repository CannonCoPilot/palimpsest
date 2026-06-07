/**
 * TextSearch — type-ahead search bar with match navigation.
 * Opens via Ctrl+F or /; closes on Escape.
 */

import { useCallback, useEffect, useRef } from 'react';
import { useSearchStore } from '../../stores/searchStore';
import { useProjectStore } from '../../stores/projectStore';

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
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px 12px',
        backgroundColor: '#f8f9fa',
        borderBottom: '1px solid #ddd',
        fontSize: '0.85em',
      }}
    >
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Search..."
        style={{
          flex: 1,
          padding: '4px 8px',
          border: '1px solid #ccc',
          borderRadius: '3px',
          fontSize: '1em',
        }}
      />

      <button
        onClick={handleToggleCase}
        title="Toggle case sensitivity"
        style={{
          padding: '2px 6px',
          border: '1px solid #ccc',
          borderRadius: '3px',
          backgroundColor: caseSensitive ? '#3498db' : 'transparent',
          color: caseSensitive ? '#fff' : '#666',
          cursor: 'pointer',
          fontWeight: 'bold',
        }}
      >
        Aa
      </button>

      <span style={{ color: '#888', minWidth: '70px', textAlign: 'center' }} aria-live="polite">
        {matchText}
      </span>

      <button
        onClick={() => useSearchStore.getState().prevMatch()}
        disabled={matches.length === 0}
        style={{ padding: '2px 6px', cursor: matches.length ? 'pointer' : 'default' }}
        title="Previous match (Shift+Enter)"
      >
        ↑
      </button>
      <button
        onClick={() => useSearchStore.getState().nextMatch()}
        disabled={matches.length === 0}
        style={{ padding: '2px 6px', cursor: matches.length ? 'pointer' : 'default' }}
        title="Next match (Enter)"
      >
        ↓
      </button>

      <button
        onClick={() => useSearchStore.getState().close()}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#999', fontSize: '1.2em' }}
        title="Close search (Escape)"
      >
        ✕
      </button>
    </div>
  );
}
