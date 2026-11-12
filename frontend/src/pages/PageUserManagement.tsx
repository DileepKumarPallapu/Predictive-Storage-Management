import React, { useEffect, useState } from 'react';
import {
  Users, UserPlus, Shield, CheckCircle2, XCircle, KeyRound,
  LogOut, Eye, Lock, Save, RefreshCw
} from 'lucide-react';
import { api } from '../api/client';

interface PageUserManagementProps {
  currentUserRole: string;
}

export const PageUserManagement: React.FC<PageUserManagementProps> = ({ currentUserRole }) => {
  const [activeTab, setActiveTab] = useState<'users' | 'permissions'>('users');
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('OPERATOR');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [issuedResetToken, setIssuedResetToken] = useState<{ username: string; token: string } | null>(null);
  const [selectedUserAudit, setSelectedUserAudit] = useState<any>(null);
  const [editingEmailId, setEditingEmailId] = useState<string | null>(null);
  const [editingEmailVal, setEditingEmailVal] = useState('');

  // Permissions & Approval Policy state
  const [permCatalog, setPermCatalog] = useState<any[]>([]);
  const [rolePerms, setRolePerms] = useState<Record<string, Record<string, boolean>>>({});
  const [selectedPermRole, setSelectedPermRole] = useState<string>('OPERATOR');
  const [savingPerms, setSavingPerms] = useState(false);
  const [selfApproveAllowed, setSelfApproveAllowed] = useState<boolean>(false);

  const isAdmin = currentUserRole.toUpperCase() === 'ADMIN';

  const loadUsers = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const list = await api.listUsers();
      setUsers(list);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Unable to load users');
    } finally {
      setLoading(false);
    }
  };

  const loadPermissionsAndPolicy = async () => {
    try {
      const [cat, sysSettings] = await Promise.all([
        api.getPermissionCatalog(),
        api.getSettings(),
      ]);
      setPermCatalog(cat.permissions || []);
      const boolMap: Record<string, Record<string, boolean>> = {};
      for (const [rKey, allowedArr] of Object.entries(cat.role_matrix || {})) {
        const inner: Record<string, boolean> = {};
        for (const pKey of allowedArr || []) {
          inner[pKey] = true;
        }
        boolMap[rKey] = inner;
      }
      setRolePerms(boolMap);
      setSelfApproveAllowed(Boolean(sysSettings?.approval_policy?.operator_can_self_approve));
    } catch (err: any) {
      setErrorMsg(err?.message || 'Unable to load RBAC permission matrix');
    }
  };

  useEffect(() => {
    if (isAdmin) {
      loadUsers();
      loadPermissionsAndPolicy();
    } else {
      setLoading(false);
    }
  }, [isAdmin]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      await api.createUser({ username: username.trim(), email: email.trim(), password, role });
      setStatusMsg(`User '${username.trim()}' (${role}) created cleanly.`);
      setUsername('');
      setEmail('');
      setPassword('');
      await loadUsers();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to create user');
    }
  };

  const handleToggleActive = async (u: any) => {
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      await api.updateUser(u.id, { is_active: !u.is_active });
      setStatusMsg(
        `User '${u.username}' is now ${!u.is_active ? 'ACTIVE' : 'DEACTIVATED'} (active sessions invalidated).`
      );
      await loadUsers();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to update user status');
    }
  };

  const handleRoleChange = async (u: any, newRole: string) => {
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      await api.updateUser(u.id, { role: newRole });
      setStatusMsg(`Updated '${u.username}' role to ${newRole}. Existing sessions were revoked.`);
      await loadUsers();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to update user role');
    }
  };

  const handleSaveEmail = async (u: any) => {
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      await api.updateUser(u.id, { email: editingEmailVal.trim() });
      setEditingEmailId(null);
      setStatusMsg(`Updated email for '${u.username}'.`);
      await loadUsers();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to update email');
    }
  };

  const handleRevokeSessions = async (u: any) => {
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      const res = await api.revokeUserSessions(u.id);
      setStatusMsg(`Revoked ${res.revoked_sessions ?? 0} active session(s) for '${u.username}'.`);
      await loadUsers();
      if (selectedUserAudit?.user?.id === u.id) {
        const auditRes = await api.getUserAudit(u.id);
        setSelectedUserAudit(auditRes);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to revoke sessions');
    }
  };

  const handleTriggerReset = async (u: any) => {
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      const res = await api.triggerUserReset(u.id);
      setStatusMsg(res.message);
      if (res.reset_token) {
        setIssuedResetToken({ username: u.username, token: res.reset_token });
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to trigger password reset');
    }
  };

  const handleInspectAudit = async (u: any) => {
    setErrorMsg(null);
    try {
      const res = await api.getUserAudit(u.id);
      setSelectedUserAudit(res);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to load user security audit');
    }
  };

  const handleTogglePermission = (permKey: string) => {
    if (selectedPermRole === 'ADMIN') return;
    setRolePerms((prev) => ({
      ...prev,
      [selectedPermRole]: {
        ...(prev[selectedPermRole] || {}),
        [permKey]: !(prev[selectedPermRole]?.[permKey]),
      },
    }));
  };

  const handleSavePermissions = async () => {
    setSavingPerms(true);
    setErrorMsg(null);
    setStatusMsg(null);
    try {
      const map = rolePerms[selectedPermRole] || {};
      const enabledKeys = Object.entries(map).filter(([, v]) => Boolean(v)).map(([k]) => k);
      await api.updateRolePermissions(selectedPermRole, enabledKeys);
      setStatusMsg(`Updated permission matrix for role ${selectedPermRole}.`);
      await loadPermissionsAndPolicy();
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to save role permissions');
    } finally {
      setSavingPerms(false);
    }
  };

  const handleToggleSelfApprove = async () => {
    setErrorMsg(null);
    setStatusMsg(null);
    const nextVal = !selfApproveAllowed;
    try {
      await api.updateSettings({ approval_policy: { operator_can_self_approve: nextVal } });
      setSelfApproveAllowed(nextVal);
      setStatusMsg(`Operator self-approval policy set to ${nextVal ? 'ENABLED' : 'DISABLED'}.`);
    } catch (err: any) {
      setErrorMsg(err?.message || 'Failed to update approval policy');
    }
  };

  if (!isAdmin) {
    return (
      <div className="titan-card rounded-xl p-6 text-sm text-[var(--status-critical)] flex items-center gap-3">
        <Shield size={18} /> Administrator permissions (`users.*`) are required to access User & Access Management.
      </div>
    );
  }

  // Group permission catalog by module
  const permsByModule: Record<string, any[]> = {};
  for (const item of permCatalog) {
    if (!permsByModule[item.module]) permsByModule[item.module] = [];
    permsByModule[item.module].push(item);
  }

  return (
    <div className="space-y-6">
      {/* Header + Sub-Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center">
              <Users size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              User, Role & RBAC Access Governance
            </h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Provision accounts, manage sessions & resets, inspect failed-login lockouts, and configure role permissions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('users')}
            className={`px-3 py-2 rounded-lg text-xs font-semibold border ${
              activeTab === 'users'
                ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                : 'border-[var(--border-strong)] bg-[var(--surface-primary)]'
            }`}
          >
            Users & Sessions ({users.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('permissions')}
            className={`px-3 py-2 rounded-lg text-xs font-semibold border ${
              activeTab === 'permissions'
                ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                : 'border-[var(--border-strong)] bg-[var(--surface-primary)]'
            }`}
          >
            Role Permissions & Policies
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg border border-[var(--status-critical)] bg-[var(--status-critical)]/10 text-xs text-[var(--status-critical)]">
          {errorMsg}
        </div>
      )}
      {statusMsg && (
        <div className="p-3 rounded-lg border border-[var(--status-success)] bg-[var(--status-success)]/10 text-xs text-[var(--status-success)]">
          {statusMsg}
        </div>
      )}
      {issuedResetToken && (
        <div className="p-3 rounded-lg border border-[var(--accent)]/40 bg-[var(--brand-soft)]/30 text-xs font-mono space-y-1">
          <div className="font-bold text-[var(--text-primary)]">
            Single-Use Password Reset Token for {issuedResetToken.username}
          </div>
          <div className="break-all text-[var(--accent)]">{issuedResetToken.token}</div>
        </div>
      )}

      {activeTab === 'users' && (
        <>
          {/* Create User Form */}
          <form onSubmit={handleCreateUser} className="titan-card rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <UserPlus size={16} className="text-[var(--accent)]" /> Create New User Account
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={3}
                className="px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-primary)]"
              />
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-primary)]"
              />
              <input
                type="password"
                placeholder="Password (min 8 chars)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-primary)]"
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-primary)]"
              >
                <option value="OPERATOR">OPERATOR (Full Day-to-Day Ops)</option>
                <option value="VIEWER">VIEWER (Read-Only Stakeholder)</option>
                <option value="ADMIN">ADMIN (Platform & IAM Admin)</option>
                <option value="AUDITOR">AUDITOR (Audit Compliance)</option>
              </select>
            </div>
            <button type="submit" className="px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white">
              Create User
            </button>
          </form>

          {/* Users Table */}
          <div className="titan-card rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--surface-secondary)] text-[var(--text-secondary)] uppercase text-[10px] font-mono border-b border-[var(--border-subtle)]">
                  <tr>
                    <th className="px-4 py-3">User & Security</th>
                    <th className="px-4 py-3">Email</th>
                    <th className="px-4 py-3">Role</th>
                    <th className="px-4 py-3">Status & Login Telemetry</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-6 text-center text-[var(--text-muted)]">
                        Loading users...
                      </td>
                    </tr>
                  ) : (
                    users.map((u) => (
                      <tr key={u.id}>
                        <td className="px-4 py-3">
                          <div className="font-semibold text-[var(--text-primary)]">{u.username}</div>
                          <div className="font-mono text-[10px] text-[var(--text-muted)]">{u.id}</div>
                        </td>
                        <td className="px-4 py-3">
                          {editingEmailId === u.id ? (
                            <div className="flex items-center gap-1.5">
                              <input
                                type="email"
                                value={editingEmailVal}
                                onChange={(e) => setEditingEmailVal(e.target.value)}
                                className="px-2 py-1 rounded border border-[var(--border-strong)] bg-[var(--surface-primary)] text-xs w-44"
                              />
                              <button
                                type="button"
                                onClick={() => handleSaveEmail(u)}
                                className="px-2 py-1 rounded bg-[var(--accent)] text-white text-[10px]"
                              >
                                Save
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingEmailId(null)}
                                className="px-2 py-1 rounded border border-[var(--border-subtle)] text-[10px]"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2 font-mono text-[var(--text-secondary)]">
                              <span>{u.email}</span>
                              <button
                                type="button"
                                onClick={() => {
                                  setEditingEmailId(u.id);
                                  setEditingEmailVal(u.email);
                                }}
                                className="text-[10px] text-[var(--accent)] hover:underline font-sans"
                              >
                                Edit
                              </button>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <select
                            aria-label={`Role for ${u.username}`}
                            value={u.role}
                            onChange={(e) => handleRoleChange(u, e.target.value)}
                            className="px-2 py-1 rounded border border-[var(--border-strong)] bg-[var(--surface-primary)] text-xs font-mono"
                          >
                            <option value="ADMIN">ADMIN</option>
                            <option value="OPERATOR">OPERATOR</option>
                            <option value="VIEWER">VIEWER</option>
                            <option value="AUDITOR">AUDITOR</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px]">
                          <div className="flex items-center gap-1.5">
                            {u.is_active ? (
                              <span className="inline-flex items-center gap-1 text-[var(--status-success)] font-semibold">
                                <CheckCircle2 size={13} /> Active
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[var(--status-critical)] font-semibold">
                                <XCircle size={13} /> Deactivated
                              </span>
                            )}
                            {u.locked_until && (
                              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[var(--status-critical)]/15 text-[var(--status-critical)] text-[10px]">
                                <Lock size={10} /> Locked
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
                            Failures: {u.failed_login_attempts ?? 0} · Last login:{' '}
                            {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never'}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right whitespace-nowrap space-x-1.5">
                          <button
                            type="button"
                            onClick={() => handleInspectAudit(u)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)] text-[11px]"
                          >
                            <Eye size={12} /> Security
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRevokeSessions(u)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)] text-[11px]"
                          >
                            <LogOut size={12} /> Revoke
                          </button>
                          <button
                            type="button"
                            onClick={() => handleTriggerReset(u)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)] text-[11px]"
                          >
                            <KeyRound size={12} /> Reset
                          </button>
                          <button
                            type="button"
                            onClick={() => handleToggleActive(u)}
                            className={`px-2.5 py-1 rounded text-[11px] font-semibold ${
                              u.is_active
                                ? 'border border-[var(--status-critical)]/40 text-[var(--status-critical)]'
                                : 'bg-[var(--status-success)] text-white'
                            }`}
                          >
                            {u.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Per-User Security & Login Audit Inspector */}
          {selectedUserAudit && (
            <div className="titan-card rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
                <div>
                  <h3 className="text-sm font-bold">
                    Security & Audit Inspection · {selectedUserAudit.user?.username}
                  </h3>
                  <div className="text-[11px] font-mono text-[var(--text-muted)]">
                    Role: {selectedUserAudit.user?.role} · Failed attempts: {selectedUserAudit.user?.failed_login_attempts ?? 0}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedUserAudit(null)}
                  className="px-2.5 py-1 rounded border border-[var(--border-subtle)] text-xs"
                >
                  Close
                </button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="text-[11px] font-mono uppercase text-[var(--text-muted)]">
                    Recent Authentication Attempts ({selectedUserAudit.login_attempts?.length ?? 0})
                  </div>
                  <div className="max-h-56 overflow-y-auto space-y-1.5 text-xs font-mono">
                    {(selectedUserAudit.login_attempts || []).map((la: any) => (
                      <div key={la.id} className="p-2 rounded border border-[var(--border-subtle)] flex items-center justify-between">
                        <span>
                          {la.success ? 'SUCCESS' : `FAILED (${la.failure_reason})`} · {la.client_ip || '127.0.0.1'}
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)]">
                          {la.attempted_at ? new Date(la.attempted_at).toLocaleString() : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-[11px] font-mono uppercase text-[var(--text-muted)]">
                    User Audit Ledger ({(selectedUserAudit.logs || []).length})
                  </div>
                  <div className="max-h-56 overflow-y-auto space-y-1.5 text-xs font-mono">
                    {(selectedUserAudit.logs || []).map((al: any) => (
                      <div key={al.id} className="p-2 rounded border border-[var(--border-subtle)] flex items-center justify-between">
                        <span>
                          {al.action} ({al.outcome}) · {al.target_type}
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)]">
                          {al.timestamp ? new Date(al.timestamp).toLocaleString() : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'permissions' && (
        <div className="space-y-5">
          {/* Approval Policy Toggle */}
          <div className="titan-card rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                Approval Governance Policy · Operator Self-Approval
              </h3>
              <p className="text-xs text-[var(--text-secondary)]">
                By default, Operators can approve recommendations submitted by others, while self-approval of their own changes is blocked (`403`).
              </p>
            </div>
            <button
              type="button"
              onClick={handleToggleSelfApprove}
              className={`px-4 py-2 rounded-lg text-xs font-semibold ${
                selfApproveAllowed
                  ? 'bg-[var(--status-warning)] text-white'
                  : 'border border-[var(--border-strong)] bg-[var(--surface-secondary)]'
              }`}
            >
              Self-Approval: {selfApproveAllowed ? 'ENABLED' : 'BLOCKED (Recommended)'}
            </button>
          </div>

          {/* Role Permissions Matrix */}
          <div className="titan-card rounded-xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--border-subtle)] pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-[var(--text-secondary)]">Editing Role:</span>
                {['OPERATOR', 'VIEWER', 'AUDITOR', 'ADMIN'].map((rName) => (
                  <button
                    key={rName}
                    type="button"
                    onClick={() => setSelectedPermRole(rName)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold border ${
                      selectedPermRole === rName
                        ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                        : 'border-[var(--border-subtle)] bg-[var(--surface-secondary)]'
                    }`}
                  >
                    {rName}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={loadPermissionsAndPolicy}
                  className="p-2 rounded-lg border border-[var(--border-subtle)]"
                  title="Reload catalog"
                >
                  <RefreshCw size={14} />
                </button>
                {selectedPermRole !== 'ADMIN' && (
                  <button
                    type="button"
                    disabled={savingPerms}
                    onClick={handleSavePermissions}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white disabled:opacity-50"
                  >
                    <Save size={14} /> {savingPerms ? 'Saving...' : `Save ${selectedPermRole} Permissions`}
                  </button>
                )}
              </div>
            </div>

            {selectedPermRole === 'ADMIN' && (
              <div className="text-xs text-[var(--text-muted)] font-mono">
                ADMIN role retains full platform permissions as the immutable recovery baseline.
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(permsByModule).map(([moduleName, items]) => (
                <div key={moduleName} className="p-3.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-secondary)]/40 space-y-2">
                  <div className="text-xs font-bold uppercase tracking-wider text-[var(--accent)] font-mono">
                    {moduleName}
                  </div>
                  <div className="space-y-1.5">
                    {items.map((item) => {
                      const checked = Boolean(rolePerms[selectedPermRole]?.[item.key]);
                      return (
                        <label
                          key={item.key}
                          className="flex items-start gap-2 text-xs cursor-pointer select-none"
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            disabled={selectedPermRole === 'ADMIN'}
                            onChange={() => handleTogglePermission(item.key)}
                            className="mt-0.5"
                          />
                          <div>
                            <div className="font-mono font-medium text-[var(--text-primary)]">{item.key}</div>
                            <div className="text-[11px] text-[var(--text-muted)]">{item.description}</div>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
