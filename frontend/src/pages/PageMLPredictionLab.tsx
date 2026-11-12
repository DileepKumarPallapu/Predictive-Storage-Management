import React, { useState, useEffect } from 'react';
import { api, DeviceSummary } from '../api/client';
import { MetricChart } from '../components/MetricChart';
import { Brain, RefreshCw, AlertCircle, CheckCircle2, Layers } from 'lucide-react';

export const PageMLPredictionLab: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string>('vol-nvme-tier1-db');
  const [horizonDays, setHorizonDays] = useState<number>(30);
  const [historyData, setHistoryData] = useState<any>(null);
  const [generatedForecast, setGeneratedForecast] = useState<any>(null);
  const [compareForecastId, setCompareForecastId] = useState<string>('');
  const [reliability, setReliability] = useState<any>(null);
  const [regime, setRegime] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [generating, setGenerating] = useState<boolean>(false);
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

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

  const loadWorkspace = async (sid: string) => {
    setLoading(true);
    setBanner(null);
    try {
      const [histRes, relRes, regRes] = await Promise.all([
        api.getV2ForecastHistory(sid),
        api.getDataReliability(sid).catch(() => null),
        api.getWorkloadRegime(sid).catch(() => null),
      ]);
      setHistoryData(histRes);
      setReliability(relRes);
      setRegime(regRes);
      setGeneratedForecast(null);
      setCompareForecastId('');
    } catch (e: any) {
      setBanner({ type: 'error', text: e.message || 'Failed to load Forecast Studio context.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDevice) loadWorkspace(selectedDevice);
  }, [selectedDevice]);

  const handleGenerate = async () => {
    setGenerating(true);
    setBanner(null);
    try {
      const res = await api.generateV2Forecast(selectedDevice, horizonDays, true);
      setGeneratedForecast(res);
      setBanner({
        type: 'success',
        text: `Generated ${horizonDays}-day Split Conformal forecast using Champion ${res.champion_model_type}. Saved as Forecast #${res.forecast_id}.`,
      });
      const updatedHist = await api.getV2ForecastHistory(selectedDevice);
      setHistoryData(updatedHist);
    } catch (e: any) {
      setBanner({ type: 'error', text: e.message || 'Forecast generation failed.' });
    } finally {
      setGenerating(false);
    }
  };

  const savedForecasts: any[] = historyData?.saved_forecasts || [];
  const activeForecastSeries: any[] = generatedForecast?.series || savedForecasts[0]?.series || [];
  const compareForecast = savedForecasts.find((f) => String(f.forecast_id) === compareForecastId) || null;
  const historicalActuals: any[] = (historyData?.historical_actuals || []).slice(-48);
  const currentDevice = devices.find((d) => d.id === selectedDevice);
  const totalCapGb = historyData?.total_capacity_gb || (currentDevice ? currentDevice.total_capacity_bytes / 1024 ** 3 : 0);
  const critGb = totalCapGb && currentDevice ? (totalCapGb * currentDevice.critical_threshold_pct) / 100 : null;

  // Build aligned timeline clearly separating Historical Actuals from Future Predictions
  const actualLabels = historicalActuals.map((a) => a.timestamp || '');
  const forecastLabels = activeForecastSeries.map((f) => f.timestamp || '');
  const combinedLabels = [...actualLabels, ...forecastLabels];

  const actualValues: (number | null)[] = [
    ...historicalActuals.map((a) => Number(a.used_gb)),
    ...forecastLabels.map(() => null),
  ];
  const p50Values: (number | null)[] = [
    ...actualLabels.map((_, idx) => (idx === actualLabels.length - 1 ? Number(historicalActuals[idx].used_gb) : null)),
    ...activeForecastSeries.map((f) => f.p50_used_gb),
  ];
  const p10Values: (number | null)[] = [
    ...actualLabels.map(() => null),
    ...activeForecastSeries.map((f) => f.p10_used_gb),
  ];
  const p90Values: (number | null)[] = [
    ...actualLabels.map(() => null),
    ...activeForecastSeries.map((f) => f.p90_used_gb),
  ];

  const chartSeries: any[] = [
    { id: 'actual', label: 'Historical Actual (Observed)', color: 'var(--chart-observation)', values: actualValues },
    { id: 'p50', label: 'Predicted P50 (Forecast)', color: 'var(--brand-primary)', dashed: true, values: p50Values },
  ];

  if (compareForecast) {
    const compSeries: any[] = compareForecast.series || [];
    const compAligned: (number | null)[] = [
      ...actualLabels.map(() => null),
      ...forecastLabels.map((_, idx) => (idx < compSeries.length ? compSeries[idx].p50_used_gb : null)),
    ];
    chartSeries.push({
      id: 'compare',
      label: `Comparison #${compareForecast.forecast_id} (${compareForecast.model_name})`,
      color: 'var(--status-info)',
      dashed: true,
      values: compAligned,
    });
  }

  const activeMeta = generatedForecast || savedForecasts[0];
  const valMetrics = activeMeta?.validation_metrics || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Brain size={20} className="text-[var(--brand-primary)]" />
            Forecast Studio
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Multi-horizon P10/P50/P90 forecasts calibrated via Split Conformal Prediction and Data Reliability scaling. Historical actuals remain strictly separated from future predictions.
          </p>
        </div>
      </div>

      {/* Workspace Control Strip */}
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
        <div>
          <label className="block text-[11px] font-medium text-[var(--text-muted)] mb-1">Storage Volume</label>
          <select
            aria-label="Forecast target storage"
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="w-full px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-[11px] font-medium text-[var(--text-muted)] mb-1">Forecast Horizon</label>
          <select
            aria-label="Forecast horizon days"
            value={horizonDays}
            onChange={(e) => setHorizonDays(Number(e.target.value))}
            className="w-full px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
          >
            {[1, 7, 14, 30, 60, 90].map((d) => (
              <option key={d} value={d}>
                {d} Day{d > 1 ? 's' : ''}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-[11px] font-medium text-[var(--text-muted)] mb-1">Compare Saved Version</label>
          <select
            aria-label="Compare forecast version"
            value={compareForecastId}
            onChange={(e) => setCompareForecastId(e.target.value)}
            className="w-full px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
          >
            <option value="">No Overlay</option>
            {savedForecasts.map((f) => (
              <option key={f.forecast_id} value={String(f.forecast_id)}>
                #{f.forecast_id} · {f.model_name} ({f.horizon_days}d)
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generating || loading}
          className="inline-flex items-center justify-center gap-1.5 px-4 py-1.5 text-xs font-medium rounded bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white disabled:opacity-60"
        >
          <RefreshCw size={13} className={generating ? 'animate-spin' : ''} />
          {generating ? 'Forecasting...' : 'Generate Conformal Forecast'}
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
          {banner.type === 'success' ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
          {banner.text}
        </div>
      )}

      {/* Telemetry + Reliability + Regime Context Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-3">
          <div className="text-[11px] text-[var(--text-muted)]">Model & Calibration</div>
          <div className="text-xs font-mono font-bold text-[var(--text-primary)] mt-1">
            {activeMeta?.champion_model_type || activeMeta?.model_name || 'Generate to inspect'}
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">Split Conformal Prediction</div>
        </div>
        <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-3">
          <div className="text-[11px] text-[var(--text-muted)]">Holdout Error (RMSE / MASE)</div>
          <div className="text-xs font-mono font-bold text-[var(--text-primary)] mt-1">
            {valMetrics.rmse !== undefined && valMetrics.rmse !== null ? `${valMetrics.rmse} GB` : '—'} /{' '}
            {valMetrics.mase ?? '—'}
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
            Coverage: {valMetrics.interval_coverage ? `${(valMetrics.interval_coverage * 100).toFixed(1)}%` : '—'}
          </div>
        </div>
        <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-3">
          <div className="text-[11px] text-[var(--text-muted)]">Data Reliability Score</div>
          <div className="text-xs font-mono font-bold text-[var(--text-primary)] mt-1">
            {reliability ? `${(reliability.reliability_score * 100).toFixed(1)}% (${reliability.reliability_tier})` : '—'}
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
            Band Multiplier: x{reliability?.uncertainty_multiplier ?? 1.0}
          </div>
        </div>
        <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-3">
          <div className="text-[11px] text-[var(--text-muted)]">Workload Regime</div>
          <div className="text-xs font-mono font-bold text-[var(--text-primary)] mt-1">
            {regime?.regime_label || 'NOT_ANALYZED'}
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">Slope: {regime?.metrics?.overall_slope_pct_per_day ?? '—'}%/d</div>
        </div>
      </div>

      {/* Historical vs Future Prediction Chart */}
      <MetricChart
        title="Observed History (Solid) vs Calibrated Future Capacity Trajectory (Dashed)"
        subtitle="Quantiles P10 / P50 / P90 widen with sqrt(horizon) and Data Reliability uncertainty factor."
        labels={combinedLabels}
        series={chartSeries}
        bandLower={p10Values}
        bandUpper={p90Values}
        bandLabel="P10–P90 Conformal Uncertainty"
        thresholdValue={critGb}
        thresholdLabel={critGb ? `Critical (${currentDevice?.critical_threshold_pct}% = ${critGb.toFixed(0)} GB)` : undefined}
        unit="GB"
        height={260}
      />

      {/* Previous Saved Forecasts Version Table */}
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
          <Layers size={15} className="text-[var(--brand-primary)]" />
          Persisted Forecast Versions ({savedForecasts.length})
        </h3>
        {savedForecasts.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No persisted forecasts yet for {selectedDevice}. Click Generate above.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                  <th className="py-2 px-3">ID</th>
                  <th className="py-2 px-3">Model</th>
                  <th className="py-2 px-3">Horizon</th>
                  <th className="py-2 px-3">Generated At</th>
                  <th className="py-2 px-3">End P10 / P50 / P90 (GB)</th>
                  <th className="py-2 px-3">Coverage</th>
                </tr>
              </thead>
              <tbody>
                {savedForecasts.map((f) => {
                  const lastPt = f.series?.[f.series.length - 1];
                  return (
                    <tr key={f.forecast_id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                      <td className="py-2 px-3 font-mono">#{f.forecast_id}</td>
                      <td className="py-2 px-3 font-mono font-semibold">{f.model_name}</td>
                      <td className="py-2 px-3 font-mono">{f.horizon_days} days</td>
                      <td className="py-2 px-3 font-mono text-[var(--text-muted)]">{f.generated_at?.slice(0, 19).replace('T', ' ')}</td>
                      <td className="py-2 px-3 font-mono">
                        {lastPt ? `${lastPt.p10_used_gb?.toFixed(1)} / ${lastPt.p50_used_gb?.toFixed(1)} / ${lastPt.p90_used_gb?.toFixed(1)}` : '—'}
                      </td>
                      <td className="py-2 px-3 font-mono">{((f.interval_coverage || 0.8) * 100).toFixed(1)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
