import React, { useState, useEffect } from 'react';
import { api, AuditItem } from '../api/client';
import { Settings, Shield, Clock, FileText, Lock } from 'lucide-react';

export const PageSettingsAudit: React.FC = () => {
  const [settingsData, setSettingsData] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadSettingsAndAudit();
  }, []);

  const loadSettingsAndAudit = async () => {
    try {
      const [s, a] = await Promise.all([api.getSettings(), api.getAuditTrail()]);
      setSettingsData(s);
      setAuditLogs(a);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent-cyan)]/15 border border-[var(--accent-cyan)]/30 flex items-center justify-center text-[var(--accent-cyan)] shadow-[0_0_12px_rgba(85,214,255,0.2)]">
            <Settings size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            System Settings & Immutable Governance Audit Trail
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          Review system parameters, Hard Safety Envelope invariants, and auditable operational records.
        </p>
      </div>

      {/* Safety Envelope Invariants */}
      {settingsData && (
        <div className="glass-panel rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Shield className="text-[var(--color-success)]" size={17} />
              Active Hard Safety Envelope Invariants
            </h3>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--color-success)]/15 text-[var(--color-success)] border border-[var(--color-success)]/40 shadow-sm">
              ENFORCED IN SHADOW MODE
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div className="bg-[var(--surface-raised)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
              <span className="text-[var(--text-tertiary)] uppercase text-[10px] block">Critical Capacity Ceiling</span>
              <span className="text-[var(--text-primary)] font-bold mt-1 block">90% Utilization Cap</span>
            </div>

            <div className="bg-[var(--surface-raised)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
              <span className="text-[var(--text-tertiary)] uppercase text-[10px] block">Max Migration I/O Penalty</span>
              <span className="text-[var(--text-primary)] font-bold mt-1 block">35% Tail Latency Cap</span>
            </div>

            <div className="bg-[var(--surface-raised)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
              <span className="text-[var(--text-tertiary)] uppercase text-[10px] block">Destructive Host Mutations</span>
              <span className="text-[var(--color-success)] font-bold mt-1 block">Strictly Blocked</span>
            </div>
          </div>
        </div>
      )}

      {/* Audit Log Table */}
      <div className="glass-panel rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Immutable System & Human Approval Logs</h3>
          <span className="text-xs text-[var(--text-secondary)] font-mono">{auditLogs.length} Events Recorded</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[var(--surface-raised)]/60 text-[var(--text-secondary)] uppercase text-[10px] border-b border-[var(--border-subtle)]">
              <tr>
                <th className="px-5 py-3 font-semibold">Timestamp (UTC)</th>
                <th className="px-5 py-3 font-semibold">Operator</th>
                <th className="px-5 py-3 font-semibold">Action</th>
                <th className="px-5 py-3 font-semibold">Target</th>
                <th className="px-5 py-3 font-semibold">Event Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-[var(--surface-raised)]/50 transition-colors">
                  <td className="px-5 py-3.5 text-[var(--text-secondary)]">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-5 py-3.5 text-[var(--accent-cyan)] font-semibold">{log.user}</td>
                  <td className="px-5 py-3.5 font-semibold text-[var(--text-primary)]">
                    <span className="px-2 py-0.5 rounded-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[11px]">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-[var(--text-secondary)]">
                    {log.target_type}: {log.target_id}
                  </td>
                  <td className="px-5 py-3.5 text-[var(--text-secondary)] font-mono text-[11px] truncate max-w-xs">
                    {JSON.stringify(log.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
