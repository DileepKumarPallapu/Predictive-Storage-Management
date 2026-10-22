import React, { useState, useEffect } from 'react';
import { api, AlertItem } from '../api/client';
import { AlertTriangle, CheckCircle2, ShieldAlert, Check, X, Filter, Sparkles, ArrowRight } from 'lucide-react';
import { EmptyState } from '../components/EmptyState';
import { usePresentationMode } from '../context/PresentationModeContext';

export const PageAlertsIncidents: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const { isGuided } = usePresentationMode();

  useEffect(() => {
    loadAlerts();
  }, [categoryFilter, statusFilter]);

  const loadAlerts = async () => {
    try {
      const data = await api.getAlerts(categoryFilter || undefined, undefined, statusFilter || undefined);
      setAlerts(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (id: string) => {
    try {
      await api.acknowledgeAlert(id);
      loadAlerts();
    } catch (e) {
      console.error(e);
    }
  };

  const handleResolve = async (id: string) => {
    try {
      await api.resolveAlert(id);
      loadAlerts();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--status-critical)]/15 border border-[var(--status-critical)]/30 flex items-center justify-center text-[var(--status-critical)] shadow-[0_0_12px_rgba(255,120,141,0.2)]">
            <AlertTriangle size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            {isGuided ? 'Alerts, Notifications & Action Guide' : 'Alerts, Incidents & Operational Safeguards'}
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          {isGuided
            ? 'Proactive notices explaining what happened, why it matters, and what you can do next.'
            : 'Proactive notifications generated when risk envelopes or telemetry quality boundaries are approached.'}
        </p>
      </div>

      {/* Filter Bar */}
      <div className="titan-card rounded-lg p-3.5 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2 text-xs">
          <Filter size={14} className="text-[var(--text-muted)]" />
          <span className="text-[var(--text-secondary)] font-medium">Category:</span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none cursor-pointer"
            aria-label="Category Filter"
          >
            <option value="" className="bg-[var(--surface-primary)]">All Categories</option>
            <option value="CAPACITY_RISK" className="bg-[var(--surface-primary)]">Capacity Shortage Risk</option>
            <option value="PERFORMANCE_RISK" className="bg-[var(--surface-primary)]">Latency SLA Risk</option>
            <option value="DATA_QUALITY" className="bg-[var(--surface-primary)]">Data Quality / Dropout</option>
            <option value="MODEL_DRIFT" className="bg-[var(--surface-primary)]">Workload Pattern Shift</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-[var(--text-secondary)] font-medium">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none cursor-pointer"
            aria-label="Status Filter"
          >
            <option value="" className="bg-[var(--surface-primary)]">All Statuses</option>
            <option value="ACTIVE" className="bg-[var(--surface-primary)]">Active</option>
            <option value="ACKNOWLEDGED" className="bg-[var(--surface-primary)]">Acknowledged</option>
            <option value="RESOLVED" className="bg-[var(--surface-primary)]">Resolved</option>
          </select>
        </div>
      </div>

      {/* Alerts List */}
      {alerts.length === 0 ? (
        <EmptyState
          title="No Active Alerts or Incidents"
          description="All monitored pools are operating within the Hard Safety Envelope. Telemetry quality is nominal."
        />
      ) : (
        <div className="space-y-4">
          {alerts.map((a) => (
            <div
              key={a.id}
              className={`titan-card rounded-lg p-5 transition-all ${
                a.status === 'ACTIVE'
                  ? a.severity === 'CRITICAL'
                    ? 'border-[var(--status-critical)]/50 shadow-[0_0_12px_rgba(255,120,141,0.15)]'
                    : 'border-[var(--status-warning)]/50 shadow-[0_0_12px_rgba(255,208,128,0.12)]'
                  : 'opacity-70'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="flex items-start gap-3.5 flex-1">
                  <span className="mt-0.5 shrink-0">
                    {a.severity === 'CRITICAL' ? (
                      <ShieldAlert size={20} className="text-[var(--status-critical)]" />
                    ) : (
                      <AlertTriangle size={20} className="text-[var(--status-warning)]" />
                    )}
                  </span>
                  <div className="space-y-3 flex-1">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-bold text-[var(--text-primary)]">{a.title}</h3>
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[var(--accent-primary)]">
                          {a.category}
                        </span>
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">{a.message}</p>
                      <div className="flex items-center gap-3 text-[10px] font-mono text-[var(--text-muted)] mt-1.5">
                        <span>Target Pool: <strong className="text-[var(--text-primary)]">{a.device_id}</strong></span>
                        <span>•</span>
                        <span>Triggered: {new Date(a.triggered_at).toLocaleString()}</span>
                      </div>
                    </div>

                    {/* 4-Question Framework */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-[var(--border-subtle)] text-[11px] font-sans">
                      <div className="p-2.5 rounded-xl bg-[var(--surface-secondary)]/40 border border-[var(--border-subtle)]">
                        <strong className="text-[var(--text-primary)] block">1. What happened?</strong>
                        <span className="text-[var(--text-secondary)] mt-0.5 block leading-relaxed">
                          Storage growth on {a.device_id} is trending faster than historical rates.
                        </span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-[var(--surface-secondary)]/40 border border-[var(--border-subtle)]">
                        <strong className="text-[var(--text-primary)] block">2. Why does it matter?</strong>
                        <span className="text-[var(--text-secondary)] mt-0.5 block leading-relaxed">
                          Unmonitored growth risks hitting the 90% hard ceiling, triggering application I/O throttling.
                        </span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-[var(--surface-secondary)]/40 border border-[var(--border-subtle)]">
                        <strong className="text-[var(--text-primary)] block">3. Supporting Evidence:</strong>
                        <span className="text-[var(--text-secondary)] mt-0.5 block leading-relaxed">
                          Telemetry readings verified by calibrated quantile forecast with {a.status} severity status.
                        </span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-[var(--surface-secondary)]/40 border border-[var(--border-subtle)]">
                        <strong className="text-[var(--text-primary)] block">4. What to do next:</strong>
                        <span className="text-[var(--text-secondary)] mt-0.5 block leading-relaxed">
                          Acknowledge this notification and simulate cold data migration in the Digital Twin.
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Status and Action Buttons */}
                <div className="flex items-center gap-2 self-end md:self-start shrink-0">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                      a.status === 'ACTIVE'
                        ? 'bg-[var(--status-critical)]/15 text-[var(--status-critical)] border border-[var(--status-critical)]/40 shadow-sm'
                        : a.status === 'ACKNOWLEDGED'
                        ? 'bg-[var(--status-warning)]/15 text-[var(--status-warning)] border border-[var(--status-warning)]/40 shadow-sm'
                        : 'bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm'
                    }`}
                  >
                    {a.status}
                  </span>

                  {a.status === 'ACTIVE' && (
                    <button
                      onClick={() => handleAcknowledge(a.id)}
                      className="btn-ember-secondary px-3 py-1.5 rounded-lg text-xs font-medium"
                    >
                      Acknowledge
                    </button>
                  )}

                  {a.status !== 'RESOLVED' && (
                    <button
                      onClick={() => handleResolve(a.id)}
                      className="btn-ember-primary px-3.5 py-1.5 rounded-lg text-xs font-semibold"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
