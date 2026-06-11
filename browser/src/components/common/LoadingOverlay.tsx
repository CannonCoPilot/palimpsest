import { useProjectStore } from '../../stores/projectStore';

function SkeletonLine({ width }: { width: string }) {
  return (
    <div
      className="h-2.5 rounded-sm bg-[var(--color-bg-muted)] animate-pulse mb-1.5"
      style={{ width }}
    />
  );
}

function TrackSkeleton() {
  return (
    <div className="flex items-center gap-2 py-1.5">
      <div className="w-2.5 h-2.5 rounded-sm bg-[var(--color-bg-muted)] animate-pulse" />
      <SkeletonLine width="60%" />
      <SkeletonLine width="20px" />
    </div>
  );
}

export default function LoadingOverlay() {
  const loadingState = useProjectStore((s) => s.loadingState);
  const loadingStep = useProjectStore((s) => s.loadingStep);

  if (loadingState !== 'loading') return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 bg-white/90 flex items-center justify-center z-[var(--z-overlay)]"
    >
      <div className="p-6 bg-[var(--color-bg)] rounded-[var(--radius-lg)] shadow-[var(--shadow-popover)] text-center min-w-[300px]">
        <div className="mb-4">
          <div className="inline-block w-8 h-8 border-3 border-[var(--color-bg-muted)] border-t-[var(--color-primary)] rounded-full animate-spin" />
        </div>
        <h2 className="text-lg font-semibold mb-1 font-[var(--font-serif)]">Loading Palimpsest</h2>
        <div className="text-[var(--color-text-muted)] text-sm mb-4">{loadingStep || 'Preparing...'}</div>

        <div className="text-left border-t border-[var(--color-border-subtle)] pt-3 mt-2">
          <div className="text-[0.7em] text-[var(--color-text-muted)] font-semibold mb-1.5">Loading tracks...</div>
          <TrackSkeleton />
          <TrackSkeleton />
          <TrackSkeleton />
          <TrackSkeleton />
          <TrackSkeleton />
        </div>
      </div>
    </div>
  );
}
