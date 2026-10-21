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
  ChevronRight
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
  | 'settings';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  activeAlertsCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  collapsed,
  onToggleCollapsed,
  activeAlertsCount,
}) => {
  const navItems = [
    { id: 'overview' as PageId, label: 'Executive Overview', icon: Activity },
    { id: 'fleet' as PageId, label: 'Storage Fleet', icon: HardDrive },
    { id: 'intelligence' as PageId, label: 'Device Intelligence', icon: Cpu },
    { id: 'twin' as PageId, label: 'Storage Digital Twin', icon: Layers, highlight: true },
    { id: 'interventions' as PageId, label: 'Intervention Studio', icon: Sliders },
    { id: 'telemetry' as PageId, label: 'Telemetry Explorer', icon: LineChart },
    { id: 'ml-lab' as PageId, label: 'ML Prediction Lab', icon: Brain },
    { id: 'experiments' as PageId, label: 'Experiment Workbench', icon: FlaskConical },
    { id: 'reliability' as PageId, label: 'Model Reliability', icon: ShieldCheck },
    { id: 'alerts' as PageId, label: 'Alerts & Incidents', icon: AlertTriangle, badge: activeAlertsCount },
    { id: 'datasets' as PageId, label: 'Datasets & Quality', icon: Database },
    { id: 'settings' as PageId, label: 'Settings & Audit', icon: Settings },
  ];

  return (
    <aside
      className={`h-screen bg-obsidian-sidebar border-r border-obsidian-border flex flex-col justify-between transition-all duration-200 select-none ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="p-4 border-b border-obsidian-border flex items-center justify-between">
        {!collapsed && (
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-obsidian-cyan shadow-[0_0_8px_var(--accent-cyan)]"></span>
              <span className="font-extrabold tracking-wider text-base text-obsidian-text">
                AEGIS<span className="text-obsidian-cyan">STOR</span>
              </span>
            </div>
            <p className="text-[10px] text-obsidian-muted font-mono tracking-tight mt-0.5">
              RESILIENCE TWIN v1.0
            </p>
          </div>
        )}
        <button
          onClick={onToggleCollapsed}
          className="p-1 rounded bg-obsidian-panel border border-obsidian-border text-obsidian-muted hover:text-obsidian-text hover:border-obsidian-cyan transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectPage(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                isActive
                  ? 'bg-obsidian-panel text-obsidian-cyan border border-obsidian-border font-semibold shadow-sm'
                  : 'text-obsidian-muted hover:bg-obsidian-panel/60 hover:text-obsidian-text border border-transparent'
              } ${item.highlight && !isActive ? 'border-obsidian-cyan/30 text-obsidian-cyan/90' : ''}`}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={16} className={isActive ? 'text-obsidian-cyan' : ''} />
              {!collapsed && (
                <span className="flex-1 text-left truncate">{item.label}</span>
              )}
              {!collapsed && item.badge !== undefined && item.badge > 0 && (
                <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-obsidian-coral/20 text-obsidian-coral border border-obsidian-coral/40">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Profile */}
      <div className="p-3 border-t border-obsidian-border text-xs">
        {!collapsed ? (
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-obsidian-panel border border-obsidian-border flex items-center justify-center font-mono text-[11px] text-obsidian-cyan font-bold">
              SA
            </div>
            <div className="truncate">
              <div className="text-obsidian-text font-medium truncate text-xs">Principal Architect</div>
              <div className="text-[10px] text-obsidian-muted font-mono">Shadow Mode Active</div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="w-7 h-7 rounded-full bg-obsidian-panel border border-obsidian-border flex items-center justify-center font-mono text-[10px] text-obsidian-cyan font-bold">
              SA
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
