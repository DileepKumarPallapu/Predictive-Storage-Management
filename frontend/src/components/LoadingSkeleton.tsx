import React from 'react';

export const LoadingSkeleton: React.FC<{ rows?: number; height?: string }> = ({
  rows = 4,
  height = 'h-4',
}) => {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={`w-full bg-[var(--surface-raised)]/70 rounded-lg animate-pulse border border-[var(--border-subtle)] ${height}`}
          style={{ width: `${100 - (i % 3) * 15}%` }}
        />
      ))}
    </div>
  );
};
