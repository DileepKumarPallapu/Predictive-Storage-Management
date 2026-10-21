import React, { useState, useEffect } from 'react';
import { api, DeviceSummary } from '../api/client';
import { HardDrive, Search, Filter, Sliders, CheckCircle2, AlertTriangle, ArrowUpRight } from 'lucide-react';

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
        <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
          <HardDrive className="text-obsidian-cyan" size={22} />
          Storage Fleet Inventory & Service Constraints
        </h2>
        <p className="text-xs text-obsidian-muted mt-1">
          Catalog of physical pools, active workloads, provisioned thresholds, and live health metrics.
        </p>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-obsidian-panel border border-obsidian-border rounded-lg p-3">
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 text-obsidian-muted" size={14} />
          <input
            type="text"
            placeholder="Search pool ID or name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-obsidian-secondary border border-obsidian-border rounded pl-8 pr-3 py-1.5 text-xs text-obsidian-text focus:outline-none focus:border-obsidian-cyan"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter size={14} className="text-obsidian-muted" />
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value)}
            className="bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text focus:outline-none focus:border-obsidian-cyan cursor-pointer"
          >
            <option value="">All Storage Tiers</option>
            <option value="NVME_TIER1">Tier 1 NVMe</option>
            <option value="SAS_TIER2">Tier 2 Enterprise SAS</option>
            <option value="HDD_ARCHIVE">Tier 3 Cold Archive</option>
          </select>
        </div>
      </div>

      {/* Grid of Devices */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {devices.map((d) => (
          <div
            key={d.id}
            className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5 flex flex-col justify-between hover:border-obsidian-cyan/50 transition-colors"
          >
            <div>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-obsidian-text">{d.name}</h3>
                  <div className="text-[11px] font-mono text-obsidian-cyan mt-0.5">{d.id}</div>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                    d.status === 'HEALTHY'
                      ? 'bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40'
                      : 'bg-obsidian-amber/20 text-obsidian-amber border border-obsidian-amber/40'
                  }`}
                >
                  {d.status}
                </span>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                <div className="bg-obsidian-secondary/50 rounded p-2 border border-obsidian-border/50">
                  <div className="text-obsidian-muted text-[10px]">Media & Tier</div>
                  <div className="text-obsidian-text font-medium mt-0.5 font-mono">{d.tier}</div>
                  <div className="text-obsidian-muted text-[10px] truncate">{d.media_type}</div>
                </div>
                <div className="bg-obsidian-secondary/50 rounded p-2 border border-obsidian-border/50">
                  <div className="text-obsidian-muted text-[10px]">Workload Profile</div>
                  <div className="text-obsidian-text font-medium mt-0.5 truncate">{d.workload_profile}</div>
                  <div className="text-obsidian-muted text-[10px]">Active IOPS: {(d.current_read_iops + d.current_write_iops).toLocaleString()}</div>
                </div>
              </div>

              {/* Progress */}
              <div className="mt-4">
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-obsidian-muted">Capacity Used</span>
                  <span className="text-obsidian-text font-semibold">
                    {formatTB(d.current_used_bytes)} / {formatTB(d.total_capacity_bytes)} ({d.current_utilization_pct.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-obsidian-secondary h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      d.current_utilization_pct >= d.critical_threshold_pct
                        ? 'bg-obsidian-coral'
                        : d.current_utilization_pct >= d.warning_threshold_pct
                        ? 'bg-obsidian-amber'
                        : 'bg-obsidian-teal'
                    }`}
                    style={{ width: `${Math.min(100, d.current_utilization_pct)}%` }}
                  ></div>
                </div>
              </div>

              {/* Threshold info */}
              <div className="mt-3 flex items-center justify-between text-[11px] text-obsidian-muted font-mono">
                <span>Warn: {d.warning_threshold_pct}% | Crit: {d.critical_threshold_pct}%</span>
                <span>Max Latency SLA: {d.max_acceptable_latency_ms}ms</span>
              </div>
            </div>

            <div className="mt-5 pt-3 border-t border-obsidian-border flex items-center justify-between gap-2">
              <button
                onClick={() => openEditModal(d)}
                className="px-3 py-1.5 rounded bg-obsidian-secondary hover:bg-obsidian-raised border border-obsidian-border text-obsidian-muted hover:text-obsidian-text text-xs flex items-center gap-1.5 transition-colors font-medium"
              >
                <Sliders size={13} />
                Configure Thresholds
              </button>

              <button
                onClick={() => onNavigateToIntelligence(d.id)}
                className="px-3 py-1.5 rounded bg-obsidian-cyan/10 hover:bg-obsidian-cyan/20 border border-obsidian-cyan/40 text-obsidian-cyan text-xs flex items-center gap-1 font-medium transition-colors"
              >
                Deep Intelligence <ArrowUpRight size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Threshold Edit Modal */}
      {editingDevice && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-obsidian-text">
              Configure Hard Safety Envelope: {editingDevice.name}
            </h3>
            <p className="text-xs text-obsidian-muted">
              Adjust warning and critical capacity limits. The digital twin simulator will refuse any intervention that violates these constraints.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-obsidian-muted mb-1">Warning Threshold (% Utilization):</label>
                <input
                  type="number"
                  min="50"
                  max="95"
                  value={warnThreshold}
                  onChange={(e) => setWarnThreshold(Number(e.target.value))}
                  className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-2 text-obsidian-text font-mono focus:border-obsidian-cyan"
                />
              </div>

              <div>
                <label className="block text-obsidian-muted mb-1">Critical Hard Limit (% Utilization):</label>
                <input
                  type="number"
                  min="60"
                  max="99"
                  value={critThreshold}
                  onChange={(e) => setCritThreshold(Number(e.target.value))}
                  className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-2 text-obsidian-text font-mono focus:border-obsidian-cyan"
                />
              </div>

              <div>
                <label className="block text-obsidian-muted mb-1">Maximum Latency SLA (ms):</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={maxLat}
                  onChange={(e) => setMaxLat(Number(e.target.value))}
                  className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-2 text-obsidian-text font-mono focus:border-obsidian-cyan"
                />
              </div>
            </div>

            {saveMsg && (
              <div className="text-xs text-obsidian-teal font-medium font-mono">{saveMsg}</div>
            )}

            <div className="flex justify-end gap-2 pt-3 border-t border-obsidian-border">
              <button
                onClick={() => setEditingDevice(null)}
                className="px-3 py-1.5 rounded bg-obsidian-secondary border border-obsidian-border text-obsidian-muted hover:text-obsidian-text text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveThresholds}
                className="px-4 py-1.5 rounded bg-obsidian-cyan text-obsidian-bg font-semibold text-xs hover:opacity-90 transition-opacity"
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
