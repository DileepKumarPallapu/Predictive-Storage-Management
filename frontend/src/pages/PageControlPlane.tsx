import React, { useCallback, useEffect, useState } from 'react';
import {
  CheckCircle2,
  Play,
  Plus,
  RefreshCw,
  Server,
  XCircle,
} from 'lucide-react';
import { api } from '../api/client';
import { useRealtimeSubscription } from '../context/RealtimeContext';

interface PageControlPlaneProps {
  currentUserRole?: string;
  userPermissions?: string[];
}

type ControlPlaneTab =
  | 'connectors'
  | 'capabilities'
  | 'actions'
  | 'approvals'
  | 'evidence'
  | 'history';

const STATUS_BADGE: Record<string, string> = {
  CONNECTED: 'bg-emerald-50 text-[#22784D] border-emerald-200',
  CONFIGURED: 'bg-amber-50 text-[#94651A] border-amber-200',
  DEGRADED: 'bg-amber-50 text-[#94651A] border-amber-200',
  ERROR: 'bg-red-50 text-[#C33F36] border-red-200',
  SUCCEEDED: 'bg-emerald-50 text-[#22784D] border-emerald-200',
  APPROVED: 'bg-emerald-50 text-[#22784D] border-emerald-200',
  PASS: 'bg-emerald-50 text-[#22784D] border-emerald-200',
  PENDING_APPROVAL: 'bg-amber-50 text-[#94651A] border-amber-200',
  WARNING: 'bg-amber-50 text-[#94651A] border-amber-200',
  DRY_RUN: 'bg-sky-50 text-sky-800 border-sky-200',
  DRAFT: 'bg-[#F8F8F6] text-[#555C56] border-[#DFE2DD]',
  REJECTED: 'bg-red-50 text-[#C33F36] border-red-200',
  FAILED: 'bg-red-50 text-[#C33F36] border-red-200',
  BLOCKED: 'bg-red-50 text-[#C33F36] border-red-200',
  CANCELLED: 'bg-[#F8F8F6] text-[#727971] border-[#DFE2DD]',
};

