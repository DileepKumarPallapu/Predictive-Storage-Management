const API_BASE = "http://localhost:8000/api/v1";

export interface SystemHealth {
  status: string;
  version: string;
  mode: string;
  database: string;
  collector_status: string;
  models_loaded: number;
  timestamp: string;
}

export interface DeviceSummary {
  id: string;
  name: string;
  tier: string;
  media_type: string;
  total_capacity_bytes: number;
  warning_threshold_pct: number;
  critical_threshold_pct: number;
  max_acceptable_latency_ms: number;
  min_free_reserve_pct: number;
  status: string;
  workload_profile: string;
  current_used_bytes: number;
  current_utilization_pct: number;
  current_read_iops: number;
  current_write_iops: number;
  current_latency_p95_ms: number;
  runway_hours_estimate: number;
  risk_level: string;
}

export interface TelemetryResponse {
  device_id: string;
  metric: string;
  total_capacity_bytes: number;
  is_synthetic: boolean;
  timestamps: string[];
  values: number[];
  units: string;
  missing_intervals: { from: string; to: string; missing_hours: number }[];
}

export interface ForecastResponse {
  device_id: string;
  target_metric: string;
  model_name: string;
  forecast_horizon_hours: number;
  generated_at: string;
  historical_cutoff: string;
  timestamps: string[];
  q10: number[];
  q50: number[];
  q90: number[];
  units: string;
  hard_constraint_value: number | null;
  interval_coverage: number;
  inference_latency_ms: number;
}

export interface RiskContributor {
  factor: string;
  impact_score: number;
}

export interface RiskResponse {
  device_id: string;
  computed_at: string;
  current_capacity_pct: number;
  runway_hours_estimate: number;
  runway_hours_lower_bound: number;
  runway_hours_upper_bound: number;
  risk_level: string;
  capacity_breach_prob_24h: number;
  capacity_breach_prob_72h: number;
  latency_breach_prob_24h: number;
  risk_contributors: RiskContributor[];
}

export interface ScenarioSimulationResponse {
  scenario_id: string;
  device_id: string;
  name: string;
  action_type: string;
  parameters: Record<string, any>;
  duration_minutes: number;
  estimated_cost_usd: number;
  overhead_io_penalty_pct: number;
  safety_envelope_passed: boolean;
  violation_reasons: string[];
  residual_risk_score: number;
  assumptions: string[];
  timeline_timestamps: string[];
  baseline_q50: number[];
  counterfactual_q50: number[];
  hard_limit: number;
  is_simulated_estimate: boolean;
}

export interface RecommendationItem {
  id: string;
  device_id: string;
  action_type: string;
  title: string;
  rationale: string;
  rank: number;
  utility_score: number;
  estimated_runway_gain_hours: number;
  hard_constraints_checked: boolean;
  approval_status: string;
  reviewed_by?: string;
  review_notes?: string;
  created_at: string;
}

export interface AlertItem {
  id: string;
  device_id: string;
  category: string;
  severity: string;
  title: string;
  message: string;
  status: string;
  triggered_at: string;
  resolved_at?: string;
}

export interface ExperimentItem {
  id: string;
  name: string;
  dataset_name: string;
  model_type: string;
  horizon_hours: number;
  train_samples: number;
  test_samples: number;
  mae: number;
  rmse: number;
  pinball_loss: number;
  interval_coverage: number;
  mean_interval_width: number;
  created_at: string;
  manifest: Record<string, any>;
}

export interface ReliabilityMetrics {
  model_version: string;
  overall_interval_coverage: number;
  target_nominal_coverage: number;
  mean_pinball_loss: number;
  mean_mae_capacity_gb: number;
  mean_mae_latency_ms: number;
  drift_status: string;
  active_drift_alerts: number;
  last_evaluation_timestamp: string;
  is_fallback_active: boolean;
}

export interface DatasetItem {
  id: string;
  name: string;
  dataset_type: string;
  records_count: number;
  missing_rate: number;
  sampling_interval_s: number;
  license: string;
  description: string;
  created_at: string;
}

export interface AuditItem {
  id: number;
  timestamp: string;
  user: string;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, any>;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

// Token storage helpers
export const authStorage = {
  getToken: () => localStorage.getItem("aegisstor_jwt"),
  setToken: (token: string) => localStorage.setItem("aegisstor_jwt", token),
  clearToken: () => localStorage.removeItem("aegisstor_jwt"),
};

// Helper fetch wrapper with JWT attachment and standardized error parsing
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = authStorage.getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options?.headers as Record<string, string>),
  };

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errData = null;
      let errMsg = `HTTP ${res.status}`;
      try {
        errData = await res.json();
        errMsg = errData.detail || errData.message || errMsg;
      } catch {
        errMsg = await res.text();
      }
      throw new ApiError(res.status, errMsg, errData);
    }

    return (await res.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, err.message || "Network request failed");
  }
}

