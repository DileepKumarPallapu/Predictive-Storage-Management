import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, ForecastResponse, TelemetryResponse, RiskResponse } from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import { ContextualHelp } from '../components/ContextualHelp';
import { KpiCard } from '../components/KpiCard';
import { usePresentationMode } from '../context/PresentationModeContext';
import { Cpu, Clock, AlertTriangle, Layers, TrendingUp, ShieldCheck, Activity } from 'lucide-react';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

interface Props {
  deviceId: string;
  onSelectDevice: (id: string) => void;
  onLaunchTwin: (id: string) => void;
}

export const PageDeviceIntelligence: React.FC<Props> = ({ deviceId, onSelectDevice, onLaunchTwin }) => {
  const [deviceList, setDeviceList] = useState<DeviceSummary[]>([]);
  const [device, setDevice] = useState<DeviceSummary | null>(null);
  const [targetMetric, setTargetMetric] = useState<string>('used_bytes');
  const [horizonHours, setHorizonHours] = useState<number>(72);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [risks, setRisks] = useState<RiskResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const { isGuided, isExpert } = usePresentationMode();

  useEffect(() => {
    loadDevices();
  }, []);

  useEffect(() => {
    if (deviceId) {
      loadDeviceDetails(deviceId, targetMetric, horizonHours);
    }
  }, [deviceId, targetMetric, horizonHours]);

  const loadDevices = async () => {
    try {
      const list = await api.getDevices();
      setDeviceList(list);
    } catch (e) {
      console.error(e);
    }
  };

  const loadDeviceDetails = async (id: string, metric: string, horizon: number) => {
    setLoading(true);
    try {
      const [dev, tel, fc, rsk] = await Promise.all([
        api.getDevice(id),
        api.getTelemetry(id, metric, 168),
        api.getForecast(id, metric, 'lightgbm_quantile', horizon),
        api.getRisks(id),
      ]);
      setDevice(dev);
      setTelemetry(tel);
      setForecast(fc);
      setRisks(rsk);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const formatTB = (bytes: number) => (bytes / (1024 ** 4)).toFixed(2) + ' TB';

  return (
    <div className="space-y-6">
      {/* Device Header and Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 titan-card rounded-lg p-5">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center shadow-xs">
              <Cpu size={18} />
            </div>
            <span className="text-xs font-mono text-[var(--accent-primary)] uppercase font-semibold">
              {isGuided ? 'Device Detail & Health' : 'Deep Telemetry & ML Intelligence'}
            </span>
          </div>
          <h2 className="text-lg font-bold text-[var(--text-primary)] mt-1.5 tracking-tight">
            {device?.name || deviceId}
          </h2>
          <div className="flex items-center gap-3 text-xs text-[var(--text-secondary)] mt-1 font-mono">
            <span>Pool ID: <strong className="text-[var(--text-primary)]">{deviceId}</strong></span>
            <span>•</span>
            <span>Tier: <strong className="text-[var(--text-primary)]">{device?.tier}</strong></span>
            <span>•</span>
            <span>Media: <strong className="text-[var(--text-primary)]">{device?.media_type}</strong></span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={deviceId}
            onChange={(e) => onSelectDevice(e.target.value)}
            className="bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
            aria-label="Select Device"
          >
            {deviceList.map((d) => (
              <option key={d.id} value={d.id} className="bg-[var(--surface-primary)] text-[var(--text-primary)]">
                {d.name} ({d.id})
              </option>
            ))}
          </select>

          <button
            onClick={() => onLaunchTwin(deviceId)}
            className="btn-primary px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5"
          >
            <Layers size={14} />
            {isGuided ? 'Test Actions in Sandbox' : 'Simulate Interventions'}
          </button>
        </div>
      </div>

      {loading && !device ? (
        <LoadingSkeleton rows={6} height="h-8" />
      ) : (
        <>
          {/* Metrics & Risk Cards */}
          {risks && device && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label={isGuided ? 'Runway Left' : 'Estimated Reserve Runway'}
                value={`~${risks.runway_hours_estimate.toFixed(0)} hrs`}
                help={{
                  title: 'Reserve Runway',
                  simpleExplanation: 'Estimated hours until this pool crosses its critical 90% utilization threshold.',
                  technicalDetails: 'Linear and non-linear spline extrapolation from quantile forecast q50.',
                }}
                footer={
                  <span className="text-[11px] text-[var(--text-muted)] font-mono">
                    {isGuided ? 'Expected bounds:' : 'Confidence Band:'} [{risks.runway_hours_lower_bound}h — {risks.runway_hours_upper_bound}h]
                  </span>
                }
              />

              <KpiCard
                label={isGuided ? 'Chance of Running Short (72h)' : 'Capacity Breach Probability (72h)'}
                value={
                  <span className="text-[var(--status-critical)]">
                    {(risks.capacity_breach_prob_72h * 100).toFixed(1)}%
                  </span>
                }
                help={{
                  title: 'Breach Probability',
                  simpleExplanation: 'Likelihood that organic storage demand will exceed the provisioned safety margin within 3 days.',
                  technicalDetails: 'P(Used_Bytes(t+72h) >= Critical_Limit) under empirical residual distribution.',
                }}
                footer={
                  <span className="text-[11px] text-[var(--text-muted)] font-mono">
                    24h risk: {(risks.capacity_breach_prob_24h * 100).toFixed(1)}%
                  </span>
                }
              />

              <KpiCard
                label={isGuided ? 'Response Delay (P95)' : 'P95 Tail Latency Risk'}
                value={
                  <span className="text-[var(--brand-primary)]">
                    {device.current_latency_p95_ms === null ? 'Not collected' : device.current_latency_p95_ms.toFixed(1) + ' ms'}
                  </span>
                }
                help={{
                  title: 'P95 Tail Latency',
                  simpleExplanation: '95% of storage read/write requests complete faster than this response time.',
                  technicalDetails: '95th percentile latency from disk controller queue telemetry.',
                }}
                footer={
                  <span className="text-[11px] text-[var(--text-muted)] font-mono">
                    SLA Maximum: {device.max_acceptable_latency_ms} ms
                  </span>
                }
              />

              <KpiCard
                label={isGuided ? 'Pool Health Status' : 'Risk Classification'}
                value={
                  <span className={
                    risks.risk_level === 'CRITICAL'
                      ? 'text-[var(--status-critical)]'
                      : risks.risk_level === 'ELEVATED'
                      ? 'text-[var(--status-warning)]'
                      : 'text-[var(--status-success)]'
                  }>
                    {risks.risk_level}
                  </span>
                }
                help={{
                  title: 'Status Classification',
                  simpleExplanation: 'Current operational classification based on capacity and latency safety rules.',
                }}
                footer={
                  <span className="text-[11px] text-[var(--text-muted)] font-mono">
                    Safety rules active
                  </span>
                }
              />
            </div>
          )}

          {/* Target Metric Selector & Fan Chart */}
          <div className="space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--text-secondary)] font-medium">Metric Dimension:</span>
                {[
                  { id: 'used_bytes', label: 'Capacity (Bytes)' },
                  { id: 'latency_p95_ms', label: 'Response Delay (ms)' },
                  { id: 'read_iops', label: 'Read IOPS' },
                  { id: 'write_iops', label: 'Write IOPS' },
                ].map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setTargetMetric(m.id)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium border transition-all ${
                      targetMetric === m.id
                        ? 'bg-[var(--accent-primary)]/15 border-[var(--accent-primary)] text-[var(--accent-primary)] font-bold shadow-xs'
                        : 'titan-card text-[var(--text-secondary)] hover:text-[var(--text-primary)] border-[var(--border-subtle)]'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--text-secondary)] font-medium">Horizon:</span>
                {[24, 72, 168].map((h) => (
                  <button
                    key={h}
                    onClick={() => setHorizonHours(h)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-mono border transition-all ${
                      horizonHours === h
                        ? 'bg-[var(--accent-tertiary)]/20 border-[var(--accent-tertiary)] text-[var(--accent-tertiary)] font-semibold shadow-sm'
                        : 'titan-card text-[var(--text-secondary)] border-[var(--border-subtle)]'
                    }`}
                  >
                    +{h}h
                  </button>
                ))}
              </div>
            </div>

            {telemetry && forecast && (
              <ScientificForecastChart
                title={`${targetMetric === 'used_bytes' ? 'Storage Capacity' : targetMetric} Forecast & Quantile Intervals`}
                historicalTimestamps={telemetry.timestamps}
                historicalValues={telemetry.values}
                forecastTimestamps={forecast.timestamps}
                q10={forecast.q10}
                q50={forecast.q50}
                q90={forecast.q90}
                hardConstraint={forecast.hard_constraint_value}
                units={forecast.units}
                isBytes={targetMetric === 'used_bytes'}
              />
            )}
          </div>

          {/* Risk Factors Breakdown */}
          {risks && (
            <div className="titan-card rounded-lg p-5">
              <h3 className="text-sm font-bold text-[var(--text-primary)] mb-3">
                {isGuided ? 'Key Factors Affecting This Pool' : 'Primary Risk Contributors'}
              </h3>
              <div className="space-y-3">
                {risks.risk_contributors.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-xs bg-[var(--surface-secondary)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                    <span className="text-[var(--text-primary)] font-medium">{c.factor}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-28 bg-[var(--surface-primary)] h-2 rounded-full overflow-hidden p-0.5 border border-[var(--border-subtle)]">
                        <div
                          className="h-full bg-[var(--status-critical)] rounded-full shadow-[0_0_6px_var(--status-critical)]"
                          style={{ width: `${Math.round(c.impact_score * 100)}%` }}
                        />
                      </div>
                      <span className="font-mono text-[var(--status-critical)] font-semibold">
                        {(c.impact_score * 100).toFixed(0)}% Weight
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
