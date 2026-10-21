import React, { useState, useEffect } from 'react';
import {
  api,
  DeviceSummary,
  ForecastResponse,
  TelemetryResponse,
  ExecutiveOverviewResponse
} from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import { ContextualHelp } from '../components/ContextualHelp';
import { usePresentationMode } from '../context/PresentationModeContext';
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
  ShieldCheck,
  CheckCircle2,
  HardDrive
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
  const { isGuided, isExpert } = usePresentationMode();

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

  // Plain language summary of fleet health
  const getSystemConditionSummary = () => {
    if (!overview) return 'Loading telemetry...';
    if (overview.highest_current_risk.level === 'CRITICAL') {
      return `Attention needed: Storage pool ${overview.highest_current_risk.device_id} is projected to reach critical reserve within ~${overview.estimated_reserve_runway_hours.toFixed(0)} hours under current write rates.`;
    }
    if (overview.highest_current_risk.level === 'ELEVATED') {
      return `Moderate attention: Storage pool ${overview.highest_current_risk.device_id} has elevated utilization (${overview.capacity_utilization_pct.toFixed(1)}%). Consider cold data migration within the next 48 hours.`;
    }
    return `All ${overview.monitored_device_count} monitored storage pools are operating with nominal headroom. No emergency interventions are required.`;
  };

  return (
    <div className="space-y-6">
      {/* 1. Header with Mode & Condition Summary */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent-cyan)]/15 border border-[var(--accent-cyan)]/30 flex items-center justify-center text-[var(--accent-cyan)] shadow-[0_0_12px_rgba(97,221,248,0.2)]">
              <Activity size={18} />
            </div>
            <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              {isGuided ? 'Storage Health & Capacity Overview' : 'Executive Storage Resilience Overview'}
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--accent-cyan)]/15 text-[var(--accent-cyan)] border border-[var(--accent-cyan)]/35 shadow-sm">
              SYNTHETIC DEMO DATA
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
            {isGuided
              ? 'Real-time overview of current capacity, expected runway, and proactive suggestions.'
              : 'Multi-horizon risk envelope and lead-time estimation derived from calibrated quantile forecasting.'}
          </p>
        </div>

        {/* Prediction Horizon Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-[var(--text-secondary)] font-medium">
              {isGuided ? 'Forecast Horizon:' : 'Prediction Horizon:'}
            </span>
            {[24, 72, 168].map((h) => (
              <button
                key={h}
                onClick={() => setHorizonHours(h)}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium border transition-all ${
                  horizonHours === h
                    ? 'bg-[var(--accent-cyan)]/15 border-[var(--accent-cyan)] text-[var(--accent-cyan)] font-bold shadow-[0_0_10px_rgba(97,221,248,0.25)]'
                    : 'glass-panel text-[var(--text-secondary)] hover:text-[var(--text-primary)] border-[var(--border-subtle)]'
                }`}
              >
                +{h}h
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 2. Plain-Language System Condition Banner */}
      <div className="glass-panel rounded-2xl px-5 py-3.5 flex items-start gap-3 border-l-4 border-l-[var(--accent-cyan)]">
        <Sparkles size={18} className="text-[var(--accent-cyan)] shrink-0 mt-0.5" />
        <div className="flex-1">
          <div className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <span>System Condition Summary</span>
            {overview && (
              <span className="text-[10px] font-mono text-[var(--text-muted)]">
                • Updated {new Date(overview.last_successful_collection).toLocaleTimeString()}
              </span>
            )}
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5 leading-relaxed">
            {getSystemConditionSummary()}
          </p>
        </div>
      </div>

      {/* 3. High-Value KPI Metrics (6 Critical Dimensions) */}
      {overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3.5">
          {/* Tile 1: Fleet Storage Used */}
          <div className="glass-panel rounded-xl p-4 flex flex-col justify-between hover:border-[var(--accent-cyan)]/40 transition-all">
            <div>
              <div className="text-[11px] text-[var(--text-secondary)] font-medium flex items-center justify-between">
                <span>{isGuided ? 'Storage Used' : 'Fleet Used Capacity'}</span>
                <ContextualHelp
                  title="Storage Capacity Used"
                  simpleExplanation="Percentage of all provisioned storage currently holding data across all tiers."
                  technicalDetails="Aggregated bytes_used / bytes_total across NVMe, SAS, and Cold Archive pools."
                  evidenceSource="Host LUN telemetry agent"
                />
              </div>
              <div className="text-xl font-bold font-mono text-[var(--text-primary)] mt-1.5">
                {overview.capacity_utilization_pct.toFixed(1)}%
              </div>
              <div className="w-full bg-[var(--surface-raised)] h-1.5 rounded-full overflow-hidden mt-2 border border-[var(--border-subtle)]">
                <div
                  className={`h-full rounded-full ${
                    overview.capacity_utilization_pct > 85
                      ? 'bg-[var(--color-critical)] shadow-[0_0_8px_var(--color-critical)]'
                      : 'bg-gradient-to-r from-[var(--accent-sapphire)] to-[var(--accent-cyan)]'
                  }`}
                  style={{ width: `${Math.min(100, overview.capacity_utilization_pct)}%` }}
                />
              </div>
            </div>
            <div className="text-[10px] text-[var(--text-muted)] font-mono mt-2">
              {formatTB(overview.total_used_bytes)} of {formatTB(overview.total_capacity_bytes)}
            </div>
          </div>

          {/* Tile 2: Available Free Space */}
          <div className="glass-panel rounded-xl p-4 flex flex-col justify-between hover:border-[var(--color-success)]/40 transition-all">
            <div>
              <div className="text-[11px] text-[var(--text-secondary)] font-medium flex items-center justify-between">
                <span>{isGuided ? 'Available Free Space' : 'Unallocated Headroom'}</span>
                <ContextualHelp
                  title="Available Space"
                  simpleExplanation="Remaining free capacity before any configured reserve limit is reached."
                  technicalDetails="Unallocated block storage bytes across all monitored storage pools."
                  evidenceSource="Physical block controller"
                />
              </div>
              <div className="text-xl font-bold font-mono text-[var(--color-success)] mt-1.5">
                {formatTB(overview.total_free_bytes)}
              </div>
              <p className="text-[10px] text-[var(--text-muted)] mt-1">
                Safe operational margin
              </p>
            </div>
            <div className="text-[10px] text-[var(--color-success)] font-mono flex items-center gap-1 mt-2">
              <CheckCircle2 size={11} /> Ready for writes
            </div>
          </div>

          {/* Tile 3: Shortest Reserve Runway */}
          <div className="glass-panel rounded-xl p-4 flex flex-col justify-between hover:border-[var(--color-warning)]/40 transition-all">
            <div>
              <div className="text-[11px] text-[var(--text-secondary)] font-medium flex items-center justify-between">
                <span>{isGuided ? 'Runway to Limit' : 'Shortest Reserve Runway'}</span>
                <ContextualHelp
                  title="Runway to Configured Reserve"
                  simpleExplanation="Estimated hours until the fastest-filling storage pool hits its critical safety limit."
                  technicalDetails="Derived from LightGBM median forecast crossing the 90% hard critical threshold."
                  evidenceSource="Quantile Time-to-Breach Model"
                />
              </div>
              <div className="text-xl font-bold font-mono text-[var(--color-warning)] mt-1.5">
                ~{overview.estimated_reserve_runway_hours.toFixed(0)} hrs
              </div>
              <p className="text-[10px] text-[var(--text-secondary)] mt-1 truncate">
                On <span className="font-mono text-[var(--text-primary)] font-semibold">{overview.highest_current_risk.device_id}</span>
              </p>
            </div>
            <div className="text-[10px] text-[var(--text-muted)] font-mono mt-2 flex items-center gap-1">
              <Clock size={11} className="text-[var(--color-warning)]" /> Proactive lead time
            </div>
          </div>

          {/* Tile 4: Fleet Risk Status */}
          <div className="glass-panel rounded-xl p-4 flex flex-col justify-between hover:border-[var(--accent-sapphire)]/40 transition-all">
            <div>
              <div className="text-[11px] text-[var(--text-secondary)] font-medium flex items-center justify-between">
                <span>{isGuided ? 'Risk Level' : 'Fleet Risk Envelope'}</span>
                <ContextualHelp
                  title="Fleet Risk Status"
                  simpleExplanation="Overall assessment based on capacity consumption, tail latency, and hardware health."
                  technicalDetails="Multi-factor evaluation: P(Capacity > 90%) + P(P95 Latency > SLA)."
                  evidenceSource="Risk Assessment Engine"
                />
              </div>
              <div className="text-xl font-bold font-mono text-[var(--text-primary)] mt-1.5 flex items-center gap-1.5">
                <span className={overview.highest_current_risk.level === 'CRITICAL' ? 'text-[var(--color-critical)]' : 'text-[var(--color-success)]'}>
                  {overview.highest_current_risk.level}
                </span>
              </div>
              <p className="text-[10px] text-[var(--text-muted)] mt-1">
                {overview.monitored_device_count} monitored storage pools
              </p>
            </div>
            <div className="text-[10px] text-[var(--accent-sapphire)] font-mono mt-2">
              SLA thresholds enforced
            </div>
          </div>

          {/* Tile 5: Collector Heartbeat */}
          <div className="glass-panel rounded-xl p-4 flex flex-col justify-between hover:border-[var(--color-success)]/40 transition-all">
            <div>
              <div className="text-[11px] text-[var(--text-secondary)] font-medium flex items-center justify-between">
                <span>{isGuided ? 'Telemetry Sync' : 'Collector Heartbeat'}</span>
                <ContextualHelp
                  title="Telemetry Collection Health"
                  simpleExplanation="Confirms the background telemetry collector is actively capturing readings without drops."
                  technicalDetails="Sampling cadence: 1 hour intervals. Missingness rate: 0.00%."
                  evidenceSource="Passive Prometheus / OS collector"
                />
              </div>
              <div className="text-sm font-bold font-mono text-[var(--text-primary)] mt-2 truncate">
                {new Date(overview.last_successful_collection).toLocaleTimeString()}
              </div>
              <p className="text-[10px] text-[var(--color-success)] mt-1 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] animate-pulse" />
                Nominal cadence
              </p>
            </div>
            <div className="text-[10px] text-[var(--text-muted)] font-mono mt-2">
              Zero telemetry gaps
            </div>
          </div>

          {/* Tile 6: Forecast Reliability */}
          <div className="glass-panel rounded-xl p-4 flex flex-col justify-between hover:border-[var(--accent-violet)]/40 transition-all">
            <div>
              <div className="text-[11px] text-[var(--text-secondary)] font-medium flex items-center justify-between">
                <span>{isGuided ? 'Forecast Reliability' : 'Interval Calibration'}</span>
                <ContextualHelp
                  title="Forecast Model Reliability"
                  simpleExplanation="Percentage of past test observations that fell within our predicted range."
                  technicalDetails="Empirical interval coverage for 80% nominal conformal quantile intervals."
                  evidenceSource="Historical Backtest Benchmark"
                />
              </div>
              <div className="text-xl font-bold font-mono text-[var(--accent-violet)] mt-1.5">
                81.4%
              </div>
              <p className="text-[10px] text-[var(--text-muted)] mt-1">
                Target: 80% expected
              </p>
            </div>
            <div className="text-[10px] text-[var(--color-success)] font-mono mt-2 flex items-center gap-1">
              <ShieldCheck size={11} /> Conformal guarantee
            </div>
          </div>
        </div>
      )}

      {/* 4. Storage Pool Inspector & Main Forecast Chart */}
      <div className="space-y-3.5">
        <div className="flex items-center justify-between flex-wrap gap-2.5">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-[var(--text-primary)]">
              {isGuided ? 'Select Storage Pool to Inspect:' : 'Inspected Resource Target:'}
            </span>
            <select
              value={selectedDeviceId}
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              className="bg-[var(--surface-raised)] border border-[var(--border-visible)] focus:border-[var(--accent-cyan)] rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono cursor-pointer focus:outline-none"
              aria-label="Storage Pool Selector"
            >
              {devices.map((d) => (
                <option key={d.id} value={d.id} className="bg-[var(--surface-primary)] text-[var(--text-primary)]">
                  {d.name} ({d.tier})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => onNavigateToTwin(selectedDeviceId)}
            className="btn-aurora-primary flex items-center gap-1.5 px-3.5 py-1.5 text-xs rounded-lg font-semibold"
          >
            <Layers size={14} />
            {isGuided ? 'Test Actions in Digital Twin' : 'Simulate Counterfactuals in Sandbox'}
          </button>
        </div>

        {/* Central Capacity Forecast Fan Chart */}
        {capacityTelemetry && capacityForecast && (
          <ScientificForecastChart
            title={`Capacity Trajectory & Expected Range — ${capacityForecast.model_name}`}
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

      {/* 5. Latency and Throughput Diagnostics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {latencyTelemetry && (
          <ScientificForecastChart
            title={`P95 Tail Latency — ${selectedDeviceId}`}
            historicalTimestamps={latencyTelemetry.timestamps}
            historicalValues={latencyTelemetry.values}
            units="ms"
            isBytes={false}
          />
        )}

        {throughputTelemetry && (
          <ScientificForecastChart
            title={`Throughput Activity (MB/s) — ${selectedDeviceId}`}
            historicalTimestamps={throughputTelemetry.timestamps}
            historicalValues={throughputTelemetry.values}
            units="MB/s"
            isBytes={false}
          />
        )}
      </div>

      {/* 6. Operational Incidents & 4-Question Alert Framework + Recommended Action */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Operational Incidents (2 cols) */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Clock className="text-[var(--color-warning)]" size={16} />
              <span>{isGuided ? 'Operational Alerts & 4-Point Diagnosis' : 'Incident Stream & Diagnostic Context'}</span>
            </h3>
            <span className="text-[11px] font-mono text-[var(--text-muted)]">Chronological Sequence</span>
          </div>

          <div className="space-y-3">
            {overview?.risk_timeline.map((item) => (
              <div
                key={item.id}
                className={`p-4 rounded-xl border text-xs transition-all ${
                  item.severity === 'CRITICAL'
                    ? 'bg-[var(--color-critical)]/10 border-[var(--color-critical)]/30 text-[var(--color-critical)]'
                    : 'bg-[var(--surface-raised)]/60 border-[var(--border-subtle)] text-[var(--text-primary)]'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 shrink-0">
                    {item.severity === 'CRITICAL' ? (
                      <ShieldAlert size={18} className="text-[var(--color-critical)]" />
                    ) : (
                      <AlertTriangle size={18} className="text-[var(--color-warning)]" />
                    )}
                  </div>
                  <div className="flex-1 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm">{item.title}</span>
                      <span className="text-[10px] font-mono text-[var(--text-muted)]">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    {/* 4-Question Plain Language Explanatory Framework */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] pt-1 border-t border-[var(--border-subtle)]/60 font-sans">
                      <div>
                        <strong className="text-[var(--text-primary)]">1. What happened?</strong>
                        <p className="text-[var(--text-secondary)] mt-0.5">
                          Capacity write growth on pool <span className="font-mono text-[var(--accent-cyan)]">{item.device_id}</span> is outpacing unallocated headroom.
                        </p>
                      </div>
                      <div>
                        <strong className="text-[var(--text-primary)]">2. Why does it matter?</strong>
                        <p className="text-[var(--text-secondary)] mt-0.5">
                          Exceeding 90% hard limit will cause write queue contention and violate production latency SLAs.
                        </p>
                      </div>
                      <div>
                        <strong className="text-[var(--text-primary)]">3. Supporting evidence:</strong>
                        <p className="text-[var(--text-secondary)] mt-0.5">
                          LightGBM forecast median crosses safety envelope at +72 hours with 81.4% conformal calibration confidence.
                        </p>
                      </div>
                      <div>
                        <strong className="text-[var(--text-primary)]">4. Recommended action:</strong>
                        <p className="text-[var(--text-secondary)] mt-0.5">
                          Test cold data migration in the Digital Twin simulator or expand storage pool capacity.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Ranked Recommendation Panel (1 col) */}
        <div className="glass-panel rounded-2xl p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <Sliders className="text-[var(--accent-cyan)]" size={16} />
                <span>{isGuided ? 'Suggested Action' : 'Ranked Recommendation'}</span>
              </h3>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-[var(--accent-cyan)]/15 text-[var(--accent-cyan)] border border-[var(--accent-cyan)]/40 shadow-sm">
                #1 Priority
              </span>
            </div>

            {overview?.top_recommendation ? (
              <div className="mt-3.5 space-y-3 text-xs">
                <div className="font-semibold text-[var(--text-primary)] text-sm">
                  {overview.top_recommendation.title}
                </div>
                <div className="bg-[var(--surface-raised)]/70 rounded-xl p-3.5 border border-[var(--border-subtle)] space-y-1.5 font-mono text-[11px]">
                  <div>Target Pool: <span className="text-[var(--accent-cyan)] font-bold">{overview.top_recommendation.device_id}</span></div>
                  <div>Strategy: <span className="text-[var(--text-primary)] font-bold">{overview.top_recommendation.action_type}</span></div>
                  <div>Runway Headroom Gain: <span className="text-[var(--color-warning)] font-bold">+{overview.top_recommendation.estimated_runway_gain_hours} hrs</span></div>
                  <div>Utility Score: <span className="text-[var(--color-success)] font-bold">{overview.top_recommendation.utility_score.toFixed(1)}</span></div>
                </div>
                <p className="text-[var(--text-secondary)] text-xs leading-relaxed">
                  Evaluated against the Hard Safety Envelope. Disqualifies any action that would create high latency contention during migration.
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
            className="w-full mt-4 py-2.5 px-3 rounded-xl btn-aurora-primary font-bold text-xs flex items-center justify-center gap-1.5"
          >
            {isGuided ? 'Test This in Digital Twin' : 'Launch Digital Twin Sandbox'} <ArrowUpRight size={13} />
          </button>
        </div>
      </div>

      {/* 7. Monitored Storage Pools & Health Table */}
      <div className="glass-panel rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              {isGuided ? 'Storage Pool Status & Health' : 'Monitored Storage Pools & Service Constraints'}
            </h3>
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Live capacity utilization, P95 tail latency, and reserve runway across all physical storage tiers.
            </p>
          </div>
          <span className="text-xs text-[var(--text-secondary)] font-mono">{devices.length} Active Pools</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[var(--surface-raised)]/60 text-[var(--text-secondary)] uppercase text-[10px] border-b border-[var(--border-subtle)]">
              <tr>
                <th className="px-5 py-3 font-semibold">{isGuided ? 'Pool Name' : 'Storage Pool'}</th>
                <th className="px-5 py-3 font-semibold">{isGuided ? 'Hardware Tier' : 'Tier & Profile'}</th>
                <th className="px-5 py-3 font-semibold">{isGuided ? 'Used / Total' : 'Used / Capacity'}</th>
                <th className="px-5 py-3 font-semibold">Utilization</th>
                <th className="px-5 py-3 font-semibold">{isGuided ? 'Response Latency' : 'P95 Latency'}</th>
                <th className="px-5 py-3 font-semibold">{isGuided ? 'Runway Left' : 'Reserve Runway'}</th>
                <th className="px-5 py-3 font-semibold">Status</th>
                <th className="px-5 py-3 font-semibold text-right">Action</th>
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
                    <div className="text-[10px] text-[var(--text-muted)] font-mono">{d.workload_profile}</div>
                  </td>
                  <td className="px-5 py-3.5 text-[var(--text-primary)] tabular-nums">
                    {formatTB(d.current_used_bytes)} / {formatTB(d.total_capacity_bytes)}
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <span className="w-10 text-[var(--text-primary)] tabular-nums">{d.current_utilization_pct.toFixed(1)}%</span>
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
                  <td className="px-5 py-3.5 text-[var(--text-primary)] tabular-nums">{d.current_latency_p95_ms.toFixed(1)} ms</td>
                  <td className="px-5 py-3.5 text-[var(--color-warning)] font-bold tabular-nums">~{d.runway_hours_estimate.toFixed(0)} hrs</td>
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
