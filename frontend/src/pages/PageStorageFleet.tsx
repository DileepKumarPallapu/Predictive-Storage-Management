import React, { useState, useEffect } from 'react';
import { api, DeviceSummary } from '../api/client';
import {
  HardDrive,
  Search,
  Filter,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  Database,
  X,
  Info,
  ShieldCheck
} from 'lucide-react';
import { usePresentationMode } from '../context/PresentationModeContext';
import { ContextualHelp } from '../components/ContextualHelp';

interface Props {
  onNavigateToIntelligence: (deviceId: string) => void;
}

export const PageStorageFleet: React.FC<Props> = ({ onNavigateToIntelligence }) => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const [editingDevice, setEditingDevice] = useState<DeviceSummary | null>(null);
  const [warnThreshold, setWarnThreshold] = useState<number>(80);
  const [critThreshold, setCritThreshold] = useState<number>(90);
  const [maxLat, setMaxLat] = useState<number>(20);
  const [saveMsg, setSaveMsg] = useState('');
  const { isGuided } = usePresentationMode();

  useEffect(() => {
    loadFleet();
  }, [tierFilter, searchTerm]);

  const loadFleet = async () => {
    try {
      const data = await api.getDevices(tierFilter || undefined, undefined, searchTerm || undefined);
      setDevices(data);
    } catch (e) {
      console.error(e);
    }
  };

  const openEditModal = (dev: DeviceSummary) => {
    setEditingDevice(dev);
    setWarnThreshold(dev.warning_threshold_pct);
    setCritThreshold(dev.critical_threshold_pct);
    setMaxLat(dev.max_acceptable_latency_ms);
    setSaveMsg('');
  };

  const handleSaveThresholds = async () => {
    if (!editingDevice) return;
    try {
      await api.updateThresholds(editingDevice.id, {
        warning_threshold_pct: warnThreshold,
        critical_threshold_pct: critThreshold,
        max_acceptable_latency_ms: maxLat,
      });
      setSaveMsg('Thresholds saved & logged to audit trail.');
      setTimeout(() => {
        setEditingDevice(null);
        loadFleet();
      }, 1000);
    } catch (e: any) {
      setSaveMsg(`Error: ${e.message}`);
    }
  };

  const formatTB = (bytes: number) => (bytes / (1024 ** 4)).toFixed(1) + ' TB';

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/30 flex items-center justify-center text-[var(--accent-primary)] shadow-glow-vermilion">
            <HardDrive size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            {isGuided ? 'Storage Fleet & Safety Limits' : 'Storage Fleet Inventory & Service Constraints'}
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          {isGuided
            ? 'View all active storage pools, check how much room is left, and adjust safety alert limits.'
            : 'Catalog of physical pools, active workloads, provisioned thresholds, and live health metrics.'}
        </p>
      </div>

      {/* Safety Envelope Contextual Card */}
      <div className="glass-panel rounded-2xl p-4 flex items-start gap-3 border-l-4 border-l-[var(--status-success)] text-xs">
        <ShieldCheck size={18} className="text-[var(--status-success)] shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-[var(--text-primary)]">
            {isGuided ? 'What are Hard Safety Limits?' : 'Hard Safety Envelope Governance'}
          </span>
          <p className="text-[var(--text-secondary)] mt-0.5 leading-relaxed">
            Safety limits define the maximum storage utilization and latency your workloads can tolerate. The Digital Twin simulator strictly enforces these rules: it will disqualify any proposed remediation that would cause service disruption.
          </p>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between glass-panel rounded-xl p-3.5">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-2.5 text-[var(--text-muted)]" size={15} />
          <input
            type="text"
            placeholder="Search pool ID or name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg pl-9 pr-3 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none transition-colors"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          <Filter size={14} className="text-[var(--text-muted)]" />
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none cursor-pointer"
          >
            <option value="" className="bg-[var(--surface-primary)]">All Storage Tiers</option>
            <option value="NVME_TIER1" className="bg-[var(--surface-primary)]">Tier 1 NVMe (Fastest)</option>
            <option value="SAS_TIER2" className="bg-[var(--surface-primary)]">Tier 2 Enterprise SAS</option>
            <option value="HDD_ARCHIVE" className="bg-[var(--surface-primary)]">Tier 3 Cold Archive</option>
          </select>
        </div>
      </div>

      {/* Grid of Storage Devices */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {devices.map((d) => (
          <div
            key={d.id}
            className="glass-panel rounded-2xl p-5 flex flex-col justify-between hover:border-[var(--accent-primary)]/40 transition-all group"
          >
            <div>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">{d.name}</h3>
                  <div className="text-[11px] font-mono text-[var(--accent-primary)] mt-0.5">{d.id}</div>
                </div>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                    d.status === 'HEALTHY'
                      ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm'
                      : 'bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40 shadow-sm'
                  }`}
                >
                  {d.status}
                </span>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-2.5 border border-[var(--border-subtle)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase font-mono tracking-wider">
                    {isGuided ? 'Drive Tier' : 'Media & Tier'}
                  </div>
                  <div className="text-[var(--text-primary)] font-semibold mt-0.5 font-mono">{d.tier}</div>
                  <div className="text-[var(--text-secondary)] text-[10px] truncate">{d.media_type}</div>
                </div>
                <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-2.5 border border-[var(--border-subtle)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase font-mono tracking-wider">
                    {isGuided ? 'Application' : 'Workload Profile'}
                  </div>
                  <div className="text-[var(--text-primary)] font-semibold mt-0.5 truncate">{d.workload_profile}</div>
                  <div className="text-[var(--text-secondary)] text-[10px]">
                    Active IOPS: {(d.current_read_iops + d.current_write_iops).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mt-4">
                <div className="flex justify-between text-xs font-mono mb-1.5">
                  <span className="text-[var(--text-secondary)]">Capacity In Use</span>
                  <span className="text-[var(--text-primary)] font-semibold tabular-nums">
                    {formatTB(d.current_used_bytes)} / {formatTB(d.total_capacity_bytes)} ({d.current_utilization_pct.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-[var(--surface-secondary)] h-2 rounded-full overflow-hidden p-0.5 border border-[var(--border-subtle)]">
                  <div
                    className={`h-full rounded-full transition-all ${
                      d.current_utilization_pct >= d.critical_threshold_pct
                        ? 'bg-[var(--status-critical)] shadow-[0_0_6px_var(--status-critical)]'
                        : d.current_utilization_pct >= d.warning_threshold_pct
                        ? 'bg-[var(--status-warning)] shadow-[0_0_6px_var(--status-warning)]'
                        : 'bg-gradient-to-r from-[var(--accent-secondary)] to-[var(--accent-primary)] shadow-[0_0_6px_var(--accent-primary)]'
                    }`}
                    style={{ width: `${Math.min(100, d.current_utilization_pct)}%` }}
                  />
                </div>
              </div>

              {/* Threshold info */}
              <div className="mt-3 flex items-center justify-between text-[11px] text-[var(--text-muted)] font-mono">
                <span>Warn: {d.warning_threshold_pct}% | Limit: {d.critical_threshold_pct}%</span>
                <span>Max Latency: {d.max_acceptable_latency_ms}ms</span>
              </div>
            </div>

            <div className="mt-5 pt-3.5 border-t border-[var(--border-subtle)] flex items-center justify-between gap-2">
              <button
                onClick={() => openEditModal(d)}
                className="px-3 py-1.5 rounded-lg btn-ember-secondary text-xs flex items-center gap-1.5 font-medium"
              >
                <Sliders size={13} />
                Adjust Safety Limits
              </button>

              <button
                onClick={() => onNavigateToIntelligence(d.id)}
                className="px-3.5 py-1.5 rounded-lg btn-ember-primary text-xs flex items-center gap-1.5 font-semibold"
              >
                {isGuided ? 'Inspect Device' : 'Deep Intelligence'} <ArrowUpRight size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Threshold Edit Modal */}
      {editingDevice && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center p-4 z-50">
          <div className="glass-modal max-w-md w-full p-6 space-y-4 shadow-glass-modal rounded-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/30 flex items-center justify-center text-[var(--accent-primary)]">
                  <Sliders size={16} />
                </div>
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  Configure Safety Limits: {editingDevice.name}
                </h3>
              </div>
              <button
                onClick={() => setEditingDevice(null)}
                className="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded-lg transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Adjust warning and critical capacity limits. The digital twin simulator will refuse any intervention that violates these constraints.
            </p>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[var(--text-secondary)] mb-1 text-[11px] uppercase tracking-wider font-medium">
                  Warning Alert Threshold (% Capacity):
                </label>
                <input
                  type="number"
                  min="50"
                  max="95"
                  value={warnThreshold}
                  onChange={(e) => setWarnThreshold(Number(e.target.value))}
                  className="w-full bg-[var(--surface-primary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-2 text-[var(--text-primary)] font-mono focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] mb-1 text-[11px] uppercase tracking-wider font-medium">
                  Critical Safety Limit (% Capacity):
                </label>
                <input
                  type="number"
                  min="60"
                  max="99"
                  value={critThreshold}
                  onChange={(e) => setCritThreshold(Number(e.target.value))}
                  className="w-full bg-[var(--surface-primary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-2 text-[var(--text-primary)] font-mono focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] mb-1 text-[11px] uppercase tracking-wider font-medium">
                  Maximum Allowable Latency (ms):
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={maxLat}
                  onChange={(e) => setMaxLat(Number(e.target.value))}
                  className="w-full bg-[var(--surface-primary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-2 text-[var(--text-primary)] font-mono focus:outline-none"
                />
              </div>
            </div>

            {saveMsg && (
              <div className="text-xs text-[var(--status-success)] bg-[var(--status-success)]/10 border border-[var(--status-success)]/30 p-2.5 rounded-lg font-medium font-mono">
                {saveMsg}
              </div>
            )}

            <div className="flex justify-end gap-2.5 pt-3.5 border-t border-[var(--border-subtle)]">
              <button
                onClick={() => setEditingDevice(null)}
                className="px-3.5 py-1.5 rounded-lg btn-ember-secondary text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveThresholds}
                className="px-4 py-1.5 rounded-lg btn-ember-primary font-semibold text-xs"
              >
                Save Constraints
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