export interface RiskTimelineItem {
  id: string;
  timestamp: string;
  category: string;
  severity: string;
  title: string;
  device_id: string;
  is_forecasted: boolean;
}

export interface ExecutiveOverviewResponse {
  total_capacity_bytes: number;
  total_used_bytes: number;
  total_free_bytes: number;
  capacity_utilization_pct: number;
  estimated_reserve_runway_hours: number;
  monitored_device_count: number;
  highest_current_risk: {
    level: string;
    device_id: string;
  };
  last_successful_collection: string;
  data_mode_label: string;
  is_synthetic: boolean;
  risk_timeline: RiskTimelineItem[];
  top_recommendation?: {
    id: string;
    device_id: string;
    title: string;
    action_type: string;
    utility_score: number;
    estimated_runway_gain_hours: number;
    approval_status: string;
  };
}

export const api = {
  getHealth: () => apiFetch<SystemHealth>("/health"),
  getOverview: () => apiFetch<ExecutiveOverviewResponse>("/overview"),
  setOperatingMode: (mode: string) =>
    apiFetch<{ message: string; mode: string }>("/system/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  getDevices: (tier?: string, status?: string, search?: string) => {
    const params = new URLSearchParams();
    if (tier) params.append("tier", tier);
    if (status) params.append("status", status);
    if (search) params.append("search", search);
    return apiFetch<DeviceSummary[]>(`/devices?${params.toString()}`);
  },

  getDevice: (id: string) => apiFetch<DeviceSummary>(`/devices/${id}`),

  updateThresholds: (id: string, payload: any) =>
    apiFetch(`/devices/${id}/thresholds`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  getTelemetry: (deviceId: string, metric = "used_bytes", hours = 720) =>
    apiFetch<TelemetryResponse>(
      `/devices/${deviceId}/telemetry?metric=${metric}&hours=${hours}`
    ),

  getForecast: (
    deviceId: string,
    metric = "used_bytes",
    model = "lightgbm_quantile",
    horizon = 72
  ) =>
    apiFetch<ForecastResponse>(
      `/devices/${deviceId}/forecasts?target_metric=${metric}&model_type=${model}&horizon_hours=${horizon}`
    ),

  getRisks: (deviceId: string) =>
    apiFetch<RiskResponse>(`/devices/${deviceId}/risks`),

  getReserveRunway: (deviceId: string) =>
    apiFetch<any>(`/devices/${deviceId}/reserve-runway`),

  getRiskAssessment: (deviceId: string) =>
    apiFetch<any>(`/devices/${deviceId}/risk-assessment`),

  evaluatePlanning: (deviceId: string) =>
    apiFetch<any>("/planning/evaluate", {
      method: "POST",
      body: JSON.stringify({ device_id: deviceId }),
    }),

  listScenarios: (deviceId?: string) =>
    apiFetch<any[]>(`/scenarios${deviceId ? `?device_id=${deviceId}` : ""}`),

  getScenario: (scenarioId: string) =>
    apiFetch<any>(`/scenarios/${scenarioId}`),

  rerunScenario: (scenarioId: string, seed = 42) =>
    apiFetch<ScenarioSimulationResponse>(`/scenarios/${scenarioId}/run?seed=${seed}`, {
      method: "POST",
    }),

  getScenarioResults: (scenarioId: string) =>
    apiFetch<any>(`/scenarios/${scenarioId}/results`),

  createScenario: (payload: {
    device_id: string;
    name: string;
    action_type: string;
    parameters: Record<string, any>;
  }) =>
    apiFetch<ScenarioSimulationResponse>("/scenarios", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getRecommendations: (deviceId: string) =>
    apiFetch<RecommendationItem[]>(`/devices/${deviceId}/recommendations`),

  approveRecommendation: (id: string, notes?: string) =>
    apiFetch(`/recommendations/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  rejectRecommendation: (id: string, notes?: string) =>
    apiFetch(`/recommendations/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),

  getExperiments: () => apiFetch<ExperimentItem[]>("/experiments"),
  getAblationStudies: () => apiFetch<any>("/experiments/ablations"),

  runExperiment: (payload: {
    name: string;
    dataset_name: string;
    model_type: string;
    horizon_hours: number;
  }) =>
    apiFetch<ExperimentItem>("/experiments", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getModelReliability: () =>
    apiFetch<ReliabilityMetrics>("/models/reliability"),

  getAlerts: (category?: string, severity?: string, status?: string) => {
    const params = new URLSearchParams();
    if (category) params.append("category", category);
    if (severity) params.append("severity", severity);
    if (status) params.append("status", status);
    return apiFetch<AlertItem[]>(`/alerts?${params.toString()}`);
  },

  acknowledgeAlert: (id: string) =>
    apiFetch(`/alerts/${id}/acknowledge`, { method: "POST" }),

  resolveAlert: (id: string) =>
    apiFetch(`/alerts/${id}/resolve`, { method: "POST" }),

  getDatasets: () => apiFetch<DatasetItem[]>("/datasets"),

  getSettings: () => apiFetch<any>("/settings"),

  getAuditTrail: () => apiFetch<AuditItem[]>("/audit"),

  // Authentication & RBAC methods
  login: async (username: string, password: string) => {
    const data = await apiFetch<{
      access_token: string;
      token_type: string;
      user_id: string;
      username: string;
      role: string;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    if (data.access_token) {
      authStorage.setToken(data.access_token);
    }
    return data;
  },

  getCurrentUser: () =>
    apiFetch<{
      id: string;
      username: string;
      email: string;
      role: string;
      is_active: boolean;
    }>("/auth/me"),

  logout: () => {
    authStorage.clearToken();
  },

  // ==========================================
  // AEGISSTOR OMEGA FLEET INTELLIGENCE API
  // ==========================================
  getOmegaTopology: () => apiFetch<any>("/omega/topology"),
  getOmegaFleetRisk: () => apiFetch<any>("/omega/fleet-risk"),
  getOmegaDecisionEvaluation: (deviceId = "vol-nvme-tier1-db", horizonHours = 72) =>
    apiFetch<any>(`/omega/decision-evaluation?device_id=${deviceId}&horizon_hours=${horizonHours}`),
  getOmegaAdaptiveMonitoring: (simulationDays = 30) =>
    apiFetch<any>(`/omega/adaptive-monitoring?simulation_days=${simulationDays}`),
  simulateOmegaFleetPlan: (plan: {
    source_device_id: string;
    destination_device_id: string;
    migration_size_gb: number;
    bandwidth_cap_mb_s: number;
  }) =>
    apiFetch<any>("/omega/fleet-plan", {
      method: "POST",
      body: JSON.stringify(plan),
    }),
  getOmegaOutcomeLedger: (limit = 50) =>
    apiFetch<any>(`/omega/outcome-ledger?limit=${limit}`),
  getOmegaGovernance: () => apiFetch<any>("/omega/governance"),
  evaluateOmegaCandidate: (candidate: any) =>
    apiFetch<any>("/omega/governance/evaluate", {
      method: "POST",
      body: JSON.stringify(candidate),
    }),

  // ==========================================
  // AEGISSTOR JURASSIC RESILIENCE LAB API
  // ==========================================
  getJurassicCommandCenter: () => apiFetch<any>("/jurassic/command-center"),
  getJurassicScenarios: (family?: string) => {
    const params = family ? `?family=${family}` : "";
    return apiFetch<any[]>(`/jurassic/scenarios${params}`);
  },
  getJurassicScenario: (id: string) => apiFetch<any>(`/jurassic/scenarios/${id}`),
  createJurassicScenario: (scenario: any) =>
    apiFetch<any>("/jurassic/scenarios", {
      method: "POST",
      body: JSON.stringify(scenario),
    }),
  runJurassicExperiment: (scenarioId: string, targetDeviceId?: string) =>
    apiFetch<any>("/jurassic/experiments/run", {
      method: "POST",
      body: JSON.stringify({ scenario_id: scenarioId, target_device_id: targetDeviceId }),
    }),
  getJurassicExperiments: (limit = 20) =>
    apiFetch<any[]>(`/jurassic/experiments?limit=${limit}`),
  getJurassicExperimentDetails: (id: string) =>
    apiFetch<any>(`/jurassic/experiments/${id}`),
  getJurassicFallbackStates: () => apiFetch<any>("/jurassic/fallback-states"),
  getJurassicReportUrl: (experimentId: string, format: "markdown" | "csv" = "markdown") =>
    `${API_BASE}/jurassic/experiments/${experimentId}/report?format=${format}`,
};
