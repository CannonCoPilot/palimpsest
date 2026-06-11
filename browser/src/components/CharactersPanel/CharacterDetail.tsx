interface CharacterRecord {
  canonicalName: string;
  aliases: string[];
  type: string;
  mentionCount: number;
  firstOccurrence: number;
  lastOccurrence: number;
  firstParagraph: number;
  lastParagraph: number;
  paragraphIndices: number[];
  density: number[];
}

interface Props {
  character: CharacterRecord;
  onClose: () => void;
  onChainFollow: (char: CharacterRecord) => void;
}

function MentionHistogram({ density }: { density: number[] }) {
  const max = Math.max(1, ...density);
  const width = 250;
  const height = 60;
  const barW = width / density.length;

  return (
    <div>
      <div className="text-[0.75em] text-[var(--color-text-muted)] mb-1">Mention distribution</div>
      <svg width={width} height={height + 16} className="block">
        {density.map((v, i) => {
          if (v === 0) return null;
          const h = (v / max) * height;
          return <rect key={i} x={i * barW} y={height - h} width={Math.max(0.5, barW - 0.2)} height={h} fill="var(--color-primary)" fillOpacity={0.5} />;
        })}
        <text x={0} y={height + 12} fontSize={8} fill="var(--color-text-muted)">¶0</text>
        <text x={width} y={height + 12} fontSize={8} fill="var(--color-text-muted)" textAnchor="end">¶{density.length}</text>
      </svg>
    </div>
  );
}

export default function CharacterDetail({ character, onClose, onChainFollow }: Props) {
  const typeBadgeColor: Record<string, string> = { person: '#3b82f6', organization: '#f59e0b', place: '#10b981', group: '#8b5cf6', other: '#6b7280' };

  return (
    <div className="w-[280px] border-l border-[var(--color-border)] bg-[var(--color-bg)] overflow-auto p-3 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-[1em]">{character.canonicalName}</h3>
        <button onClick={onClose} className="text-[var(--color-text-muted)] cursor-pointer hover:text-[var(--color-text)]">✕</button>
      </div>

      <div className="flex items-center gap-2">
        <span className="px-1.5 py-0.5 rounded-full text-[0.7em] text-white" style={{ backgroundColor: typeBadgeColor[character.type] ?? '#6b7280' }}>
          {character.type}
        </span>
        <span className="text-[var(--color-text-muted)] text-[0.85em]">{character.mentionCount} mentions</span>
      </div>

      {character.aliases.length > 0 && (
        <div>
          <div className="text-[0.75em] text-[var(--color-text-muted)] mb-1">Aliases / referent forms</div>
          <div className="flex flex-wrap gap-1">
            {character.aliases.slice(0, 15).map((alias) => (
              <span key={alias} className="px-1.5 py-0.5 bg-[var(--color-bg-muted)] rounded text-[0.8em] border border-[var(--color-border-subtle)]">
                {alias}
              </span>
            ))}
            {character.aliases.length > 15 && (
              <span className="text-[var(--color-text-muted)] text-[0.8em]">+{character.aliases.length - 15} more</span>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-[0.85em]">
        <div>
          <span className="text-[var(--color-text-muted)] text-[0.8em]">First mention</span>
          <div className="font-[var(--font-mono)]">¶{character.firstParagraph}</div>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)] text-[0.8em]">Last mention</span>
          <div className="font-[var(--font-mono)]">¶{character.lastParagraph}</div>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)] text-[0.8em]">Paragraphs</span>
          <div className="font-[var(--font-mono)]">{character.paragraphIndices.length}</div>
        </div>
        <div>
          <span className="text-[var(--color-text-muted)] text-[0.8em]">Span</span>
          <div className="font-[var(--font-mono)]">¶{character.firstParagraph}–¶{character.lastParagraph}</div>
        </div>
      </div>

      <MentionHistogram density={character.density} />

      <button
        onClick={() => onChainFollow(character)}
        className="w-full py-1.5 rounded border border-[var(--color-primary)] text-[var(--color-primary)] cursor-pointer hover:bg-[var(--color-primary)] hover:text-white transition-colors text-[0.85em]"
      >
        Show in Reading view
      </button>
    </div>
  );
}
