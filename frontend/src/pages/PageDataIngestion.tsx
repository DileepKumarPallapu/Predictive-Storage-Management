import React, { useState, useEffect } from 'react';
import { api, DeviceSummary } from '../api/client';
import {
  Upload, Download, CheckCircle2, FileWarning, PlusCircle, Terminal, History, ArrowRight
} from 'lucide-react';

export const PageDataIngestion: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedStorage, setSelectedStorage] = useState<string>('vol-nvme-tier1-db');
  const [step, setStep] = useState<number>(1);
  const [filename, setFilename] = useState<string>('telemetry_upload.csv');
  const [csvText, setCsvText] = useState<string>('');
  const [validating, setValidating] = useState<boolean>(false);
  const [importing, setImporting] = useState<boolean>(false);
  const [previewResult, setPreviewResult] = useState<any>(null);
  const [importResult, setImportResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJobErrors, setSelectedJobErrors] = useState<{ jobId: string; errors: any[] } | null>(null);

  // Manual entry form
  const [manualTs, setManualTs] = useState<string>(new Date().toISOString().slice(0, 16) + ':00Z');
  const [manualUsedGb, setManualUsedGb] = useState<string>('500');
  const [manualReadIops, setManualReadIops] = useState<string>('');
  const [manualWriteIops, setManualWriteIops] = useState<string>('');
  const [manualReadLat, setManualReadLat] = useState<string>('');
  const [manualWriteLat, setManualWriteLat] = useState<string>('');
  const [manualThroughput, setManualThroughput] = useState<string>('');
  const [manualMsg, setManualMsg] = useState<string>('');
  const [demoRegime, setDemoRegime] = useState<string>('STABLE_GROWTH');
  const [demoHours, setDemoHours] = useState<number>(96);
  const [demoMsg, setDemoMsg] = useState<string>('');

  useEffect(() => {
    loadInitial();
  }, []);

  const loadInitial = async () => {
    try {
      const [devs, jobList] = await Promise.all([api.getDevices(), api.getIngestionJobs()]);
      setDevices(devs);
      setJobs(jobList);
      if (devs.length > 0 && !devs.some(d => d.id === selectedStorage)) {
        setSelectedStorage(devs[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleFileChoose = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFilename(file.name);
    setErrorMsg('');
    setImportResult(null);
    const reader = new FileReader();
    reader.onload = (ev) => {
      if (typeof ev.target?.result === 'string') {
        setCsvText(ev.target.result);
        setStep(2);
      }
    };
    reader.readAsText(file);
  };

  const handleValidateOnBackend = async () => {
    if (!csvText.trim()) {
      setErrorMsg('Please choose a CSV file or paste CSV records first.');
      return;
    }
    setValidating(true);
    setErrorMsg('');
    setImportResult(null);
    try {
      const res = await api.previewCsvImport(csvText, selectedStorage);
      setPreviewResult(res);
      setStep(res.errors?.length > 0 ? 4 : 3);
    } catch (e: any) {
      setErrorMsg(e.message || 'CSV validation failed');
    } finally {
      setValidating(false);
    }
  };

  const handleCommitImport = async () => {
    setImporting(true);
    setErrorMsg('');
    try {
      const res = await api.commitCsvImport(csvText, selectedStorage);
      if (res.job_id) {
        setImportResult(res);
        setStep(6);
        await loadInitial();
      } else {
        setErrorMsg(res.detail?.message || 'Import rejected by backend');
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'CSV import failed');
    } finally {
      setImporting(false);
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setManualMsg('');
    const dev = devices.find(d => d.id === selectedStorage);
    const usedNum = parseFloat(manualUsedGb);
    if (isNaN(usedNum) || usedNum < 0) {
      setManualMsg('Error: Used capacity must be a non-negative number.');
      return;
    }
    try {
      const res = await api.manualTelemetryEntry({
        storage_id: selectedStorage,
        timestamp: manualTs,
        total_capacity_bytes: dev?.total_capacity_bytes,
        used_capacity_bytes: Math.round(usedNum * (1024 ** 3)),
        read_iops: manualReadIops ? parseFloat(manualReadIops) : undefined,
        write_iops: manualWriteIops ? parseFloat(manualWriteIops) : undefined,
        read_latency_ms: manualReadLat ? parseFloat(manualReadLat) : undefined,
        write_latency_ms: manualWriteLat ? parseFloat(manualWriteLat) : undefined,
        throughput_mbps: manualThroughput ? parseFloat(manualThroughput) : undefined,
      });
      setManualMsg(`Saved reading at ${res.timestamp} (${res.utilization_pct}% utilized).`);
      loadInitial();
    } catch (err: any) {
      setManualMsg(`Error: ${err.message}`);
    }
  };

  const inspectJobErrors = async (jobId: string) => {
    try {
      const data = await api.getIngestionJobErrors(jobId);
      setSelectedJobErrors({ jobId, errors: data.errors || [] });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center">
              <Upload size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">Data Ingestion</h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            6-step CSV telemetry import workflow, manual measurement entry, import history, and REST collector setup.
          </p>
        </div>
        <a
          href={api.getCsvTemplateUrl()}
          download="aegisstor_telemetry_template.csv"
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90"
        >
          <Download size={14} /> Download CSV Template
        </a>
      </div>

      {/* Stepper Indicator */}
      <div className="titan-card rounded-xl p-4">
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-[11px] font-mono">
          {[
            '1. Choose CSV',
            '2. Validate File',
            '3. Preview Rows',
            '4. Review Errors',
            '5. Confirm Import',
            '6. Import Result',
          ].map((label, idx) => {
            const num = idx + 1;
            const active = step >= num;
            return (
              <div
                key={label}
                className={`px-2.5 py-2 rounded-lg border text-center ${
                  active
                    ? 'border-[var(--accent)] bg-[var(--brand-soft)] text-[var(--accent)] font-bold'
                    : 'border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-[var(--text-muted)]'
                }`}
              >
                {label}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main CSV Import Card */}
      <div className="titan-card rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="text-sm font-bold text-[var(--text-primary)]">CSV Upload & Backend Validation</h3>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-[var(--text-secondary)]">Fallback Storage Pool:</span>
            <select
              value={selectedStorage}
              onChange={(e) => setSelectedStorage(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] text-[var(--text-primary)]"
            >
              {devices.map(d => (
                <option key={d.id} value={d.id}>{d.name} ({d.id})</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <input type="file" accept=".csv,text/csv" onChange={handleFileChoose} className="text-xs text-[var(--text-secondary)]" />
          <span className="text-xs font-mono text-[var(--text-muted)]">Selected: {filename}</span>
        </div>

        <textarea
          rows={5}
          placeholder="timestamp,storage_id,total_capacity_bytes,used_capacity_bytes,read_iops,write_iops,read_latency_ms,write_latency_ms,throughput_mbps"
          value={csvText}
          onChange={(e) => { setCsvText(e.target.value); if (step < 2) setStep(2); }}
          className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-secondary)] p-3 text-xs font-mono text-[var(--text-primary)]"
        />

        {errorMsg && (
          <div className="p-3 rounded-lg border border-[var(--status-critical)] bg-[var(--status-critical)]/10 text-xs text-[var(--status-critical)]">
            {errorMsg}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleValidateOnBackend}
            disabled={validating}
            className="px-4 py-2 rounded-lg text-xs font-semibold border border-[var(--border-strong)] bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-[var(--surface-secondary)]"
          >
            {validating ? 'Validating...' : 'Validate & Preview on Backend'}
          </button>

          {previewResult && previewResult.accepted_rows > 0 && (
            <button
              onClick={() => { setStep(5); handleCommitImport(); }}
              disabled={importing}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white hover:opacity-90"
            >
              <ArrowRight size={14} />
              {importing ? 'Importing...' : `Confirm & Import ${previewResult.accepted_rows} Valid Rows`}
            </button>
          )}
        </div>

        {previewResult && (
          <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-secondary)] space-y-3 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 font-mono">
              <div>Total Rows: <strong>{previewResult.total_rows}</strong></div>
              <div className="text-[var(--status-success)]">Accepted: <strong>{previewResult.accepted_rows}</strong></div>
              <div className="text-[var(--status-warning)]">Duplicates: <strong>{previewResult.duplicate_rows}</strong></div>
              <div className="text-[var(--status-critical)]">Rejected: <strong>{previewResult.rejected_rows}</strong></div>
              <div>Completeness: <strong>{previewResult.data_completeness_pct}%</strong></div>
            </div>

            {previewResult.preview_rows?.length > 0 && (
              <div className="overflow-x-auto">
                <div className="text-[11px] font-semibold text-[var(--text-secondary)] mb-1">Preview (First {previewResult.preview_rows.length} Valid Records)</div>
                <table className="w-full text-[11px] font-mono text-left">
                  <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                    <tr>
                      <th className="py-1.5 pr-3">Row</th>
                      <th className="py-1.5 pr-3">Timestamp</th>
                      <th className="py-1.5 pr-3">Storage ID</th>
                      <th className="py-1.5 pr-3">Used (Bytes)</th>
                      <th className="py-1.5 pr-3">Util %</th>
                      <th className="py-1.5">Read/Write Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewResult.preview_rows.slice(0, 8).map((r: any, i: number) => (
                      <tr key={i} className="border-b border-[var(--border-subtle)]/50">
                        <td className="py-1.5 pr-3">{r.row_number}</td>
                        <td className="py-1.5 pr-3">{r.timestamp}</td>
                        <td className="py-1.5 pr-3">{r.storage_id}</td>
                        <td className="py-1.5 pr-3">{Number(r.used_bytes).toLocaleString()}</td>
                        <td className="py-1.5 pr-3">{r.utilization_pct}%</td>
                        <td className="py-1.5">{r.read_latency_ms ?? 'N/A'} / {r.write_latency_ms ?? 'N/A'} ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {previewResult.errors?.length > 0 && (
              <div className="space-y-1">
                <div className="font-semibold text-[var(--status-critical)] flex items-center gap-1.5">
                  <FileWarning size={14} /> Row-Level Errors & Duplicates:
                </div>
                <ul className="list-disc pl-5 font-mono text-[11px] text-[var(--text-secondary)] max-h-32 overflow-y-auto">
                  {previewResult.errors.map((err: any, i: number) => (
                    <li key={i}>Row {err.row_number} [{err.type}]: {err.reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {importResult && (
          <div className="p-4 rounded-xl border border-[var(--status-success)] bg-[var(--status-success)]/10 text-xs space-y-2">
            <div className="font-bold text-[var(--status-success)] flex items-center gap-1.5">
              <CheckCircle2 size={15} /> Backend Confirmed Import — Job {importResult.job_id} ({importResult.status})
            </div>
            <div className="font-mono text-[var(--text-primary)]">
              Accepted: {importResult.accepted_rows} | Rejected: {importResult.rejected_rows} | Duplicates: {importResult.duplicate_rows}
            </div>
            {(importResult.rejected_rows > 0 || importResult.duplicate_rows > 0) && (
              <a
                href={importResult.error_report_url}
                className="inline-block underline font-semibold text-[var(--accent)]"
              >
                Download Row-Level Error Report (CSV)
              </a>
            )}
          </div>
        )}
      </div>

      {/* Manual Entry + REST Collector Docs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <form onSubmit={handleManualSubmit} className="titan-card rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
            <PlusCircle size={16} className="text-[var(--accent)]" /> Manual Telemetry Entry
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Timestamp (UTC ISO)</label>
              <input type="text" value={manualTs} onChange={(e) => setManualTs(e.target.value)} required className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono" />
            </div>
            <div>
              <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Used Capacity (GB)</label>
              <input type="number" step="0.1" value={manualUsedGb} onChange={(e) => setManualUsedGb(e.target.value)} required className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono" />
            </div>
            <div>
              <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Read IOPS (optional)</label>
              <input type="number" step="0.1" value={manualReadIops} onChange={(e) => setManualReadIops(e.target.value)} placeholder="Leave blank if unavailable" className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono" />
            </div>
            <div>
              <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Write IOPS (optional)</label>
              <input type="number" step="0.1" value={manualWriteIops} onChange={(e) => setManualWriteIops(e.target.value)} placeholder="Leave blank if unavailable" className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono" />
            </div>
            <div>
              <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Read Latency ms (optional)</label>
              <input type="number" step="0.1" value={manualReadLat} onChange={(e) => setManualReadLat(e.target.value)} placeholder="Optional" className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono" />
            </div>
            <div>
              <label className="block text-[11px] text-[var(--text-secondary)] mb-1">Throughput MB/s (optional)</label>
              <input type="number" step="0.1" value={manualThroughput} onChange={(e) => setManualThroughput(e.target.value)} placeholder="Optional" className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono" />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button type="submit" className="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white">Submit Manual Record</button>
            {manualMsg && <span className="text-xs font-mono text-[var(--text-secondary)]">{manualMsg}</span>}
          </div>
        </form>

        <div className="titan-card rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Terminal size={16} className="text-[var(--accent)]" /> External Collector REST Integration
          </h3>
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
            Authenticated collectors (ADMIN / OPERATOR JWT Bearer token) push validated telemetry batches to <code className="font-mono">POST /api/v1/telemetry/ingest</code>:
          </p>
          <pre className="p-3 rounded-lg bg-[var(--surface-tertiary)] border border-[var(--border-subtle)] text-[11px] font-mono overflow-x-auto text-[var(--text-primary)]">
{`curl -X POST http://localhost:8000/api/v1/telemetry/ingest \\
  -H "Authorization: Bearer <JWT_TOKEN>" \\
  -H "Content-Type: application/json" \\
  -d '{"device_id": "${selectedStorage}", "records": [{"timestamp": "2026-11-11T12:00:00Z", "used_bytes": 500000000000, "free_bytes": 500000000000, "read_iops": 1200, "write_iops": 800, "throughput_mb_s": 210, "latency_p95_ms": 2.1, "queue_depth": 1.2, "is_synthetic": false}]}'`}
          </pre>
        </div>
      </div>

      {/* Clearly Labeled Synthetic Demo Telemetry Generator (Demo Mode Only) */}
      <div className="titan-card rounded-xl p-5 space-y-3 border border-[var(--status-warning)]/30">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-bold text-[var(--text-primary)]">
            SYNTHETIC DEMO TELEMETRY GENERATOR (Demo Mode Only)
          </h3>
          <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-[var(--status-warning)]/15 text-[var(--status-warning)]">
            IS_SYNTHETIC = TRUE · SEPARATED FROM LIVE/REPLAY
          </span>
        </div>
        <p className="text-xs text-[var(--text-secondary)]">
          For evaluating ML training on an empty demonstration volume. Blocked automatically in Live and Replay modes; all generated samples are tagged <code className="font-mono">is_synthetic=true</code>.
        </p>
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <select
            aria-label="Synthetic demo regime"
            value={demoRegime}
            onChange={(e) => setDemoRegime(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)]"
          >
            <option value="STABLE_GROWTH">STABLE_GROWTH</option>
            <option value="ACCELERATING_GROWTH">ACCELERATING_GROWTH</option>
            <option value="PERIODIC_SEASONAL">PERIODIC_SEASONAL</option>
            <option value="SUDDEN_BURST">SUDDEN_BURST</option>
            <option value="DECLINING_CONSUMPTION">DECLINING_CONSUMPTION</option>
          </select>
          <input
            type="number"
            min={24}
            max={720}
            value={demoHours}
            onChange={(e) => setDemoHours(Number(e.target.value))}
            className="w-24 px-2.5 py-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono"
          />
          <button
            type="button"
            onClick={async () => {
              setDemoMsg('');
              try {
                const res = await api.generateSyntheticDemo(selectedStorage, demoHours, demoRegime);
                setDemoMsg(`Inserted ${res.inserted_records} synthetic demo record(s) for ${selectedStorage}.`);
                loadInitial();
              } catch (e: any) {
                setDemoMsg(`Generator blocked/failed: ${e.message}`);
              }
            }}
            className="px-3.5 py-1.5 rounded-lg font-semibold border border-[var(--border-subtle)] bg-[var(--surface-secondary)] hover:bg-[var(--surface-tertiary)]"
          >
            Generate Synthetic Demo Series
          </button>
          {demoMsg && <span className="font-mono text-[var(--text-secondary)]">{demoMsg}</span>}
        </div>
      </div>

      {/* Import History */}
      <div className="titan-card rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
          <History size={16} className="text-[var(--accent)]" /> Ingestion History ({jobs.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left font-mono">
            <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)] text-[10px] uppercase">
              <tr>
                <th className="py-2 pr-3">Job ID</th>
                <th className="py-2 pr-3">Source</th>
                <th className="py-2 pr-3">Storage</th>
                <th className="py-2 pr-3">Accepted / Rejected / Dup</th>
                <th className="py-2 pr-3">Uploaded By</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} className="border-b border-[var(--border-subtle)]/50">
                  <td className="py-2 pr-3">{j.id}</td>
                  <td className="py-2 pr-3">{j.source_type}</td>
                  <td className="py-2 pr-3">{j.storage_id || 'multi'}</td>
                  <td className="py-2 pr-3">{j.accepted_rows} / {j.rejected_rows} / {j.duplicate_rows}</td>
                  <td className="py-2 pr-3">{j.uploaded_by}</td>
                  <td className="py-2 pr-3">{j.status}</td>
                  <td className="py-2 flex items-center gap-3">
                    {(j.rejected_rows > 0 || j.duplicate_rows > 0) ? (
                      <>
                        <button onClick={() => inspectJobErrors(j.id)} className="text-[var(--accent)] underline">Inspect Errors</button>
                        <a href={`/api/v1/ingestion/jobs/${j.id}/errors?format=csv`} className="text-[var(--text-secondary)] underline">CSV</a>
                      </>
                    ) : 'Clean'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {selectedJobErrors && (
          <div className="p-3 rounded-lg bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-xs font-mono space-y-1">
            <div className="font-bold">Errors for {selectedJobErrors.jobId}:</div>
            {selectedJobErrors.errors.map((e, i) => (
              <div key={i}>Row {e.row_number} [{e.type}]: {e.reason}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
