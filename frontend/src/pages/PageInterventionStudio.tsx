import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, RecommendationItem } from '../api/client';
import {
  Sliders,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  AlertTriangle,
  Clock,
  DollarSign,
  TrendingDown,
  Activity,
  Layers,
  ArrowRight,
  ShieldAlert,
  Info,
  Sparkles
} from 'lucide-react';
import { EmptyState } from '../components/EmptyState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ContextualHelp } from '../components/ContextualHelp';
import { usePresentationMode } from '../context/PresentationModeContext';

interface Props {
  initialDeviceId?: string;
}

export const PageInterventionStudio: React.FC<Props> = ({ initialDeviceId }) => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(initialDeviceId || 'vol-nvme-tier1-db');
  const [horizonHours, setHorizonHours] = useState<number>(72);
  
  // Intelligence states
  const [runwayData, setRunwayData] = useState<any | null>(null);
  const [planningData, setPlanningData] = useState<any | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [activeSimulation, setActiveSimulation] = useState<any | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  
  // Actions feedback
  const [actionNotes, setActionNotes] = useState<string>('');
  const [actionStatusMsg, setActionStatusMsg] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const { isGuided } = usePresentationMode();

  useEffect(() => {
    loadDevices();
  }, []);

  useEffect(() => {
    if (initialDeviceId && initialDeviceId !== selectedDeviceId) {
      setSelectedDeviceId(initialDeviceId);
    }
  }, [initialDeviceId]);

  useEffect(() => {
    if (selectedDeviceId) {
      loadDeviceIntelligence(selectedDeviceId);
    }
  }, [selectedDeviceId, horizonHours]);

  const loadDevices = async () => {
    try {
      const list = await api.getDevices();
      setDevices(list);
      if (initialDeviceId) {
        setSelectedDeviceId(initialDeviceId);
      } else if (list.length > 0) {
        setSelectedDeviceId(list[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadDeviceIntelligence = async (id: string) => {
    setLoading(true);
    setActionStatusMsg('');
    try {
      const [rw, plan, recs] = await Promise.all([
        api.getReserveRunway(id),
        api.evaluatePlanning(id),
        api.getRecommendations(id),
      ]);
      setRunwayData(rw);
      setPlanningData(plan);
      setRecommendations(recs);

      // Select top recommendation if available
      if (plan.top_recommendation) {
        setSelectedCandidateId(plan.top_recommendation.id);
        runComparativeSimulation(plan.top_recommendation.action_type);
      }
    } catch (e: any) {
      console.error('Failed to load device intelligence:', e);
    } finally {
      setLoading(false);
    }
  };

  const runComparativeSimulation = async (actionType: string) => {
    try {
      let params: Record<string, any> = {};
      if (actionType === 'TIER_COLD_DATA') {
        params = { data_volume_gb: 1500.0, migration_rate_mb_s: 150.0 };
      } else if (actionType === 'EXPAND_CAPACITY') {
        params = { added_capacity_gb: 2000.0, provisioning_lead_hours: 2.0 };
      } else if (actionType === 'REBALANCE_WORKLOAD') {
        params = { relocated_iops_pct: 25.0 };
      }

      const res = await api.createScenario({
        device_id: selectedDeviceId,
        name: `Intervention Studio: ${actionType}`,
        action_type: actionType,
        parameters: params,
      });
      setActiveSimulation(res);
    } catch (e) {
      console.error('Simulation error:', e);
    }
  };

  const handleApprove = async (recId: string) => {
    try {
      await api.approveRecommendation(recId, actionNotes || 'Approved dry-run in shadow mode.');
      setActionStatusMsg(`Action ${recId} approved for safe shadow execution.`);
      loadDeviceIntelligence(selectedDeviceId);
    } catch (e: any) {
      setActionStatusMsg(`Error: ${e.message}`);
    }
  };

  const handleReject = async (recId: string) => {
    try {
      await api.rejectRecommendation(recId, actionNotes || 'Rejected by operator discretion.');
      setActionStatusMsg(`Action ${recId} dismissed.`);
      loadDeviceIntelligence(selectedDeviceId);
    } catch (e: any) {
      setActionStatusMsg(`Error: ${e.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center shadow-xs">
              <Sliders size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              {isGuided ? 'Compare Possible Actions & Action Planner' : 'Counterfactual Intervention Studio'}
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm">
              SHADOW MODE: SAFE
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
            {isGuided
              ? 'Evaluates whether proposed actions (like cold tiering or capacity growth) can finish before your disks fill up.'
              : 'Lead-time-aware preventive action planning. Evaluates whether candidate interventions can complete before predicted capacity or latency SLA breach.'}
          </p>
        </div>

        {/* Storage Pool Selector */}
        <div className="flex items-center gap-3">
          <select
            value={selectedDeviceId}
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            className="bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3.5 py-1.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
            aria-label="Storage Pool"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id} className="bg-[var(--surface-primary)] text-[var(--text-primary)]">
                {d.name} ({d.tier})
              </option>
            ))}
          </select>
        </div>
      </div>

      {actionStatusMsg && (
        <div className="bg-[var(--status-success)]/15 border border-[var(--status-success)]/40 rounded-xl p-3 text-xs text-[var(--status-success)] font-mono flex items-center gap-2 shadow-sm animate-in fade-in">
          <CheckCircle2 size={16} />
          <span>{actionStatusMsg}</span>
        </div>
      )}

      {loading ? (
        <LoadingSkeleton rows={6} height="h-10" />
      ) : (
        <>
          {/* STEP 1 & 2: Risk Breach Diagnostic Banner */}
          {runwayData && (
            <div className={`p-5 rounded-lg border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 transition-all ${
              runwayData.estimated_runway_hours <= 48
                ? 'bg-[var(--status-critical)]/10 border-[var(--status-critical)]/35 text-[var(--text-primary)]'
                : runwayData.estimated_runway_hours <= 96
                ? 'bg-[var(--status-warning)]/10 border-[var(--status-warning)]/35 text-[var(--text-primary)]'
                : 'titan-card text-[var(--text-primary)]'
            }`}>
              <div className="flex items-start gap-3.5">
                <AlertTriangle
                  size={22}
                  className={runwayData.estimated_runway_hours <= 48 ? 'text-[var(--status-critical)] mt-0.5' : 'text-[var(--status-warning)] mt-0.5'}
                />
                <div>
                  <div className="text-xs font-bold flex items-center gap-2">
                    <span>{isGuided ? 'Projected Time to Critical Reserve:' : 'Projected Reserve Breach Horizon:'}</span>
                    <span className="font-mono text-[var(--accent-primary)] font-semibold">
                      ~{runwayData.estimated_runway_hours.toFixed(0)} hours
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
                      {runwayData.breach_status}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] mt-1.5 leading-relaxed">
                    Under current write growth (+{runwayData.growth_rate_daily_gb} GB/day), free reserve drops below {runwayData.configured_critical_threshold_pct}% critical threshold.
                    Sensitivity window: <span className="font-mono text-[var(--text-primary)] font-semibold">[{runwayData.sensitivity_pessimistic_hours}h pessimistic .. {runwayData.sensitivity_optimistic_hours}h optimistic]</span>.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono shrink-0">
                <div className="px-3.5 py-2 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-center shadow-inner">
                  <div className="text-[10px] text-[var(--text-muted)]">Usable Capacity</div>
                  <div className="font-bold text-[var(--text-primary)]">
                    {(runwayData.total_capacity_bytes / 1e12).toFixed(1)} TB
                  </div>
                </div>
                <div className="px-3.5 py-2 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-center shadow-inner">
                  <div className="text-[10px] text-[var(--text-muted)]">Current Util</div>
                  <div className={`font-bold ${runwayData.current_utilization_pct > 80 ? 'text-[var(--status-critical)]' : 'text-[var(--text-primary)]'}`}>
                    {runwayData.current_utilization_pct}%
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3 & 4: Action Candidates Matrix */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                <span>{isGuided ? 'Safe, Feasible Actions' : 'Feasible Preventive Candidates'}</span>
                <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30 font-semibold shadow-sm">
                  {planningData?.feasible_candidates?.length || 0} FEASIBLE
                </span>
              </h3>
              <span className="text-[11px] text-[var(--text-secondary)]">
                Objective: Maximize Runway Headroom while Minimizing Contention Penalty
              </span>
            </div>

            {/* Feasible Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {planningData?.feasible_candidates?.map((candidate: any) => {
                const isSelected = selectedCandidateId === candidate.id;
                return (
                  <div
                    key={candidate.id}
                    onClick={() => {
                      setSelectedCandidateId(candidate.id);
                      runComparativeSimulation(candidate.action_type);
                    }}
                    className={`titan-card rounded-lg p-4.5 cursor-pointer transition-all ${
                      isSelected
                        ? 'border-[var(--accent-primary)] shadow-[0_0_15px_rgba(97,221,248,0.18)] bg-[var(--surface-secondary)]'
                        : 'hover:border-[var(--accent-primary)]/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/40">
                        RANK #{candidate.rank}
                      </span>
                      <span className="text-xs font-mono font-bold text-[var(--status-success)]">
                        Score: {candidate.utility_score}
                      </span>
                    </div>

                    <h4 className="text-xs font-bold text-[var(--text-primary)] mt-2.5 line-clamp-1">
                      {candidate.title}
                    </h4>
                    <p className="text-[11px] text-[var(--text-secondary)] mt-1 line-clamp-2">
                      {candidate.description}
                    </p>

                    <div className="mt-3 pt-3 border-t border-[var(--border-subtle)] grid grid-cols-2 gap-2 text-[10px] font-mono">
                      <div>
                        <span className="text-[var(--text-muted)]">Runway Gain:</span>
                        <div className="text-[var(--status-warning)] font-bold">+{candidate.estimated_runway_gain_hours} hrs</div>
                      </div>
                      <div>
                        <span className="text-[var(--text-muted)]">Duration:</span>
                        <div className="text-[var(--text-primary)] font-bold">{candidate.estimated_duration_hours} hrs</div>
                      </div>
                      <div>
                        <span className="text-[var(--text-muted)]">Contention:</span>
                        <div className={candidate.io_overhead_pct > 15 ? 'text-[var(--status-critical)]' : 'text-[var(--status-success)]'}>
                          {candidate.io_overhead_pct > 0 ? `+${candidate.io_overhead_pct}%` : `${candidate.io_overhead_pct}%`}
                        </div>
                      </div>
                      <div>
                        <span className="text-[var(--text-muted)]">Cost Est:</span>
                        <div className="text-[var(--text-primary)] font-bold">${candidate.estimated_cost_usd}</div>
                      </div>
                    </div>

                    <div className="mt-3.5 flex items-center justify-between pt-2.5 border-t border-[var(--border-subtle)]">
                      <span className="text-[10px] font-mono text-[var(--status-success)] flex items-center gap-1">
                        <CheckCircle2 size={12} />
                        Safe to schedule
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleApprove(candidate.id);
                        }}
                        className="px-3 py-1 btn-ember-primary rounded-lg text-[10px] font-bold"
                      >
                        Approve
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Disqualified Candidates Section with 4-Point Explanation */}
            {planningData?.rejected_candidates?.length > 0 && (
              <div className="mt-4 p-5 rounded-lg titan-card border border-[var(--status-critical)]/30 space-y-3">
                <div className="text-xs font-bold text-[var(--status-critical)] flex items-center gap-2">
                  <XCircle size={16} />
                  <span>Disqualified Actions (Rejected by Hard Safety Limits)</span>
                </div>
                <div className="space-y-2">
                  {planningData.rejected_candidates.map((rej: any) => (
                    <div
                      key={rej.id}
                      className="text-xs p-3.5 rounded-xl bg-[var(--surface-secondary)]/60 border border-[var(--border-subtle)] flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                    >
                      <div>
                        <span className="font-semibold text-[var(--text-primary)]">{rej.title}: </span>
                        <span className="text-[var(--text-secondary)]">{rej.rejection_reason}</span>
                      </div>
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--status-critical)]/15 text-[var(--status-critical)] border border-[var(--status-critical)]/40 shrink-0">
                        {rej.feasibility}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* STEP 5: Side-by-Side Simulation Trajectory Inspector */}
          {activeSimulation && (
            <div className="titan-card rounded-lg p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                    <Activity size={16} className="text-[var(--accent-primary)]" />
                    <span>Side-by-Side Scenario Trajectory</span>
                  </h3>
                  <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                    Comparing Baseline organic growth (Do Nothing) versus {activeSimulation.action_type}.
                  </p>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono">
                  <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
                    <span className="w-3 h-0.5 bg-[var(--text-muted)] inline-block"></span>
                    Baseline (Do Nothing)
                  </span>
                  <span className="flex items-center gap-1.5 text-[var(--accent-primary)] font-bold">
                    <span className="w-3 h-0.5 bg-[var(--accent-primary)] inline-block"></span>
                    Virtual Action Trajectory
                  </span>
                </div>
              </div>

              {/* Trajectory Key Metrics Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[var(--surface-secondary)]/60 p-3.5 rounded-xl border border-[var(--border-subtle)] text-xs font-mono">
                <div>
                  <span className="text-[var(--text-muted)] text-[10px]">Action Duration:</span>
                  <div className="text-[var(--text-primary)] font-bold">{activeSimulation.duration_minutes} min</div>
                </div>
                <div>
                  <span className="text-[var(--text-muted)] text-[10px]">I/O Contention:</span>
                  <div className="text-[var(--status-warning)] font-bold">+{activeSimulation.overhead_io_penalty_pct}%</div>
                </div>
                <div>
                  <span className="text-[var(--text-muted)] text-[10px]">Estimated Cost:</span>
                  <div className="text-[var(--text-primary)] font-bold">${activeSimulation.estimated_cost_usd}</div>
                </div>
                <div>
                  <span className="text-[var(--text-muted)] text-[10px]">Safety Envelope:</span>
                  <div className={activeSimulation.safety_envelope_passed ? 'text-[var(--status-success)] font-bold' : 'text-[var(--status-critical)] font-bold'}>
                    {activeSimulation.safety_envelope_passed ? 'PASSED (100%)' : 'VIOLATION'}
                  </div>
                </div>
              </div>

              {/* Assumptions & Model Limitations */}
              <div className="text-[11px] text-[var(--text-secondary)] bg-[var(--surface-secondary)]/40 p-3.5 rounded-xl border border-[var(--border-subtle)] space-y-1.5">
                <div className="text-[var(--text-primary)] font-semibold flex items-center gap-1.5">
                  <Info size={13} className="text-[var(--accent-primary)]" />
                  <span>Simulator Physical Assumptions:</span>
                </div>
                <ul className="list-disc pl-5 space-y-0.5">
                  {activeSimulation.assumptions?.map((asmp: string, idx: number) => (
                    <li key={idx}>{asmp}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
