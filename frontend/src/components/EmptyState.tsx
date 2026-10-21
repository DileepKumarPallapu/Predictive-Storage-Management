import React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  actionText,
  onAction,
}) => {
  return (
    <div className="glass-panel rounded-xl p-8 flex flex-col items-center justify-center text-center">
      <div className="w-14 h-14 rounded-2xl bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--accent-cyan)] mb-3 shadow-inner">
        <Icon size={24} className="text-[var(--accent-cyan)]" />
      </div>
      <h4 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h4>
      <p className="text-xs text-[var(--text-secondary)] max-w-sm mt-1.5 leading-relaxed">
        {description}
      </p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-4 py-2 rounded-lg btn-aurora-primary text-xs font-semibold"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
