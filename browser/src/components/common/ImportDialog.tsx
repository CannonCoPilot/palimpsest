/**
 * ImportDialog — upload an EPUB/TXT/PDF file, ingest and compute all tracks.
 */

import { useCallback, useRef, useState } from 'react';
import { useProjectStore } from '../../stores/projectStore';

type ImportState =
  | { status: 'idle' }
  | { status: 'uploading'; filename: string }
  | { status: 'processing'; filename: string; step: string }
  | { status: 'done'; projectId: string; title: string; wordCount: number; trackCount: number }
  | { status: 'error'; message: string };

const ACCEPTED_FORMATS = '.epub,.txt,.pdf,.html,.htm,.md,.markdown';

export default function ImportDialog(): JSX.Element {
  const [state, setState] = useState<ImportState>({ status: 'idle' });
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback(async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    const filename = file.name;
    setState({ status: 'uploading', filename });

    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (author) formData.append('author', author);

    try {
      setState({ status: 'processing', filename, step: 'Ingesting text and computing tracks...' });

      const res = await fetch('/api/import', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        setState({ status: 'error', message: err.detail || 'Import failed' });
        return;
      }

      const data = await res.json();
      setState({
        status: 'done',
        projectId: data.project_id,
        title: data.title,
        wordCount: data.word_count,
        trackCount: data.track_count,
      });
    } catch (err) {
      setState({ status: 'error', message: 'Failed to connect to server' });
    }
  }, [title, author]);

  const handleLoadProject = useCallback((projectId: string) => {
    const url = new URL(window.location.href);
    url.searchParams.set('project', projectId);
    window.history.pushState({}, '', url.toString());
    useProjectStore.getState().loadProject('', projectId);
  }, []);

  if (state.status === 'done') {
    return (
      <div style={{ padding: '16px', backgroundColor: '#f0faf0', borderRadius: '8px', border: '1px solid #27ae60' }}>
        <div style={{ fontWeight: 'bold', color: '#27ae60', marginBottom: '8px' }}>Import Complete</div>
        <div><strong>{state.title}</strong></div>
        <div style={{ color: '#666', fontSize: '0.9em' }}>
          {state.wordCount.toLocaleString()} words, {state.trackCount} tracks computed
        </div>
        <button
          onClick={() => handleLoadProject(state.projectId)}
          style={{
            marginTop: '12px',
            padding: '8px 20px',
            backgroundColor: '#27ae60',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1em',
          }}
        >
          Open Project
        </button>
        <button
          onClick={() => {
            setState({ status: 'idle' });
            setTitle('');
            setAuthor('');
          }}
          style={{
            marginLeft: '8px',
            padding: '8px 16px',
            backgroundColor: 'transparent',
            color: '#666',
            border: '1px solid #ccc',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Import Another
        </button>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div style={{ padding: '16px', backgroundColor: '#fdf0f0', borderRadius: '8px', border: '1px solid #e74c3c' }}>
        <div style={{ color: '#e74c3c', fontWeight: 'bold', marginBottom: '4px' }}>Import Failed</div>
        <div style={{ color: '#666', marginBottom: '8px' }}>{state.message}</div>
        <button
          onClick={() => setState({ status: 'idle' })}
          style={{ padding: '6px 12px', border: '1px solid #ccc', borderRadius: '4px', cursor: 'pointer' }}
        >
          Try Again
        </button>
      </div>
    );
  }

  const isProcessing = state.status === 'uploading' || state.status === 'processing';

  return (
    <div style={{ padding: '16px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fafafa' }}>
      <div style={{ fontWeight: 'bold', marginBottom: '12px' }}>Import a Text</div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
        <input
          type="text"
          placeholder="Title (optional — extracted from EPUB metadata)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={isProcessing}
          style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.9em' }}
        />
        <input
          type="text"
          placeholder="Author (optional — extracted from EPUB metadata)"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          disabled={isProcessing}
          style={{ padding: '8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '0.9em' }}
        />
      </div>

      <input
        ref={fileRef}
        type="file"
        accept={ACCEPTED_FORMATS}
        onChange={handleFileSelect}
        disabled={isProcessing}
        style={{ display: 'none' }}
      />

      {isProcessing ? (
        <div style={{ textAlign: 'center', padding: '16px' }}>
          <div style={{ fontSize: '1.2em', marginBottom: '8px' }}>
            {state.status === 'uploading' ? 'Uploading...' : 'Processing...'}
          </div>
          <div style={{ color: '#666', fontSize: '0.9em' }}>
            {state.status === 'processing' && 'step' in state ? state.step : state.filename}
          </div>
          <div style={{ color: '#999', fontSize: '0.8em', marginTop: '8px' }}>
            This may take a few minutes for long novels
          </div>
        </div>
      ) : (
        <button
          onClick={() => fileRef.current?.click()}
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: '#3498db',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1em',
          }}
        >
          Select File (EPUB, TXT, PDF, HTML, Markdown)
        </button>
      )}

      <div style={{ color: '#999', fontSize: '0.8em', marginTop: '8px', textAlign: 'center' }}>
        EPUB files preserve chapters, endnotes, and metadata. Other formats extract plain text.
      </div>
    </div>
  );
}
