/**
 * CostDialog — reusable pre-run cost surface (C7c, P2 / NFR-C4).
 *
 * The workbench's honesty guarantee for expensive operations: embedding a probe query, re-embedding
 * members to reconcile a metric space, and any future costed run must show their cost and NEVER auto-run.
 * The work happens only when the user confirms this dialog — mounting it is the "are you sure + here's the
 * cost" step, not the execution. Callers pass the estimate as children so each op explains its own cost.
 */

import type { ReactNode } from 'react';

export default function CostDialog({
  title,
  confirmLabel = 'Proceed',
  busy = false,
  onConfirm,
  onCancel,
  children,
}: {
  title: string;
  confirmLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  children: ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" role="dialog" aria-modal="true" aria-label={title}>
      <div className="bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg p-5 shadow-lg max-w-[460px]">
        <div className="font-semibold text-[1em] mb-2">{title}</div>
        <div className="text-[0.85em] text-[var(--color-text-muted)] mb-4 flex flex-col gap-2">{children}</div>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            disabled={busy}
            className="px-3 py-1.5 rounded border border-[var(--color-border)] text-[var(--color-text-muted)] cursor-pointer hover:bg-[var(--color-bg-muted)] text-[0.85em] disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={busy}
            className="px-3 py-1.5 rounded bg-[var(--color-primary)] text-white cursor-pointer hover:opacity-90 text-[0.85em] disabled:opacity-50"
          >
            {busy ? 'Working…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
