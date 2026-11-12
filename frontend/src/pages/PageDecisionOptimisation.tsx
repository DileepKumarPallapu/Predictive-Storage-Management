import React, { useEffect, useState } from 'react';
import { Sliders, CheckCircle2, XCircle, AlertCircle, DollarSign, ShieldCheck } from 'lucide-react';
import { api, DeviceSummary } from '../api/client';

export const PageDecisionOptimisation: React.FC = () => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string>('vol-nvme-tier1-db');
  const [maxUtil, setMaxUtil] = useState<number>(85);
  const [minFree, setMinFree] = useState<number>(15);
  const [maxLat, setMaxLat] = useState<number>(25);
  const [maxTransfer, setMaxTransfer] = useState<string>('');
  const [budgetUsd, setBudgetUsd] = useState<string>('');
  const [horizonDays, setHorizonDays] = useState<number>(30);
  const [includeUnitCosts, setIncludeUnitCosts] = useState<boolean>(false);
  const [expandPerGb, setExpandPerGb] = useState<number>(0.4);
  const [archivePerGb, setArchivePerGb] = useState<number>(0.12);
  const [migrationPerGb, setMigrationPerGb] = useState<number>(0.15);

  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

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

  const runOptimize = async () => {
    setLoading(true);
    setBanner(null);
    try {
      const payload: Record<string, any> = {
        max_utilization_pct: maxUtil,
        min_free_space_pct: minFree,
        max_latency_ms: maxLat,
        decision_horizon_days: horizonDays,
      };
      if (maxTransfer.trim() !== '') payload.max_transfer_gb = Number(maxTransfer);
      if (budgetUsd.trim() !== '') payload.budget_usd = Number(budgetUsd);
      if (includeUnitCosts) {
        payload.unit_costs = {
          expand_usd_per_gb: expandPerGb,
          archive_usd_per_gb: archivePerGb,
          migration_usd_per_gb: migrationPerGb,
          dedup_compute_usd: 25,
        };
      }
      const res = await api.optimizeInterventions(selectedId, payload);
      setResult(res);
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Optimization failed.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedId) runOptimize();
  }, [selectedId]);

  const handleGenerateRecommendations = async () => {
    setLoading(true);
    setBanner(null);
    try {
      const res = await api.generateRecommendations(selectedId);
      setBanner({
        type: 'success',
        text: `Generated ${res.generated_count} evidence-backed recommendation(s) for ${selectedId} (Reliability tier: ${res.data_reliability_tier}). Review & approve in Approval Centre.`,
      });
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Failed to generate recommendations (check operator/admin permissions).' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Sliders size={20} className="text-[var(--brand-primary)]" />
            Constrained Decision Optimisation
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Ranks feasible intervention alternatives strictly under explicit utilization, headroom, latency, transfer, and optional budget constraints. Zero cost fabrication when unit rates are omitted.
          </p>
        </div>
        <button
          type="button"
          onClick={handleGenerateRecommendations}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)] text-[var(--text-primary)]"
        >
          <ShieldCheck size={14} className="text-[var(--brand-primary)]" />
          Persist Ranked Recommendations
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

      {/* Constraints Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          runOptimize();
        }}
        className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-4"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          <div>
            <label className="block text-[11px] text-[var(--text-muted)] mb-1">Target Volume</label>
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="w-full px-2.5 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
            >
              {devices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] text-[var(--text-muted)] mb-1">Max Util (%)</label>
            <input
              type="number"
              value={maxUtil}
              onChange={(e) => setMaxUtil(Number(e.target.value))}
              className="w-full px-2.5 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
            />
          </div>
          <div>
            <label className="block text-[11px] text-[var(--text-muted)] mb-1">Min Free Margin (%)</label>
            <input
              type="number"
              value={minFree}
              onChange={(e) => setMinFree(Number(e.target.value))}
              className="w-full px-2.5 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
            />
          </div>
          <div>
            <label className="block text-[11px] text-[var(--text-muted)] mb-1">Max Latency (ms)</label>
            <input
              type="number"
              value={maxLat}
              onChange={(e) => setMaxLat(Number(e.target.value))}
              className="w-full px-2.5 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
            />
          </div>
          <div>
            <label className="block text-[11px] text-[var(--text-muted)] mb-1">Max Transfer (GB opt.)</label>
            <input
              type="number"
              value={maxTransfer}
              onChange={(e) => setMaxTransfer(e.target.value)}
              placeholder="Unlimited"
              className="w-full px-2.5 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
            />
          </div>
          <div>
            <label className="block text-[11px] text-[var(--text-muted)] mb-1">Horizon (Days)</label>
            <input
              type="number"
              min={1}
              max={180}
              value={horizonDays}
              onChange={(e) => setHorizonDays(Number(e.target.value))}
              className="w-full px-2.5 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-[var(--border-subtle)]">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <label className="inline-flex items-center gap-1.5 cursor-pointer text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={includeUnitCosts}
                onChange={(e) => setIncludeUnitCosts(e.target.checked)}
              />
              <DollarSign size={13} />
              Supply Unit Cost Model
            </label>
            {includeUnitCosts && (
              <>
                <input
                  type="number"
                  step="0.01"
                  value={budgetUsd}
                  onChange={(e) => setBudgetUsd(e.target.value)}
                  placeholder="Budget USD cap"
                  className="w-28 px-2 py-1 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
                />
                <span className="text-[11px] text-[var(--text-muted)] font-mono">
                  Expand $/GB:
                  <input
                    type="number"
                    step="0.01"
                    value={expandPerGb}
                    onChange={(e) => setExpandPerGb(Number(e.target.value))}
                    className="ml-1 w-16 px-1.5 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
                  />
                </span>
                <span className="text-[11px] text-[var(--text-muted)] font-mono">
                  Archive $/GB:
                  <input
                    type="number"
                    step="0.01"
                    value={archivePerGb}
                    onChange={(e) => setArchivePerGb(Number(e.target.value))}
                    className="ml-1 w-16 px-1.5 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
                  />
                </span>
                <span className="text-[11px] text-[var(--text-muted)] font-mono">
                  Migrate $/GB:
                  <input
                    type="number"
                    step="0.01"
                    value={migrationPerGb}
                    onChange={(e) => setMigrationPerGb(Number(e.target.value))}
                    className="ml-1 w-16 px-1.5 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
                  />
                </span>
              </>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-1.5 text-xs font-medium rounded bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white"
          >
            {loading ? 'Optimizing...' : 'Run Constrained Optimizer'}
          </button>
        </div>
      </form>

      {result && (
        <>
          <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div>
              <span className="font-semibold text-[var(--text-primary)]">Recommended Option: </span>
              <span className="font-mono font-bold text-[var(--brand-primary)]">
                {result.recommended_option ? result.recommended_option.title : 'NO FEASIBLE OPTION UNDER CURRENT CONSTRAINTS'}
              </span>
            </div>
            <div className="font-mono text-[11px] text-[var(--text-muted)]">
              Reliability: {result.data_reliability_tier} · {result.non_execution_notice}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
              <h3 className="text-sm font-semibold text-[var(--status-success)] flex items-center gap-1.5">
                <CheckCircle2 size={15} />
                Feasible Ranked Options ({result.feasible_candidates?.length || 0})
              </h3>
              {(result.feasible_candidates || []).map((c: any, idx: number) => (
                <div key={c.action_type} className="p-3 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-xs space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-[var(--text-primary)]">
                      #{idx + 1} {c.title}
                    </span>
                    <span className="font-mono px-2 py-0.5 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                      Score {c.rank_score}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[11px] font-mono text-[var(--text-secondary)]">
                    <span>Post Util: {c.projected_post_action.utilization_pct}%</span>
                    <span>P90 Util: {c.projected_post_action.adverse_p90_utilization_pct}%</span>
                    <span>Free Margin: {c.projected_post_action.free_space_pct}%</span>
                    <span>Cost: {c.estimated_cost_usd !== null ? `$${c.estimated_cost_usd}` : c.cost_status}</span>
                  </div>
                  {c.binding_constraints?.length > 0 && (
                    <div className="text-[11px] text-[var(--status-warning)]">
                      Near limits: {c.binding_constraints.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
              <h3 className="text-sm font-semibold text-[var(--status-critical)] flex items-center gap-1.5">
                <XCircle size={15} />
                Rejected Infeasible Options ({result.rejected_candidates?.length || 0})
              </h3>
              {(result.rejected_candidates || []).length === 0 ? (
                <p className="text-xs text-[var(--text-muted)]">All candidate strategies satisfy the active constraints.</p>
              ) : (
                (result.rejected_candidates || []).map((c: any) => (
                  <div key={c.action_type} className="p-3 rounded bg-[var(--surface-secondary)] border border-[var(--status-critical)]/30 text-xs space-y-1">
                    <div className="font-semibold text-[var(--text-primary)]">{c.title}</div>
                    <ul className="list-disc list-inside text-[11px] text-[var(--status-critical)]">
                      {(c.violation_reasons || []).map((v: string) => (
                        <li key={v}>{v}</li>
                      ))}
                    </ul>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
