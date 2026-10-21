import React from 'react';
import { Shield, Sun, Moon, Database, Radio, Bell } from 'lucide-react';

interface TopBarProps {
  currentMode: string;
  onModeChange: (newMode: string) => void;
  isLightTheme: boolean;
  onToggleTheme: () => void;
  activeAlertsCount: number;
  onOpenAlerts: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  currentMode,
  onModeChange,
  isLightTheme,
  onToggleTheme,
  activeAlertsCount,
  onOpenAlerts,
}) => {
  return (
    <header className="h-14 bg-obsidian-secondary border-b border-obsidian-border px-6 flex items-center justify-between text-xs select-none">
      {/* Left: Academic Title and Mode Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded bg-obsidian-panel border border-obsidian-border text-obsidian-cyan font-semibold">
            {currentMode.toUpperCase()} MODE
          </span>
          <span className="hidden lg:inline text-obsidian-muted text-[11px] italic">
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

      {/* Right: Security, Collector Health, Alerts, Theme */}
      <div className="flex items-center gap-3">
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
