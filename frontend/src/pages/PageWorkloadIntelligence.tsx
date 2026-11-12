import React, { useEffect, useState } from 'react';
import { Activity, RefreshCw, TrendingUp, AlertCircle, Zap } from 'lucide-react';
import { api, DeviceSummary } from '../api/client';

export const PageWorkloadIntelligence: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string>('vol-nvme-tier1-db');
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDevices()
      .then((list) => {
        setDevices(list);
        if (list.length > 0 && !list.some((d) => d.id === selectedId)) {
          setSelectedId(list[0].id);
        }
      })
      .catch(() => {});
  }, []);

  const fetchAnalysis = async (storageId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getWorkloadRegime(storageId);
      setAnalysis(res);
    } catch (err: any) {
      setError(err.message || 'Failed to inspect workload regime.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedId) fetchAnalysis(selectedId);
  }, [selectedId]);

  const handleAnalyze = async () => {
    setRunning(true);
    setError(null);
    try {
      await api.analyzeWorkloadRegime(selectedId);
      await fetchAnalysis(selectedId);
    } catch (err: any) {
      setError(err.message || 'Workload analysis failed.');
    } finally {
      setRunning(false);
    }
  };

  const metrics = analysis?.metrics || {};
  const history = analysis?.recent_history || [];

  const regimeBadgeClass = (label: string) => {
    if (label === 'SUDDEN_BURST' || label === 'UNUSUAL_CONSUMPTION_CHANGE') return 'bg-[var(--brand-soft)] text-[var(--status-critical)]';
    if (label === 'ACCELERATING_GROWTH') return 'bg-[var(--status-warning)]/15 text-[var(--status-warning)]';
    if (label === 'INSUFFICIENT_HISTORY') return 'bg-[var(--surface-secondary)] text-[var(--text-muted)]';
    return 'bg-[var(--status-success)]/15 text-[var(--status-success)]';
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Activity size={20} className="text-[var(--brand-primary)]" />
            Workload Intelligence & Drift Detection
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Statistical trend decomposition, lag-24 periodicity, Z-score burst changepoints, KS/PSI distribution drift, and interruption audits linked to timestamps.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Select storage volume"
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-md bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-[var(--text-primary)]"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.id})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={running || loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white"
          >
            <RefreshCw size={13} className={running ? 'animate-spin' : ''} />
            {running ? 'Analyzing...' : 'Run Regime Analysis'}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg border border-[var(--status-critical)]/30 bg-[var(--brand-soft)] text-xs text-[var(--status-critical)] flex items-center gap-2">
          <AlertCircle size={15} />
          {error}
        </div>
      )}

      {analysis && (
        <>
          <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <TrendingUp size={18} className="text-[var(--brand-primary)]" />
                <span className="text-sm font-semibold text-[var(--text-primary)]">Classified Workload Regime:</span>
                <span className={`px-2.5 py-0.5 rounded font-mono text-xs font-bold ${regimeBadgeClass(analysis.regime_label)}`}>
                  {analysis.regime_label}
                </span>
              </div>
              <span className="text-xs font-mono text-[var(--text-muted)]">
                Confidence: {((analysis.confidence ?? 0) * 100).toFixed(1)}% · Samples: {metrics.sample_count ?? analysis.sample_count ?? 0}
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{analysis.explanation}</p>
          </div>

          {/* Underlying Quantitative Evidence */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Overall Slope', val: metrics.overall_slope_pct_per_day !== undefined ? `${metrics.overall_slope_pct_per_day}% / day` : 'N/A' },
              { label: 'Recent vs Early Slope', val: metrics.recent_slope_pct_per_day !== undefined ? `${metrics.recent_slope_pct_per_day}% vs ${metrics.early_slope_pct_per_day}%` : 'N/A' },
              { label: 'Periodicity Autocorrelation', val: metrics.periodicity_autocorr ?? 'N/A' },
              { label: 'Burst Z-Score (Recent Max)', val: metrics.recent_max_zscore ?? 'N/A' },
              { label: 'KS Statistic / p-value', val: metrics.ks_statistic !== undefined ? `${metrics.ks_statistic} (p=${metrics.ks_pvalue})` : 'N/A' },
              { label: 'PSI Distribution Drift', val: metrics.psi_drift ?? 'N/A' },
              { label: 'Collection Interruptions', val: metrics.interruptions_detected ?? 0 },
              { label: 'Observed Span', val: metrics.span_days !== undefined ? `${metrics.span_days} days` : 'N/A' },
            ].map((item) => (
              <div key={item.label} className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-3">
                <div className="text-[11px] text-[var(--text-muted)]">{item.label}</div>
                <div className="text-sm font-bold font-mono text-[var(--text-primary)] mt-1">{String(item.val)}</div>
              </div>
            ))}
          </div>

          {/* Timestamped Event Ledger */}
          <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
              <Zap size={15} className="text-[var(--brand-primary)]" />
              Persisted Regime & Drift Event Log
            </h3>
            {history.length === 0 ? (
              <p className="text-xs text-[var(--text-muted)]">No historical regime events recorded yet for this volume.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                      <th className="py-2 px-3">Detected At</th>
                      <th className="py-2 px-3">Event Type</th>
                      <th className="py-2 px-3">Regime</th>
                      <th className="py-2 px-3">Severity</th>
                      <th className="py-2 px-3">Explanation & Statistical Link</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h: any) => (
                      <tr key={h.id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                        <td className="py-2 px-3 font-mono text-[var(--text-muted)] whitespace-nowrap">
                          {h.detected_at ? h.detected_at.slice(0, 19).replace('T', ' ') : '—'}
                        </td>
                        <td className="py-2 px-3 font-mono">{h.event_type}</td>
                        <td className="py-2 px-3">
                          <span className={`px-2 py-0.5 rounded font-mono text-[11px] ${regimeBadgeClass(h.regime_label)}`}>
                            {h.regime_label}
                          </span>
                        </td>
                        <td className="py-2 px-3 font-mono">{h.severity}</td>
                        <td className="py-2 px-3 text-[var(--text-secondary)]">{h.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
