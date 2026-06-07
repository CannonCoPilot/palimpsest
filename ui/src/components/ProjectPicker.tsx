import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useProjectStore } from '../stores/projectStore';
import { useTrackStore } from '../stores/trackStore';

interface ProjectEntry {
  id: string;
  title: string;
  author: string | null;
  word_count: number;
}

export default function ProjectPicker() {
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const loadProject = useProjectStore((s) => s.loadProject);
  const initTracks = useTrackStore((s) => s.initTracks);

  useEffect(() => {
    invoke<ProjectEntry[]>('list_projects')
      .then(setProjects)
      .catch(() => {});
  }, []);

  async function handleSelect(id: string) {
    setLoading(true);
    await loadProject(id);
    const info = useProjectStore.getState().info;
    if (info) initTracks(info.tracks);
    setLoading(false);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '24px' }}>
      <h1 style={{ fontSize: '2em', fontFamily: "'Crimson Pro', Georgia, serif" }}>Palimpsest</h1>
      <p style={{ color: '#666' }}>Computational Literary Analysis Platform</p>
      {loading && <p>Loading...</p>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '400px' }}>
        {projects.map((p) => (
          <button
            key={p.id}
            onClick={() => handleSelect(p.id)}
            style={{
              padding: '16px',
              border: '1px solid #ddd',
              borderRadius: '6px',
              background: 'white',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'border-color 0.15s',
            }}
          >
            <div style={{ fontWeight: 'bold', fontSize: '1.1em' }}>{p.title}</div>
            {p.author && <div style={{ color: '#666', fontSize: '0.9em' }}>by {p.author}</div>}
            <div style={{ color: '#999', fontSize: '0.8em' }}>{p.word_count.toLocaleString()} words</div>
          </button>
        ))}
        {projects.length === 0 && !loading && (
          <p style={{ color: '#999', textAlign: 'center' }}>No projects found. Run: palimpsest ingest</p>
        )}
      </div>
    </div>
  );
}
