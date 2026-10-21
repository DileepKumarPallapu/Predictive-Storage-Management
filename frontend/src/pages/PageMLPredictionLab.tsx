import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, ForecastResponse, TelemetryResponse } from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import { Brain, Clock, Zap, CheckCircle2, ShieldCheck, Cpu } from 'lucide-react';

export const PageMLPredictionLab: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('vol-nvme-tier1-db');
  const [selectedModel, setSelectedModel] = useState<string>('lightgbm_quantile');
  const [horizonHours, setHorizonHours] = useState<number>(72);
  const [targetMetric, setTargetMetric] = useState<string>('used_bytes');
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    loadDevices();
  }, []);

  useEffect(() => {
    if (selectedDevice) {
      loadModelForecast();
    }
  }, [selectedDevice, selectedModel, horizonHours, targetMetric]);

  const loadDevices = async () => {
    try {
      const list = await api.getDevices();
      setDevices(list);
    } catch (e) {
      console.error(e);
    }
  };

  const loadModelForecast = async () => {
    setLoading(true);
    try {
      const [tel, fc] = await Promise.all([
        api.getTelemetry(selectedDevice, targetMetric, 168),
        api.getForecast(selectedDevice, targetMetric, selectedModel, horizonHours),
      ]);
      setTelemetry(tel);
      setForecast(fc);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
          <Brain className="text-obsidian-cyan" size={22} />
          ML Multi-Horizon Prediction Lab
        </h2>
        <p className="text-xs text-obsidian-muted mt-1">
          Interactive evaluation of non-parametric quantile regressors vs statistical & persistence baselines.
        </p>
      </div>

      {/* Control Grid */}
      <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
        <div>
          <label className="block text-obsidian-muted mb-1 font-medium">Storage Pool:</label>
          <select
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-obsidian-text font-mono focus:border-obsidian-cyan cursor-pointer"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.id})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-obsidian-muted mb-1 font-medium">Model Architecture:</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-obsidian-text font-semibold focus:border-obsidian-cyan cursor-pointer"
          >
            <option value="lightgbm_quantile">LightGBM Multi-Quantile (q10, q50, q90)</option>
            <option value="seasonal_naive">Seasonal-Naive Diurnal Baseline</option>
            <option value="persistence">Persistence Baseline (Random Walk)</option>
          </select>
        </div>

        <div>
          <label className="block text-obsidian-muted mb-1 font-medium">Target Dimension:</label>
          <select
            value={targetMetric}
            onChange={(e) => setTargetMetric(e.target.value)}
            className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-obsidian-text font-mono focus:border-obsidian-cyan cursor-pointer"
          >
            <option value="used_bytes">Capacity (Bytes)</option>
            <option value="latency_p95_ms">P95 Tail Latency (ms)</option>
            <option value="read_iops">Read IOPS</option>
            <option value="write_iops">Write IOPS</option>
          </select>
        </div>

        <div>
          <label className="block text-obsidian-muted mb-1 font-medium">Forecast Horizon:</label>
          <div className="flex gap-2">
            {[24, 72, 168].map((h) => (
              <button
                key={h}
                onClick={() => setHorizonHours(h)}
                className={`flex-1 py-1.5 rounded text-xs font-mono font-medium border transition-colors ${
                  horizonHours === h
                    ? 'bg-obsidian-cyan/15 border-obsidian-cyan text-obsidian-cyan'
                    : 'bg-obsidian-secondary border-obsidian-border text-obsidian-muted hover:text-obsidian-text'
                }`}
              >
                +{h}h
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Model Diagnostics Metadata */}
      {forecast && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
          <div className="bg-obsidian-panel border border-obsidian-border rounded p-3">
            <div className="text-obsidian-muted font-medium flex items-center gap-1.5">
              <Brain size={13} className="text-obsidian-violet" /> Model Instance
            </div>
            <div className="text-sm font-bold text-obsidian-text mt-1 truncate">
              {forecast.model_name}
            </div>
          </div>

          <div className="bg-obsidian-panel border border-obsidian-border rounded p-3">
            <div className="text-obsidian-muted font-medium flex items-center gap-1.5">
              <Zap size={13} className="text-obsidian-cyan" /> Inference Latency
            </div>
            <div className="text-sm font-bold font-mono text-obsidian-cyan mt-1">
              {forecast.inference_latency_ms.toFixed(1)} ms
            </div>
          </div>

          <div className="bg-obsidian-panel border border-obsidian-border rounded p-3">
            <div className="text-obsidian-muted font-medium flex items-center gap-1.5">
              <ShieldCheck size={13} className="text-obsidian-teal" /> Interval Coverage
            </div>
            <div className="text-sm font-bold font-mono text-obsidian-teal mt-1">
              {(forecast.interval_coverage * 100).toFixed(1)}% (Nominal 80%)
            </div>
          </div>

          <div className="bg-obsidian-panel border border-obsidian-border rounded p-3">
            <div className="text-obsidian-muted font-medium flex items-center gap-1.5">
              <Clock size={13} className="text-obsidian-amber" /> Training Cutoff
            </div>
            <div className="text-sm font-bold font-mono text-obsidian-muted mt-1">
              {new Date(forecast.historical_cutoff).toLocaleTimeString()}
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      {telemetry && forecast && (
        <ScientificForecastChart
          title={`${forecast.model_name} — Horizon +${horizonHours}h`}
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
  );
};
