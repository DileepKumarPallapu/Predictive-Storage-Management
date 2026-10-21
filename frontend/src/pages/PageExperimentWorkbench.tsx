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
          <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
            <FlaskConical className="text-obsidian-cyan" size={22} />
            Reproducible Experiment & Scientific Ablation Workbench
          </h2>
          <p className="text-xs text-obsidian-muted mt-1">
            Chronological backtesting, conformal quantile calibration, and lead-time planning ablations.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-2 bg-obsidian-panel border border-obsidian-border rounded-lg p-1 text-xs">
          <button
            onClick={() => setActiveTab('ablations')}
            className={`px-3 py-1.5 rounded font-medium transition-colors ${
              activeTab === 'ablations'
                ? 'bg-obsidian-cyan text-obsidian-bg font-bold shadow-sm'
                : 'text-obsidian-muted hover:text-obsidian-text'
            }`}
          >
            Scientific Ablation Studies
          </button>
          <button
            onClick={() => setActiveTab('backtests')}
            className={`px-3 py-1.5 rounded font-medium transition-colors ${
              activeTab === 'backtests'
                ? 'bg-obsidian-cyan text-obsidian-bg font-bold shadow-sm'
                : 'text-obsidian-muted hover:text-obsidian-text'
            }`}
          >
            Custom Backtests ({experiments.length})
          </button>
        </div>
      </div>

      {/* ABLATION STUDIES TAB */}
      {activeTab === 'ablations' && ablations && (
        <div className="space-y-6">
          {/* Study 1: Calibration */}
          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg overflow-hidden">
            <div className="px-5 py-3 border-b border-obsidian-border bg-obsidian-secondary/30 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-obsidian-text">
                  Ablation 1: Multi-Quantile Forecast Calibration (72h Horizon)
                </h3>
                <p className="text-[11px] text-obsidian-muted mt-0.5">
                  Evaluates persistence vs seasonal-naive vs uncalibrated LightGBM vs conformal calibrated intervals.
                </p>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-cyan/15 text-obsidian-cyan border border-obsidian-cyan/30">
                PROVENANCE: VOL-NVME-01
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-obsidian-secondary/60 text-obsidian-muted uppercase text-[10px] border-b border-obsidian-border">
                  <tr>
                    <th className="px-4 py-2.5">Architecture</th>
                    <th className="px-4 py-2.5">MAE (GB)</th>
                    <th className="px-4 py-2.5">RMSE (GB)</th>
                    <th className="px-4 py-2.5">Empirical Coverage</th>
                    <th className="px-4 py-2.5">Mean Width (Sharpness)</th>
                    <th className="px-4 py-2.5">Pinball Loss</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-obsidian-border">
                  {ablations.ablation_1_forecast_calibration.map((row: any, i: number) => (
                    <tr key={i} className="hover:bg-obsidian-raised/40 transition-colors">
                      <td className="px-4 py-3 font-semibold text-obsidian-text font-sans">
                        {row.model_name}
                      </td>
                      <td className="px-4 py-3 text-obsidian-cyan font-bold">{row.mae_gb} GB</td>
                      <td className="px-4 py-3 text-obsidian-muted">{row.rmse_gb} GB</td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            row.empirical_coverage >= 0.8
                              ? 'bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40'
                              : 'bg-obsidian-amber/20 text-obsidian-amber border border-obsidian-amber/40'
                          }`}
                        >
                          {(row.empirical_coverage * 100).toFixed(1)}% (Nominal 80%)
                        </span>
                      </td>
                      <td className="px-4 py-3 text-obsidian-text">{row.mean_interval_width_gb} GB</td>
                      <td className="px-4 py-3 text-obsidian-muted">{row.pinball_loss}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Study 2 & 3: Lead Time & Overhead */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Lead Time Planning */}
            <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5 space-y-4">
              <h3 className="text-sm font-bold text-obsidian-text">
                Ablation 2: Lead-Time-Aware Planning vs Reactive Alerts
              </h3>
              <p className="text-xs text-obsidian-muted leading-relaxed">
                Evaluates whether predictive quantile planning provides sufficient lead time (T_lead) to stage cold data migration before critical capacity saturation.
              </p>

              <div className="space-y-3 pt-1">
                {ablations.ablation_2_lead_time_planning.map((row: any, i: number) => (
                  <div
                    key={i}
                    className="bg-obsidian-secondary/50 rounded-lg p-3.5 border border-obsidian-border/50 text-xs font-mono space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-sans font-bold text-obsidian-text">{row.policy}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          row.emergency_breach_occurred
                            ? 'bg-obsidian-coral/20 text-obsidian-coral border border-obsidian-coral/40'
                            : 'bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40'
                        }`}
                      >
                        {row.emergency_breach_occurred ? 'Breach Occurred' : 'Safely Remediated'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-obsidian-muted">
                      <span>Warning Lead Time:</span>
                      <span className="text-obsidian-cyan font-bold text-sm">+{row.warning_lead_time_hours} hrs</span>
                    </div>
                    <div className="text-[11px] text-obsidian-muted font-sans italic">
                      {row.operational_window}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Intervention Overhead */}
            <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5 space-y-4">
              <h3 className="text-sm font-bold text-obsidian-text">
                Ablation 3: Migration Overhead & Tail Latency SLAs
              </h3>
              <p className="text-xs text-obsidian-muted leading-relaxed">
                Demonstrates that modeling transient migration latency inflation (ΔLatency P95) prevents secondary SLA violations during remediation.
              </p>

              <div className="space-y-3 pt-1">
                {ablations.ablation_3_intervention_overhead.map((row: any, i: number) => (
                  <div
                    key={i}
                    className="bg-obsidian-secondary/50 rounded-lg p-3.5 border border-obsidian-border/50 text-xs font-mono space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-sans font-bold text-obsidian-text">{row.strategy}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          row.recommendation_engine_action.includes('Ranked')
                            ? 'bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40'
                            : 'bg-obsidian-amber/20 text-obsidian-amber border border-obsidian-amber/40'
                        }`}
                      >
                        {row.recommendation_engine_action}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-obsidian-muted">
                      <div>Duration: <span className="text-obsidian-text font-bold">{row.migration_duration_hours}h</span></div>
                      <div>Penalty: <span className="text-obsidian-amber font-bold">+{row.latency_inflation_pct}%</span></div>
                      <div>Peak P95: <span className="text-obsidian-text font-bold">{row.peak_latency_ms} ms</span></div>
                      <div>SLA Limit: <span className="text-obsidian-text font-bold">{row.sla_limit_ms} ms</span></div>
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
          <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5">
            <h3 className="text-sm font-bold text-obsidian-text mb-3">Launch Chronological Backtest</h3>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
              <div>
                <label className="block text-obsidian-muted mb-1 font-medium">Experiment Name:</label>
                <input
                  type="text"
                  value={expName}
                  onChange={(e) => setExpName(e.target.value)}
                  className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-obsidian-text focus:border-obsidian-cyan"
                />
              </div>

              <div>
                <label className="block text-obsidian-muted mb-1 font-medium">Candidate Architecture:</label>
                <select
                  value={modelType}
                  onChange={(e) => setModelType(e.target.value)}
                  className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-obsidian-text font-semibold focus:border-obsidian-cyan cursor-pointer"
                >
                  <option value="LightGBM">LightGBM Multi-Quantile Regressor</option>
                  <option value="SeasonalNaive">Seasonal-Naive Baseline</option>
                  <option value="Persistence">Persistence Baseline</option>
                </select>
              </div>

              <div>
                <label className="block text-obsidian-muted mb-1 font-medium">Evaluation Horizon:</label>
                <select
                  value={horizon}
                  onChange={(e) => setHorizon(Number(e.target.value))}
                  className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-obsidian-text font-mono focus:border-obsidian-cyan cursor-pointer"
                >
                  <option value={24}>24 Hours Lead Time</option>
                  <option value={72}>72 Hours Lead Time</option>
                  <option value={168}>168 Hours (7 Days)</option>
                </select>
              </div>

              <div className="flex items-end">
                <button
                  onClick={handleRunBacktest}
                  disabled={running}
                  className="w-full py-2 px-4 rounded bg-obsidian-cyan hover:opacity-90 text-obsidian-bg font-bold text-xs flex items-center justify-center gap-2 transition-opacity"
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
            <div className="bg-obsidian-panel border border-obsidian-border rounded-lg overflow-hidden">
              <div className="px-4 py-3 border-b border-obsidian-border flex items-center justify-between">
                <h3 className="text-sm font-semibold text-obsidian-text">Empirical Model Comparison Results</h3>
                <span className="text-xs text-obsidian-muted font-mono">{experiments.length} Executed Runs</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-obsidian-secondary/50 text-obsidian-muted uppercase text-[10px] border-b border-obsidian-border">
                    <tr>
                      <th className="px-4 py-2.5">Experiment & Model</th>
                      <th className="px-4 py-2.5">Horizon</th>
                      <th className="px-4 py-2.5">Train / Test Split</th>
                      <th className="px-4 py-2.5">MAE (GB)</th>
                      <th className="px-4 py-2.5">RMSE (GB)</th>
                      <th className="px-4 py-2.5">Pinball Loss</th>
                      <th className="px-4 py-2.5">Coverage (q10-q90)</th>
                      <th className="px-4 py-2.5 text-right">Manifest</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-obsidian-border">
                    {experiments.map((exp) => (
                      <tr key={exp.id} className="hover:bg-obsidian-raised/40 transition-colors">
                        <td className="px-4 py-3 font-semibold text-obsidian-text font-sans">
                          {exp.name}
                          <div className="text-[10px] font-mono text-obsidian-cyan">{exp.model_type}</div>
                        </td>
                        <td className="px-4 py-3 text-obsidian-text">+{exp.horizon_hours}h</td>
                        <td className="px-4 py-3 text-obsidian-muted">{exp.train_samples} / {exp.test_samples}</td>
                        <td className="px-4 py-3 font-bold text-obsidian-text">{exp.mae.toFixed(1)} GB</td>
                        <td className="px-4 py-3 text-obsidian-muted">{exp.rmse.toFixed(1)} GB</td>
                        <td className="px-4 py-3 text-obsidian-cyan">{exp.pinball_loss.toFixed(2)}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            exp.interval_coverage >= 0.78
                              ? 'bg-obsidian-teal/20 text-obsidian-teal'
                              : 'bg-obsidian-amber/20 text-obsidian-amber'
                          }`}>
                            {(exp.interval_coverage * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => handleDownloadManifest(exp.manifest)}
                            className="px-2.5 py-1 rounded bg-obsidian-secondary hover:bg-obsidian-raised border border-obsidian-border text-obsidian-text hover:border-obsidian-cyan text-[11px] inline-flex items-center gap-1 font-sans"
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
    </div>
  );
};
