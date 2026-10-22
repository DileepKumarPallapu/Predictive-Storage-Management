import React from 'react';
import {
  Sun,
  Moon,
  Bell,
  Search,
  User,
  Sparkles,
  SlidersHorizontal,
  BookOpen,
  Radio,
  ChevronRight,
  Menu,
  Database
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
  currentPageLabel?: string;
  onToggleMobileMenu?: () => void;
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
  currentPageLabel = 'Executive Overview',
  onToggleMobileMenu,
}) => {
  const { toggleMode, isGuided } = usePresentationMode();

  return (
    <header className="h-16 bg-[var(--surface)] border-b border-[var(--border)] px-4 sm:px-6 flex items-center justify-between text-xs select-none sticky top-0 z-30 transition-colors gap-2">
      {/* LEFT: Mobile toggle & Workspace Breadcrumb Context */}
      <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
        {onToggleMobileMenu && (
          <button
            type="button"
            onClick={onToggleMobileMenu}
            className="lg:hidden p-1.5 rounded-md hover:bg-[var(--surface-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            title="Toggle Navigation Menu"
            aria-label="Toggle Navigation Menu"
          >
            <Menu size={18} />
          </button>
        )}

        {/* Operational Workspace Context (No duplicate logo) */}
        <div className="flex items-center gap-2 text-xs font-medium">
          <span className="text-[var(--text-muted)] font-mono text-[11px] hidden md:inline">Storage Operations</span>
          <ChevronRight size={13} className="text-[var(--text-muted)] hidden md:inline" />
          <span className="text-[var(--text-primary)] font-semibold text-xs whitespace-nowrap">
            {currentPageLabel}
          </span>
        </div>
      </div>

      {/* CENTER: Search Bar + Intelligently Grouped Data Source Environment */}
      <div className="hidden sm:flex items-center gap-2 shrink min-w-0 justify-center">
        {/* Universal Command Search (Desktop full bar) */}
        <button
          onClick={onOpenSearch}
          className="hidden 2xl:flex items-center gap-2.5 w-60 px-3 py-1.5 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] hover:border-[var(--border-visible)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-all shadow-xs group"
          title="Search storage pools, telemetry, actions (Ctrl+K)"
          aria-label="Global Search"
        >
          <Search size={14} className="text-[var(--text-muted)] group-hover:text-[var(--text-primary)]" />
          <span className="text-xs font-normal flex-1 text-left text-[var(--text-secondary)] truncate">Search pools, signals...</span>
          <kbd className="text-[10px] font-mono bg-[var(--surface)] px-1.5 py-0.5 rounded border border-[var(--border)] text-[var(--text-muted)] shrink-0">
            Ctrl K
          </kbd>
        </button>

        {/* Compact Search button on tablet / < 2xl */}
        <button
          onClick={onOpenSearch}
          className="2xl:hidden flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all text-xs shrink-0"
          title="Search (Ctrl+K)"
          aria-label="Search"
        >
          <Search size={14} />
          <span className="hidden xl:inline font-medium text-[11px]">Search</span>
        </button>

        {/* Grouped Data Source Environment */}
        <div className="flex items-center bg-[var(--surface-elevated)] rounded-lg p-0.5 border border-[var(--border)] shrink-0">
          <div className="hidden xl:flex items-center gap-1.5 px-2 py-1 text-[11px] font-medium text-[var(--text-secondary)] border-r border-[var(--border)]">
            <Database size={12} className="text-[var(--accent)]" />
            <span className="text-[var(--text-muted)]">Source:</span>
          </div>
          <select
            value={currentMode}
            onChange={(e) => onModeChange(e.target.value)}
            className="bg-transparent border-0 text-[var(--text-primary)] text-xs font-medium px-2 py-1 focus:outline-none cursor-pointer max-w-[130px] sm:max-w-none truncate"
            aria-label="Select Operating Data Mode"
          >
            <option value="demo">Synthetic Demo</option>
            <option value="replay">Benchmark Traces</option>
            <option value="live">Passive Host (C:\)</option>
          </select>
        </div>
      </div>

      {/* RIGHT: Mode Switcher, Status, Notifications, Account, Theme */}
      <div className="flex items-center gap-1 sm:gap-2.5 shrink-0">
        {/* Guided vs Expert Segmented Control */}
        <div className="flex items-center bg-[var(--surface-elevated)] rounded-lg p-0.5 border border-[var(--border)]">
          <button
            type="button"
            onClick={() => toggleMode()}
            className={`flex items-center gap-1 sm:gap-1.5 px-1.5 sm:px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
              isGuided
                ? 'bg-[var(--surface)] text-[var(--accent)] font-semibold shadow-sm border border-[var(--border)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
            }`}
            title="Guided Mode: Clear operational narratives for storage administrators"
          >
            <Sparkles size={11} className={isGuided ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'} />
            <span className="hidden sm:inline">Guided</span>
          </button>
          <button
            type="button"
            onClick={() => toggleMode()}
            className={`flex items-center gap-1 sm:gap-1.5 px-1.5 sm:px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
              !isGuided
                ? 'bg-[var(--surface)] text-[var(--text-primary)] font-semibold shadow-sm border border-[var(--border)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
            }`}
            title="Expert Mode: Machine learning loss functions, quantiles, and raw telemetry parameters"
          >
            <SlidersHorizontal size={11} />
            <span className="hidden sm:inline">Expert</span>
          </button>
        </div>

        {/* Real Synchronized Provenance Indicator (Strictly accurate) */}
        <div
          className={`hidden xl:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono border ${
            currentMode === 'live'
              ? 'bg-[var(--success)]/10 text-[var(--success)] border-[var(--success)]/30'
              : currentMode === 'replay'
              ? 'bg-[var(--warning)]/10 text-[var(--warning)] border-[var(--warning)]/30'
              : 'bg-[var(--surface-elevated)] text-[var(--text-muted)] border-[var(--border)]'
          }`}
          title={
            currentMode === 'live'
              ? 'Connected to real host operating system storage metrics'
              : currentMode === 'replay'
              ? 'Replaying chronological storage benchmark traces'
              : 'Synthesized multi-tier storage telemetry with diurnal variance'
          }
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              currentMode === 'live'
                ? 'bg-[var(--success)] animate-pulse'
                : currentMode === 'replay'
                ? 'bg-[var(--warning)]'
                : 'bg-[var(--text-muted)]'
            }`}
          />
          <span className="font-medium">
            {currentMode === 'live'
              ? 'Live Host Synced'
              : currentMode === 'replay'
              ? 'Trace Replay'
              : 'Synthetic Demo'}
          </span>
        </div>

        {/* Tour / Guide Button */}
        {onOpenTour && (
          <button
            onClick={onOpenTour}
            className="hidden sm:flex p-1.5 rounded-lg hover:bg-[var(--surface-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            title="Platform Orientation Tour"
            aria-label="Platform Tour"
          >
            <BookOpen size={15} />
          </button>
        )}

        {/* Notifications / Alerts Pill */}
        <button
          onClick={onOpenAlerts}
          className="relative p-1.5 rounded-lg hover:bg-[var(--surface-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          title="Active Alerts and SLA Incidents"
          aria-label="Active Alerts"
        >
          <Bell size={16} />
          {activeAlertsCount > 0 && (
            <span className="absolute top-0 right-0 min-w-[15px] h-[15px] px-1 rounded-full bg-[var(--critical)] text-white text-[9px] font-bold flex items-center justify-center font-mono">
              {activeAlertsCount}
            </span>
          )}
        </button>

        {/* User Account / RBAC Pill */}
        <button
          onClick={onOpenAuth}
          className="flex items-center gap-1.5 sm:gap-2 px-1.5 sm:pl-2 sm:pr-2.5 py-1 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] hover:border-[var(--border-visible)] text-[var(--text-primary)] transition-colors text-xs"
          title="Session & Role-Based Access Control"
        >
          <div className="w-5 h-5 rounded-full bg-[var(--surface-subtle)] text-[var(--text-primary)] font-bold text-[10px] flex items-center justify-center border border-[var(--border)]">
            {currentUser.username[0]?.toUpperCase() || 'A'}
          </div>
          <span className="font-medium hidden sm:inline">{currentUser.username}</span>
          <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-[var(--surface)] text-[var(--text-muted)] border border-[var(--border)] hidden sm:inline">
            {currentUser.role}
          </span>
        </button>

        {/* Light / Dark Theme Toggle Button */}
        <button
          onClick={onToggleTheme}
          className="p-1.5 rounded-lg hover:bg-[var(--surface-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          title={isLightTheme ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
          aria-label="Toggle Color Theme"
        >
          {isLightTheme ? (
            <Moon size={16} className="text-[var(--text-secondary)]" />
          ) : (
            <Sun size={16} className="text-[var(--warning)]" />
          )}
        </button>
      </div>
    </header>
  );
};
