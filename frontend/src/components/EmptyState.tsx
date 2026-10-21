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
    <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-8 flex flex-col items-center justify-center text-center">
      <div className="w-12 h-12 rounded-full bg-obsidian-secondary border border-obsidian-border flex items-center justify-center text-obsidian-muted mb-3">
        <Icon size={22} className="text-obsidian-cyan" />
      </div>
      <h4 className="text-sm font-semibold text-obsidian-text">{title}</h4>
      <p className="text-xs text-obsidian-muted max-w-sm mt-1 leading-relaxed">
        {description}
      </p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-3.5 py-1.5 rounded bg-obsidian-cyan/15 hover:bg-obsidian-cyan/25 border border-obsidian-cyan/40 text-obsidian-cyan text-xs font-semibold transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
