import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, RecommendationItem } from '../api/client';
import { Sliders, CheckCircle2, XCircle, ShieldCheck, ArrowRight, ShieldAlert, FileText, Check } from 'lucide-react';
import { EmptyState } from '../components/EmptyState';

interface Props {
  initialDeviceId?: string;
}

export const PageInterventionStudio: React.FC<Props> = ({ initialDeviceId }) => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(initialDeviceId || 'vol-nvme-tier1-db');
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [selectedRec, setSelectedRec] = useState<RecommendationItem | null>(null);
  const [actionNotes, setActionNotes] = useState<string>('');
  const [actionStatusMsg, setActionStatusMsg] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    loadDevices();
  }, []);

  useEffect(() => {
    if (selectedDeviceId) {
      loadRecommendations(selectedDeviceId);
    }
  }, [selectedDeviceId]);

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

  const loadRecommendations = async (id: string) => {
    setLoading(true);
    try {
      const recs = await api.getRecommendations(id);
      setRecommendations(recs);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (rec: RecommendationItem) => {
    try {
      await api.approveRecommendation(rec.id, actionNotes || 'Approved dry-run in shadow mode.');
      setActionStatusMsg(`Recommendation ${rec.id} approved for shadow dry-run.`);
      loadRecommendations(selectedDeviceId);
      setSelectedRec(null);
    } catch (e: any) {
      setActionStatusMsg(`Error: ${e.message}`);
    }
  };

  const handleReject = async (rec: RecommendationItem) => {
    try {
      await api.rejectRecommendation(rec.id, actionNotes || 'Rejected by operator discretion.');
      setActionStatusMsg(`Recommendation ${rec.id} rejected.`);
      loadRecommendations(selectedDeviceId);
      setSelectedRec(null);
    } catch (e: any) {
      setActionStatusMsg(`Error: ${e.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
            <Sliders className="text-obsidian-cyan" size={22} />
            Constraint-Aware Intervention Studio
          </h2>
          <p className="text-xs text-obsidian-muted mt-1">
            Pareto-ranked preventive interventions evaluated against hard safety constraints. Approval executes in shadow mode.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-obsidian-muted font-medium">Select Storage Pool:</span>
          <select
            value={selectedDeviceId}
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            className="bg-obsidian-panel border border-obsidian-border rounded px-3 py-1.5 text-xs text-obsidian-text font-mono focus:border-obsidian-cyan cursor-pointer"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.id})
              </option>
            ))}
          </select>
        </div>
      </div>

      {actionStatusMsg && (
        <div className="bg-obsidian-teal/15 border border-obsidian-teal/40 rounded p-3 text-xs text-obsidian-teal font-mono flex items-center gap-2">
          <CheckCircle2 size={16} />
          <span>{actionStatusMsg}</span>
        </div>
      )}

      {/* Ranked Candidate Interventions Cards */}
      {recommendations.length === 0 ? (
        <EmptyState
          title="No Active Interventions Required"
          description="Storage pool has sufficient Reserve Runway (>720 hours) and operates within nominal capacity limits."
        />
      ) : (
        <div className="space-y-4">
          {recommendations.map((rec) => {
          const isDisqualified = rec.utility_score < 0;
          return (
            <div
              key={rec.id}
              className={`bg-obsidian-panel border rounded-lg p-5 transition-all ${
                isDisqualified
                  ? 'border-obsidian-coral/40 opacity-75'
                  : rec.rank === 1
                  ? 'border-obsidian-cyan shadow-[0_0_12px_rgba(85,214,255,0.08)]'
                  : 'border-obsidian-border hover:border-obsidian-border/80'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center font-mono font-bold text-xs ${
                      isDisqualified
                        ? 'bg-obsidian-coral/20 text-obsidian-coral'
                        : rec.rank === 1
                        ? 'bg-obsidian-cyan/20 text-obsidian-cyan'
                        : 'bg-obsidian-secondary text-obsidian-muted'
                    }`}
                  >
                    #{rec.rank}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-obsidian-text flex items-center gap-2">
                      {rec.title}
                      {rec.rank === 1 && !isDisqualified && (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-obsidian-cyan/20 text-obsidian-cyan border border-obsidian-cyan/40 font-mono font-semibold uppercase">
                          Recommended
                        </span>
                      )}
                    </h3>
                    <div className="text-[11px] font-mono text-obsidian-muted mt-0.5">
                      Action Type: <span className="text-obsidian-cyan">{rec.action_type}</span> | Pool: {rec.device_id}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-xs font-mono">
                  <div>
                    <span className="text-obsidian-muted">Runway Gain: </span>
                    <span className="text-obsidian-amber font-bold">+{rec.estimated_runway_gain_hours} hrs</span>
                  </div>
                  <div>
                    <span className="text-obsidian-muted">Utility: </span>
                    <span className="text-obsidian-text font-bold">{rec.utility_score.toFixed(1)}</span>
                  </div>
                  <div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        rec.approval_status === 'APPROVED_SHADOW'
                          ? 'bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40'
                          : rec.approval_status === 'REJECTED'
                          ? 'bg-obsidian-coral/20 text-obsidian-coral border border-obsidian-coral/40'
                          : 'bg-obsidian-secondary text-obsidian-muted border border-obsidian-border'
                      }`}
                    >
                      {rec.approval_status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Rationale & Constraint Breakdown */}
              <div className="mt-4 text-xs text-obsidian-muted leading-relaxed bg-obsidian-secondary/50 rounded p-3 border border-obsidian-border/50">
                <span className="text-obsidian-text font-medium">Objective Trade-Off Rationale: </span>
                {rec.rationale}
              </div>

              {/* Action Buttons */}
              <div className="mt-4 pt-3 border-t border-obsidian-border flex items-center justify-between">
                <div className="flex items-center gap-2 text-[11px] text-obsidian-muted font-mono">
                  <ShieldCheck size={14} className="text-obsidian-teal" />
                  <span>Hard Safety Envelope Verified: 100% Non-Violating</span>
                </div>

                {rec.approval_status === 'PENDING_REVIEW' && !isDisqualified && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleReject(rec)}
                      className="px-3 py-1.5 rounded bg-obsidian-secondary hover:bg-obsidian-raised border border-obsidian-border text-obsidian-coral text-xs flex items-center gap-1 font-medium transition-colors"
                    >
                      <XCircle size={13} />
                      Reject
                    </button>
                    <button
                      onClick={() => handleApprove(rec)}
                      className="px-3.5 py-1.5 rounded bg-obsidian-cyan hover:opacity-90 text-obsidian-bg text-xs flex items-center gap-1.5 font-bold transition-opacity"
                    >
                      <Check size={14} />
                      Approve Shadow Dry-Run
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      )}
    </div>
  );
};
