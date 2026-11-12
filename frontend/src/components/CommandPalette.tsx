import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  HardDrive,
  Activity,
  Cpu,
  Layers,
  Sliders,
  LineChart,
  Brain,
  ShieldCheck,
  AlertTriangle,
  Database,
  Settings,
  X,
  Sparkles,
  Flame,
  ShieldAlert,
  Compass,
  FlaskConical,
  Network
} from 'lucide-react';
import { PageId } from './Sidebar';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigatePage: (page: PageId) => void;
  onNavigateDevice: (deviceId: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigatePage,
  onNavigateDevice,
}) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const devices = [
    { id: 'vol-nvme-tier1-db', name: 'Production E-Commerce OLTP NVMe', tier: 'NVMe Tier 1' },
    { id: 'vol-sas-tier2-analytics', name: 'Corporate Data Warehouse & ETL SAS', tier: 'SAS Tier 2' },
    { id: 'vol-hdd-archive', name: 'Object & Media Archive Cold Pool', tier: 'Cold Archive' },
    { id: 'vol-backup-target', name: 'Secondary Veeam / SnapMirror Target', tier: 'Backup Target' },
    { id: 'host-vol-C', name: 'Host Storage Drive (C:\\)', tier: 'Host Local OS' },
  ];

  const pages: { id: PageId; label: string; icon: any }[] = [
    { id: 'overview', label: '1. Operations Overview', icon: Activity },
    { id: 'fleet', label: '2. Infrastructure Inventory', icon: HardDrive },
    { id: 'topology', label: '3. Storage Topology', icon: Network },
    { id: 'live-telemetry', label: '4. Live Telemetry', icon: Activity },
    { id: 'ingestion', label: '5. Data Ingestion', icon: Database },
    { id: 'datasets', label: '6. Data Quality', icon: Database },
    { id: 'workload', label: '7. Workload Intelligence', icon: Sparkles },
    { id: 'ml-centre', label: '8. ML Model Centre (LightGBM & SARIMAX)', icon: Cpu },
    { id: 'ml-lab', label: '9. Forecast Studio', icon: Brain },
    { id: 'risk-centre', label: '10. Capacity Risk Centre', icon: ShieldAlert },
    { id: 'telemetry', label: '11. Performance Analytics', icon: LineChart },
    { id: 'twin', label: '12. Digital Twin', icon: Layers },
    { id: 'optimizer', label: '13. Decision Optimisation', icon: Sliders },
    { id: 'interventions', label: '14. Recommendations', icon: Compass },
    { id: 'approvals', label: '15. Approval Centre', icon: ShieldCheck },
    { id: 'alerts', label: '16. Alert Centre', icon: AlertTriangle },
    { id: 'reports', label: '17. Reports and Exports', icon: Database },
    { id: 'audit', label: '18. Audit and Activity', icon: ShieldCheck },
    { id: 'integrations', label: '19. Integration Management', icon: Network },
    { id: 'settings', label: '20. Administration and Settings', icon: Settings },
  ];

  const filteredDevices = devices.filter(
    (d) =>
      d.name.toLowerCase().includes(query.toLowerCase()) ||
      d.id.toLowerCase().includes(query.toLowerCase())
  );

  const filteredPages = pages.filter((p) =>
    p.label.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-start justify-center pt-20 p-4">
      <div className="glass-modal border border-[var(--border-normal)] rounded-2xl shadow-glass-modal w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
        {/* Search Input Header */}
        <div className="flex items-center px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--surface-secondary)]">
          <Search size={18} className="text-[var(--accent-primary)] mr-3" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search storage pools, pages, or commands (Ctrl+K)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded hover:bg-[var(--surface-hover)]"
          >
            <X size={16} />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-3">
          {/* Devices Section */}
          {filteredDevices.length > 0 && (
            <div>
              <div className="text-[10px] uppercase font-mono font-bold text-[var(--text-muted)] px-3 py-1">
                Storage Pools
              </div>
              <div className="space-y-1">
                {filteredDevices.map((dev) => (
                  <button
                    key={dev.id}
                    onClick={() => {
                      onNavigateDevice(dev.id);
                      onClose();
                    }}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-left text-xs hover:bg-[var(--accent-primary)]/15 group transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <HardDrive size={15} className="text-[var(--accent-primary)] group-hover:scale-110 transition-transform" />
                      <div>
                        <div className="font-semibold text-[var(--text-primary)]">{dev.name}</div>
                        <div className="font-mono text-[10px] text-[var(--text-muted)]">{dev.id}</div>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[var(--accent-primary)]">
                      {dev.tier}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Navigation Section */}
          {filteredPages.length > 0 && (
            <div>
              <div className="text-[10px] uppercase font-mono font-bold text-[var(--text-muted)] px-3 py-1">
                Platform Views
              </div>
              <div className="space-y-1">
                {filteredPages.map((page) => {
                  const Icon = page.icon;
                  return (
                    <button
                      key={page.id}
                      onClick={() => {
                        onNavigatePage(page.id);
                        onClose();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-xs text-[var(--text-primary)] hover:bg-[var(--surface-hover)] group transition-colors"
                    >
                      <Icon size={15} className="text-[var(--text-muted)] group-hover:text-[var(--accent-primary)]" />
                      <span className="font-medium">{page.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {filteredDevices.length === 0 && filteredPages.length === 0 && (
            <div className="py-8 text-center text-xs text-[var(--text-muted)] font-mono">
              No matching storage devices or pages found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
