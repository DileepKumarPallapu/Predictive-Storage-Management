import React, { useState, useEffect } from 'react';
import { api, DeviceSummary } from '../api/client';
import { FileText, Download, Eye, History } from 'lucide-react';

const REPORT_TYPES = [
  { id: 'storage_inventory', label: 'Infrastructure Health & Inventory' },
  { id: 'storage_utilisation', label: 'Capacity Analysis & Utilisation' },
  { id: 'capacity_forecast', label: 'Forecast Evaluation Report' },
  { id: 'model_performance', label: 'Model Comparison (LightGBM / SARIMAX)' },
  { id: 'performance_trends', label: 'Performance Trends' },
  { id: 'data_reliability', label: 'Data Reliability Profiles' },
  { id: 'workload_behaviour', label: 'Workload Behaviour & Drift' },
  { id: 'capacity_risk', label: 'Probabilistic Capacity Risk' },
  { id: 'risk_and_alert', label: 'Risk and Alert History' },
  { id: 'data_quality', label: 'Data Quality Preprocessing' },
  { id: 'digital_twin_comparison', label: 'Digital Twin Scenario Comparison' },
  { id: 'recommendation_history', label: 'Recommendation & Approval History' },
];

export const PageReports: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [reportType, setReportType] = useState<string>('storage_inventory');
  const [storageFilter, setStorageFilter] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [previewData, setPreviewData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    loadInitial();
  }, []);

  const loadInitial = async () => {
    try {
      const [devs, hist] = await Promise.all([api.getDevices(), api.getReportHistory()]);
      setDevices(devs);
      setHistory(hist);
    } catch (e) {
      console.error(e);
    }
  };

  const handleGeneratePreview = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await api.previewReportJson(reportType, storageFilter || undefined, startDate || undefined, endDate || undefined);
      setPreviewData(data);
      const hist = await api.getReportHistory();
      setHistory(hist);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to generate report preview');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadBlob = async (fmt: 'csv' | 'pdf') => {
    setErrorMsg('');
    try {
      const blob = await api.downloadAuthenticatedReport(
        reportType,
        fmt,
        storageFilter || undefined,
        startDate || undefined,
        endDate || undefined
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reportType.toLowerCase()}_report.${fmt}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      const hist = await api.getReportHistory();
      setHistory(hist);
    } catch (e: any) {
      setErrorMsg(e.message || `Failed to download ${fmt.toUpperCase()}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center">
            <FileText size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">Reports & Export Centre</h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          Generate auditable operational, ML model, performance, data quality, and Digital Twin reports directly from persisted database records.
        </p>
      </div>

      {/* Filter & Export Controls */}
      <div className="titan-card rounded-xl p-5 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] text-[var(--text-primary)]"
            >
              {REPORT_TYPES.map((rt) => (
                <option key={rt.id} value={rt.id}>{rt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Storage Resource (Optional)</label>
            <select
              value={storageFilter}
              onChange={(e) => setStorageFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] text-[var(--text-primary)]"
            >
              <option value="">All Storage Resources</option>
              {devices.map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.id})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Start Date (ISO / Optional)</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono"
            />
          </div>
          <div>
            <label className="block text-[11px] text-[var(--text-secondary)] mb-1">End Date (ISO / Optional)</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono"
            />
          </div>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-lg bg-[var(--status-critical)]/10 border border-[var(--status-critical)] text-xs text-[var(--status-critical)]">
            {errorMsg}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleGeneratePreview}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90"
          >
            <Eye size={14} /> {loading ? 'Generating...' : 'Generate & Preview Report'}
          </button>
          <button
            type="button"
            onClick={() => handleDownloadBlob('csv')}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold border border-[var(--border-strong)] bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-[var(--surface-secondary)]"
          >
            <Download size={14} /> Download CSV
          </button>
          <button
            type="button"
            onClick={() => handleDownloadBlob('pdf')}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold border border-[var(--accent)] text-[var(--accent)] hover:bg-[var(--brand-soft)]"
          >
            <Download size={14} /> Download PDF
          </button>
        </div>
      </div>

      {/* Report Preview */}
      {previewData && (
        <div className="titan-card rounded-xl p-5 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--border-subtle)] pb-3">
            <div>
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Preview: {previewData.report_type} ({previewData.row_count} rows)
              </h3>
              <p className="text-[11px] font-mono text-[var(--text-muted)]">
                ID: {previewData.report_id} · Generated: {previewData.generated_at} · Methodology: {previewData.methodology}
              </p>
            </div>
          </div>
          {previewData.rows?.length === 0 ? (
            <div className="text-xs text-[var(--text-secondary)]">No persisted records matched the selected filters.</div>
          ) : (
            <div className="overflow-x-auto max-h-96">
              <table className="w-full text-xs text-left font-mono">
                <thead className="border-b border-[var(--border-subtle)] text-[10px] uppercase text-[var(--text-muted)]">
                  <tr>
                    {Object.keys(previewData.rows[0]).map((col) => (
                      <th key={col} className="py-2 pr-3">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewData.rows.slice(0, 50).map((r: any, idx: number) => (
                    <tr key={idx} className="border-b border-[var(--border-subtle)]/50">
                      {Object.values(r).map((val: any, cidx: number) => (
                        <td key={cidx} className="py-1.5 pr-3 whitespace-nowrap">
                          {val === null || val === undefined ? 'N/A' : String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Report Generation History */}
      <div className="titan-card rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
          <History size={16} className="text-[var(--accent)]" /> Report History ({history.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left font-mono">
            <thead className="border-b border-[var(--border-subtle)] text-[10px] uppercase text-[var(--text-muted)]">
              <tr>
                <th className="py-2 pr-3">Report ID</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Format</th>
                <th className="py-2 pr-3">Storage Filter</th>
                <th className="py-2 pr-3">Rows</th>
                <th className="py-2 pr-3">Generated By</th>
                <th className="py-2">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(0, 20).map((h) => (
                <tr key={h.id} className="border-b border-[var(--border-subtle)]/50">
                  <td className="py-2 pr-3">{h.id}</td>
                  <td className="py-2 pr-3">{h.report_type}</td>
                  <td className="py-2 pr-3">{h.format}</td>
                  <td className="py-2 pr-3">{h.storage_id || 'All'}</td>
                  <td className="py-2 pr-3">{h.row_count}</td>
                  <td className="py-2 pr-3">{h.generated_by}</td>
                  <td className="py-2">{h.created_at ? new Date(h.created_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
