import type { W3CAnnotation } from '../../adapters/AnnotationAdapter';

interface Props {
  annotation: W3CAnnotation;
}

export default function AnnotationHoverCard({ annotation }: Props) {
  const body = annotation.body as Record<string, unknown>;
  const typeName = annotation.body.type.replace('palimpsest:', '');
  const confidence = (annotation['palimpsest:confidence'] as number) ?? 0;
  const evidenceLevel = (annotation['palimpsest:evidenceLevel'] as string) ?? 'E5';
  const pct = Math.round(confidence * 100);

  const stateId = body['palimpsest:stateId'] as number | undefined;
  const stateDesc = body['palimpsest:stateDescription'] as string | undefined;
  const noteNum = body['palimpsest:noteNumber'] as number | undefined;
  const noteText = body['palimpsest:noteText'] as string | undefined;
  const headingText = body['palimpsest:headingText'] as string | undefined;
  const topicLabel = body['palimpsest:topicLabel'] as string | undefined;

  const confColor = confidence >= 0.8
    ? 'var(--color-confidence-high)'
    : confidence >= 0.5
      ? 'var(--color-confidence-mid)'
      : 'var(--color-confidence-low)';

  let subtitle = annotation.body.value || '';
  if (stateId != null && stateDesc) subtitle = `State ${stateId}: ${stateDesc}`;
  else if (noteNum != null && noteText) subtitle = `Endnote ${noteNum}: ${noteText.slice(0, 80)}${noteText.length > 80 ? '...' : ''}`;
  else if (headingText) subtitle = headingText;
  else if (topicLabel) subtitle = String(topicLabel);

  return (
    <div className="min-w-[180px] max-w-[280px]">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="font-semibold text-white text-[0.85em]">{typeName}</span>
        <span className="px-1 text-[0.6em] rounded-sm bg-white/20 text-white/80 font-bold">{evidenceLevel}</span>
      </div>
      {subtitle && (
        <div className="text-white/80 text-[0.75em] mb-1.5 leading-snug line-clamp-2">{subtitle}</div>
      )}
      <div className="flex items-center gap-1.5">
        <div className="flex-1 h-1 rounded-full bg-white/20 overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: confColor }} />
        </div>
        <span className="text-[0.65em] text-white/70 font-mono">{pct}%</span>
      </div>
    </div>
  );
}
