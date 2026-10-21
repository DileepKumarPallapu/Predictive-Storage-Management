import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, TelemetryResponse } from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import { LineChart, Download, Calendar, HardDrive, AlertTriangle } from 'lucide-react';

export const PageTelemetryExplorer: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('vol-nvme-tier1-db');
  const [selectedMetric, setSelectedMetric] = useState<string>('used_bytes');
  const [timeRangeHours, setTimeRangeHours] = useState<number>(168); // 7 days
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    loadDevices();
  }, []);

  useEffect(() => {
    if (selectedDevice) {
      loadTelemetry();
    }
  }, [selectedDevice, selectedMetric, timeRangeHours]);

  const loadDevices = async () => {
    try {
      const list = await api.getDevices();
      setDevices(list);
    } catch (e) {
      console.error(e);
    }
  };

  const loadTelemetry = async () => {
    setLoading(true);
    try {
      const data = await api.getTelemetry(selectedDevice, selectedMetric, timeRangeHours);
      setTelemetry(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCsv = () => {
    window.open(`http://localhost:8000/api/v1/telemetry/export?device_id=${selectedDevice}`, '_blank');
  };

  const metrics = [
    { id: 'used_bytes', label: 'Used Storage Capacity', isBytes: true },
    { id: 'utilization_pct', label: 'Utilization Percentage (%)', isBytes: false },
    { id: 'read_iops', label: 'Read IOPS', isBytes: false },
    { id: 'write_iops', label: 'Write IOPS', isBytes: false },
    { id: 'throughput_mb_s', label: 'Throughput (MB/s)', isBytes: false },
    { id: 'latency_p95_ms', label: 'Tail Latency P95 (ms)', isBytes: false },
    { id: 'queue_depth', label: 'Queue Depth', isBytes: false },
  ];

  const currentMetricCfg = metrics.find((m) => m.id === selectedMetric) || metrics[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent-cyan)]/15 border border-[var(--accent-cyan)]/30 flex items-center justify-center text-[var(--accent-cyan)] shadow-[0_0_12px_rgba(85,214,255,0.2)]">
              <LineChart size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              Telemetry Explorer & Raw Signal Diagnostics
            </h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
            High-fidelity time-series telemetry inspection, missingness detection, and empirical data export.
          </p>
        </div>

        <button
          onClick={handleExportCsv}
          className="btn-aurora-secondary flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold font-mono"
        >
          <Download size={14} className="text-[var(--accent-cyan)]" />
          Export Dataset (CSV)
        </button>
      </div>

      {/* Control Bar */}
      <div className="glass-panel rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        {/* Device select */}
        <div className="flex items-center gap-2">
          <HardDrive size={15} className="text-[var(--text-tertiary)]" />
          <span className="text-xs text-[var(--text-secondary)] font-medium">Device:</span>
          <select
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="bg-[var(--surface-raised)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id} className="bg-[var(--surface-panel)] text-[var(--text-primary)]">
                {d.name} ({d.id})
              </option>
            ))}
          </select>
        </div>

        {/* Time range */}
        <div className="flex items-center gap-2">
          <Calendar size={15} className="text-[var(--text-tertiary)]" />
          <span className="text-xs text-[var(--text-secondary)] font-medium">Window:</span>
          {[
            { hours: 24, label: '24 Hours' },
            { hours: 72, label: '3 Days' },
            { hours: 168, label: '7 Days' },
            { hours: 720, label: '30 Days' },
          ].map((t) => (
            <button
              key={t.hours}
              onClick={() => setTimeRangeHours(t.hours)}
              className={`px-3 py-1 rounded-lg text-xs font-mono font-medium border transition-all ${
                timeRangeHours === t.hours
                  ? 'bg-[var(--accent-cyan)]/15 border-[var(--accent-cyan)] text-[var(--accent-cyan)] font-bold shadow-[0_0_8px_rgba(85,214,255,0.2)]'
                  : 'glass-panel text-[var(--text-secondary)] hover:text-[var(--text-primary)] border-[var(--border-subtle)]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Metric Selector Tabs */}
      <div className="flex flex-wrap gap-2">
        {metrics.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelectedMetric(m.id)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              selectedMetric === m.id
                ? 'bg-[var(--accent-cyan)]/15 border-[var(--accent-cyan)] text-[var(--accent-cyan)] shadow-[0_0_10px_rgba(85,214,255,0.2)] font-semibold'
                : 'glass-panel text-[var(--text-secondary)] hover:text-[var(--text-primary)] border-[var(--border-subtle)]'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Main Chart */}
      {telemetry && (
        <ScientificForecastChart
          title={`${currentMetricCfg.label} — ${selectedDevice}`}
          historicalTimestamps={telemetry.timestamps}
          historicalValues={telemetry.values}
          units={telemetry.units}
          isBytes={currentMetricCfg.isBytes}
        />
      )}

      {/* Missingness Notification if present */}
      {telemetry && telemetry.missing_intervals.length > 0 && (
        <div className="bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/30 rounded-xl p-4 text-xs text-[var(--color-warning)] space-y-1">
          <div className="font-bold flex items-center gap-2">
            <AlertTriangle size={15} /> Telemetry Gaps Detected (Never Fabricated):
          </div>
          <p className="text-[11px] text-[var(--text-secondary)] font-mono">
            Collector recorded {telemetry.missing_intervals.length} intermittent dropout window(s).
          </p>
        </div>
      )}
    </div>
  );
};
