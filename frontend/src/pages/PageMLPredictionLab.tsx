import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, ForecastResponse, TelemetryResponse } from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import { ContextualHelp } from '../components/ContextualHelp';
import { usePresentationMode } from '../context/PresentationModeContext';
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
  const { isGuided, isExpert } = usePresentationMode();

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
          <div className="w-8 h-8 rounded-lg bg-[var(--accent-tertiary)]/15 border border-[var(--accent-tertiary)]/30 flex items-center justify-center text-[var(--accent-tertiary)] shadow-[0_0_12px_rgba(178,154,255,0.2)]">
            <Brain size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            {isGuided ? 'Machine Learning Forecast Lab' : 'ML Multi-Horizon Prediction Lab'}
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          {isGuided
            ? 'Compare machine-learning predictions against traditional statistical baselines to evaluate accuracy.'
            : 'Interactive evaluation of non-parametric quantile regressors vs statistical & persistence baselines.'}
        </p>
      </div>

      {/* Control Grid */}
      <div className="glass-panel rounded-2xl p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
        <div>
          <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">
            Storage Pool:
          </label>
          <select
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="w-full bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
            aria-label="Storage Pool"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id} className="bg-[var(--surface-primary)] text-[var(--text-primary)]">
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
            className="w-full bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-semibold focus:outline-none cursor-pointer"
            aria-label="Model Architecture"
          >
            <option value="lightgbm_quantile" className="bg-[var(--surface-primary)]">LightGBM Quantile (q10, q50, q90)</option>
            <option value="seasonal_naive" className="bg-[var(--surface-primary)]">Seasonal-Naive Diurnal Baseline</option>
            <option value="persistence" className="bg-[var(--surface-primary)]">Persistence Baseline (Random Walk)</option>
          </select>
        </div>

        <div>
          <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">
            Target Dimension:
          </label>
          <select
            value={targetMetric}
            onChange={(e) => setTargetMetric(e.target.value)}
            className="w-full bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
            aria-label="Target Dimension"
          >
            <option value="used_bytes" className="bg-[var(--surface-primary)]">Capacity (Bytes)</option>
            <option value="latency_p95_ms" className="bg-[var(--surface-primary)]">P95 Response Delay (ms)</option>
            <option value="read_iops" className="bg-[var(--surface-primary)]">Read IOPS</option>
            <option value="write_iops" className="bg-[var(--surface-primary)]">Write IOPS</option>
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
                    ? 'bg-[var(--accent-primary)]/15 border-[var(--accent-primary)] text-[var(--accent-primary)] font-bold shadow-glow-vermilion'
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
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3.5 text-xs">
          <div className="glass-panel rounded-xl p-3.5">
            <div className="text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Brain size={13} className="text-[var(--accent-tertiary)]" /> Model Name
              </span>
              <ContextualHelp
                title="Model Algorithm"
                simpleExplanation="Active gradient boosting regressor generating quantile forecasts."
                technicalDetails="LightGBM gradient boosted trees with pinball loss objectives at alpha = 0.1, 0.5, 0.9."
              />
            </div>
            <div className="text-sm font-bold text-[var(--text-primary)] mt-1.5 truncate">
              {forecast.model_name}
            </div>
          </div>

          <div className="glass-panel rounded-xl p-3.5">
            <div className="text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Zap size={13} className="text-[var(--accent-primary)]" />
                {isGuided ? 'Time to Generate Prediction' : 'Inference Latency'}
              </span>
              <ContextualHelp
                title="Inference Latency"
                simpleExplanation="Milliseconds required to compute the 72-hour forecast."
              />
            </div>
            <div className="text-sm font-bold font-mono text-[var(--accent-primary)] mt-1.5">
              {forecast.inference_latency_ms.toFixed(1)} ms
            </div>
          </div>

          <div className="glass-panel rounded-xl p-3.5">
            <div className="text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <ShieldCheck size={13} className="text-[var(--status-success)]" />
                {isGuided ? 'Expected Range Coverage' : 'Interval Calibration'}
              </span>
              <ContextualHelp
                title="Interval Calibration"
                simpleExplanation="Percentage of test points falling cleanly between the expected bounds."
              />
            </div>
            <div className="text-sm font-bold font-mono text-[var(--status-success)] mt-1.5">
              {(forecast.interval_coverage * 100).toFixed(1)}% (Target: 80%)
            </div>
          </div>

          <div className="glass-panel rounded-xl p-3.5">
            <div className="text-[var(--text-secondary)] font-medium flex items-center gap-1.5">
              <Clock size={13} className="text-[var(--status-warning)]" /> Training Cutoff
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
