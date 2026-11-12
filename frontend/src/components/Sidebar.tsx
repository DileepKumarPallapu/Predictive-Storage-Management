import React from 'react';
import { AegisstorBrand } from './AegisstorBrand';
import {
  Activity,
  HardDrive,
  Cpu,
  Layers,
  Sliders,
  LineChart,
  Brain,
  ShieldCheck,
  AlertTriangle,
  Database,
  Settings,
  ChevronLeft,
  ChevronRight,
  Network,
  ShieldAlert,
  Compass,
  Sparkles,
  Workflow,
  X,
  Upload,
  FileText,
  ClipboardList,
  ClipboardCheck,
  Radio,
  Plug,
  Users
} from 'lucide-react';
import { usePresentationMode } from '../context/PresentationModeContext';

export type PageId =
  | 'admin'
  | 'operator'
  | 'viewer'
  | 'access-denied'
  | 'overview'
  | 'fleet'
  | 'topology'
  | 'live-telemetry'
  | 'ingestion'
  | 'datasets'
  | 'workload'
  | 'ml-centre'
  | 'ml-lab'
  | 'risk-centre'
  | 'telemetry'
  | 'twin'
  | 'optimizer'
  | 'interventions'
  | 'approvals'
  | 'tasks'
  | 'alerts'
  | 'reports'
  | 'audit'
  | 'integrations'
  | 'control-plane'
  | 'settings'
  | 'intelligence'
  | 'users'
  | 'experiments'
  | 'reliability';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  activeAlertsCount: number;
  currentUserRole?: string;
  userPermissions?: string[];
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
    requiredPermission?: string;
  }[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  collapsed,
  onToggleCollapsed,
  activeAlertsCount,
  currentUserRole = 'VIEWER',
  userPermissions = [],
  mobileOpen = false,
  onCloseMobile,
}) => {
  usePresentationMode();
  const permSet = new Set(userPermissions);
  const roleUpper = (currentUserRole || 'VIEWER').toUpperCase();
  const homePage: { id: PageId; label: string } =
    roleUpper === 'ADMIN'
      ? { id: 'admin', label: 'Admin Workspace' }
      : roleUpper === 'OPERATOR'
      ? { id: 'operator', label: 'Operator Workspace' }
      : { id: 'viewer', label: 'Viewer Summary' };

  const rawNavGroups: NavGroup[] = [
    {
      groupName: 'OVERVIEW',
      items: [
        { id: homePage.id, label: homePage.label, icon: ShieldCheck, requiredPermission: 'storage.read' },
        { id: 'overview', label: 'Overview', icon: Activity, requiredPermission: 'storage.read' },
      ],
    },
    {
      groupName: 'DATA SOURCES',
      items: [
        { id: 'integrations', label: 'Data Sources & Connections', icon: Plug, requiredPermission: 'integrations.read' },
        { id: 'ingestion', label: 'Import Data', icon: Upload, requiredPermission: 'ingestion.preview' },
        { id: 'datasets', label: 'Data Quality', icon: Database, requiredPermission: 'quality.read' },
      ],
    },
    {
      groupName: 'STORAGE',
      items: [
        { id: 'fleet', label: 'Storage Systems', icon: HardDrive, requiredPermission: 'storage.read' },
        { id: 'topology', label: 'Storage Topology', icon: Network, requiredPermission: 'storage.read' },
        { id: 'intelligence', label: 'Device Details', icon: Cpu, requiredPermission: 'storage.read' },
      ],
    },
    {
      groupName: 'MONITORING',
      items: [
        { id: 'live-telemetry', label: 'Live Monitoring', icon: Radio, requiredPermission: 'telemetry.read' },
        { id: 'telemetry', label: 'Performance Trends', icon: LineChart, requiredPermission: 'performance.read' },
        { id: 'workload', label: 'Workload Patterns', icon: Sparkles, requiredPermission: 'workload.read' },
      ],
    },
    {
      groupName: 'PREDICTIONS',
      items: [
        { id: 'ml-lab', label: 'Capacity Forecasts', icon: Brain, requiredPermission: 'forecasts.read' },
        { id: 'ml-centre', label: 'Forecasting Models', icon: Cpu, requiredPermission: 'models.read' },
        { id: 'reliability', label: 'Forecast Accuracy', icon: ShieldCheck, requiredPermission: 'models.read' },
      ],
    },
    {
      groupName: 'RISK AND ALERTS',
      items: [
        { id: 'risk-centre', label: 'Capacity Risk', icon: ShieldAlert, requiredPermission: 'risk.read' },
        { id: 'alerts', label: 'Alerts', icon: AlertTriangle, badge: activeAlertsCount, requiredPermission: 'alerts.read' },
      ],
    },
    {
      groupName: 'OPTIMISATION',
      items: [
        { id: 'optimizer', label: 'Optimisation', icon: Sliders, requiredPermission: 'optimisation.read' },
        { id: 'interventions', label: 'Recommendations', icon: Compass, requiredPermission: 'recommendations.read' },
      ],
    },
    {
      groupName: 'DIGITAL TWIN',
      items: [
        { id: 'twin', label: 'Digital Twin (Simulation)', icon: Layers, requiredPermission: 'digital_twin.read' },
      ],
    },
    {
      groupName: 'TASKS AND APPROVALS',
      items: [
        { id: 'tasks', label: 'Tasks', icon: ClipboardList, requiredPermission: 'alerts.read' },
        { id: 'approvals', label: 'Approvals', icon: ClipboardCheck, requiredPermission: 'approvals.read' },
        { id: 'control-plane', label: 'Control Plane', icon: Workflow, requiredPermission: 'control_plane.read' },
      ],
    },
    {
      groupName: 'REPORTS',
      items: [
        { id: 'reports', label: 'Reports', icon: FileText, requiredPermission: 'reports.read' },
        { id: 'audit', label: 'Activity Log', icon: ClipboardList, requiredPermission: 'audit.read' },
      ],
    },
    {
      groupName: 'ADMINISTRATION',
      items: [
        { id: 'settings', label: 'Settings', icon: Settings, requiredPermission: 'settings.update' },
        { id: 'users', label: 'Users & Roles', icon: Users, requiredPermission: 'users.read' },
      ],
    },
  ];

  const navGroups = rawNavGroups
    .map((g) => ({
      ...g,
      items: g.items.filter((it) => !it.requiredPermission || permSet.size === 0 || permSet.has(it.requiredPermission)),
    }))
    .filter((g) => g.items.length > 0);

  const handleItemClick = (id: PageId) => {
    onSelectPage(id);
    if (onCloseMobile) onCloseMobile();
  };

  const sidebarContent = (
    <div className="flex flex-col h-full justify-between">
      {/* Permanent Far Top-Left Brand Position (64px height to match global top bar) */}
      <div className={`h-16 flex items-center border-b border-[var(--border)] shrink-0 px-4 ${collapsed ? 'justify-center px-2' : 'justify-between'}`}>
        <AegisstorBrand collapsed={collapsed} />
        {mobileOpen && (
          <button
            onClick={onCloseMobile}
            className="p-1 rounded-md text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            aria-label="Close Navigation Menu"
          >
            <X size={18} />
          </button>
        )}
      </div>

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
                    className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all relative group text-left ${
                      isActive
                        ? 'bg-[var(--surface-secondary)] text-[var(--accent)] font-bold shadow-2xs'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)]'
                    }`}
                    title={collapsed ? item.label : undefined}
                  >
                    {/* Active Brand Accent Bar */}
                    {isActive && (
                      <span
                        className="absolute left-0 top-1 bottom-1 w-1 rounded-r shadow-xs bg-[var(--brand-primary)]"
                      />
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
          collapsed ? 'w-16' : 'w-64'
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
