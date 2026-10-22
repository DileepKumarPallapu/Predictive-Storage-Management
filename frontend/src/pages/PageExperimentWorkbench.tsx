import React, { useState, useEffect } from 'react';
import { api, ExperimentItem } from '../api/client';
import { FlaskConical, Play, Download, CheckCircle2, ShieldCheck, Layers, ArrowRight } from 'lucide-react';
import { EmptyState } from '../components/EmptyState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

export const PageExperimentWorkbench: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'backtests' | 'ablations'>('ablations');
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [ablations, setAblations] = useState<any>(null);
  const [expName, setExpName] = useState('Quantile Evaluation v1');
  const [modelType, setModelType] = useState('LightGBM');
  const [horizon, setHorizon] = useState<number>(72);
  const [running, setRunning] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [expData, ablData] = await Promise.all([
        api.getExperiments(),
        api.getAblationStudies(),
      ]);
      setExperiments(expData);
      setAblations(ablData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRunBacktest = async () => {
    setRunning(true);
    try {
      await api.runExperiment({
        name: expName,
        dataset_name: 'Synthetic Multi-Tier Enterprise Storage Benchmark',
        model_type: modelType,
        horizon_hours: horizon,
      });
      const data = await api.getExperiments();
      setExperiments(data);
      setActiveTab('backtests');
    } catch (e) {
      console.error(e);
    } finally {
      setRunning(false);
    }
  };

  const handleDownloadManifest = (manifest: Record<string, any>) => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(manifest, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute('href', dataStr);
    dlAnchor.setAttribute('download', `experiment_manifest_${Date.now()}.json`);
    dlAnchor.click();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center shadow-xs">
              <FlaskConical size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              Reproducible Experiment & Scientific Ablation Workbench
            </h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
            Chronological backtesting, conformal quantile calibration, and lead-time planning ablations.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-2 titan-card rounded-xl p-1.5 text-xs">
          <button
            onClick={() => setActiveTab('ablations')}
            className={`px-3.5 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'ablations'
                ? 'btn-ember-primary font-bold shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Scientific Ablation Studies
          </button>
          <button
            onClick={() => setActiveTab('backtests')}
            className={`px-3.5 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'backtests'
                ? 'btn-ember-primary font-bold shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Custom Backtests ({experiments.length})
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton rows={6} height="h-10" />
      ) : (
        <>
          {/* ABLATION STUDIES TAB */}
          {activeTab === 'ablations' && ablations && (
            <div className="space-y-6">
              {/* Study 1: Calibration */}
              <div className="titan-card rounded-xl overflow-hidden">
                <div className="px-5 py-4 border-b border-[var(--border-subtle)] bg-[var(--surface-secondary)]/40 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">
                      Ablation 1: Multi-Quantile Forecast Calibration (72h Horizon)
                    </h3>
                    <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                      Evaluates persistence vs seasonal-naive vs uncalibrated LightGBM vs conformal calibrated intervals.
                    </p>
                  </div>
                  <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/35 font-semibold">
                    PROVENANCE: VOL-NVME-01
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-[var(--surface-secondary)]/60 text-[var(--text-secondary)] uppercase text-[10px] border-b border-[var(--border-subtle)]">
                      <tr>
                        <th className="px-5 py-3 font-semibold">Architecture</th>
                        <th className="px-5 py-3 font-semibold">MAE (GB)</th>
                        <th className="px-5 py-3 font-semibold">RMSE (GB)</th>
                        <th className="px-5 py-3 font-semibold">Empirical Coverage</th>
                        <th className="px-5 py-3 font-semibold">Mean Width (Sharpness)</th>
                        <th className="px-5 py-3 font-semibold">Pinball Loss</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)]">
                      {ablations.ablation_1_forecast_calibration.map((row: any, i: number) => (
                        <tr key={i} className="hover:bg-[var(--surface-secondary)]/50 transition-colors">
                          <td className="px-5 py-3.5 font-semibold text-[var(--text-primary)] font-sans">
                            {row.model_name}
                          </td>
                          <td className="px-5 py-3.5 text-[var(--accent-primary)] font-bold">{row.mae_gb} GB</td>
                          <td className="px-5 py-3.5 text-[var(--text-secondary)]">{row.rmse_gb} GB</td>
                          <td className="px-5 py-3.5">
                            <span
                              className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                                row.empirical_coverage >= 0.8
                                  ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm'
                                  : 'bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40 shadow-sm'
                              }`}
                            >
                              {(row.empirical_coverage * 100).toFixed(1)}% (Nominal 80%)
                            </span>
                          </td>
                          <td className="px-5 py-3.5 text-[var(--text-primary)]">{row.mean_interval_width_gb} GB</td>
                          <td className="px-5 py-3.5 text-[var(--text-secondary)]">{row.pinball_loss}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Study 2 & 3: Lead Time & Overhead */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Lead Time Planning */}
                <div className="titan-card rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">
                    Ablation 2: Lead-Time-Aware Planning vs Reactive Alerts
                  </h3>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    Evaluates whether predictive quantile planning provides sufficient lead time (T_lead) to stage cold data migration before critical capacity saturation.
                  </p>

                  <div className="space-y-3 pt-1">
                    {ablations.ablation_2_lead_time_planning.map((row: any, i: number) => (
                      <div
                        key={i}
                        className="bg-[var(--surface-secondary)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)] text-xs font-mono space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-sans font-bold text-[var(--text-primary)]">{row.policy}</span>
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                              row.emergency_breach_occurred
                                ? 'bg-[var(--status-critical)]/15 text-[var(--status-critical)] border border-[var(--status-critical)]/40 shadow-sm'
                                : 'bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm'
                            }`}
                          >
                            {row.emergency_breach_occurred ? 'Breach Occurred' : 'Safely Remediated'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[var(--text-secondary)]">
                          <span>Warning Lead Time:</span>
                          <span className="text-[var(--accent-primary)] font-bold text-sm">+{row.warning_lead_time_hours} hrs</span>
                        </div>
                        <div className="text-[11px] text-[var(--text-secondary)] font-sans italic">
                          {row.operational_window}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Intervention Overhead */}
                <div className="titan-card rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">
                    Ablation 3: Migration Overhead & Tail Latency SLAs
                  </h3>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    Demonstrates that modeling transient migration latency inflation (ΔLatency P95) prevents secondary SLA violations during remediation.
                  </p>

                  <div className="space-y-3 pt-1">
                    {ablations.ablation_3_intervention_overhead.map((row: any, i: number) => (
                      <div
                        key={i}
                        className="bg-[var(--surface-secondary)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)] text-xs font-mono space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-sans font-bold text-[var(--text-primary)]">{row.strategy}</span>
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                              row.recommendation_engine_action.includes('Ranked')
                                ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm'
                                : 'bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40 shadow-sm'
                            }`}
                          >
                            {row.recommendation_engine_action}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-[11px] text-[var(--text-secondary)]">
                          <div>Duration: <span className="text-[var(--text-primary)] font-bold">{row.migration_duration_hours}h</span></div>
                          <div>Penalty: <span className="text-[var(--status-warning)] font-bold">+{row.latency_inflation_pct}%</span></div>
                          <div>Peak P95: <span className="text-[var(--text-primary)] font-bold">{row.peak_latency_ms} ms</span></div>
                          <div>SLA Limit: <span className="text-[var(--text-primary)] font-bold">{row.sla_limit_ms} ms</span></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* CUSTOM BACKTESTS TAB */}
          {activeTab === 'backtests' && (
            <div className="space-y-6">
              {/* Experiment Runner Controls */}
              <div className="titan-card rounded-xl p-5">
                <h3 className="text-sm font-bold text-[var(--text-primary)] mb-3">Launch Chronological Backtest</h3>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
                  <div>
                    <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">Experiment Name:</label>
                    <input
                      type="text"
                      value={expName}
                      onChange={(e) => setExpName(e.target.value)}
                      className="w-full bg-[var(--surface-secondary)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-primary)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">Candidate Architecture:</label>
                    <select
                      value={modelType}
                      onChange={(e) => setModelType(e.target.value)}
                      className="w-full bg-[var(--surface-secondary)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-primary)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-semibold focus:outline-none cursor-pointer"
                    >
                      <option value="LightGBM" className="bg-[var(--surface-panel)]">LightGBM Multi-Quantile Regressor</option>
                      <option value="SeasonalNaive" className="bg-[var(--surface-panel)]">Seasonal-Naive Baseline</option>
                      <option value="Persistence" className="bg-[var(--surface-panel)]">Persistence Baseline</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">Evaluation Horizon:</label>
                    <select
                      value={horizon}
                      onChange={(e) => setHorizon(Number(e.target.value))}
                      className="w-full bg-[var(--surface-secondary)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-primary)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
                    >
                      <option value={24} className="bg-[var(--surface-panel)]">24 Hours Lead Time</option>
                      <option value={72} className="bg-[var(--surface-panel)]">72 Hours Lead Time</option>
                      <option value={168} className="bg-[var(--surface-panel)]">168 Hours (7 Days)</option>
                    </select>
                  </div>

                  <div className="flex items-end">
                    <button
                      onClick={handleRunBacktest}
                      disabled={running}
                      className="w-full btn-ember-primary py-2 px-4 rounded-lg font-bold text-xs flex items-center justify-center gap-2"
                    >
                      <Play size={14} />
                      {running ? 'Running Backtest...' : 'Execute Backtest'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Results Table */}
              {experiments.length === 0 ? (
                <EmptyState
                  title="No Backtest Runs Recorded"
                  description="Configure an evaluation horizon and launch a chronological backtest to compare model pinball losses."
                  actionText="Run Initial Backtest"
                  onAction={handleRunBacktest}
                />
              ) : (
                <div className="titan-card rounded-xl overflow-hidden">
                  <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-[var(--text-primary)]">Empirical Model Comparison Results</h3>
                    <span className="text-xs text-[var(--text-secondary)] font-mono">{experiments.length} Executed Runs</span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-[var(--surface-secondary)]/60 text-[var(--text-secondary)] uppercase text-[10px] border-b border-[var(--border-subtle)]">
                        <tr>
                          <th className="px-5 py-3 font-semibold">Experiment & Model</th>
                          <th className="px-5 py-3 font-semibold">Horizon</th>
                          <th className="px-5 py-3 font-semibold">Train / Test Split</th>
                          <th className="px-5 py-3 font-semibold">MAE (GB)</th>
                          <th className="px-5 py-3 font-semibold">RMSE (GB)</th>
                          <th className="px-5 py-3 font-semibold">Pinball Loss</th>
                          <th className="px-5 py-3 font-semibold">Coverage (q10-q90)</th>
                          <th className="px-5 py-3 font-semibold text-right">Manifest</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border-subtle)]">
                        {experiments.map((exp) => (
                          <tr key={exp.id} className="hover:bg-[var(--surface-secondary)]/50 transition-colors">
                            <td className="px-5 py-3.5 font-semibold text-[var(--text-primary)] font-sans">
                              {exp.name}
                              <div className="text-[10px] font-mono text-[var(--accent-primary)] font-normal">{exp.model_type}</div>
                            </td>
                            <td className="px-5 py-3.5 text-[var(--text-primary)]">+{exp.horizon_hours}h</td>
                            <td className="px-5 py-3.5 text-[var(--text-secondary)]">{exp.train_samples} / {exp.test_samples}</td>
                            <td className="px-5 py-3.5 font-bold text-[var(--text-primary)]">{exp.mae.toFixed(1)} GB</td>
                            <td className="px-5 py-3.5 text-[var(--text-secondary)]">{exp.rmse.toFixed(1)} GB</td>
                            <td className="px-5 py-3.5 text-[var(--accent-primary)] font-bold">{exp.pinball_loss.toFixed(2)}</td>
                            <td className="px-5 py-3.5">
                              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                                exp.interval_coverage >= 0.78
                                  ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm'
                                  : 'bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40 shadow-sm'
                              }`}>
                                {(exp.interval_coverage * 100).toFixed(1)}%
                              </span>
                            </td>
                            <td className="px-5 py-3.5 text-right">
                              <button
                                onClick={() => handleDownloadManifest(exp.manifest)}
                                className="btn-ember-secondary px-3 py-1.5 rounded-lg text-[11px] inline-flex items-center gap-1.5 font-sans font-medium"
                              >
                                <Download size={12} /> JSON
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};
