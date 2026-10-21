import React from 'react';
import { Shield, Sun, Moon, Database, Radio, Bell, Search, User } from 'lucide-react';

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
    <header className="h-14 bg-obsidian-secondary border-b border-obsidian-border px-6 flex items-center justify-between text-xs select-none">
      {/* Left: Academic Title and Mode Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded bg-obsidian-panel border border-obsidian-border text-obsidian-cyan font-semibold">
            {currentMode.toUpperCase()} MODE
          </span>
          <span className="hidden xl:inline text-obsidian-muted text-[11px] italic">
            Predictive Storage Capacity and Performance Management Using ML
          </span>
        </div>

        {/* Operating Mode Dropdown */}
        <select
          value={currentMode}
          onChange={(e) => onModeChange(e.target.value)}
          className="bg-obsidian-panel border border-obsidian-border text-obsidian-text text-xs rounded px-2.5 py-1 focus:outline-none focus:border-obsidian-cyan cursor-pointer"
        >
          <option value="demo">Demo Mode (Synthetic Telemetry)</option>
          <option value="replay">Replay Mode (Chronological Traces)</option>
          <option value="live">Live Read-Only Mode (Host Partition)</option>
        </select>
      </div>

      {/* Right: Search, Security, Collector Health, Alerts, User, Theme */}
      <div className="flex items-center gap-3">
        {/* Quick Search Shortcut */}
        <button
          onClick={onOpenSearch}
          className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded bg-obsidian-panel border border-obsidian-border text-obsidian-muted hover:text-obsidian-text hover:border-obsidian-cyan transition-colors"
          title="Search pools and pages (Ctrl+K)"
        >
          <Search size={13} className="text-obsidian-cyan" />
          <span className="text-[11px]">Quick Search</span>
          <kbd className="text-[9px] font-mono bg-obsidian-secondary px-1.5 py-0.5 rounded border border-obsidian-border">
            Ctrl+K
          </kbd>
        </button>

        {/* Shadow Mode Badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-obsidian-teal/10 border border-obsidian-teal/30 text-obsidian-teal text-[11px] font-mono">
          <Shield size={13} />
          <span>SHADOW MODE: SAFE</span>
        </div>

        {/* Collector Status Pulse */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-obsidian-panel border border-obsidian-border text-[11px] font-mono text-obsidian-muted">
          <Radio size={13} className="text-obsidian-teal animate-pulse" />
          <span>COLLECTOR: ACTIVE</span>
        </div>

        {/* Alerts Pill */}
        <button
          onClick={onOpenAlerts}
          className="relative p-1.5 rounded bg-obsidian-panel border border-obsidian-border text-obsidian-muted hover:text-obsidian-text hover:border-obsidian-cyan transition-colors"
          title="View Incidents and Alerts"
        >
          <Bell size={15} />
          {activeAlertsCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-obsidian-coral text-white text-[9px] font-bold flex items-center justify-center">
              {activeAlertsCount}
            </span>
          )}
        </button>

        {/* User / RBAC Session Pill */}
        <button
          onClick={onOpenAuth}
          className="flex items-center gap-1.5 px-2 py-1 rounded bg-obsidian-panel border border-obsidian-border text-obsidian-text hover:border-obsidian-cyan transition-colors text-[11px] font-mono"
          title="Manage Session & Roles"
        >
          <User size={13} className="text-obsidian-cyan" />
          <span className="font-semibold">{currentUser.username}</span>
          <span className="text-[9px] px-1 py-0.2 rounded bg-obsidian-secondary text-obsidian-muted">
            {currentUser.role}
          </span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={onToggleTheme}
          className="p-1.5 rounded bg-obsidian-panel border border-obsidian-border text-obsidian-muted hover:text-obsidian-text hover:border-obsidian-cyan transition-colors"
          title={isLightTheme ? "Switch to Dark Mode (Obsidian Aurora)" : "Switch to Light Mode"}
        >
          {isLightTheme ? <Moon size={15} /> : <Sun size={15} />}
        </button>
      </div>
    </header>
  );
};
