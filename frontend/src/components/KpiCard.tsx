import React, { ReactNode } from 'react';
import { ContextualHelp } from './ContextualHelp';

export interface KpiCardProps {
  label: string;
  value: string | number | ReactNode;
  unit?: string;
  help?: {
    title: string;
    simpleExplanation: string;
    technicalDetails?: string;
  };
  progress?: {
    value: number; // 0 to 100
    status?: 'normal' | 'success' | 'warning' | 'critical';
  };
  description?: string | ReactNode;
  footer?: ReactNode;
  badge?: {
    label: string;
    variant?: 'normal' | 'success' | 'warning' | 'critical' | 'brand';
  };
  className?: string;
  onClick?: () => void;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  unit,
  help,
  progress,
  description,
  footer,
  badge,
  className = '',
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={`kpi-card flex flex-col justify-between ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      <div className="kpi-card__content flex flex-col justify-between flex-1">
        {/* Header row: Label + optional help icon + optional badge */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-xs font-semibold text-[var(--text-secondary)] truncate">
              {label}
            </span>
            {help && (
              <ContextualHelp
                title={help.title}
                simpleExplanation={help.simpleExplanation}
                technicalDetails={help.technicalDetails}
              />
            )}
          </div>
          {badge && (
            <span
              className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full shrink-0 ${
                badge.variant === 'critical'
                  ? 'bg-[var(--status-critical)]/10 text-[var(--status-critical)] border border-[var(--status-critical)]/30'
                  : badge.variant === 'warning'
                  ? 'bg-[var(--status-warning)]/10 text-[var(--status-warning)] border border-[var(--status-warning)]/30'
                  : badge.variant === 'success'
                  ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border border-[var(--status-success)]/30'
                  : badge.variant === 'brand'
                  ? 'bg-[var(--brand-soft)] text-[var(--brand-primary)] border border-[var(--brand-primary)]/20'
                  : 'bg-[var(--surface-secondary)] text-[var(--text-muted)] border border-[var(--border-subtle)]'
              }`}
            >
              {badge.label}
            </span>
          )}
        </div>

        {/* Main metric value */}
        <div className="mt-2.5">
          <div className="kpi-card__value flex items-baseline gap-1.5">
            <span>{value}</span>
            {unit && (
              <span className="text-xs font-medium text-[var(--text-muted)] font-sans">
                {unit}
              </span>
            )}
          </div>

          {/* Optional progress indicator */}
          {progress && (
            <div className="w-full bg-[var(--surface-secondary)] border border-[var(--border-subtle)] h-1.5 rounded-full overflow-hidden mt-3">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  progress.status === 'critical'
                    ? 'bg-[var(--status-critical)]'
                    : progress.status === 'warning'
                    ? 'bg-[var(--status-warning)]'
                    : progress.status === 'success'
                    ? 'bg-[var(--status-success)]'
                    : 'bg-[var(--brand-primary)]'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, progress.value))}%` }}
              />
            </div>
          )}

          {/* Supporting description */}
          {description && (
            <div className="text-[11.5px] text-[var(--text-secondary)] mt-2 leading-relaxed break-words">
              {description}
            </div>
          )}
        </div>
      </div>

      {/* Optional footer / status row */}
      {footer && <div className="kpi-card__footer">{footer}</div>}
    </div>
  );
};
