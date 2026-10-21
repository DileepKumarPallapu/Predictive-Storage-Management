import React, { useState, useEffect } from 'react';
import {
  api,
  DeviceSummary,
  ForecastResponse,
  TelemetryResponse,
  ExecutiveOverviewResponse
} from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import {
  Activity,
  ShieldAlert,
  Clock,
  ArrowUpRight,
  AlertTriangle,
  Layers,
  Radio,
  Sliders,
  Info,
  Sparkles,
  Server,
  Zap,
  TrendingUp,
  Cpu
} from 'lucide-react';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

interface Props {
  onNavigateToDevice: (deviceId: string) => void;
  onNavigateToTwin: (deviceId: string) => void;
}

export const PageExecutiveOverview: React.FC<Props> = ({ onNavigateToDevice, onNavigateToTwin }) => {
  const [overview, setOverview] = useState<ExecutiveOverviewResponse | null>(null);
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('vol-nvme-tier1-db');
  const [horizonHours, setHorizonHours] = useState<number>(72);
  const [capacityForecast, setCapacityForecast] = useState<ForecastResponse | null>(null);
  const [capacityTelemetry, setCapacityTelemetry] = useState<TelemetryResponse | null>(null);
  const [latencyTelemetry, setLatencyTelemetry] = useState<TelemetryResponse | null>(null);
  const [throughputTelemetry, setThroughputTelemetry] = useState<TelemetryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedDeviceId) {
      loadDeviceCharts(selectedDeviceId, horizonHours);
    }
  }, [selectedDeviceId, horizonHours]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [ov, devList] = await Promise.all([
        api.getOverview(),
        api.getDevices(),
      ]);
      setOverview(ov);
      setDevices(devList);
      if (devList.length > 0) {
        setSelectedDeviceId(devList[0].id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadDeviceCharts = async (devId: string, horizon: number) => {
    try {
      const [capTel, capFc, latTel, tpTel] = await Promise.all([
        api.getTelemetry(devId, 'used_bytes', 168),
        api.getForecast(devId, 'used_bytes', 'lightgbm_quantile', horizon),
        api.getTelemetry(devId, 'latency_p95_ms', 168),
        api.getTelemetry(devId, 'throughput_mb_s', 168),
      ]);
      setCapacityTelemetry(capTel);
      setCapacityForecast(capFc);
      setLatencyTelemetry(latTel);
      setThroughputTelemetry(tpTel);
    } catch (e) {
      console.error(e);
    }
  };

  const formatTB = (bytes: number) => (bytes / (1024 ** 4)).toFixed(1) + ' TB';

  if (loading && !overview) {
    return <LoadingSkeleton rows={8} height="h-10" />;
  }

  return (
    <div className="space-y-6">
      {/* Header & Synthetic Data Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent-cyan)]/15 border border-[var(--accent-cyan)]/30 flex items-center justify-center text-[var(--accent-cyan)] shadow-[0_0_12px_rgba(85,214,255,0.2)]">
              <Activity size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              Executive Storage Resilience Overview
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--accent-cyan)]/15 text-[var(--accent-cyan)] border border-[var(--accent-cyan)]/35 shadow-sm">
              SYNTHETIC DEMO DATA
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
            Multi-horizon risk envelope and lead-time estimation derived from calibrated quantile forecasting.
          </p>
        </div>

        {/* Horizon selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-[var(--text-secondary)] font-medium">Prediction Horizon:</span>
            {[24, 72, 168].map((h) => (
              <button
                key={h}
                onClick={() => setHorizonHours(h)}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium border transition-all ${
                  horizonHours === h
                    ? 'bg-[var(--accent-cyan)]/15 border-[var(--accent-cyan)] text-[var(--accent-cyan)] font-bold shadow-[0_0_10px_rgba(85,214,255,0.25)]'
                    : 'glass-panel text-[var(--text-secondary)] hover:text-[var(--text-primary)] border-[var(--border-subtle)]'
                }`}
              >
                +{h}h
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Visual Status Legend */}
      <div className="glass-panel rounded-xl px-4 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="text-[var(--text-secondary)] font-semibold flex items-center gap-2">
          <Info size={14} className="text-[var(--accent-cyan)]" />
          <span>Telemetry Status Differentiation:</span>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono">
          <span className="flex items-center gap-1.5 text-[var(--text-primary)]">
            <span className="w-3 h-1 bg-[var(--accent-cyan)] inline-block rounded-full shadow-[0_0_6px_var(--accent-cyan)]"></span>
            OBSERVED DATA
          </span>
          <span className="flex items-center gap-1.5 text-[var(--accent-violet)]">
            <span className="w-3 h-1 bg-[var(--accent-violet)] inline-block rounded-full shadow-[0_0_6px_var(--accent-violet)]"></span>
            FORECAST [q10, q90]
          </span>
          <span className="flex items-center gap-1.5 text-[var(--color-success)]">
            <span className="w-3 h-0.5 border-t border-dashed border-[var(--color-success)] inline-block"></span>
            SIMULATED SCENARIO
          </span>
          <span className="flex items-center gap-1.5 text-[var(--text-tertiary)]">
            <span className="w-3 h-1 bg-[var(--surface-raised)] border border-[var(--border-subtle)] inline-block rounded-full"></span>
            UNAVAILABLE / NO EVIDENCE
          </span>
        </div>
      </div>

      {/* KPI Tiles (4 Critical Dimensions with Glass Aurora finish) */}
      {overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Tile 1: Capacity Utilization */}
          <div className="glass-panel rounded-xl p-4 relative overflow-hidden group hover:border-[var(--accent-cyan)]/40 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-[var(--accent-cyan)]/10 to-transparent rounded-bl-full pointer-events-none" />
            <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span>Fleet Storage Capacity</span>
              <span className="text-[var(--accent-cyan)] font-mono text-[11px]">
                {formatTB(overview.total_used_bytes)} / {formatTB(overview.total_capacity_bytes)}
              </span>
            </div>
            <div className="text-2xl font-bold font-mono text-[var(--text-primary)] mt-2">
              {overview.capacity_utilization_pct.toFixed(1)}%
            </div>
            <div className="w-full bg-[var(--surface-raised)] h-2 rounded-full overflow-hidden mt-2.5 p-0.5 border border-[var(--border-subtle)]">
              <div
                className={`h-full rounded-full transition-all ${
                  overview.capacity_utilization_pct > 85
                    ? 'bg-[var(--color-critical)] shadow-[0_0_8px_var(--color-critical)]'
                    : 'bg-gradient-to-r from-[var(--accent-blue)] to-[var(--accent-cyan)] shadow-[0_0_8px_var(--accent-cyan)]'
                }`}
                style={{ width: `${Math.min(100, overview.capacity_utilization_pct)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-[var(--text-tertiary)] font-mono mt-2">
              <span>Available: {formatTB(overview.total_free_bytes)}</span>
              <span>Total: {formatTB(overview.total_capacity_bytes)}</span>
            </div>
          </div>

          {/* Tile 2: Estimated Reserve Runway */}
          <div className="glass-panel rounded-xl p-4 relative overflow-hidden group hover:border-[var(--color-warning)]/40 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-[var(--color-warning)]/10 to-transparent rounded-bl-full pointer-events-none" />
            <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span>Shortest Reserve Runway</span>
              <Clock size={15} className="text-[var(--color-warning)]" />
            </div>
            <div className="text-2xl font-bold font-mono text-[var(--color-warning)] mt-2">
              ~{overview.estimated_reserve_runway_hours.toFixed(1)} hrs
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-2">
              Earliest critical breach on <span className="text-[var(--text-primary)] font-mono font-semibold">{overview.highest_current_risk.device_id}</span>.
            </p>
          </div>

          {/* Tile 3: Highest Risk & Device Count */}
          <div className="glass-panel rounded-xl p-4 relative overflow-hidden group hover:border-[var(--color-critical)]/40 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-[var(--color-critical)]/10 to-transparent rounded-bl-full pointer-events-none" />
            <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span>Fleet Risk Status</span>
              <ShieldAlert size={15} className="text-[var(--color-critical)]" />
            </div>
            <div className="text-2xl font-bold font-mono text-[var(--color-critical)] mt-2 flex items-center gap-2">
              <span>{overview.highest_current_risk.level}</span>
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-2">
              {overview.monitored_device_count} pools actively monitored across NVMe, SAS, and Cold tiers.
            </p>
          </div>

          {/* Tile 4: Last Collection & Telemetry Health */}
          <div className="glass-panel rounded-xl p-4 relative overflow-hidden group hover:border-[var(--color-success)]/40 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-[var(--color-success)]/10 to-transparent rounded-bl-full pointer-events-none" />
            <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span>Last Telemetry Sync</span>
              <Radio size={14} className="text-[var(--color-success)] animate-pulse" />
            </div>
            <div className="text-sm font-bold font-mono text-[var(--text-primary)] mt-2 truncate">
              {new Date(overview.last_successful_collection).toLocaleTimeString()} UTC
            </div>
            <div className="text-[11px] text-[var(--text-secondary)] font-mono mt-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[var(--color-success)] shadow-[0_0_6px_var(--color-success)]"></span>
              <span>Heartbeat: 100% nominal cadence</span>
            </div>
          </div>
        </div>
      )}

      {/* Storage Pool Selector & Main Capacity Forecast Fan Chart */}
      <div className="space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-[var(--text-primary)]">Inspect Storage Pool:</span>
            <select
              value={selectedDeviceId}
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              className="bg-[var(--surface-panel)] border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono cursor-pointer focus:outline-none"
            >
              {devices.map((d) => (
                <option key={d.id} value={d.id} className="bg-[var(--surface-raised)] text-[var(--text-primary)]">
                  {d.name} ({d.id})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => onNavigateToTwin(selectedDeviceId)}
            className="btn-aurora-primary flex items-center gap-1.5 px-3.5 py-1.5 text-xs rounded-lg font-semibold"
          >
            <Layers size={14} />
            Simulate Counterfactuals in Digital Twin
          </button>
        </div>

        {/* Central Capacity Forecast Fan Chart */}
        {capacityTelemetry && capacityForecast && (
          <ScientificForecastChart
            title={`Capacity Trajectory & Prediction Interval — ${capacityForecast.model_name}`}
            historicalTimestamps={capacityTelemetry.timestamps}
            historicalValues={capacityTelemetry.values}
            forecastTimestamps={capacityForecast.timestamps}
            q10={capacityForecast.q10}
            q50={capacityForecast.q50}
            q90={capacityForecast.q90}
            hardConstraint={capacityForecast.hard_constraint_value}
            units="Bytes"
            isBytes={true}
          />
        )}
      </div>

      {/* Latency and Throughput Charts Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {latencyTelemetry && (
          <ScientificForecastChart
            title={`P95 Tail Latency History — ${selectedDeviceId}`}
            historicalTimestamps={latencyTelemetry.timestamps}
            historicalValues={latencyTelemetry.values}
            units="ms"
            isBytes={false}
          />
        )}

        {throughputTelemetry && (
          <ScientificForecastChart
            title={`Throughput History (MB/s) — ${selectedDeviceId}`}
            historicalTimestamps={throughputTelemetry.timestamps}
            historicalValues={throughputTelemetry.values}
            units="MB/s"
            isBytes={false}
          />
        )}
      </div>

      {/* Risk Timeline & Ranked Recommendation Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Timeline (2 cols) */}
        <div className="lg:col-span-2 glass-panel rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Clock className="text-[var(--color-warning)]" size={16} />
              Operational Risk & Incident Timeline
            </h3>
            <span className="text-[11px] font-mono text-[var(--text-tertiary)]">Chronological Progression</span>
          </div>

          <div className="space-y-3">
            {overview?.risk_timeline.map((item) => (
              <div
                key={item.id}
                className={`flex items-start gap-3 p-3.5 rounded-xl border text-xs transition-all ${
                  item.severity === 'CRITICAL'
                    ? 'bg-[var(--color-critical)]/10 border-[var(--color-critical)]/30 text-[var(--color-critical)]'
                    : 'bg-[var(--surface-raised)]/60 border-[var(--border-subtle)] text-[var(--text-primary)]'
                }`}
              >
                <div className="mt-0.5">
                  {item.severity === 'CRITICAL' ? (
                    <ShieldAlert size={16} className="text-[var(--color-critical)]" />
                  ) : (
                    <AlertTriangle size={16} className="text-[var(--color-warning)]" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{item.title}</span>
                    <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="text-[11px] text-[var(--text-secondary)] font-mono mt-1">
                    Pool: <span className="text-[var(--accent-cyan)] font-semibold">{item.device_id}</span> | Category: {item.category}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Ranked Recommendation Panel (1 col) */}
        <div className="glass-panel rounded-xl p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <Sliders className="text-[var(--accent-cyan)]" size={16} />
                Ranked Action
              </h3>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-[var(--accent-cyan)]/15 text-[var(--accent-cyan)] border border-[var(--accent-cyan)]/40 shadow-sm">
                #1 Recommended
              </span>
            </div>

            {overview?.top_recommendation ? (
              <div className="mt-3.5 space-y-3 text-xs">
                <div className="font-semibold text-[var(--text-primary)] text-sm">
                  {overview.top_recommendation.title}
                </div>
                <div className="bg-[var(--surface-raised)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)] space-y-1.5 font-mono text-[11px]">
                  <div>Target: <span className="text-[var(--accent-cyan)] font-bold">{overview.top_recommendation.device_id}</span></div>
                  <div>Type: <span className="text-[var(--text-primary)] font-bold">{overview.top_recommendation.action_type}</span></div>
                  <div>Runway Gain: <span className="text-[var(--color-warning)] font-bold">+{overview.top_recommendation.estimated_runway_gain_hours} hrs</span></div>
                  <div>Utility Score: <span className="text-[var(--color-success)] font-bold">{overview.top_recommendation.utility_score.toFixed(1)}</span></div>
                </div>
                <p className="text-[var(--text-secondary)] text-xs leading-relaxed">
                  Evaluated against Hard Safety Envelope. Disqualifies interventions that violate latency SLAs during data tiering.
                </p>
              </div>
            ) : (
              <div className="text-xs text-[var(--text-secondary)] mt-3">
                No immediate critical intervention required.
              </div>
            )}
          </div>

          <button
            onClick={() => onNavigateToTwin(overview?.top_recommendation?.device_id || selectedDeviceId)}
            className="w-full mt-4 py-2.5 px-3 rounded-lg btn-aurora-primary font-bold text-xs flex items-center justify-center gap-1.5"
          >
            Launch Digital Twin Sandbox <ArrowUpRight size={13} />
          </button>
        </div>
      </div>

      {/* Storage Devices Table */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Monitored Storage Pools & Health</h3>
          <span className="text-xs text-[var(--text-secondary)] font-mono">{devices.length} Monitored Devices</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[var(--surface-raised)]/60 text-[var(--text-secondary)] uppercase text-[10px] border-b border-[var(--border-subtle)]">
              <tr>
                <th className="px-5 py-3 font-semibold">Storage Pool</th>
                <th className="px-5 py-3 font-semibold">Tier & Profile</th>
                <th className="px-5 py-3 font-semibold">Used / Total</th>
                <th className="px-5 py-3 font-semibold">Utilization</th>
                <th className="px-5 py-3 font-semibold">P95 Latency</th>
                <th className="px-5 py-3 font-semibold">Reserve Runway</th>
                <th className="px-5 py-3 font-semibold">Risk Level</th>
                <th className="px-5 py-3 font-semibold text-right">Drilldown</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {devices.map((d) => (
                <tr key={d.id} className="hover:bg-[var(--surface-raised)]/50 transition-colors">
                  <td className="px-5 py-3.5 font-semibold text-[var(--text-primary)] font-sans">
                    {d.name}
                    <div className="text-[10px] font-mono text-[var(--accent-cyan)] font-normal">{d.id}</div>
                  </td>
                  <td className="px-5 py-3.5 text-[var(--text-secondary)] font-sans">
                    {d.tier}
                    <div className="text-[10px] text-[var(--text-tertiary)] font-mono">{d.workload_profile}</div>
                  </td>
                  <td className="px-5 py-3.5 text-[var(--text-primary)]">
                    {formatTB(d.current_used_bytes)} / {formatTB(d.total_capacity_bytes)}
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <span className="w-10 text-[var(--text-primary)]">{d.current_utilization_pct.toFixed(1)}%</span>
                      <div className="w-20 bg-[var(--surface-raised)] h-2 rounded-full overflow-hidden p-0.5 border border-[var(--border-subtle)]">
                        <div
                          className={`h-full rounded-full ${
                            d.current_utilization_pct >= d.critical_threshold_pct
                              ? 'bg-[var(--color-critical)] shadow-[0_0_6px_var(--color-critical)]'
                              : d.current_utilization_pct >= d.warning_threshold_pct
                              ? 'bg-[var(--color-warning)] shadow-[0_0_6px_var(--color-warning)]'
                              : 'bg-[var(--color-success)] shadow-[0_0_6px_var(--color-success)]'
                          }`}
                          style={{ width: `${Math.min(100, d.current_utilization_pct)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-[var(--text-primary)]">{d.current_latency_p95_ms.toFixed(1)} ms</td>
                  <td className="px-5 py-3.5 text-[var(--color-warning)] font-bold">~{d.runway_hours_estimate.toFixed(1)} hrs</td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        d.risk_level === 'CRITICAL'
                          ? 'bg-[var(--color-critical)]/15 text-[var(--color-critical)] border border-[var(--color-critical)]/40 shadow-sm'
                          : d.risk_level === 'ELEVATED'
                          ? 'bg-[var(--color-warning)]/15 text-[var(--color-warning)] border border-[var(--color-warning)]/40 shadow-sm'
                          : 'bg-[var(--color-success)]/15 text-[var(--color-success)] border border-[var(--color-success)]/40 shadow-sm'
                      }`}
                    >
                      {d.risk_level}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button
                      onClick={() => onNavigateToDevice(d.id)}
                      className="px-3 py-1.5 rounded-lg btn-aurora-secondary text-[11px] font-sans inline-flex items-center gap-1.5 font-medium"
                    >
                      Inspect <ArrowUpRight size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
