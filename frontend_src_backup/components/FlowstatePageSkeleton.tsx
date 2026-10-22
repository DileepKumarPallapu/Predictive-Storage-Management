import React from 'react';

export const FlowstatePageSkeleton: React.FC = () => {
  return (
    <div className="space-y-6 animate-pulse" aria-label="Loading page content" role="status">
      {/* Skeleton Header Banner */}
      <div className="glass-panel border border-[var(--border-subtle)] rounded-xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="space-y-2.5 w-full max-w-lg">
            <div className="h-3 w-32 bg-[var(--surface-elevated)] rounded-full" />
            <div className="h-7 w-72 bg-[var(--surface-elevated)] rounded-lg" />
            <div className="h-4 w-96 bg-[var(--surface-elevated)]/60 rounded" />
          </div>
          <div className="flex items-center gap-3">
            <div className="h-8 w-36 bg-[var(--surface-elevated)] rounded-lg" />
            <div className="h-8 w-28 bg-[var(--surface-elevated)] rounded-lg" />
          </div>
        </div>

        {/* Skeleton Sub-metrics */}
        <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-[var(--border-subtle)]/60">
          <div className="h-4 bg-[var(--surface-elevated)]/80 rounded w-28" />
          <div className="h-4 bg-[var(--surface-elevated)]/80 rounded w-32" />
          <div className="h-4 bg-[var(--surface-elevated)]/80 rounded w-24" />
          <div className="h-4 bg-[var(--surface-elevated)]/80 rounded w-36" />
        </div>
      </div>

      {/* Skeleton KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="glass-panel border border-[var(--border-subtle)] rounded-xl p-5 space-y-3">
            <div className="h-3 w-24 bg-[var(--surface-elevated)] rounded" />
            <div className="h-8 w-32 bg-[var(--surface-elevated)] rounded" />
            <div className="h-3 w-40 bg-[var(--surface-elevated)]/60 rounded" />
          </div>
        ))}
      </div>

      {/* Skeleton Content Section / Chart */}
      <div className="glass-panel border border-[var(--border-subtle)] rounded-xl p-6 space-y-4">
        <div className="flex justify-between items-center">
          <div className="h-5 w-48 bg-[var(--surface-elevated)] rounded" />
          <div className="h-4 w-24 bg-[var(--surface-elevated)]/60 rounded" />
        </div>
        <div className="h-64 bg-[var(--surface-primary)] border border-dashed border-[var(--border-normal)] rounded-lg flex items-center justify-center">
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)]">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-primary)] animate-ping" />
            <span>Loading telemetry stream...</span>
          </div>
        </div>
      </div>
    </div>
  );
};
