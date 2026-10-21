import React from 'react';
import {
  Activity,
  HardDrive,
  Cpu,
  Layers,
  Sliders,
  LineChart,
  Brain,
  FlaskConical,
  ShieldCheck,
  AlertTriangle,
  Database,
  Settings,
  ChevronLeft,
  ChevronRight,
  Network,
  Flame,
  ShieldAlert,
  Compass,
  Sparkles,
  Search,
  BookOpen
} from 'lucide-react';
import { usePresentationMode } from '../context/PresentationModeContext';

export type PageId =
  | 'overview'
  | 'fleet'
  | 'intelligence'
  | 'twin'
  | 'interventions'
  | 'telemetry'
  | 'ml-lab'
  | 'experiments'
  | 'reliability'
  | 'alerts'
  | 'datasets'
  | 'settings'
  | 'omega'
  | 'jurassic'
  | 'phoenix'
  | 'atlas';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  activeAlertsCount: number;
  onOpenOnboarding?: () => void;
}

interface NavGroup {
  groupName: string;
  items: {
    id: PageId;
    guidedLabel: string;
    expertLabel: string;
    icon: any;
    highlight?: boolean;
    badge?: number;
  }[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  collapsed,
  onToggleCollapsed,
  activeAlertsCount,
  onOpenOnboarding,
}) => {
  const { isGuided } = usePresentationMode();

  const navGroups: NavGroup[] = [
    {
      groupName: '1. OVERVIEW',
      items: [
        {
          id: 'overview',
          guidedLabel: 'Dashboard & Health',
          expertLabel: 'Executive Overview',
          icon: Activity,
        },
      ],
    },
    {
      groupName: '2. MONITOR',
      items: [
        {
          id: 'fleet',
          guidedLabel: 'Storage Fleet',
          expertLabel: 'Fleet Inventory & SLAs',
          icon: HardDrive,
        },
        {
          id: 'intelligence',
          guidedLabel: 'Device Details',
          expertLabel: 'Device Intelligence',
          icon: Cpu,
        },
        {
          id: 'telemetry',
          guidedLabel: 'Telemetry Signals',
          expertLabel: 'Telemetry Explorer',
          icon: LineChart,
        },
        {
          id: 'alerts',
          guidedLabel: 'Alerts & Safeguards',
          expertLabel: 'Alerts & Incidents',
          icon: AlertTriangle,
          badge: activeAlertsCount,
        },
      ],
    },
    {
      groupName: '3. PREDICT',
      items: [
        {
          id: 'ml-lab',
          guidedLabel: 'Capacity Forecast',
          expertLabel: 'ML Prediction Lab',
          icon: Brain,
        },
        {
          id: 'reliability',
          guidedLabel: 'Forecast Reliability',
          expertLabel: 'Model Calibration & Drift',
          icon: ShieldCheck,
        },
      ],
    },
    {
      groupName: '4. SIMULATE',
      items: [
        {
          id: 'twin',
          guidedLabel: 'Digital Twin Sandbox',
          expertLabel: 'Resilience Digital Twin',
          icon: Layers,
          highlight: true,
        },
        {
          id: 'interventions',
          guidedLabel: 'Compare Actions',
          expertLabel: 'Intervention Studio',
          icon: Sliders,
          highlight: true,
        },
      ],
    },
    {
      groupName: '5. RESPOND',
      items: [
        {
          id: 'phoenix',
          guidedLabel: 'Incident Command',
          expertLabel: 'Phoenix Orchestrator',
          icon: ShieldAlert,
          highlight: true,
        },
      ],
    },
    {
      groupName: '6. RESEARCH',
      items: [
        {
          id: 'omega',
          guidedLabel: 'Fleet Topology Control',
          expertLabel: 'Omega Fleet Control',
          icon: Network,
        },
        {
          id: 'jurassic',
          guidedLabel: 'Resilience Testing Lab',
          expertLabel: 'Jurassic Resilience Lab',
          icon: Flame,
        },
        {
          id: 'atlas',
          guidedLabel: 'Reality Calibration',
          expertLabel: 'Atlas Reality Lab',
          icon: Compass,
        },
        {
          id: 'experiments',
          guidedLabel: 'Scientific Ablations',
          expertLabel: 'Experiment Workbench',
          icon: FlaskConical,
        },
        {
          id: 'datasets',
          guidedLabel: 'Dataset Provenance',
          expertLabel: 'Datasets & Schema Quality',
          icon: Database,
        },
      ],
    },
    {
      groupName: '7. ADMINISTRATION',
      items: [
        {
          id: 'settings',
          guidedLabel: 'Settings & Audit Log',
          expertLabel: 'Settings & Governance Audit',
          icon: Settings,
        },
      ],
    },
  ];

  return (
    <aside
      className={`h-screen glass-panel border-r border-[var(--border-subtle)] flex flex-col justify-between transition-all duration-200 select-none z-30 shrink-0 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
        {!collapsed && (
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-cyan)] shadow-[0_0_10px_var(--accent-cyan)] animate-pulse" />
              <span className="font-black tracking-wider text-base text-[var(--text-primary)]">
                AEGIS<span className="text-[var(--accent-cyan)]">STOR</span>
              </span>
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-[10px] text-[var(--text-muted)] font-mono tracking-tight uppercase">
                Aurora Experience
              </span>
              <Sparkles size={11} className="text-[var(--accent-violet)]" />
            </div>
          </div>
        )}
        <button
          onClick={onToggleCollapsed}
          className="p-1.5 rounded-lg glass-panel hover:border-[var(--accent-cyan)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
        </button>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 overflow-y-auto p-2.5 space-y-4">
        {navGroups.map((group, gIdx) => (
          <div key={gIdx} className="space-y-1">
            {!collapsed && (
              <div className="px-3 pt-2 pb-1 text-[9px] font-mono font-bold tracking-widest text-[var(--text-muted)] uppercase">
                {group.groupName}
              </div>
            )}
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;
              const label = isGuided ? item.guidedLabel : item.expertLabel;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectPage(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-[var(--accent-cyan)]/15 text-[var(--accent-cyan)] border border-[var(--accent-cyan)]/50 font-bold shadow-glow-cyan'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)] border border-transparent'
                  } ${item.highlight && !isActive ? 'border-[var(--accent-cyan)]/25 text-[var(--text-primary)]' : ''}`}
                  title={collapsed ? label : undefined}
                >
                  <Icon
                    size={16}
                    className={`shrink-0 transition-transform ${
                      isActive ? 'text-[var(--accent-cyan)] scale-110' : 'text-[var(--text-secondary)]'
                    }`}
                  />
                  {!collapsed && (
                    <span className="flex-1 text-left truncate tracking-tight">{label}</span>
                  )}
                  {!collapsed && item.badge !== undefined && item.badge > 0 && (
                    <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded-full bg-[var(--color-critical)]/20 text-[var(--color-critical)] border border-[var(--color-critical)]/40 shadow-sm">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer Quick Tour / Onboarding & Profile */}
      <div className="p-3 border-t border-[var(--border-subtle)] space-y-2 text-xs">
        {onOpenOnboarding && !collapsed && (
          <button
            onClick={onOpenOnboarding}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 px-2.5 rounded-lg btn-aurora-secondary text-[11px] font-medium"
          >
            <BookOpen size={13} className="text-[var(--accent-cyan)]" />
            <span>Interactive Guide</span>
          </button>
        )}

        {!collapsed ? (
          <div className="flex items-center gap-2.5 p-2 rounded-xl glass-panel">
            <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-[var(--accent-cyan)]/25 to-[var(--accent-sapphire)]/25 border border-[var(--accent-cyan)]/40 flex items-center justify-center font-mono text-[11px] text-[var(--accent-cyan)] font-bold shadow-sm shrink-0">
              SA
            </div>
            <div className="truncate">
              <div className="text-[var(--text-primary)] font-semibold truncate text-xs">Storage SRE</div>
              <div className="text-[10px] text-[var(--color-success)] font-mono flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] animate-pulse" />
                Zero Physical Mutations
              </div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-7 h-7 rounded-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-center font-mono text-[10px] text-[var(--accent-cyan)] font-bold">
              SA
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
