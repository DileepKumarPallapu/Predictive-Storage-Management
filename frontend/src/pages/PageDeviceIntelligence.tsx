import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, ForecastResponse, TelemetryResponse, RiskResponse } from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import { Cpu, Clock, AlertTriangle, Layers, TrendingUp, ShieldCheck } from 'lucide-react';

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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="text-obsidian-cyan" size={20} />
            <span className="text-xs font-mono text-obsidian-muted uppercase">Device Intelligence</span>
          </div>
          <h2 className="text-lg font-bold text-obsidian-text mt-1">
            {device?.name || deviceId}
          </h2>
          <div className="flex items-center gap-3 text-xs text-obsidian-muted mt-1 font-mono">
            <span>ID: {deviceId}</span>
            <span>•</span>
            <span>Tier: {device?.tier}</span>
            <span>•</span>
            <span>Media: {device?.media_type}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={deviceId}
            onChange={(e) => onSelectDevice(e.target.value)}
            className="bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text font-mono focus:border-obsidian-cyan cursor-pointer"
          >
            {deviceList.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.id})
              </option>
            ))}
          </select>

          <button
            onClick={() => onLaunchTwin(deviceId)}
            className="px-3 py-1.5 rounded bg-obsidian-cyan/15 hover:bg-obsidian-cyan/25 border border-obsidian-cyan/50 text-obsidian-cyan text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <Layers size={14} />
            Simulate Interventions
          </button>
        </div>
      </div>

      {/* Metrics & Risk Cards */}
      {risks && device && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium">Estimated Reserve Runway</div>
            <div className="text-2xl font-bold font-mono text-obsidian-amber mt-1">
              ~{risks.runway_hours_estimate.toFixed(1)} hrs
            </div>
            <div className="text-[11px] text-obsidian-muted font-mono mt-2">
              Confidence Band: [{risks.runway_hours_lower_bound}h — {risks.runway_hours_upper_bound}h]
            </div>
          </div>

          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium">Breach Probability (72h)</div>
            <div className="text-2xl font-bold font-mono text-obsidian-coral mt-1">
              {(risks.capacity_breach_prob_72h * 100).toFixed(1)}%
            </div>
            <div className="text-[11px] text-obsidian-muted font-mono mt-2">
              24h breach risk: {(risks.capacity_breach_prob_24h * 100).toFixed(1)}%
            </div>
          </div>

          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium">P95 Tail Latency Risk</div>
            <div className="text-2xl font-bold font-mono text-obsidian-cyan mt-1">
              {device.current_latency_p95_ms.toFixed(1)} ms
            </div>
            <div className="text-[11px] text-obsidian-muted font-mono mt-2">
              SLA Limit: {device.max_acceptable_latency_ms} ms
            </div>
          </div>

          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium">Risk Status Classification</div>
            <div className="mt-2">
              <span className={`px-2.5 py-1 rounded text-xs font-bold font-mono ${
                risks.risk_level === 'CRITICAL'
                  ? 'bg-obsidian-coral/20 text-obsidian-coral border border-obsidian-coral/40'
                  : risks.risk_level === 'ELEVATED'
                  ? 'bg-obsidian-amber/20 text-obsidian-amber border border-obsidian-amber/40'
                  : 'bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40'
              }`}>
                {risks.risk_level}
              </span>
            </div>
            <div className="text-[11px] text-obsidian-muted font-mono mt-2">
              Hard constraints checked
            </div>
          </div>
        </div>
      )}

      {/* Target Metric Selector & Fan Chart */}
      <div className="space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-obsidian-muted">Target Metric:</span>
            {[
              { id: 'used_bytes', label: 'Capacity (Bytes)' },
              { id: 'latency_p95_ms', label: 'P95 Latency (ms)' },
              { id: 'read_iops', label: 'Read IOPS' },
              { id: 'write_iops', label: 'Write IOPS' },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => setTargetMetric(m.id)}
                className={`px-3 py-1 rounded text-xs font-medium border transition-colors ${
                  targetMetric === m.id
                    ? 'bg-obsidian-cyan/15 border-obsidian-cyan text-obsidian-cyan'
                    : 'bg-obsidian-panel border-obsidian-border text-obsidian-muted hover:text-obsidian-text'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-obsidian-muted">Horizon:</span>
            {[24, 72, 168].map((h) => (
              <button
                key={h}
                onClick={() => setHorizonHours(h)}
                className={`px-2.5 py-1 rounded text-xs font-mono border transition-colors ${
                  horizonHours === h
                    ? 'bg-obsidian-violet/20 border-obsidian-violet text-obsidian-violet font-semibold'
                    : 'bg-obsidian-panel border-obsidian-border text-obsidian-muted'
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
        <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5">
          <h3 className="text-sm font-bold text-obsidian-text mb-3">Primary Risk Contributors</h3>
          <div className="space-y-3">
            {risks.risk_contributors.map((c, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-obsidian-secondary/50 rounded p-3 border border-obsidian-border/50">
                <span className="text-obsidian-text font-medium">{c.factor}</span>
                <div className="flex items-center gap-3">
                  <div className="w-24 bg-obsidian-panel h-1.5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-obsidian-coral"
                      style={{ width: `${Math.round(c.impact_score * 100)}%` }}
                    ></div>
                  </div>
                  <span className="font-mono text-obsidian-coral font-semibold">
                    {(c.impact_score * 100).toFixed(0)}% Impact
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
