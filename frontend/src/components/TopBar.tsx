import React from 'react';
import { Shield, Sun, Moon, Radio, Bell, Search, User, Sparkles } from 'lucide-react';

interface TopBarProps {
  currentMode: string;
  onModeChange: (newMode: string) => void;
  isLightTheme: boolean;
  onToggleTheme: () => void;
  activeAlertsCount: number;
  onOpenAlerts: () => void;
  onOpenSearch: () => void;
  onOpenAuth: () => void;
  currentUser: {
    username: string;
    role: string;
  };
}

export const TopBar: React.FC<TopBarProps> = ({
  currentMode,
  onModeChange,
  isLightTheme,
  onToggleTheme,
  activeAlertsCount,
  onOpenAlerts,
  onOpenSearch,
  onOpenAuth,
  currentUser,
}) => {
  return (
    <header className="h-14 glass-panel border-b border-aurora-borderSubtle px-6 flex items-center justify-between text-xs select-none sticky top-0 z-20 backdrop-blur-glass">
      {/* Left: Mode Status & Academic Title */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono uppercase px-2.5 py-0.5 rounded-full bg-aurora-cyan/15 border border-aurora-cyan/40 text-aurora-cyan font-bold tracking-wider shadow-sm">
            {currentMode.toUpperCase()} MODE
          </span>
          <span className="hidden xl:inline text-aurora-textMuted text-[11px] font-medium tracking-tight">
            Predictive Storage Capacity and Performance Management Using ML
          </span>
        </div>

        {/* Operating Mode Dropdown */}
        <select
          value={currentMode}
          onChange={(e) => onModeChange(e.target.value)}
          className="glass-panel border border-aurora-borderSubtle text-aurora-textPrimary text-xs rounded-lg px-2.5 py-1 focus:outline-none focus:border-aurora-cyan cursor-pointer transition-colors"
        >
          <option value="demo">Demo Mode (Synthetic Telemetry)</option>
          <option value="replay">Replay Mode (Chronological Traces)</option>
          <option value="live">Live Read-Only Mode (Host Partition)</option>
        </select>
      </div>

      {/* Right: Quick Search, Safety Badge, Collector Status, Alerts, Identity, Theme */}
      <div className="flex items-center gap-3">
        {/* Quick Search Button */}
        <button
          onClick={onOpenSearch}
          className="hidden md:flex items-center gap-2 px-3 py-1 rounded-lg glass-panel hover:border-aurora-cyan text-aurora-textMuted hover:text-aurora-textPrimary transition-all"
          title="Search storage pools and pages (Ctrl+K)"
        >
          <Search size={13} className="text-aurora-cyan" />
          <span className="text-[11px] font-medium">Search Commands</span>
          <kbd className="text-[9px] font-mono bg-aurora-surfaceElevated px-1.5 py-0.5 rounded border border-aurora-borderSubtle text-aurora-textSecondary">
            Ctrl+K
          </kbd>
        </button>

        {/* Shadow Mode Safe Badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-[11px] font-mono font-semibold">
          <Shield size={12} className="text-emerald-400" />
          <span>SHADOW MODE</span>
        </div>

        {/* Collector Status Pulse */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full glass-panel border border-aurora-borderSubtle text-[11px] font-mono text-aurora-textSecondary">
          <Radio size={12} className="text-emerald-400 animate-pulse" />
          <span>COLLECTOR ACTIVE</span>
        </div>

        {/* Alerts Pill */}
        <button
          onClick={onOpenAlerts}
          className="relative p-2 rounded-lg glass-panel hover:border-aurora-cyan text-aurora-textSecondary hover:text-aurora-textPrimary transition-colors"
          title="View Incidents and Alerts"
        >
          <Bell size={14} />
          {activeAlertsCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-aurora-danger text-white text-[9px] font-bold flex items-center justify-center shadow-sm">
              {activeAlertsCount}
            </span>
          )}
        </button>

        {/* User / RBAC Session Pill */}
        <button
          onClick={onOpenAuth}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg glass-panel hover:border-aurora-cyan text-aurora-textPrimary transition-colors text-[11px] font-mono"
          title="Session & Access Control"
        >
          <User size={13} className="text-aurora-violet" />
          <span className="font-bold">{currentUser.username}</span>
          <span className="text-[9px] px-1 py-0.2 rounded bg-aurora-surfaceSecondary border border-aurora-borderSubtle text-aurora-cyan">
            {currentUser.role}
          </span>
        </button>

        {/* Theme Toggle (Dark / Light) */}
        <button
          onClick={onToggleTheme}
          className="p-2 rounded-lg glass-panel hover:border-aurora-cyan text-aurora-textSecondary hover:text-aurora-textPrimary transition-colors"
          title={isLightTheme ? 'Switch to Aurora Dark Theme' : 'Switch to Pearl Glass Light Theme'}
        >
          {isLightTheme ? <Moon size={14} className="text-aurora-violet" /> : <Sun size={14} className="text-aurora-warning" />}
        </button>
      </div>
    </header>
  );
};
