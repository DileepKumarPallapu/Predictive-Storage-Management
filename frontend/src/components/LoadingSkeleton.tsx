import React from 'react';

export const LoadingSkeleton: React.FC<{ rows?: number; height?: string }> = ({
  rows = 4,
  height = 'h-4',
}) => {
  return (
    <div className="space-y-3 animate-pulse p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={`w-full bg-obsidian-secondary/60 rounded ${height}`}
          style={{ width: `${100 - (i % 3) * 15}%` }}
        ></div>
      ))}
    </div>
  );
};
