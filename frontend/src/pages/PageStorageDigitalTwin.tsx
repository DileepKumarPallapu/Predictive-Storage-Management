import React, { useState, useEffect } from 'react';
import { api, DeviceSummary, ScenarioSimulationResponse, TelemetryResponse } from '../api/client';
import { ScientificForecastChart } from '../components/ScientificForecastChart';
import { Layers, Play, AlertCircle, CheckCircle2, ShieldAlert, DollarSign, Clock, Zap } from 'lucide-react';

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

  const [simulation, setSimulation] = useState<ScenarioSimulationResponse | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    loadDevices();
  }, []);

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
      {/* Page Header with Persistent Warning */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
            <Layers className="text-obsidian-cyan" size={22} />
            Storage Resilience Digital Twin Studio
          </h2>
          <p className="text-xs text-obsidian-muted mt-1">
            Safe, sandboxed counterfactual intervention simulation. Tests hypothetical remediations against an immutable Hard Safety Envelope.
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-obsidian-amber/10 border border-obsidian-amber/30 text-obsidian-amber text-xs font-mono">
          <AlertCircle size={14} />
          <span>SIMULATION SANDBOX: NO PHYSICAL MUTATION</span>
        </div>
      </div>

      {/* Control Sandbox Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Configuration Panel */}
        <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5 space-y-4">
          <h3 className="text-sm font-bold text-obsidian-text flex items-center justify-between">
            <span>Intervention Parameters</span>
            <span className="text-[10px] font-mono text-obsidian-cyan">SANDBOX v1.0</span>
          </h3>

          <div className="space-y-3 text-xs">
            {/* Target Pool */}
            <div>
              <label className="block text-obsidian-muted mb-1 font-medium">Target Storage Pool:</label>
              <select
                value={selectedDeviceId}
                onChange={(e) => setSelectedDeviceId(e.target.value)}
                className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-obsidian-text font-mono focus:border-obsidian-cyan"
              >
                {devices.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.id})
                  </option>
                ))}
              </select>
            </div>

            {/* Action Type */}
            <div>
              <label className="block text-obsidian-muted mb-1 font-medium">Simulated Intervention Strategy:</label>
              <select
                value={actionType}
                onChange={(e) => setActionType(e.target.value)}
                className="w-full bg-obsidian-secondary border border-obsidian-border rounded px-3 py-1.5 text-obsidian-text font-semibold focus:border-obsidian-cyan cursor-pointer"
              >
                <option value="TIER_COLD_DATA">Move Inactive Cold Data to Tier 2/Archive</option>
                <option value="EXPAND_CAPACITY">Online Capacity Provisioning (+LUN Growth)</option>
                <option value="RESCHEDULE_TASK">Reschedule Background RAID Scrub / Backup</option>
                <option value="REBALANCE_WORKLOAD">Rebalance Noisy Workloads to Adjacent Pool</option>
                <option value="DO_NOTHING">Do Nothing (Observe Baseline Risk Trajectory)</option>
              </select>
            </div>

            {/* Dynamic Parameter Sliders */}
            {actionType === 'TIER_COLD_DATA' && (
              <div className="space-y-3 pt-2 border-t border-obsidian-border">
                <div>
                  <div className="flex justify-between text-obsidian-muted mb-1 font-mono">
                    <span>Migrated Data Volume:</span>
                    <span className="text-obsidian-cyan font-bold">{dataVolumeGb} GB</span>
                  </div>
                  <input
                    type="range"
                    min="200"
                    max="5000"
                    step="100"
                    value={dataVolumeGb}
                    onChange={(e) => setDataVolumeGb(Number(e.target.value))}
                    className="w-full accent-obsidian-cyan cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-obsidian-muted mb-1 font-mono">
                    <span>Migration I/O Throttling Rate:</span>
                    <span className="text-obsidian-cyan font-bold">{migrationRateMb} MB/s</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="500"
                    step="25"
                    value={migrationRateMb}
                    onChange={(e) => setMigrationRateMb(Number(e.target.value))}
                    className="w-full accent-obsidian-cyan cursor-pointer"
                  />
                </div>
              </div>
            )}

            {actionType === 'EXPAND_CAPACITY' && (
              <div className="space-y-3 pt-2 border-t border-obsidian-border">
                <div>
                  <div className="flex justify-between text-obsidian-muted mb-1 font-mono">
                    <span>Additional Block Storage:</span>
                    <span className="text-obsidian-cyan font-bold">{addedCapacityGb} GB</span>
                  </div>
                  <input
                    type="range"
                    min="1000"
                    max="10000"
                    step="500"
                    value={addedCapacityGb}
                    onChange={(e) => setAddedCapacityGb(Number(e.target.value))}
                    className="w-full accent-obsidian-cyan cursor-pointer"
                  />
                </div>
              </div>
            )}

            {actionType === 'REBALANCE_WORKLOAD' && (
              <div className="space-y-3 pt-2 border-t border-obsidian-border">
                <div>
                  <div className="flex justify-between text-obsidian-muted mb-1 font-mono">
                    <span>Tenant Partition Relocated:</span>
                    <span className="text-obsidian-cyan font-bold">{relocatedIopsPct}% IOPS</span>
                  </div>
                  <input
                    type="range"
                    min="10"
                    max="60"
                    step="5"
                    value={relocatedIopsPct}
                    onChange={(e) => setRelocatedIopsPct(Number(e.target.value))}
                    className="w-full accent-obsidian-cyan cursor-pointer"
                  />
                </div>
              </div>
            )}

            <button
              onClick={runSimulation}
              disabled={loading}
              className="w-full mt-4 py-2 px-4 rounded bg-obsidian-cyan hover:opacity-90 text-obsidian-bg font-bold text-xs flex items-center justify-center gap-2 transition-opacity"
            >
              <Play size={14} />
              {loading ? 'Simulating Digital Twin Physics...' : 'Run Counterfactual Simulation'}
            </button>
          </div>
        </div>

        {/* Right: Simulation Outcomes & Safety Envelope */}
        <div className="lg:col-span-2 space-y-4">
          {simulation && (
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div className="bg-obsidian-panel border border-obsidian-border rounded p-3 text-xs">
                <div className="text-obsidian-muted flex items-center gap-1.5 font-medium">
                  <Clock size={13} className="text-obsidian-cyan" /> Action Duration
                </div>
                <div className="text-base font-bold font-mono text-obsidian-text mt-1">
                  {simulation.duration_minutes > 60
                    ? `${(simulation.duration_minutes / 60).toFixed(1)} hrs`
                    : `${simulation.duration_minutes.toFixed(0)} min`}
                </div>
              </div>

              <div className="bg-obsidian-panel border border-obsidian-border rounded p-3 text-xs">
                <div className="text-obsidian-muted flex items-center gap-1.5 font-medium">
                  <DollarSign size={13} className="text-obsidian-teal" /> Estimated Cost
                </div>
                <div className="text-base font-bold font-mono text-obsidian-teal mt-1">
                  ${simulation.estimated_cost_usd.toFixed(2)}
                </div>
              </div>

              <div className="bg-obsidian-panel border border-obsidian-border rounded p-3 text-xs">
                <div className="text-obsidian-muted flex items-center gap-1.5 font-medium">
                  <Zap size={13} className="text-obsidian-amber" /> Latency Overhead
                </div>
                <div className="text-base font-bold font-mono text-obsidian-amber mt-1">
                  {simulation.overhead_io_penalty_pct > 0 ? `+${simulation.overhead_io_penalty_pct}%` : `${simulation.overhead_io_penalty_pct}%`}
                </div>
              </div>

              <div className="bg-obsidian-panel border border-obsidian-border rounded p-3 text-xs">
                <div className="text-obsidian-muted flex items-center gap-1.5 font-medium">
                  <ShieldAlert size={13} /> Safety Envelope
                </div>
                <div className="mt-1">
                  {simulation.safety_envelope_passed ? (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-obsidian-teal/20 text-obsidian-teal border border-obsidian-teal/40">
                      PASSED (SAFE)
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-obsidian-coral/20 text-obsidian-coral border border-obsidian-coral/40">
                      SAFETY VIOLATED
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Hard Safety Envelope Violations Alert */}
          {simulation && !simulation.safety_envelope_passed && (
            <div className="bg-obsidian-coral/10 border border-obsidian-coral/30 rounded-lg p-4 text-xs text-obsidian-coral space-y-1">
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
              title={`Digital Twin: Baseline vs Counterfactual (${actionType})`}
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
            <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4 text-xs">
              <h4 className="font-semibold text-obsidian-text mb-2">Simulation Physics & Stated Assumptions:</h4>
              <ul className="list-disc pl-5 space-y-1 text-obsidian-muted font-mono text-[11px]">
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
