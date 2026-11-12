import React, { useEffect, useState } from 'react';
import { Network, Server, HardDrive, Plug, RefreshCw, AlertCircle, Database } from 'lucide-react';
import { api } from '../api/client';

interface PageStorageTopologyProps {
  onSelectDevice?: (deviceId: string) => void;
}

export const PageStorageTopology: React.FC<PageStorageTopologyProps> = ({ onSelectDevice }) => {
  const [topology, setTopology] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEnv, setSelectedEnv] = useState<string>('ALL');

  const loadTopology = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStorageTopology();
      setTopology(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load persisted storage topology.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTopology();
  }, []);

  const volumes: any[] = topology?.volumes || [];
  const pools: any[] = topology?.pools || [];
  const systems: any[] = topology?.systems || [];
  const connectors: any[] = topology?.connectors || [];
  const relationships: any[] = topology?.relationships || [];
  const workloads: any[] = topology?.workloads || [];

  const environments = ['ALL', ...Array.from(new Set(volumes.map((v) => v.environment_location || 'Unassigned')))];
  const filteredVolumes = selectedEnv === 'ALL' ? volumes : volumes.filter((v) => (v.environment_location || 'Unassigned') === selectedEnv);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <Network size={20} className="text-[var(--brand-primary)]" />
            Storage Topology
          </h2>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Persisted physical & collector relationships between storage systems, pools, volumes, workloads, and telemetry connectors. Unlinked assets remain standalone without invented edges.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            aria-label="Filter topology environment"
            value={selectedEnv}
            onChange={(e) => setSelectedEnv(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-md bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-[var(--text-primary)]"
          >
            {environments.map((env) => (
              <option key={env} value={env}>
                Env: {env}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={loadTopology}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-[var(--surface-primary)] border border-[var(--border-subtle)] hover:bg-[var(--surface-secondary)] text-[var(--text-primary)]"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg border border-[var(--status-critical)]/30 bg-[var(--brand-soft)] text-xs text-[var(--status-critical)] flex items-center gap-2">
          <AlertCircle size={15} />
          {error}
        </div>
      )}

      {/* Summary Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          { label: 'Storage Systems', val: systems.length, icon: Server },
          { label: 'Storage Pools', val: pools.length, icon: Database },
          { label: 'Storage Volumes', val: filteredVolumes.length, icon: HardDrive },
          { label: 'Attached Connectors', val: connectors.length, icon: Plug },
          { label: 'Verified Edges', val: relationships.length, icon: Network },
        ].map((card) => (
          <div key={card.label} className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-3.5">
            <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
              <span>{card.label}</span>
              <card.icon size={14} />
            </div>
            <div className="text-xl font-bold font-mono text-[var(--text-primary)] mt-1">{card.val}</div>
          </div>
        ))}
      </div>

      {/* Systems -> Pools -> Volumes Hierarchy */}
      <div className="space-y-4">
        {systems.map((sys) => {
          const sysPools = pools.filter((p) => p.system_id === sys.id);
          return (
            <div key={sys.id} className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] pb-2.5">
                <div className="flex items-center gap-2">
                  <Server size={16} className="text-[var(--brand-primary)]" />
                  <span className="font-semibold text-sm text-[var(--text-primary)]">{sys.name}</span>
                  <span className="text-[11px] font-mono text-[var(--text-muted)]">({sys.id})</span>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="px-2 py-0.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] font-mono">
                    {sys.system_type} · {sys.interconnect_type}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[var(--surface-secondary)] font-mono text-[var(--status-success)]">
                    {sys.status}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {sysPools.map((pool) => {
                  const poolVols = filteredVolumes.filter((v) => v.pool_id === pool.id);
                  return (
                    <div key={pool.id} className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-md p-3 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-xs font-semibold text-[var(--text-primary)] flex items-center gap-1.5">
                          <Database size={13} className="text-[var(--brand-primary)]" />
                          {pool.name}
                        </div>
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
                          {pool.redundancy_policy} · {pool.tier}
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {poolVols.length === 0 ? (
                          <div className="text-[11px] text-[var(--text-muted)] italic">No matching volumes in selected filter.</div>
                        ) : (
                          poolVols.map((vol) => {
                            const attachedConns = connectors.filter((c) => c.target_storage_id === vol.id);
                            const attachedWorkloads = workloads.filter((w) => w.device_id === vol.id);
                            return (
                              <div
                                key={vol.id}
                                className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded p-2.5 text-xs flex flex-col gap-1.5"
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <button
                                    type="button"
                                    onClick={() => onSelectDevice?.(vol.id)}
                                    className="font-semibold text-[var(--text-primary)] hover:text-[var(--brand-primary)] text-left"
                                  >
                                    {vol.name}
                                  </button>
                                  <span className="font-mono text-[11px] text-[var(--text-muted)]">
                                    {(vol.total_capacity_bytes / 1024 ** 3).toFixed(0)} GB · {vol.environment_location}
                                  </span>
                                </div>
                                <div className="flex flex-wrap gap-1.5 text-[10px]">
                                  {attachedConns.map((c) => (
                                    <span key={c.id} className="px-1.5 py-0.5 rounded bg-[var(--brand-soft)] text-[var(--brand-primary)] font-mono">
                                      Collector: {c.connector_type} ({c.last_status})
                                    </span>
                                  ))}
                                  {attachedWorkloads.map((w) => (
                                    <span key={w.id} className="px-1.5 py-0.5 rounded bg-[var(--surface-secondary)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
                                      Workload: {w.workload_name} ({w.criticality})
                                    </span>
                                  ))}
                                  {attachedConns.length === 0 && attachedWorkloads.length === 0 && (
                                    <span className="text-[var(--text-muted)]">No external collector or workload mapped</span>
                                  )}
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {/* Standalone / Host-Discovered Volumes without a Pool/System Link */}
        {(() => {
          const poolIds = new Set(pools.map((p) => p.id));
          const unlinked = filteredVolumes.filter((v) => !v.pool_id || !poolIds.has(v.pool_id));
          if (unlinked.length === 0) return null;
          return (
            <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-2.5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                  Standalone & Host-Associated Volumes (No Invented Pool Links)
                </h3>
                <span className="text-xs font-mono text-[var(--text-muted)]">{unlinked.length} resource(s)</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {unlinked.map((vol) => {
                  const attachedConns = connectors.filter((c) => c.target_storage_id === vol.id);
                  return (
                    <div key={vol.id} className="bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded-md p-3 text-xs space-y-1">
                      <div className="font-semibold text-[var(--text-primary)]">{vol.name}</div>
                      <div className="text-[var(--text-muted)] font-mono">
                        {vol.id} · {vol.storage_type} · {vol.environment_location}
                      </div>
                      {attachedConns.length > 0 ? (
                        attachedConns.map((c) => (
                          <div key={c.id} className="text-[11px] text-[var(--brand-primary)] font-mono">
                            Linked Collector: {c.name} ({c.connector_type} · {c.last_status})
                          </div>
                        ))
                      ) : (
                        <div className="text-[11px] text-[var(--text-muted)]">No pool or collector edge collected</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })()}
      </div>

      {/* Explicit Persisted Interconnect Edges Table */}
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Persisted Infrastructure Relationships</h3>
        {relationships.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No persisted topology edges recorded.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] text-[var(--text-muted)] bg-[var(--surface-secondary)]">
                  <th className="py-2 px-3">Relationship ID</th>
                  <th className="py-2 px-3">Source Resource</th>
                  <th className="py-2 px-3">Type</th>
                  <th className="py-2 px-3">Target Resource</th>
                  <th className="py-2 px-3">Weight</th>
                </tr>
              </thead>
              <tbody>
                {relationships.map((r) => (
                  <tr key={r.id} className="border-b border-[var(--border-subtle)] last:border-b-0">
                    <td className="py-2 px-3 font-mono text-[var(--text-muted)]">{r.id}</td>
                    <td className="py-2 px-3 font-mono text-[var(--text-primary)]">{r.source_id}</td>
                    <td className="py-2 px-3">
                      <span className="px-2 py-0.5 rounded bg-[var(--surface-secondary)] font-mono">{r.relationship_type}</span>
                    </td>
                    <td className="py-2 px-3 font-mono text-[var(--text-primary)]">{r.target_id}</td>
                    <td className="py-2 px-3 font-mono">{r.weight}</td>
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
