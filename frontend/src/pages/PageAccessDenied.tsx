import React from 'react';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

interface PageAccessDeniedProps {
  attemptedRoute: string;
  userRole: string;
  requiredPermission?: string;
  onReturnHome: () => void;
}

export const PageAccessDenied: React.FC<PageAccessDeniedProps> = ({
  attemptedRoute,
  userRole,
  requiredPermission,
  onReturnHome,
}) => {
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-6">
      <div className="titan-card max-w-lg w-full rounded-2xl border border-[var(--status-critical)]/30 bg-[var(--surface-primary)] p-7 text-center space-y-4">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-[var(--status-critical)]/10 text-[var(--status-critical)] flex items-center justify-center">
          <ShieldAlert size={28} />
        </div>
        <div className="space-y-1">
          <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--status-critical)] font-semibold">
            HTTP 403 · Access Denied
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)]">
            Insufficient Role Permissions
          </h2>
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
            Your active role (<span className="font-mono font-semibold text-[var(--text-primary)]">{userRole}</span>) is not authorized to access{' '}
            <span className="font-mono text-[var(--text-primary)]">{attemptedRoute}</span>
            {requiredPermission ? (
              <>
                {' '}(requires <span className="font-mono">{requiredPermission}</span>)
              </>
            ) : null}
            . This authorization boundary is also enforced server-side.
          </p>
        </div>
        <button
          type="button"
          onClick={onReturnHome}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-xs font-semibold hover:opacity-95"
        >
          <ArrowLeft size={14} /> Return to My Authorized Dashboard
        </button>
      </div>
    </div>
  );
};
