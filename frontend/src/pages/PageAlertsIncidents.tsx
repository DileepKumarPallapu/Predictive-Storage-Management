import React, { useState, useEffect } from 'react';
import { api, AlertItem } from '../api/client';
import { AlertTriangle, CheckCircle2, ShieldAlert, Check, X, Filter } from 'lucide-react';
import { EmptyState } from '../components/EmptyState';

export const PageAlertsIncidents: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

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
          <div className="w-8 h-8 rounded-lg bg-[var(--color-critical)]/15 border border-[var(--color-critical)]/30 flex items-center justify-center text-[var(--color-critical)] shadow-[0_0_12px_rgba(255,113,138,0.2)]">
            <AlertTriangle size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            Alerts, Incidents & Operational Safeguards
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          Proactive notifications generated when risk envelopes or telemetry quality boundaries are approached.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="glass-panel rounded-xl p-3.5 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2 text-xs">
          <Filter size={14} className="text-[var(--text-tertiary)]" />
          <span className="text-[var(--text-secondary)] font-medium">Category:</span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-[var(--surface-raised)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none cursor-pointer"
          >
            <option value="" className="bg-[var(--surface-panel)]">All Categories</option>
            <option value="CAPACITY_RISK" className="bg-[var(--surface-panel)]">Capacity Risk</option>
            <option value="PERFORMANCE_RISK" className="bg-[var(--surface-panel)]">Performance Risk</option>
            <option value="DATA_QUALITY" className="bg-[var(--surface-panel)]">Data Quality</option>
            <option value="MODEL_DRIFT" className="bg-[var(--surface-panel)]">Model Drift</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-[var(--text-secondary)] font-medium">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[var(--surface-raised)]/60 border border-[var(--border-subtle)] focus:border-[var(--accent-cyan)]/70 rounded-lg px-3 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none cursor-pointer"
          >
            <option value="" className="bg-[var(--surface-panel)]">All Statuses</option>
            <option value="ACTIVE" className="bg-[var(--surface-panel)]">Active</option>
            <option value="ACKNOWLEDGED" className="bg-[var(--surface-panel)]">Acknowledged</option>
            <option value="RESOLVED" className="bg-[var(--surface-panel)]">Resolved</option>
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
        <div className="space-y-3">
          {alerts.map((a) => (
            <div
              key={a.id}
              className={`glass-panel rounded-xl p-4.5 transition-all ${
                a.status === 'ACTIVE'
                  ? a.severity === 'CRITICAL'
                    ? 'border-[var(--color-critical)]/50 shadow-[0_0_12px_rgba(255,113,138,0.15)]'
                    : 'border-[var(--color-warning)]/50 shadow-[0_0_12px_rgba(255,203,112,0.12)]'
                  : 'opacity-70'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-start gap-3.5">
                  <span className="mt-0.5">
                    {a.severity === 'CRITICAL' ? (
                      <ShieldAlert size={19} className="text-[var(--color-critical)]" />
                    ) : (
                      <AlertTriangle size={19} className="text-[var(--color-warning)]" />
                    )}
                  </span>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-bold text-[var(--text-primary)]">{a.title}</h3>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--accent-cyan)]">
                        {a.category}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">{a.message}</p>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-[var(--text-tertiary)] mt-2">
                      <span>Target: <strong className="text-[var(--text-primary)]">{a.device_id}</strong></span>
                      <span>•</span>
                      <span>Triggered: {new Date(a.triggered_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {/* Status and Action Buttons */}
                <div className="flex items-center gap-2 self-end md:self-center">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                      a.status === 'ACTIVE'
                        ? 'bg-[var(--color-critical)]/15 text-[var(--color-critical)] border border-[var(--color-critical)]/40 shadow-sm'
                        : a.status === 'ACKNOWLEDGED'
                        ? 'bg-[var(--color-warning)]/15 text-[var(--color-warning)] border border-[var(--color-warning)]/40 shadow-sm'
                        : 'bg-[var(--color-success)]/15 text-[var(--color-success)] border border-[var(--color-success)]/40 shadow-sm'
                    }`}
                  >
                    {a.status}
                  </span>

                  {a.status === 'ACTIVE' && (
                    <button
                      onClick={() => handleAcknowledge(a.id)}
                      className="btn-aurora-secondary px-3 py-1.5 rounded-lg text-xs font-medium"
                    >
                      Acknowledge
                    </button>
                  )}

                  {a.status !== 'RESOLVED' && (
                    <button
                      onClick={() => handleResolve(a.id)}
                      className="btn-aurora-primary px-3 py-1.5 rounded-lg text-xs font-semibold"
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
