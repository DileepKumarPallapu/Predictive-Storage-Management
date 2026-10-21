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
  Sparkles
} from 'lucide-react';

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
}

interface NavGroup {
  groupName: string;
  items: {
    id: PageId;
    label: string;
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
}) => {
  const navGroups: NavGroup[] = [
    {
      groupName: 'OPERATIONS & FLEET',
      items: [
        { id: 'overview', label: 'Executive Overview', icon: Activity },
        { id: 'fleet', label: 'Storage Fleet', icon: HardDrive },
        { id: 'intelligence', label: 'Device Intelligence', icon: Cpu },
        { id: 'telemetry', label: 'Telemetry Explorer', icon: LineChart },
      ],
    },
    {
      groupName: 'RESILIENCE TWIN & ENGINES',
      items: [
        { id: 'twin', label: 'Storage Digital Twin', icon: Layers, highlight: true },
        { id: 'omega', label: 'Omega Fleet Control', icon: Network, highlight: true },
        { id: 'jurassic', label: 'Jurassic Resilience Lab', icon: Flame, highlight: true },
        { id: 'phoenix', label: 'Phoenix Orchestrator', icon: ShieldAlert, highlight: true },
        { id: 'atlas', label: 'Atlas Reality Lab', icon: Compass, highlight: true },
        { id: 'interventions', label: 'Intervention Studio', icon: Sliders },
      ],
    },
    {
      groupName: 'RESEARCH & GOVERNANCE',
      items: [
        { id: 'ml-lab', label: 'ML Prediction Lab', icon: Brain },
        { id: 'experiments', label: 'Experiment Workbench', icon: FlaskConical },
        { id: 'reliability', label: 'Model Reliability', icon: ShieldCheck },
        { id: 'alerts', label: 'Alerts & Incidents', icon: AlertTriangle, badge: activeAlertsCount },
        { id: 'datasets', label: 'Datasets & Quality', icon: Database },
        { id: 'settings', label: 'Settings & Audit', icon: Settings },
      ],
    },
  ];

  return (
    <aside
      className={`h-screen glass-panel border-r border-aurora-borderSubtle flex flex-col justify-between transition-all duration-200 select-none z-30 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-aurora-borderSubtle flex items-center justify-between">
        {!collapsed && (
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-aurora-cyan shadow-[0_0_10px_var(--accent-cyan)] animate-pulse" />
              <span className="font-black tracking-wider text-base text-aurora-textPrimary">
                AEGIS<span className="text-aurora-cyan">STOR</span>
              </span>
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-[10px] text-aurora-textMuted font-mono tracking-tight">
                AURORA GLASS INFINITY
              </span>
              <Sparkles size={10} className="text-aurora-violet" />
            </div>
          </div>
        )}
        <button
          onClick={onToggleCollapsed}
          className="p-1.5 rounded-lg glass-panel hover:border-aurora-cyan text-aurora-textMuted hover:text-aurora-textPrimary transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
        </button>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 overflow-y-auto p-2.5 space-y-4">
        {navGroups.map((group, gIdx) => (
          <div key={gIdx} className="space-y-1">
            {!collapsed && (
              <div className="px-3 pt-2 pb-1 text-[9px] font-mono font-bold tracking-widest text-aurora-textMuted/70 uppercase">
                {group.groupName}
              </div>
            )}
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectPage(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-aurora-cyan/15 text-aurora-cyan border border-aurora-cyan/40 font-bold shadow-glow-cyan'
                      : 'text-aurora-textSecondary hover:bg-aurora-surfaceSecondary hover:text-aurora-textPrimary border border-transparent'
                  } ${item.highlight && !isActive ? 'border-aurora-cyan/20 text-aurora-cyan/85 hover:border-aurora-cyan/40' : ''}`}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon
                    size={16}
                    className={`shrink-0 transition-transform ${
                      isActive ? 'text-aurora-cyan scale-110' : 'text-aurora-textSecondary'
                    }`}
                  />
                  {!collapsed && (
                    <span className="flex-1 text-left truncate tracking-tight">{item.label}</span>
                  )}
                  {!collapsed && item.badge !== undefined && item.badge > 0 && (
                    <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold rounded-full bg-aurora-danger/20 text-aurora-danger border border-aurora-danger/40">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer Profile */}
      <div className="p-3 border-t border-aurora-borderSubtle text-xs">
        {!collapsed ? (
          <div className="flex items-center gap-2.5 p-1.5 rounded-lg glass-panel">
            <div className="w-7 h-7 rounded-full bg-aurora-surfaceSecondary border border-aurora-borderSubtle flex items-center justify-center font-mono text-[11px] text-aurora-cyan font-bold shadow-sm">
              SA
            </div>
            <div className="truncate">
              <div className="text-aurora-textPrimary font-semibold truncate text-xs">Principal Architect</div>
              <div className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Zero Mutations Verified
              </div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-7 h-7 rounded-full bg-aurora-surfaceSecondary border border-aurora-borderSubtle flex items-center justify-center font-mono text-[10px] text-aurora-cyan font-bold">
              SA
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
