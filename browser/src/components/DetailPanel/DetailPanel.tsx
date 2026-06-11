/**
 * DetailPanel — shows W3C annotation properties when an annotation is selected.
 * Displays evidence level, confidence, body type, target offsets, and creator.
 */

import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';
import { useViewStore } from '../../stores/viewStore';
import { useProjectStore } from '../../stores/projectStore';
import LLMSummary from './LLMSummary';
import StateExplainer from './StateExplainer';
import { Tooltip } from '../common/Tooltip';

function ConfidenceBadge({ value }: { value: number }): JSX.Element {
  const pct = Math.round(value * 100);
  const color = value >= 0.8 ? '#27ae60' : value >= 0.5 ? '#e67e22' : '#e74c3c';
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 6px',
        borderRadius: '3px',
        backgroundColor: `${color}22`,
        color,
        fontWeight: 'bold',
        fontSize: '0.85em',
      }}
    >
      {pct}%
    </span>
  );
}

function EvidenceBadge({ level }: { level: string }): JSX.Element {
  const descriptions: Record<string, string> = {
    E1: 'Explicit in text',
    E2: 'Human annotator',
    E3: 'Cross-text homology',
    E4: 'ML prediction',
    E5: 'Rule-based/statistical',
  };
  return (
    <Tooltip content={descriptions[level] || level} side="bottom">
      <span
        style={{
          display: 'inline-block',
          padding: '2px 6px',
          borderRadius: '3px',
          backgroundColor: '#3498db22',
          color: '#2980b9',
          fontWeight: 'bold',
          fontSize: '0.85em',
        }}
      >
        {level}
      </span>
    </Tooltip>
  );
}

function PropertyRow({ label, children }: { label: string; children: React.ReactNode }): JSX.Element {
  return (
    <div style={{ display: 'flex', padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
      <span style={{ width: '90px', color: '#888', fontSize: '0.8em', flexShrink: 0 }}>{label}</span>
      <span style={{ flex: 1, fontSize: '0.9em' }}>{children}</span>
    </div>
  );
}

function AnnotationDetail({ ann }: { ann: W3CAnnotation }): JSX.Element {
  const referenceText = useProjectStore((s) => s.referenceText);
  const sel = ann.target.selector;
  const excerpt =
    sel.type === 'TextPositionSelector' && sel.start != null && sel.end != null
      ? referenceText.slice(sel.start, sel.end)
      : ann.body.value || '';

  const bodyType = ann.body.type.replace('palimpsest:', '');
  const confidence = ann['palimpsest:confidence'] ?? 0;
  const evidenceLevel = ann['palimpsest:evidenceLevel'] ?? 'E4';

  const bodyObj = ann.body as Record<string, unknown>;
  const isEndnote = ann.body.type === 'palimpsest:EndnoteAnnotation';
  const noteText = bodyObj['palimpsest:noteText'] as string | undefined;
  const noteNumber = bodyObj['palimpsest:noteNumber'] as number | undefined;

  const extraProps = Object.entries(ann.body)
    .filter(([k]) => k.startsWith('palimpsest:') && k !== 'palimpsest:lfoType'
      && k !== 'palimpsest:noteText')
    .map(([k, v]) => [k.replace('palimpsest:', ''), v] as [string, unknown]);

  return (
    <div>
      <div style={{ marginBottom: '12px' }}>
        <div
          style={{
            fontWeight: 'bold',
            fontSize: '1em',
            color: '#2c3e50',
            marginBottom: '4px',
          }}
        >
          {isEndnote ? `Endnote ${noteNumber ?? ''}` : bodyType}
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <EvidenceBadge level={evidenceLevel} />
          <ConfidenceBadge value={confidence} />
        </div>
      </div>

      {isEndnote && noteText ? (
        <div
          style={{
            padding: '10px',
            backgroundColor: '#fdf6f0',
            borderLeft: '3px solid #e74c3c',
            marginBottom: '12px',
            fontSize: '0.9em',
            lineHeight: 1.5,
            maxHeight: '250px',
            overflowY: 'auto',
            whiteSpace: 'pre-wrap',
          }}
        >
          {noteText}
        </div>
      ) : excerpt ? (
        <div
          style={{
            padding: '8px',
            backgroundColor: '#f8f9fa',
            borderLeft: '3px solid #3498db',
            marginBottom: '12px',
            fontStyle: 'italic',
            fontSize: '0.9em',
            maxHeight: '100px',
            overflow: 'auto',
          }}
        >
          {excerpt.length > 200 ? `${excerpt.slice(0, 200)}...` : excerpt}
        </div>
      ) : null}

      <PropertyRow label="ID">{ann.id}</PropertyRow>
      <PropertyRow label="Creator">{ann.creator.name}</PropertyRow>
      {sel.type === 'TextPositionSelector' && (
        <PropertyRow label="Offsets">
          {sel.start}–{sel.end}
        </PropertyRow>
      )}
      {!isEndnote && ann.body.value && <PropertyRow label="Value">{ann.body.value}</PropertyRow>}
      {extraProps.map(([k, v]) => (
        <PropertyRow key={k} label={k}>
          {typeof v === 'string' && v.length > 100 ? `${v.slice(0, 100)}...` : String(v)}
        </PropertyRow>
      ))}
    </div>
  );
}

export default function DetailPanel(): JSX.Element {
  const selectedAnnotation = useViewStore((s) => s.selectedAnnotation);
  const selectAnnotation = useViewStore((s) => s.selectAnnotation);
  const referenceText = useProjectStore((s) => s.referenceText);
  const projectId = useProjectStore((s) => s.projectId);

  return (
    <div
      style={{
        width: '280px',
        borderLeft: '1px solid #ddd',
        overflowY: 'auto',
        padding: '12px',
        fontSize: '0.85em',
      }}
    >
      <div
        style={{
          fontWeight: 'bold',
          marginBottom: '8px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span>Details</span>
        {selectedAnnotation && (
          <button
            onClick={() => selectAnnotation(null)}
            style={{
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              color: '#999',
              fontSize: '1.1em',
            }}
          >
            ×
          </button>
        )}
      </div>

      {selectedAnnotation ? (
        <>
          <AnnotationDetail ann={selectedAnnotation} />
          {selectedAnnotation.body.type === 'palimpsest:LitHMMAnnotation' && projectId && (
            <div style={{ marginTop: '16px', borderTop: '1px solid #eee', paddingTop: '12px' }}>
              <div style={{ fontWeight: 'bold', marginBottom: '6px' }}>State Explanation</div>
              <StateExplainer
                projectId={projectId}
                stateId={(selectedAnnotation.body as Record<string, unknown>)['palimpsest:stateId'] as number ?? 0}
                stateDescription={(selectedAnnotation.body as Record<string, unknown>)['palimpsest:stateDescription'] as string | undefined}
              />
            </div>
          )}
          {selectedAnnotation.target.selector.start != null && (
            <div style={{ marginTop: '16px', borderTop: '1px solid #eee', paddingTop: '12px' }}>
              <div style={{ fontWeight: 'bold', marginBottom: '6px' }}>AI Summary</div>
              <LLMSummary
                passage={referenceText.slice(
                  selectedAnnotation.target.selector.start!,
                  Math.min(selectedAnnotation.target.selector.end! + 500, referenceText.length)
                )}
                passageId={selectedAnnotation.id}
              />
            </div>
          )}
        </>
      ) : (
        <div style={{ color: '#999', fontStyle: 'italic' }}>
          Click an annotation highlight to view its properties.
        </div>
      )}
    </div>
  );
}
