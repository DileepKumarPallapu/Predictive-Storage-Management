import React, { useEffect, useState } from 'react';
import { Plug, KeyRound, Plus, Trash2, CheckCircle2, AlertCircle, RefreshCw, Copy } from 'lucide-react';
import { api, DeviceSummary } from '../api/client';

export const PageIntegrationManagement: React.FC = () => {
  const [connectors, setConnectors] = useState<any[]>([]);
  const [types, setTypes] = useState<string[]>([]);
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Connector Form
  const [connName, setConnName] = useState('');
  const [connType, setConnType] = useState('PROMETHEUS');
  const [endpointUrl, setEndpointUrl] = useState('http://127.0.0.1:9100');
  const [targetStorageId, setTargetStorageId] = useState('');
  const [pollFreq, setPollFreq] = useState(300);
  const [dbHost, setDbHost] = useState('');
  const [dbPort, setDbPort] = useState('5432');
  const [dbName, setDbName] = useState('');
  const [dbUser, setDbUser] = useState('');
  const [dbPassword, setDbPassword] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);

  const isDatabaseType = ['POSTGRESQL', 'MYSQL', 'MARIADB', 'MSSQL', 'ORACLE'].includes(connType);

  // API Key Form
  const [keyName, setKeyName] = useState('');
  const [keyRole, setKeyRole] = useState('OPERATOR');
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [typeRes, connRes, devRes, keysRes] = await Promise.all([
        api.getConnectorTypes(),
        api.getConnectors(),
        api.getDevices(),
        api.getApiKeys().catch(() => ({ api_keys: [] })),
      ]);
      setTypes(typeRes.supported_types || []);
      setConnectors(connRes.connectors || []);
      setDevices(devRes || []);
      setApiKeys(keysRes.api_keys || []);
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Failed to load integrations.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleRegisterConnector = async (e: React.FormEvent) => {
    e.preventDefault();
    setBanner(null);
    if (connName.trim().length < 2) {
      setBanner({ type: 'error', text: 'Connector name must be at least 2 characters.' });
      return;
    }
    try {
      const cfg: Record<string, any> = { collection_frequency_seconds: pollFreq };
      if (isDatabaseType) {
        if (dbHost.trim()) cfg.host = dbHost.trim();
        if (dbPort.trim()) cfg.port = Number(dbPort.trim()) || 5432;
        if (dbName.trim()) cfg.database = dbName.trim();
        if (dbUser.trim()) cfg.username = dbUser.trim();
        if (dbPassword) cfg.password = dbPassword;
      }
      await api.registerConnector({
        name: connName.trim(),
        connector_type: connType,
        endpoint_url: connType === 'LINUX_HOST' || isDatabaseType ? undefined : endpointUrl.trim() || undefined,
        target_storage_id: targetStorageId || undefined,
        config: cfg,
        is_enabled: true,
      });
      setConnName('');
      setDbPassword('');
      setBanner({ type: 'success', text: `Registered ${connType} data source cleanly.` });
      await loadAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Connector creation failed.' });
    }
  };

  const handleTestConnector = async (conn: any) => {
    setBanner(null);
    setBusyId(conn.id);
    try {
      const res = await api.testConnector(conn.id);
      const r = res?.result || {};
      const status = res?.last_status || r.status || 'UNKNOWN';
      setBanner({
        type: status === 'CONNECTED' ? 'success' : 'error',
        text:
          status === 'CONNECTED'
            ? `${conn.name}: Connected (read-only metadata verified).`
            : `${conn.name}: ${status} — ${r.error || 'Connection could not be verified.'}`,
      });
      await loadAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Connection test failed.' });
    } finally {
      setBusyId(null);
    }
  };

  const handleCollectConnector = async (conn: any) => {
    setBanner(null);
    setBusyId(conn.id);
    try {
      const res = await api.collectFromConnector(conn.id);
      const r = res?.result || {};
      if (r.status === 'CONNECTION_FAILED') {
        setBanner({ type: 'error', text: `${conn.name}: Collection failed — ${r.error || 'Check configuration.'}` });
      } else if (r.database_summary) {
        const sizeMb = Math.round((r.database_summary.logical_size_bytes || 0) / (1024 * 1024));
        setBanner({
          type: 'success',
          text: `${conn.name}: Collected logical DB metadata (${r.database_summary.database_name}, ${sizeMb} MiB across ${r.database_summary.table_count_sampled} tables).`,
        });
      } else {
        setBanner({
          type: 'success',
          text: `${conn.name}: Collected ${r.volumes_count ?? 0} volume(s), persisted ${res?.persisted_count ?? 0} record(s).`,
        });
      }
      await loadAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Collection failed.' });
    } finally {
      setBusyId(null);
    }
  };

  const handleToggleConnector = async (conn: any) => {
    setBanner(null);
    try {
      await api.updateConnector(conn.id, { is_enabled: !conn.is_enabled });
      setBanner({ type: 'success', text: `Connector ${conn.name} ${!conn.is_enabled ? 'enabled' : 'disabled'}.` });
      await loadAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Failed to update connector.' });
    }
  };

  const handleDeleteConnector = async (id: string) => {
    setBanner(null);
    try {
      await api.deleteConnector(id);
      setBanner({ type: 'success', text: `Connector ${id} deleted.` });
      await loadAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Delete failed (Admin role required).' });
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setBanner(null);
    setNewlyCreatedKey(null);
    if (keyName.trim().length < 2) {
      setBanner({ type: 'error', text: 'API key name must be at least 2 characters.' });
      return;
    }
    try {
      const res = await api.createApiKey(keyName.trim(), keyRole);
      setNewlyCreatedKey(res.api_key);
      setKeyName('');
      setBanner({ type: 'success', text: 'API key issued. Copy the secret now; it is hashed at rest and never shown again.' });
      await loadAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Failed to create API key (Admin role required).' });
    }
  };

  const handleRevokeKey = async (id: string) => {
    setBanner(null);
    try {
      await api.revokeApiKey(id);
      setBanner({ type: 'success', text: `API key ${id} revoked.` });
      await loadAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Failed to revoke key.' });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Plug size={20} className="text-[var(--brand-primary)]" />
            Data Sources & Connections
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Connect storage hosts, Prometheus monitoring, enterprise databases (PostgreSQL, MySQL, MariaDB, SQL Server, Oracle), CSV imports, and API keys. All database connectors use read-only metadata queries only; saved passwords are never shown again.
          </p>
        </div>
        <button
          type="button"
          onClick={loadAll}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)]"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          Refresh
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

      {/* Register Telemetry Connector */}
      <form onSubmit={handleRegisterConnector} className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
          <Plus size={15} className="text-[var(--brand-primary)]" />
          Register Read-Only Telemetry Connector
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <input
            type="text"
            placeholder="Connector Name (e.g. Prod Prom)"
            value={connName}
            onChange={(e) => setConnName(e.target.value)}
            required
            className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
          />
          <select
            aria-label="Connector type"
            value={connType}
            onChange={(e) => setConnType(e.target.value)}
            className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
          >
            {(types.length ? types : ['LINUX_HOST', 'PROMETHEUS', 'CSV_HISTORICAL', 'HTTP_API', 'POSTGRESQL', 'MYSQL', 'MARIADB', 'MSSQL', 'ORACLE']).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder={isDatabaseType ? 'Configured via DB fields below' : 'Endpoint URL (if applicable)'}
            value={connType === 'LINUX_HOST' ? 'local-host-read-only' : isDatabaseType ? 'read-only-database-metadata' : endpointUrl}
            disabled={connType === 'LINUX_HOST' || isDatabaseType}
            onChange={(e) => setEndpointUrl(e.target.value)}
            className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono disabled:opacity-60"
          />
          <select
            aria-label="Associated storage volume"
            value={targetStorageId}
            onChange={(e) => setTargetStorageId(e.target.value)}
            className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
          >
            <option value="">Target Volume (Optional)</option>
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <div className="flex gap-2">
            <input
              type="number"
              min={15}
              value={pollFreq}
              onChange={(e) => setPollFreq(Number(e.target.value))}
              title="Collection interval (seconds)"
              className="w-20 px-2 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
            />
            <button
              type="submit"
              className="flex-1 px-3 py-1.5 text-xs font-medium rounded bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white"
            >
              Add Data Source
            </button>
          </div>
        </div>
        {isDatabaseType && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-2 border-t border-[var(--border-subtle)]">
            <input
              type="text"
              placeholder="DB Host (e.g. 127.0.0.1)"
              value={dbHost}
              onChange={(e) => setDbHost(e.target.value)}
              className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
            />
            <input
              type="text"
              placeholder="Port (e.g. 5432)"
              value={dbPort}
              onChange={(e) => setDbPort(e.target.value)}
              className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)] font-mono"
            />
            <input
              type="text"
              placeholder="Database / Service Name"
              value={dbName}
              onChange={(e) => setDbName(e.target.value)}
              className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
            />
            <input
              type="text"
              placeholder="Read-Only Username"
              value={dbUser}
              onChange={(e) => setDbUser(e.target.value)}
              className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
            />
            <input
              type="password"
              placeholder="Password (write-only)"
              value={dbPassword}
              onChange={(e) => setDbPassword(e.target.value)}
              className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
            />
          </div>
        )}
      </form>

      {/* Connector Table */}
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">Configured Integrations ({connectors.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <th className="py-2 px-3">Name</th>
                <th className="py-2 px-3">Type</th>
                <th className="py-2 px-3">Target</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Enabled</th>
                <th className="py-2 px-3 text-right">Manage</th>
              </tr>
            </thead>
            <tbody>
              {connectors.map((c) => (
                <tr key={c.id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                  <td className="py-2 px-3 font-semibold">{c.name}</td>
                  <td className="py-2 px-3 font-mono">{c.connector_type}</td>
                  <td className="py-2 px-3 font-mono">{c.target_storage_id || 'Unbound'}</td>
                  <td className="py-2 px-3">
                    <span className="font-mono">{c.last_status}</span>
                    {c.last_error && (
                      <div className="text-[11px] text-[var(--status-critical)] mt-0.5 max-w-xs truncate" title={c.last_error}>
                        {c.last_error}
                      </div>
                    )}
                  </td>
                  <td className="py-2 px-3">
                    <button
                      type="button"
                      onClick={() => handleToggleConnector(c)}
                      className={`px-2 py-0.5 rounded font-mono text-[11px] ${
                        c.is_enabled ? 'bg-[var(--status-success)]/15 text-[var(--status-success)]' : 'bg-[var(--surface-secondary)] text-[var(--text-muted)]'
                      }`}
                    >
                      {c.is_enabled ? 'ENABLED' : 'DISABLED'}
                    </button>
                  </td>
                  <td className="py-2 px-3 text-right space-x-3 whitespace-nowrap">
                    <button
                      type="button"
                      disabled={busyId === c.id}
                      onClick={() => handleTestConnector(c)}
                      className="text-[var(--brand-primary)] hover:underline inline-flex items-center gap-1 disabled:opacity-50"
                    >
                      Test
                    </button>
                    <button
                      type="button"
                      disabled={busyId === c.id || !c.is_enabled}
                      onClick={() => handleCollectConnector(c)}
                      className="text-[var(--status-success)] hover:underline inline-flex items-center gap-1 disabled:opacity-50"
                    >
                      Collect
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteConnector(c.id)}
                      className="text-[var(--status-critical)] hover:underline inline-flex items-center gap-1"
                    >
                      <Trash2 size={12} /> Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* API Keys */}
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
          <KeyRound size={15} className="text-[var(--brand-primary)]" />
          Collector API Keys (Hashed Storage — Write-Once Reveal)
        </h3>
        <form onSubmit={handleCreateKey} className="flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Key label (e.g. datacenter-east-agent)"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            required
            className="flex-1 min-w-[200px] px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
          />
          <select
            aria-label="API Key Role"
            value={keyRole}
            onChange={(e) => setKeyRole(e.target.value)}
            className="px-3 py-1.5 text-xs rounded border border-[var(--border-subtle)] bg-[var(--surface-secondary)]"
          >
            <option value="OPERATOR">OPERATOR</option>
            <option value="VIEWER">VIEWER</option>
            <option value="ADMIN">ADMIN</option>
          </select>
          <button
            type="submit"
            className="px-3 py-1.5 text-xs font-medium rounded bg-[var(--brand-primary)] hover:bg-[var(--brand-hover)] text-white"
          >
            Issue API Key
          </button>
        </form>

        {newlyCreatedKey && (
          <div className="p-3 rounded bg-[var(--surface-secondary)] border border-[var(--status-warning)]/40 text-xs flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="font-semibold text-[var(--status-warning)]">Copy Key Now (Shown Once): </span>
              <code className="font-mono text-[var(--text-primary)]">{newlyCreatedKey}</code>
            </div>
            <button
              type="button"
              onClick={() => navigator.clipboard?.writeText(newlyCreatedKey)}
              className="inline-flex items-center gap-1 px-2 py-1 rounded border border-[var(--border-subtle)] bg-[var(--surface-primary)] text-[11px]"
            >
              <Copy size={11} /> Copy
            </button>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="bg-[var(--surface-secondary)] border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <th className="py-2 px-3">Name</th>
                <th className="py-2 px-3">Prefix (Redacted)</th>
                <th className="py-2 px-3">Role</th>
                <th className="py-2 px-3">State</th>
                <th className="py-2 px-3">Last Used</th>
                <th className="py-2 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {apiKeys.map((k) => (
                <tr key={k.id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                  <td className="py-2 px-3 font-semibold">{k.name}</td>
                  <td className="py-2 px-3 font-mono">{k.key_prefix}...</td>
                  <td className="py-2 px-3 font-mono">{k.role}</td>
                  <td className="py-2 px-3 font-mono">{k.is_active ? 'ACTIVE' : 'REVOKED'}</td>
                  <td className="py-2 px-3 font-mono text-[var(--text-muted)]">{k.last_used_at ? k.last_used_at.slice(0, 19) : 'Never'}</td>
                  <td className="py-2 px-3 text-right">
                    {k.is_active && (
                      <button type="button" onClick={() => handleRevokeKey(k.id)} className="text-[var(--status-critical)] hover:underline">
                        Revoke
                      </button>
                    )}
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
