import React, { useEffect, useState } from 'react';
import { ClipboardCheck, CheckCircle2, XCircle, AlertCircle, RefreshCw, Shield } from 'lucide-react';
import { api, AuditItem } from '../api/client';
import { useRealtimeSubscription } from '../context/RealtimeContext';

export const PageApprovalCentre: React.FC = () => {
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [noteInput, setNoteInput] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [recRes, auditRes] = await Promise.all([
        api.listAllRecommendations(),
        api.getAuditTrail().catch(() => []),
      ]);
      setRecommendations(recRes.recommendations || []);
      setAuditLogs(
        (auditRes || []).filter((a: AuditItem) =>
          ['APPROVE_RECOMMENDATION', 'REJECT_RECOMMENDATION', 'COMPLETE_RECOMMENDATION', 'FAIL_RECOMMENDATION', 'GENERATE_RECOMMENDATIONS'].includes(
            a.action
          )
        )
      );
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Failed to load approval queue.' });
    } finally {
      setLoading(false);
    }
  };

  useRealtimeSubscription(['approval.', 'recommendation.'], () => {
    loadData();
  });

  useEffect(() => {
    loadData();
  }, []);

  const runAction = async (recId: string, action: 'approve' | 'reject' | 'complete' | 'fail') => {
    setBusyId(recId);
    setBanner(null);
    const notes = noteInput[recId]?.trim() || undefined;
    try {
      let res: any;
      if (action === 'approve') res = await api.approveRecommendation(recId, notes || 'Approved via Approval Centre (shadow-only).');
      else if (action === 'reject') res = await api.rejectRecommendation(recId, notes || 'Rejected via Approval Centre.');
      else if (action === 'complete') res = await api.completeRecommendation(recId, notes);
      else res = await api.failRecommendation(recId, notes);
      setBanner({
        type: 'success',
        text: `${res.message || 'Updated'} Status: ${res.status}. Physical mutation executed: false.`,
      });
      await loadData();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || `Action '${action}' failed.` });
    } finally {
      setBusyId(null);
    }
  };

  const filtered = recommendations.filter((r) => statusFilter === 'ALL' || r.approval_status === statusFilter);

  const badgeStyle = (st: string) => {
    if (st === 'COMPLETED' || st === 'APPROVED_SHADOW' || st === 'APPROVED') return 'bg-[var(--status-success)]/15 text-[var(--status-success)]';
    if (st === 'REJECTED' || st === 'FAILED') return 'bg-[var(--brand-soft)] text-[var(--status-critical)]';
    return 'bg-[var(--status-warning)]/15 text-[var(--status-warning)]';
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <ClipboardCheck size={20} className="text-[var(--brand-primary)]" />
            Human-in-the-Loop Approval Centre
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Track recommendation approvals, rejections, offline completion confirmation, and immutable audit entries. AEGISSTOR never mutates live storage hardware.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            aria-label="Filter approval status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-xs rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)]"
          >
            <option value="ALL">All States</option>
            <option value="PENDING_REVIEW">PENDING_REVIEW</option>
            <option value="APPROVED_SHADOW">APPROVED_SHADOW</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="REJECTED">REJECTED</option>
            <option value="FAILED">FAILED</option>
          </select>
          <button
            type="button"
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)]"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
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

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-6 text-center text-xs text-[var(--text-muted)]">
            No recommendations match filter '{statusFilter}'. Generate recommendations in Recommendations or Decision Optimisation.
          </div>
        ) : (
          filtered.map((rec) => {
            const st = rec.approval_status || 'PENDING_REVIEW';
            return (
              <div key={rec.id} className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-2.5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-sm text-[var(--text-primary)]">{rec.title}</span>
                      <span className={`px-2 py-0.5 rounded font-mono text-[11px] font-semibold ${badgeStyle(st)}`}>{st}</span>
                      <span className="text-[11px] font-mono text-[var(--text-muted)]">{rec.device_id}</span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] mt-1">{rec.rationale}</p>
                    {rec.review_notes && (
                      <p className="text-[11px] text-[var(--text-muted)] mt-1 font-mono">
                        Review note ({rec.reviewed_by || 'operator'}): {rec.review_notes}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-[var(--border-subtle)]">
                  <input
                    type="text"
                    placeholder="Optional review / audit note..."
                    value={noteInput[rec.id] || ''}
                    onChange={(e) => setNoteInput((prev) => ({ ...prev, [rec.id]: e.target.value }))}
                    className="flex-1 min-w-[180px] px-2.5 py-1 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
                  />
                  {(st === 'PENDING_REVIEW' || st === 'PENDING') && (
                    <>
                      <button
                        type="button"
                        onClick={() => runAction(rec.id, 'approve')}
                        disabled={busyId === rec.id}
                        className="px-2.5 py-1 rounded bg-[var(--status-success)] text-white text-xs font-medium"
                      >
                        Approve (Shadow)
                      </button>
                      <button
                        type="button"
                        onClick={() => runAction(rec.id, 'reject')}
                        disabled={busyId === rec.id}
                        className="px-2.5 py-1 rounded bg-[var(--status-critical)] text-white text-xs font-medium"
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {(st === 'APPROVED_SHADOW' || st === 'APPROVED') && (
                    <>
                      <button
                        type="button"
                        onClick={() => runAction(rec.id, 'complete')}
                        disabled={busyId === rec.id}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white text-xs font-medium"
                      >
                        <CheckCircle2 size={12} />
                        Confirm Completed
                      </button>
                      <button
                        type="button"
                        onClick={() => runAction(rec.id, 'fail')}
                        disabled={busyId === rec.id}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--surface-secondary)] border border-[var(--status-critical)]/40 text-[var(--status-critical)] text-xs font-medium"
                      >
                        <XCircle size={12} />
                        Mark Failed
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Audit History Trail */}
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
          <Shield size={15} className="text-[var(--brand-primary)]" />
          Recommendation & Approval Audit History ({auditLogs.length})
        </h3>
        {auditLogs.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No approval audit events recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                  <th className="py-2 px-3">Timestamp</th>
                  <th className="py-2 px-3">Action</th>
                  <th className="py-2 px-3">Actor</th>
                  <th className="py-2 px-3">Target</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.slice(0, 15).map((log) => (
                  <tr key={log.id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                    <td className="py-1.5 px-3 font-mono text-[var(--text-muted)]">{log.timestamp.slice(0, 19).replace('T', ' ')}</td>
                    <td className="py-1.5 px-3 font-mono font-semibold text-[var(--text-primary)]">{log.action}</td>
                    <td className="py-1.5 px-3 font-mono">{log.user}</td>
                    <td className="py-1.5 px-3 font-mono text-[var(--text-secondary)]">{log.target_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
