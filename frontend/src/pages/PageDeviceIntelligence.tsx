import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, ForecastResponse, TelemetryResponse, RiskResponse } from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import { ContextualHelp } from '../components/ContextualHelp';
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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel rounded-2xl p-5">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent-cyan)]/15 border border-[var(--accent-cyan)]/30 flex items-center justify-center text-[var(--accent-cyan)] shadow-[0_0_12px_rgba(97,221,248,0.2)]">
              <Cpu size={18} />
            </div>
            <span className="text-xs font-mono text-[var(--accent-cyan)] uppercase font-semibold">
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
            className="bg-[var(--surface-raised)] border border-[var(--border-visible)] focus:border-[var(--accent-cyan)] rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
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
            className="btn-aurora-primary px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5"
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
              <div className="glass-panel rounded-2xl p-4 relative overflow-hidden group hover:border-[var(--color-warning)]/40 transition-all">
                <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
                  <span>{isGuided ? 'Runway Left' : 'Estimated Reserve Runway'}</span>
                  <ContextualHelp
                    title="Reserve Runway"
                    simpleExplanation="Estimated hours until this pool crosses its critical 90% utilization threshold."
                    technicalDetails="Linear and non-linear spline extrapolation from quantile forecast q50."
                  />
                </div>
                <div className="text-2xl font-bold font-mono text-[var(--color-warning)] mt-1.5">
                  ~{risks.runway_hours_estimate.toFixed(0)} hrs
                </div>
                <div className="text-[11px] text-[var(--text-muted)] font-mono mt-2">
                  {isGuided ? 'Expected bounds:' : 'Confidence Band:'} [{risks.runway_hours_lower_bound}h — {risks.runway_hours_upper_bound}h]
                </div>
              </div>

              <div className="glass-panel rounded-2xl p-4 relative overflow-hidden group hover:border-[var(--color-critical)]/40 transition-all">
                <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
                  <span>{isGuided ? 'Chance of Running Short (72h)' : 'Capacity Breach Probability (72h)'}</span>
                  <ContextualHelp
                    title="Breach Probability"
                    simpleExplanation="Likelihood that organic storage demand will exceed the provisioned safety margin within 3 days."
                    technicalDetails="P(Used_Bytes(t+72h) >= Critical_Limit) under empirical residual distribution."
                  />
                </div>
                <div className="text-2xl font-bold font-mono text-[var(--color-critical)] mt-1.5">
                  {(risks.capacity_breach_prob_72h * 100).toFixed(1)}%
                </div>
                <div className="text-[11px] text-[var(--text-muted)] font-mono mt-2">
                  24h risk: {(risks.capacity_breach_prob_24h * 100).toFixed(1)}%
                </div>
              </div>

              <div className="glass-panel rounded-2xl p-4 relative overflow-hidden group hover:border-[var(--accent-cyan)]/40 transition-all">
                <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
                  <span>{isGuided ? 'Response Delay (P95)' : 'P95 Tail Latency Risk'}</span>
                  <ContextualHelp
                    title="P95 Tail Latency"
                    simpleExplanation="95% of storage read/write requests complete faster than this response time."
                    technicalDetails="95th percentile latency from disk controller queue telemetry."
                  />
                </div>
                <div className="text-2xl font-bold font-mono text-[var(--accent-cyan)] mt-1.5">
                  {device.current_latency_p95_ms.toFixed(1)} ms
                </div>
                <div className="text-[11px] text-[var(--text-muted)] font-mono mt-2">
                  SLA Maximum: {device.max_acceptable_latency_ms} ms
                </div>
              </div>

              <div className="glass-panel rounded-2xl p-4 relative overflow-hidden group hover:border-[var(--color-success)]/40 transition-all">
                <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
                  <span>{isGuided ? 'Pool Health Status' : 'Risk Classification'}</span>
                  <ContextualHelp
                    title="Status Classification"
                    simpleExplanation="Current operational classification based on capacity and latency safety rules."
                  />
                </div>
                <div className="mt-2">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold font-mono ${
                    risks.risk_level === 'CRITICAL'
                      ? 'bg-[var(--color-critical)]/15 text-[var(--color-critical)] border border-[var(--color-critical)]/40 shadow-sm'
                      : risks.risk_level === 'ELEVATED'
                      ? 'bg-[var(--color-warning)]/15 text-[var(--color-warning)] border border-[var(--color-warning)]/40 shadow-sm'
                      : 'bg-[var(--color-success)]/15 text-[var(--color-success)] border border-[var(--color-success)]/40 shadow-sm'
                  }`}>
                    {risks.risk_level}
                  </span>
                </div>
                <div className="text-[11px] text-[var(--text-muted)] font-mono mt-2">
                  Safety rules active
                </div>
              </div>
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
                        ? 'bg-[var(--accent-cyan)]/15 border-[var(--accent-cyan)] text-[var(--accent-cyan)] font-bold shadow-[0_0_8px_rgba(97,221,248,0.2)]'
                        : 'glass-panel text-[var(--text-secondary)] hover:text-[var(--text-primary)] border-[var(--border-subtle)]'
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
                        ? 'bg-[var(--accent-violet)]/20 border-[var(--accent-violet)] text-[var(--accent-violet)] font-semibold shadow-[0_0_8px_rgba(178,154,255,0.2)]'
                        : 'glass-panel text-[var(--text-secondary)] border-[var(--border-subtle)]'
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
            <div className="glass-panel rounded-2xl p-5">
              <h3 className="text-sm font-bold text-[var(--text-primary)] mb-3">
                {isGuided ? 'Key Factors Affecting This Pool' : 'Primary Risk Contributors'}
              </h3>
              <div className="space-y-3">
                {risks.risk_contributors.map((c, i) => (
                  <div key={i} className="flex items-center justify-between text-xs bg-[var(--surface-raised)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                    <span className="text-[var(--text-primary)] font-medium">{c.factor}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-28 bg-[var(--surface-primary)] h-2 rounded-full overflow-hidden p-0.5 border border-[var(--border-subtle)]">
                        <div
                          className="h-full bg-[var(--color-critical)] rounded-full shadow-[0_0_6px_var(--color-critical)]"
                          style={{ width: `${Math.round(c.impact_score * 100)}%` }}
                        />
                      </div>
                      <span className="font-mono text-[var(--color-critical)] font-semibold">
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
