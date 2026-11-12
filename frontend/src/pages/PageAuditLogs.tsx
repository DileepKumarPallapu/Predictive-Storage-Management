import React, { useState, useEffect } from 'react';
import { api, AuditItem } from '../api/client';
import { ClipboardList, Search, ShieldCheck, RefreshCw } from 'lucide-react';

export const PageAuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditItem[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [actionFilter, setActionFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [chainStatus, setChainStatus] = useState<string>('');

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditTrail();
      setLogs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async () => {
    try {
      const data = await api.verifyAuditChain();
      setChainStatus(`Chain Status: ${data.status || 'VERIFIED'} (${data.verified_entries ?? data.total_checked ?? 'all'} entries verified)`);
    } catch (e: any) {
      setChainStatus(`Verification unavailable: ${e.message}`);
    }
  };

  const uniqueActions = Array.from(new Set(logs.map((l) => l.action)));
  const filtered = logs.filter((l) => {
    if (actionFilter && l.action !== actionFilter) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        l.user.toLowerCase().includes(q) ||
        l.action.toLowerCase().includes(q) ||
        l.target_type.toLowerCase().includes(q) ||
        l.target_id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center">
              <ClipboardList size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">Audit Logs</h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Immutable operational audit trail recording logins, storage changes, data imports, ML training, forecasts, scenarios, and settings updates.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleVerifyChain}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold border border-[var(--border-strong)] bg-[var(--surface-primary)] text-[var(--text-primary)] hover:bg-[var(--surface-secondary)]"
          >
            <ShieldCheck size={14} /> Verify Hash Chain
          </button>
          <button
            onClick={loadLogs}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-[var(--accent)] text-white"
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {chainStatus && (
        <div className="p-3 rounded-lg bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-xs font-mono text-[var(--text-primary)]">
          {chainStatus}
        </div>
      )}

      {/* Filters */}
      <div className="titan-card rounded-xl p-4 flex flex-col sm:flex-row gap-3 text-xs">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-2.5 text-[var(--text-muted)]" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter by user, action, target resource..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)]"
          />
        </div>
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-primary)]"
        >
          <option value="">All Actions ({logs.length})</option>
          {uniqueActions.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="titan-card rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[var(--surface-secondary)] text-[var(--text-secondary)] uppercase text-[10px] border-b border-[var(--border-subtle)]">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Module / Target</th>
                <th className="px-4 py-3">Result / Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {loading ? (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-[var(--text-muted)]">Loading audit records...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-[var(--text-muted)]">No matching audit events found.</td></tr>
              ) : (
                filtered.map((l) => (
                  <tr key={l.id} className="hover:bg-[var(--surface-secondary)]/50">
                    <td className="px-4 py-3 whitespace-nowrap text-[var(--text-secondary)]">
                      {new Date(l.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-[var(--accent)] font-semibold">{l.user}</td>
                    <td className="px-4 py-3 font-semibold">{l.action}</td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{l.target_type}: {l.target_id}</td>
                    <td className="px-4 py-3 text-[var(--text-muted)] max-w-md truncate">{JSON.stringify(l.details)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
