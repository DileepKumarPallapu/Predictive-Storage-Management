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
        <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
          <AlertTriangle className="text-obsidian-coral" size={22} />
          Alerts, Incidents & Operational Safeguards
        </h2>
        <p className="text-xs text-obsidian-muted mt-1">
          Proactive notifications generated when risk envelopes or telemetry quality boundaries are approached.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-3 flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2 text-xs">
          <Filter size={14} className="text-obsidian-muted" />
          <span className="text-obsidian-muted font-medium">Category:</span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1 text-obsidian-text focus:border-obsidian-cyan cursor-pointer"
          >
            <option value="">All Categories</option>
            <option value="CAPACITY_RISK">Capacity Risk</option>
            <option value="PERFORMANCE_RISK">Performance Risk</option>
            <option value="DATA_QUALITY">Data Quality</option>
            <option value="MODEL_DRIFT">Model Drift</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-obsidian-muted font-medium">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1 text-obsidian-text focus:border-obsidian-cyan cursor-pointer"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="RESOLVED">Resolved</option>
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
            className={`bg-obsidian-panel border rounded-lg p-4 transition-all ${
              a.status === 'ACTIVE'
                ? a.severity === 'CRITICAL'
                  ? 'border-obsidian-coral/50'
                  : 'border-obsidian-amber/50'
                : 'border-obsidian-border opacity-70'
            }`}
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className="mt-0.5">
                  {a.severity === 'CRITICAL' ? (
                    <ShieldAlert size={18} className="text-obsidian-coral" />
                  ) : (
                    <AlertTriangle size={18} className="text-obsidian-amber" />
                  )}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-obsidian-text">{a.title}</h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-obsidian-secondary border border-obsidian-border text-obsidian-cyan">
                      {a.category}
                    </span>
                  </div>
                  <p className="text-xs text-obsidian-muted mt-1 leading-relaxed">{a.message}</p>
                  <div className="flex items-center gap-4 text-[10px] font-mono text-obsidian-muted mt-2">
                    <span>Target: <span className="text-obsidian-text">{a.device_id}</span></span>
                    <span>•</span>
                    <span>Triggered: {new Date(a.triggered_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* Status and Action Buttons */}
              <div className="flex items-center gap-2 self-end md:self-center">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    a.status === 'ACTIVE'
                      ? 'bg-obsidian-coral/20 text-obsidian-coral border border-obsidian-coral/40'
                      : a.status === 'ACKNOWLEDGED'
                      ? 'bg-obsidian-amber/20 text-obsidian-amber border border-obsidian-amber/40'
                      : 'bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40'
                  }`}
                >
                  {a.status}
                </span>

                {a.status === 'ACTIVE' && (
                  <button
                    onClick={() => handleAcknowledge(a.id)}
                    className="px-2.5 py-1 rounded bg-obsidian-secondary hover:bg-obsidian-raised border border-obsidian-border text-obsidian-text text-xs transition-colors"
                  >
                    Acknowledge
                  </button>
                )}

                {a.status !== 'RESOLVED' && (
                  <button
                    onClick={() => handleResolve(a.id)}
                    className="px-2.5 py-1 rounded bg-obsidian-cyan/15 hover:bg-obsidian-cyan/25 border border-obsidian-cyan/40 text-obsidian-cyan text-xs font-semibold transition-colors"
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
