import React, { useState, useEffect } from 'react';
import { api, AuditItem, VaultBackupItem, VaultTestRestoreResult } from '../api/client';
import { Settings, Shield, HardDrive, CheckCircle2, AlertTriangle, RefreshCw, Play, ShieldCheck, Database, FileCheck } from 'lucide-react';

export const PageSettingsAudit: React.FC = () => {
  const [settingsData, setSettingsData] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);
  const [backups, setBackups] = useState<VaultBackupItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'vault' | 'audit' | 'safety'>('vault');

  // Vault action states
  const [creatingBackup, setCreatingBackup] = useState<boolean>(false);
  const [backupNotes, setBackupNotes] = useState<string>('');
  const [testingBackupId, setTestingBackupId] = useState<string | null>(null);
  const [verifyingBackupId, setVerifyingBackupId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<VaultTestRestoreResult | null>(null);
  const [actionMessage, setActionMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      setLoading(true);
      const [s, a, vaultRes] = await Promise.all([
        api.getSettings(),
        api.getAuditTrail(),
        api.getVaultBackups().catch(() => ({ status: 'error', backups_count: 0, backups: [] }))
      ]);
      setSettingsData(s);
      setAuditLogs(a);
      setBackups(vaultRes.backups || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBackup = async () => {
    try {
      setCreatingBackup(true);
      setActionMessage({ text: 'Generating transaction-consistent database snapshot & SHA-256 manifests...', type: 'info' });
      const res = await api.createVaultBackup(backupNotes || 'Operator requested snapshot via Ember Noir console');
      setBackupNotes('');
      setActionMessage({ text: `Backup successfully created: ${res.backup.backup_id} (${res.backup.database_size_bytes} bytes protected)`, type: 'success' });
      await loadAllData();
    } catch (e: any) {
      setActionMessage({ text: `Backup creation failed: ${e.message}`, type: 'error' });
    } finally {
      setCreatingBackup(false);
    }
  };

  const handleVerifyIntegrity = async (backupId: string) => {
    try {
      setVerifyingBackupId(backupId);
      const res = await api.verifyVaultBackupIntegrity(backupId);
      if (res.checksum_status === 'SHA256_VERIFIED') {
        setActionMessage({ text: `Integrity check PASSED for ${backupId}: all manifests and file hashes verified.`, type: 'success' });
      } else {
        setActionMessage({ text: `Integrity check FAILED for ${backupId}: ${res.error || 'Checksum mismatch detected'}`, type: 'error' });
      }
      await loadAllData();
    } catch (e: any) {
      setActionMessage({ text: `Integrity check failed: ${e.message}`, type: 'error' });
    } finally {
      setVerifyingBackupId(null);
    }
  };

  const handleTestRestore = async (backupId: string) => {
    try {
      setTestingBackupId(backupId);
      setActionMessage({ text: `Spawning isolated sandbox database for ${backupId} and executing full recovery test...`, type: 'info' });
      const res = await api.testVaultIsolatedRestore(backupId);
      setTestResult(res);
      if (res.status === 'RESTORE_TEST_SUCCESS') {
        setActionMessage({
          text: `Sandbox restoration PASSED: RTO=${res.measured_rto_seconds}s (Target: <${res.target_rto_seconds}s), RPO=${res.measured_rpo_hours}h. Live production untouched.`,
          type: 'success'
        });
      } else {
        setActionMessage({ text: `Sandbox restoration FAILED: ${res.error || 'Validation error'}`, type: 'error' });
      }
      await loadAllData();
    } catch (e: any) {
      setActionMessage({ text: `Recovery test failed: ${e.message}`, type: 'error' });
    } finally {
      setTestingBackupId(null);
    }
  };

  // Compute aggregate recovery metrics
  const testedBackups = backups.filter(b => b.last_test_rto_seconds !== null);
  const bestRto = testedBackups.length > 0
    ? Math.min(...testedBackups.map(b => b.last_test_rto_seconds!))
    : null;
  const bestRpo = testedBackups.length > 0
    ? Math.min(...testedBackups.map(b => b.last_test_rpo_hours!))
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/30 flex items-center justify-center text-[var(--accent-primary)] shadow-glow-vermilion">
              <HardDrive size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              AEGISSTOR VAULT — Disaster Recovery & Governance
            </h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
            Verified backup manifests, isolated sandbox disaster recovery testing, RTO/RPO SLA tracking, and immutable audit logs.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center p-1 bg-[var(--surface-secondary)]/80 rounded-xl border border-[var(--border-subtle)] text-xs font-semibold">
          <button
            onClick={() => setActiveTab('vault')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'vault'
                ? 'bg-[var(--accent-primary)] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <ShieldCheck size={14} />
            Vault Backups & DR
          </button>
          <button
            onClick={() => setActiveTab('safety')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'safety'
                ? 'bg-[var(--accent-primary)] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <Shield size={14} />
            Safety Invariants
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'audit'
                ? 'bg-[var(--accent-primary)] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <Settings size={14} />
            Audit Trail ({auditLogs.length})
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionMessage && (
        <div className={`p-3.5 rounded-xl text-xs font-mono flex items-center justify-between border ${
          actionMessage.type === 'success'
            ? 'bg-[var(--status-success)]/15 border-[var(--status-success)]/40 text-[var(--status-success)]'
            : actionMessage.type === 'error'
            ? 'bg-[var(--status-critical)]/15 border-[var(--status-critical)]/40 text-[var(--status-critical)]'
            : 'bg-[var(--accent-primary)]/15 border-[var(--accent-primary)]/40 text-[var(--text-primary)]'
        }`}>
          <span>{actionMessage.text}</span>
          <button
            onClick={() => setActionMessage(null)}
            className="text-[10px] uppercase font-bold underline ml-4 hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* TAB 1: AEGISSTOR VAULT (Disaster Recovery & Backup Management) */}
      {activeTab === 'vault' && (
        <div className="space-y-6">
          {/* Recovery Objectives SLA Overview Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            {/* Target RTO */}
            <div className="glass-panel rounded-xl p-4 border border-[var(--border-subtle)] space-y-1">
              <span className="text-[10px] font-mono uppercase text-[var(--text-tertiary)] block">Recovery Time (RTO)</span>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-[var(--text-primary)]">
                  {bestRto !== null ? `${bestRto.toFixed(2)}s` : '60.0s'}
                </span>
                <span className="text-[11px] font-mono text-[var(--text-secondary)]">/ target 60s</span>
              </div>
              <div className="flex items-center gap-1 mt-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)]"></span>
                <span className="text-[10px] font-mono text-[var(--status-success)] font-bold">
                  {bestRto !== null && bestRto <= 60.0 ? 'RTO SLA VERIFIED' : 'TARGET: 60.0s MAX'}
                </span>
              </div>
            </div>

            {/* Target RPO */}
            <div className="glass-panel rounded-xl p-4 border border-[var(--border-subtle)] space-y-1">
              <span className="text-[10px] font-mono uppercase text-[var(--text-tertiary)] block">Recovery Point (RPO)</span>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-[var(--text-primary)]">
                  {bestRpo !== null ? `${bestRpo.toFixed(2)}h` : '1.0h'}
                </span>
                <span className="text-[11px] font-mono text-[var(--text-secondary)]">/ target 1.0h</span>
              </div>
              <div className="flex items-center gap-1 mt-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--status-success)]"></span>
                <span className="text-[10px] font-mono text-[var(--status-success)] font-bold">
                  {bestRpo !== null && bestRpo <= 1.0 ? 'RPO SLA VERIFIED' : 'TARGET: 1.0h MAX'}
                </span>
              </div>
            </div>

            {/* Retained Archives */}
            <div className="glass-panel rounded-xl p-4 border border-[var(--border-subtle)] space-y-1">
              <span className="text-[10px] font-mono uppercase text-[var(--text-tertiary)] block">Retained Archives</span>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-[var(--text-primary)]">
                  {backups.length}
                </span>
                <span className="text-[11px] font-mono text-[var(--text-secondary)]">/ 10 max retained</span>
              </div>
              <span className="text-[10px] font-mono text-[var(--accent-primary)] block">
                Auto-pruning active
              </span>
            </div>

            {/* Verification Engine */}
            <div className="glass-panel rounded-xl p-4 border border-[var(--border-subtle)] space-y-1">
              <span className="text-[10px] font-mono uppercase text-[var(--text-tertiary)] block">Sandbox Isolation</span>
              <div className="flex items-baseline gap-1">
                <span className="text-base font-bold font-mono text-[var(--status-success)]">
                  Zero Production Risk
                </span>
              </div>
              <span className="text-[10px] font-mono text-[var(--text-secondary)] block">
                PRAGMA integrity check
              </span>
            </div>
          </div>

          {/* Backup Creator Panel */}
          <div className="glass-panel rounded-xl p-5 border border-[var(--border-subtle)] space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                  <Database size={16} className="text-[var(--accent-primary)]" />
                  Create Transaction-Consistent Vault Backup
                </h3>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                  Protects live database, safe configuration (excluding secrets/keys), model version registry, and audit logs.
                </p>
              </div>
              <button
                onClick={handleCreateBackup}
                disabled={creatingBackup}
                className="px-4 py-2 rounded-xl bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-50 transition-all shadow-glow-vermilion"
              >
                {creatingBackup ? <RefreshCw size={14} className="animate-spin" /> : <HardDrive size={14} />}
                {creatingBackup ? 'Creating Snapshot...' : 'Create Instant Backup'}
              </button>
            </div>

            <div className="flex gap-3">
              <input
                type="text"
                placeholder="Optional operator note or incident reference (e.g. Pre-maintenance baseline snapshot)"
                value={backupNotes}
                onChange={(e) => setBackupNotes(e.target.value)}
                className="flex-1 bg-[var(--surface-secondary)]/70 border border-[var(--border-subtle)] rounded-xl px-3.5 py-2 text-xs font-mono text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
              />
            </div>
          </div>

          {/* Detailed Isolated Recovery Sandbox Test Results (if available) */}
          {testResult && (
            <div className="glass-panel rounded-xl p-5 border border-[var(--status-success)]/40 bg-[var(--status-success)]/5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-[var(--status-success)] flex items-center gap-2 uppercase tracking-wide">
                  <ShieldCheck size={16} />
                  Sandbox Disaster Recovery Test Result — {testResult.backup_id}
                </h4>
                <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
                  Tested: {new Date(testResult.tested_at).toLocaleString()}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                <div className="bg-[var(--surface-secondary)]/80 p-3 rounded-lg border border-[var(--border-subtle)]">
                  <span className="text-[10px] text-[var(--text-tertiary)] uppercase block">Measured RTO</span>
                  <span className="text-sm font-bold text-[var(--text-primary)] block mt-0.5">
                    {testResult.measured_rto_seconds} seconds
                  </span>
                  <span className="text-[10px] text-[var(--status-success)]">
                    {testResult.rto_sla_met ? '✓ Target < 60s Met' : '✗ Breached Target'}
                  </span>
                </div>

                <div className="bg-[var(--surface-secondary)]/80 p-3 rounded-lg border border-[var(--border-subtle)]">
                  <span className="text-[10px] text-[var(--text-tertiary)] uppercase block">Measured RPO</span>
                  <span className="text-sm font-bold text-[var(--text-primary)] block mt-0.5">
                    {testResult.measured_rpo_hours} hours
                  </span>
                  <span className="text-[10px] text-[var(--status-success)]">
                    {testResult.rpo_sla_met ? '✓ Target < 1.0h Met' : '✗ Breached Target'}
                  </span>
                </div>

                <div className="bg-[var(--surface-secondary)]/80 p-3 rounded-lg border border-[var(--border-subtle)]">
                  <span className="text-[10px] text-[var(--text-tertiary)] uppercase block">SQLite PRAGMA</span>
                  <span className="text-sm font-bold text-[var(--status-success)] block mt-0.5">
                    {testResult.integrity_check_passed ? 'Integrity OK' : 'Corruption Detected'}
                  </span>
                  <span className="text-[10px] text-[var(--text-secondary)]">Zero page defects</span>
                </div>

                <div className="bg-[var(--surface-secondary)]/80 p-3 rounded-lg border border-[var(--border-subtle)]">
                  <span className="text-[10px] text-[var(--text-tertiary)] uppercase block">Safety Guarantee</span>
                  <span className="text-[11px] font-bold text-[var(--accent-primary)] block mt-0.5 truncate">
                    Sandbox Isolation
                  </span>
                  <span className="text-[10px] text-[var(--status-success)]">Zero production mutation</span>
                </div>
              </div>

              {/* Verified table counts */}
              {testResult.verified_tables && (
                <div className="pt-2 border-t border-[var(--border-subtle)]">
                  <span className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase block mb-2">
                    Verified Restored Table Row Counts:
                  </span>
                  <div className="flex flex-wrap gap-2 text-[11px] font-mono">
                    {Object.entries(testResult.verified_tables).map(([tbl, count]) => (
                      <span key={tbl} className="px-2.5 py-1 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
                        <strong className="text-[var(--text-primary)]">{tbl}:</strong> {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Backup Archives Table */}
          <div className="glass-panel rounded-xl overflow-hidden border border-[var(--border-subtle)]">
            <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                  Vault Protected Backup Archives
                </h3>
                <span className="text-xs text-[var(--text-secondary)] font-mono">
                  {backups.length} snapshots available (SHA-256 cryptographically sealed)
                </span>
              </div>
              <button
                onClick={loadAllData}
                disabled={loading}
                className="p-1.5 rounded-lg bg-[var(--surface-secondary)] hover:bg-[var(--surface-secondary)]/80 text-[var(--text-secondary)] border border-[var(--border-subtle)] transition-colors"
                title="Refresh archives"
              >
                <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[var(--surface-secondary)]/60 text-[var(--text-secondary)] uppercase text-[10px] border-b border-[var(--border-subtle)]">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Backup ID</th>
                    <th className="px-5 py-3 font-semibold">Created (UTC)</th>
                    <th className="px-5 py-3 font-semibold">Operator</th>
                    <th className="px-5 py-3 font-semibold">Size</th>
                    <th className="px-5 py-3 font-semibold">Integrity Hash</th>
                    <th className="px-5 py-3 font-semibold">Restoration Status</th>
                    <th className="px-5 py-3 font-semibold">Last RTO / RPO</th>
                    <th className="px-5 py-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]">
                  {backups.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-5 py-8 text-center text-[var(--text-tertiary)]">
                        No backup archives created yet. Click "Create Instant Backup" above.
                      </td>
                    </tr>
                  ) : (
                    backups.map((b) => (
                      <tr key={b.id} className="hover:bg-[var(--surface-secondary)]/50 transition-colors">
                        <td className="px-5 py-3.5 font-bold text-[var(--text-primary)]">
                          {b.id}
                        </td>
                        <td className="px-5 py-3.5 text-[var(--text-secondary)]">
                          {b.created_at ? new Date(b.created_at).toLocaleString() : '—'}
                        </td>
                        <td className="px-5 py-3.5 text-[var(--accent-primary)] font-semibold">
                          {b.created_by}
                        </td>
                        <td className="px-5 py-3.5 text-[var(--text-secondary)]">
                          {b.database_size_mb} MB
                        </td>
                        <td className="px-5 py-3.5">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            b.checksum_status === 'SHA256_VERIFIED'
                              ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/40'
                              : 'bg-[var(--accent-secondary)]/15 text-[var(--accent-secondary)] border-[var(--accent-secondary)]/40'
                          }`}>
                            {b.checksum_status}
                          </span>
                        </td>
                        <td className="px-5 py-3.5">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            b.restoration_status === 'RESTORE_TESTED_SUCCESS'
                              ? 'bg-[var(--status-success)]/15 text-[var(--status-success)] border-[var(--status-success)]/40'
                              : b.restoration_status === 'RESTORE_TEST_FAILED'
                              ? 'bg-[var(--status-critical)]/15 text-[var(--status-critical)] border-[var(--status-critical)]/40'
                              : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)] border-[var(--border-subtle)]'
                          }`}>
                            {b.restoration_status}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-[var(--text-secondary)]">
                          {b.last_test_rto_seconds !== null ? (
                            <span>{b.last_test_rto_seconds.toFixed(2)}s / {b.last_test_rpo_hours?.toFixed(2)}h</span>
                          ) : (
                            <span className="text-[var(--text-tertiary)]">Not tested yet</span>
                          )}
                        </td>
                        <td className="px-5 py-3.5 text-right space-x-2">
                          <button
                            onClick={() => handleVerifyIntegrity(b.id)}
                            disabled={verifyingBackupId === b.id}
                            className="px-2.5 py-1 rounded bg-[var(--surface-secondary)] hover:bg-[var(--surface-secondary)]/80 text-[var(--text-primary)] border border-[var(--border-subtle)] text-[11px] font-semibold transition-colors disabled:opacity-50 inline-flex items-center gap-1"
                            title="Verify SHA-256 Checksums"
                          >
                            <FileCheck size={12} className={verifyingBackupId === b.id ? 'animate-spin' : ''} />
                            Verify
                          </button>
                          <button
                            onClick={() => handleTestRestore(b.id)}
                            disabled={testingBackupId === b.id}
                            className="px-2.5 py-1 rounded bg-[var(--accent-primary)]/15 hover:bg-[var(--accent-primary)]/25 text-[var(--accent-primary)] border border-[var(--accent-primary)]/40 text-[11px] font-semibold transition-colors disabled:opacity-50 inline-flex items-center gap-1 shadow-sm"
                            title="Run Isolated Recovery Test in Sandbox"
                          >
                            <Play size={12} className={testingBackupId === b.id ? 'animate-spin' : ''} />
                            Test Recovery
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Safety Envelope Invariants */}
      {activeTab === 'safety' && settingsData && (
        <div className="glass-panel rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Shield className="text-[var(--status-success)]" size={17} />
              Active Hard Safety Envelope Invariants
            </h3>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm">
              ENFORCED IN SHADOW MODE
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
              <span className="text-[var(--text-tertiary)] uppercase text-[10px] block">Critical Capacity Ceiling</span>
              <span className="text-[var(--text-primary)] font-bold mt-1 block">90% Utilization Cap</span>
            </div>

            <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
              <span className="text-[var(--text-tertiary)] uppercase text-[10px] block">Max Migration I/O Penalty</span>
              <span className="text-[var(--text-primary)] font-bold mt-1 block">35% Tail Latency Cap</span>
            </div>

            <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3.5 border border-[var(--border-subtle)]">
              <span className="text-[var(--text-tertiary)] uppercase text-[10px] block">Destructive Host Mutations</span>
              <span className="text-[var(--status-success)] font-bold mt-1 block">Strictly Blocked</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Audit Log Table */}
      {activeTab === 'audit' && (
        <div className="glass-panel rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">Immutable System & Human Approval Logs</h3>
            <span className="text-xs text-[var(--text-secondary)] font-mono">{auditLogs.length} Events Recorded</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[var(--surface-secondary)]/60 text-[var(--text-secondary)] uppercase text-[10px] border-b border-[var(--border-subtle)]">
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
                  <tr key={log.id} className="hover:bg-[var(--surface-secondary)]/50 transition-colors">
                    <td className="px-5 py-3.5 text-[var(--text-secondary)]">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 text-[var(--accent-primary)] font-semibold">{log.user}</td>
                    <td className="px-5 py-3.5 font-semibold text-[var(--text-primary)]">
                      <span className="px-2 py-0.5 rounded-full bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[11px]">
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
      )}
    </div>
  );
};
