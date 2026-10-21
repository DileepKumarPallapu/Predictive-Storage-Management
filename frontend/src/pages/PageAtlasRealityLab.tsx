import React, { useState, useEffect } from 'react';
import {
  Compass,
  Database,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Network,
  Clock,
  Layers,
  FileCode,
  ShieldCheck,
  Flame,
  Activity,
  TrendingUp,
  Cpu,
  Lock,
  Sparkles,
  BarChart3,
  Scale,
  FlaskConical,
  Eye,
  ChevronRight,
  Info
} from 'lucide-react';
import { api } from '../api/client';

export const PageAtlasRealityLab: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    'overview' | 'comparison' | 'calibration' | 'effects' | 'experiments' | 'gated_planning' | 'voe_coverage'
  >('overview');

  const [overviewData, setOverviewData] = useState<any | null>(null);
  const [configs, setConfigs] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [discrepancyData, setDiscrepancyData] = useState<any | null>(null);
  const [actionEffects, setActionEffects] = useState<any[]>([]);
  const [fidelityData, setFidelityData] = useState<any | null>(null);
  const [gatedPlan, setGatedPlan] = useState<any | null>(null);
  const [experiments, setExperiments] = useState<any[]>([]);
  const [voeGaps, setVoeGaps] = useState<any[]>([]);

  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('vol-nvme-tier1-db');
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // New Experiment Form
  const [expName, setExpName] = useState<string>('Controlled 4KB Latency Profile');
  const [expType, setExpType] = useState<string>('SIM_TO_REAL_COMPARISON');
  const [expObjective, setExpObjective] = useState<string>('Quantify controller tail latency under sustained write bursts');
  const [expHypothesis, setExpHypothesis] = useState<string>('Queue depth > 4.0 inflates tail latency by 2.2x');

  useEffect(() => {
    loadInitialData();
  }, [selectedDeviceId]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [ov, cfgs, rns, eff, fid, gaps, exps] = await Promise.all([
        api.getAtlasOverview(),
        api.getAtlasCalibrationConfigs(selectedDeviceId),
        api.getAtlasCalibrationRuns(),
        api.getAtlasActionEffects(selectedDeviceId),
        api.getAtlasFidelity(selectedDeviceId),
        api.getAtlasVoeGaps(selectedDeviceId),
        api.getAtlasExperiments(),
      ]);

      setOverviewData(ov);
      setConfigs(cfgs);
      setRuns(rns);
      setActionEffects(eff);
      setFidelityData(fid);
      setVoeGaps(gaps);
      setExperiments(exps);

      if (rns.length > 0) {
        const firstRunId = rns[0].id;
        setSelectedRunId(firstRunId);
        loadDiscrepancy(firstRunId);
      }

      // Auto evaluate gated plan
      const planRes = await api.evaluateAtlasGatedPlan({ device_id: selectedDeviceId });
      setGatedPlan(planRes);
    } catch (err: any) {
      console.error('Failed to load Atlas data:', err);
      setMessage({ type: 'error', text: 'Error loading Atlas reality lab: ' + (err.message || String(err)) });
    } finally {
      setLoading(false);
    }
  };

  const loadDiscrepancy = async (runId: string) => {
    try {
      const disc = await api.getAtlasDiscrepancy(runId);
      setDiscrepancyData(disc);
    } catch (err: any) {
      console.error('Failed to load discrepancy:', err);
    }
  };

  const handleTriggerCalibration = async () => {
    setActionLoading(true);
    try {
      const res = await api.runAtlasCalibration({
        device_id: selectedDeviceId,
        simulator_version: 'DigitalTwin-v4.0',
      });
      setMessage({
        type: 'success',
        text: `Calibration run ${res.run_id} completed: Evaluation RMSE ${res.evaluation_rmse}% (Status: ${res.calibration_status}).`,
      });
      await loadInitialData();
      if (res.run_id) {
        setSelectedRunId(res.run_id);
        await loadDiscrepancy(res.run_id);
        setActiveTab('comparison');
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Calibration failed: ' + (err.message || String(err)) });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateExperiment = async () => {
    setActionLoading(true);
    try {
      const res = await api.createAtlasExperiment({
        name: expName,
        experiment_type: expType,
        objective: expObjective,
        hypothesis: expHypothesis,
        target_device_id: selectedDeviceId,
        configuration: { test_block_size_kb: 4, duration_minutes: 30 },
        safety_restrictions: { mode: 'ISOLATED_TEST_SANDBOX', zero_host_disk_mutations: true },
      });
      setMessage({
        type: 'success',
        text: `Experiment ${res.experiment_id} completed in isolated sandbox with zero host mutations.`,
      });
      const exps = await api.getAtlasExperiments();
      setExperiments(exps);
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Experiment execution error: ' + (err.message || String(err)) });
    } finally {
      setActionLoading(false);
    }
  };

  const getFidelityBadgeClass = (status: string) => {
    switch (status) {
      case 'HIGH_FIDELITY':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      case 'MODERATE_FIDELITY':
        return 'bg-obsidian-cyan/20 text-obsidian-cyan border-obsidian-cyan/40';
      case 'LIMITED_SCOPE':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'DEGRADED':
        return 'bg-obsidian-coral/20 text-obsidian-coral border-obsidian-coral/40';
      default:
        return 'bg-obsidian-panel text-obsidian-muted border-obsidian-border';
    }
  };

  const getVerdictBadgeClass = (verdict: string) => {
    switch (verdict) {
      case 'SUPPORTED_RECOMMENDATION':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      case 'SAFE_TO_SIMULATE':
        return 'bg-obsidian-cyan/20 text-obsidian-cyan border-obsidian-cyan/40';
      case 'REQUIRES_HUMAN_REVIEW':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'REQUIRES_ADDITIONAL_EVIDENCE':
        return 'bg-obsidian-purple/20 text-obsidian-purple border-obsidian-purple/40';
      case 'REJECTED_BY_HARD_CONSTRAINT':
        return 'bg-obsidian-coral/20 text-obsidian-coral border-obsidian-coral/40';
      default:
        return 'bg-obsidian-panel text-obsidian-muted border-obsidian-border';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Reality Calibration Principles */}
      <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-obsidian-cyan/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2.5 h-2.5 rounded-full bg-obsidian-cyan shadow-[0_0_10px_var(--accent-cyan)]" />
              <span className="text-xs font-mono uppercase tracking-widest text-obsidian-cyan font-bold">
                AEGISSTOR ATLAS — REALITY CALIBRATION LAB
              </span>
            </div>
            <h1 className="text-2xl font-black tracking-tight text-obsidian-text">
              Reality-Calibrated Storage Digital Twin & Sim-to-Real Validation
            </h1>
            <p className="text-sm text-obsidian-muted mt-1 max-w-3xl">
              Quantifies discrepancy between simulated predictions and actual storage measurements.
              Evaluates held-out error, defines empirical condition envelopes, and gates interventions
              to prevent unsupported simulations from being treated as established facts.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={selectedDeviceId}
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              className="bg-obsidian-panel border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-text font-mono focus:outline-none focus:border-obsidian-cyan"
            >
              <option value="vol-nvme-tier1-db">Production E-Commerce OLTP NVMe</option>
              <option value="vol-sas-tier2-analytics">Corporate Data Warehouse SAS</option>
              <option value="vol-hdd-archive">Regulatory Compliance HDD Archive</option>
              <option value="vol-nvme-cache">Redis / Kafka High-Throughput NVMe</option>
            </select>

            <button
              onClick={handleTriggerCalibration}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-obsidian-cyan/15 hover:bg-obsidian-cyan/25 border border-obsidian-cyan/40 text-obsidian-cyan text-xs font-bold transition-all disabled:opacity-50"
            >
              <Scale size={14} className={actionLoading ? 'animate-spin' : ''} />
              Run Held-Out Calibration
            </button>
          </div>
        </div>

        {/* Guarantees & Active Status Badges */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-4 gap-3 pt-4 border-t border-obsidian-border/60 text-xs">
          <div className="flex items-center gap-2">
            <Scale size={14} className="text-obsidian-cyan shrink-0" />
            <span className="text-obsidian-muted font-mono">Test Leakage:</span>
            <span className="font-mono font-bold text-emerald-400">PREVENTED (Held-Out Eval)</span>
          </div>
          <div className="flex items-center gap-2">
            <Database size={14} className="text-obsidian-purple shrink-0" />
            <span className="text-obsidian-muted font-mono">Missing Values:</span>
            <span className="font-mono font-bold text-obsidian-purple">NEVER ZERO-SUBSTITUTED</span>
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck size={14} className="text-amber-400 shrink-0" />
            <span className="text-obsidian-muted font-mono">Calibration Accuracy:</span>
            <span className="font-mono font-bold text-amber-400">NO 100% CLAIMS</span>
          </div>
          <div className="flex items-center gap-2">
            <Lock size={14} className="text-emerald-400 shrink-0" />
            <span className="text-obsidian-muted font-mono">Physical Disks:</span>
            <span className="font-mono font-bold text-emerald-400">ZERO MUTATIONS</span>
          </div>
        </div>
      </div>

      {/* Global Notification */}
      {message && (
        <div
          className={`p-4 rounded-lg border text-xs flex items-center justify-between ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : message.type === 'error'
              ? 'bg-obsidian-coral/10 border-obsidian-coral/30 text-obsidian-coral'
              : 'bg-obsidian-cyan/10 border-obsidian-cyan/30 text-obsidian-cyan'
          }`}
        >
          <div className="flex items-center gap-2">
            {message.type === 'success' ? (
              <CheckCircle2 size={16} />
            ) : message.type === 'error' ? (
              <AlertTriangle size={16} />
            ) : (
              <Info size={16} />
            )}
            <span>{message.text}</span>
          </div>
          <button onClick={() => setMessage(null)} className="text-obsidian-muted hover:text-obsidian-text">
            ✕
          </button>
        </div>
      )}

      {/* Navigation Tabs (7 Sub-Views) */}
      <div className="flex flex-wrap items-center gap-2 border-b border-obsidian-border pb-3">
        {[
          { id: 'overview', label: 'Reality Overview', icon: Compass },
          { id: 'comparison', label: 'Sim-to-Real Comparison', icon: BarChart3 },
          { id: 'calibration', label: 'Calibration Lab', icon: Scale },
          { id: 'effects', label: 'Action-Effect Evidence', icon: Sliders },
          { id: 'experiments', label: 'Experiment Workbench', icon: FlaskConical, badge: experiments.length },
          { id: 'gated_planning', label: 'Evidence-Gated Planning', icon: ShieldCheck },
          { id: 'voe_coverage', label: 'Coverage & Value-of-Experiment', icon: TrendingUp, badge: voeGaps.length },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
                isActive
                  ? 'bg-obsidian-panel text-obsidian-cyan border border-obsidian-cyan/40 shadow-sm'
                  : 'text-obsidian-muted hover:text-obsidian-text hover:bg-obsidian-panel/50 border border-transparent'
              }`}
            >
              <Icon size={14} className={isActive ? 'text-obsidian-cyan' : ''} />
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-obsidian-panel border border-obsidian-border text-obsidian-text">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB A: REALITY OVERVIEW */}
      {activeTab === 'overview' && overviewData && (
        <div className="space-y-6">
          {/* Key Metric Highlights */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-4 shadow-md">
              <span className="text-xs font-mono text-obsidian-muted">Total Storage Fleet</span>
              <div className="text-2xl font-black text-obsidian-text mt-1">{overviewData.total_storage_devices} Volumes</div>
            </div>
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-4 shadow-md">
              <span className="text-xs font-mono text-obsidian-muted">Calibrated Configs</span>
              <div className="text-2xl font-black text-obsidian-cyan mt-1">{overviewData.calibrated_devices_count} Active</div>
            </div>
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-4 shadow-md">
              <span className="text-xs font-mono text-obsidian-muted">Calibration Coverage</span>
              <div className="text-2xl font-black text-emerald-400 mt-1">{overviewData.calibration_coverage_pct}%</div>
            </div>
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-4 shadow-md">
              <span className="text-xs font-mono text-obsidian-muted">Digital Twin Version</span>
              <div className="text-2xl font-black text-obsidian-purple mt-1">v4.0 Held-Out</div>
            </div>
          </div>

          {/* Data Sources & Reality Connectors */}
          <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database size={16} className="text-obsidian-cyan" />
                <h3 className="text-sm font-bold text-obsidian-text">Connected Storage Reality Adapters</h3>
              </div>
              <span className="text-xs font-mono text-obsidian-muted">Provenance Explicitly Tracked</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-obsidian-panel/80 text-obsidian-muted font-mono uppercase text-[10px]">
                  <tr>
                    <th className="py-2.5 px-4">Data Source Name</th>
                    <th className="py-2.5 px-4">Adapter Implementation</th>
                    <th className="py-2.5 px-4">Provenance Classification</th>
                    <th className="py-2.5 px-4">Stream Status</th>
                    <th className="py-2.5 px-4">Heartbeat Freshness</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-obsidian-border">
                  {overviewData.data_sources?.map((src: any) => (
                    <tr key={src.name} className="hover:bg-obsidian-panel/30">
                      <td className="py-2.5 px-4 font-bold text-obsidian-text">{src.name}</td>
                      <td className="py-2.5 px-4 font-mono text-obsidian-cyan">{src.adapter}</td>
                      <td className="py-2.5 px-4 font-mono">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-obsidian-panel border border-obsidian-border text-obsidian-text">
                          {src.provenance}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono text-emerald-400">{src.status}</td>
                      <td className="py-2.5 px-4 font-mono text-obsidian-muted">
                        {src.freshness_seconds > 0 ? `${src.freshness_seconds}s ago` : 'Static Benchmark'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Calibration Runs */}
          <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
            <h3 className="text-sm font-bold text-obsidian-text">Recent Out-of-Sample Calibration Runs</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-obsidian-panel/80 text-obsidian-muted font-mono uppercase text-[10px]">
                  <tr>
                    <th className="py-2.5 px-4">Run ID</th>
                    <th className="py-2.5 px-4">Simulator Version</th>
                    <th className="py-2.5 px-4">Calibration Status</th>
                    <th className="py-2.5 px-4">Evaluation RMSE</th>
                    <th className="py-2.5 px-4">Evaluation MAE</th>
                    <th className="py-2.5 px-4">Systematic Bias</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-obsidian-border">
                  {overviewData.recent_runs?.map((r: any) => (
                    <tr key={r.id} className="hover:bg-obsidian-panel/30">
                      <td className="py-2.5 px-4 font-mono text-obsidian-cyan font-bold">{r.id}</td>
                      <td className="py-2.5 px-4 font-mono">{r.simulator_version}</td>
                      <td className="py-2.5 px-4 font-mono">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getFidelityBadgeClass(r.status)}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono text-emerald-400 font-bold">{r.evaluation_rmse}%</td>
                      <td className="py-2.5 px-4 font-mono text-obsidian-text">{r.evaluation_mae}%</td>
                      <td className="py-2.5 px-4 font-mono text-amber-400">{r.bias > 0 ? `+${r.bias}` : r.bias}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB B: SIM-TO-REAL COMPARISON */}
      {activeTab === 'comparison' && discrepancyData && (
        <div className="space-y-6">
          {/* Discrepancy KPI Summary */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-4 shadow-md">
              <span className="text-xs font-mono text-obsidian-muted">Overall Held-Out RMSE</span>
              <div className="text-2xl font-black text-emerald-400 mt-1">{discrepancyData.overall_rmse}%</div>
            </div>
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-4 shadow-md">
              <span className="text-xs font-mono text-obsidian-muted">Systematic Bias Direction</span>
              <div className="text-base font-bold text-amber-400 mt-1">
                {discrepancyData.bias_direction} ({discrepancyData.systematic_bias > 0 ? `+${discrepancyData.systematic_bias}` : discrepancyData.systematic_bias}%)
              </div>
            </div>
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-4 shadow-md">
              <span className="text-xs font-mono text-obsidian-muted">Horizon Error Drift</span>
              <div className="text-base font-bold text-obsidian-cyan mt-1">{discrepancyData.time_dependent_drift}</div>
              <span className="text-[10px] font-mono text-obsidian-muted">Expansion ratio: {discrepancyData.drift_expansion_ratio}x</span>
            </div>
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-4 shadow-md">
              <span className="text-xs font-mono text-obsidian-muted">Evaluated Samples</span>
              <div className="text-2xl font-black text-obsidian-purple mt-1">{discrepancyData.discrepancy_count} Hours</div>
            </div>
          </div>

          {/* Workload Regime Error Breakdown */}
          <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
            <h3 className="text-sm font-bold text-obsidian-text">Discrepancy Breakdown by Workload Regime</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(discrepancyData.regime_breakdown || {}).map(([regime, stats]: [string, any]) => (
                <div key={regime} className="p-4 rounded-xl bg-obsidian-panel border border-obsidian-border space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-obsidian-text">{regime}</span>
                    <span className="text-[10px] font-mono text-obsidian-muted">{stats.sample_count} points</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-obsidian-muted font-mono">Regime RMSE:</span>
                    <span className="font-mono font-bold text-emerald-400">{stats.rmse}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-obsidian-muted font-mono">Regime MAE:</span>
                    <span className="font-mono text-obsidian-text">{stats.mae}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-obsidian-muted font-mono">Mean Bias:</span>
                    <span className="font-mono text-amber-400">{stats.mean_bias > 0 ? `+${stats.mean_bias}` : stats.mean_bias}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Synchronized Timeline & Residuals Table */}
          <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-obsidian-text">Chronological Sim-to-Real Residual Timeline</h3>
              <span className="text-xs font-mono text-obsidian-muted">e_t = Observed - Simulated</span>
            </div>

            <div className="overflow-x-auto max-h-96">
              <table className="w-full text-left text-xs">
                <thead className="bg-obsidian-panel text-obsidian-muted font-mono uppercase text-[10px] sticky top-0">
                  <tr>
                    <th className="py-2.5 px-4">Evaluation Timestamp</th>
                    <th className="py-2.5 px-4">Observed Value</th>
                    <th className="py-2.5 px-4">Simulated Value</th>
                    <th className="py-2.5 px-4">Residual (e_t)</th>
                    <th className="py-2.5 px-4">Relative Error</th>
                    <th className="py-2.5 px-4">Workload Regime</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-obsidian-border font-mono">
                  {discrepancyData.timeline?.slice(0, 30).map((pt: any, idx: number) => (
                    <tr key={idx} className="hover:bg-obsidian-panel/30">
                      <td className="py-2 px-4 text-obsidian-muted">{pt.timestamp}</td>
                      <td className="py-2 px-4 text-obsidian-text font-bold">{pt.observed.toFixed(2)}%</td>
                      <td className="py-2 px-4 text-obsidian-cyan">{pt.simulated.toFixed(2)}%</td>
                      <td className={`py-2 px-4 font-bold ${pt.residual > 0 ? 'text-amber-400' : 'text-obsidian-purple'}`}>
                        {pt.residual > 0 ? `+${pt.residual.toFixed(2)}` : pt.residual.toFixed(2)}%
                      </td>
                      <td className="py-2 px-4 text-obsidian-text">{(pt.relative_error * 100).toFixed(2)}%</td>
                      <td className="py-2 px-4 text-[10px] text-obsidian-muted">{pt.workload_regime}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB C: CALIBRATION LAB */}
      {activeTab === 'calibration' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center gap-2">
              <Scale size={16} className="text-obsidian-cyan" />
              <h3 className="text-sm font-bold text-obsidian-text">Digital Twin Calibration Controls</h3>
            </div>
            <p className="text-xs text-obsidian-muted">
              Executes parameter alignment across a calibration window (e.g. 14 days) and verifies generalization on a held-out evaluation window (7 days).
            </p>

            <div className="space-y-4 pt-2">
              <div>
                <label className="text-xs font-mono text-obsidian-muted block mb-1">Target Volume Identifier:</label>
                <input
                  type="text"
                  value={selectedDeviceId}
                  readOnly
                  className="w-full bg-obsidian-panel border border-obsidian-border rounded px-3 py-2 text-xs font-mono text-obsidian-cyan"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-obsidian-muted block mb-1">Calibration Target Metric:</label>
                <select className="w-full bg-obsidian-panel border border-obsidian-border rounded px-3 py-2 text-xs text-obsidian-text">
                  <option value="utilization_pct">Storage Capacity Utilization (%)</option>
                  <option value="latency_p95_ms">P95 Tail Latency (ms)</option>
                  <option value="throughput_mb_s">Throughput (MB/s)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-xs font-mono text-obsidian-muted block mb-1">Calibration Window:</span>
                  <input
                    type="number"
                    defaultValue={14}
                    className="w-full bg-obsidian-panel border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text font-mono"
                  />
                </div>
                <div>
                  <span className="text-xs font-mono text-obsidian-muted block mb-1">Held-out Evaluation:</span>
                  <input
                    type="number"
                    defaultValue={7}
                    className="w-full bg-obsidian-panel border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text font-mono"
                  />
                </div>
              </div>

              <button
                onClick={handleTriggerCalibration}
                disabled={actionLoading}
                className="w-full py-2.5 rounded-lg bg-obsidian-cyan/20 hover:bg-obsidian-cyan/30 border border-obsidian-cyan/40 text-obsidian-cyan text-xs font-bold transition-all disabled:opacity-50"
              >
                Execute Controlled Calibration Run →
              </button>
            </div>
          </div>

          {/* Calibration Configs List */}
          <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
            <h3 className="text-sm font-bold text-obsidian-text">Active Calibration Configurations</h3>
            <div className="space-y-3">
              {configs.map((c) => (
                <div key={c.id} className="p-4 rounded-xl bg-obsidian-panel border border-obsidian-border space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-obsidian-text">{c.name}</span>
                    <span className="text-[10px] font-mono text-obsidian-cyan">v{c.version}</span>
                  </div>
                  <div className="text-[11px] font-mono text-obsidian-muted">
                    Device: {c.device_id} • Metric: {c.target_metric}
                  </div>
                  <div className="text-[11px] font-mono text-obsidian-muted">
                    Window: {c.calibration_window_days}d cal / {c.evaluation_window_days}d eval
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB D: ACTION-EFFECT EVIDENCE */}
      {activeTab === 'effects' && (
        <div className="space-y-6">
          <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sliders size={16} className="text-obsidian-cyan" />
                <h3 className="text-sm font-bold text-obsidian-text">Reality-Calibrated Action-Effect Model</h3>
              </div>
              <span className="text-xs font-mono text-amber-400 font-bold">
                Causal Verification Explicitly Separated from Correlation
              </span>
            </div>
            <p className="text-xs text-obsidian-muted">
              Distinguishes simulation counterfactuals, controlled benchmark measurements, operational outcomes,
              and theoretical assumptions. Includes migration overhead, fabric contention, and secondary penalties.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-obsidian-panel/80 text-obsidian-muted font-mono uppercase text-[10px]">
                  <tr>
                    <th className="py-2.5 px-4">Action Type</th>
                    <th className="py-2.5 px-4">Evidence Category</th>
                    <th className="py-2.5 px-4">Empirical Sample Size</th>
                    <th className="py-2.5 px-4">Primary Headroom Effect</th>
                    <th className="py-2.5 px-4">Side-Effect Costs & Contention</th>
                    <th className="py-2.5 px-4">Causal Verification</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-obsidian-border">
                  {actionEffects.map((act) => (
                    <tr key={act.id} className="hover:bg-obsidian-panel/30">
                      <td className="py-3 px-4 font-mono font-bold text-obsidian-text">{act.action_type}</td>
                      <td className="py-3 px-4 font-mono">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-obsidian-panel border border-obsidian-border text-obsidian-cyan">
                          {act.evidence_category}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-obsidian-muted">{act.sample_size} trials</td>
                      <td className="py-3 px-4 font-mono font-bold text-emerald-400">
                        {act.primary_effect_mean > 0 ? `+${act.primary_effect_mean} GB` : `${act.primary_effect_mean} ms`}
                      </td>
                      <td className="py-3 px-4 text-[11px] text-obsidian-muted">
                        {Object.entries(act.side_effects || {}).map(([k, v]) => (
                          <div key={k} className="font-mono">
                            {k}: <span className="text-amber-400">{String(v)}</span>
                          </div>
                        ))}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {act.is_causally_verified ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                            ✓ Causal Verified
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
                            Observational Estimate
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB E: EXPERIMENT WORKBENCH */}
      {activeTab === 'experiments' && (
        <div className="space-y-6">
          <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FlaskConical size={16} className="text-obsidian-cyan" />
                <h3 className="text-sm font-bold text-obsidian-text">Controlled Experiment Workbench</h3>
              </div>
              <span className="text-xs font-mono text-emerald-400 font-bold">Isolated Sandbox Testing</span>
            </div>

            <p className="text-xs text-obsidian-muted">
              Executes controlled benchmark measurements to validate action effects, queue depth inflation, and model calibration without affecting production storage.
            </p>

            <div className="p-4 rounded-xl bg-obsidian-panel border border-obsidian-border space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-mono text-obsidian-muted block mb-1">Experiment Name:</label>
                  <input
                    type="text"
                    value={expName}
                    onChange={(e) => setExpName(e.target.value)}
                    className="w-full bg-obsidian-card border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text"
                  />
                </div>
                <div>
                  <label className="text-xs font-mono text-obsidian-muted block mb-1">Experiment Type:</label>
                  <select
                    value={expType}
                    onChange={(e) => setExpType(e.target.value)}
                    className="w-full bg-obsidian-card border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text"
                  >
                    <option value="SIM_TO_REAL_COMPARISON">SIM_TO_REAL_COMPARISON</option>
                    <option value="FORECAST_BACKTEST">FORECAST_BACKTEST</option>
                    <option value="WORKLOAD_REPLAY">WORKLOAD_REPLAY</option>
                    <option value="MODEL_CALIBRATION">MODEL_CALIBRATION</option>
                    <option value="ACTION_DURATION_BENCHMARK">ACTION_DURATION_BENCHMARK</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-mono text-obsidian-muted block mb-1">Research Question & Hypothesis:</label>
                <input
                  type="text"
                  value={expHypothesis}
                  onChange={(e) => setExpHypothesis(e.target.value)}
                  className="w-full bg-obsidian-card border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text"
                />
              </div>

              <button
                onClick={handleCreateExperiment}
                disabled={actionLoading}
                className="px-4 py-2 rounded-lg bg-obsidian-cyan/20 hover:bg-obsidian-cyan/30 border border-obsidian-cyan/40 text-obsidian-cyan text-xs font-bold transition-all disabled:opacity-50"
              >
                Dispatch Controlled Experiment Trial →
              </button>
            </div>

            {/* Experiment History List */}
            <div className="pt-4 border-t border-obsidian-border space-y-3">
              <h4 className="text-xs font-mono uppercase text-obsidian-muted font-bold">Executed Experiments History</h4>
              <div className="divide-y divide-obsidian-border">
                {experiments.map((e) => (
                  <div key={e.id} className="py-3 flex flex-col md:flex-row justify-between items-start md:items-center gap-2 text-xs">
                    <div>
                      <span className="font-bold text-obsidian-text">{e.name}</span>
                      <span className="text-[11px] font-mono text-obsidian-muted block">{e.id} • {e.experiment_type}</span>
                      <p className="text-[11px] text-obsidian-muted mt-0.5">Hypothesis: {e.hypothesis}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                        {e.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB F: EVIDENCE-GATED PLANNING */}
      {activeTab === 'gated_planning' && (
        <div className="space-y-6">
          {/* Multi-indicator Fidelity Scorecard */}
          {fidelityData && (
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-obsidian-text">Digital Twin Fidelity Assessment Envelope</h3>
                  <span className="text-xs font-mono text-obsidian-muted">Target: {fidelityData.device_id}</span>
                </div>
                <span className={`px-2.5 py-1 rounded text-xs font-mono font-bold border ${getFidelityBadgeClass(fidelityData.assessment_status)}`}>
                  {fidelityData.assessment_status} ({fidelityData.overall_fidelity_score}/100)
                </span>
              </div>

              {/* Multi-Indicators Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 pt-2">
                <div className="p-3 rounded-lg bg-obsidian-panel border border-obsidian-border">
                  <span className="text-[10px] font-mono text-obsidian-muted block">Prediction Fidelity</span>
                  <span className="text-base font-bold text-emerald-400">{fidelityData.prediction_fidelity_score}%</span>
                </div>
                <div className="p-3 rounded-lg bg-obsidian-panel border border-obsidian-border">
                  <span className="text-[10px] font-mono text-obsidian-muted block">Workload Coverage</span>
                  <span className="text-base font-bold text-obsidian-cyan">{fidelityData.workload_coverage_score}%</span>
                </div>
                <div className="p-3 rounded-lg bg-obsidian-panel border border-obsidian-border">
                  <span className="text-[10px] font-mono text-obsidian-muted block">Data Quality</span>
                  <span className="text-base font-bold text-obsidian-purple">{fidelityData.data_quality_score}%</span>
                </div>
                <div className="p-3 rounded-lg bg-obsidian-panel border border-obsidian-border">
                  <span className="text-[10px] font-mono text-obsidian-muted block">Calibration Recency</span>
                  <span className="text-base font-bold text-amber-400">{fidelityData.calibration_recency_score}%</span>
                </div>
                <div className="p-3 rounded-lg bg-obsidian-panel border border-obsidian-border">
                  <span className="text-[10px] font-mono text-obsidian-muted block">Action Evidence</span>
                  <span className="text-base font-bold text-obsidian-text">{fidelityData.action_effect_evidence_score}%</span>
                </div>
              </div>

              {/* Scope Warnings */}
              {fidelityData.out_of_scope_warnings?.length > 0 && (
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300 space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <AlertTriangle size={14} />
                    Operating Conditions Outside Calibrated Envelope:
                  </div>
                  {fidelityData.out_of_scope_warnings.map((w: string, idx: number) => (
                    <div key={idx} className="ml-5 list-disc">• {w}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Evidence-Gated Interventions Table */}
          {gatedPlan && (
            <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-obsidian-text">Evidence-Gated Action Recommendations</h3>
                <span className="text-xs font-mono text-obsidian-muted">Sorted by Evidence Support & Safety Feasibility</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-obsidian-panel text-obsidian-muted font-mono uppercase text-[10px]">
                    <tr>
                      <th className="py-2.5 px-4">Action Type</th>
                      <th className="py-2.5 px-4">Gating Classification</th>
                      <th className="py-2.5 px-4">Evidence Grounding</th>
                      <th className="py-2.5 px-4">Operational Rationale</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-obsidian-border">
                    {gatedPlan.recommendations?.map((rec: any) => (
                      <tr key={rec.action_type} className="hover:bg-obsidian-panel/30">
                        <td className="py-3 px-4 font-mono font-bold text-obsidian-text">{rec.action_type}</td>
                        <td className="py-3 px-4 font-mono">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getVerdictBadgeClass(rec.gating_verdict)}`}>
                            {rec.gating_verdict}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-obsidian-cyan">
                          {rec.evidence_category} ({rec.sample_size} trials)
                        </td>
                        <td className="py-3 px-4 text-obsidian-muted">{rec.gating_rationale}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB G: CALIBRATION COVERAGE & VALUE-OF-EXPERIMENT */}
      {activeTab === 'voe_coverage' && (
        <div className="space-y-6">
          <div className="bg-obsidian-card border border-obsidian-border rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp size={16} className="text-obsidian-cyan" />
                <h3 className="text-sm font-bold text-obsidian-text">Value-of-Experiment (VOE) Priority Ranking</h3>
              </div>
              <span className="text-xs font-mono text-amber-400 font-bold">Ranks Experiments by Uncertainty Reduction</span>
            </div>
            <p className="text-xs text-obsidian-muted">
              Prioritizes follow-up measurements where simulation discrepancy is highest and operational stakes are critical.
            </p>

            <div className="space-y-4 pt-2">
              {voeGaps.map((gap) => (
                <div key={gap.id} className="p-4 rounded-xl bg-obsidian-panel border border-obsidian-border space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-obsidian-border pb-2">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-obsidian-cyan/20 border border-obsidian-cyan/40 text-obsidian-cyan flex items-center justify-center font-mono text-xs font-bold">
                        #{gap.voe_rank}
                      </span>
                      <span className="text-xs font-bold text-obsidian-text">{gap.candidate_experiment?.title}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-obsidian-coral/20 text-obsidian-coral border border-obsidian-coral/40 font-bold">
                        Impact: {gap.impact_level}
                      </span>
                      <span className="text-[11px] font-mono text-obsidian-muted">
                        Uncertainty: {(gap.uncertainty_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-obsidian-text">{gap.gap_description}</p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-obsidian-card/60 p-3 rounded-lg border border-obsidian-border">
                    <div>
                      <span className="text-obsidian-cyan font-mono text-[11px] block font-bold">Research Question:</span>
                      <p className="text-obsidian-muted">{gap.candidate_experiment?.research_question}</p>
                    </div>
                    <div>
                      <span className="text-emerald-400 font-mono text-[11px] block font-bold">Learning Objective:</span>
                      <p className="text-obsidian-muted">{gap.candidate_experiment?.learning_objective}</p>
                    </div>
                  </div>

                  <div className="text-[11px] font-mono text-obsidian-muted flex justify-between">
                    <span>Safety: {gap.candidate_experiment?.safety_constraints}</span>
                    <span className="text-amber-400">Regime: {gap.workload_regime}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
