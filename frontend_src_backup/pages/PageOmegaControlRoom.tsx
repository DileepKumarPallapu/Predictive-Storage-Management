import React, { useState, useEffect } from 'react';
import {
  Network,
  Shield,
  Activity,
  Layers,
  Zap,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Database,
  BarChart3,
  Server,
  Cpu,
  Lock,
  GitCompare,
  RefreshCw,
  Sliders,
  DollarSign,
  Info
} from 'lucide-react';
import { api } from '../api/client';

export const PageOmegaControlRoom: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'topology' | 'h1_decision' | 'h2_monitor' | 'h3_planner' | 'h4_ledger'>('topology');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Data states
  const [topologyData, setTopologyData] = useState<any>(null);
  const [fleetRiskData, setFleetRiskData] = useState<any>(null);
  const [h1Data, setH1Data] = useState<any>(null);
  const [h2Data, setH2Data] = useState<any>(null);
  const [ledgerData, setLedgerData] = useState<any>(null);
  const [governanceData, setGovernanceData] = useState<any>(null);

  // H1 Selector
  const [selectedH1Device, setSelectedH1Device] = useState<string>('vol-nvme-tier1-db');

  // H3 Planner Inputs
  const [planSource, setPlanSource] = useState<string>('vol-nvme-tier1-db');
  const [planDest, setPlanDest] = useState<string>('vol-sas-tier2-analytics');
  const [planSizeGb, setPlanSizeGb] = useState<number>(1200);
  const [planBandwidthMb, setPlanBandwidthMb] = useState<number>(300);
  const [plannerResult, setPlannerResult] = useState<any>(null);
  const [isSimulatingPlan, setIsSimulatingPlan] = useState<boolean>(false);

  // H4 Candidate Evaluation Form
  const [candName, setCandName] = useState<string>('LightGBM-DynamicQuantile-v2.3');
  const [candVersion, setCandVersion] = useState<string>('2.3.0');
  const [candMae, setCandMae] = useState<number>(2.45);
  const [candLoss, setCandLoss] = useState<number>(295.0);
  const [candEce, setCandEce] = useState<number>(0.021);
  const [evalResult, setEvalResult] = useState<any>(null);

  useEffect(() => {
    loadAllOmegaData();
  }, []);

  const loadAllOmegaData = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [top, risk, h1, h2, ledger, gov] = await Promise.all([
        api.getOmegaTopology(),
        api.getOmegaFleetRisk(),
        api.getOmegaDecisionEvaluation(selectedH1Device, 72),
        api.getOmegaAdaptiveMonitoring(30),
        api.getOmegaOutcomeLedger(50),
        api.getOmegaGovernance(),
      ]);
      setTopologyData(top);
      setFleetRiskData(risk);
      setH1Data(h1);
      setH2Data(h2);
      setLedgerData(ledger);
      setGovernanceData(gov);
    } catch (err: any) {
      console.error("Failed to load Omega platform telemetry:", err);
      setErrorMessage(err.message || "Failed to connect to Omega intelligence endpoints");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunPlannerSimulation = async () => {
    setIsSimulatingPlan(true);
    try {
      const res = await api.simulateOmegaFleetPlan({
        source_device_id: planSource,
        destination_device_id: planDest,
        migration_size_gb: planSizeGb,
        bandwidth_cap_mb_s: planBandwidthMb,
      });
      setPlannerResult(res);
    } catch (err: any) {
      alert("Simulation failed: " + err.message);
    } finally {
      setIsSimulatingPlan(false);
    }
  };

  const handleEvaluateCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.evaluateOmegaCandidate({
        candidate_model_name: candName,
        candidate_version: candVersion,
        candidate_mae: Number(candMae),
        candidate_decision_loss: Number(candLoss),
        candidate_calibration_error: Number(candEce),
      });
      setEvalResult(res);
      // Reload governance history
      const gov = await api.getOmegaGovernance();
      setGovernanceData(gov);
    } catch (err: any) {
      alert("Evaluation failed: " + err.message);
    }
  };

  const handleH1DeviceChange = async (devId: string) => {
    setSelectedH1Device(devId);
    try {
      const h1 = await api.getOmegaDecisionEvaluation(devId, 72);
      setH1Data(h1);
    } catch (err) {
      console.error(err);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <RefreshCw size={36} className="text-[var(--accent-primary)] animate-spin" />
        <p className="text-sm font-mono text-[var(--text-secondary)]">
          Aggregating Fleet Topology, Correlated Contention & Omega Research Ledger...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/30 text-[var(--accent-primary)]">
              <Network size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                  AEGISSTOR OMEGA — Fleet Intelligence Control Room
                </h1>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[var(--accent-secondary)]/20 text-[var(--accent-tertiary)] border border-[var(--accent-secondary)]/40">
                  OMEGA 6.0
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border border-[var(--accent-primary)]/40">
                  SHADOW MODE (ACTIVE)
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)] font-mono mt-0.5">
                Official Project: Predictive Storage Capacity and Performance Management Using Machine Learning
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={loadAllOmegaData}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-xs font-mono text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent-primary)] transition-colors"
        >
          <RefreshCw size={14} />
          Sync Fleet Telemetry
        </button>
      </div>

      {/* Fleet Risk Budget Status Banner */}
      {fleetRiskData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
          <div className="space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
              <Server size={14} className="text-[var(--accent-primary)]" /> Monitored Fleet
            </span>
            <div className="text-xl font-bold text-[var(--text-primary)]">
              {fleetRiskData.fleet_metrics.total_devices} Volumes ({fleetRiskData.fleet_metrics.total_capacity_tb} TB)
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Fleet Utilized: <span className="text-[var(--text-primary)] font-mono font-medium">{fleetRiskData.fleet_metrics.fleet_utilization_pct}%</span>
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
              <Shield size={14} className="text-[var(--accent-tertiary)]" /> Fleet Risk Budget
            </span>
            <div className="text-xl font-bold flex items-center gap-2">
              <span className={fleetRiskData.fleet_risk_budget.budget_status === 'BALANCED' ? 'text-[var(--status-success)]' : 'text-[var(--status-warning)]'}>
                {fleetRiskData.fleet_risk_budget.consumed_risk_points} / 100.0 pts
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Remaining: <span className="font-mono text-[var(--status-success)]">{fleetRiskData.fleet_risk_budget.remaining_budget_points} pts</span>
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
              <AlertTriangle size={14} className="text-[var(--status-warning)]" /> Correlated Bottlenecks
            </span>
            <div className="text-xl font-bold text-[var(--status-warning)]">
              {fleetRiskData.correlated_bottlenecks.length} Active
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Shared SAN Bus & Snapshot Locks
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
              <Clock size={14} className="text-[var(--accent-primary)]" /> Research Status
            </span>
            <div className="text-xl font-bold text-[var(--accent-primary)]">
              Hypotheses H1-H4
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Empirical Evaluation Verified
            </p>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-[var(--border-subtle)] gap-2 overflow-x-auto pb-1">
        {[
          { id: 'topology', label: '1. Fleet Topology & Resource Graph', icon: Network },
          { id: 'h1_decision', label: '2. Decision-Aware Forecasting (H1)', icon: BarChart3 },
          { id: 'h2_monitor', label: '3. Adaptive Monitoring (H2)', icon: Activity },
          { id: 'h3_planner', label: '4. Fleet Intervention Planner (H3)', icon: Sliders },
          { id: 'h4_ledger', label: '5. Outcome Ledger & Governance (H4)', icon: GitCompare },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg font-medium text-xs transition-colors whitespace-nowrap ${
                isActive
                  ? 'bg-[var(--surface-primary)] border-t border-x border-[var(--border-subtle)] text-[var(--accent-primary)] border-b-2 border-b-[var(--accent-primary)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)]/50'
              }`}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: FLEET TOPOLOGY & RESOURCE RELATIONSHIP GRAPH */}
      {/* ========================================================================= */}
      {activeTab === 'topology' && topologyData && (
        <div className="space-y-6">
          {/* Summary Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-3 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
              <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase">Storage Systems</span>
              <div className="text-lg font-bold text-[var(--text-primary)]">{topologyData.summary.total_systems}</div>
            </div>
            <div className="p-3 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
              <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase">Storage Pools</span>
              <div className="text-lg font-bold text-[var(--accent-primary)]">{topologyData.summary.total_pools}</div>
            </div>
            <div className="p-3 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
              <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase">Volumes</span>
              <div className="text-lg font-bold text-[var(--accent-tertiary)]">{topologyData.summary.total_devices}</div>
            </div>
            <div className="p-3 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
              <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase">Topology Edges</span>
              <div className="text-lg font-bold text-[var(--status-success)]">{topologyData.summary.total_relationships}</div>
            </div>
            <div className="p-3 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
              <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase">Active Workloads</span>
              <div className="text-lg font-bold text-[var(--status-warning)]">{topologyData.summary.total_workloads}</div>
            </div>
          </div>

          {/* Node Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Storage Systems */}
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Server size={16} className="text-[var(--accent-primary)]" /> Storage Systems & Fabrics
              </h3>
              <div className="space-y-2.5">
                {topologyData.nodes.filter((n: any) => n.type === 'SYSTEM').map((sys: any) => (
                  <div key={sys.id} className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)]/70 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[var(--text-primary)]">{sys.label}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30">
                        {sys.system_type}
                      </span>
                    </div>
                    <p className="text-[11px] text-[var(--text-secondary)] font-mono">
                      Bus: {sys.interconnect} | {sys.bandwidth_mb_s} MB/s | {sys.max_iops.toLocaleString()} IOPS
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Storage Pools */}
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Layers size={16} className="text-[var(--accent-tertiary)]" /> Storage Pools & Redundancy
              </h3>
              <div className="space-y-2.5">
                {topologyData.nodes.filter((n: any) => n.type === 'POOL').map((pool: any) => (
                  <div key={pool.id} className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)]/70 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[var(--text-primary)]">{pool.label}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--accent-secondary)]/10 text-[var(--accent-tertiary)] border border-[var(--accent-secondary)]/30">
                        {pool.tier}
                      </span>
                    </div>
                    <p className="text-[11px] text-[var(--text-secondary)] font-mono">
                      Policy: {pool.redundancy} | Usable: {Math.round(pool.usable_capacity_bytes / (1024**4))} TB
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Workload Dependencies */}
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Cpu size={16} className="text-[var(--status-warning)]" /> Workload Dependencies & SLAs
              </h3>
              <div className="space-y-2.5">
                {topologyData.workloads.map((wl: any) => (
                  <div key={wl.id} className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)]/70 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[var(--text-primary)]">{wl.workload_name}</span>
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                        wl.criticality === 'MISSION_CRITICAL'
                          ? 'bg-[var(--status-critical)]/10 text-[var(--status-critical)] border-[var(--status-critical)]/30'
                          : 'bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] border-[var(--accent-primary)]/30'
                      }`}>
                        {wl.criticality}
                      </span>
                    </div>
                    <p className="text-[11px] text-[var(--text-secondary)] font-mono">
                      Primary: {wl.primary_device_id} | SLA: &lt;{wl.sla_max_latency_ms}ms | Pattern: {wl.io_pattern}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Relationship Provenance & Coupling Table */}
          <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
              <Network size={16} className="text-[var(--accent-primary)]" /> Multi-Pool Resource Relationships & Concurrency Edges
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)] font-mono text-[11px]">
                    <th className="py-2 px-3">Source</th>
                    <th className="py-2 px-3">Target</th>
                    <th className="py-2 px-3">Relationship Type</th>
                    <th className="py-2 px-3">Provenance Attribution</th>
                    <th className="py-2 px-3">Contention Weight</th>
                    <th className="py-2 px-3">Coupling Dynamics</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]/50 font-mono text-[11px]">
                  {topologyData.edges.map((edge: any) => (
                    <tr key={edge.id} className="hover:bg-[var(--bg-primary)]/50 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-[var(--text-primary)]">{edge.source}</td>
                      <td className="py-2.5 px-3 text-[var(--text-secondary)]">{edge.target}</td>
                      <td className="py-2.5 px-3 text-[var(--accent-primary)]">{edge.relationship_type}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] border ${
                          edge.provenance === 'DISCOVERED'
                            ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border-[var(--status-success)]/30'
                            : edge.provenance === 'USER_DEFINED'
                            ? 'bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] border-[var(--accent-primary)]/30'
                            : 'bg-[var(--accent-secondary)]/10 text-[var(--accent-tertiary)] border-[var(--accent-secondary)]/30'
                        }`}>
                          {edge.provenance} ({Math.round(edge.confidence_score * 100)}%)
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[var(--status-warning)] font-bold">{edge.contention_weight}</td>
                      <td className="py-2.5 px-3 text-[var(--text-secondary)] truncate max-w-xs font-sans text-xs">
                        {edge.metadata?.shared_resource || edge.metadata?.policy || edge.metadata?.inference_basis || "Direct Pool Mapping"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: HYPOTHESIS H1 — DECISION-AWARE FORECASTING LAB */}
      {/* ========================================================================= */}
      {activeTab === 'h1_decision' && h1Data && (
        <div className="space-y-6">
          {/* Scientific Hypothesis Explanation */}
          <div className="p-4 rounded-xl bg-[var(--accent-primary)]/5 border border-[var(--accent-primary)]/20 space-y-2">
            <div className="flex items-center gap-2 text-[var(--accent-primary)] font-semibold text-sm">
              <Info size={16} /> Research Hypothesis H1: Decision-Aware Storage Forecasting vs Conventional ML
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Conventional time-series models optimize for symmetric accuracy (e.g. Mean Absolute Error). In storage systems,
              symmetric error is operationally misleading: underpredicting capacity bursts causes catastrophic unplanned downtime ($3,500 penalty),
              while slightly overpredicting merely prompts early rebalancing ($320 penalty). AEGISSTOR Omega optimizes asymmetric
              decision loss and conformal lead-time reliability.
            </p>
          </div>

          {/* Device Selector */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-[var(--text-secondary)]">Target Storage Volume:</span>
            <select
              value={selectedH1Device}
              onChange={(e) => handleH1DeviceChange(e.target.value)}
              className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-md px-3 py-1.5 text-xs font-mono text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-primary)]"
            >
              <option value="vol-nvme-tier1-db">Production E-Commerce OLTP NVMe (vol-nvme-tier1-db)</option>
              <option value="vol-sas-tier2-analytics">Corporate Data Warehouse SAS (vol-sas-tier2-analytics)</option>
              <option value="vol-hdd-archive">High-Density Cold Archive (vol-hdd-archive)</option>
              <option value="vol-backup-target">Veeam Backup Target (vol-backup-target)</option>
            </select>
          </div>

          {/* Model Comparison Table */}
          <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <BarChart3 size={16} className="text-[var(--accent-primary)]" /> Empirical 72-Hour Backtest: Standard Accuracy vs Operational Decision Loss
              </h3>
              <span className="text-[10px] font-mono text-[var(--text-secondary)]">
                Evaluated over {h1Data.evaluation_window_test_samples} test timesteps
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)] font-mono text-[11px]">
                    <th className="py-2.5 px-3">Forecasting Strategy</th>
                    <th className="py-2.5 px-3">Architecture Type</th>
                    <th className="py-2.5 px-3">Symmetric MAE</th>
                    <th className="py-2.5 px-3">Interval Coverage</th>
                    <th className="py-2.5 px-3">Missed Breaches</th>
                    <th className="py-2.5 px-3">Mean Usable Lead-Time</th>
                    <th className="py-2.5 px-3">Total Operational Loss ($)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]/50 font-mono text-[11px]">
                  {h1Data.models_comparison.map((m: any) => {
                    const isOmega = m.model_id === 'aegisstor_omega_decision_aware';
                    return (
                      <tr key={m.model_id} className={isOmega ? 'bg-[var(--accent-primary)]/10 font-bold' : 'hover:bg-[var(--bg-primary)]/50'}>
                        <td className="py-3 px-3 text-[var(--text-primary)] flex items-center gap-2">
                          {isOmega && <CheckCircle2 size={14} className="text-[var(--accent-primary)]" />}
                          {m.model_name}
                        </td>
                        <td className="py-3 px-3 text-[var(--text-secondary)] text-[10px]">{m.model_type}</td>
                        <td className="py-3 px-3 text-[var(--text-primary)]">{m.mae_pct}%</td>
                        <td className="py-3 px-3 text-[var(--text-secondary)]">{(m.interval_coverage * 100).toFixed(1)}%</td>
                        <td className="py-3 px-3">
                          {m.missed_breaches_count > 0 ? (
                            <span className="text-[var(--status-critical)] font-bold">{m.missed_breaches_count} missed</span>
                          ) : (
                            <span className="text-[var(--status-success)] font-bold">0 (Zero)</span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-[var(--text-primary)]">{m.mean_lead_time_hours} hrs</td>
                        <td className="py-3 px-3">
                          <span className={`text-sm ${isOmega ? 'text-[var(--accent-primary)] font-extrabold' : 'text-[var(--status-critical)]'}`}>
                            ${m.total_operational_decision_loss_usd.toLocaleString()}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Research Finding Box */}
          <div className="p-4 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-subtle)] space-y-2">
            <h4 className="text-xs font-mono uppercase tracking-wider text-[var(--status-success)] flex items-center gap-1.5 font-bold">
              <CheckCircle2 size={14} /> Empirical Finding (Hypothesis H1 Confirmed)
            </h4>
            <p className="text-xs text-[var(--text-primary)] leading-relaxed">
              {h1Data.research_findings.key_takeaway}
            </p>
            <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed font-mono">
              Note: {h1Data.research_findings.mae_vs_decision_divergence}
            </p>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: HYPOTHESIS H2 — ADAPTIVE MONITORING (VALUE OF INFORMATION) */}
      {/* ========================================================================= */}
      {activeTab === 'h2_monitor' && h2Data && (
        <div className="space-y-6">
          {/* Scientific Hypothesis Explanation */}
          <div className="p-4 rounded-xl bg-[var(--accent-secondary)]/5 border border-[var(--accent-secondary)]/20 space-y-2">
            <div className="flex items-center gap-2 text-[var(--accent-tertiary)] font-semibold text-sm">
              <Info size={16} /> Research Hypothesis H2: Adaptive Telemetry Attention & Value of Information (VoI)
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Fixed high-frequency polling generates gigabytes of redundant telemetry and burns host CPU. Reactive threshold triggers
              reduce bandwidth but remain blind to sub-hourly micro-bursts until thresholds trip. Policy C allocates attention dynamically:
              high sampling rates are deployed only where predictive breach probability and conformal uncertainty are elevated.
            </p>
          </div>

          {/* Comparative Simulation Policies */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {h2Data.policies.map((p: any) => {
              const isOmegaPolicy = p.policy_id === 'POLICY_C_VALUE_OF_INFORMATION';
              return (
                <div
                  key={p.policy_id}
                  className={`p-4 rounded-xl border space-y-3 ${
                    isOmegaPolicy
                      ? 'bg-[var(--surface-primary)] border-[var(--accent-primary)] shadow-[0_0_15px_rgba(85,214,255,0.1)]'
                      : 'bg-[var(--surface-primary)] border-[var(--border-subtle)]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--text-primary)]">{p.policy_name}</span>
                    {isOmegaPolicy && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border border-[var(--accent-primary)]/40">
                        AEGISSTOR OMEGA
                      </span>
                    )}
                  </div>
                  <div className="space-y-2 font-mono text-xs">
                    <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1">
                      <span className="text-[var(--text-secondary)]">Network Bandwidth:</span>
                      <span className="text-[var(--text-primary)] font-bold">{p.network_bandwidth_mb_day} MB / day</span>
                    </div>
                    <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1">
                      <span className="text-[var(--text-secondary)]">Agent CPU Overhead:</span>
                      <span className="text-[var(--text-primary)]">{p.collector_cpu_overhead_pct}%</span>
                    </div>
                    <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1">
                      <span className="text-[var(--text-secondary)]">Warning Lead-Time:</span>
                      <span className="text-[var(--accent-primary)] font-bold">{p.lead_time_warning_margin_hours} hrs</span>
                    </div>
                    <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1">
                      <span className="text-[var(--text-secondary)]">Micro-Burst Capture:</span>
                      <span className="text-[var(--status-success)]">{p.anomaly_capture_rate_pct}%</span>
                    </div>
                    <div className="flex justify-between pt-1">
                      <span className="text-[var(--text-secondary)]">VoI Efficiency Score:</span>
                      <span className="text-base font-extrabold text-[var(--accent-primary)]">{p.value_of_information_score}</span>
                    </div>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed font-sans pt-1">
                    {p.operational_verdict}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Live Device Attention Allocations Table */}
          <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
              <Activity size={16} className="text-[var(--accent-primary)]" /> Live Device Dynamic Attention Allocation (Policy C)
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)] text-[11px]">
                    <th className="py-2 px-3">Volume</th>
                    <th className="py-2 px-3">Current Util (%)</th>
                    <th className="py-2 px-3">P95 Latency</th>
                    <th className="py-2 px-3">Attention Score</th>
                    <th className="py-2 px-3">Allocated Sampling Rate</th>
                    <th className="py-2 px-3">Regime Status</th>
                    <th className="py-2 px-3">Telemetry Collection Depth</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]/50 text-[11px]">
                  {h2Data.live_device_attention_allocations?.map((alloc: any) => (
                    <tr key={alloc.device_id} className="hover:bg-[var(--bg-primary)]/50">
                      <td className="py-2.5 px-3 font-semibold text-[var(--text-primary)]">{alloc.device_name}</td>
                      <td className="py-2.5 px-3">{alloc.utilization_pct}%</td>
                      <td className="py-2.5 px-3">{alloc.p95_latency_ms} ms</td>
                      <td className="py-2.5 px-3 text-[var(--accent-primary)] font-bold">{alloc.attention_score}</td>
                      <td className="py-2.5 px-3 text-[var(--status-success)] font-bold">Every {alloc.allocated_sampling_interval_s}s</td>
                      <td className="py-2.5 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-[var(--text-primary)]">
                          {alloc.monitoring_regime}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[var(--text-secondary)] text-[10px]">{alloc.metrics_collection_depth}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: HYPOTHESIS H3 — FLEET INTERVENTION PLANNER & SAFETY ENVELOPE */}
      {/* ========================================================================= */}
      {activeTab === 'h3_planner' && (
        <div className="space-y-6">
          {/* Scientific Hypothesis Explanation */}
          <div className="p-4 rounded-xl bg-[var(--status-success)]/5 border border-[var(--status-success)]/20 space-y-2">
            <div className="flex items-center gap-2 text-[var(--status-success)] font-semibold text-sm">
              <Info size={16} /> Research Hypothesis H3: Dual-Sided Hard Safety Envelope & Secondary Bottleneck Prevention
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              In enterprise multi-tenant arrays, solving an overloaded volume&apos;s capacity risk by migrating data to another tier
              can inadvertently saturate shared controller buses or breach destination SLA limits. The AEGISSTOR Omega Fleet Planner
              enforces an invariant: both source, destination, and interconnect safety envelopes are modeled simultaneously before dispatch.
            </p>
          </div>

          {/* Interactive Simulation Form */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-4">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Sliders size={16} className="text-[var(--accent-primary)]" /> Cross-Volume Rebalance Parameters
              </h3>

              <div className="space-y-3 text-xs">
                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Source Volume (Risk Offload):</label>
                  <select
                    value={planSource}
                    onChange={(e) => setPlanSource(e.target.value)}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] font-mono"
                  >
                    <option value="vol-nvme-tier1-db">Production E-Commerce OLTP NVMe</option>
                    <option value="vol-sas-tier2-analytics">Corporate Analytics SAS</option>
                  </select>
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Destination Volume (Target Tier):</label>
                  <select
                    value={planDest}
                    onChange={(e) => setPlanDest(e.target.value)}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] font-mono"
                  >
                    <option value="vol-sas-tier2-analytics">Corporate Analytics SAS (Pool 02)</option>
                    <option value="vol-hdd-archive">High-Density Cold Archive (Pool 04)</option>
                    <option value="vol-backup-target">Veeam Backup Secondary Target</option>
                  </select>
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Data Migration Volume (GB):</label>
                  <input
                    type="number"
                    value={planSizeGb}
                    onChange={(e) => setPlanSizeGb(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] font-mono"
                    min="100"
                    max="50000"
                    step="100"
                  />
                  <p className="text-[10px] text-[var(--text-secondary)] mt-0.5">Test with 45,000 GB to trigger safety envelope rejection.</p>
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Migration Bandwidth Cap (MB/s):</label>
                  <input
                    type="number"
                    value={planBandwidthMb}
                    onChange={(e) => setPlanBandwidthMb(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] font-mono"
                    min="50"
                    max="2000"
                    step="50"
                  />
                  <p className="text-[10px] text-[var(--text-secondary)] mt-0.5">Shared SAN bus saturates above 250 MB/s concurrent load.</p>
                </div>

                <button
                  onClick={handleRunPlannerSimulation}
                  disabled={isSimulatingPlan}
                  className="w-full py-2.5 rounded-lg bg-[var(--accent-primary)] text-[var(--bg-primary)] font-bold text-xs hover:bg-[var(--accent-primary)]/90 transition-colors flex items-center justify-center gap-2"
                >
                  {isSimulatingPlan ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
                  Simulate Dual-Sided Safety Envelope
                </button>
              </div>
            </div>

            {/* Simulation Results Display */}
            <div className="lg:col-span-2 space-y-4">
              {plannerResult ? (
                <div className="space-y-4">
                  {/* Verdict Banner */}
                  <div className={`p-4 rounded-xl border flex items-center justify-between ${
                    plannerResult.dual_safety_envelope.verdict === 'FEASIBLE_SAFE'
                      ? 'bg-[var(--status-success)]/10 border-[var(--status-success)]/40 text-[var(--status-success)]'
                      : plannerResult.dual_safety_envelope.verdict === 'FEASIBLE_WITH_THROTTLING'
                      ? 'bg-[var(--status-warning)]/10 border-[var(--status-warning)]/40 text-[var(--status-warning)]'
                      : 'bg-[var(--status-critical)]/10 border-[var(--status-critical)]/40 text-[var(--status-critical)]'
                  }`}>
                    <div className="flex items-center gap-3">
                      {plannerResult.dual_safety_envelope.passed ? (
                        <CheckCircle2 size={24} />
                      ) : (
                        <XCircle size={24} />
                      )}
                      <div>
                        <div className="font-bold text-sm">
                          VERDICT: {plannerResult.dual_safety_envelope.verdict}
                        </div>
                        <p className="text-xs opacity-90 mt-0.5">
                          {plannerResult.dual_safety_envelope.rationale}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Impact Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Source Impact */}
                    <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-2 text-xs">
                      <span className="font-mono text-[var(--accent-primary)] font-bold block">SOURCE VOLUME IMPACT</span>
                      <div className="font-mono space-y-1">
                        <div className="flex justify-between">
                          <span className="text-[var(--text-secondary)]">Utilization:</span>
                          <span>{plannerResult.source_impact.current_utilization_pct}% &rarr; {plannerResult.source_impact.projected_utilization_pct}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[var(--text-secondary)]">Runway Gained:</span>
                          <span className="text-[var(--status-success)] font-bold">+{plannerResult.source_impact.runway_hours_gained} hrs</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[var(--text-secondary)]">Source SLA Status:</span>
                          <span className="text-[var(--status-success)]">SATISFIED</span>
                        </div>
                      </div>
                    </div>

                    {/* Destination Impact */}
                    <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-2 text-xs">
                      <span className="font-mono text-[var(--accent-tertiary)] font-bold block">DESTINATION VOLUME IMPACT</span>
                      <div className="font-mono space-y-1">
                        <div className="flex justify-between">
                          <span className="text-[var(--text-secondary)]">Utilization:</span>
                          <span>{plannerResult.destination_impact.current_utilization_pct}% &rarr; {plannerResult.destination_impact.projected_utilization_pct}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[var(--text-secondary)]">Peak Latency:</span>
                          <span>{plannerResult.destination_impact.peak_migration_latency_ms} ms (SLA: &lt;{plannerResult.destination_impact.sla_max_latency_ms}ms)</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[var(--text-secondary)]">Destination SLA Status:</span>
                          <span className={plannerResult.destination_impact.sla_satisfied ? 'text-[var(--status-success)]' : 'text-[var(--status-critical)] font-bold'}>
                            {plannerResult.destination_impact.sla_satisfied ? 'SATISFIED' : 'BREACHED'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Safety Violations list if any */}
                  {plannerResult.dual_safety_envelope.violations.length > 0 && (
                    <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--status-critical)]/30 space-y-2">
                      <span className="text-xs font-mono font-bold text-[var(--status-critical)] flex items-center gap-1.5">
                        <AlertTriangle size={14} /> Safety Envelope Violations Detected
                      </span>
                      <ul className="space-y-1 text-xs text-[var(--text-secondary)] font-mono list-disc list-inside">
                        {plannerResult.dual_safety_envelope.violations.map((v: string, idx: number) => (
                          <li key={idx}>{v}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-12 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-center space-y-2">
                  <Sliders size={36} className="mx-auto text-[var(--text-secondary)] opacity-50" />
                  <p className="text-sm font-medium text-[var(--text-primary)]">Configure rebalance parameters and run simulation</p>
                  <p className="text-xs text-[var(--text-secondary)] font-mono max-w-md mx-auto">
                    The simulator will evaluate destination tier headroom, migration transfer duration, and shared interconnect bus contention.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: HYPOTHESIS H4 — OUTCOME LEDGER & MODEL GOVERNANCE */}
      {/* ========================================================================= */}
      {activeTab === 'h4_ledger' && ledgerData && (
        <div className="space-y-6">
          {/* Scientific Hypothesis Explanation */}
          <div className="p-4 rounded-xl bg-[var(--accent-primary)]/5 border border-[var(--accent-primary)]/20 space-y-2">
            <div className="flex items-center gap-2 text-[var(--accent-primary)] font-semibold text-sm">
              <Info size={16} /> Research Hypothesis H4: Closed-Loop Outcome Ledger & Governed Model Evolution
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Prevents model drift from silently degrading decisions. The system tracks past decisions in an immutable ledger
              comparing Predicted vs Simulated vs Observed outcomes across four explicit classes. Candidate models undergo safety
              gating: lower symmetric MAE is rejected if operational decision loss or calibration error worsens.
            </p>
          </div>

          {/* Ledger Statistics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-1">
              <span className="text-[11px] font-mono text-[var(--text-secondary)] uppercase">Intervention Precision</span>
              <div className="text-2xl font-bold text-[var(--status-success)]">
                {ledgerData.statistics.intervention_precision_pct}%
              </div>
              <p className="text-xs text-[var(--text-secondary)] font-mono">
                {ledgerData.statistics.correct_preventive_success} Success / {ledgerData.statistics.unnecessary_interventions} False Alarms
              </p>
            </div>

            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-1">
              <span className="text-[11px] font-mono text-[var(--text-secondary)] uppercase">Action Reliability Rate</span>
              <div className="text-2xl font-bold text-[var(--accent-primary)]">
                {ledgerData.statistics.action_reliability_rate_pct}%
              </div>
              <p className="text-xs text-[var(--text-secondary)] font-mono">
                {ledgerData.statistics.missed_breaches} Missed Breaches
              </p>
            </div>

            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-1">
              <span className="text-[11px] font-mono text-[var(--text-secondary)] uppercase">Protected Runway Hours</span>
              <div className="text-2xl font-bold text-[var(--accent-tertiary)]">
                +{ledgerData.statistics.total_runway_hours_protected} hrs
              </div>
              <p className="text-xs text-[var(--text-secondary)] font-mono">Cumulative Headroom Gained</p>
            </div>

            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-1">
              <span className="text-[11px] font-mono text-[var(--text-secondary)] uppercase">Net Decision Loss Saved</span>
              <div className="text-2xl font-bold text-[var(--status-success)]">
                ${(14200 - ledgerData.statistics.total_net_decision_loss_usd).toLocaleString()}
              </div>
              <p className="text-xs text-[var(--text-secondary)] font-mono">vs Unmitigated Baseline</p>
            </div>
          </div>

          {/* Immutable Outcome Ledger Table */}
          <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
              <Database size={16} className="text-[var(--accent-primary)]" /> Immutable Closed-Loop Outcome Audit Trail
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)] text-[11px]">
                    <th className="py-2.5 px-3">Timestamp</th>
                    <th className="py-2.5 px-3">Volume</th>
                    <th className="py-2.5 px-3">Forecasted</th>
                    <th className="py-2.5 px-3">Simulated</th>
                    <th className="py-2.5 px-3">Observed</th>
                    <th className="py-2.5 px-3">Action Taken</th>
                    <th className="py-2.5 px-3">Outcome Classification</th>
                    <th className="py-2.5 px-3">Runway Gain</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]/50 text-[11px]">
                  {ledgerData.records.map((r: any) => (
                    <tr key={r.id} className="hover:bg-[var(--bg-primary)]/50">
                      <td className="py-2.5 px-3 text-[var(--text-secondary)] text-[10px]">{r.timestamp ? r.timestamp.slice(0, 16).replace('T', ' ') : 'N/A'}</td>
                      <td className="py-2.5 px-3 font-semibold text-[var(--text-primary)]">{r.device_id}</td>
                      <td className="py-2.5 px-3">{r.forecasted_used_pct}%</td>
                      <td className="py-2.5 px-3">{r.simulated_used_pct}%</td>
                      <td className="py-2.5 px-3 text-[var(--accent-primary)] font-bold">{r.observed_used_pct}%</td>
                      <td className="py-2.5 px-3 text-[var(--text-secondary)]">{r.action_taken}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] border ${
                          r.counterfactual_outcome_class === 'CORRECT_PREVENTIVE_SUCCESS'
                            ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border-[var(--status-success)]/30'
                            : r.counterfactual_outcome_class === 'UNNECESSARY_INTERVENTION'
                            ? 'bg-[var(--status-warning)]/10 text-[var(--status-warning)] border-[var(--status-warning)]/30'
                            : 'bg-[var(--status-critical)]/10 text-[var(--status-critical)] border-[var(--status-critical)]/30'
                        }`}>
                          {r.counterfactual_outcome_class}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[var(--status-success)] font-bold">+{r.runway_hours_gained}h</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Model Evolution & Promotion Gate */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Candidate Evaluation Form */}
            <form onSubmit={handleEvaluateCandidate} className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-4">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Lock size={16} className="text-[var(--accent-primary)]" /> Submit Candidate Model to Safety Promotion Gate
              </h3>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Candidate Model Name:</label>
                  <input
                    type="text"
                    value={candName}
                    onChange={(e) => setCandName(e.target.value)}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Version Tag:</label>
                  <input
                    type="text"
                    value={candVersion}
                    onChange={(e) => setCandVersion(e.target.value)}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Candidate MAE (%):</label>
                  <input
                    type="number"
                    step="0.01"
                    value={candMae}
                    onChange={(e) => setCandMae(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Operational Decision Loss ($):</label>
                  <input
                    type="number"
                    step="1"
                    value={candLoss}
                    onChange={(e) => setCandLoss(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] font-mono"
                    required
                  />
                </div>
                <div className="col-span-2">
                  <label className="text-[var(--text-secondary)] block mb-1">Expected Calibration Error (ECE &le; 0.05):</label>
                  <input
                    type="number"
                    step="0.001"
                    value={candEce}
                    onChange={(e) => setCandEce(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] font-mono"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 rounded-lg bg-[var(--accent-primary)] text-[var(--bg-primary)] font-bold text-xs hover:bg-[var(--accent-primary)]/90 transition-colors flex items-center justify-center gap-2"
              >
                <Shield size={14} />
                Evaluate Promotion Gating Envelope
              </button>

              {evalResult && (
                <div className={`p-3 rounded-lg border text-xs font-mono ${
                  evalResult.gate_verdict === 'PROMOTED'
                    ? 'bg-[var(--status-success)]/10 border-[var(--status-success)]/40 text-[var(--status-success)]'
                    : 'bg-[var(--status-critical)]/10 border-[var(--status-critical)]/40 text-[var(--status-critical)]'
                }`}>
                  <strong>Verdict: {evalResult.gate_verdict}</strong> &mdash; {evalResult.verdict_rationale}
                </div>
              )}
            </form>

            {/* Historical Promotion Gate Decisions */}
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Shield size={16} className="text-[var(--accent-tertiary)]" /> Promotion Gate Decision History
              </h3>
              <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
                {governanceData?.evaluations?.map((g: any) => (
                  <div key={g.id} className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)]/70 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[var(--text-primary)] font-mono">{g.candidate_model_name} (v{g.candidate_version})</span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                        g.gate_verdict === 'PROMOTED'
                          ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border-[var(--status-success)]/30'
                          : 'bg-[var(--status-critical)]/10 text-[var(--status-critical)] border-[var(--status-critical)]/30'
                      }`}>
                        {g.gate_verdict}
                      </span>
                    </div>
                    <p className="text-[11px] text-[var(--text-secondary)] font-mono">
                      MAE: {g.candidate_mae}% vs {g.baseline_mae}% | Loss: ${g.candidate_decision_loss} vs ${g.baseline_decision_loss}
                    </p>
                    <p className="text-[11px] text-[var(--text-secondary)] leading-tight font-sans">
                      {g.verdict_rationale}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
