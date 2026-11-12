import React, { useEffect, useState } from 'react';
import {
  Eye, HardDrive, Bell, TrendingUp, Cpu, FileText, ArrowRight, RefreshCw
} from 'lucide-react';
import { api } from '../api/client';

interface PageViewerDashboardProps {
  onNavigate: (tab: string, deviceId?: string) => void;
}

const formatTb = (bytes: number) => `${(bytes / (1024 ** 4)).toFixed(2)} TB`;

export const PageViewerDashboard: React.FC<PageViewerDashboardProps> = ({ onNavigate }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadSnapshot = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.getOperatorDashboard();
      setData(res);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Unable to load read-only workspace summary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSnapshot();
  }, []);

  if (loading && !data) {
    return <div className="p-6 text-xs text-[var(--text-secondary)]">Loading read-only stakeholder dashboard...</div>;
  }

  const kpis = data?.kpis || {};
  const resources: any[] = data?.managed_resources || [];
  const alerts: any[] = data?.active_alerts || [];
  const forecasts: any[] = data?.forecasts_summary || [];
  const models: any[] = data?.ml_models || [];
  const reports: any[] = data?.recent_reports || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-[var(--surface-secondary)] text-[var(--text-secondary)] border border-[var(--border-strong)]">
              <Eye size={11} /> VIEWER · READ-ONLY ACCESS
            </span>
            <span className="text-[11px] font-mono text-[var(--text-muted)]">
              {data?.user?.username || 'viewer'}
            </span>
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] mt-1">
            Storage Resilience Stakeholder Summary
          </h1>
          <p className="text-xs text-[var(--text-secondary)]">
            Read-only visibility into capacity utilization, calibrated forecasts, risk indicators, alerts, and exportable compliance reports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onNavigate('reports')}
            className="px-3 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-95 inline-flex items-center gap-1.5"
          >
            <FileText size={13} /> View & Export Reports
          </button>
          <button
            type="button"
            onClick={loadSnapshot}
            className="p-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-primary)]"
            title="Refresh snapshot"
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

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] font-mono uppercase text-[var(--text-muted)]">
            <span>Monitored Pools</span>
            <HardDrive size={14} className="text-[var(--accent)]" />
          </div>
          <div className="text-2xl font-bold mt-1">{kpis.managed_storage_count ?? resources.length}</div>
          <button type="button" onClick={() => onNavigate('devices')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            View Inventory <ArrowRight size={11} />
          </button>
        </div>

        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] font-mono uppercase text-[var(--text-muted)]">
            <span>Active Alerts</span>
            <Bell size={14} className="text-[var(--status-warning)]" />
          </div>
          <div className="text-2xl font-bold mt-1">{kpis.active_alerts_count ?? alerts.length}</div>
          <button type="button" onClick={() => onNavigate('alerts')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            Inspect Alerts <ArrowRight size={11} />
          </button>
        </div>

        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] font-mono uppercase text-[var(--text-muted)]">
            <span>Projected Breaches</span>
            <TrendingUp size={14} className="text-[var(--status-critical)]" />
          </div>
          <div className="text-2xl font-bold mt-1">{kpis.projected_breaches_count ?? 0}</div>
          <button type="button" onClick={() => onNavigate('forecasts')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            View Forecasts <ArrowRight size={11} />
          </button>
        </div>

        <div className="titan-card rounded-xl p-4">
          <div className="flex items-center justify-between text-[11px] font-mono uppercase text-[var(--text-muted)]">
            <span>ML Models Tracked</span>
            <Cpu size={14} className="text-[var(--accent)]" />
          </div>
          <div className="text-2xl font-bold mt-1">{kpis.trained_models_count ?? models.length}</div>
          <button type="button" onClick={() => onNavigate('models')} className="text-[11px] text-[var(--accent)] mt-1 inline-flex items-center gap-1 hover:underline">
            Model Accuracy <ArrowRight size={11} />
          </button>
        </div>
      </div>

      {/* Read-only fleet summary */}
      <div className="titan-card rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-bold">Fleet Capacity & Health Snapshot</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="border-b border-[var(--border-subtle)] text-[10px] font-mono uppercase text-[var(--text-muted)]">
              <tr>
                <th className="py-2 pr-3">Storage System</th>
                <th className="py-2 pr-3">Tier</th>
                <th className="py-2 pr-3">Utilization</th>
                <th className="py-2 pr-3">Used / Total</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2 text-right">Read-Only Inspect</th>
              </tr>
            </thead>
            <tbody>
              {resources.map((r) => (
                <tr key={r.id} className="border-b border-[var(--border-subtle)]/50">
                  <td className="py-2 pr-3">
                    <div className="font-semibold">{r.name}</div>
                    <div className="font-mono text-[10px] text-[var(--text-muted)]">{r.id}</div>
                  </td>
                  <td className="py-2 pr-3 font-mono text-[11px]">{r.tier}</td>
                  <td className="py-2 pr-3 font-mono">{r.utilization_pct.toFixed(1)}%</td>
                  <td className="py-2 pr-3 font-mono text-[var(--text-secondary)]">
                    {formatTb(r.used_bytes)} / {formatTb(r.total_capacity_bytes)}
                  </td>
                  <td className="py-2 pr-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-[var(--surface-secondary)]">
                      {r.status}
                    </span>
                  </td>
                  <td className="py-2 text-right space-x-1.5">
                    <button type="button" onClick={() => onNavigate('telemetry', r.id)} className="px-2 py-1 rounded text-[11px] border border-[var(--border-subtle)]">Telemetry</button>
                    <button type="button" onClick={() => onNavigate('risk', r.id)} className="px-2 py-1 rounded text-[11px] border border-[var(--border-subtle)]">Risk</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forecasts + Recent Reports */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="titan-card rounded-xl p-5 space-y-2.5">
          <h3 className="text-sm font-bold">Latest Forecast Runs</h3>
          {forecasts.slice(0, 5).map((f) => (
            <div key={f.id} className="flex items-center justify-between p-2 rounded border border-[var(--border-subtle)] text-xs font-mono">
              <span>{f.device_id} · {f.horizon_days}d</span>
              <span>{f.projected_capacity_breach ? 'BREACH RISK' : 'SAFE'}</span>
            </div>
          ))}
          {forecasts.length === 0 && <div className="text-xs text-[var(--text-muted)]">No saved forecast runs yet.</div>}
        </div>

        <div className="titan-card rounded-xl p-5 space-y-2.5">
          <h3 className="text-sm font-bold">Available Reports</h3>
          {reports.slice(0, 5).map((rp) => (
            <div key={rp.id} className="flex items-center justify-between p-2 rounded border border-[var(--border-subtle)] text-xs font-mono">
              <span>{rp.report_type} ({rp.format})</span>
              <span className="text-[var(--text-muted)]">{rp.row_count} rows</span>
            </div>
          ))}
          {reports.length === 0 && <div className="text-xs text-[var(--text-muted)]">No report snapshots recorded yet.</div>}
        </div>
      </div>
    </div>
  );
};
