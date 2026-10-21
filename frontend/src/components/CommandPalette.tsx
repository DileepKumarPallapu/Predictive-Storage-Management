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
    { id: 'vol-nvme-tier1-db', name: 'PostgreSQL Primary Cluster', tier: 'NVMe' },
    { id: 'vol-sas-tier2-analytics', name: 'Analytics & OLAP Pool', tier: 'SAS' },
    { id: 'vol-cold-tier3-backup', name: 'Disaster Recovery Vault', tier: 'Cold' },
    { id: 'vol-edge-cache-01', name: 'Edge Ingestion Buffer', tier: 'NVMe' },
  ];

  const pages: { id: PageId; label: string; icon: any }[] = [
    { id: 'overview', label: 'Executive Overview & Condition', icon: Activity },
    { id: 'fleet', label: 'Storage Fleet & Hardware Pools', icon: HardDrive },
    { id: 'intelligence', label: 'Device Telemetry & Tail Risks', icon: Cpu },
    { id: 'twin', label: 'Resilience Digital Twin Simulator', icon: Layers },
    { id: 'interventions', label: 'Intervention Studio & Counterfactuals', icon: Sliders },
    { id: 'telemetry', label: 'Raw Telemetry Signal Explorer', icon: LineChart },
    { id: 'ml-lab', label: 'ML Prediction & Quantile Lab', icon: Brain },
    { id: 'reliability', label: 'Model Reliability & Conformal Drift', icon: ShieldCheck },
    { id: 'alerts', label: 'Alerts, Thresholds & Active Incidents', icon: AlertTriangle },
    { id: 'omega', label: 'Omega Fleet Topology & Correlated Risk', icon: Network },
    { id: 'jurassic', label: 'Jurassic Resilience & Stress Lab', icon: Flame },
    { id: 'phoenix', label: 'Phoenix Safe Incident Orchestrator', icon: ShieldAlert },
    { id: 'atlas', label: 'Atlas Reality Calibration & Fidelity', icon: Compass },
    { id: 'experiments', label: 'Ablation Experiments & Benchmarks', icon: FlaskConical },
    { id: 'datasets', label: 'Dataset Provenance & Quality Checks', icon: Database },
    { id: 'settings', label: 'Settings & Audit Governance', icon: Settings },
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
