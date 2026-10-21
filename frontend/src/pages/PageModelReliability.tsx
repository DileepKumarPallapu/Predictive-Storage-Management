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
        <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
          <ShieldCheck className="text-obsidian-cyan" size={22} />
          Model Reliability, Calibration & Drift Diagnostics
        </h2>
        <p className="text-xs text-obsidian-muted mt-1">
          Tracking empirical interval coverage, residual distributions, and automatic fallback safeguards.
        </p>
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium">Empirical Coverage [q10, q90]</div>
            <div className="text-2xl font-bold font-mono text-obsidian-teal mt-1">
              {(metrics.overall_interval_coverage * 100).toFixed(1)}%
            </div>
            <div className="text-[11px] text-obsidian-muted font-mono mt-2">
              Nominal Target: {(metrics.target_nominal_coverage * 100).toFixed(0)}%
            </div>
          </div>

          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium">Quantile Pinball Loss</div>
            <div className="text-2xl font-bold font-mono text-obsidian-cyan mt-1">
              {metrics.mean_pinball_loss.toFixed(2)}
            </div>
            <div className="text-[11px] text-obsidian-muted font-mono mt-2">
              Mean over multi-step horizons
            </div>
          </div>

          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium">Capacity MAE</div>
            <div className="text-2xl font-bold font-mono text-obsidian-text mt-1">
              {metrics.mean_mae_capacity_gb.toFixed(1)} GB
            </div>
            <div className="text-[11px] text-obsidian-muted font-mono mt-2">
              Latency MAE: {metrics.mean_mae_latency_ms.toFixed(2)} ms
            </div>
          </div>

          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4">
            <div className="text-xs text-obsidian-muted font-medium">Workload Drift Status</div>
            <div className="mt-2">
              <span className={`px-2.5 py-1 rounded text-xs font-bold font-mono ${
                metrics.drift_status === 'STABLE'
                  ? 'bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40'
                  : 'bg-obsidian-amber/20 text-obsidian-amber border border-obsidian-amber/40'
              }`}>
                {metrics.drift_status}
              </span>
            </div>
            <div className="text-[11px] text-obsidian-muted font-mono mt-2">
              Active drift alerts: {metrics.active_drift_alerts}
            </div>
          </div>
        </div>
      )}

      {/* Calibration Protocol Card */}
      <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5 space-y-3">
        <h3 className="text-sm font-bold text-obsidian-text">Conformal Calibration Protocol</h3>
        <p className="text-xs text-obsidian-muted leading-relaxed">
          AEGISSTOR evaluates empirical prediction intervals using conformal quantile regression. If incoming test telemetry reveals coverage below nominal <span className="text-obsidian-cyan font-mono">80%</span>, the conformal adjustment factor <span className="text-obsidian-cyan font-mono">γ (gamma)</span> dynamically expands forecast bounds to preserve statistical guarantees.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 text-xs font-mono">
          <div className="bg-obsidian-secondary/50 rounded p-3 border border-obsidian-border/50">
            <span className="text-obsidian-muted block text-[10px]">Active Model Artifact</span>
            <span className="text-obsidian-text font-bold mt-1 block">LightGBM Quantile v1.2</span>
          </div>
          <div className="bg-obsidian-secondary/50 rounded p-3 border border-obsidian-border/50">
            <span className="text-obsidian-muted block text-[10px]">Conservative Fallback Trigger</span>
            <span className="text-obsidian-teal font-bold mt-1 block">Ready (Inactive)</span>
          </div>
          <div className="bg-obsidian-secondary/50 rounded p-3 border border-obsidian-border/50">
            <span className="text-obsidian-muted block text-[10px]">Retraining Recommendation</span>
            <span className="text-obsidian-muted font-bold mt-1 block">Scheduled in 48h</span>
          </div>
        </div>
      </div>
    </div>
  );
};
