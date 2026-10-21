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
  CheckCircle2,
  AlertTriangle,
  Layers,
  Database,
  Radio,
  Sliders,
  TrendingUp,
  Zap,
  Info
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
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
              <Activity className="text-obsidian-cyan" size={22} />
              Executive Storage Resilience Overview
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-obsidian-cyan/15 text-obsidian-cyan border border-obsidian-cyan/40">
              SYNTHETIC DEMO DATA
            </span>
          </div>
          <p className="text-xs text-obsidian-muted mt-1 leading-relaxed">
            Multi-horizon risk envelope and lead-time estimation derived from calibrated quantile forecasting.
          </p>
        </div>

        {/* Horizon selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-obsidian-muted font-medium">Prediction Horizon:</span>
            {[24, 72, 168].map((h) => (
              <button
                key={h}
                onClick={() => setHorizonHours(h)}
                className={`px-2.5 py-1 rounded text-xs font-mono font-medium border transition-colors ${
                  horizonHours === h
                    ? 'bg-obsidian-cyan/15 border-obsidian-cyan text-obsidian-cyan font-bold'
                    : 'bg-obsidian-panel border-obsidian-border text-obsidian-muted hover:text-obsidian-text'
                }`}
              >
                +{h}h
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Visual Status Legend */}
      <div className="bg-obsidian-panel border border-obsidian-border rounded-lg px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="text-obsidian-muted font-semibold flex items-center gap-2">
          <Info size={14} className="text-obsidian-cyan" />
          <span>Telemetry Status Differentiation:</span>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono">
          <span className="flex items-center gap-1.5 text-obsidian-text">
            <span className="w-3 h-1 bg-obsidian-cyan inline-block rounded-sm"></span>
            OBSERVED DATA
          </span>
          <span className="flex items-center gap-1.5 text-obsidian-violet">
            <span className="w-3 h-1 bg-obsidian-violet inline-block rounded-sm"></span>
            FORECAST [q10, q90]
          </span>
          <span className="flex items-center gap-1.5 text-obsidian-teal">
            <span className="w-3 h-0.5 border-t border-dashed border-obsidian-teal inline-block"></span>
            SIMULATED SCENARIO
          </span>
          <span className="flex items-center gap-1.5 text-obsidian-muted">
            <span className="w-3 h-1 bg-obsidian-secondary border border-obsidian-border inline-block rounded-sm"></span>
            UNAVAILABLE OR INSUFFICIENT EVIDENCE
          </span>
        </div>
      </div>

      {/* KPI Tiles (8 Critical Dimensions) */}
      {overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Tile 1: Capacity Utilization */}
          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium flex items-center justify-between">
              <span>Fleet Storage Capacity</span>
              <span className="text-obsidian-cyan font-mono text-[11px]">
                {formatTB(overview.total_used_bytes)} / {formatTB(overview.total_capacity_bytes)}
              </span>
            </div>
            <div className="text-2xl font-bold font-mono text-obsidian-text mt-2">
              {overview.capacity_utilization_pct.toFixed(1)}%
            </div>
            <div className="w-full bg-obsidian-secondary h-1.5 rounded-full overflow-hidden mt-2">
              <div
                className={`h-full ${overview.capacity_utilization_pct > 85 ? 'bg-obsidian-coral' : 'bg-obsidian-cyan'}`}
                style={{ width: `${Math.min(100, overview.capacity_utilization_pct)}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-[10px] text-obsidian-muted font-mono mt-2">
              <span>Available: {formatTB(overview.total_free_bytes)}</span>
              <span>Total: {formatTB(overview.total_capacity_bytes)}</span>
            </div>
          </div>

          {/* Tile 2: Estimated Reserve Runway */}
          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium flex items-center justify-between">
              <span>Shortest Reserve Runway</span>
              <Clock size={15} className="text-obsidian-amber" />
            </div>
            <div className="text-2xl font-bold font-mono text-obsidian-amber mt-2">
              ~{overview.estimated_reserve_runway_hours.toFixed(1)} hrs
            </div>
            <p className="text-[11px] text-obsidian-muted mt-2">
              Earliest critical threshold breach on <span className="text-obsidian-text font-mono">{overview.highest_current_risk.device_id}</span>.
            </p>
          </div>

          {/* Tile 3: Highest Risk & Device Count */}
          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium flex items-center justify-between">
              <span>Fleet Risk Status</span>
              <ShieldAlert size={15} className="text-obsidian-coral" />
            </div>
            <div className="text-2xl font-bold font-mono text-obsidian-coral mt-2 flex items-center gap-2">
              <span>{overview.highest_current_risk.level}</span>
            </div>
            <p className="text-[11px] text-obsidian-muted mt-2">
              {overview.monitored_device_count} pools actively monitored across NVMe, SAS, and Cold tiers.
            </p>
          </div>

          {/* Tile 4: Last Collection & Telemetry Health */}
          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium flex items-center justify-between">
              <span>Last Telemetry Sync</span>
              <Radio size={14} className="text-obsidian-teal animate-pulse" />
            </div>
            <div className="text-sm font-bold font-mono text-obsidian-text mt-2 truncate">
              {new Date(overview.last_successful_collection).toLocaleTimeString()} UTC
            </div>
            <div className="text-[11px] text-obsidian-muted font-mono mt-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-obsidian-teal"></span>
              <span>Heartbeat: 100% nominal cadence</span>
            </div>
          </div>
        </div>
      )}

      {/* Storage Pool Selector & Main Capacity Forecast Fan Chart */}
      <div className="space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-obsidian-text">Inspect Storage Pool:</span>
            <select
              value={selectedDeviceId}
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              className="bg-obsidian-panel border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text font-mono focus:border-obsidian-cyan cursor-pointer"
            >
              {devices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.id})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => onNavigateToTwin(selectedDeviceId)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-obsidian-cyan/15 border border-obsidian-cyan/50 text-obsidian-cyan hover:bg-obsidian-cyan/25 transition-colors font-semibold"
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
        <div className="lg:col-span-2 bg-obsidian-panel border border-obsidian-border rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-obsidian-text flex items-center gap-2">
              <Clock className="text-obsidian-amber" size={16} />
              Operational Risk & Incident Timeline
            </h3>
            <span className="text-[11px] font-mono text-obsidian-muted">Chronological Progression</span>
          </div>

          <div className="space-y-3">
            {overview?.risk_timeline.map((item) => (
              <div
                key={item.id}
                className={`flex items-start gap-3 p-3 rounded border text-xs ${
                  item.severity === 'CRITICAL'
                    ? 'bg-obsidian-coral/10 border-obsidian-coral/30 text-obsidian-coral'
                    : 'bg-obsidian-secondary/50 border-obsidian-border/50 text-obsidian-text'
                }`}
              >
                <div className="mt-0.5">
                  {item.severity === 'CRITICAL' ? (
                    <ShieldAlert size={16} className="text-obsidian-coral" />
                  ) : (
                    <AlertTriangle size={16} className="text-obsidian-amber" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold">{item.title}</span>
                    <span className="text-[10px] font-mono text-obsidian-muted">
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="text-[11px] text-obsidian-muted font-mono mt-1">
                    Pool: <span className="text-obsidian-cyan">{item.device_id}</span> | Category: {item.category}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Ranked Recommendation Panel (1 col) */}
        <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-obsidian-text flex items-center gap-2">
                <Sliders className="text-obsidian-cyan" size={16} />
                Ranked Action
              </h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-obsidian-cyan/15 text-obsidian-cyan border border-obsidian-cyan/40">
                #1 Recommended
              </span>
            </div>

            {overview?.top_recommendation ? (
              <div className="mt-3 space-y-3 text-xs">
                <div className="font-bold text-obsidian-text text-sm">
                  {overview.top_recommendation.title}
                </div>
                <div className="bg-obsidian-secondary/50 rounded p-3 border border-obsidian-border/50 space-y-1 font-mono text-[11px]">
                  <div>Target: <span className="text-obsidian-cyan font-bold">{overview.top_recommendation.device_id}</span></div>
                  <div>Type: <span className="text-obsidian-text font-bold">{overview.top_recommendation.action_type}</span></div>
                  <div>Runway Gain: <span className="text-obsidian-amber font-bold">+{overview.top_recommendation.estimated_runway_gain_hours} hrs</span></div>
                  <div>Utility Score: <span className="text-obsidian-teal font-bold">{overview.top_recommendation.utility_score.toFixed(1)}</span></div>
                </div>
                <p className="text-obsidian-muted text-xs leading-relaxed">
                  Evaluated against Hard Safety Envelope. Disqualifies interventions that violate latency SLAs during data tiering.
                </p>
              </div>
            ) : (
              <div className="text-xs text-obsidian-muted mt-3">
                No immediate critical intervention required.
              </div>
            )}
          </div>

          <button
            onClick={() => onNavigateToTwin(overview?.top_recommendation?.device_id || selectedDeviceId)}
            className="w-full mt-4 py-2 px-3 rounded bg-obsidian-cyan hover:opacity-90 text-obsidian-bg font-bold text-xs flex items-center justify-center gap-1.5 transition-opacity"
          >
            Launch Digital Twin Sandbox <ArrowUpRight size={13} />
          </button>
        </div>
      </div>

      {/* Storage Devices Table */}
      <div className="bg-obsidian-panel border border-obsidian-border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-obsidian-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-obsidian-text">Monitored Storage Pools & Health</h3>
          <span className="text-xs text-obsidian-muted font-mono">{devices.length} Monitored Devices</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-obsidian-secondary/50 text-obsidian-muted uppercase text-[10px] border-b border-obsidian-border">
              <tr>
                <th className="px-4 py-2.5">Storage Pool</th>
                <th className="px-4 py-2.5">Tier & Profile</th>
                <th className="px-4 py-2.5">Used / Total</th>
                <th className="px-4 py-2.5">Utilization</th>
                <th className="px-4 py-2.5">P95 Latency</th>
                <th className="px-4 py-2.5">Reserve Runway</th>
                <th className="px-4 py-2.5">Risk Level</th>
                <th className="px-4 py-2.5 text-right">Drilldown</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-obsidian-border">
              {devices.map((d) => (
                <tr key={d.id} className="hover:bg-obsidian-raised/40 transition-colors">
                  <td className="px-4 py-3 font-semibold text-obsidian-text font-sans">
                    {d.name}
                    <div className="text-[10px] font-mono text-obsidian-cyan">{d.id}</div>
                  </td>
                  <td className="px-4 py-3 text-obsidian-muted font-sans">
                    {d.tier}
                    <div className="text-[10px] text-obsidian-muted font-mono">{d.workload_profile}</div>
                  </td>
                  <td className="px-4 py-3 text-obsidian-text">
                    {formatTB(d.current_used_bytes)} / {formatTB(d.total_capacity_bytes)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="w-10">{d.current_utilization_pct.toFixed(1)}%</span>
                      <div className="w-16 bg-obsidian-secondary h-1.5 rounded-full overflow-hidden">
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
                  </td>
                  <td className="px-4 py-3 text-obsidian-text">{d.current_latency_p95_ms.toFixed(1)} ms</td>
                  <td className="px-4 py-3 text-obsidian-amber font-bold">~{d.runway_hours_estimate.toFixed(1)} hrs</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        d.risk_level === 'CRITICAL'
                          ? 'bg-obsidian-coral/20 text-obsidian-coral border border-obsidian-coral/40'
                          : d.risk_level === 'ELEVATED'
                          ? 'bg-obsidian-amber/20 text-obsidian-amber border border-obsidian-amber/40'
                          : 'bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40'
                      }`}
                    >
                      {d.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => onNavigateToDevice(d.id)}
                      className="px-2.5 py-1 rounded bg-obsidian-secondary hover:bg-obsidian-raised border border-obsidian-border text-obsidian-cyan hover:border-obsidian-cyan text-[11px] font-sans inline-flex items-center gap-1 transition-colors"
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
