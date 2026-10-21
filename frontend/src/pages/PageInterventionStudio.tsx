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
  HelpCircle,
  RotateCcw,
  Check,
  Info
} from 'lucide-react';
import { EmptyState } from '../components/EmptyState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

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

  useEffect(() => {
    loadDevices();
  }, []);

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
      setActionStatusMsg(`Recommendation ${recId} approved for shadow dry-run.`);
      loadDeviceIntelligence(selectedDeviceId);
    } catch (e: any) {
      setActionStatusMsg(`Error: ${e.message}`);
    }
  };

  const handleReject = async (recId: string) => {
    try {
      await api.rejectRecommendation(recId, actionNotes || 'Rejected by operator discretion.');
      setActionStatusMsg(`Recommendation ${recId} rejected.`);
      loadDeviceIntelligence(selectedDeviceId);
    } catch (e: any) {
      setActionStatusMsg(`Error: ${e.message}`);
    }
  };

  const selectedDevice = devices.find((d) => d.id === selectedDeviceId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
              <Sliders className="text-obsidian-cyan" size={22} />
              Counterfactual Intervention Studio
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-obsidian-teal/15 text-obsidian-teal border border-obsidian-teal/40">
              SHADOW MODE: SAFE
            </span>
          </div>
          <p className="text-xs text-obsidian-muted mt-1 leading-relaxed">
            Lead-time-aware preventive action planning. Evaluates whether candidate interventions can complete before predicted capacity or latency SLA breach.
          </p>
        </div>

        {/* Storage Pool Selector & Horizon */}
        <div className="flex items-center gap-3">
          <select
            value={selectedDeviceId}
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            className="bg-obsidian-panel border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text font-mono focus:border-obsidian-cyan cursor-pointer"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.tier})
              </option>
            ))}
          </select>
        </div>
      </div>

      {actionStatusMsg && (
        <div className="bg-obsidian-teal/15 border border-obsidian-teal/40 rounded-lg p-3 text-xs text-obsidian-teal font-mono flex items-center gap-2">
          <CheckCircle2 size={16} />
          <span>{actionStatusMsg}</span>
        </div>
      )}

      {loading ? (
        <LoadingSkeleton />
      ) : (
        <>
          {/* STEP 1 & 2: Risk Breach Diagnostic Banner */}
          {runwayData && (
            <div className={`p-4 rounded-xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
              runwayData.estimated_runway_hours <= 48
                ? 'bg-obsidian-coral/10 border-obsidian-coral/40 text-obsidian-text'
                : runwayData.estimated_runway_hours <= 96
                ? 'bg-obsidian-amber/10 border-obsidian-amber/40 text-obsidian-text'
                : 'bg-obsidian-panel border-obsidian-border text-obsidian-text'
            }`}>
              <div className="flex items-start gap-3">
                <AlertTriangle
                  size={20}
                  className={runwayData.estimated_runway_hours <= 48 ? 'text-obsidian-coral mt-0.5' : 'text-obsidian-amber mt-0.5'}
                />
                <div>
                  <div className="text-xs font-bold flex items-center gap-2">
                    <span>Projected Reserve Breach Horizon:</span>
                    <span className="font-mono text-obsidian-cyan">
                      ~{runwayData.estimated_runway_hours.toFixed(1)} hours
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-obsidian-surface border border-obsidian-border text-obsidian-muted">
                      {runwayData.breach_status}
                    </span>
                  </div>
                  <p className="text-[11px] text-obsidian-muted mt-1 leading-relaxed">
                    Under current write growth (+{runwayData.growth_rate_daily_gb} GB/day), free reserve drops below {runwayData.configured_critical_threshold_pct}% critical threshold.
                    Sensitivity range: <span className="font-mono text-obsidian-text">[{runwayData.sensitivity_pessimistic_hours}h pessimistic .. {runwayData.sensitivity_optimistic_hours}h optimistic]</span>.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono shrink-0">
                <div className="px-3 py-1.5 rounded bg-obsidian-panel border border-obsidian-border text-center">
                  <div className="text-[10px] text-obsidian-muted">Usable Capacity</div>
                  <div className="font-bold text-obsidian-text">
                    {(runwayData.total_capacity_bytes / 1e12).toFixed(1)} TB
                  </div>
                </div>
                <div className="px-3 py-1.5 rounded bg-obsidian-panel border border-obsidian-border text-center">
                  <div className="text-[10px] text-obsidian-muted">Current Util</div>
                  <div className={`font-bold ${runwayData.current_utilization_pct > 80 ? 'text-obsidian-coral' : 'text-obsidian-text'}`}>
                    {runwayData.current_utilization_pct}%
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3 & 4: Action Candidates Matrix (Feasible vs Disqualified) */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-obsidian-text flex items-center gap-2">
                <span>Feasible Preventive Candidates</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-cyan/15 text-obsidian-cyan border border-obsidian-cyan/30">
                  {planningData?.feasible_candidates?.length || 0} FEASIBLE
                </span>
              </h3>
              <span className="text-[11px] text-obsidian-muted">
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
                    className={`bg-obsidian-panel border rounded-xl p-4 cursor-pointer transition-all ${
                      isSelected
                        ? 'border-obsidian-cyan shadow-[0_0_15px_rgba(85,214,255,0.12)] bg-obsidian-raised'
                        : 'border-obsidian-border hover:border-obsidian-cyan/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-obsidian-cyan/20 text-obsidian-cyan border border-obsidian-cyan/40">
                        RANK #{candidate.rank}
                      </span>
                      <span className="text-xs font-mono font-bold text-obsidian-teal">
                        Score: {candidate.utility_score}
                      </span>
                    </div>

                    <h4 className="text-xs font-bold text-obsidian-text mt-2.5 line-clamp-1">
                      {candidate.title}
                    </h4>
                    <p className="text-[11px] text-obsidian-muted mt-1 line-clamp-2">
                      {candidate.description}
                    </p>

                    <div className="mt-3 pt-3 border-t border-obsidian-border/60 grid grid-cols-2 gap-2 text-[10px] font-mono">
                      <div>
                        <span className="text-obsidian-muted">Runway Gain:</span>
                        <div className="text-obsidian-amber font-bold">+{candidate.estimated_runway_gain_hours} hrs</div>
                      </div>
                      <div>
                        <span className="text-obsidian-muted">Action Duration:</span>
                        <div className="text-obsidian-text font-bold">{candidate.estimated_duration_hours} hrs</div>
                      </div>
                      <div>
                        <span className="text-obsidian-muted">Contention:</span>
                        <div className={candidate.io_overhead_pct > 15 ? 'text-obsidian-coral' : 'text-obsidian-teal'}>
                          {candidate.io_overhead_pct > 0 ? `+${candidate.io_overhead_pct}%` : `${candidate.io_overhead_pct}%`}
                        </div>
                      </div>
                      <div>
                        <span className="text-obsidian-muted">Estimated Cost:</span>
                        <div className="text-obsidian-text font-bold">${candidate.estimated_cost_usd}</div>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center justify-between pt-2 border-t border-obsidian-border/40">
                      <span className="text-[9px] font-mono text-obsidian-teal flex items-center gap-1">
                        <CheckCircle2 size={11} />
                        Prerequisites Satisfied
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleApprove(candidate.id);
                        }}
                        className="px-2.5 py-1 bg-obsidian-cyan text-obsidian-bg rounded text-[10px] font-bold hover:opacity-90 transition-opacity"
                      >
                        Approve
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Disqualified Candidates Section */}
            {planningData?.rejected_candidates?.length > 0 && (
              <div className="mt-4 p-4 rounded-xl bg-obsidian-panel/60 border border-obsidian-coral/30 space-y-3">
                <div className="text-xs font-bold text-obsidian-coral flex items-center gap-2">
                  <XCircle size={15} />
                  <span>Disqualified Candidate Actions (Hard Safety Envelope Rejections)</span>
                </div>
                <div className="space-y-2">
                  {planningData.rejected_candidates.map((rej: any) => (
                    <div
                      key={rej.id}
                      className="text-xs p-2.5 rounded bg-obsidian-secondary/60 border border-obsidian-border/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                    >
                      <div>
                        <span className="font-semibold text-obsidian-text">{rej.title}: </span>
                        <span className="text-obsidian-muted">{rej.rejection_reason}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-obsidian-coral/20 text-obsidian-coral border border-obsidian-coral/40 shrink-0">
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
            <div className="bg-obsidian-panel border border-obsidian-border rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-obsidian-text flex items-center gap-2">
                    <Activity size={16} className="text-obsidian-cyan" />
                    <span>Side-by-Side Scenario Trajectory</span>
                  </h3>
                  <p className="text-[11px] text-obsidian-muted mt-0.5">
                    Comparing Baseline organic growth (Do Nothing) versus {activeSimulation.action_type}.
                  </p>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono">
                  <span className="flex items-center gap-1.5 text-obsidian-muted">
                    <span className="w-3 h-0.5 bg-obsidian-muted inline-block"></span>
                    Baseline (Do Nothing)
                  </span>
                  <span className="flex items-center gap-1.5 text-obsidian-cyan font-bold">
                    <span className="w-3 h-0.5 bg-obsidian-cyan inline-block"></span>
                    Counterfactual Trajectory
                  </span>
                </div>
              </div>

              {/* Trajectory Key Metrics Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-obsidian-secondary p-3 rounded-lg text-xs font-mono">
                <div>
                  <span className="text-obsidian-muted text-[10px]">Action Duration:</span>
                  <div className="text-obsidian-text font-bold">{activeSimulation.duration_minutes} min</div>
                </div>
                <div>
                  <span className="text-obsidian-muted text-[10px]">I/O Contention:</span>
                  <div className="text-obsidian-amber font-bold">+{activeSimulation.overhead_io_penalty_pct}%</div>
                </div>
                <div>
                  <span className="text-obsidian-muted text-[10px]">Estimated Cost:</span>
                  <div className="text-obsidian-text font-bold">${activeSimulation.estimated_cost_usd}</div>
                </div>
                <div>
                  <span className="text-obsidian-muted text-[10px]">Safety Envelope:</span>
                  <div className={activeSimulation.safety_envelope_passed ? 'text-obsidian-teal font-bold' : 'text-obsidian-coral font-bold'}>
                    {activeSimulation.safety_envelope_passed ? 'PASSED (100%)' : 'VIOLATION'}
                  </div>
                </div>
              </div>

              {/* Assumptions & Model Limitations */}
              <div className="text-[11px] text-obsidian-muted bg-obsidian-secondary/50 p-3 rounded-lg border border-obsidian-border/40 space-y-1">
                <div className="text-obsidian-text font-semibold flex items-center gap-1.5">
                  <Info size={13} className="text-obsidian-cyan" />
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
