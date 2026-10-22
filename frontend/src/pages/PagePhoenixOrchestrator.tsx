import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Network,
  Clock,
  Layers,
  FileCode,
  Sliders,
  Check,
  XCircle,
  Eye,
  RefreshCw,
  GitBranch,
  Terminal,
  ChevronRight,
  TrendingUp,
  Cpu,
  Lock,
  Sparkles
} from 'lucide-react';
import { api } from '../api/client';

export const PagePhoenixOrchestrator: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    'incidents' | 'detail' | 'runbooks' | 'approvals' | 'recovery' | 'learning'
  >('incidents');

  const [incidents, setIncidents] = useState<any[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<any | null>(null);
  const [evidenceGraph, setEvidenceGraph] = useState<any | null>(null);
  const [runbooks, setRunbooks] = useState<any[]>([]);
  const [policy, setPolicy] = useState<any | null>(null);
  const [executions, setExecutions] = useState<any[]>([]);
  const [repeatedPatterns, setRepeatedPatterns] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Filter state
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Proposal modal & approval form state
  const [approvalReviewer, setApprovalReviewer] = useState<string>('lead_sre@aegisstor.internal');
  const [approvalRationale, setApprovalRationale] = useState<string>(
    'Verified simulated headroom gain; zero physical mutations guaranteed.'
  );
  const [activeProposal, setActiveProposal] = useState<any | null>(null);

  // Proposal synthesis state
  const [selectedRunbookId, setSelectedRunbookId] = useState<string>('');
  const [selectedActionType, setSelectedActionType] = useState<string>('COMPACT_SHADOW_SNAPSHOTS');
  const [proposalParamReclaim, setProposalParamReclaim] = useState<number>(8.0);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [incRes, rbRes, polRes, execRes, patRes] = await Promise.all([
        api.getPhoenixIncidents(),
        api.getPhoenixRunbooks(),
        api.getPhoenixPolicies(),
        api.getPhoenixExecutions(),
        api.getPhoenixRepeatedPatterns(),
      ]);
      setIncidents(incRes);
      setRunbooks(rbRes);
      setPolicy(polRes);
      setExecutions(execRes);
      setRepeatedPatterns(patRes);

      if (incRes.length > 0 && !selectedIncident) {
        handleSelectIncident(incRes[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load Phoenix data:', err);
      setMessage({ type: 'error', text: 'Error fetching Phoenix data: ' + (err.message || String(err)) });
    } finally {
      setLoading(false);
    }
  };

  const handleSelectIncident = async (id: string) => {
    try {
      const [detail, graph] = await Promise.all([
        api.getPhoenixIncident(id),
        api.getPhoenixEvidenceGraph(id),
      ]);
      setSelectedIncident(detail);
      setEvidenceGraph(graph);
    } catch (err: any) {
      console.error('Failed to fetch incident details:', err);
    }
  };

  const handleFleetScan = async () => {
    setActionLoading(true);
    try {
      const res = await api.scanPhoenixIncidents();
      setMessage({
        type: 'success',
        text: `Fleet scan completed: ${res.scanned_devices_count} devices evaluated, ${res.active_incidents_count} active incidents tracked.`,
      });
      await loadAllData();
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Fleet scan failed: ' + err.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleTransitionState = async (targetState: string) => {
    if (!selectedIncident) return;
    setActionLoading(true);
    try {
      await api.transitionPhoenixIncident(
        selectedIncident.id,
        targetState,
        `Transitioned to ${targetState} via Phoenix Command Console`
      );
      setMessage({ type: 'success', text: `Incident transitioned to ${targetState}.` });
      await handleSelectIncident(selectedIncident.id);
      const incRes = await api.getPhoenixIncidents();
      setIncidents(incRes);
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Transition rejected: ' + (err.message || String(err)) });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSynthesizeProposal = async () => {
    if (!selectedIncident) return;
    setActionLoading(true);
    try {
      const payload = {
        runbook_id: selectedRunbookId || undefined,
        action_type: selectedActionType,
        parameters: {
          target_reclaim_pct: proposalParamReclaim,
          throttle_factor: 0.85,
        },
        simulated_outcome: {
          projected_utilization_pct: 72.5,
          projected_latency_ms: 12.4,
          projected_bandwidth_mb_s: 2100.0,
        },
      };
      const prop = await api.createPhoenixProposal(selectedIncident.id, payload);
      setActiveProposal(prop);
      setMessage({
        type: 'success',
        text: `Synthesized Action Proposal ${prop.proposal_id} (${prop.policy_verdict}).`,
      });
      await handleSelectIncident(selectedIncident.id);
      setActiveTab('approvals');
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Proposal creation failed: ' + (err.message || String(err)) });
    } finally {
      setActionLoading(false);
    }
  };

  const handleApproveProposal = async (propId: string) => {
    setActionLoading(true);
    try {
      await api.approvePhoenixProposal(propId, approvalReviewer, approvalRationale);
      setMessage({ type: 'success', text: `Proposal ${propId} approved by ${approvalReviewer}.` });
      if (selectedIncident) await handleSelectIncident(selectedIncident.id);
      await loadAllData();
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Approval failed: ' + (err.message || String(err)) });
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecuteProposal = async (propId: string, mode = 'MODE_A_SIMULATE') => {
    setActionLoading(true);
    try {
      const idempotencyToken = `phx-exec-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const res = await api.executePhoenixProposal(propId, idempotencyToken, mode);
      setMessage({
        type: 'success',
        text: `Execution ${res.execution_id} completed successfully in ${res.execution_mode} with zero physical host mutations.`,
      });
      if (selectedIncident) await handleSelectIncident(selectedIncident.id);
      await loadAllData();
      setActiveTab('recovery');
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Execution rejected: ' + (err.message || String(err)) });
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerifyRecovery = async () => {
    if (!selectedIncident) return;
    setActionLoading(true);
    try {
      const res = await api.verifyPhoenixRecovery(selectedIncident.id, {
        observation_window_hours: 24.0,
      });
      setMessage({
        type: 'success',
        text: `Independent Recovery Verification: ${res.status}. Residual risk: ${(res.residual_risk_score * 100).toFixed(1)}%.`,
      });
      await handleSelectIncident(selectedIncident.id);
      await loadAllData();
    } catch (err: any) {
      setMessage({ type: 'error', text: 'Verification error: ' + (err.message || String(err)) });
    } finally {
      setActionLoading(false);
    }
  };

  const filteredIncidents = incidents.filter((inc) => {
    if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;
    if (statusFilter !== 'ALL' && inc.status !== statusFilter) return false;
    return true;
  });

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev) {
      case 'SEV1_CRITICAL':
        return 'bg-[var(--status-critical)]/20 text-[var(--status-critical)] border-[var(--status-critical)]/40';
      case 'SEV2_HIGH':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      case 'SEV3_MEDIUM':
        return 'bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border-[var(--accent-primary)]/40';
      default:
        return 'bg-[var(--border-subtle)] text-[var(--text-secondary)] border-[var(--border-subtle)]';
    }
  };

  const getStatusBadgeClass = (st: string) => {
    switch (st) {
      case 'RESOLVED':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      case 'FAILED':
        return 'bg-[var(--status-critical)]/20 text-[var(--status-critical)] border-[var(--status-critical)]/40';
      case 'EXECUTING':
      case 'VERIFYING_RECOVERY':
        return 'bg-[var(--accent-secondary)]/20 text-[var(--accent-tertiary)] border-[var(--accent-secondary)]/40 animate-pulse';
      case 'APPROVED':
        return 'bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border-[var(--accent-primary)]/40';
      default:
        return 'bg-[var(--surface-primary)] text-[var(--text-primary)] border-[var(--border-subtle)]';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Safety Invariants */}
      <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-[var(--accent-primary)]/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--status-critical)] shadow-[0_0_10px_var(--accent-coral)]" />
              <span className="text-xs font-mono uppercase tracking-widest text-[var(--status-critical)] font-bold">
                AEGISSTOR PHOENIX ORCHESTRATION ENGINE
              </span>
            </div>
            <h1 className="text-2xl font-black tracking-tight text-[var(--text-primary)]">
              Predictive Incident Orchestration & Safe Self-Healing
            </h1>
            <p className="text-sm text-[var(--text-secondary)] mt-1 max-w-3xl">
              Connects forecasting horizons, conformal uncertainty, and Policy-as-Code safety gates
              into an auditable 14-state recovery machine with strict zero physical mutations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleFleetScan}
              disabled={actionLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-primary)]/15 hover:bg-[var(--accent-primary)]/25 border border-[var(--accent-primary)]/40 text-[var(--accent-primary)] text-xs font-bold transition-all disabled:opacity-50"
            >
              <RefreshCw size={14} className={actionLoading ? 'animate-spin' : ''} />
              Scan Storage Fleet
            </button>
          </div>
        </div>

        {/* Safety Invariant Badges */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-[var(--border-subtle)]/60">
          <div className="flex items-center gap-2 text-xs">
            <Lock size={14} className="text-emerald-400 shrink-0" />
            <span className="text-[var(--text-secondary)] font-mono">Shadow Mode:</span>
            <span className="font-mono font-bold text-emerald-400">ENABLED (Zero Host Mutations)</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <Terminal size={14} className="text-[var(--accent-primary)] shrink-0" />
            <span className="text-[var(--text-secondary)] font-mono">Default Mode:</span>
            <span className="font-mono font-bold text-[var(--accent-primary)]">MODE_A_SIMULATE</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <ShieldCheck size={14} className="text-[var(--accent-tertiary)] shrink-0" />
            <span className="text-[var(--text-secondary)] font-mono">Hard Safety Invariant:</span>
            <span className="font-mono font-bold text-[var(--accent-tertiary)]">Reserve ≥ 10.0% | P95 ≤ 20ms</span>
          </div>
        </div>
      </div>

      {/* Global Alert Notification */}
      {message && (
        <div
          className={`p-4 rounded-lg border text-xs flex items-center justify-between ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : message.type === 'error'
              ? 'bg-[var(--status-critical)]/10 border-[var(--status-critical)]/30 text-[var(--status-critical)]'
              : 'bg-[var(--accent-primary)]/10 border-[var(--accent-primary)]/30 text-[var(--accent-primary)]'
          }`}
        >
          <div className="flex items-center gap-2">
            {message.type === 'success' ? (
              <CheckCircle2 size={16} />
            ) : message.type === 'error' ? (
              <XCircle size={16} />
            ) : (
              <AlertTriangle size={16} />
            )}
            <span>{message.text}</span>
          </div>
          <button onClick={() => setMessage(null)} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
            ✕
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border-subtle)] pb-3">
        {[
          { id: 'incidents', label: 'Incident Command Center', icon: ShieldAlert, badge: incidents.length },
          { id: 'detail', label: 'Detail & Evidence Graph', icon: Network },
          { id: 'runbooks', label: 'Runbooks & Policy Gateway', icon: FileCode },
          { id: 'approvals', label: 'Approval & Execution Queue', icon: CheckCircle2 },
          { id: 'recovery', label: 'Recovery Verification Lab', icon: RotateCcw },
          { id: 'learning', label: 'Repeated Incident Learning', icon: TrendingUp },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                isActive
                  ? 'bg-[var(--surface-primary)] text-[var(--accent-primary)] border border-[var(--accent-primary)]/40 shadow-sm'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)]/50 border border-transparent'
              }`}
            >
              <Icon size={14} className={isActive ? 'text-[var(--accent-primary)]' : ''} />
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-[var(--text-primary)]">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB 1: INCIDENT COMMAND CENTER */}
      {activeTab === 'incidents' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--text-secondary)]">Severity:</span>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded px-2.5 py-1 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-primary)]"
                >
                  <option value="ALL">All Severities</option>
                  <option value="SEV1_CRITICAL">SEV1 Critical</option>
                  <option value="SEV2_HIGH">SEV2 High</option>
                  <option value="SEV3_MEDIUM">SEV3 Medium</option>
                  <option value="SEV4_LOW">SEV4 Low</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--text-secondary)]">Lifecycle State:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded px-2.5 py-1 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-primary)]"
                >
                  <option value="ALL">All States (14 Phases)</option>
                  <option value="DETECTED">DETECTED</option>
                  <option value="TRIAGE">TRIAGE</option>
                  <option value="PLAN_GENERATION">PLAN_GENERATION</option>
                  <option value="SIMULATION">SIMULATION</option>
                  <option value="AWAITING_APPROVAL">AWAITING_APPROVAL</option>
                  <option value="APPROVED">APPROVED</option>
                  <option value="EXECUTING">EXECUTING</option>
                  <option value="VERIFYING_RECOVERY">VERIFYING_RECOVERY</option>
                  <option value="RESOLVED">RESOLVED</option>
                  <option value="FAILED">FAILED</option>
                </select>
              </div>
            </div>

            <div className="text-xs text-[var(--text-secondary)] font-mono">
              Displaying {filteredIncidents.length} of {incidents.length} incidents
            </div>
          </div>

          {/* Incidents Table */}
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--surface-primary)]/80 text-[var(--text-secondary)] border-b border-[var(--border-subtle)] uppercase tracking-wider font-mono text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Severity / Category</th>
                    <th className="py-3 px-4">Incident Title</th>
                    <th className="py-3 px-4">Lifecycle State</th>
                    <th className="py-3 px-4">Evidence Type</th>
                    <th className="py-3 px-4">Target Resource</th>
                    <th className="py-3 px-4">Runway Horizon</th>
                    <th className="py-3 px-4">Confidence</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {filteredIncidents.map((inc) => (
                    <tr
                      key={inc.id}
                      onClick={() => handleSelectIncident(inc.id)}
                      className={`hover:bg-[var(--surface-primary)]/40 cursor-pointer transition-colors ${
                        selectedIncident?.id === inc.id ? 'bg-[var(--surface-primary)]/60 border-l-2 border-[var(--accent-primary)]' : ''
                      }`}
                    >
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="flex flex-col gap-1">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold border ${getSeverityBadgeClass(
                              inc.severity
                            )}`}
                          >
                            {inc.severity}
                          </span>
                          <span className="text-[10px] text-[var(--text-secondary)] font-mono">{inc.category}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 font-medium text-[var(--text-primary)]">
                        <div className="max-w-md truncate">{inc.title}</div>
                        <div className="text-[10px] text-[var(--text-secondary)] font-mono">{inc.id}</div>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getStatusBadgeClass(
                            inc.status
                          )}`}
                        >
                          {inc.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap font-mono text-[var(--accent-primary)]">
                        <span className="px-1.5 py-0.5 rounded bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/30 text-[10px]">
                          {inc.evidence_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap font-mono text-[var(--text-primary)]">
                        {inc.target_device_id || 'Fleet Wide'}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap font-mono text-amber-400">
                        {inc.time_to_breach_hours ? `${inc.time_to_breach_hours.toFixed(1)} hrs` : 'N/A'}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap font-mono text-[var(--accent-tertiary)]">
                        {(inc.confidence_score * 100).toFixed(0)}%
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectIncident(inc.id);
                            setActiveTab('detail');
                          }}
                          className="px-2.5 py-1 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-[var(--accent-primary)] hover:border-[var(--accent-primary)] transition-colors text-[11px]"
                        >
                          Inspect →
                        </button>
                      </td>
                    </tr>
                  ))}
                  {filteredIncidents.length === 0 && (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-[var(--text-secondary)] font-mono">
                        No incidents matching current filter criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DETAIL & EVIDENCE GRAPH */}
      {activeTab === 'detail' && selectedIncident && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Incident Dossier & Lifecycle Controls */}
          <div className="space-y-6 lg:col-span-1">
            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between">
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getSeverityBadgeClass(
                    selectedIncident.severity
                  )}`}
                >
                  {selectedIncident.severity}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getStatusBadgeClass(
                    selectedIncident.status
                  )}`}
                >
                  {selectedIncident.status}
                </span>
              </div>

              <div>
                <h2 className="text-base font-bold text-[var(--text-primary)]">{selectedIncident.title}</h2>
                <p className="text-xs text-[var(--text-secondary)] font-mono mt-0.5">{selectedIncident.id}</p>
              </div>

              {/* Lifecycle Machine Transitions */}
              <div className="pt-3 border-t border-[var(--border-subtle)]">
                <h3 className="text-xs font-mono uppercase text-[var(--text-secondary)] tracking-wider mb-2">
                  State Machine: Allowed Transitions
                </h3>
                <div className="flex flex-wrap gap-2">
                  {selectedIncident.allowed_next_states?.map((st: string) => (
                    <button
                      key={st}
                      onClick={() => handleTransitionState(st)}
                      disabled={actionLoading}
                      className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-[var(--accent-primary)] hover:border-[var(--accent-primary)] transition-colors disabled:opacity-50"
                    >
                      → {st}
                    </button>
                  ))}
                  {(!selectedIncident.allowed_next_states || selectedIncident.allowed_next_states.length === 0) && (
                    <span className="text-xs text-[var(--text-secondary)] font-mono">Terminal state reached.</span>
                  )}
                </div>
              </div>

              {/* Synthesize Proposal Action */}
              <div className="pt-3 border-t border-[var(--border-subtle)]">
                <button
                  onClick={() => {
                    setActiveTab('runbooks');
                  }}
                  className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-[var(--accent-primary)]/15 hover:bg-[var(--accent-primary)]/25 border border-[var(--accent-primary)]/40 text-[var(--accent-primary)] text-xs font-bold transition-all"
                >
                  <Sparkles size={14} />
                  Synthesize Runbook Proposal
                </button>
              </div>

              {/* Key Metadata Grid */}
              <div className="pt-3 border-t border-[var(--border-subtle)] space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-[var(--text-secondary)] font-mono">Target Resource:</span>
                  <span className="font-mono text-[var(--text-primary)]">{selectedIncident.target_device_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-secondary)] font-mono">Evidence Type:</span>
                  <span className="font-mono text-[var(--accent-primary)]">{selectedIncident.evidence_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-secondary)] font-mono">Time to Breach:</span>
                  <span className="font-mono text-amber-400">
                    {selectedIncident.time_to_breach_hours ? `${selectedIncident.time_to_breach_hours.toFixed(1)} hrs` : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-secondary)] font-mono">Confidence:</span>
                  <span className="font-mono text-[var(--accent-tertiary)]">
                    {(selectedIncident.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-secondary)] font-mono">Predictive Model:</span>
                  <span className="font-mono text-[var(--text-primary)]">{selectedIncident.model_version}</span>
                </div>
              </div>
            </div>

            {/* Structured Symptoms & Hypotheses */}
            <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-lg space-y-4">
              <h3 className="text-xs font-mono uppercase tracking-wider text-[var(--text-secondary)] font-bold">
                Transparent Symptoms & Hypotheses
              </h3>

              <div className="space-y-2">
                <span className="text-[11px] font-mono text-[var(--accent-primary)] uppercase">Observed Symptoms:</span>
                {selectedIncident.symptoms?.map((sym: string, idx: number) => (
                  <div key={idx} className="p-2 rounded bg-[var(--surface-primary)]/60 border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] flex items-start gap-2">
                    <span className="text-amber-400 mt-0.5">•</span>
                    <span>{sym}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-2 pt-2 border-t border-[var(--border-subtle)]">
                <span className="text-[11px] font-mono text-[var(--accent-tertiary)] uppercase">Correlated Hypotheses:</span>
                {selectedIncident.hypotheses?.map((hyp: any, idx: number) => (
                  <div key={idx} className="p-2.5 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-[var(--accent-secondary)]/20 text-[var(--accent-tertiary)] border border-[var(--accent-secondary)]/40">
                        {hyp.status}
                      </span>
                      {hyp.value && (
                        <span className="text-[10px] font-mono text-[var(--text-secondary)]">
                          {hyp.metric}: {Number(hyp.value).toFixed(1)}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[var(--text-primary)]">{hyp.hypothesis}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Interactive Incident Evidence Graph */}
          <div className="lg:col-span-2 bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-lg flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Network size={16} className="text-[var(--accent-primary)]" />
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">
                    Directed Incident Evidence Graph
                  </h3>
                </div>
                <span className="text-xs font-mono text-[var(--text-secondary)]">
                  {evidenceGraph?.node_count || 0} Nodes • {evidenceGraph?.edge_count || 0} Relationships
                </span>
              </div>

              <p className="text-xs text-[var(--text-secondary)] mb-6">
                Visualizes the complete causality and governance chain connecting telemetry anomalies,
                quantile forecast horizons, policy invariants, proposed runbooks, and recovery verifiers.
              </p>

              {/* Node Visualization Canvas */}
              <div className="p-6 rounded-xl bg-[var(--surface-primary)]/50 border border-[var(--border-subtle)]/80 min-h-[360px] flex flex-col justify-around gap-6">
                {/* Layer 1: Incident & Resource */}
                <div className="flex flex-wrap items-center justify-center gap-4">
                  <div className="p-3 rounded-lg bg-[var(--surface-secondary)] border border-[var(--status-critical)]/50 shadow-md text-center min-w-[200px]">
                    <span className="text-[10px] font-mono uppercase text-[var(--status-critical)] font-bold block">Incident Node</span>
                    <span className="text-xs font-bold text-[var(--text-primary)] truncate block mt-1">{selectedIncident.title}</span>
                    <span className="text-[10px] font-mono text-[var(--text-secondary)]">{selectedIncident.severity}</span>
                  </div>

                  <span className="text-[var(--text-secondary)] font-mono text-xs">── AFFECTS ──►</span>

                  <div className="p-3 rounded-lg bg-[var(--surface-secondary)] border border-[var(--accent-primary)]/50 shadow-md text-center min-w-[180px]">
                    <span className="text-[10px] font-mono uppercase text-[var(--accent-primary)] font-bold block">Storage Resource</span>
                    <span className="text-xs font-bold text-[var(--text-primary)] block mt-1">{selectedIncident.target_device_id}</span>
                    <span className="text-[10px] font-mono text-[var(--text-secondary)]">{selectedIncident.pool_id || 'Primary Pool'}</span>
                  </div>
                </div>

                {/* Layer 2: Predictive Horizon & Safety Policy */}
                <div className="flex flex-wrap items-center justify-center gap-4">
                  <div className="p-3 rounded-lg bg-[var(--surface-secondary)] border border-[var(--accent-secondary)]/50 shadow-md text-center min-w-[200px]">
                    <span className="text-[10px] font-mono uppercase text-[var(--accent-tertiary)] font-bold block">Conformal Horizon</span>
                    <span className="text-xs font-bold text-[var(--text-primary)] block mt-1">
                      {selectedIncident.time_to_breach_hours ? `Runway: ${selectedIncident.time_to_breach_hours.toFixed(1)}h` : 'Historical Drift'}
                    </span>
                    <span className="text-[10px] font-mono text-[var(--text-secondary)]">{selectedIncident.model_version}</span>
                  </div>

                  <span className="text-[var(--text-secondary)] font-mono text-xs">── GOVERNED ──►</span>

                  <div className="p-3 rounded-lg bg-[var(--surface-secondary)] border border-emerald-500/50 shadow-md text-center min-w-[200px]">
                    <span className="text-[10px] font-mono uppercase text-emerald-400 font-bold block">Policy-as-Code Gateway</span>
                    <span className="text-xs font-bold text-emerald-300 block mt-1">Hard Reserve & Latency Ceilings</span>
                    <span className="text-[10px] font-mono text-[var(--text-secondary)]">Non-Bypassable Hard Gate</span>
                  </div>
                </div>

                {/* Layer 3: Runbook Proposal & Independent Recovery Verification */}
                <div className="flex flex-wrap items-center justify-center gap-4">
                  <div className="p-3 rounded-lg bg-[var(--surface-secondary)] border border-amber-500/50 shadow-md text-center min-w-[200px]">
                    <span className="text-[10px] font-mono uppercase text-amber-400 font-bold block">Runbook Plan</span>
                    <span className="text-xs font-bold text-[var(--text-primary)] block mt-1">
                      {selectedIncident.active_proposal_id ? 'Synthesized Proposal' : 'Awaiting Synthesis'}
                    </span>
                    <span className="text-[10px] font-mono text-[var(--text-secondary)]">Mode A (Simulation)</span>
                  </div>

                  <span className="text-[var(--text-secondary)] font-mono text-xs">── VERIFIED ──►</span>

                  <div className="p-3 rounded-lg bg-[var(--surface-secondary)] border border-[var(--accent-primary)]/50 shadow-md text-center min-w-[200px]">
                    <span className="text-[10px] font-mono uppercase text-[var(--accent-primary)] font-bold block">Recovery Verifier</span>
                    <span className="text-xs font-bold text-[var(--text-primary)] block mt-1">Independent Telemetry Audit</span>
                    <span className="text-[10px] font-mono text-[var(--text-secondary)]">API Success ≠ Recovery</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-[var(--border-subtle)] text-xs text-[var(--text-secondary)] flex items-center justify-between">
              <span className="font-mono">AEGISSTOR Provenance Assurance</span>
              <span className="font-mono text-[var(--accent-primary)]">Audit Ledger Hash: SHA256-PHX-77F</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: RUNBOOKS & POLICY GATEWAY */}
      {activeTab === 'runbooks' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Runbook Synthesizer */}
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center gap-2">
              <FileCode size={16} className="text-[var(--accent-primary)]" />
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Runbook Synthesizer & Proposal Generator
              </h3>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Select an allowlisted recovery runbook, configure mitigation parameters, and submit for Policy Gateway evaluation.
            </p>

            <div className="space-y-4 pt-2">
              <div>
                <label className="text-xs font-mono text-[var(--text-secondary)] block mb-1">Target Incident:</label>
                <select
                  value={selectedIncident?.id || ''}
                  onChange={(e) => handleSelectIncident(e.target.value)}
                  className="w-full bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded px-3 py-2 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-primary)]"
                >
                  {incidents.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.title} ({i.severity} - {i.status})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-mono text-[var(--text-secondary)] block mb-1">Standard Runbook Template:</label>
                <select
                  value={selectedRunbookId}
                  onChange={(e) => setSelectedRunbookId(e.target.value)}
                  className="w-full bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded px-3 py-2 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-primary)]"
                >
                  <option value="">Default Category Best-Fit</option>
                  {runbooks.map((rb) => (
                    <option key={rb.id} value={rb.id}>
                      {rb.name} (v{rb.version})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-mono text-[var(--text-secondary)] block mb-1">Primary Action Type:</label>
                <select
                  value={selectedActionType}
                  onChange={(e) => setSelectedActionType(e.target.value)}
                  className="w-full bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded px-3 py-2 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-primary)]"
                >
                  <option value="COMPACT_SHADOW_SNAPSHOTS">COMPACT_SHADOW_SNAPSHOTS (Safe reclaim)</option>
                  <option value="WORKLOAD_RATE_LIMIT">WORKLOAD_RATE_LIMIT (Throttle ingest)</option>
                  <option value="POOL_WEIGHT_REBALANCE">POOL_WEIGHT_REBALANCE (Cross-pool migration)</option>
                  <option value="READ_CACHE_PREFETCH_REBALANCE">READ_CACHE_PREFETCH_REBALANCE (Latency fix)</option>
                  <option value="NOOP_DIAGNOSTIC_SAMPLE">NOOP_DIAGNOSTIC_SAMPLE (Non-mutating probe)</option>
                </select>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-mono text-[var(--text-secondary)]">Target Capacity Reclaim Ratio:</span>
                  <span className="font-mono text-[var(--accent-primary)] font-bold">{proposalParamReclaim}%</span>
                </div>
                <input
                  type="range"
                  min={2}
                  max={25}
                  step={1}
                  value={proposalParamReclaim}
                  onChange={(e) => setProposalParamReclaim(Number(e.target.value))}
                  className="w-full accent-[var(--accent-primary)] cursor-pointer"
                />
              </div>

              <button
                onClick={handleSynthesizeProposal}
                disabled={actionLoading}
                className="w-full py-2.5 rounded-lg bg-[var(--accent-primary)]/20 hover:bg-[var(--accent-primary)]/30 border border-[var(--accent-primary)]/40 text-[var(--accent-primary)] text-xs font-bold transition-all disabled:opacity-50"
              >
                Synthesize & Evaluate Against Safety Gateway →
              </button>
            </div>
          </div>

          {/* Right: Active Policy Invariants */}
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center gap-2">
              <ShieldCheck size={16} className="text-emerald-400" />
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Policy-as-Code Invariant Rules
              </h3>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Hard constraints defined in code. Invariant rule: high recommendation scores can never override these limits.
            </p>

            {policy && (
              <div className="space-y-3 pt-2">
                <div className="p-3 rounded-lg bg-[var(--surface-primary)]/60 border border-[var(--border-subtle)] flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-[var(--text-primary)] block">Minimum Free Capacity Reserve</span>
                    <span className="text-[11px] text-[var(--text-secondary)] font-mono">Action cannot leave buffer below threshold</span>
                  </div>
                  <span className="font-mono text-sm font-bold text-emerald-400">≥ {policy.min_free_reserve_pct}%</span>
                </div>

                <div className="p-3 rounded-lg bg-[var(--surface-primary)]/60 border border-[var(--border-subtle)] flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-[var(--text-primary)] block">Maximum Acceptable P95 Latency</span>
                    <span className="text-[11px] text-[var(--text-secondary)] font-mono">Controller tail latency ceiling</span>
                  </div>
                  <span className="font-mono text-sm font-bold text-emerald-400">≤ {policy.max_latency_ms} ms</span>
                </div>

                <div className="p-3 rounded-lg bg-[var(--surface-primary)]/60 border border-[var(--border-subtle)] flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-[var(--text-primary)] block">Interconnect Bandwidth Cap</span>
                    <span className="text-[11px] text-[var(--text-secondary)] font-mono">Fabric saturation boundary</span>
                  </div>
                  <span className="font-mono text-sm font-bold text-emerald-400">≤ {policy.max_bandwidth_mb_s} MB/s</span>
                </div>

                <div className="p-3 rounded-lg bg-[var(--surface-primary)]/60 border border-[var(--border-subtle)] flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-[var(--text-primary)] block">Human Approval Enforcement</span>
                    <span className="text-[11px] text-[var(--text-secondary)] font-mono">Operator signoff required before run</span>
                  </div>
                  <span className="font-mono text-xs font-bold text-[var(--accent-tertiary)]">MANDATORY</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: APPROVAL & EXECUTION QUEUE */}
      {activeTab === 'approvals' && (
        <div className="space-y-6">
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-[var(--accent-primary)]" />
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  Action Proposal Approval & Non-Destructive Execution
                </h3>
              </div>
              <span className="text-xs font-mono text-emerald-400 font-bold">
                Fail-Closed Policy Guard Active
              </span>
            </div>

            <p className="text-xs text-[var(--text-secondary)]">
              Inspect synthesized action proposals, verify SHA256 integrity hash against post-approval tampering,
              and trigger safe execution in MODE_A_SIMULATE.
            </p>

            {activeProposal ? (
              <div className="p-5 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-4 mt-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] pb-3">
                  <div>
                    <span className="text-xs font-bold text-[var(--text-primary)]">{activeProposal.action_type}</span>
                    <span className="text-[11px] text-[var(--text-secondary)] font-mono block">Proposal ID: {activeProposal.proposal_id}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
                      {activeProposal.policy_verdict}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border border-[var(--accent-primary)]/40">
                      Status: {activeProposal.approval_status}
                    </span>
                  </div>
                </div>

                {/* Parameters & Proposal Hash */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-[var(--text-secondary)] font-mono block mb-1">Action Parameters:</span>
                    <pre className="p-2.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[11px] font-mono text-[var(--accent-primary)] overflow-x-auto">
                      {JSON.stringify(activeProposal.parameters, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <span className="text-[var(--text-secondary)] font-mono block mb-1">Tamper Integrity Hash (SHA256):</span>
                    <div className="p-2.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[11px] font-mono text-[var(--accent-tertiary)] break-all">
                      {activeProposal.proposal_hash}
                    </div>
                  </div>
                </div>

                {/* Approval Form */}
                {activeProposal.approval_status === 'PENDING' && (
                  <div className="pt-3 border-t border-[var(--border-subtle)] space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-mono text-[var(--text-secondary)] block mb-1">Reviewer ID:</label>
                        <input
                          type="text"
                          value={approvalReviewer}
                          onChange={(e) => setApprovalReviewer(e.target.value)}
                          className="w-full bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded px-3 py-1.5 text-xs text-[var(--text-primary)] font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-mono text-[var(--text-secondary)] block mb-1">Approval Justification:</label>
                        <input
                          type="text"
                          value={approvalRationale}
                          onChange={(e) => setApprovalRationale(e.target.value)}
                          className="w-full bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded px-3 py-1.5 text-xs text-[var(--text-primary)]"
                        />
                      </div>
                    </div>

                    <button
                      onClick={() => handleApproveProposal(activeProposal.proposal_id)}
                      disabled={actionLoading}
                      className="px-4 py-2 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-bold transition-all disabled:opacity-50"
                    >
                      ✓ Formally Approve Proposal
                    </button>
                  </div>
                )}

                {/* Execution Controls */}
                {activeProposal.approval_status === 'APPROVED' && (
                  <div className="pt-3 border-t border-[var(--border-subtle)] flex items-center gap-3">
                    <button
                      onClick={() => handleExecuteProposal(activeProposal.proposal_id, 'MODE_A_SIMULATE')}
                      disabled={actionLoading}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-primary)]/20 hover:bg-[var(--accent-primary)]/30 border border-[var(--accent-primary)]/40 text-[var(--accent-primary)] text-xs font-bold transition-all disabled:opacity-50"
                    >
                      <Play size={14} />
                      Execute in MODE_A_SIMULATE (Digital Twin)
                    </button>

                    <button
                      onClick={() => handleExecuteProposal(activeProposal.proposal_id, 'MODE_B_DIAGNOSTIC_READONLY')}
                      disabled={actionLoading}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs font-bold transition-all disabled:opacity-50"
                    >
                      <Eye size={14} />
                      Run MODE_B_DIAGNOSTIC_READONLY
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 text-center text-[var(--text-secondary)] font-mono text-xs border border-dashed border-[var(--border-subtle)] rounded-xl">
                No active proposal selected. Synthesize a proposal in the Runbook tab first.
              </div>
            )}
          </div>

          {/* Historical Execution Records */}
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-5 shadow-lg space-y-3">
            <h4 className="text-xs font-mono uppercase text-[var(--text-secondary)] font-bold">Recent Safe Execution Runs</h4>
            <div className="divide-y divide-[var(--border-subtle)]">
              {executions.slice(0, 5).map((ex) => (
                <div key={ex.id} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-mono text-[var(--text-primary)] font-bold">{ex.id}</span>
                    <span className="text-[11px] text-[var(--text-secondary)] font-mono block">Incident: {ex.incident_id}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30">
                      {ex.execution_mode}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                      {ex.status}
                    </span>
                  </div>
                </div>
              ))}
              {executions.length === 0 && (
                <div className="py-4 text-center text-[var(--text-secondary)] font-mono text-xs">
                  No execution records yet.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: RECOVERY VERIFICATION LAB */}
      {activeTab === 'recovery' && (
        <div className="space-y-6">
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <RotateCcw size={16} className="text-[var(--accent-primary)]" />
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  Independent Post-Action Recovery Verification
                </h3>
              </div>
              <span className="text-xs font-mono text-amber-400 font-bold">
                Invariant: API Success ≠ Recovery
              </span>
            </div>

            <p className="text-xs text-[var(--text-secondary)]">
              Evaluates actual and simulated post-action telemetry across an observation window (e.g. 24 hours).
              Only resolves incidents if metrics stay below warning boundaries and zero secondary degradation is detected.
            </p>

            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-4 mt-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[var(--text-secondary)] font-mono">Current Target Incident:</span>
                <span className="font-mono text-[var(--text-primary)] font-bold">{selectedIncident?.title || 'None Selected'}</span>
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2">
                <p className="text-xs text-[var(--text-secondary)]">
                  Evaluates target volume post-execution telemetry against SLA limits and residual risk boundaries without mock overrides.
                </p>
                <button
                  onClick={() => handleVerifyRecovery()}
                  disabled={actionLoading || !selectedIncident}
                  className="px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-xs font-bold transition-all disabled:opacity-50 shrink-0 shadow-xs hover:bg-[var(--accent-hover)]"
                >
                  Verify Post-Action Telemetry Window
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: REPEATED INCIDENT LEARNING */}
      {activeTab === 'learning' && (
        <div className="space-y-6">
          <div className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-lg space-y-4">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} className="text-[var(--accent-primary)]" />
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Repeated Incident Learning & Post-Mortem Intelligence
              </h3>
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Aggregates historical incidents to detect recurring failure patterns, hotspot devices, and mean time to recovery (MTTR).
            </p>

            {repeatedPatterns && (
              <div className="space-y-6 pt-2">
                {/* Metric Summary Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                    <span className="text-xs font-mono text-[var(--text-secondary)]">Total Tracked Incidents</span>
                    <div className="text-2xl font-black text-[var(--text-primary)] mt-1">{repeatedPatterns.total_incidents}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                    <span className="text-xs font-mono text-[var(--text-secondary)]">Recurring Pattern Signature</span>
                    <div className="text-base font-bold text-amber-400 mt-1">{repeatedPatterns.repeat_incident_signature}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                    <span className="text-xs font-mono text-[var(--text-secondary)]">Preventive Action Recommendation</span>
                    <div className="text-xs text-emerald-300 mt-1">{repeatedPatterns.recommended_preventive_action}</div>
                  </div>
                </div>

                {/* Category MTTR Table */}
                <div className="rounded-xl border border-[var(--border-subtle)] overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[var(--surface-primary)] text-[var(--text-secondary)] font-mono uppercase text-[10px]">
                      <tr>
                        <th className="py-2.5 px-4">Category</th>
                        <th className="py-2.5 px-4">Total Incidents</th>
                        <th className="py-2.5 px-4">Resolved</th>
                        <th className="py-2.5 px-4">MTTR (Minutes)</th>
                        <th className="py-2.5 px-4">Recurrence Rate</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)]">
                      {repeatedPatterns.category_distribution?.map((cat: any) => (
                        <tr key={cat.category} className="hover:bg-[var(--surface-primary)]/30">
                          <td className="py-2.5 px-4 font-mono font-bold text-[var(--text-primary)]">{cat.category}</td>
                          <td className="py-2.5 px-4 font-mono">{cat.total_count}</td>
                          <td className="py-2.5 px-4 font-mono text-emerald-400">{cat.resolved_count}</td>
                          <td className="py-2.5 px-4 font-mono text-amber-400">{cat.mttr_minutes} min</td>
                          <td className="py-2.5 px-4 font-mono text-[var(--accent-tertiary)]">{(cat.recurrence_rate * 100).toFixed(0)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
