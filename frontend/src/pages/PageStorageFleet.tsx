import React, { useState, useEffect } from 'react';
import { api, DeviceSummary } from '../api/client';
import { HardDrive, Search, Filter, Sliders, CheckCircle2, AlertTriangle, ArrowUpRight, Database, X } from 'lucide-react';

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
          <div className="w-8 h-8 rounded-lg bg-[var(--accent-cyan)]/15 border border-[var(--accent-cyan)]/30 flex items-center justify-center text-[var(--accent-cyan)] shadow-[0_0_12px_rgba(85,214,255,0.2)]">
            <HardDrive size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            Storage Fleet Inventory & Service Constraints
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          Catalog of physical pools, active workloads, provisioned thresholds, and live health metrics.
        </p>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between glass-panel rounded-xl p-3.5">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-2.5 text-[var(--text-tertiary)]" size={15} />
          <input
            type="text"
            placeholder="Search pool ID or name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[var(--surface-raised)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg pl-9 pr-3 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none transition-colors"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          <Filter size={14} className="text-[var(--text-tertiary)]" />
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="bg-[var(--surface-raised)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none cursor-pointer"
          >
            <option value="" className="bg-[var(--surface-panel)]">All Storage Tiers</option>
            <option value="NVME_TIER1" className="bg-[var(--surface-panel)]">Tier 1 NVMe</option>
            <option value="SAS_TIER2" className="bg-[var(--surface-panel)]">Tier 2 Enterprise SAS</option>
            <option value="HDD_ARCHIVE" className="bg-[var(--surface-panel)]">Tier 3 Cold Archive</option>
          </select>
        </div>
      </div>

      {/* Grid of Devices */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {devices.map((d) => (
          <div
            key={d.id}
            className="glass-panel rounded-xl p-5 flex flex-col justify-between hover:border-[var(--accent-cyan)]/40 transition-all group"
          >
            <div>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">{d.name}</h3>
                  <div className="text-[11px] font-mono text-[var(--accent-cyan)] mt-0.5">{d.id}</div>
                </div>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono ${
                    d.status === 'HEALTHY'
                      ? 'bg-[var(--color-success)]/15 text-[var(--color-success)] border border-[var(--color-success)]/40 shadow-sm'
                      : 'bg-[var(--color-warning)]/15 text-[var(--color-warning)] border border-[var(--color-warning)]/40 shadow-sm'
                  }`}
                >
                  {d.status}
                </span>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                <div className="bg-[var(--surface-raised)]/60 rounded-xl p-2.5 border border-[var(--border-subtle)]">
                  <div className="text-[var(--text-tertiary)] text-[10px] uppercase font-mono tracking-wider">Media & Tier</div>
                  <div className="text-[var(--text-primary)] font-semibold mt-0.5 font-mono">{d.tier}</div>
                  <div className="text-[var(--text-secondary)] text-[10px] truncate">{d.media_type}</div>
                </div>
                <div className="bg-[var(--surface-raised)]/60 rounded-xl p-2.5 border border-[var(--border-subtle)]">
                  <div className="text-[var(--text-tertiary)] text-[10px] uppercase font-mono tracking-wider">Workload Profile</div>
                  <div className="text-[var(--text-primary)] font-semibold mt-0.5 truncate">{d.workload_profile}</div>
                  <div className="text-[var(--text-secondary)] text-[10px]">Active IOPS: {(d.current_read_iops + d.current_write_iops).toLocaleString()}</div>
                </div>
              </div>

              {/* Progress */}
              <div className="mt-4">
                <div className="flex justify-between text-xs font-mono mb-1.5">
                  <span className="text-[var(--text-secondary)]">Capacity Used</span>
                  <span className="text-[var(--text-primary)] font-semibold">
                    {formatTB(d.current_used_bytes)} / {formatTB(d.total_capacity_bytes)} ({d.current_utilization_pct.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-[var(--surface-raised)] h-2 rounded-full overflow-hidden p-0.5 border border-[var(--border-subtle)]">
                  <div
                    className={`h-full rounded-full transition-all ${
                      d.current_utilization_pct >= d.critical_threshold_pct
                        ? 'bg-[var(--color-critical)] shadow-[0_0_6px_var(--color-critical)]'
                        : d.current_utilization_pct >= d.warning_threshold_pct
                        ? 'bg-[var(--color-warning)] shadow-[0_0_6px_var(--color-warning)]'
                        : 'bg-gradient-to-r from-[var(--accent-blue)] to-[var(--accent-cyan)] shadow-[0_0_6px_var(--accent-cyan)]'
                    }`}
                    style={{ width: `${Math.min(100, d.current_utilization_pct)}%` }}
                  />
                </div>
              </div>

              {/* Threshold info */}
              <div className="mt-3 flex items-center justify-between text-[11px] text-[var(--text-tertiary)] font-mono">
                <span>Warn: {d.warning_threshold_pct}% | Crit: {d.critical_threshold_pct}%</span>
                <span>Max Latency SLA: {d.max_acceptable_latency_ms}ms</span>
              </div>
            </div>

            <div className="mt-5 pt-3.5 border-t border-[var(--border-subtle)] flex items-center justify-between gap-2">
              <button
                onClick={() => openEditModal(d)}
                className="px-3 py-1.5 rounded-lg btn-aurora-secondary text-xs flex items-center gap-1.5 font-medium"
              >
                <Sliders size={13} />
                Configure Thresholds
              </button>

              <button
                onClick={() => onNavigateToIntelligence(d.id)}
                className="px-3.5 py-1.5 rounded-lg btn-aurora-primary text-xs flex items-center gap-1.5 font-semibold"
              >
                Deep Intelligence <ArrowUpRight size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Threshold Edit Modal */}
      {editingDevice && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center p-4 z-50">
          <div className="glass-modal max-w-md w-full p-6 space-y-4 shadow-glass-modal animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[var(--accent-cyan)]/15 border border-[var(--accent-cyan)]/30 flex items-center justify-center text-[var(--accent-cyan)]">
                  <Sliders size={16} />
                </div>
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  Safety Envelope: {editingDevice.name}
                </h3>
              </div>
              <button
                onClick={() => setEditingDevice(null)}
                className="p-1.5 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] rounded-lg transition-colors"
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
                  Warning Threshold (% Utilization):
                </label>
                <input
                  type="number"
                  min="50"
                  max="95"
                  value={warnThreshold}
                  onChange={(e) => setWarnThreshold(Number(e.target.value))}
                  className="w-full bg-[var(--surface-panel)] border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-2 text-[var(--text-primary)] font-mono focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] mb-1 text-[11px] uppercase tracking-wider font-medium">
                  Critical Hard Limit (% Utilization):
                </label>
                <input
                  type="number"
                  min="60"
                  max="99"
                  value={critThreshold}
                  onChange={(e) => setCritThreshold(Number(e.target.value))}
                  className="w-full bg-[var(--surface-panel)] border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-2 text-[var(--text-primary)] font-mono focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] mb-1 text-[11px] uppercase tracking-wider font-medium">
                  Maximum Latency SLA (ms):
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={maxLat}
                  onChange={(e) => setMaxLat(Number(e.target.value))}
                  className="w-full bg-[var(--surface-panel)] border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-2 text-[var(--text-primary)] font-mono focus:outline-none"
                />
              </div>
            </div>

            {saveMsg && (
              <div className="text-xs text-[var(--color-success)] bg-[var(--color-success)]/10 border border-[var(--color-success)]/30 p-2.5 rounded-lg font-medium font-mono">
                {saveMsg}
              </div>
            )}

            <div className="flex justify-end gap-2.5 pt-3.5 border-t border-[var(--border-subtle)]">
              <button
                onClick={() => setEditingDevice(null)}
                className="px-3.5 py-1.5 rounded-lg btn-aurora-secondary text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveThresholds}
                className="px-4 py-1.5 rounded-lg btn-aurora-primary font-semibold text-xs"
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
