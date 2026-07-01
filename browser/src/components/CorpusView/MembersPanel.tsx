/**
 * MembersPanel — the collection Members tab (C7, FR-24/FR-25).
 *
 * Lists a collection's members with their inverse-navigation lattice (Work tag, parent + derived
 * children, edition siblings) from `GET /api/projects/{id}/lattice`, and each member's collection-local
 * role. Toggling a member to **root** (`PUT /api/collections/{id}/roles/{pid}`) re-coordinates the lens
 * the Overview/Corpus surfaces project onto — root re-coordination. A member name opens its single-text
 * browser (the deepest zoom tier).
 */

import { useEffect, useState, useCallback } from 'react';

interface Lattice {
  project_id: string;
  work_id: string | null;
  parent: string | null;
  children: string[];
  siblings: string[];
  collections: string[];
}

export default function MembersPanel({
  collectionId,
  members,
  roles,
  onMember,
  onRolesChanged,
}: {
  collectionId: string;
  members: string[];
  roles: Record<string, string>;
  onMember: (m: string) => void;
  onRolesChanged?: () => void;
}) {
  const [lattices, setLattices] = useState<Record<string, Lattice>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      members.map((m) =>
        fetch(`/api/projects/${m}/lattice`)
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
      ),
    ).then((results) => {
      if (cancelled) return;
      const map: Record<string, Lattice> = {};
      results.forEach((lat, i) => {
        if (lat) map[members[i]] = lat as Lattice;
      });
      setLattices(map);
    });
    return () => {
      cancelled = true;
    };
  }, [members]);

  const setRole = useCallback(
    async (pid: string, role: string) => {
      setBusy(pid);
      setError(null);
      try {
        const resp = await fetch(`/api/collections/${collectionId}/roles/${pid}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role }),
        });
        if (!resp.ok) {
          const j = await resp.json().catch(() => ({}));
          throw new Error(j.detail ?? 'Failed to set role');
        }
        onRolesChanged?.();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(null);
      }
    },
    [collectionId, onRolesChanged],
  );

  return (
    <div className="flex flex-col gap-3 max-w-[720px]">
      {error && (
        <div className="px-3 py-2 rounded bg-[var(--color-danger-subtle)] text-[var(--color-danger)] text-[0.85em]">{error}</div>
      )}
      <table className="w-full border-collapse text-[0.82em]">
        <thead>
          <tr className="text-left text-[var(--color-text-muted)] border-b border-[var(--color-border)]">
            <th className="py-1.5 pr-3 font-medium">Member</th>
            <th className="py-1.5 pr-3 font-medium">Work</th>
            <th className="py-1.5 pr-3 font-medium">Lineage</th>
            <th className="py-1.5 pr-3 font-medium">Role</th>
          </tr>
        </thead>
        <tbody>
          {members.map((m) => {
            const lat = lattices[m];
            const role = roles[m] ?? 'member';
            const isRoot = role === 'root';
            return (
              <tr key={m} className="border-b border-[var(--color-border)] align-top">
                <td className="py-1.5 pr-3">
                  <button
                    onClick={() => onMember(m)}
                    title={`Open ${m} in the single-text browser`}
                    className="text-[var(--color-primary)] hover:underline cursor-pointer truncate max-w-52 text-left"
                  >
                    {m}
                  </button>
                </td>
                <td className="py-1.5 pr-3 text-[var(--color-text-muted)]">
                  {lat?.work_id ?? <span className="opacity-50">—</span>}
                </td>
                <td className="py-1.5 pr-3 text-[var(--color-text-muted)] text-[0.92em]">
                  {lat ? (
                    <div className="flex flex-col gap-0.5">
                      {lat.parent && <span>↳ from <span className="text-[var(--color-text)]">{lat.parent}</span></span>}
                      {lat.children.length > 0 && <span>{lat.children.length} derived</span>}
                      {lat.siblings.length > 0 && <span>{lat.siblings.length} sibling{lat.siblings.length !== 1 ? 's' : ''}</span>}
                      {!lat.parent && lat.children.length === 0 && lat.siblings.length === 0 && (
                        <span className="opacity-50">standalone</span>
                      )}
                    </div>
                  ) : (
                    <span className="opacity-50">…</span>
                  )}
                </td>
                <td className="py-1.5 pr-3">
                  <button
                    disabled={busy === m}
                    onClick={() => setRole(m, isRoot ? 'member' : 'root')}
                    aria-pressed={isRoot}
                    title={isRoot ? 'This member is the root lens — click to demote to co-equal member' : 'Make this member the root lens (re-coordinates the Overview/Corpus projection)'}
                    className="px-2 py-0.5 rounded border cursor-pointer disabled:opacity-50 text-[0.92em]"
                    style={{
                      borderColor: isRoot ? 'var(--color-primary)' : 'var(--color-border)',
                      background: isRoot ? 'var(--color-primary)' : 'transparent',
                      color: isRoot ? 'white' : 'var(--color-text-muted)',
                    }}
                  >
                    {isRoot ? 'root' : 'member'}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
