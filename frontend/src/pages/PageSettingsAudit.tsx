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
        <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
          <Settings className="text-obsidian-cyan" size={22} />
          System Settings & Immutable Governance Audit Trail
        </h2>
        <p className="text-xs text-obsidian-muted mt-1">
          Review system parameters, Hard Safety Envelope invariants, and auditable operational records.
        </p>
      </div>

      {/* Safety Envelope Invariants */}
      {settingsData && (
        <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-obsidian-text flex items-center gap-2">
              <Shield className="text-obsidian-teal" size={17} />
              Active Hard Safety Envelope Invariants
            </h3>
            <span className="px-2.5 py-1 rounded text-[10px] font-mono font-bold bg-obsidian-teal/15 text-obsidian-teal border border-obsidian-teal/30">
              ENFORCED IN SHADOW MODE
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div className="bg-obsidian-secondary/50 rounded p-3 border border-obsidian-border/50">
              <span className="text-obsidian-muted block text-[10px]">Critical Capacity Ceiling</span>
              <span className="text-obsidian-text font-bold mt-1 block">90% Utilization Cap</span>
            </div>

            <div className="bg-obsidian-secondary/50 rounded p-3 border border-obsidian-border/50">
              <span className="text-obsidian-muted block text-[10px]">Max Migration I/O Penalty</span>
              <span className="text-obsidian-text font-bold mt-1 block">35% Tail Latency Cap</span>
            </div>

            <div className="bg-obsidian-secondary/50 rounded p-3 border border-obsidian-border/50">
              <span className="text-obsidian-muted block text-[10px]">Destructive Host Mutations</span>
              <span className="text-obsidian-teal font-bold mt-1 block">Strictly Blocked</span>
            </div>
          </div>
        </div>
      )}

      {/* Audit Log Table */}
      <div className="bg-obsidian-panel border border-obsidian-border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-obsidian-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-obsidian-text">Immutable System & Human Approval Logs</h3>
          <span className="text-xs text-obsidian-muted font-mono">{auditLogs.length} Events Recorded</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-obsidian-secondary/50 text-obsidian-muted uppercase text-[10px] border-b border-obsidian-border">
              <tr>
                <th className="px-4 py-2.5">Timestamp (UTC)</th>
                <th className="px-4 py-2.5">Operator</th>
                <th className="px-4 py-2.5">Action</th>
                <th className="px-4 py-2.5">Target</th>
                <th className="px-4 py-2.5">Event Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-obsidian-border">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-obsidian-raised/40 transition-colors">
                  <td className="px-4 py-3 text-obsidian-muted">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-obsidian-cyan">{log.user}</td>
                  <td className="px-4 py-3 font-semibold text-obsidian-text">
                    <span className="px-1.5 py-0.5 rounded bg-obsidian-secondary border border-obsidian-border text-[11px]">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-obsidian-muted">
                    {log.target_type}: {log.target_id}
                  </td>
                  <td className="px-4 py-3 text-obsidian-muted font-mono text-[11px] truncate max-w-xs">
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
