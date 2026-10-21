import React, { useState } from 'react';
import { Shield, Key, LogOut, CheckCircle2, AlertCircle, X, Sparkles, UserCheck } from 'lucide-react';
import { api } from '../api/client';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: {
    username: string;
    role: string;
    email?: string;
  };
  onAuthSuccess: (username: string, role: string) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onAuthSuccess,
}) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await api.login(username, password);
      setSuccess(`Authenticated successfully as ${res.username} (${res.role})`);
      onAuthSuccess(res.username, res.role);
      setTimeout(() => {
        onClose();
      }, 900);
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    api.logout();
    onAuthSuccess('anonymous', 'GUEST');
    onClose();
  };

  const setDemoRole = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4">
      <div className="glass-modal w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150 shadow-glass-modal">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)]/40">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent-cyan)]/15 border border-[var(--accent-cyan)]/30 flex items-center justify-center text-[var(--accent-cyan)]">
              <Shield size={18} />
            </div>
            <div>
              <h3 className="text-sm font-semibold tracking-wide text-[var(--text-primary)]">
                Access Control & Identity
              </h3>
              <p className="text-[11px] text-[var(--text-tertiary)] font-mono">
                Cryptographic RBAC Token Session
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] rounded-lg transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Active Session Status */}
          <div className="p-3.5 glass-panel rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-[var(--accent-cyan)]/30 to-[var(--accent-violet)]/30 border border-[var(--accent-cyan)]/40 flex items-center justify-center text-[var(--accent-cyan)] font-bold text-xs shadow-inner">
                {currentUser.username[0]?.toUpperCase() || 'U'}
              </div>
              <div>
                <div className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                  {currentUser.username}
                  {currentUser.username !== 'anonymous' && (
                    <UserCheck size={13} className="text-[var(--color-success)]" />
                  )}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] font-mono flex items-center gap-1">
                  Role: <span className="text-[var(--accent-cyan)] font-semibold">{currentUser.role}</span>
                </div>
              </div>
            </div>
            {currentUser.username !== 'anonymous' && (
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--color-critical)]/12 hover:bg-[var(--color-critical)]/22 border border-[var(--color-critical)]/30 text-[var(--color-critical)] rounded-lg text-[11px] font-medium transition-colors"
              >
                <LogOut size={12} />
                Logout
              </button>
            )}
          </div>

          {/* Quick Demo Credentials Info & Fill Buttons */}
          <div className="text-xs text-[var(--text-secondary)] bg-[var(--surface-raised)]/50 p-3.5 rounded-xl border border-[var(--border-subtle)] space-y-2">
            <div className="font-medium text-[var(--text-primary)] flex items-center gap-1.5 text-[11px] uppercase tracking-wider">
              <Sparkles size={13} className="text-[var(--accent-cyan)]" /> Quick Role Presets:
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setDemoRole('admin', 'admin123')}
                className={`flex-1 px-2.5 py-1.5 rounded-lg border text-[11px] font-mono transition-colors text-center ${
                  username === 'admin'
                    ? 'border-[var(--accent-cyan)]/60 bg-[var(--accent-cyan)]/15 text-[var(--accent-cyan)] font-semibold'
                    : 'border-[var(--border-subtle)] bg-[var(--surface-panel)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Admin (Full Access)
              </button>
              <button
                type="button"
                onClick={() => setDemoRole('operator', 'operator123')}
                className={`flex-1 px-2.5 py-1.5 rounded-lg border text-[11px] font-mono transition-colors text-center ${
                  username === 'operator'
                    ? 'border-[var(--accent-cyan)]/60 bg-[var(--accent-cyan)]/15 text-[var(--accent-cyan)] font-semibold'
                    : 'border-[var(--border-subtle)] bg-[var(--surface-panel)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Operator (Standard)
              </button>
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1.5 uppercase tracking-wider">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full bg-[var(--surface-panel)] border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3.5 py-2 text-xs text-[var(--text-primary)] font-mono focus:outline-none transition-colors"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-[var(--text-secondary)] mb-1.5 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-[var(--surface-panel)] border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3.5 py-2 text-xs text-[var(--text-primary)] font-mono focus:outline-none transition-colors"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-[var(--color-critical)] text-xs bg-[var(--color-critical)]/10 p-3 rounded-lg border border-[var(--color-critical)]/30 animate-in fade-in">
                <AlertCircle size={15} />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="flex items-center gap-2 text-[var(--color-success)] text-xs bg-[var(--color-success)]/10 p-3 rounded-lg border border-[var(--color-success)]/30 animate-in fade-in">
                <CheckCircle2 size={15} />
                <span>{success}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 btn-aurora-primary flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold disabled:opacity-50"
            >
              <Key size={14} />
              {loading ? 'Authenticating...' : 'Sign In with JWT'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
