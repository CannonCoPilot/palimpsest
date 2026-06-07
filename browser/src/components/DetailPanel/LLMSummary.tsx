/**
 * LLMSummary — AI-generated summary of selected text passage.
 * Gracefully handles Ollama unavailability with friendly messaging.
 */

import { useCallback, useEffect, useState } from 'react';

type SummaryState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; summary: string; model: string }
  | { status: 'unavailable' }
  | { status: 'error'; message: string };

interface Props {
  passage: string;
  passageId: string;
}

export default function LLMSummary({ passage, passageId }: Props): JSX.Element {
  const [state, setState] = useState<SummaryState>({ status: 'idle' });

  useEffect(() => {
    setState({ status: 'idle' });
  }, [passageId]);

  const handleSummarize = useCallback(async () => {
    setState({ status: 'loading' });
    try {
      const res = await fetch('/api/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ passage }),
      });
      if (!res.ok) {
        setState({ status: 'error', message: `Server error: ${res.status}` });
        return;
      }
      const data = await res.json();
      if (!data.ollama_available) {
        setState({ status: 'unavailable' });
        return;
      }
      if (!data.summary) {
        setState({ status: 'error', message: 'No summary generated' });
        return;
      }
      setState({ status: 'done', summary: data.summary, model: data.model });
    } catch (err) {
      setState({ status: 'error', message: 'Failed to connect to server' });
    }
  }, [passage]);

  if (state.status === 'idle') {
    return (
      <button
        onClick={handleSummarize}
        style={{
          padding: '6px 12px',
          backgroundColor: '#3498db',
          color: '#fff',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '0.85em',
        }}
      >
        Summarize
      </button>
    );
  }

  if (state.status === 'loading') {
    return <div style={{ color: '#888', fontStyle: 'italic' }}>Generating summary...</div>;
  }

  if (state.status === 'unavailable') {
    return (
      <div style={{ color: '#e67e22', fontSize: '0.85em' }}>
        Start AI services for summaries.
        <br />
        <span style={{ color: '#999' }}>Run: ollama serve</span>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div>
        <div style={{ color: '#e74c3c', fontSize: '0.85em' }}>{state.message}</div>
        <button
          onClick={() => setState({ status: 'idle' })}
          style={{ background: 'none', border: 'none', color: '#3498db', cursor: 'pointer', fontSize: '0.8em' }}
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          padding: '8px',
          backgroundColor: '#f8f9fa',
          borderLeft: '3px solid #2ecc71',
          marginBottom: '8px',
          lineHeight: 1.5,
          fontSize: '0.9em',
        }}
      >
        {state.summary}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: '#999', fontSize: '0.75em' }}>via {state.model}</span>
        <button
          onClick={() => setState({ status: 'idle' })}
          style={{ background: 'none', border: 'none', color: '#999', cursor: 'pointer', fontSize: '0.8em' }}
        >
          Clear
        </button>
      </div>
    </div>
  );
}
