import React, { useState, useEffect } from 'react';
import { api, ReliabilityMetrics } from '../api/client';
import { ShieldCheck, AlertCircle, RefreshCw, Activity, ArrowUpRight, CheckCircle2, Info } from 'lucide-react';
import { ContextualHelp } from '../components/ContextualHelp';
import { usePresentationMode } from '../context/PresentationModeContext';

export const PageModelReliability: React.FC = () => {
  const [metrics, setMetrics] = useState<ReliabilityMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const { isGuided, isExpert } = usePresentationMode();

  useEffect(() => {
    loadReliability();
  }, []);

  const loadReliability = async () => {
    setLoading(true);
    try {
      const data = await api.getModelReliability();
      setMetrics(data);
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
          <div className="w-8 h-8 rounded-lg bg-[var(--status-success)]/15 border border-[var(--status-success)]/30 flex items-center justify-center text-[var(--status-success)] shadow-[0_0_12px_rgba(74,219,181,0.2)]">
            <ShieldCheck size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            {isGuided ? 'Forecast Reliability & Workload Consistency' : 'Model Reliability, Calibration & Drift Diagnostics'}
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          {isGuided
            ? 'Monitors whether storage models are staying accurate over time or if workload patterns have changed.'
            : 'Tracking empirical interval coverage, residual distributions, and automatic fallback safeguards.'}
        </p>
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel rounded-2xl p-4 hover:border-[var(--status-success)]/40 transition-all">
            <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span>{isGuided ? 'Reliability Score (Coverage)' : 'Empirical Coverage [q10, q90]'}</span>
              <ContextualHelp
                title="Forecast Reliability"
                simpleExplanation="Percentage of actual future observations that fell inside our 80% expected bounds."
                technicalDetails="Empirical interval coverage calculated over 168-hour rolling validation windows."
              />
            </div>
            <div className="text-2xl font-bold font-mono text-[var(--status-success)] mt-1.5">
              {(metrics.overall_interval_coverage * 100).toFixed(1)}%
            </div>
            <div className="text-[11px] text-[var(--text-muted)] font-mono mt-2">
              Target Guarantee: {(metrics.target_nominal_coverage * 100).toFixed(0)}%
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-4 hover:border-[var(--accent-primary)]/40 transition-all">
            <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span>{isGuided ? 'Forecast Sharpness (Spread)' : 'Quantile Pinball Loss'}</span>
              <ContextualHelp
                title="Forecast Sharpness"
                simpleExplanation="Measures how narrow the prediction bounds are while still remaining accurate."
                technicalDetails="Mean pinball check loss across alpha = 0.1, 0.5, 0.9 quantiles."
              />
            </div>
            <div className="text-2xl font-bold font-mono text-[var(--accent-primary)] mt-1.5">
              {metrics.mean_pinball_loss.toFixed(2)}
            </div>
            <div className="text-[11px] text-[var(--text-muted)] font-mono mt-2">
              Lower is sharper and better
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-4 hover:border-[var(--accent-tertiary)]/40 transition-all">
            <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span>{isGuided ? 'Average Prediction Error' : 'Capacity MAE'}</span>
              <ContextualHelp
                title="Mean Absolute Error"
                simpleExplanation="Average difference between predicted storage and actual observed storage."
              />
            </div>
            <div className="text-2xl font-bold font-mono text-[var(--text-primary)] mt-1.5">
              {metrics.mean_mae_capacity_gb.toFixed(1)} GB
            </div>
            <div className="text-[11px] text-[var(--text-muted)] font-mono mt-2">
              Response Delay Error: {metrics.mean_mae_latency_ms.toFixed(2)} ms
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-4 hover:border-[var(--status-warning)]/40 transition-all">
            <div className="text-xs text-[var(--text-secondary)] font-medium flex items-center justify-between">
              <span>{isGuided ? 'Workload Pattern Status' : 'Workload Drift Status'}</span>
              <ContextualHelp
                title="Workload Pattern Shift"
                simpleExplanation="Detects if sudden changes in database or VM write behavior have disrupted historical patterns."
                technicalDetails="Page-Hinkley cumulative deviation detector on sequential residuals."
              />
            </div>
            <div className="mt-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold font-mono ${
                metrics.drift_status === 'STABLE'
                  ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm'
                  : 'bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40 shadow-sm'
              }`}>
                {isGuided
                  ? metrics.drift_status === 'STABLE' ? 'Normal / Consistent' : 'Pattern Changed'
                  : metrics.drift_status}
              </span>
            </div>
            <div className="text-[11px] text-[var(--text-muted)] font-mono mt-2">
              Active pattern shifts: {metrics.active_drift_alerts}
            </div>
          </div>
        </div>
      )}

      {/* Calibration Protocol Card */}
      <div className="glass-panel rounded-2xl p-5 space-y-3">
        <h3 className="text-sm font-bold text-[var(--text-primary)]">
          {isGuided ? 'Automatic Reliability Safeguards' : 'Conformal Calibration Protocol'}
        </h3>
        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
          {isGuided
            ? 'If test data shows the model is becoming less accurate, AEGISSTOR automatically expands the expected safety bounds to protect operations from unexpected spikes.'
            : 'AEGISSTOR evaluates empirical prediction intervals using conformal quantile regression. If test telemetry reveals coverage below nominal 80%, the conformal adjustment factor γ (gamma) dynamically expands forecast bounds to preserve statistical guarantees.'}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 text-xs font-mono">
          <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
            <span className="text-[var(--text-muted)] uppercase text-[10px] block">Active Model Artifact</span>
            <span className="text-[var(--text-primary)] font-bold mt-1 block">LightGBM Quantile v1.2</span>
          </div>
          <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
            <span className="text-[var(--text-muted)] uppercase text-[10px] block">Fallback Safeguard</span>
            <span className="text-[var(--status-success)] font-bold mt-1 block">Armed & Ready (Inactive)</span>
          </div>
          <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
            <span className="text-[var(--text-muted)] uppercase text-[10px] block">Retraining Schedule</span>
            <span className="text-[var(--text-secondary)] font-bold mt-1 block">Scheduled in 48h</span>
          </div>
        </div>
      </div>
    </div>
  );
};
