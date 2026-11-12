import React, { useState, useEffect } from 'react';
import { api, DatasetItem, DeviceSummary } from '../api/client';
import {
  Database,
  CheckCircle2,
  Info,
  Upload,
  Download,
  FileWarning,
  PlusCircle,
  Activity
} from 'lucide-react';

export const PageDatasetsQuality: React.FC = () => {
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedStorage, setSelectedStorage] = useState<string>('vol-nvme-tier1-db');
  const [qualityReport, setQualityReport] = useState<any>(null);
  const [ingestionJobs, setIngestionJobs] = useState<any[]>([]);
  const [csvText, setCsvText] = useState<string>(
    'timestamp,storage_id,total_capacity_bytes,used_capacity_bytes,read_iops,write_iops,read_latency_ms,write_latency_ms,throughput_mbps\n'
  );
  const [previewResult, setPreviewResult] = useState<any>(null);
  const [importMsg, setImportMsg] = useState<string>('');
  const [manualTs, setManualTs] = useState<string>(new Date().toISOString().slice(0, 16) + ':00Z');
  const [manualUsedGb, setManualUsedGb] = useState<string>('500');
  const [manualMsg, setManualMsg] = useState<string>('');
  const [reliabilityProfile, setReliabilityProfile] = useState<any>(null);
  const [telemetryRecords, setTelemetryRecords] = useState<any[]>([]);
  const [recordsTotal, setRecordsTotal] = useState<number>(0);

  useEffect(() => {
    loadDatasets();
    loadIngestionJobs();
  }, []);

  useEffect(() => {
    if (selectedStorage) {
      loadDataQuality(selectedStorage);
    }
  }, [selectedStorage]);

  const loadDatasets = async () => {
    try {
      const [dsData, devData] = await Promise.all([api.getDatasets(), api.getDevices()]);
      setDatasets(dsData);
      setDevices(devData);
      if (devData.length > 0 && !devData.some(d => d.id === selectedStorage)) {
        setSelectedStorage(devData[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadDataQuality = async (sid: string) => {
    try {
      const [dq, rel, recRes] = await Promise.all([
        api.getDataQuality(sid),
        api.getDataReliability(sid).catch(() => null),
        api.getTelemetryRecords(sid, undefined, 25, 0).catch(() => ({ total: 0, records: [] })),
      ]);
      setQualityReport(dq);
      setReliabilityProfile(rel);
      setTelemetryRecords(recRes.records || []);
      setRecordsTotal(recRes.total || 0);
    } catch (e) {
      console.error(e);
    }
  };

  const loadIngestionJobs = async () => {
    try {
      const jobs = await api.getIngestionJobs();
      setIngestionJobs(jobs);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      if (typeof ev.target?.result === 'string') {
        setCsvText(ev.target.result);
        setPreviewResult(null);
        setImportMsg('');
      }
    };
    reader.readAsText(file);
  };

  const handlePreviewCsv = async () => {
    setImportMsg('');
    try {
      const res = await api.previewCsvImport(csvText, selectedStorage);
      setPreviewResult(res);
    } catch (e: any) {
      setImportMsg(`Preview error: ${e.message}`);
    }
  };

  const handleCommitCsv = async () => {
    setImportMsg('');
    try {
      const res = await api.commitCsvImport(csvText, selectedStorage);
      if (res.job_id) {
        setImportMsg(`Imported ${res.accepted_rows} rows (rejected: ${res.rejected_rows}, duplicates: ${res.duplicate_rows}). Job ID: ${res.job_id}`);
        setPreviewResult(null);
        loadIngestionJobs();
        loadDataQuality(selectedStorage);
      } else {
        setImportMsg(`Import issue: ${res.detail?.message || JSON.stringify(res)}`);
      }
    } catch (e: any) {
      setImportMsg(`Import error: ${e.message}`);
    }
  };

  const handleManualEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    setManualMsg('');
    const dev = devices.find(d => d.id === selectedStorage);
    const usedBytes = Math.round(parseFloat(manualUsedGb) * (1024 ** 3));
    try {
      const res = await api.manualTelemetryEntry({
        storage_id: selectedStorage,
        timestamp: manualTs,
        total_capacity_bytes: dev?.total_capacity_bytes,
        used_capacity_bytes: usedBytes,
      });
      setManualMsg(`Saved telemetry record at ${res.timestamp} (${res.utilization_pct}% utilized).`);
      loadIngestionJobs();
      loadDataQuality(selectedStorage);
    } catch (err: any) {
      setManualMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center shadow-xs">
              <Database size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              Data Ingestion, Quality & Provenance
            </h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
            CSV upload validation, duplicate detection, manual telemetry entry, and deterministic preprocessing quality inspection.
          </p>
        </div>
        <a
          href={api.getCsvTemplateUrl()}
          download="aegisstor_telemetry_template.csv"
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
        >
          <Download size={14} />
          Download CSV Template
        </a>
      </div>

      {/* CSV Ingestion & Preview Panel */}
      <div className="titan-card rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Upload size={16} className="text-[var(--accent-primary)]" />
            CSV Telemetry Upload & Validation Pipeline
          </h3>
          <select
            value={selectedStorage}
            onChange={(e) => setSelectedStorage(e.target.value)}
            className="text-xs px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] text-[var(--text-primary)]"
          >
            {devices.map(d => (
              <option key={d.id} value={d.id}>{d.name} ({d.id})</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={handleFileUpload}
            className="text-xs text-[var(--text-secondary)]"
          />
        </div>

        <textarea
          rows={4}
          value={csvText}
          onChange={(e) => setCsvText(e.target.value)}
          className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-secondary)]/50 p-3 text-xs font-mono text-[var(--text-primary)]"
        />

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handlePreviewCsv}
            className="px-4 py-2 rounded-lg text-xs font-semibold border border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-[var(--text-primary)] hover:border-[var(--accent-primary)]"
          >
            Preview & Validate Rows
          </button>
          <button
            onClick={handleCommitCsv}
            className="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90"
          >
            Commit Valid Records to Database
          </button>
          {importMsg && (
            <span className="text-xs font-mono text-[var(--text-primary)]">{importMsg}</span>
          )}
        </div>

        {previewResult && (
          <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-secondary)]/40 space-y-3 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono">
              <div>Total Rows: <strong>{previewResult.total_rows}</strong></div>
              <div className="text-[var(--status-success)]">Accepted: <strong>{previewResult.accepted_rows}</strong></div>
              <div className="text-amber-600">Duplicates: <strong>{previewResult.duplicate_rows}</strong></div>
              <div className="text-red-600">Rejected: <strong>{previewResult.rejected_rows}</strong></div>
              <div>Completeness: <strong>{previewResult.data_completeness_pct}%</strong></div>
            </div>
            {previewResult.errors && previewResult.errors.length > 0 && (
              <div className="space-y-1">
                <div className="font-semibold text-red-600 flex items-center gap-1">
                  <FileWarning size={14} /> Row-Level Validation Issues:
                </div>
                <ul className="list-disc pl-5 font-mono text-[11px] text-[var(--text-secondary)] max-h-32 overflow-y-auto">
                  {previewResult.errors.slice(0, 15).map((err: any, i: number) => (
                    <li key={i}>Row {err.row_number} [{err.type}]: {err.reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Manual Entry + Live Data Quality Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <form onSubmit={handleManualEntry} className="titan-card rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
            <PlusCircle size={16} className="text-[var(--accent-primary)]" />
            Manual Telemetry Entry ({selectedStorage})
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Timestamp (UTC ISO)</label>
              <input
                type="text"
                value={manualTs}
                onChange={(e) => setManualTs(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono"
              />
            </div>
            <div>
              <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Used Capacity (GB)</label>
              <input
                type="number"
                step="0.1"
                value={manualUsedGb}
                onChange={(e) => setManualUsedGb(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button type="submit" className="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white">
              Save Manual Reading
            </button>
            {manualMsg && <span className="text-xs font-mono text-[var(--text-secondary)]">{manualMsg}</span>}
          </div>
        </form>

        {qualityReport && (
          <div className="titan-card rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Activity size={16} className="text-[var(--accent-primary)]" />
              Preprocessing & Data Quality ({qualityReport.storage_id})
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-[var(--surface-secondary)]/50 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] block">Total Records</span>
                <strong>{qualityReport.total_records_received}</strong>
              </div>
              <div className="p-2.5 rounded-lg bg-[var(--surface-secondary)]/50 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] block">Valid / Rejected</span>
                <strong>{qualityReport.valid_records} / {qualityReport.rejected_records}</strong>
              </div>
              <div className="p-2.5 rounded-lg bg-[var(--surface-secondary)]/50 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] block">Completeness</span>
                <strong>{qualityReport.data_completeness_pct}%</strong>
              </div>
              <div className="p-2.5 rounded-lg bg-[var(--surface-secondary)]/50 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] block">Duplicates</span>
                <strong>{qualityReport.duplicate_records}</strong>
              </div>
              <div className="p-2.5 rounded-lg bg-[var(--surface-secondary)]/50 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] block">Outliers</span>
                <strong>{qualityReport.outlier_count}</strong>
              </div>
              <div className="p-2.5 rounded-lg bg-[var(--surface-secondary)]/50 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] block">Latest Sample</span>
                <strong className="truncate block">{qualityReport.latest_telemetry_timestamp?.slice(0, 16) || 'None'}</strong>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Recent Ingestion Jobs */}
      {ingestionJobs.length > 0 && (
        <div className="titan-card rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-[var(--text-primary)]">Recent Ingestion Jobs</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left font-mono">
              <thead className="text-[10px] uppercase text-[var(--text-tertiary)] border-b border-[var(--border-subtle)]">
                <tr>
                  <th className="py-2 pr-3">Job ID</th>
                  <th className="py-2 pr-3">Source</th>
                  <th className="py-2 pr-3">Storage</th>
                  <th className="py-2 pr-3">Accepted / Rejected / Dup</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2">Error Report</th>
                </tr>
              </thead>
              <tbody>
                {ingestionJobs.slice(0, 8).map((j) => (
                  <tr key={j.id} className="border-b border-[var(--border-subtle)]/50">
                    <td className="py-2 pr-3">{j.id}</td>
                    <td className="py-2 pr-3">{j.source_type}</td>
                    <td className="py-2 pr-3">{j.storage_id || 'multi'}</td>
                    <td className="py-2 pr-3">{j.accepted_rows} / {j.rejected_rows} / {j.duplicate_rows}</td>
                    <td className="py-2 pr-3">{j.status}</td>
                    <td className="py-2">
                      {(j.rejected_rows > 0 || j.duplicate_rows > 0) ? (
                        <a
                          href={`/api/v1/ingestion/jobs/${j.id}/errors?format=csv`}
                          className="text-[var(--accent-primary)] underline"
                        >
                          Download CSV
                        </a>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 9-Factor Data Reliability & Record-Level Inspection View (Module D) */}
      {reliabilityProfile && (
        <div className="titan-card rounded-xl p-5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              9-Factor Data Reliability Score: {(reliabilityProfile.reliability_score * 100).toFixed(1)}% ({reliabilityProfile.reliability_tier})
            </h3>
            <span className="text-[11px] font-mono text-[var(--text-muted)]">
              {reliabilityProfile.is_stale ? 'STALE TELEMETRY' : 'FRESH'} · Conformal Multiplier x{reliabilityProfile.uncertainty_multiplier}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-xs font-mono">
            {Object.entries(reliabilityProfile.factors || {}).map(([k, v]: [string, any]) => (
              <div key={k} className="p-2.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)]">
                <div className="text-[10px] text-[var(--text-muted)] uppercase">{k.replace(/_score/g, '').replace(/_/g, ' ')}</div>
                <div className="font-bold text-[var(--text-primary)] mt-0.5">{(Number(v) * 100).toFixed(1)}%</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="titan-card rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-[var(--text-primary)]">
            Record-Level Telemetry Inspection ({recordsTotal} total for {selectedStorage})
          </h3>
          <span className="text-[11px] font-mono text-[var(--text-muted)]">Showing latest 25 persisted records</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left font-mono">
            <thead className="text-[10px] uppercase text-[var(--text-muted)] border-b border-[var(--border-subtle)]">
              <tr>
                <th className="py-2 pr-3">Timestamp</th>
                <th className="py-2 pr-3">Used (GB)</th>
                <th className="py-2 pr-3">Util %</th>
                <th className="py-2 pr-3">Read / Write IOPS</th>
                <th className="py-2 pr-3">Latency ms</th>
                <th className="py-2">Provenance / Source</th>
              </tr>
            </thead>
            <tbody>
              {telemetryRecords.map((rec) => (
                <tr key={rec.id} className="border-b border-[var(--border-subtle)]/50">
                  <td className="py-1.5 pr-3">{rec.timestamp?.slice(0, 19).replace('T', ' ')}</td>
                  <td className="py-1.5 pr-3">{(rec.used_bytes / 1024 ** 3).toFixed(2)}</td>
                  <td className="py-1.5 pr-3">{rec.utilization_pct}%</td>
                  <td className="py-1.5 pr-3">
                    {rec.read_iops !== null ? rec.read_iops : 'N/A'} / {rec.write_iops !== null ? rec.write_iops : 'N/A'}
                  </td>
                  <td className="py-1.5 pr-3">{rec.latency_p95_ms !== null ? rec.latency_p95_ms : 'N/A'}</td>
                  <td className="py-1.5">
                    {rec.is_synthetic ? 'SYNTHETIC' : 'REAL'} ({rec.source_label})
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Dataset Cards */}
      <div className="grid grid-cols-1 gap-4">
        {datasets.map((ds) => (
          <div key={ds.id} className="titan-card rounded-xl p-5 space-y-4 hover:border-[var(--accent-primary)]/40 transition-all">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2.5">
                  {ds.name}
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/40 shadow-sm">
                    {ds.dataset_type}
                  </span>
                </h3>
                <div className="text-[11px] font-mono text-[var(--accent-primary)] mt-0.5">ID: {ds.id}</div>
              </div>

              <div className="text-xs font-mono text-[var(--status-success)] flex items-center gap-1.5">
                <CheckCircle2 size={14} />
                <span>Verified Schema Provenance</span>
              </div>
            </div>

            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{ds.description}</p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider block">Records Count</span>
                <span className="text-[var(--text-primary)] font-bold mt-1 block">{ds.records_count.toLocaleString()} samples</span>
              </div>

              <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider block">Sampling Interval</span>
                <span className="text-[var(--text-primary)] font-bold mt-1 block">{ds.sampling_interval_s} seconds (1h)</span>
              </div>

              <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider block">Missingness Rate</span>
                <span className="text-[var(--status-success)] font-bold mt-1 block">{(ds.missing_rate * 100).toFixed(2)}%</span>
              </div>

              <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider block">License & Citation</span>
                <span className="text-[var(--accent-primary)] font-bold mt-1 block truncate">{ds.license}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Provenance Ethics Statement */}
      <div className="titan-card rounded-xl p-5 text-xs text-[var(--text-secondary)] space-y-2">
        <h4 className="font-semibold text-[var(--text-primary)] flex items-center gap-2">
          <Info size={15} className="text-[var(--accent-primary)]" />
          Academic Rigor & Data Transparency Statement
        </h4>
        <p className="leading-relaxed">
          AEGISSTOR maintains explicit demarcation between synthetic, replay, and live physical telemetry. Synthetic datasets are deterministically generated using physics-informed workload generators and are labeled as synthetic across all APIs, database records, and visualization charts. Real-world host telemetry collection operates in strict read-only mode without destructive commands.
        </p>
      </div>
    </div>
  );
};
