import React, { useState, useEffect } from 'react';
import { api, ReliabilityMetrics } from '../api/client';
import { ShieldCheck, AlertCircle, RefreshCw, Activity, ArrowUpRight, CheckCircle2 } from 'lucide-react';

export const PageModelReliability: React.FC = () => {
  const [metrics, setMetrics] = useState<ReliabilityMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

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
          <div className="w-8 h-8 rounded-lg bg-[var(--color-success)]/15 border border-[var(--color-success)]/30 flex items-center justify-center text-[var(--color-success)] shadow-[0_0_12px_rgba(67,230,189,0.2)]">
            <ShieldCheck size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            Model Reliability, Calibration & Drift Diagnostics
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          Tracking empirical interval coverage, residual distributions, and automatic fallback safeguards.
        </p>
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel rounded-xl p-4 hover:border-[var(--color-success)]/40 transition-all">
            <div className="text-xs text-[var(--text-secondary)] font-medium">Empirical Coverage [q10, q90]</div>
            <div className="text-2xl font-bold font-mono text-[var(--color-success)] mt-1.5">
              {(metrics.overall_interval_coverage * 100).toFixed(1)}%
            </div>
            <div className="text-[11px] text-[var(--text-tertiary)] font-mono mt-2">
              Nominal Target: {(metrics.target_nominal_coverage * 100).toFixed(0)}%
            </div>
          </div>

          <div className="glass-panel rounded-xl p-4 hover:border-[var(--accent-cyan)]/40 transition-all">
            <div className="text-xs text-[var(--text-secondary)] font-medium">Quantile Pinball Loss</div>
            <div className="text-2xl font-bold font-mono text-[var(--accent-cyan)] mt-1.5">
              {metrics.mean_pinball_loss.toFixed(2)}
            </div>
            <div className="text-[11px] text-[var(--text-tertiary)] font-mono mt-2">
              Mean over multi-step horizons
            </div>
          </div>

          <div className="glass-panel rounded-xl p-4 hover:border-[var(--accent-violet)]/40 transition-all">
            <div className="text-xs text-[var(--text-secondary)] font-medium">Capacity MAE</div>
            <div className="text-2xl font-bold font-mono text-[var(--text-primary)] mt-1.5">
              {metrics.mean_mae_capacity_gb.toFixed(1)} GB
            </div>
            <div className="text-[11px] text-[var(--text-tertiary)] font-mono mt-2">
              Latency MAE: {metrics.mean_mae_latency_ms.toFixed(2)} ms
            </div>
          </div>

          <div className="glass-panel rounded-xl p-4 hover:border-[var(--color-warning)]/40 transition-all">
            <div className="text-xs text-[var(--text-secondary)] font-medium">Workload Drift Status</div>
            <div className="mt-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold font-mono ${
                metrics.drift_status === 'STABLE'
                  ? 'bg-[var(--color-success)]/15 text-[var(--color-success)] border border-[var(--color-success)]/40 shadow-sm'
                  : 'bg-[var(--color-warning)]/15 text-[var(--color-warning)] border border-[var(--color-warning)]/40 shadow-sm'
              }`}>
                {metrics.drift_status}
              </span>
            </div>
            <div className="text-[11px] text-[var(--text-tertiary)] font-mono mt-2">
              Active drift alerts: {metrics.active_drift_alerts}
            </div>
          </div>
        </div>
      )}

      {/* Calibration Protocol Card */}
      <div className="glass-panel rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-bold text-[var(--text-primary)]">Conformal Calibration Protocol</h3>
        <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
          AEGISSTOR evaluates empirical prediction intervals using conformal quantile regression. If incoming test telemetry reveals coverage below nominal <span className="text-[var(--accent-cyan)] font-mono font-bold">80%</span>, the conformal adjustment factor <span className="text-[var(--accent-cyan)] font-mono font-bold">γ (gamma)</span> dynamically expands forecast bounds to preserve statistical guarantees.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 text-xs font-mono">
          <div className="bg-[var(--surface-raised)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
            <span className="text-[var(--text-tertiary)] uppercase text-[10px] block">Active Model Artifact</span>
            <span className="text-[var(--text-primary)] font-bold mt-1 block">LightGBM Quantile v1.2</span>
          </div>
          <div className="bg-[var(--surface-raised)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
            <span className="text-[var(--text-tertiary)] uppercase text-[10px] block">Conservative Fallback Trigger</span>
            <span className="text-[var(--color-success)] font-bold mt-1 block">Ready (Inactive)</span>
          </div>
          <div className="bg-[var(--surface-raised)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
            <span className="text-[var(--text-tertiary)] uppercase text-[10px] block">Retraining Recommendation</span>
            <span className="text-[var(--text-secondary)] font-bold mt-1 block">Scheduled in 48h</span>
          </div>
        </div>
      </div>
    </div>
  );
};
