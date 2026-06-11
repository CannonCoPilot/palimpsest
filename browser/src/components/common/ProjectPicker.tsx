/**
 * ProjectPicker — dropdown populated by /api/projects.
 * Shown when no project is loaded. Allows selection without URL manipulation.
 */

import { useEffect, useState } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import ImportDialog from './ImportDialog';

interface ProjectEntry {
  id: string;
  title: string;
  author: string;
  word_count: number;
}

export default function ProjectPicker(): JSX.Element {
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadProject = useProjectStore((s) => s.loadProject);

  useEffect(() => {
    fetch('/api/projects')
      .then((r) => {
        if (!r.ok) throw new Error('Failed to fetch projects');
        return r.json();
      })
      .then((data: ProjectEntry[]) => {
        setProjects(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  function handleSelect(id: string): void {
    const url = new URL(window.location.href);
    url.searchParams.set('project', id);
    window.history.pushState({}, '', url.toString());
    loadProject('', id);
  }

  if (loading) {
    return <div style={{ color: '#999', padding: '16px' }}>Loading projects...</div>;
  }

  if (error) {
    return (
      <div style={{ color: '#e74c3c', padding: '16px' }}>
        Could not load projects: {error}
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div style={{ padding: '16px' }}>
        <ImportDialog />
      </div>
    );
  }

  return (
    <div style={{ padding: '16px' }}>
      <div style={{ marginBottom: '16px' }}>
        <ImportDialog />
      </div>
      <div style={{ marginBottom: '12px', fontWeight: 'bold' }}>Or select an existing project:</div>
      {projects.map((p) => (
        <div
          key={p.id}
          onClick={() => handleSelect(p.id)}
          style={{
            padding: '12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            marginBottom: '8px',
            cursor: 'pointer',
            transition: 'background-color 0.15s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f0f7ff')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          <div style={{ fontWeight: 'bold' }}>{p.title}</div>
          {p.author && <div style={{ color: '#666', fontSize: '0.9em' }}>by {p.author}</div>}
          <div style={{ color: '#999', fontSize: '0.8em' }}>
            {p.word_count.toLocaleString()} words
          </div>
        </div>
      ))}
    </div>
  );
}
