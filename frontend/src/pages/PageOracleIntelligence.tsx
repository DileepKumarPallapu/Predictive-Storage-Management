import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Search,
  HardDrive,
  Cpu,
  Layers,
  Sliders,
  AlertTriangle,
  ShieldCheck,
  Activity,
  TrendingUp,
  FileText,
  Download,
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  ArrowRight,
  HelpCircle,
  Eye,
  Scale,
  RefreshCw,
  Plus,
  Compass,
  Zap,
  Filter,
  Flame,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react';
import {
  api,
  OracleWorkloadItem,
  OracleAttributionResponse,
  OracleCapacityForensicsResponse,
  OracleBottleneckResponse,
  OracleContentionGraphResponse,
  OracleHypothesisItem,
  OracleBottleneckCaseItem
} from '../api/client';

export const PageOracleIntelligence: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    'catalog' | 'capacity' | 'bottlenecks' | 'graph' | 'workspace'
  >('catalog');

  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('vol-nvme-tier1-db');
  const [windowHours, setWindowHours] = useState<number>(72);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Data states
  const [workloads, setWorkloads] = useState<OracleWorkloadItem[]>([]);
  const [attribution, setAttribution] = useState<OracleAttributionResponse | null>(null);
  const [capacityForensics, setCapacityForensics] = useState<OracleCapacityForensicsResponse | null>(null);
  const [bottlenecks, setBottlenecks] = useState<OracleBottleneckResponse | null>(null);
  const [contentionGraph, setContentionGraph] = useState<OracleContentionGraphResponse | null>(null);
  const [cases, setCases] = useState<OracleBottleneckCaseItem[]>([]);
  const [hypotheses, setHypotheses] = useState<OracleHypothesisItem[]>([]);
  const [selectedHypothesis, setSelectedHypothesis] = useState<OracleHypothesisItem | null>(null);

  // Counterfactual simulation state
  const [simWorkloadId, setSimWorkloadId] = useState<string>('wl-analytics-batch');
  const [simIntervention, setSimIntervention] = useState<string>('THROTTLE_INTENSITY');
  const [simThrottlePct, setSimThrottlePct] = useState<number>(35);
  const [simShiftHours, setSimShiftHours] = useState<number>(4);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<any | null>(null);

  // New Hypothesis modal state
  const [showHypModal, setShowHypModal] = useState<boolean>(false);
  const [hypForm, setHypForm] = useState({
    question: '',
    target_resource: 'vol-nvme-tier1-db',
    workload_id: 'wl-analytics-batch',
    supporting_evidence: '',
    contradicting_evidence: '',
    confounding_variables: '',
    proposed_evaluation_method: 'CONTROLLED_DIGITAL_TWIN_THROTTLING',
    reviewer: 'sre-lead@aegisstor.internal'
  });

  useEffect(() => {
    loadAllData();
  }, [selectedDeviceId, windowHours]);

  const loadAllData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [wlData, attrData, capData, btnkData, graphData, caseData, hypData] = await Promise.all([
        api.getOracleWorkloads(),
        api.getOracleAttribution(selectedDeviceId, windowHours),
        api.getOracleCapacityForensics(selectedDeviceId, windowHours === 72 ? 168 : windowHours),
        api.getOracleBottlenecks(selectedDeviceId, windowHours),
        api.getOracleContentionGraph(selectedDeviceId),
        api.getOracleCases(undefined, selectedDeviceId),
        api.getOracleHypotheses(selectedDeviceId),
      ]);

      setWorkloads(wlData);
      setAttribution(attrData);
      setCapacityForensics(capData);
      setBottlenecks(btnkData);
      setContentionGraph(graphData);
      setCases(caseData);
      setHypotheses(hypData);
      if (hypData.length > 0 && !selectedHypothesis) {
        setSelectedHypothesis(hypData[0]);
      }
    } catch (err: any) {
      console.error('Error loading Oracle intelligence data:', err);
      setErrorMsg('Failed to fetch Oracle telemetry intelligence: ' + (err.message || String(err)));
    } finally {
      setLoading(false);
    }
  };

  const handleRunCounterfactual = async () => {
    setSimulating(true);
    setErrorMsg(null);
    try {
      const params: any = {};
      if (simIntervention === 'THROTTLE_INTENSITY') {
        params.intensity_reduction_pct = simThrottlePct;
      } else if (simIntervention === 'RESCHEDULE_WINDOW') {
        params.shift_hours = simShiftHours;
      }

      const res = await api.runOracleCounterfactual({
        target_device_id: selectedDeviceId,
        workload_id: simWorkloadId,
        intervention_type: simIntervention,
        parameters: params,
        horizon_hours: 72,
      });

      setSimResult(res);
      setSuccessMsg(`Counterfactual simulation completed. Verified 0 physical host mutations.`);
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err: any) {
      setErrorMsg('Simulation error: ' + (err.message || String(err)));
    } finally {
      setSimulating(false);
    }
  };

  const handleCreateHypothesis = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        question: hypForm.question,
        target_resource: hypForm.target_resource,
        workload_id: hypForm.workload_id,
        supporting_evidence: hypForm.supporting_evidence.split('\n').filter(s => s.trim().length > 0),
        contradicting_evidence: hypForm.contradicting_evidence.split('\n').filter(s => s.trim().length > 0),
        confounding_variables: hypForm.confounding_variables.split('\n').filter(s => s.trim().length > 0),
        proposed_evaluation_method: hypForm.proposed_evaluation_method,
        reviewer: hypForm.reviewer,
      };

      const res = await api.createOracleHypothesis(payload);
      setShowHypModal(false);
      setSuccessMsg(`Hypothesis created (${res.id}). Automated contradictions flagged: ${res.automated_contradictions_flagged}`);
      await loadAllData();
      setTimeout(() => setSuccessMsg(null), 6000);
    } catch (err: any) {
      setErrorMsg('Failed to record hypothesis: ' + (err.message || String(err)));
    }
  };

  const handlePromoteHypothesis = async (hypId: string, nextStatus: string) => {
    try {
      await api.updateOracleHypothesisStatus(hypId, {
        new_status: nextStatus,
        rationale: `Promotion through scientific investigation workflow to ${nextStatus}`,
        reviewer: 'lead_sre@aegisstor.internal',
        conclusion: nextStatus === 'SUPPORTED_WITHIN_CONDITIONS' ? 'Supported by Digital Twin counterfactual ablation under peak workload conditions.' : undefined
      });
      setSuccessMsg(`Hypothesis updated to ${nextStatus}`);
      await loadAllData();
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setErrorMsg('Lifecycle transition rejected: ' + (err.message || String(err)));
      setTimeout(() => setErrorMsg(null), 6000);
    }
  };

  const handleDownloadReport = (format: 'markdown' | 'csv') => {
    const url = `http://localhost:8000/api/v1/oracle/report/${selectedDeviceId}/export?format=${format}`;
    window.open(url, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Ember Noir Header */}
      <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-[var(--accent-primary)]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-primary)] shadow-[0_0_10px_var(--accent-primary)]" />
              <span className="text-xs font-mono uppercase tracking-widest text-[var(--accent-primary)] font-bold">
                AEGISSTOR ORACLE — WORKLOAD FORENSICS & ATTRIBUTION LAB
              </span>
            </div>
            <h1 className="text-2xl font-black tracking-tight text-[var(--text-primary)] flex items-center gap-2">
              Workload Attribution, Bottleneck Forensics & Explainable Intelligence
            </h1>
            <p className="text-sm text-[var(--text-secondary)] mt-1 max-w-3xl">
              Strictly non-causal workload decomposition. Reconciles granular telemetry with storage pool aggregates,
              isolates queue contention hot-spots, surfaces unmeasured residual growth, and manages falsifiable hypotheses.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={selectedDeviceId}
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-xs text-[var(--text-primary)] font-mono focus:outline-none focus:border-[var(--accent-primary)]"
            >
              <option value="vol-nvme-tier1-db">Production E-Commerce OLTP NVMe</option>
              <option value="vol-sas-tier2-analytics">Corporate Data Warehouse SAS</option>
              <option value="vol-cold-tier3-backup">Regulatory Compliance Cold Vault</option>
              <option value="vol-edge-cache-01">Edge Ingestion Buffer Stream</option>
            </select>

            <select
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
              className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-xs text-[var(--text-primary)] font-mono focus:outline-none focus:border-[var(--accent-primary)]"
            >
              <option value={24}>Window: 24h</option>
              <option value={72}>Window: 72h</option>
              <option value={168}>Window: 7 Days</option>
              <option value={720}>Window: 30 Days</option>
            </select>

            <button
              onClick={() => loadAllData()}
              className="p-2 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
              title="Refresh Telemetry"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Epistemological Safeguard Bar */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-4 gap-3 pt-4 border-t border-[var(--border-subtle)]/60 text-xs">
          <div className="flex items-center gap-2">
            <Scale size={14} className="text-[var(--accent-primary)] shrink-0" />
            <span className="text-[var(--text-secondary)] font-mono">Causality Guard:</span>
            <span className="font-mono font-bold text-amber-400">CORRELATION ≠ CAUSATION</span>
          </div>
          <div className="flex items-center gap-2">
            <ShieldCheck size={14} className="text-emerald-400 shrink-0" />
            <span className="text-[var(--text-secondary)] font-mono">Attribution Coverage:</span>
            <span className="font-mono font-bold text-emerald-400">
              {attribution?.attribution_coverage_pct ?? '--'}% ({attribution?.reconciliation_status ?? 'SYNC'})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <HardDrive size={14} className="text-[var(--accent-tertiary)] shrink-0" />
            <span className="text-[var(--text-secondary)] font-mono">Unmeasured Residual:</span>
            <span className="font-mono font-bold text-[var(--accent-tertiary)]">
              {attribution?.residual_unattributed_gb ?? 0} GB
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-rose-400 shrink-0" />
            <span className="text-[var(--text-secondary)] font-mono">Contention Index:</span>
            <span className="font-mono font-bold text-rose-400">
              {bottlenecks?.contention_index ?? 0.0} ({bottlenecks?.contention_level ?? 'LOW'})
            </span>
          </div>
        </div>
      </div>

      {/* Alert Messages */}
      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-500/50 text-rose-200 px-4 py-3 rounded-lg text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle size={16} className="text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-white">✕</button>
        </div>
      )}

      {successMsg && (
        <div className="bg-emerald-950/40 border border-emerald-500/50 text-emerald-200 px-4 py-3 rounded-lg text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle size={16} className="text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-[var(--border-subtle)] gap-2">
        <button
          onClick={() => setActiveTab('catalog')}
          className={`flex items-center gap-2 px-4 py-3 text-xs font-mono uppercase tracking-wider font-bold border-b-2 transition-all ${
            activeTab === 'catalog'
              ? 'border-[var(--accent-primary)] text-[var(--accent-primary)] bg-[var(--surface-secondary)]/50'
              : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <Layers size={14} />
          1. Workload Catalog ({workloads.length})
        </button>

        <button
          onClick={() => setActiveTab('capacity')}
          className={`flex items-center gap-2 px-4 py-3 text-xs font-mono uppercase tracking-wider font-bold border-b-2 transition-all ${
            activeTab === 'capacity'
              ? 'border-[var(--accent-primary)] text-[var(--accent-primary)] bg-[var(--surface-secondary)]/50'
              : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <TrendingUp size={14} />
          2. Capacity Forensics & Residuals
        </button>

        <button
          onClick={() => setActiveTab('bottlenecks')}
          className={`flex items-center gap-2 px-4 py-3 text-xs font-mono uppercase tracking-wider font-bold border-b-2 transition-all ${
            activeTab === 'bottlenecks'
              ? 'border-[var(--accent-primary)] text-[var(--accent-primary)] bg-[var(--surface-secondary)]/50'
              : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <Zap size={14} />
          3. Bottlenecks & Contention Index
        </button>

        <button
          onClick={() => setActiveTab('graph')}
          className={`flex items-center gap-2 px-4 py-3 text-xs font-mono uppercase tracking-wider font-bold border-b-2 transition-all ${
            activeTab === 'graph'
              ? 'border-[var(--accent-primary)] text-[var(--accent-primary)] bg-[var(--surface-secondary)]/50'
              : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <Compass size={14} />
          4. Contention Topology Graph
        </button>

        <button
          onClick={() => setActiveTab('workspace')}
          className={`flex items-center gap-2 px-4 py-3 text-xs font-mono uppercase tracking-wider font-bold border-b-2 transition-all ${
            activeTab === 'workspace'
              ? 'border-[var(--accent-primary)] text-[var(--accent-primary)] bg-[var(--surface-secondary)]/50'
              : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          <Sparkles size={14} />
          5. Hypothesis Workspace & What-If
        </button>
      </div>

      {/* ======================================================== */}
      {/* TAB 1: WORKLOAD CATALOG & OVERVIEW */}
      {/* ======================================================== */}
      {activeTab === 'catalog' && (
        <div className="space-y-6">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-4">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Total Attributed Storage</span>
              <div className="text-2xl font-black text-[var(--text-primary)] mt-1">
                {attribution?.total_attributed_gb ? `${attribution.total_attributed_gb.toLocaleString()} GB` : '--'}
              </div>
              <div className="text-xs text-[var(--accent-tertiary)] mt-1 font-mono">
                Across {attribution?.workload_breakdown?.length ?? 0} active entities
              </div>
            </div>

            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-4">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Aggregate Physical Usage</span>
              <div className="text-2xl font-black text-[var(--text-primary)] mt-1">
                {attribution?.device_aggregate_used_gb ? `${attribution.device_aggregate_used_gb.toLocaleString()} GB` : '--'}
              </div>
              <div className="text-xs text-emerald-400 mt-1 font-mono">
                Device: {selectedDeviceId}
              </div>
            </div>

            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-4">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Attribution Coverage</span>
              <div className="text-2xl font-black text-emerald-400 mt-1">
                {attribution?.attribution_coverage_pct ?? '--'}%
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1 font-mono">
                Status: {attribution?.reconciliation_status ?? 'BALANCED'}
              </div>
            </div>

            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-4">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Unattributed Residual</span>
              <div className="text-2xl font-black text-[var(--accent-primary)] mt-1">
                {attribution?.residual_unattributed_gb ? `${attribution.residual_unattributed_gb.toLocaleString()} GB` : '0 GB'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1 font-mono">
                Journaling & untagged tenant writes
              </div>
            </div>
          </div>

          {/* Workload Inventory Table */}
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl overflow-hidden shadow-lg">
            <div className="p-4 border-b border-[var(--border-subtle)] flex justify-between items-center bg-[var(--surface-primary)]">
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)] font-mono uppercase">
                  Active Workloads & Granular Telemetry Probes
                </h3>
                <p className="text-xs text-[var(--text-secondary)]">
                  Live metrics collected via host agent daemon and synthetic storage probes.
                </p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/30 text-[var(--accent-primary)]">
                6 Discovered Workloads
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                  <tr>
                    <th className="p-3">Workload ID / Name</th>
                    <th className="p-3">Target Device</th>
                    <th className="p-3">Type & Priority</th>
                    <th className="p-3">Allocated GB</th>
                    <th className="p-3">R/W IOPS</th>
                    <th className="p-3">Throughput</th>
                    <th className="p-3">P95 Latency</th>
                    <th className="p-3">Attribution Probe</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {workloads.map((w) => {
                    const tel = w.latest_telemetry;
                    const isResidual = w.workload_type === 'RESIDUAL';
                    return (
                      <tr key={w.id} className="hover:bg-[var(--surface-primary)]/50 transition-colors">
                        <td className="p-3">
                          <div className="font-bold text-[var(--text-primary)]">{w.name}</div>
                          <div className="text-[10px] text-[var(--accent-primary)]">{w.id}</div>
                          <div className="text-[10px] text-[var(--text-secondary)] mt-0.5 line-clamp-1">{w.description}</div>
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-[10px]">
                            {w.target_device_id}
                          </span>
                        </td>
                        <td className="p-3">
                          <div className="flex flex-col gap-1">
                            <span className="font-semibold text-[var(--text-primary)]">{w.workload_type}</span>
                            <span className={`w-fit px-1.5 py-0.2 rounded text-[9px] font-bold ${
                              w.priority === 'P0_CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                              w.priority === 'P1_HIGH' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                              'bg-[var(--surface-elevated)] text-[var(--text-secondary)] border border-[var(--border-normal)]'
                            }`}>
                              {w.priority}
                            </span>
                          </div>
                        </td>
                        <td className="p-3 font-bold text-[var(--text-primary)]">
                          {tel?.allocated_gb ? `${tel.allocated_gb.toLocaleString()} GB` : '--'}
                        </td>
                        <td className="p-3">
                          <span className="text-emerald-400">{tel?.read_iops ?? 0}</span> / <span className="text-[var(--accent-primary)]">{tel?.write_iops ?? 0}</span>
                        </td>
                        <td className="p-3 text-[var(--text-primary)]">
                          {tel?.throughput_mb_s ? `${tel.throughput_mb_s} MB/s` : '--'}
                        </td>
                        <td className="p-3">
                          <span className={tel && tel.latency_p95_ms > w.sla_max_latency_ms ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                            {tel?.latency_p95_ms ? `${tel.latency_p95_ms} ms` : '--'}
                          </span>
                          <span className="text-[10px] text-[var(--text-secondary)] block">
                            (SLA: {w.sla_max_latency_ms}ms)
                          </span>
                        </td>
                        <td className="p-3">
                          {w.attribution_available ? (
                            <span className="inline-flex items-center gap-1 text-emerald-400 font-bold text-[10px]">
                              <CheckCircle2 size={12} /> PROBE ACTIVE
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-amber-400 font-bold text-[10px]">
                              <AlertTriangle size={12} /> UNMEASURED RESIDUAL
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 2: CAPACITY FORENSICS & RESIDUAL RECONCILIATION */}
      {/* ======================================================== */}
      {activeTab === 'capacity' && capacityForensics && (
        <div className="space-y-6">
          {/* Top Velocity & Acceleration Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-4">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Net Velocity</span>
              <div className="text-2xl font-black text-[var(--accent-primary)] mt-1">
                +{capacityForensics.growth_rate_gb_per_day} GB/day
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1 font-mono">
                Evaluated over {capacityForensics.window_hours}h
              </div>
            </div>

            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-4">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Acceleration Index</span>
              <div className="text-2xl font-black text-amber-400 mt-1">
                {capacityForensics.acceleration_gb_per_day2 > 0 ? `+${capacityForensics.acceleration_gb_per_day2}` : capacityForensics.acceleration_gb_per_day2} GB/day²
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1 font-mono">
                Pattern: {capacityForensics.growth_pattern}
              </div>
            </div>

            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-4">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Reserve Runway Breach</span>
              <div className="text-2xl font-black text-rose-400 mt-1">
                {capacityForensics.reserve_runway_projection.projected_days_to_breach !== null
                  ? `${capacityForensics.reserve_runway_projection.projected_days_to_breach} Days`
                  : 'SAFE (>180d)'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1 font-mono">
                Ceiling: {capacityForensics.reserve_runway_projection.safe_reserve_ceiling_gb} GB
              </div>
            </div>

            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-4">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Reconciliation Coverage</span>
              <div className="text-2xl font-black text-emerald-400 mt-1">
                {attribution?.attribution_coverage_pct ?? '--'}%
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1 font-mono">
                Residual: {attribution?.residual_unattributed_gb ?? 0} GB
              </div>
            </div>
          </div>

          {/* Three-Method Attribution Decomposition */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Method A & B Breakdown */}
            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-lg">
              <h3 className="text-sm font-bold text-[var(--text-primary)] font-mono uppercase mb-1">
                Method A & B: Direct Attribution & Residual Tracking
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mb-4">
                Compares sum of known workload allocations against the physical pool volume.
              </p>

              <div className="space-y-3">
                {attribution?.workload_breakdown.map((item: any) => {
                  const pct = attribution.device_aggregate_used_gb > 0
                    ? Math.round((item.current_allocated_gb / attribution.device_aggregate_used_gb) * 100)
                    : 0;
                  const isResidual = item.workload_type === 'RESIDUAL';
                  return (
                    <div key={item.workload_id} className="p-3 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                      <div className="flex justify-between items-center mb-1">
                        <span className={`font-mono text-xs font-bold ${isResidual ? 'text-[var(--accent-primary)]' : 'text-[var(--text-primary)]'}`}>
                          {item.workload_name}
                        </span>
                        <span className="font-mono text-xs text-[var(--text-secondary)]">
                          {item.current_allocated_gb} GB ({pct}%)
                        </span>
                      </div>
                      <div className="w-full bg-[var(--surface-elevated)] rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${isResidual ? 'bg-[var(--accent-primary)]' : 'bg-emerald-500'}`}
                          style={{ width: `${Math.min(100, pct)}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-[10px] text-[var(--text-secondary)] font-mono mt-1">
                        <span>Delta: +{item.growth_delta_gb} GB</span>
                        <span>Confidence: {(item.attribution_confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Method C: Statistical Feature Importance */}
            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-lg">
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-sm font-bold text-[var(--text-primary)] font-mono uppercase">
                  Method C: Statistical Attribution Proxy
                </h3>
                <span className="px-2 py-0.5 rounded text-[9px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  CORRELATION ONLY
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)] mb-4">
                Relative contribution derived from capacity growth delta and IOPS arrival rate.
              </p>

              <div className="space-y-3">
                {attribution?.statistical_attribution.map((stat: any) => (
                  <div key={stat.workload_id} className="p-3 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                    <div className="flex justify-between items-center mb-1 font-mono text-xs">
                      <span className="font-bold text-[var(--text-primary)]">{stat.workload_name}</span>
                      <span className="font-bold text-[var(--accent-primary)]">Score: {stat.composite_attribution_score}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-[var(--text-secondary)] mt-1">
                      <div>Capacity Share: <span className="text-[var(--text-primary)] font-bold">{stat.capacity_growth_share_pct}%</span></div>
                      <div>IOPS Contention: <span className="text-[var(--text-primary)] font-bold">{stat.iops_contention_share_pct}%</span></div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 p-3 rounded-lg bg-amber-950/20 border border-amber-500/30 text-amber-300 text-[11px] flex gap-2">
                <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                <span>
                  <strong>Scientific Notice:</strong> Statistical feature decomposition identifies mathematical correlation with demand bursts. It does not establish physical causation without a controlled ablation test.
                </span>
              </div>
            </div>
          </div>

          {/* Changepoint Surges Table */}
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl overflow-hidden shadow-lg">
            <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--surface-primary)]">
              <h3 className="text-sm font-bold text-[var(--text-primary)] font-mono uppercase">
                Historical Changepoint Surges & Compaction Events
              </h3>
              <p className="text-xs text-[var(--text-secondary)]">
                Step-changes detected (&gt;30GB burst or &lt;-15GB compaction) via discrete difference calculus.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                  <tr>
                    <th className="p-3">Timestamp</th>
                    <th className="p-3">Event Type</th>
                    <th className="p-3">Step Delta</th>
                    <th className="p-3">Suspected Workload</th>
                    <th className="p-3">Confidence</th>
                    <th className="p-3">Forensic Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {capacityForensics.changepoints_detected.map((cp: any, idx: number) => (
                    <tr key={idx} className="hover:bg-[var(--surface-primary)]/50">
                      <td className="p-3 text-[var(--text-secondary)]">{cp.timestamp}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          cp.type === 'RAPID_SURGE' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                          'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        }`}>
                          {cp.type}
                        </span>
                      </td>
                      <td className="p-3 font-bold text-[var(--text-primary)]">
                        {cp.delta_gb > 0 ? `+${cp.delta_gb}` : cp.delta_gb} GB
                      </td>
                      <td className="p-3 text-[var(--accent-primary)] font-bold">{cp.suspected_workload}</td>
                      <td className="p-3">{(cp.confidence * 100).toFixed(0)}%</td>
                      <td className="p-3 text-[var(--text-secondary)]">{cp.description}</td>
                    </tr>
                  ))}
                  {capacityForensics.changepoints_detected.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-4 text-center text-[var(--text-secondary)]">
                        No step changepoints detected exceeding ±15GB threshold.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 3: PERFORMANCE BOTTLENECKS & CONTENTION INDEX */}
      {/* ======================================================== */}
      {activeTab === 'bottlenecks' && bottlenecks && (
        <div className="space-y-6">
          {/* Contention Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Contention Index (0.0 – 1.0)</span>
              <div className="text-3xl font-black text-rose-400 mt-1">
                {bottlenecks.contention_index}
              </div>
              <div className="text-xs font-mono font-bold text-rose-400 mt-1">
                Level: {bottlenecks.contention_level}
              </div>
              <p className="text-[11px] text-[var(--text-secondary)] mt-2">
                Evaluates concurrent queue saturation, tail latency variance, and I/O bus contention.
              </p>
            </div>

            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Current P95 Tail Latency</span>
              <div className={`text-3xl font-black mt-1 ${bottlenecks.sla_breached ? 'text-rose-400' : 'text-emerald-400'}`}>
                {bottlenecks.latency_p95_current_ms} ms
              </div>
              <div className="text-xs font-mono text-[var(--text-secondary)] mt-1">
                SLA Ceiling: {bottlenecks.sla_max_latency_ms} ms ({bottlenecks.sla_breached ? 'BREACHED' : 'COMPLIANT'})
              </div>
              <p className="text-[11px] text-[var(--text-secondary)] mt-2">
                Monitored at storage controller flash submission queues.
              </p>
            </div>

            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5">
              <span className="text-[10px] font-mono uppercase text-[var(--text-secondary)]">Concurrent Background Jobs</span>
              <div className="text-3xl font-black text-amber-400 mt-1">
                {bottlenecks.concurrent_background_jobs.length}
              </div>
              <div className="text-xs font-mono text-[var(--text-secondary)] mt-1">
                Overlapping ETL, backup, and GC TRIM cycles
              </div>
              <p className="text-[11px] text-[var(--text-secondary)] mt-2">
                High risk of tail latency spikes during 01:00 – 04:00 maintenance windows.
              </p>
            </div>
          </div>

          {/* Forensics Findings List */}
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-lg">
            <h3 className="text-sm font-bold text-[var(--text-primary)] font-mono uppercase mb-4">
              Forensic Contention Signals & Confounders
            </h3>

            <div className="space-y-3">
              {bottlenecks.forensics_findings.map((finding: any, idx: number) => (
                <div key={idx} className="p-4 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-mono text-xs font-bold text-[var(--accent-primary)]">
                        {finding.signal}
                      </span>
                      <p className="text-xs text-[var(--text-secondary)] mt-1">
                        {finding.evidence}
                      </p>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                      finding.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                      finding.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                      'bg-[var(--surface-elevated)] text-[var(--text-secondary)] border border-[var(--border-normal)]'
                    }`}>
                      {finding.severity}
                    </span>
                  </div>
                  <div className="flex gap-1.5 mt-2 flex-wrap">
                    <span className="text-[10px] text-[var(--text-secondary)] font-mono">Associated Workloads:</span>
                    {finding.contributing_workloads.map((wId: string) => (
                      <span key={wId} className="px-1.5 py-0.5 rounded bg-[var(--surface-secondary)] text-[var(--text-secondary)] text-[10px] font-mono border border-[var(--border-normal)]">
                        {wId}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Active Bottleneck Forensic Cases */}
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl overflow-hidden shadow-lg">
            <div className="p-4 border-b border-[var(--border-subtle)] flex justify-between items-center bg-[var(--surface-primary)]">
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)] font-mono uppercase">
                  Active Forensic Investigation Cases
                </h3>
                <p className="text-xs text-[var(--text-secondary)]">
                  Triaged contention incidents assigned to storage reliability engineers.
                </p>
              </div>
              <span className="text-xs font-mono text-[var(--text-secondary)]">
                {cases.length} Tracked Cases
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                  <tr>
                    <th className="p-3">Case ID / Title</th>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Suspected Workload</th>
                    <th className="p-3">Assigned Investigator</th>
                    <th className="p-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {cases.map((c) => (
                    <tr key={c.id} className="hover:bg-[var(--surface-primary)]/50">
                      <td className="p-3">
                        <div className="font-bold text-[var(--text-primary)]">{c.title}</div>
                        <div className="text-[10px] text-[var(--accent-primary)]">{c.id}</div>
                        <div className="text-[10px] text-[var(--text-secondary)] line-clamp-1">{c.evidence_summary}</div>
                      </td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          c.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                          'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        }`}>
                          {c.severity}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)] font-bold text-[10px]">
                          {c.status}
                        </span>
                      </td>
                      <td className="p-3 text-[var(--accent-primary)] font-bold">
                        {c.suspected_workload_id || 'GENERAL_CONTENTION'}
                      </td>
                      <td className="p-3 text-[var(--text-secondary)]">
                        {c.assigned_investigator || 'Unassigned'}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-2">
                          {c.status !== 'RESOLVED' && (
                            <button
                              onClick={async () => {
                                await api.updateOracleCase(c.id, {
                                  status: 'RESOLVED',
                                  notes: 'Mitigated via what-if rescheduling',
                                  investigator: 'lead_sre@aegisstor.internal'
                                });
                                await loadAllData();
                              }}
                              className="px-2.5 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-[10px] font-bold"
                            >
                              Resolve
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 4: RESOURCE CONTENTION TOPOLOGY GRAPH */}
      {/* ======================================================== */}
      {activeTab === 'graph' && contentionGraph && (
        <div className="space-y-6">
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-lg">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)] font-mono uppercase">
                  Storage Dependency & Contention Topology
                </h3>
                <p className="text-xs text-[var(--text-secondary)]">
                  Visual mapping of Workload, Device, Pool, and Storage Controller nodes.
                </p>
              </div>
              <div className="flex gap-3 text-xs font-mono">
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <span className="w-3 h-0.5 bg-emerald-400 inline-block" /> Verified Dependency
                </span>
                <span className="flex items-center gap-1.5 text-rose-400 font-bold">
                  <span className="w-3 h-0.5 border-b-2 border-dashed border-rose-400 inline-block" /> Suspected Contention
                </span>
              </div>
            </div>

            {/* Interactive SVG Topology Representation */}
            <div className="relative bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-6 overflow-hidden min-h-[380px]">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative z-10">
                {/* Column 1: Workloads */}
                <div className="space-y-3">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-[var(--accent-primary)] font-bold pb-2 border-b border-[var(--border-subtle)]">
                    Workload Tier
                  </div>
                  {contentionGraph.nodes.filter((n: any) => n.type === 'WORKLOAD').map((node: any) => (
                    <div key={node.id} className="p-2.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-xs font-mono hover:border-[var(--accent-primary)] transition-colors">
                      <div className="font-bold text-[var(--text-primary)]">{node.name}</div>
                      <div className="text-[10px] text-[var(--accent-primary)]">{node.id}</div>
                      <div className="text-[10px] text-[var(--text-secondary)] mt-1">{node.allocated_gb} GB</div>
                    </div>
                  ))}
                </div>

                {/* Column 2: Storage Volumes */}
                <div className="space-y-3">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-[var(--accent-tertiary)] font-bold pb-2 border-b border-[var(--border-subtle)]">
                    Target Volumes
                  </div>
                  {contentionGraph.nodes.filter((n: any) => n.type === 'DEVICE').map((node: any) => (
                    <div key={node.id} className="p-2.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-xs font-mono hover:border-[var(--accent-tertiary)] transition-colors">
                      <div className="font-bold text-[var(--text-primary)]">{node.name}</div>
                      <div className="text-[10px] text-[var(--accent-tertiary)]">{node.id}</div>
                      <div className="text-[10px] text-[var(--text-secondary)] mt-1">Util: {node.utilization_pct}% | {node.latency_p95_ms}ms</div>
                    </div>
                  ))}
                </div>

                {/* Column 3: Storage Pools */}
                <div className="space-y-3">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-emerald-400 font-bold pb-2 border-b border-[var(--border-subtle)]">
                    Storage Pools
                  </div>
                  {contentionGraph.nodes.filter((n: any) => n.type === 'POOL').map((node: any) => (
                    <div key={node.id} className="p-2.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-xs font-mono">
                      <div className="font-bold text-[var(--text-primary)]">{node.name}</div>
                      <div className="text-[10px] text-emerald-400">{node.id}</div>
                    </div>
                  ))}
                </div>

                {/* Column 4: Storage Controllers & Bus */}
                <div className="space-y-3">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-amber-400 font-bold pb-2 border-b border-[var(--border-subtle)]">
                    Controllers / Bus
                  </div>
                  {contentionGraph.nodes.filter((n: any) => n.type === 'CONTROLLER').map((node: any) => (
                    <div key={node.id} className="p-2.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-xs font-mono">
                      <div className="font-bold text-[var(--text-primary)]">{node.name}</div>
                      <div className="text-[10px] text-amber-400">{node.id}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Topology Disclaimer */}
            <div className="mt-4 p-3 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-xs text-[var(--text-secondary)] font-mono flex items-center gap-2">
              <Scale size={16} className="text-[var(--accent-primary)] shrink-0" />
              <span>{contentionGraph.summary.graph_disclaimer}</span>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 5: HYPOTHESIS WORKSPACE & WHAT-IF SIMULATION */}
      {/* ======================================================== */}
      {activeTab === 'workspace' && (
        <div className="space-y-6">
          {/* Action Toolbar */}
          <div className="flex flex-wrap justify-between items-center gap-4 bg-[var(--surface-secondary)] border border-[var(--border-subtle)] p-4 rounded-xl">
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono uppercase font-bold text-[var(--text-primary)]">
                Falsifiable Hypothesis Manager
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] font-bold">
                {hypotheses.length} Recorded
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowHypModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white text-xs font-bold font-mono transition-all shadow-md"
              >
                <Plus size={14} /> New Hypothesis
              </button>

              <button
                onClick={() => handleDownloadReport('markdown')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] text-[var(--text-secondary)] hover:text-white text-xs font-mono transition-all"
              >
                <Download size={14} /> Export Markdown
              </button>

              <button
                onClick={() => handleDownloadReport('csv')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] text-[var(--text-secondary)] hover:text-white text-xs font-mono transition-all"
              >
                <Download size={14} /> Export CSV
              </button>
            </div>
          </div>

          {/* Master-Detail Layout */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Hypotheses List */}
            <div className="space-y-3">
              {hypotheses.map((hyp) => {
                const isSelected = selectedHypothesis?.id === hyp.id;
                return (
                  <div
                    key={hyp.id}
                    onClick={() => setSelectedHypothesis(hyp)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-[var(--surface-secondary)] border-[var(--accent-primary)] shadow-md'
                        : 'bg-[var(--surface-primary)] border-[var(--border-subtle)] hover:border-[var(--border-highlight)]'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-[10px] font-mono text-[var(--accent-primary)] font-bold">{hyp.id}</span>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold ${
                        hyp.status === 'SUPPORTED_WITHIN_CONDITIONS' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                        hyp.status === 'READY_FOR_TESTING' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40' :
                        hyp.status === 'UNDER_EVALUATION' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                        'bg-[var(--surface-elevated)] text-[var(--text-secondary)] border border-[var(--border-normal)]'
                      }`}>
                        {hyp.status}
                      </span>
                    </div>
                    <h4 className="text-xs font-bold text-[var(--text-primary)] line-clamp-2 mb-2 font-mono">
                      {hyp.question}
                    </h4>
                    <div className="flex justify-between text-[10px] text-[var(--text-secondary)] font-mono">
                      <span>Target: {hyp.target_resource}</span>
                      <span>Reviewer: {hyp.reviewer.split('@')[0]}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Selected Hypothesis Detail */}
            {selectedHypothesis ? (
              <div className="md:col-span-2 space-y-4 bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-lg">
                <div className="flex justify-between items-start pb-3 border-b border-[var(--border-subtle)]">
                  <div>
                    <span className="text-xs font-mono text-[var(--accent-primary)] font-bold">{selectedHypothesis.id}</span>
                    <h3 className="text-base font-bold text-[var(--text-primary)] mt-1">
                      {selectedHypothesis.question}
                    </h3>
                  </div>
                  <div className="flex gap-2">
                    {selectedHypothesis.status === 'DRAFT' && (
                      <button
                        onClick={() => handlePromoteHypothesis(selectedHypothesis.id, 'EVIDENCE_GATHERING')}
                        className="px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 border border-blue-500/40 text-xs font-mono font-bold"
                      >
                        Gather Evidence
                      </button>
                    )}
                    {selectedHypothesis.status === 'EVIDENCE_GATHERING' && (
                      <button
                        onClick={() => handlePromoteHypothesis(selectedHypothesis.id, 'READY_FOR_TESTING')}
                        className="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-mono font-bold"
                      >
                        Mark Ready for Testing
                      </button>
                    )}
                    {selectedHypothesis.status === 'READY_FOR_TESTING' && (
                      <button
                        onClick={() => handlePromoteHypothesis(selectedHypothesis.id, 'UNDER_EVALUATION')}
                        className="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-mono font-bold"
                      >
                        Start Evaluation
                      </button>
                    )}
                    {selectedHypothesis.status === 'UNDER_EVALUATION' && (
                      <button
                        onClick={() => handlePromoteHypothesis(selectedHypothesis.id, 'SUPPORTED_WITHIN_CONDITIONS')}
                        className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-mono font-bold"
                      >
                        Support Within Conditions
                      </button>
                    )}
                  </div>
                </div>

                {/* Evidence Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Supporting Evidence */}
                  <div className="p-3 rounded-lg bg-[var(--surface-primary)] border border-emerald-500/30">
                    <h5 className="text-xs font-mono font-bold text-emerald-400 mb-2 flex items-center gap-1.5">
                      <CheckCircle2 size={14} /> Supporting Evidence
                    </h5>
                    <ul className="space-y-1.5 text-xs text-[var(--text-secondary)] font-mono">
                      {selectedHypothesis.supporting_evidence.map((item: string, idx: number) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-emerald-400 font-bold">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                      {selectedHypothesis.supporting_evidence.length === 0 && (
                        <li className="italic text-[var(--text-muted)]">No supporting evidence recorded.</li>
                      )}
                    </ul>
                  </div>

                  {/* Contradicting Evidence */}
                  <div className="p-3 rounded-lg bg-[var(--surface-primary)] border border-rose-500/30">
                    <h5 className="text-xs font-mono font-bold text-rose-400 mb-2 flex items-center gap-1.5">
                      <AlertTriangle size={14} /> Contradictions & Confounds
                    </h5>
                    <ul className="space-y-1.5 text-xs text-[var(--text-secondary)] font-mono">
                      {selectedHypothesis.contradicting_evidence.map((item: string, idx: number) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <span className="text-rose-400 font-bold">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                      {selectedHypothesis.contradicting_evidence.length === 0 && (
                        <li className="italic text-[var(--text-muted)]">No contradicting evidence recorded.</li>
                      )}
                    </ul>
                  </div>
                </div>

                {/* Controlled What-If Simulator Section */}
                <div className="mt-4 p-4 rounded-lg bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <h4 className="text-xs font-mono font-bold text-[var(--text-primary)] uppercase flex items-center gap-1.5">
                        <Play size={14} className="text-[var(--accent-primary)]" />
                        Controlled Digital Twin What-If Simulator
                      </h4>
                      <p className="text-[11px] text-[var(--text-secondary)]">
                        Tests hypothesis counterfactually without mutating real production storage.
                      </p>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[var(--surface-elevated)] text-[var(--text-secondary)] border border-[var(--border-normal)]">
                      Zero Host Mutations
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <label className="text-[10px] font-mono uppercase text-[var(--text-secondary)] block mb-1">Target Workload</label>
                      <select
                        value={simWorkloadId}
                        onChange={(e) => setSimWorkloadId(e.target.value)}
                        className="w-full bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded p-2 text-xs font-mono text-[var(--text-primary)]"
                      >
                        {workloads.map((w) => (
                          <option key={w.id} value={w.id}>{w.name}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-[10px] font-mono uppercase text-[var(--text-secondary)] block mb-1">Intervention Type</label>
                      <select
                        value={simIntervention}
                        onChange={(e) => setSimIntervention(e.target.value)}
                        className="w-full bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded p-2 text-xs font-mono text-[var(--text-primary)]"
                      >
                        <option value="THROTTLE_INTENSITY">Throttle Intensity (% Reduction)</option>
                        <option value="RESCHEDULE_WINDOW">Reschedule Batch Window (+Hours Shift)</option>
                        <option value="EXPAND_SHARED_LIMIT">Expand Controller Queue Limit</option>
                      </select>
                    </div>

                    <div>
                      {simIntervention === 'THROTTLE_INTENSITY' && (
                        <div>
                          <label className="text-[10px] font-mono uppercase text-[var(--text-secondary)] block mb-1">
                            Reduction: {simThrottlePct}%
                          </label>
                          <input
                            type="range"
                            min="5"
                            max="75"
                            value={simThrottlePct}
                            onChange={(e) => setSimThrottlePct(Number(e.target.value))}
                            className="w-full accent-[var(--accent-primary)] mt-2"
                          />
                        </div>
                      )}
                      {simIntervention === 'RESCHEDULE_WINDOW' && (
                        <div>
                          <label className="text-[10px] font-mono uppercase text-[var(--text-secondary)] block mb-1">
                            Shift Window: +{simShiftHours} Hours
                          </label>
                          <input
                            type="range"
                            min="1"
                            max="12"
                            value={simShiftHours}
                            onChange={(e) => setSimShiftHours(Number(e.target.value))}
                            className="w-full accent-[var(--accent-primary)] mt-2"
                          />
                        </div>
                      )}
                      {simIntervention === 'EXPAND_SHARED_LIMIT' && (
                        <div>
                          <label className="text-[10px] font-mono uppercase text-[var(--text-secondary)] block mb-1">Queue Limit</label>
                          <input
                            type="text"
                            disabled
                            value="Controller Cap Relaxed (-35% Queue Delay)"
                            className="w-full bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded p-2 text-xs font-mono text-[var(--text-secondary)]"
                          />
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button
                      onClick={handleRunCounterfactual}
                      disabled={simulating}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white font-mono font-bold text-xs shadow-md transition-all disabled:opacity-50"
                    >
                      <Play size={14} className={simulating ? 'animate-spin' : ''} />
                      {simulating ? 'Simulating in Twin...' : 'Run Pure-Software What-If'}
                    </button>
                  </div>

                  {/* Simulation Output Card */}
                  {simResult && (
                    <div className="p-4 rounded-lg bg-[var(--surface-secondary)] border border-[var(--accent-primary)]/40 mt-3 space-y-3 font-mono">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-[var(--accent-primary)]">{simResult.title}</span>
                        <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                          simResult.sla_breach_prevented
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                            : 'bg-[var(--surface-elevated)] text-[var(--text-secondary)]'
                        }`}>
                          {simResult.sla_breach_prevented ? 'SLA BREACH PREVENTED' : 'LATENCY REDUCED'}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                        <div className="p-2.5 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                          <span className="text-[10px] text-[var(--text-secondary)]">Baseline P95</span>
                          <div className="text-base font-bold text-[var(--text-primary)]">
                            {simResult.baseline.baseline_p95_latency_ms} ms
                          </div>
                        </div>

                        <div className="p-2.5 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                          <span className="text-[10px] text-[var(--text-secondary)]">Simulated Avg P95</span>
                          <div className="text-base font-bold text-emerald-400">
                            {simResult.simulated_outcome.avg_simulated_latency_ms} ms (-{simResult.simulated_outcome.latency_reduction_pct}%)
                          </div>
                        </div>

                        <div className="p-2.5 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                          <span className="text-[10px] text-[var(--text-secondary)]">Causality Status</span>
                          <div className="text-base font-bold text-amber-400">
                            SIMULATED ONLY
                          </div>
                        </div>
                      </div>

                      <p className="text-[10px] text-[var(--text-secondary)] italic">
                        {simResult.causality_disclaimer}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="md:col-span-2 p-8 text-center text-[var(--text-muted)] font-mono text-xs bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl flex items-center justify-center">
                Select a hypothesis to view evidence audit trail and run controlled counterfactuals.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* NEW HYPOTHESIS MODAL */}
      {/* ======================================================== */}
      {showHypModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-[var(--border-subtle)]">
              <div>
                <h3 className="text-base font-bold text-[var(--text-primary)] font-mono uppercase">
                  Formulate Falsifiable Storage Hypothesis
                </h3>
                <p className="text-xs text-[var(--text-secondary)]">
                  Subjected to automated topological and data quality contradiction checks.
                </p>
              </div>
              <button
                onClick={() => setShowHypModal(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)] font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateHypothesis} className="space-y-4 font-mono text-xs">
              <div>
                <label className="block text-[10px] uppercase text-[var(--text-secondary)] mb-1">
                  Investigation Question (Falsifiable)
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Does batch ETL concurrency solely explain P95 latency breaches?"
                  value={hypForm.question}
                  onChange={(e) => setHypForm({ ...hypForm, question: e.target.value })}
                  className="w-full bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded p-2.5 text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-primary)]"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] uppercase text-[var(--text-secondary)] mb-1">
                    Target Resource
                  </label>
                  <select
                    value={hypForm.target_resource}
                    onChange={(e) => setHypForm({ ...hypForm, target_resource: e.target.value })}
                    className="w-full bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                  >
                    <option value="vol-nvme-tier1-db">vol-nvme-tier1-db (OLTP NVMe)</option>
                    <option value="vol-sas-tier2-analytics">vol-sas-tier2-analytics (SAS Warehouse)</option>
                    <option value="vol-cold-tier3-backup">vol-cold-tier3-backup (Cold Archive)</option>
                    <option value="vol-edge-cache-01">vol-edge-cache-01 (Edge Stream)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] uppercase text-[var(--text-secondary)] mb-1">
                    Suspected Workload
                  </label>
                  <select
                    value={hypForm.workload_id}
                    onChange={(e) => setHypForm({ ...hypForm, workload_id: e.target.value })}
                    className="w-full bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                  >
                    {workloads.map((w) => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[var(--text-secondary)] mb-1">
                  Supporting Evidence (One per line)
                </label>
                <textarea
                  rows={2}
                  placeholder="P95 latency surges to 18ms between 01:00-04:00&#10;Analytics batch arrives with 3200 IOPS in the same window"
                  value={hypForm.supporting_evidence}
                  onChange={(e) => setHypForm({ ...hypForm, supporting_evidence: e.target.value })}
                  className="w-full bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[var(--text-secondary)] mb-1">
                  Candidate Contradicting Evidence & Confounders (One per line)
                </label>
                <textarea
                  rows={2}
                  placeholder="PCIe bus throughput remains under 65% capacity&#10;Security vulnerability scanning concurrently active at 02:00"
                  value={hypForm.contradicting_evidence}
                  onChange={(e) => setHypForm({ ...hypForm, contradicting_evidence: e.target.value })}
                  className="w-full bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-[var(--border-subtle)]">
                <button
                  type="button"
                  onClick={() => setShowHypModal(false)}
                  className="px-4 py-2 rounded bg-[var(--surface-secondary)] hover:bg-[var(--surface-elevated)] text-[var(--text-primary)] border border-[var(--border-normal)] font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white font-bold"
                >
                  Save Hypothesis & Run Contradiction Checks
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
