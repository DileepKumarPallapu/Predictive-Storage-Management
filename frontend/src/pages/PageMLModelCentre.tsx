import React, { useState, useEffect, useRef } from 'react';
import { api, DeviceSummary } from '../api/client';
import { useRealtimeSubscription } from '../context/RealtimeContext';
import { Cpu, CheckCircle2, AlertTriangle, Play, RefreshCw, Award, Clock, Activity } from 'lucide-react';

export const PageMLModelCentre: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedStorage, setSelectedStorage] = useState<string>('vol-nvme-tier1-db');
  const [activeTab, setActiveTab] = useState<'LightGBM' | 'SARIMAX' | 'COMPARE'>('COMPARE');
  const [familyData, setFamilyData] = useState<any>(null);
  const [storageV2Models, setStorageV2Models] = useState<any[]>([]);
  const [dqInfo, setDqInfo] = useState<any>(null);
  const [regimeInfo, setRegimeInfo] = useState<any>(null);
  const [activeJob, setActiveJob] = useState<any>(null);
  const [training, setTraining] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string>('');
  const pollRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => {
    loadInitial();
    return () => stopPolling();
  }, []);

  useEffect(() => {
    if (selectedStorage) {
      loadStorageState(selectedStorage);
    }
  }, [selectedStorage]);

  useRealtimeSubscription(['model.', 'forecast.'], (evt) => {
    const p = evt.relevant_safe_payload || {};
    if (evt.event_type === 'model.training_queued' || evt.event_type === 'model.training_stage') {
      setActiveJob(p);
      setTraining(true);
    } else if (evt.event_type === 'model.training_completed') {
      setActiveJob(p);
      setTraining(false);
      setSuccessMsg(`Training completed: ${p.champion_model_type || p.champion_family || 'Champion'} (${p.version_tag || 'v2'})`);
      if (selectedStorage) loadStorageState(selectedStorage);
    } else if (evt.event_type === 'model.training_failed') {
      setActiveJob(p);
      setTraining(false);
      setErrorMsg(p.error_message || 'Model training failed');
    } else if (selectedStorage) {
      loadStorageState(selectedStorage);
    }
  });

  const loadInitial = async () => {
    try {
      const [list, fam] = await Promise.all([
        api.getDevices(),
        api.getV2ModelsByFamily().catch(() => null),
      ]);
      setDevices(list || []);
      setFamilyData(fam);
      if (list.length > 0 && !list.some((d) => d.id === selectedStorage)) {
        setSelectedStorage(list[0].id);
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to load model catalogue.');
    }
  };

  const loadStorageState = async (sid: string) => {
    setErrorMsg('');
    try {
      const [fam, v2Res, dqRes, regRes] = await Promise.all([
        api.getV2ModelsByFamily().catch(() => null),
        api.getV2ModelsForStorage(sid).catch(() => ({ versions: [] })),
        api.getDataQuality(sid).catch(() => null),
        api.getWorkloadRegime(sid).catch(() => null),
      ]);
      if (fam) setFamilyData(fam);
      setStorageV2Models(v2Res?.versions || []);
      setDqInfo(dqRes);
      setRegimeInfo(regRes);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to load model state');
    }
  };

  const handleStartAsyncTraining = async () => {
    stopPolling();
    setTraining(true);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      const queued = await api.trainV2ChampionChallengerAsync(selectedStorage);
      setActiveJob(queued);

      pollRef.current = window.setInterval(async () => {
        try {
          const status = await api.getBackgroundJobStatus(queued.job_id);
          setActiveJob(status);
          if (status.status === 'COMPLETED') {
            stopPolling();
            setTraining(false);
            setSuccessMsg(
              `Training job ${status.job_id} completed cleanly. Champion: ${status.result?.champion_model_type || 'Updated'}.`
            );
            await loadStorageState(selectedStorage);
          } else if (status.status === 'FAILED') {
            stopPolling();
            setTraining(false);
            setErrorMsg(status.error_message || 'Background training job failed; active champion model preserved.');
          }
        } catch (pollErr: any) {
          stopPolling();
          setTraining(false);
          setErrorMsg(pollErr.message || 'Failed polling background training job.');
        }
      }, 1200);
    } catch (e: any) {
      setTraining(false);
      setErrorMsg(e.message || 'Training request rejected (check OPERATOR/ADMIN role or history >= 60 records).');
    }
  };

  const eligible = (dqInfo?.valid_records ?? 0) >= 60;
  const families = familyData?.families || {};
  const lgbmFam = families.LightGBM;
  const sarimaxFam = families.SARIMAX;
  const recentJobs: any[] = familyData?.recent_jobs || [];

  const champModel = storageV2Models.find((m) => m.is_active && (m.model_type || '').startsWith('LGBM'))
    || storageV2Models.find((m) => (m.model_type || '').startsWith('LGBM'));
  const sarimaxModel = storageV2Models.find((m) => m.is_active && (m.model_type || '').startsWith('SARIMAX'))
    || storageV2Models.find((m) => (m.model_type || '').startsWith('SARIMAX'));

  const renderFamilyPage = (familyKey: 'LightGBM' | 'SARIMAX', famObj: any, perVolModel: any) => (
    <div className="space-y-4">
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] pb-3">
          <div>
            <h3 className="text-base font-bold text-[var(--text-primary)]">
              {familyKey === 'LightGBM' ? 'Model A: LightGBM Quantile / Conformal Regressor' : 'Model B: SARIMAX State-Space Time Series'}
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              {familyKey === 'LightGBM'
                ? 'Gradient-boosted multivariate tree learner on leak-free lag, rolling mean/std, cyclical calendar, and verified exogenous IOPS/latency features.'
                : 'Autoregressive integrated moving-average state-space estimator with cyclical Fourier covariates and sequential Kalman state updates.'}
            </p>
          </div>
          <span
            className={`px-2.5 py-1 rounded font-mono text-xs font-semibold ${
              perVolModel?.is_active
                ? 'bg-[var(--status-success)]/15 text-[var(--status-success)]'
                : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)]'
            }`}
          >
            {perVolModel ? (perVolModel.is_active ? 'CHAMPION FOR VOLUME' : perVolModel.status || 'CHALLENGER') : 'NOT TRAINED FOR VOLUME'}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="bg-[var(--surface-secondary)] p-3 rounded border border-[var(--border-subtle)]">
            <div className="text-[var(--text-muted)]">Fleet Coverage</div>
            <div className="font-mono font-bold text-sm text-[var(--text-primary)] mt-1">
              {famObj?.coverage_ratio || '0/0'} volumes
            </div>
          </div>
          <div className="bg-[var(--surface-secondary)] p-3 rounded border border-[var(--border-subtle)]">
            <div className="text-[var(--text-muted)]">Total Versions / Wins</div>
            <div className="font-mono font-bold text-sm text-[var(--text-primary)] mt-1">
              {famObj?.total_versions ?? 0} versions · {famObj?.champion_wins ?? 0} champion
            </div>
          </div>
          <div className="bg-[var(--surface-secondary)] p-3 rounded border border-[var(--border-subtle)]">
            <div className="text-[var(--text-muted)]">Drift State (Selected Vol)</div>
            <div className="font-mono font-bold text-sm text-[var(--text-primary)] mt-1">
              {regimeInfo?.regime_label || 'NOT_ANALYZED'}
            </div>
          </div>
          <div className="bg-[var(--surface-secondary)] p-3 rounded border border-[var(--border-subtle)]">
            <div className="text-[var(--text-muted)]">Empirical Interval Coverage</div>
            <div className="font-mono font-bold text-sm text-[var(--text-primary)] mt-1">
              {perVolModel?.metrics?.interval_coverage !== undefined
                ? `${(perVolModel.metrics.interval_coverage * 100).toFixed(1)}%`
                : 'N/A'}
            </div>
          </div>
        </div>

        {perVolModel && (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2.5 text-xs font-mono">
            <div className="p-2.5 rounded border border-[var(--border-subtle)]">
              <div className="text-[10px] text-[var(--text-muted)]">MAE (GB)</div>
              <div className="font-bold">{perVolModel.metrics?.mae ?? '—'}</div>
            </div>
            <div className="p-2.5 rounded border border-[var(--border-subtle)]">
              <div className="text-[10px] text-[var(--text-muted)]">RMSE (GB)</div>
              <div className="font-bold">{perVolModel.metrics?.rmse ?? '—'}</div>
            </div>
            <div className="p-2.5 rounded border border-[var(--border-subtle)]">
              <div className="text-[10px] text-[var(--text-muted)]">MASE</div>
              <div className="font-bold">{perVolModel.metrics?.mase ?? '—'}</div>
            </div>
            <div className="p-2.5 rounded border border-[var(--border-subtle)]">
              <div className="text-[10px] text-[var(--text-muted)]">Pinball Loss</div>
              <div className="font-bold">{perVolModel.metrics?.pinball_loss ?? '—'}</div>
            </div>
            <div className="p-2.5 rounded border border-[var(--border-subtle)]">
              <div className="text-[10px] text-[var(--text-muted)]">R² Score</div>
              <div className="font-bold">{perVolModel.metrics?.r2_score ?? '—'}</div>
            </div>
            <div className="p-2.5 rounded border border-[var(--border-subtle)]">
              <div className="text-[10px] text-[var(--text-muted)]">vs Naive Baseline</div>
              <div className="font-bold">{perVolModel.metrics?.vs_baseline_status || '—'}</div>
            </div>
          </div>
        )}

        {/* Version History Table */}
        <div>
          <h4 className="text-xs font-semibold text-[var(--text-primary)] mb-2">{familyKey} Training Version History</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                  <th className="py-2 px-3">Volume</th>
                  <th className="py-2 px-3">Version</th>
                  <th className="py-2 px-3">Data Window</th>
                  <th className="py-2 px-3">Train / Val</th>
                  <th className="py-2 px-3">RMSE</th>
                  <th className="py-2 px-3">MASE</th>
                  <th className="py-2 px-3">Coverage</th>
                  <th className="py-2 px-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {(famObj?.versions || []).length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-4 text-center text-[var(--text-muted)]">
                      No {familyKey} runs recorded yet. Trigger asynchronous training above on an eligible volume (&gt;= 60 samples).
                    </td>
                  </tr>
                ) : (
                  (famObj?.versions || []).map((v: any) => (
                    <tr key={v.id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                      <td className="py-2 px-3 font-mono">{v.storage_id}</td>
                      <td className="py-2 px-3 font-mono">{v.version_tag}</td>
                      <td className="py-2 px-3 font-mono text-[11px] text-[var(--text-muted)]">
                        {v.train_start_at ? v.train_start_at.slice(0, 10) : '?'} → {v.train_end_at ? v.train_end_at.slice(0, 10) : '?'}
                      </td>
                      <td className="py-2 px-3 font-mono">
                        {v.train_samples} / {v.validation_samples}
                      </td>
                      <td className="py-2 px-3 font-mono">{v.metrics?.rmse ?? '—'}</td>
                      <td className="py-2 px-3 font-mono">{v.metrics?.mase ?? '—'}</td>
                      <td className="py-2 px-3 font-mono">
                        {v.metrics?.interval_coverage !== undefined ? `${(v.metrics.interval_coverage * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-2 px-3 font-mono">{v.is_champion ? 'CHAMPION' : v.status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Cpu size={20} className="text-[var(--brand-primary)]" />
            ML Model Centre — Champion-Challenger Governance
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Dedicated operational evaluation of LightGBM vs SARIMAX against Seasonal-Naive using chronological 3-way splits, Split Conformal calibration, and real async background jobs.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Select training target volume"
            value={selectedStorage}
            onChange={(e) => setSelectedStorage(e.target.value)}
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
            onClick={handleStartAsyncTraining}
            disabled={training}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium rounded-md bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white disabled:opacity-60"
          >
            {training ? <RefreshCw size={13} className="animate-spin" /> : <Play size={13} />}
            {training ? 'Training Background Job...' : 'Train LightGBM vs SARIMAX (Async)'}
          </button>
        </div>
      </div>

      {/* Real Background Job Progress Banner */}
      {activeJob && (
        <div className="p-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-secondary)] text-xs flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 font-mono">
            <Clock size={14} className={activeJob.status === 'RUNNING' || activeJob.status === 'QUEUED' ? 'animate-spin text-[var(--brand-primary)]' : 'text-[var(--status-success)]'} />
            <span>Job {activeJob.job_id}:</span>
            <span className="font-bold text-[var(--text-primary)]">{activeJob.status}</span>
          </div>
          <span className="text-[11px] font-mono text-[var(--text-muted)]">Target: {activeJob.storage_id}</span>
        </div>
      )}

      {!eligible && (
        <div className="p-3 rounded-lg border border-[var(--status-warning)]/30 bg-[var(--status-warning)]/10 text-xs text-[var(--status-warning)] flex items-center gap-2">
          <AlertTriangle size={15} />
          Volume {selectedStorage} currently has {dqInfo?.valid_records ?? 0} telemetry records (minimum 60 required for Champion-Challenger LightGBM/SARIMAX training). Existing active models are preserved.
        </div>
      )}

      {errorMsg && (
        <div className="p-3 rounded-lg border border-[var(--status-critical)]/30 bg-[var(--brand-soft)] text-xs text-[var(--status-critical)]">
          {errorMsg}
        </div>
      )}

      {successMsg && (
        <div className="p-3 rounded-lg border border-[var(--status-success)]/30 bg-[var(--status-success)]/10 text-xs text-[var(--status-success)] flex items-center gap-2">
          <CheckCircle2 size={15} />
          {successMsg}
        </div>
      )}

      {/* Sub-navigation tabs: Separate Model Pages for LightGBM & SARIMAX */}
      <div className="flex flex-wrap gap-2 border-b border-[var(--border-subtle)] pb-2">
        {(['COMPARE', 'LightGBM', 'SARIMAX'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              activeTab === tab
                ? 'bg-[var(--brand-primary)] text-white'
                : 'bg-[var(--surface-primary)] text-[var(--text-secondary)] border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)]'
            }`}
          >
            {tab === 'COMPARE' ? 'Champion-Challenger Overview' : `${tab} Model Page`}
          </button>
        ))}
      </div>

      {activeTab === 'LightGBM' && renderFamilyPage('LightGBM', lgbmFam, champModel)}
      {activeTab === 'SARIMAX' && renderFamilyPage('SARIMAX', sarimaxFam, sarimaxModel)}

      {activeTab === 'COMPARE' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[
              { title: 'Model A: LightGBM (LGBMRegressor)', model: champModel, fam: lgbmFam },
              { title: 'Model B: SARIMAX (State-Space)', model: sarimaxModel, fam: sarimaxFam },
            ].map(({ title, model, fam }) => (
              <div key={title} className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">{title}</h3>
                  {model?.is_active ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[var(--status-success)]/15 text-[var(--status-success)] font-mono text-[11px] font-bold">
                      <Award size={12} /> CHAMPION
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded bg-[var(--surface-secondary)] text-[var(--text-muted)] font-mono text-[11px]">
                      {model ? model.status : 'NOT TRAINED'}
                    </span>
                  )}
                </div>
                {model ? (
                  <div className="space-y-2 text-xs font-mono">
                    <div className="grid grid-cols-3 gap-2">
                      <div>MAE: {model.metrics?.mae ?? '—'} GB</div>
                      <div>RMSE: {model.metrics?.rmse ?? '—'} GB</div>
                      <div>MASE: {model.metrics?.mase ?? '—'}</div>
                      <div>Pinball: {model.metrics?.pinball_loss ?? '—'}</div>
                      <div>Coverage: {model.metrics?.interval_coverage ? `${(model.metrics.interval_coverage * 100).toFixed(1)}%` : '—'}</div>
                      <div>MAPE: {model.metrics?.mape !== null && model.metrics?.mape !== undefined ? `${model.metrics.mape}%` : 'N/A'}</div>
                    </div>
                    <p className="text-[11px] font-sans text-[var(--text-secondary)] border-t border-[var(--border-subtle)] pt-2">
                      {model.metrics?.selection_reason || 'No selection note.'}
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-[var(--text-muted)]">
                    No trained version yet for {selectedStorage}. Fleet coverage: {fam?.coverage_ratio || '0/0'}.
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Async Training Jobs Ledger */}
          <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-2">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
              <Activity size={14} className="text-[var(--brand-primary)]" />
              Backend Training Job Queue & History
            </h3>
            {recentJobs.length === 0 ? (
              <p className="text-xs text-[var(--text-muted)]">No async training jobs submitted yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                      <th className="py-2 px-3">Job ID</th>
                      <th className="py-2 px-3">Storage</th>
                      <th className="py-2 px-3">Status</th>
                      <th className="py-2 px-3">Triggered By</th>
                      <th className="py-2 px-3">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentJobs.slice(0, 10).map((j) => (
                      <tr key={j.job_id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                        <td className="py-1.5 px-3 font-mono">{j.job_id}</td>
                        <td className="py-1.5 px-3 font-mono">{j.storage_id}</td>
                        <td className="py-1.5 px-3 font-mono font-semibold">{j.status}</td>
                        <td className="py-1.5 px-3 font-mono">{j.triggered_by}</td>
                        <td className="py-1.5 px-3 font-mono text-[var(--text-muted)]">{j.created_at?.slice(0, 19).replace('T', ' ')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
