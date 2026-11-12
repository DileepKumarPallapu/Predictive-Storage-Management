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
import { KpiCard } from '../components/KpiCard';
import { usePresentationMode } from '../context/PresentationModeContext';
import { useOperatingMode } from '../context/OperatingModeContext';
import { useRealtimeSubscription } from '../context/RealtimeContext';
import {
  Activity,
  Clock,
  ArrowUpRight,
  AlertTriangle,
  Layers,
  Radio,
  Sliders,
  Sparkles,
  CheckCircle2,
  HardDrive,
  ShieldCheck,
  ShieldAlert,
  Server
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
  const { operatingMode, provenanceLabel, refreshKey } = useOperatingMode();

  useEffect(() => {
    loadInitialData();
  }, [refreshKey, operatingMode]);

  useEffect(() => {
    if (selectedDeviceId) {
      loadDeviceCharts(selectedDeviceId, horizonHours);
    }
  }, [selectedDeviceId, horizonHours]);

  useRealtimeSubscription(
    ['storage.', 'telemetry.', 'alert.', 'model.', 'forecast.', 'approval.', 'task.', 'ingestion.'],
    () => {
      loadInitialData();
      if (selectedDeviceId) loadDeviceCharts(selectedDeviceId, horizonHours);
    },
  );

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
      console.error('Failed to load overview data:', e);
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
      console.error('Failed to load device charts:', e);
    }
  };

  const formatTB = (bytes: number) => (bytes / (1024 ** 4)).toFixed(1) + ' TB';

  if (loading && !overview) {
    return <LoadingSkeleton rows={8} height="h-10" />;
  }

  const isCritical = overview?.highest_current_risk.level === 'CRITICAL';
  const isElevated = overview?.highest_current_risk.level === 'ELEVATED';

  return (
    <div className="space-y-6">
      {/* SECTION A: Page Introduction & Environment Controls */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-[var(--border)]">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="font-editorial text-2xl sm:text-3xl font-bold text-[var(--text-primary)] tracking-tight">
              {isGuided ? 'Storage Health & Capacity Overview' : 'Storage Resilience & Capacity Intelligence'}
            </h1>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
                operatingMode === 'live'
                  ? 'bg-[var(--success)]/10 text-[var(--success)] border-[var(--success)]/30'
                  : operatingMode === 'replay'
                  ? 'bg-[var(--warning)]/10 text-[var(--warning)] border-[var(--warning)]/30'
                  : 'bg-[var(--surface-elevated)] text-[var(--text-muted)] border-[var(--border)]'
              }`}
            >
              {overview?.data_mode_label || provenanceLabel}
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 max-w-2xl leading-relaxed">
            {isGuided
              ? 'Real-time monitoring of fleet capacity, machine-learned reserve runways, and proactive suggestions.'
              : 'Multi-horizon risk envelope and predictive time-to-breach estimation powered by conformal quantile regressors.'}
          </p>
        </div>

        {/* Forecast Horizon Switcher */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
            <Clock size={13} />
            <span className="font-medium">{isGuided ? 'Projection:' : 'Forecast Horizon:'}</span>
          </div>
          <div className="flex items-center bg-[var(--surface-elevated)] p-0.5 rounded-lg border border-[var(--border)]">
            {[24, 72, 168].map((h) => (
              <button
                key={h}
                type="button"
                onClick={() => setHorizonHours(h)}
                className={`px-2.5 py-1 text-xs font-mono font-semibold rounded-md transition-all ${
                  horizonHours === h
                    ? 'bg-[var(--accent)] text-white shadow-xs'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                +{h}h
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 5-Question Plain-English Summary Strip */}
      {overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-3">
            <div className="text-[11px] text-[var(--text-muted)]">1. Connected Storage</div>
            <div className="text-sm font-bold text-[var(--text-primary)] mt-0.5">
              {overview.monitored_device_count} {overview.monitored_device_count === 1 ? 'pool' : 'pools'}
            </div>
            <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">Monitored storage resources</div>
          </div>
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-3">
            <div className="text-[11px] text-[var(--text-muted)]">2. Storage Used</div>
            <div className="text-sm font-bold text-[var(--text-primary)] mt-0.5">
              {overview.capacity_utilization_pct.toFixed(1)}%
            </div>
            <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">Active fleet capacity</div>
          </div>
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-3">
            <div className="text-[11px] text-[var(--text-muted)]">3. Needs Attention</div>
            <div className="text-sm font-bold text-[var(--text-primary)] mt-0.5">
              {overview.highest_current_risk?.level || 'LOW'} Risk
            </div>
            <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              Top pool: {overview.highest_current_risk?.device_id || 'None'}
            </div>
          </div>
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-3">
            <div className="text-[11px] text-[var(--text-muted)]">4. Future Outlook</div>
            <div className="text-sm font-bold text-[var(--text-primary)] mt-0.5">
              ~{overview.estimated_reserve_runway_hours.toFixed(0)} hours
            </div>
            <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">Estimated time to safety limit</div>
          </div>
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-3">
            <div className="text-[11px] text-[var(--text-muted)]">5. Recommended Next Step</div>
            <div className="text-sm font-bold text-[var(--text-primary)] mt-0.5">
              {isCritical || isElevated ? 'Review & Simulate Action' : 'Continue Monitoring'}
            </div>
            <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              {overview.highest_current_risk?.device_id || 'All pools healthy'}
            </div>
          </div>
        </div>
      )}

      {/* SECTION B: Storage Condition Panel */}
      {overview && (
        <div
          className={`p-4 rounded-lg border transition-all ${
            isCritical
              ? 'bg-[var(--critical)]/5 border-[var(--critical)]/30'
              : isElevated
              ? 'bg-[var(--warning)]/5 border-[var(--warning)]/30'
              : 'bg-[var(--surface)] border-[var(--border)]'
          }`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 shrink-0">
                {isCritical ? (
                  <ShieldAlert size={18} className="text-[var(--critical)]" />
                ) : isElevated ? (
                  <AlertTriangle size={18} className="text-[var(--warning)]" />
                ) : (
                  <ShieldCheck size={18} className="text-[var(--success)]" />
                )}
              </div>
              <div className="space-y-0.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-bold text-[var(--text-primary)]">
                    {isCritical
                      ? 'Critical Capacity Runway Alert'
                      : isElevated
                      ? 'Elevated Growth Notice'
                      : 'Operational Condition Nominal'}
                  </span>
                  <span className="text-[10px] font-mono text-[var(--text-muted)]">
                    • Evaluated at {new Date(overview.last_successful_collection).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  {isCritical ? (
                    <>
                      Target pool <strong className="font-mono text-[var(--text-primary)]">{overview.highest_current_risk.device_id}</strong> is projected to reach its safety limit in approximately{' '}
                      <span className="font-mono font-bold text-[var(--critical)]">~{overview.estimated_reserve_runway_hours.toFixed(0)} hours</span>. Countermeasure simulation recommended.
                    </>
                  ) : isElevated ? (
                    <>
                      Pool <strong className="font-mono text-[var(--text-primary)]">{overview.highest_current_risk.device_id}</strong> has increased write pressure with{' '}
                      <span className="font-mono font-bold text-[var(--warning)]">~{overview.estimated_reserve_runway_hours.toFixed(0)} hours</span> of reserve runway.
                    </>
                  ) : (
                    <>All {overview.monitored_device_count} monitored storage pools are operating with healthy reserve headroom.</>
                  )}
                </p>
              </div>
            </div>

            <button
              onClick={() => onNavigateToTwin(overview.highest_current_risk.device_id || selectedDeviceId)}
              className="btn-secondary text-xs shrink-0 self-start sm:self-center inline-flex items-center gap-1.5"
            >
              <Layers size={13} className="text-[var(--accent)]" />
              <span>{isGuided ? 'Test Action in Digital Twin' : 'Simulate in Sandbox'}</span>
              <ArrowUpRight size={12} />
            </button>
          </div>
        </div>
      )}

      {/* SECTION C: 4 Primary Metrics & 2 Secondary Health Indicators */}
      {overview && (
        <div className="space-y-3">
          {/* 4 Primary Key Metrics — Rebuilt Shared KPI Component */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Primary 1: Storage Utilization */}
            <KpiCard
              label={isGuided ? 'Storage Utilization' : 'Fleet Utilization'}
              value={`${overview.capacity_utilization_pct.toFixed(1)}%`}
              help={{
                title: 'Storage Utilization',
                simpleExplanation: 'Total storage capacity in active use across all monitored tiers.',
                technicalDetails: 'Aggregated bytes_used / bytes_total across NVMe, SAS, and Cold Archive.',
              }}
              progress={{
                value: overview.capacity_utilization_pct,
                status: overview.capacity_utilization_pct > 85 ? 'critical' : 'normal',
              }}
              footer={
                <span className="text-[11px] font-mono text-[var(--text-secondary)]">
                  {formatTB(overview.total_used_bytes)} used / {formatTB(overview.total_capacity_bytes)} total
                </span>
              }
            />

            {/* Primary 2: Available Capacity */}
            <KpiCard
              label={isGuided ? 'Available Capacity' : 'Available Headroom'}
              value={formatTB(overview.total_free_bytes)}
              help={{
                title: 'Available Headroom',
                simpleExplanation: 'Total unallocated space available for writes before reaching any configured limits.',
                technicalDetails: 'Unallocated block storage bytes reported by storage controller.',
              }}
              description="Unallocated reserve headroom"
              footer={
                <div className="flex items-center gap-1.5 text-[var(--status-success)] font-medium text-[11px]">
                  <CheckCircle2 size={13} />
                  <span>Ready for writes</span>
                </div>
              }
            />

            {/* Primary 3: Estimated Reserve Runway */}
            <KpiCard
              label={isGuided ? 'Estimated Runway' : 'Shortest Reserve Runway'}
              value={`~${overview.estimated_reserve_runway_hours.toFixed(0)}h`}
              help={{
                title: 'Reserve Runway',
                simpleExplanation: 'Estimated operational hours until the fastest-filling pool hits its critical safety limit.',
                technicalDetails: 'Derived from LightGBM median forecast crossing the 90% hard threshold.',
              }}
              description={
                <span>
                  Leading on <strong className="font-mono text-[var(--text-primary)]">{overview.highest_current_risk.device_id}</strong>
                </span>
              }
              footer={
                <div className="flex items-center gap-1.5 text-[var(--text-secondary)] font-medium text-[11px]">
                  <Clock size={13} />
                  <span>Proactive lead time</span>
                </div>
              }
            />

            {/* Primary 4: Storage Risk State */}
            <KpiCard
              label={isGuided ? 'Risk State' : 'Fleet Risk State'}
              value={
                <span className={isCritical ? 'text-[var(--status-critical)]' : isElevated ? 'text-[var(--status-warning)]' : 'text-[var(--status-success)]'}>
                  {overview.highest_current_risk.level}
                </span>
              }
              help={{
                title: 'Risk State Classification',
                simpleExplanation: 'Overall assessment of storage health based on capacity exhaustion and tail latency.',
                technicalDetails: 'Calculates joint risk: P(Capacity > 90%) + P(P95 Latency > SLA).',
              }}
              description={`${overview.monitored_device_count} monitored storage pools`}
              footer={
                <div className="flex items-center gap-1.5 text-[var(--text-secondary)] font-medium text-[11px]">
                  <ShieldCheck size={13} />
                  <span>SLA limits active</span>
                </div>
              }
            />
          </div>

          {/* Operational Readiness KPIs & Backend Health Matrix (Module A) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              { label: 'Managed Resources', val: String(overview.monitored_device_count ?? 0) },
              { label: 'Resources at Risk', val: String((overview as any).resources_at_risk ?? 0) },
              { label: 'Critical Alerts', val: String((overview as any).critical_alerts_count ?? 0) },
              {
                label: 'Data Freshness',
                val:
                  (overview as any).data_freshness_hours !== null && (overview as any).data_freshness_hours !== undefined
                    ? `${(overview as any).data_freshness_hours}h max age`
                    : 'No samples',
              },
              {
                label: 'Telemetry Quality',
                val:
                  (overview as any).avg_data_reliability_score !== null && (overview as any).avg_data_reliability_score !== undefined
                    ? `${(((overview as any).avg_data_reliability_score) * 100).toFixed(0)}%`
                    : 'Unscored',
              },
              {
                label: 'Active Connectors',
                val: `${(overview as any).active_connectors_count ?? 0} / ${(overview as any).total_connectors_count ?? 0}`,
              },
              { label: 'Pending Decisions', val: String((overview as any).pending_decisions_count ?? 0) },
            ].map((item) => (
              <div key={item.label} className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-3">
                <div className="text-[10px] font-medium text-[var(--text-muted)] uppercase truncate">{item.label}</div>
                <div className="text-sm font-bold font-mono text-[var(--text-primary)] mt-1 truncate">{item.val}</div>
              </div>
            ))}
          </div>

          {/* Real Telemetry Heartbeat & Model Training / Latest Forecast Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-3 bg-[var(--surface-elevated)] border border-[var(--border)] rounded-lg flex items-center justify-between text-xs gap-2">
              <div className="flex items-center gap-2.5 min-w-0">
                <Radio size={15} className={(overview as any).stale_resources_count > 0 ? 'text-[var(--warning)] shrink-0' : 'text-[var(--success)] shrink-0'} />
                <div className="truncate">
                  <span className="font-semibold text-[var(--text-primary)]">Telemetry Freshness: </span>
                  <span className="text-[var(--text-secondary)]">
                    {(overview as any).stale_resources_count ?? 0} stale resource(s) · {(overview as any).active_alerts_count ?? 0} active alert(s)
                  </span>
                </div>
              </div>
              <span className="text-[10px] font-mono text-[var(--text-primary)] font-semibold px-2 py-0.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] shrink-0">
                {(overview as any).errored_connectors_count > 0 ? `${(overview as any).errored_connectors_count} CONN ERR` : 'HEALTHY'}
              </span>
            </div>

            <div className="p-3 bg-[var(--surface-elevated)] border border-[var(--border)] rounded-lg flex items-center justify-between text-xs gap-2">
              <div className="flex items-center gap-2.5 min-w-0">
                <Sparkles size={15} className="text-[var(--brand-primary)] shrink-0" />
                <div className="truncate">
                  <span className="font-semibold text-[var(--text-primary)]">ML Engine: </span>
                  <span className="text-[var(--text-secondary)]">
                    {(overview as any).model_training_status?.latest_model_type || 'Unset'} ({(overview as any).model_training_status?.latest_status || 'IDLE'})
                  </span>
                </div>
              </div>
              <span className="text-[10px] font-mono text-[var(--text-muted)] shrink-0">
                {(overview as any).latest_forecast_run?.generated_at
                  ? `FC ${(overview as any).latest_forecast_run.generated_at.slice(0, 10)}`
                  : 'No forecast'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Target Resource Inspection Selector */}
      <div className="titan-card p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-[var(--surface-elevated)]">
        <div className="flex items-center gap-2.5 flex-1 min-w-0 flex-wrap sm:flex-nowrap">
          <HardDrive size={16} className="text-[var(--accent)] shrink-0" />
          <span className="text-xs font-semibold text-[var(--text-primary)] shrink-0">
            {isGuided ? 'Inspect Storage Pool:' : 'Target Resource:'}
          </span>
          <select
            value={selectedDeviceId}
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            className="bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] text-xs font-medium rounded-md px-2.5 py-1 focus:outline-none cursor-pointer flex-1 max-w-md min-w-[200px]"
            aria-label="Select Storage Pool"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.id}) — {d.current_utilization_pct.toFixed(1)}% used
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={() => onNavigateToTwin(selectedDeviceId)}
          className="btn-secondary text-xs whitespace-nowrap shrink-0 inline-flex items-center gap-1.5"
        >
          <Layers size={13} className="text-[var(--accent)]" />
          <span>{isGuided ? 'Test Actions in Digital Twin' : 'Simulate Counterfactuals'}</span>
          <ArrowUpRight size={12} />
        </button>
      </div>

      {/* SECTION D: Forecast Centerpiece (Central Visualization) */}
      {capacityTelemetry && capacityForecast && (
        <ScientificForecastChart
          title={`Calibrated Capacity Quantile Forecast: ${selectedDeviceId}`}
          historicalTimestamps={capacityTelemetry.timestamps}
          historicalValues={capacityTelemetry.values}
          forecastTimestamps={capacityForecast.timestamps}
          q10={capacityForecast.q10}
          q50={capacityForecast.q50}
          q90={capacityForecast.q90}
          hardConstraint={capacityForecast.hard_constraint_value}
          units={capacityForecast.units}
          isBytes={true}
        />
      )}

      {/* SECTION E: Supporting Analysis */}
      {/* 1. Secondary Performance Signals: Tail Latency & Throughput */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {latencyTelemetry && (
          <ScientificForecastChart
            title={`P95 Tail Latency: ${selectedDeviceId}`}
            historicalTimestamps={latencyTelemetry.timestamps}
            historicalValues={latencyTelemetry.values}
            units="ms"
            isBytes={false}
          />
        )}
        {throughputTelemetry && (
          <ScientificForecastChart
            title={`I/O Throughput: ${selectedDeviceId}`}
            historicalTimestamps={throughputTelemetry.timestamps}
            historicalValues={throughputTelemetry.values}
            units="MB/s"
            isBytes={false}
          />
        )}
      </div>

      {/* 2. Operational Incidents & Top Recommendation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Incident Stream (2 columns) */}
        <div className="lg:col-span-2 titan-card p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
            <h3 className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Clock className="text-[var(--warning)]" size={14} />
              <span>{isGuided ? 'Operational Incidents & Signals' : 'Recent Telemetry Events & Anomalies'}</span>
            </h3>
            <span className="text-[11px] font-mono text-[var(--text-muted)]">
              {overview?.risk_timeline.length || 0} events recorded
            </span>
          </div>

          <div className="space-y-2.5">
            {overview?.risk_timeline.slice(0, 3).map((item) => (
              <div
                key={item.id}
                className="bg-[var(--surface-elevated)] rounded-md p-3 border border-[var(--border)] space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        item.severity === 'CRITICAL' ? 'bg-[var(--critical)]' : 'bg-[var(--warning)]'
                      }`}
                    />
                    <span className="font-semibold text-[var(--text-primary)]">{item.title}</span>
                  </div>
                  <span className="text-[10px] font-mono text-[var(--text-muted)]">
                    {new Date(item.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] pt-1.5 border-t border-[var(--border)] text-[var(--text-secondary)]">
                  <div>
                    <span className="text-[var(--text-primary)] font-medium">Affected Resource: </span>
                    <span className="font-mono text-[var(--accent)] font-semibold">{item.device_id}</span>
                  </div>
                  <div>
                    <span className="text-[var(--text-primary)] font-medium">Category: </span>
                    <span className="font-mono">{item.category}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Recommendation (1 column) */}
        <div className="titan-card p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
              <h3 className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                <Sliders className="text-[var(--accent)]" size={14} />
                <span>{isGuided ? 'Top Recommendation' : 'Ranked Intervention'}</span>
              </h3>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-[var(--accent)]/10 text-[var(--accent)] border border-[var(--accent)]/20">
                #1 Priority
              </span>
            </div>

            {overview?.top_recommendation ? (
              <div className="mt-3 space-y-2.5 text-xs">
                <div className="font-semibold text-[var(--text-primary)]">
                  {overview.top_recommendation.title}
                </div>
                <div className="bg-[var(--surface-elevated)] rounded-md p-2.5 border border-[var(--border)] space-y-1 font-mono text-[11px]">
                  <div>Target: <span className="text-[var(--accent)] font-bold">{overview.top_recommendation.device_id}</span></div>
                  <div>Strategy: <span className="text-[var(--text-primary)] font-bold">{overview.top_recommendation.action_type}</span></div>
                  <div>Runway Gain: <span className="text-[var(--warning)] font-bold">+{overview.top_recommendation.estimated_runway_gain_hours} hrs</span></div>
                  <div>Utility Score: <span className="text-[var(--success)] font-bold">{overview.top_recommendation.utility_score.toFixed(1)}</span></div>
                </div>
                <p className="text-[var(--text-secondary)] text-[11px] leading-relaxed">
                  Evaluated against the Hard Safety Envelope. Disqualifies any action that would violate P95 latency SLAs.
                </p>
              </div>
            ) : (
              <div className="text-xs text-[var(--text-muted)] mt-3">
                No immediate critical intervention required.
              </div>
            )}
          </div>

          <button
            onClick={() => onNavigateToTwin(overview?.top_recommendation?.device_id || selectedDeviceId)}
            className="w-full mt-4 btn-primary text-xs flex items-center justify-center gap-1.5"
          >
            <span>{isGuided ? 'Test in Digital Twin' : 'Launch Digital Twin Sandbox'}</span>
            <ArrowUpRight size={13} />
          </button>
        </div>
      </div>

      {/* 3. Monitored Storage Pools & Service Constraints Table */}
      <div className="titan-card overflow-hidden">
        <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-[var(--text-primary)]">
              {isGuided ? 'Monitored Storage Pools' : 'Monitored Storage Pools & Service Constraints'}
            </h3>
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Live capacity utilization, P95 tail latency, and reserve runway across all physical tiers.
            </p>
          </div>
          <span className="text-xs text-[var(--text-muted)] font-mono">{devices.length} Monitored Pools</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[var(--surface-elevated)] text-[var(--text-muted)] uppercase text-[10px] border-b border-[var(--border)]">
              <tr>
                <th className="px-4 py-2.5 font-semibold">{isGuided ? 'Pool Name' : 'Storage Pool'}</th>
                <th className="px-4 py-2.5 font-semibold">{isGuided ? 'Hardware Tier' : 'Tier & Profile'}</th>
                <th className="px-4 py-2.5 font-semibold">{isGuided ? 'Used / Total' : 'Used / Capacity'}</th>
                <th className="px-4 py-2.5 font-semibold">Utilization</th>
                <th className="px-4 py-2.5 font-semibold">{isGuided ? 'Latency' : 'P95 Latency'}</th>
                <th className="px-4 py-2.5 font-semibold">{isGuided ? 'Runway Left' : 'Reserve Runway'}</th>
                <th className="px-4 py-2.5 font-semibold">Status</th>
                <th className="px-4 py-2.5 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {devices.map((d) => (
                <tr key={d.id} className="hover:bg-[var(--surface-hover)] transition-colors">
                  <td className="px-4 py-2.5 font-semibold text-[var(--text-primary)] font-sans">
                    {d.name}
                    <div className="text-[10px] font-mono text-[var(--accent)] font-normal">{d.id}</div>
                  </td>
                  <td className="px-4 py-2.5 text-[var(--text-secondary)] font-sans">
                    {d.tier}
                    <div className="text-[10px] text-[var(--text-muted)] font-mono">{d.workload_profile}</div>
                  </td>
                  <td className="px-4 py-2.5 text-[var(--text-primary)] tabular-nums">
                    {formatTB(d.current_used_bytes)} / {formatTB(d.total_capacity_bytes)}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="w-10 text-[var(--text-primary)] tabular-nums">{d.current_utilization_pct.toFixed(1)}%</span>
                      <div className="w-16 bg-[var(--surface-subtle)] h-1.5 rounded-full overflow-hidden border border-[var(--border)]">
                        <div
                          className={`h-full rounded-full ${
                            d.current_utilization_pct >= d.critical_threshold_pct
                              ? 'bg-[var(--critical)]'
                              : d.current_utilization_pct >= d.warning_threshold_pct
                              ? 'bg-[var(--warning)]'
                              : 'bg-[var(--success)]'
                          }`}
                          style={{ width: `${Math.min(100, d.current_utilization_pct)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-[var(--text-primary)] tabular-nums">{d.current_latency_p95_ms.toFixed(1)} ms</td>
                  <td className="px-4 py-2.5 text-[var(--warning)] font-bold tabular-nums">~{d.runway_hours_estimate.toFixed(0)}h</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        d.risk_level === 'CRITICAL'
                          ? 'bg-[var(--critical)]/10 text-[var(--critical)] border border-[var(--critical)]/30'
                          : d.risk_level === 'ELEVATED'
                          ? 'bg-[var(--warning)]/10 text-[var(--warning)] border border-[var(--warning)]/30'
                          : 'bg-[var(--success)]/10 text-[var(--success)] border border-[var(--success)]/30'
                      }`}
                    >
                      {d.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={() => onNavigateToDevice(d.id)}
                      className="btn-secondary text-[11px] py-1 px-2.5 inline-flex items-center gap-1 font-sans"
                    >
                      Inspect <ArrowUpRight size={11} />
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
