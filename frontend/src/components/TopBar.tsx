import React from 'react';
import {
  Shield,
  Sun,
  Moon,
  Radio,
  Bell,
  Search,
  User,
  Sparkles,
  BookOpen,
  SlidersHorizontal,
  Compass
} from 'lucide-react';
import { usePresentationMode } from '../context/PresentationModeContext';

interface TopBarProps {
  currentMode: string;
  onModeChange: (newMode: string) => void;
  isLightTheme: boolean;
  onToggleTheme: () => void;
  activeAlertsCount: number;
  onOpenAlerts: () => void;
  onOpenSearch: () => void;
  onOpenAuth: () => void;
  onOpenTour?: () => void;
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
  onOpenTour,
  currentUser,
}) => {
  const { mode, toggleMode, isGuided } = usePresentationMode();

  return (
    <header className="h-14 glass-panel-elevated border-b border-[var(--border-subtle)] px-4 sm:px-6 flex items-center justify-between text-xs select-none sticky top-0 z-20">
      {/* Left: Mode Status & Guided/Expert Toggle */}
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Operating Mode Dropdown */}
        <div className="flex items-center gap-2">
          <select
            value={currentMode}
            onChange={(e) => onModeChange(e.target.value)}
            className="bg-[var(--surface-secondary)] border border-[var(--border-normal)] text-[var(--text-primary)] text-xs rounded-lg px-2.5 py-1 focus:outline-none focus:border-[var(--accent-primary)] cursor-pointer transition-colors font-medium"
            aria-label="Operating Mode"
          >
            <option value="demo" className="bg-[var(--bg-secondary)]">Demo Mode (Synthetic Telemetry)</option>
            <option value="replay" className="bg-[var(--bg-secondary)]">Replay Mode (Chronological Traces)</option>
            <option value="live" className="bg-[var(--bg-secondary)]">Live Read-Only (Passive Host)</option>
          </select>
        </div>

        {/* Guided vs Expert Mode Switch */}
        <div className="hidden md:flex items-center glass-panel rounded-lg p-0.5 border border-[var(--border-subtle)]">
          <button
            type="button"
            onClick={() => toggleMode()}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
              isGuided
                ? 'bg-[var(--accent-primary)] text-[var(--bg-primary)] font-bold shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
            }`}
            title="Guided Mode: Simplified plain-language explanations"
          >
            <Sparkles size={12} />
            <span>Guided</span>
          </button>
          <button
            type="button"
            onClick={() => toggleMode()}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
              !isGuided
                ? 'bg-[var(--accent-secondary)] text-[var(--bg-primary)] font-bold shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
            }`}
            title="Expert Mode: Raw mathematical formulas and deep diagnostics"
          >
            <SlidersHorizontal size={12} />
            <span>Expert</span>
          </button>
        </div>
      </div>

      {/* Right: Quick Search, Guided Tour, Safety Badge, Alerts, Identity, Theme */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Quick Search Button */}
        <button
          onClick={onOpenSearch}
          className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-lg glass-panel hover:border-[var(--accent-primary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-all"
          title="Search storage pools and views (Ctrl+K)"
          aria-label="Search Commands"
        >
          <Search size={13} className="text-[var(--accent-primary)]" />
          <span className="text-[11px] font-medium">Search Commands</span>
          <kbd className="text-[9px] font-mono bg-[var(--surface-secondary)] px-1.5 py-0.5 rounded border border-[var(--border-subtle)] text-[var(--text-secondary)]">
            Ctrl+K
          </kbd>
        </button>

        {/* Interactive Tour Trigger */}
        {onOpenTour && (
          <button
            onClick={onOpenTour}
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg glass-panel hover:border-[var(--accent-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-[11px]"
            title="Open Interactive Guide"
          >
            <BookOpen size={13} className="text-[var(--accent-primary)]" />
            <span className="font-medium">Tour</span>
          </button>
        )}

        {/* Shadow Mode Safe Badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--status-success)]/15 border border-[var(--status-success)]/30 text-[var(--status-success)] text-[11px] font-mono font-semibold">
          <Shield size={12} className="text-[var(--status-success)]" />
          <span>SAFE SHADOW</span>
        </div>

        {/* Collector Status Pulse */}
        <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-full glass-panel border border-[var(--border-subtle)] text-[11px] font-mono text-[var(--text-secondary)]">
          <Radio size={12} className="text-[var(--status-success)] animate-pulse" />
          <span>SYNC ACTIVE</span>
        </div>

        {/* Alerts Pill */}
        <button
          onClick={onOpenAlerts}
          className="relative p-2 rounded-lg glass-panel hover:border-[var(--accent-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          title="View Incidents and Alerts"
          aria-label="Alerts"
        >
          <Bell size={14} />
          {activeAlertsCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[var(--status-critical)] text-[var(--bg-primary)] text-[9px] font-bold flex items-center justify-center shadow-sm">
              {activeAlertsCount}
            </span>
          )}
        </button>

        {/* User / RBAC Session Pill */}
        <button
          onClick={onOpenAuth}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg glass-panel hover:border-[var(--accent-primary)] text-[var(--text-primary)] transition-colors text-[11px] font-mono"
          title="Session & Role-Based Access Control"
        >
          <User size={13} className="text-[var(--accent-secondary)]" />
          <span className="font-bold hidden sm:inline">{currentUser.username}</span>
          <span className="text-[9px] px-1 py-0.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[var(--accent-primary)]">
            {currentUser.role}
          </span>
        </button>

        {/* Theme Toggle (Ember Noir / Porcelain Atelier) */}
        <button
          onClick={onToggleTheme}
          className="p-2 rounded-lg glass-panel hover:border-[var(--accent-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          title={isLightTheme ? 'Switch to Ember Noir Dark Theme' : 'Switch to Porcelain Atelier Light Theme'}
          aria-label="Toggle Theme"
        >
          {isLightTheme ? (
            <Moon size={14} className="text-[var(--accent-primary)]" />
          ) : (
            <Sun size={14} className="text-[var(--status-warning)]" />
          )}
        </button>
      </div>
    </header>
  );
};
