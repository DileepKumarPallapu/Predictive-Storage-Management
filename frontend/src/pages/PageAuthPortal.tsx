import React, { useEffect, useState } from 'react';
import {
  ShieldCheck, Lock, Mail, User as UserIcon, KeyRound,
  AlertCircle, CheckCircle2, Eye, EyeOff, ArrowLeft, Activity
} from 'lucide-react';
import { api } from '../api/client';

export type AuthPortalMode = 'login' | 'forgot-password' | 'reset-password' | 'setup';

interface PageAuthPortalProps {
  mode: AuthPortalMode;
  onNavigateMode: (mode: AuthPortalMode) => void;
  onAuthenticated: () => Promise<void>;
  setupRequired: boolean;
  onSetupComplete: () => void;
}

export const PageAuthPortal: React.FC<PageAuthPortalProps> = ({
  mode,
  onNavigateMode,
  onAuthenticated,
  setupRequired,
  onSetupComplete,
}) => {
  // Login state
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Setup state
  const [setupUsername, setSetupUsername] = useState('');
  const [setupEmail, setSetupEmail] = useState('');
  const [setupPassword, setSetupPassword] = useState('');
  const [setupConfirm, setSetupConfirm] = useState('');

  // Forgot / Reset password state
  const [forgotIdentifier, setForgotIdentifier] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [infoMsg, setInfoMsg] = useState<string | null>(null);
  const [issuedResetToken, setIssuedResetToken] = useState<string | null>(null);

  useEffect(() => {
    setErrorMsg(null);
    if (setupRequired && mode !== 'setup') {
      onNavigateMode('setup');
    }
  }, [mode, setupRequired, onNavigateMode]);

  const activeMode: AuthPortalMode = setupRequired ? 'setup' : mode;

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setInfoMsg(null);
    if (!identifier.trim() || !password) {
      setErrorMsg('Enter your username or email address and password.');
      return;
    }
    setLoading(true);
    try {
      await api.login(identifier.trim(), password);
      await onAuthenticated();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Sign-in failed. Verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSetupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setInfoMsg(null);
    if (!setupUsername.trim() || !setupEmail.trim()) {
      setErrorMsg('Administrator username and email are required.');
      return;
    }
    if (setupPassword.length < 8) {
      setErrorMsg('Administrator password must be at least 8 characters.');
      return;
    }
    if (setupPassword !== setupConfirm) {
      setErrorMsg('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await api.setupFirstAdmin({
        username: setupUsername.trim(),
        email: setupEmail.trim(),
        password: setupPassword,
      });
      setInfoMsg('Initial Administrator created. Sign in with your new credentials.');
      onSetupComplete();
      setIdentifier(setupUsername.trim());
      setPassword('');
      onNavigateMode('login');
    } catch (err: any) {
      setErrorMsg(err?.message || 'Administrator setup failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setInfoMsg(null);
    setIssuedResetToken(null);
    if (!forgotIdentifier.trim()) {
      setErrorMsg('Enter your account username or email address.');
      return;
    }
    setLoading(true);
    try {
      const res: any = await api.forgotPassword(forgotIdentifier.trim());
      setInfoMsg(res.message);
      const tok = res.reset_token || res.reset_token_dev;
      if (tok) {
        setIssuedResetToken(tok);
        setResetToken(tok);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Unable to initiate password reset.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setInfoMsg(null);
    if (!resetToken.trim()) {
      setErrorMsg('A single-use reset token is required.');
      return;
    }
    if (newPassword.length < 8) {
      setErrorMsg('New password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setErrorMsg('New passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.resetPassword(resetToken.trim(), newPassword);
      setInfoMsg(res.message || 'Password updated cleanly. Sign in below.');
      setResetToken('');
      setNewPassword('');
      setConfirmNewPassword('');
      setIssuedResetToken(null);
      onNavigateMode('login');
    } catch (err: any) {
      setErrorMsg(err?.message || 'Password reset failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-canvas)] text-[var(--text-primary)] p-4 sm:p-6">
      <div className="w-full max-w-md space-y-5">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-[var(--accent)]/12 border border-[var(--accent)]/30 flex items-center justify-center text-[var(--accent)] shadow-sm">
            <ShieldCheck size={26} />
          </div>
          <div>
            <div className="text-xl font-bold tracking-tight">AEGISSTOR</div>
            <div className="text-xs text-[var(--text-muted)] font-mono uppercase tracking-wider">
              Storage Resilience Intelligence Platform
            </div>
          </div>
        </div>

        {/* Main Card */}
        <div className="titan-card rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-primary)] p-6 sm:p-7 shadow-lg space-y-5">
          {activeMode === 'setup' && (
            <>
              <div className="space-y-1">
                <span className="inline-flex items-center gap-1.5 text-[11px] font-mono font-semibold uppercase tracking-wider text-[var(--accent)]">
                  <Activity size={13} /> First-Run Bootstrap
                </span>
                <h1 className="text-lg font-bold">Initialize Administrator Account</h1>
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  No active Administrator account exists yet. Create the initial Administrator to unlock AEGISSTOR and provision Operator and Viewer accounts.
                </p>
              </div>
            </>
          )}

          {activeMode === 'login' && (
            <div className="space-y-1">
              <h1 className="text-lg font-bold">Sign in to AEGISSTOR</h1>
              <p className="text-xs text-[var(--text-secondary)]">
                Authenticate with your assigned Administrator, Operator, or Viewer credentials.
              </p>
            </div>
          )}

          {activeMode === 'forgot-password' && (
            <div className="space-y-1">
              <h1 className="text-lg font-bold">Recover Account Access</h1>
              <p className="text-xs text-[var(--text-secondary)]">
                Request a time-limited single-use password reset token for your account.
              </p>
            </div>
          )}

          {activeMode === 'reset-password' && (
            <div className="space-y-1">
              <h1 className="text-lg font-bold">Set New Password</h1>
              <p className="text-xs text-[var(--text-secondary)]">
                Enter your reset token and choose a new password (all existing sessions will be revoked).
              </p>
            </div>
          )}

          {errorMsg && (
            <div
              role="alert"
              className="flex items-start gap-2.5 p-3 rounded-lg bg-[var(--status-critical)]/10 border border-[var(--status-critical)]/30 text-xs text-[var(--status-critical)]"
            >
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {infoMsg && (
            <div
              role="status"
              className="flex items-start gap-2.5 p-3 rounded-lg bg-[var(--status-success)]/10 border border-[var(--status-success)]/30 text-xs text-[var(--status-success)]"
            >
              <CheckCircle2 size={16} className="shrink-0 mt-0.5" />
              <div className="space-y-1.5">
                <div>{infoMsg}</div>
                {issuedResetToken && (
                  <div className="p-2 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono break-all">
                    <div className="text-[10px] text-[var(--text-muted)] uppercase mb-1">Single-Use Reset Token</div>
                    <div>{issuedResetToken}</div>
                    <button
                      type="button"
                      onClick={() => onNavigateMode('reset-password')}
                      className="mt-2 px-2.5 py-1 rounded bg-[var(--accent)] text-white text-[11px] font-sans font-semibold"
                    >
                      Proceed to Reset Password
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* SETUP FORM */}
          {activeMode === 'setup' && (
            <form onSubmit={handleSetupSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Administrator Username
                </label>
                <div className="relative">
                  <UserIcon size={15} className="absolute left-3 top-2.5 text-[var(--text-muted)]" />
                  <input
                    type="text"
                    required
                    minLength={3}
                    value={setupUsername}
                    onChange={(e) => setSetupUsername(e.target.value)}
                    placeholder="e.g. sysadmin"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Administrator Email
                </label>
                <div className="relative">
                  <Mail size={15} className="absolute left-3 top-2.5 text-[var(--text-muted)]" />
                  <input
                    type="email"
                    required
                    value={setupEmail}
                    onChange={(e) => setSetupEmail(e.target.value)}
                    placeholder="admin@company.com"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Password (min 8 characters)
                </label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-2.5 text-[var(--text-muted)]" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={setupPassword}
                    onChange={(e) => setSetupPassword(e.target.value)}
                    placeholder="Strong unique password"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-2.5 text-[var(--text-muted)]" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={setupConfirm}
                    onChange={(e) => setSetupConfirm(e.target.value)}
                    placeholder="Repeat password"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-[var(--accent)] hover:opacity-95 text-white text-xs font-semibold disabled:opacity-50"
              >
                {loading ? 'Creating Administrator...' : 'Create Initial Administrator'}
              </button>
            </form>
          )}

          {/* LOGIN FORM */}
          {activeMode === 'login' && (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label htmlFor="login-identifier" className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Username or Email
                </label>
                <div className="relative">
                  <UserIcon size={15} className="absolute left-3 top-2.5 text-[var(--text-muted)]" />
                  <input
                    id="login-identifier"
                    type="text"
                    required
                    autoComplete="username"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="operator@company.com or username"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label htmlFor="login-password" className="block text-xs font-medium text-[var(--text-secondary)]">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => onNavigateMode('forgot-password')}
                    className="text-[11px] font-medium text-[var(--accent)] hover:underline"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-2.5 text-[var(--text-muted)]" />
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    className="w-full pl-9 pr-9 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                  />
                  <button
                    type="button"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-2.5 top-2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-[var(--accent)] hover:opacity-95 text-white text-xs font-semibold disabled:opacity-50"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>
          )}

          {/* FORGOT PASSWORD FORM */}
          {activeMode === 'forgot-password' && (
            <form onSubmit={handleForgotSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Username or Registered Email
                </label>
                <div className="relative">
                  <Mail size={15} className="absolute left-3 top-2.5 text-[var(--text-muted)]" />
                  <input
                    type="text"
                    required
                    value={forgotIdentifier}
                    onChange={(e) => setForgotIdentifier(e.target.value)}
                    placeholder="username or email"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-[var(--accent)] hover:opacity-95 text-white text-xs font-semibold disabled:opacity-50"
              >
                {loading ? 'Issuing Reset Token...' : 'Request Reset Token'}
              </button>
              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={() => onNavigateMode('login')}
                  className="inline-flex items-center gap-1 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  <ArrowLeft size={13} /> Back to Sign In
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateMode('reset-password')}
                  className="text-xs text-[var(--accent)] hover:underline"
                >
                  Have a token?
                </button>
              </div>
            </form>
          )}

          {/* RESET PASSWORD FORM */}
          {activeMode === 'reset-password' && (
            <form onSubmit={handleResetSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Reset Token
                </label>
                <div className="relative">
                  <KeyRound size={15} className="absolute left-3 top-2.5 text-[var(--text-muted)]" />
                  <input
                    type="text"
                    required
                    value={resetToken}
                    onChange={(e) => setResetToken(e.target.value)}
                    placeholder="Paste single-use reset token"
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)] font-mono"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  New Password (min 8 characters)
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[var(--border-strong)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-[var(--accent)] hover:opacity-95 text-white text-xs font-semibold disabled:opacity-50"
              >
                {loading ? 'Updating Password...' : 'Confirm Password Reset'}
              </button>
              <button
                type="button"
                onClick={() => onNavigateMode('login')}
                className="inline-flex items-center gap-1 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                <ArrowLeft size={13} /> Back to Sign In
              </button>
            </form>
          )}
        </div>

        <div className="text-center text-[11px] text-[var(--text-muted)] font-mono">
          Protected by Argon2id + Session Revocation + RBAC Permission Engine
        </div>
      </div>
    </div>
  );
};
