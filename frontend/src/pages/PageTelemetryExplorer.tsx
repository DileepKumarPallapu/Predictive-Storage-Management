import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, TelemetryResponse } from '../api/client';
import { MetricChart } from '../components/MetricChart';
import { LineChart, Download, AlertTriangle, RefreshCw } from 'lucide-react';

export const PageTelemetryExplorer: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('vol-nvme-tier1-db');
  const [timeRangeHours, setTimeRangeHours] = useState<number>(168);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [perfData, setPerfData] = useState<any>(null);
  const [compareData, setCompareData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    api.getDevices()
      .then((list) => {
        setDevices(list);
        if (list.length > 0 && !list.some((d) => d.id === selectedDevice)) {
          setSelectedDevice(list[0].id);
        }
      })
      .catch(() => {});
  }, []);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const [tel, perf, cmp] = await Promise.all([
        api.getTelemetry(selectedDevice, 'used_bytes', timeRangeHours),
        api.getStoragePerformance(selectedDevice),
        api.compareStoragePerformance().catch(() => null),
      ]);
      setTelemetry(tel);
      setPerfData(perf);
      setCompareData(cmp);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDevice) loadAnalytics();
  }, [selectedDevice, timeRangeHours]);

  const series: any[] = perfData?.series || [];
  const summary = perfData?.summary || {};
  const labels = series.map((s) => s.timestamp || '');

  const renderSummaryMetric = (label: string, item: any) => {
    const avail = item?.available;
    const status = item?.status || (avail ? 'AVAILABLE' : 'UNAVAILABLE');
    return (
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-3.5">
        <div className="flex items-center justify-between gap-1 text-[11px] text-[var(--text-muted)]">
          <span>{label}</span>
          <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-[var(--surface-secondary)]">{status}</span>
        </div>
        <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-1">
          {avail ? item.display : item?.display || 'No data available'}
        </div>
        {avail && (
          <div className="text-[10px] font-mono text-[var(--text-muted)] mt-1">
            Avg {item.avg} · P95 {item.p95} · Max {item.max}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <LineChart size={20} className="text-[var(--brand-primary)]" />
            Performance Analytics
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Read/Write IOPS, Read/Write Latency, Throughput, threshold breaches, and multi-resource comparisons. Unavailable fields are surfaced explicitly without fabrication.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Select storage volume"
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-primary)]"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Time window"
            value={timeRangeHours}
            onChange={(e) => setTimeRangeHours(Number(e.target.value))}
            className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-primary)] font-mono"
          >
            <option value={24}>24h</option>
            <option value={168}>7 days</option>
            <option value={720}>30 days</option>
          </select>
          <button
            type="button"
            onClick={loadAnalytics}
            disabled={loading}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-primary)] hover:bg-[var(--surface-secondary)]"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => window.open(`/api/v1/telemetry/export?device_id=${selectedDevice}`, '_blank')}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded bg-[var(--brand-primary)] text-white hover:bg-[var(--brand-hover)]"
          >
            <Download size={13} />
            Export CSV
          </button>
        </div>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {renderSummaryMetric('Read IOPS', summary.read_iops)}
        {renderSummaryMetric('Write IOPS', summary.write_iops)}
        {renderSummaryMetric('Read Latency', summary.read_latency_ms)}
        {renderSummaryMetric('Write Latency', summary.write_latency_ms)}
        {renderSummaryMetric('Throughput', summary.throughput_mbps)}
      </div>

      {/* Dual Charts: IOPS & Latency/Throughput */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MetricChart
          title="IOPS History (Read vs Write)"
          labels={labels}
          series={[
            { id: 'riops', label: 'Read IOPS', color: 'var(--brand-primary)', values: series.map((s) => s.read_iops) },
            { id: 'wiops', label: 'Write IOPS', color: 'var(--status-info)', values: series.map((s) => s.write_iops) },
          ]}
          unit="IOPS"
          emptyMessage="No IOPS measurements recorded for this volume."
        />
        <MetricChart
          title="Latency & SLA Threshold History"
          labels={labels}
          series={[
            { id: 'rlat', label: 'Read Latency (ms)', color: 'var(--status-warning)', values: series.map((s) => s.read_latency_ms) },
            { id: 'wlat', label: 'Write Latency (ms)', color: 'var(--brand-primary)', dashed: true, values: series.map((s) => s.write_latency_ms) },
          ]}
          thresholdValue={perfData?.thresholds?.max_acceptable_latency_ms ?? null}
          thresholdLabel={`SLA (${perfData?.thresholds?.max_acceptable_latency_ms} ms)`}
          unit="ms"
          emptyMessage="No latency measurements recorded for this volume."
        />
      </div>

      {/* Multi-Resource Comparison Table */}
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Cross-Resource Performance Comparison</h3>
          <span className="text-[11px] font-mono text-[var(--text-muted)]">
            {telemetry?.is_synthetic ? 'Includes synthetic demo labels' : 'Real/Persisted telemetry'}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <th className="py-2 px-3">Resource</th>
                <th className="py-2 px-3">Util</th>
                <th className="py-2 px-3">Read IOPS</th>
                <th className="py-2 px-3">Write IOPS</th>
                <th className="py-2 px-3">P95 Latency</th>
                <th className="py-2 px-3">Throughput</th>
              </tr>
            </thead>
            <tbody>
              {(compareData?.volumes || []).map((v: any) => (
                <tr key={v.storage_id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                  <td className="py-2 px-3">
                    <div className="font-semibold">{v.name}</div>
                    <div className="text-[10px] font-mono text-[var(--text-muted)]">
                      {v.storage_id} {v.is_stale ? '· STALE' : ''}
                    </div>
                  </td>
                  <td className="py-2 px-3 font-mono">{v.metrics?.utilization_pct?.display}</td>
                  <td className="py-2 px-3 font-mono">{v.metrics?.read_iops?.display}</td>
                  <td className="py-2 px-3 font-mono">{v.metrics?.write_iops?.display}</td>
                  <td className="py-2 px-3 font-mono">{v.metrics?.latency_p95_ms?.display}</td>
                  <td className="py-2 px-3 font-mono">{v.metrics?.throughput_mbps?.display}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Threshold Breaches */}
      {perfData?.threshold_breaches?.length > 0 && (
        <div className="bg-[var(--surface-primary)] border border-[var(--status-critical)]/30 rounded-lg p-4 space-y-2">
          <h3 className="text-sm font-semibold text-[var(--status-critical)] flex items-center gap-1.5">
            <AlertTriangle size={15} />
            Latency SLA Breaches Detected ({perfData.threshold_breaches_count})
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 text-xs font-mono">
            {perfData.threshold_breaches.map((b: any, i: number) => (
              <div key={i} className="p-2 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)]">
                {b.timestamp?.slice(0, 19).replace('T', ' ')}: {b.observed_value} ms (limit {b.threshold} ms)
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
