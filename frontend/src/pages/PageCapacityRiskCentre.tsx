import React, { useEffect, useState } from 'react';
import { ShieldAlert, RefreshCw, AlertCircle, Calendar, Percent } from 'lucide-react';
import { api, DeviceSummary } from '../api/client';

export const PageCapacityRiskCentre: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string>('vol-nvme-tier1-db');
  const [horizonDays, setHorizonDays] = useState<number>(30);
  const [thresholdPct, setThresholdPct] = useState<number>(85);
  const [riskData, setRiskData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
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

  const runRiskEvaluation = async (sid: string, hDays: number, thr: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.evaluateCapacityRisk(sid, hDays, thr);
      setRiskData(res);
    } catch (err: any) {
      setError(err.message || 'Capacity risk evaluation requires >= 60 telemetry records.');
      setRiskData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedId) runRiskEvaluation(selectedId, horizonDays, thresholdPct);
  }, [selectedId]);

  const details = riskData?.details || {};
  const bandColor =
    riskData?.risk_band === 'CRITICAL'
      ? 'text-[var(--status-critical)] bg-[var(--brand-soft)]'
      : riskData?.risk_band === 'HIGH'
        ? 'text-[var(--status-warning)] bg-[var(--status-warning)]/15'
        : 'text-[var(--status-success)] bg-[var(--status-success)]/15';

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <ShieldAlert size={20} className="text-[var(--brand-primary)]" />
            Capacity Risk Centre
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Probabilistic safety-threshold crossing probability from empirical calibration residuals, validated via Brier score, expected shortfall, and exhaustion horizon.
          </p>
        </div>
      </div>

      {/* Controls Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          runRiskEvaluation(selectedId, horizonDays, thresholdPct);
        }}
        className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end"
      >
        <div>
          <label className="block text-[11px] font-medium text-[var(--text-muted)] mb-1">Storage Volume</label>
          <select
            aria-label="Risk volume selector"
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="w-full px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-[var(--text-primary)]"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-[11px] font-medium text-[var(--text-muted)] mb-1">Evaluation Horizon (Days)</label>
          <select
            aria-label="Evaluation horizon"
            value={horizonDays}
            onChange={(e) => setHorizonDays(Number(e.target.value))}
            className="w-full px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-[var(--text-primary)] font-mono"
          >
            {[7, 14, 30, 60, 90].map((d) => (
              <option key={d} value={d}>
                {d} days
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-[11px] font-medium text-[var(--text-muted)] mb-1">Safety Threshold (%)</label>
          <input
            type="number"
            min={10}
            max={99}
            step={1}
            value={thresholdPct}
            onChange={(e) => setThresholdPct(Number(e.target.value))}
            className="w-full px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-[var(--text-primary)] font-mono"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center justify-center gap-1.5 px-4 py-1.5 text-xs font-medium rounded bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Evaluating...' : 'Compute Probabilistic Risk'}
        </button>
      </form>

      {error && (
        <div className="p-3 rounded-lg border border-[var(--status-critical)]/30 bg-[var(--brand-soft)] text-xs text-[var(--status-critical)] flex items-center gap-2">
          <AlertCircle size={15} />
          {error}
        </div>
      )}

      {riskData && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4">
              <div className="text-[11px] text-[var(--text-muted)]">Risk Posture Band</div>
              <div className="mt-1.5">
                <span className={`px-2.5 py-1 rounded font-mono text-sm font-bold ${bandColor}`}>{riskData.risk_band}</span>
              </div>
              <div className="text-[11px] text-[var(--text-muted)] mt-2">
                Current: {riskData.current_utilization_pct}% → P50: {riskData.forecasted_utilization_pct}%
              </div>
            </div>

            <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4">
              <div className="text-[11px] text-[var(--text-muted)] flex items-center gap-1">
                <Percent size={12} /> Crossing Probability (Residual CDF)
              </div>
              <div className="text-2xl font-bold font-mono text-[var(--text-primary)] mt-1">
                {(riskData.threshold_crossing_probability * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] text-[var(--text-muted)] mt-1">
                Brier Calibration Score: {details.brier_calibration_score ?? 'N/A'} (lower = better)
              </div>
            </div>

            <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4">
              <div className="text-[11px] text-[var(--text-muted)]">Adverse P90 Utilization / Shortfall</div>
              <div className="text-2xl font-bold font-mono text-[var(--text-primary)] mt-1">
                {riskData.adverse_p90_utilization_pct}%
              </div>
              <div className="text-[11px] text-[var(--text-muted)] mt-1">
                Expected Shortfall: {(riskData.expected_shortfall_bytes / 1024 ** 3).toFixed(2)} GB
              </div>
            </div>

            <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4">
              <div className="text-[11px] text-[var(--text-muted)] flex items-center gap-1">
                <Calendar size={12} /> Projected Breach Dates
              </div>
              <div className="text-xs font-mono text-[var(--text-primary)] mt-1.5 space-y-1">
                <div>
                  Safety ({thresholdPct}%):{' '}
                  <span className="font-bold">
                    {riskData.safety_threshold_crossing_date ? riskData.safety_threshold_crossing_date.slice(0, 10) : 'Not breached in window'}
                  </span>
                </div>
                <div>
                  Exhaustion (100%):{' '}
                  <span className="font-bold">
                    {riskData.exhaustion_date ? riskData.exhaustion_date.slice(0, 10) : 'Not within 365d'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-2 text-xs">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Supporting Evidence & Calibration Context</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 font-mono text-[var(--text-secondary)]">
              <div>Remaining Safe Headroom: {(riskData.remaining_safe_capacity_bytes / 1024 ** 3).toFixed(2)} GB</div>
              <div>Daily Growth Rate: {details.daily_projected_growth_gb ?? '0'} GB/day</div>
              <div>Data Reliability Score: {(riskData.data_reliability_score * 100).toFixed(1)}%</div>
              <div>Champion Model: {details.champion_family || 'N/A'}</div>
              <div>Workload Regime: {details.workload_regime || 'N/A'}</div>
              <div>Empirical Residuals Used: {details.residual_sample_size ?? 0} holdout points</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