export const PageControlPlane: React.FC<PageControlPlaneProps> = ({
  currentUserRole = 'VIEWER',
  userPermissions = [],
}) => {
  const [tab, setTab] = useState<ControlPlaneTab>('actions');
  const [connectors, setConnectors] = useState<any[]>([]);
  const [definitions, setDefinitions] = useState<any[]>([]);
  const [actions, setActions] = useState<any[]>([]);
  const [devices, setDevices] = useState<any[]>([]);
  const [locks, setLocks] = useState<any[]>([]);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [selectedConnector, setSelectedConnector] = useState<any | null>(null);
  const [selectedActionId, setSelectedActionId] = useState<string>('');
  const [actionDetail, setActionDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  // Forms
  const [connName, setConnName] = useState('');
  const [connProvider, setConnProvider] = useState('AEGISSTOR_LOCAL');
  const [connVersion, setConnVersion] = useState('1.0.0');
  const [connCredRef, setConnCredRef] = useState('none://local-readonly');

  const [capConnId, setCapConnId] = useState('');
  const [capActionKey, setCapActionKey] = useState('RESOURCE_INSPECT');
  const [capDryRunMode, setCapDryRunMode] = useState('AEGISSTOR_PREFLIGHT');

  const [reqConnId, setReqConnId] = useState('');
  const [reqOp, setReqOp] = useState('CONFIG_INSPECT');
  const [reqResType, setReqResType] = useState('DEVICE');
  const [reqResId, setReqResId] = useState('');
  const [reqParams, setReqParams] = useState('{"scope":"summary"}');
  const [decisionComment, setDecisionComment] = useState('');

  const canManageConnectors =
    currentUserRole === 'ADMIN' || userPermissions.includes('control_plane.connectors.manage');
  const canCreateActions =
    currentUserRole === 'ADMIN' || userPermissions.includes('control_plane.actions.create');
  const canApproveActions =
    currentUserRole === 'ADMIN' || userPermissions.includes('control_plane.actions.approve');

  const loadAll = useCallback(async () => {
    try {
      const [cRes, dRes, aRes, devRes, lRes, audRes] = await Promise.all([
        api.listControlPlaneConnectors(),
        api.listControlPlaneActionDefinitions(),
        api.listControlPlaneActions(),
        api.getDevices().catch(() => []),
        api.listControlPlaneLocks(),
        api.listControlPlaneAudit(),
      ]);
      const connList = cRes.connectors || [];
      setConnectors(connList);
      setDefinitions(dRes.definitions || []);
      const actList = aRes.actions || [];
      setActions(actList);
      const devList = Array.isArray(devRes) ? devRes : ((devRes as any)?.devices || []);
      setDevices(devList);
      setLocks(lRes.locks || []);
      setAuditEvents(audRes.events || []);

      if (connList.length > 0) {
        setSelectedConnector((prev: any) => prev || connList[0]);
        setCapConnId((prev) => prev || connList[0].id);
        setReqConnId((prev) => prev || connList[0].id);
      }
      if (devList.length > 0) {
        setReqResId((prev) => prev || devList[0].id);
      }
      if (actList.length > 0 && !selectedActionId) {
        setSelectedActionId(actList[0].id);
      }
    } catch (err: any) {
      setBanner({ type: 'err', text: err?.message || 'Failed to load Control Plane state' });
    } finally {
      setLoading(false);
    }
  }, [selectedActionId]);

  const loadDetail = useCallback(async (actionId: string) => {
    if (!actionId) {
      setActionDetail(null);
      return;
    }
    try {
      const d = await api.getControlPlaneActionDetail(actionId);
      setActionDetail(d);
    } catch {
      setActionDetail(null);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (selectedActionId) {
      loadDetail(selectedActionId);
    }
  }, [selectedActionId, loadDetail]);

  useRealtimeSubscription(
    [
      'action.created',
      'action.preflight_completed',
      'action.approval_requested',
      'action.approved',
      'action.rejected',
      'action.cancelled',
      'action.executed',
      'connector.updated',
    ],
    () => {
      loadAll();
      if (selectedActionId) {
        loadDetail(selectedActionId);
      }
    },
  );

  const runOp = async (fn: () => Promise<void>, okMsg: string) => {
    setBusy(true);
    setBanner(null);
    try {
      await fn();
      await loadAll();
      if (selectedActionId) await loadDetail(selectedActionId);
      setBanner({ type: 'ok', text: okMsg });
    } catch (err: any) {
      setBanner({ type: 'err', text: err?.message || 'Operation failed' });
    } finally {
      setBusy(false);
    }
  };

  const handleRegisterConnector = (e: React.FormEvent) => {
    e.preventDefault();
    runOp(async () => {
      const created = await api.registerControlPlaneConnector({
        name: connName,
        provider: connProvider,
        version: connVersion,
        credential_ref: connCredRef,
      });
      setConnName('');
      setSelectedConnector(created);
    }, 'Connector registered (credentials stored as reference only).');
  };

  const handleRegisterCapability = (e: React.FormEvent) => {
    e.preventDefault();
    if (!capConnId) return;
    runOp(async () => {
      await api.registerControlPlaneCapability(capConnId, {
        action_key: capActionKey,
        dry_run_mode: capDryRunMode,
      });
    }, `Capability ${capActionKey} registered.`);
  };

  const handleCreateAction = (e: React.FormEvent) => {
    e.preventDefault();
    runOp(async () => {
      const parsedParams = JSON.parse(reqParams || '{}');
      const created = await api.createControlPlaneAction({
        connector_id: reqConnId,
        operation: reqOp,
        resource_type: reqResType,
        resource_id: reqResType === 'CONNECTOR' ? (reqResId || reqConnId) : (reqResId || devices[0]?.id || reqConnId),
        parameters: parsedParams,
      });
      setSelectedActionId(created.id);
    }, 'Action request created in DRAFT state.');
  };

  const pendingApprovals = actions.filter((a) => a.status === 'PENDING_APPROVAL');

  if (loading) {
    return <div className="p-6 text-sm text-[#555C56]">Loading Control Plane Foundation...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-[#242724]">
            Storage Control Plane Foundation (Sprint 1)
          </h1>
          <p className="text-sm text-[#555C56]">
            Read-only governed operations, connector capability registry, 8-check preflight, dry-run simulation, and dual-control approvals.
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadAll()}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg border border-[#DFE2DD] bg-white px-3 py-2 text-xs font-medium text-[#242724] hover:bg-[#F8F8F6]"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh State
        </button>
      </div>

      {banner && (
        <div
          className={`rounded-lg border px-4 py-2.5 text-sm ${
            banner.type === 'ok'
              ? 'border-emerald-200 bg-emerald-50 text-[#22784D]'
              : 'border-red-200 bg-red-50 text-[#C33F36]'
          }`}
        >
          {banner.text}
        </div>
      )}

      {/* Sub-navigation covering all Control Plane views */}
      <div className="flex flex-wrap gap-2 border-b border-[#DFE2DD] pb-3">
        {(
          [
            ['actions', 'Action Centre & New Request'],
            ['approvals', `Approval Queue (${pendingApprovals.length})`],
            ['evidence', 'Preflight & Execution Evidence'],
            ['connectors', `Connector Registry (${connectors.length})`],
            ['capabilities', 'Capability Matrix'],
            ['history', 'Action History & Locks'],
          ] as [ControlPlaneTab, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              tab === id
                ? 'bg-[#B82432] text-white'
                : 'border border-[#DFE2DD] bg-white text-[#555C56] hover:bg-[#F8F8F6]'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* TAB 1: ACTION CENTRE + NEW ACTION REQUEST */}
      {tab === 'actions' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {canCreateActions && (
            <form
              onSubmit={handleCreateAction}
              className="rounded-xl border border-[#DFE2DD] bg-white p-5 space-y-4"
            >
              <div className="flex items-center gap-2 font-semibold text-[#242724]">
                <Plus className="h-4 w-4 text-[#B82432]" />
                New Action Request (Read-Only)
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555C56] mb-1">Connector</label>
                <select
                  value={reqConnId}
                  onChange={(e) => setReqConnId(e.target.value)}
                  className="w-full rounded-lg border border-[#DFE2DD] bg-white px-3 py-2 text-sm text-[#242724]"
                  required
                >
                  <option value="">Select connector...</option>
                  {connectors.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.provider} - {c.connection_status})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555C56] mb-1">Operation</label>
                <select
                  value={reqOp}
                  onChange={(e) => setReqOp(e.target.value)}
                  className="w-full rounded-lg border border-[#DFE2DD] bg-white px-3 py-2 text-sm text-[#242724]"
                >
                  {definitions.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.id} ({d.risk_level} | {d.requires_approval ? 'Approval Req' : 'No Approval'})
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#555C56] mb-1">Resource Type</label>
                  <select
                    value={reqResType}
                    onChange={(e) => setReqResType(e.target.value)}
                    className="w-full rounded-lg border border-[#DFE2DD] bg-white px-3 py-2 text-sm text-[#242724]"
                  >
                    <option value="DEVICE">DEVICE</option>
                    <option value="CONNECTOR">CONNECTOR</option>
                    <option value="POOL">POOL</option>
                    <option value="VOLUME">VOLUME</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#555C56] mb-1">Resource ID</label>
                  {reqResType === 'DEVICE' && devices.length > 0 ? (
                    <select
                      value={reqResId}
                      onChange={(e) => setReqResId(e.target.value)}
                      className="w-full rounded-lg border border-[#DFE2DD] bg-white px-3 py-2 text-sm text-[#242724]"
                    >
                      {devices.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.id})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={reqResId}
                      onChange={(e) => setReqResId(e.target.value)}
                      placeholder="Resource ID"
                      className="w-full rounded-lg border border-[#DFE2DD] px-3 py-2 text-sm"
                      required
                    />
                  )}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555C56] mb-1">Parameters (JSON)</label>
                <textarea
                  value={reqParams}
                  onChange={(e) => setReqParams(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg border border-[#DFE2DD] px-3 py-2 font-mono text-xs"
                />
              </div>
              <button
                type="submit"
                disabled={busy || !reqConnId}
                className="w-full rounded-lg bg-[#B82432] px-4 py-2 text-sm font-medium text-white hover:bg-[#981E2A] disabled:opacity-50"
              >
                Create Action Request
              </button>
            </form>
          )}

          <div className={`${canCreateActions ? 'lg:col-span-2' : 'lg:col-span-3'} rounded-xl border border-[#DFE2DD] bg-white p-5`}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold text-[#242724]">Action Centre ({actions.length})</h2>
              <span className="text-xs text-[#727971]">Sprint 1: Read-Only Infrastructure Inspection</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-[#DFE2DD] text-[#727971]">
                  <tr>
                    <th className="py-2 pr-3">Operation</th>
                    <th className="py-2 pr-3">Resource</th>
                    <th className="py-2 pr-3">Requester</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Ver</th>
                    <th className="py-2">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#DFE2DD]">
                  {actions.map((a) => (
                    <tr
                      key={a.id}
                      onClick={() => setSelectedActionId(a.id)}
                      className={`cursor-pointer hover:bg-[#F8F8F6] ${
                        selectedActionId === a.id ? 'bg-[#F9E9EB]/40' : ''
                      }`}
                    >
                      <td className="py-2.5 pr-3 font-medium text-[#242724]">
                        {a.operation}
                        <div className="text-[11px] text-[#727971]">{a.id}</div>
                      </td>
                      <td className="py-2.5 pr-3 text-[#555C56]">
                        {a.resource_type}:{a.resource_id}
                      </td>
                      <td className="py-2.5 pr-3 text-[#555C56]">
                        {a.requester_username} ({a.requesting_role})
                      </td>
                      <td className="py-2.5 pr-3">
                        <span
                          className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                            STATUS_BADGE[a.status] || 'bg-[#F8F8F6] text-[#555C56] border-[#DFE2DD]'
                          }`}
                        >
                          {a.status}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-[#727971]">v{a.entity_version}</td>
                      <td className="py-2.5 space-x-1.5" onClick={(e) => e.stopPropagation()}>
                        {canCreateActions && a.status === 'DRAFT' && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              runOp(
                                () => api.runControlPlanePreflight(a.id),
                                `Preflight & dry-run completed for ${a.id}.`,
                              )
                            }
                            className="rounded border border-[#DFE2DD] bg-white px-2 py-1 text-[11px] font-medium hover:bg-[#F8F8F6]"
                          >
                            Preflight
                          </button>
                        )}
                        {canCreateActions && a.status === 'DRY_RUN' && a.approval_required && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              runOp(
                                () => api.submitControlPlaneApproval(a.id),
                                `Submitted ${a.id} for Administrator approval.`,
                              )
                            }
                            className="rounded bg-amber-600 px-2 py-1 text-[11px] font-medium text-white hover:bg-amber-700"
                          >
                            Submit Approval
                          </button>
                        )}
                        {canCreateActions &&
                          ((a.status === 'APPROVED') || (a.status === 'DRY_RUN' && !a.approval_required)) && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                runOp(
                                  () => api.executeControlPlaneAction(a.id),
                                  `Executed read-only ${a.operation} (${a.id}).`,
                                )
                              }
                              className="inline-flex items-center gap-1 rounded bg-[#22784D] px-2 py-1 text-[11px] font-medium text-white hover:opacity-90"
                            >
                              <Play className="h-3 w-3" />
                              Execute
                            </button>
                          )}
                        {canCreateActions &&
                          ['DRAFT', 'VALIDATING', 'DRY_RUN', 'PENDING_APPROVAL', 'APPROVED'].includes(a.status) && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                runOp(
                                  () => api.cancelControlPlaneAction(a.id, 'Cancelled from Action Centre', a.entity_version),
                                  `Action ${a.id} cancelled.`,
                                )
                              }
                              className="rounded border border-red-200 px-2 py-1 text-[11px] text-[#C33F36] hover:bg-red-50"
                            >
                              Cancel
                            </button>
                          )}
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedActionId(a.id);
                            setTab('evidence');
                          }}
                          className="rounded border border-[#DFE2DD] px-2 py-1 text-[11px] text-[#555C56] hover:bg-[#F8F8F6]"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                  {actions.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-[#727971]">
                        No action requests yet. Register a connector and create a read-only inspection request.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: APPROVAL QUEUE */}
      {tab === 'approvals' && (
        <div className="rounded-xl border border-[#DFE2DD] bg-white p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-[#242724]">
              Control Plane Approval Queue ({pendingApprovals.length})
            </h2>
            {canApproveActions && (
              <input
                value={decisionComment}
                onChange={(e) => setDecisionComment(e.target.value)}
                placeholder="Optional approval/rejection comment..."
                className="w-72 rounded-lg border border-[#DFE2DD] px-3 py-1.5 text-xs"
              />
            )}
          </div>
          {pendingApprovals.length === 0 ? (
            <p className="text-sm text-[#727971]">No actions currently awaiting Administrator approval.</p>
          ) : (
            <div className="space-y-3">
              {pendingApprovals.map((a) => (
                <div
                  key={a.id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-[#DFE2DD] bg-[#F8F8F6] p-4"
                >
                  <div>
                    <div className="font-medium text-[#242724]">
                      {a.operation} on {a.resource_type}:{a.resource_id}
                    </div>
                    <div className="text-xs text-[#555C56]">
                      Requested by {a.requester_username} ({a.requesting_role}) · Risk: {a.risk_level} · v{a.entity_version}
                    </div>
                  </div>
                  {canApproveActions ? (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          runOp(
                            () => api.approveControlPlaneAction(a.id, decisionComment || 'Approved', a.entity_version),
                            `Approved action ${a.id}.`,
                          )
                        }
                        className="inline-flex items-center gap-1 rounded-lg bg-[#22784D] px-3 py-1.5 text-xs font-medium text-white"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Approve
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          runOp(
                            () => api.rejectControlPlaneAction(a.id, decisionComment || 'Rejected', a.entity_version),
                            `Rejected action ${a.id}.`,
                          )
                        }
                        className="inline-flex items-center gap-1 rounded-lg bg-[#C33F36] px-3 py-1.5 text-xs font-medium text-white"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        Reject
                      </button>
                    </div>
                  ) : (
                    <span className="text-xs text-[#727971]">Awaiting Administrator review</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: PREFLIGHT RESULTS & EXECUTION EVIDENCE */}
      {tab === 'evidence' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-[#DFE2DD] bg-white p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-[#242724]">Preflight & Dry-Run Results</h2>
              <select
                value={selectedActionId}
                onChange={(e) => setSelectedActionId(e.target.value)}
                className="rounded-lg border border-[#DFE2DD] px-2.5 py-1 text-xs"
              >
                {actions.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.operation} ({a.status}) - {a.id}
                  </option>
                ))}
              </select>
            </div>
            {actionDetail?.preflights?.length ? (
              actionDetail.preflights.map((pf: any) => (
                <div key={pf.id} className="space-y-3 rounded-lg border border-[#DFE2DD] p-4">
                  <div className="flex items-center justify-between">
                    <span
                      className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                        STATUS_BADGE[pf.overall_status] || ''
                      }`}
                    >
                      Overall: {pf.overall_status}
                    </span>
                    <span className="text-xs font-medium text-[#555C56]">
                      Dry-Run Mode: {pf.dry_run_mode}
                    </span>
                  </div>
                  <div className="space-y-1.5">
                    {(pf.checks || []).map((chk: any) => (
                      <div key={chk.check} className="flex items-center justify-between text-xs">
                        <span className="font-mono text-[#242724]">{chk.check}</span>
                        <span className="text-[#555C56]">{chk.detail}</span>
                        <span
                          className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold ${
                            STATUS_BADGE[chk.status] || ''
                          }`}
                        >
                          {chk.status}
                        </span>
                      </div>
                    ))}
                  </div>
                  <pre className="overflow-x-auto rounded bg-[#F8F8F6] p-3 text-[11px] text-[#242724]">
                    {JSON.stringify(pf.dry_run_summary, null, 2)}
                  </pre>
                </div>
              ))
            ) : (
              <p className="text-sm text-[#727971]">No preflight results recorded for this action yet.</p>
            )}
          </div>

          <div className="rounded-xl border border-[#DFE2DD] bg-white p-5 space-y-4">
            <h2 className="font-semibold text-[#242724]">Execution Evidence & Step Trace</h2>
            {actionDetail?.executions?.length ? (
              actionDetail.executions.map((ex: any) => (
                <div key={ex.id} className="space-y-3 rounded-lg border border-[#DFE2DD] p-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-[#242724]">Execution {ex.id}</span>
                    <span className={`rounded-full border px-2 py-0.5 font-medium ${STATUS_BADGE[ex.status] || ''}`}>
                      {ex.status}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {(ex.steps || []).map((st: any) => (
                      <div key={st.id} className="rounded bg-[#F8F8F6] p-2.5 text-xs">
                        <div className="flex justify-between font-medium text-[#242724]">
                          <span>
                            Step {st.step_order}: {st.step_name}
                          </span>
                          <span className="text-[#22784D]">{st.status}</span>
                        </div>
                        <pre className="mt-1 overflow-x-auto text-[11px] text-[#555C56]">
                          {JSON.stringify(st.output, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-[#727971]">No read-only execution recorded for this action yet.</p>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: CONNECTOR REGISTRY & DETAILS */}
      {tab === 'connectors' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {canManageConnectors && (
            <form
              onSubmit={handleRegisterConnector}
              className="rounded-xl border border-[#DFE2DD] bg-white p-5 space-y-4"
            >
              <div className="flex items-center gap-2 font-semibold text-[#242724]">
                <Server className="h-4 w-4 text-[#B82432]" />
                Register Storage Connector
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555C56] mb-1">Connector Name</label>
                <input
                  value={connName}
                  onChange={(e) => setConnName(e.target.value)}
                  placeholder="e.g. ONTAP-Primary-RO"
                  className="w-full rounded-lg border border-[#DFE2DD] px-3 py-2 text-sm"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#555C56] mb-1">Provider</label>
                  <select
                    value={connProvider}
                    onChange={(e) => setConnProvider(e.target.value)}
                    className="w-full rounded-lg border border-[#DFE2DD] bg-white px-3 py-2 text-sm"
                  >
                    <option value="AEGISSTOR_LOCAL">AEGISSTOR_LOCAL</option>
                    <option value="LINUX_STORAGE">LINUX_STORAGE</option>
                    <option value="PROMETHEUS">PROMETHEUS</option>
                    <option value="ONTAP_READONLY">ONTAP_READONLY</option>
                    <option value="S3_STORAGE">S3_STORAGE</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#555C56] mb-1">Version</label>
                  <input
                    value={connVersion}
                    onChange={(e) => setConnVersion(e.target.value)}
                    className="w-full rounded-lg border border-[#DFE2DD] px-3 py-2 text-sm"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555C56] mb-1">
                  Credential Reference (no plain-text secrets)
                </label>
                <input
                  value={connCredRef}
                  onChange={(e) => setConnCredRef(e.target.value)}
                  placeholder="vault://... or env://..."
                  className="w-full rounded-lg border border-[#DFE2DD] px-3 py-2 font-mono text-xs"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={busy}
                className="w-full rounded-lg bg-[#B82432] px-4 py-2 text-sm font-medium text-white hover:bg-[#981E2A]"
              >
                Register Connector
              </button>
            </form>
          )}

          <div className={`${canManageConnectors ? 'lg:col-span-2' : 'lg:col-span-3'} space-y-4`}>
            <div className="rounded-xl border border-[#DFE2DD] bg-white p-5">
              <h2 className="mb-3 font-semibold text-[#242724]">Connector Registry</h2>
              <div className="space-y-2.5">
                {connectors.map((c) => (
                  <div
                    key={c.id}
                    onClick={() => setSelectedConnector(c)}
                    className={`cursor-pointer rounded-lg border p-3.5 transition ${
                      selectedConnector?.id === c.id
                        ? 'border-[#B82432] bg-[#F9E9EB]/30'
                        : 'border-[#DFE2DD] hover:bg-[#F8F8F6]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-[#242724]">{c.name}</div>
                        <div className="text-xs text-[#555C56]">
                          {c.provider} v{c.version} · Ref: <span className="font-mono">{c.credential_ref}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                            STATUS_BADGE[c.connection_status] || ''
                          }`}
                        >
                          {c.connection_status}
                        </span>
                        {canCreateActions && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={(e) => {
                              e.stopPropagation();
                              runOp(
                                () => api.checkControlPlaneConnectorHealth(c.id),
                                `Health check completed for ${c.name}.`,
                              );
                            }}
                            className="rounded border border-[#DFE2DD] bg-white px-2.5 py-1 text-xs hover:bg-[#F8F8F6]"
                          >
                            Health Check
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {selectedConnector && (
              <div className="rounded-xl border border-[#DFE2DD] bg-white p-5 space-y-2">
                <h3 className="font-semibold text-[#242724]">
                  Connector Details: {selectedConnector.name}
                </h3>
                <div className="grid grid-cols-2 gap-2 text-xs text-[#555C56]">
                  <div>ID: <span className="font-mono text-[#242724]">{selectedConnector.id}</span></div>
                  <div>Organisation: <span className="font-mono text-[#242724]">{selectedConnector.organization_id}</span></div>
                  <div>Last Health Check: {selectedConnector.last_health_check_at || 'Never'}</div>
                  <div>Capabilities: {(selectedConnector.capabilities || []).length}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: CAPABILITY MATRIX */}
      {tab === 'capabilities' && (
        <div className="space-y-6">
          {canManageConnectors && connectors.length > 0 && (
            <form
              onSubmit={handleRegisterCapability}
              className="flex flex-wrap items-end gap-3 rounded-xl border border-[#DFE2DD] bg-white p-4"
            >
              <div>
                <label className="block text-xs font-medium text-[#555C56] mb-1">Connector</label>
                <select
                  value={capConnId}
                  onChange={(e) => setCapConnId(e.target.value)}
                  className="rounded-lg border border-[#DFE2DD] bg-white px-3 py-1.5 text-xs"
                >
                  {connectors.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555C56] mb-1">Typed Action</label>
                <select
                  value={capActionKey}
                  onChange={(e) => setCapActionKey(e.target.value)}
                  className="rounded-lg border border-[#DFE2DD] bg-white px-3 py-1.5 text-xs"
                >
                  {definitions.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.id}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555C56] mb-1">Dry-Run Mode</label>
                <select
                  value={capDryRunMode}
                  onChange={(e) => setCapDryRunMode(e.target.value)}
                  className="rounded-lg border border-[#DFE2DD] bg-white px-3 py-1.5 text-xs"
                >
                  <option value="AEGISSTOR_PREFLIGHT">AEGISSTOR_PREFLIGHT</option>
                  <option value="NATIVE_PROVIDER">NATIVE_PROVIDER</option>
                  <option value="UNSUPPORTED">UNSUPPORTED</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={busy}
                className="rounded-lg bg-[#B82432] px-3 py-1.5 text-xs font-medium text-white"
              >
                Register Capability
              </button>
            </form>
          )}

          <div className="rounded-xl border border-[#DFE2DD] bg-white p-5 overflow-x-auto">
            <h2 className="mb-3 font-semibold text-[#242724]">Connector Capability Matrix & Action Policies</h2>
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#DFE2DD] text-[#727971]">
                <tr>
                  <th className="py-2 pr-4">Action Definition</th>
                  <th className="py-2 pr-4">Risk</th>
                  <th className="py-2 pr-4">Approval Policy</th>
                  {connectors.map((c) => (
                    <th key={c.id} className="py-2 pr-4">
                      {c.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#DFE2DD]">
                {definitions.map((d) => (
                  <tr key={d.id}>
                    <td className="py-2.5 pr-4 font-medium text-[#242724]">
                      {d.id}
                      <div className="text-[11px] font-normal text-[#727971]">{d.description}</div>
                    </td>
                    <td className="py-2.5 pr-4">{d.risk_level}</td>
                    <td className="py-2.5 pr-4">
                      {canManageConnectors ? (
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() =>
                            runOp(
                              () =>
                                api.updateControlPlaneActionPolicy(d.id, {
                                  requires_approval: !d.requires_approval,
                                }),
                              `Updated approval policy for ${d.id}.`,
                            )
                          }
                          className="rounded border border-[#DFE2DD] px-2 py-0.5 text-[11px] hover:bg-[#F8F8F6]"
                        >
                          {d.requires_approval ? 'Approval Required' : 'Auto-Allowed'}
                        </button>
                      ) : (
                        <span>{d.requires_approval ? 'Approval Required' : 'Auto-Allowed'}</span>
                      )}
                    </td>
                    {connectors.map((c) => {
                      const cap = (c.capabilities || []).find((x: any) => x.action_key === d.id);
                      return (
                        <td key={c.id} className="py-2.5 pr-4">
                          {cap ? (
                            <span className="rounded bg-emerald-50 px-2 py-0.5 text-[11px] text-[#22784D]">
                              {cap.dry_run_mode}
                            </span>
                          ) : (
                            <span className="text-[#727971]">Not Registered</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 6: ACTION HISTORY & LOCKS */}
      {tab === 'history' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-[#DFE2DD] bg-white p-5">
            <h2 className="mb-3 font-semibold text-[#242724]">Control Plane Audit History</h2>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {auditEvents.map((ev) => (
                <div key={ev.id} className="rounded border border-[#DFE2DD] bg-[#F8F8F6] p-2.5 text-xs">
                  <div className="flex justify-between font-medium text-[#242724]">
                    <span>{ev.event_type}</span>
                    <span className="text-[#727971]">{ev.actor_username} ({ev.actor_role})</span>
                  </div>
                  {(ev.from_status || ev.to_status) && (
                    <div className="text-[#555C56]">
                      {ev.from_status || '—'} → {ev.to_status}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-[#DFE2DD] bg-white p-5">
            <h2 className="mb-3 font-semibold text-[#242724]">Resource Execution Locks</h2>
            <div className="space-y-2">
              {locks.map((l) => (
                <div key={l.id} className="flex items-center justify-between rounded border border-[#DFE2DD] p-2.5 text-xs">
                  <div>
                    <div className="font-medium text-[#242724]">
                      {l.resource_type}:{l.resource_id}
                    </div>
                    <div className="text-[#727971]">Action: {l.locked_by_action_id}</div>
                  </div>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[11px] ${
                      l.is_active ? 'border-amber-200 bg-amber-50 text-[#94651A]' : 'border-[#DFE2DD] bg-[#F8F8F6] text-[#727971]'
                    }`}
                  >
                    {l.is_active ? 'ACTIVE' : 'RELEASED'}
                  </span>
                </div>
              ))}
              {locks.length === 0 && <p className="text-sm text-[#727971]">No execution locks recorded.</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
