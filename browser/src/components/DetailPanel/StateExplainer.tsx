/**
 * StateExplainer — AI-generated explanation of a LitHMM state.
 * Shows statistical description, sample passages, and optional LLM narrative explanation.
 */

import { useCallback, useEffect, useState } from 'react';

type ExplainState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; explanation: string | null; stateDescription: string; samplePassages: string[]; model: string }
  | { status: 'unavailable'; stateDescription: string; samplePassages: string[] }
  | { status: 'error'; message: string };

interface Props {
  projectId: string;
  stateId: number;
  stateDescription?: string;
}

export default function StateExplainer({ projectId, stateId, stateDescription }: Props): JSX.Element {
  const [state, setState] = useState<ExplainState>({ status: 'idle' });

  useEffect(() => {
    setState({ status: 'idle' });
  }, [stateId, projectId]);

  const handleExplain = useCallback(async () => {
    setState({ status: 'loading' });
    try {
      const res = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: projectId, state_id: stateId }),
      });
      if (!res.ok) {
        setState({ status: 'error', message: `Server error: ${res.status}` });
        return;
      }
      const data = await res.json();
      if (!data.ollama_available) {
        setState({
          status: 'unavailable',
          stateDescription: data.state_description,
          samplePassages: data.sample_passages ?? [],
        });
        return;
      }
      setState({
        status: 'done',
        explanation: data.explanation,
        stateDescription: data.state_description,
        samplePassages: data.sample_passages ?? [],
        model: data.model,
      });
    } catch {
      setState({ status: 'error', message: 'Failed to connect to server' });
    }
  }, [projectId, stateId]);

  if (state.status === 'idle') {
    return (
      <div>
        {stateDescription && (
          <div style={{ fontSize: '0.85em', color: '#555', marginBottom: '8px', lineHeight: 1.4 }}>
            {stateDescription}
          </div>
        )}
        <button
          onClick={handleExplain}
          style={{
            padding: '6px 12px',
            backgroundColor: '#16a085',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.85em',
          }}
        >
          Explain this state
        </button>
      </div>
    );
  }

  if (state.status === 'loading') {
    return <div style={{ color: '#888', fontStyle: 'italic' }}>Analyzing state...</div>;
  }

  if (state.status === 'unavailable') {
    return (
      <div>
        <div style={{ fontSize: '0.85em', color: '#555', marginBottom: '8px', lineHeight: 1.4 }}>
          {state.stateDescription}
        </div>
        {state.samplePassages.length > 0 && (
          <div style={{ marginTop: '8px' }}>
            <div style={{ fontWeight: 'bold', fontSize: '0.8em', color: '#888', marginBottom: '4px' }}>
              Sample passages
            </div>
            {state.samplePassages.slice(0, 2).map((p, i) => (
              <div
                key={i}
                style={{
                  padding: '6px',
                  backgroundColor: '#f8f9fa',
                  borderLeft: '3px solid #16a085',
                  marginBottom: '4px',
                  fontSize: '0.8em',
                  fontStyle: 'italic',
                  maxHeight: '60px',
                  overflow: 'hidden',
                }}
              >
                {p.length > 150 ? `${p.slice(0, 150)}...` : p}
              </div>
            ))}
          </div>
        )}
        <div style={{ color: '#e67e22', fontSize: '0.85em', marginTop: '8px' }}>
          Start AI services for full explanation.
          <br />
          <span style={{ color: '#999' }}>Run: ollama serve</span>
        </div>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div>
        <div style={{ color: '#e74c3c', fontSize: '0.85em' }}>{state.message}</div>
        <button
          onClick={() => setState({ status: 'idle' })}
          style={{ background: 'none', border: 'none', color: '#16a085', cursor: 'pointer', fontSize: '0.8em' }}
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div>
      <div style={{ fontSize: '0.8em', color: '#888', marginBottom: '4px' }}>
        Statistical: {state.stateDescription}
      </div>
      {state.explanation && (
        <div
          style={{
            padding: '8px',
            backgroundColor: '#f0faf7',
            borderLeft: '3px solid #16a085',
            marginBottom: '8px',
            lineHeight: 1.5,
            fontSize: '0.9em',
          }}
        >
          {state.explanation}
        </div>
      )}
      {state.samplePassages.length > 0 && (
        <div style={{ marginTop: '8px' }}>
          <div style={{ fontWeight: 'bold', fontSize: '0.8em', color: '#888', marginBottom: '4px' }}>
            Sample passages
          </div>
          {state.samplePassages.slice(0, 2).map((p, i) => (
            <div
              key={i}
              style={{
                padding: '6px',
                backgroundColor: '#f8f9fa',
                borderLeft: '3px solid #16a085',
                marginBottom: '4px',
                fontSize: '0.8em',
                fontStyle: 'italic',
                maxHeight: '60px',
                overflow: 'hidden',
              }}
            >
              {p.length > 150 ? `${p.slice(0, 150)}...` : p}
            </div>
          ))}
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
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
