import React, { useEffect, useState } from 'react';
import {
  Shield, UserCheck, AlertCircle, CheckCircle2, X, LogOut,
  KeyRound, MonitorSmartphone, History
} from 'lucide-react';
import { api } from '../api/client';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: {
    username: string;
    role: string;
    email?: string;
  };
  onLogoutSuccess: () => Promise<void>;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onLogoutSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<'profile' | 'password' | 'sessions'>('profile');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [sessions, setSessions] = useState<any[]>([]);
  const [loginHistory, setLoginHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadSessionsAndHistory = async () => {
    try {
      const [sessRes, histRes] = await Promise.all([
        api.listSessions(),
        api.getLoginHistory(),
      ]);
      setSessions(sessRes.sessions || []);
      setLoginHistory((histRes as any).login_history || (histRes as any).attempts || []);
    } catch (err: any) {
      setError(err?.message || 'Unable to load session history');
    }
  };

  useEffect(() => {
    if (isOpen && activeTab === 'sessions') {
      loadSessionsAndHistory();
    }
  }, [isOpen, activeTab]);

  if (!isOpen) return null;

  const handleLogout = async () => {
    await onLogoutSuccess();
    onClose();
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setError('New passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.changePassword(currentPassword, newPassword);
      setSuccess(res.message || 'Password updated. All other sessions were revoked.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
    } catch (err: any) {
      setError(err?.message || 'Unable to change password.');
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    setError(null);
    setSuccess(null);
    try {
      await api.revokeSession(sessionId);
      setSuccess('Session revoked.');
      await loadSessionsAndHistory();
    } catch (err: any) {
      setError(err?.message || 'Unable to revoke session.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="glass-modal w-full max-w-lg overflow-hidden border border-[var(--border-strong)] rounded-2xl bg-[var(--surface-primary)] shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-subtle)] bg-[var(--surface-secondary)]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)]/15 border border-[var(--accent)]/30 flex items-center justify-center text-[var(--accent)]">
              <Shield size={18} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Account & Session Security
              </h3>
              <p className="text-[11px] text-[var(--text-muted)] font-mono">
                {currentUser.username} · {currentUser.role}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded-lg"
          >
            <X size={16} />
          </button>
        </div>

        {/* Sub-nav */}
        <div className="flex border-b border-[var(--border-subtle)] px-6 gap-4 text-xs">
          <button
            type="button"
            onClick={() => { setActiveTab('profile'); setError(null); setSuccess(null); }}
            className={`py-2.5 font-semibold border-b-2 ${
              activeTab === 'profile'
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-transparent text-[var(--text-secondary)]'
            }`}
          >
            Active Profile
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('password'); setError(null); setSuccess(null); }}
            className={`py-2.5 font-semibold border-b-2 inline-flex items-center gap-1 ${
              activeTab === 'password'
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-transparent text-[var(--text-secondary)]'
            }`}
          >
            <KeyRound size={12} /> Change Password
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab('sessions'); setError(null); setSuccess(null); }}
            className={`py-2.5 font-semibold border-b-2 inline-flex items-center gap-1 ${
              activeTab === 'sessions'
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-transparent text-[var(--text-secondary)]'
            }`}
          >
            <MonitorSmartphone size={12} /> Sessions & History
          </button>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-[var(--status-critical)]/10 border border-[var(--status-critical)]/30 text-xs text-[var(--status-critical)]">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-[var(--status-success)]/10 border border-[var(--status-success)]/30 text-xs text-[var(--status-success)]">
              <CheckCircle2 size={15} className="shrink-0 mt-0.5" />
              <span>{success}</span>
            </div>
          )}

          {activeTab === 'profile' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-secondary)] flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[var(--accent)]/15 border border-[var(--accent)]/30 flex items-center justify-center text-[var(--accent)] font-bold text-sm">
                    {currentUser.username[0]?.toUpperCase() || 'U'}
                  </div>
                  <div>
                    <div className="text-xs font-semibold flex items-center gap-1.5">
                      {currentUser.username}
                      <UserCheck size={13} className="text-[var(--status-success)]" />
                    </div>
                    <div className="text-[11px] font-mono text-[var(--text-muted)]">
                      {currentUser.email || 'Verified Active Session'} · Role: {currentUser.role}
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--status-critical)]/12 border border-[var(--status-critical)]/30 text-[var(--status-critical)] text-xs font-semibold"
                >
                  <LogOut size={13} /> Sign Out
                </button>
              </div>
              <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                All actions performed under this account are verified server-side against database role permissions and recorded in the tamper-evident audit ledger.
              </p>
            </div>
          )}

          {activeTab === 'password' && (
            <form onSubmit={handleChangePassword} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-[var(--text-secondary)] mb-1">Current Password</label>
                <input
                  type="password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)]"
                />
              </div>
              <div>
                <label className="block font-medium text-[var(--text-secondary)] mb-1">New Password (min 8 characters)</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)]"
                />
              </div>
              <div>
                <label className="block font-medium text-[var(--text-secondary)] mb-1">Confirm New Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)]"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-[var(--accent)] text-white font-semibold disabled:opacity-50"
              >
                {loading ? 'Updating...' : 'Update Password'}
              </button>
            </form>
          )}

          {activeTab === 'sessions' && (
            <div className="space-y-4 max-h-80 overflow-y-auto pr-1 text-xs">
              <div>
                <div className="text-[11px] font-mono uppercase text-[var(--text-muted)] mb-2">
                  Active Server Sessions ({sessions.length})
                </div>
                <div className="space-y-1.5">
                  {sessions.map((s) => (
                    <div key={s.id} className="p-2.5 rounded-lg border border-[var(--border-subtle)] flex items-center justify-between gap-2">
                      <div className="font-mono text-[11px]">
                        <div>{s.client_ip || '127.0.0.1'} · {s.is_revoked ? 'REVOKED' : 'ACTIVE'}</div>
                        <div className="text-[10px] text-[var(--text-muted)]">
                          Expires: {s.expires_at ? new Date(s.expires_at).toLocaleString() : ''}
                        </div>
                      </div>
                      {!s.is_revoked && (
                        <button
                          type="button"
                          onClick={() => handleRevokeSession(s.id)}
                          className="px-2.5 py-1 rounded border border-[var(--status-critical)]/40 text-[var(--status-critical)] text-[11px]"
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  ))}
                  {sessions.length === 0 && <div className="text-[var(--text-muted)]">No active session records found.</div>}
                </div>
              </div>

              <div>
                <div className="text-[11px] font-mono uppercase text-[var(--text-muted)] mb-2 flex items-center gap-1">
                  <History size={12} /> Recent Sign-In History
                </div>
                <div className="space-y-1">
                  {loginHistory.slice(0, 8).map((a) => (
                    <div key={a.id} className="p-2 rounded bg-[var(--surface-secondary)]/50 flex items-center justify-between font-mono text-[11px]">
                      <span>{a.success ? 'SUCCESS' : `FAILED (${a.failure_reason})`}</span>
                      <span className="text-[10px] text-[var(--text-muted)]">
                        {a.attempted_at ? new Date(a.attempted_at).toLocaleString() : ''}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
