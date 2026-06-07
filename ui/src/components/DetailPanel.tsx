import { useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useProjectStore } from '../stores/projectStore';

export default function DetailPanel() {
  const info = useProjectStore((s) => s.info);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  async function loadDetail(index: number) {
    if (!info) return;
    try {
      const json = await invoke<string>('get_annotation_detail', {
        projectId: info.id,
        annotationIndex: index,
      });
      const parsed = JSON.parse(json);
      setDetail(parsed);
      setSelectedIndex(index);
    } catch {
      setDetail(null);
    }
  }

  // Expose for external use
  (window as unknown as { loadAnnotationDetail: (i: number) => void }).loadAnnotationDetail = loadDetail;

  return (
    <aside style={{
      width: '280px',
      borderLeft: '1px solid #e0e0e0',
      overflowY: 'auto',
      padding: '12px',
      fontSize: '0.85em',
      flexShrink: 0,
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>Details</div>
      {detail ? (
        <div>
          <div style={{ marginBottom: '8px' }}>
            <span style={{
              padding: '2px 6px',
              backgroundColor: '#3498db22',
              color: '#2980b9',
              borderRadius: '3px',
              fontWeight: 'bold',
              fontSize: '0.85em',
            }}>
              {String(detail['palimpsest:evidenceLevel'] ?? 'E5')}
            </span>
            {' '}
            <span style={{
              padding: '2px 6px',
              backgroundColor: '#27ae6022',
              color: '#27ae60',
              borderRadius: '3px',
              fontWeight: 'bold',
              fontSize: '0.85em',
            }}>
              {Math.round((detail['palimpsest:confidence'] as number ?? 0) * 100)}%
            </span>
          </div>

          <div style={{ fontSize: '0.8em', color: '#666', marginBottom: '8px' }}>
            Index: {selectedIndex} · Type: {String((detail.body as Record<string, unknown>)?.type ?? '').replace('palimpsest:', '')}
          </div>

          <pre style={{
            fontSize: '0.75em',
            backgroundColor: '#f5f5f5',
            padding: '8px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '400px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}>
            {JSON.stringify(detail, null, 2)}
          </pre>
        </div>
      ) : (
        <p style={{ color: '#999', fontStyle: 'italic' }}>Click an annotation to view details.</p>
      )}
    </aside>
  );
}
