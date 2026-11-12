import React, { useEffect, useState } from 'react';
import {
  HardDrive, Activity, Bell, CheckSquare, Cpu, TrendingUp,
  RefreshCw, ArrowRight, Database, ShieldCheck, FileText, FlaskConical,
  AlertTriangle, CheckCircle2, UserCheck
} from 'lucide-react';
import { api } from '../api/client';
import { useRealtimeSubscription } from '../context/RealtimeContext';

interface PageOperatorDashboardProps {
  onNavigate: (tab: string, deviceId?: string) => void;
  selectedDeviceId: string;
}

const formatTb = (bytes: number) => `${(bytes / (1024 ** 4)).toFixed(2)} TB`;

export const PageOperatorDashboard: React.FC<PageOperatorDashboardProps> = ({
  onNavigate,
  selectedDeviceId,
}) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [assignInputs, setAssignInputs] = useState<Record<string, string>>({});

  const loadDashboard = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.getOperatorDashboard();
      setData(res);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to load operator operational workspace');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  useRealtimeSubscription(
    ['storage.', 'alert.', 'task.', 'approval.', 'recommendation.', 'model.', 'ingestion.', 'telemetry.'],
    () => {
      loadDashboard();
    },
  );

  const handleAckAlert = async (alertId: string) => {
    try {
      await api.acknowledgeAlert(alertId);
      setActionMsg(`Alert ${alertId} acknowledged.`);
      await loadDashboard();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to acknowledge alert');
    }
  };

  const handleAssignAlert = async (alertId: string) => {
    const assignee = (assignInputs[alertId] || data?.user?.username || '').trim();
    if (!assignee) return;
    try {
      await api.assignAlert(alertId, assignee, 'Assigned from Operator Workspace');
      setActionMsg(`Alert ${alertId} assigned to ${assignee}.`);
      await loadDashboard();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to assign alert');
    }
  };

  const handleEvaluateRisk = async () => {
    try {
      await api.evaluateAlerts();
      setActionMsg('Fleet-wide capacity & SLA risk evaluation completed.');
      await loadDashboard();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to run risk evaluation');
    }
  };

  if (loading && !data) {
    return (
      <div className="p-6 text-xs text-[var(--text-secondary)]">
        Loading Operator operational workspace...
      </div>
    );
  }

  const kpis = data?.kpis || {};
  const resources: any[] = data?.managed_resources || [];
  const collectors: any[] = data?.collectors || [];
  const jobs: any[] = data?.recent_ingestion_jobs || [];
  const models: any[] = data?.ml_models || [];
  const forecasts: any[] = data?.forecasts_summary || [];
  const risks: any[] = data?.capacity_risk_summary || [];
  const alerts: any[] = data?.active_alerts || [];
  const simulations: any[] = data?.recent_simulations || [];
  const recs: any[] = data?.pending_recommendations || [];
  const reports: any[] = data?.recent_reports || [];
  const activities: any[] = data?.recent_operational_activity || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-[var(--accent)]/12 text-[var(--accent)] border border-[var(--accent)]/30">
              {data?.user?.role || 'OPERATOR'} WORKSPACE
            </span>
            <span className="text-[11px] font-mono text-[var(--text-muted)]">
              Signed in as {data?.user?.username || 'operator'}
            </span>
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] mt-1">
            Storage Operations Command Workspace
          </h1>
          <p className="text-xs text-[var(--text-secondary)]">
            Full operational lifecycle: storage registration, telemetry ingestion, quality scoring, ML training, forecasting, risk analysis, Digital Twin simulation, alerts, and reporting.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => onNavigate('devices')}
            className="px-3 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-95"
          >
            + Manage Storage
          </button>
          <button
            type="button"
            onClick={() => onNavigate('ingestion')}
            className="px-3 py-2 rounded-lg text-xs font-semibold border border-[var(--border-strong)] bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)]"
          >
            Ingest Telemetry
          </button>
          <button
            type="button"
            onClick={handleEvaluateRisk}
            className="px-3 py-2 rounded-lg text-xs font-semibold border border-[var(--border-strong)] bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)]"
          >
            Evaluate Fleet Risk
          </button>
          <button
            type="button"
            onClick={loadDashboard}
            className="p-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)]"
            title="Refresh workspace"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-[var(--status-critical)]/10 border border-[var(--status-critical)]/30 text-xs text-[var(--status-critical)]">
          {errorMsg}
        </div>
      )}
      {actionMsg && (
        <div className="p-3 rounded-lg bg-[var(--status-success)]/10 border border-[var(--status-success)]/30 text-xs text-[var(--status-success)] flex items-center justify-between">
          <span>{actionMsg}</span>
          <button type="button" onClick={() => setActionMsg(null)} className="text-[11px] underline">Dismiss</button>
        </div>
      )}

      {/* Top Operational KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)] uppercase font-mono">
            <span>Resources</span>
            <HardDrive size={14} className="text-[var(--accent)]" />
          </div>
          <div className="text-2xl font-bold mt-1">{kpis.managed_storage_count ?? resources.length}</div>
          <button type="button" onClick={() => onNavigate('devices')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            Inventory <ArrowRight size={11} />
          </button>
        </div>

        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)] uppercase font-mono">
            <span>Collectors</span>
            <Database size={14} className="text-[var(--accent)]" />
          </div>
          <div className="text-2xl font-bold mt-1">{kpis.active_collectors_count ?? 0}</div>
          <button type="button" onClick={() => onNavigate('telemetry')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            Telemetry <ArrowRight size={11} />
          </button>
        </div>

        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)] uppercase font-mono">
            <span>Quality Score</span>
            <ShieldCheck size={14} className="text-[var(--status-success)]" />
          </div>
          <div className="text-2xl font-bold mt-1">
            {data?.quality_summary?.avg_reliability_score != null
              ? `${(data.quality_summary.avg_reliability_score * 100).toFixed(1)}%`
              : 'N/A'}
          </div>
          <button type="button" onClick={() => onNavigate('data-quality')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            Inspect <ArrowRight size={11} />
          </button>
        </div>

        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)] uppercase font-mono">
            <span>ML Models</span>
            <Cpu size={14} className="text-[var(--accent)]" />
          </div>
          <div className="text-2xl font-bold mt-1">{kpis.trained_models_count ?? models.length}</div>
          <button type="button" onClick={() => onNavigate('models')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            Model Centre <ArrowRight size={11} />
          </button>
        </div>

        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)] uppercase font-mono">
            <span>Active Alerts</span>
            <Bell size={14} className="text-[var(--status-warning)]" />
          </div>
          <div className="text-2xl font-bold mt-1">{kpis.active_alerts_count ?? alerts.length}</div>
          <button type="button" onClick={() => onNavigate('alerts')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            Alert Centre <ArrowRight size={11} />
          </button>
        </div>

        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)] uppercase font-mono">
            <span>Approvals</span>
            <CheckSquare size={14} className="text-[var(--accent)]" />
          </div>
          <div className="text-2xl font-bold mt-1">{kpis.pending_approvals_count ?? recs.length}</div>
          <button type="button" onClick={() => onNavigate('recommendations')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            Review Queue <ArrowRight size={11} />
          </button>
        </div>
      </div>

      {/* Managed Storage Resources with Direct Workflow Deep Links */}
      <div className="titan-card rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-[var(--text-primary)]">Managed Storage Infrastructure</h2>
            <p className="text-[11px] text-[var(--text-secondary)]">
              Select a storage resource to launch Telemetry, ML Training, Forecast Studio, Risk Analysis, or Digital Twin simulations.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate('devices')}
            className="text-xs font-semibold text-[var(--accent)] hover:underline"
          >
            Open Full Inventory →
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="border-b border-[var(--border-subtle)] text-[10px] font-mono uppercase text-[var(--text-muted)]">
              <tr>
                <th className="py-2 pr-3">Storage Resource</th>
                <th className="py-2 pr-3">Type / Tier</th>
                <th className="py-2 pr-3">Capacity Utilization</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2 pr-3">Last Telemetry</th>
                <th className="py-2 text-right">Workflow Shortcuts</th>
              </tr>
            </thead>
            <tbody>
              {resources.map((r) => {
                const isSelected = r.id === selectedDeviceId;
                return (
                  <tr
                    key={r.id}
                    className={`border-b border-[var(--border-subtle)]/50 ${isSelected ? 'bg-[var(--brand-soft)]/30' : ''}`}
                  >
                    <td className="py-2.5 pr-3">
                      <div className="font-semibold text-[var(--text-primary)]">{r.name}</div>
                      <div className="font-mono text-[10px] text-[var(--text-muted)]">{r.id}</div>
                    </td>
                    <td className="py-2.5 pr-3 font-mono text-[11px]">
                      {r.storage_type} · {r.tier}
                    </td>
                    <td className="py-2.5 pr-3 min-w-[160px]">
                      <div className="flex items-center justify-between text-[11px] font-mono mb-1">
                        <span>{r.utilization_pct.toFixed(1)}%</span>
                        <span className="text-[var(--text-muted)]">
                          {formatTb(r.used_bytes)} / {formatTb(r.total_capacity_bytes)}
                        </span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-[var(--surface-secondary)] overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            r.utilization_pct >= r.critical_threshold_pct
                              ? 'bg-[var(--status-critical)]'
                              : r.utilization_pct >= r.warning_threshold_pct
                              ? 'bg-[var(--status-warning)]'
                              : 'bg-[var(--status-success)]'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(0, r.utilization_pct))}%` }}
                        />
                      </div>
                    </td>
                    <td className="py-2.5 pr-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          r.status === 'CRITICAL'
                            ? 'bg-[var(--status-critical)]/15 text-[var(--status-critical)]'
                            : r.status === 'WARNING'
                            ? 'bg-[var(--status-warning)]/15 text-[var(--status-warning)]'
                            : 'bg-[var(--status-success)]/15 text-[var(--status-success)]'
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 font-mono text-[11px] text-[var(--text-muted)]">
                      {r.last_telemetry_at ? new Date(r.last_telemetry_at).toLocaleString() : 'No samples'}
                    </td>
                    <td className="py-2.5 text-right whitespace-nowrap space-x-1.5">
                      <button type="button" onClick={() => onNavigate('telemetry', r.id)} className="px-2 py-1 rounded text-[11px] border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)]">Telemetry</button>
                      <button type="button" onClick={() => onNavigate('models', r.id)} className="px-2 py-1 rounded text-[11px] border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)]">Train ML</button>
                      <button type="button" onClick={() => onNavigate('forecasts', r.id)} className="px-2 py-1 rounded text-[11px] border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)]">Forecast</button>
                      <button type="button" onClick={() => onNavigate('twin', r.id)} className="px-2 py-1 rounded text-[11px] bg-[var(--accent)]/12 text-[var(--accent)] font-semibold">Twin</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2-Column Operational Queues: Alerts + ML/Forecasts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Active Alerts Queue */}
        <div className="titan-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold flex items-center gap-2">
              <AlertTriangle size={15} className="text-[var(--status-warning)]" />
              Active Alerts & Incident Triage ({alerts.length})
            </h2>
            <button type="button" onClick={() => onNavigate('alerts')} className="text-xs text-[var(--accent)] hover:underline">
              Full Queue →
            </button>
          </div>
          {alerts.length === 0 ? (
            <div className="text-xs text-[var(--text-secondary)] py-4">No active capacity or latency alerts.</div>
          ) : (
            <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
              {alerts.slice(0, 8).map((a) => (
                <div key={a.id} className="p-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-secondary)]/50 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-xs font-semibold text-[var(--text-primary)]">{a.title}</div>
                      <div className="text-[10px] font-mono text-[var(--text-muted)]">
                        {a.device_id} · {a.severity} · {a.status} {a.assigned_to ? `· Owner: ${a.assigned_to}` : ''}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {a.status === 'ACTIVE' && (
                      <button
                        type="button"
                        onClick={() => handleAckAlert(a.id)}
                        className="px-2.5 py-1 rounded text-[11px] font-medium bg-[var(--accent)] text-white"
                      >
                        Acknowledge
                      </button>
                    )}
                    <input
                      type="text"
                      placeholder="Assign username..."
                      value={assignInputs[a.id] ?? ''}
                      onChange={(e) => setAssignInputs((prev) => ({ ...prev, [a.id]: e.target.value }))}
                      className="px-2 py-1 text-[11px] rounded border border-[var(--border-strong)] bg-[var(--surface-primary)] w-32"
                    />
                    <button
                      type="button"
                      onClick={() => handleAssignAlert(a.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] border border-[var(--border-strong)] hover:bg-[var(--surface-primary)]"
                    >
                      <UserCheck size={12} /> Assign
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ML Models, Forecasts & Risk Evaluations */}
        <div className="titan-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold flex items-center gap-2">
              <TrendingUp size={15} className="text-[var(--accent)]" />
              Trained Models & Forecast Threshold Crossings
            </h2>
            <button type="button" onClick={() => onNavigate('forecasts')} className="text-xs text-[var(--accent)] hover:underline">
              Forecast Studio →
            </button>
          </div>
          <div className="space-y-3">
            <div>
              <div className="text-[11px] font-mono uppercase text-[var(--text-muted)] mb-1.5">Recent ML Models</div>
              <div className="space-y-1.5">
                {models.slice(0, 4).map((m) => (
                  <div key={m.id} className="flex items-center justify-between p-2 rounded border border-[var(--border-subtle)] text-xs">
                    <div>
                      <span className="font-semibold">{m.model_type}</span>
                      <span className="ml-2 font-mono text-[10px] text-[var(--text-muted)]">{m.storage_id} · {m.version_tag}</span>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-[11px]">
                      {m.is_active && <span className="px-1.5 py-0.5 rounded bg-[var(--status-success)]/15 text-[var(--status-success)] text-[10px]">ACTIVE</span>}
                      <span>RMSE: {m.rmse != null ? m.rmse.toFixed(3) : 'N/A'}</span>
                    </div>
                  </div>
                ))}
                {models.length === 0 && <div className="text-xs text-[var(--text-muted)]">No trained models persisted yet.</div>}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-mono uppercase text-[var(--text-muted)] mb-1.5">Recent Forecasts & Runway Risk</div>
              <div className="space-y-1.5">
                {forecasts.slice(0, 3).map((f) => (
                  <div key={f.id} className="flex items-center justify-between p-2 rounded border border-[var(--border-subtle)] text-xs">
                    <div>
                      <span className="font-mono font-semibold">{f.device_id}</span>
                      <span className="ml-2 text-[var(--text-muted)]">{f.horizon_days}d · {f.model_name}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                      f.projected_capacity_breach
                        ? 'bg-[var(--status-critical)]/15 text-[var(--status-critical)]'
                        : 'bg-[var(--status-success)]/15 text-[var(--status-success)]'
                    }`}>
                      {f.projected_capacity_breach ? 'BREACH PROJECTED' : 'WITHIN SAFE RUNWAY'}
                    </span>
                  </div>
                ))}
                {risks.slice(0, 2).map((r) => (
                  <div key={r.id} className="flex items-center justify-between p-2 rounded bg-[var(--surface-secondary)]/50 text-xs">
                    <span className="font-mono">{r.storage_id}</span>
                    <span className="font-mono text-[11px]">
                      Risk: <b>{r.risk_level}</b> · Runway: {r.estimated_days_to_threshold?.toFixed(1) ?? 'N/A'}d
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom 3-Column Strip: Collectors/Ingestion, Twin/Recommendations, Reports/Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Collectors & Ingestion Jobs */}
        <div className="titan-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)]">
              Collectors & Ingestion Jobs
            </h3>
            <button type="button" onClick={() => onNavigate('ingestion')} className="text-[11px] text-[var(--accent)] hover:underline">Open Ingestion →</button>
          </div>
          <div className="space-y-2 text-xs">
            {collectors.slice(0, 3).map((c) => (
              <div key={c.id} className="flex items-center justify-between p-2 rounded border border-[var(--border-subtle)]">
                <div>
                  <div className="font-semibold">{c.name}</div>
                  <div className="text-[10px] font-mono text-[var(--text-muted)]">{c.connector_type} · {c.target_storage_id || 'Fleet'}</div>
                </div>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--surface-secondary)]">{c.last_status}</span>
              </div>
            ))}
            {jobs.slice(0, 4).map((j) => (
              <div key={j.id} className="flex items-center justify-between text-[11px] font-mono text-[var(--text-secondary)]">
                <span className="truncate max-w-[160px]">{j.filename || j.source_type}</span>
                <span>+{j.accepted_rows} / -{j.rejected_rows} ({j.status})</span>
              </div>
            ))}
          </div>
        </div>

        {/* Digital Twin & Pending Approvals */}
        <div className="titan-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1.5">
              <FlaskConical size={13} /> Digital Twin & Approvals
            </h3>
            <button type="button" onClick={() => onNavigate('twin')} className="text-[11px] text-[var(--accent)] hover:underline">Run Twin →</button>
          </div>
          <div className="space-y-2 text-xs">
            {simulations.slice(0, 3).map((s) => (
              <div key={s.id} className="p-2 rounded border border-[var(--border-subtle)] flex items-center justify-between">
                <div>
                  <div className="font-semibold">{s.name}</div>
                  <div className="text-[10px] font-mono text-[var(--text-muted)]">{s.device_id} · {s.action_type}</div>
                </div>
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                  s.safety_envelope_passed ? 'bg-[var(--status-success)]/15 text-[var(--status-success)]' : 'bg-[var(--status-critical)]/15 text-[var(--status-critical)]'
                }`}>
                  {s.safety_envelope_passed ? 'SAFE' : 'BLOCKED'}
                </span>
              </div>
            ))}
            {recs.slice(0, 3).map((r) => (
              <div key={r.id} className="p-2 rounded bg-[var(--surface-secondary)]/50 flex items-center justify-between">
                <div className="truncate max-w-[190px]">
                  <div className="font-medium truncate">{r.title}</div>
                  <div className="text-[10px] font-mono text-[var(--text-muted)]">{r.device_id} · {r.approval_status}</div>
                </div>
                <button type="button" onClick={() => onNavigate('recommendations')} className="text-[11px] text-[var(--accent)] font-semibold">Review</button>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Reports & Operational Activity */}
        <div className="titan-card rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1.5">
              <FileText size={13} /> Reports & Operational Activity
            </h3>
            <button type="button" onClick={() => onNavigate('reports')} className="text-[11px] text-[var(--accent)] hover:underline">Reports →</button>
          </div>
          <div className="space-y-2 text-xs">
            {reports.slice(0, 3).map((rp) => (
              <div key={rp.id} className="flex items-center justify-between p-2 rounded border border-[var(--border-subtle)]">
                <span className="font-mono text-[11px]">{rp.report_type} ({rp.format})</span>
                <span className="text-[10px] text-[var(--text-muted)]">{rp.row_count} rows</span>
              </div>
            ))}
            <div className="pt-1 border-t border-[var(--border-subtle)] space-y-1">
              {activities.slice(0, 4).map((act) => (
                <div key={act.id} className="flex items-center justify-between text-[11px] text-[var(--text-secondary)]">
                  <span className="font-mono truncate max-w-[190px]">
                    <CheckCircle2 size={11} className="inline mr-1 text-[var(--status-success)]" />
                    {act.action}
                  </span>
                  <span className="font-mono text-[10px] text-[var(--text-muted)]">{act.user}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
