import React, { useState, useEffect } from 'react';
import {
  api,
  ReliabilityMetrics,
  SentinelTrustAssessment,
  SentinelTrustHistoryItem
} from '../api/client';
import {
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Activity,
  CheckCircle2,
  Sliders,
  History,
  TrendingDown,
  Layers,
  ChevronRight,
  Database,
  Lock,
  ArrowRight
} from 'lucide-react';
import { ContextualHelp } from '../components/ContextualHelp';
import { usePresentationMode } from '../context/PresentationModeContext';

export const PageModelReliability: React.FC = () => {
  const [metrics, setMetrics] = useState<ReliabilityMetrics | null>(null);
  const [sentinel, setSentinel] = useState<SentinelTrustAssessment | null>(null);
  const [history, setHistory] = useState<SentinelTrustHistoryItem[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('vol-nvme-tier1-db');
  const [loading, setLoading] = useState<boolean>(true);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [candidateResult, setCandidateResult] = useState<any | null>(null);
  const { isGuided, isExpert } = usePresentationMode();

  const devices = [
    { id: 'vol-nvme-tier1-db', name: 'NVMe Tier-1 Primary DB' },
    { id: 'vol-sas-tier2-analytics', name: 'SAS Tier-2 Analytics' },
    { id: 'vol-hdd-archive', name: 'HDD Cold Archive' },
    { id: 'vol-backup-target', name: 'Secondary Backup Target' }
  ];

  useEffect(() => {
    loadAllData();
  }, [selectedDevice]);

  const loadAllData = async () => {
    setLoading(true);
    setActionMessage(null);
    try {
      const [relData, sentData, histData] = await Promise.all([
        api.getModelReliability(),
        api.getSentinelTrust(selectedDevice),
        api.getSentinelTrustHistory(selectedDevice, 10)
      ]);
      setMetrics(relData);
      setSentinel(sentData);
      setHistory(histData);
    } catch (e) {
      console.error('Failed to load Sentinel reliability data:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleRecalibrate = async () => {
    try {
      const res = await api.recalibrateSentinelModel({
        device_id: selectedDevice,
        adjustment_factor_gamma: 1.15,
        notes: 'Operator requested safe conformal bounds inflation factor gamma=1.15.'
      });
      setActionMessage(`Recalibrated successfully. Gamma adjusted to ${res.conformal_adjustment_factor_gamma}. Reversibility guaranteed.`);
      loadAllData();
    } catch (e) {
      console.error(e);
      setActionMessage('Failed to trigger recalibration.');
    }
  };

  const handleEvaluateCandidate = async () => {
    try {
      const res = await api.evaluateRetrainCandidate({
        device_id: selectedDevice,
        candidate_model_type: 'lightgbm_quantile_retrained'
      });
      setCandidateResult(res);
      setActionMessage('Chronological holdout validation completed. Production model replacement requires human sign-off.');
    } catch (e) {
      console.error(e);
      setActionMessage('Candidate evaluation failed.');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'HEALTHY':
        return 'bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/40';
      case 'WATCH':
        return 'bg-[var(--status-warning)]/15 text-[var(--status-warning)] border-[var(--status-warning)]/40';
      case 'DEGRADED':
        return 'bg-[var(--status-critical)]/15 text-[var(--status-critical)] border-[var(--status-critical)]/40';
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return 'bg-[var(--text-muted)]/15 text-[var(--text-secondary)] border-[var(--border-subtle)]';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Device Selector & Live Action */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[var(--border-subtle)]">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--status-success)]/15 border border-[var(--status-success)]/30 flex items-center justify-center text-[var(--status-success)] shadow-[0_0_12px_rgba(74,219,181,0.2)]">
              <ShieldCheck size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              AEGISSTOR SENTINEL — Prediction Trust & Drift Engine
            </h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
            {isGuided
              ? 'Detects changing storage workloads, pairs forecasts against realized actuals, and enforces safe model improvement.'
              : 'Statistical PSI & Kolmogorov-Smirnov distribution drift monitoring, forecast-vs-actual calibration, and chronological holdout validation.'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[var(--surface-secondary)]/80 border border-[var(--border-subtle)] rounded-xl px-3 py-1.5 text-xs font-mono">
            <Database size={13} className="text-[var(--text-muted)]" />
            <select
              value={selectedDevice}
              onChange={(e) => setSelectedDevice(e.target.value)}
              className="bg-transparent text-[var(--text-primary)] focus:outline-none cursor-pointer"
            >
              {devices.map((d) => (
                <option key={d.id} value={d.id} className="bg-[var(--surface-primary)] text-[var(--text-primary)]">
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={loadAllData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[var(--border-subtle)] hover:border-[var(--accent-primary)]/50 text-xs font-mono text-[var(--text-primary)] transition-all bg-[var(--surface-secondary)]/60"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="titan-card p-3.5 rounded-xl text-xs font-mono text-[var(--status-success)] border border-[var(--status-success)]/40 flex items-center gap-2">
          <CheckCircle2 size={16} />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Sentinel Actionable Trust Status Card */}
      {sentinel && (
        <div className="titan-card rounded-lg p-5 border border-[var(--border-subtle)] relative overflow-hidden">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-full text-xs font-bold font-mono border ${getStatusColor(sentinel.trust_status)}`}>
                  TRUST STATUS: {sentinel.trust_status}
                </span>
                <span className="text-[11px] text-[var(--text-muted)] font-mono">
                  Evaluated: {new Date(sentinel.evaluated_at).toLocaleTimeString()} UTC
                </span>
              </div>
              <p className="text-sm font-medium text-[var(--text-primary)] leading-relaxed">
                {sentinel.status_reason}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {sentinel.safe_model_improvement.recalibration_eligible && (
                <button
                  onClick={handleRecalibrate}
                  className="px-3 py-2 rounded-xl text-xs font-mono font-medium bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/40 hover:bg-[var(--accent-primary)]/25 text-[var(--accent-primary)] transition-all flex items-center gap-1.5"
                >
                  <Sliders size={14} />
                  <span>Recalibrate Bounds (γ)</span>
                </button>
              )}

              <button
                onClick={handleEvaluateCandidate}
                className="px-3 py-2 rounded-xl text-xs font-mono font-medium bg-[var(--surface-secondary)] border border-[var(--border-subtle)] hover:border-[var(--text-primary)]/40 text-[var(--text-primary)] transition-all flex items-center gap-1.5"
              >
                <Layers size={14} />
                <span>Evaluate Holdout Retrain</span>
              </button>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[var(--border-subtle)]/50 flex flex-wrap items-center justify-between text-xs font-mono text-[var(--text-secondary)]">
            <div className="flex items-center gap-4">
              <span>Recommended Action: <strong className="text-[var(--text-primary)]">{sentinel.recommended_action}</strong></span>
              <span>Telemetry Age: <strong className="text-[var(--text-primary)]">{sentinel.data_quality.latest_observation_age_hours}h</strong></span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-muted)]">
              <Lock size={12} />
              <span>Automatic production model replacement is strictly blocked</span>
            </div>
          </div>
        </div>
      )}

      {/* 3-Way Drift Diagnostics Breakdown */}
      {sentinel && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Workload Data Drift */}
          <div className="titan-card rounded-lg p-4.5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-[var(--text-secondary)] font-medium">1. Workload Data Drift</span>
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                sentinel.workload_data_drift.detected
                  ? 'bg-[var(--status-warning)]/15 text-[var(--status-warning)]'
                  : 'bg-[var(--status-success)]/15 text-[var(--status-success)]'
              }`}>
                {sentinel.workload_data_drift.detected ? 'DRIFT DETECTED' : 'NOMINAL'}
              </span>
            </div>
            <div>
              <div className="text-2xl font-bold font-mono text-[var(--text-primary)]">
                PSI {sentinel.workload_data_drift.max_psi.toFixed(3)}
              </div>
              <div className="text-[11px] text-[var(--text-muted)] font-mono mt-1">
                Threshold: &gt; 0.10 moderate, &gt; 0.25 critical
              </div>
            </div>
            <div className="text-xs text-[var(--text-secondary)] pt-1 border-t border-[var(--border-subtle)]">
              Drifted features: <strong>{sentinel.workload_data_drift.drifted_metrics_count}</strong> of {Object.keys(sentinel.workload_data_drift.metrics_breakdown).length} monitored
            </div>
          </div>

          {/* Card 2: Prediction Drift */}
          <div className="titan-card rounded-lg p-4.5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-[var(--text-secondary)] font-medium">2. Prediction Drift</span>
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                sentinel.prediction_drift.detected
                  ? 'bg-[var(--status-warning)]/15 text-[var(--status-warning)]'
                  : 'bg-[var(--status-success)]/15 text-[var(--status-success)]'
              }`}>
                {sentinel.prediction_drift.severity}
              </span>
            </div>
            <div>
              <div className="text-2xl font-bold font-mono text-[var(--text-primary)]">
                PSI {sentinel.prediction_drift.prediction_psi.toFixed(3)}
              </div>
              <div className="text-[11px] text-[var(--text-muted)] font-mono mt-1">
                Compares forecasted trajectory vs reference forecast
              </div>
            </div>
            <div className="text-xs text-[var(--text-secondary)] pt-1 border-t border-[var(--border-subtle)]">
              Trajectory consistency: <strong>{sentinel.prediction_drift.detected ? 'Trajectory Shifted' : 'Trajectory Aligned'}</strong>
            </div>
          </div>

          {/* Card 3: Evaluated Performance Deterioration */}
          <div className="titan-card rounded-lg p-4.5 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-[var(--text-secondary)] font-medium">3. Performance Deterioration</span>
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                sentinel.performance_reliability.deterioration_detected
                  ? 'bg-[var(--status-critical)]/15 text-[var(--status-critical)]'
                  : 'bg-[var(--status-success)]/15 text-[var(--status-success)]'
              }`}>
                {sentinel.performance_reliability.deterioration_detected ? 'DEGRADED' : 'CALIBRATED'}
              </span>
            </div>
            <div>
              <div className="text-2xl font-bold font-mono text-[var(--status-success)]">
                {sentinel.performance_reliability.empirical_coverage_pct.toFixed(1)}%
              </div>
              <div className="text-[11px] text-[var(--text-muted)] font-mono mt-1">
                Conformal Coverage (Target: {sentinel.performance_reliability.target_nominal_coverage_pct}%)
              </div>
            </div>
            <div className="text-xs text-[var(--text-secondary)] pt-1 border-t border-[var(--border-subtle)]">
              Evaluated MAE: <strong>{sentinel.performance_reliability.evaluated_mae_gb} GB</strong> | WAPE: <strong>{sentinel.performance_reliability.evaluated_wape_pct}%</strong>
            </div>
          </div>
        </div>
      )}

      {/* Candidate Holdout Retrain Decision Result */}
      {candidateResult && (
        <div className="titan-card rounded-lg p-5 border border-[var(--accent-primary)]/40 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers size={18} className="text-[var(--accent-primary)]" />
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Chronological Holdout Validation: Candidate Model vs Production
              </h3>
            </div>
            <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40">
              POLICY: AUTOMATIC PROMOTION BLOCKED
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono pt-2">
            <div className="p-3.5 rounded-xl bg-[var(--surface-secondary)]/70 border border-[var(--border-subtle)] space-y-1.5">
              <div className="text-[var(--text-muted)] text-[10px] uppercase">Active Production Model</div>
              <div className="text-[var(--text-primary)] font-bold">{candidateResult.production_model.version}</div>
              <div className="text-[var(--text-secondary)]">Holdout MAE: {candidateResult.production_model.holdout_mae_gb} GB</div>
              <div className="text-[var(--text-secondary)]">Coverage: {candidateResult.production_model.holdout_coverage_pct}%</div>
            </div>

            <div className="p-3.5 rounded-xl bg-[var(--surface-secondary)]/70 border border-[var(--status-success)]/40 space-y-1.5">
              <div className="text-[var(--text-muted)] text-[10px] uppercase">Evaluated Candidate Model</div>
              <div className="text-[var(--status-success)] font-bold">{candidateResult.candidate_evaluation.version}</div>
              <div className="text-[var(--text-secondary)]">Holdout MAE: {candidateResult.candidate_evaluation.holdout_mae_gb} GB ({candidateResult.candidate_evaluation.mae_improvement_pct}% improvement)</div>
              <div className="text-[var(--text-secondary)]">Coverage: {candidateResult.candidate_evaluation.holdout_coverage_pct}%</div>
            </div>
          </div>

          <div className="pt-2 text-xs text-[var(--text-secondary)] flex items-center justify-between">
            <span>Governance Verdict: <strong className="text-[var(--text-primary)]">{candidateResult.governance_decision.recommended_action}</strong></span>
            <span>Sign-off Required: <strong>{candidateResult.governance_decision.required_approver}</strong></span>
          </div>
        </div>
      )}

      {/* Monitored Workload Input Metrics Drift Table */}
      {sentinel && (
        <div className="titan-card rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={18} className="text-[var(--accent-primary)]" />
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Workload Input Metrics Drift Monitor
              </h3>
            </div>
            <span className="text-xs font-mono text-[var(--text-muted)]">
              Reference: {sentinel.data_quality.reference_window_samples}h vs Evaluation: {sentinel.data_quality.evaluation_window_samples}h
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                  <th className="pb-2.5">Input Feature</th>
                  <th className="pb-2.5">Reference Dist (Mean / P95)</th>
                  <th className="pb-2.5">Current Dist (Mean / P95)</th>
                  <th className="pb-2.5">PSI Score</th>
                  <th className="pb-2.5">KS p-value</th>
                  <th className="pb-2.5 text-right">Drift Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]/40">
                {Object.entries(sentinel.workload_data_drift.metrics_breakdown).map(([name, d]) => (
                  <tr key={name} className="hover:bg-[var(--surface-secondary)]/30 transition-colors">
                    <td className="py-2.5 text-[var(--text-primary)] font-semibold">{name}</td>
                    <td className="py-2.5 text-[var(--text-secondary)]">
                      {d.reference_distribution.mean} / {d.reference_distribution.p95}
                    </td>
                    <td className="py-2.5 text-[var(--text-secondary)]">
                      {d.current_distribution.mean} / {d.current_distribution.p95}
                    </td>
                    <td className="py-2.5 font-bold text-[var(--text-primary)]">{d.psi.toFixed(4)}</td>
                    <td className="py-2.5 text-[var(--text-secondary)]">{d.ks_p_value.toFixed(4)}</td>
                    <td className="py-2.5 text-right">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        d.severity === 'SIGNIFICANT_DRIFT'
                          ? 'bg-[var(--status-critical)]/15 text-[var(--status-critical)] border border-[var(--status-critical)]/30'
                          : d.severity === 'MODERATE_DRIFT'
                          ? 'bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/30'
                          : 'bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/30'
                      }`}>
                        {d.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Forecast vs Actual Realization Table */}
      {sentinel && sentinel.performance_reliability.forecast_vs_actual_samples.length > 0 && (
        <div className="titan-card rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingDown size={18} className="text-[var(--status-success)]" />
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Historical Forecast vs Realized Actual Telemetry
              </h3>
            </div>
            <span className="text-xs font-mono text-[var(--text-muted)]">
              Evaluated over {sentinel.performance_reliability.actual_samples_evaluated} chronological hours
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                  <th className="pb-2.5">Timestamp</th>
                  <th className="pb-2.5">Actual Used (GB)</th>
                  <th className="pb-2.5">Forecast q50 (GB)</th>
                  <th className="pb-2.5">Conformal Interval [q10, q90]</th>
                  <th className="pb-2.5">Absolute Error</th>
                  <th className="pb-2.5 text-right">In Bounds</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]/40">
                {sentinel.performance_reliability.forecast_vs_actual_samples.map((s, idx) => (
                  <tr key={idx} className="hover:bg-[var(--surface-secondary)]/30 transition-colors">
                    <td className="py-2.5 text-[var(--text-secondary)]">{s.timestamp.slice(0, 16).replace('T', ' ')}</td>
                    <td className="py-2.5 font-bold text-[var(--text-primary)]">{s.actual_used_gb}</td>
                    <td className="py-2.5 text-[var(--accent-primary)] font-semibold">{s.predicted_q50_gb}</td>
                    <td className="py-2.5 text-[var(--text-muted)]">[{s.predicted_q10_gb}, {s.predicted_q90_gb}]</td>
                    <td className="py-2.5 font-bold text-[var(--text-primary)]">{s.absolute_error_gb} GB</td>
                    <td className="py-2.5 text-right">
                      {s.within_interval ? (
                        <span className="text-[var(--status-success)] font-bold">YES</span>
                      ) : (
                        <span className="text-[var(--status-critical)] font-bold">OUT</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Historical Drift Timeline */}
      {history.length > 0 && (
        <div className="titan-card rounded-lg p-5 space-y-4">
          <div className="flex items-center gap-2">
            <History size={18} className="text-[var(--text-muted)]" />
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              Historical Sentinel Trust & Drift Timeline
            </h3>
          </div>

          <div className="space-y-2.5">
            {history.map((h) => (
              <div
                key={h.id}
                className="p-3 rounded-xl bg-[var(--surface-secondary)]/50 border border-[var(--border-subtle)] flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs font-mono"
              >
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getStatusColor(h.trust_status)}`}>
                    {h.trust_status}
                  </span>
                  <span className="text-[var(--text-primary)] font-medium">{h.status_reason}</span>
                </div>
                <div className="flex items-center gap-4 text-[var(--text-muted)]">
                  <span>Max PSI: {h.max_metric_psi.toFixed(3)}</span>
                  <span>Coverage: {h.empirical_coverage_pct.toFixed(1)}%</span>
                  <span>{h.evaluated_at ? new Date(h.evaluated_at).toLocaleDateString() : 'Recent'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
