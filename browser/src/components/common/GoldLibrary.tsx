/**
 * Gold Library — browse the Bible Gold Set and apply a stored gold masking map.
 *
 * Fetches GET /api/gold (the registry manifest, flagged with local availability) and,
 * for each Bible, offers an Apply action that POSTs /api/gold/{idx}/apply — the server
 * ingests the (preserve-don't-push) source and applies the frozen map after the
 * reference_sha256 check, exactly as the CLI's `gold apply` does. A Bible is appliable
 * only when both its map is committed and its source binary is present on this machine.
 */
import { useEffect, useState, type ReactElement } from 'react';

export interface GoldBible {
  id: number;
  translation: string;
  year: number | null;
  spelling: string;
  typeset: string;
  canon: string;
  kind: string;
  source_origin: string;
  source_present: boolean;
  map_present: boolean;
  gold_map: string;
  annotation_gold: string | null;
  accuracy_source: string;
  structure: { books: number | null; chapters: number | null; verses: number | null };
  validated: { cli: boolean; api: boolean; ui: boolean };
  note?: string;
}

/** Whether a Bible can be applied here, and why not when it can't. Pure — unit-tested. */
export function goldApplyState(
  b: Pick<GoldBible, 'source_present' | 'map_present'>,
): { canApply: boolean; reason: string } {
  if (!b.map_present) return { canApply: false, reason: 'map not committed' };
  if (!b.source_present) return { canApply: false, reason: 'source not on this machine' };
  return { canApply: true, reason: 'ready' };
}

/** Stable display order for the registry: ascending gold id. Pure — unit-tested. */
export function sortGold(bibles: GoldBible[]): GoldBible[] {
  return [...bibles].sort((a, b) => a.id - b.id);
}

type ApplyStatus = { state: 'idle' | 'applying' | 'done' | 'error'; detail?: string };

function StructureLine({ s }: { s: GoldBible['structure'] }): ReactElement {
  const parts = [
    s.books != null ? `${s.books} books` : null,
    s.chapters != null ? `${s.chapters} chapters` : null,
    s.verses != null ? `${s.verses.toLocaleString()} verses` : null,
  ].filter(Boolean);
  return <span className="text-[11px] text-[#8e8e93]">{parts.join(' · ') || '—'}</span>;
}

export default function GoldLibrary({
  onClose,
  onApplied,
}: {
  onClose: () => void;
  onApplied?: () => void;
}): ReactElement {
  const [bibles, setBibles] = useState<GoldBible[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<Record<number, ApplyStatus>>({});

  useEffect(() => {
    fetch('/api/gold')
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load the gold registry');
        return r.json();
      })
      .then((data: { bibles?: GoldBible[] }) => {
        setBibles(sortGold(data.bibles ?? []));
        setLoading(false);
      })
      .catch((err: Error) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  async function apply(b: GoldBible): Promise<void> {
    setStatus((s) => ({ ...s, [b.id]: { state: 'applying' } }));
    try {
      const res = await fetch(`/api/gold/${b.id}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ overwrite: true }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
      const gm = data.gold_map ?? {};
      const verses = gm.verse_count != null ? `${gm.verse_count.toLocaleString()} verses` : 'applied';
      setStatus((s) => ({ ...s, [b.id]: { state: 'done', detail: `sha verified · ${verses}` } }));
      onApplied?.();
    } catch (err) {
      setStatus((s) => ({
        ...s,
        [b.id]: { state: 'error', detail: err instanceof Error ? err.message : 'apply failed' },
      }));
    }
  }

  return (
    <div className="fixed inset-0 z-[var(--z-overlay)] flex flex-col bg-[#1c1c1e] text-[#e8e8ea] font-[var(--font-sans)]">
      <header className="shrink-0 flex items-center gap-3 h-14 px-5 border-b border-black/40 bg-[#242426]">
        <button
          type="button"
          onClick={onClose}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[13px] text-[#d6d6d8] hover:bg-white/[0.08] transition-colors"
        >
          ← Library
        </button>
        <h1 className="text-[15px] font-semibold text-white">Gold Library</h1>
        <span className="text-[12px] text-[#8e8e93]">
          Verified Bible masking maps — apply one to a fresh project.
        </span>
      </header>

      <div className="flex-1 min-h-0 overflow-y-auto px-8 py-6">
        {loading && <p className="text-[13px] text-[#8e8e93]">Loading gold registry…</p>}
        {error && <p className="text-[13px] text-[#ff453a]">{error}</p>}
        {!loading && !error && (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4">
            {bibles.map((b) => {
              const { canApply, reason } = goldApplyState(b);
              const st = status[b.id] ?? { state: 'idle' as const };
              return (
                <div
                  key={b.id}
                  className="flex flex-col gap-2 rounded-lg ring-1 ring-white/10 bg-[#242426] p-4"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-[14px] font-semibold text-white leading-tight">{b.translation}</h3>
                    <span className="shrink-0 text-[10px] uppercase tracking-wide text-[#8e8e93] mt-0.5">
                      {b.id}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#9a9aa0]">
                    {[b.kind, b.canon, b.year ?? null].filter((x) => x != null && x !== '').join(' · ')}
                  </div>
                  <StructureLine s={b.structure} />
                  <div className="mt-auto flex items-center justify-between gap-2 pt-2">
                    <button
                      type="button"
                      disabled={!canApply || st.state === 'applying'}
                      onClick={() => apply(b)}
                      title={canApply ? 'Ingest the source and apply this gold map' : reason}
                      className="px-3 py-1.5 rounded-md text-[12px] font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-[#0a84ff] text-white hover:bg-[#0a78e6]"
                    >
                      {st.state === 'applying' ? 'Applying…' : 'Apply'}
                    </button>
                    <span
                      className={`text-[11px] ${
                        st.state === 'error'
                          ? 'text-[#ff453a]'
                          : st.state === 'done'
                            ? 'text-[#30d158]'
                            : 'text-[#8e8e93]'
                      }`}
                    >
                      {st.state === 'idle' ? (canApply ? '' : reason) : st.detail}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
