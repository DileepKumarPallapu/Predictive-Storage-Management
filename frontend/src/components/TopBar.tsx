import React, { useState } from 'react';
import {
  Sun,
  Moon,
  Bell,
  Search,
  SlidersHorizontal,
  BookOpen,
  ChevronRight,
  Menu,
  Database,
  Sparkles,
  Wifi,
  WifiOff,
  Users,
  CheckCheck,
} from 'lucide-react';
import { usePresentationMode } from '../context/PresentationModeContext';
import { useRealtime } from '../context/RealtimeContext';

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
  const {
    connectionStatus,
    lastUpdatedAt,
    notifications,
    unreadCount,
    onlineUsers,
    markNotificationRead,
    markAllNotificationsRead,
  } = useRealtime();
  const [notifOpen, setNotifOpen] = useState(false);
  const [presenceOpen, setPresenceOpen] = useState(false);

  return (
    <header className="h-16 bg-[var(--surface)] border-b border-[var(--border)] px-3 sm:px-4 lg:px-6 flex items-center justify-between text-xs select-none sticky top-0 z-30 transition-colors gap-2 min-w-0">
      {/* LEFT: Mobile toggle & Responsive Breadcrumb */}
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 min-w-0">
        {onToggleMobileMenu && (
          <button
            type="button"
            onClick={onToggleMobileMenu}
            className="lg:hidden p-1.5 rounded-lg hover:bg-[var(--surface-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors shrink-0"
            title="Toggle Navigation Menu"
            aria-label="Toggle Navigation Menu"
          >
            <Menu size={18} />
          </button>
        )}

        <div className="flex items-center gap-1.5 text-xs font-medium">
          <span className="text-[var(--text-muted)] font-mono text-[11px] hidden 2xl:inline shrink-0">
            Storage Operations
          </span>
          <ChevronRight size={13} className="text-[var(--text-muted)] hidden 2xl:inline shrink-0" />
          <span className="text-[var(--text-primary)] font-bold text-xs sm:text-[13px] truncate">
            {currentPageLabel}
          </span>
        </div>
      </div>

      {/* CENTER: Adaptive Search + Data Source Selector */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 shrink min-w-0 justify-center">
        {/* Full Search Bar on >= xl */}
        <button
          onClick={onOpenSearch}
          className="hidden xl:flex items-center gap-2 w-44 2xl:w-56 px-2.5 py-1.5 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] hover:border-[var(--border-strong)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-all shadow-2xs group shrink-0"
          title="Search storage pools, telemetry, actions (Ctrl+K)"
          aria-label="Global Search"
        >
          <Search size={13} className="text-[var(--text-muted)] group-hover:text-[var(--accent)] transition-colors shrink-0" />
          <span className="text-xs font-normal flex-1 text-left text-[var(--text-secondary)] truncate">Search pools, signals...</span>
          <kbd className="text-[9.5px] font-mono bg-[var(--surface)] px-1.5 py-0.5 rounded border border-[var(--border)] text-[var(--text-muted)] shrink-0">
            Ctrl K
          </kbd>
        </button>

        {/* Compact Search Icon on < xl and >= md */}
        <button
          onClick={onOpenSearch}
          className="xl:hidden hidden md:flex items-center p-1.5 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] hover:border-[var(--border-strong)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-all shrink-0"
          title="Search (Ctrl+K)"
          aria-label="Search"
        >
          <Search size={15} />
        </button>

        {/* Operating Data Mode Selector (Clean, comfortable, non-clipping) */}
        <div className="flex items-center bg-[var(--surface-elevated)] rounded-lg p-0.5 border border-[var(--border)] shrink-0 shadow-2xs">
          <div className="hidden sm:flex items-center gap-1 px-1.5 py-1 text-[11px] font-medium text-[var(--text-secondary)] border-r border-[var(--border)]">
            <Database size={12} className="text-[var(--accent)] shrink-0" />
            <span className="text-[var(--text-muted)] font-mono text-[10px]">SRC</span>
          </div>
          <select
            value={currentMode}
            onChange={(e) => onModeChange(e.target.value)}
            className="bg-transparent border-0 text-[var(--text-primary)] text-xs font-semibold px-2 py-1 focus:outline-none cursor-pointer min-w-[125px] sm:min-w-[135px]"
            aria-label="Select Operating Data Mode"
          >
            <option value="demo">Synthetic Demo</option>
            <option value="replay">Benchmark Traces</option>
            <option value="live">Passive Host (C:\)</option>
          </select>
        </div>
      </div>

      {/* RIGHT: Persona Switcher, Provenance Status, Notifications, Account, Theme */}
      <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
        {/* Guided vs Expert Segmented Control */}
        <div className="flex items-center bg-[var(--surface-elevated)] rounded-lg p-0.5 border border-[var(--border)] shrink-0 shadow-2xs">
          <button
            type="button"
            onClick={() => toggleMode()}
            className={`flex items-center gap-1 sm:gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
              isGuided
                ? 'bg-[var(--surface)] text-[var(--accent)] font-bold shadow-2xs border border-[var(--border)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
            }`}
            title="Guided Mode: Narrative summaries for storage administrators"
          >
            <Sparkles size={11} className={isGuided ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'} />
            <span className="hidden sm:inline">Guided</span>
          </button>
          <button
            type="button"
            onClick={() => toggleMode()}
            className={`flex items-center gap-1 sm:gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
              !isGuided
                ? 'bg-[var(--surface)] text-[var(--text-primary)] font-bold shadow-2xs border border-[var(--border)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
            }`}
            title="Expert Mode: Raw telemetry, loss curves, and quantile model parameters"
          >
            <SlidersHorizontal size={11} />
            <span className="hidden sm:inline">Expert</span>
          </button>
        </div>

        {/* Real Synchronized Provenance Indicator (Visible on 2XL wide views) */}
        <div
          className={`hidden 2xl:inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-mono border shrink-0 ${
            currentMode === 'live'
              ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border-[var(--status-success)]/30'
              : currentMode === 'replay'
              ? 'bg-[var(--status-warning)]/10 text-[var(--status-warning)] border-[var(--status-warning)]/30'
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
                ? 'bg-[var(--status-success)] animate-pulse'
                : currentMode === 'replay'
                ? 'bg-[var(--status-warning)]'
                : 'bg-[var(--text-muted)]'
            }`}
          />
          <span className="font-medium text-[10px]">
            {currentMode === 'live'
              ? 'Host Synced'
              : currentMode === 'replay'
              ? 'Trace Replay'
              : 'Synthetic Demo'}
          </span>
        </div>

        {/* Tour / Guide Button on large screens */}
        {onOpenTour && (
          <button
            onClick={onOpenTour}
            className="hidden xl:flex p-1.5 rounded-lg hover:bg-[var(--surface-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors shrink-0"
            title="Platform Orientation Tour"
            aria-label="Platform Tour"
          >
            <BookOpen size={15} />
          </button>
        )}

        {/* Live WebSocket Sync Badge */}
        <div
          className={`hidden md:inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-mono border shrink-0 ${
            connectionStatus === 'LIVE'
              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
              : connectionStatus === 'RECONNECTING'
              ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30'
              : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30'
          }`}
          title={
            lastUpdatedAt
              ? `WebSocket ${connectionStatus} · Last sync ${new Date(lastUpdatedAt).toLocaleTimeString()}`
              : `WebSocket ${connectionStatus}`
          }
          data-testid="realtime-status-badge"
        >
          {connectionStatus === 'DISCONNECTED' ? (
            <WifiOff size={11} />
          ) : (
            <Wifi size={11} className={connectionStatus === 'LIVE' ? 'animate-pulse' : ''} />
          )}
          <span className="font-bold">{connectionStatus}</span>
        </div>

        {/* Live Authenticated Presence Pill */}
        <div className="relative hidden lg:block">
          <button
            type="button"
            onClick={() => {
              setPresenceOpen((v) => !v);
              setNotifOpen(false);
            }}
            className="flex items-center gap-1 px-2 py-1 rounded-md bg-[var(--surface-elevated)] border border-[var(--border)] hover:border-[var(--border-strong)] text-[10px] font-mono text-[var(--text-secondary)]"
            title="Live Connected Users"
            data-testid="live-presence-button"
          >
            <Users size={11} className="text-emerald-500" />
            <span>{onlineUsers.length} online</span>
          </button>
          {presenceOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-xl p-3 z-50 space-y-2">
              <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                Active Authenticated Sessions ({onlineUsers.length})
              </div>
              {onlineUsers.length === 0 ? (
                <div className="text-xs text-[var(--text-muted)]">No active sessions</div>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {onlineUsers.map((u) => (
                    <div
                      key={u.user_id}
                      className="flex items-center justify-between text-xs p-1.5 rounded bg-[var(--surface-elevated)]"
                    >
                      <span className="font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        {u.username}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--text-muted)]">
                        {u.role} · {u.current_route || '/'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Notifications / Alerts Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setNotifOpen((v) => !v);
              setPresenceOpen(false);
            }}
            className="relative p-1.5 rounded-lg hover:bg-[var(--surface-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors shrink-0"
            title="Notifications & Active Alerts"
            aria-label="Notifications"
            data-testid="notifications-bell"
          >
            <Bell size={16} />
            {(unreadCount + activeAlertsCount) > 0 && (
              <span className="absolute top-0.5 right-0.5 min-w-[15px] h-[15px] px-1 rounded-full bg-[var(--critical)] text-white text-[9px] font-bold flex items-center justify-center font-mono shadow-xs">
                {unreadCount > 0 ? unreadCount : activeAlertsCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-xl p-3 z-50 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-[var(--text-primary)]">
                  Notifications ({unreadCount} unread)
                </span>
                <div className="flex items-center gap-2">
                  {unreadCount > 0 && (
                    <button
                      type="button"
                      onClick={() => markAllNotificationsRead()}
                      className="text-[10px] text-[var(--accent)] hover:underline flex items-center gap-1"
                    >
                      <CheckCheck size={11} />
                      Mark all read
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setNotifOpen(false);
                      onOpenAlerts();
                    }}
                    className="text-[10px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] underline"
                  >
                    Alerts ({activeAlertsCount})
                  </button>
                </div>
              </div>
              <div className="space-y-1.5 max-h-64 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="text-xs text-[var(--text-muted)] py-3 text-center">
                    No notifications yet.
                  </div>
                ) : (
                  notifications.slice(0, 12).map((n) => (
                    <button
                      key={n.id}
                      type="button"
                      onClick={() => markNotificationRead(n.id)}
                      className={`w-full text-left p-2 rounded-lg border text-xs transition-colors ${
                        n.is_read
                          ? 'bg-[var(--surface)] border-[var(--border)] opacity-70'
                          : 'bg-[var(--surface-elevated)] border-[var(--accent)]/40'
                      }`}
                    >
                      <div className="font-semibold text-[var(--text-primary)] flex items-center justify-between gap-2">
                        <span className="truncate">{n.title}</span>
                        {!n.is_read && <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] shrink-0" />}
                      </div>
                      <div className="text-[11px] text-[var(--text-secondary)] mt-0.5 line-clamp-2">
                        {n.message}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Account / RBAC Pill */}
        <button
          onClick={onOpenAuth}
          className="flex items-center gap-1.5 px-1.5 sm:px-2 py-1 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] hover:border-[var(--border-strong)] text-[var(--text-primary)] transition-colors text-xs shrink-0"
          title={`User: ${currentUser.username} (${currentUser.role})`}
        >
          <div className="w-5 h-5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-bold text-[10px] flex items-center justify-center border border-[var(--accent)]/30 shrink-0">
            {currentUser.username[0]?.toUpperCase() || 'A'}
          </div>
          <span className="font-medium hidden md:inline truncate max-w-[70px] lg:max-w-none">{currentUser.username}</span>
          <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-[var(--surface)] text-[var(--text-muted)] border border-[var(--border)] hidden xl:inline">
            {currentUser.role}
          </span>
        </button>

        {/* Light / Dark Theme Toggle Button */}
        <button
          onClick={onToggleTheme}
          className="p-1.5 rounded-lg hover:bg-[var(--surface-elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors shrink-0"
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
