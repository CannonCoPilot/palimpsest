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
      <div role="listbox" aria-label="Available projects">
        {projects.map((p) => (
          <div
            key={p.id}
            role="option"
            tabIndex={0}
            onClick={() => handleSelect(p.id)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSelect(p.id); } }}
            className="p-3 border border-[var(--color-border)] rounded mb-2 cursor-pointer transition-colors hover:bg-[#f0f7ff] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          >
            <div className="font-bold">{p.title}</div>
            {p.author && <div className="text-[var(--color-text-secondary)] text-[0.9em]">by {p.author}</div>}
            <div className="text-[var(--color-text-muted)] text-[0.8em]">
              {p.word_count.toLocaleString()} words
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
