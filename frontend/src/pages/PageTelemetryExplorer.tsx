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
          <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
            <LineChart className="text-obsidian-cyan" size={22} />
            Telemetry Explorer & Raw Signal Diagnostics
          </h2>
          <p className="text-xs text-obsidian-muted mt-1">
            High-fidelity time-series telemetry inspection, missingness detection, and empirical data export.
          </p>
        </div>

        <button
          onClick={handleExportCsv}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded bg-obsidian-secondary hover:bg-obsidian-raised border border-obsidian-border text-obsidian-text hover:border-obsidian-cyan text-xs font-semibold transition-colors font-mono"
        >
          <Download size={14} className="text-obsidian-cyan" />
          Export Dataset (CSV)
        </button>
      </div>

      {/* Control Bar */}
      <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
        {/* Device select */}
        <div className="flex items-center gap-2">
          <HardDrive size={15} className="text-obsidian-muted" />
          <span className="text-xs text-obsidian-muted font-medium">Device:</span>
          <select
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1 text-xs text-obsidian-text font-mono focus:border-obsidian-cyan cursor-pointer"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.id})
              </option>
            ))}
          </select>
        </div>

        {/* Time range */}
        <div className="flex items-center gap-2">
          <Calendar size={15} className="text-obsidian-muted" />
          <span className="text-xs text-obsidian-muted font-medium">Window:</span>
          {[
            { hours: 24, label: '24 Hours' },
            { hours: 72, label: '3 Days' },
            { hours: 168, label: '7 Days' },
            { hours: 720, label: '30 Days' },
          ].map((t) => (
            <button
              key={t.hours}
              onClick={() => setTimeRangeHours(t.hours)}
              className={`px-2.5 py-1 rounded text-xs font-mono font-medium border transition-colors ${
                timeRangeHours === t.hours
                  ? 'bg-obsidian-cyan/15 border-obsidian-cyan text-obsidian-cyan'
                  : 'bg-obsidian-secondary border-obsidian-border text-obsidian-muted hover:text-obsidian-text'
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
            className={`px-3 py-1.5 rounded text-xs font-medium border transition-all ${
              selectedMetric === m.id
                ? 'bg-obsidian-panel border-obsidian-cyan text-obsidian-cyan shadow-sm font-semibold'
                : 'bg-obsidian-secondary border-obsidian-border text-obsidian-muted hover:text-obsidian-text'
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
        <div className="bg-obsidian-amber/10 border border-obsidian-amber/30 rounded-lg p-4 text-xs text-obsidian-amber space-y-1">
          <div className="font-bold flex items-center gap-2">
            <AlertTriangle size={15} /> Telemetry Gaps Detected (Never Fabricated):
          </div>
          <p className="text-[11px] text-obsidian-muted font-mono">
            Collector recorded {telemetry.missing_intervals.length} intermittent dropout window(s).
          </p>
        </div>
      )}
    </div>
  );
};
