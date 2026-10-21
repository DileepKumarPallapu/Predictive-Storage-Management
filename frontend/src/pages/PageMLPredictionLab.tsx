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
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent-violet)]/15 border border-[var(--accent-violet)]/30 flex items-center justify-center text-[var(--accent-violet)] shadow-[0_0_12px_rgba(171,140,255,0.2)]">
            <Brain size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            ML Multi-Horizon Prediction Lab
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          Interactive evaluation of non-parametric quantile regressors vs statistical & persistence baselines.
        </p>
      </div>

      {/* Control Grid */}
      <div className="glass-panel rounded-xl p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
        <div>
          <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">
            Storage Pool:
          </label>
          <select
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="w-full bg-[var(--surface-raised)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id} className="bg-[var(--surface-panel)] text-[var(--text-primary)]">
                {d.name} ({d.id})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">
            Model Architecture:
          </label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full bg-[var(--surface-raised)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-semibold focus:outline-none cursor-pointer"
          >
            <option value="lightgbm_quantile" className="bg-[var(--surface-panel)]">LightGBM Multi-Quantile (q10, q50, q90)</option>
            <option value="seasonal_naive" className="bg-[var(--surface-panel)]">Seasonal-Naive Diurnal Baseline</option>
            <option value="persistence" className="bg-[var(--surface-panel)]">Persistence Baseline (Random Walk)</option>
          </select>
        </div>

        <div>
          <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">
            Target Dimension:
          </label>
          <select
            value={targetMetric}
            onChange={(e) => setTargetMetric(e.target.value)}
            className="w-full bg-[var(--surface-raised)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
          >
            <option value="used_bytes" className="bg-[var(--surface-panel)]">Capacity (Bytes)</option>
            <option value="latency_p95_ms" className="bg-[var(--surface-panel)]">P95 Tail Latency (ms)</option>
            <option value="read_iops" className="bg-[var(--surface-panel)]">Read IOPS</option>
            <option value="write_iops" className="bg-[var(--surface-panel)]">Write IOPS</option>
          </select>
        </div>

        <div>
          <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">
            Forecast Horizon:
          </label>
          <div className="flex gap-2">
            {[24, 72, 168].map((h) => (
              <button
                key={h}
                onClick={() => setHorizonHours(h)}
                className={`flex-1 py-1.5 rounded-lg text-xs font-mono font-medium border transition-all ${
                  horizonHours === h
                    ? 'bg-[var(--accent-cyan)]/15 border-[var(--accent-cyan)] text-[var(--accent-cyan)] font-bold shadow-[0_0_8px_rgba(85,214,255,0.2)]'
                    : 'glass-panel text-[var(--text-secondary)] hover:text-[var(--text-primary)] border-[var(--border-subtle)]'
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
          <div className="glass-panel rounded-xl p-3.5">
            <div className="text-[var(--text-secondary)] font-medium flex items-center gap-1.5">
              <Brain size={13} className="text-[var(--accent-violet)]" /> Model Instance
            </div>
            <div className="text-sm font-bold text-[var(--text-primary)] mt-1.5 truncate">
              {forecast.model_name}
            </div>
          </div>

          <div className="glass-panel rounded-xl p-3.5">
            <div className="text-[var(--text-secondary)] font-medium flex items-center gap-1.5">
              <Zap size={13} className="text-[var(--accent-cyan)]" /> Inference Latency
            </div>
            <div className="text-sm font-bold font-mono text-[var(--accent-cyan)] mt-1.5">
              {forecast.inference_latency_ms.toFixed(1)} ms
            </div>
          </div>

          <div className="glass-panel rounded-xl p-3.5">
            <div className="text-[var(--text-secondary)] font-medium flex items-center gap-1.5">
              <ShieldCheck size={13} className="text-[var(--color-success)]" /> Interval Coverage
            </div>
            <div className="text-sm font-bold font-mono text-[var(--color-success)] mt-1.5">
              {(forecast.interval_coverage * 100).toFixed(1)}% (Nominal 80%)
            </div>
          </div>

          <div className="glass-panel rounded-xl p-3.5">
            <div className="text-[var(--text-secondary)] font-medium flex items-center gap-1.5">
              <Clock size={13} className="text-[var(--color-warning)]" /> Training Cutoff
            </div>
            <div className="text-sm font-bold font-mono text-[var(--text-secondary)] mt-1.5">
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
