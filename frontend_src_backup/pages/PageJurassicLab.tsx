import React, { useState, useEffect } from 'react';
import {
  Flame,
  Shield,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  Zap,
  Sliders,
  FileText,
  Download,
  RefreshCw,
  Search,
  Server,
  Lock,
  GitPullRequest,
  BarChart2,
  TrendingUp,
  Cpu,
  Info,
  ChevronRight,
  Database,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';

export const PageJurassicLab: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'cmd_center' | 'designer' | 'adversarial' | 'robustness' | 'timeline' | 'forensics' | 'reports'>('cmd_center');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Data states
  const [commandCenterData, setCommandCenterData] = useState<any>(null);
  const [scenariosList, setScenariosList] = useState<any[]>([]);
  const [experimentsList, setExperimentsList] = useState<any[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<any>(null);
  const [fallbackStates, setFallbackStates] = useState<any>(null);

  // Scenario Designer State
  const [selectedPresetId, setSelectedPresetId] = useState<string>('scenario-jurassic-cap-burst-01');
  const [customName, setCustomName] = useState<string>('Adversarial Burst Shock Lab');
  const [customFamily, setCustomFamily] = useState<string>('COMPOUND_DISTURBANCE');
  const [customDevice, setCustomDevice] = useState<string>('vol-nvme-tier1-db');
  const [customSeed, setCustomSeed] = useState<number>(42);
  const [customDuration, setCustomDuration] = useState<number>(168);
  const [customCapacityPct, setCustomCapacityPct] = useState<number>(75.0);
  const [customGrowthGb, setCustomGrowthGb] = useState<number>(140.0);
  const [customDropRate, setCustomDropRate] = useState<number>(0.15);
  const [customNoise, setCustomNoise] = useState<number>(1.2);

  // Execution state
  const [isRunningExperiment, setIsRunningExperiment] = useState<boolean>(false);
  const [executionMessage, setExecutionMessage] = useState<string | null>(null);

  useEffect(() => {
    loadJurassicData();
  }, []);

  const loadJurassicData = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [cmd, scs, exps, fbs] = await Promise.all([
        api.getJurassicCommandCenter(),
        api.getJurassicScenarios(),
        api.getJurassicExperiments(20),
        api.getJurassicFallbackStates(),
      ]);
      setCommandCenterData(cmd);
      setScenariosList(scs);
      setExperimentsList(exps);
      setFallbackStates(fbs);

      if (exps.length > 0) {
        // Load details of the latest experiment
        const latestDetails = await api.getJurassicExperimentDetails(exps[0].id);
        setSelectedExperiment(latestDetails);
      }
    } catch (err: any) {
      console.error("Failed to load Jurassic Lab data:", err);
      setErrorMessage(err.message || "Failed to connect to Jurassic Lab endpoints");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectExperiment = async (expId: string) => {
    try {
      const details = await api.getJurassicExperimentDetails(expId);
      setSelectedExperiment(details);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRunExperiment = async (scenarioIdToRun?: string) => {
    const scId = scenarioIdToRun || selectedPresetId;
    setIsRunningExperiment(true);
    setExecutionMessage(null);
    try {
      const res = await api.runJurassicExperiment(scId);
      setExecutionMessage(`Experiment ${res.experiment_id} completed successfully (Score: ${res.resilience_score}/100)`);
      // Reload experiments and command center
      const [cmd, exps] = await Promise.all([
        api.getJurassicCommandCenter(),
        api.getJurassicExperiments(20),
      ]);
      setCommandCenterData(cmd);
      setExperimentsList(exps);
      const details = await api.getJurassicExperimentDetails(res.experiment_id);
      setSelectedExperiment(details);
      setActiveTab('cmd_center');
    } catch (err: any) {
      alert("Experiment failed: " + err.message);
    } finally {
      setIsRunningExperiment(false);
    }
  };

  const handleSaveAndRunCustomScenario = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsRunningExperiment(true);
    try {
      const created = await api.createJurassicScenario({
        name: customName,
        scenario_family: customFamily,
        target_device_id: customDevice,
        seed: Number(customSeed),
        simulation_duration_hours: Number(customDuration),
        initial_capacity_pct: Number(customCapacityPct),
        capacity_growth_gb_day: Number(customGrowthGb),
        telemetry_drop_rate: Number(customDropRate),
        latency_noise_ms: Number(customNoise),
        burst_events: [{"hour": 24, "size_gb": 300.0, "reason": "Designer write burst"}],
        chaos_faults: customDropRate > 0.1 ? [{"hour": 36, "duration_hours": 12, "fault_type": "TELEMETRY_PAUSE"}] : []
      });
      // Run it
      await handleRunExperiment(created.id);
      const scs = await api.getJurassicScenarios();
      setScenariosList(scs);
    } catch (err: any) {
      alert("Failed to create and run custom scenario: " + err.message);
      setIsRunningExperiment(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <RefreshCw size={36} className="text-[var(--status-warning)] animate-spin" />
        <p className="text-sm font-mono text-[var(--text-secondary)]">
          Initializing AEGISSTOR Jurassic Failure Discovery Lab & Fault Engine...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[var(--status-warning)]/10 border border-[var(--status-warning)]/30 text-[var(--status-warning)]">
              <Flame size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
                  AEGISSTOR JURASSIC — Resilience & Failure Discovery Lab
                </h1>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[var(--status-warning)]/20 text-[var(--status-warning)] border border-[var(--status-warning)]/40">
                  JURASSIC 7.0
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] border border-[var(--accent-primary)]/40">
                  SHADOW SIMULATOR (ZERO HOST MUTATION)
                </span>
              </div>
              <p className="text-xs text-[var(--text-secondary)] font-mono mt-0.5">
                Official Project: Predictive Storage Capacity and Performance Management Using Machine Learning
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadJurassicData}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-xs font-mono text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent-primary)] transition-colors"
          >
            <RefreshCw size={14} />
            Sync Records
          </button>
        </div>
      </div>

      {/* Global Resilience Metrics Summary */}
      {commandCenterData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)]">
          <div className="space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
              <Server size={14} className="text-[var(--accent-primary)]" /> Scenarios Tested
            </span>
            <div className="text-xl font-bold text-[var(--text-primary)]">
              {commandCenterData.summary.scenarios_tested} / {commandCenterData.summary.scenarios_available} Catalogued
            </div>
            <p className="text-xs text-[var(--text-secondary)] font-mono">
              Total Runs: <span className="text-[var(--text-primary)] font-bold">{commandCenterData.summary.total_experiments_run}</span>
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
              <Shield size={14} className="text-[var(--status-success)]" /> Unsafe Actions Blocked
            </span>
            <div className="text-xl font-bold text-[var(--status-success)]">
              {commandCenterData.summary.unsafe_recommendations_blocked} Interventions
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              Hard Safety Envelope Enforced
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
              <AlertTriangle size={14} className="text-[var(--status-warning)]" /> Drift Events Caught
            </span>
            <div className="text-xl font-bold text-[var(--status-warning)]">
              {commandCenterData.summary.model_degradation_events_detected} Detected
            </div>
            <p className="text-xs text-[var(--text-secondary)] font-mono">
              Mean Recovery: {commandCenterData.summary.mean_recovery_time_hours}h
            </p>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-secondary)] flex items-center gap-1.5">
              <Activity size={14} className="text-[var(--accent-tertiary)]" /> Mean Resilience Score
            </span>
            <div className="text-xl font-bold text-[var(--accent-tertiary)]">
              {commandCenterData.summary.mean_resilience_index} / 100.0
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              10-Dimension Composite Index
            </p>
          </div>
        </div>
      )}

      {/* Execution Feedback Banner if any */}
      {executionMessage && (
        <div className="p-3 rounded-lg bg-[var(--status-success)]/10 border border-[var(--status-success)]/40 text-[var(--status-success)] text-xs font-mono flex items-center gap-2">
          <CheckCircle2 size={16} />
          {executionMessage}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-[var(--border-subtle)] gap-2 overflow-x-auto pb-1">
        {[
          { id: 'cmd_center', label: 'Command Center', icon: Activity },
          { id: 'designer', label: 'Scenario Designer', icon: Sliders },
          { id: 'adversarial', label: 'Adversarial Telemetry', icon: Layers },
          { id: 'robustness', label: 'Model Robustness', icon: BarChart2 },
          { id: 'timeline', label: 'Failure Timeline', icon: Clock },
          { id: 'forensics', label: 'Failure Forensics', icon: Search },
          { id: 'reports', label: 'Resilience Reports', icon: FileText },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg font-medium text-xs transition-colors whitespace-nowrap ${
                isActive
                  ? 'bg-[var(--surface-primary)] border-t border-x border-[var(--border-subtle)] text-[var(--status-warning)] border-b-2 border-b-[var(--status-warning)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)]/50'
              }`}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* PAGE A: RESILIENCE COMMAND CENTER */}
      {/* ========================================================================= */}
      {activeTab === 'cmd_center' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Quick Launch Panel */}
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-4">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Zap size={16} className="text-[var(--status-warning)]" /> Launch Stress Experiment Preset
              </h3>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                Execute a deterministic chaos stress test against the Resilience Digital Twin to evaluate model degradation,
                prediction interval collapse, and fallback state transitions.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="text-[var(--text-secondary)] block text-xs mb-1 font-mono">Select Preset Scenario:</label>
                  <select
                    value={selectedPresetId}
                    onChange={(e) => setSelectedPresetId(e.target.value)}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-xs font-mono text-[var(--text-primary)] focus:outline-none focus:border-[var(--status-warning)]"
                  >
                    {scenariosList.map((sc) => (
                      <option key={sc.id} value={sc.id}>
                        {sc.name} ({sc.scenario_family})
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={() => handleRunExperiment()}
                  disabled={isRunningExperiment}
                  className="w-full py-2.5 rounded-lg bg-[var(--status-warning)] text-[var(--bg-primary)] font-bold text-xs hover:bg-[var(--status-warning)]/90 transition-colors flex items-center justify-center gap-2 shadow-[0_0_12px_rgba(255,198,109,0.2)]"
                >
                  {isRunningExperiment ? <RefreshCw size={14} className="animate-spin" /> : <Flame size={14} />}
                  Execute Resilience Test Run
                </button>
              </div>
            </div>

            {/* Fallback States Summary */}
            <div className="lg:col-span-2 p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Lock size={16} className="text-[var(--accent-primary)]" /> Formal Safe Fallback States Architecture
              </h3>
              <p className="text-xs text-[var(--text-secondary)]">
                AEGISSTOR enforces deterministic safe states when evidence or models degrade:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                {fallbackStates && Object.entries(fallbackStates).map(([key, val]: any) => (
                  <div key={key} className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)]/70 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[var(--text-primary)]">{val.user_visible_status}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--surface-primary)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
                        {key.slice(0, 7)}
                      </span>
                    </div>
                    <p className="text-[11px] text-[var(--text-secondary)] leading-tight">
                      {val.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Stored Experiments Table */}
          <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
              <Database size={16} className="text-[var(--accent-primary)]" /> Historical Resilience Experiment Runs (Audit Trail)
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)] text-[11px]">
                    <th className="py-2.5 px-3">Experiment ID</th>
                    <th className="py-2.5 px-3">Scenario Name</th>
                    <th className="py-2.5 px-3">Target Volume</th>
                    <th className="py-2.5 px-3">Final Safe State</th>
                    <th className="py-2.5 px-3">Shift Detected</th>
                    <th className="py-2.5 px-3">Resilience Score</th>
                    <th className="py-2.5 px-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]/50 text-[11px]">
                  {experimentsList.map((exp) => {
                    const isSelected = selectedExperiment?.id === exp.id;
                    return (
                      <tr key={exp.id} className={isSelected ? 'bg-[var(--status-warning)]/10' : 'hover:bg-[var(--bg-primary)]/50'}>
                        <td className="py-2.5 px-3 font-semibold text-[var(--text-primary)]">{exp.id}</td>
                        <td className="py-2.5 px-3 text-[var(--text-secondary)] truncate max-w-xs">{exp.scenario_name}</td>
                        <td className="py-2.5 px-3 text-[var(--accent-primary)]">{exp.target_device_id}</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] border ${
                            exp.final_fallback_state === 'STATE_1_HEALTHY_EVIDENCE'
                              ? 'bg-[var(--status-success)]/10 text-[var(--status-success)] border-[var(--status-success)]/30'
                              : exp.final_fallback_state === 'STATE_4_PLANNING_UNSAFE'
                              ? 'bg-[var(--status-critical)]/10 text-[var(--status-critical)] border-[var(--status-critical)]/30'
                              : 'bg-[var(--status-warning)]/10 text-[var(--status-warning)] border-[var(--status-warning)]/30'
                          }`}>
                            {exp.final_fallback_state}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          {exp.drift_detected ? (
                            <span className="text-[var(--status-warning)] font-bold">YES</span>
                          ) : (
                            <span className="text-[var(--status-success)]">NO</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-[var(--text-primary)] font-bold">
                          {exp.resilience_score} / 100
                        </td>
                        <td className="py-2.5 px-3">
                          <button
                            onClick={() => handleSelectExperiment(exp.id)}
                            className="px-2 py-1 rounded bg-[var(--bg-primary)] border border-[var(--border-subtle)] text-[10px] text-[var(--accent-primary)] hover:border-[var(--accent-primary)]"
                          >
                            Inspect Forensics &rarr;
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PAGE B: SCENARIO DESIGNER */}
      {/* ========================================================================= */}
      {activeTab === 'designer' && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-[var(--status-warning)]/5 border border-[var(--status-warning)]/20 space-y-2">
            <div className="flex items-center gap-2 text-[var(--status-warning)] font-semibold text-sm">
              <Info size={16} /> Adversarial Scenario Designer & Parameter Generator
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              Design synthetic stress-test scenarios with reproducible random seeds. Scenarios can simulate multi-burst write spikes,
              rapid organic growth acceleration, flash controller GC saturation, telemetry agent partitions, and destination saturation.
            </p>
          </div>

          <form onSubmit={handleSaveAndRunCustomScenario} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-4">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Sliders size={16} className="text-[var(--status-warning)]" /> Disturbance Characteristics & Storage Parameters
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Scenario Name:</label>
                  <input
                    type="text"
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                    required
                  />
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Disturbance Family:</label>
                  <select
                    value={customFamily}
                    onChange={(e) => setCustomFamily(e.target.value)}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                  >
                    <option value="CAPACITY_DISTURBANCE">Capacity Disturbance (Bursts & Growth)</option>
                    <option value="PERFORMANCE_DISTURBANCE">Performance Disturbance (GC Storm / Latency)</option>
                    <option value="TEMPORAL_DISTURBANCE">Temporal Disturbance (Diurnal Inversion)</option>
                    <option value="TELEMETRY_DISTURBANCE">Telemetry Disturbance (Blackout / Dropouts)</option>
                    <option value="COMPOUND_DISTURBANCE">Compound Disturbance (Multi-Failure Shock)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Target Storage Volume:</label>
                  <select
                    value={customDevice}
                    onChange={(e) => setCustomDevice(e.target.value)}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                  >
                    <option value="vol-nvme-tier1-db">Production E-Commerce OLTP NVMe</option>
                    <option value="vol-sas-tier2-analytics">Corporate Analytics SAS</option>
                    <option value="vol-hdd-archive">High-Density Cold Archive</option>
                    <option value="vol-backup-target">Veeam Backup Target</option>
                  </select>
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Deterministic Random Seed:</label>
                  <input
                    type="number"
                    value={customSeed}
                    onChange={(e) => setCustomSeed(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                    required
                  />
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Initial Capacity Utilization (%):</label>
                  <input
                    type="number"
                    value={customCapacityPct}
                    onChange={(e) => setCustomCapacityPct(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                    min="10"
                    max="95"
                  />
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Daily Growth Rate (GB/day):</label>
                  <input
                    type="number"
                    value={customGrowthGb}
                    onChange={(e) => setCustomGrowthGb(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                  />
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Telemetry Dropout Rate (0.0 to 1.0):</label>
                  <input
                    type="number"
                    step="0.05"
                    value={customDropRate}
                    onChange={(e) => setCustomDropRate(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                    min="0"
                    max="1"
                  />
                </div>

                <div>
                  <label className="text-[var(--text-secondary)] block mb-1">Simulation Duration (hours):</label>
                  <input
                    type="number"
                    value={customDuration}
                    onChange={(e) => setCustomDuration(Number(e.target.value))}
                    className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
                    min="24"
                    max="720"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isRunningExperiment}
                className="w-full py-2.5 rounded-lg bg-[var(--status-warning)] text-[var(--bg-primary)] font-bold text-xs hover:bg-[var(--status-warning)]/90 transition-colors flex items-center justify-center gap-2"
              >
                {isRunningExperiment ? <RefreshCw size={14} className="animate-spin" /> : <Flame size={14} />}
                Save Custom Scenario & Execute Resilience Run
              </button>
            </div>

            {/* Presets Quick Selector */}
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Database size={16} className="text-[var(--accent-primary)]" /> Preconfigured Catalog Presets
              </h3>
              <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                {scenariosList.map((sc) => (
                  <div
                    key={sc.id}
                    onClick={() => {
                      setSelectedPresetId(sc.id);
                      setCustomName(sc.name);
                      setCustomFamily(sc.scenario_family);
                      setCustomDevice(sc.target_device_id);
                      setCustomSeed(sc.seed);
                      setCustomCapacityPct(sc.initial_capacity_pct);
                      setCustomGrowthGb(sc.capacity_growth_gb_day);
                      setCustomDropRate(sc.telemetry_drop_rate);
                    }}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedPresetId === sc.id
                        ? 'bg-[var(--status-warning)]/10 border-[var(--status-warning)]'
                        : 'bg-[var(--bg-primary)]/70 border-[var(--border-subtle)] hover:border-[var(--text-muted)]'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs font-bold text-[var(--text-primary)]">
                      <span>{sc.name}</span>
                    </div>
                    <p className="text-[10px] text-[var(--text-secondary)] mt-1 leading-tight font-mono">
                      Family: {sc.scenario_family} | Seed: {sc.seed}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </form>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PAGE C: ADVERSARIAL WORKLOAD STUDIO */}
      {/* ========================================================================= */}
      {activeTab === 'adversarial' && selectedExperiment && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                  <Layers size={16} className="text-[var(--status-warning)]" /> Adversarial Synthetic Telemetry Timeline — {selectedExperiment.scenario_name}
                </h3>
                <span className="text-[10px] font-mono text-[var(--status-warning)] font-bold">
                  SYNTHETIC EXPERIMENTAL TELEMETRY — VALIDATED AGAINST FLASH CONTROLLER GC DYNAMICS
                </span>
              </div>
              <span className="text-xs font-mono text-[var(--text-secondary)]">
                Displaying first {selectedExperiment.telemetry_samples?.length || 0} hours
              </span>
            </div>

            {/* Telemetry Visual Table */}
            <div className="overflow-x-auto max-h-[480px]">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead className="sticky top-0 bg-[var(--surface-primary)] border-b border-[var(--border-subtle)] text-[var(--text-secondary)] text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">Hour</th>
                    <th className="py-2.5 px-3">Timestamp</th>
                    <th className="py-2.5 px-3">Utilization (%)</th>
                    <th className="py-2.5 px-3">Read IOPS</th>
                    <th className="py-2.5 px-3">Write IOPS</th>
                    <th className="py-2.5 px-3">Throughput (MB/s)</th>
                    <th className="py-2.5 px-3">P95 Latency</th>
                    <th className="py-2.5 px-3">Active Fault / Anomaly</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-subtle)]/50 text-[11px]">
                  {selectedExperiment.telemetry_samples?.map((s: any) => (
                    <tr key={s.step_hour} className={s.is_telemetry_dropped ? 'bg-[var(--status-critical)]/10' : 'hover:bg-[var(--bg-primary)]/50'}>
                      <td className="py-2 px-3 font-semibold text-[var(--text-primary)]">h+{s.step_hour}</td>
                      <td className="py-2 px-3 text-[var(--text-secondary)] text-[10px]">{s.timestamp?.slice(0, 16).replace('T', ' ')}</td>
                      <td className="py-2 px-3">
                        <span className={s.utilization_pct >= 90 ? 'text-[var(--status-critical)] font-bold' : (s.utilization_pct >= 80 ? 'text-[var(--status-warning)] font-bold' : 'text-[var(--text-primary)]')}>
                          {s.utilization_pct}%
                        </span>
                      </td>
                      <td className="py-2 px-3">{s.read_iops}</td>
                      <td className="py-2 px-3">{s.write_iops}</td>
                      <td className="py-2 px-3 text-[var(--accent-primary)]">{s.throughput_mb_s}</td>
                      <td className="py-2 px-3">
                        <span className={s.latency_p95_ms > 20 ? 'text-[var(--status-critical)] font-bold' : 'text-[var(--text-primary)]'}>
                          {s.latency_p95_ms} ms
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        {s.is_telemetry_dropped ? (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--status-critical)]/20 text-[var(--status-critical)] border border-[var(--status-critical)]/40">
                            TELEMETRY DROPPED
                          </span>
                        ) : s.active_fault ? (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--status-warning)]/20 text-[var(--status-warning)] border border-[var(--status-warning)]/40">
                            {s.active_fault}
                          </span>
                        ) : (
                          <span className="text-[var(--text-secondary)] text-[10px]">Nominal</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PAGE D: MODEL ROBUSTNESS LAB */}
      {/* ========================================================================= */}
      {activeTab === 'robustness' && selectedExperiment && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Distribution Shift Detection Card */}
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <BarChart2 size={16} className="text-[var(--status-warning)]" /> Workload Distribution Shift Assessment (Page-Hinkley)
              </h3>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1.5">
                  <span className="text-[var(--text-secondary)]">Drift Status:</span>
                  <span className={`font-bold px-2 py-0.5 rounded ${
                    selectedExperiment.drift_detected
                      ? 'bg-[var(--status-critical)]/10 text-[var(--status-critical)] border border-[var(--status-critical)]/30'
                      : 'bg-[var(--status-success)]/10 text-[var(--status-success)] border border-[var(--status-success)]/30'
                  }`}>
                    {selectedExperiment.drift_details?.drift_status || "NO_DETECTED_SHIFT"}
                  </span>
                </div>
                <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1.5">
                  <span className="text-[var(--text-secondary)]">Page-Hinkley Statistic:</span>
                  <span className="text-[var(--text-primary)] font-bold">{selectedExperiment.drift_details?.drift_statistic ?? 0.0}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1.5">
                  <span className="text-[var(--text-secondary)]">Standardized Z-Score:</span>
                  <span className="text-[var(--text-primary)]">{selectedExperiment.drift_details?.mean_shift_z_score ?? 0.0}</span>
                </div>
                <p className="text-[11px] text-[var(--text-secondary)] pt-2 font-sans leading-relaxed">
                  {selectedExperiment.drift_details?.explanation || "Workload remains within training bounds."}
                </p>
              </div>
            </div>

            {/* Prediction Interval Stress Testing Card */}
            <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                <Shield size={16} className="text-[var(--accent-primary)]" /> Prediction Interval Stress Testing (q10 - q90)
              </h3>
              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1.5">
                  <span className="text-[var(--text-secondary)]">Target Nominal Coverage:</span>
                  <span className="text-[var(--text-primary)]">80.0%</span>
                </div>
                <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1.5">
                  <span className="text-[var(--text-secondary)]">Observed Empirical Coverage:</span>
                  <span className={`font-bold ${
                    selectedExperiment.forecast_evaluations?.calibration_passed
                      ? 'text-[var(--status-success)]'
                      : 'text-[var(--status-critical)] font-extrabold'
                  }`}>
                    {((selectedExperiment.forecast_evaluations?.empirical_coverage ?? 0.8) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between border-b border-[var(--border-subtle)]/50 pb-1.5">
                  <span className="text-[var(--text-secondary)]">Error Source Attribution:</span>
                  <span className="text-[var(--status-warning)] font-bold">{selectedExperiment.forecast_evaluations?.error_attribution || "NOMINAL"}</span>
                </div>
                <p className="text-[11px] text-[var(--text-secondary)] pt-2 font-sans leading-relaxed">
                  {selectedExperiment.forecast_evaluations?.breakdown_reason || "Conformal calibration maintained."}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PAGE E: FAILURE AND RECOVERY TIMELINE */}
      {/* ========================================================================= */}
      {activeTab === 'timeline' && selectedExperiment && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-3">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
              <Clock size={16} className="text-[var(--status-warning)]" /> Chronological Experiment & Fallback Transition Timeline
            </h3>

            <div className="space-y-3 pl-4 border-l-2 border-[var(--border-subtle)]/80 my-4">
              {selectedExperiment.fallback_transitions?.map((trans: any, idx: number) => (
                <div key={idx} className="relative space-y-1">
                  <div className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-[var(--status-warning)] border-2 border-[var(--bg-primary)]" />
                  <div className="flex items-center gap-2 text-xs font-mono">
                    <span className="text-[var(--text-secondary)]">Hour +{trans.hour}:</span>
                    <span className="font-bold text-[var(--text-primary)]">{trans.state}</span>
                  </div>
                  <p className="text-xs text-[var(--text-secondary)] font-sans pl-2">
                    {trans.trigger}
                  </p>
                </div>
              ))}
            </div>

            {/* Injected Fault Events */}
            {selectedExperiment.fault_events?.length > 0 && (
              <div className="pt-4 border-t border-[var(--border-subtle)]/50 space-y-2">
                <h4 className="text-xs font-mono font-bold text-[var(--status-critical)]">INJECTED CHAOS FAULT LOG:</h4>
                {selectedExperiment.fault_events.map((fe: any, idx: number) => (
                  <div key={idx} className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)] text-xs font-mono space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--status-critical)] font-bold">{fe.fault_type}</span>
                      <span className="text-[10px] text-[var(--text-secondary)]">Hour +{fe.injection_hour} (Duration: {fe.duration_hours}h)</span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] font-sans">{fe.actual_outcome}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PAGE F: FAILURE FORENSICS */}
      {/* ========================================================================= */}
      {activeTab === 'forensics' && selectedExperiment && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-4">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
              <Search size={16} className="text-[var(--status-warning)]" /> Failure Forensics & Root-Cause Hypotheses — {selectedExperiment.scenario_name}
            </h3>

            {/* First Detected Failure Banner */}
            <div className="p-3.5 rounded-lg bg-[var(--status-critical)]/10 border border-[var(--status-critical)]/30 space-y-1">
              <span className="text-[11px] font-mono text-[var(--status-critical)] uppercase font-bold flex items-center gap-1.5">
                <AlertTriangle size={14} /> First Detected Failure Event
              </span>
              <p className="text-xs text-[var(--text-primary)] font-mono">
                {selectedExperiment.forensics?.first_detected_failure || "No critical failures recorded."}
              </p>
            </div>

            {/* Causes Breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)] space-y-2">
                <span className="text-xs font-mono font-bold text-[var(--status-success)] flex items-center gap-1.5">
                  <CheckCircle2 size={14} /> Confirmed Causes
                </span>
                <ul className="text-xs text-[var(--text-secondary)] space-y-1 list-disc list-inside font-sans">
                  {selectedExperiment.forensics?.confirmed_causes?.map((c: string, idx: number) => (
                    <li key={idx}>{c}</li>
                  ))}
                </ul>
              </div>

              <div className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)] space-y-2">
                <span className="text-xs font-mono font-bold text-[var(--status-warning)] flex items-center gap-1.5">
                  <Info size={14} /> Suspected Causes
                </span>
                <ul className="text-xs text-[var(--text-secondary)] space-y-1 list-disc list-inside font-sans">
                  {selectedExperiment.forensics?.suspected_causes?.map((c: string, idx: number) => (
                    <li key={idx}>{c}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Hard Safety Envelope Blocked Actions */}
            <div className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)] space-y-2">
              <span className="text-xs font-mono font-bold text-[var(--accent-tertiary)] flex items-center gap-1.5">
                <Shield size={14} /> Hard Safety Envelope Action Blocks
              </span>
              <ul className="text-xs text-[var(--text-secondary)] space-y-1 list-disc list-inside font-sans">
                {selectedExperiment.forensics?.rejected_actions?.length > 0 ? (
                  selectedExperiment.forensics.rejected_actions.map((a: string, idx: number) => (
                    <li key={idx} className="text-[var(--status-critical)]">{a}</li>
                  ))
                ) : (
                  <li>No candidate actions were rejected; plan remained feasible.</li>
                )}
              </ul>
            </div>

            {/* Suggested Follow-Ups */}
            <div className="p-3 rounded-lg bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)] space-y-2">
              <span className="text-xs font-mono font-bold text-[var(--accent-primary)] flex items-center gap-1.5">
                <ArrowRight size={14} /> Recommended Follow-Up Resilience Experiments
              </span>
              <ul className="text-xs text-[var(--text-secondary)] space-y-1 list-disc list-inside font-sans">
                {selectedExperiment.forensics?.suggested_followups?.map((f: string, idx: number) => (
                  <li key={idx}>{f}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* PAGE G: RESILIENCE REPORTS & EXPORTS */}
      {/* ========================================================================= */}
      {activeTab === 'reports' && selectedExperiment && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-[var(--surface-primary)] border border-[var(--border-subtle)] space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
                  <FileText size={16} className="text-[var(--accent-primary)]" /> Multi-Dimensional Resilience Scorecard & Report Export
                </h3>
                <span className="text-xs text-[var(--text-secondary)] font-mono">
                  Experiment ID: {selectedExperiment.id}
                </span>
              </div>

              {/* Export Buttons */}
              <div className="flex items-center gap-2">
                <a
                  href={api.getJurassicReportUrl(selectedExperiment.id, "markdown")}
                  download={`jurassic_report_${selectedExperiment.id}.md`}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--accent-primary)] text-[var(--bg-primary)] font-bold text-xs hover:bg-[var(--accent-primary)]/90 transition-colors"
                >
                  <Download size={14} />
                  Export Markdown (.md)
                </a>
                <a
                  href={api.getJurassicReportUrl(selectedExperiment.id, "csv")}
                  download={`jurassic_metrics_${selectedExperiment.id}.csv`}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[var(--bg-primary)] border border-[var(--border-subtle)] text-[var(--text-primary)] text-xs hover:border-[var(--text-muted)] transition-colors font-mono"
                >
                  <Download size={14} />
                  Export CSV (.csv)
                </a>
              </div>
            </div>

            {/* Scorecard Dimensions Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs pt-2">
              {selectedExperiment.resilience_breakdown && Object.entries(selectedExperiment.resilience_breakdown).map(([dim, score]: any) => (
                <div key={dim} className="flex justify-between p-2.5 rounded bg-[var(--bg-primary)]/70 border border-[var(--border-subtle)]/70">
                  <span className="text-[var(--text-secondary)] truncate max-w-[240px]">{dim.replace(/_/g, ' ')}:</span>
                  <span className={`font-bold ${score >= 85 ? 'text-[var(--status-success)]' : (score >= 70 ? 'text-[var(--status-warning)]' : 'text-[var(--status-critical)]')}`}>
                    {score} / 100
                  </span>
                </div>
              ))}
            </div>

            <p className="text-[11px] text-[var(--text-secondary)] font-sans leading-relaxed pt-2">
              Notice: The AEGISSTOR Resilience Scorecard calculates empirical software reliability across ten auditable dimensions.
              It represents software tolerance to unseen regimes and compound faults, not a physical hardware failure probability.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
