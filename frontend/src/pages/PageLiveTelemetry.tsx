import React, { useEffect, useState } from 'react';
import { Radio, RefreshCw, Play, CheckCircle2, XCircle, AlertTriangle, Server } from 'lucide-react';
import { api } from '../api/client';

export const PageLiveTelemetry: React.FC = () => {
  const [connectors, setConnectors] = useState<any[]>([]);
  const [liveHost, setLiveHost] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionBusyId, setActionBusyId] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [promEndpoint, setPromEndpoint] = useState('http://127.0.0.1:9100/metrics');
  const [promResult, setPromResult] = useState<any>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [connRes, hostRes] = await Promise.all([
        api.getConnectors(),
        api.getLiveHostTelemetry().catch(() => null),
      ]);
      setConnectors(connRes.connectors || []);
      setLiveHost(hostRes);
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Failed to load live collector telemetry state.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTest = async (connectorId: string) => {
    setActionBusyId(connectorId);
    setBanner(null);
    try {
      const res = await api.testConnector(connectorId);
      const status = res?.result?.status;
      if (status === 'CONNECTED' || status === 'READY') {
        setBanner({ type: 'success', text: `Collector ${connectorId} verified (${status}) by backend probe.` });
      } else {
        setBanner({ type: 'error', text: `Collector ${connectorId} probe failed: ${res?.result?.error || status}` });
      }
      await loadData();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Connection test failed.' });
    } finally {
      setActionBusyId(null);
    }
  };

  const handleCollect = async (connectorId: string) => {
    setActionBusyId(connectorId);
    setBanner(null);
    try {
      const res = await api.collectFromConnector(connectorId, {});
      if (res?.result?.status === 'CONNECTION_FAILED') {
        setBanner({ type: 'error', text: `Collection failed: ${res.result.error}` });
      } else {
        setBanner({
          type: 'success',
          text: `Collector ${connectorId} sampled ${res?.result?.volumes_count ?? 0} volume(s); persisted ${res?.persisted_count ?? 0} new record(s).`,
        });
      }
      await loadData();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Telemetry refresh failed.' });
    } finally {
      setActionBusyId(null);
    }
  };

  const handlePromScrape = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionBusyId('prom-probe');
    setBanner(null);
    try {
      const res = await api.scrapePrometheus(promEndpoint.trim());
      setPromResult(res);
      if (res?.status === 'OK' || res?.status === 'SUCCESS') {
        setBanner({ type: 'success', text: `Prometheus scrape succeeded from ${promEndpoint}.` });
      } else {
        setBanner({ type: 'error', text: `Prometheus endpoint unavailable or returned error: ${res?.error || res?.status}` });
      }
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Prometheus scrape request failed.' });
    } finally {
      setActionBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Radio size={20} className="text-[var(--brand-primary)]" />
            Live Telemetry Monitoring
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Real-time collector health, last sync timestamps, ingestion delays, received metric counts, and error logs in strict read-only mode.
          </p>
        </div>
        <button
          type="button"
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-[var(--surface-primary)] border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)]"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh Collectors
        </button>
      </div>

      {banner && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center gap-2 ${
            banner.type === 'success'
              ? 'border-[var(--status-success)]/30 bg-[var(--status-success)]/10 text-[var(--status-success)]'
              : 'border-[var(--status-critical)]/30 bg-[var(--brand-soft)] text-[var(--status-critical)]'
          }`}
        >
          {banner.type === 'success' ? <CheckCircle2 size={15} /> : <XCircle size={15} />}
          {banner.text}
        </div>
      )}

      {/* Registered Connectors Table */}
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Connected Collectors ({connectors.length})</h3>
          <span className="text-[11px] font-mono text-[var(--status-success)]">PERMISSION MODE: READ_ONLY</span>
        </div>

        {connectors.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)] py-4">
            No collectors registered yet. Add a Linux Host or Prometheus collector in Integration Management.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                  <th className="py-2 px-3">Collector</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Target Volume</th>
                  <th className="py-2 px-3">Last Success</th>
                  <th className="py-2 px-3">Last Failure</th>
                  <th className="py-2 px-3">Delay / Freq</th>
                  <th className="py-2 px-3">Metrics Received</th>
                  <th className="py-2 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {connectors.map((c) => (
                  <tr key={c.id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-[var(--text-primary)]">{c.name}</div>
                      <div className="text-[10px] font-mono text-[var(--text-muted)]">
                        {c.connector_type} {c.endpoint_url ? `· ${c.endpoint_url}` : ''}
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[11px] ${
                          c.last_status === 'CONNECTED'
                            ? 'bg-[var(--status-success)]/15 text-[var(--status-success)]'
                            : c.last_status === 'ERROR'
                              ? 'bg-[var(--brand-soft)] text-[var(--status-critical)]'
                              : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)]'
                        }`}
                      >
                        {c.last_status}
                      </span>
                      {c.last_error && (
                        <div className="text-[10px] text-[var(--status-critical)] mt-1 max-w-xs truncate" title={c.last_error}>
                          {c.last_error}
                        </div>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[var(--text-secondary)]">{c.target_storage_id || 'Unbound'}</td>
                    <td className="py-2.5 px-3 font-mono text-[var(--text-secondary)]">
                      {c.last_sync_at ? c.last_sync_at.slice(0, 19).replace('T', ' ') : 'Never'}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[var(--text-muted)]">
                      {c.last_failure_at ? c.last_failure_at.slice(0, 19).replace('T', ' ') : 'None'}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {c.data_delay_seconds !== null && c.data_delay_seconds !== undefined ? `${c.data_delay_seconds}s` : 'N/A'} /{' '}
                      {c.collection_frequency_seconds ?? 300}s
                    </td>
                    <td className="py-2.5 px-3 font-mono font-semibold text-[var(--text-primary)]">{c.metrics_received ?? 0}</td>
                    <td className="py-2.5 px-3 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleTest(c.id)}
                          disabled={actionBusyId === c.id}
                          className="px-2 py-1 rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] hover:bg-[var(--surface-tertiary)] text-[11px] font-medium"
                        >
                          Test
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCollect(c.id)}
                          disabled={actionBusyId === c.id || !c.is_enabled}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white text-[11px] font-medium disabled:opacity-50"
                        >
                          <Play size={11} />
                          Collect
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Host Live Partition Probe + Prometheus Live Diagnostic */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
              <Server size={15} className="text-[var(--brand-primary)]" />
              Host OS Mounted Partitions (Read-Only Probe)
            </h3>
            <span className="text-[11px] font-mono text-[var(--text-muted)]">
              Provenance: {liveHost?.provenance || 'LIVE'}
            </span>
          </div>
          {!liveHost?.partitions?.length ? (
            <p className="text-xs text-[var(--text-muted)]">No live partitions reported by OS collector.</p>
          ) : (
            <div className="space-y-2">
              {liveHost.partitions.map((p: any) => (
                <div key={p.id} className="p-2.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-xs flex items-center justify-between gap-2">
                  <div>
                    <div className="font-semibold text-[var(--text-primary)]">{p.name}</div>
                    <div className="text-[11px] font-mono text-[var(--text-muted)]">{p.mountpoint}</div>
                  </div>
                  <div className="text-right font-mono">
                    <div className="font-semibold text-[var(--text-primary)]">{p.utilization_pct}% used</div>
                    <div className="text-[10px] text-[var(--text-muted)]">
                      {(p.used_bytes / 1024 ** 3).toFixed(1)} / {(p.total_capacity_bytes / 1024 ** 3).toFixed(1)} GB
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
            <AlertTriangle size={15} className="text-[var(--status-warning)]" />
            On-Demand Prometheus Node Exporter Probe
          </h3>
          <form onSubmit={handlePromScrape} className="flex flex-wrap gap-2">
            <input
              type="url"
              value={promEndpoint}
              onChange={(e) => setPromEndpoint(e.target.value)}
              placeholder="http://127.0.0.1:9100/metrics"
              required
              className="flex-1 min-w-[200px] px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-[var(--text-primary)] font-mono"
            />
            <button
              type="submit"
              disabled={actionBusyId === 'prom-probe'}
              className="px-3 py-1.5 text-xs font-medium rounded bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white"
            >
              {actionBusyId === 'prom-probe' ? 'Probing...' : 'Scrape Target'}
            </button>
          </form>
          {promResult && (
            <pre className="p-2.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[11px] font-mono text-[var(--text-secondary)] overflow-x-auto max-h-44">
              {JSON.stringify(promResult, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};
