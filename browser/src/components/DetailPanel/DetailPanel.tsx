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
      className="inline-block px-[6px] py-[2px] rounded-[3px] font-bold text-[0.85em]"
      style={{ backgroundColor: `${color}22`, color }}
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
        className="inline-block px-[6px] py-[2px] rounded-[3px] font-bold text-[0.85em] bg-[var(--color-primary-subtle)] text-[var(--color-primary-hover)]"
      >
        {level}
      </span>
    </Tooltip>
  );
}

function PropertyRow({ label, children }: { label: string; children: React.ReactNode }): JSX.Element {
  return (
    <div className="flex py-[4px] border-b border-[var(--color-border-subtle)]">
      <span className="w-[90px] text-[#888] text-[0.8em] shrink-0">{label}</span>
      <span className="flex-1 text-[0.9em]">{children}</span>
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
      <div className="mb-[12px]">
        <div className="font-bold text-[1em] text-[#2c3e50] mb-[4px]">
          {isEndnote ? `Endnote ${noteNumber ?? ''}` : bodyType}
        </div>
        <div className="flex gap-[6px] items-center">
          <EvidenceBadge level={evidenceLevel} />
          <ConfidenceBadge value={confidence} />
        </div>
      </div>

      {isEndnote && noteText ? (
        <div className="p-[10px] bg-[#fdf6f0] border-l-[3px] border-[var(--color-danger)] mb-[12px] text-[0.9em] leading-[1.5] max-h-[250px] overflow-y-auto whitespace-pre-wrap">
          {noteText}
        </div>
      ) : excerpt ? (
        <div className="p-[8px] bg-[var(--color-bg-overlay)] border-l-[3px] border-[var(--color-primary)] mb-[12px] italic text-[0.9em] max-h-[100px] overflow-auto">
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
    <div className="w-[var(--width-detail-panel)] border-l border-[var(--color-border)] overflow-y-auto p-[var(--spacing-panel)] text-[0.85em]">
      <div className="font-bold mb-[8px] flex justify-between items-center">
        <span>Details</span>
        {selectedAnnotation && (
          <button
            onClick={() => selectAnnotation(null)}
            className="border-none bg-none cursor-pointer text-[var(--color-text-muted)] text-[1.1em]"
          >
            ×
          </button>
        )}
      </div>

      {selectedAnnotation ? (
        <>
          <AnnotationDetail ann={selectedAnnotation} />
          {selectedAnnotation.body.type === 'palimpsest:LitHMMAnnotation' && projectId && (
            <div className="mt-[16px] border-t border-[#eee] pt-[12px]">
              <div className="font-bold mb-[6px]">State Explanation</div>
              <StateExplainer
                projectId={projectId}
                stateId={(selectedAnnotation.body as Record<string, unknown>)['palimpsest:stateId'] as number ?? 0}
                stateDescription={(selectedAnnotation.body as Record<string, unknown>)['palimpsest:stateDescription'] as string | undefined}
              />
            </div>
          )}
          {selectedAnnotation.target.selector.start != null && (
            <div className="mt-[16px] border-t border-[#eee] pt-[12px]">
              <div className="font-bold mb-[6px]">AI Summary</div>
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
        <div className="text-[var(--color-text-muted)] italic">
          Click an annotation highlight to view its properties.
        </div>
      )}
    </div>
  );
}
