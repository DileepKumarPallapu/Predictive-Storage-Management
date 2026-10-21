import React, { useState } from 'react';
import { User, Shield, Key, LogOut, CheckCircle, AlertCircle, X } from 'lucide-react';
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
      }, 1000);
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

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-obsidian-surface border border-obsidian-border rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-100">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-obsidian-border bg-obsidian-raised">
          <div className="flex items-center gap-2.5">
            <Shield size={18} className="text-obsidian-cyan" />
            <h3 className="text-sm font-bold text-obsidian-text">
              Role-Based Access Control & Identity
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-obsidian-muted hover:text-obsidian-text rounded"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {/* Active Session Status */}
          <div className="p-3 bg-obsidian-panel border border-obsidian-border rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-obsidian-cyan/15 border border-obsidian-cyan/30 flex items-center justify-center text-obsidian-cyan font-bold text-xs">
                {currentUser.username[0]?.toUpperCase() || 'U'}
              </div>
              <div>
                <div className="text-xs font-bold text-obsidian-text">
                  {currentUser.username}
                </div>
                <div className="text-[10px] text-obsidian-muted font-mono">
                  Role: <span className="text-obsidian-cyan">{currentUser.role}</span>
                </div>
              </div>
            </div>
            {currentUser.username !== 'anonymous' && (
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-2.5 py-1 bg-obsidian-coral/10 hover:bg-obsidian-coral/20 border border-obsidian-coral/30 text-obsidian-coral rounded text-[11px] font-medium transition-colors"
              >
                <LogOut size={12} />
                Logout
              </button>
            )}
          </div>

          {/* Quick Demo Credentials Info */}
          <div className="text-[11px] text-obsidian-muted bg-obsidian-secondary/60 p-2.5 rounded border border-obsidian-border/50">
            <div className="font-semibold text-obsidian-text mb-1">Pre-configured Demo Credentials:</div>
            <div className="font-mono text-[10px] space-y-0.5">
              <div>Administrator: <span className="text-obsidian-cyan">admin</span> / <span className="text-obsidian-text">admin123</span></div>
              <div>Operator: <span className="text-obsidian-cyan">operator</span> / <span className="text-obsidian-text">operator123</span></div>
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleLogin} className="space-y-3">
            <div>
              <label className="block text-[11px] font-medium text-obsidian-muted mb-1">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full bg-obsidian-panel border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text font-mono focus:border-obsidian-cyan focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-obsidian-muted mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-obsidian-panel border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text font-mono focus:border-obsidian-cyan focus:outline-none"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-obsidian-coral text-xs bg-obsidian-coral/10 p-2.5 rounded border border-obsidian-coral/30">
                <AlertCircle size={14} />
                <span>{error}</span>
              </div>
            )}

            {success && (
              <div className="flex items-center gap-2 text-obsidian-teal text-xs bg-obsidian-teal/10 p-2.5 rounded border border-obsidian-teal/30">
                <CheckCircle size={14} />
                <span>{success}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 flex items-center justify-center gap-2 px-4 py-2 bg-obsidian-cyan/15 hover:bg-obsidian-cyan/25 border border-obsidian-cyan/40 text-obsidian-cyan rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
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
