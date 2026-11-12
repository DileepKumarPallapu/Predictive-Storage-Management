import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, ScenarioSimulationResponse, TelemetryResponse } from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import { ContextualHelp } from '../components/ContextualHelp';
import { usePresentationMode } from '../context/PresentationModeContext';
import {
  Layers,
  Play,
  AlertCircle,
  CheckCircle2,
  ShieldAlert,
  DollarSign,
  Clock,
  Zap,
  Cpu,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';

interface Props {
  initialDeviceId?: string;
}

export const PageStorageDigitalTwin: React.FC<Props> = ({ initialDeviceId }) => {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>(initialDeviceId || 'vol-nvme-tier1-db');
  const [actionType, setActionType] = useState<string>('TIER_COLD_DATA');
  
  // Scenario Parameters
  const [dataVolumeGb, setDataVolumeGb] = useState<number>(1500);
  const [migrationRateMb, setMigrationRateMb] = useState<number>(150);
  const [addedCapacityGb, setAddedCapacityGb] = useState<number>(3000);
  const [relocatedIopsPct, setRelocatedIopsPct] = useState<number>(25);
  const [growthMultiplier, setGrowthMultiplier] = useState<number>(0.5);
  const [maintHours, setMaintHours] = useState<number>(4);
  const [maintOverheadPct, setMaintOverheadPct] = useState<number>(12);

  const [simulation, setSimulation] = useState<ScenarioSimulationResponse | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const { isGuided } = usePresentationMode();

  useEffect(() => {
    loadDevices();
  }, []);

  useEffect(() => {
    if (initialDeviceId && initialDeviceId !== selectedDeviceId) {
      setSelectedDeviceId(initialDeviceId);
    }
  }, [initialDeviceId]);

  useEffect(() => {
    if (selectedDeviceId) {
      loadDeviceTelemetry(selectedDeviceId);
      runSimulation();
    }
  }, [selectedDeviceId, actionType]);

  const loadDevices = async () => {
    try {
      const list = await api.getDevices();
      setDevices(list);
      if (initialDeviceId) {
        setSelectedDeviceId(initialDeviceId);
      } else if (list.length > 0) {
        setSelectedDeviceId(list[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadDeviceTelemetry = async (id: string) => {
    try {
      const tel = await api.getTelemetry(id, 'used_bytes', 168);
      setTelemetry(tel);
    } catch (e) {
      console.error(e);
    }
  };

  const runSimulation = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      let params: Record<string, any> = {};
      if (actionType === 'TIER_COLD_DATA') {
        params = { data_volume_gb: dataVolumeGb, migration_rate_mb_s: migrationRateMb };
      } else if (actionType === 'EXPAND_CAPACITY') {
        params = { added_capacity_gb: addedCapacityGb, provisioning_lead_hours: 1.5 };
      } else if (actionType === 'REBALANCE_WORKLOAD') {
        params = { relocated_iops_pct: relocatedIopsPct };
      } else if (actionType === 'CAPACITY_GROWTH_CHANGE') {
        params = { growth_multiplier: growthMultiplier };
      } else if (actionType === 'MAINTENANCE_PLANNING') {
        params = { maintenance_window_hours: maintHours, expected_io_overhead_pct: maintOverheadPct };
      }

      const res = await api.createScenario({
        device_id: selectedDeviceId,
        name: `Simulation: ${actionType} on ${selectedDeviceId}`,
        action_type: actionType,
        parameters: params,
      });
      setSimulation(res);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to execute digital twin simulation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header with Persistent Safe Warning */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[var(--accent)] text-white flex items-center justify-center shadow-xs">
              <Layers size={18} />
            </div>
            <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
              {isGuided ? 'Compare Possible Actions (Digital Twin Simulator)' : 'Storage Resilience Digital Twin Studio'}
            </h2>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
            {isGuided
              ? 'Test hypothetical storage remediations virtually. Simulations calculate outcomes without modifying real physical disks.'
              : 'Safe, sandboxed counterfactual intervention simulation. Tests hypothetical remediations against an immutable Hard Safety Envelope.'}
          </p>
        </div>

        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-[var(--status-success)]/10 border border-[var(--status-success)]/30 text-[var(--status-success)] text-xs font-mono">
          <ShieldCheck size={14} />
          <span>VIRTUAL SANDBOX: ZERO HARDWARE CHANGES</span>
        </div>
      </div>

      {/* Control Sandbox Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Configuration Panel */}
        <div className="titan-card rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)]">
            <h3 className="text-sm font-bold text-[var(--text-primary)]">
              {isGuided ? 'Choose Action to Simulate' : 'Intervention Parameters'}
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30 font-semibold">
              SANDBOX v1.0
            </span>
          </div>

          <div className="space-y-4 text-xs">
            {/* Target Pool */}
            <div>
              <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">
                Target Storage Pool:
              </label>
              <select
                value={selectedDeviceId}
                onChange={(e) => setSelectedDeviceId(e.target.value)}
                className="w-full bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-2 text-[var(--text-primary)] font-mono focus:outline-none cursor-pointer"
                aria-label="Target Storage Pool"
              >
                {devices.map((d) => (
                  <option key={d.id} value={d.id} className="bg-[var(--surface-primary)] text-[var(--text-primary)]">
                    {d.name} ({d.id})
                  </option>
                ))}
              </select>
            </div>

            {/* Action Type */}
            <div>
              <label className="block text-[var(--text-secondary)] mb-1.5 font-medium text-[11px] uppercase tracking-wider">
                Remediation Strategy:
              </label>
              <select
                value={actionType}
                onChange={(e) => setActionType(e.target.value)}
                className="w-full bg-[var(--surface-secondary)] border border-[var(--border-normal)] focus:border-[var(--accent-primary)] rounded-lg px-3 py-2 text-[var(--text-primary)] font-semibold focus:outline-none cursor-pointer"
                aria-label="Remediation Strategy"
              >
                <option value="TIER_COLD_DATA" className="bg-[var(--surface-primary)]">Data Tiering / Cold Archival</option>
                <option value="EXPAND_CAPACITY" className="bg-[var(--surface-primary)]">Capacity Expansion (+Provisioning)</option>
                <option value="REBALANCE_WORKLOAD" className="bg-[var(--surface-primary)]">Workload Distribution / Rebalance</option>
                <option value="CAPACITY_GROWTH_CHANGE" className="bg-[var(--surface-primary)]">Capacity Growth Rate Change</option>
                <option value="MAINTENANCE_PLANNING" className="bg-[var(--surface-primary)]">Maintenance Window Planning</option>
                <option value="RESCHEDULE_TASK" className="bg-[var(--surface-primary)]">Reschedule Background Scrub / Backup</option>
                <option value="DO_NOTHING" className="bg-[var(--surface-primary)]">Do Nothing (Baseline Trajectory)</option>
              </select>
            </div>

            {/* Dynamic Parameter Sliders */}
            {actionType === 'TIER_COLD_DATA' && (
              <div className="space-y-4 pt-3 border-t border-[var(--border-subtle)]">
                <div>
                  <div className="flex justify-between text-[var(--text-secondary)] mb-1.5 font-mono">
                    <span>Migrated Data Volume:</span>
                    <span className="text-[var(--accent-primary)] font-bold">{dataVolumeGb} GB</span>
                  </div>
                  <input
                    type="range"
                    min="200"
                    max="5000"
                    step="100"
                    value={dataVolumeGb}
                    onChange={(e) => setDataVolumeGb(Number(e.target.value))}
                    className="w-full accent-[var(--accent-primary)] cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-[var(--text-secondary)] mb-1.5 font-mono">
                    <span>Migration I/O Rate:</span>
                    <span className="text-[var(--accent-primary)] font-bold">{migrationRateMb} MB/s</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="500"
                    step="25"
                    value={migrationRateMb}
                    onChange={(e) => setMigrationRateMb(Number(e.target.value))}
                    className="w-full accent-[var(--accent-primary)] cursor-pointer"
                  />
                </div>
              </div>
            )}

            {actionType === 'EXPAND_CAPACITY' && (
              <div className="space-y-4 pt-3 border-t border-[var(--border-subtle)]">
                <div>
                  <div className="flex justify-between text-[var(--text-secondary)] mb-1.5 font-mono">
                    <span>Additional Block Storage:</span>
                    <span className="text-[var(--accent-primary)] font-bold">{addedCapacityGb} GB</span>
                  </div>
                  <input
                    type="range"
                    min="1000"
                    max="10000"
                    step="500"
                    value={addedCapacityGb}
                    onChange={(e) => setAddedCapacityGb(Number(e.target.value))}
                    className="w-full accent-[var(--accent-primary)] cursor-pointer"
                  />
                </div>
              </div>
            )}

            {actionType === 'REBALANCE_WORKLOAD' && (
              <div className="space-y-4 pt-3 border-t border-[var(--border-subtle)]">
                <div>
                  <div className="flex justify-between text-[var(--text-secondary)] mb-1.5 font-mono">
                    <span>Tenant Partition Relocated:</span>
                    <span className="text-[var(--accent-primary)] font-bold">{relocatedIopsPct}% IOPS</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="60"
                    step="5"
                    value={relocatedIopsPct}
                    onChange={(e) => setRelocatedIopsPct(Number(e.target.value))}
                    className="w-full accent-[var(--accent-primary)] cursor-pointer"
                  />
                </div>
              </div>
            )}

            {actionType === 'CAPACITY_GROWTH_CHANGE' && (
              <div className="space-y-4 pt-3 border-t border-[var(--border-subtle)]">
                <div>
                  <div className="flex justify-between text-[var(--text-secondary)] mb-1.5 font-mono">
                    <span>Growth Rate Multiplier:</span>
                    <span className="text-[var(--accent-primary)] font-bold">{growthMultiplier.toFixed(1)}x</span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="3.0"
                    step="0.1"
                    value={growthMultiplier}
                    onChange={(e) => setGrowthMultiplier(Number(e.target.value))}
                    className="w-full accent-[var(--accent-primary)] cursor-pointer"
                  />
                </div>
              </div>
            )}

            {actionType === 'MAINTENANCE_PLANNING' && (
              <div className="space-y-4 pt-3 border-t border-[var(--border-subtle)]">
                <div>
                  <div className="flex justify-between text-[var(--text-secondary)] mb-1.5 font-mono">
                    <span>Maintenance Window:</span>
                    <span className="text-[var(--accent-primary)] font-bold">{maintHours} hrs</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="24"
                    step="1"
                    value={maintHours}
                    onChange={(e) => setMaintHours(Number(e.target.value))}
                    className="w-full accent-[var(--accent-primary)] cursor-pointer"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[var(--text-secondary)] mb-1.5 font-mono">
                    <span>Expected I/O Overhead:</span>
                    <span className="text-[var(--accent-primary)] font-bold">{maintOverheadPct}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="50"
                    step="2"
                    value={maintOverheadPct}
                    onChange={(e) => setMaintOverheadPct(Number(e.target.value))}
                    className="w-full accent-[var(--accent-primary)] cursor-pointer"
                  />
                </div>
              </div>
            )}

            {errorMsg && (
              <div className="p-2.5 rounded-lg bg-[var(--status-critical)]/10 border border-[var(--status-critical)] text-xs text-[var(--status-critical)]">
                {errorMsg}
              </div>
            )}

            <button
              onClick={runSimulation}
              disabled={loading}
              className="w-full mt-4 py-2.5 px-4 rounded-xl btn-primary font-bold text-xs flex items-center justify-center gap-2"
            >
              <Play size={14} />
              {loading ? 'Simulating Digital Twin Physics...' : 'Run Simulation'}
            </button>

            {simulation && (
              <a
                href={`/api/v1/digital-twin/scenarios/${simulation.scenario_id}/export?format=csv`}
                className="block text-center mt-2 text-[11px] font-mono text-[var(--accent-primary)] underline"
              >
                Export Simulation Results (CSV)
              </a>
            )}
          </div>
        </div>

        {/* Right: Simulation Outcomes & Safety Envelope */}
        <div className="lg:col-span-2 space-y-4">
          {simulation && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="titan-card rounded-xl p-3.5 text-xs">
                <div className="text-[var(--text-secondary)] flex items-center gap-1.5 font-medium">
                  <Clock size={13} className="text-[var(--accent-primary)]" /> Estimated Duration
                </div>
                <div className="text-base font-bold font-mono text-[var(--text-primary)] mt-1.5">
                  {simulation.duration_minutes > 60
                    ? `${(simulation.duration_minutes / 60).toFixed(1)} hrs`
                    : `${simulation.duration_minutes.toFixed(0)} min`}
                </div>
              </div>

              <div className="titan-card rounded-xl p-3.5 text-xs">
                <div className="text-[var(--text-secondary)] flex items-center gap-1.5 font-medium">
                  <DollarSign size={13} className="text-[var(--status-success)]" /> Estimated Cost
                </div>
                <div className="text-base font-bold font-mono text-[var(--status-success)] mt-1.5">
                  ${simulation.estimated_cost_usd.toFixed(2)}
                </div>
              </div>

              <div className="titan-card rounded-xl p-3.5 text-xs">
                <div className="text-[var(--text-secondary)] flex items-center gap-1.5 font-medium">
                  <Zap size={13} className="text-[var(--status-warning)]" /> Contention Penalty
                </div>
                <div className="text-base font-bold font-mono text-[var(--status-warning)] mt-1.5">
                  {simulation.overhead_io_penalty_pct > 0 ? `+${simulation.overhead_io_penalty_pct}%` : `${simulation.overhead_io_penalty_pct}%`}
                </div>
              </div>

              <div className="titan-card rounded-xl p-3.5 text-xs">
                <div className="text-[var(--text-secondary)] flex items-center gap-1.5 font-medium">
                  <ShieldAlert size={13} className="text-[var(--text-muted)]" /> Safety Envelope
                </div>
                <div className="mt-1.5">
                  {simulation.safety_envelope_passed ? (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-[var(--status-success)]/15 text-[var(--status-success)] border border-[var(--status-success)]/40 shadow-sm">
                      PASSED (SAFE)
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-[var(--status-critical)]/15 text-[var(--status-critical)] border border-[var(--status-critical)]/40 shadow-sm">
                      SAFETY VIOLATED
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Hard Safety Envelope Violations Alert */}
          {simulation && !simulation.safety_envelope_passed && (
            <div className="bg-[var(--status-critical)]/10 border border-[var(--status-critical)]/30 rounded-lg p-4 text-xs text-[var(--status-critical)] space-y-1.5">
              <div className="font-bold flex items-center gap-2">
                <ShieldAlert size={16} /> Hard Safety Constraint Violated:
              </div>
              <ul className="list-disc pl-5 space-y-1 font-mono text-[11px]">
                {simulation.violation_reasons.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Side-by-Side Trajectory Chart */}
          {simulation && telemetry && (
            <ScientificForecastChart
              title={`Simulation Outcome: Baseline vs Remediated (${actionType})`}
              historicalTimestamps={telemetry.timestamps}
              historicalValues={telemetry.values}
              forecastTimestamps={simulation.timeline_timestamps}
              q50={simulation.baseline_q50}
              counterfactualQ50={simulation.counterfactual_q50}
              hardConstraint={simulation.hard_limit}
              units="Bytes"
              isBytes={true}
            />
          )}

          {/* Documented Assumptions & Limitations */}
          {simulation && (
            <div className="titan-card rounded-lg p-4 text-xs">
              <h4 className="font-semibold text-[var(--text-primary)] mb-2 flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-[var(--accent-primary)]" /> Simulation Physics & Stated Assumptions:
              </h4>
              <ul className="list-disc pl-5 space-y-1 text-[var(--text-secondary)] font-mono text-[11px]">
                {simulation.assumptions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
