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
  Lock,
  Workflow,
  X
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
  | 'atlas'
  | 'oracle'
  | 'gauntlet'
  | 'sovereign';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  activeAlertsCount: number;
  onOpenOnboarding?: () => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavGroup {
  groupName: string;
  items: {
    id: PageId;
    label: string;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    badge?: number;
  }[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  collapsed,
  onToggleCollapsed,
  activeAlertsCount,
  mobileOpen = false,
  onCloseMobile,
}) => {
  const { isGuided } = usePresentationMode();

  const navGroups: NavGroup[] = [
    {
      groupName: 'OVERVIEW',
      items: [
        {
          id: 'overview',
          label: isGuided ? 'Storage Health' : 'Executive Overview',
          icon: Activity,
        },
      ],
    },
    {
      groupName: 'MONITOR',
      items: [
        {
          id: 'fleet',
          label: isGuided ? 'Storage Fleet' : 'Fleet Inventory & SLAs',
          icon: HardDrive,
        },
        {
          id: 'intelligence',
          label: isGuided ? 'Device Details' : 'Device Telemetry & Tail',
          icon: Cpu,
        },
        {
          id: 'telemetry',
          label: isGuided ? 'Telemetry Signals' : 'Raw Signals Explorer',
          icon: LineChart,
        },
        {
          id: 'alerts',
          label: isGuided ? 'Alerts & Safeguards' : 'Incidents & Active Alerts',
          icon: AlertTriangle,
          badge: activeAlertsCount,
        },
      ],
    },
    {
      groupName: 'PREDICT',
      items: [
        {
          id: 'ml-lab',
          label: isGuided ? 'Capacity Forecast' : 'ML Quantile Lab',
          icon: Brain,
        },
        {
          id: 'reliability',
          label: isGuided ? 'Forecast Reliability' : 'Model Drift & Reliability',
          icon: ShieldCheck,
        },
      ],
    },
    {
      groupName: 'SIMULATE',
      items: [
        {
          id: 'twin',
          label: isGuided ? 'Digital Twin Sandbox' : 'Resilience Digital Twin',
          icon: Layers,
        },
        {
          id: 'interventions',
          label: isGuided ? 'Compare Actions' : 'Counterfactual Interventions',
          icon: Sliders,
        },
      ],
    },
    {
      groupName: 'RESPOND',
      items: [
        {
          id: 'phoenix',
          label: isGuided ? 'Incident Command' : 'Phoenix Orchestrator',
          icon: ShieldAlert,
        },
      ],
    },
    {
      groupName: 'RESEARCH LABS',
      items: [
        {
          id: 'omega',
          label: isGuided ? 'Fleet Topology' : 'Omega Correlated Risk',
          icon: Network,
        },
        {
          id: 'jurassic',
          label: isGuided ? 'Stress Testing' : 'Jurassic Resilience Lab',
          icon: Flame,
        },
        {
          id: 'atlas',
          label: isGuided ? 'Reality Calibration' : 'Atlas Reality Lab',
          icon: Compass,
        },
        {
          id: 'oracle',
          label: isGuided ? 'Bottleneck Analysis' : 'Oracle Attribution AI',
          icon: Sparkles,
        },
        {
          id: 'gauntlet',
          label: isGuided ? 'Scientific Benchmarks' : 'Gauntlet Workbench',
          icon: FlaskConical,
        },
        {
          id: 'sovereign',
          label: isGuided ? 'Federated Privacy' : 'Sovereign Federation',
          icon: Lock,
        },
        {
          id: 'experiments',
          label: isGuided ? 'Ablation Studies' : 'Research Benchmarks',
          icon: Workflow,
        },
      ],
    },
    {
      groupName: 'PLATFORM',
      items: [
        {
          id: 'datasets',
          label: isGuided ? 'Datasets & Quality' : 'Telemetry Repositories',
          icon: Database,
        },
        {
          id: 'settings',
          label: isGuided ? 'Settings & Backups' : 'Governance & Vault Recovery',
          icon: Settings,
        },
      ],
    },
  ];

  const handleItemClick = (id: PageId) => {
    onSelectPage(id);
    if (onCloseMobile) onCloseMobile();
  };

  const sidebarContent = (
    <div className="flex flex-col h-full justify-between">
      {/* Mobile Drawer Header */}
      {mobileOpen && (
        <div className="p-3 border-b border-[var(--border)] flex items-center justify-between">
          <span className="font-bold text-sm text-[var(--text-primary)]">Navigation Menu</span>
          <button
            onClick={onCloseMobile}
            className="p-1 rounded-md text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            aria-label="Close Navigation Menu"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {/* Navigation Scrollable Area */}
      <div className="flex-1 overflow-y-auto py-3 px-2 space-y-4 pb-12">
        {navGroups.map((group) => (
          <div key={group.groupName} className="space-y-0.5">
            {/* Group Header */}
            {!collapsed && (
              <div className="px-2.5 py-1 text-[10px] font-mono font-semibold tracking-wider text-[var(--text-muted)] uppercase">
                {group.groupName}
              </div>
            )}

            {/* Navigation Items */}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const IconComponent = item.icon;
                const isActive = currentPage === item.id;

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleItemClick(item.id)}
                    className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors relative group text-left ${
                      isActive
                        ? 'bg-[var(--surface-elevated)] text-[var(--accent)] font-semibold shadow-xs'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)]'
                    }`}
                    title={collapsed ? item.label : undefined}
                  >
                    {/* Active Accent Bar */}
                    {isActive && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-[var(--accent)] rounded-r" />
                    )}

                    <IconComponent
                      size={15}
                      className={`shrink-0 transition-colors ${
                        isActive
                          ? 'text-[var(--accent)]'
                          : 'text-[var(--text-muted)] group-hover:text-[var(--text-primary)]'
                      }`}
                    />

                    {!collapsed && (
                      <span className="truncate flex-1 text-left text-[12px]">
                        {item.label}
                      </span>
                    )}

                    {/* Badge */}
                    {!collapsed && item.badge !== undefined && item.badge > 0 && (
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-[var(--critical)] text-white">
                        {item.badge}
                      </span>
                    )}

                    {/* Tooltip in collapsed mode */}
                    {collapsed && (
                      <div className="absolute left-full ml-2 px-2.5 py-1 rounded bg-[var(--surface-elevated)] border border-[var(--border)] text-[var(--text-primary)] text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity shadow-md z-50 font-medium">
                        {item.label}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Rail: Mutation Guard Status & Collapse Toggle */}
      <div className="p-2 border-t border-[var(--border)] bg-[var(--surface)] shrink-0 space-y-1">
        {!collapsed && (
          <div className="px-2 py-1 flex items-center justify-between text-[10px] font-mono text-[var(--text-muted)]">
            <span>MUTATION GUARD</span>
            <span className="text-[var(--success)] font-semibold">READ-ONLY</span>
          </div>
        )}

        <button
          type="button"
          onClick={onToggleCollapsed}
          className="w-full flex items-center justify-center gap-2 py-1.5 px-2 rounded-md hover:bg-[var(--surface-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors text-xs"
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {collapsed ? (
            <ChevronRight size={15} />
          ) : (
            <>
              <ChevronLeft size={15} />
              <span className="text-[11px] font-medium">Collapse Sidebar</span>
            </>
          )}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={`hidden lg:flex h-screen bg-[var(--surface)] border-r border-[var(--border)] flex-col justify-between select-none transition-all duration-150 ease-out z-20 shrink-0 sticky top-0 ${
          collapsed ? 'w-16' : 'w-60'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
            onClick={onCloseMobile}
          />
          <aside className="relative w-64 max-w-[80vw] bg-[var(--surface)] border-r border-[var(--border)] h-full z-10 shadow-xl flex flex-col">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
};
